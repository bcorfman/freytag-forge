"""Runtime Jev question builders share the bench payloads and fail closed."""

from __future__ import annotations

import json

from bench.jev_use import ask_moves_thing, ask_needs_to_stand, ask_same_or_part, ask_uses_thing
from storygame.runtime.jev import JevClient
from storygame.runtime.jev_questions import moves_thing, needs_to_stand, same_or_part, uses_thing


class _Response:
    def __init__(self, body: object) -> None:
        self.body = body if isinstance(body, bytes) else json.dumps(body).encode()

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return self.body


def test_runtime_questions_post_same_input_through_jev_client() -> None:
    environment = {"CLOUDFLARE_ACCOUNT_ID": "account", "CLOUDFLARE_AI_TOKEN": "token"}
    calls = [
        (
            ask_uses_thing,
            uses_thing,
            ("Read the files on my laptop.", "Kristin's laptop"),
            "uses_thing",
        ),
        (
            ask_moves_thing,
            moves_thing,
            ("Put Michelle's photograph in my pocket.", "Michelle's photograph"),
            "moves_thing",
        ),
        (
            ask_needs_to_stand,
            needs_to_stand,
            ("Go out to the truck.", "workstation chair", ("workstation", "Kristin's laptop")),
            "needs_to_stand",
        ),
        (
            ask_same_or_part,
            same_or_part,
            (
                "Search the guard's desk.",
                "The guard points to the desk.",
                "Are the desk and the console the same thing?",
                "the desk and the console are the same thing",
                {"name": "Kristin"},
                {"name": "console"},
            ),
            "same_or_part",
        ),
    ]

    for bench_function, runtime_function, arguments, key in calls:
        bench_body = {}

        def bench_opener(request, timeout, *, body=bench_body, answer_key=key):
            body["body"] = json.loads(request.data)
            return _Response(
                {
                    "success": True,
                    "result": {"state": "Completed", "result": {"answers": {answer_key: {"noul": 0.8}}}},
                }
            )

        assert bench_function(*arguments, environment=environment, opener=bench_opener) is True

        runtime_body = {}

        def runtime_opener(request, timeout, *, body=runtime_body, answer_key=key):
            body["body"] = json.loads(request.data)
            return _Response({"answers": {answer_key: {"type": "noul", "noul": 0.8}}})

        client = JevClient("https://worker.example", "token", opener=runtime_opener)
        assert runtime_function(client.ask, *arguments) is True
        assert runtime_body["body"]["input"] == bench_body["body"]["input"]


def test_runtime_questions_fail_closed() -> None:
    functions = (
        (uses_thing, ("Read the files on my laptop.", "Kristin's laptop"), "uses_thing"),
        (moves_thing, ("Put the photograph in my pocket.", "photograph"), "moves_thing"),
        (needs_to_stand, ("Go out to the truck.", "chair", ()), "needs_to_stand"),
        (same_or_part, ("Search the desk.", "", "Are they the same?", "they are the same", {}, {}), "same_or_part"),
    )
    for function, arguments, key in functions:
        assert function(lambda *_args: None, *arguments) is None
        assert function(lambda *_args: (_ for _ in ()).throw(RuntimeError("offline")), *arguments) is None
        assert function(lambda *_args: {}, *arguments) is None
        assert function(lambda *_args, answer_key=key: {answer_key: {"noul": "yes"}}, *arguments) is None
