"""Frozen-transcript player-choice probe for the 3C families cue."""

from __future__ import annotations

import argparse
import difflib
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
MAIN_CHECKOUT = Path("/home/bcorfman/dev/freytag-forge")
sys.path.insert(0, str(ROOT))

from bench.core import load_variation, package_and_state  # noqa: E402
from scripts.ringer.stage7.door_transport import SpendBudget  # noqa: E402
from storygame.runtime.candidate_matcher import uniquely_matched_authored_handoff  # noqa: E402
from storygame.runtime.engine import RuntimeEngine  # noqa: E402
from storygame.runtime.facts import Fact  # noqa: E402


def _load_three_c_probe() -> Any:
    path = Path(__file__).with_name("three_c_probe.py")
    spec = importlib.util.spec_from_file_location("stage7_three_c_probe", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_THREE_C = _load_three_c_probe()
_ask_player = _THREE_C._ask_player
_player_screen = _THREE_C._player_screen

ARMS = ("control", "offer")
OLD_CUE = "Families of the missing call the broadcast chamber for word."
OFFER_SENTENCE = "Kristin can answer the families with news of the captives."
OFFER_CUE = f"{OLD_CUE} {OFFER_SENTENCE}"
RAW_PLAYER_CAP = 24
SOURCE_TURN = 10
VARIATION = "bench/variations/stage7-3c-families-offer.json"


def _resolve(path: Path) -> Path:
    if path.exists():
        return path
    fallback = MAIN_CHECKOUT / path
    if fallback.exists():
        return fallback
    raise FileNotFoundError(path)


def _json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _source_row(rows_path: Path) -> tuple[dict[str, Any], int]:
    raw = json.loads(rows_path.read_text(encoding="utf-8"))
    rows = raw if isinstance(raw, list) else raw["rows"]
    for index, row in enumerate(rows):
        if row.get("arm") == "item-facts":
            return row, index
    raise ValueError("rows.json has no item-facts source row")


def _transcript(row: dict[str, Any], offer: bool) -> list[tuple[str, str]]:
    prefix = row.get("scripted_prefix", {})
    transcript = [(turn["command"], turn["response"]) for turn in prefix.get("turns", [])]
    selected = [turn for turn in row.get("turns", []) if turn.get("scene_turn") in (8, 9, 10)]
    if [turn.get("scene_turn") for turn in selected] != [8, 9, 10]:
        raise ValueError("source row must contain scene turns 8, 9, and 10")
    for turn in selected:
        reply = turn["response"]
        if turn["scene_turn"] == SOURCE_TURN:
            if reply.count(OLD_CUE) != 1:
                raise ValueError("turn 10 reply must contain the cue sentence exactly once")
            if offer:
                reply = reply.replace(OLD_CUE, OFFER_CUE, 1)
        transcript.append((turn["command"], reply))
    return transcript


def build_screens(rows_path: Path) -> tuple[dict[str, str], dict[str, Any]]:
    row, row_index = _source_row(rows_path)
    entry = row["entry_text_shown"]
    screens = {arm: _player_screen(entry, _transcript(row, arm == "offer"))[0] for arm in ARMS}
    if screens["control"].count(OLD_CUE) != 1:
        raise ValueError("control screen cue sentence must occur exactly once")
    if screens["offer"].count(OFFER_SENTENCE) != 1:
        raise ValueError("offer screen cue sentence must occur exactly once")
    return screens, {
        "row_index": row_index,
        "row_arm": row.get("arm"),
        "row_id": row.get("row_id"),
        "source_turn": SOURCE_TURN,
        "entry_text": row["entry_text_shown"],
        "scripted_prefix_turn_index": row.get("scripted_prefix", {}).get("turn_index"),
    }


def _write_plan(out: Path, samples: int, source: dict[str, Any], mode: str) -> None:
    _json(
        out / "plan.json",
        {
            "arms": list(ARMS),
            "samples": samples,
            "call_count": 2 * samples,
            "caps": {"raw_player": RAW_PLAYER_CAP, "cloudflare": 0},
            "source": source,
            "mode": mode,
            "interleave": "control then offer for each sample index",
            "notes": "Player calls only; no Cloudflare narration calls. Live uses SpendBudget for both caps.",
        },
    )


def _write_dry(out: Path, samples: int, rows_path: Path) -> None:
    screens, source = build_screens(rows_path)
    out.mkdir(parents=True, exist_ok=True)
    for arm in ARMS:
        (out / f"{arm}.screen.txt").write_text(screens[arm], encoding="utf-8")
    diff = difflib.unified_diff(
        [f"{line}\n" for line in screens["control"].splitlines()],
        [f"{line}\n" for line in screens["offer"].splitlines()],
        fromfile="control.screen.txt",
        tofile="offer.screen.txt",
    )
    (out / "screen.diff").write_text("".join(diff), encoding="utf-8")
    _json(
        out / "sha256.json",
        {f"{arm}.screen.txt": hashlib.sha256(screens[arm].encode()).hexdigest() for arm in ARMS},
    )
    _write_plan(out, samples, source, "dry")


def _append_row(path: Path, row: dict[str, Any]) -> None:
    rows: list[dict[str, Any]]
    if path.exists():
        value = json.loads(path.read_text(encoding="utf-8"))
        rows = value if isinstance(value, list) else value.get("rows", [])
    else:
        rows = []
    rows.append(row)
    _json(path, rows)


def _live(out: Path, samples: int, rows_path: Path) -> None:
    if samples > 12:
        raise SystemExit("--samples must be at most 12 in live mode")
    screens, source = build_screens(rows_path)
    out.mkdir(parents=True, exist_ok=True)
    _write_plan(out, samples, source, "live")
    rows_path_out = out / "rows.json"
    budget = SpendBudget(limit=RAW_PLAYER_CAP, cloudflare_limit=0, player_limit=RAW_PLAYER_CAP)
    for sample in range(1, samples + 1):
        for arm in ARMS:
            result: dict[str, Any] = {"arm": arm, "sample": sample}
            try:
                result["command"] = _ask_player(screens[arm], budget)
            except Exception as error:
                result["error"] = f"{type(error).__name__}: {error}"
                _append_row(rows_path_out, result)
                (out / "run-failure.txt").write_text(result["error"], encoding="utf-8")
                raise
            _append_row(rows_path_out, result)


def _families_match(command: str) -> str | None:
    variation = load_variation(_resolve(Path(VARIATION)))
    package, state = package_and_state(variation, "3C")
    state._assert_scene_entry_fact("3C")  # noqa: SLF001
    for fact_id in ("broadcast_started", "brandon_confession_available", "detention_locations_secured"):
        state.facts.assert_fact(Fact(predicate=fact_id, subject="story", value="true"))

    def provider(knowledge_id: str):
        knowledge = package.knowledge_indexes.by_id[knowledge_id]
        text = knowledge.delivery_text or knowledge.statement
        return lambda _command: {
            "segments": [{"kind": "narration", "text": text}],
            "selected_knowledge_ids": [knowledge_id],
        }

    commands = {
        "k_sl_3c_a_r1": "Send the evidence package.",
        "k_sl_3c_b_r1": "Take the Portable data case from Rebecca.",
        "k_sl_3c_c_r1": "Restore the drainage pumps.",
        "k_sl_3c_c_r2": "Open the surface gates.",
    }
    engine = RuntimeEngine(state, provider("k_sl_3c_a_r1"))
    for reveal in commands:
        engine.provider = provider(reveal)
        engine.turn(commands[reveal])
        engine._activate_pacing()  # noqa: SLF001
    engine.provider = provider("k_sl_3c_d_r1")
    engine.turn("Read the detention site reports.")
    engine._activate_pacing()  # noqa: SLF001
    projection = engine.projector.project(engine.state, "player", command)
    matched = uniquely_matched_authored_handoff(command, projection.reveal_universe)
    return matched.candidate.id if matched is not None else None


def _score(out: Path) -> None:
    rows_path = out / "rows.json"
    value = json.loads(rows_path.read_text(encoding="utf-8"))
    rows = value if isinstance(value, list) else value.get("rows", [])
    scored = []
    for row in rows:
        if "command" not in row:
            continue
        scored.append({**row, "reveal_id": _families_match(row["command"])})
    _json(out / "score.json", scored)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=Path, default=Path("bench/results/stage7-3c-escape-close-smoke/rows.json"))
    parser.add_argument("--samples", type=int, default=12)
    parser.add_argument("--dry", action="store_true")
    parser.add_argument("--confirm", action="store_true")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--score", action="store_true")
    args = parser.parse_args(argv)
    if args.dry and args.score:
        raise SystemExit("--dry and --score are mutually exclusive")
    out = args.out
    if args.score:
        _score(out)
        return 0
    rows_path = _resolve(args.rows)
    if args.samples <= 0:
        raise SystemExit("--samples must be positive")
    if args.dry:
        _write_dry(out, args.samples, rows_path)
        return 0
    if not args.confirm:
        raise SystemExit("--confirm is mandatory for live execution")
    if args.samples > 12:
        raise SystemExit("--samples must be at most 12 in live mode")
    _live(out, args.samples, rows_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
