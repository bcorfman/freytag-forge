"""Summarize candidate-selection benchmark runs."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

TURN1_POSITION0_IDS = {"k_sl_1a_a_r1", "k_sl_1a_a_r2"}
TURN3_POSITION2_IDS = {"k_sl_1a_b_r1", "k_sl_1a_b_r2"}


def _rate(selected: int, offered: int) -> dict[str, int | float | None]:
    return {
        "selected": selected,
        "offered": offered,
        "rate": selected / offered if offered else None,
    }


def _match_rate(matched: int, occurrences: int) -> dict[str, int | float | None]:
    return {
        "matched": matched,
        "occurrences": occurrences,
        "rate": matched / occurrences if occurrences else None,
    }


def compute_report(data: dict[str, Any]) -> dict[str, Any]:
    """Compute candidate-selection metrics for every run and turn."""
    if "runs" not in data:
        raise ValueError("input JSON is missing the required 'runs' key")

    runs = data["runs"]
    if not isinstance(runs, list):
        raise ValueError("input JSON 'runs' value must be a list")

    total_turns = 0
    offered = 0
    selected = 0
    turn1_occurrences = 0
    turn1_matched = 0
    turn3_occurrences = 0
    turn3_matched = 0
    per_turn: list[dict[str, Any]] = []

    for run_index, run in enumerate(runs):
        turns = run.get("turns", [])
        if not isinstance(turns, list):
            raise ValueError("each run's 'turns' value must be a list")
        total_turns += len(turns)

        for index, turn in enumerate(turns):
            candidates = turn.get("candidates_offered", [])
            selected_ids = turn.get("selected_knowledge_ids", [])
            expected_ids = TURN1_POSITION0_IDS if index % 4 == 0 else TURN3_POSITION2_IDS if index % 4 == 2 else set()
            if candidates:
                offered += 1
                if selected_ids:
                    selected += 1

            if index % 4 == 0:
                turn1_occurrences += 1
                if set(selected_ids) & expected_ids:
                    turn1_matched += 1
            if index % 4 == 2:
                turn3_occurrences += 1
                if set(selected_ids) & expected_ids:
                    turn3_matched += 1
            per_turn.append(
                {
                    "replicate": run.get("replicate", run_index + 1),
                    "turn": index + 1,
                    "player_input": turn.get("player_input", ""),
                    "candidates_offered": candidates,
                    "selected_knowledge_ids": selected_ids,
                    "model_selected_knowledge_ids": turn.get("model_selected_knowledge_ids", []),
                    "grounding_ids": turn.get("grounding_ids", []),
                    "model_grounding_ids": turn.get("model_grounding_ids", []),
                    "expected_candidate_ids": sorted(expected_ids),
                    "expected_match": None if not expected_ids else bool(set(selected_ids) & expected_ids),
                }
            )

    return {
        "total_runs": len(runs),
        "total_turns": total_turns,
        "overall_selection_rate": _rate(selected, offered),
        "turn1_position0_match_rate": _match_rate(turn1_matched, turn1_occurrences),
        "turn3_position2_match_rate": _match_rate(turn3_matched, turn3_occurrences),
        "per_turn": per_turn,
    }


def _load_input(path: Path) -> dict[str, Any]:
    try:
        with path.open(encoding="utf-8") as input_file:
            data = json.load(input_file)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"could not parse input JSON '{path}': {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError("input JSON must contain an object with a 'runs' key")
    return data


def _write_markdown(path: Path, report: dict[str, Any]) -> None:
    overall = report["overall_selection_rate"]
    turn1 = report["turn1_position0_match_rate"]
    turn3 = report["turn3_position2_match_rate"]
    lines = [
        "# Candidate Selection Report",
        "",
        f"- Total runs: {report['total_runs']}; total turns: {report['total_turns']}.",
        f"- Overall selection: {overall['selected']} selected of {overall['offered']} offered ({overall['rate']}).",
        f"- Turn 1 position 0 matches: {turn1['matched']} of {turn1['occurrences']} occurrences ({turn1['rate']}).",
        f"- Turn 3 position 2 matches: {turn3['matched']} of {turn3['occurrences']} occurrences ({turn3['rate']}).",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Report candidate-selection benchmark metrics.")
    parser.add_argument("--in", dest="input_path", required=True, type=Path, help="input JSON path")
    parser.add_argument("--out-json", required=True, type=Path, help="output JSON path")
    parser.add_argument("--out-md", required=True, type=Path, help="output Markdown path")
    args = parser.parse_args(argv)

    try:
        report = compute_report(_load_input(args.input_path))
        args.out_json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        _write_markdown(args.out_md, report)
    except (OSError, ValueError) as exc:
        print(f"candidate selection report: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
