"""Replies' short condition phrases that match an approved facet value become facets (richer-narration 3A)."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from worldkeeper import PropProposal

from storygame.runtime.item_facts import ItemFactsProvider
from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import incidental_policy_for, world_for
from storygame.story_package.loader import load_story_package
from tests.test_incidental_package import LIGHTHOUSE, lighthouse


def provider_for(tmp_path, *, policy=True):
    package = load_story_package(lighthouse(Path(tempfile.mkdtemp(dir=tmp_path))) if policy else LIGHTHOUSE)
    state = RuntimeState.bootstrap(package)
    provider = ItemFactsProvider(
        worker_url="", token="", state=state, item_facts={}, mode="single_call", seed_from_package=True, held_by=True
    )
    provider.prepare_turn("Look at the logbook.")
    return provider


def world(provider):
    return world_for(provider.state.package, provider.state.facts)


def test_a_phrase_that_matches_a_facet_value_becomes_a_facet_and_the_rest_stay_conditions(tmp_path):
    provider = provider_for(tmp_path)
    _facts, issues = provider.apply_item_facts({"Tom's logbook": {"condition": ["brown", "dusty"]}})
    assert world(provider).facets("logbook") == {"color": "brown"}
    assert world(provider).conditions("logbook") == ("dusty",)
    assert not any("brown" in issue for issue in issues)


def test_matching_ignores_case_and_spacing(tmp_path):
    provider = provider_for(tmp_path)
    provider.apply_item_facts({"Tom's logbook": {"condition": ["  Black "]}})
    assert world(provider).facets("logbook") == {"color": "black"}
    assert world(provider).conditions("logbook") == ()


def test_without_a_package_policy_conditions_behave_exactly_as_before(tmp_path):
    provider = provider_for(tmp_path, policy=False)
    provider.apply_item_facts({"Tom's logbook": {"condition": ["brown", "dusty"]}})
    assert world(provider).conditions("logbook") == ("brown", "dusty")
    assert world(provider).facets("logbook") == {}


def test_a_matching_phrase_for_a_value_already_set_differently_is_refused_and_reported(tmp_path):
    provider = provider_for(tmp_path)
    provider.apply_item_facts({"Tom's logbook": {"condition": ["brown"]}})
    _facts, issues = provider.apply_item_facts({"Tom's logbook": {"condition": ["black"]}})
    assert world(provider).facets("logbook") == {"color": "brown"}
    assert "black" not in world(provider).conditions("logbook")
    assert any("black" in issue for issue in issues)


def _prop(provider):
    policy = incidental_policy_for(provider.state.package)
    result = world(provider).apply_embellishments(policy, "1A", (PropProposal("tea cup", "bench"),), ())
    assert result.ok
    return result.created[0]


def test_a_new_prop_takes_facets_only_and_never_a_free_condition(tmp_path):
    provider = provider_for(tmp_path)
    cup = _prop(provider)
    _facts, issues = provider.apply_item_facts({"tea cup": {"condition": ["blue", "chipped"]}})
    assert world(provider).facets(cup) == {"color": "blue"}
    assert world(provider).conditions(cup) == ()
    assert any("chipped" in issue for issue in issues)


@pytest.mark.parametrize("phrase", ["lit", "sturdy", "locked"])
def test_other_phrases_on_authored_things_are_kept_as_conditions(tmp_path, phrase):
    provider = provider_for(tmp_path)
    provider.apply_item_facts({"Tom's logbook": {"condition": [phrase]}})
    assert world(provider).conditions("logbook") == (phrase,)


def test_a_reply_that_only_routes_facets_keeps_the_existing_conditions(tmp_path):
    provider = provider_for(tmp_path)
    provider.apply_item_facts({"Tom's logbook": {"condition": ["dusty"]}})
    provider.apply_item_facts({"Tom's logbook": {"condition": ["brown"]}})
    assert world(provider).facets("logbook") == {"color": "brown"}
    assert world(provider).conditions("logbook") == ("dusty",)
