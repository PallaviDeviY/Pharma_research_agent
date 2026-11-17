from __future__ import annotations

import re


class InvalidResearchQuery(ValueError):
    pass


MEDICAL_ADVICE_PATTERNS = [
    re.compile(r"\b(should i|can i|may i)\b.{0,40}\b(take|stop|start|increase|decrease|change|skip)\b", re.I),
    re.compile(r"\b(what dose|dosage for me|diagnose me|do i have|my symptoms)\b", re.I),
    re.compile(r"\b(is it safe for me|treat my|cure my)\b", re.I),
]


def validate_question(question: str) -> str:
    value = (question or "").strip()
    if not value:
        raise InvalidResearchQuery("Enter a research question.")
    if len(value) > 1000:
        raise InvalidResearchQuery("Research questions are limited to 1,000 characters.")
    if any(ord(char) < 32 and char not in "\t\n\r" for char in value):
        raise InvalidResearchQuery("The question contains unsupported control characters.")
    return value


def is_personal_medical_advice(question: str) -> bool:
    return any(pattern.search(question) for pattern in MEDICAL_ADVICE_PATTERNS)

