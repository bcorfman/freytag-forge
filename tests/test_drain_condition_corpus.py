from __future__ import annotations

import importlib.util
import json
import random
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/ringer/environment_narration/drain_condition_corpus.py"


def _module():
    specification = importlib.util.spec_from_file_location("drain_condition_corpus", SCRIPT)
    assert specification is not None and specification.loader is not None
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def _write(path: Path, document: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")


def _labels(module, key: dict[str, object], value: bool = False) -> dict[str, dict[str, bool]]:
    return {opaque_id: {name: value for name in module.LABEL_NAMES} for opaque_id in key}


def test_real_build_is_deterministic_and_carries_the_known_labels() -> None:
    module = _module()
    first = module.build_corpus()
    second = module.build_corpus()

    assert first == second
    assert len(first["rows"]) == 100
    labeled = [row for row in first["rows"] if row["provisional_label"] is not None]
    assert len(labeled) == 49
    assert sum(row["provisional_label"]["forbidden"] for row in labeled) == 18
    counts = {}
    for row in first["rows"]:
        counts[row["run"]] = counts.get(row["run"], 0) + 1
    assert counts == {
        "t9h-drain-details/screen": 19,
        "t9h-drain-details/confirm": 30,
        "t9h-hidden/smoke": 6,
        "t9h-latency/hedge-short": 9,
        "t9h-latency/all-on": 9,
        "t9h-latency/on-2": 10,
        "t9h-latency/off-2": 8,
        "t9h-drain/smoke/off": 6,
        "t9h-drain/smoke/on": 3,
    }


def test_fixture_rows_extract_player_text_and_late_completion_note(tmp_path: Path) -> None:
    module = _module()
    details_rows = tmp_path / "details.json"
    details_key = tmp_path / "blind_key.json"
    details_labels = tmp_path / "labels.json"
    _write(
        details_rows,
        {
            "rows": [
                {
                    "arm": "control",
                    "sample": 1,
                    "response_text": json.dumps(
                        {
                            "item_facts": {"storm drain": {"place": "park"}},
                            "segments": [{"kind": "narration", "text": "A."}, {"text": "B."}],
                        }
                    ),
                }
            ]
        },
    )
    _write(details_key, {"sample-001": {"row_index": 1, "sample": 1}})
    _write(details_labels, {"sample-001": {name: False for name in module.LABEL_NAMES}})
    engine_rows = tmp_path / "engine.json"
    _write(
        engine_rows,
        [
            {
                "turns": [
                    {
                        "input": "inspect the storm drain",
                        "enforce_attempts": [{"narration": "First."}, {"narration": "Second."}],
                    }
                ]
            }
        ],
    )
    details = module._detail_rows("details", details_rows, details_key, details_labels)
    engine = module._engine_rows("engine", engine_rows)
    assert details[0]["narration"] == "A. B."
    assert details[0]["item_facts_raw"] == {"storm drain": {"place": "park"}}
    assert [row["narration"] for row in engine] == ["First.", "Second."]
    assert all("late completions" in row["notes"] for row in engine)


def test_blind_sheet_uses_seeded_shuffle_and_has_no_metadata(tmp_path: Path) -> None:
    module = _module()
    rows = [{"id": f"row-{index:03d}", "narration": f"Text {index}."} for index in range(1, 4)]
    corpus = tmp_path / "corpus.json"
    _write(corpus, {"schema": 1, "built_from": [], "rows": rows})
    output = tmp_path / "sheet"
    module.blind_sheet(corpus, output)
    key = json.loads((output / "blind_key.json").read_text())
    expected = list(range(1, 4))
    random.Random(module.SHUFFLE_SEED).shuffle(expected)
    assert [entry["row_index"] for entry in key.values()] == expected
    sheet = (output / "blind_sheet.md").read_text().lower()
    banned_words = ("control", "candidate", "source", "attempt", "outcome", "score", "provisional", "label", "path")
    assert all(word not in sheet for word in banned_words)
    assert "text 1." in sheet and "text 2." in sheet and "text 3." in sheet
    labels = json.loads((output / "labels_template.json").read_text())
    assert all(set(entry) == set(module.LABEL_NAMES) for entry in labels.values())
    assert all(value is None for entry in labels.values() for value in entry.values())


def test_freeze_rejects_null_and_changed_hash(tmp_path: Path) -> None:
    module = _module()
    labels_path = tmp_path / "labels.json"
    _write(labels_path, {"row-001": {name: None for name in module.LABEL_NAMES}})
    with pytest.raises(ValueError) as error:
        module.freeze_labels(labels_path)
    assert "null label" in str(error.value)
    _write(labels_path, {"row-001": {name: False for name in module.LABEL_NAMES}})
    freeze = module.freeze_labels(labels_path)
    frozen = freeze.read_text()
    labels = json.loads(labels_path.read_text())
    labels["row-001"][module.LABEL_NAMES[0]] = True
    _write(labels_path, labels)
    with pytest.raises(ValueError) as error:
        module.freeze_labels(labels_path)
    assert "different hash" in str(error.value)
    assert freeze.read_text() == frozen


def test_join_requires_freeze_and_reports_disagreements(tmp_path: Path) -> None:
    module = _module()
    corpus_path = tmp_path / "corpus.json"
    labels_path = tmp_path / "labels.json"
    key_path = tmp_path / "key.json"
    out_path = tmp_path / "joined.json"
    provisional = {name: False for name in module.LABEL_NAMES}
    provisional["forbidden"] = False
    _write(
        corpus_path,
        {
            "schema": 1,
            "built_from": ["fixture/rows.json"],
            "rows": [
                {"id": "row-001", "narration": "A", "provisional_label": provisional},
                {"id": "row-002", "narration": "B", "provisional_label": None},
            ],
        },
    )
    _write(key_path, {"row-001": {"row_index": 1}, "row-002": {"row_index": 2}})
    labels = _labels(module, {"row-001": {}, "row-002": {}})
    labels["row-001"][module.LABEL_NAMES[0]] = True
    _write(labels_path, labels)
    with pytest.raises(ValueError) as error:
        module.join_corpus(corpus_path, labels_path, key_path, out_path)
    assert str(error.value) == "run --freeze-labels first"
    module.freeze_labels(labels_path)
    module.join_corpus(corpus_path, labels_path, key_path, out_path)
    joined = json.loads(out_path.read_text())
    assert joined["rows"][0]["final_label"][module.LABEL_NAMES[0]] is True
    assert joined["rows"][0]["label_disagreements"] == [module.LABEL_NAMES[0], "forbidden"]
    assert joined["disagreements"] == [
        {"id": "row-001", "opaque_id": "row-001", "fields": [module.LABEL_NAMES[0], "forbidden"]}
    ]
