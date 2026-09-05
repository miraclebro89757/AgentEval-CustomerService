"""模拟知识库检索：中英混合的词面打分，零额外依赖。"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from typing import Any

from graph.state import KB_PATH

_TOKEN_RE = re.compile(r"[a-z0-9]+|[\u4e00-\u9fff]{1,2}", re.I)


def tokenize(text: str) -> list[str]:
    text = (text or "").lower()
    tokens: list[str] = []
    for raw in _TOKEN_RE.findall(text):
        if re.fullmatch(r"[\u4e00-\u9fff]{2}", raw):
            tokens.append(raw)
        elif re.fullmatch(r"[\u4e00-\u9fff]", raw):
            tokens.append(raw)
        else:
            tokens.append(raw)
    # 连续汉字再切 bigram，提高「无理由退货」这类短语命中
    hans = "".join(ch for ch in text if "\u4e00" <= ch <= "\u9fff")
    tokens.extend(hans[i : i + 2] for i in range(len(hans) - 1))
    return tokens


@lru_cache(maxsize=1)
def load_knowledge_base() -> list[dict[str, Any]]:
    return json.loads(KB_PATH.read_text(encoding="utf-8"))


INTENT_CATEGORY = {
    "product_inquiry": "product",
    "refund": "refund",
    "shipping": "shipping",
    "account": "account",
}


def retrieve(query: str, *, top_k: int | None = None, intent: str | None = None) -> list[dict[str, Any]]:
    from prompts import load_agent

    policy = load_agent("rag_retrieve").policy
    k = int(top_k if top_k is not None else policy.get("top_k") or 3)
    boost = float(policy.get("category_boost") or 18)
    penalty = float(policy.get("off_category_penalty") or 0.25)
    docs = load_knowledge_base()
    q_tokens = set(tokenize(query))
    category = INTENT_CATEGORY.get(intent or "")
    scored: list[tuple[float, dict[str, Any]]] = []
    for doc in docs:
        blob = " ".join(
            [
                doc.get("title", ""),
                doc.get("content", ""),
                " ".join(doc.get("tags") or []),
                doc.get("category", ""),
            ]
        )
        d_tokens = tokenize(blob)
        if not d_tokens:
            continue
        overlap = sum(1 for t in d_tokens if t in q_tokens)
        tag_boost = 8 * sum(1 for tag in doc.get("tags") or [] if tag in query)
        title_boost = 6 * sum(1 for t in tokenize(doc.get("title", "")) if t in q_tokens)
        score = overlap + tag_boost + title_boost
        if category:
            if doc.get("category") == category:
                score += boost
            else:
                score *= penalty
        if score > 0:
            scored.append((score, doc))
    scored.sort(key=lambda x: x[0], reverse=True)
    results = []
    for score, doc in scored[:k]:
        item = dict(doc)
        item["score"] = round(float(score), 2)
        results.append(item)
    return results
