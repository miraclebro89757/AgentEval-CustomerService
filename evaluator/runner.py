"""跑完整数据集：先跑 LangGraph 拿节点 Trace，再做 Component + Trajectory 打分。"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from typing import Any, Optional

from evaluator.metrics import (
    Score,
    current_judge,
    score_intent,
    score_path_efficiency,
    score_rag,
    score_reply_dimensions,
    score_routing,
    score_task_completion,
    score_tools,
    try_official_task_completion_metric,
)
from evaluator.reporter import write_report
from graph.graph import build_graph, invoke_agent
from graph.llm import load_llm_settings
from graph.state import CASES_PATH, RESULTS_DIR


def load_test_cases() -> list[dict[str, Any]]:
    return json.loads(CASES_PATH.read_text(encoding="utf-8"))


def _overall(component: list[Score], trajectory: list[Score]) -> float:
    items = [s.score for s in component + trajectory if not s.extra.get("skipped")]
    return sum(items) / len(items) if items else 0.0


def evaluate_graph_result(case: dict[str, Any], result: dict[str, Any], model: Any) -> dict[str, Any]:
    query = case["query"]
    predicted_intent = result.get("intent") or ""
    predicted_route = result.get("route") or ""
    reply = result.get("final_reply") or ""
    docs = result.get("retrieved_docs") or []
    doc_ids = result.get("retrieved_doc_ids") or []
    tools = result.get("tools_called") or []
    path = result.get("path") or []
    context = [f"{d.get('id')}: {d.get('content')}" for d in docs]

    intent_s = score_intent(predicted_intent, case["expected_intent"], query, model)
    route_s = score_routing(predicted_route, case["expected_route"], predicted_intent, query, model)
    rag_s = score_rag(query, doc_ids, docs, case.get("relevant_doc_ids") or [], model)
    reply_scores = score_reply_dimensions(
        query,
        reply,
        case.get("expected_output") or "",
        case.get("expected_reply_points") or [],
        context,
        model,
    )
    tool_s = score_tools(query, tools, case.get("expected_tools") or [], reply)
    component = [intent_s, route_s, rag_s, *reply_scores, tool_s]

    traj_task = score_task_completion(
        query=query,
        task=case.get("task") or "",
        reply=reply,
        path=path,
        tools_called=tools,
        points=case.get("expected_reply_points") or [],
        intent_ok=intent_s.success,
        route_ok=route_s.success,
        model=model,
    )
    traj_eff = score_path_efficiency(path, case.get("expected_path") or [])
    trajectory = [traj_task, traj_eff]

    overall = _overall(component, trajectory)
    passed = all(s.success or s.extra.get("skipped") for s in component + trajectory)
    return {
        "id": case["id"],
        "query": query,
        "task": case.get("task"),
        "expected_intent": case["expected_intent"],
        "predicted_intent": predicted_intent,
        "expected_route": case["expected_route"],
        "predicted_route": predicted_route,
        "expected_path": case.get("expected_path") or [],
        "path": path,
        "final_reply": reply,
        "component": [s.as_dict() for s in component],
        "trajectory": [s.as_dict() for s in trajectory],
        "overall": round(overall, 4),
        "passed": passed,
        "traces_json": json.dumps(result.get("node_traces") or [], ensure_ascii=False, indent=2),
        "tools_called": tools,
        "retrieved_doc_ids": doc_ids,
    }


def _summarize(cases: list[dict[str, Any]]) -> dict[str, Any]:
    buckets: dict[str, list[float]] = defaultdict(list)
    flags: dict[str, list[bool]] = defaultdict(list)
    for case in cases:
        for s in case["component"] + case["trajectory"]:
            if s.get("skipped"):
                continue
            buckets[s["name"]].append(float(s["score"]))
            flags[s["name"]].append(bool(s["success"]))
    metrics = {}
    for name, scores in buckets.items():
        metrics[name] = {
            "avg": sum(scores) / len(scores),
            "pass_rate": sum(1 for x in flags[name] if x) / len(flags[name]),
        }
    comp = [c["overall"] for c in cases]
    avg_component = 0.0
    avg_trajectory = 0.0
    n = 0
    for case in cases:
        cs = [s["score"] for s in case["component"] if not s.get("skipped")]
        ts = [s["score"] for s in case["trajectory"]]
        if cs:
            avg_component += sum(cs) / len(cs)
        if ts:
            avg_trajectory += sum(ts) / len(ts)
        n += 1
    return {
        "total_cases": len(cases),
        "passed_cases": sum(1 for c in cases if c["passed"]),
        "avg_overall": sum(comp) / len(comp) if comp else 0.0,
        "avg_component": avg_component / n if n else 0.0,
        "avg_trajectory": avg_trajectory / n if n else 0.0,
        "metrics": metrics,
    }


def _try_official_trace_eval(cases: list[dict[str, Any]], model: Any) -> Optional[str]:
    """
    官方 DeepEval 路径：EvaluationDataset.evals_iterator + CallbackHandler + TaskCompletionMetric。
    没有裁判模型或未安装完整链路时跳过，不影响主报告。
    """
    if model is None:
        return None
    metric = try_official_task_completion_metric(model)
    if metric is None:
        return None
    try:
        from deepeval.dataset import EvaluationDataset, Golden
        from deepeval.evaluate import AsyncConfig

        goldens = [Golden(input=c["query"], additional_metadata={"id": c["id"]}) for c in cases[:1]]
        dataset = EvaluationDataset(goldens=goldens)
        graph = build_graph()
        for golden in dataset.evals_iterator(
            metrics=[metric],
            async_config=AsyncConfig(run_async=False),
        ):
            invoke_agent(golden.input, graph=graph, case_id="official-trace")
        return "已用 TaskCompletionMetric + evals_iterator 对首条用例跑过官方轨迹评测（详见终端 / Confident AI）。"
    except Exception as exc:
        return f"官方 CallbackHandler 轨迹评测未执行（可忽略）：{exc}"


def _keep_agent_metrics(cases: list[dict[str, Any]], agent_id: str) -> list[dict[str, Any]]:
    """整图照跑，报告只保留该 Agent 的 judge 指标（单 Agent 评测）。"""
    from prompts import judge_ids_for_agent, list_agent_ids

    valid = list_agent_ids()
    if agent_id not in valid:
        raise ValueError(f"未知 Agent `{agent_id}`，可选：{valid}")
    keep = set(judge_ids_for_agent(agent_id))
    filtered: list[dict[str, Any]] = []
    for case in cases:
        item = dict(case)
        item["component"] = [s for s in case["component"] if s["name"] in keep]
        item["trajectory"] = []
        scores = [s["score"] for s in item["component"] if not s.get("skipped")]
        item["overall"] = round(sum(scores) / len(scores), 4) if scores else 0.0
        item["passed"] = all(s["success"] or s.get("skipped") for s in item["component"])
        filtered.append(item)
    return filtered


def evaluate_dataset(
    *,
    limit: Optional[int] = None,
    case_ids: Optional[list[str]] = None,
    write: bool = True,
    agent: Optional[str] = None,
) -> dict[str, Any]:
    judge_label, model = current_judge()
    cases_raw = load_test_cases()
    if case_ids:
        want = set(case_ids)
        cases_raw = [c for c in cases_raw if c["id"] in want]
    if limit is not None:
        cases_raw = cases_raw[: max(0, limit)]

    graph = build_graph()
    evaluated = []
    for case in cases_raw:
        result = invoke_agent(case["query"], graph=graph, case_id=case["id"])
        evaluated.append(evaluate_graph_result(case, result, model))

    scope = "graph"
    if agent:
        evaluated = _keep_agent_metrics(evaluated, agent)
        scope = f"single-agent:{agent}"

    official_note = None if agent else _try_official_trace_eval(cases_raw, model)
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "agent_runtime": load_llm_settings().mode,
        "judge": judge_label,
        "eval_scope": scope,
        "official_trace_note": official_note,
        "summary": _summarize(evaluated),
        "cases": evaluated,
    }
    if write:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        out = RESULTS_DIR / f"report-{stamp}.md"
        write_report(payload, out)
        write_report(payload, RESULTS_DIR / "latest.md")
        payload["report_path"] = str(out)
        payload["latest_path"] = str(RESULTS_DIR / "latest.md")
    return payload


def evaluate_single_query(query: str) -> dict[str, Any]:
    judge_label, model = current_judge()
    result = invoke_agent(query)
    fake_case = {
        "id": "adhoc",
        "query": query,
        "expected_intent": result.get("intent") or "",
        "expected_route": result.get("route") or "",
        "expected_path": result.get("path") or [],
        "expected_tools": [t.get("name") for t in result.get("tools_called") or []],
        "relevant_doc_ids": result.get("retrieved_doc_ids") or [],
        "expected_reply_points": [],
        "expected_output": result.get("final_reply") or "",
        "task": query,
    }
    scored = evaluate_graph_result(fake_case, result, model)
    scored["judge"] = judge_label
    scored["agent_runtime"] = load_llm_settings().mode
    scored["raw_state_keys"] = sorted(result.keys())
    return scored
