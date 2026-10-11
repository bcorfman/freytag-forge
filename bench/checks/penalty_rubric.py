"""Offline rubric for evidence-penalty lines in live bench records.

The scorer only reads recorded JSON and the authored pacing lines.  It never
calls a model.

Usage: penalty_rubric.py [--report PATH] <run-dir> [<run-dir> ...]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - the repository has PyYAML installed
    yaml = None


STATES = ("none", "processing", "development", "marked", "all")
FACT_STATES = {
    "evidence_gap_processing_numbers": "processing",
    "evidence_gap_development_record": "development",
    "evidence_gap_marked_site_list": "marked",
}
GENERIC_PENALTY = re.compile(
    r"without a copy|could not copy|no time to check|did not copy|unchecked|"
    r"not been verified|never verified",
    re.IGNORECASE,
)
FAILURE_WORDS = re.compile(
    r"game over|you failed|has failed|have failed|all is lost|hopeless|too late|doomed",
    re.IGNORECASE,
)
BLAME_WORDS = re.compile(
    r"should have|careless|negligent|irresponsible|your fault|her fault|blame",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class GapLine:
    state: str
    sentence: str
    key: str


@dataclass
class Score:
    replicate: Any
    state: str
    answers: dict[str, str]
    failures: list[str]
    human_turns: list[dict[str, Any]]


def load(path: Path) -> Any:
    """Load JSON, matching the small helper style used by live_bench."""

    return json.loads(path.read_text(encoding="utf-8"))


def load_gap_lines(path: Path | None = None) -> dict[str, GapLine]:
    """Load the four conditional evidence-gap realizations from pacing YAML."""

    pacing_path = path or Path(__file__).parents[2] / "data/stories/continuity-initiative/pacing.yaml"
    if yaml is None:  # pragma: no cover
        raise RuntimeError("PyYAML is required to load pacing.yaml")
    pacing = yaml.safe_load(pacing_path.read_text(encoding="utf-8"))
    lines: dict[str, GapLine] = {}
    for event in pacing.get("events", []):
        for realization in event.get("realizations", []):
            conditions = realization.get("when")
            if not conditions:
                continue
            fact_id = conditions[0].get("fact_id")
            state = FACT_STATES.get(fact_id)
            if state:
                sentence = str(realization["text"]).strip()
                lines[state] = GapLine(state, sentence, sentence.split(". ", 1)[1])
    if set(lines) != set(FACT_STATES.values()):
        raise ValueError("pacing.yaml does not contain all four evidence-gap realizations")
    return lines


def expected_states(run_dir: Path, override: str | None) -> list[str]:
    state = override or next((value for value in STATES if run_dir.name.endswith(f"-{value}")), None)
    if state is None:
        raise ValueError(f"cannot infer expected state from {run_dir.name!r}")
    return ["processing", "marked"] if state == "all" else ([] if state == "none" else [state])


def turn_text(turn: dict[str, Any]) -> str:
    return "\n".join(str(turn.get(field) or "") for field in ("narration", "complication_text"))


def quote(text: str) -> str:
    return text.replace("\n", " ").strip()


def score_replicate(replicate: dict[str, Any], state: str, gap_lines: dict[str, GapLine]) -> Score:
    turns = [turn for turn in replicate.get("turns", []) if isinstance(turn, dict)]
    texts = [turn_text(turn) for turn in turns]
    expected_states = ["processing", "marked"] if state == "all" else [] if state == "none" else [state]
    expected = [gap_lines[value] for value in expected_states]
    expected_keys = {line.key for line in expected}
    absent_lines = [line for line in gap_lines.values() if line.key not in expected_keys]
    failures: list[str] = []

    authored_absent = [line.sentence for line in absent_lines if any(line.sentence in text for text in texts)]
    expected_sentences = [marker for line in expected for marker in (line.sentence, line.key)]
    text_without_expected = [
        re.sub("|".join(re.escape(sentence) for sentence in expected_sentences), "", text) for text in texts
    ]
    generic_hits = [match.group(0) for text in text_without_expected for match in GENERIC_PENALTY.finditer(text)]
    q1_hits = authored_absent + generic_hits
    if q1_hits:
        failures.append(f"Q1 offending text: {', '.join(repr(quote(hit)) for hit in q1_hits)}")

    locations: dict[str, list[tuple[int, dict[str, Any], str]]] = {line.state: [] for line in expected}
    for turn in turns:
        text = turn_text(turn)
        for line in expected:
            if line.key in text:
                locations[line.state].append((int(turn.get("turn_number", 0)), turn, text))

    missing = [line.state for line in expected if not locations[line.state]]
    if missing:
        failures.append(f"Q2 missing expected gap line(s): {', '.join(missing)}")

    q4_hits: list[str] = []
    q5_hits: list[str] = []
    q6_hits: list[str] = []
    human_turns: list[dict[str, Any]] = []
    for line in expected:
        for turn_number, turn, text in locations[line.state]:
            human_turns.append(
                {
                    "state": line.state,
                    "replicate": replicate.get("replicate"),
                    "turn_number": turn_number,
                    "player_input": turn.get("player_input", ""),
                    "narration": turn.get("narration", ""),
                }
            )
            if FAILURE_WORDS.search(text):
                q4_hits.append(text)
            if BLAME_WORDS.search(text):
                q5_hits.append(text)
            if re.search(r"Michelle says|On the broadcast", text):
                q6_hits.append(text)
    if q4_hits:
        failures.append(f"Q4 offending text: {', '.join(repr(quote(hit)) for hit in q4_hits)}")
    if q5_hits:
        failures.append(f"Q5 offending text: {', '.join(repr(quote(hit)) for hit in q5_hits)}")
    if q6_hits:
        failures.append(f"Q6 offending text: {', '.join(repr(quote(hit)) for hit in q6_hits)}")

    doubled = [line.state for line in expected if len(locations[line.state]) != 1]
    if doubled:
        failures.append(f"Q7 expected exactly one occurrence for: {', '.join(doubled)}")

    answers = {
        "Q1": "FAIL" if q1_hits else "PASS",
        "Q2": "FAIL" if missing else "PASS",
        "Q3": (
            "info ("
            + ", ".join(f"{line.state}={'yes' if 'time' in line.sentence.lower() else 'no'}" for line in expected)
            + ")"
            if expected
            else "info"
        ),
        "Q4": "FAIL" if q4_hits else "PASS",
        "Q5": "FAIL" if q5_hits else "PASS",
        "Q6": "FAIL" if q6_hits else "PASS",
        "Q7": "FAIL" if doubled or missing else "PASS",
    }
    return Score(replicate.get("replicate"), state, answers, failures, human_turns)


def run(run_dir: Path, override: str | None, gap_lines: dict[str, GapLine]) -> list[Score]:
    state = expected_states(run_dir, override)
    records = load(run_dir / "all-turn-records.json")
    runs = records.get("runs", [])
    score_state = "all" if len(state) == 2 else state[0] if state else "none"
    return [score_replicate(replicate, score_state, gap_lines) for replicate in runs]


def report(scores: list[Score]) -> str:
    lines = ["| replicate | state | Q1 | Q2 | Q3 | Q4 | Q5 | Q6 | Q7 |", "|---|---|---|---|---|---|---|---|---|"]
    for score in scores:
        values = [str(score.replicate), score.state, *(score.answers[f"Q{i}"] for i in range(1, 8))]
        lines.append("| " + " | ".join(values) + " |")
        lines.extend(f"- {failure}" for failure in score.failures)
    lines.append("")
    lines.append("## Human-read sheet")
    for score in scores:
        for item in score.human_turns:
            lines.extend(
                [
                    f"- replicate {item['replicate']}, turn {item['turn_number']} ({item['state']})",
                    f"  - player_input: {item['player_input']}",
                    f"  - narration: {item['narration']}",
                ]
            )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path)
    parser.add_argument("--expect", choices=STATES)
    parser.add_argument("run_dirs", nargs="+")
    args = parser.parse_args(argv)
    gap_lines = load_gap_lines()
    scores: list[Score] = []
    for value in args.run_dirs:
        try:
            scores.extend(run(Path(value), args.expect, gap_lines))
        except (FileNotFoundError, json.JSONDecodeError, ValueError) as exc:
            print(f"FAIL: {value}: {exc}", file=sys.stderr)
            return 1
    output = report(scores)
    print(output, end="")
    if args.report:
        args.report.write_text(output, encoding="utf-8")
    failed = any(score.failures for score in scores)
    print(f"Total: {len(scores)} replicate(s), {'FAIL' if failed else 'PASS'}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
