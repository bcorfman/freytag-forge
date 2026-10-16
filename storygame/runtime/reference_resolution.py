"""Resolve short, scene-local references before a narration turn."""

from __future__ import annotations

import re
from dataclasses import dataclass

from storygame.runtime.fixed_refusal import _fixed_article_name
from storygame.runtime.knowledge import _entity_in_scene_scope
from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import display_name, world_for


@dataclass(frozen=True)
class Clarification:
    original_command: str
    noun: str
    options: tuple[tuple[str, str], ...]
    round: int


@dataclass(frozen=True)
class ReferenceResult:
    command: str
    question: Clarification | None
    outcome: str
    original: str
    resolutions: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class _Thing:
    entity_id: str
    name: str
    heads: tuple[str, ...]


@dataclass(frozen=True)
class _NounMatch:
    noun: str
    start: int
    end: int
    entity_ids: tuple[str, ...]


_STOPWORDS = frozenset(
    {
        "the",
        "a",
        "an",
        "of",
        "to",
        "my",
        "your",
        "our",
        "her",
        "his",
        "their",
        "and",
        "or",
        "on",
        "in",
        "at",
        "for",
        "from",
        "with",
        "into",
        "onto",
        "by",
        "is",
        "it",
        "this",
        "that",
        "one",
        "do",
        "you",
    }
)
_ORDINALS = {"first": 0, "1st": 0, "second": 1, "2nd": 1, "third": 2, "3rd": 2}


def _tokens(value: str) -> tuple[str, ...]:
    return tuple(re.findall(r"[\w']+", value.casefold()))


def _head_variants(word: str) -> tuple[str, ...]:
    variants = [word]
    if word.endswith("s") and len(word) > 3:
        variants.append(word[:-1])
    else:
        variants.append(f"{word}s")
    return tuple(dict.fromkeys(variants))


def _whole_form_pattern(form: str) -> re.Pattern[str]:
    parts = _tokens(form)
    return re.compile(r"(?<!\w)" + r"\s+".join(re.escape(part) for part in parts) + r"(?!\w)", re.IGNORECASE)


def _entity_forms(entity) -> tuple[str, ...]:
    return (entity.name, *entity.aliases)


def _masked_full_names(state: RuntimeState, command: str) -> tuple[str, frozenset[str]]:
    """Mask the simulation's full name/ordinary-alias forms, preserving offsets."""

    masked = list(command.casefold())
    matched: set[str] = set()
    entities = (
        *state.package.world.locations,
        *state.package.world.npcs,
        *state.package.world.groups,
        *state.package.world.items,
    )
    forms = sorted(
        ((form, entity.id) for entity in entities for form in _entity_forms(entity)),
        key=lambda item: len(item[0]),
        reverse=True,
    )
    folded = command.casefold()
    for form, entity_id in forms:
        pattern = _whole_form_pattern(form)
        for match in pattern.finditer(folded):
            matched.add(entity_id)
            masked[match.start() : match.end()] = " " * (match.end() - match.start())
    return "".join(masked), frozenset(matched)


def _scene_things(state: RuntimeState) -> tuple[_Thing, ...]:
    """Use knowledge._entity_in_scene_scope over world_for's live world for items, NPCs, and groups."""

    world = world_for(state.package, state.facts)
    scene = next(scene for scene in state.package.scenes if scene.metadata.scene_id == state.current_scene_id)
    things = []
    for entity in (*state.package.world.items, *state.package.world.npcs, *state.package.world.groups):
        if entity.id == state.package.protagonist_id or not _entity_in_scene_scope(
            world, entity.id, scene=scene, protagonist_id=state.package.protagonist_id
        ):
            continue
        name = display_name(state.package, state.facts, world, entity.id)
        heads = set()
        for form in (name, *entity.scoped_aliases):
            form_tokens = _tokens(form)
            if form_tokens and len(form_tokens[-1]) > 2 and form_tokens[-1] not in _STOPWORDS:
                heads.update(_head_variants(form_tokens[-1]))
        things.append(_Thing(entity.id, name, tuple(sorted(heads))))
    return tuple(things)


def _noun_matches(state: RuntimeState, command: str) -> tuple[_NounMatch, ...]:
    rest, full_matches = _masked_full_names(state, command)
    things = _scene_things(state)
    by_head: dict[str, set[str]] = {}
    for thing in things:
        if thing.entity_id in full_matches:
            continue
        for head in thing.heads:
            by_head.setdefault(head, set()).add(thing.entity_id)

    matches = []
    for noun, entity_ids in by_head.items():
        if len(noun) <= 2 or noun in _STOPWORDS:
            continue
        match = re.search(rf"(?<!\w){re.escape(noun)}(?!\w)", rest, re.IGNORECASE)
        if match:
            matches.append(_NounMatch(noun, match.start(), match.end(), tuple(sorted(entity_ids))))
    return tuple(sorted(matches, key=lambda match: (match.start, match.noun)))


def _replace_matches(command: str, matches: tuple[_NounMatch, ...], replacements: dict[str, str]) -> str:
    selected = [match for match in matches if match.noun in replacements]
    result = command
    for match in sorted(selected, key=lambda item: item.start, reverse=True):
        result = f"{result[: match.start]}{replacements[match.noun]}{result[match.end :]}"
    return result


def _options(state: RuntimeState, entity_ids: tuple[str, ...]) -> tuple[tuple[str, str], ...]:
    things = {thing.entity_id: thing for thing in _scene_things(state)}
    return tuple(
        (entity_id, things[entity_id].name)
        for entity_id in sorted(entity_ids, key=lambda item: (things[item].name.casefold(), item))
    )


def _clarification(state: RuntimeState, command: str, match: _NounMatch, round: int) -> Clarification:
    return Clarification(command, match.noun, _options(state, match.entity_ids), round)


def _fresh_result(
    state: RuntimeState, command: str, *, original: str, outcome: str, allow_question: bool = True
) -> ReferenceResult:
    matches = _noun_matches(state, command)
    ambiguous = next((match for match in matches if len(match.entity_ids) > 1), None)
    if ambiguous is not None and allow_question:
        return ReferenceResult(
            command=command,
            question=_clarification(state, command, ambiguous, 0),
            outcome="asked",
            original=original,
            resolutions=(),
        )
    resolutions = tuple((match.noun, match.entity_ids[0]) for match in matches if len(match.entity_ids) == 1)
    resolved_outcome = "resolved" if outcome == "passthrough" and resolutions else outcome
    return ReferenceResult(
        command=command,
        question=None,
        outcome=resolved_outcome,
        original=original,
        resolutions=resolutions,
    )


def _answer_option(clarification: Clarification, answer: str) -> tuple[str, str] | None:
    folded = answer.casefold()
    full_matches = [option for option in clarification.options if re.search(_whole_form_pattern(option[1]), folded)]
    if len(full_matches) == 1:
        return full_matches[0]

    distinguishing = []
    option_words = {entity_id: set(_tokens(name)) for entity_id, name in clarification.options}
    for word in _tokens(answer):
        owners = [entity_id for entity_id, words in option_words.items() if word in words]
        if len(owners) == 1:
            distinguishing.append(owners[0])
    if len(set(distinguishing)) == 1:
        entity_id = distinguishing[0]
        return next(option for option in clarification.options if option[0] == entity_id)

    ordinal = next((index for word, index in _ORDINALS.items() if re.search(rf"(?<!\w){word}(?!\w)", folded)), None)
    if ordinal is not None and ordinal < len(clarification.options):
        return clarification.options[ordinal]
    return None


def _render_option(name: str) -> str:
    if name and name[0].islower():
        return _fixed_article_name(name)
    if "'s " in name:
        return _fixed_article_name(name)
    return name


def clarification_text(clarification: Clarification) -> str:
    """Render the fixed Inform-style question without asking the narrator."""

    rendered = tuple(_render_option(name) for _entity_id, name in clarification.options)
    choices = " or ".join(rendered) if len(rendered) == 2 else ", ".join(rendered[:-1]) + f", or {rendered[-1]}"
    return f"Do you mean {choices}?"


def resolve_references(
    state: RuntimeState,
    player_input: str,
    *,
    clarifies: str | None = None,
    clarification_round: int = 0,
) -> ReferenceResult:
    """Resolve live scene-local bare heads; all pending clarification state stays with the caller."""

    if clarifies is None:
        return _fresh_result(state, player_input, original=player_input, outcome="passthrough")

    pending = _fresh_result(state, clarifies, original=clarifies, outcome="passthrough")
    if pending.question is None:
        fresh = _fresh_result(state, player_input, original=player_input, outcome="dropped")
        return fresh

    choice = _answer_option(pending.question, player_input)
    if choice is None:
        fresh = _fresh_result(state, player_input, original=player_input, outcome="dropped")
        return fresh

    option_id, option_name = choice
    pending_match = next(match for match in _noun_matches(state, clarifies) if match.noun == pending.question.noun)
    spliced = _replace_matches(clarifies, (pending_match,), {pending_match.noun: option_name})
    next_round = clarification_round + 1
    if next_round >= 2:
        capped = _fresh_result(state, spliced, original=player_input, outcome="capped", allow_question=False)
        return ReferenceResult(
            command=capped.command,
            question=None,
            outcome="capped",
            original=player_input,
            resolutions=((pending_match.noun, option_id), *capped.resolutions),
        )

    resolved = _fresh_result(state, spliced, original=player_input, outcome="answered")
    if resolved.question is None:
        return ReferenceResult(
            command=resolved.command,
            question=None,
            outcome="answered",
            original=player_input,
            resolutions=((pending_match.noun, option_id), *resolved.resolutions),
        )
    return ReferenceResult(
        command=spliced,
        question=Clarification(spliced, resolved.question.noun, resolved.question.options, next_round),
        outcome="answered",
        original=player_input,
        resolutions=((pending_match.noun, option_id),),
    )
