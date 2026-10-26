"""Confirmed, no-JSON-mode smoke harness for the two item-facts classifiers."""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from scripts.ringer.environment_narration import baseline, smoke_direct
from storygame.runtime import item_facts as item_facts_module
from storygame.runtime.cloudflare import BROWSER_USER_AGENT, CloudflareTurnProvider
from storygame.runtime.item_facts import ItemFactsProvider
from storygame.story_package.loader import load_story_package

ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = ROOT / "data/stories/continuity-initiative"
HISTORICAL_ROWS = ROOT / "bench/results/environment-narration/smoke-nojsonwide-rows.json"
API_URL = "https://api.cloudflare.com/client/v4/accounts/{account}/ai/run/{model}"
MODEL = "@cf/meta/llama-3.3-70b-instruct-fp8-fast"
INPUT_PRICE = 0.293
OUTPUT_PRICE = 2.253
SAMPLES = 5
MATCH_MAX_TOKENS = 300
SECOND_MAX_TOKENS = 400
FALLBACK_STORIES = {
    "laptop": "The laptop moves to the passenger seat.",
    "drawer": "The drawer opens in the kitchen.",
    "unchanged": "Nothing changes; the room remains as it was.",
}
_credential_values = smoke_direct._credential_values


def _write_json(path: Path, value: Any) -> None:
    smoke_direct._write_json(path, value)


def _redact(value: str) -> str:
    return smoke_direct._redact(value)


def _input_tokens(system: str, user: str) -> int:
    return (len((system + user).encode("utf-8")) + 2) // 3


def _ceiling(system: str, user: str, max_tokens: int) -> tuple[int, float]:
    input_tokens = _input_tokens(system, user)
    return input_tokens, (input_tokens * INPUT_PRICE + max_tokens * OUTPUT_PRICE) / 1_000_000


def _story_from_reply(value: str) -> str | None:
    try:
        decoded = json.loads(value)
    except json.JSONDecodeError:
        return None
    if not isinstance(decoded, dict):
        return None
    segments = decoded.get("segments")
    if not isinstance(segments, list):
        return None
    parts = [
        segment["text"]
        for segment in segments
        if isinstance(segment, dict) and isinstance(segment.get("text"), str) and segment["text"].strip()
    ]
    return " ".join(parts) if parts else None


def _historical_stories() -> dict[str, str]:
    if HISTORICAL_ROWS.is_file():
        try:
            document = json.loads(HISTORICAL_ROWS.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            document = None
        candidates: list[str] = []
        rows = document.get("rows", []) if isinstance(document, dict) else []
        if isinstance(rows, list):
            for row in rows:
                if not isinstance(row, dict):
                    continue
                for key in ("narration_repaired", "narration"):
                    text = row.get(key)
                    if isinstance(text, str) and text.strip():
                        candidates.append(text)
                final_text = row.get("final_text")
                if isinstance(final_text, str):
                    story = _story_from_reply(final_text)
                    if story:
                        candidates.append(story)
        laptop = next((text for text in candidates if "laptop" in text.casefold()), None)
        drawer = next((text for text in candidates if "drawer" in text.casefold()), None)
        unchanged = next(
            (text for text in candidates if "laptop" not in text.casefold() and "drawer" not in text.casefold()),
            None,
        )
        if laptop and drawer and unchanged:
            return {"laptop": laptop, "drawer": drawer, "unchanged": unchanged}
    return dict(FALLBACK_STORIES)


def _provider(package: Any, boarding_probe: Any, place: str) -> ItemFactsProvider:
    from storygame.runtime.capture import build_capture_provider

    state = boarding_probe._state_at(package, place)
    provider = build_capture_provider(state)
    provider.observe_automatically = False
    return provider


def _name_with(names: list[str], word: str) -> str:
    match = next((name for name in names if word in name.casefold()), None)
    if match is None:
        raise ValueError(f"real package has no offered thing containing {word!r}")
    return match


def _matcher_case(provider: ItemFactsProvider, case_id: str, command: str, word: str | None) -> dict[str, Any]:
    payload = provider._match_payload(command, [])
    offered = sorted(provider._match_offered_names)
    expected: dict[str, Any] = {"offered_names": offered, "must_include": _name_with(offered, word) if word else None}
    return {
        "id": case_id,
        "kind": "matcher",
        "command": command,
        "system": payload["system"],
        "user": payload["user"],
        "max_tokens": MATCH_MAX_TOKENS,
        "expected": expected,
    }


def _second_case(
    provider: ItemFactsProvider,
    case_id: str,
    command: str,
    story: str,
    word: str | None,
) -> dict[str, Any]:
    things = provider._things_block()
    offered = sorted(provider.item_facts)
    changed = _name_with(offered, word) if word else None
    return {
        "id": case_id,
        "kind": "second_call",
        "command": command,
        "narration": story,
        "system": item_facts_module._SECOND_CALL_SYSTEM,
        "user": f"{things}\n\nPLAYER:\n- {command}\n\nSTORY:\n{story}",
        "max_tokens": SECOND_MAX_TOKENS,
        "expected": {"offered_names": offered, "changed": changed},
    }


def _build_cases() -> list[dict[str, Any]]:
    os.environ.setdefault("CLOUDFLARE_WORKER_URL", "https://worker.example/turn")
    package = load_story_package(PACKAGE_ROOT)
    boarding_probe = baseline._load_boarding_probe()
    stories = _historical_stories()
    with baseline._stubs(lambda _state, questions: {key: {"noul": 0.0} for key in questions}):
        matcher_specs = (
            ("match_truck", "outside_house", "Enter the truck.", "truck"),
            ("match_laptop", "outside_house", "Examine my laptop.", "laptop"),
            ("match_drawer", "kitchen", "Open the drawer.", "drawer"),
            ("match_look_around", "outside_house", "Look around.", None),
        )
        matcher_cases = [
            _matcher_case(_provider(package, boarding_probe, place), case_id, command, word)
            for case_id, place, command, word in matcher_specs
        ]
        second_specs = (
            ("second_laptop", "outside_house", "Examine my laptop.", stories["laptop"], "laptop"),
            ("second_drawer", "kitchen", "Open the drawer.", stories["drawer"], "drawer"),
            ("second_unchanged", "outside_house", "Look around.", stories["unchanged"], None),
        )
        second_cases = [
            _second_case(_provider(package, boarding_probe, place), case_id, command, story, word)
            for case_id, place, command, story, word in second_specs
        ]
    return matcher_cases + second_cases


def _build_plan() -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []
    call_index = 1
    for case in _build_cases():
        for sample in range(SAMPLES):
            input_tokens, ceiling_usd = _ceiling(case["system"], case["user"], case["max_tokens"])
            calls.append(
                {
                    **case,
                    "call_index": call_index,
                    "sample": sample,
                    "model": MODEL,
                    "input_tokens_estimate": input_tokens,
                    "ceiling_usd": ceiling_usd,
                }
            )
            call_index += 1
    return calls


def _request_body(call: dict[str, Any]) -> dict[str, Any]:
    return {
        "messages": [
            {"role": "system", "content": call["system"]},
            {"role": "user", "content": call["user"]},
        ],
        "max_tokens": call["max_tokens"],
    }


def _json_object(text: str | None) -> dict[str, Any] | None:
    if not isinstance(text, str):
        return None
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def _product_decode(text: str | None) -> Any:
    if not isinstance(text, str):
        return None
    provider = object.__new__(CloudflareTurnProvider)
    provider.worker_url = "https://worker.example/turn"
    provider._record_recovery = lambda: None
    try:
        return CloudflareTurnProvider._decode_narration(provider, text)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None


def _names_in_matcher(decoded: dict[str, Any]) -> list[str]:
    names: list[str] = []
    refers = decoded.get("refers")
    if isinstance(refers, list):
        names.extend(name for name in refers if isinstance(name, str))
    same_as = decoded.get("same_as")
    if isinstance(same_as, dict):
        names.extend(name for name in same_as if isinstance(name, str))
        names.extend(name for name in same_as.values() if isinstance(name, str) and name != "new")
    return names


def _shape_and_correct(kind: str, decoded: Any, expected: dict[str, Any]) -> tuple[bool, bool]:
    if not isinstance(decoded, dict):
        return False, False
    if kind == "matcher":
        refers = decoded.get("refers")
        same_as = decoded.get("same_as")
        shape_valid = (
            isinstance(refers, list) and all(isinstance(name, str) for name in refers) and isinstance(same_as, dict)
        )
        offered = {name.casefold() for name in expected.get("offered_names", [])}
        names_ok = all(name.casefold() in offered for name in _names_in_matcher(decoded))
        must_include = expected.get("must_include")
        includes = must_include is None or any(
            isinstance(name, str) and name.casefold() == must_include.casefold() for name in refers or []
        )
        return shape_valid and names_ok, shape_valid and names_ok and includes
    item_facts = decoded.get("item_facts")
    shape_valid = isinstance(item_facts, dict)
    if shape_valid:
        for name, facts in item_facts.items():
            if not isinstance(name, str) or not isinstance(facts, dict):
                shape_valid = False
                break
            if "place" in facts and not isinstance(facts["place"], str):
                shape_valid = False
                break
            if "condition" in facts and not (
                isinstance(facts["condition"], list) and all(isinstance(item, str) for item in facts["condition"])
            ):
                shape_valid = False
                break
    changed = expected.get("changed")
    if changed is None:
        return shape_valid, shape_valid and item_facts == {}
    matching = (
        [facts for name, facts in item_facts.items() if isinstance(name, str) and name.casefold() == changed.casefold()]
        if isinstance(item_facts, dict)
        else []
    )
    correct = bool(matching and isinstance(matching[0].get("place"), str) and matching[0]["place"].strip())
    return shape_valid, shape_valid and correct


def score_reply(kind: str, text: str | None, expected: dict[str, Any]) -> dict[str, Any]:
    strict = _json_object(text)
    decoded = _product_decode(text)
    shape_valid, correct = _shape_and_correct(kind, decoded, expected)
    return {
        "strict_valid": strict is not None,
        "product_decoded": isinstance(decoded, dict),
        "shape_valid": shape_valid,
        "correct": correct,
        "decoded": decoded,
    }


_score_reply = score_reply


def _extract_reply(outer: dict[str, Any] | None) -> tuple[str | None, str | None]:
    if not isinstance(outer, dict):
        return None, None
    result = outer.get("result")
    if isinstance(result, dict):
        if isinstance(result.get("response"), str):
            return result["response"], result.get("model") or result.get("response_model")
        choices = result.get("choices")
        if isinstance(choices, list) and choices and isinstance(choices[0], dict):
            message = choices[0].get("message")
            if isinstance(message, dict) and isinstance(message.get("content"), str):
                return message["content"], result.get("model") or result.get("response_model")
    return None, outer.get("model") if isinstance(outer.get("model"), str) else None


def _call(account: str, token: str, call: dict[str, Any]) -> dict[str, Any]:
    body = _request_body(call)
    request_bytes = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    call["request_bytes"] = len(request_bytes)
    request = Request(
        API_URL.format(account=account, model=MODEL),
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
        raw_bytes = smoke_direct._read_http_error(error)
        status = int(error.code)
    except Exception as error:  # one answered attempt, never a retry
        raw_text = _redact(f"{type(error).__name__}: {error}")
        return {
            "status": None,
            "latency_ms": round((time.perf_counter() - started) * 1000, 3),
            "raw_response": raw_text,
            "raw_reply": None,
            "usage": None,
            "prompt_tokens": None,
            "completion_tokens": None,
            "response_model": None,
        }
    raw_text = _redact(raw_bytes.decode("utf-8", errors="replace"))
    outer = _json_object(raw_text)
    result = outer.get("result") if isinstance(outer, dict) and isinstance(outer.get("result"), dict) else None
    raw_reply, response_model = _extract_reply(outer)
    usage, prompt_tokens, completion_tokens = smoke_direct._usage_and_tokens(outer, result)
    return {
        "status": status,
        "latency_ms": round((time.perf_counter() - started) * 1000, 3),
        "raw_response": raw_text,
        "raw_reply": _redact(raw_reply) if raw_reply is not None else None,
        "usage": usage,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "response_model": response_model,
    }


def _stop_reason(row: dict[str, Any]) -> str | None:
    status = row.get("status")
    if status == 401:
        return "AUTH"
    if status == 429:
        text = str(row.get("raw_response") or "")
        for code in ("AI_QUOTA_EXCEEDED", "AI_DAILY_BUDGET_EXCEEDED"):
            if code in text:
                return code
        return "QUOTA"
    return None


def _run(plan: list[dict[str, Any]], account: str, token: str, out: Path, ceiling_usd: float) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    stop_reason = None
    for call in plan:
        response = _call(account, token, call)
        row = {key: value for key, value in call.items() if key not in {"system", "user"}}
        row.update(response)
        row["raw_reply"] = _redact(row.get("raw_reply")) if isinstance(row.get("raw_reply"), str) else None
        score = score_reply(call["kind"], row["raw_reply"], call["expected"])
        row.update({key: value for key, value in score.items() if key != "decoded"})
        row.pop("decoded", None)
        rows.append(row)
        stop_reason = _stop_reason(row)
        document = {"schema": 1, "mode": "run", "model": MODEL, "ceiling_usd": ceiling_usd, "rows": rows}
        document["stop_reason"] = stop_reason
        _write_json(out, document)
        if stop_reason:
            break
    return document


def _report(rows_path: Path, out: Path) -> None:
    document = json.loads(rows_path.read_text(encoding="utf-8"))
    rows = document.get("rows", [])
    lines = [
        "# Environment classifier smoke report",
        "",
        f"Planned ceiling: ${float(document.get('ceiling_usd', 0)):.6f}",
        "",
    ]
    for row in rows:
        prompt = row.get("command") if row.get("kind") == "matcher" else row.get("narration")
        expected = json.dumps(row.get("expected", {}), ensure_ascii=False, sort_keys=True)
        raw = row.get("raw_reply")
        lines.extend(
            [
                f"## Call {row.get('call_index')} — {row.get('kind')}",
                f"- Command or narration: {prompt}",
                f"- Expected: {expected}",
                f"- Raw reply text: {raw if raw is not None else '(none)'}",
                f"- strict-valid: {row.get('strict_valid', False)}",
                f"- product-decoded: {row.get('product_decoded', False)}",
                f"- shape-valid: {row.get('shape_valid', False)}",
                f"- correct: {row.get('correct', False)}",
                f"- Latency: {float(row.get('latency_ms', 0)) / 1000:.3f}s",
                f"- Usage tokens: prompt={row.get('prompt_tokens')}, completion={row.get('completion_tokens')}",
                f"- Response model: {row.get('response_model')}",
                "",
            ]
        )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(_redact("\n".join(lines) + "\n"), encoding="utf-8")


def _print_plan(plan: list[dict[str, Any]], ceiling_usd: float) -> None:
    input_tokens = sum(call["input_tokens_estimate"] for call in plan)
    print(f"{len(plan)} calls; input token estimate {input_tokens}; ceiling ${ceiling_usd:.6f}")
    for call in plan:
        label = call["command"] if call["kind"] == "matcher" else call["narration"]
        print(
            f"{call['call_index']:02d}: {call['kind']} sample={call['sample']} "
            f"input_tokens≈{call['input_tokens_estimate']} {label} ceiling=${call['ceiling_usd']:.6f}"
        )


def _error(message: str) -> int:
    print(_redact(f"error: {message}"), file=__import__("sys").stderr)
    return 2


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry", action="store_true")
    mode.add_argument("--run", action="store_true")
    mode.add_argument("--report", action="store_true")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--rows", type=Path)
    parser.add_argument("--confirm", action="store_true")
    parser.add_argument("--max-calls", type=int)
    parser.add_argument("--max-usd", type=float)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.report:
            if args.rows is None:
                return _error("--report requires --rows")
            _report(args.rows, args.out)
            print(f"report: {args.out}")
            return 0
        plan = _build_plan()
        ceiling_usd = sum(call["ceiling_usd"] for call in plan)
        if args.dry:
            _write_json(
                args.out,
                {"schema": 1, "mode": "dry", "model": MODEL, "calls": plan, "ceiling_usd": ceiling_usd},
            )
            _print_plan(plan, ceiling_usd)
            return 0
        if not args.confirm:
            return _error("live mode requires --confirm")
        if args.max_calls is None:
            return _error("live mode requires --max-calls")
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
