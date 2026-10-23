from __future__ import annotations

from pathlib import Path

from bench.core import load_variation, package_and_state, provider_for
from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.item_facts import ItemFactsProvider

ROOT = Path(__file__).resolve().parents[1]
ITEM_FACTS_VARIATION = ROOT / "bench/variations/stage7-3c-item-facts.json"
CONTROL_VARIATION = ROOT / "bench/variations/stage7-3c-control.json"


def _files(root: Path) -> dict[str, bytes]:
    return {str(path.relative_to(root)): path.read_bytes() for path in sorted(root.rglob("*")) if path.is_file()}


def test_item_facts_variation_has_control_package_without_overrides() -> None:
    item_facts = load_variation(ITEM_FACTS_VARIATION)
    control = load_variation(CONTROL_VARIATION)

    assert item_facts["overrides"] == {}
    assert item_facts["_package_hash"] == control["_package_hash"]
    assert _files(Path(item_facts["_package_path"])) == _files(Path(control["_package_path"]))


def test_provider_for_selects_item_facts_only_for_new_arm(monkeypatch) -> None:
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://worker.example/turn")
    item_facts_variation = load_variation(ITEM_FACTS_VARIATION)
    control_variation = load_variation(CONTROL_VARIATION)
    _, item_facts_state = package_and_state(item_facts_variation, "3C")
    _, control_state = package_and_state(control_variation, "3C")

    assert isinstance(provider_for(item_facts_state, item_facts_variation), ItemFactsProvider)
    assert type(provider_for(control_state, control_variation)) is CloudflareTurnProvider


def test_item_facts_apply_path_moves_kristin_to_broadcast_chamber() -> None:
    variation = load_variation(ITEM_FACTS_VARIATION)
    package, state = package_and_state(variation, "3C")
    provider = ItemFactsProvider(
        worker_url="https://worker.example/turn",
        token="",
        state=state,
        item_facts={},
        mode="single_call",
        seed_from_package=True,
    )

    provider.apply_item_facts({"Kristin": {"place": "broadcast chamber"}})

    assert provider._world().parent("kristin") == provider._world().resolve("broadcast chamber")
