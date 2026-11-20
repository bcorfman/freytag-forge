from datetime import UTC, datetime, timedelta

from factory.state import FactoryState

NOW = datetime(2026, 11, 15, 12, 0, tzinfo=UTC)


def test_state_reload_keeps_lanes_done_keys_and_breaker(tmp_path) -> None:
    path = tmp_path / "state.json"
    state = FactoryState.load(path)
    state.started_at = NOW.isoformat()
    state.sleep_lane("luna", NOW + timedelta(minutes=10))
    assert state.mark_once("merge:scene-1") is True
    state.trip_breaker("three repeated failures", NOW)

    reloaded = FactoryState.load(path)
    assert reloaded.run_id == state.run_id
    assert reloaded.started_at == NOW.isoformat()
    assert reloaded.lanes == {"luna": (NOW + timedelta(minutes=10)).isoformat()}
    assert reloaded.limited_since == {"luna": (NOW + timedelta(minutes=10)).isoformat()}
    assert reloaded.done_keys == ["merge:scene-1"]
    assert reloaded.is_tripped() is True
    assert reloaded.breaker_reason() == "three repeated failures"


def test_mark_once_persists_and_is_idempotent(tmp_path) -> None:
    path = tmp_path / "state.json"
    state = FactoryState.load(path)
    assert state.mark_once("deploy:staging") is True
    assert FactoryState.load(path).mark_once("deploy:staging") is False
    assert FactoryState.load(path).done_keys == ["deploy:staging"]


def test_lane_ready_clears_expired_entry(tmp_path) -> None:
    path = tmp_path / "state.json"
    state = FactoryState.load(path)
    state.sleep_lane("sonnet", NOW)
    assert state.lane_ready("sonnet", NOW) is True
    assert state.lanes == {}
    assert FactoryState.load(path).lanes == {}


def test_lane_ready_and_sleeping_lanes_keep_future_entries(tmp_path) -> None:
    path = tmp_path / "state.json"
    state = FactoryState.load(path)
    until = NOW + timedelta(minutes=10)
    state.sleep_lane("opus", until)
    assert state.lane_ready("opus", NOW) is False
    assert state.lane_ready("missing", NOW) is True
    assert state.sleeping_lanes(NOW) == {"opus": until.isoformat()}


def test_limited_since_is_recorded_once(tmp_path) -> None:
    state = FactoryState.load(tmp_path / "state.json")
    first = NOW - timedelta(hours=2)
    later = NOW + timedelta(hours=1)
    state.sleep_lane("codex", NOW + timedelta(hours=3), since=first)
    state.sleep_lane("codex", later, since=later)

    assert state.limited_since == {"codex": first.isoformat()}
    assert state.lanes == {"codex": later.isoformat()}


def test_lane_succeeded_clears_lane_and_limit_timestamp(tmp_path) -> None:
    state = FactoryState.load(tmp_path / "state.json")
    state.sleep_lane("codex", NOW + timedelta(hours=1), since=NOW)

    state.lane_succeeded("codex")

    assert state.lanes == {}
    assert state.limited_since == {}
    reloaded = FactoryState.load(tmp_path / "state.json")
    assert reloaded.lanes == {}
    assert reloaded.limited_since == {}


def test_wake_clears_lane_but_keeps_limit_timestamp(tmp_path) -> None:
    state = FactoryState.load(tmp_path / "state.json")
    state.sleep_lane("codex", NOW + timedelta(hours=1), since=NOW - timedelta(hours=1))

    assert state.wake("codex") is True
    assert state.wake("codex") is False
    assert state.lanes == {}
    assert state.limited_since == {"codex": (NOW - timedelta(hours=1)).isoformat()}


def test_old_state_without_limited_since_loads_empty(tmp_path) -> None:
    path = tmp_path / "state.json"
    path.write_text(
        '{"run_id":"old","started_at":null,"lanes":{},"done_keys":[],'
        '"breaker":{"tripped":false,"reason":null,"at":null}}\n',
        encoding="utf-8",
    )

    assert FactoryState.load(path).limited_since == {}
