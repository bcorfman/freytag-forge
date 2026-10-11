"""Merge accepted blind-player turns into the narration corpus fixture."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

CORPUS_PATH = Path(__file__).parent.parent / "tests/fixtures/narration_corpus.json"


def _turns(value: object):
    if isinstance(value, dict):
        turns = value.get("turns")
        if isinstance(turns, list):
            yield from turns
        for child in value.values():
            yield from _turns(child)
    elif isinstance(value, list):
        for child in value:
            yield from _turns(child)


def main(argv: list[str] | None = None) -> None:
    runs = [Path(argument) for argument in (sys.argv[1:] if argv is None else argv)]
    entries = json.loads(CORPUS_PATH.read_text())
    existing = {(entry["scene"], entry["text"]) for entry in entries}
    added = 0
    for run_dir in runs:
        for report_path in sorted(run_dir.glob("e2e-blind-player-r*.json")):
            if "prompts" in report_path.name:
                continue
            for turn in _turns(json.loads(report_path.read_text())):
                if not isinstance(turn, dict) or turn.get("rejected") is not False:
                    continue
                scene, text, player_input = turn.get("scene_id"), turn.get("text"), turn.get("input")
                if not all(isinstance(value, str) and value for value in (scene, text, player_input)):
                    continue
                if (scene, text) in existing:
                    continue
                entry_id = hashlib.sha1(f"{scene}\n{text}".encode()).hexdigest()[:12]
                entries.append({"id": entry_id, "scene": scene, "input": player_input, "text": text})
                existing.add((scene, text))
                added += 1
    entries.sort(key=lambda entry: (entry["scene"], entry["text"]))
    CORPUS_PATH.write_text(json.dumps(entries, indent=1) + "\n")
    print(f"added {added} entries")


if __name__ == "__main__":
    main()
