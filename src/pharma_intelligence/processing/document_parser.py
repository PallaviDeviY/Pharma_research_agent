from __future__ import annotations

import html
import re


TAG_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"[\t\r\f\v ]+")


def clean_text(text: str | None) -> str:
    """Remove markup and normalize spacing while retaining paragraph boundaries."""
    value = html.unescape(text or "")
    value = TAG_RE.sub(" ", value)
    value = value.replace("\u00a0", " ").replace("\r\n", "\n").replace("\r", "\n")
    lines = [SPACE_RE.sub(" ", line).strip() for line in value.split("\n")]
    return "\n".join(line for line in lines if line)

