from __future__ import annotations

import json
from pathlib import Path

import pytest

from storygame.authoring import cli
from storygame.authoring.compiler import CompilationError
from storygame.authoring.sources import StorySourceLoader
from tests.test_causal_story_contract import _story


class _Transport:
    def __init__(self, source_hash: str) -> None:
        self._source_hash = source_hash

    def generate(self, prompt: str, *, json_object: bool) -> dict[str, object]:
        candidate = _story()
        candidate["provenance"] = {
            "source_format": "story-outline-inventory-v1",
            "source_id": "signal",
            "source_hash": self._source_hash,
        }
        return candidate


def _inventory(path: Path) -> None:
    path.write_text(
        "stories:\n  - id: signal\n    genre: sci-fi\n    outline: A beacon needs repair.\n",
        encoding="utf-8",
    )


def test_live_custom_transport_writes_a_fresh_candidate(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys):
    inventory = tmp_path / "outlines.yaml"
    output = tmp_path / "signal.candidate.json"
    _inventory(inventory)
    monkeypatch.setenv("FREYTAG_ENABLE_LIVE_COMPILER", "1")
    source_hash = StorySourceLoader(inventory, Path("data/genre_profiles")).select_outline("signal").source_hash
    monkeypatch.setattr(cli, "_load_transport_factory", lambda path: _Transport(source_hash))

    assert (
        cli.main(
            [
                "--outline-id",
                "signal",
                "--inventory",
                str(inventory),
                "--transport-factory",
                "test.fake:transport",
                "--model",
                "test-model",
                "--live",
                "--output",
                str(output),
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out) == {"candidate": str(output)}
    assert json.loads(output.read_text(encoding="utf-8"))["story"]["id"] == "signal_crisis"

    with pytest.raises(SystemExit, match="CANDIDATE_OUTPUT_EXISTS"):
        cli.main(
            [
                "--outline-id",
                "signal",
                "--inventory",
                str(inventory),
                "--transport-factory",
                "test.fake:transport",
                "--model",
                "test-model",
                "--live",
                "--output",
                str(output),
            ]
        )


def test_live_command_requires_gate_provider_and_candidate_suffix(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    inventory = tmp_path / "outlines.yaml"
    _inventory(inventory)
    arguments = ["--outline-id", "signal", "--inventory", str(inventory), "--live"]
    with pytest.raises(SystemExit, match="LIVE_COMPILATION_DISABLED"):
        cli.main(arguments)

    monkeypatch.setenv("FREYTAG_ENABLE_LIVE_COMPILER", "1")
    with pytest.raises(SystemExit, match="COMPILER_PROVIDER_REQUIRED"):
        cli.main(arguments)
    with pytest.raises(SystemExit, match="LIVE_COMPILATION_ACK_REQUIRED"):
        cli.main(["--outline-id", "signal", "--inventory", str(inventory), "--provider", "openai"])


def test_transport_factory_is_a_validated_custom_seam(monkeypatch: pytest.MonkeyPatch):
    with pytest.raises(CompilationError, match="TRANSPORT_FACTORY_INVALID"):
        cli._load_transport_factory("not-a-factory")
