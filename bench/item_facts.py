"""Bench-only tracking of plain facts about named scene things."""

# ruff: noqa: E501, E701, E702
from __future__ import annotations

import copy
from urllib.error import HTTPError, URLError

from worldkeeper import MemoryBackend, World, WorldSchema

from storygame.runtime.cloudflare import CloudflareTurnProvider, NarrationProviderError
from storygame.runtime.facts import Fact
from storygame.runtime.validation import ProgressionValidator
from storygame.runtime.world_model import apply_scene_placements, apply_world_effects
from storygame.story_package.models import item_placement_is_visible, placement_text
from storygame.story_package.world_schema import world_source_schema_data


def _resolve_refer(name: str, tracked) -> str | None:
    names = list(tracked)
    if name in names:
        return name

    def norm(value):
        value = value.strip().lower().rstrip(".,;:!? ").strip()
        for article in ("the", "my", "a", "an"):
            if value.startswith(article + " "):
                return value[len(article) + 1 :]
        return value

    wanted = norm(name)
    exact = [item for item in names if norm(item) == wanted]
    if len(exact) == 1:
        return exact[0]
    suffix = [item for item in names if norm(item).endswith(" " + wanted)]
    return suffix[0] if len(suffix) == 1 else None


def _protagonist_name(package) -> str | None:
    npc = next((entity for entity in package.world.npcs if entity.id == package.protagonist_id), None)
    return min((*npc.aliases, npc.name), key=len) if npc else None


def _schema_for(package, axes=None, facts=None):
    data = copy.deepcopy(world_source_schema_data(package.world))
    if axes:
        resolver = World(WorldSchema.from_data(data), facts or MemoryBackend(), make_fact=Fact)
        for name, poles in axes.items():
            entity_id = resolver.resolve(name)
            if entity_id is None:
                raise ValueError(f"item_facts state_axes names an unknown thing {name!r}")
            entity = next((item for item in data["entities"] if item["id"] == entity_id), None)
            pole_names = list(poles)
            if entity is None:
                entity = {"id": entity_id, "name": resolver.name(entity_id), "kind": "thing"}
                data["entities"].append(entity)
            if entity.get("openable"):
                if {pole.casefold() for pole in pole_names} != {"open", "closed"}:
                    raise ValueError(f"item_facts axis for {name!r} must use open and closed")
            else:
                entity.setdefault("axes", []).append(
                    {
                        "poles": pole_names,
                        "aliases": {alias: pole for pole, aliases in poles.items() for alias in aliases},
                        "initial": pole_names[0],
                    }
                )
    return WorldSchema.from_data(data)


def _view(package, facts, axes=None, schema=None):
    world = World(schema or _schema_for(package, axes), facts, make_fact=Fact)
    ids = []
    for entity_id in world.entity_ids():
        if (
            entity_id == package.world.protagonist_id
            or not world.is_a(entity_id, "area")
            and not world.is_a(entity_id, "character")
            and world.is_visible(entity_id)
            and (world.parent(entity_id) or world.unplaced_name(entity_id))
        ):
            ids.append(entity_id)
    result = {}
    for entity_id in ids:
        name = world.name(entity_id)
        if world.is_a(entity_id, "character"):
            npc = next((e for e in package.world.npcs if e.id == entity_id), None)
            name = min((name, *(npc.aliases if npc else ())), key=len)
        place = world.place_label(entity_id)
        parent = world.parent(entity_id)
        if parent and world.is_a(parent, "character") and place == world.name(parent):
            npc = next((e for e in package.world.npcs if e.id == parent), None)
            place = min((world.name(parent), *(npc.aliases if npc else ())), key=len)
        conditions = (
            []
            if entity_id == package.world.protagonist_id
            else list(world.axis_values(entity_id).values()) + list(world.conditions(entity_id))
        )
        result[name] = {"place": place, "condition": conditions}
    return copy.deepcopy(result)


def _package_seed(package, state, scene_id):
    scene = next((item for item in package.scenes if item.metadata.scene_id == scene_id), None)
    if scene is None:
        raise ValueError(f"scene {scene_id} is not in package {package.story_id}")
    facts = state.facts.clone()
    # package_seed is a read-only projection for the requested scene.  Apply
    # that scene's authored placements to the clone even when the supplied
    # runtime state is already bootstrapped in another scene.
    apply_scene_placements(package, facts, scene_id)
    world = World(_schema_for(package), facts, make_fact=Fact)
    world.seed()
    apply_world_effects(package, facts)
    for item_id, placement in scene.metadata.item_placements.items():
        if getattr(placement, "parent", None) is None and item_placement_is_visible(placement, facts):
            text = placement_text(placement)
            if text is not None and world.exists(item_id):
                world.set_unplaced(item_id, text)
    issues = []
    unconsumed = []
    for setting in scene.metadata.setting_facts:
        phrase = setting.strip().removesuffix(".").rstrip()
        match = next(
            (
                name
                for name in _view(package, facts)
                if any(
                    phrase.casefold().startswith(prefix.casefold())
                    for prefix in (f"{name} is ", f"{name} are ", f"The {name} is ", f"The {name} are ")
                )
            ),
            None,
        )
        if match is None:
            issues.append(f"setting fact {setting!r} could not be parsed")
            unconsumed.append(setting)
            continue
        prefix = next(
            prefix
            for prefix in (f"{match} is ", f"{match} are ", f"The {match} is ", f"The {match} are ")
            if phrase.casefold().startswith(prefix.casefold())
        )
        value = phrase[len(prefix) :].strip()
        entity_id = world.resolve(match)
        if entity_id and world.set_axis(entity_id, value).ok:
            continue
        if entity_id is None or len(value) > 40 or len(world.conditions(entity_id)) >= 2:
            issues.append(f"setting fact for {match!r} could not be added as a condition")
            unconsumed.append(setting)
        else:
            world.set_conditions(entity_id, [*world.conditions(entity_id), value])
    return _view(package, facts), issues, unconsumed


def package_seed(package, state, scene_id):
    things, issues, _ = _package_seed(package, state, scene_id)
    return things, issues


_SINGLE_CALL_RULES = (
    "Every time your story moves or changes a thing, or puts a new thing in a place, add that thing to item_facts. Use where it is when the story ends.",
    'Give only what changed. Use "place" for its current location and "condition" for up to two short phrases. Example: if she throws a cup at the wall, it cracks in two and falls, so the cup is {"place": "on the floor", "condition": ["cracked in two"]}.',
    'When a place is part of something bigger, name both, like "on the passenger seat of the truck".',
)


def _single_call_rules(protagonist_name):
    return (
        _SINGLE_CALL_RULES
        if protagonist_name is None
        else (
            _SINGLE_CALL_RULES[0],
            f"When {protagonist_name} goes to a new place, add {protagonist_name} to item_facts with the place where {protagonist_name} is when the story ends.",
            *_SINGLE_CALL_RULES[1:],
        )
    )


_MATCH_SYSTEM = 'You match names in a story game. COMMAND is what the player typed. PLAYER CHARACTER is who the player plays. THINGS lists the names the game keeps track of, some with the place they are now. NEW NAMES lists names the storyteller used. Return only JSON like {"refers": ["name"], "same_as": {"new name": "name"}}. In refers, list each name from THINGS that the command talks about, even when the command uses other words, like "the old lamp" for "Grandma\'s lamp". List only the things the command itself names or points to. Do not list a thing because it is nearby. Do not list a thing because someone holds it. For "Ask the cook who took the key." list only the cook and the key. In same_as, give each name in NEW NAMES the name from THINGS that is the very same object, or "new" if it is a different object. A thing that is in, on or under another thing is a different object, like a key in a box. Copy names from THINGS exactly.'
_SECOND_CALL_SYSTEM = 'You keep track of things in a story. Read THINGS, PLAYER and STORY. Return only JSON like {"item_facts": {"thing": {"place": "place", "condition": ["phrase"]}}}. List only the things in THINGS that STORY changed. For each one, give the place it is now and up to two short condition phrases. Example: if she picks up the lantern from the table, the lantern is {"place": "in her hand", "condition": ["lit"]}. If STORY changed nothing, return {"item_facts": {}}.'


class ItemFactsProvider(CloudflareTurnProvider):
    allowed_reply_keys = CloudflareTurnProvider.allowed_reply_keys | {"item_facts"}

    def __init__(self, *, item_facts, mode, state_axes=None, seed_issues=None, seed_from_package=False, **kwargs):
        super().__init__(**kwargs)
        self.item_facts_seed_names = tuple(item_facts)
        self.item_facts_mode = mode
        self.item_facts_seed_issues = list(seed_issues or [])
        self.state_axes = copy.deepcopy(state_axes or {})
        self.seed_from_package = seed_from_package
        self._pending_item_facts = None
        self._pending_item_facts_present = False
        self._held_item_facts = {}
        self._item_facts_issues = []
        self._changed_last_turn = set()
        self._selected_names = None
        self._last_scene_seeded = None
        self._schema_cache = {}
        self._last_item_facts_unplaced = []
        self._last_item_facts_match = {
            "match_call": False,
            "match_raw": None,
            "match_issues": [],
            "resolutions": {},
            "engine_resolutions": {},
        }
        self.item_facts_match_calls = 0
        self.item_facts_axis_fixes = 0
        self.item_facts_lifted = 0
        self.item_facts_reply_keys = {"place": 0}
        self._ensure_hand_seeds(item_facts)
        self._ensure_scene_seeded()

    @property
    def item_facts(self):
        self._ensure_scene_seeded()
        return _view(self.state.package, self.state.facts, schema=self._schema())

    @classmethod
    def from_environment(
        cls, state, *, prompt_variant=None, item_facts, mode, state_axes=None, seed_issues=None, seed_from_package=False
    ):
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
            seed_from_package=seed_from_package,
        )

    def _world(self, *, axes=None):
        # RuntimeState can receive authored world-effect facts when the engine
        # advances a turn.  Apply those effects before rendering or resolving so
        # the view reflects the same world that the engine has just committed.
        apply_world_effects(self.state.package, self.state.facts)
        selected_axes = self.state_axes if axes is None else axes
        return World(self._schema(selected_axes), self.state.facts, make_fact=Fact)

    def _schema(self, axes=None):
        selected_axes = self.state_axes if axes is None else axes
        key = repr(selected_axes)
        if key not in self._schema_cache:
            self._schema_cache[key] = _schema_for(self.state.package, selected_axes, self.state.facts)
        return self._schema_cache[key]

    def _ensure_hand_seeds(self, seeds):
        world = self._world(axes={})
        for name, entry in seeds.items():
            if world.resolve(name):
                raise ValueError("item_facts seed names clash with package things")
            created = world.create(name)
            if not created.ok:
                raise ValueError(created.reason)
            world.set_unplaced(created.id, str(entry["place"]).strip()[:80])
            world.set_conditions(created.id, list(entry["condition"]))

    def _ensure_scene_seeded(self):
        scene_id = self.state.current_scene_id
        world = self._world()
        for name, poles in self.state_axes.items():
            entity_id = world.resolve(name)
            if entity_id is None or world.is_openable(entity_id):
                continue
            initial = next(iter(poles), None)
            definitions = world.axis_definitions(entity_id)
            if (
                initial is not None
                and any(initial in definition["poles"] for definition in definitions)
                and not any(definition["name"] in world.axis_values(entity_id) for definition in definitions)
            ):
                world.set_axis(entity_id, initial)
        if self._last_scene_seeded == scene_id:
            return
        scene = next(item for item in self.state.package.scenes if item.metadata.scene_id == scene_id)
        _, issues, _ = _package_seed(self.state.package, self.state, scene_id)
        self.item_facts_seed_issues.extend(issues)
        for setting in scene.metadata.setting_facts:
            phrase = setting.strip().removesuffix(".").rstrip()
            target = next(
                (
                    world.resolve(name)
                    for name in _view(self.state.package, self.state.facts, schema=self._schema())
                    if any(
                        phrase.casefold().startswith(prefix.casefold())
                        for prefix in (f"{name} is ", f"{name} are ", f"The {name} is ", f"The {name} are ")
                    )
                ),
                None,
            )
            if target is None or not world.is_visible(target):
                continue
            name = world.name(target)
            prefix = next(
                prefix
                for prefix in (f"{name} is ", f"{name} are ", f"The {name} is ", f"The {name} are ")
                if phrase.casefold().startswith(prefix.casefold())
            )
            value = phrase[len(prefix) :].strip()
            pole = self._axis_match_id(world, target, value)
            if pole:
                world.set_axis(target, pole)
            elif len(value) <= 40:
                world.set_conditions(target, [*world.conditions(target), value][:2])
        self._last_scene_seeded = scene_id

    def _axis_match_id(self, world, entity_id, text):
        query = text.strip().casefold()
        for axis in world.axis_definitions(entity_id):
            for pole in axis["poles"]:
                if pole.casefold() == query:
                    return pole
            for alias, pole in axis["aliases"].items():
                if alias.casefold() == query:
                    return pole
        for name, poles in self.state_axes.items():
            if world.resolve(name) == entity_id:
                for pole, aliases in poles.items():
                    if query == pole.casefold() or query in {alias.casefold() for alias in aliases}:
                        return pole
        return None

    def _axis_match(self, name, text):
        world = self._world()
        entity_id = world.resolve(name)
        return self._axis_match_id(world, entity_id, text) if entity_id else None

    def _object_place_rule(self):
        return "Each thing starts at the place THINGS gives it."

    def _prepare_turn_visibility(self):
        super()._prepare_turn_visibility()
        self._ensure_scene_seeded()

    def _things_block(self):
        lines = ["THINGS:"] if self._thing_names() else []
        world = self._world()
        for name in self._thing_names():
            facts = self.item_facts[name]
            line = f"- {name}."
            place = facts["place"]
            if place:
                line += f" Place: {place.strip()}."
            if facts["condition"]:
                entity_id = world.resolve(name)
                axes = world.axis_definitions(entity_id) if entity_id else ()
                rendered = []
                axis_values = world.axis_values(entity_id) if entity_id else {}
                for axis in axes:
                    current = axis_values.get(axis["name"])
                    if current:
                        other = next(pole for pole in axis["poles"] if pole != current)
                        rendered.append(f"{current} (or {other})")
                rendered.extend(condition for condition in facts["condition"] if condition not in axis_values.values())
                line += f" Condition: {', '.join(rendered)}."
            lines.append(line)
        return "\n".join(lines)

    def _thing_names(self):
        names = list(self._selected_names if self._selected_names is not None else self.dependency_names())
        protagonist = _protagonist_name(self.state.package)
        if protagonist in self.item_facts and protagonist not in names:
            names.append(protagonist)
        return names

    def _select_protagonist(self):
        if self._selected_names is not None:
            protagonist = _protagonist_name(self.state.package)
            if protagonist in self.item_facts and protagonist not in self._selected_names:
                self._selected_names.append(protagonist)

    def _player_lines(self, user):
        lines = super()._player_lines(user)
        if not lines or "scene_setting" not in user:
            return lines
        return [
            f"{name} is {self.item_facts[name]['place'].strip()}."
            for name in self._thing_names()
            if self.item_facts[name]["place"]
        ] + lines

    def _section_user_prompt(self, user):
        rendered = super()._section_user_prompt(user)
        things = self._things_block()
        if not things:
            return rendered
        marker = "\n\nCONSTRAINTS:"
        return rendered.replace(marker, f"\n\n{things}{marker}", 1) if marker in rendered else f"{rendered}\n\n{things}"

    def _placement_rules(self):
        return []

    def _setting_fact_rules(self):
        return _package_seed(self.state.package, self.state, self.state.current_scene_id)[2]

    def _system_rules(self, opening):
        if self.prompt_variant and self.prompt_variant.get("constant_rules_in_system") is True:
            return self._constant_opening_rules() if opening else self._constant_turn_rules()
        return []

    def _output_example(self):
        example = super()._output_example()
        protagonist = _protagonist_name(self.state.package)
        return example.replace("{protagonist}", protagonist) if example and protagonist else example

    def _system_prompt(self, opening=False):
        system = super()._system_prompt(opening=opening)
        if self.item_facts_mode != "single_call":
            return system
        protagonist = _protagonist_name(self.state.package)
        rules = list(_single_call_rules(protagonist))
        if not opening and protagonist:
            rules.insert(
                2,
                f"{protagonist} starts this turn at the place PLAYER gives. Do not have {protagonist} walk there again.",
            )
        return f"{system}\n{'\n'.join(rules)}"

    def _request(self, payload):
        response = super()._request(payload)
        if isinstance(response, dict):
            if "segments" in response:
                item_facts = response.get("item_facts")
                lifted = {
                    name: entry
                    for name, entry in response.items()
                    if name not in self.allowed_reply_keys
                    and (not isinstance(item_facts, dict) or name not in item_facts)
                    and isinstance(entry, dict)
                    and ({"place", "condition"} & entry.keys())
                }
                if lifted:
                    response["item_facts"] = {**lifted, **(item_facts if isinstance(item_facts, dict) else {})}
                    item_facts = response["item_facts"]
                    self.item_facts_lifted += len(lifted)
                    for name in lifted:
                        del response[name]
            self._pending_item_facts_present = "item_facts" in response
            self._pending_item_facts = copy.deepcopy(response.get("item_facts"))
            for entry in (response.get("item_facts") or {}).values():
                if isinstance(entry, dict) and "place" in entry:
                    self.item_facts_reply_keys["place"] += 1
            cleaned = dict(response)
            cleaned.pop("item_facts", None)
            return cleaned
        self._pending_item_facts_present = False
        self._pending_item_facts = copy.deepcopy(response)
        return response

    def pending_item_facts(self):
        return copy.deepcopy(self._pending_item_facts) if self._pending_item_facts_present else None

    def discard_pending_item_facts(self):
        self._pending_item_facts = None
        self._pending_item_facts_present = False

    def last_item_facts_match(self):
        return copy.deepcopy(self._last_item_facts_match)

    def last_item_facts_unplaced(self):
        return copy.deepcopy(self._last_item_facts_unplaced)

    def dependency_names(self):
        ids = {
            dependency
            for transition in ProgressionValidator(self.state.package)._reachable_transitions(
                self.state.current_scene_id
            )
            for dependency in transition.required_dependencies
        }
        world = self._world()
        return [
            name
            for name in self.item_facts
            if world.resolve(name) in ids or name == _protagonist_name(self.state.package)
        ]

    def facts_for_names(self, names):
        view = self.item_facts
        wanted = set(names)
        return {name: copy.deepcopy(facts) for name, facts in view.items() if name in wanted}

    @staticmethod
    def _valid_entry(value):
        return (
            isinstance(value, dict)
            and bool(value)
            and (
                ("place" in value and isinstance(value["place"], str) and bool(value["place"].strip()))
                or (
                    "condition" in value
                    and isinstance(value["condition"], list)
                    and all(isinstance(item, str) and item.strip() for item in value["condition"])
                )
            )
        )

    def _resolve_name(self, world, key):
        target = world.resolve(key)
        if target:
            return target
        refer = _resolve_refer(key, self.item_facts)
        return world.resolve(refer) if refer else None

    def _entity_label(self, world, entity_id):
        if world.is_a(entity_id, "character"):
            npc = next((entity for entity in self.state.package.world.npcs if entity.id == entity_id), None)
            if npc:
                return min((npc.name, *npc.aliases), key=len)
        return world.name(entity_id)

    def _match_payload(self, player_input, new_names):
        lines = []
        for name, facts in self.item_facts.items():
            line = f"- {name}."
            if facts.get("place"):
                line += f" Place: {facts['place'].strip()[:80]}."
            elif facts.get("condition"):
                line += f" Condition: {', '.join(facts['condition'])}."
            lines.append(line)
        return {
            "system": _MATCH_SYSTEM,
            "user": (
                f"COMMAND:\n- {player_input}\n\nPLAYER CHARACTER:\n- {_protagonist_name(self.state.package)}\n\n"
                "THINGS:\n" + "\n".join(lines) + "\n\nNEW NAMES:\n" + "\n".join(f"- {name}" for name in new_names)
            ),
            "max_tokens": 200,
            "response_format": {"type": "json_object"},
        }

    def _apply_entry(self, world, entity_id, name, value, issues):
        before = self.item_facts.get(name)
        current_poles = list(world.axis_values(entity_id).values())
        before_pole = current_poles[0] if current_poles else None
        place_pole = None
        if "place" in value:
            place = value["place"].strip()
            place_pole = self._axis_match_id(world, entity_id, place)
            if place_pole:
                self.item_facts_axis_fixes += 1
            elif not (world.place_label(entity_id) and world.place_label(entity_id).casefold() == place.casefold()):
                parent = self._resolve_name(world, place)
                if parent:
                    result = world.move(entity_id, parent)
                    if not result.ok and "cannot hold" in result.reason:
                        result = world.set_unplaced(entity_id, place[:80])
                    if not result.ok:
                        issues.append(f"item_facts for {name!r} refused place {place!r}: {result.reason}")
                else:
                    if world.schema.is_fixed(entity_id):
                        issues.append(f"item_facts for {name!r} refused place {place!r}: fixed things cannot move")
                    else:
                        result = world.set_unplaced(entity_id, place[:80])
                        if result.ok:
                            self._last_item_facts_unplaced.append({"name": name, "place": place[:80]})
        condition_poles = []
        if "condition" in value and value["condition"]:
            conditions = value["condition"]
            if len(conditions) > 2:
                issues.append(f"item_facts for {name!r} has more than two condition phrases; kept the first two")
            condition_poles = [self._axis_match_id(world, entity_id, item) for item in conditions]
            free = [item.strip()[:40] for item, pole in zip(conditions, condition_poles, strict=True) if not pole]
            if free:
                world.set_conditions(entity_id, free[:2])
        reply_poles = {pole for pole in (place_pole, *condition_poles) if pole is not None}
        changed_pole = None
        if reply_poles and before_pole is not None:
            differing = reply_poles - {before_pole}
            if len(differing) == 1:
                changed_pole = differing.pop()
        effective_pole = place_pole or changed_pole
        if effective_pole is not None:
            world.set_axis(entity_id, effective_pole)
        return before != self.item_facts.get(name)

    def apply_item_facts(self, raw, *, player_input="(none)"):
        self._ensure_scene_seeded()
        previous = self.item_facts
        issues = []
        changed = set()
        self._last_item_facts_unplaced = []
        if not isinstance(raw, dict):
            self._held_item_facts = {}
            self._changed_last_turn = set()
            issues.append(
                "narrator omitted item_facts"
                if raw is None
                else "item_facts must be an object mapping thing names to fact objects"
            )
            return previous, issues
        world = self._world()
        unresolved = []
        match_called = False
        match_raw = None
        match_issues = []
        resolutions = {}
        engine_resolutions = {}
        for key, value in raw.items():
            if isinstance(value, str) and value.strip():
                value = {"place": value.strip()}
            if isinstance(value, dict) and not value:
                issues.append(f"item_facts for {key!r} has an empty item_facts entry")
                continue
            if not self._valid_entry(value):
                issues.append(f"item_facts for {key!r} has no valid place or condition")
                continue
            entity_id = self._resolve_name(world, key)
            if entity_id is None:
                unresolved.append((key, value))
                continue
            name = self._entity_label(world, entity_id)
            if world.is_a(entity_id, "area"):
                issues.append(f"item_facts name {key!r} resolved to an area")
                continue
            if world.is_hidden(entity_id):
                issues.append(f"item_facts for {key!r} refused because it is hidden")
                continue
            if entity_id == self.state.package.world.protagonist_id and "condition" in value:
                short_name = _protagonist_name(self.state.package)
                issues.append(f"item_facts condition for {short_name} ignored")
                value = {k: v for k, v in value.items() if k != "condition"}
            if self._apply_entry(world, entity_id, name, value, issues):
                changed.add(name)
        prepared = []
        match_names = []
        for key, value in unresolved:
            owner = value.get("owner") if isinstance(value, dict) else None
            owner_id = self._resolve_name(world, owner) if isinstance(owner, str) else None
            candidate = f"{owner}'s {key}" if isinstance(owner, str) else None
            entity_id = self._resolve_name(world, candidate) if candidate else None
            prepared.append((key, value, owner_id, candidate, entity_id))
            if entity_id is None and owner_id is None:
                match_names.append(key)

        match_reply = None
        if match_names:
            match_called = True
            self.item_facts_match_calls += 1
            try:
                match_reply = CloudflareTurnProvider._request(self, self._match_payload(player_input, match_names))
            except Exception as error:
                match_issues.append(f"item_facts match failed: {error}")
                issues.append(match_issues[-1])
            match_raw = copy.deepcopy(match_reply)
            if not isinstance(match_reply, dict) or not isinstance(match_reply.get("same_as"), dict):
                match_issues.append("invalid item_facts match reply")

        same_as = match_reply.get("same_as", {}) if isinstance(match_reply, dict) else {}
        for key, value, owner_id, candidate, entity_id in prepared:
            if entity_id is None and owner_id is None and isinstance(same_as, dict):
                target = same_as.get(key)
                if isinstance(target, str) and target != "new":
                    resolved_target = self._resolve_name(world, target)
                    if resolved_target is not None:
                        entity_id = resolved_target
                        resolutions[key] = world.name(resolved_target)
                        if target != world.name(resolved_target):
                            engine_resolutions[target] = world.name(resolved_target)
            if entity_id is None:
                created = world.create(key, owner=owner_id)
                if not created.ok:
                    issues.append(f"item_facts for {key!r} could not be created: {created.reason}")
                    continue
                entity_id = created.id
                resolutions[key] = "new"
            name = self._entity_label(world, entity_id)
            if candidate and entity_id is not None and key not in resolutions:
                resolutions[key] = world.name(entity_id)
                if key != world.name(entity_id):
                    engine_resolutions[key] = world.name(entity_id)
            if world.is_hidden(entity_id):
                issues.append(f"item_facts for {key!r} refused because it is hidden")
                continue
            if self._apply_entry(world, entity_id, name, value, issues):
                changed.add(name)
        self._changed_last_turn = changed
        self._last_item_facts_match = {
            "match_call": match_called,
            "match_raw": match_raw,
            "match_issues": match_issues,
            "resolutions": resolutions,
            "engine_resolutions": engine_resolutions,
        }
        return self.item_facts, issues

    def prepare_turn(self, player_input):
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
        payload = self._match_payload(player_input, [])
        issues = []
        try:
            reply = CloudflareTurnProvider._request(self, payload)
        except Exception as error:
            reply = None
            issues.append(f"item_facts match failed: {error}")
        valid = (
            isinstance(reply, dict) and isinstance(reply.get("refers"), list) and isinstance(reply.get("same_as"), dict)
        )
        engine_resolutions = {}
        if not valid:
            self._selected_names = dependencies
        else:
            refers = []
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
            "match_issues": issues if not valid else [],
            "resolutions": {},
            "engine_resolutions": engine_resolutions if valid else {},
        }
        self._last_item_facts_match = copy.deepcopy(result)
        return result

    def second_call_update(self, player_input, narration):
        things = self._things_block()
        payload = {
            "system": _SECOND_CALL_SYSTEM,
            "user": f"{things}\n\nPLAYER:\n- {player_input}\n\nSTORY:\n{narration}",
            "max_tokens": 400,
            "response_format": {"type": "json_object"},
        }
        try:
            response = self._request_allowing_one_transient_retry(payload)
        except NarrationProviderError:
            raise
        except (HTTPError, URLError, OSError, TimeoutError, ValueError) as error:
            raise NarrationProviderError("narration service is unavailable") from error
        return copy.deepcopy(self._pending_item_facts) if self._pending_item_facts_present else response


def validate_item_facts(value, *, known_names=None):
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
    copied = {}
    for name, facts in seed.items():
        if (
            not isinstance(name, str)
            or not name.strip()
            or not isinstance(facts, dict)
            or not isinstance(facts.get("place"), str)
            or not facts["place"].strip()
            or len(facts["place"].strip()) > 80
            or not isinstance(facts.get("condition"), list)
            or len(facts["condition"]) > 2
            or not all(isinstance(c, str) and c.strip() and len(c.strip()) <= 40 for c in facts["condition"])
        ):
            raise ValueError(
                f"item_facts seed for {name!r} must have a place and zero to two non-empty condition phrases"
            )
        copied[name] = {"place": facts["place"].strip(), "condition": [c.strip() for c in facts["condition"]]}
    axes = value.get("state_axes", {})
    if not isinstance(axes, dict):
        raise ValueError("item_facts state_axes must be an object")
    copied_axes = {}
    for name, poles in axes.items():
        if not isinstance(name, str) or not name.strip() or (known_names is not None and name not in known_names):
            raise ValueError(f"item_facts state_axes names an unknown thing {name!r}")
        if not isinstance(poles, dict) or len(poles) != 2:
            raise ValueError(f"item_facts state_axes for {name!r} must have exactly two poles")
        words = set()
        copied_axes[name] = {}
        for pole, aliases in poles.items():
            if (
                not isinstance(pole, str)
                or not pole.strip()
                or not isinstance(aliases, list)
                or any(not isinstance(word, str) or not word.strip() for word in [pole, *aliases])
            ):
                raise ValueError(f"item_facts state axis for {name!r} has an invalid pole or aliases")
            folded = {word.strip().casefold() for word in [pole, *aliases]}
            if words & folded:
                raise ValueError(f"item_facts state axis for {name!r} repeats a word under both poles")
            words |= folded
            copied_axes[name][pole.strip()] = [a.strip() for a in aliases]
    return mode, copied, copied_axes
