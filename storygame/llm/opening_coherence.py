from __future__ import annotations

_SUPPORT_ROLE_TERMS = ("assistant", "ally", "partner", "contact", "confidant")
_SUSPECT_ROLE_TERMS = ("suspect", "culprit", "killer", "mastermind")
_QUESTION_TARGET_TERMS = ("question", "interrogate", "interview", "press", "confront", "accuse")
_ASSISTANT_NEARBY_TERMS = ("beside you", "at your side", "keeps close beside you", "close beside you")
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
    "coat pocket",
    "jacket pocket",
    "tucked into",
)
_ITEM_EXPOSED_TERMS = (
    "wedged",
    "lodged",
    "lying",
    "exposed",
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


def opening_fact_parity_issues(
    opening_lines: list[str],
    assistant_name: str,
    assistant_role: str,
    assistant_present: bool,
    item_labels: tuple[str, ...],
    assistant_held_item_labels: tuple[str, ...],
) -> list[str]:
    issues: list[str] = []
    normalized_lines = [_normalized_line(line) for line in opening_lines if _normalized_line(line)]
    normalized_assistant = _normalize_name(assistant_name)
    normalized_role = " ".join(assistant_role.split()).strip().lower()
    held_labels = {_normalized_line(label).lower() for label in assistant_held_item_labels if _normalized_line(label)}
    seen_messages: set[str] = set()

    if not normalized_assistant:
        return issues

    assistant_lines = [line for line in normalized_lines if normalized_assistant in line.lower()]
    for line in assistant_lines:
        lowered = line.lower()
        if _contains_any(lowered, _SUPPORT_ROLE_TERMS) and normalized_role != "assistant":
            message = (
                f"{assistant_name} is described as your assistant/contact in the opening, "
                f"but committed facts mark that role as {assistant_role or 'unset'}."
            )
            if message not in seen_messages:
                issues.append(message)
                seen_messages.add(message)
        if _contains_any(lowered, _ASSISTANT_NEARBY_TERMS) and not assistant_present:
            message = (
                f"{assistant_name} is staged beside the player in the opening, "
                "but committed facts place them elsewhere."
            )
            if message not in seen_messages:
                issues.append(message)
                seen_messages.add(message)
        if not _contains_any(lowered, _ITEM_HOLDING_TERMS):
            continue
        mentioned = tuple(
            label
            for label in item_labels
            if label in lowered
        )
        if mentioned:
            for label in mentioned:
                if label in held_labels:
                    continue
                message = (
                    f"The opening gives {assistant_name} custody of the {label}, "
                    "but committed facts do not."
                )
                if message not in seen_messages:
                    issues.append(message)
                    seen_messages.add(message)

    return issues
