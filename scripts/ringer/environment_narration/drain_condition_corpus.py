"""Build the recorded T9h drain-condition corpus and its blind label sheet."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
SHUFFLE_SEED = 880419
SCHEMA = 1
LABEL_NAMES = (
    "opens_or_enters_drain",
    "invents_ajar_or_cover_state",
    "asserts_definite_contents",
    "speculative_only",
    "wrong_place",
    "capture_prose_disagree",
)
FORBIDDEN_NAMES = LABEL_NAMES[:3]
ENGINE_NOTES = (
    "The recorder appended late completions to the wrong turn; raw replies cannot be attributed to an attempt."
)

DETAIL_SOURCES = (
    (
        "t9h-drain-details/screen",
        "bench/results/environment-narration/t9h-drain-details/screen/rows.json",
        "bench/results/environment-narration/t9h-drain-details/screen/sheet.md/blind_key.json",
        "bench/results/environment-narration/t9h-drain-details/screen/sheet.md/labels.json",
    ),
    (
        "t9h-drain-details/confirm",
        "bench/results/environment-narration/t9h-drain-details/confirm/rows.json",
        "bench/results/environment-narration/t9h-drain-details/confirm/sheet/blind_key.json",
        "bench/results/environment-narration/t9h-drain-details/confirm/sheet/labels.json",
    ),
)
ENGINE_SOURCES = (
    ("t9h-hidden/smoke", "bench/results/environment-narration/t9h-hidden/smoke/rows/rows.json"),
    ("t9h-latency/hedge-short", "bench/results/environment-narration/t9h-latency/hedge-short/rows/rows.json"),
    ("t9h-latency/all-on", "bench/results/environment-narration/t9h-latency/all-on/rows/rows.json"),
    ("t9h-latency/on-2", "bench/results/environment-narration/t9h-latency/on-2/rows/rows.json"),
    ("t9h-latency/off-2", "bench/results/environment-narration/t9h-latency/off-2/rows/rows.json"),
    ("t9h-drain/smoke/off", "bench/results/environment-narration/t9h-drain/smoke/off/rows/rows.json"),
    ("t9h-drain/smoke/on", "bench/results/environment-narration/t9h-drain/smoke/on/rows/rows.json"),
)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, document: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _repo_path(path: Path | str) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = ROOT / candidate
    return candidate


def _repo_relative(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _rows_document(path: Path) -> list[dict[str, Any]]:
    document = _read_json(path)
    rows = document.get("rows") if isinstance(document, dict) else document
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise ValueError(f"{path} must contain a rows list")
    return rows


def _response_fields(value: Any) -> tuple[str | None, dict[str, Any] | None]:
    parsed: Any = value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return None, None
    if not isinstance(parsed, dict):
        return None, None
    segments = parsed.get("segments")
    if not isinstance(segments, list):
        narration = None
    else:
        texts = [segment.get("text") for segment in segments if isinstance(segment, dict)]
        narration = None if not all(isinstance(text, str) for text in texts) else " ".join(texts)
    item_facts = parsed.get("item_facts")
    return narration, item_facts if isinstance(item_facts, dict) else None


def _provisional_label(labels: dict[str, Any]) -> dict[str, bool]:
    values = {name: labels.get(name) for name in LABEL_NAMES}
    if not all(isinstance(value, bool) for value in values.values()):
        raise ValueError("labels must contain all six boolean fields")
    values["forbidden"] = any(values[name] for name in FORBIDDEN_NAMES)
    return values


def _detail_rows(
    run: str,
    rows_path: Path,
    key_path: Path,
    labels_path: Path,
) -> list[dict[str, Any]]:
    rows = _rows_document(rows_path)
    key = _read_json(key_path)
    labels = _read_json(labels_path)
    if not isinstance(key, dict) or not isinstance(labels, dict):
        raise ValueError("detail key and labels must be JSON objects")
    result = []
    seen_refs: set[str] = set()
    source_file = _repo_relative(rows_path)
    for opaque_id, entry in key.items():
        if not isinstance(entry, dict):
            raise ValueError(f"invalid key entry for {opaque_id}")
        row_index = entry.get("row_index")
        if not isinstance(row_index, int) or not 1 <= row_index <= len(rows):
            raise ValueError(f"invalid row_index for {opaque_id}")
        source_ref = f"sample-{entry.get('sample', row_index):03d}/row-{row_index:03d}"
        if source_ref in seen_refs:
            continue
        seen_refs.add(source_ref)
        row = rows[row_index - 1]
        narration, item_facts = _response_fields(row.get("response_text"))
        if narration is None:
            raise ValueError(f"{source_file} row {row_index} has no readable narration segments")
        label_entry = labels.get(opaque_id)
        if not isinstance(label_entry, dict):
            raise ValueError(f"missing labels for {opaque_id}")
        result.append(
            {
                "source_file": source_file,
                "source_ref": source_ref,
                "run": run,
                "arm": row.get("arm"),
                "narration": narration,
                "item_facts_raw": item_facts,
                "provisional_label": _provisional_label(label_entry),
                "label_source": "claude-blind-provisional",
            }
        )
    return result


def _drain_turns(rows_path: Path) -> list[tuple[int, int, dict[str, Any]]]:
    replicates = _read_json(rows_path)
    if not isinstance(replicates, list):
        raise ValueError(f"{rows_path} must contain replicate rows")
    result = []
    for replicate_index, replicate in enumerate(replicates):
        turns = replicate.get("turns") if isinstance(replicate, dict) else None
        if not isinstance(turns, list):
            continue
        for turn_index, turn in enumerate(turns):
            if isinstance(turn, dict) and turn.get("input") == "inspect the storm drain":
                result.append((replicate_index, turn_index, turn))
    return result


def _engine_rows(run: str, rows_path: Path) -> list[dict[str, Any]]:
    source_file = _repo_relative(rows_path)
    result = []
    seen_refs: set[str] = set()
    for replicate_index, turn_index, turn in _drain_turns(rows_path):
        attempts = turn.get("enforce_attempts")
        if not isinstance(attempts, list):
            continue
        for attempt_index, attempt in enumerate(attempts[:2], start=1):
            if not isinstance(attempt, dict) or not isinstance(attempt.get("narration"), str):
                continue
            source_ref = f"r{replicate_index}/t{turn_index}/a{attempt_index}"
            if source_ref in seen_refs:
                continue
            seen_refs.add(source_ref)
            result.append(
                {
                    "source_file": source_file,
                    "source_ref": source_ref,
                    "run": run,
                    "arm": None,
                    "narration": attempt["narration"],
                    "item_facts_raw": None,
                    "provisional_label": None,
                    "label_source": None,
                    "notes": ENGINE_NOTES,
                }
            )
    return result


def build_corpus(
    detail_sources: tuple[tuple[str, str, str, str], ...] = DETAIL_SOURCES,
    engine_sources: tuple[tuple[str, str], ...] = ENGINE_SOURCES,
) -> dict[str, Any]:
    rows = []
    built_from = []
    for run, rows_name, key_name, labels_name in detail_sources:
        rows_path = _repo_path(rows_name)
        rows.extend(_detail_rows(run, rows_path, _repo_path(key_name), _repo_path(labels_name)))
        built_from.append(_repo_relative(rows_path))
    for run, rows_name in engine_sources:
        rows_path = _repo_path(rows_name)
        rows.extend(_engine_rows(run, rows_path))
        built_from.append(_repo_relative(rows_path))
    for index, row in enumerate(rows, start=1):
        row["id"] = f"row-{index:03d}"
    return {"schema": SCHEMA, "built_from": built_from, "rows": rows}


def _corpus_rows(path: Path) -> list[dict[str, Any]]:
    document = _read_json(path)
    rows = document.get("rows") if isinstance(document, dict) else None
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise ValueError("corpus must contain a rows list")
    return rows


def _shuffled_rows(rows: list[dict[str, Any]]) -> list[tuple[int, dict[str, Any]]]:
    indexed = list(enumerate(rows, start=1))
    random.Random(SHUFFLE_SEED).shuffle(indexed)
    return indexed


def blind_sheet(corpus_path: Path, output: Path) -> None:
    rows = _corpus_rows(corpus_path)
    output.mkdir(parents=True, exist_ok=True)
    lines = ["# Drain observations", ""]
    key: dict[str, Any] = {}
    labels: dict[str, Any] = {}
    for display_index, (row_index, row) in enumerate(_shuffled_rows(rows), start=1):
        opaque_id = f"row-{display_index:03d}"
        narration = row.get("narration")
        if not isinstance(narration, str):
            raise ValueError(f"corpus row {row_index} has no narration")
        key[opaque_id] = {"row_index": row_index}
        labels[opaque_id] = {name: None for name in LABEL_NAMES}
        lines.extend([f"## {opaque_id}", "", narration, ""])
    (output / "blind_sheet.md").write_text("\n".join(lines), encoding="utf-8")
    _write_json(output / "blind_key.json", key)
    _write_json(output / "labels_template.json", labels)


def _freeze_path(labels_path: Path) -> Path:
    return labels_path.parent / "labels.freeze.json"


def freeze_labels(labels_path: Path) -> Path:
    labels = _read_json(labels_path)
    if not isinstance(labels, dict):
        raise ValueError("labels file must be a JSON object")
    for opaque_id, entry in labels.items():
        if not isinstance(entry, dict):
            raise ValueError(f"invalid label entry for {opaque_id}")
        for name in LABEL_NAMES:
            value = entry.get(name)
            if value is None:
                raise ValueError(f"null label for {opaque_id}: {name}")
            if not isinstance(value, bool):
                raise ValueError(f"label for {opaque_id} is not boolean: {name}")
    freeze = _freeze_path(labels_path)
    digest = _sha256(labels_path)
    if freeze.exists():
        existing = _read_json(freeze)
        if not isinstance(existing, dict) or existing.get("sha256") != digest:
            raise ValueError("labels.freeze.json already exists with a different hash; refusing to overwrite")
        return freeze
    _write_json(freeze, {"sha256": digest})
    return freeze


def _frozen_hash(labels_path: Path) -> str:
    freeze = _freeze_path(labels_path)
    if not freeze.is_file():
        raise ValueError("run --freeze-labels first")
    document = _read_json(freeze)
    digest = document.get("sha256") if isinstance(document, dict) else None
    if not isinstance(digest, str):
        raise ValueError("labels.freeze.json has no frozen sha256")
    actual = _sha256(labels_path)
    if actual != digest:
        raise ValueError("labels sha256 does not match the frozen labels hash")
    return digest


def _final_label(entry: Any, opaque_id: str) -> dict[str, bool]:
    if not isinstance(entry, dict):
        raise ValueError(f"missing labels for {opaque_id}")
    result = {}
    for name in LABEL_NAMES:
        value = entry.get(name)
        if not isinstance(value, bool):
            raise ValueError(f"label for {opaque_id} is missing or not boolean: {name}")
        result[name] = value
    return result


def _disagreements(provisional: Any, final: dict[str, bool]) -> list[str]:
    if not isinstance(provisional, dict):
        return []
    names = list(LABEL_NAMES)
    if "forbidden" in provisional:
        names.append("forbidden")
    disagreements = []
    for name in names:
        expected = any(final[field] for field in FORBIDDEN_NAMES) if name == "forbidden" else final[name]
        if provisional.get(name) != expected:
            disagreements.append(name)
    return disagreements


def join_corpus(corpus_path: Path, labels_path: Path, key_path: Path, output: Path) -> None:
    _frozen_hash(labels_path)
    corpus = _read_json(corpus_path)
    rows = _corpus_rows(corpus_path)
    labels = _read_json(labels_path)
    key = _read_json(key_path)
    if not isinstance(labels, dict) or not isinstance(key, dict):
        raise ValueError("labels and key must be JSON objects")
    by_index = {index: row for index, row in enumerate(rows, start=1)}
    if len(key) != len(rows):
        raise ValueError("key does not cover every corpus row")
    joined_rows = []
    disagreements = []
    seen_indexes: set[int] = set()
    for opaque_id, entry in key.items():
        if not isinstance(entry, dict) or entry.get("row_index") not in by_index:
            raise ValueError(f"invalid key row for {opaque_id}")
        row_index = entry["row_index"]
        if row_index in seen_indexes:
            raise ValueError("key contains duplicate row_index values")
        seen_indexes.add(row_index)
        final = _final_label(labels.get(opaque_id), opaque_id)
        row = dict(by_index[row_index])
        row_disagreements = _disagreements(row.get("provisional_label"), final)
        row["final_label"] = final
        row["label_disagreements"] = row_disagreements
        joined_rows.append(row)
        if row_disagreements:
            disagreements.append(
                {
                    "id": row.get("id"),
                    "opaque_id": opaque_id,
                    "fields": row_disagreements,
                }
            )
    result = {
        "schema": corpus.get("schema", SCHEMA) if isinstance(corpus, dict) else SCHEMA,
        "built_from": corpus.get("built_from", []) if isinstance(corpus, dict) else [],
        "rows": sorted(joined_rows, key=lambda row: str(row.get("id", ""))),
        "disagreements": disagreements,
    }
    _write_json(output, result)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--build", action="store_true")
    modes.add_argument("--blind-sheet", action="store_true")
    modes.add_argument("--freeze-labels", action="store_true")
    modes.add_argument("--join", action="store_true")
    parser.add_argument("--corpus", type=Path)
    parser.add_argument("--labels", type=Path)
    parser.add_argument("--key", type=Path)
    parser.add_argument("--out", type=Path)
    return parser


def _error(message: str, code: int = 1) -> int:
    print(f"drain condition corpus: {message}", file=sys.stderr)
    return code


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.build:
            if args.out is None:
                return _error("--build requires --out", 2)
            document = build_corpus()
            _write_json(args.out / "corpus.json", document)
            counts: dict[str, int] = {}
            for row in document["rows"]:
                counts[row["run"]] = counts.get(row["run"], 0) + 1
            print(f"built {len(document['rows'])} rows")
            for run, count in counts.items():
                print(f"{run}: {count}")
            return 0
        if args.blind_sheet:
            if args.corpus is None or args.out is None:
                return _error("--blind-sheet requires --corpus and --out", 2)
            blind_sheet(args.corpus, args.out)
            return 0
        if args.freeze_labels:
            if args.labels is None:
                return _error("--freeze-labels requires --labels", 2)
            print(f"labels frozen at {freeze_labels(args.labels)}")
            return 0
        if args.join:
            if args.corpus is None or args.labels is None or args.key is None or args.out is None:
                return _error("--join requires --corpus, --labels, --key and --out", 2)
            join_corpus(args.corpus, args.labels, args.key, args.out)
            return 0
    except (OSError, ValueError, json.JSONDecodeError) as error:
        return _error(str(error))
    return _error("no mode selected", 2)


if __name__ == "__main__":
    raise SystemExit(main())
