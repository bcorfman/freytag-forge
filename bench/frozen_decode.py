"""Decode and validate saved narrator replies without contacting a model."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any

from bench.core import load_variation
from bench.frozen_prompts import _prefix_states, _variation_path
from storygame.runtime.capture import capture_prompt_variant
from storygame.runtime.contracts import RuntimeContractError, parse_turn_proposal
from storygame.runtime.item_facts import _MATCH_SYSTEM, ItemFactsProvider
from storygame.runtime.knowledge import KnowledgeProjector
from storygame.runtime.narration_safety import NarrationSafetyValidator
from storygame.runtime.validation import ProgressionValidator, ProposalValidationError, SelectedRevealResolver

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VARIATION = ROOT / "bench" / "variations" / "richer-3a-candidate.json"
SCENE = "3A"


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _strict_parse(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return False
    return True


def _body_for_row(row: dict[str, Any]) -> bytes:
    raw = row.get("raw")
    narration = row.get("narration")
    if isinstance(raw, bytes):
        return raw
    if isinstance(raw, str) and raw:
        try:
            decoded = json.loads(raw)
        except json.JSONDecodeError:
            decoded = None
        if isinstance(decoded, dict) and ("narration" in decoded or "segments" in decoded):
            return raw.encode("utf-8")
    if isinstance(narration, str):
        return json.dumps({"narration": narration}, ensure_ascii=False).encode("utf-8")
    if isinstance(raw, str):
        return raw.encode("utf-8")
    raise ValueError("row has neither a saved raw body nor a narration string")


def _summary_fact(value: object) -> dict[str, object]:
    if isinstance(value, str):
        return {"place": value, "holder": None, "condition": []}
    if not isinstance(value, dict):
        return {"place": None, "holder": None, "condition": []}
    condition = value.get("condition", [])
    return {
        "place": value.get("place"),
        "holder": value.get("held_by"),
        "condition": copy.deepcopy(condition) if isinstance(condition, list) else condition,
    }


def _proposed_facts(raw: object) -> dict[str, dict[str, object]]:
    if not isinstance(raw, dict):
        return {}
    return {str(name): _summary_fact(value) for name, value in raw.items()}


def _true_fact_ids(state) -> list[str]:
    return sorted(
        fact.predicate
        for fact in state.facts.asserted
        if fact.subject == "story" and str(fact.value).casefold() == "true"
    )


def _variation_for(frozen: dict[str, Any] | None, variation_path: Path | None):
    if variation_path is not None:
        return load_variation(variation_path), f"variation:{variation_path}"
    if frozen is not None and isinstance(frozen.get("variation"), str):
        path = _variation_path(frozen["variation"])
        return load_variation(path), f"variation:{path}"
    if DEFAULT_VARIATION.is_file():
        return load_variation(DEFAULT_VARIATION), f"default variation:{DEFAULT_VARIATION}"
    return None, "none"


def _endpoint_map(frozen: dict[str, Any] | None) -> dict[int, dict[str, Any]]:
    if not isinstance(frozen, dict) or not isinstance(frozen.get("endpoints"), list):
        return {}
    return {
        endpoint["n"]: endpoint
        for endpoint in frozen["endpoints"]
        if isinstance(endpoint, dict) and isinstance(endpoint.get("n"), int)
    }


def _context_for(
    row: dict[str, Any],
    *,
    frozen: dict[str, Any] | None,
    variation,
    variation_source: str,
):
    if variation is None:
        return None, "no story variation available"
    number = row.get("n")
    if isinstance(number, bool) or not isinstance(number, int) or number < 1:
        return None, "row has no positive endpoint number"
    try:
        states, inputs = _prefix_states(variation, [number])
    except (LookupError, ValueError) as error:
        return None, f"could not rebuild endpoint state: {error}"
    endpoint = _endpoint_map(frozen).get(number, {})
    command = row.get("command") or endpoint.get("command")
    if not isinstance(command, str) or not command:
        command = inputs[number - 1]
    state = states[number - 1]
    expected = endpoint.get("committed_after_prefix")
    mismatch = None
    if isinstance(expected, list) and sorted(expected) != _true_fact_ids(state):
        mismatch = {
            "saved": sorted(str(item) for item in expected),
            "rebuilt": _true_fact_ids(state),
        }
    return {
        "state": state,
        "command": command,
        "source": variation_source,
        "saved_committed_after_prefix": expected,
        "committed_prefix_mismatch": mismatch,
    }, None


def _provider(state, body: bytes):
    provider = ItemFactsProvider(
        worker_url="offline://saved-reply",
        token="",
        state=state,
        projector=KnowledgeProjector(),
        prompt_variant=capture_prompt_variant(state.package),
        item_facts={},
        mode="single_call",
        seed_from_package=True,
        held_by=True,
        semantic_ask=None,
    )

    def send(payload: dict[str, object]) -> bytes:
        if payload.get("system") == _MATCH_SYSTEM:
            return json.dumps({"refers": [], "same_as": {}, "kind": {}}).encode("utf-8")
        return body

    provider._send_http = send
    return provider


def _self_custody(raw: object, provider: ItemFactsProvider) -> bool:
    if not isinstance(raw, dict):
        return False
    world = provider._world()
    for name, entry in raw.items():
        if not isinstance(entry, dict) or not isinstance(entry.get("held_by"), str):
            continue
        holder = entry["held_by"].strip()
        entity_id = world.resolve(name) if isinstance(name, str) else None
        holder_id = world.resolve(holder)
        if (entity_id is not None and entity_id == holder_id) or (
            isinstance(name, str) and name.strip().casefold() == holder.casefold()
        ):
            return True
    return False


def _decode(provider: ItemFactsProvider, body: bytes) -> tuple[object, dict[str, object]]:
    before_recovery = provider.recovery_count
    decoded = provider._request({"system": "offline frozen decode", "user": "saved reply"})
    if not isinstance(decoded, dict):
        raise RuntimeContractError("decoded response is not an object")
    segments = decoded.get("segments")
    kinds = (
        [segment.get("kind") for segment in segments if isinstance(segment, dict)] if isinstance(segments, list) else []
    )
    return decoded, {
        "segments_count": len(segments) if isinstance(segments, list) else 0,
        "segment_kinds": kinds,
        "recovered": provider.recovery_count > before_recovery,
        "exception_type": None,
        "exception_message": None,
    }


def _validate(decoded: object, context: dict[str, Any] | None) -> tuple[dict[str, object], object | None]:
    if context is None:
        return {
            "status": "unavailable",
            "reason": "no rebuilt engine state",
            "code": None,
            "engine_state_rebuilt": False,
        }, None
    state = copy.deepcopy(context["state"])
    projector = KnowledgeProjector()
    command = context["command"]
    try:
        provider_proposal = parse_turn_proposal(decoded)
        projection = projector.project(state, "player", command)
        resolved, _ = SelectedRevealResolver(state.package).resolve(
            state,
            projection,
            provider_proposal,
            projector,
            command,
        )
        ProgressionValidator(state.package).validate_effects(state, resolved)
        candidate_state = copy.deepcopy(state)
        candidate_state.apply_proposal(resolved, apply_world=False)
        NarrationSafetyValidator().validate(state, candidate_state, resolved, projector, command)
    except (ProposalValidationError, RuntimeContractError, ValueError) as error:
        return {
            "status": "rejected",
            "reason": str(error),
            "code": getattr(error, "code", None),
            "engine_state_rebuilt": True,
        }, None
    return {
        "status": "accepted",
        "reason": None,
        "code": None,
        "engine_state_rebuilt": True,
    }, resolved


def _apply_facts(provider: ItemFactsProvider, raw: object, *, command: str, narration: str) -> dict[str, object]:
    before = provider.item_facts
    _previous, issues = provider.apply_item_facts(raw, player_input=command, story=narration)
    names = set(raw) if isinstance(raw, dict) else set()
    names.update(provider._changed_last_turn)
    after = provider.facts_for_names(names, structural=True) if names else {}
    before_selected = {name: before[name] for name in names if name in before}
    changed = {name: _summary_fact(value) for name, value in after.items() if before_selected.get(name) != value}
    return {
        "issues": list(issues),
        "changed": sorted(provider._changed_last_turn),
        "facts_after": {str(name): _summary_fact(value) for name, value in after.items()},
        "would_commit": changed,
    }


def _analyze_row(
    row: dict[str, Any],
    *,
    frozen: dict[str, Any] | None,
    variation,
    variation_source: str,
    contexts: dict[int, tuple[dict[str, Any] | None, str | None]],
) -> dict[str, object]:
    result: dict[str, object] = {
        "n": row.get("n"),
        "sample": row.get("sample"),
        "strict_json_parse": _strict_parse(row.get("narration")),
        "decoder_result": {},
        "validation_result": {},
        "proposed_item_facts": {},
        "item_fact_application": {"issues": [], "changed": [], "facts_after": {}, "would_commit": {}},
        "self_custody": False,
    }
    body = _body_for_row(row)
    try:
        number = row.get("n")
        if not isinstance(number, int) or number not in contexts:
            contexts[number] = _context_for(
                row,
                frozen=frozen,
                variation=variation,
                variation_source=variation_source,
            )
        context, context_error = contexts.get(number, (None, "no context"))
        provider_state = copy.deepcopy(context["state"]) if context is not None else None
        if provider_state is None:
            raise RuntimeContractError(context_error or "no validation context")
        provider = _provider(provider_state, body)
        decoded, decoder_result = _decode(provider, body)
        if not result["strict_json_parse"]:
            decoder_result["recovered"] = True
        result["decoder_result"] = decoder_result
        pending = provider.pending_item_facts()
        result["proposed_item_facts"] = _proposed_facts(pending)
        result["self_custody"] = _self_custody(pending, provider)
        validation, resolved = _validate(decoded, context)
        if context is not None:
            validation["context"] = {
                "source": context["source"],
                "command": context["command"],
                "saved_committed_after_prefix": context["saved_committed_after_prefix"],
                "committed_prefix_mismatch": context["committed_prefix_mismatch"],
            }
        result["validation_result"] = validation
        if resolved is not None and validation["status"] == "accepted":
            result["item_fact_application"] = _apply_facts(
                provider,
                pending,
                command=context["command"],
                narration=resolved.narration,
            )
    except Exception as error:  # report one bad saved reply without stopping the batch
        decoder_result = result["decoder_result"]
        if not decoder_result:
            decoder_result = {
                "segments_count": 0,
                "segment_kinds": [],
                "recovered": False,
            }
        decoder_result.update({"exception_type": type(error).__name__, "exception_message": str(error)})
        result["decoder_result"] = decoder_result
        result["validation_result"] = {
            "status": "rejected",
            "reason": str(error),
            "code": getattr(error, "code", None),
            "engine_state_rebuilt": False,
        }
    return result


def analyze_rows(
    rows: list[dict[str, Any]],
    *,
    frozen_path: Path | str | None = None,
    frozen: dict[str, Any] | None = None,
    variation_path: Path | str | None = None,
) -> dict[str, object]:
    """Analyze replay rows using the production decoder and validation boundary."""

    if frozen is None and frozen_path is not None:
        frozen = _read_json(Path(frozen_path))
    variation, variation_source = _variation_for(frozen, Path(variation_path) if variation_path else None)
    contexts: dict[int, tuple[dict[str, Any] | None, str | None]] = {}
    records: list[dict[str, object]] = []
    skipped: list[dict[str, object]] = []
    for row in rows:
        if not isinstance(row, dict):
            skipped.append({"n": None, "sample": None, "reason": "row is not an object"})
            continue
        if row.get("error"):
            skipped.append({"n": row.get("n"), "sample": row.get("sample"), "reason": str(row["error"])})
            continue
        records.append(
            _analyze_row(
                row,
                frozen=frozen,
                variation=variation,
                variation_source=variation_source,
                contexts=contexts,
            )
        )
    summary = {
        "processed": len(records),
        "skipped": len(skipped),
        "strict_json_parse_true": sum(record["strict_json_parse"] is True for record in records),
        "strict_json_parse_false": sum(record["strict_json_parse"] is False for record in records),
        "decoder_recovered": sum(record["decoder_result"].get("recovered") is True for record in records),
        "decoder_errors": sum(record["decoder_result"].get("exception_type") is not None for record in records),
        "validation_accepted": sum(record["validation_result"].get("status") == "accepted" for record in records),
        "validation_rejected": sum(record["validation_result"].get("status") == "rejected" for record in records),
        "validation_unavailable": sum(record["validation_result"].get("status") == "unavailable" for record in records),
        "self_custody": sum(record["self_custody"] is True for record in records),
    }
    limits = (
        "Production narration decoding, proposal parsing, selected_knowledge_ids validation, narration safety, "
        "and item_facts application were exercised offline. Item-fact application ran on a deep-copied rebuilt "
        "state and reports what would change; no model call, network request, live committed runtime state, "
        "observation verifier, capture lifecycle, or later turn/pacing effects were exercised."
    )
    return {
        "rows": records,
        "skipped": skipped,
        "summary": summary,
        "limits": limits,
        "validation_context": {
            "source": variation_source,
            "frozen_state_used": frozen is not None,
            "rebuilt_endpoint_states": True,
        },
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m bench.frozen_decode")
    parser.add_argument("rows", type=Path)
    parser.add_argument("--frozen", type=Path)
    parser.add_argument("--variation", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    report = analyze_rows(
        _read_json(args.rows),
        frozen_path=args.frozen,
        variation_path=args.variation,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
