"""Small, explicitly confirmed, direct Workers AI smoke harness."""

from __future__ import annotations

import argparse
import copy
import json
import math
import os
import statistics
import sys
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from storygame.runtime.cloudflare import BROWSER_USER_AGENT
from storygame.runtime.narration_json import escape_stray_quotes

API_URL = "https://api.cloudflare.com/client/v4/accounts/{account}/ai/run/{model}"
DEFAULT_MAX_CALLS = 24
RESPONSE_FORMAT = {"type": "json_object"}
RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "segments": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "properties": {
                    "kind": {"type": "string", "enum": ["narration", "dialogue", "action"]},
                    "text": {"type": "string"},
                },
                "required": ["kind", "text"],
            },
        },
        "selected_knowledge_ids": {"type": "array", "items": {"type": "string"}},
        "item_facts": {"type": "object"},
    },
    "required": ["segments"],
}

VARIANTS: tuple[dict[str, Any], ...] = (
    {
        "label": "llama-3.1-8b",
        "model_id": "@cf/meta/llama-3.1-8b-instruct-fast",
        "token_parameter": "max_tokens",
        "max_tokens": 1024,
        "extra_body": {},
        "input_price": 0.282,
        "output_price": 0.827,
        "note": "current configured baseline",
    },
    {
        "label": "gemma-4-26b-a4b",
        "model_id": "@cf/google/gemma-4-26b-a4b-it",
        "token_parameter": "max_completion_tokens",
        "max_tokens": 2048,
        "extra_body": {},
        "input_price": 0.10,
        "output_price": 0.30,
        "note": "",
    },
    {
        "label": "qwen3-30b-a3b",
        "model_id": "@cf/qwen/qwen3-30b-a3b-fp8",
        "token_parameter": "max_tokens",
        "max_tokens": 2048,
        "extra_body": {},
        "input_price": 0.0509,
        "output_price": 0.335,
        "note": "",
    },
    {
        "label": "gpt-oss-20b",
        "model_id": "@cf/openai/gpt-oss-20b",
        "token_parameter": "max_tokens",
        "max_tokens": 2048,
        "extra_body": {},
        "input_price": 0.20,
        "output_price": 0.30,
        "note": "",
    },
    {
        "label": "llama-3.3-70b",
        "model_id": "@cf/meta/llama-3.3-70b-instruct-fp8-fast",
        "token_parameter": "max_tokens",
        "max_tokens": 1024,
        "extra_body": {},
        "input_price": 0.293,
        "output_price": 2.253,
        "note": "",
    },
    {
        "label": "llama-3.3-70b-nojson",
        "model_id": "@cf/meta/llama-3.3-70b-instruct-fp8-fast",
        "token_parameter": "max_tokens",
        "max_tokens": 1024,
        "extra_body": {},
        "input_price": 0.293,
        "output_price": 2.253,
        "json_mode": False,
        "note": "omits response_format to avoid forced JSON mode",
    },
    {
        "label": "qwen3-think-off-kwargs",
        "model_id": "@cf/qwen/qwen3-30b-a3b-fp8",
        "token_parameter": "max_tokens",
        "max_tokens": 1024,
        "extra_body": {"chat_template_kwargs": {"enable_thinking": False}},
        "input_price": 0.0509,
        "output_price": 0.335,
        "json_mode": True,
        "note": "disables Qwen3 thinking through chat_template_kwargs",
    },
    {
        "label": "qwen3-think-off-soft",
        "model_id": "@cf/qwen/qwen3-30b-a3b-fp8",
        "token_parameter": "max_tokens",
        "max_tokens": 1024,
        "extra_body": {},
        "input_price": 0.0509,
        "output_price": 0.335,
        "json_mode": True,
        "user_suffix": "/no_think",
        "note": "requests Qwen3 thinking disabled with a user-message suffix",
    },
    {
        "label": "llama-3.3-70b-schema",
        "model_id": "@cf/meta/llama-3.3-70b-instruct-fp8-fast",
        "token_parameter": "max_tokens",
        "max_tokens": 1024,
        "extra_body": {},
        "input_price": 0.293,
        "output_price": 2.253,
        "response_schema": RESPONSE_SCHEMA,
        "note": "constrains the reply with response_format json_schema",
    },
    {
        "label": "llama-3.3-70b-default-temp",
        "model_id": "@cf/meta/llama-3.3-70b-instruct-fp8-fast",
        "token_parameter": "max_tokens",
        "max_tokens": 1024,
        "extra_body": {},
        "input_price": 0.293,
        "output_price": 2.253,
        "json_mode": False,
        "temperature": None,
        "note": "JSON mode off and no temperature, as the product sends it",
    },
)
_PROFILE_BY_LABEL = {profile["label"]: profile for profile in VARIANTS}

_VARIANT_ORDER = tuple(profile["label"] for profile in VARIANTS)
_DEFAULT_VARIANT_ORDER = _VARIANT_ORDER[:4]
_SLOT_ORDER = (
    ("S1", "proposed", 0),
    ("S1", "proposed", 1),
    ("S1", "proposed", 2),
    ("S1", "existing", 0),
    ("S2", "proposed", 0),
    ("S5", "proposed", 0),
)
_WIDE_SLOT_ORDER = (
    ("S1", "proposed", 0),
    ("S1", "proposed", 1),
    ("S1", "proposed", 2),
    ("S1", "existing", 0),
    ("S2", "proposed", 0),
    ("S2", "proposed", 1),
    ("S2", "proposed", 2),
    ("S2", "existing", 0),
    ("S3", "proposed", 0),
    ("S3", "proposed", 1),
    ("S4", "proposed", 0),
    ("S4", "proposed", 1),
    ("S5b", "proposed", 0),
    ("S5b", "proposed", 1),
    ("S5b", "proposed", 2),
    ("S5b", "existing", 0),
    ("S5b", "existing", 1),
    ("S6", "proposed", 0),
    ("S6", "proposed", 1),
    ("S6", "proposed", 2),
)
_PROBE_SLOT_ORDER = tuple(
    (start_id, "proposed", sample) for sample in range(8) for start_id in ("S5b", "S5bA", "S5bB", "S5bC")
)
_CONFIRM_SLOT_ORDER = tuple((start_id, "proposed", sample) for sample in range(15) for start_id in ("S5b", "S5bA"))
_SLOT_ORDERS = {
    "original": _SLOT_ORDER,
    "wide": _WIDE_SLOT_ORDER,
    "probe": _PROBE_SLOT_ORDER,
    "confirm": _CONFIRM_SLOT_ORDER,
}


def _credential_values() -> tuple[str, ...]:
    return tuple(
        value
        for value in (
            os.environ.get("CLOUDFLARE_ACCOUNT_ID", "").strip(),
            os.environ.get("CLOUDFLARE_AI_TOKEN", "").strip(),
            os.environ.get("CF_API_TOKEN", "").strip(),
        )
        if value
    )


def _redact(value: str) -> str:
    for secret in _credential_values():
        value = value.replace(secret, "[REDACTED]")
    return value


def _json_text(value: Any) -> str:
    return _redact(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_json_text(value), encoding="utf-8")


def _load_prompts(path: Path) -> dict[str, dict[str, dict[str, str]]]:
    document = json.loads(path.read_text(encoding="utf-8"))
    starts = document.get("starts") if isinstance(document, dict) else None
    if not isinstance(starts, list):
        raise ValueError("prompt document has no starts list")
    result: dict[str, dict[str, dict[str, str]]] = {}
    for start in starts:
        if not isinstance(start, dict) or not isinstance(start.get("id"), str):
            raise ValueError("prompt document has an invalid start")
        contexts = start.get("contexts")
        if not isinstance(contexts, dict):
            raise ValueError(f"{start['id']} has no contexts")
        selected: dict[str, dict[str, str]] = {}
        for context_name in ("existing", "proposed"):
            context = contexts.get(context_name)
            if (
                not isinstance(context, dict)
                or not isinstance(context.get("system"), str)
                or not isinstance(context.get("user"), str)
            ):
                raise ValueError(f"{start['id']} has an invalid {context_name} context")
            selected[context_name] = {"system": context["system"], "user": context["user"]}
        result[start["id"]] = selected
    required_start_ids = {
        start_id for slot_order in _SLOT_ORDERS.values() for start_id, _context, _sample in slot_order
    } - {"S5b", "S5bA", "S5bB", "S5bC"}
    missing = required_start_ids - result.keys()
    if missing:
        raise ValueError(f"prompt document is missing starts: {', '.join(sorted(missing))}")
    s5b: dict[str, dict[str, str]] = {}
    for context_name, context in result["S5"].items():
        lines = context["user"].splitlines(keepends=True)
        cue_lines = [line for line in lines if "may say this aloud" in line]
        if not cue_lines:
            raise ValueError(f"S5 {context_name} context has no line containing 'may say this aloud'")
        s5b[context_name] = {
            "system": context["system"],
            "user": "".join(line for line in lines if "may say this aloud" not in line),
        }
    result["S5b"] = s5b
    base = result["S5b"]["proposed"]

    def line_without_ending(line: str) -> tuple[str, str]:
        if line.endswith("\r\n"):
            return line[:-2], "\r\n"
        if line.endswith(("\n", "\r")):
            return line[:-1], line[-1]
        return line, ""

    def probe_user(arm: str, *, replace_empty_line: bool, delete_pressure_line: bool) -> str:
        lines = base["user"].splitlines(keepends=True)
        replacement: str | None = None
        output: list[str] = []
        found_empty = False
        found_pressure = False
        suffix = " holds nothing else the player can find."
        for line in lines:
            content, ending = line_without_ending(line)
            if replace_empty_line and content.startswith("- The ") and content.endswith(suffix):
                object_name = content[len("- The ") : -len(suffix)]
                replacement = (
                    f"- Nothing is left in or under the {object_name}. "
                    f"Searching the {object_name} finds nothing.{ending}"
                )
                found_empty = True
                output.append(replacement)
            elif delete_pressure_line and content.startswith("- What presses on "):
                found_pressure = True
            else:
                output.append(line)
        if replace_empty_line and not found_empty:
            raise ValueError(f"{arm} is missing the empty-search line")
        if delete_pressure_line and not found_pressure:
            raise ValueError(f"{arm} is missing the pressure line")
        return "".join(output)

    for arm, replace_empty_line, delete_pressure_line in (
        ("S5bA", True, False),
        ("S5bB", False, True),
        ("S5bC", True, True),
    ):
        result[arm] = {
            "existing": result["S5b"]["existing"],
            "proposed": {
                "system": base["system"],
                "user": probe_user(
                    arm,
                    replace_empty_line=replace_empty_line,
                    delete_pressure_line=delete_pressure_line,
                ),
            },
        }
    return result


def _input_tokens(system: str, user: str) -> int:
    return math.ceil(len((system + user).encode("utf-8")) / 3)


def _build_plan(
    prompts: dict[str, dict[str, dict[str, str]]],
    variant_labels: tuple[str, ...],
    slot_order: tuple[tuple[str, str, int], ...] = _SLOT_ORDER,
) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []
    call_index = 1
    for start_id, context_name, sample in slot_order:
        context = prompts[start_id][context_name]
        for variant_label in variant_labels:
            profile = _PROFILE_BY_LABEL[variant_label]
            user = context["user"]
            user_suffix = profile.get("user_suffix", "")
            if user_suffix:
                user = f"{user}\n\n{user_suffix}"
            input_tokens = _input_tokens(context["system"], user)
            ceiling = (
                input_tokens * profile["input_price"] + profile["max_tokens"] * profile["output_price"]
            ) / 1_000_000
            calls.append(
                {
                    "call_index": call_index,
                    "variant": variant_label,
                    "model": profile["model_id"],
                    "start": start_id,
                    "context": context_name,
                    "sample": sample,
                    "system": context["system"],
                    "user": user,
                    "input_tokens_ceiling": input_tokens,
                    "token_parameter": profile["token_parameter"],
                    "max_tokens": profile["max_tokens"],
                    "note": profile["note"],
                    "ceiling_usd": ceiling,
                }
            )
            call_index += 1
    return calls


def _request_body(call: dict[str, Any]) -> dict[str, Any]:
    profile = _PROFILE_BY_LABEL[call["variant"]]
    body: dict[str, Any] = {
        "messages": [
            {"role": "system", "content": call["system"]},
            {"role": "user", "content": call["user"]},
        ],
    }
    body[profile["token_parameter"]] = profile["max_tokens"]
    body.update(copy.deepcopy(profile.get("extra_body", {})))
    if "response_schema" in profile:
        body["response_format"] = {
            "type": "json_schema",
            "json_schema": copy.deepcopy(profile["response_schema"]),
        }
    elif profile.get("json_mode", True):
        body["response_format"] = RESPONSE_FORMAT
    temperature = profile.get("temperature", 0)
    if temperature is not None:
        body["temperature"] = temperature
    return body


def _headers(response: Any) -> dict[str, str]:
    headers = getattr(response, "headers", {})
    return {str(key): str(value) for key, value in headers.items()} if hasattr(headers, "items") else {}


def _read_http_error(error: HTTPError) -> bytes:
    try:
        body = error.read()
    except Exception as read_error:  # pragma: no cover - malformed transport fallback
        return _redact(f"{type(read_error).__name__}: {read_error}").encode("utf-8", errors="replace")
    return body if isinstance(body, bytes) else str(body).encode("utf-8", errors="replace")


def _json_object(raw_text: str) -> dict[str, Any] | None:
    try:
        value = json.loads(raw_text)
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def _result_object(outer: dict[str, Any] | None) -> dict[str, Any] | None:
    if not outer:
        return None
    result = outer.get("result")
    return result if isinstance(result, dict) else None


def _key_paths(value: Any, prefix: str = "") -> tuple[list[str], list[str]]:
    names: list[str] = []
    paths: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            name = str(key)
            path = f"{prefix}.{name}" if prefix else name
            if "reason" in name.casefold():
                names.append(name)
                paths.append(path)
            child_names, child_paths = _key_paths(child, path)
            names.extend(child_names)
            paths.extend(child_paths)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            child_names, child_paths = _key_paths(child, f"{prefix}[{index}]")
            names.extend(child_names)
            paths.extend(child_paths)
    return names, paths


def _extract_text(outer: dict[str, Any] | None) -> tuple[str | None, str | None]:
    if not outer:
        return None, None
    result = _result_object(outer)
    if result is not None:
        if isinstance(result.get("response"), str):
            return result["response"], "result.response"
        if isinstance(result.get("response"), dict):
            return json.dumps(result["response"], ensure_ascii=False), "result.response(object)"
    if result is not None:
        choices = result.get("choices")
        if isinstance(choices, list) and choices and isinstance(choices[0], dict):
            message = choices[0].get("message")
            if isinstance(message, dict) and isinstance(message.get("content"), str):
                return message["content"], "result.choices[0].message.content"
    choices = outer.get("choices")
    if isinstance(choices, list) and choices and isinstance(choices[0], dict):
        message = choices[0].get("message")
        if isinstance(message, dict) and isinstance(message.get("content"), str):
            return message["content"], "choices[0].message.content"
    return None, None


def _narration_from_reply(text: str | None) -> str | None:
    if not text:
        return None
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return None
    segments = payload.get("segments") if isinstance(payload, dict) else None
    if not isinstance(segments, list):
        return None
    texts = [
        segment["text"] for segment in segments if isinstance(segment, dict) and isinstance(segment.get("text"), str)
    ]
    if len(texts) != len(segments):
        return None
    narration = " ".join(texts).strip()
    return narration or None


def _repair_narration(final_text: str | None, narration: str | None, usable: bool) -> tuple[bool, str | None]:
    if usable:
        return True, narration
    if not final_text:
        return False, None
    repaired_text = escape_stray_quotes(final_text)
    repaired_narration = _narration_from_reply(repaired_text)
    return bool(repaired_narration), repaired_narration


def _usage_and_tokens(
    outer: dict[str, Any] | None, result: dict[str, Any] | None
) -> tuple[Any, int | None, int | None]:
    usage = result.get("usage") if result and isinstance(result.get("usage"), dict) else None
    if usage is None and outer and isinstance(outer.get("usage"), dict):
        usage = outer["usage"]
    if not isinstance(usage, dict):
        return None, None, None

    def number(*keys: str) -> int | None:
        for key in keys:
            value = usage.get(key)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                return int(value)
        return None

    return (
        usage,
        number("prompt_tokens", "input_tokens", "promptTokens"),
        number("completion_tokens", "output_tokens", "completionTokens"),
    )


def _finish_reason(outer: dict[str, Any] | None, result: dict[str, Any] | None) -> Any:
    for container in (result, outer):
        if not isinstance(container, dict):
            continue
        choices = container.get("choices")
        if isinstance(choices, list) and choices and isinstance(choices[0], dict) and "finish_reason" in choices[0]:
            return choices[0]["finish_reason"]
        if "finish_reason" in container:
            return container["finish_reason"]
    return None


def _error_details(raw_text: str) -> tuple[str | None, str | None]:
    value = _json_object(raw_text)
    candidates: list[Any] = [value] if value is not None else []
    while candidates:
        candidate = candidates.pop(0)
        if isinstance(candidate, dict):
            code = candidate.get("code") or candidate.get("error_code")
            message = candidate.get("message") or candidate.get("detail")
            if code is not None or message is not None:
                return (
                    _redact(str(code)) if code is not None else None,
                    _redact(str(message)) if message is not None else None,
                )
            candidates.extend(candidate.values())
        elif isinstance(candidate, list):
            candidates.extend(candidate)
    return None, None


def _row_from_response(call: dict[str, Any], raw_bytes: bytes, status: int | None, latency_ms: float) -> dict[str, Any]:
    raw_text = _redact(raw_bytes.decode("utf-8", errors="replace"))
    outer = _json_object(raw_text)
    result = _result_object(outer)
    final_text, final_path = _extract_text(outer)
    narration = _narration_from_reply(final_text)
    usable = bool(status is not None and 200 <= status < 300 and narration)
    repair_usable, narration_repaired = _repair_narration(final_text, narration, usable)
    usage, prompt_tokens, completion_tokens = _usage_and_tokens(outer, result)
    finish_reason = _finish_reason(outer, result)
    reasoning_fields, reasoning_paths = _key_paths(outer)
    profile = _PROFILE_BY_LABEL[call["variant"]]
    actual_cost = None
    if prompt_tokens is not None or completion_tokens is not None:
        actual_cost = (
            (prompt_tokens or 0) * profile["input_price"] + (completion_tokens or 0) * profile["output_price"]
        ) / 1_000_000
    return {
        "call_index": call["call_index"],
        "variant": call["variant"],
        "model": call["model"],
        "start": call["start"],
        "context": call["context"],
        "sample": call["sample"],
        "status": status,
        "latency_ms": latency_ms,
        "request_bytes": call["request_bytes"],
        "response_bytes": len(raw_bytes),
        "raw_response": raw_text,
        "top_level_keys": list(outer) if outer is not None else [],
        "result_keys": list(result) if result is not None else [],
        "final_text_path": final_path,
        "final_text": final_text,
        "reasoning_fields": sorted(set(reasoning_fields)),
        "reasoning_field_paths": sorted(set(reasoning_paths)),
        "usage": usage,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "finish_reason": finish_reason,
        "narration": narration,
        "usable": usable,
        "repair_usable": repair_usable,
        "narration_repaired": narration_repaired,
        "truncated": finish_reason == "length" or bool(outer and outer.get("truncated")),
        "actual_cost_usd": actual_cost,
        "skipped": False,
    }


def _transport_row(call: dict[str, Any], error: BaseException, latency_ms: float) -> dict[str, Any]:
    message = _redact(f"{type(error).__name__}: {error}")
    return {
        "call_index": call["call_index"],
        "variant": call["variant"],
        "model": call["model"],
        "start": call["start"],
        "context": call["context"],
        "sample": call["sample"],
        "status": None,
        "latency_ms": latency_ms,
        "request_bytes": call["request_bytes"],
        "response_bytes": len(message.encode("utf-8")),
        "raw_response": message,
        "top_level_keys": [],
        "result_keys": [],
        "final_text_path": None,
        "final_text": None,
        "reasoning_fields": [],
        "reasoning_field_paths": [],
        "usage": None,
        "prompt_tokens": None,
        "completion_tokens": None,
        "finish_reason": None,
        "narration": None,
        "usable": False,
        "repair_usable": False,
        "narration_repaired": None,
        "truncated": False,
        "actual_cost_usd": None,
        "error_class": "TRANSPORT",
        "error_message": message,
        "skipped": False,
    }


def _call(account: str, token: str, call: dict[str, Any]) -> dict[str, Any]:
    body = _request_body(call)
    request_bytes = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    call["request_bytes"] = len(request_bytes)
    request = Request(
        API_URL.format(account=account, model=call["model"]),
        data=request_bytes,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "User-Agent": BROWSER_USER_AGENT,
        },
        method="POST",
    )
    started = time.perf_counter()
    try:
        with urlopen(request, timeout=float(os.environ.get("CLOUDFLARE_TIMEOUT", "15"))) as response:  # noqa: S310
            raw_bytes = response.read()
            status = int(getattr(response, "status", getattr(response, "code", 200)))
    except HTTPError as error:
        raw_bytes = _read_http_error(error)
        status = int(error.code)
    except Exception as error:  # one answered attempt, never a retry
        return _transport_row(call, error, round((time.perf_counter() - started) * 1000, 3))
    return _row_from_response(call, raw_bytes, status, round((time.perf_counter() - started) * 1000, 3))


def _error_class(row: dict[str, Any]) -> str | None:
    status = row.get("status")
    if status in (401, 403):
        return "AUTH"
    if status == 429:
        return "RATE_LIMIT"
    if isinstance(status, int) and not 200 <= status < 300:
        return "HTTP_ERROR"
    return row.get("error_class")


def _stop_reason(row: dict[str, Any]) -> str | None:
    error_class = _error_class(row)
    if error_class == "AUTH":
        row["error_class"] = "AUTH"
        code, message = _error_details(row.get("raw_response", ""))
        row["error_code"] = code
        row["error_message"] = message or f"HTTP {row['status']}"
        return "AUTH"
    if error_class == "RATE_LIMIT":
        code, message = _error_details(row.get("raw_response", ""))
        row["error_class"] = "RATE_LIMIT"
        row["error_code"] = code
        row["error_message"] = message or f"HTTP {row['status']}"
        return ": ".join(part for part in (code, message) if part) or "HTTP_429"
    return None


def _mark_variant_failure(row: dict[str, Any]) -> None:
    row["error_class"] = "VARIANT_FAILED"
    code, message = _error_details(row.get("raw_response", ""))
    row["error_code"] = code
    if message:
        row["error_message"] = message
    elif isinstance(row.get("status"), int):
        row["error_message"] = f"HTTP {row['status']}"
    else:
        row["error_message"] = "unusable response body"


def _is_variant_failure(row: dict[str, Any]) -> bool:
    status = row.get("status")
    return isinstance(status, int) and not 200 <= status < 300


def _skipped_row(call: dict[str, Any], reason: str) -> dict[str, Any]:
    return {
        "call_index": call["call_index"],
        "variant": call["variant"],
        "model": call["model"],
        "start": call["start"],
        "context": call["context"],
        "sample": call["sample"],
        "status": None,
        "latency_ms": 0.0,
        "request_bytes": 0,
        "response_bytes": 0,
        "raw_response": "",
        "top_level_keys": [],
        "result_keys": [],
        "final_text_path": None,
        "final_text": None,
        "reasoning_fields": [],
        "reasoning_field_paths": [],
        "usage": None,
        "prompt_tokens": None,
        "completion_tokens": None,
        "finish_reason": None,
        "narration": None,
        "usable": False,
        "repair_usable": False,
        "narration_repaired": None,
        "truncated": False,
        "actual_cost_usd": None,
        "error_class": "SKIPPED",
        "error_message": reason,
        "skipped": True,
    }


def _run(plan: list[dict[str, Any]], account: str, token: str, out: Path, ceiling_usd: float) -> dict[str, Any]:
    result: dict[str, Any] = {
        "schema": 1,
        "mode": "run",
        "calls_planned": len(plan),
        "ceiling_usd": ceiling_usd,
        "rows": [],
        "stop_reason": None,
        "failed_variants": {},
    }
    consecutive_transport_failures = 0
    failed_variants: set[str] = set()
    for call in plan:
        if call["variant"] in failed_variants:
            row = _skipped_row(call, f"variant {call['variant']} FAILED")
            result["rows"].append(row)
            _write_json(out, result)
            continue
        row = _call(account, token, call)
        result["rows"].append(row)
        _write_json(out, result)
        stop_reason = _stop_reason(row)
        if stop_reason is not None:
            result["stop_reason"] = stop_reason
            _write_json(out, result)
            break
        if row.get("error_class") == "TRANSPORT":
            consecutive_transport_failures += 1
            if consecutive_transport_failures >= 2:
                result["stop_reason"] = "TRANSPORT_FAILURES"
                _write_json(out, result)
                break
        else:
            consecutive_transport_failures = 0
            if _is_variant_failure(row):
                _mark_variant_failure(row)
                failed_variants.add(call["variant"])
                result["failed_variants"][call["variant"]] = {
                    "call_index": call["call_index"],
                    "error_body": row["raw_response"],
                }
                _write_json(out, result)
    return result


def _print_plan(plan: list[dict[str, Any]], ceiling_usd: float) -> None:
    print(f"{len(plan)} calls; ceiling ${ceiling_usd:.6f}")
    for call in plan:
        print(
            f"{call['call_index']:02d}: {call['variant']} {call['start']} {call['context']} "
            f"sample={call['sample']} ceiling=${call['ceiling_usd']:.6f}"
        )


def _duration_summary(rows: list[dict[str, Any]]) -> str:
    values = [float(row["latency_ms"]) / 1000 for row in rows if isinstance(row.get("latency_ms"), (int, float))]
    if not values:
        return "unknown"
    return f"min {min(values):.3f}s / median {statistics.median(values):.3f}s / max {max(values):.3f}s"


def _report(rows_path: Path, out: Path) -> None:
    document = json.loads(rows_path.read_text(encoding="utf-8"))
    rows = document.get("rows", [])
    lines = ["# Direct Workers AI smoke report", "", f"Planned ceiling: ${document.get('ceiling_usd', 0):.6f}", ""]
    lines.append("## Calls")
    lines.append("")
    for row in rows:
        lines.extend(
            [
                f"### Call {row.get('call_index')} — {row.get('variant')} — {row.get('model')}",
                "",
                f"- Start/context/sample: {row.get('start')} / {row.get('context')} / {row.get('sample')}",
                f"- HTTP status: {row.get('status')}; latency: {float(row.get('latency_ms', 0)) / 1000:.3f}s",
                f"- Final text path: {row.get('final_text_path') or 'none'}; usable: {row.get('usable', False)}",
                f"- Skipped: {row.get('skipped', False)}"
                + (f" ({row.get('error_message')})" if row.get("skipped") else ""),
                f"- Narration: {row.get('narration') or '(unusable)'}",
                "",
            ]
        )
        if not row.get("usable") and row.get("final_text") is not None:
            lines.insert(-1, f"- Raw reply text: {_redact(str(row['final_text']))}")
        if not row.get("usable") and row.get("repair_usable"):
            lines.insert(-1, f"- Repaired reply text: {_redact(str(row['narration_repaired']))}")
    failed_rows = {row["variant"]: row for row in rows if row.get("error_class") == "VARIANT_FAILED"}
    present_variants = tuple(label for label in _VARIANT_ORDER if any(row.get("variant") == label for row in rows))
    if failed_rows:
        lines.extend(["## Failed variants", ""])
        for variant_label in present_variants:
            row = failed_rows.get(variant_label)
            if row is None:
                continue
            lines.extend(
                [
                    f"### {variant_label}",
                    "",
                    "First error body (verbatim):",
                    "",
                    "```text",
                    row.get("raw_response", ""),
                    "```",
                    "",
                ]
            )
    lines.extend(["## Per-variant summary", ""])
    for variant_label in present_variants:
        profile = _PROFILE_BY_LABEL[variant_label]
        variant_rows = [row for row in rows if row.get("variant") == variant_label]
        prompt_tokens = [row["prompt_tokens"] for row in variant_rows if isinstance(row.get("prompt_tokens"), int)]
        completion_tokens = [
            row["completion_tokens"] for row in variant_rows if isinstance(row.get("completion_tokens"), int)
        ]
        costs = [row["actual_cost_usd"] for row in variant_rows if isinstance(row.get("actual_cost_usd"), (int, float))]
        auth_error_rows = sum(1 for row in variant_rows if _error_class(row) is not None)
        shapes = sorted(
            {
                json.dumps(
                    {
                        "top_level_keys": row.get("top_level_keys", []),
                        "result_keys": row.get("result_keys", []),
                        "final_text_path": row.get("final_text_path"),
                        "reasoning_fields": row.get("reasoning_fields", []),
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
                for row in variant_rows
            }
        )
        lines.extend(
            [
                f"### {variant_label} ({profile['model_id']})",
                "",
                *([f"- Note: {profile['note']}"] if profile.get("note") else []),
                f"- Usable: {sum(1 for row in variant_rows if row.get('usable'))} / {len(variant_rows)}",
                f"- Valid JSON: strict {sum(1 for row in variant_rows if row.get('usable'))} / "
                f"{sum(1 for row in variant_rows if row.get('status') is not None)}; after the product's quote repair "
                f"{sum(1 for row in variant_rows if row.get('repair_usable'))} / "
                f"{sum(1 for row in variant_rows if row.get('status') is not None)}",
                f"- Latency: {_duration_summary(variant_rows)}",
                "- Tokens: prompt "
                f"{sum(prompt_tokens) if prompt_tokens else 'unknown'}, "
                f"completion {sum(completion_tokens) if completion_tokens else 'unknown'}",
                f"- Cost: ${sum(costs):.6f}" if costs else "- Cost: unknown",
                f"- Truncated: {sum(1 for row in variant_rows if row.get('truncated'))}",
                f"- Auth/error rows: {auth_error_rows}",
                "- Discovered response shape:",
            ]
        )
        starts = sorted({str(row.get("start")) for row in variant_rows})
        if len(starts) > 1:
            lines.append(
                "- By start: "
                + ", ".join(
                    f"{start} {sum(1 for row in variant_rows if row.get('start') == start and row.get('usable'))}/"
                    f"{sum(1 for row in variant_rows if row.get('start') == start)}"
                    for start in starts
                )
            )
        if shapes:
            lines.extend(f"  - `{shape}`" for shape in shapes)
        else:
            lines.append("  - none")
        lines.append("")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(_redact("\n".join(lines) + "\n"), encoding="utf-8")


def _error(message: str) -> int:
    print(f"environment smoke direct: {_redact(message)}", file=sys.stderr)
    return 2


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--dry", action="store_true")
    modes.add_argument("--run", action="store_true")
    modes.add_argument("--report", action="store_true")
    parser.add_argument("--prompts", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--rows", type=Path)
    parser.add_argument("--confirm", action="store_true")
    parser.add_argument("--max-calls", type=int, default=DEFAULT_MAX_CALLS)
    parser.add_argument("--max-usd", type=float)
    parser.add_argument("--variants", help="comma-separated variant labels")
    parser.add_argument("--slots", choices=tuple(_SLOT_ORDERS), default="original")
    return parser


def _variant_labels(value: str | None) -> tuple[str, ...]:
    if value is None:
        return _DEFAULT_VARIANT_ORDER
    labels = tuple(label.strip() for label in value.split(","))
    seen: set[str] = set()
    for label in labels:
        if label not in _PROFILE_BY_LABEL:
            raise ValueError(f"unknown variant label: {label}")
        if label in seen:
            raise ValueError(f"duplicate variant label: {label}")
        seen.add(label)
    return labels


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.report:
            if args.rows is None:
                return _error("--report requires --rows")
            _report(args.rows, args.out)
            print(f"report: {args.out}")
            return 0
        if args.prompts is None:
            return _error("--dry/--run requires --prompts")
        prompts = _load_prompts(args.prompts)
        plan = _build_plan(prompts, _variant_labels(args.variants), _SLOT_ORDERS[args.slots])
        ceiling_usd = sum(call["ceiling_usd"] for call in plan)
        if args.dry:
            _write_json(args.out, {"schema": 1, "mode": "dry", "calls": plan, "ceiling_usd": ceiling_usd})
            _print_plan(plan, ceiling_usd)
            return 0
        if not args.confirm:
            return _error("live mode requires --confirm")
        if args.max_usd is None:
            return _error("live mode requires --max-usd")
        if args.max_calls < len(plan):
            return _error(f"planned calls {len(plan)} exceed --max-calls {args.max_calls}")
        if ceiling_usd > args.max_usd:
            return _error(f"ceiling ${ceiling_usd:.6f} exceeds --max-usd ${args.max_usd:.6f}")
        account = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "").strip()
        token = os.environ.get("CLOUDFLARE_AI_TOKEN", "").strip() or os.environ.get("CF_API_TOKEN", "").strip()
        if not account or not token:
            return _error("live mode requires CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_AI_TOKEN or CF_API_TOKEN")
        _run(plan, account, token, args.out, ceiling_usd)
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as error:
        return _error(str(error))


if __name__ == "__main__":
    raise SystemExit(main())
