from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from scripts.ringer.environment_narration import hidden_bench_matcher_probe as probe
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))


class _FakeClient:
    constructions = 0
    calls = 0
    fail_at: int | None = None

    def __init__(self) -> None:
        type(self).constructions += 1
        self.request_count = 0
        self.last_status = None

    @classmethod
    def from_environment(cls):
        return cls()

    def ask(self, _state: object, questions: object) -> dict[str, object] | None:
        type(self).calls += 1
        self.request_count += 1
        if self.fail_at == type(self).calls:
            self.last_status = 429
            return None
        return {candidate_id: {"noul": 0.0} for candidate_id in questions}


def _packages() -> dict[str, object]:
    baseline = deepcopy(PACKAGE)
    blocked = {probe.DISCOVERY, probe.POINTER}
    baseline_catalog = baseline.knowledge.model_copy(
        update={"knowledge": tuple(item for item in baseline.knowledge.knowledge if item.id not in blocked)}
    )
    baseline_indexes = baseline.knowledge_indexes.model_copy(
        update={
            "by_id": {key: value for key, value in baseline.knowledge_indexes.by_id.items() if key not in blocked},
            "scene_to_candidates": {
                scene: tuple(item for item in candidate_ids if item not in blocked)
                for scene, candidate_ids in baseline.knowledge_indexes.scene_to_candidates.items()
            },
        }
    )
    baseline = baseline.model_copy(update={"knowledge": baseline_catalog, "knowledge_indexes": baseline_indexes})
    return {"P1": PACKAGE, "P0": baseline}


def test_shortlists_use_projection_and_head_package_has_no_new_candidates() -> None:
    packages = _packages()
    p1_state = probe._package_state(packages["P1"])
    provider = probe.CloudflareTurnProvider(worker_url="", token="", state=p1_state, semantic_ask=lambda *_: {})
    provider.last_projection = provider.projector.project(p1_state, "player", "Look under the park bench.")
    shortlist = probe._shortlist(provider)
    assert probe.DISCOVERY in shortlist
    assert probe.POINTER in shortlist
    assert not {"k_sl_1b_a_r1", "k_sl_1b_a_r2", "k_sl_1b_b_r1"}.intersection(shortlist)

    p0_state = probe._package_state(packages["P0"])
    p0 = probe.CloudflareTurnProvider(worker_url="", token="", state=p0_state, semantic_ask=lambda *_: {})
    p0.last_projection = p0.projector.project(p0_state, "player", "Look under the park bench.")
    assert probe.DISCOVERY not in probe._shortlist(p0)
    assert probe.POINTER not in probe._shortlist(p0)


def test_dry_measurement_has_120_evaluations_and_fresh_provider_each_time(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    packages = _packages()
    _FakeClient.constructions = 0
    _FakeClient.calls = 0
    original_provider = probe.CloudflareTurnProvider
    provider_constructions = 0

    class _CountingProvider(original_provider):
        def __init__(self, **kwargs):
            nonlocal provider_constructions
            provider_constructions += 1
            super().__init__(**kwargs)

    monkeypatch.setattr(probe, "CloudflareTurnProvider", _CountingProvider)
    rows = []
    with probe._semantic_reveal_enabled():
        for item in probe._planned():
            row, stop = probe._evaluate(packages[item["arm"]], item, _FakeClient)
            rows.append(row)
            assert stop is None
    assert len(rows) == 120
    assert _FakeClient.calls == 120
    assert _FakeClient.constructions == 120
    assert provider_constructions == 120
    assert all(row["http_call_count"] == 1 for row in rows)


def test_dry_run_refuses_an_over_budget_plan(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    packages = _packages()
    monkeypatch.setattr(probe, "_load_packages", lambda: packages)
    result = probe.main(["--dry-run", "--max-calls", "119", "--max-usd", "0.02"])
    assert result == 1
    assert "planned HTTP calls: 120" in capsys.readouterr().out


def test_run_requires_confirmation_and_credentials(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("CLOUDFLARE_WORKER_URL", raising=False)
    monkeypatch.delenv("CLOUDFLARE_WORKER_TOKEN", raising=False)
    assert probe.main(["--run", "--out", str(tmp_path / "rows.json")]) == 1
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "http://127.0.0.1:1")
    assert probe.main(["--run", "--confirm", "--out", str(tmp_path / "rows.json")]) == 1


def test_429_stops_after_the_failing_row(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _FakeClient.constructions = 0
    _FakeClient.calls = 0
    _FakeClient.fail_at = 4
    packages = _packages()
    output = tmp_path / "rows.json"
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "http://worker.example")
    monkeypatch.setenv("CLOUDFLARE_WORKER_TOKEN", "test-token")
    monkeypatch.setattr(probe, "_load_packages", lambda: packages)
    monkeypatch.setattr(probe, "JevClient", _FakeClient)
    try:
        assert probe.main(["--run", "--confirm", "--out", str(output)]) == 0
    finally:
        _FakeClient.fail_at = None
    document = json.loads(output.read_text())
    assert len(document["rows"]) == 4
    assert document["stop_reason"] == "http_429"
    assert _FakeClient.constructions == 4


def _row(arm: str, input_id: str, matched: list[str], *, usable: bool = True) -> dict[str, object]:
    return {
        "arm": arm,
        "input_id": input_id,
        "matched_ids": matched,
        "usable": usable,
        "error": None if usable else "unusable",
    }


def _complete_rows() -> list[dict[str, object]]:
    rows = []
    for arm in probe.ARMS:
        for input_id, _command in probe.INPUTS:
            for _sample in range(probe.SAMPLES):
                selected = []
                if arm == "P1" and input_id in {"u1", "u2"}:
                    selected = [probe.DISCOVERY]
                rows.append(_row(arm, input_id, selected))
    return rows


@pytest.mark.parametrize(
    ("gate", "mutator"),
    (
        (
            "M1",
            lambda rows: (
                rows.__setitem__(0, _row("P1", "u1", [])),
                rows.__setitem__(1, _row("P1", "u1", [])),
            ),
        ),
        (
            "M2",
            lambda rows: (
                rows.__setitem__(0, _row("P1", "u1", [probe.POINTER])),
                rows.__setitem__(1, _row("P1", "u1", [probe.POINTER])),
            ),
        ),
        ("M3", lambda rows: rows.__setitem__(20, _row("P1", "n1", [probe.DISCOVERY]))),
        ("M4", lambda rows: rows.__setitem__(40, _row("P1", "n3", [probe.POINTER]))),
    ),
)
def test_report_fails_each_gate_when_its_requirement_is_broken(tmp_path: Path, gate: str, mutator) -> None:
    rows = _complete_rows()
    mutator(rows)
    rows_path = tmp_path / f"{gate}.json"
    report_path = tmp_path / f"{gate}.md"
    rows_path.write_text(json.dumps({"rows": rows, "stop_reason": None}))
    assert probe.main(["--report", "--rows", str(rows_path), "--out", str(report_path)]) == 1
    assert f"- {gate}: FAIL" in report_path.read_text()


def test_report_passes_complete_hand_built_rows_and_fails_incomplete(tmp_path: Path) -> None:
    rows = _complete_rows()
    rows_path = tmp_path / "rows.json"
    report_path = tmp_path / "report.md"
    rows_path.write_text(json.dumps({"rows": rows, "stop_reason": None}))
    assert probe.main(["--report", "--rows", str(rows_path), "--out", str(report_path)]) == 0
    text = report_path.read_text()
    assert "u1: D selected 10/10" in text
    assert "n1: E selected 0/10" in text
    rows_path.write_text(json.dumps({"rows": rows[:-1], "stop_reason": "incomplete"}))
    assert probe.main(["--report", "--rows", str(rows_path), "--out", str(report_path)]) == 1
