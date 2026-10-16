"""Read-only summaries of saved blind-player attempt bundles."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from storygame.runtime.attempt_bundle import AttemptBundle


class BundleRecords(list[tuple[Any, str, Any, AttemptBundle, dict[str, Any]]]):
    """Loaded records with validation failures kept beside the valid records."""

    def __init__(self) -> None:
        super().__init__()
        self.invalid: list[dict[str, Any]] = []


def _paths(paths: Iterable[str | Path]) -> Iterable[Path]:
    for value in paths:
        path = Path(value)
        if path.is_dir():
            yield from sorted(path.rglob("e2e-blind-player-bundles-r*.json"))
        else:
            yield path


def load_bundles(paths: Iterable[str | Path]) -> BundleRecords:
    """Load and validate bundles from saved files or directories.

    The returned list has an ``invalid`` attribute containing every malformed
    bundle, including its source file, saved turn, and validation error.
    """

    records = BundleRecords()
    model_keys = set(AttemptBundle.model_fields)
    for path in _paths(paths):
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except Exception as error:  # A bad file is evidence, too.
            records.invalid.append({"file": str(path), "turn": None, "error": str(error)})
            continue
        for replicate_data in document.get("replicates", []):
            replicate = replicate_data.get("replicate")
            for scene_data in replicate_data.get("scenes", []):
                scene = scene_data.get("scene")
                for saved in scene_data.get("bundles", []):
                    turn = saved.get("turn")
                    raw = saved.get("attempt_bundle", {})
                    if not isinstance(raw, dict):
                        records.invalid.append(
                            {"file": str(path), "turn": turn, "error": "attempt_bundle is not an object"}
                        )
                        continue
                    extras = {key: value for key, value in raw.items() if key not in model_keys}
                    payload = {key: value for key, value in raw.items() if key in model_keys}
                    try:
                        bundle = AttemptBundle.model_validate(payload)
                    except Exception as error:
                        records.invalid.append({"file": str(path), "turn": turn, "error": str(error)})
                    else:
                        records.append((replicate, scene, turn, bundle, extras))
    return records


def _scene_counts() -> defaultdict[str, Counter[str]]:
    return defaultdict(Counter)


def _range(values: list[int]) -> dict[str, int | None]:
    return {"min": min(values) if values else None, "max": max(values) if values else None}


def runtime_reveal_outcomes() -> set[str]:
    """Return reveal-selection outcomes named by the runtime source."""

    runtime = Path(__file__).resolve().parents[1] / "storygame" / "runtime"
    found: set[str] = set()
    assignment = re.compile(r'(?:["\']outcome["\']|\[["\']outcome["\']\])\s*[:=]\s*["\']([^"\']+)["\']')
    update = re.compile(r"update\(.*?outcome\s*=\s*[\"']([^\"']+)[\"']")
    for source in runtime.glob("*.py"):
        text = source.read_text(encoding="utf-8")
        for match in re.finditer(r"last_reveal_selection", text):
            window = text[match.start() : match.start() + 1200]
            found.update(m.group(1) for m in assignment.finditer(window))
            found.update(m.group(1) for m in update.finditer(window))
    return found


def summarize(records: Iterable[tuple[Any, str, Any, AttemptBundle, dict[str, Any]]]) -> dict[str, Any]:
    """Summarize valid records; invalid records are included when available."""

    invalid = getattr(records, "invalid", [])
    records = list(records)
    reveal_scene = _scene_counts()
    exit_scene = _scene_counts()
    outcome_scene = _scene_counts()
    outcomes = Counter()
    matched = Counter()
    universe: list[int] = []
    shortlist: list[int] = []
    rejection_codes = Counter()
    rejection_narration = Counter()
    recovery_distribution = Counter()
    stage_distributions = {kind: Counter() for kind in ("narration", "semantic_match", "capture")}
    scene_triples: list[dict[str, Any]] = []
    reveal_checked = exit_checked = selection_checked = refusal_checked = recovery_checked = 0
    game_breaks = operational_failures = recovery_attempts = 0

    for _replicate, scene, turn, bundle, _extras in records:
        committed = bundle.outcome == "committed"
        if committed:
            reveal_checked += 1
            earned = bool(bundle.selected_reveal.knowledge_ids)
            delivered = bundle.cue_stage.delivered
            consumed = bundle.cue_stage.consumed
            reveal_scene[str(scene)]["earned_reveals"] += earned
            reveal_scene[str(scene)]["cue_delivered"] += delivered
            reveal_scene[str(scene)]["cue_consumed"] += consumed
            reveal_scene[str(scene)]["both"] += earned and (delivered or consumed)
            reveal_scene[str(scene)]["cue_without_earned_reveal"] += (delivered or consumed) and not earned

            exit_checked += 1
            left = bundle.committed_delta.scene_from != bundle.committed_delta.scene_to
            if left or bundle.transition_cause != "none":
                cause = bundle.transition_cause
                exit_scene[str(scene)][cause] += 1
                scene_triples.append({"scene": scene, "turn": turn, "cause": cause})

        if bundle.reveal_selection is not None:
            selection_checked += 1
            selection = bundle.reveal_selection
            outcomes[selection.outcome] += 1
            outcome_scene[str(scene)][selection.outcome] += 1
            matched["present" if selection.matched is not None else "absent"] += 1
            universe.append(selection.universe_size)
            shortlist.append(selection.shortlist_size)

        refusal_checked += 1
        game_breaks += bundle.outcome == "game_break"
        operational_failures += bundle.outcome == "operational_failure"
        if bundle.outcome == "rejected":
            code = bundle.rejection.code if bundle.rejection else None
            rejection_codes[str(code)] += 1
            has_narration = any(stage.kind == "narration" for stage in bundle.stages)
            rejection_narration["with_narration" if has_narration else "provider_free"] += 1

        recovery_checked += 1
        counts = Counter(stage.kind for stage in bundle.stages)
        recovery_distribution[str(counts["narration"])] += 1
        recovery_attempts += counts["narration"] > 1
        for kind in stage_distributions:
            stage_distributions[kind][str(counts[kind])] += 1

    known_outcomes = runtime_reveal_outcomes()
    return {
        "invalid": invalid,
        "reveal_vs_cue": {"checked": reveal_checked, "per_scene": dict(reveal_scene)},
        "exits": {"checked": exit_checked, "per_scene": dict(exit_scene), "triples": scene_triples},
        "rare_selection": {
            "checked": selection_checked,
            "overall": dict(outcomes),
            "per_scene": dict(outcome_scene),
            "matched": dict(matched),
            "universe_size": _range(universe),
            "shortlist_size": _range(shortlist),
            "runtime_outcomes": sorted(known_outcomes),
            "unobserved": sorted(known_outcomes - set(outcomes)),
        },
        "refusal_telemetry": {
            "checked": refusal_checked,
            "rejection_codes": dict(rejection_codes),
            "narration": dict(rejection_narration),
            "game_break": game_breaks,
            "operational_failure": operational_failures,
        },
        "recovery_stages": {
            "checked": recovery_checked,
            "stage_count_distributions": {kind: dict(values) for kind, values in stage_distributions.items()},
            "narration_stage_distribution": dict(recovery_distribution),
            "recovery_or_guard_retry": recovery_attempts,
        },
    }


def render_markdown(summary: dict[str, Any]) -> str:
    """Render a compact, inspectable report."""

    lines = ["# Saved bundle report", ""]
    for title, key in (
        ("Reveal versus cue", "reveal_vs_cue"),
        ("Exits", "exits"),
        ("Rare selection outcomes", "rare_selection"),
        ("Refusal telemetry", "refusal_telemetry"),
        ("Recovery stages", "recovery_stages"),
    ):
        section = summary[key]
        lines.extend([f"## {title}", "", f"- Checked: {section['checked']}"])
        if key == "exits":
            lines.append(f"- Exit triples: {section['triples']}")
        elif key == "rare_selection":
            lines.append(f"- Outcomes: {section['overall']}")
            lines.append(f"- Unobserved runtime outcomes: {section['unobserved']}")
        elif key == "refusal_telemetry":
            lines.append(f"- Rejection codes: {section['rejection_codes']}")
            lines.append(
                f"- Game breaks: {section['game_break']}; operational failures: {section['operational_failure']}"
            )
        elif key == "recovery_stages":
            lines.append(f"- Narration-stage distribution: {section['narration_stage_distribution']}")
            lines.append(f"- Recovery/guard-retry attempts: {section['recovery_or_guard_retry']}")
        else:
            lines.append(f"- Per scene: {section['per_scene']}")
        lines.append("")
    lines.append(f"- Invalid bundles: {len(summary['invalid'])}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--out-json", type=Path)
    parser.add_argument("--out-md", type=Path)
    args = parser.parse_args(argv)
    summary = summarize(load_bundles(args.paths))
    markdown = render_markdown(summary)
    if args.out_json:
        args.out_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.out_md:
        args.out_md.write_text(markdown + "\n", encoding="utf-8")
    print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
