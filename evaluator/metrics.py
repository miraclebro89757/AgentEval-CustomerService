"""节点级 / 轨迹级指标：DeepEval GEval + TaskCompletionMetric，以及零配置确定性回退。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from evaluator.judge import resolve_judge
from prompts import load_judge


@dataclass
class Score:
    name: str
    score: float
    reason: str
    success: bool
    threshold: float = 0.7
    source: str = "deterministic"
    extra: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "score": round(float(self.score), 4),
            "reason": self.reason,
            "success": bool(self.success),
            "threshold": self.threshold,
            "source": self.source,
            **self.extra,
        }


def _ok(score: float, threshold: float) -> bool:
    return float(score) >= threshold


def _params():
    try:
        from deepeval.test_case import SingleTurnParams as P
    except ImportError:
        from deepeval.test_case import LLMTestCaseParams as P
    return P


def _llm_test_case(**kwargs):
    from deepeval.test_case import LLMTestCase

    return LLMTestCase(**kwargs)


def _judge(metric_id: str):
    return load_judge(metric_id)


def _geval_from_spec(spec, test_case, model: Any) -> Optional[Score]:
    P = _params()
    params = [getattr(P, name) for name in spec.evaluation_params]
    return _geval_score(
        name=spec.name,
        criteria=spec.criteria,
        evaluation_steps=list(spec.evaluation_steps),
        evaluation_params=params,
        test_case=test_case,
        model=model,
        threshold=spec.threshold,
    )


def _geval_score(
    *,
    name: str,
    criteria: str,
    evaluation_steps: list[str],
    evaluation_params: list,
    test_case,
    model: Any,
    threshold: float,
) -> Optional[Score]:
    try:
        from deepeval.metrics import GEval

        metric = GEval(
            name=name,
            criteria=criteria,
            evaluation_steps=evaluation_steps,
            evaluation_params=evaluation_params,
            threshold=threshold,
            model=model,
            async_mode=False,
        )
        metric.measure(test_case)
        return Score(
            name=name,
            score=float(metric.score if metric.score is not None else 0.0),
            reason=metric.reason or "",
            success=bool(metric.is_successful()),
            threshold=threshold,
            source="deepeval.GEval",
        )
    except Exception as exc:
        return Score(
            name=name,
            score=0.0,
            reason=f"GEval 调用失败，将回退确定性指标：{exc}",
            success=False,
            threshold=threshold,
            source="deepeval.GEval.error",
        )


def _point_hit(point: str, text: str) -> bool:
    aliases = {
        "问候": ["您好", "你好", "问候"],
        "可以帮忙": ["可以帮", "需要什么帮助", "请问需要"],
        "抱歉": ["抱歉", "对不起", "添麻烦"],
        "工单": ["工单", "ticket", "TK-"],
        "质量": ["质量", "售后", "退换"],
        "无法": ["无法", "超出", "职责范围"],
        "7天": ["7天", "七天", "7 天"],
        "1-3个工作日": ["1-3个工作日", "1-3 个工作日", "1至3个工作日"],
        "原路返回": ["原路返回", "原路退"],
        "24小时": ["24小时", "24 小时"],
        "3-5天": ["3-5天", "3-5 天", "3至5天"],
        "28小时": ["28小时", "28 小时"],
        "3.5mm": ["3.5mm", "音频线"],
        "不支持独立通话": ["不支持独立通话", "独立通话"],
        "Android 10": ["Android 10", "安卓"],
        "忘记密码": ["忘记密码", "重置"],
        "人工核验": ["人工核验", "人工"],
        "订单号": ["订单号", "订单"],
        "已发货": ["已发货"],
        "顺丰": ["顺丰"],
        "SF": ["SF", "SF109"],
        "已签收": ["已签收"],
        "899": ["899"],
        "购物": ["购物"],
        "售后": ["售后"],
        "超出": ["超出"],
        "边界": ["服务边界", "边界", "违规"],
        "无法协助": ["无法协助", "不能回答", "无法处理"],
        "违规": ["违规", "色情", "赌博", "毒品"],
        "有货": ["有货", "in_stock"],
        "成都仓": ["成都仓"],
        "128": ["128"],
        "1280": ["1280"],
        "银卡": ["银卡"],
        "在保": ["在保"],
        "2028": ["2028-09-03", "2028"],
        "职责边界": ["职责边界", "职责范围"],
        "法律": ["法律", "起诉", "诉讼"],
    }
    blob = text or ""
    for token in aliases.get(point, [point]):
        if token in blob:
            return True
    return point in blob


def score_intent(predicted: str, expected: str, query: str, model: Any) -> Score:
    spec = _judge("IntentAccuracy")
    threshold = spec.threshold
    fallback_score = 1.0 if predicted == expected else 0.0
    fallback_reason = (
        f"预测意图 `{predicted}` 与标注 `{expected}` 一致。"
        if fallback_score == 1.0
        else f"预测意图 `{predicted}` 与标注 `{expected}` 不一致。"
    )
    if model is None:
        return Score(spec.name, fallback_score, fallback_reason, _ok(fallback_score, threshold), threshold)
    case = _llm_test_case(input=query, actual_output=predicted, expected_output=expected)
    judged = _geval_from_spec(spec, case, model)
    if judged and judged.source != "deepeval.GEval.error":
        return judged
    return Score(spec.name, fallback_score, fallback_reason, _ok(fallback_score, threshold), threshold)


def score_routing(predicted: str, expected: str, intent: str, query: str, model: Any) -> Score:
    spec = _judge("RoutingCorrectness")
    threshold = spec.threshold
    fallback_score = 1.0 if predicted == expected else 0.0
    fallback_reason = (
        f"Supervisor 路由 `{predicted}` 与标注 `{expected}` 一致（意图={intent}）。"
        if fallback_score == 1.0
        else f"Supervisor 路由 `{predicted}` 错误，标注应为 `{expected}`（意图={intent}）。"
    )
    if model is None:
        return Score(spec.name, fallback_score, fallback_reason, _ok(fallback_score, threshold), threshold)
    case = _llm_test_case(
        input=f"query={query}\nintent={intent}",
        actual_output=predicted,
        expected_output=expected,
    )
    judged = _geval_from_spec(spec, case, model)
    if judged and judged.source != "deepeval.GEval.error":
        return judged
    return Score(spec.name, fallback_score, fallback_reason, _ok(fallback_score, threshold), threshold)


def score_rag(
    query: str,
    retrieved_ids: list[str],
    retrieved_docs: list[dict[str, Any]],
    gold_ids: list[str],
    model: Any,
) -> Score:
    spec = _judge("RAGQuality")
    threshold = spec.threshold
    gold = list(gold_ids or [])
    got = list(retrieved_ids or [])
    if not gold:
        if not got:
            return Score(
                spec.name,
                1.0,
                "该用例不需要检索，且节点未检索，视为正确跳过。",
                True,
                threshold,
                extra={"skipped": True},
            )
        return Score(spec.name, 0.4, f"不需要检索却返回了 {got}，存在噪声。", False, threshold)

    hit = set(got) & set(gold)
    recall = len(hit) / len(gold)
    precision = len(hit) / len(got) if got else 0.0
    f1 = 0.0 if recall + precision == 0 else 2 * recall * precision / (recall + precision)
    recall_w = float(spec.scoring.get("recall_weight") or 0.7)
    precision_w = float(spec.scoring.get("precision_weight") or 0.3)
    blended = recall_w * recall + precision_w * precision
    missing = [i for i in gold if i not in got]
    extra = [i for i in got if i not in gold]
    fallback_reason = (
        f"检索命中 {sorted(hit)}。召回={recall:.2f} 精确={precision:.2f} "
        f"F1={f1:.2f} 综合={blended:.2f}。"
        f"{' 缺失: ' + ','.join(missing) if missing else ''}"
        f"{' 多余: ' + ','.join(extra) if extra else ''}"
    )
    fallback = Score(spec.name, blended, fallback_reason, _ok(blended, threshold), threshold)

    if model is None:
        return fallback
    context = [f"{d.get('id')}: {d.get('title')} {d.get('content')}" for d in retrieved_docs]
    case = _llm_test_case(
        input=query,
        actual_output="\n".join(got) or "(empty)",
        expected_output=",".join(gold),
        retrieval_context=context or ["(empty)"],
    )
    judged = _geval_from_spec(spec, case, model)
    if judged and judged.source != "deepeval.GEval.error":
        judged.reason = f"{judged.reason} | 确定性对照：{fallback_reason}"
        judged.extra = {"f1": f1, "recall": recall, "precision": precision, "blended": blended}
        return judged
    return fallback


def score_reply_dimensions(
    query: str,
    reply: str,
    expected_output: str,
    points: list[str],
    retrieval_context: list[str],
    model: Any,
) -> list[Score]:
    hits = [p for p in points if _point_hit(p, reply)]
    coverage = 1.0 if not points else len(hits) / len(points)
    polite_tokens = ("请", "您", "您好", "感谢", "抱歉", "帮您", "可以")
    politeness = min(1.0, sum(1 for t in polite_tokens if t in (reply or "")) / 3)
    relevance = 1.0 if coverage >= 0.5 else coverage
    fallback_by_name = {
        "ReplyRelevancy": lambda spec: Score(
            spec.name,
            relevance,
            f"回复是否覆盖用户问题：要点命中 {hits} / {points}。",
            _ok(relevance, spec.threshold),
            spec.threshold,
        ),
        "ReplyCompleteness": lambda spec: Score(
            spec.name,
            coverage,
            f"完整性：命中 {len(hits)}/{len(points)} 个要点 {hits}，缺失 {[p for p in points if p not in hits]}。",
            _ok(coverage, spec.threshold),
            spec.threshold,
        ),
        "ReplyPoliteness": lambda spec: Score(
            spec.name,
            politeness,
            f"礼貌度：命中客服礼貌用语 {[t for t in polite_tokens if t in (reply or '')]}。",
            _ok(politeness, spec.threshold),
            spec.threshold,
        ),
    }
    names = ("ReplyRelevancy", "ReplyCompleteness", "ReplyPoliteness")
    fallbacks = [fallback_by_name[name](_judge(name)) for name in names]
    if model is None:
        return fallbacks

    results: list[Score] = []
    for name in names:
        spec = _judge(name)
        case = _llm_test_case(
            input=query,
            actual_output=reply or "",
            expected_output=expected_output or "",
            retrieval_context=retrieval_context or None,
        )
        judged = _geval_from_spec(spec, case, model)
        if judged and judged.source != "deepeval.GEval.error":
            results.append(judged)
        else:
            results.append(next(s for s in fallbacks if s.name == spec.name))
    return results


def score_tools(query: str, called: list[dict[str, Any]], expected_names: list[str], reply: str) -> Score:
    spec = _judge("ToolCorrectness")
    threshold = spec.threshold
    expected_names = list(expected_names or [])
    called_names = [c.get("name") for c in called or [] if c.get("name")]
    if not expected_names and not called_names:
        return Score(spec.name, 1.0, "无需工具，也未调用工具。", True, threshold, source="deterministic")
    if not expected_names and called_names:
        return Score(
            spec.name,
            0.5,
            f"标注不需要工具，但调用了 {called_names}。",
            False,
            threshold,
        )
    hit = [n for n in expected_names if n in called_names]
    extra = [n for n in called_names if n not in expected_names]
    missing = [n for n in expected_names if n not in called_names]
    score = len(hit) / len(expected_names)
    if extra:
        score *= 0.8
    reason = f"期望 {expected_names}，实际 {called_names}。命中 {hit}，缺失 {missing}，多余 {extra}。"

    try:
        from deepeval.metrics import ToolCorrectnessMetric
        from deepeval.test_case import ToolCall

        case = _llm_test_case(
            input=query,
            actual_output=reply or "",
            tools_called=[
                ToolCall(name=c.get("name") or "", input_parameters=c.get("args") or {})
                for c in called or []
            ],
            expected_tools=[ToolCall(name=n) for n in expected_names],
        )
        metric = ToolCorrectnessMetric(threshold=threshold)
        metric.measure(case)
        return Score(
            spec.name,
            float(metric.score if metric.score is not None else score),
            (metric.reason or reason),
            bool(metric.is_successful()),
            threshold,
            source="deepeval.ToolCorrectnessMetric",
        )
    except Exception:
        return Score(spec.name, score, reason, _ok(score, threshold), threshold)


def score_path_efficiency(actual_path: list[str], expected_path: list[str]) -> Score:
    spec = _judge("StepEfficiency")
    threshold = spec.threshold
    actual = list(actual_path or [])
    expected = list(expected_path or [])
    if actual == expected:
        return Score(spec.name, 1.0, f"轨迹完全一致：{actual}", True, threshold)
    it = iter(actual)
    subsequence = all(node in it for node in expected)
    extra = [n for n in actual if n not in expected]
    missing = [n for n in expected if n not in actual]
    score = 0.85 if subsequence and not missing else 0.4
    if extra and extra != ["tools"]:
        score -= 0.1 * min(3, len(extra))
    if missing:
        score -= 0.2 * min(3, len(missing))
    score = max(0.0, min(1.0, score))
    reason = (
        f"实际路径 {actual}，期望 {expected}。"
        f"{'期望路径是实际路径的子序列。' if subsequence else '路径顺序偏离。'}"
        f"{' 缺失节点: ' + str(missing) if missing else ''}"
        f"{' 额外节点: ' + str(extra) if extra else ''}"
    )
    return Score(spec.name, score, reason, _ok(score, threshold), threshold)


def score_task_completion(
    *,
    query: str,
    task: str,
    reply: str,
    path: list[str],
    tools_called: list[dict[str, Any]],
    points: list[str],
    intent_ok: bool,
    route_ok: bool,
    model: Any,
) -> Score:
    spec = _judge("TaskCompletion")
    threshold = spec.threshold
    hits = [p for p in points if _point_hit(p, reply)]
    coverage = 1.0 if not points else len(hits) / len(points)
    intent_w = float(spec.scoring.get("intent_weight") or 0.25)
    route_w = float(spec.scoring.get("route_weight") or 0.25)
    cov_w = float(spec.scoring.get("coverage_weight") or 0.5)
    fallback_score = intent_w * (1.0 if intent_ok else 0.0) + route_w * (1.0 if route_ok else 0.0) + cov_w * coverage
    fallback_reason = (
        f"任务：{task or query}。意图{'正确' if intent_ok else '错误'}，"
        f"路由{'正确' if route_ok else '错误'}，要点覆盖 {coverage:.0%}。路径={path}，工具={ [t.get('name') for t in tools_called] }。"
    )
    fallback = Score(
        spec.name,
        fallback_score,
        fallback_reason,
        _ok(fallback_score, threshold),
        threshold,
        source="deterministic",
    )
    if model is None:
        return fallback
    trajectory = (
        f"task={task}\npath={path}\ntools={tools_called}\nfinal_reply={reply}"
    )
    case = _llm_test_case(input=query, actual_output=trajectory, expected_output=task or "")
    judged = _geval_from_spec(spec, case, model)
    if judged and judged.source != "deepeval.GEval.error":
        judged.reason = f"{judged.reason} | 确定性对照：{fallback_reason}"
        return judged
    return fallback


def try_official_task_completion_metric(model: Any) -> Optional[Any]:
    """构造官方 TaskCompletionMetric，供 CallbackHandler / evals_iterator 使用。"""
    spec = _judge("TaskCompletion")
    try:
        from deepeval.metrics import TaskCompletionMetric

        kwargs: dict[str, Any] = {"threshold": spec.threshold, "include_reason": True, "async_mode": False}
        if model is not None:
            kwargs["model"] = model
        return TaskCompletionMetric(**kwargs)
    except Exception:
        return None


def current_judge():
    return resolve_judge()
