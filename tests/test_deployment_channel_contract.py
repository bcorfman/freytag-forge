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
    assert "required: false" in promotion
    assert "latest successful staging SHA" in promotion
    assert "commits?sha=main&per_page=100" in promotion
    assert "staging-deployment" in promotion
    assert "freytag-forge / production" in promotion
    assert "RAILWAY_PRODUCTION_ENVIRONMENT_ID" in promotion
    assert "FREYTAG_DEPLOYMENT_SHA" in staging
    assert "timeout 300s railway up --ci" in staging
    assert "Validate staged SHA" in promotion
    assert "Hosted demo production E2E" in promotion
    assert "Record production promotion" in promotion
    assert "railway deployment list" in promotion
    assert "Railway deployments visible before promotion" in promotion
    assert "No eligible Railway rollback deployment" in promotion
    assert "DEPLOYED_SHA: ${{ needs.validate-staged-sha.outputs.sha }}" in promotion
    assert "RAILWAY_KNOWN_GOOD_DEPLOYMENT_ID" not in promotion
    assert "deploy-production:" not in (root / ".github/workflows/test.yml").read_text(encoding="utf-8")
    assert "VITE_STAGING_API_BASE_URL" in pages
    assert "VITE_PRODUCTION_API_BASE_URL" in pages
    assert "Retrieve the published opposite Pages channel" in pages
    assert "wget --quiet --mirror" in pages
    assert "opposite-channel index" in pages
    assert '--commit "$GITHUB_SHA"' not in staging
    assert '--commit "$DEPLOYED_SHA"' not in promotion
    assert "before_pages_run_ids" in staging
    assert "before_pages_run_ids" in promotion


def test_production_pages_publish_preserves_the_downloaded_dev_directory() -> None:
    root = Path(__file__).resolve().parents[1]
    pages = (root / ".github/workflows/deploy-frontend-pages.yml").read_text(encoding="utf-8")

    assert "mkdir -p published-pages/dev" in pages
    assert 'cp -R "$source_dir/." published-pages/dev/' in pages


def test_staging_promotion_automatically_verifies_pages_and_api_identity() -> None:
    root = Path(__file__).resolve().parents[1]
    staging = (root / ".github/workflows/test.yml").read_text(encoding="utf-8")
    pages = (root / ".github/workflows/deploy-frontend-pages.yml").read_text(encoding="utf-8")

    assert "frontend/dist/deployment.json" in pages
    assert "Stamp the selected bundle with its immutable deployment identity" in pages
    assert '"${{ inputs.channel }}" "${{ inputs.sha }}"' in pages
    assert "pages_metadata_url=" in staging
    assert "/dev/deployment.json" in staging
    assert 'test "$pages_channel" = staging' in staging
    assert 'test "$pages_sha" = "$GITHUB_SHA"' in staging
    assert 'test "$health_channel" = staging && test "$health_sha" = "$GITHUB_SHA"' in staging


def test_non_production_badge_stays_hidden_until_the_staging_bundle_enables_it() -> None:
    root = Path(__file__).resolve().parents[1]
    styles = (root / "frontend" / "src" / "styles.css").read_text(encoding="utf-8")

    assert ".non-production-badge[hidden]" in styles
    assert "display: none" in styles
