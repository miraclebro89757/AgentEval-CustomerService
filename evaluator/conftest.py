"""pytest 强制走启发式，避免本机 .env 的 Ollama 拖垮单测。"""

from __future__ import annotations

import os

os.environ["AGENT_LLM"] = "heuristic"
os.environ["JUDGE_LLM"] = "heuristic"
os.environ["CONFIDENT_TRACING_ENABLED"] = "NO"
