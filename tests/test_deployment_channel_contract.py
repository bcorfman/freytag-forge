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
