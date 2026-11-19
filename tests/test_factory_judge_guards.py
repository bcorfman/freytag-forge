import json
from pathlib import Path

import pytest

import factory.judges.agreement as agreement
import factory.judges.lock as lock
from factory.judges.agreement import Decision, MonitorState, Pair, disagreement_rate, evaluate, select_slice, stricter


def _write(path: Path, text: str = "content") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_lock_compute_write_and_check_differences(tmp_path: Path) -> None:
    _write(tmp_path / "bench" / "one-judge.mjs", "one")
    _write(tmp_path / "bench" / "two-judge.mjs", "two")
    patterns = ("bench/*-judge.mjs",)
    expected = lock.compute(tmp_path, patterns)
    assert list(expected) == ["bench/one-judge.mjs", "bench/two-judge.mjs"]
    assert lock.write(tmp_path, "state/lock.json", patterns) == expected
    assert lock.check(tmp_path, "state/lock.json", patterns) == []

    _write(tmp_path / "bench" / "one-judge.mjs", "changed")
    (tmp_path / "bench" / "two-judge.mjs").unlink()
    _write(tmp_path / "bench" / "three-judge.mjs", "three")
    assert lock.check(tmp_path, "state/lock.json", patterns) == [
        "changed bench/one-judge.mjs",
        "missing bench/two-judge.mjs",
        "new bench/three-judge.mjs",
    ]


def test_lock_missing_and_outside_pattern(tmp_path: Path) -> None:
    root = tmp_path / "root"
    outside = tmp_path / "outside-judge.mjs"
    _write(outside, "outside")
    assert lock.compute(root, ("../outside-judge.mjs",)) == {}
    with pytest.raises(FileNotFoundError):
        lock.check(root, "missing.json", ("*.txt",))


def test_lock_cli_exit_codes(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _write(tmp_path / "judge.mjs", "v1")
    args = ["write", "--root", str(tmp_path), "--lock", "lock.json"]
    assert lock.main(args) == 0
    assert capsys.readouterr().out == "locked 0 files\n"

    _write(tmp_path / "judge.mjs", "v2")
    assert lock.main(["check", "--root", str(tmp_path), "--lock", "lock.json"]) == 0
    assert capsys.readouterr().out == "ok\n"

    _write(tmp_path / "bench" / "one-judge.mjs", "v1")
    lock.write(tmp_path, "lock.json", ("bench/*-judge.mjs",))
    _write(tmp_path / "bench" / "one-judge.mjs", "v2")
    assert lock.main(["check", "--root", str(tmp_path), "--lock", "lock.json"]) == 1
    assert capsys.readouterr().out == "changed bench/one-judge.mjs\n"
    assert lock.main(["check", "--root", str(tmp_path), "--lock", "gone.json"]) == 2
    assert capsys.readouterr().err.startswith("lock file not found:")


def test_slice_is_deterministic_order_independent_and_bounded() -> None:
    ids = [f"item-{index}" for index in range(100)]
    selected = select_slice(ids, fraction=0.1, salt="salt", minimum=20)
    assert selected == select_slice(ids, fraction=0.1, salt="salt", minimum=20)
    reordered = list(reversed(ids))
    assert set(selected) == set(select_slice(reordered, fraction=0.1, salt="salt", minimum=20))
    assert len(selected) == 20
    assert len(select_slice(ids[:3], fraction=0.1, minimum=20)) == 3
    assert len(select_slice(ids, fraction=0.01, minimum=7)) == 7


def test_slice_rejects_bad_fraction() -> None:
    for fraction in (0, -0.1, 1.1):
        with pytest.raises(ValueError):
            select_slice(["one"], fraction=fraction)


def test_agreement_rate_and_decision_boundaries() -> None:
    assert disagreement_rate([]) == 0.0
    assert disagreement_rate([Pair("one", True, False), Pair("two", True, True)]) == 0.5
    exact_noise = [Pair(str(index), index < 3, False) for index in range(100)]
    assert evaluate(exact_noise).status == "ok"
    four_disagreements = [Pair(str(index), index < 4, False) for index in range(100)]
    assert evaluate(four_disagreements).status == "paused"
    assert evaluate([Pair(str(index), True, True) for index in range(19)]).status == "insufficient"


def test_stricter_truth_table() -> None:
    assert [stricter(primary, secondary) for primary in (False, True) for secondary in (False, True)] == [
        False,
        False,
        False,
        True,
    ]


def test_monitor_state_persists_pause_until_clear(tmp_path: Path) -> None:
    path = tmp_path / "state" / "monitor.json"
    state = MonitorState(path)
    paused = Decision("paused", 0.04, 20, True)
    state.record("jev", paused)
    assert state.is_paused("jev")
    assert MonitorState(path).get("jev") == {"paused": True, "last_rate": 0.04, "pairs": 20}

    MonitorState(path).record("jev", Decision("ok", 0.01, 30, False))
    retained = MonitorState(path)
    assert retained.is_paused("jev")
    assert retained.effective("jev", True, False) is False
    assert retained.effective("jev", True, True) is True
    retained.clear("jev")
    assert MonitorState(path).is_paused("jev") is False
    assert MonitorState(path).effective("jev", True, False) is True


def test_agreement_cli_records_state(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    pairs_path = tmp_path / "pairs.json"
    state_path = tmp_path / "monitor.json"
    pairs_path.write_text(
        json.dumps([{"id": str(index), "primary": index > 3, "secondary": False} for index in range(20)]),
        encoding="utf-8",
    )
    assert agreement.main(["--pairs", str(pairs_path), "--judge", "jev", "--state", str(state_path)]) == 1
    assert capsys.readouterr().out == "jev: paused 80.00% over 20 pairs\n"
    assert json.loads(state_path.read_text(encoding="utf-8"))["jev"]["paused"] is True

    assert (
        agreement.main(["--pairs", str(tmp_path / "missing.json"), "--judge", "jev", "--state", str(state_path)]) == 2
    )
    assert capsys.readouterr().err.startswith("could not read pairs file:")
