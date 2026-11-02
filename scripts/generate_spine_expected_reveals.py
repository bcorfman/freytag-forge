from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

from storygame.runtime.candidate_matcher import uniquely_matched_authored_handoff
from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.reveal_eligibility import explain_reveal
from storygame.runtime.state import RuntimeState
from storygame.story_package.loader import load_story_package

FRONTEND_ROOT = Path("frontend/e2e")
PACKAGE_ROOT = Path("data/stories/continuity-initiative")
SCENE_IDS = ("1A", "1B", "1C", "2A", "2B", "2C", "3A", "3B", "3C")


def scene_prompts() -> dict[str, list[str]]:
    source = (FRONTEND_ROOT / "canon-journey.js").read_text()
    scenes: dict[str, list[str]] = {}
    scene_block = re.search(r"export const scenePrompts = \{(?P<body>.*?)\n\};", source, re.DOTALL)
    assert scene_block, "Could not find scenePrompts in canon-journey.js."
    arrays = list(re.finditer(r'"(?P<scene>[123][ABC])"\s*:\s*\[(?P<body>.*?)\]', scene_block.group("body"), re.DOTALL))
    assert {match.group("scene") for match in arrays} == set(SCENE_IDS)
    for match in arrays:
        scene = match.group("scene")
        body = match.group("body")
        strings = list(re.finditer(r'"(?:\\.|[^"\\])*"', body))
        remainder = re.sub(r'"(?:\\.|[^"\\])*"', "", body)
        assert not remainder.strip(" \t\r\n,"), f'The "{scene}" array contains non-string content.'
        scenes[scene] = [json.loads(string.group(0)) for string in strings]
    return scenes


def knowledge_items() -> dict[str, dict]:
    raw = yaml.safe_load((PACKAGE_ROOT / "knowledge.yaml").read_text())
    return {item["id"]: item for item in raw["knowledge"]}


class _ScriptedProvider(CloudflareTurnProvider):
    """Run the transport's authored-handoff selection without dispatching it."""

    def __init__(self, state: RuntimeState) -> None:
        super().__init__(worker_url="https://offline.invalid/turn", token="", state=state)

    def __call__(self, player_input: str) -> dict[str, object]:
        self.assemble_turn_prompt(player_input)
        candidates = tuple(
            candidate
            for candidate in self._reveal_universe()
            if (item := self.state.package.knowledge_indexes.by_id.get(candidate.id)) is not None
            and explain_reveal(self.state, "player", item).eligible
        )
        handoff = uniquely_matched_authored_handoff(self._evidence_input(player_input), candidates)
        self.authored_handoff = handoff
        selected = () if handoff is None else (handoff.candidate.id,)
        if handoff is not None:
            item = self.state.package.knowledge_indexes.by_id[handoff.candidate.id]
            assert explain_reveal(self.state, "player", item).eligible
            text = handoff.delivery_text or item.statement
        else:
            text = "A concrete authored consequence lands."
        return {
            "segments": [{"kind": "narration", "text": text, "grounding_ids": list(selected)}],
            "selected_knowledge_ids": list(selected),
        }


def simulate_expected_reveals() -> dict[str, list[str]]:
    """Simulate the hosted prompt walk against the real offline runtime."""

    package = load_story_package(PACKAGE_ROOT)
    state = RuntimeState.bootstrap(package)
    provider = _ScriptedProvider(state)
    engine = RuntimeEngine(state, provider)
    prompts = scene_prompts()
    used: dict[str, int] = {scene: 0 for scene in SCENE_IDS}
    committed: dict[str, set[str]] = {scene: set() for scene in SCENE_IDS}

    for _ in range(120):
        scene = state.current_scene_id
        command = prompts[scene][used[scene] % len(prompts[scene])]
        used[scene] += 1
        engine.turn(command)
        committed[scene].update(state.last_turn_delivery.revealed_knowledge_ids)
        if Fact(predicate="resolution_complete", subject="story", value="true") in state.facts.asserted:
            return {scene_id: sorted(committed[scene_id]) for scene_id in SCENE_IDS}

    raise RuntimeError("scripted spine walk did not reach resolution_complete within 120 turns")


def main() -> None:
    expected = simulate_expected_reveals()
    assert "k_sl_2c_c_r1" in expected["2C"]
    (FRONTEND_ROOT / "spine-expected-reveals.json").write_text(json.dumps(expected, indent=2) + "\n")


if __name__ == "__main__":
    main()
