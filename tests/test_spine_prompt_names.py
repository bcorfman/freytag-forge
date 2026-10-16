from __future__ import annotations

import json
import re
from pathlib import Path

from storygame.runtime.narration_safety import NarrationSafetyValidator
from storygame.story_package.loader import load_story_package

FRONTEND_ROOT = Path("frontend/e2e")
PACKAGE_ROOT = Path("data/stories/continuity-initiative")
SCENES = ("1A", "1B", "1C", "2A", "2B", "2C", "3A", "3B", "3C")


def _scene_prompts(scene: str) -> list[str]:
    source = (FRONTEND_ROOT / "canon-journey.js").read_text()
    match = re.search(rf'"{scene}"\s*:\s*\[(?P<body>.*?)\]', source, re.DOTALL)
    assert match, f'Could not find the "{scene}" prompt array in canon-journey.js.'

    body = match.group("body")
    strings = list(re.finditer(r'"(?:\\.|[^"\\])*"', body))
    remainder = re.sub(r'"(?:\\.|[^"\\])*"', "", body)
    assert not remainder.strip(" \t\r\n,"), f'The "{scene}" array contains non-string content.'
    return [json.loads(string.group(0)) for string in strings]


def _unavailable_character_forms(scene: str) -> dict[str, tuple[str, ...]]:
    package = load_story_package(PACKAGE_ROOT)
    scene_definition = next(item for item in package.scenes if item.metadata.scene_id == scene)
    nameable_ids = NarrationSafetyValidator._scene_entity_ids(package, scene_definition)
    return {npc.id: (npc.name, *npc.aliases) for npc in package.world.npcs if npc.id not in nameable_ids}


def test_spine_prompts_do_not_name_unavailable_characters() -> None:
    findings: list[str] = []
    for scene in SCENES:
        unavailable = _unavailable_character_forms(scene)
        for prompt_number, prompt in enumerate(_scene_prompts(scene), start=1):
            for character_id, forms in unavailable.items():
                if any(re.search(rf"(?<!\w){re.escape(form)}(?!\w)", prompt, re.IGNORECASE) for form in forms):
                    findings.append(f"{scene} prompt {prompt_number}: {prompt!r} names {character_id!r}")

    assert not findings, "Spine prompts name characters unavailable in their scene:\n" + "\n".join(findings)
