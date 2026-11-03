"""A fact-backed world model for narrated games."""

from .incidental import EmbellishResult, IncidentalPolicy, PhraseRouting, PropProposal, PropTemplate, TraitProposal
from .model import BASE_KINDS, Fact, FactBackend, MemoryBackend, OpResult, SchemaError, World, WorldSchema

__all__ = [
    "BASE_KINDS",
    "EmbellishResult",
    "Fact",
    "FactBackend",
    "IncidentalPolicy",
    "MemoryBackend",
    "OpResult",
    "PhraseRouting",
    "PropProposal",
    "PropTemplate",
    "SchemaError",
    "TraitProposal",
    "World",
    "WorldSchema",
]
