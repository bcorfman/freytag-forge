"""Bench-only tracking of plain facts about named scene things."""

from __future__ import annotations

import copy
from collections.abc import Mapping
from urllib.error import HTTPError, URLError

from storygame.runtime.cloudflare import CloudflareTurnProvider, NarrationProviderError
from storygame.runtime.validation import predicate_matches
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
    "Also return item_facts for each thing in THINGS that your story changed. Use only the names in THINGS.",
    "For each one, give where it is now and up to two short condition phrases. Example: if she picks up "
    'the lantern from the table, the lantern is {"where": "in her hand", "condition": ["lit"]}.',
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
        for name in self.item_facts_seed_names:
            facts = self.item_facts[name]
            conditions = facts["condition"]
            condition_text = ", ".join(conditions) if conditions else "none"
            lines.append(f"- {name}. Where: {facts['where']}. Condition: {condition_text}.")
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
        request_count = self.request_count
        response = super()._request(payload)
        # Tests may replace the base transport method, which also replaces its
        # request counter increment. Keep the bench record accurate in that
        # case while avoiding a double increment for the normal transport.
        if self.request_count == request_count:
            self.request_count += 1
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

    def apply_item_facts(self, raw: object) -> tuple[dict[str, dict[str, object]], list[str]]:
        previous = {
            name: {"where": facts["where"], "condition": list(facts["condition"])}
            for name, facts in self.item_facts.items()
        }
        issues: list[str] = []
        if not isinstance(raw, dict):
            issues.append("item_facts must be an object mapping thing names to fact objects")
            return previous, issues

        for name in raw:
            if name not in self.item_facts:
                issues.append(f"unknown item_facts name {name!r} was dropped")

        updated: dict[str, dict[str, object]] = {}
        for name in self.item_facts_seed_names:
            if name not in raw:
                updated[name] = previous[name]
                continue
            value = raw[name]
            if (
                not isinstance(value, dict)
                or not isinstance(value.get("where"), str)
                or not value["where"].strip()
                or not isinstance(value.get("condition"), list)
                or any(not isinstance(phrase, str) or not phrase.strip() for phrase in value["condition"])
            ):
                issues.append(
                    f"item_facts for {name!r} must have a non-empty where and a list of non-empty condition strings"
                )
                updated[name] = previous[name]
                continue
            conditions = value["condition"]
            if len(conditions) > 2:
                issues.append(f"item_facts for {name!r} has more than two condition phrases; kept the first two")
            updated[name] = {
                "where": value["where"].strip()[:80],
                "condition": [phrase.strip()[:40] for phrase in conditions[:2]],
            }

        self.item_facts = updated
        return {
            name: {"where": facts["where"], "condition": list(facts["condition"])} for name, facts in updated.items()
        }, issues

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
