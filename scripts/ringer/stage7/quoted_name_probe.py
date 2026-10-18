"""Replay the dialogue prompt with rules for quoting program names."""

from __future__ import annotations

import argparse
import difflib
import json
import os
import re
from collections import Counter
from pathlib import Path
from urllib.request import Request, urlopen

from scripts.ringer.stage7.narration_only_probe import (
    ANCHOR,
    RULE,
    _is_truncated,
    _make_provider,
    capture_prompts,
)
from scripts.ringer.stage7.narration_only_probe import classify_body as _classify_body
from scripts.ringer.stage7.segment_replay_probe import _worker_payload

MAX_CALLS = 60
ARMS = ("rule", "no_name_quotes", "speech_only")
NO_NAME_QUOTES = "Write names and titles with no quotation marks."
SPEECH_ONLY = "Use quotation marks only around spoken words."


def build_arms(payload: dict[str, object]) -> dict[str, dict[str, object]]:
    system = payload.get("system")
    user = payload.get("user")
    if not isinstance(system, str) or not isinstance(user, str):
        raise AssertionError("dialogue payload must contain string system and user fields")
    if system.count(ANCHOR) != 1:
        raise AssertionError("anchor must occur exactly once in the system string")
    arms: dict[str, dict[str, object]] = {}
    additions = {
        "rule": (RULE,),
        "no_name_quotes": (RULE, NO_NAME_QUOTES),
        "speech_only": (RULE, SPEECH_ONLY),
    }
    for name, lines in additions.items():
        arm = dict(payload)
        inserted = "\n".join((*lines, ANCHOR))
        arm["system"] = system.replace(ANCHOR, inserted)
        if arm["system"].replace("\n".join(lines) + "\n", "", 1) != system:
            raise AssertionError(f"{name} system differs by more than its inserted lines")
        if arm["user"] != user:
            raise AssertionError(f"{name} user string differs")
        arms[name] = arm
    return arms


def arm_order(rep: int) -> tuple[str, ...]:
    shift = rep % len(ARMS)
    return ARMS[shift:] + ARMS[:shift]


def _write_arms(out: Path, arms: dict[str, dict[str, object]]) -> None:
    arm_dir = out / "arms"
    arm_dir.mkdir(parents=True, exist_ok=True)
    for name in ARMS:
        arm_dir.joinpath(f"{name}.json").write_text(json.dumps(arms[name], indent=2) + "\n", encoding="utf-8")

    baseline_system = str(arms["rule"]["system"]).replace(RULE + "\n", "", 1)
    diffs = []
    for name in ARMS:
        diffs.append(
            "".join(
                difflib.unified_diff(
                    baseline_system.splitlines(keepends=True),
                    str(arms[name]["system"]).splitlines(keepends=True),
                    fromfile="baseline.system",
                    tofile=f"{name}.system",
                )
            )
        )
    arm_dir.joinpath("system.diff").write_text("\n".join(diffs), encoding="utf-8")


def _segment_texts(raw_body: str, provider: object) -> list[str]:
    payload = _worker_payload(raw_body, provider)
    segments = payload.get("segments") if isinstance(payload, dict) else None
    if not isinstance(segments, list):
        return []
    return [
        segment["text"] for segment in segments if isinstance(segment, dict) and isinstance(segment.get("text"), str)
    ]


def quoted_name_flags(raw_body: str, provider: object) -> tuple[bool, bool, int]:
    """Inspect repaired segment text; a name quote is a quote after space/called/named/known as."""
    try:
        texts = _segment_texts(raw_body, provider)
    except Exception:
        return False, False, 0
    joined = "\n".join(texts)
    quoted_name = bool(re.search(r"(?:\s|called|named|known as)\"", joined))
    return quoted_name, '"' in joined, sum(len(text) for text in texts)


def _empty_row(arm: str, rep: int) -> dict[str, object]:
    return {
        "arm": arm,
        "rep": rep,
        "raw_body": "",
        "error": None,
        "ok": False,
        "invalid_kind": False,
        "stray_selected_ids": False,
        "bad_segments": [],
        "kinds": [],
        "truncated": False,
        "quoted_name": False,
        "double_quote_any": False,
        "_kept_chars": 0,
    }


def make_summary(rows: list[dict[str, object]], calls: int) -> dict[str, object]:
    per_arm: dict[str, object] = {}
    for arm in ARMS:
        arm_rows = [row for row in rows if row["arm"] == arm]
        valid = [row["_kept_chars"] for row in arm_rows if row["ok"]]
        kind_counts = Counter(kind for row in arm_rows for kind in row.get("kinds", []))
        per_arm[arm] = {
            "rows": len(arm_rows),
            "ok": sum(bool(row["ok"]) for row in arm_rows),
            "bad_rows": sum(not bool(row["ok"]) for row in arm_rows),
            "truncated": sum(bool(row["truncated"]) for row in arm_rows),
            "invalid_kind": sum(bool(row["invalid_kind"]) for row in arm_rows),
            "quoted_name": sum(bool(row["quoted_name"]) for row in arm_rows),
            "double_quote_any": sum(bool(row["double_quote_any"]) for row in arm_rows),
            "errors": sum(row["error"] is not None for row in arm_rows),
            "mean_kept_chars": sum(valid) / len(valid) if valid else 0,
            "distinct_kinds": dict(sorted(kind_counts.items())),
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
    with (out / "replies.jsonl").open("w", encoding="utf-8") as reply_file:
        for rep in range(n):
            for arm in arm_order(rep):
                if calls >= MAX_CALLS:
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
                    row.update(_classify_body(row["raw_body"], provider))
                    row["quoted_name"], row["double_quote_any"], row["_kept_chars"] = quoted_name_flags(
                        row["raw_body"], provider
                    )
                except Exception as error:  # noqa: BLE001 - continue collecting evidence
                    row["error"] = f"{type(error).__name__}: {error}"
                public_row = {k: v for k, v in row.items() if not k.startswith("_")}
                reply_file.write(json.dumps(public_row, separators=(",", ":")) + "\n")
                rows.append(row)
                if not row["ok"] or row["truncated"]:
                    (out / "bad" / f"{arm}-{rep}.txt").write_text(str(row["raw_body"]), encoding="utf-8")
            if calls >= MAX_CALLS:
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
    if args.dry_run:
        summary = make_summary([], 0)
        args.out.joinpath("notes.md").write_text(
            "This dry run captured only the dialogue prompt and wrote three quote-handling arms.\n"
            "Each arm inserts its requested lines immediately before the JSON anchor; users remain identical.\n"
            "The system diff compares every arm with the unmodified baseline. No worker requests or credentials "
            "were used.\n",
            encoding="utf-8",
        )
    else:
        summary = replay(arms, args.n, args.out)
    args.out.joinpath("summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
