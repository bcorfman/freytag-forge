from __future__ import annotations

from pathlib import Path

import three_c_probe as probe

from bench.core import load_variation, package_and_state, provider_for
from scripts.ringer.stage7.door_transport import SpendBudget
from storygame.runtime.capture import WorldCapture
from storygame.runtime.item_facts import ItemFactsProvider

ROOT = Path(__file__).resolve().parents[1]
SHIPPED_VARIATION = ROOT / "bench/variations/stage7-3c-item-facts.json"
FAMILIES_OFFER_VARIATION = ROOT / "bench/variations/stage7-3c-families-offer-arm.json"


def _files(root: Path) -> dict[str, bytes]:
    return {str(path.relative_to(root)): path.read_bytes() for path in sorted(root.rglob("*")) if path.is_file()}


def test_variation_loads_and_reverses_only_the_adopted_handoff_sentence() -> None:
    shipped = load_variation(SHIPPED_VARIATION)
    families_offer = load_variation(FAMILIES_OFFER_VARIATION)
    shipped_root = Path(shipped["_package_path"])
    families_offer_root = Path(families_offer["_package_path"])
    assert _files(shipped_root).keys() == _files(families_offer_root).keys()

    handoff = "handoffs.yaml"
    old = (
        b"  cue_text: Families of the missing call the broadcast chamber for word. "
        b"Kristin can answer the families with news of the captives."
    )
    new = b"  cue_text: Families of the missing call the broadcast chamber for word."
    shipped_files = _files(shipped_root)
    families_offer_files = _files(families_offer_root)
    assert shipped_files[handoff].count(old) == 1
    assert families_offer_files[handoff] == shipped_files[handoff].replace(old, new, 1)
    assert families_offer_files[handoff].count(new) == 1
    assert all(shipped_files[name] == families_offer_files[name] for name in shipped_files if name != handoff)

    package, _ = package_and_state(families_offer, "3C")
    delivery = next(item for item in package.deliveries if item.fact_id == "community_rescue_efforts_begun")
    assert delivery.cue_text == "Families of the missing call the broadcast chamber for word."


def test_families_offer_uses_item_facts_provider_and_world_capture(monkeypatch) -> None:
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://worker.example/turn")
    shipped = load_variation(SHIPPED_VARIATION)
    families_offer = load_variation(FAMILIES_OFFER_VARIATION)
    _, shipped_state = package_and_state(shipped, "3C")
    _, families_offer_state = package_and_state(families_offer, "3C")
    shipped_provider = provider_for(shipped_state, shipped)
    families_offer_provider = provider_for(families_offer_state, families_offer)
    assert type(families_offer_provider) is type(shipped_provider) is ItemFactsProvider

    shipped_engine, shipped_capture = probe._probe_engine(
        "item-facts", shipped_state, shipped_provider, SpendBudget(1), "on", lambda _state, _questions: None
    )
    families_offer_engine, families_offer_capture = probe._probe_engine(
        "families-offer",
        families_offer_state,
        families_offer_provider,
        SpendBudget(1),
        "on",
        lambda _state, _questions: None,
    )
    assert type(families_offer_capture) is type(shipped_capture) is WorldCapture
    assert type(families_offer_engine.capture) is type(shipped_engine.capture) is WorldCapture
