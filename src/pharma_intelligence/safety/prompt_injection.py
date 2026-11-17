from __future__ import annotations

import re


INSTRUCTION_PATTERNS = [
    re.compile(r"ignore (all )?(previous|prior|above) instructions", re.I),
    re.compile(r"(system|developer) prompt", re.I),
    re.compile(r"execute (this )?(sql|query)|run (this )?(sql|query)", re.I),
    re.compile(r"call (the )?(tool|function)|send (an )?(email|message)", re.I),
    re.compile(r"reveal (the )?(hidden|secret)|disregard (the )?(user|question)", re.I),
]


def contains_instruction_like_text(text: str) -> bool:
    return any(pattern.search(text or "") for pattern in INSTRUCTION_PATTERNS)


def filter_retrieved_text(text: str) -> tuple[str, bool]:
    """Drop complete sentences that try to control a tool or override the research task."""
    segments = re.split(r"(?<=[.!?])\s+|\n+", text or "")
    kept = [segment for segment in segments if segment.strip() and not contains_instruction_like_text(segment)]
    return " ".join(kept), len(kept) != len([segment for segment in segments if segment.strip()])

