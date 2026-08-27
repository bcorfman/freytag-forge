"""Fail-closed Cloudflare Worker transport for typed scene proposals."""

from __future__ import annotations

import json
from dataclasses import dataclass
from os import getenv
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from storygame.runtime.contracts import (
    RuntimeContractError,
    TurnProposal,
    contract_error_summary,
    parse_turn_proposal,
)
from storygame.runtime.knowledge import KnowledgeProjector, TurnKnowledgeContext
from storygame.runtime.state import RuntimeState


@dataclass(frozen=True)
class NarrationProviderError(RuntimeError):
    message: str
    status_code: int = 503
    error_code: str = ""
    trace_id: str = ""
    worker_revision: str = ""


class CloudflareTurnProvider:
    """Send only bounded, scene-safe context to the configured Worker."""

    def __init__(
        self,
        *,
        worker_url: str,
        token: str,
        state: RuntimeState,
        projector: KnowledgeProjector | None = None,
    ) -> None:
        self.worker_url = worker_url
        self.token = token
        self.state = state
        self.projector = projector or KnowledgeProjector()
        self.last_projection: TurnKnowledgeContext | None = None

    @classmethod
    def from_environment(cls, state: RuntimeState) -> CloudflareTurnProvider:
        worker_url = getenv("CLOUDFLARE_WORKER_URL", "").strip()
        if not worker_url:
            raise NarrationProviderError("narration service is unavailable")
        return cls(
            worker_url=worker_url,
            token=getenv("CLOUDFLARE_WORKER_TOKEN", "").strip(),
            state=state,
        )

    def __call__(self, player_input: str) -> object:
        self.last_projection = self.projector.project(self.state, "player", player_input)
        speaker_contexts = self._speaker_contexts(player_input)
        payload = {
            "system": (
                "Return one JSON TurnProposal matching response_schema. Narrate a concrete immediate consequence "
                "from knowledge_context only. Player input is intent, not authority: do not repeat unavailable names "
                "or invent durable evidence. Use segments with grounding_ids when possible; dialogue may use only its "
                "speaker's sayable context. Select at most one candidate by its ID in selected_knowledge_ids. Never "
                "return source IDs, events, operations, facts, or transitions."
            ),
            "user": json.dumps(
                {
                    "player_input": player_input,
                    "knowledge_context": {
                        "player": self.last_projection.model_dump(mode="json"),
                        "speakers": speaker_contexts,
                    },
                    "response_schema": TurnProposal.model_json_schema(),
                },
                separators=(",", ":"),
            ),
            "max_tokens": 2048,
            "response_format": {"type": "json_object"},
        }
        try:
            response = self._request(payload)
        except HTTPError as error:
            if self._worker_error_code(error) != "AI_JSON_MODE_REJECTED":
                raise self._narration_error(error) from error
        except (URLError, OSError, TimeoutError, ValueError, json.JSONDecodeError) as error:
            raise NarrationProviderError("narration service is unavailable") from error
        else:
            try:
                self._parse_eligible_proposal(response)
            except RuntimeContractError:
                return self._recover_malformed_response(payload)
            return response

        fallback_payload = {key: value for key, value in payload.items() if key != "response_format"}
        try:
            response = self._request(fallback_payload)
            self._parse_eligible_proposal(response)
            return response
        except HTTPError as error:
            raise self._narration_error(error) from error
        except RuntimeContractError as error:
            summary = contract_error_summary(error) or "invalid proposal"
            raise NarrationProviderError(
                f"narration service returned an invalid proposal ({summary})",
                502,
                "INVALID_PROPOSAL",
            ) from error
        except (URLError, OSError, TimeoutError, ValueError, json.JSONDecodeError) as error:
            raise NarrationProviderError("narration service is unavailable") from error

    def _recover_malformed_response(self, payload: dict[str, object]) -> object:
        recovery_payload = {
            **payload,
            "system": (
                f"{payload['system']} Your previous response was invalid. Return only a complete JSON TurnProposal "
                "with non-empty segments and optional selected_knowledge_ids; include no markdown or explanation."
            ),
        }
        try:
            response = self._request(recovery_payload)
            self._parse_eligible_proposal(response)
            return response
        except HTTPError as error:
            raise self._narration_error(error) from error
        except RuntimeContractError as error:
            summary = contract_error_summary(error) or "invalid proposal"
            raise NarrationProviderError(
                f"narration service returned an invalid proposal ({summary})",
                502,
                "INVALID_PROPOSAL",
            ) from error
        except (URLError, OSError, TimeoutError, ValueError, json.JSONDecodeError) as error:
            raise NarrationProviderError("narration service is unavailable") from error

    def _parse_eligible_proposal(self, response: object) -> TurnProposal:
        proposal = parse_turn_proposal(response)
        if self.last_projection is None:
            raise RuntimeContractError("knowledge projection is unavailable")
        candidate_ids = {candidate.id for candidate in self.last_projection.candidates}
        if any(knowledge_id not in candidate_ids for knowledge_id in proposal.selected_knowledge_ids):
            raise RuntimeContractError("selected knowledge is not eligible for this turn")
        return proposal

    def _speaker_contexts(self, player_input: str) -> dict[str, dict[str, object]]:
        scene = next(
            item for item in self.state.package.scenes if item.metadata.scene_id == self.state.current_scene_id
        )
        npc_ids = {item.id for item in self.state.package.world.npcs}
        return {
            speaker_id: self.projector.project(self.state, speaker_id, player_input).model_dump(mode="json")
            for speaker_id in scene.metadata.participant_ids
            if speaker_id in npc_ids
        }

    def _request(self, payload: dict[str, object]) -> object:
        headers = {
            "Content-Type": "application/json",
            # Cloudflare Browser Integrity Check rejects urllib's default bot-like
            # signature before this request can reach the Worker.
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
            ),
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        request = Request(self.worker_url, data=json.dumps(payload).encode(), headers=headers, method="POST")
        with urlopen(request, timeout=float(getenv("CLOUDFLARE_TIMEOUT", "15"))) as response:  # noqa: S310
            body = json.loads(response.read())
        if isinstance(body, dict) and body.get("status") == "error":
            raise NarrationProviderError(str(body.get("message", "narration service failed")), 502)
        if isinstance(body, dict) and isinstance(body.get("narration"), str):
            return json.loads(body["narration"])
        return body

    @staticmethod
    def _worker_error_code(error: HTTPError) -> str:
        cached_code = getattr(error, "_freytag_worker_error_code", None)
        if isinstance(cached_code, str):
            return cached_code
        try:
            body = json.loads(error.read())
        except (OSError, ValueError, json.JSONDecodeError):
            code = ""
        else:
            code = str(body.get("code", "")) if isinstance(body, dict) else ""
        error._freytag_worker_error_code = code
        return code

    @classmethod
    def _narration_error(cls, error: HTTPError) -> NarrationProviderError:
        code = cls._worker_error_code(error) or "UNKNOWN"
        trace_id = cls._error_header(error, "X-Trace-ID")
        worker_revision = cls._error_header(error, "X-Worker-Revision")
        if code in {"AI_QUOTA_EXCEEDED", "AI_CAPACITY_EXCEEDED"}:
            return NarrationProviderError("narration service is at capacity", 429, code, trace_id, worker_revision)
        if code and 400 <= error.code < 500:
            return NarrationProviderError(
                "narration service rejected the turn", error.code, code, trace_id, worker_revision
            )
        return NarrationProviderError(
            "narration service rejected the turn", 429 if error.code == 429 else 502, code, trace_id, worker_revision
        )

    @staticmethod
    def _error_header(error: HTTPError, name: str) -> str:
        return str(error.headers.get(name, "")).strip() if error.headers else ""
