"""Classify failing turns by deterministic signals, with a bounded fallback."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from collections import Counter
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from factory.followups import _safe_id
from factory.guard import Caps, ModelGuard, SpendLedger, guarded_call
from factory.line import StationHandler, StationResult
from factory.stations.deliver import _atomic_json_write, _record
from factory.stations.planner import _load_config, claude_call, extract_plan
from storygame.story_package.loader import load_story_package

from .wiring import _story_root

CAUSES = (
    "match_miss_on_offered_candidate",
    "claim_not_offered",
    "lead_outside_scene",
    "unknown_object",
    "no_authored_outcome",
    "unclear",
)
DIAGNOSE_VERSION = "diagnose-v1"
DIAGNOSE_MODEL_ID = "claude-sonnet-5-5"
DIAGNOSE_EFFORT = "high"

STOPWORDS = frozenset(
    {
        "a",
        "about",
        "after",
        "again",
        "all",
        "an",
        "and",
        "around",
        "as",
        "at",
        "away",
        "back",
        "be",
        "before",
        "beneath",
        "by",
        "can",
        "could",
        "do",
        "for",
        "from",
        "get",
        "go",
        "her",
        "his",
        "i",
        "in",
        "into",
        "is",
        "it",
        "its",
        "look",
        "my",
        "of",
        "on",
        "open",
        "or",
        "out",
        "over",
        "search",
        "take",
        "that",
        "the",
        "their",
        "them",
        "there",
        "this",
        "through",
        "to",
        "under",
        "up",
        "we",
        "what",
        "when",
        "where",
        "which",
        "who",
        "with",
        "would",
        "you",
        "your",
        "ask",
        "carry",
        "check",
        "drive",
        "enter",
        "examine",
        "feel",
        "find",
        "head",
        "inspect",
        "investigate",
        "listen",
        "notice",
        "question",
        "read",
        "retrieve",
        "see",
        "study",
        "talk",
        "tell",
        "watch",
    }
)
ACTING_VERBS = frozenset(
    {
        "ask",
        "carry",
        "check",
        "close",
        "drive",
        "enter",
        "examine",
        "feel",
        "find",
        "go",
        "head",
        "inspect",
        "investigate",
        "leave",
        "listen",
        "look",
        "notice",
        "open",
        "play",
        "pull",
        "question",
        "read",
        "retrieve",
        "search",
        "see",
        "study",
        "take",
        "talk",
        "tell",
        "type",
        "watch",
        "use",
    }
)
DIAGNOSE_BRIEF = """Diagnose each failing turn using one cause.

match_miss_on_offered_candidate: a listed candidate matched, but nothing was committed.
claim_not_offered: the command satisfies an authored claim that was not offered.
lead_outside_scene: the command names a story entity that belongs to another scene.
unknown_object: a meaningful command word is absent from the story vocabulary.
no_authored_outcome: the command concerns this scene, but no authored outcome was found.
unclear: use this only when the first five causes cannot be supported by the evidence.

Return ONE JSON object mapping every listed turn key to an object with exactly a cause from
the first five causes and one plain sentence explaining why. Return nothing else."""


@dataclass(frozen=True)
class ClassifierReply:
    """The classifier's text and provider-reported token count."""

    text: str
    tokens: int


_WORD_RE = re.compile(r"[a-z0-9]+")


def _words(value: object) -> set[str]:
    if value is None:
        return set()
    return set(_WORD_RE.findall(str(value).lower()))


def _contains(text: str, term: object) -> bool:
    phrase = str(term).strip().lower()
    if not phrase:
        return False
    return re.search(rf"(?<!\w){re.escape(phrase)}(?!\w)", text.lower()) is not None


def _iter_values(value: object) -> Iterable[Any]:
    if isinstance(value, Mapping):
        return value.values()
    if isinstance(value, (tuple, list, set, frozenset)):
        return value
    return ()


def _world_entities(package: Any) -> dict[str, Any]:
    entities: dict[str, Any] = {}
    world = getattr(package, "world", None)
    for field in ("locations", "npcs", "items", "groups"):
        for entity in _iter_values(getattr(world, field, ())):
            entity_id = getattr(entity, "id", None)
            if isinstance(entity_id, str):
                entities[entity_id] = entity
    return entities


def _entity_surfaces(package: Any) -> dict[str, tuple[str, ...]]:
    entities = _world_entities(package)
    surfaces: dict[str, set[str]] = {entity_id: set() for entity_id in entities}
    for entity_id, entity in entities.items():
        for field in ("name", "aliases", "scoped_aliases"):
            value = getattr(entity, field, ())
            if isinstance(value, str):
                value = (value,)
            for surface in _iter_values(value):
                if isinstance(surface, str) and surface.strip():
                    surfaces[entity_id].add(surface.strip())
    indexes = getattr(package, "knowledge_indexes", None)
    for alias, entity_ids in (getattr(indexes, "entity_alias_to_entities", {}) or {}).items():
        for entity_id in entity_ids:
            if entity_id in surfaces and isinstance(alias, str):
                surfaces[entity_id].add(alias)
    return {
        entity_id: tuple(sorted(values, key=lambda value: (-len(value), value.casefold())))
        for entity_id, values in surfaces.items()
    }


def _scene_entity_ids(package: Any, scene_id: str) -> set[str]:
    scene = next(
        (item for item in getattr(package, "scenes", ()) if getattr(item.metadata, "scene_id", None) == scene_id), None
    )
    if scene is None:
        return set()
    metadata = scene.metadata
    result = set(metadata.participant_ids) | set(metadata.item_ids) | {metadata.location_id}
    parents: dict[str, str | None] = {
        entity.id: getattr(entity, "parent", None) for entity in _iter_values(getattr(package.world, "locations", ()))
    }
    current = metadata.location_id
    while current in parents and parents[current] is not None:
        current = parents[current]
        result.add(current)
    for placement in tuple(metadata.item_placements.values()) + tuple(metadata.character_placements.values()):
        parent = getattr(placement, "parent", None) if not isinstance(placement, Mapping) else placement.get("parent")
        if isinstance(parent, str):
            result.add(parent)
            current = parent
            while current in parents and parents[current] is not None:
                current = parents[current]
                result.add(current)
    return result


def _named_entity_ids(text: str, package: Any) -> set[str]:
    return {
        entity_id
        for entity_id, surfaces in _entity_surfaces(package).items()
        if any(_contains(text, surface) for surface in surfaces)
    }


def _entity_names(package: Any, entity_ids: Iterable[str]) -> list[str]:
    entities = _world_entities(package)
    return sorted(
        [str(getattr(entities[entity_id], "name", entity_id)) for entity_id in entity_ids if entity_id in entities],
        key=str.casefold,
    )


def _claim_ids(package: Any, scene_id: str) -> tuple[str, ...]:
    indexes = getattr(package, "knowledge_indexes", None)
    scene_claims = getattr(indexes, "scene_to_candidates", {}) or {}
    return tuple(scene_claims.get(scene_id, ()))


def _claims_with_evidence(package: Any, scene_id: str) -> Iterable[Any]:
    indexes = getattr(package, "knowledge_indexes", None)
    by_id = getattr(indexes, "by_id", {}) or {}
    for claim_id in _claim_ids(package, scene_id):
        claim = by_id.get(claim_id)
        if claim is not None:
            yield claim


def _matches_evidence(player_input: str, evidence: object) -> bool:
    groups = evidence if isinstance(evidence, (tuple, list)) else ()
    return bool(groups) and all(
        any(_contains(player_input, term) for term in group if isinstance(term, str))
        for group in groups
        if isinstance(group, (tuple, list))
    )


def _story_vocabulary(package: Any) -> set[str]:
    vocabulary: set[str] = set()
    world = getattr(package, "world", None)
    for field in ("locations", "npcs", "items", "groups"):
        for entity in _iter_values(getattr(world, field, ())):
            for attr in ("name", "aliases", "scoped_aliases", "description", "narrator_bio"):
                value = getattr(entity, attr, ())
                if isinstance(value, str):
                    vocabulary |= _words(value)
                else:
                    for item in _iter_values(value):
                        vocabulary |= _words(item)
    for claim in getattr(getattr(package, "knowledge", None), "knowledge", ()):
        vocabulary |= _words(getattr(claim, "statement", ""))
        vocabulary |= _words(getattr(claim, "aliases", ()))
    for scene in getattr(package, "scenes", ()):
        vocabulary |= _words(getattr(scene.metadata, "entry_text", ""))
        for variant in _iter_values(getattr(scene.metadata, "entry_variants", ())):
            for field in ("text", "say", "entry_text"):
                value = variant.get(field, "") if isinstance(variant, Mapping) else getattr(variant, field, "")
                vocabulary |= _words(value)
    indexes = getattr(package, "knowledge_indexes", None)
    for alias in getattr(indexes, "alias_to_knowledge", {}) or {}:
        vocabulary |= _words(alias)
    return vocabulary


def _acting_verb(text: str) -> bool:
    return any(word in ACTING_VERBS for word in _words(text))


def diagnose_turn(packet: dict, package: Any) -> dict:
    """Return a deterministic diagnosis for one failing-turn packet."""

    player_input = packet.get("player_input", "") if isinstance(packet.get("player_input", ""), str) else ""
    key = packet.get("key")
    matched = packet.get("matched_candidate")
    if matched is not None and packet.get("committed") is None:
        return {
            "key": key,
            "cause": CAUSES[0],
            "why": f"Matched claim {matched}, but nothing was committed.",
            "signals": {"matched_candidate": matched, "decided_by": "rule"},
        }

    scene_id = packet.get("scene", "")
    offered = set(packet.get("candidates_offered", ())) if isinstance(packet.get("candidates_offered"), list) else set()
    missing_claims = sorted(
        str(claim.id)
        for claim in _claims_with_evidence(package, scene_id)
        if claim.id not in offered and _matches_evidence(player_input, claim.action_evidence)
    )
    if missing_claims:
        return {
            "key": key,
            "cause": CAUSES[1],
            "why": f"The command satisfies authored claims not offered: {', '.join(missing_claims)}.",
            "signals": {"claim_ids": missing_claims, "decided_by": "rule"},
        }

    named_ids = _named_entity_ids(player_input, package)
    scene_ids = _scene_entity_ids(package, scene_id)
    outside_names = _entity_names(package, named_ids - scene_ids)
    if outside_names:
        return {
            "key": key,
            "cause": CAUSES[2],
            "why": f"The command names {', '.join(outside_names)}, which belong to another scene.",
            "signals": {"entities": outside_names, "decided_by": "rule"},
        }

    vocabulary = _story_vocabulary(package)
    unknown_words = sorted(
        word for word in _words(player_input) if len(word) >= 4 and word not in STOPWORDS and word not in vocabulary
    )[:8]
    if unknown_words:
        return {
            "key": key,
            "cause": CAUSES[3],
            "why": f"The command contains words absent from the story vocabulary: {', '.join(unknown_words)}.",
            "signals": {"unknown_words": unknown_words, "decided_by": "rule"},
        }

    scene_names = _entity_names(package, named_ids & scene_ids)
    if scene_names or _acting_verb(player_input):
        return {
            "key": key,
            "cause": CAUSES[4],
            "why": "The command concerns this scene, but no authored outcome applies.",
            "signals": {"scene_entities": scene_names, "decided_by": "rule"},
        }

    return {
        "key": key,
        "cause": CAUSES[5],
        "why": "The available evidence does not identify a cause.",
        "signals": {"decided_by": "rule"},
    }


def diagnose_turns(packets: list[dict], package: Any) -> list[dict]:
    """Diagnose packets in their original order."""

    return [diagnose_turn(packet, package) for packet in packets]


def _prompt(packets: list[dict], rows: list[dict], package: Any) -> str:
    unclear = {row["key"] for row in rows if row["cause"] == "unclear"}
    details = []
    for packet in packets:
        if packet.get("key") not in unclear:
            continue
        claims = []
        for claim in list(_claims_with_evidence(package, packet.get("scene", "")))[:40]:
            claims.append({"id": claim.id, "says": str(getattr(claim, "statement", ""))[:160]})
        details.append(
            {
                "key": packet.get("key"),
                "player_input": packet.get("player_input", ""),
                "narration": str(packet.get("narration", ""))[:300],
                "candidates_offered": packet.get("candidates_offered", []),
                "claims": claims,
            }
        )
    return f"{DIAGNOSE_BRIEF}\n\nTurns to classify:\n{json.dumps(details, ensure_ascii=False, sort_keys=True)}"


def default_classifier(
    root: Path | None = None,
    *,
    run: Callable[..., subprocess.CompletedProcess] = subprocess.run,
    model_id: str = DIAGNOSE_MODEL_ID,
) -> Callable[[Any, str, datetime], ClassifierReply]:
    """Build the guarded classifier from the repository's guard and budget files."""

    repository_root = Path(root) if root is not None else Path(__file__).resolve().parents[2]
    config, config_root = _load_config(repository_root)
    paths = config["paths"]

    def resolve(value: object) -> Path:
        if not isinstance(value, (str, Path)):
            raise ValueError("path must be a string")
        path = Path(value)
        return path if path.is_absolute() else repository_root / path

    allowlist = resolve(paths["allowlist"])
    if not allowlist.is_file():
        allowlist = config_root / paths["allowlist"]
    guard = ModelGuard.from_file(allowlist)
    ledger = SpendLedger(resolve(paths["ledger"]))
    caps = Caps.from_dict(config["caps"])

    def classify(ticket: Any, prompt: str, now: datetime) -> ClassifierReply:
        result = guarded_call(
            guard=guard,
            ledger=ledger,
            caps=caps,
            station="diagnose",
            model_id=model_id,
            effort=DIAGNOSE_EFFORT,
            scene=ticket.scene,
            ticket_id=ticket.id,
            now=now,
            fn=lambda: claude_call(prompt, model_id=model_id, effort=DIAGNOSE_EFFORT, run=run),
        )
        return ClassifierReply(result.output, result.tokens)

    return classify


def _input_hash(packets: list[dict]) -> str:
    encoded = json.dumps(packets, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256((encoded + DIAGNOSE_VERSION).encode("utf-8")).hexdigest()


def _counts(rows: list[dict]) -> dict[str, int]:
    counts = Counter(row["cause"] for row in rows)
    return {cause: counts[cause] for cause in CAUSES if counts[cause]}


def _summary(counts: dict[str, int]) -> str:
    return ", ".join(f"{cause} {counts[cause]}" for cause in CAUSES if counts.get(cause))


def _apply_classifier(
    rows: list[dict],
    packets: list[dict],
    package: Any,
    classifier: Callable[[Any, str, datetime], ClassifierReply],
    ticket: Any,
    now: datetime,
) -> tuple[list[dict], int]:
    reply = classifier(ticket, _prompt(packets, rows, package), now)
    total_tokens = reply.tokens if isinstance(reply.tokens, int) else 0
    parsed = extract_plan(reply.text) if isinstance(reply.text, str) else None
    if not isinstance(parsed, dict):
        return rows, total_tokens
    updated = []
    for row in rows:
        if row["cause"] != "unclear":
            updated.append(row)
            continue
        answer = parsed.get(row["key"])
        if isinstance(answer, dict) and answer.get("cause") in CAUSES[:5] and isinstance(answer.get("why"), str):
            updated.append(
                {
                    **row,
                    "cause": answer["cause"],
                    "why": answer["why"],
                    "signals": {**row["signals"], "decided_by": "classifier"},
                }
            )
        else:
            updated.append(row)
    return updated, total_tokens


def diagnose_handler(
    root: Path | None = None,
    *,
    classifier: Callable[[Any, str, datetime], ClassifierReply] | None = None,
    package_loader: Callable[[Path], Any] | None = None,
) -> StationHandler:
    """Return the station-11 diagnosis handler."""

    repository_root = Path(root) if root is not None else Path(__file__).resolve().parents[2]
    resolved_classifier = classifier
    resolved_package_loader = package_loader or load_story_package

    def handle(ticket: Any, now: datetime) -> StationResult:
        nonlocal resolved_classifier
        payload = getattr(ticket, "payload", None)
        failing_turns = payload.get("failing_turns") if isinstance(payload, dict) else None
        if (
            not isinstance(failing_turns, list)
            or not failing_turns
            or any(not isinstance(packet, dict) for packet in failing_turns)
        ):
            return StationResult(False, "diagnose", "missing payload key: failing_turns")
        try:
            package = resolved_package_loader(_story_root(repository_root))
        except Exception:
            return StationResult(False, "diagnose", "could not load the story package for the diagnosis")

        input_hash = _input_hash(failing_turns)
        workspace_value = payload.get("workspace")
        diagnosis_path = None
        if isinstance(workspace_value, str):
            diagnosis_path = Path(workspace_value).expanduser() / _safe_id(ticket.id) / "diagnosis.json"
            saved = _record(diagnosis_path) if diagnosis_path.exists() else None
            if (
                saved is not None
                and saved.get("input_hash") == input_hash
                and isinstance(saved.get("rows"), list)
                and isinstance(saved.get("counts"), dict)
            ):
                rows = saved["rows"]
                counts = saved["counts"]
                if len(rows) == len(failing_turns) and all(isinstance(row, dict) for row in rows):
                    return StationResult(
                        True,
                        "diagnose",
                        _summary(counts),
                        payload_updates={"diagnosis": {"rows": rows, "counts": counts}},
                    )

        rows = diagnose_turns(failing_turns, package)
        total_tokens = 0
        if any(row["cause"] == "unclear" for row in rows):
            if resolved_classifier is None:
                resolved_classifier = default_classifier(repository_root)
            rows, total_tokens = _apply_classifier(rows, failing_turns, package, resolved_classifier, ticket, now)
        counts = _counts(rows)
        if diagnosis_path is not None:
            _atomic_json_write(diagnosis_path, {"input_hash": input_hash, "rows": rows, "counts": counts})
        return StationResult(
            True,
            "diagnose",
            _summary(counts),
            tokens=total_tokens,
            payload_updates={"diagnosis": {"rows": rows, "counts": counts}},
        )

    return handle


__all__ = [
    "CAUSES",
    "DIAGNOSE_BRIEF",
    "DIAGNOSE_EFFORT",
    "DIAGNOSE_MODEL_ID",
    "DIAGNOSE_VERSION",
    "ClassifierReply",
    "STOPWORDS",
    "default_classifier",
    "diagnose_handler",
    "diagnose_turn",
    "diagnose_turns",
]
