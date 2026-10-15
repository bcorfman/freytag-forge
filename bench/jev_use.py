"""Bench-only Jev questions sent directly to Cloudflare."""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from contextlib import suppress

from storygame.runtime import jev_questions

THRESHOLD = 0.5  # Matches the threshold in bench/jev-judge.mjs.

_DEFAULT_MAX_CALLS = 400
_DEFAULT_MAX_CONSECUTIVE_FAILURES = 5
_SPEND_LIMIT_CODES = {"AI_QUOTA_EXCEEDED", "AI_DAILY_BUDGET_EXCEEDED"}
_LOGGER = logging.getLogger(__name__)
_STATS = {
    "calls": 0,
    "ok": 0,
    "failures": {},
    "stopped": None,
    "cap_reached": False,
}
_CONSECUTIVE_FAILURES = 0
_LOGGED_FAILURE_KINDS = set()


def jev_stats() -> dict:
    """Return a snapshot of this process's direct Jev call statistics."""

    return {
        **_STATS,
        "failures": dict(_STATS["failures"]),
    }


def reset_jev_stats() -> None:
    """Reset direct Jev call statistics and stop state, primarily for tests."""

    global _CONSECUTIVE_FAILURES
    _STATS["calls"] = 0
    _STATS["ok"] = 0
    _STATS["failures"].clear()
    _STATS["stopped"] = None
    _STATS["cap_reached"] = False
    _CONSECUTIVE_FAILURES = 0
    _LOGGED_FAILURE_KINDS.clear()


def _environment_int(environment, name: str, default: int, *, minimum: int) -> int:
    try:
        value = int(environment.get(name, default))
    except (TypeError, ValueError):
        return default
    return value if value >= minimum else default


def _stop(reason: str) -> None:
    if _STATS["stopped"] is None:
        _STATS["stopped"] = reason


def _record_failure(kind: str, max_consecutive_failures: int) -> None:
    global _CONSECUTIVE_FAILURES
    failures = _STATS["failures"]
    failures[kind] = failures.get(kind, 0) + 1
    if kind not in _LOGGED_FAILURE_KINDS:
        _LOGGER.warning("Jev bench request failed: %s", kind)
        _LOGGED_FAILURE_KINDS.add(kind)
    _CONSECUTIVE_FAILURES += 1
    if max_consecutive_failures <= _CONSECUTIVE_FAILURES:
        _stop("max_consecutive_failures")


def _response_status(response) -> int | None:
    status = getattr(response, "status", None)
    if status is None:
        getcode = getattr(response, "getcode", None)
        status = getcode() if callable(getcode) else None
    return status if isinstance(status, int) else None


def _response_headers(response) -> dict[str, str]:
    headers = getattr(response, "headers", None)
    if headers is None:
        return {}
    try:
        return {str(key).lower(): str(value) for key, value in headers.items()}
    except (AttributeError, TypeError):
        return {}


def _spend_limit_code(raw_body: bytes | str, headers: dict[str, str]) -> str | None:
    for value in headers.values():
        for code in _SPEND_LIMIT_CODES:
            if code in value:
                return code
    text = raw_body.decode(errors="replace") if isinstance(raw_body, bytes) else raw_body
    for code in _SPEND_LIMIT_CODES:
        if code in text:
            return code
    return None


def _ask(*, environment, opener):
    account = environment.get("CLOUDFLARE_ACCOUNT_ID")
    token = environment.get("CLOUDFLARE_AI_TOKEN")
    if not account or not token:
        return lambda _state, _questions: None

    max_calls = _environment_int(environment, "FREYTAG_BENCH_JEV_MAX_CALLS", _DEFAULT_MAX_CALLS, minimum=0)
    max_consecutive_failures = _environment_int(
        environment,
        "FREYTAG_BENCH_JEV_MAX_CONSECUTIVE_FAILURES",
        _DEFAULT_MAX_CONSECUTIVE_FAILURES,
        minimum=1,
    )

    def ask(state, questions):
        global _CONSECUTIVE_FAILURES
        if _STATS["stopped"] is not None:
            return None
        if _STATS["calls"] >= max_calls:
            _STATS["cap_reached"] = True
            return None

        body = {"model": "typesafe/jev", "input": {"state": state, "questions": questions}}
        request = urllib.request.Request(
            f"https://api.cloudflare.com/client/v4/accounts/{account}/ai/run",
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
            method="POST",
        )
        _STATS["calls"] += 1
        try:
            with opener(request, timeout=30) as response:
                status = _response_status(response)
                headers = _response_headers(response)
                raw_body = response.read()
            spend_limit = _spend_limit_code(raw_body, headers)
            if spend_limit is not None:
                _stop(spend_limit)
                _record_failure("spend_limit", max_consecutive_failures)
                return None
            if status == 429:
                _stop("http_429")
                _record_failure("http_status", max_consecutive_failures)
                return None
            if status is not None and status >= 400:
                _record_failure("http_status", max_consecutive_failures)
                return None
            payload = json.loads(raw_body)
        except urllib.error.HTTPError as error:
            raw_body = b""
            with suppress(Exception):
                raw_body = error.read()
            spend_limit = _spend_limit_code(raw_body, _response_headers(error))
            if spend_limit is not None:
                _stop(spend_limit)
                _record_failure("spend_limit", max_consecutive_failures)
            elif error.code == 429:
                _stop("http_429")
                _record_failure("http_status", max_consecutive_failures)
            else:
                _record_failure("http_status", max_consecutive_failures)
            return None
        except TimeoutError:
            _record_failure("timeout", max_consecutive_failures)
            return None
        except (json.JSONDecodeError, UnicodeDecodeError, TypeError, ValueError):
            _record_failure("bad_payload", max_consecutive_failures)
            return None
        except Exception:
            _record_failure("request", max_consecutive_failures)
            return None

        if not isinstance(payload, dict):
            _record_failure("bad_payload", max_consecutive_failures)
            return None
        result = payload.get("result")
        if payload.get("success") is not True or not isinstance(result, dict) or result.get("state") != "Completed":
            _record_failure("not_completed", max_consecutive_failures)
            return None
        result_data = result.get("result")
        if not isinstance(result_data, dict) or not isinstance(result_data.get("answers"), dict):
            _record_failure("bad_payload", max_consecutive_failures)
            return None
        _STATS["ok"] += 1
        _CONSECUTIVE_FAILURES = 0
        return result_data["answers"]

    return ask


def ask_uses_thing(command: str, thing_name: str, *, environment=None, opener=None) -> bool | None:
    environment = os.environ if environment is None else environment
    opener = urllib.request.urlopen if opener is None else opener
    return jev_questions.uses_thing(_ask(environment=environment, opener=opener), command, thing_name)


def ask_moves_thing(command: str, thing_name: str, *, environment=None, opener=None) -> bool | None:
    environment = os.environ if environment is None else environment
    opener = urllib.request.urlopen if opener is None else opener
    return jev_questions.moves_thing(_ask(environment=environment, opener=opener), command, thing_name)


def ask_needs_to_stand(command: str, seat_name: str, within_reach, *, environment=None, opener=None) -> bool | None:
    environment = os.environ if environment is None else environment
    opener = urllib.request.urlopen if opener is None else opener
    return jev_questions.needs_to_stand(_ask(environment=environment, opener=opener), command, seat_name, within_reach)


def ask_same_or_part(
    command: str,
    story: str,
    question: str,
    statement: str,
    player,
    known,
    *,
    environment=None,
    opener=None,
) -> bool | None:
    environment = os.environ if environment is None else environment
    opener = urllib.request.urlopen if opener is None else opener
    return jev_questions.same_or_part(
        _ask(environment=environment, opener=opener), command, story, question, statement, player, known
    )
