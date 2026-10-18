"""Deterministic prompt and fixed-transition material for the Stage 7 screen."""

from __future__ import annotations

import difflib
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
PROMPT_FIXTURE = ROOT / "bench/results/stage7-blind-raw/attempt-1/e2e-blind-player-prompts.json"
TRANSCRIPT_FIXTURE = ROOT / "bench/results/stage7-blind-raw/attempt-1/e2e-blind-player.json"
SECTIONS = ("CHARACTERS", "SCENE", "THINGS", "CONSTRAINTS", "PLAYER")
COMMAND = "Look for a concealed route or access panel leading from the service corridors to the detention area."
ARMS = ("control", "review", "stale-scene", "wording", "fixed-control", "bridge")
REPLACEMENTS = {
    "review": (
        (
            "CONSTRAINTS",
            "This happens now. Show it in the scene: A second credential check threatens their inspector cover.",
            "This happens now. Show it in the scene: Their inspector cover faces a second review.",
        ),
    ),
    "stale-scene": (
        (
            "SCENE",
            "Kristin must plan a way into the facility. False identities are a possible cover.",
            "False identities are a possible cover.",
        ),
        (
            "SCENE",
            "Brandon prepares technical credentials while Kristin chooses how much of the real cooling-water "
            "and ventilation risk to put in their lie.",
            "Brandon prepared their technical credentials for the facility inspection.",
        ),
        (
            "CONSTRAINTS",
            "Brandon Corfman may say this aloud: Brandon prepares technical credentials while Kristin chooses "
            "how much of the real cooling-water and ventilation risk to put in their lie.",
            "Brandon Corfman may say this aloud: Brandon prepared their technical credentials "
            "for the facility inspection.",
        ),
    ),
    "wording": (("PLAYER", COMMAND, "Search the service corridors for a route to the detention area."),),
}


@dataclass(frozen=True)
class PromptSelection:
    system: str
    user: str
    source_path: str
    replicate: int = 1
    scene: str = "2A"
    turn: int = 7


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def select_prompt(path: Path = PROMPT_FIXTURE) -> PromptSelection:
    data = json.loads(path.read_text(encoding="utf-8"))
    reps = [x for x in data.get("replicates", []) if x.get("replicate") == 1]
    if len(reps) != 1:
        raise AssertionError(f"expected one replicate 1, found {len(reps)}")
    scenes = [x for x in reps[0].get("scenes", []) if x.get("scene") == "2A"]
    if len(scenes) != 1:
        raise AssertionError(f"expected one scene 2A, found {len(scenes)}")
    prompts = [x for x in scenes[0].get("prompts", []) if x.get("turn") == 7]
    if len(prompts) != 1:
        raise AssertionError(f"expected one turn 7, found {len(prompts)}")
    prompt = prompts[0].get("prompt", {})
    if not isinstance(prompt.get("system"), str) or not prompt["system"]:
        raise AssertionError("turn 7 system prompt is not a nonempty string")
    if not isinstance(prompt.get("user"), str) or not prompt["user"]:
        raise AssertionError("turn 7 user prompt is not a nonempty string")
    return PromptSelection(prompt["system"], prompt["user"], str(path))


def _sections(user: str) -> dict[str, str]:
    matches = list(re.finditer(r"(?m)^([A-Z]+):\n", user))
    section_matches = [m for m in matches if m.group(1) in SECTIONS]
    found = {m.group(1): m for m in section_matches}
    if set(found) != set(SECTIONS):
        raise AssertionError(f"expected sections {SECTIONS}, found {sorted(found)}")
    if len(section_matches) != len(SECTIONS):
        raise AssertionError("duplicate prompt section")
    ordered = sorted(found.items(), key=lambda item: item[1].start())
    result = {}
    for index, (name, match) in enumerate(ordered):
        end = ordered[index + 1][1].start() if index + 1 < len(ordered) else len(user)
        result[name] = user[match.end() : end]
    return result


def _replace_line(section: str, text: str, old: str, new: str) -> str:
    lines = section.splitlines(keepends=True)
    matches = [i for i, line in enumerate(lines) if line.rstrip("\r\n").removeprefix("- ") == old]
    if len(matches) != 1:
        raise AssertionError(f"expected one scoped line {old!r}, found {len(matches)}")
    line = lines[matches[0]]
    ending = "\n" if line.endswith("\n") else ""
    lines[matches[0]] = "- " + new + ending
    return "".join(lines)


def patch_prompt(selection: PromptSelection, arm: str) -> dict[str, Any]:
    if arm not in ARMS:
        raise ValueError(f"unknown arm {arm}")
    original = selection.user
    sections = _sections(original)
    global_credential = original.count("Brandon prepares technical credentials while Kristin chooses")
    if global_credential != 2:
        raise AssertionError(f"credential sentence global count is {global_credential}, expected 2")
    patched_sections = dict(sections)
    for section, old, new in REPLACEMENTS.get(arm, ()):
        patched_sections[section] = _replace_line(patched_sections[section], section, old, new)
    # Replace section bodies at their original offsets, preserving all separators.
    patched = original
    for section in SECTIONS:
        old_body = sections[section]
        patched_body = patched_sections[section]
        if old_body != patched_body:
            patched = patched.replace(old_body, patched_body, 1)
    return {
        "arm": arm,
        "system": selection.system,
        "user": patched,
        "original_user": original,
        "hashes": {
            "system": sha256_text(selection.system),
            "original_user": sha256_text(original),
            "user": sha256_text(patched),
        },
        "diff": "".join(
            difflib.unified_diff(original.splitlines(True), patched.splitlines(True), fromfile="original", tofile=arm)
        ),
        "source_path": selection.source_path,
    }


def recorded_transition() -> dict[str, Any]:
    data = json.loads(TRANSCRIPT_FIXTURE.read_text(encoding="utf-8"))
    reps = [x for x in data["replicates"] if x.get("replicate") == 1]
    scene = [x for x in reps[0]["scenes"] if x.get("scene") == "2A"]
    turns = [x for x in scene[0]["turns"] if x.get("turn") == 7]
    if len(reps) != len(scene) != len(turns) != 1:
        raise AssertionError("recorded transition anchors are not unique")
    row = turns[0]
    if (
        row.get("input") != COMMAND
        or row.get("rejected")
        or row.get("scene_id") != "2B"
        or row.get("transition_cause") != "earned"
    ):
        raise AssertionError("recorded turn 7 does not have the required transition contract")
    return row


def prompt_plan() -> list[tuple[int, str]]:
    return [(rep, arm) for rep in range(1, 13) for arm in ARMS]
