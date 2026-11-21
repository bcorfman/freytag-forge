"""Read the narration Worker's daily spend counter."""

from __future__ import annotations

import json
import os
import re
import urllib.request
from collections.abc import Callable, Mapping
from datetime import date
from urllib.parse import urlsplit

_TIMEOUT_SECONDS = 10
_DAY_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}\Z")
_BUDGET_FIELDS = ("spent_micro_usd", "reserved_micro_usd", "limit_micro_usd")


def _default_fetch(url: str, token: str, timeout: int) -> tuple[int, str]:
    request = urllib.request.Request(
        url,
        data=b"{}",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.status, response.read().decode("utf-8")


def _valid_day(value: object) -> bool:
    if not isinstance(value, str) or _DAY_PATTERN.fullmatch(value) is None:
        return False
    try:
        return date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


def _valid_integer(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def read_worker_budget(
    environment: Mapping[str, str] | None = None,
    *,
    fetch: Callable[[str, str, int], tuple[int, str]] | None = None,
) -> dict | None:
    """Return a validated Worker budget reading, or ``None`` when unavailable."""

    values = os.environ if environment is None else environment
    try:
        worker_url = values.get("CLOUDFLARE_WORKER_URL")
        token = values.get("CLOUDFLARE_WORKER_TOKEN")
        if not worker_url or not token:
            return None
        parsed = urlsplit(worker_url)
        if not parsed.scheme or not parsed.netloc:
            return None
        budget_url = f"{parsed.scheme}://{parsed.netloc}/budget"
        status_code, response_text = (fetch or _default_fetch)(budget_url, token, _TIMEOUT_SECONDS)
        if status_code != 200:
            return None
        payload = json.loads(response_text)
        if not isinstance(payload, dict) or payload.get("status") != "ok" or not _valid_day(payload.get("day")):
            return None
        if any(not _valid_integer(payload.get(field)) for field in _BUDGET_FIELDS):
            return None
        return {
            "status": "ok",
            "day": payload["day"],
            **{field: payload[field] for field in _BUDGET_FIELDS},
        }
    except Exception:
        return None


def spend_between(before: dict | None, after: dict | None) -> int | None:
    """Return same-day settled spend in micro-dollars between two readings."""

    if not isinstance(before, dict) or not isinstance(after, dict) or before.get("day") != after.get("day"):
        return None
    previous = before.get("spent_micro_usd")
    current = after.get("spent_micro_usd")
    if not _valid_integer(previous) or not _valid_integer(current) or current < previous:
        return None
    return current - previous
