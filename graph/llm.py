"""Agent 侧聊天模型工厂。heuristic 模式不加载任何云端/本地 LLM。"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Literal, Optional

from dotenv import load_dotenv

load_dotenv()

AgentMode = Literal["heuristic", "openai", "ollama"]


@dataclass(frozen=True)
class LLMSettings:
    mode: AgentMode
    openai_model: str
    ollama_model: str
    ollama_base_url: str
    openai_base_url: str | None


def load_llm_settings() -> LLMSettings:
    raw = (os.getenv("AGENT_LLM") or "heuristic").strip().lower()
    if raw not in {"heuristic", "openai", "ollama"}:
        raw = "heuristic"
    if raw == "openai" and not os.getenv("OPENAI_API_KEY"):
        raw = "heuristic"
    return LLMSettings(
        mode=raw,  # type: ignore[arg-type]
        openai_model=os.getenv("OPENAI_MODEL") or "gpt-4o-mini",
        ollama_model=os.getenv("OLLAMA_MODEL") or "qwen2.5:7b",
        ollama_base_url=os.getenv("OLLAMA_BASE_URL") or "http://localhost:11434",
        openai_base_url=os.getenv("OPENAI_BASE_URL") or None,
    )


def get_chat_model(temperature: float = 0):
    """返回 LangChain ChatModel；heuristic 模式返回 None。"""
    settings = load_llm_settings()
    if settings.mode == "heuristic":
        return None
    if settings.mode == "openai":
        from langchain_openai import ChatOpenAI

        kwargs: dict[str, Any] = {
            "model": settings.openai_model,
            "temperature": temperature,
        }
        if settings.openai_base_url:
            kwargs["base_url"] = settings.openai_base_url
        return ChatOpenAI(**kwargs)
    from langchain_ollama import ChatOllama

    return ChatOllama(
        model=settings.ollama_model,
        base_url=settings.ollama_base_url,
        temperature=temperature,
    )


def extract_json_object(text: str) -> Optional[dict[str, Any]]:
    """从模型输出中抠出第一个 JSON 对象。"""
    import json
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
