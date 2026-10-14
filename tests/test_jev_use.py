from __future__ import annotations

import io
import json
import urllib.error

import pytest

from bench.jev_use import (
    ask_moves_thing,
    ask_needs_to_stand,
    ask_same_or_part,
    ask_uses_thing,
    jev_stats,
    reset_jev_stats,
)

ENVIRONMENT = {"CLOUDFLARE_ACCOUNT_ID": "account", "CLOUDFLARE_AI_TOKEN": "token"}


class Response(io.BytesIO):
    def __init__(self, payload, *, status=None, headers=None):
        super().__init__(json.dumps(payload).encode() if not isinstance(payload, bytes) else payload)
        self.status = status
        self.headers = headers or {}


def completed_response(value=0.9):
    return Response(
        {
            "success": True,
            "result": {
                "state": "Completed",
                "result": {"answers": {"uses_thing": {"type": "noul", "noul": value}}},
            },
        }
    )


@pytest.fixture(autouse=True)
def clean_jev_stats():
    reset_jev_stats()
    yield
    reset_jev_stats()


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
    environment = ENVIRONMENT
    assert ask_moves_thing("Put the photograph in my pocket.", "photograph", environment={}) is None
    assert jev_stats()["calls"] == 0

    def bad_opener(*_args, **_kwargs):
        raise OSError("offline")

    assert (
        ask_moves_thing("Put the photograph in my pocket.", "photograph", environment=environment, opener=bad_opener)
        is None
    )
    assert jev_stats()["failures"] == {"request": 1}


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
    environment = ENVIRONMENT

    assert ask_uses_thing("Read the files on my laptop.", "Kristin's laptop", environment={}) is None

    def bad_opener(*_args, **_kwargs):
        raise OSError("offline")

    assert (
        ask_uses_thing("Read the files on my laptop.", "Kristin's laptop", environment=environment, opener=bad_opener)
        is None
    )
    assert jev_stats()["failures"] == {"request": 1}
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


def ask(opener, environment=None):
    return ask_uses_thing(
        "Read the files on the laptop.",
        "the laptop",
        environment=ENVIRONMENT if environment is None else environment,
        opener=opener,
    )


def test_call_cap_does_not_invoke_opener_after_cap():
    calls = []

    def opener(*args, **kwargs):
        calls.append((args, kwargs))
        return completed_response()

    environment = {**ENVIRONMENT, "FREYTAG_BENCH_JEV_MAX_CALLS": "1"}
    assert ask(opener, environment) is True
    assert ask(opener, environment) is None

    assert len(calls) == 1
    assert jev_stats() == {"calls": 1, "ok": 1, "failures": {}, "stopped": None, "cap_reached": True}


def test_http_429_stops_later_calls():
    calls = []

    def opener(*args, **kwargs):
        calls.append((args, kwargs))
        return Response({"error": "rate limited"}, status=429)

    assert ask(opener) is None
    assert ask(opener) is None

    stats = jev_stats()
    assert len(calls) == 1
    assert stats["calls"] == 1
    assert stats["failures"] == {"http_status": 1}
    assert stats["stopped"] == "http_429"


def test_quota_error_in_body_stops_later_calls():
    calls = []

    def opener(*args, **kwargs):
        calls.append((args, kwargs))
        return Response({"success": False, "error": "AI_QUOTA_EXCEEDED"})

    assert ask(opener) is None
    assert ask(opener) is None

    stats = jev_stats()
    assert len(calls) == 1
    assert stats["failures"] == {"spend_limit": 1}
    assert stats["stopped"] == "AI_QUOTA_EXCEEDED"


def test_consecutive_failures_stop_requests():
    calls = []

    def opener(*args, **kwargs):
        calls.append((args, kwargs))
        raise OSError("offline")

    environment = {**ENVIRONMENT, "FREYTAG_BENCH_JEV_MAX_CONSECUTIVE_FAILURES": "2"}
    assert ask(opener, environment) is None
    assert ask(opener, environment) is None
    assert ask(opener, environment) is None

    stats = jev_stats()
    assert len(calls) == 2
    assert stats["calls"] == 2
    assert stats["failures"] == {"request": 2}
    assert stats["stopped"] == "max_consecutive_failures"


def test_success_resets_consecutive_failure_counter():
    calls = []
    responses = iter([OSError("offline"), completed_response(), OSError("offline"), OSError("offline")])

    def opener(*args, **kwargs):
        calls.append((args, kwargs))
        response = next(responses)
        if isinstance(response, Exception):
            raise response
        return response

    environment = {**ENVIRONMENT, "FREYTAG_BENCH_JEV_MAX_CONSECUTIVE_FAILURES": "2"}
    assert ask(opener, environment) is None
    assert ask(opener, environment) is True
    assert ask(opener, environment) is None
    assert ask(opener, environment) is None

    stats = jev_stats()
    assert len(calls) == 4
    assert stats["ok"] == 1
    assert stats["failures"] == {"request": 3}
    assert stats["stopped"] == "max_consecutive_failures"


def test_stats_record_failure_kinds():
    responses = iter(
        [
            Response({"error": "server"}, status=500),
            TimeoutError("timed out"),
            b"not json",
            Response({"success": True, "result": {"state": "Running"}}),
            completed_response(),
        ]
    )

    def opener(*args, **kwargs):
        response = next(responses)
        if isinstance(response, Exception):
            raise response
        return response

    environment = {**ENVIRONMENT, "FREYTAG_BENCH_JEV_MAX_CONSECUTIVE_FAILURES": "10"}
    assert ask(opener, environment) is None
    assert ask(opener, environment) is None
    assert ask(opener, environment) is None
    assert ask(opener, environment) is None
    assert ask(opener, environment) is True

    stats = jev_stats()
    assert stats["calls"] == 5
    assert stats["ok"] == 1
    assert stats["failures"] == {
        "http_status": 1,
        "timeout": 1,
        "bad_payload": 1,
        "not_completed": 1,
    }


def test_http_error_429_stops_without_retry():
    calls = []

    def opener(*args, **kwargs):
        calls.append((args, kwargs))
        raise urllib.error.HTTPError(
            "https://example.test",
            429,
            "rate limited",
            {},
            io.BytesIO(b'{"error":"rate limited"}'),
        )

    assert ask(opener) is None
    assert ask(opener) is None
    assert len(calls) == 1
    assert jev_stats()["stopped"] == "http_429"


def test_missing_credentials_do_not_count_as_calls():
    calls = []

    def opener(*args, **kwargs):
        calls.append((args, kwargs))
        return completed_response()

    assert ask(opener, {}) is None
    assert calls == []
    assert jev_stats() == {"calls": 0, "ok": 0, "failures": {}, "stopped": None, "cap_reached": False}
