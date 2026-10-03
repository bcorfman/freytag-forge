"""Bench-only Jev questions sent directly to Cloudflare."""

from __future__ import annotations

import json
import os
import urllib.request

from storygame.runtime import jev_questions

THRESHOLD = 0.5  # Matches the threshold in bench/jev-judge.mjs.


def _ask(*, environment, opener):
    account = environment.get("CLOUDFLARE_ACCOUNT_ID")
    token = environment.get("CLOUDFLARE_AI_TOKEN")
    if not account or not token:
        return lambda _state, _questions: None

    def ask(state, questions):
        try:
            body = {"model": "typesafe/jev", "input": {"state": state, "questions": questions}}
            request = urllib.request.Request(
                f"https://api.cloudflare.com/client/v4/accounts/{account}/ai/run",
                data=json.dumps(body).encode(),
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
                method="POST",
            )
            with opener(request, timeout=30) as response:
                payload = json.loads(response.read())
            result = payload.get("result", {})
            if payload.get("success") is not True or result.get("state") != "Completed":
                return None
            answers = result.get("result", {}).get("answers")
            return answers if isinstance(answers, dict) else None
        except Exception:
            return None

    return ask


def ask_uses_thing(command: str, thing_name: str, *, environment=None, opener=None) -> bool | None:
    environment = os.environ if environment is None else environment
    opener = urllib.request.urlopen if opener is None else opener
    return jev_questions.uses_thing(_ask(environment=environment, opener=opener), command, thing_name)


def ask_moves_thing(command: str, thing_name: str, *, environment=None, opener=None) -> bool | None:
    environment = os.environ if environment is None else environment
    opener = urllib.request.urlopen if opener is None else opener
    return jev_questions.moves_thing(_ask(environment=environment, opener=opener), command, thing_name)


def ask_needs_to_stand(command: str, seat_name: str, within_reach, *, environment=None, opener=None) -> bool | None:
    environment = os.environ if environment is None else environment
    opener = urllib.request.urlopen if opener is None else opener
    return jev_questions.needs_to_stand(_ask(environment=environment, opener=opener), command, seat_name, within_reach)


def ask_same_or_part(
    command: str,
    story: str,
    question: str,
    statement: str,
    player,
    known,
    *,
    environment=None,
    opener=None,
) -> bool | None:
    environment = os.environ if environment is None else environment
    opener = urllib.request.urlopen if opener is None else opener
    return jev_questions.same_or_part(
        _ask(environment=environment, opener=opener), command, story, question, statement, player, known
    )
