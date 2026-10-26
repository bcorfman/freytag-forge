"""Small fail-closed client for structured Jev evaluations."""

from __future__ import annotations

import json
from os import getenv
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from storygame.runtime.cloudflare import BROWSER_USER_AGENT

THRESHOLD = 0.5  # This matches bench/jev-judge.mjs.


class JevClient:
    def __init__(self, worker_url: str, token: str, *, opener=None, timeout: float = 15.0) -> None:
        self.worker_url = worker_url
        self.token = token
        self.opener = opener or urlopen
        self.timeout = timeout
        self.request_count = 0
        self.last_model: str | None = None
        self.last_status: int | None = None

    @classmethod
    def from_environment(cls) -> JevClient:
        return cls(
            worker_url=getenv("CLOUDFLARE_WORKER_URL", "").strip(),
            token=getenv("CLOUDFLARE_WORKER_TOKEN", "").strip(),
        )

    def ask(self, state: object, questions: object) -> dict | None:
        self.last_model = None
        self.last_status = None
        self.request_count += 1
        worker_url = self.worker_url.strip()
        if not worker_url:
            return None
        try:
            payload = json.dumps({"input": {"state": state, "questions": questions}}).encode()
            headers = {"Content-Type": "application/json", "User-Agent": BROWSER_USER_AGENT}
            if self.token:
                headers["Authorization"] = f"Bearer {self.token}"
            request = Request(f"{worker_url.rstrip('/')}/jev", data=payload, headers=headers, method="POST")
            with self.opener(request, timeout=self.timeout) as response:
                self.last_status = getattr(response, "status", 200)
                if self.last_status >= 400:
                    return None
                body = json.loads(response.read())
            if not isinstance(body, dict):
                return None
            if body.get("status") == "error":
                return None
            answers = body.get("answers")
            if not isinstance(answers, dict):
                return None
            model = body.get("model")
            if isinstance(model, str) and model:
                self.last_model = model
            return answers
        except HTTPError as error:
            self.last_status = error.code
            return None
        except (URLError, OSError, TimeoutError, ValueError, TypeError):
            return None


def noul_yes(answer: object) -> bool | None:
    if not isinstance(answer, dict):
        return None
    value = answer.get("noul")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value > THRESHOLD
