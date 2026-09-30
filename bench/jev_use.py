"""Bench-only Jev question for deciding whether a command uses a thing."""

from __future__ import annotations

import json
import os
import urllib.request

THRESHOLD = 0.5  # Matches the threshold in bench/jev-judge.mjs.


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
                        "Using a thing means working on it: reading it, typing on it, "
                        "searching its files, or working with what is on its screen. "
                        "Opening, closing, turning it on or off, moving, carrying, "
                        "picking it up, and putting it down are not using it."
                    ),
                    "criteria": {
                        "true": "The command means working on the thing or working with what is on its screen.",
                        "false": (
                            "The command only opens, closes, turns the thing on or off, moves, carries, "
                            "picks up, or puts down the thing."
                        ),
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
        if payload.get("success") is True and payload.get("result", {}).get("state") == "Completed":
            noul = answer.get("noul") if isinstance(answer, dict) else None
            if isinstance(noul, (int, float)) and not isinstance(noul, bool):
                return noul > THRESHOLD
    except Exception:
        return None
    return None


def ask_moves_thing(command: str, thing_name: str, *, environment=None, opener=None) -> bool | None:
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
                "moves_thing": {
                    "type": "noul",
                    "instructions": (
                        "Moving a thing means the command puts it somewhere, places it, stores it, "
                        "or hands it to someone. The player must hold it first."
                    ),
                    "criteria": {
                        "true": "The command puts, places, stores, or hands over the thing.",
                        "false": (
                            "The command already says to pick up or take the thing, or it only looks at, "
                            "reads, searches, or talks about the thing."
                        ),
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
        answer = payload.get("result", {}).get("result", {}).get("answers", {}).get("moves_thing")
        if payload.get("success") is True and payload.get("result", {}).get("state") == "Completed":
            noul = answer.get("noul") if isinstance(answer, dict) else None
            if isinstance(noul, (int, float)) and not isinstance(noul, bool):
                return noul > THRESHOLD
    except Exception:
        return None
    return None


def ask_needs_to_stand(command: str, seat_name: str, within_reach, *, environment=None, opener=None) -> bool | None:
    environment = os.environ if environment is None else environment
    opener = urllib.request.urlopen if opener is None else opener
    account = environment.get("CLOUDFLARE_ACCOUNT_ID")
    token = environment.get("CLOUDFLARE_AI_TOKEN")
    if not account or not token:
        return None
    body = {
        "model": "typesafe/jev",
        "input": {
            "state": {"command": command, "seat": seat_name, "within_reach": list(within_reach)},
            "questions": {
                "needs_to_stand": {
                    "type": "noul",
                    "instructions": (
                        "The player's character is sitting in the seat. Decide if the command needs "
                        "another place or a thing outside within_reach."
                    ),
                    "criteria": {
                        "true": "The command means going to another place or acting on a thing outside within_reach.",
                        "false": (
                            "The command only acts on things in within_reach, or only talks, looks, "
                            "or listens from the seat."
                        ),
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
        answer = payload.get("result", {}).get("result", {}).get("answers", {}).get("needs_to_stand")
        if payload.get("success") is True and payload.get("result", {}).get("state") == "Completed":
            noul = answer.get("noul") if isinstance(answer, dict) else None
            if isinstance(noul, (int, float)) and not isinstance(noul, bool):
                return noul > THRESHOLD
    except Exception:
        return None
    return None


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
    account = environment.get("CLOUDFLARE_ACCOUNT_ID")
    token = environment.get("CLOUDFLARE_AI_TOKEN")
    if not account or not token:
        return None
    body = {
        "model": "typesafe/jev",
        "input": {
            "state": {"command": command, "story": story, "player": player, "known": known},
            "questions": {
                "same_or_part": {
                    "type": "noul",
                    "instructions": f"{question} Use story, player and known to decide what is most likely.",
                    "criteria": {
                        "true": f"Most likely, {statement}.",
                        "false": f"Most likely, this is not so: {statement}.",
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
        answer = payload.get("result", {}).get("result", {}).get("answers", {}).get("same_or_part")
        if payload.get("success") is True and payload.get("result", {}).get("state") == "Completed":
            noul = answer.get("noul") if isinstance(answer, dict) else None
            if isinstance(noul, (int, float)) and not isinstance(noul, bool):
                return noul > THRESHOLD
    except Exception:
        return None
    return None
