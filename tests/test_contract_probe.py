import json
from pathlib import Path


def test_contract_probe_corpus_has_three_commands_per_label():
    corpus = json.loads(Path("bench/variations/contract-probe-2c.json").read_text())["commands"]
    assert [item["label"] for item in corpus].count("positive") == 4
    assert [item["label"] for item in corpus].count("near-miss") == 4
    assert [item["label"] for item in corpus].count("state-claim") == 6
    assert all(not item["command"].startswith("I ") and "do not" not in item["command"].casefold() for item in corpus)


def test_probe_commands_are_not_contract_examples():
    from storygame.story_package.loader import load_story_package

    package = load_story_package(Path("data/stories/continuity-initiative"))
    examples = {
        example.casefold()
        for item in package.knowledge.knowledge
        if item.action_contract is not None
        for example in (*item.action_contract.positive, *item.action_contract.near_miss)
    }
    corpus = json.loads(Path("bench/variations/contract-probe-2c.json").read_text())["commands"]
    assert not {item["command"].casefold() for item in corpus} & examples
