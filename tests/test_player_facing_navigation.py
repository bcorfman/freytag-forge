"""Player-facing routing must use semantic route names, never compass coordinates."""

import json

from storygame.engine.affordances import build_affordance_context
from storygame.engine.freeform import _freeform_planner_prompt
from storygame.engine.parser import parse_command
from storygame.llm.context import build_narration_context
from storygame.llm.prompts import build_prompt
from tests.fast_fixtures import make_cached_story_state as build_default_state


def test_mystery_routes_expose_semantic_labels_instead_of_compass_directions() -> None:
    state = build_default_state(seed=1701, genre="mystery")

    context = build_narration_context(state, parse_command("look"), "hook")
    prompt = build_prompt(context)["user"]
    _system, planner_json = _freeform_planner_prompt(state, "enter the mansion")
    planner = json.loads(planner_json)
    affordances = build_affordance_context(state)

    assert context.exits == ("mansion entrance",)
    assert "Exits: mansion entrance" in prompt
    assert "north" not in prompt.lower()
    assert planner["room"]["exits"] == ["mansion entrance"]
    assert affordances["exits"][0]["label"] == "mansion entrance"
