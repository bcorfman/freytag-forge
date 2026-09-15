"""Bench-only tracking of plain facts about named scene things."""

from __future__ import annotations

import copy
from collections.abc import Mapping
from urllib.error import HTTPError, URLError

from storygame.runtime.cloudflare import CloudflareTurnProvider, NarrationProviderError
from storygame.runtime.validation import ProgressionValidator, predicate_matches
from storygame.story_package.models import FactPredicate, ItemPlacement


def package_seed(package, state, scene_id: str) -> tuple[dict[str, dict], list[str]]:
    """Build tracked things from the authored placements and setting facts."""

    scene = next((item for item in package.scenes if item.metadata.scene_id == scene_id), None)
    if scene is None:
        raise ValueError(f"scene {scene_id} is not in package {package.story_id}")
    items = {item.id: item for item in package.world.items}
    locations = {location.id: location for location in package.world.locations}
    things: dict[str, dict] = {}
    issues: list[str] = []
    for item_id, placement in scene.metadata.item_placements.items():
        item = items.get(item_id)
        if item is None:
            issues.append(f"scene {scene_id} placement references unknown item {item_id!r}")
            continue
        if isinstance(placement, ItemPlacement) and placement.while_fact_false:
            guard = FactPredicate(fact_id=placement.while_fact_false, equals=True)
            if predicate_matches(guard, state.facts):
                continue
        where = placement if isinstance(placement, str) else placement.placement
        if len(where) > 80:
            issues.append(f"placement for {item.name!r} is longer than 80 characters")
            continue
        things[item.name] = {"where": where, "condition": []}

    location = locations.get(scene.metadata.location_id)
    location_name = location.name if location is not None else scene.metadata.location_id
    for setting in scene.metadata.setting_facts:
        phrase = setting.strip()
        if phrase.endswith("."):
            phrase = phrase[:-1].rstrip()
        matched = next(
            (name for name in things if phrase.startswith(f"{name} is ") or phrase.startswith(f"{name} are ")), None
        )
        if matched is not None:
            condition = phrase[len(matched) + (4 if phrase.startswith(f"{matched} is ") else 5) :].strip()
            if len(things[matched]["condition"]) >= 2 or len(condition) > 40:
                issues.append(f"setting fact for {matched!r} could not be added as a condition")
                continue
            things[matched]["condition"].append(condition)
            continue
        separator = next((separator for separator in (" is ", " are ") if separator in phrase), None)
        if separator is None:
            issues.append(f"setting fact {setting!r} could not be parsed")
            continue
        name, condition = (part.strip() for part in phrase.split(separator, 1))
        where = f"in {location_name}"
        if not name or len(where) > 80 or len(condition) > 40:
            issues.append(f"setting fact {setting!r} exceeds item-facts limits")
            continue
        things[name] = {"where": where, "condition": [condition]}
    return things, issues


_SINGLE_CALL_RULES = (
    "Also return item_facts for each thing your story moved or changed, and for each new thing it put in a place.",
    "Give only what changed: where it is now, its condition list of up to two short phrases, or both. "
    "Example: if she blows out the cracked, lit lantern on the table, the lantern is "
    '{"condition": ["dark", "cracked"]}.',
)
_MATCH_SYSTEM = (
    "You match names in a story game. COMMAND is what the player typed. THINGS lists the names the game keeps "
    "track of. NEW NAMES lists names the storyteller used. Return only JSON like "
    '{"refers": ["name"], "same_as": {"new name": "name"}}. '
    "In refers, list each name from THINGS that the command talks about, even when the command uses other words, like "
    '"the old lamp" for "Grandma\'s lamp". In same_as, give each name in NEW NAMES the name from THINGS that means '
    'the same thing, or "new" if it is a different thing. Copy names from THINGS exactly.'
)
_SECOND_CALL_SYSTEM = (
    "You keep track of things in a story. Read THINGS, PLAYER and STORY. Return only JSON like "
    '{"item_facts": {"thing": {"where": "place", "condition": ["phrase"]}}}. List only the things '
    "in THINGS that STORY changed. For each one, give where it is now and up to two short condition phrases. "
    "Example: if she picks up the lantern from the table, the lantern is "
    '{"where": "in her hand", "condition": ["lit"]}. If STORY changed nothing, return {"item_facts": {}}.'
)


class ItemFactsProvider(CloudflareTurnProvider):
    """Cloudflare provider with a bench-only, plain-facts side channel."""

    def __init__(
        self,
        *,
        item_facts: Mapping[str, Mapping[str, object]],
        mode: str,
        seed_issues: list[str] | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(**kwargs)
        self.item_facts = {
            name: {"where": facts["where"], "condition": list(facts["condition"])} for name, facts in item_facts.items()
        }
        self.item_facts_seed_names = tuple(self.item_facts)
        self.item_facts_mode = mode
        self.item_facts_seed_issues = list(seed_issues or [])
        self._pending_item_facts: object = None
        self._pending_item_facts_present = False
        self._held_item_facts: dict[str, dict[str, object]] = {}
        self._changed_last_turn: set[str] = set()
        self._selected_names: list[str] | None = None
        self.item_facts_match_calls = 0
        package_names, _ = package_seed(self.state.package, self.state, self.state.current_scene_id)
        self._hand_seed_names = {name for name in self.item_facts if name not in package_names}

    @classmethod
    def from_environment(
        cls,
        state,
        *,
        prompt_variant: Mapping[str, object] | None = None,
        item_facts: Mapping[str, Mapping[str, object]],
        mode: str,
        seed_issues: list[str] | None = None,
    ) -> ItemFactsProvider:
        # Let the shipped provider perform its normal environment validation and
        # then reuse the resolved transport settings for this bench subclass.
        base = CloudflareTurnProvider.from_environment(state, prompt_variant=prompt_variant)
        return cls(
            worker_url=base.worker_url,
            token=base.token,
            state=state,
            projector=base.projector,
            prompt_variant=prompt_variant,
            item_facts=item_facts,
            mode=mode,
            seed_issues=seed_issues,
        )

    def _things_block(self) -> str:
        lines = ["THINGS:"]
        names = self._selected_names if self._selected_names is not None else self.always_included_names()
        for name in names:
            facts = self.item_facts[name]
            conditions = facts["condition"]
            line = f"- {name}. Where: {facts['where']}."
            if conditions:
                line += f" Condition: {', '.join(conditions)}."
            lines.append(line)
        return "\n".join(lines)

    def _section_user_prompt(self, user: dict[str, object]) -> str:
        rendered = super()._section_user_prompt(user)
        things = self._things_block()
        marker = "\n\nCONSTRAINTS:"
        if marker in rendered:
            return rendered.replace(marker, f"\n\n{things}{marker}", 1)
        return f"{rendered}\n\n{things}" if rendered else things

    def _placement_rules(self) -> list[str]:
        return []

    def _setting_fact_rules(self) -> list[str]:
        return []

    def _system_prompt(self) -> str:
        system = super()._system_prompt()
        if self.item_facts_mode == "single_call":
            return f"{system}\n{_SINGLE_CALL_RULES[0]}\n{_SINGLE_CALL_RULES[1]}"
        return system

    def _request(self, payload: dict[str, object]) -> object:
        response = super()._request(payload)
        if isinstance(response, dict):
            self._pending_item_facts_present = "item_facts" in response
            self._pending_item_facts = copy.deepcopy(response.get("item_facts"))
            cleaned = dict(response)
            cleaned.pop("item_facts", None)
            return cleaned
        self._pending_item_facts_present = False
        self._pending_item_facts = copy.deepcopy(response)
        return response

    def pending_item_facts(self) -> object:
        return copy.deepcopy(self._pending_item_facts) if self._pending_item_facts_present else None

    def discard_pending_item_facts(self) -> None:
        self._pending_item_facts = None
        self._pending_item_facts_present = False

    def always_included_names(self) -> list[str]:
        package_names, _ = package_seed(self.state.package, self.state, self.state.current_scene_id)
        required_ids = {
            dependency
            for transition in ProgressionValidator(self.state.package)._reachable_transitions(
                self.state.current_scene_id
            )
            for dependency in transition.required_dependencies
        }
        dependency_names = {item.name for item in self.state.package.world.items if item.id in required_ids}
        protagonist = self._protagonist_name().casefold()
        carried = {name for name, facts in self.item_facts.items() if protagonist in str(facts["where"]).casefold()}
        included = set(package_names) | self._hand_seed_names | dependency_names | carried | self._changed_last_turn
        # Use the live store here.  Tests and bench callers may add tracked
        # things after construction; those things still need to participate in
        # dependency and carried-item selection.
        return [name for name in self.item_facts if name in included]

    def facts_for_names(self, names: list[str] | tuple[str, ...] | set[str]) -> dict[str, dict[str, object]]:
        wanted = set(names)
        return {
            name: {"where": facts["where"], "condition": list(facts["condition"])}
            for name, facts in self.item_facts.items()
            if name in wanted
        }

    @staticmethod
    def _valid_entry(value: object) -> bool:
        if not isinstance(value, dict) or not value:
            return False
        if "where" in value and (not isinstance(value["where"], str) or not value["where"].strip()):
            return False
        if "condition" in value and (
            not isinstance(value["condition"], list)
            or any(not isinstance(item, str) or not item.strip() for item in value["condition"])
        ):
            return False
        return "where" in value or "condition" in value

    def _merge_entry(self, name: str, value: dict[str, object]) -> bool:
        facts = self.item_facts[name]
        if "where" in value:
            where = value["where"]
            if not isinstance(where, str) or not where.strip():
                return False
            facts["where"] = where.strip()[:80]
        if "condition" in value:
            condition = value["condition"]
            if not isinstance(condition, list) or any(
                not isinstance(item, str) or not item.strip() for item in condition
            ):
                return False
            facts["condition"] = [item.strip()[:40] for item in condition[:2]]
        return True

    def apply_item_facts(self, raw: object) -> tuple[dict[str, dict[str, object]], list[str]]:
        previous = {
            name: {"where": facts["where"], "condition": list(facts["condition"])}
            for name, facts in self.item_facts.items()
        }
        issues: list[str] = []
        if not isinstance(raw, dict):
            issues.append("item_facts must be an object mapping thing names to fact objects")
            return previous, issues

        self._held_item_facts = {}
        changed: set[str] = set()
        for name, value in raw.items():
            if name not in self.item_facts:
                if isinstance(value, dict) and not value:
                    continue
                if self._valid_entry(value):
                    self._held_item_facts[name] = copy.deepcopy(value)
                    issues.append(f"item_facts name {name} held for matching")
                else:
                    issues.append(f"unknown item_facts name {name!r} was dropped")
                continue
            if isinstance(value, dict) and not value:
                issues.append(f"empty item_facts entry for {name} ignored")
                continue
            if not self._valid_entry(value):
                issues.append(f"item_facts for {name!r} has invalid where or condition")
                continue
            before = copy.deepcopy(self.item_facts[name])
            if self._merge_entry(name, value) and before != self.item_facts[name]:
                changed.add(name)
            if isinstance(value.get("condition"), list) and len(value["condition"]) > 2:
                issues.append(f"item_facts for {name!r} has more than two condition phrases; kept the first two")
        self._changed_last_turn = changed
        return copy.deepcopy(self.item_facts), issues

    def prepare_turn(self, player_input: str) -> dict[str, object]:
        always = self.always_included_names()
        candidates = [name for name in self.item_facts if name not in always]
        held = list(self._held_item_facts)
        if not candidates and not held:
            self._selected_names = always
            return {"match_call": False, "match_raw": None, "match_issues": [], "resolutions": {}}
        self.item_facts_match_calls += 1
        payload = {
            "system": _MATCH_SYSTEM,
            "user": (
                f"COMMAND:\n- {player_input}\n\nTHINGS:\n"
                + "\n".join(f"- {name}" for name in self.item_facts)
                + "\n\nNEW NAMES:\n"
                + ("\n".join(f"- {name}" for name in held) if held else "- (none)")
            ),
            "max_tokens": 200,
            "response_format": {"type": "json_object"},
        }
        issues: list[str] = []
        resolutions: dict[str, str] = {}
        try:
            reply = CloudflareTurnProvider._request(self, payload)
        except Exception as error:
            reply = None
            issues.append(f"item_facts match failed: {error}")
        valid = (
            isinstance(reply, dict) and isinstance(reply.get("refers"), list) and isinstance(reply.get("same_as"), dict)
        )
        if not valid:
            if held:
                issues.append("invalid item_facts match reply")
            for name in held:
                resolutions[name] = "dropped"
            self._held_item_facts = {}
            self._selected_names = always
        else:
            refers = [
                name
                for name in reply["refers"]
                if isinstance(name, str) and name in self.item_facts and name in candidates
            ]
            for name in held:
                target = reply["same_as"].get(name)
                entry = self._held_item_facts[name]
                if isinstance(target, str) and target in self.item_facts:
                    before = copy.deepcopy(self.item_facts[target])
                    if self._merge_entry(target, entry):
                        if before != self.item_facts[target]:
                            self._changed_last_turn.add(target)
                        resolutions[name] = target
                    else:
                        resolutions[name] = "dropped"
                elif target == "new" and isinstance(entry.get("where"), str) and entry["where"].strip():
                    self.item_facts[name] = {"where": entry["where"].strip()[:80], "condition": []}
                    self._merge_entry(name, entry)
                    self.item_facts_seed_names = (*self.item_facts_seed_names, name)
                    self._changed_last_turn.add(name)
                    resolutions[name] = "new"
                else:
                    issues.append(f"item_facts name {name} had no valid match")
                    resolutions[name] = "dropped"
            self._held_item_facts = {}
            selected = set(self.always_included_names()) | set(refers)
            self._selected_names = [name for name in self.item_facts if name in selected]
        return {
            "match_call": True,
            "match_raw": copy.deepcopy(reply),
            "match_issues": issues,
            "resolutions": resolutions,
        }

    def resolve_held(self) -> dict[str, object]:
        if not self._held_item_facts:
            return {"match_call": False, "match_raw": None, "match_issues": [], "resolutions": {}}
        return self.prepare_turn("(none)")

    def second_call_update(self, player_input: str, narration: str) -> object:
        payload = {
            "system": _SECOND_CALL_SYSTEM,
            "user": f"{self._things_block()}\n\nPLAYER:\n- {player_input}\n\nSTORY:\n{narration}",
            "max_tokens": 400,
            "response_format": {"type": "json_object"},
        }
        try:
            response = self._request_allowing_one_transient_retry(payload)
        except NarrationProviderError:
            raise
        except (HTTPError, URLError, OSError, TimeoutError, ValueError) as error:
            raise NarrationProviderError("narration service is unavailable") from error
        if self._pending_item_facts_present:
            return copy.deepcopy(self._pending_item_facts)
        return response


def validate_item_facts(value: object) -> tuple[str, dict[str, dict[str, object]]] | None:
    """Validate and copy a variation's item_facts option."""

    if not isinstance(value, dict):
        raise ValueError("item_facts must be an object with mode and seed")
    mode = value.get("mode")
    if mode not in {"single_call", "second_call"}:
        raise ValueError("item_facts must have mode single_call or second_call")
    seed_from_package = value.get("seed_from_package", False)
    if not isinstance(seed_from_package, bool):
        raise ValueError("item_facts seed_from_package must be a boolean")
    seed = value.get("seed", {})
    if not isinstance(seed, dict) or (not seed and not seed_from_package):
        raise ValueError("item_facts must have a non-empty seed unless seed_from_package is enabled")
    copied: dict[str, dict[str, object]] = {}
    for name, facts in seed.items():
        if not isinstance(name, str) or not name.strip():
            raise ValueError("item_facts seed names must be non-empty strings")
        if (
            not isinstance(facts, dict)
            or not isinstance(facts.get("where"), str)
            or not facts["where"].strip()
            or len(facts["where"].strip()) > 80
            or not isinstance(facts.get("condition"), list)
            or len(facts["condition"]) > 2
            or not all(
                isinstance(condition, str) and condition.strip() and len(condition.strip()) <= 40
                for condition in facts["condition"]
            )
        ):
            raise ValueError(
                f"item_facts seed for {name!r} must have a where and zero to two non-empty condition phrases"
            )
        copied[name] = {
            "where": facts["where"].strip(),
            "condition": [condition.strip() for condition in facts["condition"]],
        }
    return mode, copied
