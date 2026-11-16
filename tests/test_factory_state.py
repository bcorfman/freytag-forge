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
