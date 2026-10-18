"""Replay the stage-7 dialogue prompt with a narration-only system rule."""

from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path
from urllib.request import Request, urlopen

from scripts.ringer.stage7.segment_replay_probe import _worker_payload, capture_prompts
from scripts.ringer.stage7.segment_replay_probe import classify_body as _classify_body

ROOT = Path(__file__).resolve().parents[3]
ANCHOR = "Write each paragraph as one segment and return only JSON in this form:"
RULE = (
    "Every paragraph uses the kind narration. Put spoken words inside the paragraph, in quotation marks. "
    "Do not use any other kind."
)
SINGLE_QUOTE_RULE = (
    "Every paragraph uses the kind narration. Put spoken words inside the paragraph, in single quotation marks. "
    "Do not use any other kind."
)
ARMS = ("control", "narration_only", "single_quote")
KINDS = {"narration", "dialogue", "action"}
MAX_CALLS = 60


def build_arms(payload: dict[str, object]) -> dict[str, dict[str, object]]:
    system = payload.get("system")
    user = payload.get("user")
    if not isinstance(system, str) or not isinstance(user, str):
        raise AssertionError("dialogue payload must contain string system and user fields")
    if system.count(ANCHOR) != 1:
        raise AssertionError("anchor must occur exactly once in the system string")
    control = dict(payload)
    arms = {"control": control}
    for name, rule in (("narration_only", RULE), ("single_quote", SINGLE_QUOTE_RULE)):
        arm = dict(payload)
        arm["system"] = system.replace(ANCHOR, rule + "\n" + ANCHOR)
        if arm["system"].replace(rule + "\n", "", 1) != control["system"]:
            raise AssertionError(f"{name} system differs by more than the inserted rule")
        if control["user"] != arm["user"]:
            raise AssertionError(f"{name} user string differs")
        arms[name] = arm
    return arms


def _segment_texts(raw_body: str, provider: object) -> list[str]:
    payload = _worker_payload(raw_body, provider)
    segments = payload.get("segments") if isinstance(payload, dict) else None
    if not isinstance(segments, list):
        return []
    return [
        segment["text"] for segment in segments if isinstance(segment, dict) and isinstance(segment.get("text"), str)
    ]


def classify_body(raw_body: str, provider: object) -> dict[str, object]:
    result = _classify_body(raw_body, provider)
    try:
        texts = _segment_texts(raw_body, provider)
    except Exception:
        texts = []
    result["kinds"] = []
    try:
        payload = _worker_payload(raw_body, provider)
        segments = payload.get("segments") if isinstance(payload, dict) else []
        result["kinds"] = [
            segment.get("kind")
            for segment in segments
            if isinstance(segment, dict) and isinstance(segment.get("kind"), str)
        ]
    except Exception:
        pass
    result["speech_visible"] = any(
        '"' in text or "“" in text or "”" in text or re.search(r"'[^']+'", text) for text in texts
    )
    result["brandon_named"] = any("Brandon" in text for text in texts)
    return result


def _is_truncated(raw_body: str) -> bool:
    try:
        body = json.loads(raw_body)
    except Exception:
        return False
    narration = body.get("narration") if isinstance(body, dict) else None
    if not isinstance(narration, str):
        return False
    try:
        json.loads(narration)
    except json.JSONDecodeError:
        return True
    return False


def _make_provider() -> object:
    from bench.core import load_variation, package_and_state
    from storygame.runtime.cloudflare import CloudflareTurnProvider

    variation = ROOT / "bench/variations/stage7-door-grounded.json"
    _, state = package_and_state(load_variation(variation), "2B")
    return CloudflareTurnProvider(worker_url="", token="", state=state)


def _write_arms(out: Path, arms: dict[str, dict[str, object]]) -> None:
    arm_dir = out / "arms"
    arm_dir.mkdir(parents=True, exist_ok=True)
    for name, payload in arms.items():
        arm_dir.joinpath(f"{name}.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    diffs = []
    for name in ARMS[1:]:
        diffs.append(
            "".join(
                difflib.unified_diff(
                    arms["control"]["system"].splitlines(keepends=True),
                    arms[name]["system"].splitlines(keepends=True),
                    fromfile="control.system",
                    tofile=f"{name}.system",
                )
            )
        )
    arm_dir.joinpath("system.diff").write_text("\n".join(diffs), encoding="utf-8")


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
        "speech_visible": False,
        "brandon_named": False,
        "truncated": False,
    }


def make_summary(rows: list[dict[str, object]], calls: int) -> dict[str, object]:
    per_arm: dict[str, object] = {}
    for arm in ARMS:
        arm_rows = [row for row in rows if row["arm"] == arm]
        kind_counts = Counter(kind for row in arm_rows for kind in row.get("kinds", []))
        per_arm[arm] = {
            "rows": len(arm_rows),
            "ok": sum(bool(row["ok"]) for row in arm_rows),
            "bad_rows": sum(not bool(row["ok"]) for row in arm_rows),
            "invalid_kind": sum(bool(row["invalid_kind"]) for row in arm_rows),
            "errors": sum(row["error"] is not None for row in arm_rows),
            "rows_with_any_non_narration_kind": sum(
                any(kind != "narration" for kind in row["kinds"]) for row in arm_rows
            ),
            "speech_visible": sum(bool(row["speech_visible"]) for row in arm_rows),
            "truncated": sum(bool(row["truncated"]) for row in arm_rows),
            "distinct_kinds": dict(sorted(kind_counts.items())),
        }
    return {"calls": calls, **per_arm}


def arm_order(rep: int) -> tuple[str, ...]:
    shift = rep % len(ARMS)
    return ARMS[shift:] + ARMS[:shift]


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
            order = arm_order(rep)
            for arm in order:
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
                    row.update(classify_body(row["raw_body"], provider))
                except Exception as error:  # noqa: BLE001
                    row["error"] = f"{type(error).__name__}: {error}"
                reply_file.write(json.dumps(row, separators=(",", ":")) + "\n")
                rows.append(row)
                if not row["ok"]:
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
            "This dry run captured the dialogue prompt and wrote control, narration-only, and single-quote arms.\n"
            "The arms share an identical user string. Each non-control system adds one rule immediately "
            "before the JSON anchor.\n"
            "No worker requests were made, and no credentials were read.\n",
            encoding="utf-8",
        )
    else:
        summary = replay(arms, args.n, args.out)
    args.out.joinpath("summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))
    main()
