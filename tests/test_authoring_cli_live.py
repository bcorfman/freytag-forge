from __future__ import annotations

import json
from pathlib import Path

import pytest

from storygame.authoring import cli
from storygame.authoring.blueprint_compiler import BlueprintCompilationExhausted
from storygame.authoring.compiler import CompilationError
from storygame.authoring.sources import NormalizedStorySource, StorySourceLoader
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


def _source() -> NormalizedStorySource:
    return NormalizedStorySource(
        source_format="story-outline-inventory-v1",
        source_id="signal",
        genre="sci-fi",
        profile="sci-fi",
        source_path="outlines.yaml#signal",
        source_schema_version="story-outline-inventory-v1",
        source_hash="a" * 64,
        premise="A beacon needs repair.",
        opening_public_boundary="The beacon is failing.",
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


def test_live_command_writes_an_explicit_nonplayable_diagnostic_on_exhaustion(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    output = tmp_path / "failure.diagnostic.json"

    def fail(_: object) -> dict[str, object]:
        raise BlueprintCompilationExhausted(
            "invalid response",
            (),
            provider="openai",
            model="gpt-5.5",
            source=StorySourceLoader(Path("data/story_outlines.yaml"), Path("data/genre_profiles")).select_outline(
                "vale_mansion_rebuild"
            ),
        )

    monkeypatch.setattr(cli, "_compile_candidate", fail)

    with pytest.raises(SystemExit, match="diagnostic saved"):
        cli.main(
            [
                "--outline-id",
                "vale_mansion_rebuild",
                "--provider",
                "openai",
                "--live",
                "--diagnostic-output",
                str(output),
            ]
        )

    assert json.loads(output.read_text(encoding="utf-8"))["schema_version"] == "story-blueprint-diagnostic-v1"
    with pytest.raises(SystemExit, match="BLUEPRINT_COMPILATION_EXHAUSTED"):
        cli.main(["--replay-diagnostic", str(output)])


def test_diagnostic_artifacts_replay_without_a_provider_and_reject_bad_paths(tmp_path: Path):
    source = _source()
    story = _story()
    story["provenance"] = source.provenance()
    diagnostic = tmp_path / "valid.diagnostic.json"
    diagnostic.write_text(
        json.dumps(
            {
                "schema_version": "story-blueprint-diagnostic-v1",
                "source": source.model_dump(mode="json"),
                "provider": "openai",
                "model": "gpt-5.5",
                "attempts": [{"request_index": 1, "json_object": True, "response": json.dumps(story)}],
            }
        ),
        encoding="utf-8",
    )

    assert cli._replay_diagnostic(diagnostic, Path("data/genre_profiles"))["validation_results"][-1] == "critics_valid"
    with pytest.raises(CompilationError, match="DIAGNOSTIC_OUTPUT_INVALID"):
        cli._write_diagnostic(tmp_path / "wrong.json", {})
    cli._write_diagnostic(tmp_path / "saved.diagnostic.json", {})
    with pytest.raises(CompilationError, match="DIAGNOSTIC_OUTPUT_EXISTS"):
        cli._write_diagnostic(tmp_path / "saved.diagnostic.json", {})
    with pytest.raises(CompilationError, match="DIAGNOSTIC_NOT_FOUND"):
        cli._replay_diagnostic(tmp_path / "missing.diagnostic.json", Path("data/genre_profiles"))


def test_diagnostic_replay_transport_rejects_unavailable_or_mismatched_attempts():
    cases = [
        ([], "no response"),
        ([{"json_object": False, "response": "{}"}], "sequence does not match"),
        ([{"json_object": True, "error_code": "OPENAI_TIMEOUT", "error_detail": "timed out"}], "OPENAI_TIMEOUT"),
        ([{"json_object": True}], "response is unavailable"),
    ]
    for attempts, expected in cases:
        with pytest.raises(CompilationError, match=expected):
            cli._DiagnosticReplayTransport(attempts).generate("prompt", json_object=True)
