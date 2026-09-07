"""编译 Supervisor + 子 Agent 的 StateGraph。"""

from __future__ import annotations

from typing import Any

from langchain_core.messages import HumanMessage
from langgraph.graph import END, START, StateGraph

from graph.llm import load_llm_settings
from graph.nodes import (
    after_preprocess,
    after_reply,
    intent_preprocess,
    rag_retrieve,
    reply_generate,
    route_from_supervisor,
    supervisor,
    tools_node,
)
from graph.state import AgentState


def build_graph():
    workflow = StateGraph(AgentState)
    workflow.add_node("intent_preprocess", intent_preprocess)
    workflow.add_node("supervisor", supervisor)
    workflow.add_node("rag_retrieve", rag_retrieve)
    workflow.add_node("reply_generate", reply_generate)
    workflow.add_node("tools", tools_node)

    workflow.add_edge(START, "intent_preprocess")
    workflow.add_conditional_edges(
        "intent_preprocess",
        after_preprocess,
        {"supervisor": "supervisor", "end": END},
    )
    workflow.add_conditional_edges(
        "supervisor",
        route_from_supervisor,
        {
            "rag_agent": "rag_retrieve",
            "tool_agent": "reply_generate",
            "direct_reply": "reply_generate",
        },
    )
    workflow.add_edge("rag_retrieve", "reply_generate")
    workflow.add_conditional_edges(
        "reply_generate",
        after_reply,
        {"tools": "tools", "end": END},
    )
    workflow.add_edge("tools", "reply_generate")
    return workflow.compile()


def _deepeval_callbacks(case_id: str | None = None) -> list:
    """官方推荐：把 DeepEval CallbackHandler 挂到 graph.invoke。失败则静默跳过。"""
    try:
        from deepeval.integrations.langchain import CallbackHandler

        kwargs: dict[str, Any] = {
            "name": "customer-service-graph",
            "tags": ["langgraph", "customer-service", "agenteval"],
            "metadata": {"demo": "AgentEval-CustomerService", "case_id": case_id},
        }
        return [CallbackHandler(**kwargs)]
    except Exception:
        return []


def invoke_agent(
    query: str,
    *,
    graph=None,
    case_id: str | None = None,
    use_deepeval_callback: bool = True,
    memory: dict[str, Any] | None = None,
    history: list | None = None,
    turn_index: int = 1,
) -> AgentState:
    compiled = graph or build_graph()
    callbacks = _deepeval_callbacks(case_id) if use_deepeval_callback else []
    config: dict[str, Any] = {"recursion_limit": 12}
    if callbacks:
        config["callbacks"] = callbacks
    prior = list(history or [])
    result = compiled.invoke(
        {
            "messages": [*prior, HumanMessage(content=query)],
            "user_query": query,
            "path": [],
            "node_traces": [],
            "tools_called": [],
            "retrieved_docs": [],
            "retrieved_doc_ids": [],
            "tool_round": 0,
            "entities": {},
            "policy_blocked": False,
            "policy_hit": {},
            "duty_hit": {},
            "memory": memory or {},
            "turn_index": turn_index,
            "session_capped": False,
        },
        config=config,
    )
    if not result.get("final_reply"):
        last = (result.get("messages") or [None])[-1]
        content = getattr(last, "content", None)
        if content:
            result["final_reply"] = content
    result["_runtime"] = load_llm_settings().mode
    return result
