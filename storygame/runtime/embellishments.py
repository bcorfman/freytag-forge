"""Typed adaptation of narrator-supplied incidental world changes."""

from __future__ import annotations

from copy import deepcopy
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StrictStr, ValidationError, field_validator
from worldkeeper import EmbellishResult, PropProposal, TraitProposal

from storygame.runtime.facts import FactStore
from storygame.runtime.validation import ProposalValidationError
from storygame.runtime.world_model import apply_scene_placements, incidental_policy_for, world_for

Name = Annotated[StrictStr, Field(min_length=1, max_length=120)]


class _Entry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    @field_validator("template", "parent", "target", "facet", "value", mode="before", check_fields=False)
    @classmethod
    def stripped_name(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be blank")
        return stripped


class PropEntry(_Entry):
    template: Name
    parent: Name


class TraitEntry(_Entry):
    target: Name
    facet: Name
    value: Name


class Embellishments(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    props: tuple[PropEntry, ...] = ()
    traits: tuple[TraitEntry, ...] = ()

    def proposals(self) -> tuple[tuple[PropProposal, ...], tuple[TraitProposal, ...]]:
        return (
            tuple(PropProposal(item.template, item.parent) for item in self.props),
            tuple(TraitProposal(item.target, item.facet, item.value) for item in self.traits),
        )


def parse_embellishments(raw: object) -> Embellishments:
    if raw is None or raw == {}:
        return Embellishments()
    try:
        return Embellishments.model_validate(raw)
    except (TypeError, ValidationError) as error:
        raise ProposalValidationError(
            "The narrator supplied malformed world details.", code="embellishment_malformed"
        ) from error


def _checked(package, facts: FactStore, scene_id: str, value: Embellishments):
    policy = incidental_policy_for(package)
    if policy is None:
        raise ProposalValidationError("The package does not allow these world details.", code="embellishment_rejected")
    props, traits = value.proposals()
    result = world_for(package, facts).check_embellishments(policy, scene_id, props, traits)
    if not result.ok:
        raise ProposalValidationError(result.reason, code="embellishment_rejected")
    return policy, props, traits


def check_for_state(
    package, facts: FactStore, scene_id: str, raw: object, *, entered_scene: bool = False
) -> Embellishments:
    value = parse_embellishments(raw)
    if not value.props and not value.traits:
        return value
    scratch = facts.clone()
    if entered_scene:
        apply_scene_placements(package, scratch, scene_id)
    _checked(package, scratch, scene_id, value)
    return value


def commit_for_state(package, facts: FactStore, scene_id: str, value: Embellishments):
    policy = incidental_policy_for(package)
    props, traits = value.proposals()
    if policy is None:
        return EmbellishResult(False, "The package does not allow these world details.")
    return world_for(package, facts).apply_embellishments(policy, scene_id, props, traits)


def copy_raw(raw: object) -> object:
    return deepcopy(raw)
