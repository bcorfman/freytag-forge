"""Shared character-name display rules."""

from __future__ import annotations


def short_name(npc) -> str:
    """Return the author's preferred short form for a character."""

    return npc.aliases[0] if npc.aliases else npc.name
