import json
from pathlib import Path

import pytest

import bench.cli as bench_cli
import bench.core as core
from bench.core import load_variation, score_fact_tracking_judgments
from bench.item_facts import _MATCH_SYSTEM, ItemFactsProvider, package_seed, validate_item_facts
from storygame.runtime.cloudflare import CloudflareTurnProvider, NarrationProviderError
from storygame.runtime.state import RuntimeState
from storygame.story_package.loader import load_story_package

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = load_story_package(ROOT / "data" / "stories" / "continuity-initiative")
SINGLE = ROOT / "bench" / "variations" / "item-facts-single.json"
SECOND = ROOT / "bench" / "variations" / "item-facts-second.json"


def _provider(mode="single_call"):
    state = RuntimeState.bootstrap(PACKAGE)
    return ItemFactsProvider(
        worker_url="https://worker.example/turn",
        token="",
        state=state,
        item_facts={
            "the lantern": {"place": "on the table", "condition": ["lit"]},
            "the gate": {"place": "at the garden path", "condition": []},
        },
        mode=mode,
    )


class _Response:
    def __init__(self, body):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return json.dumps(self.body).encode()


def test_things_are_after_scene_and_render_single_value_facts():
    provider = _provider()
    provider._selected_names = list(provider.item_facts)
    prompt = provider.assemble_turn_prompt("Look at the back door.")
    user = provider._section_user_prompt(prompt["context"])

    assert (
        "\n\nTHINGS:\n"
        "- the lantern. Place: on the table. Condition: lit.\n"
        "- the gate. Place: at the garden path.\n\n"
        "CONSTRAINTS:"
    ) in user
    assert provider._placement_rules() == []
    assert provider._setting_fact_rules() == []


def test_player_block_places_come_before_the_command():
    provider = _provider()
    provider.item_facts["the notebook"] = {"place": "in Michelle's hand", "condition": []}
    provider.item_facts["the gate"]["place"] = None
    provider._selected_names = ["the notebook", "the lantern", "the gate"]

    prompt = provider.assemble_turn_prompt("Pick up the notebook.")
    user = provider._section_user_prompt(prompt["context"])

    assert user.split("PLAYER:\n", 1)[1] == (
        "- the notebook is in Michelle's hand.\n- the lantern is on the table.\n- Pick up the notebook."
    )


def test_single_call_rules_require_facts_for_every_change():
    system = _provider()._system_prompt()

    assert system.endswith(
        "Every time your story moves or changes a thing, or puts a new thing in a place, "
        "add that thing to item_facts. Use where it is when the story ends.\n"
        'Give only what changed. Use "place" for its current location and "condition" for up to two short phrases. '
        "Example: if she throws a cup at the wall, it cracks in two and falls, so the cup is "
        '{"place": "on the floor", '
        '"condition": ["cracked in two"]}.'
    )
    assert 'falls, so the cup is {"place": "on the floor"' in system
    assert '"condition": ["cracked in two"]' in system
    assert "Also return item_facts" not in system


def test_item_facts_uses_things_place_rule_on_turn_and_opening(monkeypatch):
    provider = _provider()

    assert "Each thing starts at the place THINGS gives it." in provider._turn_rules()
    assert "Keep each object where the scene puts it." not in provider._turn_rules()

    monkeypatch.setattr(
        "storygame.runtime.cloudflare.urlopen",
        lambda request, **kwargs: _Response({"segments": [{"kind": "narration", "text": "The room is quiet."}]}),
    )
    provider.opening()
    user = provider.last_prompt["user"]
    assert "Each thing starts at the place THINGS gives it." in user
    assert "Keep each object where the scene puts it." not in user


def test_match_system_describes_references_and_new_names():
    assert '"refers"' in _MATCH_SYSTEM and '"same_as"' in _MATCH_SYSTEM
    assert "carried" not in _MATCH_SYSTEM
    assert "PLACES" not in _MATCH_SYSTEM
    assert '"places"' not in _MATCH_SYSTEM
    assert '"refers"' in _MATCH_SYSTEM and '"same_as"' in _MATCH_SYSTEM


def test_things_omit_condition_for_empty_condition_list():
    provider = _provider()
    provider._selected_names = list(provider.item_facts)
    assert provider._things_block() == (
        "THINGS:\n- the lantern. Place: on the table. Condition: lit.\n- the gate. Place: at the garden path."
    )


def test_things_show_state_axis_vocabulary_and_other_conditions():
    provider = _provider()
    provider._selected_names = list(provider.item_facts)
    provider.state_axes = {
        "the lantern": {"shut": ["closed"], "open": []},
        "the gate": {"open": [], "closed": []},
    }
    provider.item_facts["the lantern"]["condition"] = ["shut", "dusty"]
    assert provider._things_block() == (
        "THINGS:\n"
        "- the lantern. Place: on the table. Condition: shut (or open), dusty.\n"
        "- the gate. Place: at the garden path."
    )


def test_things_axis_vocabulary_remains_after_axis_is_cleared():
    provider = _provider()
    provider._selected_names = list(provider.item_facts)
    provider.state_axes = {"the lantern": {"shut": ["closed"], "open": []}}
    provider.apply_item_facts({"the lantern": {"condition": ["shut"]}})
    assert "Condition: shut (or open)." in provider._things_block()
    provider.apply_item_facts({"the lantern": {"condition": []}})
    assert "Condition:" not in provider._things_block().splitlines()[1]


def test_single_call_strips_item_facts_before_strict_proposal_and_carries_them(monkeypatch):
    provider = _provider()
    payloads = iter(
        [
            {
                "segments": [{"kind": "narration", "text": "The house is quiet."}],
                "item_facts": {
                    "the lantern": {"place": "in her hand", "condition": ["warm"]},
                    "the gate": {"place": "at the garden path", "condition": []},
                },
            },
        ]
    )
    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", lambda *_args, **_kwargs: _Response(next(payloads)))

    provider("Look at the lantern.")
    assert provider.pending_item_facts() == {
        "the lantern": {"place": "in her hand", "condition": ["warm"]},
        "the gate": {"place": "at the garden path", "condition": []},
    }
    provider.apply_item_facts(provider.pending_item_facts())
    provider._selected_names = ["the lantern", "the gate"]
    next_prompt = provider.assemble_turn_prompt("Look at the gate.")
    assert "- the lantern. Place: in her hand. Condition: warm." in provider._section_user_prompt(
        next_prompt["context"]
    )


def test_item_facts_lifts_misplaced_changes_without_overriding_explicit_facts(monkeypatch):
    provider = _provider()
    monkeypatch.setattr(
        "storygame.runtime.cloudflare.urlopen",
        lambda *_args, **_kwargs: _Response(
            {
                "segments": [{"kind": "narration", "text": "The change is clear."}],
                "selected_knowledge_ids": [],
                "truck": {"condition": ["moving"], "place": "on the road"},
                "the lantern": {"place": "wrong", "condition": ["wrong"]},
                "item_facts": {"the lantern": {"place": "right", "condition": ["lit"]}},
            }
        ),
    )

    reply = provider._request({"system": "", "user": ""})

    assert reply["segments"]
    assert provider.pending_item_facts() == {
        "the lantern": {"place": "right", "condition": ["lit"]},
        "truck": {"condition": ["moving"], "place": "on the road"},
    }
    assert provider.item_facts_lifted == 1


def test_item_facts_does_not_create_empty_side_channel_when_nothing_is_lifted(monkeypatch):
    provider = _provider()
    monkeypatch.setattr(
        "storygame.runtime.cloudflare.urlopen",
        lambda *_args, **_kwargs: _Response({"segments": [{"kind": "narration", "text": "Nothing changes."}]}),
    )

    reply = provider._request({"system": "", "user": ""})

    assert reply == {"segments": [{"kind": "narration", "text": "Nothing changes."}]}
    assert "item_facts" not in reply
    assert provider.pending_item_facts() is None


def test_item_facts_creates_side_channel_for_a_lifted_entry(monkeypatch):
    provider = _provider()
    monkeypatch.setattr(
        "storygame.runtime.cloudflare.urlopen",
        lambda *_args, **_kwargs: _Response(
            {
                "segments": [{"kind": "narration", "text": "The truck moves."}],
                "truck": {"place": "on the road"},
            }
        ),
    )

    reply = provider._request({"system": "", "user": ""})

    assert reply["segments"]
    assert provider.pending_item_facts() == {"truck": {"place": "on the road"}}
    assert provider.item_facts_lifted == 1


def test_item_facts_keeps_empty_side_channel_and_match_reply(monkeypatch):
    provider = _provider()
    replies = iter(
        [
            {"segments": [{"kind": "narration", "text": "Nothing changes."}], "item_facts": {}},
            {"refers": [], "same_as": {}},
        ]
    )
    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", lambda *_args, **_kwargs: _Response(next(replies)))

    assert provider._request({"system": "", "user": ""}) == {
        "segments": [{"kind": "narration", "text": "Nothing changes."}]
    }
    assert provider.pending_item_facts() == {}
    assert CloudflareTurnProvider._request(provider, {"system": "", "user": ""}) == {"refers": [], "same_as": {}}


def test_apply_item_facts_replaces_valid_entry_and_leaves_omitted_things_unchanged():
    provider = _provider()
    facts, issues = provider.apply_item_facts(
        {"the lantern": {"place": "  in her hand  ", "condition": ["  warm  ", "held"]}}
    )

    assert facts == {
        "the lantern": {"place": "in her hand", "condition": ["warm", "held"]},
        "the gate": {"place": "at the garden path", "condition": []},
    }
    assert issues == []


def test_apply_item_facts_empty_reply_records_no_issue():
    provider = _provider()

    facts, issues = provider.apply_item_facts({})

    assert facts == provider.item_facts
    assert issues == []


def test_apply_item_facts_omitted_reply_clears_transient_state():
    provider = _provider()
    provider.apply_item_facts({"the lantern": {"place": "in her hand"}})
    state_after_change = provider.item_facts.copy()

    facts, issues = provider.apply_item_facts(None)

    assert facts == state_after_change
    assert provider._changed_last_turn == set()
    assert provider._held_item_facts == {}
    assert issues == ["narrator omitted item_facts"]


def test_apply_item_facts_non_dict_reply_clears_transient_state():
    provider = _provider()
    provider.apply_item_facts({"the lantern": {"place": "in her hand"}})

    facts, issues = provider.apply_item_facts("not an object")

    assert facts == provider.item_facts
    assert provider._changed_last_turn == set()
    assert provider._held_item_facts == {}
    assert issues == ["item_facts must be an object mapping thing names to fact objects"]


def test_apply_item_facts_adds_unknown_and_preserves_malformed_entries(monkeypatch):
    provider = _provider()
    monkeypatch.setattr(CloudflareTurnProvider, "_request", lambda *_args: {"oops": 1})
    facts, issues = provider.apply_item_facts(
        {
            "unknown thing": {"place": "somewhere", "condition": []},
            "the gate": {"place": "  ", "condition": ["closed"]},
        }
    )

    assert facts["unknown thing"] == {"place": "somewhere", "condition": []}
    assert provider._held_item_facts == {}
    assert any("the gate" in issue for issue in issues)


def test_apply_item_facts_trims_third_condition_and_phrase_lengths():
    provider = _provider()
    facts, issues = provider.apply_item_facts(
        {
            "the lantern": {
                "place": f"  {'a' * 90}  ",
                "condition": [f" {'b' * 50} ", "second", "third"],
            }
        }
    )

    assert facts["the lantern"] == {"place": "a" * 80, "condition": ["b" * 40, "second"]}
    assert any("condition" in issue for issue in issues)


def test_state_axis_place_becomes_condition_without_match_call():
    provider = _provider()
    provider.state_axes = {"the lantern": {"lit": [], "dark": ["unlit"]}}
    provider.apply_item_facts({"the lantern": {"place": "DARK"}})
    assert provider.item_facts["the lantern"] == {"place": "on the table", "condition": ["dark"]}
    assert provider.item_facts_axis_fixes == 1


def test_fixed_item_refuses_place_but_accepts_condition_change():
    provider = _provider()
    provider.item_facts["drawer"] = {
        "place": "in Michelle's workstation",
        "condition": ["shut"],
    }
    facts, issues = provider.apply_item_facts({"drawer": {"place": "in front of her", "condition": ["open"]}})

    assert facts["drawer"] == {
        "place": "in Michelle's workstation",
        "condition": ["open"],
    }
    assert any("drawer" in issue and "in front of her" in issue for issue in issues)


def test_fixed_item_repeated_place_is_not_a_refusal():
    provider = _provider()
    provider.item_facts["drawer"] = {
        "place": "in Michelle's workstation",
        "condition": ["shut"],
    }

    facts, issues = provider.apply_item_facts(
        {"drawer": {"place": " IN MICHELLE'S WORKSTATION ", "condition": ["open"]}}
    )

    assert facts["drawer"] == {"place": "in Michelle's workstation", "condition": ["open"]}
    assert issues == []


def test_fixed_item_axis_place_still_sets_pole_without_moving():
    provider = _provider()
    provider.item_facts["drawer"] = {
        "place": "in Michelle's workstation",
        "condition": ["shut"],
    }
    provider.state_axes = {"drawer": {"shut": ["closed"], "open": []}}

    facts, issues = provider.apply_item_facts({"drawer": {"place": "open"}})

    assert facts["drawer"] == {
        "place": "in Michelle's workstation",
        "condition": ["open"],
    }
    assert issues == []
    assert provider.item_facts_axis_fixes == 1


def test_movable_item_still_updates_place():
    provider = _provider()

    provider.apply_item_facts({"the lantern": {"place": "in her hand"}})

    assert provider.item_facts["the lantern"]["place"] == "in her hand"


def test_state_axis_alias_is_canonical_and_evicts_opposite():
    provider = _provider()
    provider.state_axes = {"the lantern": {"lit": [], "dark": ["unlit"]}}
    provider.apply_item_facts({"the lantern": {"condition": ["unlit"]}})
    assert provider.item_facts["the lantern"]["condition"] == ["dark"]

    provider.apply_item_facts({"the lantern": {"condition": ["lit"]}})
    assert provider.item_facts["the lantern"]["condition"] == ["lit"]


def test_axis_place_has_its_own_slot_when_conditions_are_full():
    provider = _provider()
    provider.state_axes = {"the lantern": {"lit": [], "dark": ["unlit"]}}
    provider.item_facts["the lantern"]["condition"] = ["carved with KMS", "dusty"]

    provider.apply_item_facts({"the lantern": {"place": "unlit"}})

    assert provider.item_facts["the lantern"] == {
        "place": "on the table",
        "condition": ["dark", "carved with KMS", "dusty"],
    }
    assert provider.item_facts_axis_fixes == 1


def test_non_axis_condition_reply_preserves_axis_and_non_axis_place_does_not_fix_axis():
    provider = _provider()
    provider.state_axes = {"the lantern": {"lit": [], "dark": ["unlit"]}}
    provider.apply_item_facts({"the lantern": {"condition": ["unlit"]}})
    provider.apply_item_facts({"the lantern": {"condition": ["warm"]}})
    assert provider.item_facts["the lantern"]["condition"] == ["dark", "warm"]

    provider.apply_item_facts({"the lantern": {"place": "in her hand"}})
    assert provider.item_facts["the lantern"]["place"] == "in her hand"
    assert provider.item_facts_axis_fixes == 0


def test_empty_condition_reply_clears_axis_and_conditions_but_keeps_place():
    provider = _provider()
    provider.state_axes = {"the lantern": {"shut": ["closed"], "open": []}}
    provider.item_facts["the lantern"]["condition"] = ["open", "carved with KMS"]

    provider.apply_item_facts({"the lantern": {"condition": []}})
    assert provider.item_facts["the lantern"] == {"place": "on the table", "condition": []}

    provider.apply_item_facts({"the lantern": {"condition": ["open"]}})
    provider.apply_item_facts({"the lantern": {"condition": []}})
    assert provider.item_facts["the lantern"]["condition"] == []

    provider.apply_item_facts({"the lantern": {"condition": []}})
    assert provider.item_facts["the lantern"] == {"place": "on the table", "condition": []}


def test_non_axis_place_still_updates_location():
    provider = _provider()
    provider.state_axes = {"the lantern": {"shut": ["closed"], "open": []}}
    provider.apply_item_facts({"the lantern": {"place": "in her hand"}})
    assert provider.item_facts["the lantern"]["place"] == "in her hand"


def test_match_call_has_no_places_section(monkeypatch):
    provider = _provider()
    provider._hand_seed_names = set(provider.item_facts)
    payloads = []
    monkeypatch.setattr(
        CloudflareTurnProvider,
        "_request",
        lambda _provider, payload: payloads.append(payload) or {"refers": [], "same_as": {}},
    )

    provider.apply_item_facts({"the notebook": {"place": "on the desk"}})
    provider.prepare_turn("Search the desk.")
    assert payloads and "PLACES" not in payloads[0]["user"]


def test_second_call_uses_only_things_player_and_story_and_counts_request(monkeypatch):
    provider = _provider("second_call")
    requests = []

    def open_request(request, **_kwargs):
        requests.append(json.loads(request.data))
        return _Response(
            {
                "item_facts": {
                    "the lantern": {"place": "in her hand", "condition": ["warm"]},
                    "the gate": {"place": "at the garden path", "condition": []},
                }
            }
        )

    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", open_request)
    raw = provider.second_call_update("Look at the lantern.", "The lantern feels warm.")

    assert raw == {
        "the lantern": {"place": "in her hand", "condition": ["warm"]},
        "the gate": {"place": "at the garden path", "condition": []},
    }
    assert provider.request_count == 1
    assert "CONSTRAINTS" not in requests[0]["user"]
    assert requests[0]["user"] == ("PLAYER:\n- Look at the lantern.\n\nSTORY:\nThe lantern feels warm.")
    assert requests[0]["system"] == (
        "You keep track of things in a story. Read THINGS, PLAYER and STORY. Return only JSON like "
        '{"item_facts": {"thing": {"place": "place", "condition": ["phrase"]}}}. '
        "List only the things in THINGS that STORY changed. For each one, give the place it is now and up to "
        "two short condition phrases. "
        "Example: if she picks up the lantern from the table, the lantern is "
        '{"place": "in her hand", "condition": ["lit"]}. '
        'If STORY changed nothing, return {"item_facts": {}}.'
    )


@pytest.mark.parametrize("path", [SINGLE, SECOND])
def test_item_facts_variations_load_and_render_offline(path):
    variation = load_variation(path)
    prompt = core.prompt_for(variation, "1A", "Look at the back door.")
    assert "THINGS:" not in prompt["user"]
    assert variation["_package_hash"]


@pytest.mark.parametrize(
    "bad_seed",
    [
        [],
        {"condition": ["lit"]},
        {"place": "", "condition": []},
        {"place": "on the table", "condition": "lit"},
        {"place": "on the table", "condition": [""]},
        {"place": "on the table", "condition": ["one", "two", "three"]},
    ],
)
def test_item_facts_seed_validation_errors(bad_seed):
    with pytest.raises(ValueError, match="item_facts"):
        validate_item_facts({"mode": "single_call", "seed": {"thing": bad_seed}})


@pytest.mark.parametrize(
    "axes",
    [
        {"unknown": {"shut": [], "open": []}},
        {"thing": {"shut": [], "open": [], "ajar": []}},
        {"thing": {"shut": []}},
        {"thing": {"shut": ["closed"], "open": [" CLOSED "]}},
    ],
)
def test_state_axes_validation_rejects_unknown_or_invalid_axes(axes):
    with pytest.raises(ValueError, match="item_facts"):
        validate_item_facts(
            {
                "mode": "single_call",
                "seed": {"thing": {"place": "on the table", "condition": []}},
                "state_axes": axes,
            },
            known_names={"thing"},
        )


def test_bad_item_facts_and_fact_tracking_options_are_rejected(tmp_path):
    source = json.loads(SINGLE.read_text())
    source["item_facts"] = {"mode": "single_call", "seed": {"thing": []}}
    path = tmp_path / "bad-facts.json"
    path.write_text(json.dumps(source))
    with pytest.raises(ValueError, match="item_facts"):
        load_variation(path)


@pytest.mark.parametrize(
    "axes",
    [
        {"unknown": {"shut": [], "open": []}},
        {"thing": {"shut": [], "open": [], "ajar": []}},
        {"thing": {"shut": []}},
    ],
)
def test_variation_load_rejects_invalid_state_axes(tmp_path, axes):
    source = json.loads(SINGLE.read_text())
    source["item_facts"]["state_axes"] = axes
    path = tmp_path / "bad-axes.json"
    path.write_text(json.dumps(source))
    with pytest.raises(ValueError, match="state_axes"):
        load_variation(path)

    source = json.loads(SINGLE.read_text())
    source["fact_tracking_judge"] = "yes"
    path = tmp_path / "bad-judge.json"
    path.write_text(json.dumps(source))
    with pytest.raises(ValueError, match="fact_tracking_judge must be a boolean"):
        load_variation(path)


def test_fact_tracking_score_counts_verdicts_and_causes():
    result = score_fact_tracking_judgments(
        [
            {
                "turns": [
                    {
                        "facts_after_correct": "yes",
                        "missed_change": "no",
                        "invented_change": "no",
                        "narration_contradicts_given_facts": "no",
                        "dropped_true_condition": "no",
                        "kept_ended_condition": "no",
                        "state_as_place": "no",
                        "changes": [{"thing": "the lantern", "change": "warm", "cause": "command"}],
                    }
                ]
            }
        ],
        1,
    )
    assert result["facts_after_correct"] == {"yes": 1, "no": 0}
    assert result["dropped_true_condition"] == {"yes": 0, "no": 1}
    assert result["kept_ended_condition"] == {"yes": 0, "no": 1}
    assert result["state_as_place"] == {"yes": 0, "no": 1}
    assert result["changes_by_cause"] == {"command": 1, "narrator": 0}
    assert result["turns_judged"] == 1
    assert result["judge_calls"] == 1


def test_variations_without_item_facts_keep_the_original_provider(monkeypatch):
    variation = core.resolve_variation(
        {"name": "plain", "story_package": "data/stories/continuity-initiative"},
        ROOT / "plain.json",
    )
    state = RuntimeState.bootstrap(PACKAGE)
    monkeypatch.setattr(
        CloudflareTurnProvider,
        "from_environment",
        classmethod(lambda cls, state, **kwargs: cls(worker_url="", token="", state=state)),
    )
    assert type(core.provider_for(state, variation)) is CloudflareTurnProvider


def test_package_seed_scene_1a_matches_authored_things():
    state = RuntimeState(package=PACKAGE, current_scene_id="1A", phase="exposition")
    state._assert_scene_entry_fact("1A")
    things, issues = package_seed(PACKAGE, state, "1A")
    assert things == {
        "Michelle's phone": {"place": "on the kitchen floor", "condition": ["not damaged"]},
        "Kristin's laptop": {"place": "in Kristin's truck outside the house", "condition": []},
        "drawer": {
            "place": "in Michelle's workstation",
            "condition": ["shut"],
        },
    }
    assert issues == []


def test_package_seed_accepts_the_prefix_case_insensitively():
    scene = next(item for item in PACKAGE.scenes if item.metadata.scene_id == "1A")
    replacement = scene.model_copy(
        update={"metadata": scene.metadata.model_copy(update={"setting_facts": ("THE DRAWER IS SHUT.",)})}
    )
    package = PACKAGE.model_copy(
        update={"scenes": tuple(replacement if item is scene else item for item in PACKAGE.scenes)}
    )
    things, issues = package_seed(package, RuntimeState.bootstrap(package), "1A")
    assert things["drawer"]["condition"] == ["SHUT"]
    assert issues == []


def test_package_seed_hides_guarded_3c_archive():
    state = RuntimeState(package=PACKAGE, current_scene_id="3C", phase="resolution")
    state._assert_scene_entry_fact("3C")
    things, _ = package_seed(PACKAGE, state, "3C")
    assert things["Portable data case"] == {"place": "with Rebecca in her hands", "condition": []}
    state.facts.assert_fact(core.Fact(predicate="portable_archive_secured", subject="story", value="true"))
    things, _ = package_seed(PACKAGE, state, "3C")
    assert "Portable data case" not in things


@pytest.mark.parametrize("change", [{"fixed_turns": 1}, {"scene": "9Z", "fixed_turns": 1, "script": "x"}])
def test_continue_to_validation_errors(tmp_path, change):
    source = json.loads(SINGLE.read_text())
    source["continue_to"] = {"scene": "1B", "fixed_turns": 1, "script": "missing"}
    source["continue_to"].update(change)
    if change == {"fixed_turns": 1}:
        source.pop("fixed_turns")
    path = tmp_path / "invalid-continuation.json"
    path.write_text(json.dumps(source))
    with pytest.raises(ValueError, match="continue_to"):
        load_variation(path)


def test_package_seed_clashing_hand_seed_is_rejected(tmp_path):
    source = json.loads(SINGLE.read_text())
    source["item_facts"] = {
        "mode": "single_call",
        "seed_from_package": True,
        "seed": {"Michelle's phone": {"place": "x", "condition": []}},
    }
    path = tmp_path / "clash.json"
    path.write_text(json.dumps(source))
    with pytest.raises(ValueError, match="clash"):
        load_variation(path)


def test_package_seed_parses_new_and_reports_unparseable_setting_facts(tmp_path):
    scene = next(item for item in PACKAGE.scenes if item.metadata.scene_id == "1A")
    replacement = scene.model_copy(
        update={
            "metadata": scene.metadata.model_copy(
                update={"setting_facts": ("A lamp is bright.", "This has no predicate.")}
            )
        }
    )
    package = PACKAGE.model_copy(
        update={"scenes": tuple(replacement if item is scene else item for item in PACKAGE.scenes)}
    )
    things, issues = package_seed(package, RuntimeState.bootstrap(package), "1A")
    assert "A lamp" not in things
    assert any("A lamp" in issue and "A lamp is bright." in issue for issue in issues)
    assert any("could not be parsed" in issue for issue in issues)


def test_package_seed_refuses_to_place_unplaced_setting_fact():
    scene = next(item for item in PACKAGE.scenes if item.metadata.scene_id == "1A")
    replacement = scene.model_copy(
        update={"metadata": scene.metadata.model_copy(update={"setting_facts": ("The kettle is warm.",)})}
    )
    package = PACKAGE.model_copy(
        update={"scenes": tuple(replacement if item is scene else item for item in PACKAGE.scenes)}
    )
    things, issues = package_seed(package, RuntimeState.bootstrap(package), "1A")
    assert "The kettle" not in things
    assert any("The kettle" in issue and "The kettle is warm." in issue for issue in issues)


def test_legacy_location_key_does_not_move_entry_and_records_issue():
    provider = _provider()
    legacy_location_key = "".join(("w", "here"))
    facts, issues = provider.apply_item_facts({"the lantern": {legacy_location_key: "in her hand"}})
    assert facts["the lantern"] == {"place": "on the table", "condition": ["lit"]}
    assert any("no valid place or condition" in issue for issue in issues)


def test_legacy_location_key_can_still_carry_a_valid_condition():
    provider = _provider()
    legacy_location_key = "".join(("w", "here"))
    facts, issues = provider.apply_item_facts(
        {"the lantern": {legacy_location_key: "in her hand", "condition": ["dark"]}}
    )
    assert facts["the lantern"] == {"place": "on the table", "condition": ["dark"]}
    assert issues == []


def test_place_entry_sets_existing_location():
    provider = _provider()
    provider.apply_item_facts({"the lantern": {"place": "in her hand"}})
    assert provider.item_facts["the lantern"] == {"place": "in her hand", "condition": ["lit"]}


def test_place_entry_updates_location():
    provider = _provider()
    provider.apply_item_facts({"the lantern": {"place": "on the floor"}})
    assert provider.item_facts["the lantern"]["place"] == "on the floor"


def test_same_turn_match_can_add_a_new_tracked_thing(monkeypatch):
    provider = _provider()
    monkeypatch.setattr(
        CloudflareTurnProvider,
        "_request",
        lambda *_args: {"refers": [], "same_as": {"the notebook": "new"}},
    )
    provider.apply_item_facts(
        {"the notebook": {"place": "on the desk", "condition": ["open"]}},
        player_input="Pick up the notebook.",
    )
    result = provider.last_item_facts_match()
    assert result["resolutions"] == {"the notebook": "new"}
    assert provider.item_facts["the notebook"] == {"place": "on the desk", "condition": ["open"]}


def test_reply_location_key_counts_prefer_place(monkeypatch):
    provider = _provider()
    monkeypatch.setattr(
        "storygame.runtime.cloudflare.urlopen",
        lambda *_args, **_kwargs: _Response(
            {
                "segments": [],
                "item_facts": {
                    "the lantern": {"place": "in her hand"},
                    "the gate": {"place": "at the path"},
                    "other": {"condition": ["open"]},
                },
            }
        ),
    )
    provider._request({"system": "test", "user": "test"})
    assert provider.item_facts_reply_keys == {"place": 2}


def test_condition_only_entry_keeps_existing_place():
    provider = _provider()
    provider.apply_item_facts({"the lantern": {"condition": ["dark"]}})
    assert provider.item_facts["the lantern"] == {"place": "on the table", "condition": ["dark"]}


def test_empty_entries_are_ignored_for_tracked_and_untracked_names():
    provider = _provider()
    facts, issues = provider.apply_item_facts({"the lantern": {}, "new thing": {}})
    assert facts == provider.item_facts
    assert provider._held_item_facts == {}
    assert any("empty item_facts entry" in issue for issue in issues)


def test_valid_untracked_name_is_resolved_same_turn(monkeypatch):
    provider = _provider()
    monkeypatch.setattr(CloudflareTurnProvider, "_request", lambda *_args: {"oops": 1})
    provider.apply_item_facts({"the notebook": {"place": "on the desk", "condition": ["open"]}})
    assert provider.item_facts["the notebook"] == {"place": "on the desk", "condition": ["open"]}
    assert provider._held_item_facts == {}


def test_owner_resolves_untracked_name_without_match_call(monkeypatch):
    provider = _provider()
    provider.item_facts["Kristin's laptop"] = {"place": "in the truck", "condition": []}
    monkeypatch.setattr(CloudflareTurnProvider, "_request", lambda *_args: pytest.fail("unexpected match"))

    provider.apply_item_facts({"laptop": {"owner": "Kristin", "place": "on the desk"}})

    result = provider.last_item_facts_match()
    assert provider.item_facts["Kristin's laptop"]["place"] == "on the desk"
    assert provider.item_facts_match_calls == 0
    assert result["match_call"] is False
    assert result["match_raw"] is None
    assert result["match_issues"] == []
    assert result["resolutions"] == {"laptop": "Kristin's laptop"}
    assert result["engine_resolutions"] == {"laptop": "Kristin's laptop"}


def test_bare_name_still_reaches_match_call(monkeypatch):
    provider = _provider()
    provider.item_facts["Kristin's laptop"] = {"place": "in the truck", "condition": []}
    payloads = []
    monkeypatch.setattr(
        CloudflareTurnProvider,
        "_request",
        lambda _provider, payload: payloads.append(payload) or {"refers": [], "same_as": {}},
    )

    provider.apply_item_facts({"laptop": {"place": "on the desk"}})

    assert provider.item_facts_match_calls == 1
    assert "- laptop." in payloads[0]["user"]


def test_owner_naming_untracked_person_still_reaches_match_call(monkeypatch):
    provider = _provider()
    monkeypatch.setattr(
        CloudflareTurnProvider,
        "_request",
        lambda _provider, payload: {"refers": [], "same_as": {}},
    )

    provider.apply_item_facts({"laptop": {"owner": "Morgan", "place": "on the desk"}})

    assert provider.item_facts_match_calls == 1
    assert provider.last_item_facts_match()["engine_resolutions"] == {}


def test_prepare_turn_skips_match_when_all_things_are_dependencies(monkeypatch):
    provider = _provider()
    provider.item_facts = {}
    monkeypatch.setattr(CloudflareTurnProvider, "_request", lambda *_args, **_kwargs: pytest.fail("unexpected match"))
    result = provider.prepare_turn("Inspect the lantern.")
    assert result["match_call"] is False
    assert provider.item_facts_match_calls == 0
    assert provider._selected_names == provider.dependency_names()


def test_prepare_turn_match_payload_has_prompt_sections_and_no_facts(monkeypatch):
    provider = _provider()
    provider._hand_seed_names = set(provider.item_facts)
    provider.item_facts["the notebook"] = {"place": "on the desk", "condition": []}
    payloads = []
    monkeypatch.setattr(
        CloudflareTurnProvider,
        "_request",
        lambda _provider, payload: payloads.append(payload) or {"refers": [], "same_as": {"the notebook": "new"}},
    )
    result = provider.prepare_turn("Search the desk.")
    assert result["match_call"] is True
    assert provider.item_facts_match_calls == 1
    assert payloads[0]["system"] == _MATCH_SYSTEM
    assert all(marker in payloads[0]["user"] for marker in ("COMMAND:", "PLAYER CHARACTER:", "THINGS:", "NEW NAMES:"))
    assert "PLAYER CHARACTER:\n- Kristin" in payloads[0]["user"]
    assert "- the lantern. Place:" in payloads[0]["user"]
    assert "- the gate. Place:" in payloads[0]["user"]
    assert "- the notebook. Place: on the desk." in payloads[0]["user"]
    assert payloads[0]["user"].split("NEW NAMES:", 1)[1].strip() == "- (none)"


def test_same_as_tracked_name_merges_new_entry_same_turn(monkeypatch):
    provider = _provider()
    monkeypatch.setattr(
        CloudflareTurnProvider,
        "_request",
        lambda *_args: {"refers": [], "same_as": {"the old lamp": "the lantern"}},
    )
    provider.apply_item_facts(
        {"the old lamp": {"place": "by the door", "condition": ["warm"]}},
        player_input="Carry the old lamp.",
    )
    result = provider.last_item_facts_match()
    assert result["resolutions"] == {"the old lamp": "the lantern"}
    assert provider.item_facts["the lantern"] == {"place": "by the door", "condition": ["warm"]}
    assert "the old lamp" not in provider.item_facts


def test_self_mapping_adds_new_thing_same_turn(monkeypatch):
    provider = _provider()
    monkeypatch.setattr(
        CloudflareTurnProvider,
        "_request",
        lambda *_args: {"refers": [], "same_as": {"the notebook": "the notebook"}},
    )
    provider.apply_item_facts(
        {"the notebook": {"place": "on the desk", "condition": ["open"]}},
        player_input="Pick up the notebook.",
    )
    result = provider.last_item_facts_match()
    assert result["resolutions"] == {"the notebook": "new"}
    assert provider.item_facts["the notebook"] == {"place": "on the desk", "condition": ["open"]}


def test_omitted_same_as_adds_condition_only_thing_without_place(monkeypatch):
    provider = _provider()
    monkeypatch.setattr(CloudflareTurnProvider, "_request", lambda *_args: {"refers": [], "same_as": {}})
    provider.apply_item_facts(
        {"back door frame": {"condition": ["damaged"]}},
        player_input="Inspect the back door frame.",
    )
    provider._selected_names = ["back door frame"]
    assert provider.item_facts["back door frame"] == {"place": None, "condition": ["damaged"]}
    line = provider._things_block()
    assert "- back door frame. Condition: damaged." in line
    assert "Place:" not in line.split("- back door frame.", 1)[1].splitlines()[0]
    assert "None" not in line


def test_invalid_match_reply_adds_new_names_without_raising(monkeypatch):
    provider = _provider()
    monkeypatch.setattr(CloudflareTurnProvider, "_request", lambda *_args: {"oops": 1})
    provider.apply_item_facts({"the notebook": {"place": "on the desk"}}, player_input="Open the notebook.")
    result = provider.last_item_facts_match()
    assert result["resolutions"] == {"the notebook": "new"}
    assert provider.item_facts["the notebook"] == {"place": "on the desk", "condition": []}
    assert provider._held_item_facts == {}
    assert result["match_issues"] == ["invalid item_facts match reply"]


def test_match_transport_exception_adds_new_names(monkeypatch):
    provider = _provider()

    def fail(*_args):
        raise OSError("offline")

    monkeypatch.setattr(CloudflareTurnProvider, "_request", fail)
    provider.apply_item_facts({"the notebook": {"place": "on the desk"}}, player_input="Open the notebook.")
    result = provider.last_item_facts_match()
    assert result["resolutions"] == {"the notebook": "new"}
    assert provider.item_facts["the notebook"] == {"place": "on the desk", "condition": []}
    assert any("match failed: offline" in issue for issue in result["match_issues"])
    assert provider._held_item_facts == {}


def test_command_reference_adds_non_always_name_and_omits_unreferred_name(monkeypatch):
    provider = _provider()
    provider._hand_seed_names = {"the lantern"}
    provider.item_facts["the box"] = {"place": "under the bench", "condition": []}
    monkeypatch.setattr(CloudflareTurnProvider, "_request", lambda *_args: {"refers": ["the gate"], "same_as": {}})
    result = provider.prepare_turn("Open the gate.")
    assert result["match_call"] is True
    assert provider._selected_names == ["the gate"]
    assert "the box" not in provider._selected_names
    assert "the gate" in provider._things_block()
    assert "the box" not in provider._things_block()


def test_dependency_names_only_cover_reachable_dependencies():
    provider = _provider()
    provider._hand_seed_names = set()
    provider.item_facts.update(
        {
            "drawer": {"place": "in the house", "condition": []},
            "Michelle's memory card": {"place": "under the drawer", "condition": []},
            "Kristin's notebook": {"place": "in Kristin's jacket pocket", "condition": []},
            "toolbox": {"place": "in Kristin's truck", "condition": []},
            "changed thing": {"place": "in the yard", "condition": []},
            "unrelated thing": {"place": "in a shed", "condition": []},
        }
    )
    provider._changed_last_turn = {"changed thing"}
    names = provider.dependency_names()
    assert "drawer" not in names
    assert "Michelle's memory card" in names
    assert "Kristin's notebook" not in names
    assert "toolbox" not in names
    assert "changed thing" not in names
    assert "unrelated thing" not in names


def test_match_carried_name_is_ignored(monkeypatch):
    provider = _provider()
    provider._hand_seed_names = {"the lantern"}
    provider.item_facts.update(
        {
            "the notebook": {"place": "in Kristin's jacket pocket", "condition": []},
            "the toolbox": {"place": "in Kristin's truck", "condition": []},
        }
    )
    monkeypatch.setattr(
        CloudflareTurnProvider,
        "_request",
        lambda *_args: {"refers": [], "carried": ["the notebook"], "same_as": {}},
    )

    result = provider.prepare_turn("Search the desk.")

    assert result["match_call"] is True
    assert provider._selected_names == []
    assert "the notebook" not in provider._things_block()
    assert "the toolbox" not in provider._things_block()


def test_apply_skips_match_when_all_reply_names_are_tracked(monkeypatch):
    provider = _provider()
    monkeypatch.setattr(CloudflareTurnProvider, "_request", lambda *_args: pytest.fail("unexpected match"))
    provider.apply_item_facts({"the lantern": {"condition": ["warm"]}})
    assert provider.item_facts_match_calls == 0


def test_stubbed_run_records_new_change_on_same_turn(monkeypatch):
    """A new item appears in the bench turn record on the same turn."""
    calls = []

    def request(_provider, payload):
        calls.append(payload)
        if payload["system"] == _MATCH_SYSTEM:
            return {"refers": [], "same_as": {"new notebook": "new"}}
        response = {
            "segments": [{"kind": "narration", "text": "Kristin looks around the room."}],
            "selected_knowledge_ids": [],
            "item_facts": {},
        }
        if len(calls) == 3:
            response["item_facts"] = {"new notebook": {"place": "on the desk", "condition": ["open"]}}
        return response

    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://worker.example/turn")
    monkeypatch.setenv("CLOUDFLARE_WORKER_TOKEN", "test-token")
    monkeypatch.setattr(CloudflareTurnProvider, "_request", request)
    variation = load_variation(SINGLE)
    variation["_fixed_turns"] = 2
    result = core.run_scene(variation, "1A", core.scripts_for(variation, "1A")[0])
    turn_record = result["turns"][0]
    assert turn_record["item_facts_resolutions"] == {"new notebook": "new"}
    assert turn_record["item_facts_after"]["new notebook"] == {
        "place": "on the desk",
        "condition": ["open"],
    }


def test_stubbed_two_scene_run_carries_facts_and_records_transition(monkeypatch):
    calls = []

    def request(_provider, payload):
        calls.append(True)
        return {
            "segments": [{"kind": "narration", "text": "Kristin looks around the room."}],
            "selected_knowledge_ids": [],
            "item_facts": {},
        }

    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://worker.example/turn")
    monkeypatch.setenv("CLOUDFLARE_WORKER_TOKEN", "test-token")
    monkeypatch.setattr(CloudflareTurnProvider, "_request", request)
    variation = load_variation(ROOT / "bench" / "variations" / "item-facts-package-two-scene.json")
    result = core.run_scene(variation, "1A", core.scripts_for(variation, "1A")[0])
    assert result["status"] == "ok"
    assert len(result["turns"]) == 18
    assert [turn["scene_id"] for turn in result["turns"]] == ["1A"] * 12 + ["1B"] * 6
    assert result["scene_transitions"] == [
        {"from_scene": "1A", "to_scene": "1B", "after_turn": 12, "advanced_offline": True}
    ]
    assert "Michelle's phone" not in result["turns"][11]["item_facts_after"]
    assert "Kristin's laptop" not in result["turns"][12]["item_facts_before"]
    assert len(calls) == 37


def test_invalid_proposal_after_recovery_is_a_rejected_turn(monkeypatch):
    calls = []

    def request(_provider, _payload):
        calls.append(True)
        response = {
            "segments": [{"kind": "narration", "text": "Kristin looks around the room."}],
            "selected_knowledge_ids": [],
            "item_facts": {},
        }
        if len(calls) in (4, 5):
            response["things"] = []
        return response

    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://worker.example/turn")
    monkeypatch.setenv("CLOUDFLARE_WORKER_TOKEN", "test-token")
    monkeypatch.setattr(CloudflareTurnProvider, "_request", request)
    variation = load_variation(SINGLE)
    result = core.run_scene(variation, "1A", core.scripts_for(variation, "1A")[0])

    assert result["status"] == "ok"
    assert len(result["turns"]) == 12
    assert result["rejected_turns"] == []


def test_other_narration_provider_error_still_fails_fixed_turn_run(monkeypatch):
    calls = []

    def request(_provider, payload):
        calls.append(True)
        if payload["system"] != _MATCH_SYSTEM:
            raise NarrationProviderError("service unavailable", 503, "UNAVAILABLE")
        return {
            "segments": [{"kind": "narration", "text": "Kristin looks around the room."}],
            "selected_knowledge_ids": [],
            "item_facts": {},
        }

    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://worker.example/turn")
    monkeypatch.setenv("CLOUDFLARE_WORKER_TOKEN", "test-token")
    monkeypatch.setattr(CloudflareTurnProvider, "_request", request)
    variation = load_variation(SINGLE)
    result = core.run_scene(variation, "1A", core.scripts_for(variation, "1A")[0])

    assert result["status"] == "failed"
    assert result["failure_reason"].startswith("UNAVAILABLE:")


def test_fact_tracking_is_wired_into_cli_summary_and_ledger(monkeypatch, tmp_path):
    variation = json.loads(SINGLE.read_text())
    variation = core.resolve_variation(variation, SINGLE)
    record = {
        "status": "ok",
        "script": "phone-bag-door",
        "scene_id": "1A",
        "opening": "Opening.",
        "turns": [],
        "completed": True,
        "quota": None,
        "narration_turns": 0,
        "narration_requests": 1,
        "recovery_requests": 0,
        "package": variation["_package_path"],
        "entry_state": {"scene_id": "1A", "seeded_by": "none"},
        "replicate": 1,
    }
    judgment = {
        "turns": [
            {
                "facts_after_correct": "yes",
                "missed_change": "no",
                "invented_change": "no",
                "narration_contradicts_given_facts": "no",
                "dropped_true_condition": "no",
                "kept_ended_condition": "no",
                "state_as_place": "no",
                "changes": [],
            }
        ]
    }
    monkeypatch.setattr(bench_cli, "load_variation", lambda _: variation)
    monkeypatch.setattr(bench_cli, "scripts_for", lambda *_: [{"name": "phone-bag-door", "inputs": ["Look."]}])
    monkeypatch.setattr(bench_cli, "run_scene", lambda *_: record.copy())
    monkeypatch.setattr(bench_cli, "run_judges", lambda *_: {"judgments": [{"scene_id": "1A"}], "judge_calls": 1})
    monkeypatch.setattr(
        bench_cli,
        "run_continuity_judges",
        lambda *_: {
            "judgments": [
                {
                    "turns": [
                        {
                            "contradicts_stated_fact": "no",
                            "protagonist_acts_beyond_command": "no",
                            "restarts_scene": "no",
                        }
                    ]
                }
            ],
            "judge_calls": 1,
        },
    )
    monkeypatch.setattr(bench_cli, "run_fact_tracking_judges", lambda *_: {"judgments": [judgment], "judge_calls": 1})
    monkeypatch.setattr(bench_cli, "LEDGER_PATH", tmp_path / "ledger.jsonl")
    args = bench_cli.parser().parse_args(
        ["run", "--variation", str(SINGLE), "--scene", "1A", "--replicates", "1", "--out", str(tmp_path)]
    )
    assert bench_cli._run(args) == 0
    summary = json.loads((tmp_path / "summary.json").read_text())
    assert summary["fact_tracking"]["judge_calls"] == 1
    ledger = json.loads((tmp_path / "ledger.jsonl").read_text())
    assert ledger["fact_tracking"]["changes_by_cause"] == {"command": 0, "narrator": 0}
    assert ledger["spend"]["judge_calls"] == 3
