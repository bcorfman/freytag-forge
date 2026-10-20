from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from storygame.runtime.candidate_matcher import (
    ActionEvidenceCandidate,
    uniquely_matched_candidate,
)
from storygame.story_package.loader import load_story_package

ROOT = Path(__file__).resolve().parents[3]
RUN = ROOT / "bench/results/stage7-2b-entry/attempt-1"
OUT = ROOT / "bench/results/stage7-3c-matcher-table"
REVEALS = tuple(
    f"k_sl_3c_{part}"
    for part in (
        "a_r1",
        "a_r2",
        "b_r1",
        "b_r2",
        "c_r1",
        "c_r2",
        "d_r1",
        "d_r2",
        "e_r1",
        "e_r2",
    )
)
SUBSETS = {
    1: ("a_r1", "a_r2"),
    2: ("b_r1", "b_r2"),
    3: ("c_r1", "c_r2"),
    4: ("c_r2",),
    5: ("c_r2",),
    6: ("d_r1", "d_r2"),
    7: ("d_r1", "d_r2"),
    8: ("d_r1", "d_r2"),
    **{turn: ("d_r1",) for turn in range(9, 16)},
}
EXPECTED = {
    1: ((), ()),
    2: (("b_r1",), ("b_r1",)),
    3: (("c_r1",), ("c_r1",)),
    4: ((), ()),
    5: (("c_r2",), ("c_r2",)),
    6: (("c_r2",), ("c_r2",)),
    7: (("a_r1", "b_r2"), ("a_r1", "b_r2")),
    8: (("d_r2",), ("d_r2",)),
    9: (("d_r2",), ("d_r2",)),
    10: ((), ()),
    11: ((), ()),
    12: (("d_r2",), ("d_r1", "d_r2")),
    13: ((), ("d_r1",)),
    14: (("d_r2",), ("d_r1", "d_r2")),
    15: (("d_r2",), ("d_r2",)),
}
EXPECTED_ELIGIBLE = {
    1: ((), ()),
    2: (("b_r1",), ("b_r1",)),
    3: (("c_r1",), ("c_r1",)),
    4: ((), ()),
    5: (("c_r2",), ("c_r2",)),
    6: ((), ()),
    7: ((), ()),
    8: (("d_r2",), ("d_r2",)),
    9: ((), ()),
    10: ((), ()),
    11: ((), ()),
    12: ((), ("d_r1",)),
    13: ((), ("d_r1",)),
    14: ((), ("d_r1",)),
    15: ((), ()),
}


def _ids(package, ids: tuple[str, ...]) -> tuple[ActionEvidenceCandidate, ...]:
    return tuple(
        ActionEvidenceCandidate(id=item_id, required_groups=package.knowledge_indexes.by_id[item_id].action_evidence)
        for item_id in ids
        if package.knowledge_indexes.by_id[item_id].action_evidence
    )


def _matches(command: str, package, ids: tuple[str, ...]) -> list[str]:
    candidates = _ids(package, ids)
    # Call the real unique matcher once per candidate set, while retaining all
    # matches for the audit (the unique API intentionally returns None on ties).
    matches = [candidate.id for candidate in candidates if uniquely_matched_candidate(command, (candidate,))]
    return [item_id.removeprefix("k_sl_3c_") for item_id in matches]


def _load_packages():
    current = load_story_package(ROOT / "data/stories/continuity-initiative")
    deployed_yaml = subprocess.check_output(
        ["git", "show", "62cae8aed2996b64a5ebd9afa4ee2fc2b0999cf4:data/stories/continuity-initiative/knowledge.yaml"],
        cwd=ROOT,
    )
    temp_root = Path(tempfile.mkdtemp(prefix="stage7-3c-package-"))
    package_copy = temp_root / "continuity-initiative"
    shutil.copytree(ROOT / "data/stories/continuity-initiative", package_copy)
    (package_copy / "knowledge.yaml").write_bytes(deployed_yaml)
    deployed = load_story_package(package_copy)
    return deployed, current, temp_root


def _load_turns():
    player = json.loads((RUN / "e2e-blind-player.json").read_text())
    scene = next(item for item in player["replicates"][0]["scenes"] if item.get("scene") == "3C")
    bundles = json.loads((RUN / "e2e-blind-player-bundles.json").read_text())
    bundle_scene = next(item for item in bundles["replicates"][0]["scenes"] if item.get("scene") == "3C")
    bundle_by_turn = {item["turn"]: item["attempt_bundle"] for item in bundle_scene["bundles"]}
    return scene["turns"][:15], bundle_by_turn


def _label(matches: list[str]) -> str:
    return "—" if not matches else ", ".join(matches)


def main() -> None:
    deployed, current, temp_root = _load_packages()
    try:
        turns, bundles = _load_turns()
        rows = []
        for turn in turns:
            number = turn["turn"]
            commands = {"raw": turn["raw_input"]}
            if "input" in turn:
                commands["normalized"] = turn["input"]
            subset = SUBSETS[number]
            bundle_universe_size = bundles[number]["reveal_selection"]["universe_size"]
            row = {
                "turn": number,
                "commands": commands,
                "bundle_universe_size": bundle_universe_size,
                "universe_size_matches_subset": len(subset) == bundle_universe_size,
                "variants": {},
            }
            for variant, command in commands.items():
                all_deployed = _matches(command, deployed, REVEALS)
                all_current = _matches(command, current, REVEALS)
                subset_ids = tuple(f"k_sl_3c_{part}" for part in subset)
                subset_deployed = _matches(command, deployed, subset_ids)
                subset_current = _matches(command, current, subset_ids)
                row["variants"][variant] = {
                    "all_ten_deployed": all_deployed,
                    "all_ten_current": all_current,
                    "eligible_deployed": subset_deployed,
                    "eligible_current": subset_current,
                }
            rows.append(row)

        disagreements = []
        for row in rows:
            got_d = tuple(row["variants"]["normalized"]["all_ten_deployed"])
            got_c = tuple(row["variants"]["normalized"]["all_ten_current"])
            expected_columns = (
                ("all-ten deployed", got_d, EXPECTED[row["turn"]][0]),
                ("all-ten current", got_c, EXPECTED[row["turn"]][1]),
            )
            for column, got, expected in expected_columns:
                if got != expected:
                    disagreements.append(
                        {
                            "turn": row["turn"],
                            "column": column,
                            "expected": list(expected),
                            "got": list(got),
                        }
                    )
        eligible_disagreements = []
        for row in rows:
            got_d = tuple(row["variants"]["normalized"]["eligible_deployed"])
            got_c = tuple(row["variants"]["normalized"]["eligible_current"])
            expected_columns = (
                ("eligible deployed", got_d, EXPECTED_ELIGIBLE[row["turn"]][0]),
                ("eligible current", got_c, EXPECTED_ELIGIBLE[row["turn"]][1]),
            )
            for column, got, expected in expected_columns:
                if got != expected:
                    eligible_disagreements.append(
                        {
                            "turn": row["turn"],
                            "column": column,
                            "expected": list(expected),
                            "got": list(got),
                        }
                    )
        universe_disagreements = [
            {
                "turn": row["turn"],
                "expected_subset_size": len(SUBSETS[row["turn"]]),
                "bundle_universe_size": row["bundle_universe_size"],
            }
            for row in rows
            if not row["universe_size_matches_subset"]
        ]
        changed = []
        for row in rows:
            variant = row["variants"]["normalized"]
            if variant["eligible_deployed"] != variant["eligible_current"]:
                changed.append(row["turn"])
        report = {
            "scene": "3C",
            "reveal_ids": list(REVEALS),
            "subset_definition": {str(turn): [f"k_sl_3c_{part}" for part in ids] for turn, ids in SUBSETS.items()},
            "rows": rows,
            "plan_table_agrees": not disagreements,
            "disagreements": disagreements,
            "plan_eligible_table_agrees": not eligible_disagreements,
            "plan_eligible_disagreements": eligible_disagreements,
            "universe_size_disagreements": universe_disagreements,
            "unique_selection_changed_by_667": changed,
        }
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / "table.json").write_text(json.dumps(report, indent=2) + "\n")
        headers = [
            "turn",
            "command",
            "all-ten deployed",
            "all-ten current",
            "eligible deployed",
            "eligible current",
        ]
        lines = [
            "| " + " | ".join(headers) + " |",
            "|" + "|".join("---" for _ in headers) + "|",
        ]
        for row in rows:
            cells = [
                str(row["turn"]),
                "<br>".join(f"{name}: {command}" for name, command in row["commands"].items()),
            ]
            value_keys = (
                "all_ten_deployed",
                "all_ten_current",
                "eligible_deployed",
                "eligible_current",
            )
            for key in value_keys:
                values = [row["variants"][name][key] for name in row["commands"]]
                cells.append(
                    "<br>".join(
                        f"{name}: {_label(value) if value is not None else 'absent'}"
                        for name, value in zip(row["commands"], values, strict=True)
                    )
                )
            lines.append("| " + " | ".join(cells) + " |")
        (OUT / "table.md").write_text("# Stage 7 3C matcher table\n\n" + "\n".join(lines) + "\n")
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


if __name__ == "__main__":
    main()
