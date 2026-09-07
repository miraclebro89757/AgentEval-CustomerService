"""Agent 侧聊天模型工厂。默认走本地 Ollama Qwen；pytest / --heuristic 可切回规则机。"""

from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass
from typing import Any, Literal, Optional

from dotenv import load_dotenv

load_dotenv()

AgentMode = Literal["heuristic", "openai", "ollama"]
DEFAULT_OLLAMA_MODEL = "qwen2.5:7b"


@dataclass(frozen=True)
class LLMSettings:
    mode: AgentMode
    openai_model: str
    ollama_model: str
    ollama_base_url: str
    openai_base_url: str | None
    temperature: float


def ollama_base_url() -> str:
    return (os.getenv("OLLAMA_BASE_URL") or "http://localhost:11434").rstrip("/")


def ollama_model_name() -> str:
    return os.getenv("OLLAMA_MODEL") or DEFAULT_OLLAMA_MODEL


def ollama_available(timeout: float = 0.8) -> bool:
    try:
        urllib.request.urlopen(f"{ollama_base_url()}/api/tags", timeout=timeout)
        return True
    except Exception:
        return False


def ollama_has_model(model: str | None = None, timeout: float = 1.5) -> bool:
    name = model or ollama_model_name()
    try:
        with urllib.request.urlopen(f"{ollama_base_url()}/api/tags", timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return False
    names = {item.get("name") or "" for item in payload.get("models") or []}
    if name in names:
        return True
    return any(item.startswith(f"{name}:") or item.split(":")[0] == name.split(":")[0] for item in names)


def load_llm_settings() -> LLMSettings:
    raw = (os.getenv("AGENT_LLM") or "ollama").strip().lower()
    if raw not in {"heuristic", "openai", "ollama"}:
        raw = "ollama"
    if raw == "openai" and not os.getenv("OPENAI_API_KEY"):
        raw = "ollama" if ollama_available() else "heuristic"
    temperature = 0.0
    try:
        temperature = float(os.getenv("AGENT_TEMPERATURE") or 0)
    except ValueError:
        temperature = 0.0
    return LLMSettings(
        mode=raw,  # type: ignore[arg-type]
        openai_model=os.getenv("OPENAI_MODEL") or "gpt-4o-mini",
        ollama_model=ollama_model_name(),
        ollama_base_url=ollama_base_url(),
        openai_base_url=os.getenv("OPENAI_BASE_URL") or None,
        temperature=temperature,
    )


def require_agent_runtime() -> LLMSettings:
    """CLI 入口用：Ollama 没起来时直接说清，不要静默掉回启发式。"""
    settings = load_llm_settings()
    if settings.mode != "ollama":
        return settings
    if not ollama_available(timeout=1.5):
        raise SystemExit(
            "AGENT_LLM=ollama，但本机 Ollama 没有响应 "
            f"({settings.ollama_base_url})。先执行 `ollama serve`，"
            f"再 `ollama pull {settings.ollama_model}`。"
            "临时不跑模型：`python main.py --heuristic` 或 AGENT_LLM=heuristic。"
        )
    if not ollama_has_model(settings.ollama_model):
        raise SystemExit(
            f"Ollama 已启动，但没有模型 `{settings.ollama_model}`。"
            f"执行：`ollama pull {settings.ollama_model}`"
        )
    return settings


def get_chat_model(temperature: float | None = None):
    """返回 LangChain ChatModel；heuristic 模式返回 None。"""
    settings = load_llm_settings()
    if settings.mode == "heuristic":
        return None
    temp = settings.temperature if temperature is None else temperature
    if settings.mode == "openai":
        from langchain_openai import ChatOpenAI

        kwargs: dict[str, Any] = {
            "model": settings.openai_model,
            "temperature": temp,
        }
        if settings.openai_base_url:
            kwargs["base_url"] = settings.openai_base_url
        return ChatOpenAI(**kwargs)
    from langchain_ollama import ChatOllama

    kwargs: dict[str, Any] = {
        "model": settings.ollama_model,
        "base_url": settings.ollama_base_url,
        "temperature": temp,
        "reasoning": False,
    }
    return ChatOllama(**kwargs)


def extract_json_object(text: str) -> Optional[dict[str, Any]]:
    """从模型输出中抠出第一个 JSON 对象。"""
    import re

    if not text:
        return None
    text = text.strip()
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        return None
