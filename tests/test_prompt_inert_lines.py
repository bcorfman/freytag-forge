from __future__ import annotations

from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import apply_scene_placements
from tests import test_richer_3a

PICK = "randomly pick one candidate"
CANDIDATE_ID_RULE = "Do not put a candidate's ID in grounding_ids unless you picked it."
NO_CANDIDATES = "This turn has no candidates. Leave selected_knowledge_ids empty."


def _constraints(scene_id: str, command: str) -> list[str]:
    package = test_richer_3a.PACKAGE
    state = RuntimeState.bootstrap(package)
    state.current_scene_id = scene_id
    state.phase = next(s for s in package.scenes if s.metadata.scene_id == scene_id).metadata.freytag_phase
    state._assert_scene_entry_fact(scene_id)
    apply_scene_placements(package, state.facts, scene_id)
    provider = CloudflareTurnProvider(worker_url="", token="", state=state)
    text = provider._section_user_prompt(provider.assemble_turn_prompt(command)["context"])
    block = text.split("CONSTRAINTS:\n", 1)[1].split("\n\n", 1)[0]
    return [line.removeprefix("- ") for line in block.splitlines()]


def test_a_turn_with_no_candidates_carries_no_rule_about_picking_one():
    # Offering a pick rule and then saying "no candidates" is an instruction and its cancellation: the prompt pays
    # for both and the narrator reads both. The turn that offers candidates keeps the pick rule (see
    # test_cloudflare_transport.py::test_turn_prompt_matches_what_the_turn_actually_offers).
    for scene_id in ("1A", "3A"):
        lines = _constraints(scene_id, "Look around.")
        assert NO_CANDIDATES in lines
        assert not any(PICK in line for line in lines)
        assert CANDIDATE_ID_RULE not in lines
        assert "In grounding_ids, use only an ID you were given as known, or the one candidate you picked." in lines


def test_a_placement_that_repeats_the_thing_s_own_name_is_not_stated():
    lines = _constraints("1A", "Look around.")
    assert "splinters around the back door frame is around the back door frame." not in lines
    # A placement that adds the place still reads.
    assert "back door deadbolt is on the back door." in lines
