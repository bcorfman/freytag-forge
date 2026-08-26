"""Hosted deployment identity endpoints for the current scene runtime.

The player adapter is rebuilt in later runtime phases.  Keep this module small:
Railway needs an importable ASGI application now, while gameplay remains owned by
the validated, story-agnostic runtime rather than by a deployment fallback.
"""

from __future__ import annotations

from os import getenv

from fastapi import FastAPI


def _deployment_sha() -> str:
    """Return the immutable deploy identity supplied by Railway or CI."""
    return getenv("FREYTAG_DEPLOYMENT_SHA", "").strip() or getenv("RAILWAY_GIT_COMMIT_SHA", "").strip() or "unknown"


def create_demo_app(*, channel: str | None = None) -> FastAPI:
    """Build the Railway-facing adapter without reintroducing the retired V2 engine."""
    resolved_channel = channel or getenv("FREYTAG_DEPLOYMENT_CHANNEL", "unknown").strip() or "unknown"
    app = FastAPI(title="Freytag Forge", version="2")

    @app.get("/api/v1/health")
    def health() -> dict[str, str]:
        return {
            "status": "ok",
            "runtime": "v2",
            "channel": resolved_channel,
            "sha": _deployment_sha(),
        }

    @app.get("/api/v1/version")
    def version() -> dict[str, str]:
        return {
            "api": "v1",
            "runtime": "v2",
            "channel": resolved_channel,
            "sha": _deployment_sha(),
        }

    return app


app = create_demo_app()
