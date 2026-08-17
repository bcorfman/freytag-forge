"""Operator-only live smoke; never enabled by CI or the default test suite."""

from __future__ import annotations

import os

import pytest

from storygame.authoring.openai_transport import OpenAIBlueprintTransport, OpenAICompilerConfig


@pytest.mark.live_e2e
def test_openai_responses_json_object_smoke():
    if os.getenv("FREYTAG_RUN_LIVE_SMOKE") != "1":
        pytest.skip("set FREYTAG_RUN_LIVE_SMOKE=1 for an operator-owned paid smoke")
    if not os.getenv("OPENAI_API_KEY") or not os.getenv("FREYTAG_COMPILER_MODEL"):
        pytest.skip("OpenAI credentials and an explicit compiler model are required")

    output = OpenAIBlueprintTransport(OpenAICompilerConfig.from_environment()).generate(
        "Return one empty JSON object.", json_object=True
    )

    assert output == {}
