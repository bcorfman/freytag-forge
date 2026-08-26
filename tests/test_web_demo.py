"""Deployment-adapter contract tests."""

from fastapi.testclient import TestClient

from storygame.web_demo import create_demo_app


def test_hosted_adapter_reports_sha_bound_identity(monkeypatch) -> None:
    monkeypatch.setenv("FREYTAG_DEPLOYMENT_SHA", "a" * 40)
    app = create_demo_app(channel="staging")

    with TestClient(app) as client:
        health = client.get("/api/v1/health")
        version = client.get("/api/v1/version")

    assert health.json() == {
        "status": "ok",
        "runtime": "v2",
        "channel": "staging",
        "sha": "a" * 40,
    }
    assert version.json() == {
        "api": "v1",
        "runtime": "v2",
        "channel": "staging",
        "sha": "a" * 40,
    }
