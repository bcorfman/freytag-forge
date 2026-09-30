from __future__ import annotations

import io
import json

from bench.jev_use import ask_moves_thing, ask_needs_to_stand, ask_same_or_part, ask_uses_thing


def test_jev_moves_thing_request_and_answers():
    calls = []

    def opener(request, timeout):
        calls.append((request, timeout))
        return io.BytesIO(
            json.dumps(
                {
                    "success": True,
                    "result": {
                        "state": "Completed",
                        "result": {"answers": {"moves_thing": {"type": "noul", "noul": 0.78}}},
                    },
                }
            ).encode()
        )

    assert (
        ask_moves_thing(
            "Put Michelle's photograph in my pocket.",
            "Michelle's photograph",
            environment={"CLOUDFLARE_ACCOUNT_ID": "account", "CLOUDFLARE_AI_TOKEN": "token"},
            opener=opener,
        )
        is True
    )
    body = json.loads(calls[0][0].data)
    assert "moves_thing" in body["input"]["questions"]


def test_jev_moves_thing_failures_give_none():
    environment = {"CLOUDFLARE_ACCOUNT_ID": "account", "CLOUDFLARE_AI_TOKEN": "token"}
    assert ask_moves_thing("Put the photograph in my pocket.", "photograph", environment={}) is None

    def bad_opener(*_args, **_kwargs):
        raise OSError("offline")

    assert (
        ask_moves_thing("Put the photograph in my pocket.", "photograph", environment=environment, opener=bad_opener)
        is None
    )


def test_jev_use_request_and_answers():
    response = {
        "success": True,
        "result": {
            "state": "Completed",
            "result": {"answers": {"uses_thing": {"type": "noul", "noul": 0.78}}},
        },
    }
    calls = []

    def opener(request, timeout):
        calls.append((request, timeout))
        return io.BytesIO(json.dumps(response).encode())

    answer = ask_uses_thing(
        "Read the files on my laptop.",
        "Kristin's laptop",
        environment={"CLOUDFLARE_ACCOUNT_ID": "account", "CLOUDFLARE_AI_TOKEN": "token"},
        opener=opener,
    )

    assert answer is True
    request, timeout = calls[0]
    assert request.full_url == "https://api.cloudflare.com/client/v4/accounts/account/ai/run"
    assert request.method == "POST"
    assert request.get_header("Content-type") == "application/json"
    assert request.get_header("Authorization") == "Bearer token"
    body = json.loads(request.data)
    assert body["model"] == "typesafe/jev"
    assert body["input"]["state"] == {
        "command": "Read the files on my laptop.",
        "thing": "Kristin's laptop",
    }
    assert "Kristin's laptop" not in body["input"]["questions"]["uses_thing"]["instructions"]
    assert timeout == 30


def test_jev_use_failures_give_none():
    environment = {"CLOUDFLARE_ACCOUNT_ID": "account", "CLOUDFLARE_AI_TOKEN": "token"}

    assert ask_uses_thing("Read the files on my laptop.", "Kristin's laptop", environment={}) is None

    def bad_opener(*_args, **_kwargs):
        raise OSError("offline")

    assert (
        ask_uses_thing("Read the files on my laptop.", "Kristin's laptop", environment=environment, opener=bad_opener)
        is None
    )
    for payload in (
        {"success": False},
        {"success": True, "result": {"state": "Running"}},
        {
            "success": True,
            "result": {
                "state": "Completed",
                "result": {"answers": {"uses_thing": {"type": "noul", "noul": "yes"}}},
            },
        },
    ):

        def opener(*_args, payload=payload, **_kwargs):
            return io.BytesIO(json.dumps(payload).encode())

        assert (
            ask_uses_thing(
                "Read the files on my laptop.",
                "Kristin's laptop",
                environment=environment,
                opener=opener,
            )
            is None
        )

    for noul in (0.5, 0.2):

        def opener(*_args, noul=noul, **_kwargs):
            return io.BytesIO(
                json.dumps(
                    {
                        "success": True,
                        "result": {
                            "state": "Completed",
                            "result": {"answers": {"uses_thing": {"type": "noul", "noul": noul}}},
                        },
                    }
                ).encode()
            )

        assert (
            ask_uses_thing(
                "Carry the laptop to the truck.",
                "Kristin's laptop",
                environment=environment,
                opener=opener,
            )
            is False
        )


def test_jev_stand_request_and_answers():
    environment = {"CLOUDFLARE_ACCOUNT_ID": "account", "CLOUDFLARE_AI_TOKEN": "token"}
    calls = []

    def opener(request, timeout):
        calls.append((request, timeout))
        return io.BytesIO(
            json.dumps(
                {
                    "success": True,
                    "result": {
                        "state": "Completed",
                        "result": {"answers": {"needs_to_stand": {"type": "noul", "noul": 0.8}}},
                    },
                }
            ).encode()
        )

    assert (
        ask_needs_to_stand(
            "Go out to the truck.",
            "workstation chair",
            ("workstation chair", "workstation", "Kristin's laptop"),
            environment=environment,
            opener=opener,
        )
        is True
    )
    request, timeout = calls[0]
    body = json.loads(request.data)
    assert body["input"]["state"] == {
        "command": "Go out to the truck.",
        "seat": "workstation chair",
        "within_reach": ["workstation chair", "workstation", "Kristin's laptop"],
    }
    assert timeout == 30

    def below_threshold(*_args, **_kwargs):
        return io.BytesIO(
            json.dumps(
                {
                    "success": True,
                    "result": {
                        "state": "Completed",
                        "result": {"answers": {"needs_to_stand": {"type": "noul", "noul": 0.2}}},
                    },
                }
            ).encode()
        )

    assert (
        ask_needs_to_stand(
            "Read the files on my laptop.",
            "workstation chair",
            (),
            environment=environment,
            opener=below_threshold,
        )
        is False
    )
    assert ask_needs_to_stand("Go out to the truck.", "workstation chair", (), environment={}) is None


def test_same_or_part_request_and_answers():
    environment = {"CLOUDFLARE_ACCOUNT_ID": "account", "CLOUDFLARE_AI_TOKEN": "token"}
    calls = []

    def opener(request, timeout):
        calls.append((request, timeout))
        return io.BytesIO(
            json.dumps(
                {
                    "success": True,
                    "result": {
                        "state": "Completed",
                        "result": {"answers": {"same_or_part": {"type": "noul", "noul": 0.8}}},
                    },
                }
            ).encode()
        )

    assert (
        ask_same_or_part(
            "Search the guard's desk.",
            "The guard points to the desk.",
            "Are the desk and the console the same thing?",
            "the desk and the console are the same thing",
            {"name": "Kristin", "place": "office", "held_by": None},
            {"name": "console", "place": "office", "held_by": None, "can_move": True},
            environment=environment,
            opener=opener,
        )
        is True
    )
    request, timeout = calls[0]
    body = json.loads(request.data)
    assert body["input"]["state"] == {
        "command": "Search the guard's desk.",
        "story": "The guard points to the desk.",
        "player": {"name": "Kristin", "place": "office", "held_by": None},
        "known": {"name": "console", "place": "office", "held_by": None, "can_move": True},
    }
    question = body["input"]["questions"]["same_or_part"]
    assert question["type"] == "noul"
    assert question["instructions"] == (
        "Are the desk and the console the same thing? Use story, player and known to decide what is most likely."
    )
    assert question["criteria"] == {
        "true": "Most likely, the desk and the console are the same thing.",
        "false": "Most likely, this is not so: the desk and the console are the same thing.",
    }
    assert timeout == 30

    def below_threshold(*_args, **_kwargs):
        return io.BytesIO(
            json.dumps(
                {
                    "success": True,
                    "result": {
                        "state": "Completed",
                        "result": {"answers": {"same_or_part": {"type": "noul", "noul": 0.2}}},
                    },
                }
            ).encode()
        )

    assert (
        ask_same_or_part(
            "Search the desk.",
            "",
            "Are they the same?",
            "they are the same",
            {"name": "Kristin", "place": None, "held_by": None},
            {"name": "desk", "place": None, "held_by": None, "can_move": True},
            environment=environment,
            opener=below_threshold,
        )
        is False
    )
    assert (
        ask_same_or_part(
            "Search the desk.",
            "",
            "Are they the same?",
            "they are the same",
            {},
            {},
            environment={},
        )
        is None
    )

    def bad_opener(*_args, **_kwargs):
        raise OSError("offline")

    assert (
        ask_same_or_part(
            "Search the desk.",
            "",
            "Are they the same?",
            "they are the same",
            {},
            {},
            environment=environment,
            opener=bad_opener,
        )
        is None
    )
