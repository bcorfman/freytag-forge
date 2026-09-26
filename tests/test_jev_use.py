from __future__ import annotations

import io
import json

from bench.jev_use import ask_uses_thing


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
