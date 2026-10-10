from fastapi.testclient import TestClient

from storygame.web_demo import create_demo_app


def test_unhandled_route_errors_are_cors_safe_and_missing_sessions_stay_404(tmp_path) -> None:
    app = create_demo_app(store_path=tmp_path / "sessions.sqlite")

    @app.get("/test-error")
    def raise_unexpected_error():
        raise RuntimeError("secret exception text")

    with TestClient(app, raise_server_exceptions=False) as client:
        error = client.get(
            "/test-error",
            headers={"Origin": "http://127.0.0.1:4173"},
        )
        missing_session = client.post(
            "/api/v1/turn",
            json={"session_id": "absent", "player_input": "Listen."},
            headers={"Origin": "http://127.0.0.1:4173"},
        )

    assert error.status_code == 500
    assert error.json() == {"detail": "internal server error"}
    assert "access-control-allow-origin" in error.headers
    assert "secret exception text" not in error.text
    assert missing_session.status_code == 404
    assert missing_session.json() == {"detail": "session does not exist"}
