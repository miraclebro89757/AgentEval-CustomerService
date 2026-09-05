"""LangGraph 节点：预处理子 Agent、Supervisor、RAG 子 Agent、回复子 Agent。"""

from __future__ import annotations

import json
import re
import time
import uuid
from typing import Any, Literal

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.prebuilt import ToolNode

from graph.llm import extract_json_object, get_chat_model
from graph.retriever import retrieve
from graph.safety import boundary_reply, scan_policy_violation
from graph.state import BLOCKED_ROUTE, INTENT_TO_ROUTE, VALID_INTENTS, VALID_ROUTES, AgentState
from graph.tools import CUSTOMER_TOOLS, invoke_tool
from prompts import load_agent

ORDER_RE = re.compile(r"\bA\d{7,10}\b", re.I)

INTENT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "greeting": ("你好", "您好", "在吗", "hi", "hello", "早上好"),
    "complaint": ("投诉", "损坏", "划痕", "撞坏", "太气", "差评", "态度"),
    "refund": ("退货", "退款", "无理由", "能退吗", "退多少"),
    "order_status": ("发到哪", "到哪了", "物流", "运单", "查一下订单", "订单"),
    "shipping": ("发货", "几天能到", "几天能收到", "配送", "时效", "改地址", "拦截"),
    "account": ("密码", "登录", "账号", "注销", "发票", "积分", "验证码"),
    "product_inquiry": (
        "耳机",
        "手表",
        "续航",
        "规格",
        "参数",
        "兼容",
        "音频线",
        "打电话",
        "降噪",
        "wh-100",
        "s2",
    ),
    "out_of_scope": ("下雨", "天气", "写一首", "写诗", "股票", "彩票"),
}


def _now() -> float:
    return time.perf_counter()


def _trace(state: AgentState, node: str, inputs: dict, outputs: dict, started: float) -> dict:
    traces = list(state.get("node_traces") or [])
    traces.append(
        {
            "node": node,
            "input": inputs,
            "output": outputs,
            "latency_ms": round((_now() - started) * 1000, 2),
        }
    )
    path = list(state.get("path") or [])
    path.append(node)
    return {"node_traces": traces, "path": path}


def _extract_order_id(text: str) -> str | None:
    match = ORDER_RE.search(text or "")
    return match.group(0).upper() if match else None


def classify_intent_heuristic(query: str) -> tuple[str, float]:
    if scan_policy_violation(query):
        return "policy_violation", 1.0
    q = (query or "").strip().lower()
    scores: dict[str, int] = {}
    for intent, kws in INTENT_KEYWORDS.items():
        scores[intent] = sum(1 for kw in kws if kw.lower() in q)
    # 退货咨询优先于纯订单查询
    if scores.get("refund") and scores.get("order_status"):
        scores["order_status"] = 0
    if scores.get("complaint"):
        scores["refund"] = max(0, scores.get("refund", 0) - 1)
    best = max(scores, key=lambda k: scores[k])
    best_score = scores[best]
    if best_score <= 0:
        if len(q) <= 8 and any(g in q for g in ("你好", "在吗", "hi")):
            return "greeting", 0.8
        return "chitchat", 0.45
    confidence = min(0.95, 0.55 + 0.15 * best_score)
    return best, confidence


def _heuristic_preprocess(query: str) -> dict[str, Any]:
    intent, confidence = classify_intent_heuristic(query)
    order_id = _extract_order_id(query)
    product = None
    if "耳机" in query or "WH-100" in query.upper() or "降噪" in query:
        product = "星云降噪耳机 Pro"
    elif "手表" in query or "S2" in query.upper():
        product = "星云手表 S2"
    cleaned = re.sub(r"\s+", " ", query).strip()
    return {
        "intent": intent,
        "intent_confidence": confidence,
        "cleaned_query": cleaned,
        "entities": {"order_id": order_id, "product": product},
    }


def _policy_block_payload(query: str, hit: dict[str, Any]) -> dict[str, Any]:
    reply = boundary_reply()
    cleaned = re.sub(r"\s+", " ", query).strip()
    return {
        "intent": "policy_violation",
        "intent_confidence": 1.0,
        "cleaned_query": cleaned,
        "entities": {},
        "policy_blocked": True,
        "policy_hit": hit,
        "route": BLOCKED_ROUTE,
        "route_reason": "预处理命中安全策略，声明服务边界并终止后续节点",
        "final_reply": reply,
        "messages": [AIMessage(content=reply)],
    }


def intent_preprocess(state: AgentState) -> dict:
    """子 Agent 1：安全过滤 + 意图识别 + 预处理。黄赌毒命中则直接声明边界。"""
    started = _now()
    query = state.get("user_query") or ""
    if state.get("messages"):
        first = state["messages"][0]
        query = query or getattr(first, "content", "") or str(first)
    hit = scan_policy_violation(query)
    if hit:
        result = _policy_block_payload(query, hit)
        traced = _trace(
            state,
            "intent_preprocess",
            {"user_query": query},
            {
                "intent": result["intent"],
                "policy_blocked": True,
                "policy_hit": hit,
                "route": BLOCKED_ROUTE,
            },
            started,
        )
        return {"user_query": query, **result, **traced}
    result = _heuristic_preprocess(query)
    model = get_chat_model()
    if model is not None:
        try:
            prompt = load_agent("intent_preprocess")
            msg = model.invoke(
                [
                    SystemMessage(content=prompt.render_system()),
                    HumanMessage(content=prompt.render_user(query=query)),
                ]
            )
            parsed = extract_json_object(getattr(msg, "content", "") or "")
            if parsed and parsed.get("intent") in VALID_INTENTS and parsed.get("intent") != "policy_violation":
                result["intent"] = parsed["intent"]
                result["intent_confidence"] = float(parsed.get("confidence") or result["intent_confidence"])
                result["cleaned_query"] = parsed.get("cleaned_query") or result["cleaned_query"]
                entities = dict(result["entities"])
                entities.update(parsed.get("entities") or {})
                if not entities.get("order_id"):
                    entities["order_id"] = _extract_order_id(query)
                result["entities"] = entities
        except Exception:
            pass
    traced = _trace(
        state,
        "intent_preprocess",
        {"user_query": query},
        result,
        started,
    )
    return {"user_query": query, **result, **traced}


def _route_for_intent(intent: str) -> str:
    return INTENT_TO_ROUTE.get(intent, "direct_reply")


def after_preprocess(state: AgentState) -> Literal["supervisor", "end"]:
    """安全命中后不再进入 Supervisor / RAG / 工具。"""
    if state.get("policy_blocked") or state.get("intent") == "policy_violation":
        return "end"
    return "supervisor"


def supervisor(state: AgentState) -> dict:
    """主 Agent：只做意图复核和路由，不生成最终回复。"""
    started = _now()
    if state.get("policy_blocked") or state.get("intent") == "policy_violation":
        outputs = {
            "supervisor_intent": "policy_violation",
            "route": BLOCKED_ROUTE,
            "route_reason": "预处理已声明服务边界，Supervisor 不再改路由",
        }
        traced = _trace(
            state,
            "supervisor",
            {"intent": state.get("intent"), "entities": state.get("entities") or {}},
            outputs,
            started,
        )
        return {**outputs, **traced}
    intent = state.get("intent") or "chitchat"
    query = state.get("user_query") or ""
    route = _route_for_intent(intent)
    reason = f"根据意图 {intent} 按路由表分发给 {route}"
    supervisor_intent = intent

    model = get_chat_model()
    if model is not None:
        try:
            prompt = load_agent("supervisor")
            msg = model.invoke(
                [
                    SystemMessage(content=prompt.render_system()),
                    HumanMessage(
                        content=prompt.render_user(
                            query=query,
                            intent=intent,
                            entities=json.dumps(state.get("entities") or {}, ensure_ascii=False),
                        )
                    ),
                ]
            )
            parsed = extract_json_object(getattr(msg, "content", "") or "")
            if parsed:
                if parsed.get("intent") in VALID_INTENTS:
                    supervisor_intent = parsed["intent"]
                    route = _route_for_intent(supervisor_intent)
                if parsed.get("route") in VALID_ROUTES:
                    route = parsed["route"]
                if parsed.get("reason"):
                    reason = str(parsed["reason"])
        except Exception:
            pass

    outputs = {
        "supervisor_intent": supervisor_intent,
        "route": route,
        "route_reason": reason,
    }
    traced = _trace(
        state,
        "supervisor",
        {"intent": intent, "entities": state.get("entities") or {}},
        outputs,
        started,
    )
    return {**outputs, **traced}


def route_from_supervisor(state: AgentState) -> Literal["rag_agent", "tool_agent", "direct_reply"]:
    route = state.get("route") or "direct_reply"
    if route not in VALID_ROUTES:
        return "direct_reply"
    return route  # type: ignore[return-value]


def rag_retrieve(state: AgentState) -> dict:
    """子 Agent 2：模拟知识库检索。"""
    started = _now()
    query = state.get("cleaned_query") or state.get("user_query") or ""
    policy = load_agent("rag_retrieve").policy
    docs = retrieve(query, top_k=int(policy.get("top_k") or 3), intent=state.get("intent"))
    outputs = {
        "retrieval_query": query,
        "retrieved_docs": docs,
        "retrieved_doc_ids": [d["id"] for d in docs],
    }
    traced = _trace(
        state,
        "rag_retrieve",
        {"retrieval_query": query},
        {
            "retrieved_doc_ids": outputs["retrieved_doc_ids"],
            "titles": [d.get("title") for d in docs],
        },
        started,
    )
    return {**outputs, **traced}


def _docs_block(state: AgentState) -> str:
    docs = state.get("retrieved_docs") or []
    if not docs:
        return "（无检索结果）"
    lines = []
    for doc in docs:
        lines.append(f"- [{doc.get('id')}] {doc.get('title')}: {doc.get('content')}")
    return "\n".join(lines)


def _tool_messages_text(state: AgentState) -> str:
    chunks = []
    for msg in state.get("messages") or []:
        if isinstance(msg, ToolMessage):
            chunks.append(f"{msg.name}: {msg.content}")
    return "\n".join(chunks) if chunks else "（尚无工具结果）"


def _plan_heuristic_tools(state: AgentState) -> list[tuple[str, dict[str, Any]]]:
    if state.get("policy_blocked") or state.get("intent") == "policy_violation":
        return []
    intent = state.get("intent") or ""
    entities = state.get("entities") or {}
    order_id = entities.get("order_id")
    already = {item.get("name") for item in (state.get("tools_called") or [])}
    planned: list[tuple[str, dict[str, Any]]] = []

    def add(name: str, args: dict[str, Any]) -> None:
        if name not in already:
            planned.append((name, args))

    query = state.get("user_query") or ""
    if order_id:
        add("lookup_order", {"order_id": order_id})
        if intent == "order_status":
            add("get_shipping_status", {"order_id": order_id})
        if intent == "refund":
            add("calculate_refund", {"order_id": order_id, "reason": "无理由退货"})
        if intent == "complaint":
            add(
                "create_ticket",
                {
                    "category": "complaint",
                    "summary": query[:80],
                    "order_id": order_id,
                },
            )
    elif intent == "complaint":
        add(
            "create_ticket",
            {"category": "complaint", "summary": query[:80], "order_id": ""},
        )
    return planned


def _heuristic_final_reply(state: AgentState) -> str:
    intent = state.get("intent") or "chitchat"
    query = state.get("user_query") or ""
    if state.get("policy_blocked") or intent == "policy_violation":
        return boundary_reply()
    docs = state.get("retrieved_docs") or []
    tool_text = _tool_messages_text(state)
    order_id = (state.get("entities") or {}).get("order_id")

    if intent == "greeting":
        return "您好，我是星云数码客服助手。可以帮您查订单、退换货政策、商品规格或账号问题，请问需要什么帮助？"
    if intent == "out_of_scope":
        return (
            "这个问题超出了我的职责范围，我这边主要处理购物、物流、退换货和账号售后。"
            "如果您有订单或商品相关的问题，我很乐意继续帮您。"
        )
    if intent == "chitchat":
        return "我在的。您可以直接说订单号、商品名称或具体售后问题，我来帮您处理。"

    facts = []
    for doc in docs[:3]:
        facts.append(doc.get("content", ""))
    fact_blob = "\n".join(facts)

    if intent == "product_inquiry":
        top = (docs[0].get("content", "") if docs else "") or fact_blob
        if "手表" in query or "S2" in query.upper() or "独立通话" in top:
            return (
                "您好，星云手表 S2 不支持独立通话，需连接手机使用；"
                "兼容 Android 10+ 与 iOS 15+。您可以继续问我续航或表带问题。"
            )
        extra = ""
        if "28 小时" in top or "28小时" in top or "续航" in query:
            extra += "开启降噪后续航约 28 小时，关闭降噪约 40 小时。"
        if "3.5mm" in top or "音频线" in query or "音频线" in top:
            extra += "包装内含 Type-C 充电线、3.5mm 音频线和收纳盒。"
        if extra:
            return f"您好，根据商品说明：{extra} 您可以继续问我其他规格。"
        if top:
            return f"您好，为您查到如下信息：{top} 如需对比其他型号，您可以继续问我。"
        return "您好，我暂时没有检索到对应规格，请告诉我具体型号（例如 WH-100 或手表 S2）。"

    if intent in {"refund", "shipping", "account"} and fact_blob:
        prefix = docs[0].get("content", "")
        more = docs[1].get("content", "") if len(docs) > 1 else ""
        tool_note = ""
        if "refund_amount" in tool_text or "已签收" in tool_text or "ok" in tool_text:
            tool_note = f" 结合您的订单数据：{tool_text}"
        if not order_id and intent == "refund" and "订单" in query:
            return f"您好，{prefix} 请提供订单号，我可以帮您试算能否退货以及可退金额。"
        return f"您好，{prefix} {more}{tool_note} 您可以按上述说明办理，需要我帮您操作请再说一声。".strip()

    if "lookup_order" in tool_text or "get_shipping_status" in tool_text or "create_ticket" in tool_text:
        polite = "抱歉给您添麻烦了，已为您查询：" if intent == "complaint" else "您好，已为您查到："
        return f"{polite}{tool_text} 如需继续处理退换货或加急，请告诉我。"

    if intent == "order_status" and not order_id:
        return "好的，我可以帮您查物流。请提供订单号（形如 A20240901）。"
    if intent == "complaint":
        return "非常抱歉给您带来不便。请补充订单号和问题照片/视频，我会为您创建投诉工单并走质量问题售后。"
    return "收到，我来帮您处理。请再补充一下订单号或具体商品名称，我可以查政策或调用订单工具。"


def reply_generate(state: AgentState) -> dict:
    """子 Agent 3：可调用工具的回复生成。"""
    started = _now()
    if state.get("policy_blocked") or state.get("intent") == "policy_violation":
        reply = state.get("final_reply") or boundary_reply()
        ai_msg = AIMessage(content=reply)
        outputs = {"action": "boundary", "final_reply": reply}
        traced = _trace(
            state,
            "reply_generate",
            {"query": state.get("user_query") or "", "tool_round": 0},
            outputs,
            started,
        )
        return {"messages": [ai_msg], "final_reply": reply, **traced}
    model = get_chat_model()
    query = state.get("user_query") or ""
    tool_round = int(state.get("tool_round") or 0)

    if model is not None:
        prompt = load_agent("reply_generate")
        llm = model.bind_tools(CUSTOMER_TOOLS)
        sys = prompt.render_system(
            knowledge=_docs_block(state),
            entities=json.dumps(state.get("entities") or {}, ensure_ascii=False),
        )
        history = list(state.get("messages") or [])
        if not history:
            history = [HumanMessage(content=query)]
        ai_msg = llm.invoke([SystemMessage(content=sys), *history])
        update: dict[str, Any] = {"messages": [ai_msg]}
        if getattr(ai_msg, "tool_calls", None):
            planned = [
                {"name": tc.get("name"), "args": tc.get("args") or {}, "id": tc.get("id")}
                for tc in ai_msg.tool_calls
            ]
            outputs = {"action": "call_tools", "tool_calls": planned, "tool_round": tool_round}
        else:
            text = getattr(ai_msg, "content", "") or ""
            update["final_reply"] = text
            outputs = {"action": "final_reply", "final_reply": text}
        traced = _trace(state, "reply_generate", {"query": query, "tool_round": tool_round}, outputs, started)
        return {**update, **traced}

    planned = _plan_heuristic_tools(state)
    if planned:
        tool_calls = []
        for name, args in planned:
            tool_calls.append(
                {
                    "name": name,
                    "args": args,
                    "id": f"call_{name}_{uuid.uuid4().hex[:8]}",
                    "type": "tool_call",
                }
            )
        ai_msg = AIMessage(content="", tool_calls=tool_calls)
        outputs = {"action": "call_tools", "tool_calls": tool_calls, "tool_round": tool_round}
        traced = _trace(state, "reply_generate", {"query": query, "tool_round": tool_round}, outputs, started)
        return {"messages": [ai_msg], **traced}

    reply = _heuristic_final_reply(state)
    ai_msg = AIMessage(content=reply)
    outputs = {"action": "final_reply", "final_reply": reply}
    traced = _trace(state, "reply_generate", {"query": query, "tool_round": tool_round}, outputs, started)
    return {"messages": [ai_msg], "final_reply": reply, **traced}


_RAW_TOOL_NODE = ToolNode(CUSTOMER_TOOLS)


def tools_node(state: AgentState) -> dict:
    """包装 ToolNode，把调用记录写进 state.tools_called，供节点级评测使用。"""
    started = _now()
    result = _RAW_TOOL_NODE.invoke(state)
    called = list(state.get("tools_called") or [])
    last = (state.get("messages") or [None])[-1]
    new_calls = []
    if last is not None and getattr(last, "tool_calls", None):
        for tc in last.tool_calls:
            name = tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", "")
            args = tc.get("args") if isinstance(tc, dict) else getattr(tc, "args", {})
            output = None
            for msg in result.get("messages") or []:
                if isinstance(msg, ToolMessage) and msg.name == name:
                    output = msg.content
                    break
            record = {"name": name, "args": args or {}, "output": output}
            called.append(record)
            new_calls.append(record)
    traced = _trace(
        state,
        "tools",
        {"tool_round": int(state.get("tool_round") or 0)},
        {"tools_called": new_calls},
        started,
    )
    return {
        **result,
        "tools_called": called,
        "tool_round": int(state.get("tool_round") or 0) + 1,
        **traced,
    }


def after_reply(state: AgentState) -> Literal["tools", "end"]:
    if state.get("policy_blocked") or state.get("intent") == "policy_violation":
        return "end"
    max_rounds = int(load_agent("reply_generate").policy.get("max_tool_rounds") or 3)
    if int(state.get("tool_round") or 0) >= max_rounds:
        return "end"
    messages = state.get("messages") or []
    if not messages:
        return "end"
    last = messages[-1]
    if getattr(last, "tool_calls", None):
        return "tools"
    return "end"


# 启发式模式下若模型不可用，仍允许直接 invoke 单个工具（评测单测会用到）
__all__ = [
    "intent_preprocess",
    "after_preprocess",
    "supervisor",
    "route_from_supervisor",
    "rag_retrieve",
    "reply_generate",
    "tools_node",
    "after_reply",
    "invoke_tool",
]
