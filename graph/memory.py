"""多轮会话记忆：滑动窗口保留最近 5 轮（用户 5 次 + 助手 5 次）。"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage

WINDOW_TURNS = 5
MAX_USER_TURNS = WINDOW_TURNS
MAX_AI_TURNS = WINDOW_TURNS

# 短句承接：上一轮已有订单/商品时，用来判定本轮意图。
FOLLOWUP_INTENTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("refund", ("那就退", "帮我退", "退吧", "退掉", "申请退", "退了", "退货吧")),
    ("order_status", ("到哪了", "物流呢", "发到哪", "到了吗", "到了没", "什么时候到")),
    ("account", ("积分呢", "多少分", "会员呢")),
    ("product_inquiry", ("保修呢", "在保吗", "质保呢", "有货吗", "续航呢", "规格呢")),
    ("complaint", ("要投诉", "投诉一下")),
)

DEICTIC_ORDER = (
    "那个订单",
    "这个订单",
    "刚才那个",
    "刚才的订单",
    "该订单",
    "同一单",
    "还是这个",
    "那单",
    "上一单",
)


def merge_entities(base: dict[str, Any] | None, overlay: dict[str, Any] | None) -> dict[str, Any]:
    """overlay 里的空值不覆盖已记住的订单号 / 商品。"""
    merged = dict(base or {})
    for key, value in (overlay or {}).items():
        if value not in (None, "", [], {}):
            merged[key] = value
    return merged


def is_deictic_order(query: str) -> bool:
    return any(token in (query or "") for token in DEICTIC_ORDER)


def resolve_followup_intent(query: str, last_intent: str | None) -> str | None:
    """短句/指代在有上一轮意图时，补出本轮意图。"""
    q = (query or "").strip()
    if not q:
        return None
    for intent, keywords in FOLLOWUP_INTENTS:
        if any(token in q for token in keywords):
            return intent
    if is_deictic_order(q) and last_intent in {
        "order_status",
        "refund",
        "shipping",
        "complaint",
        "account",
        "product_inquiry",
    }:
        return last_intent
    return None


def format_dialogue(turns: list[dict[str, str]]) -> str:
    if not turns:
        return ""
    lines = []
    for turn in turns:
        role = "用户" if turn.get("role") == "user" else "助手"
        lines.append(f"{role}：{turn.get('content') or ''}")
    return "\n".join(lines)


def format_memory_block(memory: dict[str, Any] | None) -> str:
    memory = memory or {}
    if not memory.get("dialogue") and not memory.get("entities") and not memory.get("last_intent"):
        return "（无历史对话）"
    used = int(memory.get("user_turns") or 0)
    cap = int(memory.get("max_user_turns") or WINDOW_TURNS)
    entities = json.dumps(memory.get("entities") or {}, ensure_ascii=False)
    return "\n".join(
        [
            f"对话窗口：最近 {used}/{cap} 轮（超出则丢掉最早一轮）",
            f"上一轮意图：{memory.get('last_intent') or '无'}",
            f"已知实体：{entities}",
            "最近对话：",
            str(memory.get("dialogue") or "（空）"),
            "用户说「那个订单 / 刚才 / 还能退吗」时必须沿用已知实体，不要丢掉订单号。",
        ]
    )


def history_messages(turns: list[dict[str, str]]) -> list:
    messages = []
    for turn in turns:
        content = str(turn.get("content") or "")
        if turn.get("role") == "user":
            messages.append(HumanMessage(content=content))
        else:
            messages.append(AIMessage(content=content))
    return messages


def _pairs_from_turns(turns: list[dict[str, str]]) -> list[tuple[dict[str, str], dict[str, str] | None]]:
    pairs: list[tuple[dict[str, str], dict[str, str] | None]] = []
    index = 0
    while index < len(turns):
        item = turns[index]
        if item.get("role") != "user":
            index += 1
            continue
        assistant = None
        if index + 1 < len(turns) and turns[index + 1].get("role") == "assistant":
            assistant = turns[index + 1]
            index += 2
        else:
            index += 1
        pairs.append((item, assistant))
    return pairs


def keep_recent_window(turns: list[dict[str, str]], window: int = WINDOW_TURNS) -> list[dict[str, str]]:
    """只留最近 window 轮（每轮 = 用户一条 + 助手一条）。"""
    trimmed: list[dict[str, str]] = []
    for user, assistant in _pairs_from_turns(turns)[-window:]:
        trimmed.append(user)
        if assistant is not None:
            trimmed.append(assistant)
    return trimmed


class Conversation:
    """跨轮记住实体和对话；始终只保留最近 5 轮，更早的从窗口里剔除。"""

    def __init__(self, graph=None):
        self.turns: list[dict[str, str]] = []
        self.entities: dict[str, Any] = {}
        self.last_intent: str | None = None
        self.last_route: str | None = None
        self._round_meta: list[dict[str, Any]] = []
        self._graph = graph

    @property
    def user_turns(self) -> int:
        return sum(1 for turn in self.turns if turn.get("role") == "user")

    @property
    def ai_turns(self) -> int:
        return sum(1 for turn in self.turns if turn.get("role") == "assistant")

    def reset(self) -> None:
        self.turns = []
        self.entities = {}
        self.last_intent = None
        self.last_route = None
        self._round_meta = []

    def snapshot(self) -> dict[str, Any]:
        return {
            "entities": dict(self.entities),
            "last_intent": self.last_intent,
            "last_route": self.last_route,
            "user_turns": self.user_turns,
            "ai_turns": self.ai_turns,
            "max_user_turns": MAX_USER_TURNS,
            "max_ai_turns": MAX_AI_TURNS,
            "dialogue": format_dialogue(self.turns),
        }

    def _sync_from_window(self) -> None:
        self.turns = keep_recent_window(self.turns, WINDOW_TURNS)
        self._round_meta = self._round_meta[-WINDOW_TURNS:]
        if self._round_meta:
            latest = self._round_meta[-1]
            self.entities = dict(latest.get("entities") or {})
            self.last_intent = latest.get("intent") or self.last_intent
            self.last_route = latest.get("route") or self.last_route
        else:
            self.entities = {}
            self.last_intent = None
            self.last_route = None

    def _make_room(self) -> None:
        """即将写入新一轮时，若窗口已满则先丢掉最早一轮。"""
        if self.user_turns >= WINDOW_TURNS:
            self.turns = keep_recent_window(self.turns, WINDOW_TURNS - 1)
            self._round_meta = self._round_meta[-(WINDOW_TURNS - 1) :]
            self._sync_from_window()

    def _commit(self, query: str, result: dict[str, Any]) -> None:
        reply = str(result.get("final_reply") or "").strip()
        self.turns.append({"role": "user", "content": query})
        self.turns.append({"role": "assistant", "content": reply})
        intent = result.get("intent") or ""
        if intent not in {"policy_violation", "out_of_scope"} and not result.get("policy_blocked"):
            merged = merge_entities(self.entities, result.get("entities") or {})
        else:
            merged = dict(self.entities)
        self._round_meta.append(
            {
                "user": query,
                "assistant": reply,
                "intent": intent,
                "route": result.get("route"),
                "entities": merged,
            }
        )
        self._sync_from_window()

    def ask(
        self,
        query: str,
        *,
        use_deepeval_callback: bool = False,
        case_id: str | None = None,
    ) -> dict[str, Any]:
        from graph.graph import build_graph, invoke_agent

        text = (query or "").strip()
        if self._graph is None:
            self._graph = build_graph()
        self._make_room()
        result = invoke_agent(
            text,
            graph=self._graph,
            case_id=case_id,
            use_deepeval_callback=use_deepeval_callback,
            memory=self.snapshot(),
            history=history_messages(self.turns),
            turn_index=min(self.user_turns + 1, WINDOW_TURNS),
        )
        self._commit(text, result)
        result["turn_index"] = self.user_turns
        result["memory"] = self.snapshot()
        return result
