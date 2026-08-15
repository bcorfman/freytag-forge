"""End-to-end Phase-5 route progression through the V2 turn boundary."""

from storygame.authoring.blueprint_contracts import load_story_blueprint_fixture
from storygame.authoring.compiler import load_compiled_story_fixture
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.state import bootstrap_runtime_state


class _Model:
    def __init__(self, responses: list[dict[str, object]]) -> None:
        self.responses = responses
        self.contexts: list[object] = []

    def play_turn(self, context: object, *, json_object: bool) -> dict[str, object]:
        self.contexts.append(context)
        return self.responses.pop(0)


def _engine(responses: list[dict[str, object]]) -> tuple[RuntimeEngine, _Model]:
    state = bootstrap_runtime_state(
        load_compiled_story_fixture("mystery"), load_story_blueprint_fixture("vale_mansion_case")
    )
    model = _Model(responses)
    return RuntimeEngine(state, model), model


def _route_turn(route_id: str, *, failed: bool = False) -> dict[str, object]:
    return {
        "narration": "The investigation produces a bounded result.",
        "beat_updates": [
            {
                "beat_id": "suspicious_opening",
                "route_id": route_id,
                "evidence_ids": ["case_file"] if route_id == "review_case_file" else [],
                "route_failed": failed,
            }
        ],
        "material_progress": True,
    }


def test_blueprint_turn_commits_an_authored_route_in_one_model_request() -> None:
    engine, model = _engine([_route_turn("review_case_file")])

    response = engine.turn("Review the case file.")

    assert response.ok and response.model_calls == 1
    assert "suspicious_death" in engine.state.blueprint_runtime.player_truths  # type: ignore[union-attr]
    context = model.contexts[0]
    assert "perpetrator_identity" not in context.payload["blueprint"]["known_truth_ids"]


def test_blueprint_failed_route_commits_failure_forward_and_unblocks_the_next_route() -> None:
    engine, _ = _engine([_route_turn("inspect_gallery_staging", failed=True)])

    response = engine.turn("Inspect the staged window.")

    assert response.ok
    runtime = engine.state.blueprint_runtime
    assert runtime is not None and "suspicious_death" in runtime.player_truths
    assert "find_ledger_leaf" in {route.id for route in runtime.legal_routes()}


def test_blueprint_turn_rejects_an_invented_route_without_committing_facts() -> None:
    engine, _ = _engine([_route_turn("invented_route"), _route_turn("invented_route")])

    response = engine.turn("Invent a clue.")

    assert not response.ok and response.model_calls == 2
    runtime = engine.state.blueprint_runtime
    assert runtime is not None and runtime.player_truths == set()
