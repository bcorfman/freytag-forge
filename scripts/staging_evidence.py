"""Build the JSON artifact used by the staging promotion gate."""

import json
import os
from pathlib import Path


def build_evidence(
    sha: str,
    api_base_url: str,
    api_identity: str,
    pages_identity: str,
    adapter_contract: str,
) -> dict[str, object]:
    """Return release evidence from the outcomes of the three verification checks."""
    outcomes = [api_identity, pages_identity, adapter_contract]
    normalized = [outcome if outcome else "not-run" for outcome in outcomes]
    checks = [
        {
            "name": "api-identity",
            "scope": "deployed",
            "outcome": normalized[0],
            "detail": "health+version of the Railway staging API matched channel and SHA",
        },
        {
            "name": "pages-identity",
            "scope": "deployed",
            "outcome": normalized[1],
            "detail": "published Pages /dev/deployment.json matched channel and SHA",
        },
        {
            "name": "adapter-contract",
            "scope": "local",
            "outcome": normalized[2],
            "detail": (
                "tests/test_web_demo.py and tests/test_cloudflare_transport.py ran on the CI runner; "
                "this does not touch the deployed service"
            ),
        },
    ]
    return {
        "schema_version": "scene-staging-evidence-v2",
        "sha": sha,
        "api_base_url": api_base_url,
        "runtime": "scene-v1",
        "result": "success" if all(outcome == "success" for outcome in normalized) else "failure",
        "checks": checks,
    }


def main() -> None:
    report_path = Path(os.environ["FREYTAG_EVALUATION_REPORT"])
    report_path.parent.mkdir(parents=True, exist_ok=True)
    evidence = build_evidence(
        os.environ.get("CANDIDATE_SHA", ""),
        os.environ.get("API_BASE_URL", ""),
        os.environ.get("API_IDENTITY_OUTCOME", ""),
        os.environ.get("PAGES_IDENTITY_OUTCOME", ""),
        os.environ.get("ADAPTER_CONTRACT_OUTCOME", ""),
    )
    report_path.write_text(json.dumps(evidence, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
