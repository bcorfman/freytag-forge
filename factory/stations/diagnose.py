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

MATCH_MISS_ON_OFFERED_CANDIDATE = "match_miss_on_offered_candidate"
CLAIM_NOT_OFFERED = "claim_not_offered"
ALREADY_DELIVERED = "already_delivered"
FOLLOWS_PRIOR_NARRATION = "follows_prior_narration"
CLAIM_WORDING_MISS = "claim_wording_miss"
LEAD_OUTSIDE_SCENE = "lead_outside_scene"
UNKNOWN_OBJECT = "unknown_object"
NO_AUTHORED_OUTCOME = "no_authored_outcome"
UNCLEAR = "unclear"

CAUSES = (
    MATCH_MISS_ON_OFFERED_CANDIDATE,
    CLAIM_NOT_OFFERED,
    ALREADY_DELIVERED,
    FOLLOWS_PRIOR_NARRATION,
    CLAIM_WORDING_MISS,
    LEAD_OUTSIDE_SCENE,
    UNKNOWN_OBJECT,
    NO_AUTHORED_OUTCOME,
    UNCLEAR,
)
CLASSIFIABLE_CAUSES = frozenset(
    {
        MATCH_MISS_ON_OFFERED_CANDIDATE,
        CLAIM_NOT_OFFERED,
        ALREADY_DELIVERED,
        FOLLOWS_PRIOR_NARRATION,
        CLAIM_WORDING_MISS,
        LEAD_OUTSIDE_SCENE,
        UNKNOWN_OBJECT,
        NO_AUTHORED_OUTCOME,
    }
)
DIAGNOSE_VERSION = "diagnose-v2"
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
already_delivered: the command revisits a claim delivered earlier in this run.
follows_prior_narration: the command refers to an object introduced by the prior narration.
claim_wording_miss: an authored claim matches all but one evidence group, so one wording is missing.
lead_outside_scene: the command names a story entity that belongs to another scene.
unknown_object: a meaningful command word is absent from the story vocabulary.
no_authored_outcome: the command concerns this scene, but no authored outcome was found.
unclear: use this only when every cause except unclear cannot be supported by the evidence.

Return ONE JSON object mapping every listed turn key to an object with exactly one cause from the causes above
other than unclear, and one plain sentence explaining why. Return nothing else."""


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


def _word_stems(word: str) -> tuple[str, ...]:
    """Return the small set of suffix-stripped forms used by diagnosis."""

    stems = {word}
    for suffix in ("ing", "ed", "es", "s"):
        if word.endswith(suffix) and len(word) > len(suffix) + 1:
            stem = word[: -len(suffix)]
            stems.add(stem)
            if suffix == "ing":
                stems.add(stem + "e")
    return tuple(stems)


def _known_word(word: str, vocabulary: set[str]) -> bool:
    return any(stem in vocabulary for stem in _word_stems(word))


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


def _entity_surfaces(package: Any, scene_id: str | None = None) -> dict[str, tuple[str, ...]]:
    entities = _world_entities(package)
    scene_ids = _scene_entity_ids(package, scene_id) if scene_id is not None else None
    surfaces: dict[str, set[str]] = {entity_id: set() for entity_id in entities}
    for entity_id, entity in entities.items():
        for field in ("name", "aliases", "scoped_aliases"):
            if field == "scoped_aliases" and scene_ids is not None and entity_id not in scene_ids:
                continue
            value = getattr(entity, field, ())
            if isinstance(value, str):
                value = (value,)
            for surface in _iter_values(value):
                if isinstance(surface, str) and surface.strip():
                    surfaces[entity_id].add(surface.strip())
    indexes = getattr(package, "knowledge_indexes", None)
    for alias, entity_ids in (getattr(indexes, "entity_alias_to_entities", {}) or {}).items():
        for entity_id in entity_ids:
            entity = entities.get(entity_id)
            scoped_aliases = getattr(entity, "scoped_aliases", ()) if entity is not None else ()
            is_scoped = alias in scoped_aliases if not isinstance(scoped_aliases, str) else alias == scoped_aliases
            if (
                entity_id in surfaces
                and isinstance(alias, str)
                and (not is_scoped or scene_ids is None or entity_id in scene_ids)
            ):
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


def _named_entity_ids(text: str, package: Any, scene_id: str | None = None) -> set[str]:
    return {
        entity_id
        for entity_id, surfaces in _entity_surfaces(package, scene_id).items()
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
    matches = _evidence_group_matches(player_input, evidence)
    return bool(matches) and all(matches)


def _evidence_group_matches(player_input: str, evidence: object) -> tuple[bool, ...]:
    groups = evidence if isinstance(evidence, (tuple, list)) else ()
    return tuple(
        any(_contains(player_input, term) for term in group if isinstance(term, str))
        for group in groups
        if isinstance(group, (tuple, list))
    )


def _claim_wording_misses(player_input: str, package: Any, scene_id: str) -> list[tuple[str, int]]:
    misses: list[tuple[str, int]] = []
    for claim in _claims_with_evidence(package, scene_id):
        matches = _evidence_group_matches(player_input, getattr(claim, "action_evidence", ()))
        missing = [index for index, matched in enumerate(matches) if not matched]
        if len(matches) >= 2 and len(missing) == 1:
            misses.append((str(claim.id), missing[0]))
    return sorted(misses)


def _evidence_entity_ids(group: object, package: Any, scene_id: str) -> set[str]:
    """Return scene-valid entities named by one evidence group."""

    terms = group if isinstance(group, (tuple, list)) else ()
    return {
        entity_id
        for entity_id, surfaces in _entity_surfaces(package, scene_id).items()
        if any(
            isinstance(term, str) and any(_contains(term, surface) or _contains(surface, term) for surface in surfaces)
            for term in terms
        )
    }


def _wording_miss_is_relevant(
    player_input: str, package: Any, scene_id: str, claim_id: str, missing_group: int
) -> bool:
    indexes = getattr(package, "knowledge_indexes", None)
    claim = (getattr(indexes, "by_id", {}) or {}).get(claim_id)
    evidence = getattr(claim, "action_evidence", ()) if claim is not None else ()
    groups = evidence if isinstance(evidence, (tuple, list)) else ()
    if missing_group >= len(groups):
        return False
    claim_entities = _evidence_entity_ids(groups[missing_group], package, scene_id)
    if not claim_entities:
        return True
    command_entities = _named_entity_ids(player_input, package, scene_id)
    return bool(claim_entities & command_entities)


def _delivered_ids(packet: Mapping[str, Any]) -> list[str]:
    values = packet.get("delivered_before")
    if not isinstance(values, list):
        return []
    return list(dict.fromkeys(value for value in values if isinstance(value, str)))


def _delivered_turns(packet: Mapping[str, Any]) -> dict[str, int]:
    values = packet.get("delivered_before_turns")
    if not isinstance(values, Mapping):
        return {}
    return {
        claim_id: turn
        for claim_id, turn in values.items()
        if isinstance(claim_id, str) and isinstance(turn, int) and not isinstance(turn, bool)
    }


def _claim_for_id(package: Any, claim_id: str) -> Any | None:
    indexes = getattr(package, "knowledge_indexes", None)
    return (getattr(indexes, "by_id", {}) or {}).get(claim_id)


def _spent_by_sibling(claim_id: str, delivered: Iterable[str], package: Any) -> str | None:
    claim = _claim_for_id(package, claim_id)
    source = getattr(claim, "source", None)
    storylet_id = getattr(source, "storylet_id", None)
    if not storylet_id:
        return None
    for delivered_id in delivered:
        if delivered_id == claim_id:
            continue
        sibling = _claim_for_id(package, delivered_id)
        sibling_source = getattr(sibling, "source", None)
        if getattr(sibling_source, "storylet_id", None) == storylet_id:
            return delivered_id
    return None


def _unmet_requirement(claim: Any, packet: Mapping[str, Any]) -> tuple[str, str] | None:
    """Return ``(fact id, readable condition)`` when packet facts disprove a requirement."""

    facts = packet.get("facts_before")
    if not isinstance(facts, Mapping):
        return None
    for predicate in getattr(claim, "requires", ()) or ():
        fact_id = getattr(predicate, "fact_id", None)
        if not isinstance(fact_id, str):
            continue
        expected = getattr(predicate, "equals", None)
        expected_value = str(expected).lower() if isinstance(expected, bool) else expected
        raw = facts.get(fact_id)
        present = raw is not None
        if isinstance(raw, Mapping):
            if "value" in raw:
                raw = raw["value"]
            elif "object" in raw:
                raw = raw["object"]
        matches = expected is False if not present else expected is None or raw in (expected_value, expected)
        if not matches:
            return fact_id, f"{fact_id} must equal {expected_value!r}"
    return None


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


def _modifier_words(text: str, package: Any, entity_ids: Iterable[str]) -> set[str]:
    tokens = _WORD_RE.findall(text.lower())
    modifiers: set[str] = set()
    surfaces = _entity_surfaces(package)
    for entity_id in entity_ids:
        for surface in surfaces.get(entity_id, ()):
            surface_tokens = _WORD_RE.findall(surface.lower())
            if not surface_tokens:
                continue
            width = len(surface_tokens)
            for start in range(len(tokens) - width + 1):
                if tokens[start : start + width] == surface_tokens and start:
                    modifiers.add(tokens[start - 1])
    return modifiers


def _unknown_words(text: str, vocabulary: set[str], modifiers: set[str]) -> list[str]:
    return sorted(
        word
        for word in _words(text)
        if len(word) >= 4 and word not in STOPWORDS and not _known_word(word, vocabulary) and word not in modifiers
    )[:8]


def diagnose_turn(packet: dict, package: Any) -> dict:
    """Return a deterministic diagnosis for one failing-turn packet."""

    player_input = packet.get("player_input", "") if isinstance(packet.get("player_input", ""), str) else ""
    key = packet.get("key")
    matched = packet.get("matched_candidate")
    if matched is not None and packet.get("committed") is None:
        return {
            "key": key,
            "cause": MATCH_MISS_ON_OFFERED_CANDIDATE,
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
        delivered = _delivered_ids(packet)
        delivered_claims = [claim_id for claim_id in missing_claims if claim_id in delivered]
        if delivered_claims:
            delivered_turns = _delivered_turns(packet)
            evidence = []
            for claim_id in delivered_claims:
                turn_number = delivered_turns.get(claim_id)
                if turn_number is None:
                    evidence.append(f"Claim {claim_id} was delivered earlier in this run.")
                else:
                    evidence.append(f"Claim {claim_id} was delivered at turn {turn_number}.")
            # ``delivered_before`` and ``delivered_at_turn`` expose the prior
            # delivery evidence; the plural form preserves all turn numbers.
            signals = {
                "claim_ids": delivered_claims,
                "delivered_before": delivered_claims,
                "decided_by": "rule",
            }
            if len(delivered_claims) == 1 and delivered_claims[0] in delivered_turns:
                signals["delivered_at_turn"] = delivered_turns[delivered_claims[0]]
            if delivered_turns:
                signals["delivered_at_turns"] = {
                    claim_id: delivered_turns[claim_id] for claim_id in delivered_claims if claim_id in delivered_turns
                }
            return {
                "key": key,
                "cause": ALREADY_DELIVERED,
                "why": " ".join(evidence),
                "signals": signals,
            }
        sibling_claims = [
            (claim_id, sibling)
            for claim_id in missing_claims
            if (sibling := _spent_by_sibling(claim_id, delivered, package)) is not None
        ]
        if sibling_claims:
            claim_id, sibling = sibling_claims[0]
            # ``spent_by_sibling`` names the delivered alternative that made
            # this non-follow-up claim unavailable.
            return {
                "key": key,
                "cause": CLAIM_NOT_OFFERED,
                "why": f"Claim {claim_id} was not offered because sibling claim {sibling} was delivered earlier.",
                "signals": {
                    "claim_ids": missing_claims,
                    "spent_by_sibling": sibling,
                    "decided_by": "rule",
                },
            }
        unmet = next(
            (
                (claim_id, requirement)
                for claim_id in missing_claims
                if (requirement := _unmet_requirement(_claim_for_id(package, claim_id), packet)) is not None
            ),
            None,
        )
        if unmet is not None:
            claim_id, (fact_id, condition) = unmet
            # ``unmet`` is the runtime-style fact identifier; the condition
            # keeps the deterministic explanation readable to the operator.
            signals = {
                "claim_ids": missing_claims,
                "unmet": fact_id,
                "unmet_condition": condition,
                "decided_by": "rule",
            }
            return {
                "key": key,
                "cause": CLAIM_NOT_OFFERED,
                "why": f"Claim {claim_id} was not offered because {condition}.",
                "signals": signals,
            }
        return {
            "key": key,
            "cause": CLAIM_NOT_OFFERED,
            "why": f"The command satisfies authored claims not offered: {', '.join(missing_claims)}.",
            "signals": {"claim_ids": missing_claims, "decided_by": "rule"},
        }

    scene_ids = _scene_entity_ids(package, scene_id)
    named_ids = _named_entity_ids(player_input, package, scene_id)
    scene_named_ids = named_ids & scene_ids
    vocabulary = _story_vocabulary(package)
    modifiers = _modifier_words(player_input, package, scene_named_ids)
    unknown_words = _unknown_words(player_input, vocabulary, modifiers)
    outside_names = _entity_names(package, named_ids - scene_ids)

    wording_misses = (
        []
        if unknown_words or outside_names
        else [
            (claim_id, group)
            for claim_id, group in _claim_wording_misses(player_input, package, scene_id)
            if _wording_miss_is_relevant(player_input, package, scene_id, claim_id, group)
        ]
    )
    if wording_misses:
        claim_ids = sorted({claim_id for claim_id, _ in wording_misses})
        return {
            "key": key,
            "cause": CLAIM_WORDING_MISS,
            "why": f"The command nearly matches authored claims {', '.join(claim_ids)}, missing one wording group.",
            "signals": {
                "claim_ids": claim_ids,
                "missing": [{"claim_id": claim_id, "group": group} for claim_id, group in wording_misses],
                # ``hypothesis`` keeps this lexical near-match from looking proven.
                "hypothesis": True,
                "decided_by": "rule",
            },
        }

    if outside_names:
        return {
            "key": key,
            "cause": LEAD_OUTSIDE_SCENE,
            "why": f"The command names {', '.join(outside_names)}, which belong to another scene.",
            "signals": {"entities": outside_names, "decided_by": "rule"},
        }

    prior_narration = packet.get("previous_narration")
    prior_terms = (
        sorted(word for word in unknown_words if isinstance(prior_narration, str) and _contains(prior_narration, word))
        if isinstance(prior_narration, str)
        else []
    )
    if prior_terms:
        # ``introduced_words`` and ``previous_narration`` record the referents
        # that the narration, rather than the player, supplied.
        return {
            "key": key,
            "cause": FOLLOWS_PRIOR_NARRATION,
            "why": f"The previous narration introduced {', '.join(prior_terms)}, which the command refers to.",
            "signals": {
                "unknown_words": unknown_words,
                "introduced_words": prior_terms,
                "previous_narration": prior_narration[:600],
                "decided_by": "rule",
            },
        }

    if unknown_words:
        return {
            "key": key,
            "cause": UNKNOWN_OBJECT,
            "why": f"The command contains words absent from the story vocabulary: {', '.join(unknown_words)}.",
            "signals": {"unknown_words": unknown_words, "decided_by": "rule"},
        }

    scene_names = _entity_names(package, scene_named_ids)
    if scene_names or _acting_verb(player_input):
        return {
            "key": key,
            "cause": NO_AUTHORED_OUTCOME,
            "why": "The command concerns this scene, but no authored outcome applies.",
            "signals": {"scene_entities": scene_names, "decided_by": "rule"},
        }

    return {
        "key": key,
        "cause": UNCLEAR,
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
        for field in (
            "previous_narration",
            "delivered_before",
            "delivered_before_turns",
            "rejected_code",
            "rejected_message",
            "facts_before",
        ):
            if field not in packet:
                continue
            value = packet[field]
            if isinstance(value, str):
                value = value[:600]
            elif isinstance(value, list):
                value = value[:100]
            elif isinstance(value, Mapping):
                value = dict(list(value.items())[:40])
            details[-1][field] = value
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
        if row["cause"] != UNCLEAR:
            updated.append(row)
            continue
        answer = parsed.get(row["key"])
        if (
            isinstance(answer, dict)
            and answer.get("cause") in CLASSIFIABLE_CAUSES
            and isinstance(answer.get("why"), str)
        ):
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
        if not isinstance(failing_turns, list) or any(not isinstance(packet, dict) for packet in failing_turns):
            return StationResult(False, "diagnose", "missing payload key: failing_turns")
        if not failing_turns:
            return StationResult(
                True, "diagnose", "no failing turns", payload_updates={"diagnosis": {"rows": [], "counts": {}}}
            )
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
