from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import requests

from pharma_intelligence.config import settings


RAW_DIR = Path(__file__).resolve().parents[3] / "data" / "raw"


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-") or "unknown"


def save_raw_json(source: str, drug_name: str, payload: dict[str, Any]) -> Path:
    today = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y%m%d")
    folder = RAW_DIR / _slug(source)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{today}_{_slug(drug_name)}.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def save_raw_json_text(source: str, drug_name: str, text: str) -> Path:
    today = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y%m%d")
    folder = RAW_DIR / _slug(source)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{today}_{_slug(drug_name)}.json"
    path.write_text(text, encoding="utf-8")
    return path


def save_raw_text(source: str, drug_name: str, suffix: str, text: str) -> Path:
    today = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y%m%d")
    folder = RAW_DIR / _slug(source)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{today}_{_slug(drug_name)}_{_slug(suffix)}.xml"
    path.write_text(text, encoding="utf-8")
    return path


class SourceError(RuntimeError):
    """An upstream source could not be queried or parsed."""


def session() -> requests.Session:
    client = requests.Session()
    client.headers.update({"User-Agent": settings.user_agent, "Accept": "application/json, application/xml;q=0.9"})
    return client


def get_json(
    client: requests.Session,
    url: str,
    params: dict[str, Any],
    source: str,
    drug_name: str | None = None,
    raw_source: str | None = None,
) -> dict[str, Any]:
    try:
        response = client.get(url, params=params, timeout=settings.request_timeout_seconds)
        response.raise_for_status()
        if drug_name:
            save_raw_json_text(raw_source or source, drug_name, response.text)
        return response.json()
    except requests.RequestException as exc:
        raise SourceError(f"{source} request failed: {exc}") from exc
    except ValueError as exc:
        raise SourceError(f"{source} returned invalid JSON") from exc

