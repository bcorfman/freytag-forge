"""Offline comparison of the recorded and carried 3C input histories.

This module deliberately treats the hosted bundle as an observation, not as a
save file.  The bundle's predicate list is useful for a set comparison, but it
is not sufficient to rebuild the hosted world or projection.
"""

from __future__ import annotations

import argparse
import copy
import difflib
import json
import re
import sys
from pathlib import Path
from typing import Any
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from bench.core import load_variation, package_and_state  # noqa: E402
from scripts.ringer.stage7 import three_c_probe as probe  # noqa: E402
from storygame.runtime.candidate_matcher import uniquely_matched_authored_handoff  # noqa: E402
from storygame.runtime.cloudflare import CloudflareTurnProvider  # noqa: E402
from storygame.runtime.item_facts import ItemFactsProvider  # noqa: E402
from storygame.runtime.knowledge import KnowledgeProjector  # noqa: E402
from storygame.runtime.reveal_eligibility import explain_reveal  # noqa: E402
from storygame.runtime.world_model import world_for  # noqa: E402

LIVE_DIR = ROOT / "bench/results/stage7-3c-blind-raw-f918c663/attempt-1"
LIVE_BUNDLES = LIVE_DIR / "e2e-blind-player-bundles.json"
LIVE_PLAYER = LIVE_DIR / "e2e-blind-player.json"
CARRIED_ROWS = ROOT / "bench/results/stage7-3c-carried-n12/rows.json"
CONTROL_VARIATION = ROOT / "bench/variations/stage7-3c-control.json"
TURN6_COMMAND = "Lead Michelle and the captives through the open surface gates to safety."
DIAGNOSTIC_COMMANDS = (
    "Check the reports from other detention sites.",
    "Answer the families' requests with the confirmed news of the liberated captives.",
)
D_IDS = ("k_sl_3c_d_r1", "k_sl_3c_d_r2")
CUE_FACTS = {
    "truth_no_longer_containable",
    "rebecca_captured",
    "evacuation_route_open",
    "los_angeles_facility_lost",
    "national_network_fragmenting",
    "community_rescue_efforts_begun",
    "phase_two_conflict_plan_known",
}
RELEVANT_FACTS = CUE_FACTS | {
    "scene_3c_entry_known",
    "relay_open",
    "broadcast_started",
    "brandon_confession_available",
    "detention_locations_secured",
    "captives_reaching_surface",
    "portable_archive_secured",
    "archive_contains_prisoner_locations",
    "archive_copies_distributed",
    "facility_collapse_escalating",
}
ENTITY_IDS = {
    "Kristin": "kristin",
    "Michelle": "michelle",
    "Brandon": "brandon",
    "captives group": "captives",
    "Portable data case": "portable_archive",
    "Rebecca": "rebecca",
}
RECONSTRUCTED_REVEALS = (
    ("k_sl_3c_a_r1", "Send the evidence package."),
    ("k_sl_3c_b_r1", "Take the Portable data case from Rebecca."),
    ("k_sl_3c_c_r1", "Restore the drainage pumps."),
    ("k_sl_3c_c_r2", "Open the surface gates."),
)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_recorded_bundle(path: Path = LIVE_BUNDLES) -> dict[str, Any]:
    """Load the recorded 3C bundles and reject an unrecognizable shape loudly."""

    data = _read_json(path)
    if not isinstance(data, dict) or not isinstance(data.get("replicates"), list) or not data["replicates"]:
        raise ValueError(f"recorded bundle shape missing replicates list: {path}")
    replicate = data["replicates"][0]
    scenes = replicate.get("scenes") if isinstance(replicate, dict) else None
    if not isinstance(scenes, list):
        raise ValueError(f"recorded bundle shape missing replicate scenes list: {path}")
    scene = next((item for item in scenes if isinstance(item, dict) and item.get("scene") == "3C"), None)
    if not isinstance(scene, dict) or not isinstance(scene.get("bundles"), list):
        raise ValueError(f"recorded bundle shape missing replicate 3C bundles: {path}")
    bundles = scene["bundles"]
    if len(bundles) < 6:
        raise ValueError(f"recorded bundle shape needs at least six 3C bundles: {path}")
    for number, bundle in enumerate(bundles, start=1):
        attempt = bundle.get("attempt_bundle") if isinstance(bundle, dict) else None
        if not isinstance(attempt, dict) or not isinstance(attempt.get("pre_state"), dict):
            raise ValueError(f"recorded bundle {number} has no attempt_bundle.pre_state: {path}")
    return {"root": data, "replicate": replicate, "scene": scene, "bundles": bundles}


def grouped_set_difference(left: set[str], right: set[str]) -> dict[str, dict[str, list[str]]]:
    """Return exact set differences grouped by a stable predicate family."""

    def family(predicate: str) -> str:
        if predicate.startswith("wk_"):
            return "world (wk_*)"
        if predicate.startswith("scene_"):
            return predicate.split("_entry_", 1)[0]
        if predicate == "story_elapsed_seconds":
            return "story clock"
        return predicate.split("_", 1)[0]

    result: dict[str, dict[str, list[str]]] = {}
    for label, values in (
        ("present_live_absent_scripted", left - right),
        ("present_scripted_absent_live", right - left),
    ):
        for value in sorted(values):
            result.setdefault(family(value), {"present_live_absent_scripted": [], "present_scripted_absent_live": []})[
                label
            ].append(value)
    return dict(sorted(result.items()))


# A descriptive alias makes the helper convenient for small fixture tests.
set_difference_by_family = grouped_set_difference


def _attempt(bundle: dict[str, Any]) -> dict[str, Any]:
    return bundle["attempt_bundle"]


def _recorded_narration_request(recorded: dict[str, Any], bundle_index: int) -> dict[str, str]:
    stages = _attempt(recorded["bundles"][bundle_index]).get("stages")
    if not isinstance(stages, list) or not stages or not isinstance(stages[0], dict):
        raise ValueError(f"recorded bundle {bundle_index + 1} has no narration stage request")
    request = stages[0].get("request")
    if (
        not isinstance(request, dict)
        or not isinstance(request.get("user"), str)
        or not isinstance(request.get("system"), str)
    ):
        raise ValueError(f"recorded bundle {bundle_index + 1} has no narration request user/system")
    return {"system": request["system"], "user": request["user"]}


def _section(text: str, heading: str) -> list[str]:
    match = re.search(rf"(?:^|\n){re.escape(heading)}:\n(?P<body>.*?)(?=\n\n[A-Z][A-Z ]+:|\Z)", text, re.S)
    if not match:
        return []
    return [line[2:] if line.startswith("- ") else line for line in match.group("body").splitlines() if line]


def _things_parents(user: str) -> dict[str, Any]:
    lines = _section(user, "THINGS")
    parent_lines: dict[str, str] = {}
    for line in lines:
        match = re.match(r"(.+?)\. (?:Place|Held by): (.+?)(?:\.|$)", line)
        if match:
            parent_lines[match.group(1)] = match.group(2)
    aliases = {
        "Kristin": "Kristin",
        "Michelle": "Michelle",
        "Brandon": "Brandon",
        "captives group": "detention captives",
        "Portable data case": "Portable data case",
        "Rebecca": "Rebecca",
    }
    result: dict[str, Any] = {}
    for label, thing_name in aliases.items():
        result[label] = {
            "parent": parent_lines.get(thing_name),
            "recovered_from_things": thing_name in parent_lines,
            "thing_name": thing_name,
        }
    for line in lines:
        if line.startswith("- Kristin.") and "With Kristin:" in line:
            result["Kristin"]["with"] = line.split("With Kristin:", 1)[1].rstrip(".").strip()
    return result


def _fact_predicates(state: Any) -> set[str]:
    return {str(fact.predicate) for fact in state.facts.asserted}


def _relevant_facts(predicates: set[str]) -> list[str]:
    return sorted(
        predicate for predicate in predicates if predicate in RELEVANT_FACTS or predicate.startswith("k_sl_3c_")
    )


def _parents_from_state(package: Any, state: Any) -> dict[str, Any]:
    world = world_for(package, state.facts)
    result: dict[str, Any] = {}
    for label, entity_id in ENTITY_IDS.items():
        try:
            parent = world.parent(entity_id)
        except Exception as error:  # pragma: no cover - defensive for package drift
            result[label] = {"parent": None, "recovered_from_world": False, "error": str(error)}
        else:
            result[label] = {"parent": parent, "recovered_from_world": parent is not None, "entity_id": entity_id}
    return result


def _state_snapshot(package: Any, state: Any, *, label: str, entry_text: str | None = None) -> dict[str, Any]:
    predicates = _fact_predicates(state)
    return {
        "label": label,
        "scene_id": state.current_scene_id,
        "turn_index": state.turn_index,
        "scene_turn_count": state.turn_index - state.scene_entered_at_turn,
        "turns_since_scene_entry": state.turn_index - state.scene_entered_at_turn,
        "parents": _parents_from_state(package, state),
        "fact_predicates": sorted(predicates),
        "fact_predicate_count": len(predicates),
        "fact_predicates_are_full_state": True,
        "committed_fact_ids_relevant_to_3c": _relevant_facts(predicates),
        "entry_text": entry_text,
        "delivered_cue_ids": list(state.delivered_cue_ids),
        "staged_cue_fact_id": state.staged_cue_fact_id,
    }


def _live_entry_text() -> str | None:
    data = _read_json(LIVE_PLAYER)
    scene = data["replicates"][0]["scenes"][8]
    opening = scene.get("opening_text")
    if not isinstance(opening, str):
        return None
    prefix_path = ROOT / "bench/results/stage7-3c-prefix/prefix.json"
    if prefix_path.exists():
        bridge = _read_json(prefix_path).get("bridge_text")
        if isinstance(bridge, str) and bridge in opening:
            suffix = opening.split(bridge, 1)[1]
            if suffix:
                return suffix.lstrip()
    return None


def _live_snapshot(recorded: dict[str, Any], bundle_index: int, *, entry: bool) -> dict[str, Any]:
    bundle = recorded["bundles"][bundle_index]
    attempt = _attempt(bundle)
    pre = attempt["pre_state"]
    request = _recorded_narration_request(recorded, bundle_index)
    user = request["user"]
    predicates = set(pre.get("fact_predicates", []))
    return {
        "label": "recorded hosted run",
        "scene_id": pre.get("scene_id"),
        "turn_index": pre.get("turn_index"),
        "scene_turn_count": pre.get("turns_since_scene_entry"),
        "turns_since_scene_entry": pre.get("turns_since_scene_entry"),
        "parents": _things_parents(user),
        "fact_predicates": sorted(predicates),
        "fact_predicate_count": len(predicates),
        "fact_predicates_are_full_state": False,
        "committed_fact_ids_relevant_to_3c": _relevant_facts(predicates),
        "entry_text": _live_entry_text() if entry else None,
        "entry_text_source": "recorded player opening suffix" if entry else "not requested at turn 6",
        "delivered_cue_ids": list(pre.get("delivered_cue_ids", [])),
        "staged_cue_fact_id": pre.get("staged_cue_fact_id"),
        "recorded_reveal_selection": attempt.get("reveal_selection"),
        "recorded_prompt_things": _section(user, "THINGS"),
        "unrecovered": [
            "World parents absent from the recorded THINGS section are not recovered.",
            "fact_predicates is a bundle telemetry list, not a full save.",
        ],
    }


def _scripted_states() -> tuple[Any, Any, Any]:
    variation = load_variation(CONTROL_VARIATION)
    package, _ = package_and_state(variation, "3C")
    carried = probe.carried_replay(package, variation)
    entry_state = carried["state"]
    reconstructed_state = copy.deepcopy(entry_state)
    reconstructed_engine = probe.RuntimeEngine(reconstructed_state, None)
    for knowledge_id, command in RECONSTRUCTED_REVEALS:
        reconstructed_engine.provider = probe._scripted_provider(package, knowledge_id)  # noqa: SLF001
        response = reconstructed_engine.turn(command)
        committed = list(response.selected_knowledge_ids)
        if committed != [knowledge_id]:
            raise AssertionError(f"reconstructed reveal {knowledge_id} committed {committed or 'nothing'}")
        reconstructed_engine._activate_pacing()  # noqa: SLF001 - mirror the shipped cue-chain helpers.
    reconstructed_state = reconstructed_engine.state
    required_facts = {"scene_1a_entry_known", "relay_open"}
    present_facts = _fact_predicates(reconstructed_state)
    missing_facts = sorted(required_facts - present_facts)
    assert not missing_facts, f"reconstructed state is missing carried facts: {missing_facts}"
    parents = _parents_from_state(package, reconstructed_state)
    missing_parents = [label for label in ("Kristin", "Michelle", "captives group") if not parents[label]["parent"]]
    assert not missing_parents, f"reconstructed state is missing world parents: {missing_parents}"
    return package, entry_state, reconstructed_state


def _d_eligibility(package: Any, state: Any, command: str) -> dict[str, Any]:
    projection = state_projection(state, command)
    universe = projection.reveal_universe
    by_id = {candidate.id: candidate for candidate in universe}
    eligibility = {}
    for reveal_id in D_IDS:
        definition = package.knowledge_indexes.by_id[reveal_id]
        explanation = explain_reveal(state, "player", definition)
        eligibility[reveal_id] = {
            "eligible": explanation.eligible,
            "reason": explanation.reason,
            "detail": explanation.detail,
            "in_reveal_universe": reveal_id in by_id,
        }
    return {
        "command": command,
        "reveal_universe": [candidate.id for candidate in universe],
        "d_reveal_universe": [candidate.id for candidate in universe if candidate.id in D_IDS],
        "reveal_eligibility": eligibility,
        "matcher": _matcher_result(command, universe),
    }


def state_projection(state: Any, command: str) -> Any:
    return probe.RuntimeEngine(state, None).projector.project(state, "player", command)


def _matcher_result(command: str, universe: tuple[Any, ...] | list[Any]) -> dict[str, Any]:
    matched = uniquely_matched_authored_handoff(command, tuple(universe))
    return {"matched_id": matched.candidate.id if matched else None, "source": "runtime projected universe"}


def _live_d_eligibility(recorded: dict[str, Any]) -> dict[str, Any]:
    turn6 = _attempt(recorded["bundles"][5])
    recorded_selection = turn6.get("reveal_selection", {})
    variation = load_variation(CONTROL_VARIATION)
    package, _ = package_and_state(variation, "3C")
    authored_candidates = tuple(
        KnowledgeProjector._candidate(package.knowledge_indexes.by_id[item])
        for item in D_IDS  # noqa: SLF001
    )
    matcher = {}
    for command in (TURN6_COMMAND, *DIAGNOSTIC_COMMANDS):
        if command == TURN6_COMMAND:
            matched_id = recorded_selection.get("matched")
            source = "recorded live reveal_selection"
        else:
            matched = uniquely_matched_authored_handoff(command, authored_candidates)
            matched_id = matched.candidate.id if matched else None
            source = "package-authored D definitions; live projection membership not recovered"
        matcher[command] = {
            "matched_id": matched_id,
            "source": source,
            "stateful_live_projection_recovered": False,
        }
    return {
        "history_label": "LIVE recorded bundle; stateful projection is not reconstructible",
        "recorded_universe_size": recorded_selection.get("universe_size"),
        "recorded_shortlist_size": recorded_selection.get("shortlist_size"),
        "recorded_outcome": recorded_selection.get("outcome"),
        "reveal_universe": None,
        "d_reveal_universe": None,
        "reveal_universe_recovered": False,
        "reveal_eligibility": {
            reveal_id: {
                "eligible": None,
                "reason": "not_recoverable_from_recorded_bundle",
                "detail": "The bundle has counts and partial predicates, not the full live RuntimeState.",
                "in_reveal_universe": None,
            }
            for reveal_id in D_IDS
        },
        "matcher": matcher,
        "limitations": [
            (
                "The turn-6 live prompt says it has no candidates; the bundle separately records "
                "a universe and shortlist size of 2."
            ),
            "The two diagnostic controls were not played in the live history.",
        ],
    }


def _render_scripted_prompt(state: Any, command: str) -> dict[str, Any]:
    provider = ItemFactsProvider(
        worker_url="",
        token="",
        state=state,
        item_facts={},
        mode="single_call",
        seed_from_package=True,
        held_by=True,
        semantic_ask=lambda *_args: None,
    )
    # The item-name match is the same place where the live runtime would use a
    # provider. It is a deterministic local answer; no request is made.
    with patch.object(
        CloudflareTurnProvider,
        "_request_item_facts",
        lambda _self, _payload: {"refers": ["detention captives"], "same_as": {}, "kind": {}},
    ):
        provider.prepare_turn(command)
        assembled = provider.assemble_turn_prompt(command)
        user = provider._section_user_prompt(assembled["context"])  # noqa: SLF001 - exact runtime renderer
    return {"system": assembled["system"], "user": user}


def _prompt_sections(user: str) -> dict[str, list[str]]:
    return {heading: _section(user, heading) for heading in ("SCENE", "THINGS", "CONSTRAINTS", "PLAYER")}


def _section_diffs(live: dict[str, list[str]], scripted: dict[str, list[str]]) -> dict[str, Any]:
    result = {}
    for heading in ("SCENE", "THINGS", "CONSTRAINTS", "PLAYER"):
        live_lines, scripted_lines = live[heading], scripted[heading]
        opcodes = difflib.SequenceMatcher(a=live_lines, b=scripted_lines).get_opcodes()
        differences = []
        for tag, i1, i2, j1, j2 in opcodes:
            if tag == "equal":
                continue
            differences.append(
                {
                    "operation": tag,
                    "live_verbatim": live_lines[i1:i2],
                    "scripted_verbatim": scripted_lines[j1:j2],
                }
            )
        result[heading] = {
            "live": live_lines,
            "scripted": scripted_lines,
            "differences": differences,
            "identical": not differences,
        }
    return result


def _prompt_places(sections: dict[str, list[str]]) -> dict[str, Any]:
    result = {}
    for label, name in (("Kristin", "Kristin"), ("Michelle", "Michelle"), ("captives", "captives")):
        lines = [line for line in sections["THINGS"] if name.casefold() in line.casefold()]
        result[label] = {"present": bool(lines), "verbatim_lines": lines}
        if not lines:
            result[label]["note"] = "not present in this rendered THINGS section"
    return result


def _place_text(lines: list[str], name: str) -> str | None:
    for line in lines:
        if name.casefold() not in line.casefold():
            continue
        match = re.search(r"\. Place: (.+?)(?:\.|$)", line)
        if match:
            return match.group(1).strip()
    return None


def _place_id(package: Any, place_text: str) -> str | None:
    def normalize(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()

    target = normalize(place_text)
    for location in package.world.locations:
        names = (location.id, location.name, *location.aliases)
        if target in {normalize(name) for name in names}:
            return location.id
    return None


def _counterfactual(package: Any, state: Any, live_sections: dict[str, list[str]]) -> dict[str, Any]:
    result: dict[str, Any] = {"label": "synthetic counterfactual", "status": "not_run"}
    try:
        candidate = copy.deepcopy(state)
        live_kristin_place = _place_text(live_sections["THINGS"], "Kristin")
        if live_kristin_place is None:
            result.update(status="stopped", reason="LIVE turn-6 THINGS has no recoverable Kristin place")
            return result
        target_place = _place_id(package, live_kristin_place)
        if target_place is None:
            result.update(status="stopped", reason=f"world API target place is not recoverable: {live_kristin_place}")
            return result
        world = world_for(package, candidate.facts)
        move = world.move("kristin", target_place)
        if not move.ok:
            result.update(status="stopped", reason=f"world API refused Kristin move: {move.reason}")
            return result
        prompt = _render_scripted_prompt(candidate, TURN6_COMMAND)
        sections = _prompt_sections(prompt["user"])
        before_d = {
            command: _d_eligibility(package, state, command) for command in (TURN6_COMMAND, *DIAGNOSTIC_COMMANDS)
        }
        after_d = {
            command: _d_eligibility(package, candidate, command) for command in (TURN6_COMMAND, *DIAGNOSTIC_COMMANDS)
        }
        section_changes = {}
        before_sections = _prompt_sections(_render_scripted_prompt(state, TURN6_COMMAND)["user"])
        for heading in ("SCENE", "THINGS", "CONSTRAINTS", "PLAYER"):
            section_changes[heading] = {
                "changed": before_sections[heading] != sections[heading],
                "before": before_sections[heading],
                "after": sections[heading],
            }
        result.update(
            status="completed",
            world_api=f"world.move('kristin', {target_place!r})",
            moved_parent=target_place,
            live_turn6_kristin_place=live_kristin_place,
            changed_prompt_sections=[heading for heading, value in section_changes.items() if value["changed"]],
            prompt_section_changes=section_changes,
            d_eligibility_before=before_d,
            d_eligibility_after=after_d,
            d_eligibility_changed=[command for command in before_d if before_d[command] != after_d[command]],
            note="Synthetic only; this placement is not transplanted into the package or live history.",
        )
    except Exception as error:  # pragma: no cover - package/world drift is reported, not hidden
        result.update(status="stopped", reason=f"world API counterfactual could not be completed: {error}")
    return result


def _per_turn(recorded: dict[str, Any]) -> dict[str, Any]:
    live_rows = []
    for bundle in recorded["bundles"]:
        attempt = _attempt(bundle)
        pre = attempt["pre_state"]
        live_rows.append(
            {
                "turn": bundle.get("turn"),
                "turn_index": pre.get("turn_index"),
                "staged_cue_fact_id": pre.get("staged_cue_fact_id"),
                "delivered_cue_ids": pre.get("delivered_cue_ids", []),
                "reveal_selection": attempt.get("reveal_selection"),
            }
        )
    if not CARRIED_ROWS.exists():
        return {"status": "not_recoverable", "live_turns": live_rows, "scripted_carried_example": None}
    rows = _read_json(CARRIED_ROWS)
    pump = next((row for row in rows if row.get("arm") == "pump" and row.get("semantic") == "on"), None)
    if pump is None:
        return {"status": "not_recoverable", "live_turns": live_rows, "scripted_carried_example": None}
    scripted_rows = []
    for turn in pump.get("turns", []):
        cue = turn.get("cue_text_staged") or {}
        scripted_rows.append(
            {
                "turn": turn.get("scene_turn"),
                "staged_cue_fact_id": cue.get("fact_id"),
                "delivered_cue_ids": "not recorded in carried row",
                "reveal_selection": {
                    "committed_reveals": turn.get("committed_reveals", []),
                    "status": turn.get("status"),
                },
            }
        )
    return {
        "status": "recovered_as_one_labelled_pump_arm_example",
        "live_turns_1_to_14": live_rows,
        "scripted_carried_pump_arm": scripted_rows,
        "scripted_source": str(CARRIED_ROWS),
        "note": (
            "The carried rows do not record delivered_cue_ids or a separate reveal_selection object; "
            "those fields remain unavailable there."
        ),
    }


def build_report() -> dict[str, Any]:
    recorded = load_recorded_bundle()
    package, carried_entry_state, synthetic_state = _scripted_states()
    variation = load_variation(CONTROL_VARIATION)
    carried = probe.carried_replay(package, variation)
    live_entry = _live_snapshot(recorded, 0, entry=True)
    live_before = _live_snapshot(recorded, 5, entry=False)
    scripted_entry = _state_snapshot(
        package,
        carried_entry_state,
        label="carried replay: real 3B prefix and 3B->3C transition",
        entry_text=carried["entry_text"],
    )
    scripted_before = _state_snapshot(
        package,
        synthetic_state,
        label="reconstructed, synthetic: same four reveals, not the live player transcript",
    )
    scripted_before["reconstruction"] = {
        "source": "same carried 3C entry state; shipped package",
        "label": "reconstructed from the carried 3C entry state; same four reveals, not the live player transcript",
        "reveals": [
            {"scene_turn": index, "knowledge_id": knowledge_id, "command": command}
            for index, (knowledge_id, command) in enumerate(RECONSTRUCTED_REVEALS, start=1)
        ],
    }
    live_request = _recorded_narration_request(recorded, 5)
    live_prompt_user = live_request["user"]
    scripted_prompt = _render_scripted_prompt(synthetic_state, TURN6_COMMAND)
    live_sections = _prompt_sections(live_prompt_user)
    scripted_sections = _prompt_sections(scripted_prompt["user"])
    scripted_places = _prompt_places(scripted_sections)
    for label in ("Michelle", "captives"):
        assert scripted_places[label]["present"], f"scripted THINGS lacks a line for {label}"
    scripted_d = {
        command: _d_eligibility(package, synthetic_state, command) for command in (TURN6_COMMAND, *DIAGNOSTIC_COMMANDS)
    }
    fact_diff = grouped_set_difference(set(live_before["fact_predicates"]), set(scripted_before["fact_predicates"]))
    return {
        "metadata": {
            "offline": True,
            "live_bundle": str(LIVE_BUNDLES),
            "scripted_variation": str(CONTROL_VARIATION),
            "no_model_or_network_calls": True,
            "scripted_prompt_item_facts_stub": "deterministic local refers=[detention captives]",
        },
        "entry": {"LIVE": live_entry, "SCRIPTED": scripted_entry},
        "before_turn6": {
            "LIVE": live_before,
            "SCRIPTED": scripted_before,
            "fact_predicate_set_difference": {
                "live_is_partial_bundle_telemetry": True,
                "scripted_is_full_runtime_state": True,
                "grouped": fact_diff,
            },
        },
        "d_eligibility": {"LIVE": _live_d_eligibility(recorded), "SCRIPTED": scripted_d},
        "prompt_diff": {
            "command": TURN6_COMMAND,
            "LIVE": {
                "system": live_request["system"],
                "sections": live_sections,
            },
            "SCRIPTED": {"system": scripted_prompt["system"], "sections": scripted_sections},
            "sections": _section_diffs(live_sections, scripted_sections),
            "things_places_called_out": {
                "LIVE": _prompt_places(live_sections),
                "SCRIPTED": _prompt_places(scripted_sections),
            },
        },
        "kristin_counterfactual": _counterfactual(package, synthetic_state, live_sections),
        "per_turn": _per_turn(recorded),
        "limits": [
            (
                "This comparison records facts in the artifacts and deterministic runtime projections; "
                "it does not claim what a model would do."
            ),
            (
                "The LIVE bundle's partial fact_predicates are not presented as a full save and cannot "
                "recover absent world parents or live projection IDs."
            ),
            "The SCRIPTED before-turn-6 state is synthetic: four runtime API reveals, not the live player transcript.",
            "The synthetic Kristin placement is a counterfactual only and is not transplanted into the package.",
            (
                "What this can and cannot show: it can show recorded prompt/cue/state differences and "
                "deterministic eligibility/matcher results where state is available; it cannot show "
                "behavioral causation, model response rates, or restore an absent hosted save."
            ),
        ],
    }


def _markdown(report: dict[str, Any]) -> str:
    def compact(value: Any) -> str:
        return json.dumps(value, ensure_ascii=False, sort_keys=True)

    lines = [
        "# Stage 7 3C state comparison",
        "",
        "Offline report. It records facts from the hosted artifacts and deterministic scripted runtime outputs only.",
        "",
        "## 1. 3C entry",
        "",
        f"- LIVE: `{compact(report['entry']['LIVE'])}`",
        f"- SCRIPTED: `{compact(report['entry']['SCRIPTED'])}`",
        "",
        "## 2. Before live turn 6",
        "",
        f"- LIVE: `{compact(report['before_turn6']['LIVE'])}`",
        f"- SCRIPTED: `{compact(report['before_turn6']['SCRIPTED'])}`",
        (
            "- Predicate counts: LIVE has "
            f"`{report['before_turn6']['LIVE']['fact_predicate_count']}` entries "
            "(partial bundle telemetry, not a full save); "
            "SCRIPTED has "
            f"`{report['before_turn6']['SCRIPTED']['fact_predicate_count']}` entries "
            "(full reconstructed runtime state)."
        ),
        (
            f"- Fact predicate differences (LIVE is partial telemetry): "
            f"`{compact(report['before_turn6']['fact_predicate_set_difference'])}`"
        ),
        "",
        "## 3. D eligibility and matcher",
        "",
        f"- LIVE: `{compact(report['d_eligibility']['LIVE'])}`",
        f"- SCRIPTED: `{compact(report['d_eligibility']['SCRIPTED'])}`",
        "",
        "## 4. Narrator prompt before turn 6",
        "",
        (
            "The section diff below preserves differing lines verbatim. Kristin, Michelle, and the captives' "
            "THINGS lines are called out in `things_places_called_out`."
        ),
        "",
        f"`{compact(report['prompt_diff']['sections'])}`",
        "",
        "## 5. Synthetic Kristin counterfactual",
        "",
        f"`{compact(report['kristin_counterfactual'])}`",
        "",
        "## 6. Per-turn cue comparison",
        "",
        f"`{compact(report['per_turn'])}`",
        "",
        "## What this can and cannot show",
        "",
    ]
    lines.extend(f"- {item}" for item in report["limits"])
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)
    report = build_report()
    (args.out / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (args.out / "report.md").write_text(_markdown(report), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
