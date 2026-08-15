from __future__ import annotations

import pytest

from storygame.authoring.blueprint_cli import main


def test_blueprint_cli_requires_explicit_live_acknowledgement(tmp_path):
    with pytest.raises(SystemExit, match="2"):
        main(
            [
                "--outline-id",
                "122",
                "--genre",
                "sci-fi",
                "--transport-factory",
                "tests.fake:factory",
                "--output",
                str(tmp_path / "harbor.candidate.json"),
            ]
        )


def test_blueprint_cli_refuses_to_overwrite_an_existing_artifact(tmp_path):
    output = tmp_path / "harbor.candidate.json"
    output.write_text("reviewed", encoding="utf-8")

    with pytest.raises(SystemExit, match="2"):
        main(
            [
                "--live",
                "--outline-id",
                "122",
                "--genre",
                "sci-fi",
                "--transport-factory",
                "tests.fake:factory",
                "--output",
                str(output),
            ]
        )
