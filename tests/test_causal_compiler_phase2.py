"""Phase-2 bound IR keeps semantic passes on typed links."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from storygame.authoring.bound_ir import BoundBlueprint, bind_blueprint
from storygame.authoring.causal_contracts import validate_causal_compiled_story
from storygame.authoring.symbol_resolution import Namespace
from tests.test_causal_story_contract import _story


def test_binding_constructs_immutable_projection_with_typed_links() -> None:
    story = validate_causal_compiled_story(_story())
    bound = bind_blueprint(story)

    assert isinstance(bound, BoundBlueprint)
    assert bound.opening_truths[0].symbol.namespace is Namespace.TRUTH
    route = next(item for item in bound.realization_routes if item.id == "diagnose_scan")
    assert route.revelation.id == "diagnose"
    assert route.opportunities[0].id == "scan"
    assert route.opportunities[0].truth.id == "failure"
    assert route.opportunities[0].route.id == route.id
    with pytest.raises(FrozenInstanceError):
        bound.story = story  # type: ignore[misc]


def test_bound_projection_carries_all_declared_namespaces_once() -> None:
    bound = bind_blueprint(validate_causal_compiled_story(_story()))

    assert bound.ids(Namespace.TRUTH) == ("constraint", "failure", "opening", "remedy", "tradeoff")
    assert bound.ids(Namespace.END_STATE) == ("ending",)
    assert bound.party_knowledge[0].participant.id == "engineer"
    assert bound.party_knowledge[0].truths[0].id == "opening"
