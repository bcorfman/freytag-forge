"""Compare Workers AI JSON-object and JSON-schema response formats."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from scripts.ringer.stage7.narration_only_probe import (
    ANCHOR,
    RULE,
    _is_truncated,
    _make_provider,
    capture_prompts,
    classify_body,
)
from scripts.ringer.stage7.quoted_name_probe import quoted_name_flags
from scripts.ringer.stage7.segment_replay_probe import _worker_payload

ROOT = Path(__file__).resolve().parents[3]
ARMS = ("json_object", "json_schema")
MAX_CALLS = 40


def _schema() -> object:
    from storygame.runtime.cloudflare import _PROVIDER_RESPONSE_SCHEMA

    return _PROVIDER_RESPONSE_SCHEMA


def build_arms(payload: dict[str, object]) -> dict[str, dict[str, object]]:
    system = payload.get("system")
    user = payload.get("user")
    response_format = payload.get("response_format")
    if not isinstance(system, str) or not isinstance(user, str):
        raise AssertionError("dialogue payload must contain string system and user fields")
    if system.count(ANCHOR) != 1:
        raise AssertionError("anchor must occur exactly once in the system string")
    if response_format != {"type": "json_object"}:
        raise AssertionError("captured dialogue payload must use json_object response format")

    shared_system = system.replace(ANCHOR, RULE + "\n" + ANCHOR)
    if shared_system.replace(RULE + "\n", "", 1) != system:
        raise AssertionError("inserted rule changed more than the anchor line")
    object_arm = dict(payload)
    object_arm["system"] = shared_system
    schema_arm = dict(object_arm)
    schema_arm["response_format"] = {"type": "json_schema", "json_schema": _schema()}
    arms = {"json_object": object_arm, "json_schema": schema_arm}
    for name, arm in arms.items():
        if arm["system"] != shared_system or arm["user"] != user:
            raise AssertionError(f"{name} changed the shared prompt")
    object_without_format = {key: value for key, value in object_arm.items() if key != "response_format"}
    schema_without_format = {key: value for key, value in schema_arm.items() if key != "response_format"}
    if object_without_format != schema_without_format:
        raise AssertionError("arms differ outside response_format")
    return arms


def _write_arms(out: Path, arms: dict[str, dict[str, object]]) -> None:
    arm_dir = out / "arms"
    arm_dir.mkdir(parents=True, exist_ok=True)
    for arm in ARMS:
        (arm_dir / f"{arm}.json").write_text(json.dumps(arms[arm], indent=2) + "\n", encoding="utf-8")
    (arm_dir / "schema.json").write_text(json.dumps(_schema(), indent=2) + "\n", encoding="utf-8")


def _empty_row(arm: str, rep: int) -> dict[str, object]:
    return {
        "arm": arm,
        "rep": rep,
        "raw_body": "",
        "http_status": None,
        "error_body": "",
        "http_error_headers": {},
        "error": None,
        "truncated": False,
        "ok": False,
        "invalid_kind": False,
        "stray_selected_ids": False,
        "bad_segments": [],
        "kinds": [],
        "double_quote_any": False,
        "_kept_chars": 0,
    }


def _http_headers(error: HTTPError) -> dict[str, str]:
    headers = error.headers.items() if error.headers is not None else ()
    return {
        key: value
        for key, value in headers
        if any(word in key.lower() for word in ("freytag", "reject", "error", "code"))
    }


def arm_order(rep: int) -> tuple[str, str]:
    return ARMS if rep % 2 == 0 else (ARMS[1], ARMS[0])


def make_summary(rows: list[dict[str, object]], calls: int) -> dict[str, object]:
    per_arm: dict[str, object] = {}
    for arm in ARMS:
        arm_rows = [row for row in rows if row["arm"] == arm]
        valid_chars = [row["_kept_chars"] for row in arm_rows if row["ok"]]
        bodies = Counter(
            row["error_body"][:200] for row in arm_rows if row["http_status"] is not None and row["error_body"]
        )
        per_arm[arm] = {
            "rows": len(arm_rows),
            "ok": sum(bool(row["ok"]) for row in arm_rows),
            "bad_rows": sum(not bool(row["ok"]) for row in arm_rows),
            "truncated": sum(bool(row["truncated"]) for row in arm_rows),
            "invalid_kind": sum(bool(row["invalid_kind"]) for row in arm_rows),
            "double_quote_any": sum(bool(row["double_quote_any"]) for row in arm_rows),
            "http_errors": sum(row["http_status"] is not None for row in arm_rows),
            "other_errors": sum(row["error"] is not None for row in arm_rows),
            "mean_kept_chars": sum(valid_chars) / len(valid_chars) if valid_chars else 0,
            "distinct_http_error_bodies": dict(bodies),
        }
    return {"calls": calls, **per_arm}


def replay(arms: dict[str, dict[str, object]], n: int, out: Path, sender=urlopen) -> dict[str, object]:
    from storygame.runtime.cloudflare import BROWSER_USER_AGENT

    url = os.environ["CLOUDFLARE_WORKER_URL"]
    token = os.environ.get("CLOUDFLARE_WORKER_TOKEN", "")
    provider = _make_provider()
    (out / "bad").mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []
    calls = 0
    consecutive_schema_http_errors = 0
    stopped = False
    with (out / "replies.jsonl").open("w", encoding="utf-8") as reply_file:
        for rep in range(n):
            rep_schema_http_error = False
            for arm in arm_order(rep):
                if calls >= MAX_CALLS:
                    stopped = True
                    break
                calls += 1
                row = _empty_row(arm, rep)
                try:
                    headers = {"Content-Type": "application/json", "User-Agent": BROWSER_USER_AGENT}
                    if token:
                        headers["Authorization"] = f"Bearer {token}"
                    request = Request(url, data=json.dumps(arms[arm]).encode(), headers=headers, method="POST")
                    with sender(request, timeout=60) as response:
                        row["raw_body"] = response.read().decode()
                    row["truncated"] = _is_truncated(row["raw_body"])
                    row.update(classify_body(row["raw_body"], provider))
                    _, row["double_quote_any"], row["_kept_chars"] = quoted_name_flags(row["raw_body"], provider)
                    parsed = _worker_payload(row["raw_body"], provider)
                    segments = parsed.get("segments", []) if isinstance(parsed, dict) else []
                    row["kinds"] = [
                        segment.get("kind")
                        for segment in segments
                        if isinstance(segment, dict) and isinstance(segment.get("kind"), str)
                    ]
                except HTTPError as error:
                    body = error.read().decode()
                    row["http_status"] = error.code
                    row["error_body"] = body
                    row["http_error_headers"] = _http_headers(error)
                    if arm == "json_schema":
                        rep_schema_http_error = True
                except Exception as error:  # noqa: BLE001 - preserve each row and continue
                    row["error"] = f"{type(error).__name__}: {error}"
                public_row = {key: value for key, value in row.items() if not key.startswith("_")}
                reply_file.write(json.dumps(public_row, separators=(",", ":")) + "\n")
                rows.append(row)
                if not row["ok"] or row["truncated"] or row["http_status"] is not None or row["error"]:
                    (out / "bad" / f"{arm}-{rep}.txt").write_text(
                        str(row["error_body"] or row["raw_body"] or row["error"] or ""), encoding="utf-8"
                    )
            if stopped:
                break
            consecutive_schema_http_errors = consecutive_schema_http_errors + 1 if rep_schema_http_error else 0
            if consecutive_schema_http_errors >= 3:
                stopped = True
                (out / "run-stopped.txt").write_text(
                    "Stopped after the json_schema arm returned HTTP errors on three consecutive reps.\n",
                    encoding="utf-8",
                )
                break
    return make_summary(rows, calls)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--confirm", action="store_true")
    args = parser.parse_args()
    if args.n < 1:
        parser.error("--n must be at least 1")
    if args.n > 20:
        parser.error("refusing --n over 20")
    if not args.dry_run and not args.confirm:
        parser.error("live replay requires --confirm (or use --dry-run)")
    return args


def main() -> None:
    args = parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    prompts = capture_prompts(args.out)
    arms = build_arms(prompts["dialogue"])
    _write_arms(args.out, arms)
    summary = make_summary([], 0) if args.dry_run else replay(arms, args.n, args.out)
    args.out.joinpath("summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    if args.dry_run:
        args.out.joinpath("notes.md").write_text(
            "This offline dry run captured only the dialogue prompt. Both arms share one system and user prompt; "
            "they differ only in response_format, with the schema copied to arms/schema.json. No Worker request, "
            "credential, or billed call was used.\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))
    main()
