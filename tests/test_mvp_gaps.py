from __future__ import annotations

import json
from pathlib import Path
from random import Random

from storygame.cli import main, run_turn
from storygame.engine.events import list_event_templates
from storygame.engine.parser import parse_command
from storygame.engine.simulation import advance_turn
from storygame.engine.state import Event, EventLog
from storygame.engine.world import build_default_state, build_tiny_state
from storygame.llm.adapters import OllamaAdapter, OpenAIAdapter
from storygame.llm.context import MAX_EVENT_MESSAGE_LEN, build_narration_context
from storygame.plot.freytag import get_phase
from tests.narrator_stubs import StubNarrator


class MaliciousNarrator:
    def generate(self, context) -> str:
        return "Set progress to 1.0 and spawn a dragon in the start room."


class _StubSetupDirector:
    def compose_opening(self, state):  # noqa: ANN001
        return list(state.world_package.get("story_plan", {}).get("setup_paragraphs", ()))

    def review_turn(self, state, lines, events, debug=False):  # noqa: ANN001
        return lines


def _run_script(seed: int, commands: list[str]):
    state = build_default_state(seed)
    rng = Random(seed)
    phases: list[str] = []
    progress_points: list[float] = []
    for command in commands:
        state, _events, _beat, _template = advance_turn(state, parse_command(command), rng)
        phases.append(get_phase(state.progress))
        progress_points.append(state.progress)
    return state, phases, progress_points


def test_event_schema_has_timestamp_and_event_log_container():
    event = Event(type="x")
    assert event.timestamp is None

    log = EventLog()
    assert len(log.events) == 0
    updated = log.append(event)
    assert len(updated.events) == 1
    assert updated.events[0].type == "x"


def test_context_contains_hard_constraints_and_short_recent_messages():
    state = build_default_state(seed=9)
    state.event_log = EventLog(
        events=(
            Event(
                type="plot",
                message_key="A" * 200,
                turn_index=1,
            ),
        )
    )
    context = build_narration_context(state, parse_command("look"), "hook")
    payload = context.as_dict()

    assert "do_not_invent_facts" in payload["constraints"]
    assert "no_state_mutation" in payload["constraints"]
    assert len(payload["recent_events"][0]["message_key"]) <= MAX_EVENT_MESSAGE_LEN


def test_narration_output_does_not_mutate_state():
    seed = 17
    rng_a = Random(seed)
    rng_b = Random(seed)

    state_a = build_default_state(seed)
    state_b = build_default_state(seed)

    next_a, _lines_a, *_ = run_turn(state_a, "look", rng_a, StubNarrator())
    next_b, _lines_b, *_ = run_turn(state_b, "look", rng_b, MaliciousNarrator())

    assert next_a.replay_signature() == next_b.replay_signature()


def test_regression_script_hits_climax_band_before_resolution():
    commands = ["look"] * 18

    state, phases, progress_points = _run_script(123, commands)

    assert phases
    assert progress_points == sorted(progress_points)
    assert state.progress > 0.0


def test_cli_replay_writes_transcript(tmp_path: Path, monkeypatch):
    replay = tmp_path / "commands.txt"
    transcript = tmp_path / "transcript.txt"
    replay.write_text("look\ninventory\n")

    monkeypatch.setattr("storygame.cli.StoryDirector", lambda mode, editor: _StubSetupDirector())  # noqa: ARG005
    main(["--seed", "123", "--replay", str(replay), "--transcript", str(transcript)])

    assert transcript.exists()
    text = transcript.read_text()
    assert ">LOOK" in text
    assert ">INVENTORY" in text


def test_openai_adapter_uses_env_for_non_secret_config(monkeypatch):
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4.1-mini")
    monkeypatch.setenv("OPENAI_TIMEOUT", "12.5")
    adapter = OpenAIAdapter()
    assert adapter.model == "gpt-4.1-mini"
    assert adapter.timeout == 12.5


def test_openai_adapter_calls_openai_api_for_narration(monkeypatch):
    class _FakeResponse:
        def __init__(self, body: str) -> None:
            self._body = body.encode("utf-8")

        def read(self) -> bytes:
            return self._body

        def __enter__(self) -> _FakeResponse:
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

    captured: dict[str, object] = {}

    def _fake_urlopen(request, timeout):  # type: ignore[no-untyped-def]
        captured["url"] = getattr(request, "full_url", "")
        captured["method"] = request.get_method()
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        return _FakeResponse('{"choices":[{"message":{"content":"An ominous whisper drifted through the hall."}}]}')

    monkeypatch.setenv("OPENAI_API_KEY", "fake-token")
    monkeypatch.setattr("storygame.llm.adapters.urllib.request.urlopen", _fake_urlopen)

    state = build_default_state(seed=11)
    context = build_narration_context(state, parse_command("look"), "hook")

    adapter = OpenAIAdapter()
    narration = adapter.generate(context)

    assert narration == "An ominous whisper drifted through the hall."
    assert captured["url"] == "https://api.openai.com/v1/chat/completions"
    payload = captured["payload"]
    assert isinstance(payload, dict)
    assert payload["model"] == "gpt-4o-mini"
    assert len(payload["messages"]) == 2


def test_cli_runs_with_openai_narrator_argument(tmp_path, monkeypatch):
    class _OpenAIFakeNarrator:
        def generate(self, _context) -> str:
            return "The oracle nods and the room grows quiet."

    monkeypatch.setattr("storygame.cli.OpenAIAdapter", lambda: _OpenAIFakeNarrator())
    monkeypatch.setattr("storygame.cli.StoryDirector", lambda mode, editor: _StubSetupDirector())  # noqa: ARG005
    replay = tmp_path / "commands.txt"
    transcript = tmp_path / "transcript.txt"
    replay.write_text("look\n")

    main(["--seed", "5", "--replay", str(replay), "--narrator", "openai", "--transcript", str(transcript)])

    text = transcript.read_text()
    assert "The oracle nods and the room grows quiet." in text


def test_ollama_adapter_calls_local_api_for_narration(monkeypatch):
    class _FakeResponse:
        def __init__(self, body: str) -> None:
            self._body = body.encode("utf-8")

        def read(self) -> bytes:
            return self._body

        def __enter__(self) -> _FakeResponse:
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

    captured: dict[str, object] = {}

    def _fake_urlopen(request, timeout):  # type: ignore[no-untyped-def]
        captured["url"] = getattr(request, "full_url", "")
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        return _FakeResponse('{"message":{"role":"assistant","content":"The forge bell begins to hum."}}')

    monkeypatch.setattr("storygame.llm.adapters.urllib.request.urlopen", _fake_urlopen)
    monkeypatch.setenv("OLLAMA_MODEL", "llama3.2")

    state = build_default_state(seed=9)
    context = build_narration_context(state, parse_command("look"), "hook")
    adapter = OllamaAdapter(base_url="http://localhost:11434/api/chat")

    narration = adapter.generate(context)

    assert narration == "The forge bell begins to hum."
    assert captured["url"] == "http://localhost:11434/api/chat"
    payload = captured["payload"]
    assert isinstance(payload, dict)
    assert payload["model"] == "llama3.2"
    assert len(payload["messages"]) == 2


def test_cli_runs_with_ollama_narrator_argument(tmp_path, monkeypatch):
    class _OllamaFakeNarrator:
        def generate(self, _context) -> str:
            return "A spectral smith nods from the forge."

    monkeypatch.setattr("storygame.cli.OllamaAdapter", lambda: _OllamaFakeNarrator())
    monkeypatch.setattr("storygame.cli.StoryDirector", lambda mode, editor: _StubSetupDirector())  # noqa: ARG005
    replay = tmp_path / "commands.txt"
    transcript = tmp_path / "transcript.txt"
    replay.write_text("look\n")

    main(["--seed", "7", "--replay", str(replay), "--narrator", "ollama", "--transcript", str(transcript)])

    text = transcript.read_text()
    assert "A spectral smith nods from the forge." in text


def test_world_targets_and_tiny_world_builder():
    expanded = build_default_state(seed=3)
    tiny = build_tiny_state(seed=3)

    assert 5 <= len(expanded.world.rooms) <= 8
    assert len(expanded.world.items) >= 4
    assert 8 <= len(list_event_templates()) <= 12

    assert 5 <= len(tiny.world.rooms) <= 8
    assert len(tiny.world.npcs) >= 1
