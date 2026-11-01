from __future__ import annotations

from pathlib import Path

import pytest
import three_c_probe as probe

from bench.core import load_variation

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


@pytest.mark.nightly
def test_existing_arm_dry_run_remains_byte_stable(tmp_path: Path) -> None:
    generated = tmp_path / "generated"
    generated.mkdir()
    probe.dry_run(generated, 1, "carried", "on", ("pump", "families"), None)
    checked_in = ROOT / "bench/results/stage7-3c-carried-dry"
    for name in ("source.json", "plan.json"):
        expected = (checked_in / name).read_bytes().replace(b"/home/bcorfman/dev/freytag-forge", str(ROOT).encode())
        assert (generated / name).read_bytes() == expected
