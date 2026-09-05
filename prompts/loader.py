"""业务 Prompt / Judge Prompt 加载器。每个 Agent、每个指标各一份 YAML。"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

PROMPTS_ROOT = Path(__file__).resolve().parent


@dataclass(frozen=True)
class AgentPrompt:
    """一个子 Agent / Supervisor 的业务提示词。"""

    id: str
    node: str
    role: str
    system: str
    user_template: str = "{query}"
    policy: dict[str, Any] = field(default_factory=dict)
    path: str = ""

    def render_system(self, **kwargs: Any) -> str:
        return _format(self.system, **kwargs)

    def render_user(self, **kwargs: Any) -> str:
        return _format(self.user_template, **kwargs)


@dataclass(frozen=True)
class JudgePrompt:
    """一个评测指标的裁判提示词。GEval 直接吃 criteria + evaluation_steps。"""

    id: str
    name: str
    target_agent: str
    target_node: str
    kind: str
    criteria: str
    evaluation_steps: tuple[str, ...]
    evaluation_params: tuple[str, ...]
    threshold: float
    scoring: dict[str, Any] = field(default_factory=dict)
    notes: str = ""
    path: str = ""


def _format(template: str, **kwargs: Any) -> str:
    if not template:
        return ""

    class _Safe(dict):
        def __missing__(self, key: str) -> str:
            return "{" + key + "}"

    values = {key: "" if value is None else str(value) for key, value in kwargs.items()}
    return template.format_map(_Safe(**values))


def _pack_dirs(kind: str) -> list[Path]:
    """默认 prompts/{agents|judges}；PROMPT_PACK 可覆盖同名文件。"""
    dirs = [PROMPTS_ROOT / kind]
    pack = (os.getenv("PROMPT_PACK") or "").strip()
    if pack:
        dirs.append(PROMPTS_ROOT / "packs" / pack / kind)
    return dirs


def _resolve_yaml(kind: str, prompt_id: str) -> Path:
    found: Path | None = None
    for folder in _pack_dirs(kind):
        candidate = folder / f"{prompt_id}.yaml"
        if candidate.exists():
            found = candidate
    if found is None:
        raise FileNotFoundError(
            f"找不到 {kind} prompt `{prompt_id}`。在 prompts/{kind}/{prompt_id}.yaml 新增一份即可。"
        )
    return found


def _read_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Prompt 文件必须是 YAML 对象: {path}")
    return data


@lru_cache(maxsize=64)
def load_rules(rules_id: str) -> dict[str, Any]:
    path = _resolve_yaml("rules", rules_id)
    return _read_yaml(path)


@lru_cache(maxsize=64)
def load_agent(agent_id: str) -> AgentPrompt:
    path = _resolve_yaml("agents", agent_id)
    raw = _read_yaml(path)
    return AgentPrompt(
        id=str(raw.get("id") or agent_id),
        node=str(raw.get("node") or agent_id),
        role=str(raw.get("role") or ""),
        system=str(raw.get("system") or "").strip(),
        user_template=str(raw.get("user_template") or "{query}"),
        policy=dict(raw.get("policy") or {}),
        path=str(path),
    )


@lru_cache(maxsize=64)
def load_judge(metric_id: str) -> JudgePrompt:
    path = _resolve_yaml("judges", metric_id)
    raw = _read_yaml(path)
    steps = raw.get("evaluation_steps") or []
    params = raw.get("evaluation_params") or []
    return JudgePrompt(
        id=str(raw.get("id") or metric_id),
        name=str(raw.get("name") or metric_id),
        target_agent=str(raw.get("target_agent") or ""),
        target_node=str(raw.get("target_node") or ""),
        kind=str(raw.get("kind") or "geval"),
        criteria=str(raw.get("criteria") or "").strip(),
        evaluation_steps=tuple(str(s) for s in steps),
        evaluation_params=tuple(str(p) for p in params),
        threshold=float(raw.get("threshold") if raw.get("threshold") is not None else 0.7),
        scoring=dict(raw.get("scoring") or {}),
        notes=str(raw.get("notes") or "").strip(),
        path=str(path),
    )


def list_ids(kind: str) -> list[str]:
    names: set[str] = set()
    for folder in _pack_dirs(kind):
        if not folder.exists():
            continue
        for path in folder.glob("*.yaml"):
            names.add(path.stem)
    return sorted(names)


def judge_ids_for_agent(agent_id: str) -> list[str]:
    """该业务 Agent 对应的指标 id。轨迹级指标挂在 target_agent=graph。"""
    return [
        metric_id
        for metric_id in list_judge_ids()
        if load_judge(metric_id).target_agent == agent_id
    ]


def list_agent_ids() -> list[str]:
    return list_ids("agents")


def list_judge_ids() -> list[str]:
    return list_ids("judges")


def list_rule_ids() -> list[str]:
    return list_ids("rules")


def clear_prompt_cache() -> None:
    load_agent.cache_clear()
    load_judge.cache_clear()
    load_rules.cache_clear()
    try:
        from graph.rules import clear_duty_rules_cache

        clear_duty_rules_cache()
    except Exception:
        pass


def render_catalog() -> str:
    lines = ["# Prompt catalog", ""]
    lines.append("## Agents")
    for agent_id in list_agent_ids():
        prompt = load_agent(agent_id)
        lines.append(f"- `{prompt.id}`  node={prompt.node}  {prompt.role}  ({Path(prompt.path).name})")
    lines.append("")
    lines.append("## Rules")
    for rules_id in list_rule_ids():
        raw = load_rules(rules_id)
        lines.append(f"- `{rules_id}`  {raw.get('role') or ''}")
    lines.append("")
    lines.append("## Judges")
    for metric_id in list_judge_ids():
        prompt = load_judge(metric_id)
        lines.append(
            f"- `{prompt.id}`  → {prompt.target_agent}/{prompt.target_node}  "
            f"kind={prompt.kind}  threshold={prompt.threshold}"
        )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    print(render_catalog(), end="")
