"""预处理安全策略：黄赌毒等关键词过滤。命中则声明边界并终止后续节点。"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from prompts import load_agent

# YAML 缺失或损坏时的兜底词表。单字不进词表，避免「消毒」「黄色款」误伤。
DEFAULT_CATEGORIES: dict[str, tuple[str, ...]] = {
    "porn": (
        "色情",
        "黄色网站",
        "黄色资源",
        "黄片",
        "黄网",
        "成人影片",
        "成人视频",
        "成人网站",
        "约炮",
        "嫖娼",
        "援交",
        "裸聊",
        "色情片",
        "色情直播",
        "卖淫",
        "性服务",
        "pornhub",
        "xvideos",
        "onlyfans",
        "porn",
    ),
    "gambling": (
        "赌博",
        "博彩",
        "赌场",
        "赌球",
        "赌钱",
        "网上赌",
        "网络赌",
        "开户返水",
        "百家乐",
        "赌站",
        "casino",
        "sportsbook",
    ),
    "drugs": (
        "毒品",
        "吸毒",
        "贩毒",
        "制毒",
        "冰毒",
        "海洛因",
        "大麻",
        "可卡因",
        "摇头丸",
        "芬太尼",
        "麻古",
        "氯胺酮",
        "heroin",
        "cocaine",
        "marijuana",
        "fentanyl",
        "meth",
        "ecstasy",
        "ketamine",
    ),
}

DEFAULT_REPLY = (
    "您好。您这条消息触及本助手的服务边界，涉及色情、赌博或毒品等违规内容。"
    "我是星云数码的购物售后客服，只能处理商品、订单、物流、退换货和账号问题。"
    "这类请求我无法协助：不会回答、不会检索知识库，也不会调用任何工具。"
    "请提出与购物售后相关的问题。"
)

_SPACE_RE = re.compile(r"\s+")


def _normalize(text: str) -> str:
    return unicodedata.normalize("NFKC", text or "").casefold()


def _compact(text: str) -> str:
    return _SPACE_RE.sub("", text)


def _safety_policy() -> dict[str, Any]:
    try:
        return dict(load_agent("intent_preprocess").policy.get("safety") or {})
    except Exception:
        return {}


def _categories() -> dict[str, tuple[str, ...]]:
    raw = _safety_policy().get("categories")
    if not isinstance(raw, dict) or not raw:
        return DEFAULT_CATEGORIES
    parsed: dict[str, tuple[str, ...]] = {}
    for name, words in raw.items():
        cleaned = tuple(str(w).strip() for w in (words or []) if str(w).strip() and len(str(w).strip()) >= 2)
        if cleaned:
            parsed[str(name)] = cleaned
    return parsed or DEFAULT_CATEGORIES


def boundary_reply() -> str:
    text = str(_safety_policy().get("boundary_reply") or "").strip()
    return text or DEFAULT_REPLY


def _ascii_word_hit(haystack: str, needle: str) -> bool:
    return re.search(rf"(?<![a-z0-9]){re.escape(needle)}(?![a-z0-9])", haystack) is not None


def scan_policy_violation(query: str) -> dict[str, Any] | None:
    """命中则返回 {category, keyword, categories}；未命中返回 None。"""
    normalized = _normalize(query)
    compact = _compact(normalized)
    if not compact:
        return None
    hits: list[tuple[str, str]] = []
    for category, words in _categories().items():
        for keyword in sorted(words, key=len, reverse=True):
            needle = _compact(_normalize(keyword))
            if len(needle) < 2:
                continue
            matched = (
                _ascii_word_hit(normalized, needle)
                if needle.isascii()
                else needle in compact
            )
            if matched:
                hits.append((category, keyword))
                break
    if not hits:
        return None
    category, keyword = hits[0]
    return {
        "category": category,
        "keyword": keyword,
        "categories": [item[0] for item in hits],
    }
