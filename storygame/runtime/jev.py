"""Small fail-closed client for structured Jev evaluations."""

from __future__ import annotations

import json
from dataclasses import dataclass
from os import getenv
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from storygame.runtime.cloudflare import BROWSER_USER_AGENT
from storygame.runtime.hedged_request import HedgedResult, configured_hedge_delay, hedged_call

THRESHOLD = 0.5  # This matches bench/jev-judge.mjs.
JEV_REQUEST_TIMEOUT_SECONDS = 15.0
# A duplicate starts after 2.5 seconds; FREYTAG_HEDGE_DELAY_S=0 disables it.
JEV_HEDGE_DELAY_SECONDS = 2.5


@dataclass(frozen=True)
class _JevAttemptResult:
    answers: dict | None
    status: int
    model: str | None


class JevClient:
    def __init__(
        self,
        worker_url: str,
        token: str,
        *,
        opener=None,
        timeout: float = JEV_REQUEST_TIMEOUT_SECONDS,
    ) -> None:
        self.worker_url = worker_url
        self.token = token
        self.opener = opener or urlopen
        self.timeout = timeout
        self.request_count = 0
        self.last_model: str | None = None
        self.last_status: int | None = None
        self.last_hedge: HedgedResult[_JevAttemptResult] | None = None

    @classmethod
    def from_environment(cls) -> JevClient:
        return cls(
            worker_url=getenv("CLOUDFLARE_WORKER_URL", "").strip(),
            token=getenv("CLOUDFLARE_WORKER_TOKEN", "").strip(),
        )

    def ask(self, state: object, questions: object) -> dict | None:
        self.last_model = None
        self.last_status = None
        self.last_hedge = None
        self.request_count += 1
        worker_url = self.worker_url.strip()
        if not worker_url:
            return None
        payload = json.dumps({"input": {"state": state, "questions": questions}}).encode()
        headers = {"Content-Type": "application/json", "User-Agent": BROWSER_USER_AGENT}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        try:
            result = hedged_call(
                lambda: self._post(worker_url, payload, headers),
                delay_s=configured_hedge_delay(JEV_HEDGE_DELAY_SECONDS),
                timeout_s=self.timeout,
            )
            self.last_hedge = result
            self.last_status = result.value.status
            self.last_model = result.value.model
            return result.value.answers
        except HTTPError as error:
            self.last_status = error.code
            return None
        except (URLError, OSError, TimeoutError, ValueError, TypeError):
            return None

    def _post(self, worker_url: str, payload: bytes, headers: dict[str, str]) -> _JevAttemptResult:
        request = Request(f"{worker_url.rstrip('/')}/jev", data=payload, headers=headers, method="POST")
        with self.opener(request, timeout=self.timeout) as response:
            status = getattr(response, "status", 200)
            if status >= 400:
                return _JevAttemptResult(None, status, None)
            body = json.loads(response.read())
        if not isinstance(body, dict):
            return _JevAttemptResult(None, status, None)
        if body.get("status") == "error":
            return _JevAttemptResult(None, status, None)
        answers = body.get("answers")
        if not isinstance(answers, dict):
            return _JevAttemptResult(None, status, None)
        model = body.get("model")
        return _JevAttemptResult(answers, status, model if isinstance(model, str) and model else None)


def noul_yes(answer: object) -> bool | None:
    if not isinstance(answer, dict):
        return None
    value = answer.get("noul")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value > THRESHOLD
