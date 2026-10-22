"""Offline-first frozen-prompt replay for the Stage 7 3C C1 screen."""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from bench.core import load_variation, package_and_state

ROOT = Path(__file__).resolve().parents[3]
VARIATION = ROOT / "bench/variations/stage7-3c-recall-live.json"
BROADCAST_VARIATION = ROOT / "bench/variations/stage7-3c-broadcast-live.json"
RECORDED = ROOT / "bench/results/stage7-3c-blind-raw-f918c663/attempt-1/e2e-blind-player-bundles.json"
OLD_C1 = (
    "Kristin restores power to drainage pumps and holds one watertight barrier while Michelle leads captives "
    "through the maintenance tunnel."
)
NEW_C1 = "The drainage pumps have power. The evacuation route is open."
DEFAULT_MAX_REQUESTS = 48
OLD_C1_TRACE = "holds one watertight barrier"
C2_TEXT = (
    "Michelle uses the senior official’s authorization to release the surface gates while Brandon keeps the relay "
    "open and water closes the facility around them."
)
BR1_DELIVERY_TEXT = (
    "The prisoners capture Rebecca after the archive is copied beyond her reach. "
    "Charles escapes his remote command site."
)
PUMP_NEED_TEXT = "The drainage pumps need power. Water rises around the drainage pump controls."
BROADCAST_OLD_LITERAL = (
    "Michelle broadcasts captives, JANUS records, planning sessions, and detention locations to independent networks."
)
BROADCAST_NEW_LITERAL = (
    "Independent networks have the captives' video, JANUS records, planning sessions, and detention locations."
)


def recorded_request() -> dict[str, str]:
    data = json.loads(RECORDED.read_text(encoding="utf-8"))
    bundle = data["replicates"][0]["scenes"][8]["bundles"]
    turn = next(item for item in bundle if item["turn"] == 6)
    request = turn["attempt_bundle"]["stages"][0]["request"]
    if set(request) != {"system", "user"} or not all(isinstance(request[key], str) for key in request):
        raise ValueError("recorded turn-6 request is not a system/user prompt")
    return {"system": request["system"], "user": request["user"]}


def _broadcast_strings() -> tuple[str, str]:
    definition = json.loads(BROADCAST_VARIATION.read_text(encoding="utf-8"))
    try:
        replacement = definition["overrides"]["knowledge.yaml"]["replacements"][0]
        raw_old = replacement["old"]
        raw_new = replacement["new"]
        old = raw_old.removeprefix("statement: '").removesuffix("'")
        new = raw_new.removeprefix("statement: '").removesuffix("'").replace("''", "'")
    except (KeyError, IndexError, TypeError, AttributeError) as error:
        raise AssertionError("broadcast variation has no usable knowledge replacement") from error
    if old != BROADCAST_OLD_LITERAL or new != BROADCAST_NEW_LITERAL:
        raise AssertionError("broadcast variation strings differ from the frozen A-R1 literals")
    return old, new


def build_requests(experiment: str = "c1") -> tuple[dict[str, str], dict[str, str], int]:
    if experiment not in {"c1", "broadcast"}:
        raise ValueError(f"unknown experiment: {experiment}")
    pump = recorded_request()
    recording = recorded_request()
    if pump != recording:
        raise AssertionError("pump arm differs from the recorded request")
    if experiment == "broadcast":
        old, expected_new = _broadcast_strings()
        variation = load_variation(BROADCAST_VARIATION)
        package, _ = package_and_state(variation, "3C")
        new_statement = package.knowledge_indexes.by_id["k_sl_3c_a_r1"].statement
        if new_statement != expected_new:
            raise AssertionError("broadcast variation C1 statement does not match its replacement")
        count = sum(value.count(old) for value in pump.values())
        if count != 3:
            raise AssertionError(f"recorded request contains {count} broadcast statements, expected 3")
        broadcast = {key: value.replace(old, new_statement) for key, value in pump.items()}
        broadcast_text = json.dumps(broadcast, ensure_ascii=False)
        if broadcast_text.count(old) != 0 or broadcast_text.count("Michelle broadcasts captives") != 0:
            raise AssertionError("old broadcast statement trace remains in broadcast arm")
        if broadcast_text.count(new_statement) != 3:
            raise AssertionError("broadcast arm does not contain exactly three replacement statements")
        return pump, broadcast, count
    variation = load_variation(VARIATION)
    package, _ = package_and_state(variation, "3C")
    new_statement = package.knowledge_indexes.by_id["k_sl_3c_c_r1"].statement
    if new_statement != NEW_C1:
        raise AssertionError("variation C1 statement does not match the frozen replay statement")
    count = sum(value.count(OLD_C1) for value in pump.values())
    if count == 0:
        raise AssertionError("recorded request contains no C1 statement")
    recall = {key: value.replace(OLD_C1, new_statement) for key, value in pump.items()}
    recall_text = json.dumps(recall, ensure_ascii=False)
    if OLD_C1 in recall_text or OLD_C1_TRACE in recall_text:
        raise AssertionError("old C1 statement trace remains in recall arm")
    if recall["user"].count(new_statement) != count:
        raise AssertionError("recall arm does not contain one new statement per recorded C1 occurrence")
    return pump, recall, count


def _package_occurrences() -> list[dict[str, object]]:
    package_root = ROOT / "data/stories/continuity-initiative"
    variation = load_variation(VARIATION)
    loaded_root = Path(variation["_package_path"])
    hits: list[dict[str, object]] = []
    for path in sorted(package_root.rglob("*")):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        loaded_path = loaded_root / path.relative_to(package_root)
        loaded_text = loaded_path.read_text(encoding="utf-8", errors="replace") if loaded_path.is_file() else ""
        loaded_lines = loaded_text.splitlines()
        for line_number, line in enumerate(text.splitlines(), 1):
            if not any(
                term in line.casefold() for term in ("drainage pumps", "watertight barrier", "maintenance tunnel")
            ):
                continue
            loaded_line = loaded_lines[line_number - 1] if line_number <= len(loaded_lines) else ""
            if line == loaded_line:
                hits.append(
                    {
                        "file": str(path.relative_to(ROOT)),
                        "line": line_number,
                        "text": line,
                        "loaded_package_text": True,
                    }
                )
    return hits


def _write_dry(
    out: Path,
    pump: dict[str, str],
    recall: dict[str, str],
    occurrence_count: int,
    experiment: str = "c1",
) -> None:
    if experiment == "broadcast":
        old, new = _broadcast_strings()
        second_name = "broadcast"
    else:
        old, new = OLD_C1, NEW_C1
        second_name = "recall"
    out.joinpath("pump-request.json").write_text(json.dumps(pump, indent=2) + "\n", encoding="utf-8")
    out.joinpath(f"{second_name}-request.json").write_text(json.dumps(recall, indent=2) + "\n", encoding="utf-8")
    diff = difflib.unified_diff(
        json.dumps(pump, indent=2).splitlines(keepends=True),
        json.dumps(recall, indent=2).splitlines(keepends=True),
        fromfile="pump-request.json",
        tofile=f"{second_name}-request.json",
    )
    diff_text = "".join(diff)
    if any(
        line.startswith(("+", "-")) and not line.startswith(("+++", "---")) and old not in line and new not in line
        for line in diff_text.splitlines()
    ):
        raise AssertionError("dry-run diff contains a non-C1 change")
    out.joinpath("request.diff").write_text(diff_text, encoding="utf-8")
    variation = load_variation(BROADCAST_VARIATION if experiment == "broadcast" else VARIATION)
    package_path = Path(variation["_package_path"])
    summary = {
        "arms": {"pump": pump, second_name: recall},
        "requests": 0,
        "replacement_occurrences": occurrence_count,
        "isolation": {
            "pump_equals_recording": pump == recorded_request(),
            ("broadcast_trace_remaining" if experiment == "broadcast" else "recall_old_c1_remaining"): (
                "Michelle broadcasts captives" in json.dumps(recall)
                if experiment == "broadcast"
                else OLD_C1 in json.dumps(recall)
            ),
        },
        "network_calls": 0,
        "semantic_judge_calls": 0,
        "player_model_calls": 0,
        "unmodified_shipped_c1_occurrences": _package_occurrences(),
        "unmodified_occurrences_matter_for_loaded_package_text": any(
            bool(item["loaded_package_text"]) for item in _package_occurrences()
        ),
        "loaded_variation_package": str(package_path),
        "loaded_package_hash": _hash_package(package_path),
    }
    out.joinpath("summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    out.joinpath("failure.txt").write_text("dry-run: no failure; no network calls made\n", encoding="utf-8")


def _hash_package(path: Path) -> str:
    digest = hashlib.sha256()
    for item in sorted(path.rglob("*")):
        if item.is_file():
            digest.update(str(item.relative_to(path)).encode())
            digest.update(item.read_bytes())
    return digest.hexdigest()


def _is_budget(status: int | None, raw: str) -> bool:
    lowered = raw.casefold()
    return (
        status == 429
        or "ai_quota_exceeded" in lowered
        or "ai_daily_budget_exceeded" in lowered
        or "daily budget" in lowered
        or "daily_budget" in lowered
        or "budget exceeded" in lowered
    )


def _send(payload: dict[str, str], url: str, token: str) -> tuple[int, str]:
    headers = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(url, data=json.dumps(payload).encode(), headers=headers, method="POST")
    try:
        with urlopen(request, timeout=float(os.environ.get("CLOUDFLARE_TIMEOUT", "15"))) as response:  # noqa: S310
            return response.status, response.read().decode()
    except HTTPError as error:
        return error.code, error.read().decode(errors="replace")


def _parse(raw: str) -> tuple[str, list[str]]:
    body = json.loads(raw)
    if isinstance(body, dict) and isinstance(body.get("narration"), str):
        body = json.loads(body["narration"])
    segments = body["segments"]
    if not isinstance(segments, list):
        raise ValueError("reply has no segments list")
    return json.dumps(body, ensure_ascii=False), [
        item["text"] for item in segments if isinstance(item, dict) and isinstance(item.get("text"), str)
    ]


def replay(
    args: argparse.Namespace,
    pump: dict[str, str],
    recall: dict[str, str],
    out: Path,
    experiment: str = "c1",
) -> None:
    url = os.environ.get("CLOUDFLARE_WORKER_URL")
    if not url:
        raise RuntimeError("CLOUDFLARE_WORKER_URL is required for live replay")
    rows: list[dict[str, object]] = []
    calls = 0
    stopped = "complete"
    for index in range(args.n):
        second_arm = "broadcast" if experiment == "broadcast" else "recall"
        for arm, payload in (("pump", pump), (second_arm, recall)):
            if calls >= args.max_requests:
                stopped = "request cap reached"
                break
            calls += 1
            row_requests = 1
            status, raw = _send(payload, url, os.environ.get("CLOUDFLARE_WORKER_TOKEN", ""))
            row: dict[str, object] = {
                "arm": arm,
                "index": index,
                "request_count": row_requests,
                "raw_reply_text": raw,
                "parsed_segments_text": [],
                "error": None,
            }
            if _is_budget(status, raw):
                row["error"] = f"budget response (HTTP {status})"
                rows.append(row)
                stopped = "budget response"
                break
            try:
                _, segments = _parse(raw)
                row["parsed_segments_text"] = segments
            except Exception as error:  # noqa: BLE001 - row-level replay evidence
                row["error"] = f"{type(error).__name__}: {error}"
                if calls < args.max_requests:
                    calls += 1
                    recovery = dict(payload)
                    recovery["system"] += (
                        "\nYour previous reply was not valid JSON. Return only valid JSON with a segments list."
                    )
                    recovery_status, recovery_raw = _send(recovery, url, os.environ.get("CLOUDFLARE_WORKER_TOKEN", ""))
                    row_requests += 1
                    row["request_count"] = row_requests
                    row["raw_reply_text"] += "\n[recovery]\n" + recovery_raw
                    if _is_budget(recovery_status, recovery_raw):
                        row["error"] = f"budget response (HTTP {recovery_status})"
                        stopped = "budget response"
                    else:
                        try:
                            _, row["parsed_segments_text"] = _parse(recovery_raw)
                        except Exception as recovery_error:  # noqa: BLE001
                            row["error"] += f"; recovery {type(recovery_error).__name__}: {recovery_error}"
                else:
                    stopped = "request cap reached"
            rows.append(row)
        if stopped != "complete":
            break
    out.joinpath("rows.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8"
    )
    out.joinpath("summary.json").write_text(
        json.dumps(
            {
                "rows": len(rows),
                "requests": calls,
                "max_requests": args.max_requests,
                "stop": stopped,
                "network_calls": calls,
                "semantic_judge_calls": 0,
                "player_model_calls": 0,
                "unmodified_shipped_c1_occurrences": _package_occurrences(),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    if stopped != "complete":
        out.joinpath("failure.txt").write_text(stopped + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--confirm", action="store_true")
    parser.add_argument("--experiment", choices=("c1", "broadcast"), default="c1")
    parser.add_argument("--max-requests", type=int, default=DEFAULT_MAX_REQUESTS)
    args = parser.parse_args()
    if args.n < 1 or args.n > 12:
        parser.error("--n must be between 1 and 12")
    if args.max_requests < 1:
        parser.error("--max-requests must be positive")
    if not args.dry_run and not args.confirm:
        parser.error("live replay requires --confirm; no network calls were made")
    args.out.mkdir(parents=True, exist_ok=True)
    pump, recall, count = build_requests(args.experiment)
    if args.dry_run:
        _write_dry(args.out, pump, recall, count, args.experiment)
    else:
        replay(args, pump, recall, args.out, args.experiment)


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))
    main()
