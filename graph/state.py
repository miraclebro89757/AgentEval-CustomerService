from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any, Literal, TypedDict

from langgraph.graph.message import add_messages

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
RESULTS_DIR = ROOT_DIR / "results"
KB_PATH = DATA_DIR / "knowledge_base.json"
CASES_PATH = DATA_DIR / "test_cases.json"

Intent = Literal[
    "greeting",
    "product_inquiry",
    "order_status",
    "refund",
    "shipping",
    "account",
    "complaint",
    "chitchat",
    "out_of_scope",
]

Route = Literal["rag_agent", "tool_agent", "direct_reply"]

VALID_INTENTS: tuple[str, ...] = (
    "greeting",
    "product_inquiry",
    "order_status",
    "refund",
    "shipping",
    "account",
    "complaint",
    "chitchat",
    "out_of_scope",
)

VALID_ROUTES: tuple[str, ...] = ("rag_agent", "tool_agent", "direct_reply")

# Supervisor 路由表：意图 → 子 Agent。评测时与 expected_route 对齐。
INTENT_TO_ROUTE: dict[str, Route] = {
    "greeting": "direct_reply",
    "chitchat": "direct_reply",
    "out_of_scope": "direct_reply",
    "order_status": "tool_agent",
    "complaint": "tool_agent",
    "product_inquiry": "rag_agent",
    "shipping": "rag_agent",
    "account": "rag_agent",
    "refund": "rag_agent",
}


class NodeTrace(TypedDict, total=False):
    node: str
    input: dict[str, Any]
    output: dict[str, Any]
    latency_ms: float


class AgentState(TypedDict, total=False):
    """LangGraph 共享状态。每个关键节点写入自己的字段，评测器从这里抽 Trace。"""

    messages: Annotated[list, add_messages]
    user_query: str

    # Sub-Agent 1: 意图识别 + 预处理
    cleaned_query: str
    intent: str
    intent_confidence: float
    entities: dict[str, Any]

    # Supervisor: 只路由
    supervisor_intent: str
    route: str
    route_reason: str

    # Sub-Agent 2: RAG
    retrieval_query: str
    retrieved_docs: list[dict[str, Any]]
    retrieved_doc_ids: list[str]

    # Sub-Agent 3: 回复 + 工具
    tool_round: int
    tools_called: list[dict[str, Any]]
    final_reply: str

    # 评测用轨迹
    path: list[str]
    node_traces: list[NodeTrace]
