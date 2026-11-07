from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

from bench.core import _record_authored_segments
from bench.judge_input import judge_turns
from storygame.runtime.item_facts import declared_axes_for_package
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))


def test_declared_axes_records_carry_axes_and_old_records_fill_them() -> None:
    state_axes = {"Kristin's laptop": {"closed": ["shut"], "open": []}}
    axes = declared_axes_for_package(
        PACKAGE,
        ["drawer", "workstation chair", "Kristin's laptop", "Michelle's phone"],
        state_axes,
    )
    assert axes["drawer"] == [["open", "closed"]]
    assert axes["workstation chair"] == [["overturned", "upright"]]
    assert axes["Kristin's laptop"] == [["closed", "open"]]
    assert "Michelle's phone" not in axes

    turn = {
        "narration": "Kristin opens the drawer and checks the phone.",
        "item_facts_before": {
            "drawer": {"place": "kitchen", "condition": ["closed", "unlocked"]},
            "Michelle's phone": {"place": "table", "condition": ["undamaged"]},
        },
        "item_facts_after": {
            "drawer": {"place": "kitchen", "condition": ["open", "unlocked"]},
            "Michelle's phone": {"place": "table", "condition": ["undamaged"]},
        },
    }
    judged = judge_turns([turn], [], PACKAGE, state_axes=state_axes)[0]
    assert judged["item_facts_axes"] == {
        "drawer": [["open", "closed"]],
    }
    assert judged["item_facts_before"]["drawer"]["condition"] == ["closed"]
    assert judged["item_facts_after"]["drawer"]["condition"] == ["open"]
    assert judged["item_facts_before"]["Michelle's phone"]["condition"] == []
    assert turn["item_facts_before"]["drawer"]["condition"] == ["closed", "unlocked"]


def test_declared_axes_strip_undeclared_conditions_from_old_records() -> None:
    turn = {
        "narration": "Open the drawer.",
        "item_facts_before": {"drawer": {"place": "kitchen", "condition": ["closed", "unlocked"]}},
        "item_facts_after": {"drawer": {"place": "kitchen", "condition": ["open", "unlocked"]}},
    }

    judged = judge_turns([turn], [], PACKAGE)[0]

    assert judged["item_facts_axes"] == {"drawer": [["open", "closed"]]}
    assert judged["item_facts_before"]["drawer"]["condition"] == ["closed"]
    assert judged["item_facts_after"]["drawer"]["condition"] == ["open"]
    assert turn["item_facts_after"]["drawer"]["condition"] == ["open", "unlocked"]


def test_judge_turns_projects_location_aliases_for_fact_places() -> None:
    turn = {
        "narration": "Kristin follows Michelle into the maintenance tunnel.",
        "item_facts_before": {"Kristin": {"place": "MAINTENANCE TUNNEL"}},
        "item_facts_after": {"Kristin": {"place": "maintenance network"}, "phone": {"place": "unknown place"}},
    }

    judged = judge_turns([turn], [], PACKAGE)[0]

    assert judged["place_names"] == {
        "MAINTENANCE TUNNEL": [
            "maintenance network",
            "maintenance route",
            "maintenance routes",
            "maintenance tunnel",
            "maintenance tunnels",
        ],
        "maintenance network": [
            "maintenance network",
            "maintenance route",
            "maintenance routes",
            "maintenance tunnel",
            "maintenance tunnels",
        ],
    }


def test_judge_turns_projects_character_place_labels_without_changing_turn() -> None:
    turn = {
        "narration": "Kristin checks the phone.",
        "item_facts_before": {
            "phone": {"place": "kRISTIN"},
            "note": {"place": "table"},
        },
        "item_facts_after": {
            "phone": {"place": "Michelle"},
            "note": {"place": "TABLE"},
        },
    }
    original = deepcopy(turn)

    judged = judge_turns([turn], [], PACKAGE)[0]

    assert judged["person_places"] == ["Michelle", "kRISTIN"]
    assert turn == original


def test_judge_turns_lists_fixed_things() -> None:
    turn = {
        "narration": "Kristin checks the service entrance beside the processing line.",
        "item_facts_before": {
            "service entrance": {"place": "service level"},
            "Transit token": {"place": "Kristin"},
        },
        "item_facts_after": {
            "service entrance": {"place": "service level"},
            "Transit token": {"place": "Kristin"},
        },
    }

    judged = judge_turns([turn], [], PACKAGE)[0]

    assert judged["fixed_things"] == ["service entrance"]


def test_judge_turns_projects_authored_text_and_reveal_visibility() -> None:
    reveal = PACKAGE.knowledge_indexes.by_id["k_sl_1a_b_r0"]
    turns = [
        {
            "turn_number": 2,
            "scene_id": "1A",
            "authored_handoff_candidate_id": reveal.id,
            "narration": f"Kristin searches beneath the drawer. {reveal.delivery_text}",
            "item_facts_before": {"Michelle's memory card": {"place": "with Kristin"}, "phone": {}},
            "item_facts_after": {"Michelle's memory card": {"place": "with Kristin"}, "phone": {}},
        },
        {
            "turn_number": 3,
            "scene_id": "1A",
            "narration": "Kristin waits.",
            "item_facts_before": {"Michelle's memory card": {"place": "with Kristin"}},
            "item_facts_after": {},
        },
    ]
    original = deepcopy(turns)

    judged = judge_turns(turns, [], PACKAGE)

    assert judged[0]["story_text"] == [reveal.delivery_text]
    assert judged[0]["story_text_provenance"] == "reconstructed"
    assert judged[0]["narrator_narration"] == "Kristin searches beneath the drawer."
    assert judged[0]["command"] == ""
    assert judged[0]["turn_text"] == [
        {"by": "narrator", "text": "Kristin searches beneath the drawer."},
        {"by": "story", "text": reveal.delivery_text},
    ]
    assert "Michelle's memory card" not in judged[0]["item_facts_before"]
    assert "Michelle's memory card" in judged[0]["item_facts_after"]
    assert judged[1]["story_text"] == []
    assert judged[1]["story_text_provenance"] == "reconstructed"
    assert judged[1]["narrator_narration"] == "Kristin waits."
    assert judged[1]["item_facts_before"] == turns[1]["item_facts_before"]
    assert "Michelle's memory card" in judged[1]["item_facts_before"]
    assert turns == original


def test_judge_turns_projects_scene_bridge_after_turn() -> None:
    bridge = PACKAGE.scenes[0].metadata.bridge_text["t_1a_1b"]
    turn = {"turn_number": 13, "scene_id": "1A", "narration": bridge, "item_facts_before": {}}

    judged = judge_turns(
        [turn],
        [{"from_scene": "1A", "to_scene": "1B", "after_turn": 13, "advanced_offline": False}],
        PACKAGE,
    )

    assert judged[0]["story_text"] == [bridge]
    assert judged[0]["narrator_narration"] == ""
    assert turn == {"turn_number": 13, "scene_id": "1A", "narration": bridge, "item_facts_before": {}}


def test_judge_turns_strips_delivery_then_bridge_in_reverse_order() -> None:
    reveal = PACKAGE.knowledge_indexes.by_id["k_sl_1a_b_r0"]
    bridge = PACKAGE.scenes[0].metadata.bridge_text["t_1a_1b"]
    turn = {
        "turn_number": 13,
        "scene_id": "1A",
        "authored_handoff_candidate_id": reveal.id,
        "narration": f"Kristin starts the truck. {reveal.delivery_text} {bridge}",
        "item_facts_before": {},
    }

    judged = judge_turns(
        [turn],
        [{"from_scene": "1A", "to_scene": "1B", "after_turn": 13, "advanced_offline": False}],
        PACKAGE,
    )

    assert judged[0]["story_text"] == [reveal.delivery_text, bridge]
    assert judged[0]["narrator_narration"] == "Kristin starts the truck."


def test_judge_turns_keeps_narration_when_authored_text_is_not_a_suffix() -> None:
    reveal = PACKAGE.knowledge_indexes.by_id["k_sl_1a_b_r0"]
    narration = f"{reveal.delivery_text} Kristin searches beneath the drawer."
    judged = judge_turns(
        [{"authored_handoff_candidate_id": reveal.id, "narration": narration}],
        [],
        PACKAGE,
    )

    assert judged[0]["narrator_narration"] == narration


def test_recorded_pocketing_delivery_is_story_text() -> None:
    pocketing = "It is Michelle's memory card, and she pockets it."
    judged = judge_turns(
        [
            {
                "narration": f"Kristin searches beneath the drawer. {pocketing}",
                "authored_segments": [{"kind": "handoff", "text": pocketing}],
            }
        ],
        [],
        PACKAGE,
    )[0]

    assert judged["story_text"] == [pocketing]
    assert judged["story_text_provenance"] == "recorded"
    assert judged["narrator_narration"] == "Kristin searches beneath the drawer."


def test_recorded_delivery_does_not_remove_a_repeated_prior_signal() -> None:
    signal = "The prior-turn signal repeats here."
    delivery = "The current authored delivery is here."
    judged = judge_turns(
        [
            {
                "narration": signal,
                "authored_segments": [{"kind": "handoff", "text": signal}],
            },
            {
                "narration": f"{signal} {delivery}",
                "authored_segments": [{"kind": "handoff", "text": delivery}],
            },
        ],
        [],
        PACKAGE,
    )[1]

    assert judged["story_text"] == [delivery]
    assert judged["narrator_narration"] == signal


def test_legacy_ordinary_narration_is_reconstructed_unchanged() -> None:
    narration = "Kristin approaches and spots the open doorway."
    judged = judge_turns([{"narration": narration}], [], PACKAGE)[0]

    assert judged["story_text"] == []
    assert judged["story_text_provenance"] == "reconstructed"
    assert judged["narrator_narration"] == narration


def test_legacy_second_reunion_paragraph_stays_narrator_text() -> None:
    narration = "The reunion is complete. Kristin and Michelle share another emotional paragraph."
    judged = judge_turns([{"narration": narration}], [], PACKAGE)[0]

    assert judged["story_text"] == []
    assert judged["narrator_narration"] == narration


def test_legacy_incorrect_shared_memory_stays_narrator_text() -> None:
    narration = "Kristin remembers a shared memory that is not true."
    judged = judge_turns([{"narration": narration}], [], PACKAGE)[0]

    assert judged["story_text"] == []
    assert judged["narrator_narration"] == narration


def test_recorded_arrival_and_custody_segments_are_story_text() -> None:
    bridge = "The authored arrival bridge is shown."
    entry = "The authored final custody entry is shown."
    judged = judge_turns(
        [
            {
                "narration": "Kristin arrives at the destination.",
                "authored_segments": [
                    {"kind": "bridge", "text": bridge},
                    {"kind": "entry", "text": entry},
                ],
            }
        ],
        [],
        PACKAGE,
    )[0]

    assert judged["story_text"] == [bridge, entry]
    assert judged["narrator_narration"] == "Kristin arrives at the destination."
    assert judged["turn_text"] == [
        {"by": "narrator", "text": "Kristin arrives at the destination."},
        {"by": "story", "text": bridge},
        {"by": "story", "text": entry},
    ]


def test_recorded_segments_use_the_delivery_variant_that_was_appended() -> None:
    variant = "The authored variant delivery is shown."
    base = "The authored base delivery is not shown."
    bridge = "The authored bridge is shown."
    segments = (
        SimpleNamespace(text="Kristin searches the drawer."),
        SimpleNamespace(text=variant),
        SimpleNamespace(text=bridge),
    )

    assert _record_authored_segments(
        segments,
        handoff=SimpleNamespace(delivery_text=variant),
        cue_texts=(),
        complication_text=None,
        complication_verbatim=False,
        transition_segments=(("bridge", bridge), ("entry", "An entry not appended.")),
    ) == [
        {"kind": "handoff", "text": variant},
        {"kind": "bridge", "text": bridge},
    ]
    assert base not in {
        segment["text"]
        for segment in _record_authored_segments(
            segments,
            handoff=SimpleNamespace(delivery_text=base),
            cue_texts=(),
            complication_text=None,
            complication_verbatim=False,
            transition_segments=(),
        )
    }


def test_recorded_segments_use_the_shown_cue_and_verbatim_complication() -> None:
    cue = "The escalation cue is shown."
    complication = "The authored complication is shown."
    segments = tuple(SimpleNamespace(text=text) for text in ("Narrator.", cue, complication))

    assert _record_authored_segments(
        segments,
        handoff=None,
        cue_texts=("The base cue is not shown.", cue),
        complication_text=complication,
        complication_verbatim=True,
        transition_segments=(),
    ) == [
        {"kind": "cue", "text": cue},
        {"kind": "complication", "text": complication},
    ]


def test_judge_turns_projects_typed_command_and_engine_prefix() -> None:
    turns = [
        {
            "player_input": "The engine walks to the kitchen. Search the workstation.",
            "typed_input": "Search the workstation.",
            "narration": "Kristin searches the workstation.",
        },
        {"player_input": "Search the workstation.", "narration": "Kristin searches it."},
    ]

    judged = judge_turns(turns, [], PACKAGE)

    assert judged[0]["command_typed"] == "Search the workstation."
    assert judged[0]["command"] == "Search the workstation."
    assert judged[0]["just_before"] == "The engine walks to the kitchen."
    assert judged[0]["turn_text"] == [
        {"by": "game", "text": "The engine walks to the kitchen."},
        {"by": "narrator", "text": "Kristin searches the workstation."},
    ]
    assert judged[1]["command_typed"] == "Search the workstation."
    assert judged[1]["command"] == "Search the workstation."
    assert judged[1]["just_before"] == ""
    assert judged[1]["turn_text"] == [{"by": "narrator", "text": "Kristin searches it."}]
    assert "command_typed" not in turns[0]


def test_judge_turns_projects_nested_place_contents_and_recorded_override() -> None:
    turn = {
        "scene_id": "1A",
        "narration": "Kristin records the workstation.",
        "item_facts_after": {"workstation": {"place": "outside the house"}},
    }

    contents = judge_turns([turn], [], PACKAGE)[0]["place_contents"]

    assert "workstation" not in contents["kitchen"]
    assert "back door" in contents["kitchen"]
    assert "drawer" not in contents["kitchen"]
    assert "workstation" in contents["outside the house"]
    assert "drawer" in contents["outside the house"]
    assert "Michelle's memory card" not in contents["kitchen"]
    assert turn["item_facts_after"]["workstation"]["place"] == "outside the house"


def test_place_contents_resolves_tracked_names_and_nested_recorded_places() -> None:
    turn = {
        "scene_id": "1A",
        "narration": "Kristin checks the phone and moves the truck.",
        "item_facts_names": {"Kristin": ["Kristin Schweitzer", "Kristin's pocket"]},
        "item_facts_after": {
            "Michelle's phone": {"place": "Kristin"},
            "Kristin": {"place": "kitchen"},
            "note": {"place": "drawer"},
            "Kristin's truck": {"place": "Los Angeles park"},
        },
    }

    contents = judge_turns([turn], [], PACKAGE)[0]["place_contents"]

    assert "Michelle's phone" in contents["Kristin"]
    assert "Michelle's phone" in contents["kitchen"]
    assert "Michelle's phone" in contents["Michelle's house"]
    assert "Kristin" in contents["kitchen"]
    assert "Kristin" in contents["Michelle's house"]
    assert "Kristin Schweitzer" not in contents["kitchen"]
    assert "note" in contents["kitchen"]
    assert "Kristin's laptop" in contents["Los Angeles park"]


def test_place_contents_tracked_character_place_overrides_authored_item_place() -> None:
    turn = {
        "scene_id": "1A",
        "narration": "Kristin checks Michelle's phone.",
        "item_facts_after": {
            "Kristin": {"place": "Kristin's truck"},
            "Michelle's phone": {"place": "Kristin"},
        },
    }

    contents = judge_turns([turn], [], PACKAGE)[0]["place_contents"]

    assert "Michelle's phone" in contents["Kristin's truck"]
    assert "Michelle's phone" not in contents["kitchen"]
