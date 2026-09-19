"""Build a Markdown report from saved benchmark turns and judge results."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

FACT = [
    "facts_after_correct",
    "missed_change",
    "invented_change",
    "narration_contradicts_given_facts",
    "dropped_true_condition",
    "kept_ended_condition",
    "state_as_place",
]
CONT = ["contradicts_stated_fact", "restarts_scene"]
MISSING_FACT = "(no fact-tracking verdict)"
MISSING_CONT = "(no continuity verdict)"


def _judgment_map(path: Path, runs: list[dict]) -> dict[int, list[dict]]:
    judgments = json.loads(path.read_text())["judgments"]
    return {run["replicate"]: judgments[index]["turns"] for index, run in enumerate(runs) if index < len(judgments)}


def fact_map_from_probe(path: Path) -> dict[int, list[dict]]:
    return {judgment["replicate"]: judgment["turns"] for judgment in json.loads(path.read_text())["judgments"]}


def _match_verdicts(verdicts: list[dict] | None, turns: list[dict]) -> list[dict | None]:
    if not verdicts:
        return [None] * len(turns)
    record_numbers = [turn.get("turn_number") for turn in turns]
    verdict_numbers = [verdict.get("turn") for verdict in verdicts]
    if all(number in record_numbers for number in verdict_numbers):
        by_number = {verdict["turn"]: verdict for verdict in verdicts}
        return [by_number.get(number) for number in record_numbers]
    return [verdicts[index] if index < len(verdicts) else None for index in range(len(turns))]


def failing(fact: dict | None, cont: dict | None) -> list[str]:
    names = []
    if fact is not None:
        if fact.get("facts_after_correct") == "no":
            names.append("facts_after_wrong")
        names.extend(name for name in FACT[1:] if fact.get(name) == "yes")
    if cont is not None:
        names.extend(name for name in CONT if cont.get(name) == "yes")
    return names


def build_section(
    label: str,
    results: Path,
    facts: dict[int, list[dict]],
    lines: list[str],
    counts: list[str],
    *,
    all_turns: bool = False,
) -> None:
    source = json.loads((results / "all-turn-records.json").read_text())
    runs = source["runs"]
    cont_map = _judgment_map(results / "continuity-judgments.json", runs)
    total = sum(len(run["turns"]) for run in runs)
    tally: dict[str, int] = {}
    failing_turns = 0
    clean_turns = 0
    initiative = kept_correct = missed = 0
    body: list[str] = []

    for run in runs:
        rep = run["replicate"]
        fact_turns = _match_verdicts(facts.get(rep), run["turns"])
        cont_turns = _match_verdicts(cont_map.get(rep), run["turns"])
        for index, turn in enumerate(run["turns"]):
            fact = fact_turns[index]
            cont = cont_turns[index]
            names = failing(fact, cont)
            took_initiative = bool(cont and cont.get("protagonist_acts_beyond_command") == "yes")
            if took_initiative:
                initiative += 1
                if fact and fact.get("facts_after_correct") == "yes":
                    kept_correct += 1
                if fact and fact.get("missed_change") == "yes":
                    missed += 1
            if not names:
                if not all_turns:
                    continue
                clean_turns += 1
                heading_names = ["clean"]
            else:
                failing_turns += 1
                for name in names:
                    tally[name] = tally.get(name, 0) + 1
                heading_names = names
            suffix = " [narrator initiative]" if took_initiative else ""
            body.append(
                f"### r{rep} turn {turn['turn_number']} ({turn.get('scene_id')}) - {', '.join(heading_names)}{suffix}"
            )
            body.append("- COMMAND: " + str(turn.get("player_input", "")))
            if "narrated_command" in turn and turn["narrated_command"] != turn.get("player_input"):
                body.append("- NARRATED COMMAND: " + str(turn["narrated_command"]))
            body.append("- NARRATION: " + str(turn.get("narration", "")))
            body.append("- GIVEN: " + json.dumps(turn.get("item_facts_before")))
            body.append("- REPLY: " + json.dumps(turn.get("item_facts_raw")))
            body.append("- AFTER: " + json.dumps(turn.get("item_facts_after")))
            if turn.get("item_facts_issues"):
                body.append("- ISSUES: " + json.dumps(turn["item_facts_issues"]))
            body.append("- FACT JUDGE: " + (fact.get("reason", "") if fact else MISSING_FACT))
            body.append("- CONTINUITY JUDGE: " + (cont.get("reason", "") if cont else MISSING_CONT))
            body.append("")

    counts.append(f"**{label} ({len(runs)} replicates, {total} turns)** - {failing_turns} turns with a real failure")
    for name, count in sorted(tally.items(), key=lambda pair: (-pair[1], pair[0])):
        counts.append(f"  - {name}: {count}")
    if all_turns:
        counts.append(f"  - clean turns: {clean_turns}")
    share = f"{100 * kept_correct / initiative:.0f}%" if initiative else "n/a"
    counts.append(
        f"  - narrator initiative (context, not a failure): {initiative} turns; of those, "
        f"{kept_correct} kept facts correct ({share}) and {missed} missed the change"
    )
    counts.append("")
    lines.extend([f"## {label} ({len(runs)} replicates, {total} turns)", "", *body])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--section", action="append", required=True, metavar="LABEL=RESULTS_DIR")
    parser.add_argument("--facts", action="append", default=[], metavar="LABEL=PATH")
    parser.add_argument("--title", required=True)
    parser.add_argument("--preamble-file", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--all-turns", action="store_true")
    args = parser.parse_args()

    sections = dict(item.split("=", 1) for item in args.section)
    overrides = dict(item.split("=", 1) for item in args.facts)
    lines = [f"# {args.title}", ""]
    if args.preamble_file:
        preamble = args.preamble_file.read_text()
        lines.extend(preamble.rstrip("\n").splitlines())
        lines.append("")
    lines.extend(["## Counts", ""])
    counts: list[str] = []
    section_lines: list[str] = []
    for label, directory in sections.items():
        results = Path(directory)
        runs = json.loads((results / "all-turn-records.json").read_text())["runs"]
        fact_path = Path(overrides[label]) if label in overrides else results / "fact-tracking-judgments.json"
        fact_map = fact_map_from_probe(fact_path) if label in overrides else _judgment_map(fact_path, runs)
        build_section(label, results, fact_map, section_lines, counts, all_turns=args.all_turns)
    args.out.write_text("\n".join(lines + counts + section_lines) + "\n")


if __name__ == "__main__":
    main()
