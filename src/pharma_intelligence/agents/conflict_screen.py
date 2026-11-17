from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any


TOPICS = {
    "cardiovascular outcomes": re.compile(r"cardiovascular|heart failure|myocardial|stroke|mortality|mace", re.I),
    "safety": re.compile(r"safety|adverse event|side effect|hypoglyc|bleeding|renal|kidney", re.I),
    "glycemic outcomes": re.compile(r"glycated|hba1c|glucose|glycemic", re.I),
    "weight outcomes": re.compile(r"weight|body mass|bmi", re.I),
}
POSITIVE = re.compile(r"\b(reduced|lowered|improved|benefit|effective|decreased|fewer)\b", re.I)
NEGATIVE = re.compile(r"\b(no significant|not reduce|did not reduce|not improve|no difference|ineffective|increased risk|more adverse)\b", re.I)


def screen_conflicts(hits: Iterable[dict[str, Any]]) -> list[str]:
    """Flag possible opposite-polarity wording; it never adjudicates a clinical conflict."""
    statements: list[tuple[str, str, str]] = []
    for hit in hits:
        for sentence in re.split(r"(?<=[.!?])\s+", hit.get("text", "")):
            if not sentence.strip():
                continue
            for topic, pattern in TOPICS.items():
                if pattern.search(sentence):
                    polarity = "negative" if NEGATIVE.search(sentence) else "positive" if POSITIVE.search(sentence) else "neutral"
                    if polarity != "neutral":
                        statements.append((topic, polarity, f"{hit['source']}:{hit['external_id']}"))
    flags = []
    seen = set()
    for index, first in enumerate(statements):
        for second in statements[index + 1:]:
            if first[0] == second[0] and first[1] != second[1] and first[2] != second[2]:
                key = (first[0], *sorted((first[2], second[2])))
                if key not in seen:
                    seen.add(key)
                    flags.append(
                        f"Phrase screening found potentially different {first[0]} wording in [{first[2]}] and [{second[2]}]. "
                        "This is a review flag only; populations, endpoints, follow-up periods, and study designs may differ."
                    )
    return flags

