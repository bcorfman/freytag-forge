"""The absent-thing narrator rule is isolated behind an experimental flag."""

from __future__ import annotations

from pathlib import Path

import bench.core as core
from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.state import RuntimeState
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))
COMMAND = "Search the kitchen for signs of a struggle."
ABSENT_SENTENCE = (
    "If the player asks for something the SCENE does not give, Kristin looks around and finds nothing like it."
)
NAME_SENTENCE = "Do not use the player's name for that thing in your reply."
ANCHOR = "Use only what the SCENE section tells you."


def _assembled_prompt(absent_thing_rule: bool = False) -> dict[str, object]:
    provider = CloudflareTurnProvider(
        worker_url="",
        token="",
        state=RuntimeState.bootstrap(PACKAGE),
    )
    provider.absent_thing_rule = absent_thing_rule
    return provider.assemble_turn_prompt(COMMAND)


def test_absent_thing_flag_off_keeps_the_turn_prompt_unchanged() -> None:
    baseline = _assembled_prompt()
    explicitly_off = _assembled_prompt(False)

    assert explicitly_off == baseline
    rules = explicitly_off["context"]["_rules"]
    assert ABSENT_SENTENCE not in rules
    assert NAME_SENTENCE not in rules


def test_absent_thing_flag_on_inserts_both_rules_in_order() -> None:
    prompt = _assembled_prompt(True)
    rules = prompt["context"]["_rules"]
    anchor_index = rules.index(ANCHOR)

    assert rules[anchor_index + 1 : anchor_index + 3] == [ABSENT_SENTENCE, NAME_SENTENCE]
    rendered = "\n".join((str(prompt["system"]), str(prompt["context"])))
    assert rendered.count(ABSENT_SENTENCE) == 1
    assert rendered.count(NAME_SENTENCE) == 1


def test_absent_thing_flag_changes_only_the_two_rule_lines() -> None:
    off = _assembled_prompt(False)
    on = _assembled_prompt(True)
    off_context = off["context"]
    on_context = on["context"]

    assert on["system"] == off["system"]
    assert {key: value for key, value in on_context.items() if key != "_rules"} == {
        key: value for key, value in off_context.items() if key != "_rules"
    }
    assert [rule for rule in on_context["_rules"] if rule not in {ABSENT_SENTENCE, NAME_SENTENCE}] == off_context[
        "_rules"
    ]


def test_bench_absent_thing_flag_defaults_false_and_reads_variation(monkeypatch) -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    provider = CloudflareTurnProvider(worker_url="", token="", state=state)
    monkeypatch.setattr(core, "_provider_with_item_facts", lambda *_args: provider)

    assert core.provider_for(state, {}).absent_thing_rule is False
    assert core.provider_for(state, {"absent_thing_rule": True}).absent_thing_rule is True
