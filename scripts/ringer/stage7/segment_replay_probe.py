"""Capture and replay Stage 7 narrator prompts to find malformed segments."""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path
from urllib.request import Request, urlopen

from bench.core import load_variation, package_and_state, provider_for
from storygame.runtime.contracts import NarrationSegment
from storygame.runtime.engine import RuntimeEngine

ROOT = Path(__file__).resolve().parents[3]
VARIATION = ROOT / "bench/variations/stage7-door-grounded.json"
CELLS = {
    "reveal": "Search the selection files for Michelle's file.",
    "dialogue": "Ask Brandon what he remembers about the program.",
    "plain": "Look around the archive.",
}
KINDS = {"narration", "dialogue", "action"}
MAX_CALLS = 60


class _Response:
    def __init__(self, body: object) -> None:
        self.body = json.dumps(body).encode()

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def read(self) -> bytes:
        return self.body


def _valid_reply() -> dict[str, str]:
    return {"narration": '{"segments":[{"kind":"narration","text":"The archive waits."}]}'}


def capture_prompts(out: Path) -> dict[str, dict[str, object]]:
    prompts: dict[str, dict[str, object]] = {}
    out.joinpath("prompts").mkdir(parents=True, exist_ok=True)
    # provider_for constructs the environment-backed provider, but the URL is never
    # contacted: urlopen is replaced before the engine turn below.
    os.environ.setdefault("CLOUDFLARE_WORKER_URL", "https://offline.invalid")
    for cell, command in CELLS.items():
        _, state = package_and_state(load_variation(VARIATION), "2B")
        provider = provider_for(state, load_variation(VARIATION))
        provider.semantic_ask = None
        captured: dict[str, object] = {}

        def open_request(request: Request, timeout: float, captured: dict[str, object] = captured) -> _Response:
            captured.update(json.loads(request.data))
            return _Response(_valid_reply())

        import storygame.runtime.cloudflare as cloudflare

        original = cloudflare.urlopen
        cloudflare.urlopen = open_request
        try:
            RuntimeEngine(state, provider).turn(command)
        finally:
            cloudflare.urlopen = original
        if not captured:
            raise RuntimeError(f"no worker payload captured for {cell}")
        if cell == "reveal":
            handoff = provider.authored_handoff
            if handoff is None or handoff.candidate.id != "k_sl_2b_a_r1":
                raise RuntimeError("reveal command did not stage k_sl_2b_a_r1")
        prompts[cell] = captured
        out.joinpath("prompts", f"{cell}.json").write_text(json.dumps(captured, indent=2) + "\n", encoding="utf-8")
    return prompts


def _worker_payload(raw_body: str, provider: object) -> object:
    body = json.loads(raw_body)
    if isinstance(body, dict) and body.get("status") == "error":
        raise ValueError(str(body.get("message", "narration service failed")))
    if isinstance(body, dict) and isinstance(body.get("narration"), str):
        body = provider._decode_narration(body["narration"])
    return provider._clean_reply(body)


def classify_body(raw_body: str, provider: object) -> dict[str, object]:
    result: dict[str, object] = {
        "ok": False,
        "bad_segments": [],
        "stray_selected_ids": False,
        "invalid_kind": False,
        "error": None,
    }
    try:
        payload = _worker_payload(raw_body, provider)
        if not isinstance(payload, dict) or not isinstance(payload.get("segments"), list):
            raise ValueError("reply has no segments list")
        selected = payload.get("selected_knowledge_ids", [])
        if not isinstance(selected, list) or any(not isinstance(item, str) for item in selected):
            raise ValueError("selected_knowledge_ids is not a list of strings")
        bad: list[dict[str, object]] = []
        for index, segment in enumerate(payload["segments"]):
            error_types: list[str] = []
            if isinstance(segment, dict) and set(segment) == {"selected_knowledge_ids"}:
                result["stray_selected_ids"] = True
            try:
                NarrationSegment.model_validate(segment)
            except Exception as error:  # noqa: BLE001 - classify untrusted worker data
                error_types.append(type(error).__name__)
                if isinstance(segment, dict) and isinstance(segment.get("kind"), str) and segment["kind"] not in KINDS:
                    result["invalid_kind"] = True
                bad.append(
                    {
                        "index": index,
                        "keys": sorted(segment) if isinstance(segment, dict) else [],
                        "kind_value": segment.get("kind")[:40]
                        if isinstance(segment, dict) and isinstance(segment.get("kind"), str)
                        else None,
                        "error_types": error_types,
                    }
                )
        result["bad_segments"] = bad
        result["ok"] = not bad
    except Exception as error:  # noqa: BLE001 - row-level replay errors are evidence
        result["error"] = f"{type(error).__name__}: {error}"
    return result


def replay(prompts: dict[str, dict[str, object]], n: int, out: Path) -> dict[str, object]:
    from storygame.runtime.cloudflare import BROWSER_USER_AGENT, CloudflareTurnProvider

    url = os.environ["CLOUDFLARE_WORKER_URL"]
    token = os.environ.get("CLOUDFLARE_WORKER_TOKEN", "")
    _, state = package_and_state(load_variation(VARIATION), "2B")
    classifier_provider = CloudflareTurnProvider(worker_url="", token="", state=state)
    out.joinpath("bad").mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []
    calls = 0
    with out.joinpath("replies.jsonl").open("w", encoding="utf-8") as reply_file:
        for rep in range(n):
            for cell in CELLS:
                if calls >= MAX_CALLS:
                    break
                calls += 1
                payload = prompts[cell]
                row: dict[str, object] = {"cell": cell, "rep": rep, "raw_body": "", "error": None}
                try:
                    headers = {"Content-Type": "application/json", "User-Agent": BROWSER_USER_AGENT}
                    if token:
                        headers["Authorization"] = f"Bearer {token}"
                    request = Request(url, data=json.dumps(payload).encode(), headers=headers, method="POST")
                    with urlopen(request, timeout=60) as response:  # noqa: S310
                        raw_body = response.read().decode()
                    row["raw_body"] = raw_body
                    row.update(classify_body(raw_body, classifier_provider))
                except Exception as error:  # noqa: BLE001 - continue collecting rows
                    row["error"] = f"{type(error).__name__}: {error}"
                    row.update({"ok": False, "bad_segments": [], "stray_selected_ids": False, "invalid_kind": False})
                reply_file.write(json.dumps(row, separators=(",", ":")) + "\n")
                rows.append(row)
                if not row["ok"]:
                    out.joinpath("bad", f"{cell}-{rep}.txt").write_text(str(row["raw_body"]), encoding="utf-8")
            if calls >= MAX_CALLS:
                break
    return make_summary(rows, calls)


def make_summary(rows: list[dict[str, object]], calls: int) -> dict[str, object]:
    per_cell = {}
    invalid_values: set[str] = set()
    for cell in CELLS:
        cell_rows = [row for row in rows if row["cell"] == cell]
        for row in cell_rows:
            for bad in row.get("bad_segments", []):
                value = bad.get("kind_value")
                if isinstance(value, str) and value not in KINDS:
                    invalid_values.add(value)
        per_cell[cell] = {
            "rows": len(cell_rows),
            "ok": sum(bool(row.get("ok")) for row in cell_rows),
            "bad_rows": sum(not bool(row.get("ok")) for row in cell_rows),
            "stray_selected_ids": sum(bool(row.get("stray_selected_ids")) for row in cell_rows),
            "invalid_kind": sum(bool(row.get("invalid_kind")) for row in cell_rows),
            "errors": sum(row.get("error") is not None for row in cell_rows),
        }
    return {"calls": calls, "cells": per_cell, "invalid_kind_values": sorted(invalid_values)}


def _write_dry_summary(out: Path, prompts: dict[str, dict[str, object]]) -> None:
    summary = {
        "calls": 0,
        "cells": {
            cell: {"rows": 0, "ok": 0, "bad_rows": 0, "stray_selected_ids": 0, "invalid_kind": 0, "errors": 0}
            for cell in CELLS
        },
        "invalid_kind_values": [],
    }
    out.joinpath("summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    notes = [
        "This dry run captured prompts offline from fresh scene-2B states; it made zero worker calls.",
        "The three payloads retain the system and user strings plus the normal JSON response settings.",
    ]
    reveal = prompts["reveal"]
    offered = "k_sl_2b_a_r1" in str(reveal.get("user", ""))
    notes.append(f"The reveal prompt {'shows' if offered else 'does not show'} the offered reveal k_sl_2b_a_r1.")
    for cell, payload in prompts.items():
        system = str(payload.get("system", ""))
        user = str(payload.get("user", ""))
        notes.append(
            f"{cell}: system {len(system)} chars (~{math.ceil(len(system) / 4)} tokens), "
            f"user {len(user)} chars (~{math.ceil(len(user) / 4)} tokens)."
        )
    out.joinpath("notes.md").write_text("\n".join(notes) + "\n", encoding="utf-8")


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
    if args.dry_run:
        _write_dry_summary(args.out, prompts)
        return
    args.out.joinpath("summary.json").write_text(
        json.dumps(replay(prompts, args.n, args.out), indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))
    main()
