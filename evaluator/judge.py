"""DeepEval 裁判模型：OpenAI / Ollama / 关闭（走确定性指标）。"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Optional

from dotenv import load_dotenv

from graph.llm import extract_json_object

load_dotenv()


def _ollama_base() -> str:
    return (os.getenv("OLLAMA_BASE_URL") or "http://localhost:11434").rstrip("/")


def ollama_available(timeout: float = 0.4) -> bool:
    try:
        urllib.request.urlopen(f"{_ollama_base()}/api/tags", timeout=timeout)
        return True
    except Exception:
        return False


class OllamaJudge:
    """DeepEvalBaseLLM 适配器。延迟继承，避免未安装 deepeval 时本模块无法导入。"""

    def __init__(self, model: str | None = None, base_url: str | None = None):
        self.model_name = model or os.getenv("OLLAMA_MODEL") or "qwen2.5:7b"
        self.base_url = (base_url or _ollama_base()).rstrip("/")
        self._deepeval_base = None

    def load_model(self):
        return self

    def get_model_name(self) -> str:
        return f"ollama:{self.model_name}"

    def _complete(self, prompt: str) -> str:
        body = json.dumps(
            {"model": self.model_name, "prompt": prompt, "stream": False},
            ensure_ascii=False,
        ).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/api/generate",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        return payload.get("response") or ""

    def generate(self, prompt: str, schema: Any = None) -> Any:
        extra = ""
        if schema is not None:
            extra = "\n只输出符合给定 JSON schema 的对象，不要 Markdown。"
        raw = self._complete(prompt + extra)
        if schema is None:
            return raw
        data = extract_json_object(raw) or {}
        try:
            return schema.model_validate(data)
        except Exception:
            try:
                return schema(**data)
            except Exception:
                return raw

    async def a_generate(self, prompt: str, schema: Any = None) -> Any:
        return self.generate(prompt, schema)

    def as_deepeval_llm(self):
        from deepeval.models import DeepEvalBaseLLM

        judge = self

        class _Bound(DeepEvalBaseLLM):
            def get_model_name(self) -> str:
                return judge.get_model_name()

            def load_model(self):
                return judge.load_model()

            def generate(self, prompt: str, schema: Any = None) -> Any:
                return judge.generate(prompt, schema)

            async def a_generate(self, prompt: str, schema: Any = None) -> Any:
                return judge.generate(prompt, schema)

        return _Bound()


def resolve_judge() -> tuple[str, Optional[Any]]:
    """
    返回 (label, model)。
    model 为 str 时交给 DeepEval 走 OpenAI；为 DeepEvalBaseLLM 时走 Ollama；
    为 None 时只用确定性指标（零配置可跑）。
    """
    mode = (os.getenv("JUDGE_LLM") or "auto").strip().lower()
    if mode == "heuristic":
        return "heuristic", None
    if mode == "openai" or (mode == "auto" and os.getenv("OPENAI_API_KEY")):
        return f"openai:{(os.getenv('OPENAI_MODEL') or 'gpt-4o-mini')}", (
            os.getenv("OPENAI_MODEL") or "gpt-4o-mini"
        )
    if mode in {"ollama", "auto"} and ollama_available():
        try:
            return f"ollama:{(os.getenv('OLLAMA_MODEL') or 'qwen2.5:7b')}", OllamaJudge().as_deepeval_llm()
        except Exception:
            if mode == "ollama":
                raise
    return "heuristic", None
