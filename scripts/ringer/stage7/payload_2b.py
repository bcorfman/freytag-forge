"""Capture the offline 2B narration payload for the details experiment."""

from __future__ import annotations

import argparse
import difflib
import json
import os
from contextlib import ExitStack, suppress
from pathlib import Path
from unittest import mock

from bench.core import load_variation, package_and_state, provider_for
from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.engine import RuntimeEngine

ROOT = Path(__file__).resolve().parents[3]
FACTS = {"refers": ["access panel"], "same_as": {}, "kind": {}}


class _NarrationSentinel(RuntimeError):
    pass


def _text(value: object) -> str:
    return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)


def capture(variation_path: Path, command: str) -> dict[str, str]:
    variation = load_variation(variation_path)
    _, state = package_and_state(variation, "2B")
    with mock.patch.dict(os.environ, {"CLOUDFLARE_WORKER_URL": "offline://stage7-details-probe"}, clear=False):
        provider = provider_for(state, variation)
    provider.semantic_ask = None
    engine = RuntimeEngine(state, provider)

    def fake_request(self: CloudflareTurnProvider, payload: dict[str, object]) -> object:
        if payload.get("__freytag_request_budget") == "item_facts":
            return FACTS
        self.last_prompt = {"system": payload["system"], "user": payload["user"]}
        raise _NarrationSentinel

    with ExitStack() as stack:
        stack.enter_context(
            mock.patch.object(CloudflareTurnProvider, "_request_item_facts", lambda self, payload: FACTS)
        )
        stack.enter_context(mock.patch.object(CloudflareTurnProvider, "_request", fake_request))
        with suppress(_NarrationSentinel):
            engine.turn(command)
    if not provider.last_prompt:
        raise AssertionError("narration transport was not reached")
    return {key: _text(value) for key, value in provider.last_prompt.items()}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--command", default="Examine the hidden panel closely, then try to open it.")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    prompts = {
        "baseline": capture(ROOT / "bench/variations/stage7-details-control.json", args.command),
        "details": capture(ROOT / "bench/variations/stage7-door-grounded.json", args.command),
    }
    for arm, prompt in prompts.items():
        (args.out / f"{arm}.txt").write_text(
            f"SYSTEM:\n{prompt['system']}\n\nUSER:\n{prompt['user']}", encoding="utf-8"
        )
    diff = difflib.unified_diff(
        prompts["baseline"]["user"].splitlines(True),
        prompts["details"]["user"].splitlines(True),
        fromfile="baseline USER",
        tofile="details USER",
    )
    print("".join(diff), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
