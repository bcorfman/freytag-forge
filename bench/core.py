"""Prompt assembly, live execution, and statistics for the local bench."""

from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import tempfile
import time
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean, stdev
from typing import Any

from bench.item_facts import ItemFactsProvider, package_seed, validate_item_facts
from storygame.runtime.cloudflare import (
    DEFAULT_OUTPUT_EXAMPLE,
    CloudflareTurnProvider,
    NarrationProviderError,
)
from storygame.runtime.contracts import RuntimeContractError, join_narration
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.knowledge import KnowledgeProjector
from storygame.runtime.state import RuntimeState
from storygame.runtime.validation import ProposalValidationError, predicate_matches
from storygame.story_package.loader import load_story_package

CRITERIA = (
    "canon_consistent",
    "scene_local",
    "progressive",
    "rich",
    "protected_safe",
    "exit_motivated",
    "rewards_investigation",
)
ESCALATION_CRITERIA = (
    "cue_points_to_missing_thread",
    "complication_creates_pressure_without_unearned_knowledge",
    "no_pre_reveal_disclosure",
)
ESCALATION_VERDICTS = ("yes", "no", "not_applicable")
CONTINUITY_CRITERIA = ("contradicts_stated_fact", "protagonist_acts_beyond_command", "restarts_scene")
CONTINUITY_VERDICTS = ("yes", "no")
FACT_TRACKING_CRITERIA = (
    "facts_after_correct",
    "missed_change",
    "invented_change",
    "narration_contradicts_given_facts",
    "dropped_true_condition",
)
FACT_TRACKING_VERDICTS = ("yes", "no")
FACT_CHANGE_CAUSES = ("command", "narrator")
REFERENCE_MDE_AT_FOUR = 3.87
DEFAULT_NARRATOR_MODEL = "@cf/meta/llama-3.1-8b-instruct-fast"
LEDGER_PATH = Path(__file__).resolve().parent / "results" / "ledger.jsonl"
T_CRITICAL_95 = {
    1: 12.706,
    2: 4.303,
    3: 3.182,
    4: 2.776,
    5: 2.571,
    6: 2.447,
    7: 2.365,
    8: 2.306,
    9: 2.262,
    10: 2.228,
    11: 2.201,
    12: 2.179,
    13: 2.160,
    14: 2.145,
    15: 2.131,
    16: 2.120,
    17: 2.110,
    18: 2.101,
    19: 2.093,
    20: 2.086,
    21: 2.080,
    22: 2.074,
    23: 2.069,
    24: 2.064,
    25: 2.060,
    26: 2.056,
    27: 2.052,
    28: 2.048,
    29: 2.045,
    30: 2.042,
}


def load_dotenv() -> None:
    """Load the local env file without adding a dotenv dependency."""

    env_path = Path(__file__).resolve().parents[1] / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.removeprefix("export ").strip()
        value = value.strip().strip("\"'")
        os.environ.setdefault(key, value)


DEFAULT_PACKAGE = "data/stories/continuity-initiative"


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"cannot read JSON file {path}: {error}") from error
    if not isinstance(value, dict):
        raise ValueError(f"JSON file {path} must contain an object")
    return value


def load_variation(path: Path) -> dict[str, Any]:
    return resolve_variation(read_json(path), path)


def default_variation(package: str = DEFAULT_PACKAGE) -> dict[str, Any]:
    """Resolve the engine's shipped prompt configuration for one story package.

    Inspecting a prompt does not require a variation file. A variation exists to
    hold ONE side of a comparison; asking to see what the engine actually sends
    should not make the caller invent an experiment first.
    """

    return resolve_variation({"name": "default", "story_package": package}, Path.cwd() / "default.json")


def resolve_variation(variation: dict[str, Any], path: Path) -> dict[str, Any]:
    name = variation.get("name")
    if not isinstance(name, str) or not name:
        raise ValueError("variation must have a non-empty name")
    package_value = variation.get("story_package", variation.get("package"))
    if not isinstance(package_value, str) or not package_value:
        raise ValueError("variation must name story_package")
    escalation_judge = variation.get("escalation_judge", False)
    if not isinstance(escalation_judge, bool):
        raise ValueError("escalation_judge must be a boolean")
    fixed_turns = variation.get("fixed_turns")
    if fixed_turns is not None and (
        isinstance(fixed_turns, bool) or not isinstance(fixed_turns, int) or fixed_turns <= 0
    ):
        raise ValueError("fixed_turns must be a positive integer")
    continuity_judge = variation.get("continuity_judge", False)
    if not isinstance(continuity_judge, bool):
        raise ValueError("continuity_judge must be a boolean")
    fact_tracking_judge = variation.get("fact_tracking_judge", False)
    if not isinstance(fact_tracking_judge, bool):
        raise ValueError("fact_tracking_judge must be a boolean")
    item_facts = None
    if "item_facts" in variation:
        item_facts = validate_item_facts(variation["item_facts"])
    entry_state = variation.get("entry_state", "bare")
    if not isinstance(entry_state, str) or entry_state not in {"bare", "thorough"}:
        raise ValueError("entry_state must be bare or thorough")
    variation["_entry_state"] = entry_state
    variation["_fixed_turns"] = fixed_turns
    variation["_fact_tracking_judge"] = fact_tracking_judge
    variation["_item_facts"] = item_facts
    variation["_path"] = str(path.resolve())
    package_path = resolve_package(path, package_value)
    variation["_package_path"] = str(materialize_package(package_path, variation.get("overrides")))
    if item_facts is not None and variation.get("item_facts", {}).get("seed_from_package", False):
        package = load_story_package(Path(variation["_package_path"]))
        hand_seed = item_facts[1]
        package_names: set[str] = set()
        for scene in package.scenes:
            state = RuntimeState(
                package=package,
                current_scene_id=scene.metadata.scene_id,
                phase=scene.metadata.freytag_phase,
            )
            state._assert_scene_entry_fact(scene.metadata.scene_id)
            package_names.update(package_seed(package, state, scene.metadata.scene_id)[0])
        clashes = package_names & set(hand_seed)
        if clashes:
            raise ValueError(f"item_facts seed names clash with package things: {sorted(clashes)!r}")
    continue_to = variation.get("continue_to")
    if continue_to is not None:
        if fixed_turns is None:
            raise ValueError("continue_to requires a top-level fixed_turns")
        if not isinstance(continue_to, dict):
            raise ValueError("continue_to must be an object")
        target_scene = continue_to.get("scene")
        target_turns = continue_to.get("fixed_turns")
        target_script = continue_to.get("script")
        if not isinstance(target_scene, str) or not target_scene:
            raise ValueError("continue_to.scene must name a scene")
        if isinstance(target_turns, bool) or not isinstance(target_turns, int) or target_turns < 1:
            raise ValueError("continue_to.fixed_turns must be a positive integer")
        if not isinstance(target_script, str) or not target_script:
            raise ValueError("continue_to.script must name a script")
        package = load_story_package(Path(variation["_package_path"]))
        if target_scene not in {scene.metadata.scene_id for scene in package.scenes}:
            raise ValueError(f"continue_to scene {target_scene!r} is not in the story package")
        scripts = variation.get("scripts", {})
        if not isinstance(scripts, dict) or target_scene not in scripts:
            raise ValueError(f"continue_to script {target_script!r} is not defined for scene {target_scene}")
        if target_script not in {script["name"] for script in scripts_for(variation, target_scene)}:
            raise ValueError(f"continue_to script {target_script!r} is not defined for scene {target_scene}")
        variation["_continue_to"] = {
            "scene": target_scene,
            "fixed_turns": target_turns,
            "script": target_script,
        }
    variation["_package_hash"] = hash_package(Path(variation["_package_path"]))
    prompt = variation.get("system_prompt", {})
    user_prompt = variation.get("user_prompt", {})
    if not isinstance(prompt, dict) or not isinstance(user_prompt, dict):
        raise ValueError("system_prompt and user_prompt must be objects")
    beat_delivery = user_prompt.get("beat_delivery", "details")
    if beat_delivery not in {"details", "prose"}:
        raise ValueError("user_prompt.beat_delivery must be details or prose")
    rules = prompt.get("rules")
    if rules is not None and (not isinstance(rules, list) or not all(isinstance(rule, str) for rule in rules)):
        raise ValueError("system_prompt.rules must be a list of strings")
    include_output_example = prompt.get("include_output_example", True)
    if not isinstance(include_output_example, bool):
        raise ValueError("system_prompt.include_output_example must be a boolean")
    if "output_example" in prompt and not isinstance(prompt["output_example"], str):
        raise ValueError("system_prompt.output_example must be a string")
    use_runtime_output_example = prompt.get("use_runtime_output_example", False)
    if not isinstance(use_runtime_output_example, bool):
        raise ValueError("system_prompt.use_runtime_output_example must be a boolean")
    if use_runtime_output_example and "output_example" in prompt:
        raise ValueError("use_runtime_output_example cannot be combined with output_example")
    resolved_output_example = (
        None
        if use_runtime_output_example
        else prompt.get("output_example", DEFAULT_OUTPUT_EXAMPLE if include_output_example else None)
    )
    if "output_example" in prompt:
        include_output_example = True
    auto_select_unambiguous_candidates = prompt.get("auto_select_unambiguous_candidates", True)
    if not isinstance(auto_select_unambiguous_candidates, bool):
        raise ValueError("system_prompt.auto_select_unambiguous_candidates must be a boolean")
    positive_selection_example = prompt.get("positive_selection_example", False)
    if not isinstance(positive_selection_example, bool):
        raise ValueError("system_prompt.positive_selection_example must be a boolean")
    model_grounding = prompt.get("model_grounding", True)
    if not isinstance(model_grounding, bool):
        raise ValueError("system_prompt.model_grounding must be a boolean")
    narrow_to_shadow_match = prompt.get("narrow_to_shadow_match", False)
    if not isinstance(narrow_to_shadow_match, bool):
        raise ValueError("system_prompt.narrow_to_shadow_match must be a boolean")
    variation["_prompt_variant"] = {
        **({"rules": rules} if rules is not None else {}),
        "include_output_example": include_output_example,
        **({"output_example": resolved_output_example} if not use_runtime_output_example else {}),
        "beat_delivery": beat_delivery,
        "auto_select_unambiguous_candidates": auto_select_unambiguous_candidates,
        "positive_selection_example": positive_selection_example,
        "model_grounding": model_grounding,
        "narrow_to_shadow_match": narrow_to_shadow_match,
    }
    variation["_resolved_rules"] = list(rules) if rules is not None else None
    variation["_resolved_output_example"] = resolved_output_example
    variation["_variation_hash"] = stable_hash(
        {
            "rules": variation["_resolved_rules"],
            "include_output_example": include_output_example,
            "output_example": resolved_output_example,
            "use_runtime_output_example": use_runtime_output_example,
            "beat_delivery": beat_delivery,
            "auto_select_unambiguous_candidates": auto_select_unambiguous_candidates,
            "positive_selection_example": positive_selection_example,
            "model_grounding": model_grounding,
            "narrow_to_shadow_match": narrow_to_shadow_match,
        }
    )
    variation["_story_package_value"] = package_value
    return variation


def stable_hash(value: object) -> str:
    """Hash JSON content independently of paths, whitespace, or key order."""

    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def hash_package(root: Path) -> str:
    """Hash every effective package file, including its relative filename."""

    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        content = path.read_bytes()
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()


def materialize_package(package_path: Path, overrides: object) -> Path:
    """Return the original package or an isolated effective copy with patches."""

    if overrides is None:
        return package_path
    if not isinstance(overrides, dict):
        raise ValueError("variation.overrides must be an object")
    temporary = tempfile.TemporaryDirectory(prefix="bench-package-")
    effective = Path(temporary.name)
    shutil.copytree(package_path, effective, dirs_exist_ok=True)
    # Keep the TemporaryDirectory alive for the duration of the command and any
    # direct test using the resolved variation.
    _TEMPORARY_PACKAGES.append(temporary)
    for filename, patch in overrides.items():
        if not isinstance(filename, str) or not filename:
            raise ValueError("override filenames must be non-empty strings")
        relative = Path(filename)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"override path escapes story package: {filename}")
        target = effective / relative
        if not target.is_file():
            raise ValueError(f"override file does not exist in story package: {filename}")
        if isinstance(patch, str):
            target.write_text(patch, encoding="utf-8")
            continue
        if not isinstance(patch, dict):
            raise ValueError(f"override for {filename} must be a replacement object or string")
        replacements = patch.get("replacements")
        if not isinstance(replacements, list) or not replacements:
            raise ValueError(f"override for {filename} must contain replacements")
        content = target.read_text(encoding="utf-8")
        for replacement in replacements:
            if not isinstance(replacement, dict):
                raise ValueError(f"replacement for {filename} must be an object")
            old, new = replacement.get("old"), replacement.get("new")
            if not isinstance(old, str) or not old or not isinstance(new, str):
                raise ValueError(f"replacement for {filename} needs non-empty old and string new")
            occurrences = content.count(old)
            if occurrences != 1:
                raise ValueError(f"replacement for {filename} expected one {old!r}, found {occurrences}")
            content = content.replace(old, new, 1)
        target.write_text(content, encoding="utf-8")
    return effective


_TEMPORARY_PACKAGES: list[tempfile.TemporaryDirectory[str]] = []


def resolve_package(variation_path: Path, package_value: str) -> Path:
    candidate = Path(package_value).expanduser()
    if candidate.is_absolute():
        return candidate
    for base in (Path.cwd(), variation_path.resolve().parents[2], variation_path.resolve().parent):
        resolved = (base / candidate).resolve()
        if resolved.is_dir():
            return resolved
    return (Path.cwd() / candidate).resolve()


def package_and_state(variation: dict[str, Any], scene_id: str | None = None) -> tuple[Any, RuntimeState]:
    package = load_story_package(Path(variation["_package_path"]))
    target_scene = scene_id or package.scenes[0].metadata.scene_id
    scene = next((item for item in package.scenes if item.metadata.scene_id == target_scene), None)
    if scene is None:
        raise ValueError(f"scene {target_scene} is not in package {package.story_id}")
    state = RuntimeState(package=package, current_scene_id=target_scene, phase=scene.metadata.freytag_phase)
    state._assert_scene_entry_fact(target_scene)
    return package, state


def advance_state_to_scene(package: Any, state: RuntimeState, scene_id: str) -> None:
    """Advance an existing state to a scene with the deterministic thorough player."""

    if state.current_scene_id == scene_id:
        return
    from storygame.personas import PERSONAS, _legacy_package, _ScriptedProvider, _select_thorough, _turn_cap

    if scene_id not in {scene.metadata.scene_id for scene in package.scenes}:
        raise ValueError(f"scene {scene_id} is not in package {package.story_id}")
    persona_package = _legacy_package(package)
    provider = _ScriptedProvider(persona_package, state)
    engine = RuntimeEngine(state, provider)
    for _ in range(_turn_cap(persona_package)):
        if state.current_scene_id == scene_id:
            return
        engine._activate_pacing()
        projection = engine.projector.project(state, "player", "")
        selected = _select_thorough(persona_package, state, projection.candidates)
        provider.selected = (selected,) if selected else ()
        try:
            engine.turn(PERSONAS["thorough"])
        except (ProposalValidationError, RuntimeContractError):
            provider.selected = ()
            engine.turn(PERSONAS["thorough"])
    if state.current_scene_id != scene_id:
        raise RuntimeError(f"scene {scene_id} was not reached by offline thorough seeding")


def seeded_state_for_scene(variation: dict[str, Any], scene_id: str) -> tuple[Any, RuntimeState]:
    """Build the configured entry state without making a narration request."""

    if variation.get("_entry_state", variation.get("entry_state", "bare")) == "bare":
        return package_and_state(variation, scene_id)

    package = load_story_package(Path(variation["_package_path"]))
    scene_ids = {scene.metadata.scene_id for scene in package.scenes}
    if scene_id not in scene_ids:
        raise ValueError(f"scene {scene_id} is not in package {package.story_id}")
    state = RuntimeState.bootstrap(package)
    if state.current_scene_id == scene_id:
        return package, state

    advance_state_to_scene(package, state, scene_id)
    return package, state


def entry_state(state: RuntimeState, *, seeded_by: str = "bare") -> dict[str, Any]:
    """Describe the state used when a scene is benched."""

    projector = KnowledgeProjector()
    return {
        "scene_id": state.current_scene_id,
        "committed_knowledge_count": len(projector.project(state, "player", "").committed_knowledge),
        "earned_knowledge_count": sum(
            KnowledgeProjector._established(item, state) and KnowledgeProjector._visible_to(item, "player")
            for item in state.package.knowledge.knowledge
        ),
        "seeded_by": seeded_by,
    }


def preview_rules(variation: dict[str, Any], scene_id: str | None = None) -> list[str]:
    """Return the provider's rules without dispatching a narration request."""

    _, state = package_and_state(variation, scene_id)
    provider = CloudflareTurnProvider(worker_url="", token="", state=state, prompt_variant=variation["_prompt_variant"])
    provider.assemble_turn_prompt("")
    return list(provider._turn_rules())


def provider_for(state: RuntimeState, variation: dict[str, Any]) -> CloudflareTurnProvider:
    item_facts = variation.get("_item_facts")
    if item_facts is None and "item_facts" in variation:
        item_facts = validate_item_facts(variation["item_facts"])
    if item_facts is not None:
        mode, seed = item_facts
        seed_issues: list[str] = []
        if variation.get("item_facts", {}).get("seed_from_package", False):
            package_things, seed_issues = package_seed(state.package, state, state.current_scene_id)
            clashes = set(package_things) & set(seed)
            if clashes:
                raise ValueError(f"item_facts seed names clash with package things: {sorted(clashes)!r}")
            seed = {**package_things, **seed}
        return ItemFactsProvider.from_environment(
            state,
            prompt_variant=variation["_prompt_variant"],
            item_facts=seed,
            mode=mode,
            seed_issues=seed_issues,
        )
    return CloudflareTurnProvider.from_environment(state, prompt_variant=variation["_prompt_variant"])


def beats_for(package: Any, scene_id: str) -> list[Any]:
    """The authored beats of one scene, in authored order."""

    scene = next((item for item in package.scenes if item.metadata.scene_id == scene_id), None)
    if scene is None:
        raise ValueError(f"scene {scene_id} is not in package {package.story_id}")
    return sorted(scene.beats.values(), key=lambda beat: beat.id)


def resolve_beat(package: Any, scene_id: str, beat: str) -> Any:
    """Find one authored beat by its id, its ordinal, or its anchor slug."""

    available = beats_for(package, scene_id)
    wanted = beat.strip()
    for item in available:
        if wanted in (item.id, item.anchor) or wanted == item.id.split(".")[-1]:
            return item
    names = ", ".join(f"{item.id} ({item.title})" for item in available)
    raise ValueError(f"beat {beat!r} is not in scene {scene_id}; available beats are: {names}")


def establish_prior_beats(package: Any, state: RuntimeState, scene_id: str, beat: Any) -> tuple[str, ...]:
    """Commit what the beats before this one in the same scene already established.

    A prompt for beat N must show beats 1..N-1 as knowledge the player already
    holds, not as reveals still on offer, or the narrator is told the player has
    yet to learn something they learned two beats ago. A storylet counts as
    earlier only when every beat it links to is earlier, so a storylet spanning
    into the requested beat stays live and keeps offering its reveal.

    Storylets are OPTIONAL, and some exclude each other: SL-1A-B and SL-1A-D are
    both gated on continuity_initiative_known being false, so whichever fires
    first blocks the other for good. Assuming every earlier storylet fired would
    therefore assert a history no player could have had, and would pad the scene
    with knowledge from paths not taken. Each candidate's activation conditions
    are evaluated against the facts as they stand at that point, in beat order,
    and only what genuinely qualifies fires. What does fire is permanent: an
    optional storylet's effects are world knowledge from then on.

    Where a storylet has several authored realizations the first is applied.
    They are alternative dramatizations of the same fact effects, so the choice
    changes the prose a player would have read, never the knowledge that stands.
    """

    ordered = beats_for(package, scene_id)
    limit = ordered.index(beat)
    if limit == 0:
        return ()
    routes = {route.id: route for route in package.storylet_routes.storylets}
    prior_anchors: set[str] = set()
    established: list[str] = []
    for reached in ordered[:limit]:
        prior_anchors.add(reached.anchor)
        for storylet in package.storylets:
            if storylet.id in state.fired_event_ids or storylet.scene_id != scene_id:
                continue
            if not set(storylet.source_links) <= prior_anchors:
                continue
            route = routes.get(storylet.id)
            if route is None or not route.realizations:
                continue
            if not all(predicate_matches(item, state.facts) for item in route.activation_conditions):
                continue
            for operation in route.realizations[0].operations:
                value = str(operation.value).lower() if isinstance(operation.value, bool) else str(operation.value)
                state.facts.assert_fact(Fact(predicate=operation.fact_id, subject="story", value=value))
            state.fired_event_ids.add(storylet.id)
            established.append(storylet.id)
    return tuple(established)


def resolve_storylet(package: Any, scene_id: str, storylet_id: str) -> Any:
    """Find one storylet of a scene by id, case-insensitively."""

    available = [item for item in package.storylets if item.scene_id == scene_id]
    wanted = storylet_id.strip().upper()
    for item in available:
        if item.id.upper() == wanted:
            return item
    names = ", ".join(f"{item.id} ({item.title})" for item in available)
    raise ValueError(f"storylet {storylet_id!r} is not in scene {scene_id}; available storylets are: {names}")


def prompt_for(
    variation: dict[str, Any],
    scene_id: str,
    player_input: str,
    beat: str | None = None,
    storylet: str | None = None,
) -> dict[str, str]:
    package, state = package_and_state(variation, scene_id)
    item_facts = variation.get("_item_facts")
    if item_facts is None and "item_facts" in variation:
        item_facts = validate_item_facts(variation["item_facts"])
    if item_facts is not None:
        mode, seed = item_facts
        provider = ItemFactsProvider(
            worker_url="",
            token="",
            state=state,
            prompt_variant=variation["_prompt_variant"],
            item_facts=seed,
            mode=mode,
        )
        if variation.get("item_facts", {}).get("seed_from_package", False):
            package_things, seed_issues = package_seed(package, state, state.current_scene_id)
            if set(package_things) & set(seed):
                raise ValueError("item_facts seed names clash with package things")
            provider.item_facts = {**package_things, **provider.item_facts}
            provider.item_facts_seed_names = tuple(provider.item_facts)
            provider.item_facts_seed_issues = seed_issues
    else:
        provider = CloudflareTurnProvider(
            worker_url="", token="", state=state, prompt_variant=variation["_prompt_variant"]
        )
    RuntimeEngine(state, provider)._activate_pacing()
    if beat is not None and storylet is not None:
        raise ValueError("--beat and --storylet select the turn in different ways; name only one")
    if beat is not None:
        selected = resolve_beat(package, scene_id, beat)
        establish_prior_beats(package, state, scene_id, selected)
        # Pacing decides which beat is live on turn 1. Naming a beat asks to see a
        # different one, so its storylets are activated directly; the beat reaches
        # the prompt through the reveals those storylets offer.
        storylets = [item.id for item in package.storylets if selected.anchor in item.source_links]
        if not storylets:
            raise ValueError(
                f"beat {selected.id} ({selected.title}) has no storylet, so no turn can present it. "
                "Beats reach the narrator through the reveals their storylets offer."
            )
        state.active_event_ids.update(storylets)
    if storylet is not None:
        # One storylet in isolation, for reading a single reveal's own material.
        # Its earliest beat still fixes what the player has already been through.
        chosen = resolve_storylet(package, scene_id, storylet)
        ordered = beats_for(package, scene_id)
        by_anchor = {item.anchor: item for item in ordered}
        entry = min(
            (by_anchor[anchor] for anchor in chosen.source_links if anchor in by_anchor),
            key=lambda item: item.id,
            default=None,
        )
        if entry is not None:
            establish_prior_beats(package, state, scene_id, entry)
        # Exclusive by design: pacing may have made a neighbouring storylet live, and
        # its beat details would then read as part of this one's material.
        state.active_event_ids.clear()
        state.active_event_ids.add(chosen.id)
    assembled = provider.assemble_turn_prompt(player_input)
    context = assembled["context"]
    return {"system": str(assembled["system"]), "user": provider._section_user_prompt(context)}


_WORD_PATTERN = re.compile(r"\b[\w]+(?:[-'][\w]+)*\b", re.UNICODE)


def _example_words(text: str) -> tuple[str, ...]:
    return tuple(_WORD_PATTERN.findall(re.sub(r"\s+", " ", text).casefold()))


def has_example_leakage(narration: str, example: str | None) -> bool:
    """Return whether narration shares an eight-word contiguous span with example."""

    if not example:
        return False
    example_words = _example_words(example)
    narration_words = _example_words(narration)
    if len(example_words) < 8 or len(narration_words) < 8:
        return False
    spans = {example_words[index : index + 8] for index in range(len(example_words) - 7)}
    return any(narration_words[index : index + 8] in spans for index in range(len(narration_words) - 7))


def count_example_leakage(narrations: Iterable[str], example: str | None) -> int:
    """Count narration turns containing a distinctive span from the used example."""

    return sum(has_example_leakage(narration, example) for narration in narrations)


def scripts_for(variation: dict[str, Any], scene_id: str) -> list[dict[str, Any]]:
    scripts = variation.get("scripts", {})
    scene_scripts = scripts.get(scene_id, []) if isinstance(scripts, dict) else []
    if isinstance(scene_scripts, dict):
        scene_scripts = [scene_scripts]
    if not scene_scripts:
        scene_scripts = [{"name": "default", "inputs": ["Investigate the immediate scene carefully."] * 8}]
    output = []
    for index, script in enumerate(scene_scripts):
        if isinstance(script, list):
            name, inputs = f"script-{index + 1}", script
        elif isinstance(script, dict):
            name, inputs = script.get("name", f"script-{index + 1}"), script.get("inputs", [])
        else:
            raise ValueError(f"script {index + 1} for {scene_id} must be an object or list")
        if (
            not isinstance(name, str)
            or not isinstance(inputs, list)
            or not inputs
            or not all(isinstance(item, str) and item for item in inputs)
        ):
            raise ValueError(f"script {name!r} for {scene_id} must contain non-empty string inputs")
        output.append({"name": name, "inputs": inputs})
    return output


def run_scene(variation: dict[str, Any], scene_id: str, script: dict[str, Any], max_turns: int = 12) -> dict[str, Any]:
    package, state = seeded_state_for_scene(variation, scene_id)
    seeded_by = (
        "thorough" if variation.get("_entry_state", variation.get("entry_state", "bare")) == "thorough" else "none"
    )
    arrival_entry_state = entry_state(state, seeded_by=seeded_by)
    provider = provider_for(state, variation)
    engine = RuntimeEngine(state, provider)
    try:
        opening = engine.opening()
        if isinstance(provider, ItemFactsProvider):
            provider.discard_pending_item_facts()
    except (NarrationProviderError, ProposalValidationError, RuntimeContractError) as error:
        return _failed_scene_record(variation, scene_id, script, provider, error, entry_state=arrival_entry_state)
    turns: list[dict[str, Any]] = []
    rejected_turns: list[dict[str, Any]] = []
    fixed_turns = variation.get("_fixed_turns", variation.get("fixed_turns"))
    continue_to = variation.get("_continue_to")
    inputs = script["inputs"]
    quota = None
    scene_transitions: list[dict[str, Any]] = []

    def play_turns(turn_limit: int, turn_inputs: list[str], *, stop_on_exit: bool) -> bool:
        for turn_index in range(turn_limit):
            turn_number = len(turns) + len(rejected_turns) + 1
            player_input = turn_inputs[turn_index % len(turn_inputs)]
            prior_scene = state.current_scene_id
            try:
                proposal = _turn_with_rate_limit_retry(engine, player_input)
            except NarrationProviderError as error:
                if fixed_turns is None or error.error_code != "INVALID_PROPOSAL":
                    raise
                if isinstance(provider, ItemFactsProvider):
                    provider.discard_pending_item_facts()
                rejected_turns.append(
                    {
                        "turn_number": turn_number,
                        "player_input": player_input,
                        "rejection_code": "INVALID_PROPOSAL",
                        "rejection_reason": str(error),
                    }
                )
                continue
            except (ProposalValidationError, RuntimeContractError) as error:
                if isinstance(provider, ItemFactsProvider):
                    provider.discard_pending_item_facts()
                if fixed_turns is None:
                    raise
                rejected_turns.append(
                    {
                        "turn_number": turn_number,
                        "player_input": player_input,
                        "rejection_code": getattr(error, "code", None) or getattr(error, "error_code", ""),
                        "rejection_reason": str(error),
                    }
                )
                continue
            entered = state.current_scene_id != prior_scene
            segments = proposal.segments[:-1] if entered else proposal.segments
            narration = join_narration(tuple(segments)) if segments else ""
            item_facts_record: dict[str, Any] | None = None
            if isinstance(provider, ItemFactsProvider):
                facts_before = copy.deepcopy(provider.item_facts)
                raw_item_facts = provider.pending_item_facts()
                if provider.item_facts_mode == "second_call":
                    raw_item_facts = provider.second_call_update(player_input, narration)
                facts_after, fact_issues = provider.apply_item_facts(raw_item_facts)
                item_facts_record = {
                    "item_facts_before": facts_before,
                    "item_facts_after": facts_after,
                    "item_facts_raw": raw_item_facts,
                    "item_facts_issues": fact_issues,
                    "item_facts_source": provider.item_facts_mode,
                }
            if narration or isinstance(provider, ItemFactsProvider):
                delivery = state.last_turn_delivery
                cue_fact_id = delivery.cue_fact_id
                cue_text = next(
                    (
                        item.cue_text
                        for item in package.deliveries
                        if item.fact_id == cue_fact_id and item.cue_text is not None
                    ),
                    None,
                )
                handoff = getattr(provider, "authored_handoff", None)
                turn_record = {
                    "player_input": player_input,
                    "narration": narration,
                    "left_scene": entered,
                    "scene_id": prior_scene,
                    "beats_projected": list(delivery.beats_projected),
                    "selected_knowledge_ids": list(proposal.selected_knowledge_ids),
                    "authored_handoff_candidate_id": handoff.candidate.id if handoff is not None else None,
                    "model_selected_knowledge_ids": list(getattr(provider, "model_selected_knowledge_ids", ())),
                    "grounding_ids": sorted(
                        {grounding_id for segment in segments for grounding_id in segment.grounding_ids}
                    ),
                    "model_grounding_ids": list(getattr(provider, "model_grounding_ids", ())),
                    "shadow_matched_candidate_id": getattr(provider, "shadow_matched_candidate_id", None),
                    "prompt_candidate_ids": list(getattr(provider, "prompt_candidate_ids", ())),
                    "candidates_offered": [candidate.id for candidate in provider.last_projection.candidates]
                    if provider.last_projection is not None
                    else [],
                    "cue_fact_id": cue_fact_id,
                    "cue_text": cue_text,
                    "complication_text": getattr(delivery, "complication_text", None),
                    "handoff_staged": delivery.handoff_staged,
                }
                if item_facts_record is not None:
                    turn_record.update(item_facts_record)
                turn_record["turn_number"] = turn_number
                turns.append(turn_record)
            if entered:
                scene_transitions.append(
                    {
                        "from_scene": prior_scene,
                        "to_scene": state.current_scene_id,
                        "after_turn": turn_number,
                        "advanced_offline": False,
                    }
                )
                if stop_on_exit:
                    return True
        return False

    try:
        play_turns(fixed_turns if fixed_turns is not None else max_turns, inputs, stop_on_exit=continue_to is None)
        if continue_to is not None:
            target_scene = continue_to["scene"]
            if state.current_scene_id != target_scene:
                before_scene = state.current_scene_id
                advance_state_to_scene(package, state, target_scene)
                scene_transitions.append(
                    {
                        "from_scene": before_scene,
                        "to_scene": target_scene,
                        "after_turn": len(turns) + len(rejected_turns),
                        "advanced_offline": True,
                    }
                )
            if isinstance(provider, ItemFactsProvider) and variation.get("item_facts", {}).get(
                "seed_from_package", False
            ):
                additions, issues = package_seed(package, state, target_scene)
                additions = {name: facts for name, facts in additions.items() if name not in provider.item_facts}
                provider.item_facts.update(additions)
                provider.item_facts_seed_names = tuple(provider.item_facts)
                provider.item_facts_seed_issues.extend(issues)
            continuation_script = next(
                item for item in scripts_for(variation, target_scene) if item["name"] == continue_to["script"]
            )
            play_turns(continue_to["fixed_turns"], continuation_script["inputs"], stop_on_exit=False)
    except (NarrationProviderError, ProposalValidationError, RuntimeContractError, RuntimeError) as error:
        return _failed_scene_record(
            variation,
            scene_id,
            script,
            provider,
            error,
            opening=opening.narration,
            turns=turns,
            entry_state=arrival_entry_state,
            rejected_turns=rejected_turns,
        )

    record = {
        "status": "ok",
        "replicate": 0,
        "script": script["name"],
        "scene_id": scene_id,
        "opening": opening.narration,
        "turns": turns,
        "completed": quota is None and bool(turns),
        "quota": quota,
        "narration_turns": len(turns),
        "example_leakage": count_example_leakage(
            (turn["narration"] for turn in turns), variation.get("_resolved_output_example")
        ),
        "narration_requests": provider.request_count,
        "recovery_requests": provider.recovery_count,
        "package": str(package.root) if hasattr(package, "root") else str(variation["_package_path"]),
        "entry_state": arrival_entry_state,
    }
    if fixed_turns is not None:
        record.update(
            {"fixed_turns": fixed_turns, "rejected_turns": rejected_turns, "rejected_turn_count": len(rejected_turns)}
        )
    if scene_transitions:
        record["scene_transitions"] = scene_transitions
    if isinstance(provider, ItemFactsProvider):
        record["item_facts_final"] = copy.deepcopy(provider.item_facts)
        record["item_facts_seed_issues"] = list(provider.item_facts_seed_issues)
    return record


def _failed_scene_record(
    variation: dict[str, Any],
    scene_id: str,
    script: dict[str, Any],
    provider: CloudflareTurnProvider,
    error: BaseException,
    *,
    opening: str = "",
    turns: list[dict[str, Any]] | None = None,
    entry_state: dict[str, Any] | None = None,
    rejected_turns: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    error_code = getattr(error, "error_code", "") or getattr(error, "code", "")
    reason = f"{error_code}: {error}" if error_code else str(error)
    quota = None
    if error_code == "AI_QUOTA_EXCEEDED":
        quota = {"error": error_code, "message": "Workers AI quota is exhausted until 00:00 UTC."}
        reason = quota["message"]
    record = {
        "status": "failed",
        "replicate": 0,
        "script": script["name"],
        "scene_id": scene_id,
        "opening": opening,
        "turns": turns or [],
        "completed": False,
        "quota": quota,
        "failure_reason": reason,
        "narration_turns": len(turns or []),
        "example_leakage": 0,
        "narration_requests": provider.request_count,
        "recovery_requests": provider.recovery_count,
        "package": str(variation["_package_path"]),
    }
    if entry_state is not None:
        record["entry_state"] = entry_state
    fixed_turns = variation.get("_fixed_turns", variation.get("fixed_turns"))
    if fixed_turns is not None:
        record["fixed_turns"] = fixed_turns
        record["rejected_turns"] = rejected_turns or []
        record["rejected_turn_count"] = len(rejected_turns or [])
    if isinstance(provider, ItemFactsProvider):
        record["item_facts_final"] = copy.deepcopy(provider.item_facts)
    return record


def _turn_with_rate_limit_retry(engine: RuntimeEngine, player_input: str) -> Any:
    retries = int(os.getenv("BENCH_RATE_LIMIT_RETRIES", "3"))
    delay = float(os.getenv("BENCH_RATE_LIMIT_RETRY_SECONDS", "1"))
    for attempt in range(retries + 1):
        before = engine.state.model_copy(deep=True)
        try:
            return engine.turn(player_input)
        except NarrationProviderError as error:
            if error.error_code != "RATE_LIMITED" or attempt >= retries:
                raise
            for field in RuntimeState.model_fields:
                setattr(engine.state, field, getattr(before, field))
            engine.last_projection = None
            time.sleep(delay)
    raise AssertionError("unreachable")


def score_judgments(judgments: list[dict[str, Any]]) -> dict[str, Any]:
    per_criterion = {criterion: sum(bool(judgment.get(criterion)) for judgment in judgments) for criterion in CRITERIA}
    missing_total = 0
    attributed: dict[str, int] = {}
    for judgment in judgments:
        for item in judgment.get("missing_or_wrong", []):
            missing_total += 1
            text = item.get("criterion", "") if isinstance(item, dict) else str(item)
            for criterion in CRITERIA:
                if re.search(rf"\b{re.escape(criterion)}\b", text):
                    attributed[criterion] = attributed.get(criterion, 0) + 1
                    break
    return {
        "total": sum(per_criterion.values()),
        "per_criterion": per_criterion,
        "graded_secondary": {
            "metric": "missing_or_wrong entries (fewer is better); separate from the seven-criteria score",
            "total": missing_total,
            "per_criterion_where_attributable": attributed,
            "unattributed": missing_total - sum(attributed.values()),
        },
    }


def score_escalation_judgments(judgments: list[dict[str, Any]], judge_calls: int) -> dict[str, Any]:
    counts: dict[str, dict[str, int]] = {}
    for criterion in ESCALATION_CRITERIA:
        criterion_counts = {verdict: 0 for verdict in ESCALATION_VERDICTS}
        for judgment in judgments:
            verdict = judgment.get(criterion)
            if verdict not in criterion_counts:
                raise ValueError(f"invalid escalation verdict for {criterion}: {verdict!r}")
            criterion_counts[verdict] += 1
        counts[criterion] = criterion_counts
    counts["judge_calls"] = judge_calls
    return counts


def score_continuity_judgments(judgments: list[dict[str, Any]], judge_calls: int) -> dict[str, Any]:
    counts = {criterion: {verdict: 0 for verdict in CONTINUITY_VERDICTS} for criterion in CONTINUITY_CRITERIA}
    turns_judged = 0
    for judgment in judgments:
        for turn in judgment.get("turns", []):
            turns_judged += 1
            for criterion in CONTINUITY_CRITERIA:
                verdict = turn.get(criterion)
                if verdict not in CONTINUITY_VERDICTS:
                    raise ValueError(f"invalid continuity verdict for {criterion}: {verdict!r}")
                counts[criterion][verdict] += 1
    counts["turns_judged"] = turns_judged
    counts["judge_calls"] = judge_calls
    return counts


def score_fact_tracking_judgments(judgments: list[dict[str, Any]], judge_calls: int) -> dict[str, Any]:
    counts = {criterion: {verdict: 0 for verdict in FACT_TRACKING_VERDICTS} for criterion in FACT_TRACKING_CRITERIA}
    changes_by_cause = {cause: 0 for cause in FACT_CHANGE_CAUSES}
    turns_judged = 0
    for judgment in judgments:
        for turn in judgment.get("turns", []):
            turns_judged += 1
            for criterion in FACT_TRACKING_CRITERIA:
                verdict = turn.get(criterion)
                if verdict not in FACT_TRACKING_VERDICTS:
                    raise ValueError(f"invalid fact-tracking verdict for {criterion}: {verdict!r}")
                counts[criterion][verdict] += 1
            for change in turn.get("changes", []):
                cause = change.get("cause")
                if cause not in changes_by_cause:
                    raise ValueError(f"invalid fact-tracking change cause: {cause!r}")
                changes_by_cause[cause] += 1
    counts["changes_by_cause"] = changes_by_cause
    counts["turns_judged"] = turns_judged
    counts["judge_calls"] = judge_calls
    return counts


def _stats(values: list[float], n_for_mde: int | None = None) -> dict[str, Any]:
    count = len(values)
    average = mean(values) if values else None
    deviation = stdev(values) if count > 1 else None
    if deviation is not None:
        critical = T_CRITICAL_95.get(count - 1, 1.96)
        margin = critical * deviation / math.sqrt(count)
        interval = [average - margin, average + margin]
    else:
        interval = None
    n_for_mde = n_for_mde or count
    mde = REFERENCE_MDE_AT_FOUR * math.sqrt(4 / n_for_mde) if n_for_mde else None
    return {
        "n": count,
        "mean": average,
        "standard_deviation": deviation,
        "confidence_interval_95": interval,
        "minimum_detectable_effect": mde,
        "replicate_scores": values,
    }


def aggregate_runs(
    runs: list[dict[str, Any]],
    judgments: list[dict[str, Any]],
    replicates: int,
    *,
    failures: list[dict[str, Any]] | None = None,
    entry_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    failures = failures or []
    paired = [{**run, "judgment": judgment} for run, judgment in zip(runs, judgments, strict=False)]
    values = [float(score_judgments([item["judgment"]])["total"]) for item in paired]
    pooled_judgment = score_judgments(judgments)
    completed_replicates = len({run["replicate"] for run in runs})
    judged_scene_ids = {
        judgment.get("scene_id") for judgment in judgments if isinstance(judgment, dict) and judgment.get("scene_id")
    }
    scenes_scored = len(judged_scene_ids or {run["scene_id"] for run in paired if run.get("scene_id")})
    max_score = scenes_scored * len(CRITERIA)
    entry_records = [*runs, *failures]
    disclosed_entry_state = entry_state or next(
        (record.get("entry_state") for record in entry_records if record.get("entry_state")),
        None,
    )
    by_script: dict[str, Any] = {}
    for script in sorted({run["script"] for run in runs}):
        script_judgments = [item["judgment"] for item in paired if item["script"] == script]
        script_values = [float(score_judgments([judgment])["total"]) for judgment in script_judgments]
        script_score = score_judgments(script_judgments)
        script_replicates = len({item["replicate"] for item in paired if item["script"] == script})
        by_script[script] = {
            "score_points": _stats(script_values, script_replicates),
            "example_leakage": sum(int(item.get("example_leakage", 0)) for item in paired if item["script"] == script),
            "per_criterion": script_score["per_criterion"],
            "graded_secondary": script_score["graded_secondary"],
        }
    aggregate = {
        "replicates": replicates,
        "completed_replicates": completed_replicates,
        "failed_replicates": len(failures),
        "failures": failures,
        "scenes_scored": scenes_scored,
        "max_score": max_score,
        "score_metric": (
            f"{max_score}-point record: seven equally weighted boolean criteria across "
            f"{scenes_scored} scene{'s' if scenes_scored != 1 else ''}"
        ),
        "pooled": {"score_points": _stats(values, completed_replicates), **pooled_judgment},
        "per_script": by_script,
        "replicate_scores": values,
        "example_leakage": sum(int(run.get("example_leakage", 0)) for run in runs),
        "criteria_weighting": "All seven booleans are weighted equally despite very different difficulty.",
    }
    if disclosed_entry_state is not None:
        aggregate["entry_state"] = disclosed_entry_state
    return aggregate


def _student_t_two_sided_p(statistic: float, degrees: float) -> float:
    """Numerically integrate the Student-t density for a dependency-free p-value."""

    absolute = abs(statistic)
    if not math.isfinite(absolute):
        return 0.0
    if absolute == 0:
        return 1.0
    if absolute > 20:
        return 0.0
    coefficient = math.exp(
        math.lgamma((degrees + 1) / 2) - math.lgamma(degrees / 2) - 0.5 * math.log(degrees * math.pi)
    )
    steps = 2000
    width = absolute / steps

    def density(value: float) -> float:
        return coefficient * (1 + value * value / degrees) ** (-(degrees + 1) / 2)

    weighted = density(0) + density(absolute)
    weighted += 4 * sum(density(index * width) for index in range(1, steps, 2))
    weighted += 2 * sum(density(index * width) for index in range(2, steps, 2))
    integral = weighted * width / 3
    return max(0.0, min(1.0, 1 - 2 * integral))


def welch_t_test(left: list[float], right: list[float]) -> dict[str, Any]:
    if len(left) < 2 or len(right) < 2:
        return {"available": False, "reason": "Welch t-test needs at least two runs in each arm."}
    left_var, right_var = stdev(left) ** 2, stdev(right) ** 2
    standard_error = math.sqrt(left_var / len(left) + right_var / len(right))
    difference = mean(left) - mean(right)
    if standard_error == 0:
        p_value = 1.0 if difference == 0 else 0.0
        degrees = float("inf")
        statistic = float("inf") if difference > 0 else float("-inf")
    else:
        statistic = difference / standard_error
        numerator = (left_var / len(left) + right_var / len(right)) ** 2
        denominator = (left_var**2 / (len(left) ** 2 * (len(left) - 1))) + (
            right_var**2 / (len(right) ** 2 * (len(right) - 1))
        )
        degrees = numerator / denominator if denominator else float("inf")
        p_value = _student_t_two_sided_p(statistic, degrees)
    return {
        "available": True,
        "test": "two-sided Welch t-test",
        "difference_in_means": difference,
        "t": statistic,
        "degrees_of_freedom": degrees,
        "p_value": p_value,
        "inside_noise": p_value >= 0.05,
        "statement": "this changed nothing detectable (difference is inside the observed noise)"
        if p_value >= 0.05
        else "the difference is detectable at p < 0.05",
    }


def ledger_rows(path: Path = LEDGER_PATH) -> list[dict[str, Any]]:
    """Read the append-only ledger in its stored order."""

    if not path.is_file():
        return []
    rows = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"ledger line {line_number} is not valid JSON: {error}") from error
        if not isinstance(row, dict):
            raise ValueError(f"ledger line {line_number} must be a JSON object")
        rows.append(row)
    return rows


def successful_ledger_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return successful rows; old rows without status were successful."""

    return [row for row in rows if row.get("status", "ok") == "ok"]


def scenes_scored_for_row(row: dict[str, Any]) -> int | None:
    """Read recorded coverage; missing or null coverage has an unknown scale."""

    if "scenes_scored" not in row or row["scenes_scored"] is None:
        return None
    coverage = row["scenes_scored"]
    if isinstance(coverage, int) and not isinstance(coverage, bool) and coverage >= 0:
        return coverage
    raise ValueError("ledger row has invalid scenes_scored")


def known_scale_ledger_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return successful rows whose scene denominator was explicitly recorded."""

    return [row for row in successful_ledger_rows(rows) if scenes_scored_for_row(row) is not None]


def unknown_scale_ledger_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return successful rows without a recorded scene denominator."""

    return [row for row in successful_ledger_rows(rows) if scenes_scored_for_row(row) is None]


def append_ledger_row(row: dict[str, Any], path: Path = LEDGER_PATH) -> None:
    """Append exactly one immutable JSON row; never read-modify-write the file."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def _git_provenance() -> tuple[str, bool]:
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    status = subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=all"], text=True).strip()
    return sha, bool(status)


def ledger_row(
    variation: dict[str, Any],
    *,
    scene: str,
    scripts: list[dict[str, Any]],
    replicates: int,
    aggregate: dict[str, Any],
    status: str = "ok",
    failure_reason: str | None = None,
) -> dict[str, Any]:
    """Build the durable provenance record for one bench invocation."""

    git_sha, git_dirty = _git_provenance()
    pooled = aggregate["pooled"]
    scores = [int(score) for score in aggregate["replicate_scores"]]
    score_stats = pooled["score_points"]
    budget = aggregate["budget"]
    row = {
        "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "variation_name": variation["name"],
        "variation_hash": variation["_variation_hash"],
        "package_hash": variation["_package_hash"],
        "git_sha": git_sha,
        "git_dirty": git_dirty,
        "scene": scene,
        "scripts": [script["name"] for script in scripts],
        "replicates": replicates,
        "status": status,
        "scenes_scored": aggregate["scenes_scored"],
        "max_score": aggregate["max_score"],
        "score_metric": aggregate["score_metric"],
        "scores": scores,
        "example_leakage": int(aggregate.get("example_leakage", 0)),
        "mean": score_stats["mean"],
        "sd": score_stats["standard_deviation"],
        "per_criterion": pooled["per_criterion"],
        "missing_or_wrong": pooled["graded_secondary"],
        "spend": {
            "neurons": round(budget["estimated_workers_ai_neurons_from_requests"], 2),
            "judge_calls": budget["actual_openai_judge_calls"],
        },
        "model": os.getenv("CF_AI_MODEL", "").strip() or DEFAULT_NARRATOR_MODEL,
    }
    if "escalation" in aggregate:
        row["escalation"] = aggregate["escalation"]
    if "continuity" in aggregate:
        row["continuity"] = aggregate["continuity"]
    if "fact_tracking" in aggregate:
        row["fact_tracking"] = aggregate["fact_tracking"]
    if failure_reason is not None:
        row["failure_reason"] = failure_reason
    return row


def baseline_scenes_scored(run_dir: Path) -> int | None:
    """Return recorded baseline coverage, or unknown when no denominator exists."""

    summary_path = run_dir / "summary.json"
    if summary_path.is_file():
        summary = read_json(summary_path)
        coverage = summary.get("scenes_scored")
        if isinstance(coverage, int) and not isinstance(coverage, bool) and coverage >= 0:
            return coverage
        return None
    judgment_path = run_dir / "e2e-llm-canon.json"
    if judgment_path.is_file():
        data = read_json(judgment_path)
        judgments = data.get("judgments", [])
        scene_ids = {item.get("scene_id") for item in judgments if isinstance(item, dict) and item.get("scene_id")}
        if scene_ids:
            return len(scene_ids)
        return None
    raise ValueError(f"baseline directory {run_dir} has no scene coverage metadata")


def baseline_scores(run_dir: Path) -> list[float]:
    if baseline_scenes_scored(run_dir) is None:
        return []
    summary_path = run_dir / "summary.json"
    if summary_path.is_file():
        summary = read_json(summary_path)
        scores = summary.get("replicate_scores") or summary.get("pooled", {}).get("score_points", {}).get(
            "replicate_scores", []
        )
        if scores:
            return [float(score) for score in scores]
    judgment_path = run_dir / "e2e-llm-canon.json"
    if judgment_path.is_file():
        data = read_json(judgment_path)
        return [float(score_judgments(data.get("judgments", []))["total"])]
    raise ValueError(f"baseline directory {run_dir} has no summary.json or e2e-llm-canon.json")


def run_judges(input_path: Path, output_path: Path) -> dict[str, Any]:
    command = [
        "node",
        str(Path(__file__).with_name("judge-cli.mjs")),
        "--input",
        str(input_path),
        "--output",
        str(output_path),
    ]
    result = subprocess.run(command, check=False, text=True, capture_output=True, env=os.environ.copy())
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "judge CLI failed")
    return read_json(output_path)


def run_escalation_judges(input_path: Path, output_path: Path) -> dict[str, Any]:
    command = [
        "node",
        str(Path(__file__).with_name("escalation-judge.mjs")),
        "--input",
        str(input_path),
        "--output",
        str(output_path),
    ]
    result = subprocess.run(command, check=False, text=True, capture_output=True, env=os.environ.copy())
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "escalation judge CLI failed")
    return read_json(output_path)


def run_continuity_judges(input_path: Path, output_path: Path) -> dict[str, Any]:
    command = [
        "node",
        str(Path(__file__).with_name("continuity-judge.mjs")),
        "--input",
        str(input_path),
        "--output",
        str(output_path),
    ]
    result = subprocess.run(command, check=False, text=True, capture_output=True, env=os.environ.copy())
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "continuity judge CLI failed")
    return read_json(output_path)


def run_fact_tracking_judges(input_path: Path, output_path: Path) -> dict[str, Any]:
    command = [
        "node",
        str(Path(__file__).with_name("fact-tracking-judge.mjs")),
        "--input",
        str(input_path),
        "--output",
        str(output_path),
    ]
    result = subprocess.run(command, check=False, text=True, capture_output=True, env=os.environ.copy())
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "fact-tracking judge CLI failed")
    return read_json(output_path)
