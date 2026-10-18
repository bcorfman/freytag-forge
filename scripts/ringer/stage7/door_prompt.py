"""Deterministic prompt and fixed-transition material for the Stage 7 screen."""

from __future__ import annotations

import difflib
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from unittest import mock

ROOT = Path(__file__).resolve().parents[3]
PROMPT_FIXTURE = ROOT / "bench/results/stage7-blind-raw/attempt-1/e2e-blind-player-prompts.json"
TRANSCRIPT_FIXTURE = ROOT / "bench/results/stage7-blind-raw/attempt-1/e2e-blind-player.json"
SECTIONS = ("CHARACTERS", "SCENE", "THINGS", "CONSTRAINTS", "PLAYER")
COMMAND = "Look for a concealed route or access panel leading from the service corridors to the detention area."
FROZEN_GROUNDED_VARIATION = ROOT / "bench/variations/stage7-door-grounded-control.json"
CURRENT_GROUNDED_VARIATION = ROOT / "bench/variations/stage7-door-grounded.json"
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
THINGS_ASSUMPTION = (
    "best-case design test: assumes the per-turn match call refers to the panel for the recorded command; "
    "the real selection rate is not measured by this screen"
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


def _section_lines(user: str, *, allow_missing_things: bool = False) -> dict[str, tuple[str, ...]]:
    sections = _sections(user) if not allow_missing_things else _sections_for_derivation(user)
    return {name: tuple(line for line in body.splitlines() if line.startswith("- ")) for name, body in sections.items()}


def _sections_for_derivation(user: str) -> dict[str, str]:
    matches = list(re.finditer(r"(?m)^([A-Z]+):\n", user))
    found = {m.group(1): m for m in matches if m.group(1) in SECTIONS}
    required = {"CHARACTERS", "SCENE", "CONSTRAINTS", "PLAYER"}
    if not required <= set(found):
        raise AssertionError(f"expected derivation sections, found {sorted(found)}")
    ordered = sorted(found.items(), key=lambda item: item[1].start())
    result = {
        name: user[match.end() : (ordered[index + 1][1].start() if index + 1 < len(ordered) else len(user))]
        for index, (name, match) in enumerate(ordered)
    }
    result.setdefault("THINGS", "")
    return result


def _prompt_for_package(path: Path) -> str:
    from bench.core import load_variation, prompt_for

    return prompt_for(load_variation(path), "2A", COMMAND)["user"]


def grounded_additions(frozen_user: str | None = None, current_user: str | None = None) -> dict[str, tuple[str, ...]]:
    """Return current-package prompt lines absent from the frozen prompt.

    The package prompts are built through the same offline path as ``bench
    prompt``. Section subtraction is deliberately line-based so authored
    punctuation and separators remain untouched by the experiment patch.
    """

    derive_emulated_things = frozen_user is None and current_user is None
    frozen_user = _prompt_for_package(FROZEN_GROUNDED_VARIATION) if frozen_user is None else frozen_user
    current_user = _prompt_for_package(CURRENT_GROUNDED_VARIATION) if current_user is None else current_user
    frozen = _section_lines(frozen_user, allow_missing_things=True)
    current = _section_lines(current_user, allow_missing_things=True)
    additions: dict[str, tuple[str, ...]] = {}
    for section in SECTIONS:
        removed = [line for line in frozen[section] if line not in current[section]]
        if removed:
            raise AssertionError(f"grounded derivation removed {section} line(s): {removed!r}")
        if section not in ("SCENE", "THINGS", "CONSTRAINTS") and current[section] != frozen[section]:
            raise AssertionError(f"grounded derivation changed forbidden section {section}")
        added = tuple(line for line in current[section] if line not in frozen[section])
        if added:
            additions[section] = added
    if derive_emulated_things:
        emulated = things_emulation()
        frozen_things = tuple(emulated["frozen"][1:])
        current_things = tuple(emulated["current"][1:])
        thing_additions = tuple(line for line in current_things if line not in frozen_things)
        if thing_additions:
            additions["THINGS"] = thing_additions
    if not any(additions.values()):
        raise AssertionError("grounded derivation found no additions")
    return additions


def things_emulation() -> dict[str, list[str]]:
    """Render the recorded-command THINGS block through ItemFactsProvider offline."""

    from bench.core import load_variation, package_and_state
    from storygame.runtime.cloudflare import CloudflareTurnProvider
    from storygame.runtime.item_facts import ItemFactsProvider

    rendered: dict[str, list[str]] = {}
    for label, path in (("frozen", FROZEN_GROUNDED_VARIATION), ("current", CURRENT_GROUNDED_VARIATION)):
        variation = load_variation(path)
        package, state = package_and_state(variation, "2A")
        provider = ItemFactsProvider(
            worker_url="",
            token="",
            state=state,
            prompt_variant=variation["_prompt_variant"],
            item_facts={},
            mode="single_call",
            seed_from_package=True,
            held_by=False,
        )
        provider._world().set_unplaced(package.world.protagonist_id, "infrastructure corridors")
        provider._ensure_scene_seeded()
        with mock.patch.object(
            CloudflareTurnProvider,
            "_request_item_facts",
            lambda self, payload: {"refers": ["access panel"], "same_as": {}, "kind": {}},
        ):
            provider.prepare_turn(COMMAND)
        if label == "current" and not getattr(provider, "_last_item_facts_match", {}).get("engine_resolutions"):
            raise AssertionError("things emulation stub reply was not consumed by the item-facts engine")
        rendered[label] = provider._things_block(narration=True).splitlines()
    return rendered


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
        additions = grounded_additions()
        for section, lines in additions.items():
            body = sections[section]
            if not body.endswith("\n\n"):
                raise AssertionError(f"grounded {section} section must end with a blank line")
            existing = [line for line in lines if line in _section_lines(original)[section]]
            if existing:
                raise AssertionError(f"grounded line already present: {existing[0]!r}")
            if section == "THINGS":
                first_item = body.find("- ")
                if first_item < 0:
                    raise AssertionError("grounded THINGS section has no recorded item line")
                inserted = "".join(f"{line}\n" for line in lines)
                patched_sections[section] = body[:first_item] + inserted + body[first_item:]
            else:
                patched_sections[section] = body.rstrip("\n") + "\n" + "\n".join(lines) + "\n\n"
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
    result = {
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
    if experiment == "grounded" and arm == "grounded":
        result["things_assumption"] = THINGS_ASSUMPTION
    return result


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
