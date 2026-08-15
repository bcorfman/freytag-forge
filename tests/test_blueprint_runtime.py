"""Phase-5 runtime realization contracts for immutable Story Blueprints."""

from storygame.authoring.blueprint_contracts import load_story_blueprint_fixture
from storygame.authoring.compiler import load_compiled_story_fixture
from storygame.runtime.blueprint import (
    ProgressionValidator,
    blueprint_observer_context,
    realize_blueprint,
)
from storygame.runtime.context import RuntimeContextBuilder
from storygame.runtime.contracts import BeatUpdate, RuntimeFailure, StateOperation, TurnResult
from storygame.runtime.state import bootstrap_runtime_state
from storygame.runtime.validation import validate_and_commit


def _runtime():
    return realize_blueprint(load_story_blueprint_fixture("vale_mansion_case"))


def test_realization_keeps_canon_in_facts_but_hides_protected_truth_from_player() -> None:
    runtime = _runtime()

    assert runtime.facts["perpetrator_identity"] == "Estate solicitor Beatrice Harrow killed Emma Vale."
    context = blueprint_observer_context(runtime, "elias_wren")
    assert "perpetrator_identity" not in context["known_truth_ids"]
    assert {route["id"] for route in context["legal_routes"]} == {
        "review_case_file",
        "inspect_gallery_staging",
    }


def test_progression_requires_a_declared_available_route_and_evidence() -> None:
    validator = ProgressionValidator(_runtime())

    validator.commit(BeatUpdate(beat_id="suspicious_opening", route_id="review_case_file", evidence_ids=("case_file",)))
    assert "suspicious_death" in validator.runtime.player_truths
    assert "death_is_suspicious" in validator.runtime.completed_revelations

    before = validator.runtime.snapshot()
    try:
        validator.commit(BeatUpdate(beat_id="payment_reversal", route_id="invented_route"))
    except ValueError as exc:
        assert "route" in str(exc)
    else:
        raise AssertionError("an invented route must fail closed")
    assert validator.runtime.snapshot() == before


def test_progression_rejects_bare_mismatched_and_invalid_evidence_routes() -> None:
    validator = ProgressionValidator(_runtime())

    for update, message in (
        (BeatUpdate(beat_id="suspicious_opening"), "requires route_id"),
        (BeatUpdate(beat_id="payment_reversal", route_id="review_case_file"), "cannot complete"),
        (
            BeatUpdate(
                beat_id="suspicious_opening",
                route_id="review_case_file",
                evidence_ids=("missing_evidence",),
            ),
            "unavailable evidence",
        ),
        (
            BeatUpdate(
                beat_id="suspicious_opening",
                route_id="inspect_gallery_staging",
                evidence_ids=("delivery_log",),
            ),
            "does not support",
        ),
    ):
        try:
            validator.commit(update)
        except ValueError as exc:
            assert message in str(exc)
        else:
            raise AssertionError("invalid route progression must fail closed")


def test_runtime_operations_remain_available_before_blueprint_progression() -> None:
    state = bootstrap_runtime_state(load_compiled_story_fixture("mystery"))
    result = TurnResult(
        narration="The scene changes.",
        operations=(
            StateOperation(kind="set", path="world.location", value="gallery"),
            StateOperation(kind="set", path="world.attributes.weather", value="rain"),
        ),
    )

    committed = validate_and_commit(state, result)
    assert committed.world.location == "gallery"
    assert committed.world.attributes["weather"] == "rain"


def test_shared_validation_wraps_invalid_blueprint_progression_and_provider_envelopes() -> None:
    state = bootstrap_runtime_state(
        load_compiled_story_fixture("mystery"), load_story_blueprint_fixture("vale_mansion_case")
    )
    invalid = TurnResult(
        narration="The model invents nothing.",
        beat_updates=(BeatUpdate(beat_id="suspicious_opening", route_id="invented_route"),),
    )
    try:
        validate_and_commit(state, invalid)
    except RuntimeFailure as exc:
        assert exc.code == "INVALID_BLUEPRINT_PROGRESSION"
    else:
        raise AssertionError("invalid blueprint progression must be typed")

    try:
        TurnResult.from_provider(object())
    except RuntimeFailure as exc:
        assert exc.code == "INVALID_TURN"
    else:
        raise AssertionError("invalid provider content must fail locally")
    assert TurnResult.from_provider({"response": {"message": {"content": '{"narration":"ok"}'}}}).narration == "ok"


def test_bootstrap_uses_a_safe_location_when_legacy_fixture_omits_one() -> None:
    story = load_compiled_story_fixture("mystery").model_copy(update={"initial_world_state": {}})
    assert bootstrap_runtime_state(story).world.location == "opening"


def test_failed_route_commits_declared_failure_forward_before_returning() -> None:
    validator = ProgressionValidator(_runtime())

    outcome = validator.commit(
        BeatUpdate(beat_id="suspicious_opening", route_id="inspect_gallery_staging"),
        failed=True,
    )

    assert outcome.failed
    assert "suspicious_death" in validator.runtime.player_truths
    assert "find_ledger_leaf" in {route.id for route in validator.runtime.legal_routes()}


def test_shared_turn_contract_exposes_only_legal_routes_and_rejects_bare_tags() -> None:
    state = bootstrap_runtime_state(
        load_compiled_story_fixture("mystery"), load_story_blueprint_fixture("vale_mansion_case")
    )
    context = RuntimeContextBuilder().build(state, "Review the file.")

    assert {route["id"] for route in context.payload["blueprint"]["legal_routes"]} == {
        "review_case_file",
        "inspect_gallery_staging",
    }
    assert "perpetrator_identity" not in context.payload["blueprint"]["known_truth_ids"]

    result = TurnResult(
        narration="You find the case file.",
        beat_updates=(
            BeatUpdate(
                beat_id="suspicious_opening",
                route_id="review_case_file",
                evidence_ids=("case_file",),
            ),
        ),
    )
    committed = validate_and_commit(state, result)
    assert "suspicious_death" in committed.blueprint_runtime.player_truths  # type: ignore[union-attr]

    bare = TurnResult(
        narration="A label alone proves nothing.",
        beat_updates=(BeatUpdate(beat_id="suspicious_opening"),),
    )
    try:
        validate_and_commit(state, bare)
    except Exception as exc:
        assert getattr(exc, "code", None) == "BLUEPRINT_ROUTE_REQUIRED"
    else:
        raise AssertionError("a blueprint turn must not accept a bare completion tag")
