"""Pure projection of public world state for an observation task."""

from collections.abc import Callable, Iterable
from dataclasses import dataclass

from worldkeeper import World


@dataclass(frozen=True)
class ObservationRequest:
    """The original action, its bounded intent kind, and its focus ID."""

    action: str
    kind: str
    focus: str | None = None

    @property
    def focus_id(self) -> str | None:
        return self.focus


@dataclass(frozen=True)
class ObservedThing:
    """A public name and short placement facts for one observed entity."""

    name: str
    place: str | None
    holder: str | None = None
    scene_level: bool = False


@dataclass(frozen=True)
class ObservationContext:
    """Immutable, story-independent inputs for one observation task."""

    observer: str
    action: str
    completed_actions: tuple[str, ...]
    visible_things: tuple[ObservedThing, ...]
    contingent_things: tuple[ObservedThing, ...]
    required: tuple[str, ...]
    omitted_optional: tuple[str, ...]
    scope_complete: bool
    scene: str | None = None

    def prompt_fields(self) -> dict[str, str | bool | list[str]]:
        """Return JSON-safe public fields without internal entity IDs."""
        return {
            "observer": self.observer,
            "action": self.action,
            "completed_actions": list(self.completed_actions),
            "visible_things": [_prompt_thing(thing) for thing in self.visible_things],
            "contingent_things": [_prompt_thing(thing) for thing in self.contingent_things],
            "required": list(self.required),
            "omitted_optional": list(self.omitted_optional),
            "scope_complete": self.scope_complete,
        }


class ObservationScopeTooLarge(ValueError):
    """The required portion of an observation cannot fit its configured bound."""


def build_observation_context(
    world: World,
    observer_id: str,
    request: ObservationRequest,
    *,
    label: Callable[[World, str], str] | None = None,
    completed_actions: Iterable[str] = (),
    max_required: int = 32,
    max_optional: int = 32,
    scene_location_id: str | None = None,
) -> ObservationContext:
    """Build a deterministic public projection using only worldkeeper queries."""
    if label is None:

        def entity_label(current_world: World, entity_id: str) -> str:
            return current_world.name(entity_id)

    else:
        entity_label = label
    if max_required < 0 or max_optional < 0:
        raise ValueError("observation scope limits must be non-negative")

    visible_ids = tuple(
        sorted(
            (
                entity_id
                for entity_id in world.observable_items(observer_id, request.focus)
                if world.is_item(entity_id) and world.is_visible(entity_id) and world.sees(observer_id, entity_id)
            ),
            key=lambda entity_id: _sort_key(world, entity_id),
        )
    )
    visible_set = set(visible_ids)
    required_ids = world.required_observations(observer_id, request.focus, visible_set, request.kind)
    required_ids = tuple(sorted(required_ids, key=lambda entity_id: _sort_key(world, entity_id)))
    if len(required_ids) > max_required:
        names = ", ".join(world.name(entity_id) for entity_id in required_ids)
        raise ObservationScopeTooLarge(f"required observation scope exceeds {max_required}: {names}")

    optional_ids = tuple(entity_id for entity_id in visible_ids if entity_id not in required_ids)
    selected_optional = optional_ids[:max_optional]
    omitted_optional = tuple(world.name(entity_id) for entity_id in optional_ids[max_optional:])
    selected_ids = (*required_ids, *selected_optional)
    selected_ids = tuple(sorted(selected_ids, key=lambda entity_id: _sort_key(world, entity_id)))

    contingent_ids = _contingent_ids(world, request)
    return ObservationContext(
        observer=entity_label(world, observer_id),
        action=request.action,
        completed_actions=tuple(completed_actions),
        visible_things=tuple(
            _observed(world, entity_id, entity_label, scene_location_id) for entity_id in selected_ids
        ),
        contingent_things=tuple(
            _observed(world, entity_id, entity_label, scene_location_id) for entity_id in contingent_ids
        ),
        required=tuple(world.name(entity_id) for entity_id in required_ids),
        omitted_optional=omitted_optional,
        scope_complete=bool(request.focus and world.contents_complete(request.focus)),
        scene=entity_label(world, scene_location_id) if scene_location_id is not None else None,
    )


def _sort_key(world: World, entity_id: str) -> tuple[str, str, str]:
    name = world.name(entity_id)
    return name.casefold(), name, entity_id


def _contingent_ids(world: World, request: ObservationRequest) -> tuple[str, ...]:
    if (
        request.kind != "open"
        or not request.focus
        or not world.exists(request.focus)
        or not world.is_a(request.focus, "container")
    ):
        return ()
    return tuple(
        sorted(
            (
                entity_id
                for entity_id in world.given_with(request.focus)
                if not world.is_hidden(entity_id) and world.is_item(entity_id)
            ),
            key=lambda entity_id: _sort_key(world, entity_id),
        )
    )


def _observed(
    world: World,
    entity_id: str,
    label: Callable[[World, str], str],
    scene_location_id: str | None = None,
) -> ObservedThing:
    parent_id = world.parent(entity_id)
    holder_id = world.holder(entity_id)
    return ObservedThing(
        name=world.name(entity_id),
        place=label(world, parent_id) if parent_id else None,
        holder=label(world, holder_id) if holder_id else None,
        scene_level=(scene_location_id is not None and holder_id is None and parent_id == scene_location_id),
    )


def _prompt_thing(thing: ObservedThing) -> str:
    fields = [thing.name]
    if thing.place:
        fields.append(f"place={thing.place}")
    if thing.holder:
        fields.append(f"holder={thing.holder}")
    return "; ".join(fields)
