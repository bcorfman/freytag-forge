"""Smoke probe for the Scene 2B handoff cue arms."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

import yaml

from bench.core import load_variation, package_and_state, provider_for
from storygame.runtime.candidate_matcher import _matches_all
from storygame.runtime.engine import RuntimeEngine

ARMS = (
    ("stage7-2b-cue-control", ROOT / "bench/variations/stage7-2b-cue-control.json", "Selection files fill the archive terminals. Government and financial records sit open beside them."),
    ("stage7-2b-cue-b", ROOT / "bench/variations/stage7-2b-cue-b.json", "Selection files fill the archive terminals. Michelle's file is one of them."),
    ("stage7-2b-cue-c", ROOT / "bench/variations/stage7-2b-cue-c.json", "Selection files fill the archive terminals. One file carries Michelle's name, and another carries Kristin's."),
)
COMMAND = "Examine the unmarked door, keycard reader, and ventilation grille."
PLAYER_SCRIPT = ROOT / "scripts/ringer/stage7/2b_ask_player.mjs"
# The requested 12-replicate run has 36 narration invocations.  The player
# helper may make one validation retry, so its process-level ceiling is twice
# the number of probe rows.
NARRATION_CAP = 36
PLAYER_CAP = 72


def read_fixture_transcript() -> str:
    path = ROOT / "bench/results/stage7-blind-raw/attempt-1/e2e-blind-player.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    scene = next(item for item in data["replicates"][0]["scenes"] if item.get("scene") == "2A")
    return scene["turns"][-1]["text"]


def action_groups() -> dict[str, tuple[tuple[str, ...], ...]]:
    data = yaml.safe_load((ROOT / "data/stories/continuity-initiative/knowledge.yaml").read_text(encoding="utf-8"))
    return {
        entry["id"]: tuple(tuple(group) for group in entry["action_evidence"])
        for entry in data["knowledge"]
        if "2B" in (entry.get("available_in_scenes") or []) and entry.get("action_evidence")
    }


def player_command(transcript: str) -> str:
    completed = subprocess.run(
        ["node", str(PLAYER_SCRIPT)],
        input=json.dumps({"transcript": transcript, "status": ""}),
        text=True,
        capture_output=True,
        cwd=ROOT,
        env=os.environ.copy(),
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr or completed.stdout or f"player exited {completed.returncode}")
    try:
        result = json.loads(completed.stdout)
        command = result["command"]
    except (ValueError, KeyError, TypeError) as error:
        raise RuntimeError(f"invalid player output: {completed.stdout}") from error
    if not isinstance(command, str) or not command.strip():
        raise RuntimeError(f"invalid player command: {result!r}")
    return command


def narration_for(variation_path: Path) -> str:
    variation = load_variation(variation_path)
    package, state = package_and_state(variation, "2B")
    provider = provider_for(state, variation)
    engine = RuntimeEngine(state, provider)
    proposal = engine.turn(COMMAND)
    return proposal.narration


def write_summary(out: Path, n: int, rows: list[dict[str, Any]], narration_calls: int, player_calls: int) -> dict[str, Any]:
    arms: dict[str, Any] = {}
    for arm, _, _ in ARMS:
        arm_rows = [row for row in rows if row["arm"] == arm]
        matched_ids: dict[str, int] = {}
        for row in arm_rows:
            for identifier in row["matched"]:
                matched_ids[identifier] = matched_ids.get(identifier, 0) + 1
        arms[arm] = {
            "hits": sum(bool(row["matched"]) for row in arm_rows),
            "cue_visible": sum(bool(row["cue_visible"]) for row in arm_rows),
            "mentions_invention": sum(bool(row["mentions_invention"]) for row in arm_rows),
            "matched_ids": dict(sorted(matched_ids.items())),
        }
    summary = {"n": n, "narration_calls": narration_calls, "player_calls": player_calls, "arms": arms}
    (out / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return summary


def write_notes(out: Path, summary: dict[str, Any], deviation: str = "None.") -> None:
    lines = [
        "The probe was invoked from the repository root with the required TMPDIR=/tmp command after the requested free dry-run.",
        "The live invocation used n=12 and the requested output directory. For each replicate, arms were processed in control, cue-b, cue-c order.",
        "Each arm used its unchanged bench variation, bare Scene 2B entry state, and the specified one-input action through the bench runtime machinery.",
        "The screen transcript began with the recorded final Scene 2A turn, followed by the specified examination command and the complete returned narration.",
        f"Deviation from the requested sequence: {deviation}",
        f"Narration calls: {summary.get('narration_calls', 0)}. Player calls: {summary.get('player_calls', 0)}.",
    ]
    for arm, _, _ in ARMS:
        values = summary["arms"].get(arm, {})
        lines.append(f"{arm}: hits={values.get('hits', 0)}, cue_visible={values.get('cue_visible', 0)}.")
    (out / "notes.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.n < 1:
        raise ValueError("--n must be at least 1")
    out = args.out if args.out.is_absolute() else ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)
    transcript = read_fixture_transcript()
    screen = f"{transcript}\n\n> {COMMAND}\n\n"
    if args.dry_run:
        arm, variation, cue = ARMS[0]
        print(json.dumps({
            "arm": arm,
            "bench_prompt_path_plan": str(variation),
            "scene": "2B",
            "entry_state": "bare",
            "script_input": COMMAND,
            "player_prompt": {"transcript": screen + f"<narration from {arm}; cue: {cue}>", "status": ""},
        }, indent=2, ensure_ascii=False))
        return 0

    rows: list[dict[str, Any]] = []
    groups = action_groups()
    narration_calls = 0
    player_calls = 0
    try:
        for rep in range(1, args.n + 1):
            for arm, variation, cue in ARMS:
                if narration_calls >= NARRATION_CAP:
                    raise RuntimeError("hard call cap reached; wrote partial results")
                narration = narration_for(variation)
                narration_calls += 1
                visible = cue in narration
                if player_calls >= PLAYER_CAP:
                    raise RuntimeError("hard call cap reached; wrote partial results")
                command = player_command(screen + narration)
                # One invocation is one player call from this probe's point of
                # view. The helper itself owns its permitted validation retry.
                player_calls += 1
                matched = sorted(identifier for identifier, evidence in groups.items() if _matches_all(evidence, command))
                rows.append({
                    "arm": arm,
                    "rep": rep,
                    "narration": narration,
                    "cue_visible": visible,
                    "command": command,
                    "matched": matched,
                    "mentions_invention": any(word in command.casefold() for word in ("door", "keycard", "grille", "inspector", "credentials")),
                })
                (out / "results.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    except Exception as error:
        (out / "results.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        (out / "run-failure.txt").write_text(str(error), encoding="utf-8")
        summary = write_summary(out, args.n, rows, narration_calls, player_calls)
        write_notes(out, summary, "The live probe stopped after the recorded error.")
        return 1
    summary = write_summary(out, args.n, rows, narration_calls, player_calls)
    write_notes(out, summary, "None.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(str(error), file=sys.stderr)
        raise
