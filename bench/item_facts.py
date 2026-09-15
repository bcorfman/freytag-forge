"""Bench-only tracking of plain facts about named scene things."""

from __future__ import annotations

import copy
from collections.abc import Mapping
from urllib.error import HTTPError, URLError

from storygame.runtime.cloudflare import CloudflareTurnProvider, NarrationProviderError
from storygame.runtime.contracts import RuntimeContractError
from storygame.runtime.validation import ProposalValidationError

_SINGLE_CALL_RULES = (
    "Also return item_facts: every thing from THINGS, with its facts as a list of short phrases.",
    "Change a thing's facts only when your story changes that thing. Keep every other fact the same.",
)
_SECOND_CALL_SYSTEM = (
    "You keep track of things in a story. Read THINGS, PLAYER and STORY. Return only JSON like "
    '{"item_facts": {"thing": ["fact", "fact"]}}. List every thing from THINGS. Change a thing\'s facts '
    "only when STORY changes that thing. Keep every other fact the same."
)


class ItemFactsProvider(CloudflareTurnProvider):
    """Cloudflare provider with a bench-only, plain-facts side channel."""

    def __init__(
        self,
        *,
        item_facts: Mapping[str, list[str]],
        mode: str,
        **kwargs: object,
    ) -> None:
        super().__init__(**kwargs)
        self.item_facts = {name: list(facts) for name, facts in item_facts.items()}
        self.item_facts_seed_names = tuple(self.item_facts)
        self.item_facts_mode = mode
        self._pending_item_facts: object = None
        self._pending_item_facts_present = False

    @classmethod
    def from_environment(
        cls,
        state,
        *,
        prompt_variant: Mapping[str, object] | None = None,
        item_facts: Mapping[str, list[str]],
        mode: str,
    ) -> ItemFactsProvider:
        # Let the shipped provider perform its normal environment validation and
        # then reuse the resolved transport settings for this bench subclass.
        base = CloudflareTurnProvider.from_environment(state, prompt_variant=prompt_variant)
        return cls(
            worker_url=base.worker_url,
            token=base.token,
            state=state,
            projector=base.projector,
            prompt_variant=prompt_variant,
            item_facts=item_facts,
            mode=mode,
        )

    def _things_block(self) -> str:
        lines = ["THINGS:"]
        for name in self.item_facts_seed_names:
            facts = ", ".join(self.item_facts[name])
            lines.append(f"- {name}: {facts}")
        return "\n".join(lines)

    def _section_user_prompt(self, user: dict[str, object]) -> str:
        rendered = super()._section_user_prompt(user)
        things = self._things_block()
        marker = "\n\nCONSTRAINTS:"
        if marker in rendered:
            return rendered.replace(marker, f"\n\n{things}{marker}", 1)
        return f"{rendered}\n\n{things}" if rendered else things

    def _placement_rules(self) -> list[str]:
        return []

    def _setting_fact_rules(self) -> list[str]:
        return []

    def _parse_eligible_proposal(self, response: object) -> object:
        try:
            return super()._parse_eligible_proposal(response)
        except RuntimeContractError as error:
            # An uncommitted grounding is a runtime rejection for the fixed-turn
            # item-facts replay. Keep its side-channel reply out of recovery.
            if getattr(error, "summary", "") == "segment grounding is not committed or selected knowledge":
                raise ProposalValidationError(
                    "segment grounding is not committed or selected knowledge",
                    code="invalid_grounding_reference",
                ) from error
            raise

    def _system_prompt(self) -> str:
        system = super()._system_prompt()
        if self.item_facts_mode == "single_call":
            return f"{system}\n{_SINGLE_CALL_RULES[0]}\n{_SINGLE_CALL_RULES[1]}"
        return system

    def _request(self, payload: dict[str, object]) -> object:
        response = super()._request(payload)
        if isinstance(response, dict):
            self._pending_item_facts_present = "item_facts" in response
            self._pending_item_facts = copy.deepcopy(response.get("item_facts"))
            cleaned = dict(response)
            cleaned.pop("item_facts", None)
            return cleaned
        self._pending_item_facts_present = False
        self._pending_item_facts = copy.deepcopy(response)
        return response

    def pending_item_facts(self) -> object:
        return copy.deepcopy(self._pending_item_facts) if self._pending_item_facts_present else None

    def discard_pending_item_facts(self) -> None:
        self._pending_item_facts = None
        self._pending_item_facts_present = False

    def apply_item_facts(self, raw: object) -> tuple[dict[str, list[str]], list[str]]:
        previous = {name: list(facts) for name, facts in self.item_facts.items()}
        issues: list[str] = []
        if not isinstance(raw, dict):
            issues.append("item_facts must be an object mapping thing names to fact lists")
            return previous, issues

        for name in raw:
            if name not in self.item_facts:
                issues.append(f"unknown item_facts name {name!r} was dropped")

        updated: dict[str, list[str]] = {}
        for name in self.item_facts_seed_names:
            if name not in raw:
                issues.append(f"item_facts is missing seed thing {name!r}")
                updated[name] = previous[name]
                continue
            value = raw[name]
            if (
                not isinstance(value, list)
                or not value
                or any(not isinstance(phrase, str) or not phrase.strip() for phrase in value)
            ):
                issues.append(f"item_facts for {name!r} must be a non-empty list of non-empty strings")
                updated[name] = previous[name]
                continue
            updated[name] = [phrase.strip()[:80] for phrase in value[:6]]

        self.item_facts = updated
        return {name: list(facts) for name, facts in updated.items()}, issues

    def second_call_update(self, player_input: str, narration: str) -> object:
        payload = {
            "system": _SECOND_CALL_SYSTEM,
            "user": f"{self._things_block()}\n\nPLAYER:\n- {player_input}\n\nSTORY:\n{narration}",
            "max_tokens": 400,
            "response_format": {"type": "json_object"},
        }
        try:
            response = self._request_allowing_one_transient_retry(payload)
        except NarrationProviderError:
            raise
        except (HTTPError, URLError, OSError, TimeoutError, ValueError) as error:
            raise NarrationProviderError("narration service is unavailable") from error
        if self._pending_item_facts_present:
            return copy.deepcopy(self._pending_item_facts)
        return response


def validate_item_facts(value: object) -> tuple[str, dict[str, list[str]]] | None:
    """Validate and copy a variation's item_facts option."""

    if not isinstance(value, dict):
        raise ValueError("item_facts must be an object with mode and a non-empty seed")
    mode = value.get("mode")
    if mode not in {"single_call", "second_call"}:
        raise ValueError("item_facts must have mode single_call or second_call")
    seed = value.get("seed")
    if not isinstance(seed, dict) or not seed:
        raise ValueError("item_facts must have a non-empty seed object")
    copied: dict[str, list[str]] = {}
    for name, facts in seed.items():
        if not isinstance(name, str) or not name.strip():
            raise ValueError("item_facts seed names must be non-empty strings")
        if (
            not isinstance(facts, list)
            or not facts
            or not all(isinstance(fact, str) and fact.strip() for fact in facts)
        ):
            raise ValueError(f"item_facts seed for {name!r} must be a non-empty list of non-empty strings")
        copied[name] = list(facts)
    return mode, copied
