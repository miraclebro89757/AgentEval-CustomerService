"""跑完整数据集：先跑 LangGraph 拿节点 Trace，再做 Component + Trajectory 打分。"""

from __future__ import annotations

import json
import os
from collections import defaultdict
from datetime import datetime
from typing import Any, Optional

from evaluator.gates import (
    TAXONOMY_LABELS,
    check_hard_failures,
    classify_failure,
    must_cover_of,
    score_constraints,
)
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
from graph.memory import Conversation
from graph.state import CASES_PATH, RESULTS_DIR

EVAL_CHARTER = (
    "这次评测回答：本地 Qwen 客服图在硬失败（安全漏拦、越权调工具、编造单号）上是否可发布，"
    "以及主路径 / 职责边界 / 多轮记忆切片有没有回退。"
)


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
    cover = must_cover_of(case)

    intent_s = score_intent(predicted_intent, case["expected_intent"], query, model)
    route_s = score_routing(predicted_route, case["expected_route"], predicted_intent, query, model)
    rag_s = score_rag(query, doc_ids, docs, case.get("relevant_doc_ids") or [], model)
    reply_scores = score_reply_dimensions(
        query,
        reply,
        case.get("expected_output") or "",
        cover,
        context,
        model,
    )
    tool_s = score_tools(query, tools, case.get("expected_tools") or [], reply)
    constraint_s = score_constraints(reply, case)
    component = [intent_s, route_s, rag_s, *reply_scores, tool_s, constraint_s]

    traj_task = score_task_completion(
        query=query,
        task=case.get("task") or "",
        reply=reply,
        path=path,
        tools_called=tools,
        points=cover,
        intent_ok=intent_s.success,
        route_ok=route_s.success,
        model=model,
    )
    traj_eff = score_path_efficiency(path, case.get("expected_path") or [])
    trajectory = [traj_task, traj_eff]

    quality = _overall(component, trajectory)
    hard_fails = check_hard_failures(case, result)
    quality_passed = all(s.success or s.extra.get("skipped") for s in component + trajectory)
    gate_passed = not hard_fails
    passed = quality_passed and gate_passed
    scored = {
        "id": case["id"],
        "query": query,
        "task": case.get("task"),
        "split": case.get("split") or "dev",
        "slice": case.get("slice") or "happy_path",
        "reliability": bool(case.get("reliability")),
        "must_cover": cover,
        "must_abstain": list(case.get("must_abstain") or []),
        "forbidden_actions": list(case.get("forbidden_actions") or []),
        "expected_intent": case["expected_intent"],
        "predicted_intent": predicted_intent,
        "expected_route": case["expected_route"],
        "predicted_route": predicted_route,
        "expected_path": case.get("expected_path") or [],
        "path": path,
        "final_reply": reply,
        "component": [s.as_dict() for s in component],
        "trajectory": [s.as_dict() for s in trajectory],
        "overall": round(quality, 4),
        "quality_passed": quality_passed,
        "gate_passed": gate_passed,
        "hard_fails": hard_fails,
        "passed": passed,
        "traces_json": json.dumps(result.get("node_traces") or [], ensure_ascii=False, indent=2),
        "tools_called": tools,
        "retrieved_doc_ids": doc_ids,
        "turns": list(case.get("turns") or []),
        "trial_count": 1,
        "pass_at_k": 1.0 if passed else 0.0,
        "pass_hat_k": passed,
        "trials": [],
        "failure_taxonomy": None,
    }
    scored["failure_taxonomy"] = classify_failure(case, scored)
    return scored


def _bucket_stats(cases: list[dict[str, Any]], key: str) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for case in cases:
        grouped[str(case.get(key) or "unspecified")].append(case)
    out: dict[str, Any] = {}
    for name, items in grouped.items():
        n = len(items)
        out[name] = {
            "n": n,
            "passed": sum(1 for item in items if item["passed"]),
            "gate_failed": sum(1 for item in items if not item.get("gate_passed", True)),
            "avg_overall": sum(item["overall"] for item in items) / n if n else 0.0,
        }
    return out


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
    taxonomy = {label: 0 for label in TAXONOMY_LABELS}
    for case in cases:
        label = case.get("failure_taxonomy")
        if label in taxonomy:
            taxonomy[label] += 1
    repeated = [c for c in cases if int(c.get("trial_count") or 1) > 1]
    k = max((int(c.get("trial_count") or 1) for c in repeated), default=1)
    return {
        "total_cases": len(cases),
        "passed_cases": sum(1 for c in cases if c["passed"]),
        "gate_failed_cases": sum(1 for c in cases if not c.get("gate_passed", True)),
        "avg_overall": sum(comp) / len(comp) if comp else 0.0,
        "avg_component": avg_component / n if n else 0.0,
        "avg_trajectory": avg_trajectory / n if n else 0.0,
        "metrics": metrics,
        "slices": _bucket_stats(cases, "slice"),
        "splits": _bucket_stats(cases, "split"),
        "failure_taxonomy": taxonomy,
        "pass_k": {
            "k": k,
            "reliability_cases": len(repeated),
            "pass_hat_k": sum(1 for c in repeated if c.get("pass_hat_k")),
            "mean_pass_at_k": (
                sum(float(c.get("pass_at_k") or 0) for c in repeated) / len(repeated) if repeated else None
            ),
        },
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
        quality_passed = all(s["success"] or s.get("skipped") for s in item["component"])
        item["quality_passed"] = quality_passed
        item["passed"] = bool(quality_passed and item.get("gate_passed", True))
        item["failure_taxonomy"] = classify_failure(case, item)
        filtered.append(item)
    return filtered


def _run_case(case: dict[str, Any], graph, case_id: str | None) -> dict[str, Any]:
    turns = [str(t).strip() for t in (case.get("turns") or []) if str(t).strip()]
    if turns:
        convo = Conversation(graph=graph)
        result: dict[str, Any] = {}
        for index, utterance in enumerate(turns):
            last = index == len(turns) - 1
            result = convo.ask(
                utterance,
                use_deepeval_callback=last,
                case_id=case_id if last else None,
            )
        return result
    return invoke_agent(case["query"], graph=graph, case_id=case_id)


def _default_pass_k() -> int:
    try:
        return max(1, int(os.getenv("EVAL_PASS_K") or 3))
    except ValueError:
        return 3


def trials_for_case(case: dict[str, Any], pass_k: Optional[int], pass_k_all: bool) -> int:
    """启发式 Agent 几乎确定，默认 k=1；LLM 下 reliability 用例连跑 k 次。"""
    if load_llm_settings().mode == "heuristic" and not pass_k_all:
        return 1
    if pass_k_all:
        return max(1, pass_k or _default_pass_k())
    if pass_k is not None and pass_k <= 1:
        return 1
    tagged = int(case.get("pass_k") or 0)
    if case.get("reliability") or tagged > 1:
        return max(tagged, pass_k or _default_pass_k())
    return 1


def _compact_trial(scored: dict[str, Any], index: int) -> dict[str, Any]:
    return {
        "index": index,
        "passed": scored["passed"],
        "gate_passed": scored.get("gate_passed", True),
        "overall": scored["overall"],
        "hard_fails": scored.get("hard_fails") or [],
        "path": scored.get("path") or [],
        "tools": [t.get("name") for t in scored.get("tools_called") or []],
        "failure_taxonomy": scored.get("failure_taxonomy"),
    }


def evaluate_dataset(
    *,
    limit: Optional[int] = None,
    case_ids: Optional[list[str]] = None,
    write: bool = True,
    agent: Optional[str] = None,
    split: Optional[str] = None,
    slice_name: Optional[str] = None,
    pass_k: Optional[int] = None,
    pass_k_all: bool = False,
) -> dict[str, Any]:
    judge_label, model = current_judge()
    cases_raw = load_test_cases()
    if case_ids:
        want = set(case_ids)
        cases_raw = [c for c in cases_raw if c["id"] in want]
    if split:
        cases_raw = [c for c in cases_raw if c.get("split") == split]
    if slice_name:
        cases_raw = [c for c in cases_raw if c.get("slice") == slice_name]
    if limit is not None:
        cases_raw = cases_raw[: max(0, limit)]

    graph = build_graph()
    evaluated = []
    for case in cases_raw:
        k = trials_for_case(case, pass_k, pass_k_all)
        trial_rows: list[dict[str, Any]] = []
        last_scored: dict[str, Any] | None = None
        for index in range(k):
            result = _run_case(case, graph, case["id"] if index == k - 1 else None)
            # 只有最后一轮走 LLM Judge，避免把裁判噪声算进 pass^k。
            scored = evaluate_graph_result(case, result, model if index == k - 1 else None)
            trial_rows.append(_compact_trial(scored, index + 1))
            last_scored = scored
        assert last_scored is not None
        wins = sum(1 for row in trial_rows if row["passed"])
        last_scored["trial_count"] = k
        last_scored["trials"] = trial_rows
        last_scored["pass_at_k"] = wins / k
        last_scored["pass_hat_k"] = wins == k
        if k > 1:
            last_scored["passed"] = bool(last_scored["pass_hat_k"])
            if not last_scored["passed"] and last_scored.get("failure_taxonomy") is None:
                last_scored["failure_taxonomy"] = next(
                    (row["failure_taxonomy"] for row in trial_rows if row["failure_taxonomy"]),
                    None,
                )
        evaluated.append(last_scored)

    scope = "graph"
    if agent:
        evaluated = _keep_agent_metrics(evaluated, agent)
        scope = f"single-agent:{agent}"

    official_note = None if agent else _try_official_trace_eval(cases_raw, model)
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "charter": EVAL_CHARTER,
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
        "must_cover": [],
        "must_abstain": [],
        "forbidden_actions": [],
        "hard_fail": [],
        "expected_output": result.get("final_reply") or "",
        "task": query,
        "split": "dev",
        "slice": "happy_path",
    }
    scored = evaluate_graph_result(fake_case, result, model)
    scored["judge"] = judge_label
    scored["agent_runtime"] = load_llm_settings().mode
    scored["raw_state_keys"] = sorted(result.keys())
    return scored
