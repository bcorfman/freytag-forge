"""Bench-only tracking of plain facts about named scene things."""

# ruff: noqa: E501, E701, E702
from __future__ import annotations

import copy
import re
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


def declared_axes_for_world(world, names):
    """Return declared pole pairs for the named things that have axes."""

    axes = {}
    for name in names:
        entity_id = world.resolve(name)
        if entity_id is None:
            continue
        definitions = world.axis_definitions(entity_id)
        if definitions:
            axes[name] = [list(definition["poles"]) for definition in definitions]
    return axes


def declared_axes_for_package(package, names, state_axes=None):
    """Resolve old record names against package and variation axis definitions."""

    world = World(_schema_for(package, state_axes or {}), MemoryBackend(), make_fact=Fact)
    return declared_axes_for_world(world, names)


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
                package_axes = entity.setdefault("axes", [])
                matching = next(
                    (
                        axis
                        for axis in package_axes
                        if {pole.casefold() for pole in axis["poles"]} == {pole.casefold() for pole in pole_names}
                    ),
                    None,
                )
                if matching is None and package_axes:
                    raise ValueError(f"item_facts axis for {name!r} conflicts with its package axis")
                aliases = (
                    {
                        alias: next(pole for pole in matching["poles"] if pole.casefold() == pole_name.casefold())
                        for pole_name, alias_list in poles.items()
                        for alias in alias_list
                    }
                    if matching
                    else {alias: pole for pole, aliases in poles.items() for alias in aliases}
                )
                if matching:
                    matching["aliases"].update(aliases)
                else:
                    package_axes.append({"poles": pole_names, "aliases": aliases, "initial": pole_names[0]})
    return WorldSchema.from_data(data)


def _view(package, facts, axes=None, schema=None, *, structural=False):
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
        parent = world.parent(entity_id)
        if structural:
            place = world.unplaced_name(entity_id)
            if parent:
                place = world.name(parent)
                if world.is_a(parent, "character"):
                    npc = next((e for e in package.world.npcs if e.id == parent), None)
                    place = min((place, *(npc.aliases if npc else ())), key=len)
        else:
            place = world.place_label(entity_id)
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
    'Give only what changed. For "place", give the name of the person, thing, or place that has it now. Use "condition" for up to two short phrases.',
    'Example: if {protagonist} picks up a lantern and lights it, the lantern is {{"place": "{protagonist}", "condition": ["lit"]}}.',
    'If a thing is under something, add "under": true, like {{"place": "table", "under": true}}.',
)


def _single_call_rules(protagonist_name, *, drop_rules=frozenset()):
    protagonist = protagonist_name or "Sam"
    rules = tuple(rule.format(protagonist=protagonist) for rule in _SINGLE_CALL_RULES if rule not in drop_rules)
    if protagonist_name:
        return rules[:1] + (
            f"When {protagonist_name} goes to a new place, add {protagonist_name} to item_facts with the place where {protagonist_name} is when the story ends.",
            *rules[1:],
        )
    return rules


_MATCH_SYSTEM = 'You match names in a story game. COMMAND is what the player typed. PLAYER CHARACTER is who the player plays. THINGS lists the names the game keeps track of, some with the place they are now. NEW NAMES lists names the storyteller used. Return only JSON like {"refers": ["name"], "same_as": {"new name": "name"}, "kind": {"new name": "thing"}}. In refers, list each name from THINGS that the command talks about, even when the command uses other words, like "the old lamp" for "Grandma\'s lamp". List only the things the command itself names or points to. Do not list a thing because it is nearby. Do not list a thing because someone holds it. For "Ask the cook who took the key." list only the cook and the key. In same_as, give each name in NEW NAMES the name from THINGS that is the very same object, or "new" if it is a different object. A thing that is in, on or under another thing is a different object, like a key in a box. If a new name is a spot in a place from THINGS, like "the corner of the kitchen" for kitchen, give that place. A plain word like "corridor", "hall" or "room" is a spot in the place where PLAYER CHARACTER is now, so give that place. If a new name is a place that is not in THINGS and is not a spot in a place from THINGS, give "new". Give a person the name of someone in THINGS only when it is that same person. A guard or a prisoner who is not in THINGS is "new". Copy names from THINGS exactly. In kind, give one word for each name you called "new". Say "place" for a room, hall or other spot a person can walk into. Say "person" for one person. Say "group" for a group of people, like "prisoners". Say "thing" for anything else, like a box or a console.'
_SECOND_CALL_SYSTEM = 'You keep track of things in a story. Read THINGS, PLAYER and STORY. Return only JSON like {"item_facts": {"thing": {"place": "name", "condition": ["phrase"]}}}. List only the things in THINGS that STORY changed. For each one, give the name of who or what has it now and up to two short condition phrases. Example: if Sam picks up the lantern from the table and lights it, the lantern is {"place": "Sam", "condition": ["lit"]}. If STORY changed nothing, return {"item_facts": {}}.'


class ItemFactsProvider(CloudflareTurnProvider):
    allowed_reply_keys = CloudflareTurnProvider.allowed_reply_keys | {"item_facts"}

    def __init__(
        self, *, item_facts, mode, state_axes=None, seed_issues=None, seed_from_package=False, drop_rules=(), **kwargs
    ):
        super().__init__(**kwargs)
        self.item_facts_seed_names = tuple(item_facts)
        self.item_facts_mode = mode
        self.item_facts_seed_issues = list(seed_issues or [])
        self.state_axes = copy.deepcopy(state_axes or {})
        self.seed_from_package = seed_from_package
        self.drop_rules = frozenset(drop_rules)
        self._pending_item_facts = None
        self._pending_item_facts_present = False
        self._held_item_facts = {}
        self._item_facts_issues = []
        self._changed_last_turn = set()
        self._selected_names = None
        self._last_scene_seeded = None
        self._match_offered_names = set()
        self._schema_cache = {}
        self.prior_steps: tuple[str, ...] = ()
        self._last_item_facts_unplaced = []
        self._last_item_facts_match = {
            "match_call": False,
            "match_raw": None,
            "match_issues": [],
            "resolutions": {},
            "place_resolutions": {},
            "engine_resolutions": {},
            "mapping_checks": [],
        }
        self.item_facts_match_calls = 0
        self.item_facts_axis_fixes = 0
        self.item_facts_lifted = 0
        self.item_facts_reply_keys = {"place": 0, "contents": 0, "under": 0}
        self._ensure_hand_seeds(item_facts)
        self._ensure_scene_seeded()

    @property
    def item_facts(self):
        self._ensure_scene_seeded()
        return _view(self.state.package, self.state.facts, schema=self._schema())

    @classmethod
    def from_environment(
        cls,
        state,
        *,
        prompt_variant=None,
        item_facts,
        mode,
        state_axes=None,
        seed_issues=None,
        seed_from_package=False,
        drop_rules=(),
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
            drop_rules=drop_rules,
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
        world = self._world()
        index = 0
        while index < len(names):
            entity_id = world.resolve(names[index])
            if entity_id:
                for child_id in world.given_with(entity_id):
                    child_name = self._entity_label(world, child_id)
                    if child_name not in names and child_name in self.item_facts:
                        names.insert(index + 1, child_name)
                for seat_id in world.seats(entity_id):
                    seat_name = self._entity_label(world, seat_id)
                    if seat_name not in names and seat_name in self.item_facts:
                        names.insert(index + 1, seat_name)
            index += 1
        return names

    def _select_protagonist(self):
        if self._selected_names is not None:
            protagonist = _protagonist_name(self.state.package)
            if protagonist in self.item_facts and protagonist not in self._selected_names:
                self._selected_names.append(protagonist)

    def _player_lines(self, user):
        lines = super()._player_lines(user)
        if self.prior_steps and lines:
            lines.insert(0, f"Just before this: {' '.join(self.prior_steps)}")
        if not lines or "scene_setting" not in user:
            return lines
        return [
            f"{name}. Place: {self.item_facts[name]['place'].strip()}."
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
        rules = list(_single_call_rules(protagonist, drop_rules=self.drop_rules))
        if not opening and protagonist:
            rules.insert(
                2,
                f"{protagonist} starts this turn at the place PLAYER gives. Do not have {protagonist} walk there again.",
            )
            world = self._world()
            seat = world.parent(self.state.package.protagonist_id)
            if seat and world.schema.entities.get(seat) and world.schema.entities[seat].seat_for:
                rules.insert(3, f"{protagonist} stays sitting in the {world.name(seat)}.")
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
                    and ({"place", "condition", "contents"} & entry.keys())
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
                if isinstance(entry, dict):
                    for key in self.item_facts_reply_keys:
                        if key in entry:
                            self.item_facts_reply_keys[key] += 1
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

    def facts_for_names(self, names, *, structural=False):
        self._ensure_scene_seeded()
        view = _view(self.state.package, self.state.facts, schema=self._schema(), structural=structural)
        wanted = set(names)
        return {name: copy.deepcopy(facts) for name, facts in view.items() if name in wanted}

    @staticmethod
    def _valid_entry(value):
        if not isinstance(value, dict) or not value:
            return False
        if "contents" in value:
            return (
                isinstance(value["contents"], list)
                and bool(value["contents"])
                and all(isinstance(item, str) and item.strip() for item in value["contents"])
            )
        return ("place" in value and isinstance(value["place"], str) and bool(value["place"].strip())) or (
            "condition" in value
            and isinstance(value["condition"], list)
            and all(isinstance(item, str) and item.strip() for item in value["condition"])
        )

    def _resolve_name(self, world, key):
        target = world.resolve(key)
        if target:
            return target
        refer = _resolve_refer(key, [name for name in self.item_facts if self._name_in_scene_scope(world, name)])
        return world.resolve(refer) if refer else None

    def _name_in_scene_scope(self, world, name):
        entity_id = world.resolve(name)
        if entity_id is None:
            return True

        package = self.state.package
        protagonist_id = package.world.protagonist_id
        scene = next(item for item in package.scenes if item.metadata.scene_id == self.state.current_scene_id)
        if entity_id in {protagonist_id, *scene.metadata.participant_ids, *scene.metadata.item_ids}:
            return True

        entity_area = world.area(entity_id)
        if entity_area is None:
            return True

        def at_or_below(area_id, ancestor_id):
            return area_id == ancestor_id or ancestor_id in world.chain(area_id)

        scene_area = world.area(scene.metadata.location_id)
        protagonist_area = world.area(protagonist_id)
        return any(
            ancestor_id is not None and at_or_below(entity_area, ancestor_id)
            for ancestor_id in (scene_area, protagonist_area)
        )

    def _entity_label(self, world, entity_id):
        if world.is_a(entity_id, "character"):
            npc = next((entity for entity in self.state.package.world.npcs if entity.id == entity_id), None)
            if npc:
                return min((npc.name, *npc.aliases), key=len)
        return world.name(entity_id)

    @staticmethod
    def _mapping_name(name):
        return f'"{name}"'

    def _mapping_area_context(self, world, target_id):
        protagonist_id = self.state.package.world.protagonist_id
        player_area = world.area(protagonist_id)
        contrastive = (
            world.is_a(target_id, "area")
            and player_area is not None
            and target_id != player_area
            and player_area not in world.chain(target_id)
            and target_id not in world.chain(player_area)
        )
        return player_area, contrastive

    def _mapping_prompt(self, world, name, target_id, *, is_place):
        n = self._mapping_name(name)
        k = self._mapping_name(world.name(target_id))
        if is_place:
            if world.is_a(target_id, "area"):
                player_area, contrastive = self._mapping_area_context(world, target_id)
                if contrastive:
                    player = world.name(self.state.package.world.protagonist_id)
                    p = self._mapping_name(world.name(player_area))
                    return (
                        f"{player} is in {p}. Is the place called {n} really {k}, rather than a spot in {p}?",
                        f"the place called {n} is {k}, not a spot in {p}",
                    )
                return (
                    f"Is the place called {n} the same place as {k}, or inside it?",
                    f"the place called {n} is {k} or is inside it",
                )
            if world.is_a(target_id, "character"):
                return f"Is the place called {n} on {k}?", f"the place called {n} is on {k}"
            return f"Is the place called {n} at {k}?", f"the place called {n} is at {k}"
        if world.is_a(target_id, "character"):
            return f"Are {n} and {k} the same person?", f"{n} and {k} are the same person"
        return f"Are {n} and {k} the same thing?", f"{n} and {k} are the same thing"

    def _mapping_entity(self, world, entity_id):
        parent = world.parent(entity_id)
        holder = world.name(parent) if parent is not None and world.is_a(parent, "character") else None
        place = None if holder else world.name(parent) if parent is not None else None
        result = {"name": world.name(entity_id), "place": place, "held_by": holder}
        label = world.place_label(entity_id)
        if label and (place is None or label.casefold() != place.casefold()):
            result["place_text"] = label
        return result

    def _mapping_state(self, world, target_id):
        protagonist_id = self.state.package.world.protagonist_id
        player = self._mapping_entity(world, protagonist_id)
        if target_id == protagonist_id:
            return player, player
        known = self._mapping_entity(world, target_id)
        known["can_move"] = not world.is_a(target_id, "area") and not world.schema.is_fixed(target_id)
        return player, known

    def _match_payload(self, player_input, new_names, *, include_places=False, story=""):
        world = self._world()

        lines = []
        self._match_offered_names = set()
        for name, facts in self.item_facts.items():
            if not self._name_in_scene_scope(world, name):
                continue
            self._match_offered_names.add(name)
            line = f"- {name}."
            if facts.get("place"):
                line += f" Place: {facts['place'].strip()[:80]}."
            elif facts.get("condition"):
                line += f" Condition: {', '.join(facts['condition'])}."
            lines.append(line)
        if include_places:
            extra_ids = []
            roots = [world.resolve(_protagonist_name(self.state.package))]
            roots.extend(world.resolve(name) for name in self.item_facts)
            for root in roots:
                if root is not None:
                    extra_ids.extend(entity for entity in world.chain(root) if world.is_a(entity, "area"))
            protagonist = roots[0] if roots else None
            area_chain = (
                [entity for entity in world.chain(protagonist) if world.is_a(entity, "area")] if protagonist else []
            )
            top_area = (
                area_chain[-1]
                if area_chain
                else (protagonist if protagonist and world.is_a(protagonist, "area") else None)
            )
            if top_area:
                extra_ids.extend(
                    entity
                    for entity in world.entity_ids()
                    if world.is_a(entity, "area") and top_area in world.chain(entity)
                )
            extra_ids.extend(
                entity for entity in world.entity_ids() if world.is_a(entity, "character") and world.parent(entity)
            )
            existing = set(self.item_facts)
            for entity_id in extra_ids:
                label = self._entity_label(world, entity_id)
                if label not in existing and f"- {label}." not in lines:
                    self._match_offered_names.add(label)
                    line = f"- {label}."
                    if world.is_a(entity_id, "character"):
                        place = world.place_label(entity_id)
                        if place:
                            line += f" Place: {place.strip()[:80]}."
                    lines.append(line)
        story_sentences = [sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+", story) if sentence.strip()]
        new_name_lines = []
        for name in new_names:
            sentence = next(
                (sentence for sentence in story_sentences if name.casefold() in sentence.casefold()),
                None,
            )
            if sentence is None:
                new_name_lines.append(f"- {name}")
                continue
            sentence = sentence.replace('"', "'")[:200]
            new_name_lines.append(f'- {name} (from: "{sentence}")')
        return {
            "system": _MATCH_SYSTEM,
            "user": (
                f"COMMAND:\n- {player_input}\n\nPLAYER CHARACTER:\n- {_protagonist_name(self.state.package)}\n\n"
                "THINGS:\n" + "\n".join(lines) + "\n\nNEW NAMES:\n" + "\n".join(new_name_lines)
            ),
            "max_tokens": 300,
            "response_format": {"type": "json_object"},
        }

    def _apply_move(self, world, entity_id, name, value, place_parent, issues):
        if place_parent is None or "place" not in value:
            return
        place = value["place"].strip()
        under = value.get("under") is True
        dropped_under = under and (world.is_a(place_parent, "area") or world.is_a(place_parent, "character"))
        if dropped_under:
            under = False
        if entity_id == place_parent:
            return
        current_parent = world.parent(entity_id)
        current_relation = world.relation(entity_id)
        if current_parent == place_parent and (current_relation == "under") == under:
            return
        result = world.move(entity_id, place_parent, under=under)
        if (
            not result.ok
            and world.is_a(entity_id, "character")
            and not world.is_a(place_parent, "group")
            and result.reason.startswith("characters can only be in")
        ):
            area = world.area(place_parent)
            if area:
                result = world.move(entity_id, area)
        if not result.ok and "cannot hold" in result.reason:
            result = world.set_unplaced(entity_id, place[:80])
            entry = {"name": name, "place": place[:80]}
            if entry not in self._last_item_facts_unplaced:
                self._last_item_facts_unplaced.append(entry)
            issues.append(f"item_facts for {name!r} left unplaced: {place!r} cannot hold things")
        if not result.ok:
            issues.append(f"item_facts for {name!r} refused place {place!r}: {result.reason}")

    def _apply_state(self, world, entity_id, name, value, place_pole, issues):
        current_poles = list(world.axis_values(entity_id).values())
        before_pole = current_poles[0] if current_poles else None
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

    def _apply_entry(self, world, entity_id, name, value, issues, *, place_parent=None, place_pole=None):
        before = self.item_facts.get(name)
        self._apply_move(world, entity_id, name, value, place_parent, issues)
        self._apply_state(world, entity_id, name, value, place_pole, issues)
        return before != self.item_facts.get(name)

    def apply_item_facts(self, raw, *, player_input="(none)", story="", confirm=None):
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
        entries = []
        explicit_keys = set(raw)
        explicit_ids = {
            resolved_id
            for explicit_key in explicit_keys
            if (resolved_id := self._resolve_name(world, explicit_key)) is not None
        }
        for key, value in raw.items():
            if isinstance(value, str) and value.strip():
                value = {"place": value.strip()}
            if isinstance(value, dict) and not value:
                issues.append(f"item_facts for {key!r} has an empty item_facts entry")
                continue
            if not self._valid_entry(value):
                if isinstance(value, dict) and "contents" in value:
                    issues.append(f"item_facts for {key!r} has invalid contents")
                else:
                    issues.append(f"item_facts for {key!r} has no valid place or condition")
                continue
            entries.append((key, value))
            contents = value.get("contents", [])
            for child in contents:
                child_id = self._resolve_name(world, child)
                if child not in explicit_keys and child_id not in explicit_ids:
                    entries.append((child, {"place": key}))
        match_called = False
        match_raw = None
        match_issues = []
        resolutions = {}
        engine_resolutions = {}
        mapping_checks = []
        unresolved = []
        resolved = []
        for key, value in entries:
            entity_id = self._resolve_name(world, key)
            if entity_id is None:
                unresolved.append((key, value))
                continue
            resolved.append((key, value, entity_id))

        prepared = []
        for key, value in unresolved:
            owner = value.get("owner") if isinstance(value, dict) else None
            owner_id = self._resolve_name(world, owner) if isinstance(owner, str) else None
            candidate = f"{owner}'s {key}" if isinstance(owner, str) else None
            entity_id = self._resolve_name(world, candidate) if candidate else None
            prepared.append({"key": key, "value": value, "owner_id": owner_id, "candidate": candidate, "id": entity_id})

        place_names = []
        for _key, value, _entity_id in resolved:
            if isinstance(value.get("place"), str):
                place = value["place"].strip()
                if place and (
                    not self._axis_match_id(world, _entity_id, place)
                    and not (
                        world.place_label(_entity_id) and world.place_label(_entity_id).casefold() == place.casefold()
                    )
                    and self._resolve_name(world, place) is None
                ):
                    place_names.append(place)
        for item in prepared:
            if isinstance(item["value"].get("place"), str):
                place = item["value"]["place"].strip()
                if place and self._resolve_name(world, place) is None:
                    place_names.append(place)
        match_names = []
        for item in prepared:
            if item["id"] is None and item["owner_id"] is None:
                match_names.append(item["key"])
        match_names.extend(place_names)
        match_names = list(dict.fromkeys(match_names))

        match_reply = None
        if match_names:
            match_called = True
            self.item_facts_match_calls += 1
            try:
                match_reply = CloudflareTurnProvider._request(
                    self,
                    self._match_payload(player_input, match_names, include_places=bool(place_names), story=story),
                )
            except Exception as error:
                match_issues.append(f"item_facts match failed: {error}")
                issues.append(match_issues[-1])
            match_raw = copy.deepcopy(match_reply)
            if not isinstance(match_reply, dict) or not isinstance(match_reply.get("same_as"), dict):
                match_issues.append("invalid item_facts match reply")

        same_as = match_reply.get("same_as", {}) if isinstance(match_reply, dict) else {}
        kind_reply = match_reply.get("kind", {}) if isinstance(match_reply, dict) else {}
        if not isinstance(kind_reply, dict):
            kind_reply = {}

        def new_kind(name, *, place=False, reply_key=False):
            raw_kind = next(
                (
                    value
                    for key, value in kind_reply.items()
                    if isinstance(key, str) and key.casefold() == name.casefold()
                ),
                None,
            )
            normalized = raw_kind.strip().casefold() if isinstance(raw_kind, str) else ""
            kind = {
                "place": "area",
                "person": "character",
                "group": "group",
                "thing": "container" if reply_key else "thing",
            }.get(normalized)
            if kind is None and name in kind_required_names:
                fallback = "container" if place or reply_key else "thing"
                issues.append(f"item_facts match gave no kind for {name!r}; made a thing")
                return fallback
            if kind is None:
                return "container" if place or reply_key else "thing"
            return kind

        if isinstance(same_as, dict):
            offered = {name.strip().casefold() for name in self._match_offered_names}
            same_as = dict(same_as)
            for name, target in same_as.items():
                if isinstance(target, str) and target != "new" and target.strip().casefold() not in offered:
                    issue = f"item_facts match named {target!r} for {name!r}, which was not in THINGS; kept as new"
                    issues.append(issue)
                    match_issues.append(issue)
                    same_as[name] = "new"
        kind_required_names = {
            name
            for name, target in same_as.items()
            if isinstance(name, str) and isinstance(target, str) and target.strip().casefold() == "new"
        }
        protagonist_id = self.state.package.world.protagonist_id
        player_character_names = {
            item["key"]
            for item in prepared
            if isinstance(same_as, dict)
            and isinstance(same_as.get(item["key"]), str)
            and same_as[item["key"]] != "new"
            and self._resolve_name(world, same_as[item["key"]]) == protagonist_id
        }
        place_ids = {}
        place_resolutions = {}
        mapping_answers = {}
        mapping_contrastive = {}
        mapping_player_areas = {}

        def check_mapping(name, target_id, kind):
            pair = (name, target_id)
            if pair in mapping_answers:
                return mapping_answers[pair]
            player_area, contrastive = self._mapping_area_context(world, target_id)
            contrastive = contrastive and kind == "place"
            question, statement = self._mapping_prompt(world, name, target_id, is_place=kind == "place")
            player, known = self._mapping_state(world, target_id)
            answer = confirm(player_input, story, question, statement, player, known)
            mapping_checks.append(
                {
                    "name": name,
                    "target": world.name(target_id),
                    "kind": kind,
                    "question": question,
                    "player": player,
                    "known": known,
                    "answer": answer,
                    "contrastive": contrastive,
                }
            )
            if answer is None:
                issues.append(f"item_facts mapping check for {name!r} unavailable")
            mapping_answers[pair] = answer
            mapping_contrastive[pair] = contrastive
            mapping_player_areas[pair] = player_area
            return answer

        for place in place_names:
            target = same_as.get(place) if isinstance(same_as, dict) else None
            if isinstance(target, str) and target != "new":
                place_ids[place] = self._resolve_name(world, target)
                if place_ids[place] is not None and confirm is not None:
                    target_id = place_ids[place]
                    exact = (
                        place.casefold() == world.name(target_id).casefold()
                        or self._resolve_name(world, place) == target_id
                    )
                    if not exact:
                        answer = check_mapping(place, target_id, "place")
                        if answer is False:
                            pair = (place, target_id)
                            if mapping_contrastive.get(pair):
                                player_area = mapping_player_areas[pair]
                                place_ids[place] = player_area
                                place_resolutions[place] = world.name(player_area)
                            else:
                                place_ids.pop(place, None)
                                place_resolutions[place] = "new"
                                kind_required_names.add(place)
                            continue
                if (
                    place_ids[place] is not None
                    and place not in player_character_names
                    and not world.is_a(place_ids[place], "area")
                ):
                    world.add_alias(place_ids[place], place)
            place_id = place_ids.get(place)
            place_resolutions[place] = world.name(place_id) if place_id is not None else "new"

        def create_new_place(place):
            player_area = world.area(protagonist_id)
            player_parent = world.parent(protagonist_id)
            if player_parent and world.is_a(player_parent, "group"):
                player_parent = world.parent(player_parent)
            if place in place_ids or place not in kind_required_names:
                return
            kind = new_kind(place, place=True)
            if kind == "area":
                parent = player_area
            elif kind in ("character", "group"):
                parent = (
                    player_parent
                    if player_parent and (world.is_a(player_parent, "area") or world.is_enterable(player_parent))
                    else player_area
                )
            else:
                kind = "container"
                parent = (
                    player_parent
                    if player_parent
                    and (
                        world.is_a(player_parent, "area")
                        or world.is_a(player_parent, "container")
                        or world.is_a(player_parent, "supporter")
                    )
                    else player_area
                )
            created = world.create(place, parent=parent, kind=kind)
            if created.ok:
                place_ids[place] = created.id
                place_resolutions[place] = "new"
            else:
                issues.append(f"item_facts for {place!r} could not be created: {created.reason}")

        player_move_place = None
        for _key, value, entity_id in resolved:
            if entity_id == protagonist_id and isinstance(value.get("place"), str):
                player_move_place = value["place"].strip()
                break
        if player_move_place in place_names:
            create_new_place(player_move_place)

        player_move_applied = False
        for _key, value, entity_id in resolved:
            if entity_id != protagonist_id or "place" not in value:
                continue
            place = value["place"].strip() if isinstance(value["place"], str) else None
            place_pole = self._axis_match_id(world, entity_id, place) if place else None
            place_parent = place_ids.get(place) if place and not place_pole else None
            if place and not place_pole and place_parent is None:
                place_parent = self._resolve_name(world, place)
            self._apply_move(world, entity_id, self._entity_label(world, entity_id), value, place_parent, issues)
            player_move_applied = True
            break

        for place in place_names:
            create_new_place(place)

        for item in prepared:
            key, value = item["key"], item["value"]
            entity_id = item["id"]
            if entity_id is None and item["owner_id"] is None and isinstance(same_as, dict):
                target = same_as.get(key)
                if isinstance(target, str) and target != "new":
                    entity_id = self._resolve_name(world, target)
                    if entity_id == protagonist_id:
                        issues.append(f"item_facts match mapped {key!r} to the player character; kept as new")
                        entity_id = None
                    elif entity_id is not None:
                        answer = check_mapping(key, entity_id, "thing") if confirm is not None else True
                        if answer is False:
                            entity_id = None
                            resolutions[key] = "new"
                        else:
                            if not world.is_a(entity_id, "area"):
                                world.add_alias(entity_id, key)
                            resolutions[key] = world.name(entity_id)
                            if target != world.name(entity_id):
                                engine_resolutions[target] = world.name(entity_id)
            if entity_id is None:
                kind = new_kind(key, reply_key=True)
                parent = player_area if kind == "area" else None
                created = world.create(key, parent=parent, kind=kind, owner=item["owner_id"])
                if not created.ok:
                    issues.append(f"item_facts for {key!r} could not be created: {created.reason}")
                    continue
                entity_id = created.id
                resolutions[key] = "new"
                if key in player_character_names:
                    place_ids[key] = entity_id
            elif item["candidate"] and key not in resolutions:
                resolutions[key] = world.name(entity_id)
                if key != world.name(entity_id):
                    engine_resolutions[key] = world.name(entity_id)
            resolved.append((key, value, entity_id))

        moves = []
        states = []
        for key, value, entity_id in resolved:
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
            place = value.get("place").strip() if isinstance(value.get("place"), str) else None
            place_pole = self._axis_match_id(world, entity_id, place) if place else None
            if place_pole:
                self.item_facts_axis_fixes += 1
            place_parent = place_ids.get(place) if place and not place_pole else None
            character_inside_character = (
                place
                and not place_pole
                and place in place_ids
                and world.is_a(entity_id, "character")
                and place_parent is not None
                and world.is_a(place_parent, "character")
            )
            if character_inside_character:
                place_parent = None
                issues.append(f"item_facts match mapped place {place!r} to a character; {name} left unplaced")
            if place and not place_pole and place not in place_ids:
                place_parent = self._resolve_name(world, place)
            if place_parent and world.is_a(place_parent, "group") and not world.is_a(entity_id, "character"):
                place_parent = world.parent(place_parent)
            entity = world.schema.entities.get(entity_id)
            own_seat_place = bool(entity and entity.seat_for and place_parent == entity.seat_for)
            if own_seat_place:
                place_parent = None
            unresolved_place = (
                place
                and not place_pole
                and place_parent is None
                and not own_seat_place
                and not (world.place_label(entity_id) and world.place_label(entity_id).casefold() == place.casefold())
            )
            if unresolved_place:
                if world.schema.is_fixed(entity_id):
                    issues.append(f"item_facts for {name!r} refused place {place!r}: fixed things cannot move")
                else:
                    world.set_unplaced(entity_id, place[:80])
                    self._last_item_facts_unplaced.append({"name": name, "place": place[:80]})
            moves.append((entity_id, name, value, place_parent, place_pole))
            states.append((entity_id, name, value, place_pole))
        for entity_id, name, value, place_parent, _place_pole in moves:
            if entity_id == protagonist_id and player_move_applied:
                continue
            self._apply_move(world, entity_id, name, value, place_parent, issues)
        for entity_id, name, value, place_pole in states:
            self._apply_state(world, entity_id, name, value, place_pole, issues)
            if name in self.item_facts and previous.get(name) != self.item_facts.get(name):
                changed.add(name)
        self._changed_last_turn = changed
        self._last_item_facts_match = {
            "match_call": match_called,
            "match_raw": match_raw,
            "match_issues": match_issues,
            "resolutions": resolutions,
            "place_resolutions": place_resolutions,
            "engine_resolutions": engine_resolutions,
            "mapping_checks": mapping_checks,
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
                "place_resolutions": {},
                "engine_resolutions": {},
                "mapping_checks": [],
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
            "place_resolutions": {},
            "engine_resolutions": engine_resolutions if valid else {},
            "mapping_checks": [],
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
    drop_rules = value.get("drop_rules", [])
    if not isinstance(drop_rules, list) or not all(isinstance(rule, str) for rule in drop_rules):
        raise ValueError(f"item_facts drop_rules must be a list of strings; got {drop_rules!r}")
    for rule in drop_rules:
        if rule not in _SINGLE_CALL_RULES:
            raise ValueError(f"item_facts drop_rules contains unknown rule {rule!r}")
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
