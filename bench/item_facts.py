"""Bench-only tracking of plain facts about named scene things."""

from __future__ import annotations

import copy
from collections.abc import Mapping
from urllib.error import HTTPError, URLError

from storygame.runtime.cloudflare import CloudflareTurnProvider, NarrationProviderError
from storygame.runtime.validation import ProgressionValidator
from storygame.story_package.models import ItemPlacement, item_placement_is_visible


def _resolve_refer(name: str, tracked) -> str | None:
    tracked_names = list(tracked)
    if name in tracked_names:
        return name

    def normalize(value: str) -> str:
        normalized = value.strip().lower().rstrip(".,;:!?").strip()
        for article in ("the", "my", "a", "an"):
            if normalized.startswith(f"{article} "):
                return normalized[len(article) + 1 :]
        return normalized

    normalized_name = normalize(name)
    if not normalized_name:
        return None
    normalized_tracked = [(tracked_name, normalize(tracked_name)) for tracked_name in tracked_names]
    exact_matches = [tracked_name for tracked_name, value in normalized_tracked if value == normalized_name]
    if len(exact_matches) == 1:
        return exact_matches[0]
    suffix_matches = [
        tracked_name for tracked_name, value in normalized_tracked if value.endswith(f" {normalized_name}")
    ]
    return suffix_matches[0] if len(suffix_matches) == 1 else None


def _protagonist_name(package) -> str | None:
    """Return the short protagonist name used by the narration provider."""

    npc = next((entity for entity in package.world.npcs if entity.id == package.protagonist_id), None)
    if npc is None:
        return None
    return min((*npc.aliases, npc.name), key=len)


def _seed_protagonist(package, scene, things: dict[str, dict], issues: list[str]) -> None:
    protagonist_name = _protagonist_name(package)
    location = next((item for item in package.world.locations if item.id == scene.metadata.location_id), None)
    if protagonist_name is None:
        issues.append(f"protagonist NPC {package.protagonist_id!r} is missing")
    if location is None:
        issues.append(f"scene {scene.metadata.scene_id} location {scene.metadata.location_id!r} is missing")
    if protagonist_name is None or location is None:
        return
    things[protagonist_name] = {"place": f"in {location.name}", "condition": []}


def _package_seed(package, state, scene_id: str) -> tuple[dict[str, dict], list[str], list[str]]:
    """Build tracked things and classify the authored setting facts once."""

    scene = next((item for item in package.scenes if item.metadata.scene_id == scene_id), None)
    if scene is None:
        raise ValueError(f"scene {scene_id} is not in package {package.story_id}")
    items = {item.id: item for item in package.world.items}
    things: dict[str, dict] = {}
    issues: list[str] = []
    unconsumed_setting_facts: list[str] = []
    _seed_protagonist(package, scene, things, issues)
    for item_id, placement in scene.metadata.item_placements.items():
        item = items.get(item_id)
        if item is None:
            issues.append(f"scene {scene_id} placement references unknown item {item_id!r}")
            continue
        if not item_placement_is_visible(placement, state.facts):
            continue
        place = placement if isinstance(placement, str) else placement.placement
        if len(place) > 80:
            issues.append(f"placement for {item.name!r} is longer than 80 characters")
            continue
        things[item.name] = {"place": place, "condition": []}

    for setting in scene.metadata.setting_facts:
        phrase = setting.strip()
        if phrase.endswith("."):
            phrase = phrase[:-1].rstrip()
        matched_prefix = next(
            (
                (name, prefix)
                for name in things
                for prefix in (f"{name} is ", f"{name} are ", f"The {name} is ", f"The {name} are ")
                if phrase.casefold().startswith(prefix.casefold())
            ),
            None,
        )
        matched = matched_prefix[0] if matched_prefix is not None else None
        if matched is not None:
            condition = phrase[len(matched_prefix[1]) :].strip()
            condition = condition.removeprefix("is ").removeprefix("are ").strip()
            if len(things[matched]["condition"]) >= 2 or len(condition) > 40:
                issues.append(f"setting fact for {matched!r} could not be added as a condition")
                unconsumed_setting_facts.append(setting)
                continue
            things[matched]["condition"].append(condition)
            continue
        separator = next((separator for separator in (" is ", " are ") if separator in phrase), None)
        if separator is None:
            issues.append(f"setting fact {setting!r} could not be parsed")
            unconsumed_setting_facts.append(setting)
            continue
        name, condition = (part.strip() for part in phrase.split(separator, 1))
        if not name or len(condition) > 40:
            issues.append(f"setting fact {setting!r} exceeds item-facts limits")
            unconsumed_setting_facts.append(setting)
            continue
        issues.append(f"setting fact for unplaced thing {name!r}: {setting!r}")
        unconsumed_setting_facts.append(setting)
    return things, issues, unconsumed_setting_facts


def package_seed(package, state, scene_id: str) -> tuple[dict[str, dict], list[str]]:
    """Build tracked things from the authored placements and setting facts."""

    things, issues, _ = _package_seed(package, state, scene_id)
    return things, issues


_SINGLE_CALL_RULES = (
    "Every time your story moves or changes a thing, or puts a new thing in a place, add that thing to item_facts. "
    "Use where it is when the story ends.",
    'Give only what changed. Use "place" for its current location and "condition" for up to two short phrases. '
    'Example: if she throws a cup at the wall, it cracks in two and falls, so the cup is {"place": "on the floor", '
    '"condition": ["cracked in two"]}.',
)


def _single_call_rules(protagonist_name: str | None) -> tuple[str, ...]:
    if protagonist_name is None:
        return _SINGLE_CALL_RULES
    protagonist_rule = (
        f"When {protagonist_name} goes to a new place, add {protagonist_name} to item_facts "
        "with the place she is when the story ends."
    )
    return (_SINGLE_CALL_RULES[0], protagonist_rule, _SINGLE_CALL_RULES[1])


_MATCH_SYSTEM = (
    "You match names in a story game. COMMAND is what the player typed. PLAYER CHARACTER is who the player plays. "
    "THINGS lists the names the game keeps track of, some with the place they are now. NEW NAMES lists names the "
    "storyteller used. Return only JSON like "
    '{"refers": ["name"], "same_as": {"new name": "name"}}. '
    "In refers, list each name from THINGS that the command talks about, even when the command uses other words, "
    'like "the old lamp" for "Grandma\'s lamp". '
    "List only the things the command itself names or points to. "
    "Do not list a thing because it is nearby. "
    "Do not list a thing because someone holds it. "
    'For "Ask the cook who took the key." list only the cook and the key. '
    "In same_as, give each name in NEW NAMES the name from THINGS "
    'that is the very same object, or "new" if it is a different object. A thing that is in, on or under another '
    "thing is a different object, like a key in a box. Copy names from THINGS exactly."
)
_SECOND_CALL_SYSTEM = (
    "You keep track of things in a story. Read THINGS, PLAYER and STORY. Return only JSON like "
    '{"item_facts": {"thing": {"place": "place", "condition": ["phrase"]}}}. List only the things '
    "in THINGS that STORY changed. For each one, give the place it is now and up to two short condition phrases. "
    "Example: if she picks up the lantern from the table, the lantern is "
    '{"place": "in her hand", "condition": ["lit"]}. If STORY changed nothing, return {"item_facts": {}}.'
)


class ItemFactsProvider(CloudflareTurnProvider):
    """Cloudflare provider with a bench-only, plain-facts side channel."""

    allowed_reply_keys = CloudflareTurnProvider.allowed_reply_keys | {"item_facts"}

    def _object_place_rule(self) -> str:
        return "Each thing starts at the place THINGS gives it."

    def _prepare_turn_visibility(self) -> None:
        super()._prepare_turn_visibility()
        package = self.state.package
        items = {item.id: item for item in package.world.items}
        for item_id, placement in self._current_scene().item_placements.items():
            item = items.get(item_id)
            if (
                item is None
                or item.name in self.item_facts
                or not isinstance(placement, ItemPlacement)
                or (placement.while_fact_false is None and placement.while_fact_true is None)
            ):
                continue
            if not item_placement_is_visible(placement, self._placement_facts()):
                continue
            place = placement if isinstance(placement, str) else placement.placement
            self.item_facts[item.name] = {"place": place, "condition": []}
            self.item_facts_seed_names = (*self.item_facts_seed_names, item.name)
            if self._selected_names is None:
                self._selected_names = self.dependency_names()
            self._selected_names.append(item.name)

    def __init__(
        self,
        *,
        item_facts: Mapping[str, Mapping[str, object]],
        mode: str,
        state_axes: Mapping[str, Mapping[str, list[str]]] | None = None,
        seed_issues: list[str] | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(**kwargs)
        self.item_facts = {
            name: {"place": facts["place"], "condition": list(facts["condition"])} for name, facts in item_facts.items()
        }
        self.item_facts_seed_names = tuple(self.item_facts)
        self.item_facts_mode = mode
        self.item_facts_seed_issues = list(seed_issues or [])
        self._pending_item_facts: object = None
        self._pending_item_facts_present = False
        self._held_item_facts: dict[str, dict[str, object]] = {}
        self.state_axes = copy.deepcopy(state_axes or {})
        self._changed_last_turn: set[str] = set()
        self._selected_names: list[str] | None = None
        self._last_item_facts_match: dict[str, object] = {
            "match_call": False,
            "match_raw": None,
            "match_issues": [],
            "resolutions": {},
            "engine_resolutions": {},
        }
        self.item_facts_match_calls = 0
        self.item_facts_axis_fixes = 0
        self.item_facts_reply_keys = {"place": 0}
        self.item_facts_lifted = 0
        self._item_facts_issues: list[str] = []
        package = getattr(self.state, "package", None)
        self._fixed_item_names = {
            item.name for item in getattr(getattr(package, "world", None), "items", ()) if getattr(item, "fixed", False)
        }
        package_names, _ = (
            package_seed(package, self.state, self.state.current_scene_id) if package is not None else ({}, [])
        )
        self._hand_seed_names = {name for name in self.item_facts if name not in package_names}

    @classmethod
    def from_environment(
        cls,
        state,
        *,
        prompt_variant: Mapping[str, object] | None = None,
        item_facts: Mapping[str, Mapping[str, object]],
        mode: str,
        state_axes: Mapping[str, Mapping[str, list[str]]] | None = None,
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
            state_axes=state_axes,
            seed_issues=seed_issues,
        )

    def _things_block(self) -> str:
        names = self._thing_names()
        if not names:
            return ""
        lines = ["THINGS:"]
        for name in names:
            facts = self.item_facts[name]
            conditions = facts["condition"]
            place = facts.get("place")
            line = f"- {name}."
            if isinstance(place, str) and place.strip():
                line += f" Place: {place.strip()}."
            axes = self.state_axes.get(name)
            if axes:
                poles = list(axes)
                axis_value = next((condition for condition in conditions if condition in axes), None)
                non_axis = [condition for condition in conditions if condition not in axes]
                if axis_value is not None:
                    opposite = poles[1] if axis_value == poles[0] else poles[0]
                    condition_text = f"{axis_value} (or {opposite})"
                    if non_axis:
                        condition_text += f", {', '.join(non_axis)}"
                    line += f" Condition: {condition_text}."
                elif non_axis:
                    line += f" Condition: {', '.join(non_axis)}."
            elif conditions:
                line += f" Condition: {', '.join(conditions)}."
            lines.append(line)
        return "\n".join(lines)

    def _thing_names(self) -> list[str]:
        names = list(self._selected_names if self._selected_names is not None else self.dependency_names())
        protagonist_name = _protagonist_name(self.state.package)
        if protagonist_name in self.item_facts and protagonist_name not in names:
            names.append(protagonist_name)
        return names

    def _select_protagonist(self) -> None:
        if self._selected_names is None:
            return
        protagonist_name = _protagonist_name(self.state.package)
        if protagonist_name in self.item_facts and protagonist_name not in self._selected_names:
            self._selected_names.append(protagonist_name)

    def _player_lines(self, user: dict[str, object]) -> list[str]:
        lines = super()._player_lines(user)
        if not lines or "scene_setting" not in user:
            return lines
        place_lines = []
        for name in self._thing_names():
            place = self.item_facts[name].get("place")
            if isinstance(place, str) and place.strip():
                place_lines.append(f"{name} is {place.strip()}.")
        return place_lines + lines

    def _section_user_prompt(self, user: dict[str, object]) -> str:
        rendered = super()._section_user_prompt(user)
        things = self._things_block()
        if not things:
            return rendered
        marker = "\n\nCONSTRAINTS:"
        if marker in rendered:
            return rendered.replace(marker, f"\n\n{things}{marker}", 1)
        return f"{rendered}\n\n{things}" if rendered else things

    def _placement_rules(self) -> list[str]:
        return []

    def _setting_fact_rules(self) -> list[str]:
        package = getattr(self.state, "package", None)
        if package is None:
            return []
        _, _, unconsumed = _package_seed(package, self.state, self.state.current_scene_id)
        return unconsumed

    def _system_rules(self, opening: bool) -> list[str]:
        if self.prompt_variant and self.prompt_variant.get("constant_rules_in_system") is True:
            return self._constant_opening_rules() if opening else self._constant_turn_rules()
        return []

    def _system_prompt(self, opening: bool = False) -> str:
        system = super()._system_prompt(opening=opening)
        if self.item_facts_mode == "single_call":
            rules = _single_call_rules(_protagonist_name(self.state.package))
            return f"{system}\n{'\n'.join(rules)}"
        return system

    def _request(self, payload: dict[str, object]) -> object:
        response = super()._request(payload)
        if isinstance(response, dict):
            if "segments" in response:
                item_facts = response.get("item_facts")
                if isinstance(item_facts, dict):
                    for name, entry in list(response.items()):
                        if name in self.allowed_reply_keys:
                            continue
                        if isinstance(entry, dict) and ({"place", "condition"} & entry.keys()):
                            if name not in item_facts:
                                item_facts[name] = entry
                                self.item_facts_lifted += 1
                            del response[name]
                elif "item_facts" not in response:
                    lifted = {
                        name: entry
                        for name, entry in list(response.items())
                        if name not in self.allowed_reply_keys
                        and isinstance(entry, dict)
                        and ({"place", "condition"} & entry.keys())
                    }
                    if lifted:
                        response["item_facts"] = lifted
                        item_facts = lifted
                        self.item_facts_lifted += len(lifted)
                        for name in lifted:
                            del response[name]
            self._pending_item_facts_present = "item_facts" in response
            self._pending_item_facts = copy.deepcopy(response.get("item_facts"))
            item_facts = response.get("item_facts")
            if isinstance(item_facts, dict):
                for entry in item_facts.values():
                    if isinstance(entry, dict) and "place" in entry:
                        self.item_facts_reply_keys["place"] += 1
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

    def last_item_facts_match(self) -> dict[str, object]:
        return copy.deepcopy(self._last_item_facts_match)

    def dependency_names(self) -> list[str]:
        required_ids = {
            dependency
            for transition in ProgressionValidator(self.state.package)._reachable_transitions(
                self.state.current_scene_id
            )
            for dependency in transition.required_dependencies
        }
        dependency_names = {item.name for item in self.state.package.world.items if item.id in required_ids}
        return [name for name in self.item_facts if name in dependency_names]

    def facts_for_names(self, names: list[str] | tuple[str, ...] | set[str]) -> dict[str, dict[str, object]]:
        wanted = set(names)
        return {
            name: {"place": facts["place"], "condition": list(facts["condition"])}
            for name, facts in self.item_facts.items()
            if name in wanted
        }

    @staticmethod
    def _valid_entry(value: object) -> bool:
        if not isinstance(value, dict) or not value:
            return False
        if "place" in value and (not isinstance(value["place"], str) or not value["place"].strip()):
            return False
        if "condition" in value and (
            not isinstance(value["condition"], list)
            or any(not isinstance(item, str) or not item.strip() for item in value["condition"])
        ):
            return False
        return "place" in value or "condition" in value

    def _merge_entry(self, name: str, value: dict[str, object]) -> bool:
        facts = self.item_facts[name]
        place_pole: str | None = None
        if "place" in value:
            place = value["place"]
            if not isinstance(place, str) or not place.strip():
                return False
            place_pole = self._axis_match(name, place)
            if place_pole is None:
                current_place = facts.get("place")
                repeated_place = (
                    isinstance(current_place, str) and current_place.strip().casefold() == place.strip().casefold()
                )
                if name in self._fixed_item_names and not repeated_place:
                    self._item_facts_issues.append(
                        f"item_facts for {name!r} refused place {place.strip()[:80]!r} because it is fixed"
                    )
                elif not repeated_place:
                    facts["place"] = place.strip()[:80]
        if "condition" in value:
            condition = value["condition"]
            if not isinstance(condition, list) or any(
                not isinstance(item, str) or not item.strip() for item in condition
            ):
                return False

        before_pole = next(
            (self._axis_match(name, item) for item in facts["condition"] if self._axis_match(name, item) is not None),
            None,
        )
        reply_poles = [place_pole] if place_pole is not None else []
        if "condition" in value:
            reply_poles.extend(
                pole for item in value["condition"] if (pole := self._axis_match(name, item)) is not None
            )
        distinct_poles = set(reply_poles)
        changed_pole = None
        if len(distinct_poles) > 1 and before_pole is not None:
            differing_poles = {pole for pole in distinct_poles if pole != before_pole}
            if len(differing_poles) == 1:
                changed_pole = differing_poles.pop()

        if place_pole is not None:
            if changed_pole is None or changed_pole == place_pole:
                self._apply_conditions(name, [place_pole], replace=False)
            self.item_facts_axis_fixes += 1
        if "condition" in value and value["condition"]:
            conditions = value["condition"]
            if changed_pole is not None:
                conditions = [item for item in conditions if self._axis_match(name, item) in (None, changed_pole)]
            if conditions:
                self._apply_conditions(name, conditions[:2])
        return True

    def _axis_match(self, name: str, text: str) -> str | None:
        folded = text.strip().casefold()
        for pole, aliases in self.state_axes.get(name, {}).items():
            if folded == pole.casefold() or any(folded == alias.casefold() for alias in aliases):
                return pole
        return None

    def _apply_conditions(self, name: str, conditions: list[str], *, replace: bool = True) -> None:
        current_axis: str | None = None
        non_axis: list[str] = []
        for condition in self.item_facts[name]["condition"]:
            pole = self._axis_match(name, condition)
            if pole is not None:
                current_axis = pole
            else:
                non_axis.append(condition)
        if replace:
            non_axis = []
        for condition in conditions:
            pole = self._axis_match(name, condition)
            if pole is not None:
                current_axis = pole
            else:
                non_axis.append(condition.strip()[:40])
        self.item_facts[name]["condition"] = ([current_axis] if current_axis is not None else []) + list(
            dict.fromkeys(non_axis)
        )[:2]

    def _match_thing_line(self, name: str, facts: Mapping[str, object], *, bare: bool = False) -> str:
        if bare:
            return f"- {name}"
        line = f"- {name}."
        place = facts.get("place")
        if isinstance(place, str) and place.strip():
            line += f" Place: {place.strip()[:80]}."
        elif facts.get("condition"):
            line += f" Condition: {', '.join(facts['condition'])}."
        return line

    def _match_payload(self, player_input: str, new_names: list[str], dependencies: set[str]) -> dict[str, object]:
        match_things = [
            self._match_thing_line(name, self.item_facts[name], bare=name in dependencies) for name in self.item_facts
        ]
        match_things.extend(self._match_thing_line(name, self._held_item_facts[name]) for name in new_names)
        return {
            "system": _MATCH_SYSTEM,
            "user": (
                f"COMMAND:\n- {player_input}\n\nPLAYER CHARACTER:\n- {self._protagonist_name()}\n\nTHINGS:\n"
                + "\n".join(match_things)
                + "\n\nNEW NAMES:\n"
                + ("\n".join(f"- {name}" for name in new_names) if new_names else "- (none)")
            ),
            "max_tokens": 200,
            "response_format": {"type": "json_object"},
        }

    def _add_new_item(self, name: str, entry: dict[str, object]) -> None:
        place = entry.get("place")
        self.item_facts[name] = {
            "place": place.strip()[:80] if isinstance(place, str) else None,
            "condition": [],
        }
        self._merge_entry(name, entry)
        self.item_facts_seed_names = (*self.item_facts_seed_names, name)
        self._changed_last_turn.add(name)

    def _resolve_new_items(self, player_input: str) -> None:
        names = list(self._held_item_facts)
        if not names:
            return
        issues: list[str] = []
        resolutions: dict[str, str] = {}
        engine_resolutions: dict[str, str] = {}
        unresolved_names: list[str] = []
        for name in names:
            entry = self._held_item_facts[name]
            owner = entry.get("owner")
            candidate = f"{owner}'s {name}" if isinstance(owner, str) else None
            matches = [
                tracked for tracked in self.item_facts if candidate and tracked.casefold() == candidate.casefold()
            ]
            if len(matches) != 1:
                unresolved_names.append(name)
                continue
            target = matches[0]
            before = copy.deepcopy(self.item_facts[target])
            self._merge_entry(target, entry)
            if before != self.item_facts[target]:
                self._changed_last_turn.add(target)
            resolutions[name] = target
            engine_resolutions[name] = target

        if not unresolved_names:
            self._held_item_facts = {}
            self._last_item_facts_match = {
                "match_call": False,
                "match_raw": None,
                "match_issues": [],
                "resolutions": resolutions,
                "engine_resolutions": engine_resolutions,
            }
            return

        dependencies = set(self.dependency_names())
        payload = self._match_payload(player_input, unresolved_names, dependencies)
        self.item_facts_match_calls += 1
        try:
            reply = CloudflareTurnProvider._request(self, payload)
        except Exception as error:
            reply = None
            issues.append(f"item_facts match failed: {error}")
        valid = (
            isinstance(reply, dict) and isinstance(reply.get("refers"), list) and isinstance(reply.get("same_as"), dict)
        )
        if not valid:
            issues.append("invalid item_facts match reply")
        for name in unresolved_names:
            entry = self._held_item_facts[name]
            target = reply.get("same_as", {}).get(name) if isinstance(reply, dict) else None
            if isinstance(target, str) and target != name and target in self.item_facts:
                before = copy.deepcopy(self.item_facts[target])
                self._merge_entry(target, entry)
                if before != self.item_facts[target]:
                    self._changed_last_turn.add(target)
                resolutions[name] = target
            else:
                self._add_new_item(name, entry)
                resolutions[name] = "new"
        self._held_item_facts = {}
        self._last_item_facts_match = {
            "match_call": True,
            "match_raw": copy.deepcopy(reply),
            "match_issues": issues,
            "resolutions": resolutions,
            "engine_resolutions": engine_resolutions,
        }

    def apply_item_facts(
        self, raw: object, *, player_input: str = "(none)"
    ) -> tuple[dict[str, dict[str, object]], list[str]]:
        previous = {
            name: {"place": facts["place"], "condition": list(facts["condition"])}
            for name, facts in self.item_facts.items()
        }
        issues: list[str] = []
        if not isinstance(raw, dict):
            self._changed_last_turn = set()
            self._held_item_facts = {}
            self._item_facts_issues = issues
            if raw is None:
                issues.append("narrator omitted item_facts")
            else:
                issues.append("item_facts must be an object mapping thing names to fact objects")
            return previous, issues

        self._held_item_facts = {}
        self._item_facts_issues = issues
        changed: set[str] = set()
        for name, value in raw.items():
            if name not in self.item_facts:
                if isinstance(value, dict) and not value:
                    continue
                if self._valid_entry(value):
                    self._held_item_facts[name] = copy.deepcopy(value)
                else:
                    issues.append(f"unknown item_facts name {name!r} was dropped")
                continue
            protagonist_name = _protagonist_name(self.state.package)
            if name == protagonist_name and isinstance(value, dict) and "condition" in value:
                issues.append(f"item_facts condition for {name} ignored")
                value = {key: item for key, item in value.items() if key != "condition"}
                if not value:
                    continue
            if isinstance(value, dict) and not value:
                issues.append(f"empty item_facts entry for {name} ignored")
                continue
            if not self._valid_entry(value):
                issues.append(f"item_facts for {name!r} has no valid place or condition")
                continue
            before = copy.deepcopy(self.item_facts[name])
            if self._merge_entry(name, value) and before != self.item_facts[name]:
                changed.add(name)
            if isinstance(value.get("condition"), list) and len(value["condition"]) > 2:
                issues.append(f"item_facts for {name!r} has more than two condition phrases; kept the first two")
        self._changed_last_turn = changed
        self._resolve_new_items(player_input)
        return copy.deepcopy(self.item_facts), issues

    def prepare_turn(self, player_input: str) -> dict[str, object]:
        dependencies = self.dependency_names()
        candidates = [name for name in self.item_facts if name not in dependencies]
        if not candidates:
            self._selected_names = dependencies
            self._select_protagonist()
            result = {
                "match_call": False,
                "match_raw": None,
                "match_issues": [],
                "resolutions": {},
                "engine_resolutions": {},
            }
            self._last_item_facts_match = copy.deepcopy(result)
            return result
        self.item_facts_match_calls += 1
        payload = self._match_payload(player_input, [], set(dependencies))
        issues: list[str] = []
        try:
            reply = CloudflareTurnProvider._request(self, payload)
        except Exception as error:
            reply = None
            issues.append(f"item_facts match failed: {error}")
        valid = (
            isinstance(reply, dict) and isinstance(reply.get("refers"), list) and isinstance(reply.get("same_as"), dict)
        )
        if not valid:
            self._selected_names = dependencies
        else:
            refers = []
            engine_resolutions = {}
            for name in reply["refers"]:
                if not isinstance(name, str):
                    continue
                resolved = _resolve_refer(name, self.item_facts)
                if resolved is not None and resolved not in refers:
                    refers.append(resolved)
                if resolved is not None and resolved != name:
                    engine_resolutions[name] = resolved
            selected = set(dependencies) | set(refers)
            self._selected_names = [name for name in self.item_facts if name in selected]
        self._select_protagonist()
        result = {
            "match_call": True,
            "match_raw": copy.deepcopy(reply),
            "match_issues": issues,
            "resolutions": {},
            "engine_resolutions": engine_resolutions if valid else {},
        }
        self._last_item_facts_match = copy.deepcopy(result)
        return result

    def second_call_update(self, player_input: str, narration: str) -> object:
        things = self._things_block()
        things_prefix = f"{things}\n\n" if things else ""
        payload = {
            "system": _SECOND_CALL_SYSTEM,
            "user": f"{things_prefix}PLAYER:\n- {player_input}\n\nSTORY:\n{narration}",
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


def validate_item_facts(
    value: object, *, known_names: set[str] | None = None
) -> tuple[str, dict[str, dict[str, object]], dict[str, dict[str, list[str]]]] | None:
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
            or not isinstance(facts.get("place"), str)
            or not facts["place"].strip()
            or len(facts["place"].strip()) > 80
            or not isinstance(facts.get("condition"), list)
            or len(facts["condition"]) > 2
            or not all(
                isinstance(condition, str) and condition.strip() and len(condition.strip()) <= 40
                for condition in facts["condition"]
            )
        ):
            raise ValueError(
                f"item_facts seed for {name!r} must have a place and zero to two non-empty condition phrases"
            )
        copied[name] = {
            "place": facts["place"].strip(),
            "condition": [condition.strip() for condition in facts["condition"]],
        }
    state_axes = value.get("state_axes", {})
    if not isinstance(state_axes, dict):
        raise ValueError("item_facts state_axes must be an object")
    copied_axes: dict[str, dict[str, list[str]]] = {}
    for name, axes in state_axes.items():
        if not isinstance(name, str) or not name.strip() or (known_names is not None and name not in known_names):
            raise ValueError(f"item_facts state_axes names an unknown thing {name!r}")
        if not isinstance(axes, dict) or len(axes) != 2:
            raise ValueError(f"item_facts state_axes for {name!r} must have exactly two poles")
        copied_poles: dict[str, list[str]] = {}
        words: set[str] = set()
        for pole, aliases in axes.items():
            if not isinstance(pole, str) or not pole.strip() or not isinstance(aliases, list):
                raise ValueError(f"item_facts state axis for {name!r} has an invalid pole or aliases")
            pole = pole.strip()
            all_words = [pole, *aliases]
            if any(not isinstance(word, str) or not word.strip() for word in all_words):
                raise ValueError(f"item_facts state axis for {name!r} has an empty pole or alias")
            folded = [word.strip().casefold() for word in all_words]
            if words.intersection(folded):
                raise ValueError(f"item_facts state axis for {name!r} repeats a word under both poles")
            words.update(folded)
            copied_poles[pole] = [alias.strip() for alias in aliases]
        copied_axes[name] = copied_poles
    return mode, copied, copied_axes
