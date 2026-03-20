from __future__ import annotations

import re

from storygame.story_canon import canonical_detective_name

_SUPPORT_ROLE_TERMS = ("assistant", "ally", "partner", "contact", "confidant")
_SUSPECT_ROLE_TERMS = ("suspect", "culprit", "killer", "mastermind")
_QUESTION_TARGET_TERMS = ("question", "interrogate", "interview", "press", "confront", "accuse")
_ITEM_HOLDING_TERMS = (
    "holds",
    "holding",
    "keeps",
    "kept",
    "carries",
    "carrying",
    "clutches",
    "clutching",
    "in hand",
)
_ITEM_EXPOSED_TERMS = (
    "wedged",
    "lodged",
    "lying",
    "resting",
    "rests",
    "in the stones",
    "on the stones",
    "on the ground",
    "at your feet",
    "in front of the mansion",
    "before the mansion",
    "in the mud",
    "beside the gate",
    "out in the open",
)


def _normalized_line(value: str) -> str:
    return " ".join(value.split()).strip()


def _normalize_name(name: str) -> str:
    return " ".join(name.split()).strip().lower()


def _deduped_character_names(assistant_name: str, character_names: tuple[str, ...]) -> tuple[str, ...]:
    names: list[str] = []
    for candidate in (assistant_name, *character_names):
        cleaned = " ".join(candidate.split()).strip()
        if cleaned and cleaned not in names:
            names.append(cleaned)
    return tuple(names)


def _character_aliases(character_names: tuple[str, ...]) -> dict[str, tuple[str, ...]]:
    first_name_counts: dict[str, int] = {}
    for name in character_names:
        parts = name.split()
        if parts:
            first = parts[0].strip().lower()
            if first:
                first_name_counts[first] = first_name_counts.get(first, 0) + 1

    aliases: dict[str, tuple[str, ...]] = {}
    for name in character_names:
        values = [name.strip().lower()]
        parts = name.split()
        if parts:
            first = parts[0].strip().lower()
            if first and first_name_counts.get(first, 0) == 1:
                values.append(first)
        aliases[name] = tuple(dict.fromkeys(alias for alias in values if alias))
    return aliases


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def _support_role_claims(lines: list[str], character_aliases: dict[str, tuple[str, ...]]) -> set[str]:
    claims: set[str] = set()
    for line in lines:
        lowered = line.lower()
        if not _contains_any(lowered, _SUPPORT_ROLE_TERMS):
            continue
        for name, aliases in character_aliases.items():
            if any(alias in lowered for alias in aliases):
                claims.add(name)
    return claims


def _suspect_role_claims(lines: list[str], character_aliases: dict[str, tuple[str, ...]]) -> set[str]:
    claims: set[str] = set()
    for line in lines:
        lowered = line.lower()
        if not _contains_any(lowered, _SUSPECT_ROLE_TERMS):
            continue
        for name, aliases in character_aliases.items():
            if any(alias in lowered for alias in aliases):
                claims.add(name)
    return claims


def _question_target_claims(text: str, character_aliases: dict[str, tuple[str, ...]]) -> set[str]:
    lowered = text.lower()
    claims: set[str] = set()
    if not _contains_any(lowered, _QUESTION_TARGET_TERMS):
        return claims
    for name, aliases in character_aliases.items():
        if any(alias in lowered for alias in aliases):
            claims.add(name)
    return claims


def _rewrite_question_target_reference(
    text: str,
    character_name: str,
    replacement_label: str,
    aliases: tuple[str, ...] = (),
) -> str:
    rewritten = text
    name_aliases = tuple(dict.fromkeys((character_name.strip(), *aliases)))
    for alias in name_aliases:
        escaped_name = re.escape(alias)
        for verb in _QUESTION_TARGET_TERMS:
            rewritten = re.sub(
                rf"\b{verb}\s+{escaped_name}\b",
                f"{verb} {replacement_label}",
                rewritten,
                flags=re.IGNORECASE,
            )
        rewritten = re.sub(
            rf"\b{escaped_name}'s involvement\b",
            f"{replacement_label}'s involvement",
            rewritten,
            flags=re.IGNORECASE,
        )
        rewritten = re.sub(
            rf"\babout\s+{escaped_name}\b",
            f"about {replacement_label}",
            rewritten,
            flags=re.IGNORECASE,
        )
    return rewritten


def item_labels_for_opening(item_ids: tuple[str, ...]) -> tuple[str, ...]:
    labels: list[str] = []
    for item_id in item_ids:
        label = item_id.replace("_", " ").strip().lower()
        if label and label not in labels:
            labels.append(label)
    return tuple(labels)


def opening_coherence_issues(
    opening_lines: list[str],
    assistant_name: str,
    actionable_objective: str,
    item_labels: tuple[str, ...],
    character_names: tuple[str, ...] = (),
) -> list[str]:
    issues: list[str] = []
    normalized_lines = [_normalized_line(line) for line in opening_lines if _normalized_line(line)]
    known_names = _deduped_character_names(assistant_name, character_names)
    aliases = _character_aliases(known_names)
    support_claims = _support_role_claims(normalized_lines, aliases)
    suspect_claims = _suspect_role_claims(normalized_lines, aliases)
    question_claims = _question_target_claims(" ".join(normalized_lines), aliases)
    question_claims.update(_question_target_claims(actionable_objective, aliases))
    holder_by_item: dict[str, str] = {}

    for name in sorted(support_claims.intersection(suspect_claims)):
        issues.append(f"{name} has conflicting assistant/contact versus suspect role signals in the opening.")
    for name in sorted(support_claims.intersection(question_claims)):
        issues.append(f"{name} is framed as an assistant/contact and the direct question target at the same time.")

    for line in normalized_lines:
        lowered = line.lower()
        for name, name_aliases in aliases.items():
            if not any(alias in lowered for alias in name_aliases):
                continue
            if not _contains_any(lowered, _ITEM_HOLDING_TERMS):
                continue
            for label in item_labels:
                if label in lowered:
                    holder_by_item[label] = name

    for label, holder_name in holder_by_item.items():
        for line in normalized_lines:
            lowered = line.lower()
            if label not in lowered:
                continue
            if _contains_any(lowered, _ITEM_EXPOSED_TERMS):
                issues.append(
                    f"The {label} cannot be both in {holder_name}'s custody and exposed elsewhere in the same scene."
                )
                break

    return issues


def cohere_opening_lines(
    opening_lines: list[str],
    genre: str,
    protagonist_name: str,
    assistant_name: str,
    actionable_objective: str,
    item_labels: tuple[str, ...],
    character_names: tuple[str, ...] = (),
) -> list[str]:
    canonical_name = canonical_detective_name(genre, protagonist_name)
    revised = [_normalized_line(line) for line in opening_lines if _normalized_line(line)]
    known_names = _deduped_character_names(assistant_name, character_names)
    aliases = _character_aliases(known_names)
    support_claims = _support_role_claims(revised, aliases)
    question_claims = _question_target_claims(" ".join(revised), aliases)
    question_claims.update(_question_target_claims(actionable_objective, aliases))
    holder_by_item: dict[str, str] = {}

    for index, line in enumerate(revised):
        lowered = line.lower()
        if canonical_name and lowered in {"you are the detective.", "you are detective.", "you are the detective"}:
            revised[index] = f"You are {canonical_name}."

    for line in revised:
        lowered = line.lower()
        for name, name_aliases in aliases.items():
            if not any(alias in lowered for alias in name_aliases):
                continue
            if not _contains_any(lowered, _ITEM_HOLDING_TERMS):
                continue
            for label in item_labels:
                if label in lowered:
                    holder_by_item[label] = name

    for index, line in enumerate(revised):
        lowered = line.lower()
        for name, name_aliases in aliases.items():
            if not any(alias in lowered for alias in name_aliases):
                continue
            if name in support_claims and name in question_claims and _contains_any(lowered, _QUESTION_TARGET_TERMS):
                revised[index] = _rewrite_question_target_reference(line, name, "the strongest suspect", name_aliases)
                lowered = revised[index].lower()
            if name in support_claims and _contains_any(lowered, _SUSPECT_ROLE_TERMS):
                role_label = "assistant and first contact" if name == assistant_name else "ally contact"
                revised[index] = f"{name} remains your {role_label} while you decide which suspect to press first."
                lowered = revised[index].lower()
        for label, holder_name in holder_by_item.items():
            if label in lowered and _contains_any(lowered, _ITEM_EXPOSED_TERMS):
                revised[index] = f"{holder_name} keeps the {label} in hand rather than leaving it exposed."
                break

    if assistant_name and assistant_name in support_claims and assistant_name in question_claims:
        objective_rewritten = _rewrite_question_target_reference(
            actionable_objective,
            assistant_name,
            "the strongest suspect",
            aliases.get(assistant_name, ()),
        )
        if objective_rewritten != actionable_objective:
            revised.append(objective_rewritten)

    return revised[:4]
