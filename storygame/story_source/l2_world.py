"""Layer-two validation for world catalog records."""

from __future__ import annotations

from collections.abc import Mapping

from .checks import layer2_check
from .diagnostics import Diagnostic
from .reader import SourceTree

_CATALOG_FILE = "catalog.yaml"
_ENTITY_SECTIONS = (("places", "location"), ("characters", "npc"), ("groups", "group"), ("items", "item"))


def _mapping(value: object) -> Mapping[object, object] | None:
    """Return mappings only, leaving malformed shapes to layer one."""

    return value if isinstance(value, Mapping) else None


def _diagnostic(address: str, field: str, message: str, *, code: str) -> Diagnostic:
    """Build a source-located world diagnostic."""

    return Diagnostic(code, _CATALOG_FILE, address, field, message)


def _records(catalog: Mapping[object, object], section: str) -> list[tuple[object, Mapping[object, object]]]:
    """Return well-shaped catalog entity records in source order."""

    records = _mapping(catalog.get(section))
    if records is None:
        return []
    return [(identifier, record) for identifier, value in records.items() if (record := _mapping(value)) is not None]


def _entity_address(identifier: object) -> str:
    """Return the contract address for a catalog entity."""

    return f"entity:{identifier}"


def _axis_diagnostics(catalog: Mapping[object, object]) -> list[Diagnostic]:
    """Validate two-pole axes and unavailable poles for items and NPCs."""

    diagnostics: list[Diagnostic] = []
    for section, kind in (("items", "item"), ("characters", "npc")):
        for identifier, record in _records(catalog, section):
            axes = record.get("axes")
            if not isinstance(axes, list):
                continue
            poles: set[str] = set()
            for index, axis_value in enumerate(axes):
                axis = _mapping(axis_value)
                address = f"{_entity_address(identifier)}.axes[{index}]"
                if axis is None:
                    continue
                if len(axis) != 2:
                    diagnostics.append(
                        _diagnostic(
                            address,
                            "axes",
                            f"{kind} '{identifier}' axes must each define exactly two poles",
                            code="L2.axis_pole",
                        )
                    )
                    continue
                axis_poles = tuple(axis)
                if not all(isinstance(pole, str) and pole.strip() for pole in axis_poles):
                    continue
                poles.update(axis_poles)
                aliases = [axis.get(pole) for pole in axis_poles]
                if not all(isinstance(values, list) for values in aliases):
                    continue
                first_words = {str(axis_poles[0]).casefold(), *(str(alias).casefold() for alias in aliases[0])}
                second_words = {str(axis_poles[1]).casefold(), *(str(alias).casefold() for alias in aliases[1])}
                if first_words & second_words:
                    diagnostics.append(
                        _diagnostic(
                            address,
                            "axes",
                            f"{kind} '{identifier}' axis poles and aliases must not overlap",
                            code="L2.axis_pole",
                        )
                    )
            unavailable = record.get("unavailable")
            if isinstance(unavailable, str) and unavailable not in poles:
                diagnostics.append(
                    _diagnostic(
                        _entity_address(identifier),
                        "unavailable",
                        f"{kind} '{identifier}' unavailable is not a pole of its axes",
                        code="L2.axis_pole",
                    )
                )
    return diagnostics


def _seat_diagnostics(catalog: Mapping[object, object]) -> list[Diagnostic]:
    """Require both authored lines on every item that is a seat."""

    diagnostics: list[Diagnostic] = []
    for identifier, record in _records(catalog, "items"):
        if record.get("seat_for") is None:
            continue
        for field in ("enter_text", "leave_text"):
            value = record.get(field)
            if isinstance(value, str) and value.strip():
                continue
            diagnostics.append(
                _diagnostic(
                    _entity_address(identifier),
                    field,
                    f"item '{identifier}' seat_for requires {field}",
                    code="L2.seat_lines",
                )
            )
    return diagnostics


def _blank_description_diagnostics(catalog: Mapping[object, object]) -> list[Diagnostic]:
    """Reject explicitly blank place descriptions."""

    diagnostics: list[Diagnostic] = []
    for identifier, record in _records(catalog, "places"):
        description = record.get("description")
        if isinstance(description, str) and not description.strip():
            diagnostics.append(
                _diagnostic(
                    _entity_address(identifier),
                    "description",
                    f"location '{identifier}' description must be a non-blank string",
                    code="L2.blank_description",
                )
            )
    return diagnostics


def _scoped_alias_diagnostics(catalog: Mapping[object, object]) -> list[Diagnostic]:
    """Reject scoped aliases that collide with a declared name or alias."""

    declared_names: set[str] = set()
    for section, _kind in _ENTITY_SECTIONS:
        for _identifier, record in _records(catalog, section):
            name = record.get("name")
            if isinstance(name, str):
                declared_names.add(name.casefold())
            aliases = record.get("aliases")
            if isinstance(aliases, list):
                declared_names.update(alias.casefold() for alias in aliases if isinstance(alias, str))
    diagnostics: list[Diagnostic] = []
    for section, kind in (("groups", "group"), ("items", "item")):
        for identifier, record in _records(catalog, section):
            aliases = record.get("scoped_aliases")
            if not isinstance(aliases, list):
                continue
            for index, scoped_alias in enumerate(aliases):
                address = f"{_entity_address(identifier)}.scoped_aliases[{index}]"
                if not isinstance(scoped_alias, str):
                    continue
                if not scoped_alias.strip():
                    diagnostics.append(
                        _diagnostic(
                            address,
                            "scoped_aliases",
                            f"{kind} '{identifier}' scoped alias must be a non-blank string",
                            code="L2.scoped_alias_collision",
                        )
                    )
                elif scoped_alias.casefold() in declared_names:
                    diagnostics.append(
                        _diagnostic(
                            address,
                            "scoped_aliases",
                            f"{kind} '{identifier}' scoped alias '{scoped_alias}' duplicates a declared "
                            "entity name or alias",
                            code="L2.scoped_alias_collision",
                        )
                    )
    return diagnostics


@layer2_check
def check_world_catalog(tree: SourceTree) -> list[Diagnostic]:
    """Run layer-two checks inherited from the legacy world catalog loader."""

    catalog = _mapping(tree.files.get(_CATALOG_FILE))
    if catalog is None:
        return []
    diagnostics: list[Diagnostic] = []
    diagnostics.extend(_axis_diagnostics(catalog))
    diagnostics.extend(_seat_diagnostics(catalog))
    diagnostics.extend(_blank_description_diagnostics(catalog))
    diagnostics.extend(_scoped_alias_diagnostics(catalog))
    return diagnostics
