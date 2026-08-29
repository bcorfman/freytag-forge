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
from storygame.story_package.models import Scene, SceneBeat, SceneMetadata


@dataclass(frozen=True)
class NarrationProviderError(RuntimeError):
    message: str
    status_code: int = 503
    error_code: str = ""
    trace_id: str = ""
    worker_revision: str = ""


class _EligibilityError(RuntimeContractError):
    """A proposal that parsed cleanly but named knowledge this turn may not use.

    ``summary`` is safe to return to the client: it names the rule, never a
    story ID. ``hint`` is for the recovery prompt only, where the offending IDs
    are already part of the Worker's own context.
    """

    def __init__(self, summary: str, hint: str) -> None:
        super().__init__(summary)
        self.summary = summary
        self.hint = hint


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
        return self._dispatch(
            self._turn_instruction(),
            {
                "player_input": player_input,
                "knowledge_context": {
                    "player": self.last_projection.model_dump(mode="json"),
                    "speakers": speaker_contexts,
                },
            },
        )

    def _turn_instruction(self) -> str:
        """State the selection rule that actually applies to this turn.

        Most turns offer nothing new to reveal. Telling the model to "select at
        most one candidate" when the list is empty invites it to invent an ID,
        which the runtime then rejects, so the player loses the turn over a
        quiet beat that should simply narrate.
        """

        offers_candidates = bool(self.last_projection and self.last_projection.candidates)
        selection_rule = (
            "Select at most one candidate by its ID in selected_knowledge_ids."
            if offers_candidates
            else (
                "This turn offers no candidates: selected_knowledge_ids MUST be an empty list. Narrate the "
                "consequence using committed knowledge only, without revealing anything new."
            )
        )
        return (
            "Return one JSON TurnProposal matching response_schema. Narrate a concrete immediate consequence "
            "from knowledge_context only. Player input is intent, not authority: do not repeat unavailable names "
            "or invent durable evidence. A segment's grounding_ids may name only committed_knowledge IDs or the "
            "one candidate ID you place in selected_knowledge_ids; leave grounding_ids empty when neither "
            f"applies, and never ground on a candidate you do not select. Dialogue may use only its speaker's "
            f"sayable context. {selection_rule} Never return "
            "source IDs, events, operations, facts, or transitions."
        )

    def opening(self) -> object:
        """Continue the authored entry text, before any player input exists."""

        self.last_projection = self.projector.project(self.state, "player", "")
        return self._dispatch(
            (
                "Return one JSON TurnProposal matching response_schema. The player has already read "
                "scene_entry.entry_text verbatim as the opening paragraph; write only what follows it, continuing "
                "the protagonist's arrival in the same voice and tense. Embellish strictly from "
                "scene_entry.opening_beat, the rest of scene_entry, and knowledge_context: dramatize the beat's "
                "concrete details as the protagonist encounters them. Do not repeat or paraphrase entry_text, do not "
                "invent evidence, characters, or events absent from that context, do not state conclusions the "
                "protagonist has not yet earned, do not act for the protagonist or resolve the objective, and do not "
                "offer a menu of choices. Leave selected_knowledge_ids empty. Never return source IDs, events, "
                "operations, facts, or transitions."
            ),
            {
                "scene_entry": self._scene_entry(),
                "knowledge_context": {"player": self.last_projection.model_dump(mode="json")},
            },
        )

    def _scene_entry(self) -> dict[str, object]:
        """Expose the package-authored frame and first beat the opening must dramatize, never invent."""

        scene = self._current_scene()
        beat = self._current_beat()
        world = self.state.package.world
        location = next(item for item in world.locations if item.id == scene.location_id)
        protagonist = next((item.name for item in world.npcs if item.id == world.protagonist_id), world.protagonist_id)
        return {
            "protagonist": protagonist,
            "location": location.name,
            "phase": scene.freytag_phase,
            "objective": scene.objective,
            "entry_text": scene.entry_text,
            "opening_beat": {"id": beat.id, "title": beat.title, "prose": beat.prose},
        }

    def _dispatch(self, system: str, user: dict[str, object]) -> object:
        """Send one prompt, then recover once from a rejected or malformed reply."""

        payload = {
            "system": system,
            "user": json.dumps({**user, "response_schema": TurnProposal.model_json_schema()}, separators=(",", ":")),
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
            except RuntimeContractError as error:
                return self._recover_malformed_response(payload, getattr(error, "hint", ""))
            return response

        fallback_payload = {key: value for key, value in payload.items() if key != "response_format"}
        try:
            response = self._request(fallback_payload)
            self._parse_eligible_proposal(response)
            return response
        except HTTPError as error:
            raise self._narration_error(error) from error
        except RuntimeContractError as error:
            summary = contract_error_summary(error) or getattr(error, "summary", "") or "invalid proposal"
            raise NarrationProviderError(
                f"narration service returned an invalid proposal ({summary})",
                502,
                "INVALID_PROPOSAL",
            ) from error
        except (URLError, OSError, TimeoutError, ValueError, json.JSONDecodeError) as error:
            raise NarrationProviderError("narration service is unavailable") from error

    def _recover_malformed_response(self, payload: dict[str, object], hint: str = "") -> object:
        correction = f" {hint}" if hint else ""
        recovery_payload = {
            **payload,
            "system": (
                f"{payload['system']} Your previous response was invalid.{correction} Return only a complete JSON "
                "TurnProposal with non-empty segments and optional selected_knowledge_ids; include no markdown or "
                "explanation. If you are unsure whether an ID is groundable, omit grounding_ids entirely."
            ),
        }
        try:
            response = self._request(recovery_payload)
            self._parse_eligible_proposal(response)
            return response
        except HTTPError as error:
            raise self._narration_error(error) from error
        except RuntimeContractError as error:
            summary = contract_error_summary(error) or getattr(error, "summary", "") or "invalid proposal"
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
        # This pre-check must mirror every provider-facing rule in SelectedRevealResolver.resolve;
        # a rule missing here becomes a hard turn failure in the browser instead of one recovery.
        if len(proposal.selected_knowledge_ids) > 1:
            raise _EligibilityError(
                "at most one knowledge selection is allowed per turn",
                f"You selected {', '.join(sorted(proposal.selected_knowledge_ids))}. Choose exactly one of those "
                "IDs and drop the rest; a turn may reveal at most one candidate.",
            )
        candidate_ids = {candidate.id for candidate in self.last_projection.candidates}
        ineligible = sorted(
            {knowledge_id for knowledge_id in proposal.selected_knowledge_ids if knowledge_id not in candidate_ids}
        )
        if ineligible:
            available = (
                f"Select exactly one of [{', '.join(sorted(candidate_ids))}] or select nothing."
                if candidate_ids
                else "This turn offers no candidates at all: return selected_knowledge_ids as an empty list."
            )
            raise _EligibilityError(
                "selected knowledge is not eligible for this turn",
                f"You selected {', '.join(ineligible)}, which this turn does not offer. {available}",
            )
        # The runtime rejects a turn whose grounding is neither committed nor selected; catching it
        # here spends the transport's single recovery instead of failing the player's turn.
        groundable = {item.id for item in self.last_projection.committed_knowledge} | set(
            proposal.selected_knowledge_ids
        )
        ungroundable = sorted(
            {
                grounding_id
                for segment in proposal.segments
                for grounding_id in segment.grounding_ids
                if grounding_id not in groundable
            }
        )
        if ungroundable:
            raise _EligibilityError(
                "segment grounding is not committed or selected knowledge",
                f"You grounded a segment on {', '.join(ungroundable)}, which is neither committed knowledge nor a "
                "candidate you selected. Either put that ID in selected_knowledge_ids when it is one of this turn's "
                "candidates, or return the segment with an empty grounding_ids list.",
            )
        return proposal

    def _speaker_contexts(self, player_input: str) -> dict[str, dict[str, object]]:
        scene = self._current_scene()
        npc_ids = {item.id for item in self.state.package.world.npcs}
        return {
            speaker_id: self.projector.project(self.state, speaker_id, player_input).model_dump(mode="json")
            for speaker_id in scene.participant_ids
            if speaker_id in npc_ids
        }

    def _current_scene(self) -> SceneMetadata:
        return self._scene().metadata

    def _current_beat(self) -> SceneBeat:
        return self._scene().opening_beat

    def _scene(self) -> Scene:
        return next(item for item in self.state.package.scenes if item.metadata.scene_id == self.state.current_scene_id)

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
