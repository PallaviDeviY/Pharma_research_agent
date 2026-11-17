from __future__ import annotations

from pharma_intelligence.processing.document_parser import clean_text


def chunk_text(text: str, chunk_size: int = 900, overlap: int = 120) -> list[str]:
    """Split text on word boundaries with a bounded overlap and no empty chunks."""
    if chunk_size <= 0 or overlap < 0 or overlap >= chunk_size:
        raise ValueError("Require chunk_size > overlap >= 0")
    words = clean_text(text).split()
    if not words:
        return []
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for word in words:
        extra = len(word) + (1 if current else 0)
        if current and current_len + extra > chunk_size:
            chunks.append(" ".join(current))
            overlap_words: list[str] = []
            overlap_len = 0
            for prior in reversed(current):
                cost = len(prior) + (1 if overlap_words else 0)
                if overlap_len + cost > overlap:
                    break
                overlap_words.insert(0, prior)
                overlap_len += cost
            current = overlap_words
            current_len = overlap_len
        if current and current_len + len(word) + 1 > chunk_size:
            # A single token longer than the remaining space: keep it intact.
            chunks.append(" ".join(current))
            current, current_len = [], 0
        current.append(word)
        current_len += len(word) + (1 if len(current) > 1 else 0)
    if current:
        chunks.append(" ".join(current))
    return chunks

