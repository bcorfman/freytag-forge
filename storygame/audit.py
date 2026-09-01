"""Deterministic, offline quality checks for a Markdown story package.

These checks are deliberately heuristic.  In particular, frame/beat checking
only compares a small vocabulary of physical states attached to shared nouns;
it catches contradictory or omitted orientation/state adjectives, not every
semantic contradiction.  The auditor never imports a provider or calls a
language model.
"""

# The multiline vocabulary is more maintainable than a generated list.
# ruff: noqa: SIM905

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import yaml

CHECKS = (
    "unattested_detail",
    "frame_beat_conflict",
    "absent_speaker",
    "beat_overprojection",
    "prompt_hygiene",
    "beats_without_turns",
)
SCENES = ("1A", "1B", "1C", "2A", "2B", "2C", "3A", "3B", "3C")
_WORD = re.compile(r"[A-Za-z][A-Za-z'-]{2,}")
_STOPWORDS = set(  # noqa: SIM905
    """  # noqa: SIM905
a about after again all also an and are as at back be been before being but by can could did do does
for from had has have he her here him his how i if in into is it its just more most my no not of on one
only or our out over she should so some than that the their them then there these they this those to too
under up us was we were what when where which who will with would you your
""".split()
)
_STATE_WORDS = {
    "facedown": {"faceup", "face-down", "facedown", "screen visible", "screen exposed"},
    "face-down": {"faceup", "face-down", "facedown", "screen visible", "screen exposed"},
    "faceup": {"faceup", "face-down", "facedown", "screen visible", "screen exposed"},
    "undamaged": {"damaged", "broken", "intact", "undamaged"},
    "damaged": {"damaged", "broken", "intact", "undamaged"},
    "broken": {"damaged", "broken", "intact", "undamaged"},
    "overturned": {"overturned", "upright"},
    "upright": {"overturned", "upright"},
    "open": {"open", "closed", "shut"},
    "closed": {"open", "closed", "shut"},
    "shut": {"open", "closed", "shut"},
}

# This is intentionally a conservative vocabulary rather than a pretend POS
# tagger.  It catches named physical things that are useful to this audit,
# including an injected ``blood`` detail and fixture words such as ``ziggurat``;
# it cannot catch every concrete noun, compounds not listed here, or distinguish
# a physical sense from an abstract sense in ambiguous words such as ``mark``.
_CONCRETE_MATTER = {
    "archive",
    "bag",
    "battery",
    "bench",
    "blood",
    "bottle",
    "box",
    "card",
    "chair",
    "door",
    "drawer",
    "file",
    "floor",
    "gate",
    "hardware",
    "laptop",
    "mark",
    "memory",
    "number",
    "phone",
    "photograph",
    "radio",
    "recording",
    "server",
    "terminal",
    "track",
    "transit",
    "vent",
    "water",
    "workstation",
    "ziggurat",
}
_ABSTRACT_DETAIL_WORDS = {
    "absence",
    "deliberate",
    "doubt",
    "face",
    "match",
    "prove",
    "solution",
}


def _read_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    return value if isinstance(value, dict) else {}


def _stem(word: str) -> str:
    word = word.casefold().strip("'")
    for suffix in ("ies", "ing", "ed", "es", "s"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 4:
            return word[: -len(suffix)] + ("y" if suffix == "ies" else "")
    return word


def _words(text: str) -> set[str]:
    return {_stem(word) for word in _WORD.findall(text.casefold()) if word.casefold() not in _STOPWORDS}


def _concrete_unknowns(text: str, plot_words: set[str]) -> set[str]:
    """Return absent words likely to name physical, observable matter.

    Without a POS tagger this deliberately favors precision: only a small
    matter vocabulary is considered.  It catches concrete details such as
    ``blood`` but can miss unlisted objects and cannot resolve ambiguous words
    (for example, ``mark``) perfectly; abstract words are explicitly excluded.
    """
    tokens = _WORD.findall(text)
    words = {_stem(word) for word in tokens if word.casefold() not in _STOPWORDS}
    candidates = words & _CONCRETE_MATTER
    return {word for word in candidates if word not in plot_words}


def _finding(check: str, scene_id: str, detail: str) -> dict[str, str]:
    return {"check": check, "scene_id": scene_id, "detail": detail}


def _plot_scenes(plot: str) -> dict[str, str]:
    matches = list(re.finditer(r"^## Scene ([1-9][A-Z]) .*$", plot, re.MULTILINE))
    return {
        match.group(1): plot[match.end() : matches[index + 1].start() if index + 1 < len(matches) else len(plot)]
        for index, match in enumerate(matches)
    }


def _source_links(storylets: str) -> dict[str, list[tuple[str, int]]]:
    result: dict[str, list[tuple[str, int]]] = {}
    blocks = list(re.finditer(r"^### (SL-[1-9][A-Z]-[A-Z]) —", storylets, re.MULTILINE))
    for index, match in enumerate(blocks):
        block = storylets[match.end() : blocks[index + 1].start() if index + 1 < len(blocks) else len(storylets)]
        links = re.findall(r"plot\.md#([^)]+)", block)
        windows = re.search(r"earliest:\s*`turn (\d+)`.*?latest:\s*`turn (\d+)`", block, re.DOTALL)
        if windows:
            result[match.group(1)] = [(link, int(windows.group(1))) for link in links]
    return result


def audit_package(root: Path) -> dict[str, Any]:
    """Return deterministic findings for every scene in *root*.

    The expected package files are ``plot.md``, ``knowledge.yaml``,
    ``world.yaml``, ``pacing.yaml``, ``storylets.md``, and
    ``storylet-routes.yaml``.  Missing optional structures simply produce no
    finding for that check, which keeps small fixture packages useful.
    """
    root = Path(root)
    plot = (root / "plot.md").read_text(encoding="utf-8")
    scenes = _plot_scenes(plot)
    scene_ids = tuple(scene_id for scene_id in SCENES if scene_id in scenes) or tuple(scenes)
    knowledge = _read_yaml(root / "knowledge.yaml")
    world = _read_yaml(root / "world.yaml")
    pacing = _read_yaml(root / "pacing.yaml")
    routes = _read_yaml(root / "storylet-routes.yaml")
    findings: list[dict[str, str]] = []

    plot_words = _words(plot)
    for item in knowledge.get("knowledge", []):
        text = str(item.get("statement", ""))
        unknown = sorted(_concrete_unknowns(text, plot_words))
        if unknown:
            scene_id = (item.get("available_in_scenes") or [scene_ids[0]])[0]
            findings.append(
                _finding(
                    "unattested_detail",
                    scene_id,
                    f"Knowledge {item.get('id')} adds '{unknown[0]}', absent from plot.md.",
                )
            )
    for frame in knowledge.get("scene_frames", []):
        unknown = sorted(_concrete_unknowns(str(frame.get("situation", "")), plot_words))
        if unknown:
            findings.append(
                _finding(
                    "unattested_detail",
                    str(frame.get("scene_id")),
                    f"Scene frame adds '{unknown[0]}', absent from plot.md.",
                )
            )

    for frame in knowledge.get("scene_frames", []):
        scene_id = str(frame.get("scene_id"))
        situation = str(frame.get("situation", ""))
        beat_text = scenes.get(scene_id, "")
        for entity in re.findall(
            r"\b(?:phone|laptop|work bag|chair|door|drawer|card|bench|terminal|archive|relay)\b", situation.casefold()
        ):
            frame_states = {
                state for state in _STATE_WORDS if re.search(rf"\b{re.escape(state)}\b", situation.casefold())
            }
            beat_states = {
                state for state in _STATE_WORDS if re.search(rf"\b{re.escape(state)}\b", beat_text.casefold())
            }
            if not frame_states:
                continue
            relevant = set().union(*(_STATE_WORDS[state] for state in frame_states))
            if not (beat_states & relevant):
                state = sorted(frame_states)[0]
                findings.append(
                    _finding(
                        "frame_beat_conflict",
                        scene_id,
                        f"Frame says the {entity} is '{state}', but scene beats do not state that physical state.",
                    )
                )
                break

    entities = [*world.get("npcs", []), *world.get("locations", []), *world.get("items", [])]
    for scene_id, body in scenes.items():
        metadata = re.search(r"participant_ids:\s*\[([^]]*)\]", body)
        participants = re.findall(r"[a-z][a-z0-9_]*", metadata.group(1)) if metadata else []
        for participant in participants:
            entity = next((item for item in entities if item.get("id") == participant), None)
            if not entity:
                continue
            names = [str(entity.get("name", "")), *map(str, entity.get("aliases", []))]
            if participant == world.get("protagonist_id"):
                continue
            authored_presence = any(
                re.search(
                    rf"\b{re.escape(name)}\b[^.\n]{{0,80}}\b(?:arrive|enter|find|follow|help|meet|say|save|speak|stop|tell|watch|work)\w*\b",
                    body,
                    re.I,
                )
                for name in names
                if name
            )
            if authored_presence:
                continue
            if any(
                re.search(
                    rf"(?:{re.escape(name)})[^.\n]{{0,70}}(?:missing|gone|absent|disappeared|not present)", body, re.I
                )
                for name in names
                if name
            ):
                findings.append(
                    _finding(
                        "absent_speaker",
                        scene_id,
                        f"Participant '{participant}' is missing and cannot be offered as a present speaker.",
                    )
                )
            elif re.search(
                r"through recordings and evidence|only through .* possessions|prior presence", body, re.I
            ) and participant != world.get("protagonist_id"):
                findings.append(
                    _finding(
                        "absent_speaker",
                        scene_id,
                        f"Participant '{participant}' appears only through evidence, not as a present speaker.",
                    )
                )

    links = (
        _source_links((root / "storylets.md").read_text(encoding="utf-8")) if (root / "storylets.md").exists() else {}
    )
    route_windows = {
        item.get("id"): item.get("activation", {}).get("pacing", {}) for item in routes.get("storylets", [])
    }
    beat_sources: dict[str, list[tuple[str, int]]] = {}
    for storylet_id, values in links.items():
        earliest = int(route_windows.get(storylet_id, {}).get("earliest_turn", values[0][1] if values else 0))
        for anchor, _ in values:
            beat_sources.setdefault(anchor, []).append((storylet_id, earliest))
    for beat, sources in beat_sources.items():
        earliest = min(turn for _, turn in sources)
        latest = max(turn for _, turn in sources)
        if earliest < latest:
            scene_id = next(
                (sid for sid in scene_ids if f"scene-{sid.lower()}" in beat),
                beat.split("-")[0].upper() if beat else scene_ids[0],
            )
            findings.append(
                _finding(
                    "beat_overprojection",
                    scene_id,
                    f"Beat '{beat}' projects at turn {earliest}; its later reveal is not earnable until turn {latest}.",
                )
            )

    runtime = root.parent.parent.parent / "storygame" / "runtime" / "cloudflare.py"
    runtime_text = runtime.read_text(encoding="utf-8") if runtime.exists() else ""
    for scene_id, body in scenes.items():
        entry = re.search(r"entry_text:\s*(['\"])(.*?)\1", body, re.DOTALL)
        if entry and (entry.group(2).endswith("\\n") or entry.group(2).endswith(" ")):
            findings.append(_finding("prompt_hygiene", scene_id, "entry_text ends with stray whitespace."))
        if "You must also tell it:" in runtime_text:
            findings.append(
                _finding("prompt_hygiene", scene_id, "Prompt contains the garbled clause 'You must also tell it:'.")
            )
        estimate = len(body) + sum(
            len(str(item)) for item in knowledge.get("knowledge", []) if scene_id in item.get("available_in_scenes", [])
        )
        if estimate > 12000:
            findings.append(
                _finding(
                    "prompt_hygiene",
                    scene_id,
                    f"Estimated turn payload is {estimate} characters, exceeding the 12000-character budget.",
                )
            )
    if len(runtime_text) > 18000:
        findings.append(
            _finding(
                "prompt_hygiene", "package", "Prompt boilerplate is oversized at more than 18000 source characters."
            )
        )

    handoff = {item.get("scene_id"): item.get("handoff_after_turns", 0) for item in pacing.get("scenes", [])}
    for scene_id, body in scenes.items():
        beats = len(re.findall(rf"^### Scene {re.escape(scene_id)}\.\d+\b", body, re.MULTILINE))
        if scene_id in handoff and handoff[scene_id] < beats:
            findings.append(
                _finding(
                    "beats_without_turns",
                    scene_id,
                    f"Scene has {beats} beats but only {handoff[scene_id]} handoff turns.",
                )
            )
    return {"scenes": list(scene_ids), "findings": findings}


def _markdown(report: dict[str, Any]) -> str:
    findings = report["findings"]
    lines = ["# Story package audit", "", f"**Findings:** {len(findings)}", ""]
    for scene_id in report["scenes"]:
        lines.extend([f"## Scene {scene_id}", ""])
        scene_findings = [item for item in findings if item["scene_id"] == scene_id]
        lines.extend([f"- **{item['check']}** — {item['detail']}" for item in scene_findings] or ["No findings."])
        lines.append("")
    package_findings = [item for item in findings if item["scene_id"] not in report["scenes"]]
    if package_findings:
        lines.extend(["## Package", ""])
        lines.extend(f"- **{item['check']}** — {item['detail']}" for item in package_findings)
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit a freytag-forge story package.")
    parser.add_argument("package_root", type=Path)
    parser.add_argument("--markdown", type=Path)
    args = parser.parse_args()
    report = audit_package(args.package_root)
    if args.markdown:
        args.markdown.write_text(_markdown(report), encoding="utf-8")
    else:
        print(json.dumps(report, indent=2))
    return int(bool(report["findings"]))


if __name__ == "__main__":
    raise SystemExit(main())
