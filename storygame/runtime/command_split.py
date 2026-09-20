"""Deterministically split coordinated imperative commands."""

from __future__ import annotations

from functools import lru_cache

import spacy
from spacy.language import Language
from spacy.tokens import Span, Token


@lru_cache(maxsize=1)
def _get_pipeline() -> Language:
    """Load the parser only when the first player command needs it."""

    return spacy.load("en_core_web_sm")


def split_command(text: str) -> list[str]:
    """Split coordinated top-level imperative actions into separate sentences."""

    if not text or not text.strip():
        return [text]

    try:
        doc = _get_pipeline()(text)
        sentences = tuple(doc.sents)
    except Exception:
        return [text]

    if not sentences:
        return [text]

    pieces: list[str] = []
    did_split = False
    for sentence in sentences:
        sentence_pieces = _split_sentence(sentence)
        pieces.extend(sentence_pieces)
        did_split |= len(sentence_pieces) > 1

    return pieces if did_split else [text]


def _split_sentence(sentence: Span) -> list[str]:
    quoted = _quoted_token_indexes(sentence)
    root, parsed_root = _imperative_root(sentence)
    if root is None or parsed_root is None or root.i in quoted:
        return [sentence.text]

    action_roots = _coordinated_verbs(parsed_root, quoted)
    action_roots = [action_root for action_root in action_roots if action_root.i > root.i]
    if not action_roots:
        return [sentence.text]

    starts = [sentence.start, *(action_root.i for action_root in action_roots)]
    pieces: list[str] = []
    for piece_number, start in enumerate(starts):
        end = starts[piece_number + 1] if piece_number + 1 < len(starts) else sentence.end
        piece = sentence.doc[start:end].text.strip()
        if piece_number + 1 < len(starts):
            piece = _drop_separator(piece, sentence.doc[start:end])
            piece = f"{piece}."
        else:
            piece = _add_terminal_punctuation(piece)
        pieces.append(_capitalize(piece))
    return pieces


def _imperative_root(sentence: Span) -> tuple[Token | None, Token | None]:
    roots = [token for token in sentence if token.dep_ == "ROOT"]
    if len(roots) != 1:
        return None, None

    parsed_root = roots[0]
    if parsed_root.pos_ == "VERB" and (parsed_root.tag_ == "VB" or "Imp" in parsed_root.morph.get("Mood")):
        return parsed_root, parsed_root

    # The small model can attach a sentence-initial imperative such as
    # "Unplug" below a noun root. A leading noun/proper noun with a coordinated
    # verb is the same top-level imperative shape, so use that leading token as
    # the action root without relying on a verb vocabulary.
    first = sentence[0] if sentence else None
    if (
        first is not None
        and first.i == sentence.start
        and first.pos_ in {"NOUN", "PROPN"}
        and parsed_root.pos_ in {"NOUN", "PROPN"}
        and any(child.dep_ == "conj" and child.pos_ == "VERB" for child in parsed_root.children)
    ):
        return first, parsed_root
    return None, None


def _coordinated_verbs(parsed_root: Token, quoted: set[int]) -> list[Token]:
    action_roots: list[Token] = []
    pending = [child for child in parsed_root.children if child.dep_ == "conj"]
    while pending:
        candidate = pending.pop(0)
        if candidate.dep_ != "conj":
            continue
        if candidate.pos_ == "VERB" and candidate.i not in quoted:
            action_roots.append(candidate)
            pending.extend(child for child in candidate.children if child.dep_ == "conj")
    return sorted(action_roots, key=lambda token: token.i)


def _quoted_token_indexes(sentence: Span) -> set[int]:
    quoted: set[int] = set()
    inside_quote = False
    for token in sentence:
        if token.is_quote:
            inside_quote = not inside_quote
        elif inside_quote:
            quoted.add(token.i)
    return quoted


def _drop_separator(piece: str, span: Span) -> str:
    end = len(span) - 1
    while end >= 0:
        token = span[end]
        if token.is_punct or token.dep_ == "cc" or token.text.casefold() == "then":
            end -= 1
            continue
        break
    return piece[: span[end].idx - span[0].idx + len(span[end])].rstrip() if end >= 0 else ""


def _add_terminal_punctuation(piece: str) -> str:
    piece = piece.rstrip()
    if not piece or piece[-1] not in ".!?":
        return f"{piece}."
    return piece


def _capitalize(piece: str) -> str:
    if not piece:
        return piece
    return piece[0].upper() + piece[1:]
