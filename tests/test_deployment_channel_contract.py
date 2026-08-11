from __future__ import annotations

import json
from pathlib import Path


def _channels() -> dict[str, dict[str, str]]:
    root = Path(__file__).resolve().parents[1]
    payload = json.loads((root / "deployment" / "channel-contract.json").read_text(encoding="utf-8"))
    assert payload["version"] == 1
    return payload["channels"]


def test_root_and_dev_channels_use_distinct_api_origins() -> None:
    channels = _channels()

    assert channels["production"]["pages_path"] == "/"
    assert channels["staging"]["pages_path"] == "/dev/"
    assert channels["production"]["api_origin"] != channels["staging"]["api_origin"]


def test_root_and_dev_channels_never_share_state_configuration() -> None:
    channels = _channels()
    production = channels["production"]
    staging = channels["staging"]

    assert production["session_namespace"] != staging["session_namespace"]
    assert production["database_namespace"] != staging["database_namespace"]
    assert production["railway_environment"] != staging["railway_environment"]


def test_phase_one_delivery_workflows_keep_staging_and_production_separate() -> None:
    root = Path(__file__).resolve().parents[1]
    staging = (root / ".github/workflows/test.yml").read_text(encoding="utf-8")
    promotion = (root / ".github/workflows/promote-production.yml").read_text(encoding="utf-8")
    pages = (root / ".github/workflows/deploy-frontend-pages.yml").read_text(encoding="utf-8")

    assert "freytag-forge / staging" in staging
    assert "RAILWAY_STAGING_ENVIRONMENT_ID" in staging
    assert "needs: [cutover-contracts, fast-feedback, test]" in staging
    assert "Deploy staging" in staging
    assert "Hosted demo staging E2E" in staging
    assert "Record staging deployment" in staging
    assert "workflow_dispatch" in promotion
    assert "^[0-9a-f]{40}$" in promotion
    assert "staging-deployment" in promotion
    assert "freytag-forge / production" in promotion
    assert "RAILWAY_PRODUCTION_ENVIRONMENT_ID" in promotion
    assert "FREYTAG_DEPLOYMENT_SHA" in staging
    assert "timeout 300s railway up --ci" in staging
    assert "Validate staged SHA" in promotion
    assert "Hosted demo production E2E" in promotion
    assert "Record production promotion" in promotion
    assert "railway deployment list" in promotion
    assert "RAILWAY_KNOWN_GOOD_DEPLOYMENT_ID" not in promotion
    assert "deploy-production:" not in (root / ".github/workflows/test.yml").read_text(encoding="utf-8")
    assert "VITE_STAGING_API_BASE_URL" in pages
    assert "VITE_PRODUCTION_API_BASE_URL" in pages
    assert "Retrieve the published opposite Pages channel" in pages
    assert "wget --quiet --mirror" in pages
    assert "opposite-channel index" in pages
