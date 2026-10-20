"""Raw narrator adapter and auditable request budgets for the door screen."""

from __future__ import annotations

import json
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass, field
from typing import Any

from storygame.runtime.contracts import TurnProposal, parse_turn_proposal


class RawRequestError(RuntimeError):
    """A single door request failed, retaining the response evidence if any."""

    def __init__(self, stage: str, error: BaseException, normalized: Any = None) -> None:
        self.stage = stage
        self.error_text = str(error)
        self.error = self.error_text
        self.original_error = error
        self.normalized = normalized
        super().__init__(self.error_text)


@dataclass
class SpendBudget:
    limit: int
    cloudflare_limit: int | None = None
    player_limit: int | None = None
    sent: int = 0
    acknowledged: int = 0
    events: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.cloudflare_limit is None:
            self.cloudflare_limit = self.limit
        if self.player_limit is None:
            self.player_limit = self.limit

    @property
    def cloudflare_requests(self) -> int:
        return sum(event.get("kind") == "cloudflare" for event in self.events)

    @property
    def raw_player_attempts(self) -> int:
        return sum(event.get("kind") == "raw_player" for event in self.events)

    @property
    def cloudflare_acknowledged(self) -> int:
        return sum(event.get("kind") == "cloudflare" and event.get("status") != "reserved" for event in self.events)

    @property
    def player_acknowledged(self) -> int:
        return sum(event.get("kind") == "raw_player" and event.get("status") != "reserved" for event in self.events)

    def reserve(self, kind: str, detail: str = "") -> None:
        event_kind = "raw_player" if kind in {"player", "raw_player"} else "cloudflare"
        cap = self.player_limit if event_kind == "raw_player" else self.cloudflare_limit
        used = self.raw_player_attempts if event_kind == "raw_player" else self.cloudflare_requests
        if used >= cap:
            raise RuntimeError(f"{event_kind} request cap exhausted ({cap})")
        self.sent += 1
        self.events.append({"kind": event_kind, "sequence": self.sent, "status": "reserved", "detail": detail})

    def acknowledge(self, kind: str, ok: bool, error: str | None = None) -> None:
        self.acknowledged += 1
        event_kind = "raw_player" if kind in {"player", "raw_player"} else "cloudflare"
        event = next(
            event for event in reversed(self.events) if event["kind"] == event_kind and event["status"] == "reserved"
        )
        event.update({"status": "ok" if ok else "failed", "error": error})


class _CountedProvider:
    """Temporarily count provider sends without mutating raised exceptions."""

    def __init__(self, provider: Any, budget: SpendBudget) -> None:
        self.provider = provider
        self.budget = budget
        self.original = provider._request

    def __enter__(self) -> Any:
        def counted(payload: dict[str, Any]) -> Any:
            self.budget.reserve("cloudflare", str(payload.get("_request_budget", "narration")))
            try:
                result = self.original(payload)
            except Exception as error:
                self.budget.acknowledge("cloudflare", False, type(error).__name__)
                raise
            self.budget.acknowledge("cloudflare", True)
            return result

        self.provider._request = counted
        self.provider._door_counted = True
        return self.provider

    def __exit__(self, _exc_type: Any, _exc_value: BaseException | None, _traceback: Any) -> bool:
        self.provider._request = self.original
        with suppress(AttributeError):
            del self.provider._door_counted
        return False


def counted_provider(provider: Any, budget: SpendBudget) -> _CountedProvider:
    """Count every physical provider send, then restore the provider method."""

    return _CountedProvider(provider, budget)


@dataclass(frozen=True)
class RawProposal:
    request: dict[str, Any]
    normalized: Any
    proposal: TurnProposal
    telemetry: dict[str, Any]
    item_facts: Any = None


def _parse_payload(envelope: Any) -> tuple[Any, Any]:
    """Return the validation payload and any provider item-facts telemetry."""

    payload = envelope
    if isinstance(payload, dict) and "response" in payload:
        payload = payload["response"]
    if isinstance(payload, dict) and "content" in payload:
        payload = payload["content"]
    if isinstance(payload, str):
        payload = json.loads(payload)
    if isinstance(payload, dict) and "item_facts" in payload:
        item_facts = payload["item_facts"]
        payload = {key: value for key, value in payload.items() if key != "item_facts"}
        return payload, item_facts
    return payload, None


def raw_request(provider: Any, system: str, user: str, budget: SpendBudget | None = None) -> RawProposal:
    payload = {"system": system, "user": user, "max_tokens": 1024, "response_format": {"type": "json_object"}}
    if budget and not getattr(provider, "_door_counted", False):
        budget.reserve("cloudflare", "raw_2A")
    try:
        normalized = provider._request(payload)
    except Exception as error:
        if budget and not getattr(provider, "_door_counted", False):
            budget.acknowledge("cloudflare", False, type(error).__name__)
        last_response = next(
            (
                getattr(provider, name)
                for name in ("last_response", "last_response_body", "last_response_text")
                if hasattr(provider, name)
            ),
            None,
        )
        raise RawRequestError("request", error, last_response) from error
    try:
        validation_payload, item_facts = _parse_payload(normalized)
        proposal = parse_turn_proposal(validation_payload)
    except Exception as error:
        if budget and not getattr(provider, "_door_counted", False):
            budget.acknowledge("cloudflare", False, type(error).__name__)
        raise RawRequestError("parse", error, normalized) from error
    if proposal.selected_knowledge_ids:
        if budget and not getattr(provider, "_door_counted", False):
            budget.acknowledge("cloudflare", False, "unexpected selected knowledge IDs")
        raise ValueError("raw prompt screen received selected knowledge IDs")
    if budget and not getattr(provider, "_door_counted", False):
        budget.acknowledge("cloudflare", True)
    telemetry = {
        "request_count": getattr(provider, "request_count", None),
        "recovery_count": getattr(provider, "recovery_count", None),
        "reply_keys_dropped": dict(getattr(provider, "reply_keys_dropped", {})),
        "item_facts": item_facts,
    }
    return RawProposal(payload, normalized, proposal, telemetry, item_facts)


def without_semantic_fallback(provider: Any) -> Callable[[], None]:
    previous = getattr(provider, "semantic_ask", None)
    provider.semantic_ask = None
    if hasattr(provider, "contract_shadow_calls"):
        provider.contract_shadow_calls = 0
    return lambda: setattr(provider, "semantic_ask", previous)
