#!/usr/bin/env python3
"""AgentEval-CustomerService 可直接运行的 Demo 入口。"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

# 本地 Demo 默认不上报 Confident AI；有 Key 时再开。
if not os.getenv("CONFIDENT_API_KEY"):
    os.environ.setdefault("CONFIDENT_TRACING_ENABLED", "NO")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="LangGraph 智能客服 + DeepEval 节点级评测 Demo",
    )
    parser.add_argument("--query", type=str, help="只跑一条用户话术，打印 Trace 和回复")
    parser.add_argument("--limit", type=int, default=None, help="只评测前 N 条用例")
    parser.add_argument("--case-id", action="append", dest="case_ids", help="指定用例 id，可重复")
    parser.add_argument(
        "--no-report",
        action="store_true",
        help="不写 Markdown 报告（仍打印摘要）",
    )
    parser.add_argument(
        "--agent",
        type=str,
        choices=["intent_preprocess", "supervisor", "rag_retrieve", "reply_generate"],
        help="只评该 Agent 对应的指标（整图仍会跑，便于拿到真实节点输出）",
    )
    parser.add_argument(
        "--list-prompts",
        action="store_true",
        help="列出业务 prompt 与 judge prompt",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.list_prompts:
        from prompts import render_catalog

        print(render_catalog(), end="")
        return
    if args.query:
        from evaluator.metrics import current_judge
        from evaluator.runner import evaluate_graph_result
        from graph.graph import invoke_agent

        state = invoke_agent(args.query)
        print("=== Trace ===")
        print("path :", " → ".join(state.get("path") or []))
        print("intent:", state.get("intent"), f"({state.get('intent_confidence')})")
        print("route :", state.get("route"), "|", state.get("route_reason"))
        print("docs  :", state.get("retrieved_doc_ids"))
        print("tools :", [t.get("name") for t in state.get("tools_called") or []])
        print("reply :", state.get("final_reply"))
        print()
        _, model = current_judge()
        scored = evaluate_graph_result(
            {
                "id": "adhoc",
                "query": args.query,
                "expected_intent": state.get("intent") or "",
                "expected_route": state.get("route") or "",
                "expected_path": state.get("path") or [],
                "expected_tools": [t.get("name") for t in state.get("tools_called") or []],
                "relevant_doc_ids": state.get("retrieved_doc_ids") or [],
                "expected_reply_points": [],
                "expected_output": state.get("final_reply") or "",
                "task": args.query,
            },
            state,
            model,
        )
        print("=== 节点分（临时查询无标注，分数仅供参考）===")
        for item in scored["component"] + scored["trajectory"]:
            print(f"- {item['name']}: {item['score']:.2f} [{item['source']}] {item['reason']}")
        return

    from evaluator.runner import evaluate_dataset

    payload = evaluate_dataset(
        limit=args.limit,
        case_ids=args.case_ids,
        write=not args.no_report,
        agent=args.agent,
    )
    summary = payload["summary"]
    print("AgentEval-CustomerService")
    print(f"runtime={payload['agent_runtime']}  judge={payload['judge']}  scope={payload.get('eval_scope')}")
    print(
        f"cases={summary['passed_cases']}/{summary['total_cases']} passed  "
        f"component={summary['avg_component']:.3f}  trajectory={summary['avg_trajectory']:.3f}"
    )
    print()
    for case in payload["cases"]:
        flag = "PASS" if case["passed"] else "FAIL"
        print(f"[{flag}] {case['id']}  {case['overall']:.2f}  {case['query']}")
        print(f"       path={ ' → '.join(case['path']) }")
    if payload.get("official_trace_note"):
        print()
        print(payload["official_trace_note"])
    if payload.get("report_path"):
        print()
        print("Markdown 报告:", payload["report_path"])
        print("最新副本    :", payload["latest_path"])
    print()
    print(json.dumps({k: round(v["avg"], 3) for k, v in summary["metrics"].items()}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
