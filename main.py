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
    parser.add_argument(
        "--chat",
        action="store_true",
        help="多轮对话（滑动窗口保留最近 5 轮）",
    )
    parser.add_argument("--limit", type=int, default=None, help="只评测前 N 条用例")
    parser.add_argument("--case-id", action="append", dest="case_ids", help="指定用例 id，可重复")
    parser.add_argument("--split", choices=["dev", "regression", "challenge"], help="只跑该数据集划分")
    parser.add_argument(
        "--slice",
        dest="slice_name",
        choices=["happy_path", "safety", "duty", "memory"],
        help="只跑该切片",
    )
    parser.add_argument(
        "--pass-k",
        type=int,
        default=None,
        help="reliability 用例连跑 k 次（LLM 默认 3；启发式默认 1）",
    )
    parser.add_argument(
        "--pass-k-all",
        action="store_true",
        help="对本次选中的全部用例重复试验（很慢）",
    )
    parser.add_argument(
        "--heuristic",
        action="store_true",
        help="强制 AGENT_LLM=heuristic、JUDGE_LLM=heuristic，不打本地模型",
    )
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


def _apply_heuristic_override() -> None:
    os.environ["AGENT_LLM"] = "heuristic"
    os.environ["JUDGE_LLM"] = "heuristic"


def _run_chat() -> None:
    from graph.memory import MAX_USER_TURNS, Conversation

    convo = Conversation()
    print(f"星云数码客服 · 多轮模式（滑动窗口 {MAX_USER_TURNS} 轮：超出则丢掉最早一轮）")
    print("命令：/reset 清空记忆，/quit 退出")
    while True:
        prompt = f"你[{convo.user_turns}/{MAX_USER_TURNS} 窗]> "
        try:
            line = input(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not line:
            continue
        if line in {"/quit", "/exit", "退出"}:
            return
        if line == "/reset":
            convo.reset()
            print("已新开对话。")
            continue
        state = convo.ask(line, use_deepeval_callback=False)
        print("助手:", state.get("final_reply"))


def main() -> None:
    args = parse_args()
    if args.heuristic:
        _apply_heuristic_override()
    if args.list_prompts:
        from prompts import render_catalog

        print(render_catalog(), end="")
        return

    from graph.llm import require_agent_runtime

    settings = require_agent_runtime()
    if args.chat:
        _run_chat()
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
        if state.get("policy_blocked"):
            print("safety:", state.get("policy_hit"))
        if state.get("duty_hit"):
            print("duty  :", state.get("duty_hit"))
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
                "must_cover": [],
                "must_abstain": [],
                "forbidden_actions": [],
                "hard_fail": [],
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

    if settings.mode == "ollama" and not args.limit and not args.case_ids:
        print(
            f"使用本地 {settings.ollama_model} 跑全量用例；"
            "reliability 切片会连跑 3 次。可先 `--limit 3` 或 `--slice safety`。"
        )
    payload = evaluate_dataset(
        limit=args.limit,
        case_ids=args.case_ids,
        write=not args.no_report,
        agent=args.agent,
        split=args.split,
        slice_name=args.slice_name,
        pass_k=args.pass_k,
        pass_k_all=args.pass_k_all,
    )
    summary = payload["summary"]
    print("AgentEval-CustomerService")
    print(
        f"runtime={payload['agent_runtime']}"
        + (f":{settings.ollama_model}" if settings.mode == "ollama" else "")
        + f"  judge={payload['judge']}  scope={payload.get('eval_scope')}"
    )
    print(payload.get("charter") or "")
    print(
        f"cases={summary['passed_cases']}/{summary['total_cases']} passed  "
        f"hard_fail={summary.get('gate_failed_cases', 0)}  "
        f"component={summary['avg_component']:.3f}  trajectory={summary['avg_trajectory']:.3f}"
    )
    slices = summary.get("slices") or {}
    if slices:
        print(
            "slices: "
            + "  ".join(
                f"{name}={vals['passed']}/{vals['n']}" for name, vals in slices.items()
            )
        )
    pk = summary.get("pass_k") or {}
    if pk.get("reliability_cases"):
        print(
            f"pass^{pk.get('k')}: {pk.get('pass_hat_k')}/{pk.get('reliability_cases')} "
            f"reliability cases all-pass"
        )
    print()
    for case in payload["cases"]:
        flag = "PASS" if case["passed"] else "FAIL"
        gate = "" if case.get("gate_passed", True) else " GATE"
        tax = f"  {case['failure_taxonomy']}" if case.get("failure_taxonomy") else ""
        print(f"[{flag}{gate}] {case['id']}  {case['overall']:.2f}  {case['query']}{tax}")
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
