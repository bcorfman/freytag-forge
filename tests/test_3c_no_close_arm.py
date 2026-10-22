from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import check_three_c_probe as checker
import three_c_probe as probe

from bench.core import load_variation, package_and_state, provider_for
from scripts.ringer.stage7.door_transport import SpendBudget
from storygame.runtime.capture import WorldCapture
from storygame.runtime.item_facts import ItemFactsProvider

ROOT = Path(__file__).resolve().parents[1]
SHIPPED_VARIATION = ROOT / "bench/variations/stage7-3c-item-facts.json"
NO_CLOSE_VARIATION = ROOT / "bench/variations/stage7-3c-no-close.json"
DELIVERY_PREFIX = "  delivery_text: "


def _files(root: Path) -> dict[str, bytes]:
    return {str(path.relative_to(root)): path.read_bytes() for path in sorted(root.rglob("*")) if path.is_file()}


def _escape_delivery_line() -> str:
    routes = Path(load_variation(SHIPPED_VARIATION)["_package_path"]) / "storylet-routes.yaml"
    return next(
        line
        for line in routes.read_text(encoding="utf-8").splitlines(keepends=True)
        if line.startswith(DELIVERY_PREFIX)
    )


def test_no_close_resolves_to_shipped_package_except_one_missing_route_line() -> None:
    shipped = load_variation(SHIPPED_VARIATION)
    no_close = load_variation(NO_CLOSE_VARIATION)
    shipped_files = _files(Path(shipped["_package_path"]))
    no_close_files = _files(Path(no_close["_package_path"]))
    assert shipped_files.keys() == no_close_files.keys()
    route = "storylet-routes.yaml"
    expected_route = shipped_files[route].replace(_escape_delivery_line().encode(), b"", 1)
    assert shipped_files[route].count(_escape_delivery_line().encode()) == 1
    assert no_close_files[route] == expected_route
    assert all(shipped_files[name] == no_close_files[name] for name in shipped_files if name != route)


def test_no_close_makes_only_escape_delivery_optional() -> None:
    shipped_package, _ = package_and_state(load_variation(SHIPPED_VARIATION), "3C")
    no_close_package, _ = package_and_state(load_variation(NO_CLOSE_VARIATION), "3C")
    shipped_event = next(
        event for event in shipped_package.storylet_routes.resolution_events if event.id == "resolution_escape"
    )
    no_close_event = next(
        event for event in no_close_package.storylet_routes.resolution_events if event.id == "resolution_escape"
    )
    assert shipped_event.delivery_text
    assert no_close_event.delivery_text is None


def test_no_close_uses_item_facts_provider_and_world_capture(monkeypatch) -> None:
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://worker.example/turn")
    shipped_variation = load_variation(SHIPPED_VARIATION)
    no_close_variation = load_variation(NO_CLOSE_VARIATION)
    _, shipped_state = package_and_state(shipped_variation, "3C")
    _, no_close_state = package_and_state(no_close_variation, "3C")
    shipped_provider = provider_for(shipped_state, shipped_variation)
    no_close_provider = provider_for(no_close_state, no_close_variation)
    assert type(no_close_provider) is type(shipped_provider) is ItemFactsProvider
    shipped_engine, shipped_capture = probe._probe_engine(
        "item-facts", shipped_state, shipped_provider, SpendBudget(1), "on", lambda _state, _questions: None
    )
    no_close_engine, no_close_capture = probe._probe_engine(
        "no-close", no_close_state, no_close_provider, SpendBudget(1), "on", lambda _state, _questions: None
    )
    assert type(no_close_capture) is type(shipped_capture) is WorldCapture
    assert type(no_close_engine.capture) is type(shipped_engine.capture) is WorldCapture


def test_no_close_dry_run_has_alternating_rows_and_postc_caps(tmp_path: Path) -> None:
    output = tmp_path / "no-close-dry"
    env = os.environ | {"PYTHONPATH": str(ROOT), "TMPDIR": "/tmp"}
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/ringer/stage7/three_c_probe.py"),
            "--n",
            "12",
            "--mode",
            "play",
            "--start",
            "postc",
            "--arms",
            "item-facts,no-close",
            "--kristin-place",
            "facility_escape",
            "--capture-item-facts",
            "--semantic",
            "on",
            "--dry-run",
            "--out",
            str(output),
        ],
        check=True,
        env=env,
    )
    assert checker.check(output, 12, "dry") == []
    plan = json.loads((output / "plan.json").read_text(encoding="utf-8"))
    assert [row["arm"] for row in plan["order"]] == ["item-facts", "no-close"] * 12
    assert plan["caps"] == probe.POSTC_CAPS[12]


def test_existing_arm_dry_run_remains_byte_stable(tmp_path: Path) -> None:
    generated = tmp_path / "generated"
    generated.mkdir()
    probe.dry_run(generated, 1, "carried", "on", ("pump", "families"), None)
    checked_in = ROOT / "bench/results/stage7-3c-carried-dry"
    for name in ("source.json", "plan.json"):
        expected = (checked_in / name).read_bytes().replace(b"/home/bcorfman/dev/freytag-forge", str(ROOT).encode())
        assert (generated / name).read_bytes() == expected
