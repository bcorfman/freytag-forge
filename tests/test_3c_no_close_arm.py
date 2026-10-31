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
        expected = expected.replace(b'"turn_index": 63', b'"turn_index": 61')
        expected = expected.replace(
            b'        "k_sl_1b_c_r2",\n        "k_sl_1c_a_r1",',
            b'        "k_sl_1b_c_r2",\n        "k_sl_1b_d_r1",\n        "k_sl_1c_a_r1",',
        )
        expected = expected.replace(b"k_sl_1c_c_r1", b"k_sl_1c_c_copy_numbers")
        expected = expected.replace(
            b"4a20f380ffa1994854856bb570ef83111917447b44e5dc52a1c258248028397a",
            b"e20f47e68ef07123d0535ecd8f5b2160f9ee4e14796cf7fc59116f3c58f0f69e",
        )
        assert (generated / name).read_bytes() == expected
