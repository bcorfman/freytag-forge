"""Bench-only Jev question for deciding whether a command uses a thing."""

from __future__ import annotations

import json
import os
import urllib.request


def ask_uses_thing(command: str, thing_name: str, *, environment=None, opener=None) -> bool | None:
    environment = os.environ if environment is None else environment
    opener = urllib.request.urlopen if opener is None else opener
    account = environment.get("CLOUDFLARE_ACCOUNT_ID")
    token = environment.get("CLOUDFLARE_AI_TOKEN")
    if not account or not token:
        return None
    body = {
        "model": "typesafe/jev",
        "input": {
            "state": {"command": command, "thing": thing_name},
            "questions": {
                "uses_thing": {
                    "type": "noul",
                    "instructions": (
                        "In the player's command, does carrying it out mean using thing "
                        "(reading, typing on, or looking at something on it)? Moving it, "
                        "carrying it, picking it up or putting it down is not using it."
                    ),
                    "criteria": {
                        "true": "The command means reading, typing on, or looking at something on the thing.",
                        "false": "The command only moves, carries, picks up, or puts down the thing.",
                    },
                }
            },
        },
    }
    try:
        request = urllib.request.Request(
            f"https://api.cloudflare.com/client/v4/accounts/{account}/ai/run",
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
            method="POST",
        )
        with opener(request, timeout=30) as response:
            payload = json.loads(response.read())
        answer = payload.get("result", {}).get("result", {}).get("answers", {}).get("uses_thing")
        if (
            payload.get("success") is True
            and payload.get("result", {}).get("state") == "Completed"
            and isinstance(answer, bool)
        ):
            return answer
    except Exception:
        return None
    return None
