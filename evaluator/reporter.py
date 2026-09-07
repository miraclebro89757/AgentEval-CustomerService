"""把评测结果写成 Markdown 报告，方便对照每个节点的分数和理由。"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any


def _bar(score: float) -> str:
    filled = round(max(0.0, min(1.0, score)) * 10)
    return "█" * filled + "░" * (10 - filled)


def _flag(success: bool) -> str:
    return "PASS" if success else "FAIL"


def _md_table(headers: list[str], rows: list[list[str]]) -> str:
    line = "| " + " | ".join(headers) + " |"
    sep = "| " + " | ".join("---" for _ in headers) + " |"
    body = "\n".join("| " + " | ".join(r) + " |" for r in rows)
    return "\n".join([line, sep, body])


def _pct(passed: int, n: int) -> str:
    if n <= 0:
        return "—"
    return f"{passed}/{n} ({passed / n:.0%})"


def render_report(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    cases = payload["cases"]
    generated = payload.get("generated_at") or datetime.now().isoformat(timespec="seconds")
    pass_k = summary.get("pass_k") or {}
    taxonomy = summary.get("failure_taxonomy") or {}

    lines: list[str] = [
        "# AgentEval-CustomerService 评测报告",
        "",
        f"- 生成时间：{generated}",
        f"- 评测章程：{payload.get('charter') or '（未写）'}",
        f"- Agent 运行时：`{payload.get('agent_runtime')}`",
        f"- DeepEval 裁判：`{payload.get('judge')}`",
        f"- 评测范围：`{payload.get('eval_scope') or 'graph'}`",
        f"- 用例数：{summary['total_cases']}",
        f"- 用例通过：{summary['passed_cases']}/{summary['total_cases']}",
        f"- 硬失败（一票否决）：{summary.get('gate_failed_cases', 0)}",
        f"- 平均节点分：{summary['avg_component']:.3f}",
        f"- 平均轨迹分：{summary['avg_trajectory']:.3f}",
        "",
        "## 1. 硬失败门禁",
        "",
        "安全漏拦、越权调工具、编造单号是 gate，不与礼貌分平均。质量分可以很高，gate 失败则整条 FAIL。",
        "",
        _md_table(
            ["用例", "切片", "split", "gate", "硬失败"],
            [
                [
                    c["id"],
                    c.get("slice") or "",
                    c.get("split") or "",
                    _flag(c.get("gate_passed", True)),
                    "; ".join(f"{h['type']}: {h['reason']}" for h in (c.get("hard_fails") or [])) or "—",
                ]
                for c in cases
                if not c.get("gate_passed", True) or c.get("hard_fails")
            ]
            or [["—", "—", "—", "PASS", "本轮无硬失败"]],
        ),
        "",
        "## 2. 切片 / 数据集划分",
        "",
        _md_table(
            ["切片", "通过", "硬失败数", "平均质量分"],
            [
                [
                    name,
                    _pct(vals["passed"], vals["n"]),
                    str(vals["gate_failed"]),
                    f"{vals['avg_overall']:.3f}",
                ]
                for name, vals in (summary.get("slices") or {}).items()
            ],
        ),
        "",
        _md_table(
            ["split", "通过", "硬失败数", "平均质量分"],
            [
                [
                    name,
                    _pct(vals["passed"], vals["n"]),
                    str(vals["gate_failed"]),
                    f"{vals['avg_overall']:.3f}",
                ]
                for name, vals in (summary.get("splits") or {}).items()
            ],
        ),
        "",
        "## 3. 失败分类",
        "",
        "先看分类再看总分：intent / routing / retrieval / tool / policy / memory。",
        "",
        _md_table(
            ["类型", "失败条数"],
            [[label, str(taxonomy.get(label, 0))] for label in ("intent", "routing", "retrieval", "tool", "policy", "memory", "reply")],
        ),
        "",
        "## 4. pass^k（可靠性）",
        "",
        (
            f"reliability 用例连跑 k={pass_k.get('k') or 1} 次。"
            f"pass@k 是至少一次通过的比例口径里的试验成功率；"
            f"**pass^k** 要求 k 次全过。"
            if (pass_k.get("reliability_cases") or 0) > 0
            else "本轮没有重复试验（启发式默认 k=1；接上 LLM 后 reliability 用例会连跑 3 次）。"
        ),
        "",
    ]
    if pass_k.get("reliability_cases"):
        lines.extend(
            [
                _md_table(
                    ["k", "reliability 条数", "pass^k 全过", "平均 pass@k"],
                    [
                        [
                            str(pass_k.get("k")),
                            str(pass_k.get("reliability_cases")),
                            str(pass_k.get("pass_hat_k")),
                            (
                                f"{pass_k['mean_pass_at_k']:.0%}"
                                if pass_k.get("mean_pass_at_k") is not None
                                else "—"
                            ),
                        ]
                    ],
                ),
                "",
            ]
        )

    lines.extend(
        [
            "## 5. 指标总览",
            "",
            "节点级评测针对意图、路由、RAG、回复、工具、约束；轨迹级评测看整条路径是否完成任务、是否绕路。",
            "",
            _md_table(
                ["指标", "平均分", "通过率"],
                [
                    [name, f"{vals['avg']:.3f} {_bar(vals['avg'])}", f"{vals['pass_rate']:.0%}"]
                    for name, vals in summary["metrics"].items()
                ],
            ),
            "",
            "## 6. 用例一览",
            "",
            _md_table(
                ["ID", "split", "切片", "综合", "gate", "pass^k", "失败类型", "结果"],
                [
                    [
                        c["id"],
                        c.get("split") or "",
                        c.get("slice") or "",
                        f"{c['overall']:.2f}",
                        _flag(c.get("gate_passed", True)),
                        (
                            f"{c.get('trial_count', 1)}/{c.get('trial_count', 1)}"
                            if c.get("pass_hat_k", c.get("passed"))
                            else f"0/{c.get('trial_count', 1)}"
                        )
                        if int(c.get("trial_count") or 1) > 1
                        else "—",
                        c.get("failure_taxonomy") or "—",
                        _flag(c["passed"]),
                    ]
                    for c in cases
                ],
            ),
            "",
        ]
    )

    for case in cases:
        gate = _flag(case.get("gate_passed", True))
        lines.extend(
            [
                f"## 7. 用例 `{case['id']}` — {_flag(case['passed'])}（gate {gate}）",
                "",
                f"**split / 切片**：{case.get('split')} / {case.get('slice')}",
                "",
                f"**用户**：{case['query']}",
                "",
                *(
                    [f"**对话**：{' → '.join(case['turns'])}", ""]
                    if case.get("turns")
                    else []
                ),
                f"**任务**：{case.get('task') or '（未标注）'}",
                "",
                f"**must_cover**：{case.get('must_cover') or []}",
                "",
                f"**must_abstain**：{case.get('must_abstain') or []}",
                "",
                f"**forbidden_actions**：{case.get('forbidden_actions') or []}",
                "",
                f"**最终回复**：{case['final_reply']}",
                "",
                f"**实际路径**：`{' → '.join(case['path'])}`",
                "",
                f"**期望路径**：`{' → '.join(case['expected_path'])}`",
                "",
            ]
        )
        if case.get("hard_fails"):
            lines.extend(
                [
                    "**硬失败**：",
                    "",
                    *[f"- `{h['type']}`：{h['reason']}" for h in case["hard_fails"]],
                    "",
                ]
            )
        if int(case.get("trial_count") or 1) > 1:
            lines.extend(
                [
                    f"**pass^k**：k={case['trial_count']}  "
                    f"pass@k={case.get('pass_at_k', 0):.0%}  "
                    f"pass^{case['trial_count']}={'PASS' if case.get('pass_hat_k') else 'FAIL'}",
                    "",
                    _md_table(
                        ["trial", "结果", "gate", "质量分", "工具"],
                        [
                            [
                                str(row["index"]),
                                _flag(row["passed"]),
                                _flag(row.get("gate_passed", True)),
                                f"{row['overall']:.2f}",
                                ",".join(row.get("tools") or []) or "—",
                            ]
                            for row in case.get("trials") or []
                        ],
                    ),
                    "",
                ]
            )
        lines.extend(
            [
                "### 节点级 Component Scores",
                "",
                _md_table(
                    ["节点/指标", "分数", "结果", "来源", "理由"],
                    [
                        [
                            s["name"],
                            f"{s['score']:.2f} {_bar(s['score'])}",
                            _flag(s["success"]),
                            s.get("source", ""),
                            (s.get("reason") or "").replace("\n", " "),
                        ]
                        for s in case["component"]
                    ],
                ),
                "",
                "### 轨迹级 Trajectory Scores",
                "",
                _md_table(
                    ["指标", "分数", "结果", "来源", "理由"],
                    [
                        [
                            s["name"],
                            f"{s['score']:.2f} {_bar(s['score'])}",
                            _flag(s["success"]),
                            s.get("source", ""),
                            (s.get("reason") or "").replace("\n", " "),
                        ]
                        for s in case["trajectory"]
                    ],
                ),
                "",
                "<details><summary>节点 Trace（调试）</summary>",
                "",
                "```json",
                case.get("traces_json") or "[]",
                "```",
                "",
                "</details>",
                "",
            ]
        )

    lines.extend(
        [
            "## 8. 怎么读这份报告",
            "",
            "- **Hard Failure**：`policy_leak` / `unauthorized_tool` / `hallucinated_order` 一票否决，不进入总分平均。",
            "- **ConstraintCheck**：`must_cover` 要点必须出现，`must_abstain` 和 `forbidden_actions` 不能出现。",
            "- **切片**：happy_path / safety / duty / memory 分开报，避免安全事故被问候语拉高。",
            "- **split**：dev 用来改 prompt；regression 是事故回流；challenge 是对抗/越权。",
            "- **pass^k**：同一条 reliability 用例连跑 k 次必须全过。启发式默认 k=1。",
            "- **IntentAccuracy**：子 Agent 1 是否把用户话分到正确意图。黄赌毒必须是 `policy_violation`。",
            "- **RoutingCorrectness**：Supervisor 是否把请求交给正确的子 Agent。安全拦截应为 `blocked`。",
            "- **RAGQuality**：检索文档是否相关。",
            "- **Reply\\***：最终回复的相关性 / 完整性 / 礼貌度（质量分，不能救硬失败）。",
            "- **ToolCorrectness**：该调的工具有没有调到。",
            "- **TaskCompletion / StepEfficiency**：整条轨迹是否完成任务、有没有多余节点。",
            "",
            "分数来源 `deepeval.GEval` 表示 LLM-as-judge；`deterministic` 表示规则门禁/回退。",
            "",
        ]
    )
    return "\n".join(lines) + "\n"


def write_report(payload: dict[str, Any], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_report(payload), encoding="utf-8")
    return path
