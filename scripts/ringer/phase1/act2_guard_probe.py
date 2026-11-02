"""Bounded Act 2A narration-guard probe with an offline prompt mode."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from collections import Counter
from contextlib import ExitStack, suppress
from pathlib import Path
from typing import Any
from unittest import mock

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts/ringer/stage7"))

try:
    from . import act2_probe
except ImportError:
    import act2_probe

from door_transport import SpendBudget, counted_provider  # noqa: E402

from bench.core import load_variation, provider_for  # noqa: E402
from storygame.runtime.cloudflare import CloudflareTurnProvider  # noqa: E402
from storygame.runtime.engine import RuntimeEngine  # noqa: E402
from storygame.runtime.validation import ProposalValidationError  # noqa: E402
from storygame.story_package.loader import load_story_package  # noqa: E402
from storygame.story_package.models import term_lookup_forms  # noqa: E402

ARMS = ("control", "legacy", "leakterms")
FIXED_COMMAND = "Inspect my work order beside the facility gate."
SCENE = "2A"
DEFAULT_N = 12
CAP = 60
PACKAGE_SOURCE = ROOT / "data/stories/continuity-initiative"
VARIATION_SOURCE = ROOT / "bench/variations/phase1-slice-current.json"

_LEGACY_REPLACEMENTS = (
    (
        "  pressure: Prove the cooling system is failing to get inside",
        "  pressure: Prove the cooling fault is real to get inside",
    ),
    (
        "  statement: Kristin and Brandon are at the facility gate and must prove the cooling system is failing "
        "to get inside.",
        "  statement: Kristin and Brandon are at the facility gate and must prove the cooling fault is real "
        "to get inside.",
    ),
)
_LEGACY_PLOT_REPLACEMENT = (
    "objective: Get inside by proving the cooling system is failing",
    "objective: Get inside by proving the cooling fault is real",
)
_LEAK_LINES = {
    "k_sl_2a_c_r5": (
        "  leak_terms: [genuine cooling-water pressure fault, genuine pressure problem, genuine cooling fault, "
        "real ventilation fault, restricted infrastructure corridors, infrastructure corridors, restricted "
        "corridor access, console used]"
    ),
    "k_sl_2a_c_r6": (
        "  leak_terms: [restricted infrastructure corridors, infrastructure corridors, restricted corridor access, "
        "console used]"
    ),
}


class _NarrationSentinel(RuntimeError):
    pass


def _replace_once(text: str, old: str, new: str, arm: str) -> str:
    count = text.count(old)
    if count != 1:
        raise ValueError(f"{arm}: expected exactly one replacement target, found {count}: {old!r}")
    return text.replace(old, new)


def _insert_leak_term(text: str, knowledge_id: str, leak_line: str, arm: str) -> str:
    marker = f"- id: {knowledge_id}"
    if text.count(marker) != 1:
        raise ValueError(f"{arm}: expected exactly one block marker, found {text.count(marker)}: {marker!r}")
    start = text.index(marker)
    end = text.find("\n- id:", start + len(marker))
    block = text[start:] if end == -1 else text[start:end]
    if "\n  leak_terms:" in block or block.startswith("  leak_terms:"):
        raise ValueError(f"{arm}: {knowledge_id} already has leak_terms")
    line_end = text.find("\n", start)
    if line_end == -1:
        raise ValueError(f"{arm}: marker has no following line: {marker!r}")
    return text[: line_end + 1] + leak_line + "\n" + text[line_end + 1 :]


def build_arm_package(arm: str, workdir: Path) -> Path:
    """Copy the story package and apply exactly the requested arm edits."""

    if arm not in ARMS:
        raise ValueError(f"unknown arm: {arm}")
    destination = workdir / arm
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(PACKAGE_SOURCE, destination)
    if arm == "control":
        return destination

    knowledge_path = destination / "knowledge.yaml"
    knowledge = knowledge_path.read_text(encoding="utf-8")
    if arm == "legacy":
        for old, new in _LEGACY_REPLACEMENTS:
            knowledge = _replace_once(knowledge, old, new, arm)
        knowledge_path.write_text(knowledge, encoding="utf-8")
        plot_path = destination / "plot.md"
        plot = plot_path.read_text(encoding="utf-8")
        plot_path.write_text(_replace_once(plot, *_LEGACY_PLOT_REPLACEMENT, arm), encoding="utf-8")
    else:
        for knowledge_id, leak_line in _LEAK_LINES.items():
            knowledge = _insert_leak_term(knowledge, knowledge_id, leak_line, arm)
        knowledge_path.write_text(knowledge, encoding="utf-8")
    return destination


def _variation(package_path: Path) -> dict[str, Any]:
    variation = dict(load_variation(VARIATION_SOURCE))
    variation["_package_path"] = str(package_path)
    return variation


def _load_arm(arm: str, out: Path) -> tuple[Path, Any]:
    package_path = build_arm_package(arm, out / "package")
    try:
        package = load_story_package(package_path)
    except Exception as error:
        raise RuntimeError(f"{arm}: edited package failed to load: {error}") from error
    return package_path, package


def _capture_prompt(package: Any, variation: dict[str, Any]) -> str:
    state = act2_probe._state(package, SCENE)
    with mock.patch.dict(os.environ, {"CLOUDFLARE_WORKER_URL": "offline://act2-guard-probe"}, clear=False):
        provider = provider_for(state, variation)

    def request(self: CloudflareTurnProvider, payload: dict[str, object]) -> object:
        if payload.get("__freytag_request_budget") == "item_facts":
            return {"refers": [], "same_as": {}, "kind": {}}
        self.last_prompt = {"system": payload["system"], "user": payload["user"]}
        raise _NarrationSentinel

    engine = RuntimeEngine(state, provider)
    with ExitStack() as stack:
        stack.enter_context(
            mock.patch.object(
                CloudflareTurnProvider,
                "_request_item_facts",
                lambda self, payload: {"refers": [], "same_as": {}, "kind": {}},
            )
        )
        stack.enter_context(mock.patch.object(CloudflareTurnProvider, "_request", request))
        with suppress(_NarrationSentinel):
            engine.turn(FIXED_COMMAND)
    if not provider.last_prompt:
        raise AssertionError("offline narration transport was not reached")
    return "\n\n".join(str(provider.last_prompt[key]) for key in ("system", "user"))


def _dry_result(arm: str, package_path: Path, package: Any, variation: dict[str, Any]) -> dict[str, Any]:
    prompt = _capture_prompt(package, variation)
    leak_map = package.knowledge_indexes.leak_term_to_knowledge
    cooling_keys = term_lookup_forms("cooling fault")
    restricted_keys = term_lookup_forms("restricted infrastructure corridors")
    return {
        "mode": "dry",
        "arm": arm,
        "prompt_has_cooling_fault": "cooling fault" in prompt.casefold(),
        "leak_map_has_cooling_fault": any(key in leak_map for key in cooling_keys),
        "leak_map_has_restricted_infrastructure_corridors": any(key in leak_map for key in restricted_keys),
        "package": str(package_path),
    }


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _is_rejection(error: BaseException, engine: RuntimeEngine) -> bool:
    if isinstance(error, ProposalValidationError):
        return True
    return bool(getattr(getattr(engine, "last_attempt", None), "rejection", None))


def _sample(arm: str, package: Any, variation: dict[str, Any], budget: SpendBudget, sample: int) -> dict[str, Any]:
    state = act2_probe._state(package, SCENE)
    provider = provider_for(state, variation)
    engine = RuntimeEngine(state, provider)
    before_attempts = len(engine.attempts)
    row: dict[str, Any] = {
        "sample": sample,
        "result": "ok",
        "error_class": None,
        "error_message": None,
        "error_code": None,
        "error_term": None,
        "narration": None,
        "recovery_count": 0,
        "request_count": 0,
        "first_attempt_rejected": False,
    }
    try:
        with counted_provider(provider, budget):
            turn = engine.turn(FIXED_COMMAND)
        row["narration"] = "\n\n".join(segment.text for segment in turn.segments)
    except Exception as error:
        if isinstance(error, RuntimeError) and str(error).startswith("cloudflare request cap exhausted"):
            raise
        rejected = _is_rejection(error, engine)
        row["result"] = "rejected" if rejected else "transport_error"
        row["error_class"] = type(error).__name__
        row["error_message"] = str(error)
        row["error_code"] = getattr(error, "code", None)
        row["error_term"] = getattr(error, "term", None)
    finally:
        row["request_count"] = getattr(provider, "request_count", 0)
        row["recovery_count"] = getattr(provider, "recovery_count", 0)
        attempts = engine.attempts[before_attempts:]
        row["first_attempt_rejected"] = bool(attempts and getattr(attempts[0], "rejection", None))
    return row


def run(out: Path, arm: str, n: int, dry: bool, confirm: bool) -> int:
    if not 1 <= n <= DEFAULT_N:
        raise SystemExit("--n must be between 1 and 12")
    if not dry and not confirm:
        raise SystemExit("live mode requires --confirm")
    out.mkdir(parents=True, exist_ok=True)
    package_path, package = _load_arm(arm, out)
    variation = _variation(package_path)
    if dry:
        _write_json(out / "results.json", _dry_result(arm, package_path, package, variation))
        return 0

    budget = SpendBudget(limit=CAP, cloudflare_limit=CAP, player_limit=0)
    samples: list[dict[str, Any]] = []
    for sample_number in range(1, n + 1):
        try:
            samples.append(_sample(arm, package, variation, budget, sample_number))
        except RuntimeError as error:
            (out / "run-failure.txt").write_text(str(error) + "\n", encoding="utf-8")
            raise
        _write_json(
            out / "results.json",
            {
                "mode": "live",
                "arm": arm,
                "n": n,
                "command": FIXED_COMMAND,
                "samples": samples,
                "caps": {"cloudflare": CAP},
                "budget_events": budget.events,
            },
        )
    result_counts = Counter(row["result"] for row in samples)
    error_terms = Counter(row["error_term"] for row in samples if row["error_term"] is not None)
    _write_json(out / "summary.json", {"result": dict(result_counts), "error_term": dict(error_terms)})
    return 0


def check(out: Path, n: int, mode: str) -> list[str]:
    errors: list[str] = []
    try:
        results = json.loads((out / "results.json").read_text(encoding="utf-8"))
    except Exception as error:
        return [f"WHY cannot read results.json: {error}"]
    arm = results.get("arm")
    if mode == "dry":
        expected = {
            "control": (False, True, True),
            "legacy": (True, True, True),
            "leakterms": (False, False, True),
        }.get(arm)
        if results.get("mode") != "dry":
            errors.append("WHY dry results do not have mode dry")
        if expected is None:
            errors.append(f"WHY unknown dry arm: {arm!r}")
        elif (
            tuple(
                results.get(key)
                for key in (
                    "prompt_has_cooling_fault",
                    "leak_map_has_cooling_fault",
                    "leak_map_has_restricted_infrastructure_corridors",
                )
            )
            != expected
        ):
            errors.append(f"WHY dry booleans do not match expected values for {arm}")
        return errors

    if results.get("mode") != "live":
        errors.append("WHY live results do not have mode live")
    samples = results.get("samples", [])
    if len(samples) != n:
        errors.append(f"WHY expected {n} samples, found {len(samples)}")
    valid = {"ok", "rejected", "transport_error"}
    for row in samples:
        if row.get("result") not in valid:
            errors.append(f"WHY invalid sample result: {row.get('result')!r}")
        if row.get("result") == "ok" and not row.get("narration"):
            errors.append(f"WHY sample {row.get('sample')} has empty ok narration")
        if row.get("result") != "ok" and row.get("narration") is not None:
            errors.append(f"WHY sample {row.get('sample')} has narration for a non-ok result")
    events = results.get("budget_events", [])
    if sum(event.get("kind") == "cloudflare" for event in events) > CAP:
        errors.append("WHY cloudflare budget exceeds 60")
    if any(event.get("kind") == "raw_player" for event in events):
        errors.append("WHY budget contains a raw_player event")
    try:
        summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
        counts = Counter(row.get("result") for row in samples)
        if summary.get("result") != dict(counts):
            errors.append("WHY summary result counts disagree with samples")
        terms = Counter(row.get("error_term") for row in samples if row.get("error_term") is not None)
        if summary.get("error_term") != dict(terms):
            errors.append("WHY summary error-term counts disagree with samples")
    except Exception as error:
        errors.append(f"WHY cannot read summary.json: {error}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--arm", choices=ARMS)
    parser.add_argument("--n", type=int, default=DEFAULT_N)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--dry", action="store_true", help="check a dry-run results file")
    parser.add_argument("--confirm", action="store_true")
    parser.add_argument("--check", nargs=2, metavar=("OUT", "N"))
    args = parser.parse_args(argv)
    if args.check:
        errors = check(Path(args.check[0]), int(args.check[1]), "dry" if args.dry_run or args.dry else "live")
        for error in errors:
            print(error)
        return int(bool(errors))
    if args.arm is None or args.out is None:
        parser.error("--arm and --out are required unless --check is used")
    return run(args.out, args.arm, args.n, args.dry_run, args.confirm)


if __name__ == "__main__":
    raise SystemExit(main())
