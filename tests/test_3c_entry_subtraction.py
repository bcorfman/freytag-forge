from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from bench.core import load_variation, package_and_state
from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.facts import Fact

ROOT = Path(__file__).resolve().parents[1]
SHIPPED = ROOT / "bench/variations/stage7-3c-item-facts.json"
VARIATION = ROOT / "bench/variations/stage7-3c-entry-world-only.json"
LINE = "- Exposure and escape are both immediate under the collapsing operation."


def _probe_module():
    path = ROOT / "scripts/ringer/stage7/3c_entry_replay_probe.py"
    spec = importlib.util.spec_from_file_location("entry_replay_probe", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _prompt(variation_path: Path) -> tuple[str, str]:
    variation = load_variation(variation_path)
    package, state = package_and_state(variation, "3C")
    for fact_id in (
        "truth_no_longer_containable",
        "rebecca_captured",
        "evacuation_route_open",
        "los_angeles_facility_lost",
    ):
        state.facts.assert_fact(Fact(predicate=fact_id, subject="story", value="true"))
    provider = CloudflareTurnProvider(worker_url="", token="", state=state, prompt_variant=variation["_prompt_variant"])
    assembled = provider.assemble_turn_prompt("Continue through the maintenance tunnel to the surface.")
    return assembled["system"], provider._section_user_prompt(assembled["context"])


def test_dry_replay_writes_one_line_subtraction(tmp_path: Path) -> None:
    source = ROOT / "bench/results/stage7-3c-escape-close-smoke/rows.json"
    module = _probe_module()
    out = tmp_path / "dry"
    module.main(["--rows", str(source), "--samples", "12", "--dry", "--out", str(out)])
    control = out.joinpath("control.user.txt").read_text(encoding="utf-8")
    subtraction = out.joinpath("subtraction.user.txt").read_text(encoding="utf-8")
    assert subtraction == control.replace(LINE + "\n", "", 1)
    diff = out.joinpath("prompt.diff").read_text(encoding="utf-8")
    assert sum(line.startswith("-- ") for line in diff.splitlines()) == 1
    assert sum(line.startswith("+- ") for line in diff.splitlines()) == 0
    plan = json.loads(out.joinpath("plan.json").read_text(encoding="utf-8"))
    assert plan["call_count"] == 24
    assert plan["call_cap"] == 24
    assert {"control", "subtraction"} == set(plan["arms"])


def test_saved_a11_prompt_contains_entry_line_once() -> None:
    source = ROOT / "bench/results/stage7-3c-escape-close-smoke/rows.json"
    prompt, _, _ = _probe_module().saved_prompt(source)
    assert prompt["user"].count(LINE) == 1


def test_live_replay_requires_confirmation_and_call_cap() -> None:
    module = _probe_module()
    with pytest.raises(SystemExit):
        module.main(["--rows", "missing.json", "--samples", "1", "--out", "/tmp/out"])
    with pytest.raises(SystemExit):
        module.main(["--rows", "missing.json", "--samples", "13", "--confirm", "--out", "/tmp/out"])


def test_live_replay_records_replies_without_retry(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    source = ROOT / "bench/results/stage7-3c-escape-close-smoke/rows.json"
    module = _probe_module()

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return b'{"narration":"{\\"segments\\":[{\\"text\\":\\"Done.\\"}]}"}'

    calls = []

    def fake_urlopen(request, timeout):
        calls.append((request, timeout))
        return Response()

    monkeypatch.setattr(module, "urlopen", fake_urlopen)
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://worker.invalid")
    out = tmp_path / "live"
    module.main(["--rows", str(source), "--samples", "1", "--confirm", "--out", str(out)])
    rows = json.loads(out.joinpath("rows.json").read_text(encoding="utf-8"))
    assert len(calls) == 2
    assert [row["arm"] for row in rows] == ["control", "subtraction"]
    assert all(row["error"] is None and row["text"] for row in rows)
