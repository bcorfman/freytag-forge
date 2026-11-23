import json
import shutil
import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

import bench.core as core
from storygame.runtime.entry_snapshots import load_entry_snapshot, state_from_snapshot
from storygame.runtime.persistence import RuntimeStateSqliteStore
from storygame.runtime.world_model import world_for
from storygame.story_package.loader import load_story_package
from storygame.web_demo import create_demo_app

STORY_ROOT = Path("data/stories/continuity-initiative")
PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))
STORY_ID = PACKAGE.story_id
SECOND_SCENE_ID = PACKAGE.scenes[1].metadata.scene_id
TOKEN = "test-entry-token"


class _StubProvider:
    def opening(self) -> dict[str, object]:
        return {"segments": [{"kind": "narration", "text": "The scene opens."}]}

    def __call__(self, _player_input: str) -> dict[str, object]:
        return {"segments": [{"kind": "narration", "text": "The room shifts."}]}


def _app(monkeypatch, store_path: Path, *, channel: str = "staging", package_roots=None):
    monkeypatch.setenv("FREYTAG_ALLOW_TEST_CLOCK", "1")
    monkeypatch.setenv("FREYTAG_TEST_CLOCK_TOKEN", TOKEN)
    return create_demo_app(
        channel=channel,
        package_roots=package_roots,
        store_path=store_path,
        provider_factory=lambda _state: _StubProvider(),
    )


def _session_count(path: Path) -> int:
    with sqlite3.connect(path) as connection:
        return connection.execute("SELECT COUNT(*) FROM runtime_snapshots").fetchone()[0]


def test_canonical_default_session_matches_snapshot_and_accepts_turn(monkeypatch, tmp_path) -> None:
    store_path = tmp_path / "canonical.sqlite"
    app = _app(monkeypatch, store_path)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/session",
            json={"story_id": STORY_ID, "start_scene": SECOND_SCENE_ID},
            headers={"X-Freytag-Test-Clock-Token": TOKEN},
        )
        payload = response.json()
        actual = RuntimeStateSqliteStore(store_path).load(payload["session_id"], PACKAGE)
        turn = client.post(
            "/api/v1/turn",
            json={"session_id": payload["session_id"], "player_input": "Inspect the room."},
        )

    expected = state_from_snapshot(PACKAGE, load_entry_snapshot(STORY_ROOT, SECOND_SCENE_ID), STORY_ROOT)
    assert response.status_code == 200
    assert actual.facts == expected.facts
    assert world_for(PACKAGE, actual.facts).export_state() == world_for(PACKAGE, expected.facts).export_state()
    assert payload["state"]["scene_id"] == SECOND_SCENE_ID
    assert turn.status_code == 200


def test_thorough_seeded_session_opens_at_second_scene(monkeypatch, tmp_path) -> None:
    app = _app(monkeypatch, tmp_path / "thorough.sqlite")

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/session",
            json={"story_id": STORY_ID, "start_scene": SECOND_SCENE_ID, "start_state": "thorough"},
            headers={"X-Freytag-Test-Clock-Token": TOKEN},
        )
        payload = response.json()
        turn = client.post(
            "/api/v1/turn",
            json={"session_id": payload["session_id"], "player_input": "Inspect the room."},
        )

    assert response.status_code == 200
    assert payload["state"]["scene_id"] == SECOND_SCENE_ID
    assert payload["opening"]["scene_id"] == SECOND_SCENE_ID
    assert payload["opening"]["phase"] == PACKAGE.scenes[1].metadata.freytag_phase
    assert turn.status_code == 200


def test_bare_seeded_session_opens_at_second_scene(monkeypatch, tmp_path) -> None:
    app = _app(monkeypatch, tmp_path / "bare.sqlite")

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/session",
            json={"story_id": STORY_ID, "start_scene": SECOND_SCENE_ID, "start_state": "bare"},
            headers={"X-Freytag-Test-Clock-Token": TOKEN},
        )

    assert response.status_code == 200
    assert response.json()["state"]["scene_id"] == SECOND_SCENE_ID
    assert response.json()["opening"]["scene_id"] == SECOND_SCENE_ID


def test_seeded_entry_requires_opted_in_staging_token(monkeypatch, tmp_path) -> None:
    store_path = tmp_path / "unauthorized.sqlite"
    app = _app(monkeypatch, store_path)

    with TestClient(app) as client:
        monkeypatch.delenv("FREYTAG_ALLOW_TEST_CLOCK")
        no_opt_in = client.post(
            "/api/v1/session",
            json={"story_id": STORY_ID, "start_scene": SECOND_SCENE_ID},
            headers={"X-Freytag-Test-Clock-Token": TOKEN},
        )
        monkeypatch.setenv("FREYTAG_ALLOW_TEST_CLOCK", "1")
        no_header = client.post("/api/v1/session", json={"story_id": STORY_ID, "start_scene": SECOND_SCENE_ID})
        wrong_token = client.post(
            "/api/v1/session",
            json={"story_id": STORY_ID, "start_scene": SECOND_SCENE_ID},
            headers={"X-Freytag-Test-Clock-Token": "wrong-token"},
        )

    assert [response.status_code for response in (no_header, wrong_token, no_opt_in)] == [403, 403, 403]
    assert _session_count(store_path) == 0


def test_seeded_entry_is_forbidden_on_production(monkeypatch, tmp_path) -> None:
    store_path = tmp_path / "production.sqlite"
    app = _app(monkeypatch, store_path, channel="production")

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/session",
            json={"story_id": STORY_ID, "start_scene": SECOND_SCENE_ID},
            headers={"X-Freytag-Test-Clock-Token": TOKEN},
        )

    assert response.status_code == 403
    assert _session_count(store_path) == 0


def test_seeded_entry_validates_scene_and_state(monkeypatch, tmp_path) -> None:
    store_path = tmp_path / "invalid.sqlite"
    app = _app(monkeypatch, store_path)
    headers = {"X-Freytag-Test-Clock-Token": TOKEN}

    with TestClient(app) as client:
        unknown_scene = client.post(
            "/api/v1/session",
            json={"story_id": STORY_ID, "start_scene": "not-a-scene"},
            headers=headers,
        )
        bad_state = client.post(
            "/api/v1/session",
            json={"story_id": STORY_ID, "start_scene": SECOND_SCENE_ID, "start_state": "invalid"},
            headers=headers,
        )

    assert unknown_scene.status_code == 422
    assert bad_state.status_code == 422
    assert _session_count(store_path) == 0


def test_edited_entry_snapshot_returns_422_without_saving_session(monkeypatch, tmp_path) -> None:
    story_root = tmp_path / "continuity-initiative"
    shutil.copytree(STORY_ROOT, story_root)
    snapshot_path = story_root / "entry" / f"{SECOND_SCENE_ID}.json"
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    snapshot["source_fingerprint"] = "edited-entry"
    snapshot_path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    store_path = tmp_path / "edited.sqlite"
    app = _app(monkeypatch, store_path, package_roots=(story_root,))

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/session",
            json={"story_id": STORY_ID, "start_scene": SECOND_SCENE_ID},
            headers={"X-Freytag-Test-Clock-Token": TOKEN},
        )

    assert response.status_code == 422
    assert "source_fingerprint" in response.json()["detail"]
    assert _session_count(store_path) == 0


def test_session_without_start_scene_keeps_first_scene_response_shape(monkeypatch, tmp_path) -> None:
    app = _app(monkeypatch, tmp_path / "default.sqlite")

    with TestClient(app) as client:
        response = client.post("/api/v1/session", json={"story_id": STORY_ID})

    payload = response.json()
    first_scene = PACKAGE.scenes[0].metadata
    assert response.status_code == 200
    assert set(payload) == {"session_id", "state", "opening"}
    assert payload["state"]["scene_id"] == first_scene.scene_id
    assert payload["opening"]["scene_id"] == first_scene.scene_id
    assert payload["opening"]["phase"] == first_scene.freytag_phase
    assert set(payload["opening"]) == {"scene_id", "phase", "text", "segments"}


def test_bench_seeders_reach_the_requested_scene() -> None:
    variation_path = Path("bench/variations/seeding-test.json")
    raw = {"name": "seeding-test", "story_package": str(Path("data/stories/continuity-initiative"))}
    variation = core.resolve_variation(raw, variation_path)

    thorough = variation | {"_entry_state": "thorough"}
    bare = variation | {"_entry_state": "bare"}
    _, thorough_state = core.seeded_state_for_scene(thorough, SECOND_SCENE_ID)
    _, bare_state = core.seeded_state_for_scene(bare, SECOND_SCENE_ID)

    assert thorough_state.current_scene_id == SECOND_SCENE_ID
    assert bare_state.current_scene_id == SECOND_SCENE_ID
