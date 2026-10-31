"""Capture hidden-clue exposure in the scene 1B.2 narrator prompt."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = ROOT / "data" / "stories" / "continuity-initiative"
PROBE_PATH = ROOT / "scripts" / "ringer" / "environment_narration" / "hidden_bench_prose_probe.py"
BEAT_ID = "1B.2"
STATES = ("unrecovered", "recovered")
INPUTS = (
    "Ask the man about Michelle.",
    "Show Michelle's photograph to the man.",
    "Inspect the park bench.",
)
TERMS = (
    "transit token",
    "number sequence",
    "handwritten sequence",
    "michelle's photograph",
    "michelle photograph",
    "photograph",
    "photo",
)
CLUE_NAMES = (
    "Transit token",
    "handwritten number sequence",
    "Michelle's photograph",
)


def _load_probe() -> ModuleType:
    spec = importlib.util.spec_from_file_location("hidden_bench_prose_probe", PROBE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load probe module from {PROBE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_package(package_root: Path) -> Any:
    from storygame.story_package.loader import load_story_package

    return load_story_package(package_root)


def build_state(package: Any, recovered: bool) -> Any:
    """Build the requested 1B state, applying recovery through the real effect path."""

    from storygame.runtime.facts import Fact
    from storygame.runtime.world_model import apply_world_effects

    probe = _load_probe()
    state = probe._scene_1b_state(package)
    if recovered:
        state.facts.assert_fact(Fact(predicate="bench_clues_recovered", subject="story", value="true"))
        apply_world_effects(package, state.facts)
    return state


def _force_beat_live(package: Any, state: Any, provider: Any) -> None:
    from bench.core import resolve_beat

    selected = resolve_beat(package, "1B", BEAT_ID)
    provider._forced_beat_anchors.add(selected.anchor)
    # The bench helper also establishes every prior storylet.  That would
    # incorrectly commit the action-gated bench recovery while capturing 1B.2.
    storylets = [item.id for item in package.storylets if selected.anchor in item.source_links]
    if not storylets:
        raise RuntimeError(f"beat {selected.id} has no storylet source")
    state.active_event_ids.update(storylets)


def _hit_lines(
    system: str,
    user: str,
    composed_segments: list[dict[str, str]],
    player_input: str | None,
) -> dict[str, list[dict[str, str]]]:
    sections: list[tuple[str, str]] = [("system", system), ("user", user)]
    sections.extend(
        (
            f"composed segment {index} ({segment['kind']})",
            segment["text"],
        )
        for index, segment in enumerate(composed_segments, start=1)
    )
    hits: dict[str, list[dict[str, str]]] = {term: [] for term in TERMS}
    for section, text in sections:
        for line in text.splitlines():
            if player_input is not None and line in (player_input, f"- {player_input}"):
                continue
            folded = line.casefold()
            for term in TERMS:
                if term in folded:
                    hits[term].append({"section": section, "line": line})
    return {term: lines for term, lines in hits.items() if lines}


def _custody(things_block: str) -> dict[str, Any]:
    lines = things_block.splitlines()
    expected: dict[str, str] = {}
    for name in CLUE_NAMES:
        expected[name] = f"- {name}. Held by: Kristin"
    matches = {name: any(expected[name] in line for line in lines) for name in CLUE_NAMES}
    return {
        "things_block": things_block,
        "expected_lines": expected,
        "matches": matches,
        "all_held_by_kristin": all(matches.values()),
    }


def capture_one(package: Any, state_name: str, player_input: str | None) -> dict[str, Any]:
    from storygame.runtime.cloudflare import CloudflareTurnProvider
    from storygame.runtime.engine import RuntimeEngine

    probe = _load_probe()
    state = build_state(package, state_name == "recovered")
    provider = probe._world_aware_provider(state)
    engine = RuntimeEngine(state, provider)
    engine._activate_pacing()
    _force_beat_live(package, state, provider)
    requests: list[dict[str, str]] = []

    def stub_request(_provider: Any, payload: dict[str, object]) -> dict[str, object]:
        if payload.get("__freytag_request_budget", "narration") == "item_facts":
            return {"refers": [], "same_as": {}}
        requests.append({"system": str(payload["system"]), "user": str(payload["user"])})
        return {
            "segments": [{"kind": "narration", "text": "A short canned narration segment."}],
            "selected_knowledge_ids": [],
            "item_facts": {},
        }

    original_request = CloudflareTurnProvider._request
    CloudflareTurnProvider._request = stub_request
    try:
        if player_input is None:
            assembled = provider.assemble_turn_prompt("")
            request = {
                "system": str(assembled["system"]),
                "user": provider._section_user_prompt(assembled["context"]),
            }
            composed_segments: list[dict[str, str]] = []
        else:
            result = engine.turn(player_input)
            if not requests:
                raise RuntimeError(f"no narration request captured for {state_name}/{player_input}")
            request = requests[-1]
            composed_segments = [{"kind": segment.kind, "text": segment.text} for segment in result.segments]
    finally:
        CloudflareTurnProvider._request = original_request

    things_block = provider._things_block(narration=True)
    return {
        "state": state_name,
        "input": player_input or "opening",
        "system": request["system"],
        "user": request["user"],
        "composed_segments": composed_segments,
        "hits": _hit_lines(request["system"], request["user"], composed_segments, player_input),
        "custody": _custody(things_block) if state_name == "recovered" else None,
    }


def capture_package(package_root: Path = PACKAGE_ROOT) -> dict[str, Any]:
    package = _load_package(package_root)
    captures = []
    for state_name in STATES:
        captures.append(capture_one(package, state_name, None))
        captures.extend(capture_one(package, state_name, player_input) for player_input in INPUTS)
    return {"schema": 1, "beat": BEAT_ID, "captures": captures}


def _cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def _capture_verdict(capture: dict[str, Any]) -> str:
    if capture["state"] == "unrecovered":
        return "PASS" if not capture["hits"] else "FAIL exposure"
    return "INFO"


def render_report(document: dict[str, Any]) -> str:
    captures = document["captures"]
    lines = [
        "# Scene 1B.2 hidden-clue exposure capture",
        "",
        f"Beat forced live: `{document['beat']}`. Captures: {len(captures)}.",
        "",
        "| # | State | Input | Hits | Recovered custody | Verdict |",
        "|---:|---|---|---|---|---|",
    ]
    for index, capture in enumerate(captures, start=1):
        hits = ", ".join(capture["hits"]) or "none"
        custody = "n/a"
        if capture["custody"] is not None:
            custody = "yes" if capture["custody"]["all_held_by_kristin"] else "no"
        lines.append(
            "| "
            + " | ".join(
                (
                    str(index),
                    _cell(capture["state"]),
                    _cell(capture["input"]),
                    _cell(hits),
                    custody,
                    _capture_verdict(capture),
                )
            )
            + " |"
        )

    lines.extend(("", "## Findings", ""))
    for index, capture in enumerate(captures, start=1):
        lines.extend((f"### {index}. {capture['state']} / {capture['input']}", ""))
        if capture["hits"]:
            for term, term_hits in capture["hits"].items():
                for hit in term_hits:
                    lines.append(f"- `{term}` in **{hit['section']}**: `{hit['line']}`")
        else:
            lines.append("- No monitored string hit.")
        if capture["custody"] is not None:
            custody = capture["custody"]
            lines.append(
                "- THINGS custody: "
                + (
                    "all three expected Kristin lines present."
                    if custody["all_held_by_kristin"]
                    else "missing one or more expected Kristin lines."
                )
            )
            for name, expected in custody["expected_lines"].items():
                lines.append(f"  - `{name}`: {'present' if custody['matches'][name] else 'missing'} (`{expected}`)")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _has_unrecovered_exposure(document: dict[str, Any]) -> bool:
    return any(capture["state"] == "unrecovered" and capture["hits"] for capture in document["captures"])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, help="write the Markdown report to this path")
    parser.add_argument("--json", action="store_true", help="also print the capture document as JSON")
    args = parser.parse_args(argv)
    try:
        document = capture_package()
        report = render_report(document)
        if args.out is not None:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(report, encoding="utf-8")
        if args.json:
            print(json.dumps(document, indent=2, ensure_ascii=False))
        elif args.out is None:
            print(report, end="")
        return 1 if _has_unrecovered_exposure(document) else 0
    except Exception as error:
        print(f"capture tool error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
