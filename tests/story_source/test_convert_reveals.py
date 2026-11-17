"""Tests for converting loaded storylet and realization records to source data."""

# NOTE: The compiler feeds one reveal title/window into both package records, so
# route title/window values win the legacy Storylet drift documented in NOTES.
# NOTE: Reader-only sections, prose, and authoring handles are not package data;
# the converter uses route IDs as stable reveal/variant handles.
# NOTE: Entry, bridge, incident-observation, and ending claims are intentionally
# excluded because another converter worker owns those contract sections.

from collections import Counter
from pathlib import Path

from storygame.story_package.loader import load_story_package
from storygame.story_source.convert_reveals import RevealsResult, convert_reveals

ROOT = Path(__file__).parents[2]
PACKAGE = load_story_package(ROOT / "data" / "stories" / "continuity-initiative")
RESULT = convert_reveals(PACKAGE)


def _reveal(storylet_id: str) -> dict:
    """Find a converted reveal by its runtime storylet ID."""

    return next(
        reveal
        for document in RESULT.scene_docs.values()
        for reveal in document["reveals"]
        if reveal["storylet_id"] == storylet_id
    )


def _claim_doc(claim_id: str) -> dict:
    """Find a primary or extra converted claim by ID."""

    for document in RESULT.scene_docs.values():
        for reveal in document["reveals"]:
            for variant in reveal["variants"].values():
                if variant.get("claim_id") == claim_id:
                    return variant
                for extra in variant.get("extra_claims", []):
                    if extra.get("claim_id") == claim_id:
                        return extra
    raise AssertionError(f"missing converted claim {claim_id}")


def _skipped_claims() -> set[str]:
    """Return incident outcome claim IDs whose match entries are scene-owned."""

    outcomes = {
        (outcome.storylet_id, outcome.realization_id) for incident in PACKAGE.incidents for outcome in incident.outcomes
    }
    return {
        claim.id
        for claim in PACKAGE.knowledge.knowledge
        if claim.source.kind == "storylet_realization"
        and (claim.source.storylet_id, claim.source.realization_id) in outcomes
    }


def test_result_shape_and_all_storylets_and_realizations_are_present() -> None:
    """Every runtime storylet and realization is emitted once."""

    assert isinstance(RESULT, RevealsResult)
    assert set(RESULT.scene_docs) == {scene.metadata.scene_id for scene in PACKAGE.scenes}
    assert all(set(document) == {"reveals"} for document in RESULT.scene_docs.values())

    storylet_ids = [reveal["storylet_id"] for document in RESULT.scene_docs.values() for reveal in document["reveals"]]
    realization_ids = [
        variant["realization_id"]
        for document in RESULT.scene_docs.values()
        for reveal in document["reveals"]
        for variant in reveal["variants"].values()
    ]
    assert Counter(storylet_ids) == Counter(storylet.id for storylet in PACKAGE.storylets)
    assert Counter(realization_ids) == Counter(
        realization.id for route in PACKAGE.storylet_routes.storylets for realization in route.realizations
    )


def test_claims_are_complete_in_reveals_and_match_order() -> None:
    """Eligible realization claims appear in both outputs in package order."""

    skipped = _skipped_claims()
    expected = [claim for claim in PACKAGE.knowledge.knowledge if claim.source.kind == "storylet_realization"]
    reveal_claims = [
        variant["claim_id"]
        for document in RESULT.scene_docs.values()
        for reveal in document["reveals"]
        for variant in reveal["variants"].values()
        if "claim_id" in variant
    ]
    reveal_claims.extend(
        extra["claim_id"]
        for document in RESULT.scene_docs.values()
        for reveal in document["reveals"]
        for variant in reveal["variants"].values()
        for extra in variant.get("extra_claims", [])
    )
    assert Counter(reveal_claims) == Counter(claim.id for claim in expected)

    for scene_id, document in RESULT.match_docs.items():
        assert document["schema"] == 1
        expected_scene = [
            claim.id for claim in expected if claim.available_in_scenes == (scene_id,) and claim.id not in skipped
        ]
        assert list(document["claims"]) == expected_scene
        assert set(document) <= {"schema", "scene", "claims", "deliveries"}


def test_three_storylets_and_realizations_copy_route_values() -> None:
    """Spot-check shared reveal fields and three realization records."""

    for route in PACKAGE.storylet_routes.storylets[:3]:
        reveal = _reveal(route.id)
        assert reveal["id"] == route.id.lower().replace("-", "_")
        assert reveal["title"] == route.title
        assert reveal["guidance"]["pressure_role"] == route.pressure_role
        assert reveal["guidance"]["window"] == {
            "earliest_turn": route.earliest_turn,
            "target_turn": route.target_turn,
            "latest_turn": route.latest_turn,
        }
        realization = route.realizations[0]
        variant_key = realization.id.removeprefix(f"{route.id}-").lower().replace("-", "_")
        variant = reveal["variants"][variant_key]
        assert variant["intent"] == realization.dramatic_intent
        scene = next(scene for scene in PACKAGE.scenes if scene.metadata.scene_id == route.scene_id)
        beat_ids = {beat.anchor: beat.id for beat in scene.beats.values()}
        if realization.source_beats:
            assert variant["from_outline"] == [beat_ids[anchor] for anchor in realization.source_beats]
        else:
            assert "from_outline" not in variant
        assert variant["helps_exit"] == list(realization.helps_transition_triggers)
        assert variant["commits"] == {
            operation.fact_id: "retract" if operation.op == "retract" else operation.value
            for operation in realization.operations
        }


def test_five_claims_copy_text_and_matcher_values() -> None:
    """Spot-check claim prose plus expanded matcher fields, including the contract example."""

    claim_ids = [
        "k_sl_1a_b_r0",
        "k_sl_1a_a_r1",
        "k_sl_1a_g_r1",
        "k_sl_1a_h_r1",
        "k_sl_1a_i_r1",
    ]
    claims = {claim.id: claim for claim in PACKAGE.knowledge.knowledge}
    match_claims = {
        claim_id: RESULT.match_docs[claims[claim_id].available_in_scenes[0]]["claims"][claim_id]
        for claim_id in claim_ids
    }
    for claim_id in claim_ids:
        claim = claims[claim_id]
        variant = _claim_doc(claim_id)
        assert variant["says"] == claim.statement
        assert variant.get("text") == claim.delivery_text
        assert match_claims[claim_id]["aliases"] == list(claim.aliases)
        assert match_claims[claim_id]["action_evidence"] == [list(group) for group in claim.action_evidence]
        assert match_claims[claim_id]["must_convey"] == [list(group) for group in claim.must_convey]
        if claim.leak_terms is None:
            assert "leak_terms" not in match_claims[claim_id]
        else:
            assert match_claims[claim_id]["leak_terms"] == list(claim.leak_terms)
