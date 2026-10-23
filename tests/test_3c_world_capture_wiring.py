from __future__ import annotations

import sys
from pathlib import Path

import pytest

STAGE7 = Path(__file__).resolve().parents[1] / "scripts" / "ringer" / "stage7"
sys.path.insert(0, str(STAGE7))

import check_three_c_probe as checker  # noqa: E402
import three_c_probe as probe  # noqa: E402

from bench.core import load_variation, package_and_state  # noqa: E402
from scripts.ringer.stage7.door_transport import SpendBudget  # noqa: E402
from storygame.runtime.cloudflare import CloudflareTurnProvider  # noqa: E402
from storygame.runtime.item_facts import ItemFactsProvider  # noqa: E402
from storygame.runtime.world_model import world_for  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
ITEM_FACTS_VARIATION = ROOT / "bench/variations/stage7-3c-item-facts.json"


def _item_facts_engine(fake_ask, monkeypatch):
    variation = load_variation(ITEM_FACTS_VARIATION)
    package, state = package_and_state(variation, "3C")
    probe.assert_3c_entry_facts(state)
    probe.apply_postc_prefix(package, state, "facility_escape")
    provider = ItemFactsProvider(
        worker_url="https://worker.example/turn",
        token="",
        state=state,
        item_facts={},
        mode="single_call",
        seed_from_package=True,
        held_by=True,
    )
    monkeypatch.setattr(
        CloudflareTurnProvider,
        "_request",
        lambda _provider, _payload: {
            "segments": [{"kind": "narration", "text": "The broadcast chamber waits."}],
            "item_facts": {"Kristin": {"place": "broadcast chamber"}},
        },
    )
    budget = SpendBudget(80, cloudflare_limit=80, player_limit=40)
    engine, capture = probe._probe_engine("item-facts", state, provider, budget, "on", fake_ask)
    return engine, capture, state, budget


def test_item_facts_engine_applies_narrator_place_with_world_capture(monkeypatch):
    engine, capture, state, _budget = _item_facts_engine(lambda _state, _questions: None, monkeypatch)

    engine.turn("Follow Michelle and the captives through the surface gates.")

    assert capture is not None
    assert world_for(state.package, state.facts).parent("kristin") == world_for(state.package, state.facts).resolve(
        "broadcast chamber"
    )
    assert isinstance(state.last_turn_delivery.capture_steps, tuple)


def test_every_capture_ask_is_counted_and_cap_is_checked_before_send():
    calls: list[int] = []
    budget = SpendBudget(3, cloudflare_limit=3, player_limit=0)
    ask = probe._counted_capture_ask(lambda _state, _questions: calls.append(1) or None, budget)

    for _ in range(3):
        ask({}, {})

    assert len(calls) == 3
    assert budget.cloudflare_requests == 3
    assert all(event["detail"] == "jev_capture" for event in budget.events)

    capped_calls: list[int] = []
    capped = SpendBudget(1, cloudflare_limit=1, player_limit=0)
    capped_ask = probe._counted_capture_ask(lambda _state, _questions: capped_calls.append(1), capped)
    capped_ask({}, {})
    with pytest.raises(RuntimeError, match="cloudflare request cap exhausted"):
        capped_ask({}, {})
    assert capped_calls == [1]
    assert capped.cloudflare_requests == 1


def test_item_facts_dry_run_marks_world_capture_without_creating_jev_client(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(
        probe.JevClient,
        "from_environment",
        lambda: (_ for _ in ()).throw(AssertionError("dry run created JevClient")),
    )

    output = tmp_path / "item-facts"
    output.mkdir()
    probe.dry_run(
        output,
        1,
        "postc",
        "on",
        ("item-facts",),
        "Follow Michelle and the captives through the surface gates.",
        "facility_escape",
        True,
    )

    assert checker.check(output, 1, "dry") == []
