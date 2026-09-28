"""Deterministic local retrieval for the literature knowledge base."""

import json
import re
from pathlib import Path


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


class LiteratureRetriever:
    def __init__(self, path: str | Path):
        self.records = json.loads(Path(path).read_text(encoding="utf-8"))

    def search(self, query: str, limit: int = 2) -> list[dict]:
        query_tokens = _tokens(query)
        ranked = []
        for record in self.records:
            searchable = " ".join(str(value) for value in record.values())
            score = len(query_tokens & _tokens(searchable))
            ranked.append((score, record))
        ranked.sort(key=lambda item: (-item[0], item[1]["id"]))
        return [record for score, record in ranked[:limit] if score > 0]
