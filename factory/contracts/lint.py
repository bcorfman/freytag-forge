"""Deterministic linting for planner-produced act contracts."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_MISSING = object()
_DEFAULT_RULES = Path(__file__).resolve().parents[1] / "config" / "contract_rules.json"


@dataclass(frozen=True)
class Problem:
    """One contract-lint violation."""

    rule_id: str
    path: str
    message: str

    def __str__(self) -> str:
        return f"{self.rule_id} {self.path}: {self.message}"


def load_rules(path: str | Path | None = None) -> dict[str, Any]:
    """Load rule constants from the supplied path or the packaged defaults."""

    with Path(path or _DEFAULT_RULES).open(encoding="utf-8") as rules_file:
        rules = json.load(rules_file)
    if not isinstance(rules, dict):
        raise ValueError("rules file must contain a JSON object")
    return rules


def _is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _first_matching(values: list[str], word: str) -> str | None:
    return next((value for value in values if value == word), None)


class _ContractLint:
    def __init__(self, rules: Mapping[str, Any]) -> None:
        self.rules = rules
        self.problems: list[Problem] = []
        self.cost_kinds = list(rules.get("cost_kinds", []))
        self.beat_kinds = list(rules.get("beat_kinds", []))
        self.relations = list(rules.get("relations", []))
        self.need_roles = list(rules.get("need_roles", []))
        self.bond_kinds = list(rules.get("bond_kinds", []))
        self.scene_ids = list(rules.get("scene_ids", []))
        self.protected_characters = {str(value).casefold() for value in rules.get("protected_characters", [])}
        self.reading_verbs = {str(value).casefold() for value in rules.get("reading_verbs", [])}
        self.first_pressure_turns = set(rules.get("first_pressure_turns", []))
        self.min_gap_turns = rules.get("min_gap_turns", 2)
        self.riskier_kind = next((kind for kind in self.cost_kinds if "riskier" in kind), None)
        self.harm_kinds = {kind for kind in self.cost_kinds if "harm" in kind}
        self.entry_kind = _first_matching(self.beat_kinds, "entry")
        self.pressure_kind = _first_matching(self.beat_kinds, "pressure")
        self.relief_kind = _first_matching(self.beat_kinds, "relief")
        self.setpiece_kind = _first_matching(self.beat_kinds, "setpiece")
        self.exit_kind = _first_matching(self.beat_kinds, "exit")
        self.scene_positions = {scene_id: position for position, scene_id in enumerate(self.scene_ids)}

    def add(self, rule_id: str, path: str, message: str) -> None:
        self.problems.append(Problem(rule_id, path, message))

    def run(self, contract: Any) -> list[Problem]:
        self.find_placeholders(contract, "")
        if not isinstance(contract, dict):
            self.add("contract.shape", "contract", "contract must be an object")
            return self.problems

        self.check_contract_shape(contract)
        scenes = contract.get("scenes")
        if not isinstance(scenes, list):
            return self.problems

        prior_bonds = self._character_list(contract.get("prior_bonds"))
        scene_ids: list[Any] = []
        for index, scene in enumerate(scenes):
            scene_path = f"scenes[{index}]"
            if not isinstance(scene, dict):
                self.add("contract.shape", scene_path, "scene must be an object")
                continue
            scene_id = scene.get("scene_id")
            scene_ids.append(scene_id)
            self.check_scene_shape(scene, scene_path)
            self.check_scene_rules(scene, scene_path, index, scenes, prior_bonds)

        self.check_duplicates(scene_ids, "scenes", "scene_id")
        return self.problems

    def find_placeholders(self, value: Any, path: str) -> None:
        if isinstance(value, str):
            if value == "TODO":
                self.add("contract.placeholder", path or "contract", "placeholder value TODO")
        elif isinstance(value, list):
            for index, item in enumerate(value):
                self.find_placeholders(item, f"{path}[{index}]")
        elif isinstance(value, dict):
            for key, item in value.items():
                child_path = f"{path}.{key}" if path else str(key)
                self.find_placeholders(item, child_path)

    def check_contract_shape(self, contract: dict[str, Any]) -> None:
        self.require_string(contract, "act", "")

        if "prior_bonds" in contract:
            self.check_string_list(contract["prior_bonds"], "prior_bonds")

        harm_ladder = contract.get("harm_ladder", _MISSING)
        if not isinstance(harm_ladder, list):
            self.add("contract.shape", "harm_ladder", "harm_ladder must be a list")
        else:
            for index, rung in enumerate(harm_ladder):
                path = f"harm_ladder[{index}]"
                if not isinstance(rung, dict):
                    self.add("contract.shape", path, "harm rung must be an object")
                    continue
                if not _is_int(rung.get("rung")):
                    self.add("contract.shape", f"{path}.rung", "rung must be an integer")
                if rung.get("kind") not in self.cost_kinds:
                    self.add("contract.shape", f"{path}.kind", "unknown cost kind")
                if not _is_nonempty_string(rung.get("harm")):
                    self.add("contract.shape", f"{path}.harm", "harm must be a non-empty string")
            if len(harm_ladder) < 2:
                self.add("contract.harm_ladder", "harm_ladder", "harm ladder must contain at least two rungs")
            else:
                rung_numbers = [rung.get("rung") for rung in harm_ladder if isinstance(rung, dict)]
                if (
                    len(rung_numbers) == len(harm_ladder)
                    and all(_is_int(rung_number) for rung_number in rung_numbers)
                    and rung_numbers != list(range(1, len(harm_ladder) + 1))
                ):
                    self.add(
                        "contract.harm_ladder",
                        "harm_ladder",
                        "harm ladder rungs must be consecutive and start at 1",
                    )

        scenes = contract.get("scenes", _MISSING)
        if not isinstance(scenes, list) or not scenes:
            self.add("contract.shape", "scenes", "scenes must be a non-empty list")

    def check_scene_shape(self, scene: dict[str, Any], path: str) -> None:
        scene_id = scene.get("scene_id", _MISSING)
        if not _is_nonempty_string(scene_id) or scene_id not in self.scene_ids:
            self.add("contract.shape", f"{path}.scene_id", "scene_id must be a known non-empty scene id")

        if "entry_prior_exit_sets_threat" in scene and not isinstance(scene["entry_prior_exit_sets_threat"], bool):
            self.add("contract.shape", f"{path}.entry_prior_exit_sets_threat", "threat flag must be boolean")

        feeling = scene.get("feeling", _MISSING)
        if feeling is _MISSING or not isinstance(feeling, str):
            self.add("contract.shape", f"{path}.feeling", "feeling must be a string")

        clock = scene.get("clock", _MISSING)
        if not isinstance(clock, dict):
            self.add("contract.shape", f"{path}.clock", "clock must be an object")
        else:
            for key in ("running_out", "bridge_hook"):
                if key not in clock or not isinstance(clock[key], str):
                    self.add("contract.shape", f"{path}.clock.{key}", f"clock.{key} must be a string")

        npc = scene.get("npc_in_the_way", _MISSING)
        if isinstance(npc, dict):
            if not _is_nonempty_string(npc.get("character")):
                self.add("contract.shape", f"{path}.npc_in_the_way.character", "character must be non-empty")
        elif npc is not _MISSING:
            self.add("contract.npc", f"{path}.npc_in_the_way", "npc_in_the_way must name an entry NPC")

        self.check_beats_shape(scene.get("beats", _MISSING), f"{path}.beats")
        self.check_delay_shape(scene.get("delay_costs", _MISSING), f"{path}.delay_costs")
        self.check_bond_shape(scene.get("bond_beats", _MISSING), f"{path}.bond_beats")
        self.check_need_shape(scene.get("world_needs", _MISSING), f"{path}.world_needs")

    def check_beats_shape(self, beats: Any, path: str) -> None:
        if not isinstance(beats, list):
            self.add("contract.shape", path, "beats must be a list")
            return
        if not beats:
            self.add("contract.beats", path, "scene must contain the required beats")
            return
        ids: list[Any] = []
        for index, beat in enumerate(beats):
            beat_path = f"{path}[{index}]"
            if not isinstance(beat, dict):
                self.add("contract.shape", beat_path, "beat must be an object")
                continue
            ids.append(beat.get("id"))
            if not _is_nonempty_string(beat.get("id")):
                self.add("contract.shape", f"{beat_path}.id", "beat id must be non-empty")
            if beat.get("kind") not in self.beat_kinds:
                self.add("contract.shape", f"{beat_path}.kind", "unknown beat kind")
            if not _is_nonempty_string(beat.get("summary")):
                self.add("contract.shape", f"{beat_path}.summary", "summary must be non-empty")
            if not _is_int(beat.get("turn")) or beat["turn"] < 1:
                self.add("contract.beats", f"{beat_path}.turn", "beat turn must be an integer at least 1")
            if beat.get("kind") == self.setpiece_kind:
                outcomes = beat.get("outcomes", _MISSING)
                if not isinstance(outcomes, list):
                    self.add("contract.setpiece", f"{beat_path}.outcomes", "setpiece needs at least two outcomes")
                else:
                    outcome_ids: list[Any] = []
                    for outcome_index, outcome in enumerate(outcomes):
                        outcome_path = f"{beat_path}.outcomes[{outcome_index}]"
                        if not isinstance(outcome, dict):
                            self.add("contract.shape", outcome_path, "outcome must be an object")
                            continue
                        outcome_ids.append(outcome.get("id"))
                        if not _is_nonempty_string(outcome.get("id")):
                            self.add("contract.shape", f"{outcome_path}.id", "outcome id must be non-empty")
                        if not _is_nonempty_string(outcome.get("verb")):
                            self.add("contract.shape", f"{outcome_path}.verb", "outcome verb must be non-empty")
                    self.check_duplicates(outcome_ids, f"{beat_path}.outcomes", "id")
        self.check_duplicates(ids, path, "id")

    def check_delay_shape(self, costs: Any, path: str) -> None:
        if not isinstance(costs, list):
            self.add("contract.shape", path, "delay_costs must be a list")
            return
        if not costs:
            self.add("contract.shape", path, "delay_costs must contain at least one cost")
            return
        ids: list[Any] = []
        for index, cost in enumerate(costs):
            cost_path = f"{path}[{index}]"
            if not isinstance(cost, dict):
                self.add("contract.shape", cost_path, "delay cost must be an object")
                continue
            ids.append(cost.get("id"))
            if not _is_nonempty_string(cost.get("id")):
                self.add("contract.shape", f"{cost_path}.id", "delay cost id must be non-empty")
            if not _is_nonempty_string(cost.get("window")):
                self.add("contract.shape", f"{cost_path}.window", "window must be non-empty")
        self.check_duplicates(ids, path, "id")

    def check_bond_shape(self, bonds: Any, path: str) -> None:
        if not isinstance(bonds, list):
            self.add("contract.shape", path, "bond_beats must be a list")
            return
        if not bonds:
            self.add("contract.shape", path, "bond_beats must contain at least one beat")
            return
        ids: list[Any] = []
        for index, bond in enumerate(bonds):
            bond_path = f"{path}[{index}]"
            if not isinstance(bond, dict):
                self.add("contract.shape", bond_path, "bond beat must be an object")
                continue
            ids.append(bond.get("id"))
            if not _is_nonempty_string(bond.get("id")):
                self.add("contract.shape", f"{bond_path}.id", "bond beat id must be non-empty")
            if not _is_nonempty_string(bond.get("character")):
                self.add("contract.shape", f"{bond_path}.character", "bond character must be non-empty")
            if bond.get("kind") not in self.bond_kinds:
                self.add("contract.shape", f"{bond_path}.kind", "unknown bond kind")
            if not _is_nonempty_string(bond.get("summary")):
                self.add("contract.shape", f"{bond_path}.summary", "summary must be non-empty")
        self.check_duplicates(ids, path, "id")

    def check_need_shape(self, needs: Any, path: str) -> None:
        if not isinstance(needs, list):
            self.add("contract.shape", path, "world_needs must be a list")
            return
        if not needs:
            self.add("contract.shape", path, "world_needs must contain at least one need")
            return
        ids: list[Any] = []
        for index, need in enumerate(needs):
            need_path = f"{path}[{index}]"
            if not isinstance(need, dict):
                self.add("contract.shape", need_path, "world need must be an object")
                continue
            ids.append(need.get("id"))
            if not _is_nonempty_string(need.get("id")):
                self.add("contract.shape", f"{need_path}.id", "world need id must be non-empty")
            relation = need.get("relation")
            if relation not in self.relations:
                self.add("contract.shape", f"{need_path}.relation", "unknown relation")
            if not _is_nonempty_string(need.get("subject")):
                self.add("contract.shape", f"{need_path}.subject", "subject must be non-empty")
            for field in ("subject_kind", "object_kind"):
                if field in need and not _is_nonempty_string(need[field]):
                    self.add("contract.world_need", f"{need_path}.{field}", f"{field} must be a non-empty string")
            if "role" in need and need["role"] not in self.need_roles:
                self.add("contract.world_need", f"{need_path}.role", "unknown need role")
        self.check_duplicates(ids, path, "id")

    def check_scene_rules(
        self,
        scene: dict[str, Any],
        path: str,
        scene_index: int,
        scenes: list[Any],
        prior_bonds: list[str],
    ) -> None:
        self.check_feeling(scene, path)
        self.check_clock(scene, path)
        self.check_npc(scene, path)
        self.check_beats(scene, path)
        self.check_first_pressure(scene, path)
        self.check_pacing(scene, path)
        self.check_setpieces(scene, path)
        self.check_delays(scene, path)
        self.check_bonds(scene, path, scene_index, scenes, prior_bonds)
        self.check_world_needs(scene, path)

    def check_feeling(self, scene: dict[str, Any], path: str) -> None:
        feeling = scene.get("feeling", _MISSING)
        if isinstance(feeling, str) and not feeling.strip():
            self.add("contract.feeling", f"{path}.feeling", "feeling must be non-empty")

    def check_clock(self, scene: dict[str, Any], path: str) -> None:
        clock = scene.get("clock")
        if isinstance(clock, dict):
            for key in ("running_out", "bridge_hook"):
                if key in clock and isinstance(clock[key], str) and not clock[key].strip():
                    self.add("contract.clock", f"{path}.clock.{key}", "clock text must be non-empty")

    def check_npc(self, scene: dict[str, Any], path: str) -> None:
        npc = scene.get("npc_in_the_way", _MISSING)
        if not isinstance(npc, dict) or npc.get("named_in_entry") is not True:
            self.add("contract.npc", f"{path}.npc_in_the_way", "npc_in_the_way must be named in entry")

    def _beat_items(self, scene: dict[str, Any]) -> list[dict[str, Any]]:
        beats = scene.get("beats")
        return [beat for beat in beats if isinstance(beat, dict)] if isinstance(beats, list) else []

    def check_beats(self, scene: dict[str, Any], path: str) -> None:
        beats = self._beat_items(scene)
        if not beats:
            return
        entry_beats = [beat for beat in beats if beat.get("kind") == self.entry_kind and beat.get("turn") == 1]
        exit_beats = [beat for beat in beats if beat.get("kind") == self.exit_kind]
        if len(entry_beats) != 1:
            self.add("contract.beats", f"{path}.beats", "scene needs exactly one entry beat at turn 1")
        if len(exit_beats) != 1:
            self.add("contract.beats", f"{path}.beats", "scene needs exactly one exit beat")
        valid_turns = [beat["turn"] for beat in beats if _is_int(beat.get("turn")) and beat["turn"] >= 1]
        if exit_beats and valid_turns:
            exit_turn = exit_beats[0].get("turn")
            other_turns = [turn for beat in beats if beat is not exit_beats[0] for turn in [beat.get("turn")]]
            if not _is_int(exit_turn) or any(not _is_int(turn) or exit_turn <= turn for turn in other_turns):
                self.add("contract.beats", f"{path}.beats", "exit turn must be greater than every other beat turn")
        for kind, label in (
            (self.pressure_kind, "pressure"),
            (self.relief_kind, "relief"),
            (self.setpiece_kind, "setpiece"),
        ):
            if not any(beat.get("kind") == kind for beat in beats):
                self.add("contract.beats", f"{path}.beats", f"scene needs a {label} beat")

    def check_first_pressure(self, scene: dict[str, Any], path: str) -> None:
        pressures = [beat for beat in self._beat_items(scene) if beat.get("kind") == self.pressure_kind]
        if not pressures:
            return
        if scene.get("entry_prior_exit_sets_threat", False) is True:
            return
        turns = [beat.get("turn") for beat in pressures if _is_int(beat.get("turn")) and beat["turn"] >= 1]
        if turns and min(turns) not in self.first_pressure_turns:
            self.add(
                "contract.first_pressure",
                f"{path}.beats",
                "earliest pressure is outside the first-pressure window",
            )

    def check_pacing(self, scene: dict[str, Any], path: str) -> None:
        pressure_relief = [
            beat
            for beat in self._beat_items(scene)
            if beat.get("kind") in {self.pressure_kind, self.relief_kind} and _is_int(beat.get("turn"))
        ]
        pressure_relief.sort(key=lambda beat: beat["turn"])
        for previous, current in zip(pressure_relief, pressure_relief[1:], strict=False):
            if current["turn"] - previous["turn"] < self.min_gap_turns:
                self.add("contract.pacing", f"{path}.beats", "pressure and relief beats are too close together")
            if previous.get("kind") == self.pressure_kind and current.get("kind") == self.pressure_kind:
                self.add("contract.pacing", f"{path}.beats", "pressure beats need a relief between them")

    def check_setpieces(self, scene: dict[str, Any], path: str) -> None:
        for index, beat in enumerate(self._beat_items(scene)):
            if beat.get("kind") != self.setpiece_kind:
                continue
            outcomes = beat.get("outcomes")
            if not isinstance(outcomes, list) or len(outcomes) < 2:
                self.add("contract.setpiece", f"{path}.beats[{index}].outcomes", "setpiece needs at least two outcomes")
                continue
            verbs = [
                outcome.get("verb")
                for outcome in outcomes
                if isinstance(outcome, dict) and isinstance(outcome.get("verb"), str)
            ]
            normalized = [verb.strip().casefold() for verb in verbs]
            if len(normalized) != len(set(normalized)):
                self.add(
                    "contract.setpiece",
                    f"{path}.beats[{index}].outcomes",
                    "setpiece outcomes need distinct verbs",
                )
            for outcome_index, verb in enumerate(verbs):
                first_word = verb.strip().split(maxsplit=1)[0].casefold() if verb.strip() else ""
                if first_word in self.reading_verbs:
                    self.add(
                        "contract.setpiece",
                        f"{path}.beats[{index}].outcomes[{outcome_index}].verb",
                        "setpiece outcome cannot be a reading action",
                    )

    def check_delays(self, scene: dict[str, Any], path: str) -> None:
        costs = scene.get("delay_costs")
        if not isinstance(costs, list):
            return
        current_scene = scene.get("scene_id")
        current_position = self.scene_positions.get(current_scene)
        for index, cost in enumerate(costs):
            if not isinstance(cost, dict):
                continue
            cost_path = f"{path}.delay_costs[{index}]"
            kind = cost.get("cost_kind")
            if kind not in self.cost_kinds:
                self.add("contract.delay_cost", f"{cost_path}.cost_kind", "unknown delay cost kind")
                continue
            if not _is_nonempty_string(cost.get("passage_id")):
                self.add("contract.delay_cost", f"{cost_path}.passage_id", "delay cost needs a passage_id")
            if kind == self.riskier_kind and not _is_nonempty_string(cost.get("riskier_storylet_id")):
                self.add("contract.delay_cost", f"{cost_path}.riskier_storylet_id", "riskier storylet cost needs an id")
            if kind in self.harm_kinds:
                for key in ("cost_fact", "harmed", "read_by_scene"):
                    if key == "harmed":
                        valid = (
                            isinstance(cost.get(key), list)
                            and bool(cost[key])
                            and all(_is_nonempty_string(item) for item in cost[key])
                        )
                    else:
                        valid = _is_nonempty_string(cost.get(key))
                    if not valid:
                        self.add("contract.delay_cost", f"{cost_path}.{key}", f"harm cost needs {key}")
            if "cost_fact" in cost and cost.get("cost_fact") is not None:
                read_by_scene = cost.get("read_by_scene")
                if not _is_nonempty_string(read_by_scene):
                    self.add("contract.delay_cost", f"{cost_path}.read_by_scene", "cost_fact needs read_by_scene")
                elif (
                    current_position is None
                    or read_by_scene not in self.scene_positions
                    or self.scene_positions[read_by_scene] <= current_position
                ):
                    self.add("contract.delay_cost", f"{cost_path}.read_by_scene", "read_by_scene must be a later scene")
            harmed = cost.get("harmed")
            if isinstance(harmed, list):
                for harmed_index, character in enumerate(harmed):
                    if isinstance(character, str) and character.casefold() in self.protected_characters:
                        self.add(
                            "contract.protected",
                            f"{cost_path}.harmed[{harmed_index}]",
                            "protected characters cannot be harmed",
                        )

    def check_bonds(
        self,
        scene: dict[str, Any],
        path: str,
        scene_index: int,
        scenes: list[Any],
        prior_bonds: list[str],
    ) -> None:
        costs = scene.get("delay_costs")
        if not isinstance(costs, list):
            return
        bonded = set(prior_bonds)
        for earlier_scene in scenes[: scene_index + 1]:
            if isinstance(earlier_scene, dict):
                bonds = earlier_scene.get("bond_beats")
                if isinstance(bonds, list):
                    bonded.update(
                        bond.get("character")
                        for bond in bonds
                        if isinstance(bond, dict) and _is_nonempty_string(bond.get("character"))
                    )
        for cost_index, cost in enumerate(costs):
            if not isinstance(cost, dict) or not isinstance(cost.get("harmed"), list):
                continue
            for harmed_index, character in enumerate(cost["harmed"]):
                if _is_nonempty_string(character) and character not in bonded:
                    self.add(
                        "contract.bond",
                        f"{path}.delay_costs[{cost_index}].harmed[{harmed_index}]",
                        "harmed character has no prior or scene bond beat",
                    )

    def check_world_needs(self, scene: dict[str, Any], path: str) -> None:
        needs = scene.get("world_needs")
        if not isinstance(needs, list):
            return
        object_relations = {"hold", "know", "reach", "hidden", "seated", "companion"}
        for index, need in enumerate(needs):
            if not isinstance(need, dict):
                continue
            need_path = f"{path}.world_needs[{index}]"
            relation = need.get("relation")
            required = "object" if relation in object_relations else "axis" if relation == "axis" else None
            if required and not _is_nonempty_string(need.get(required)):
                self.add("contract.world_need", f"{need_path}.{required}", f"{relation} relation needs {required}")
            if relation == "axis" and not _is_nonempty_string(need.get("pole")):
                self.add("contract.world_need", f"{need_path}.pole", "axis relation needs pole")

    def check_duplicates(self, values: list[Any], path: str, field: str) -> None:
        seen: set[Any] = set()
        for index, value in enumerate(values):
            if not _is_nonempty_string(value):
                continue
            if value in seen:
                self.add("contract.shape", f"{path}[{index}].{field}", f"duplicate {field}")
            seen.add(value)

    def require_string(self, mapping: dict[str, Any], key: str, prefix: str) -> None:
        value = mapping.get(key, _MISSING)
        path = f"{prefix}.{key}" if prefix else key
        if value is _MISSING or not _is_nonempty_string(value):
            self.add("contract.shape", path, f"{key} must be a non-empty string")

    def check_string_list(self, value: Any, path: str) -> list[str]:
        if not isinstance(value, list):
            self.add("contract.shape", path, "value must be a list")
            return []
        result: list[str] = []
        for index, item in enumerate(value):
            if not _is_nonempty_string(item):
                self.add("contract.shape", f"{path}[{index}]", "value must be a non-empty string")
            else:
                result.append(item)
        return result

    def _character_list(self, value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        return [item for item in value if _is_nonempty_string(item)]


def lint_contract(contract: Any, rules: Mapping[str, Any] | None = None) -> list[Problem]:
    """Return all deterministic lint problems for an act contract."""

    return _ContractLint(rules or load_rules()).run(contract)


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Lint a factory act contract")
    parser.add_argument("file", type=Path)
    parser.add_argument("--rules", type=Path, default=None)
    args = parser.parse_args(argv)
    try:
        with args.file.open(encoding="utf-8") as contract_file:
            contract = json.load(contract_file)
        rules = load_rules(args.rules)
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    problems = lint_contract(contract, rules)
    if not problems:
        print("ok")
        return 0
    for problem in problems:
        print(problem)
    return 1


if __name__ == "__main__":
    raise SystemExit(_main())
