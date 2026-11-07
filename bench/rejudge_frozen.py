"""Rejudge saved bench turns against the story package from their run revision."""

from __future__ import annotations

import argparse
import copy
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from bench.core import (
    CONTINUITY_CRITERIA,
    FACT_TRACKING_CRITERIA,
    load_dotenv,
    run_continuity_judges,
    run_fact_tracking_judges,
)
from bench.judge_input import judge_turns
from storygame.story_package.loader import load_story_package

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
JUDGES = {
    "continuity": ("continuity-judgments.json", CONTINUITY_CRITERIA),
    "fact": ("fact-tracking-judgments.json", FACT_TRACKING_CRITERIA),
}


def _judge_runner(name: str):
    return run_continuity_judges if name == "continuity" else run_fact_tracking_judges


def _read_records(path: Path) -> dict[str, Any]:
    try:
        records = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"cannot read records file {path}: {error}") from error
    if not isinstance(records, dict):
        raise ValueError(f"records file {path} must contain an object")
    return records


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _relative_package_path(repo_root: Path, package_path: str) -> Path:
    candidate = Path(package_path)
    if not candidate.is_absolute():
        candidate = repo_root / candidate
    try:
        return candidate.absolute().relative_to(repo_root.absolute())
    except ValueError as error:
        raise ValueError(f"recorded package_path {package_path!r} is outside repository root {repo_root}") from error


def extract_package(repo_root: Path, package_path: Path, revision: str) -> Path:
    """Archive ``package_path`` at ``revision`` and return its extracted directory."""

    repo_root = repo_root.resolve()
    relative_path = _relative_package_path(repo_root, str(package_path))
    temporary_root = Path(tempfile.mkdtemp(prefix="rejudge-frozen-"))
    archive = subprocess.Popen(
        ["git", "archive", "--format=tar", revision, "--", relative_path.as_posix()],
        cwd=repo_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert archive.stdout is not None
    extracted = subprocess.run(
        ["tar", "-xf", "-", "-C", str(temporary_root)],
        stdin=archive.stdout,
        capture_output=True,
    )
    archive.stdout.close()
    archive_returncode = archive.wait()
    archive_stderr = (
        (archive.stderr.read() if archive.stderr is not None else b"").decode("utf-8", errors="replace").strip()
    )
    if archive_returncode != 0:
        raise ValueError(
            f"cannot extract package {relative_path} at revision {revision!r}: {archive_stderr or 'git archive failed'}"
        )
    if extracted.returncode != 0:
        tar_stderr = extracted.stderr.decode("utf-8", errors="replace").strip()
        raise ValueError(
            f"cannot extract package {relative_path} at revision {revision!r}: {tar_stderr or 'tar extraction failed'}"
        )

    extracted_package = temporary_root / relative_path
    if not extracted_package.is_dir():
        raise ValueError(
            f"cannot extract package {relative_path} at revision {revision!r}: path does not exist at that revision"
        )
    return extracted_package


def _provenance_counts(records: dict[str, Any], package_path: Path) -> dict[str, int]:
    package = load_story_package(package_path)
    counts = {"reconstructed": 0, "recorded": 0}
    for run in records.get("runs", []):
        if not isinstance(run, dict):
            continue
        judged_turns = judge_turns(run.get("turns", []), run.get("scene_transitions", []), package)
        for turn in judged_turns:
            provenance = turn.get("story_text_provenance")
            if provenance in counts:
                counts[provenance] += 1
    return counts


def _judgment_turns(result: dict[str, Any], records: dict[str, Any]) -> list[tuple[Any, Any, dict[str, Any]]]:
    judged_runs = result.get("judgments", [])
    runs = records.get("runs", [])
    entries: list[tuple[Any, Any, dict[str, Any]]] = []
    if not isinstance(judged_runs, list):
        return entries
    for index, judged_run in enumerate(judged_runs):
        if not isinstance(judged_run, dict):
            continue
        source_run = runs[index] if isinstance(runs, list) and index < len(runs) else {}
        if not isinstance(source_run, dict):
            source_run = {}
        replicate = judged_run.get("replicate", source_run.get("replicate", index + 1))
        turns = judged_run.get("turns", [])
        if not isinstance(turns, list):
            continue
        for turn_index, turn in enumerate(turns):
            if not isinstance(turn, dict):
                continue
            turn_number = turn.get("turn", turn.get("turn_number", turn_index + 1))
            entries.append((replicate, turn_number, turn))
    return entries


def _yes_counts(result: dict[str, Any], records: dict[str, Any], criteria: tuple[str, ...]) -> dict[str, int]:
    counts = {criterion: 0 for criterion in criteria}
    for _, _, turn in _judgment_turns(result, records):
        for criterion in criteria:
            if turn.get(criterion) == "yes":
                counts[criterion] += 1
    return counts


def _deltas(
    original: dict[str, Any], rejudged: dict[str, Any], records: dict[str, Any], criteria: tuple[str, ...]
) -> list[dict[str, Any]]:
    original_entries = _judgment_turns(original, records)
    rejudged_entries = _judgment_turns(rejudged, records)
    original_map = {(replicate, turn): value for replicate, turn, value in original_entries}
    rejudged_map = {(replicate, turn): value for replicate, turn, value in rejudged_entries}
    keys = list(dict.fromkeys([(replicate, turn) for replicate, turn, _ in original_entries]))
    keys.extend(key for key in rejudged_map if key not in keys)
    deltas = []
    for replicate, turn in keys:
        old = original_map.get((replicate, turn), {})
        new = rejudged_map.get((replicate, turn), {})
        for criterion in criteria:
            original_answer = old.get(criterion)
            rejudge_answer = new.get(criterion)
            if original_answer != rejudge_answer:
                deltas.append(
                    {
                        "replicate": replicate,
                        "turn": turn,
                        "criterion": criterion,
                        "original": original_answer,
                        "rejudge": rejudge_answer,
                    }
                )
    return deltas


def _summary_for_judge(
    name: str,
    rejudged: dict[str, Any],
    records: dict[str, Any],
    source_records: Path,
) -> dict[str, Any]:
    filename, criteria = JUDGES[name]
    original = _read_records(source_records / filename)
    return {
        "judge_calls": rejudged.get("judge_calls"),
        "yes_counts": _yes_counts(rejudged, records, criteria),
        "original_judge_calls": original.get("judge_calls"),
        "original_yes_counts": _yes_counts(original, records, criteria),
        "deltas": _deltas(original, rejudged, records, criteria),
    }


def rejudge(
    records_dir: Path,
    revision: str,
    output_dir: Path,
    *,
    judges: tuple[str, ...] = ("continuity", "fact"),
    dry_run: bool = False,
    repo_root: Path = REPOSITORY_ROOT,
) -> None:
    """Create a frozen-package records copy and optionally run selected judges."""

    records_dir = Path(records_dir)
    output_dir = Path(output_dir)
    if records_dir.resolve() == output_dir.resolve():
        raise ValueError("OUTDIR must differ from DIR")
    unknown = [name for name in judges if name not in JUDGES]
    if unknown:
        raise ValueError(f"unknown judge(s): {', '.join(unknown)}")

    source_records_path = records_dir / "all-turn-records.json"
    records = _read_records(source_records_path)
    original_package_path = records.get("package_path")
    if not isinstance(original_package_path, str) or not original_package_path:
        raise ValueError("all-turn-records.json must contain a string package_path")

    extracted_package = extract_package(repo_root, Path(original_package_path), revision)
    copied_records = copy.deepcopy(records)
    copied_records["package_path"] = str(extracted_package)
    copied_records["rejudge"] = {
        "source_records": str(records_dir),
        "revision": revision,
        "original_package_path": original_package_path,
        "provenance": "reconstructed",
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    input_path = output_dir / "all-turn-records.json"
    _write_json(input_path, copied_records)

    if dry_run:
        for name in judges:
            print(f"Dry-run: would run {name} judges -> {output_dir / JUDGES[name][0]}")
        return

    results: dict[str, dict[str, Any]] = {}
    for name in judges:
        filename, _ = JUDGES[name]
        runner = _judge_runner(name)
        output_path = output_dir / filename
        result = runner(input_path, output_path)
        if not isinstance(result, dict):
            raise ValueError(f"{name} judge returned a non-object result")
        _write_json(output_path, result)
        results[name] = result

    summary = {
        "story_text_provenance": _provenance_counts(copied_records, extracted_package),
        "judges": {
            name: _summary_for_judge(name, result, copied_records, records_dir) for name, result in results.items()
        },
    }
    _write_json(output_dir / "rejudge-summary.json", summary)


def _judges_argument(value: str) -> tuple[str, ...]:
    names = tuple(part.strip() for part in value.split(",") if part.strip())
    unknown = [name for name in names if name not in JUDGES]
    if not names or unknown:
        raise argparse.ArgumentTypeError("judges must be a comma-separated list of continuity and fact")
    return names


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=Path, required=True, metavar="DIR")
    parser.add_argument("--revision", required=True, metavar="GITREV")
    parser.add_argument("--out", type=Path, required=True, dest="output_dir", metavar="OUTDIR")
    parser.add_argument("--judges", type=_judges_argument, default=("continuity", "fact"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    rejudge(args.records, args.revision, args.output_dir, judges=args.judges, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
