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


def render_report(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    cases = payload["cases"]
    generated = payload.get("generated_at") or datetime.now().isoformat(timespec="seconds")

    lines: list[str] = [
        "# AgentEval-CustomerService 评测报告",
        "",
        f"- 生成时间：{generated}",
        f"- Agent 运行时：`{payload.get('agent_runtime')}`",
        f"- DeepEval 裁判：`{payload.get('judge')}`",
        f"- 评测范围：`{payload.get('eval_scope') or 'graph'}`",
        f"- 用例数：{summary['total_cases']}",
        f"- 用例通过：{summary['passed_cases']}/{summary['total_cases']}",
        f"- 平均节点分：{summary['avg_component']:.3f}",
        f"- 平均轨迹分：{summary['avg_trajectory']:.3f}",
        "",
        "## 1. 指标总览",
        "",
        "节点级评测针对意图、路由、RAG、回复、工具；轨迹级评测看整条路径是否完成任务、是否绕路。",
        "",
        _md_table(
            ["指标", "平均分", "通过率"],
            [
                [name, f"{vals['avg']:.3f} {_bar(vals['avg'])}", f"{vals['pass_rate']:.0%}"]
                for name, vals in summary["metrics"].items()
            ],
        ),
        "",
        "## 2. 用例一览",
        "",
        _md_table(
            ["ID", "意图", "路由", "路径", "综合", "结果"],
            [
                [
                    c["id"],
                    f"{c['predicted_intent']} / {c['expected_intent']}",
                    f"{c['predicted_route']} / {c['expected_route']}",
                    " → ".join(c["path"]),
                    f"{c['overall']:.2f}",
                    _flag(c["passed"]),
                ]
                for c in cases
            ],
        ),
        "",
    ]

    for case in cases:
        lines.extend(
            [
                f"## 3. 用例 `{case['id']}` — {_flag(case['passed'])}",
                "",
                f"**用户**：{case['query']}",
                "",
                f"**任务**：{case.get('task') or '（未标注）'}",
                "",
                f"**最终回复**：{case['final_reply']}",
                "",
                f"**实际路径**：`{' → '.join(case['path'])}`",
                "",
                f"**期望路径**：`{' → '.join(case['expected_path'])}`",
                "",
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
            "## 4. 怎么读这份报告",
            "",
            "- **IntentAccuracy**：子 Agent 1 是否把用户话分到正确意图。黄赌毒必须是 `policy_violation`。",
            "- **RoutingCorrectness**：Supervisor 是否把请求交给正确的子 Agent。安全拦截应为 `blocked` 且不再往下走。最终回复对、路由错，仍然算生产事故。",
            "- **RAGQuality**：子 Agent 2 检索到的文档是否相关（对照 `relevant_doc_ids`）。",
            "- **Reply\\***：子 Agent 3 最终回复的相关性 / 完整性 / 礼貌度。",
            "- **ToolCorrectness**：该调的工具有没有调到。",
            "- **TaskCompletion / StepEfficiency**：整条轨迹是否完成任务、有没有多余节点。",
            "",
            "分数来源 `deepeval.GEval` 表示 LLM-as-judge；`deterministic` 表示零配置回退，便于没有 API Key 时仍然能跑通 Demo。",
            "",
        ]
    )
    return "\n".join(lines) + "\n"


def write_report(payload: dict[str, Any], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_report(payload), encoding="utf-8")
    return path
