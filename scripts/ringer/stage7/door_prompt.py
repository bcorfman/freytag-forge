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
PERIMETER_SENTENCE = (
    "Kristin and Brandon are at the facility perimeter. Their false identities have passed the first security checks."
)
CORRIDOR_SENTENCE = (
    "Kristin and Brandon have opened a restricted infrastructure corridor, gaining access to the facility and its "
    "limited inspection console."
)
LIMITS_SENTENCE = (
    "Kristin notes its limits before they move on: it can report faults and cycle noncritical systems, "
    "but it cannot open detention cells or alter the main flood controls."
)
GROUNDED_LINES = (
    "cooling-service archive panel is beside the inspection console in the infrastructure corridors.",
    "The cooling-service archive panel leads directly from the infrastructure corridors into the records archive.",
    "The cooling-service archive panel opens with a push.",
    "Using the cooling-service archive panel requires no further credentials.",
)
GROUNDED_ANCHORS = (
    "- facility gate is at the facility perimeter.",
    "- This happens now. Show it in the scene: A second credential check threatens their inspector cover.",
)
ARMS = ("control", "review", "stale-scene", "wording", "fixed-control", "bridge")
DOOR_REPLACEMENTS = {
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

SOURCE_REPLACEMENTS = {
    "location": (
        (
            "CONSTRAINTS",
            f"Brandon Corfman may say this aloud: {PERIMETER_SENTENCE}",
            "Brandon Corfman may say this aloud: Their false identities have passed the first security checks.",
        ),
    ),
    "limits": (
        (
            "SCENE",
            CORRIDOR_SENTENCE,
            f"{CORRIDOR_SENTENCE} {LIMITS_SENTENCE}",
        ),
        (
            "CONSTRAINTS",
            f"Brandon Corfman may say this aloud: {CORRIDOR_SENTENCE}",
            f"Brandon Corfman may say this aloud: {CORRIDOR_SENTENCE} {LIMITS_SENTENCE}",
        ),
    ),
}

PROMPT_EXPERIMENTS = {
    "door": {"arms": ARMS, "replacements": DOOR_REPLACEMENTS},
    "source": {"arms": ("control", "location", "limits"), "replacements": SOURCE_REPLACEMENTS},
    "completion": {"arms": ("control", "no-finish"), "replacements": {}},
    "grounded": {"arms": ("control", "grounded"), "replacements": {}},
}
REPLACEMENTS = DOOR_REPLACEMENTS


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


def patch_prompt(selection: PromptSelection, arm: str, experiment: str = "door") -> dict[str, Any]:
    if experiment not in PROMPT_EXPERIMENTS:
        raise ValueError(f"unknown experiment {experiment}")
    if arm not in PROMPT_EXPERIMENTS[experiment]["arms"]:
        raise ValueError(f"unknown arm {arm}")
    original = selection.user
    sections = _sections(original)
    patched_sections = dict(sections)
    if experiment == "door":
        global_credential = original.count("Brandon prepares technical credentials while Kristin chooses")
        if global_credential != 2:
            raise AssertionError(f"credential sentence global count is {global_credential}, expected 2")
    elif experiment == "source":
        perimeter = original.count(PERIMETER_SENTENCE)
        corridor = original.count(CORRIDOR_SENTENCE)
        if perimeter != 1:
            raise AssertionError(f"perimeter sentence global count is {perimeter}, expected 1")
        if corridor != 2:
            raise AssertionError(f"opened-corridor sentence global count is {corridor}, expected 2")
    elif experiment == "grounded" and arm == "grounded":
        constraints = sections["CONSTRAINTS"]
        existing = [line for line in GROUNDED_LINES if line in original]
        if existing:
            raise AssertionError(f"grounded line already present: {existing[0]!r}")
        if not constraints.endswith("\n\n"):
            raise AssertionError("grounded CONSTRAINTS section must end with a blank line")
        body = constraints.rstrip("\n")
        if not any(body.endswith(anchor) for anchor in GROUNDED_ANCHORS):
            raise AssertionError("grounded CONSTRAINTS section lacks its facility-gate anchor")
        patched_sections["CONSTRAINTS"] = body + "\n" + "\n".join(f"- {line}" for line in GROUNDED_LINES) + "\n\n"
    for section, old, new in PROMPT_EXPERIMENTS[experiment]["replacements"].get(arm, ()):
        patched_sections[section] = _replace_line(patched_sections[section], section, old, new)
    # Replace section bodies at their original offsets, preserving all separators.
    patched = original
    for section in SECTIONS:
        old_body = sections[section]
        patched_body = patched_sections[section]
        if old_body != patched_body:
            patched = patched.replace(old_body, patched_body, 1)
    original_system = selection.system
    patched_system = original_system
    if experiment == "completion" and arm == "no-finish":
        removed = "Finish each action the player gives.\n"
        occurrences = original_system.count(removed)
        if occurrences != 1:
            raise AssertionError(f"finish instruction count is {occurrences}, expected 1")
        patched_system = original_system.replace(removed, "", 1)
    return {
        "arm": arm,
        "system": patched_system,
        "user": patched,
        "original_system": original_system,
        "original_user": original,
        "hashes": {
            "original_system": sha256_text(original_system),
            "system": sha256_text(patched_system),
            "original_user": sha256_text(original),
            "user": sha256_text(patched),
        },
        "system_diff": "".join(
            difflib.unified_diff(
                original_system.splitlines(True),
                patched_system.splitlines(True),
                fromfile="original_system",
                tofile=arm,
            )
        ),
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


def prompt_plan(experiment: str = "door", n: int = 12) -> list[tuple[int, str]]:
    if experiment not in PROMPT_EXPERIMENTS:
        raise ValueError(f"unknown experiment {experiment}")
    return [(rep, arm) for rep in range(1, n + 1) for arm in PROMPT_EXPERIMENTS[experiment]["arms"]]
