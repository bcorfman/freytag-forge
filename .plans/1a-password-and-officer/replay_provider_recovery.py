# ruff: noqa: E501
"""Network-free (use --no-repair to switch the fused-segment repair off): feed each recorded greeting reply to the REAL narration provider path (salvage, recovery request) and report what a live turn would do.
For every recorded row the first transport answer is the recorded reply; any further request (the provider's recovery request) is answered with a clean
two-segment narration and counted. Run: TMPDIR=/tmp PYTHONPATH=.:packages/worldkeeper/src .venv/bin/python .plans/1a-password-and-officer/replay_provider_recovery.py"""

import collections
import json
import sys
from pathlib import Path

import storygame.runtime.cloudflare as cf
from storygame.runtime.contracts import RuntimeContractError, parse_turn_proposal
from storygame.runtime.item_facts import ItemFactsProvider
from storygame.runtime.state import RuntimeState
from storygame.story_package.loader import load_story_package

RESULTS = Path("bench/results/1a-password-officer")
CLEAN = json.dumps({"segments": [{"kind": "narration", "text": "CLEAN SECOND ANSWER."}], "selected_knowledge_ids": []})


class _Response:
    def __init__(self, body):
        self.body = json.dumps(body).encode()

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def outcome(raw):
    package = load_story_package(Path("data/stories/continuity-initiative"))
    state = RuntimeState.bootstrap(package)
    calls = []

    def urlopen(request, timeout):
        calls.append(json.loads(request.data))
        text = raw if len(calls) == 1 else CLEAN
        return _Response({"narration": text})

    cf.urlopen = urlopen
    # The production provider for these single-call replies: it allows the item_facts key the recorded replies carry.
    provider = ItemFactsProvider(
        worker_url="https://worker.example/turn", token="", state=state, item_facts={}, mode="single_call"
    )
    if "--no-repair" in sys.argv:
        provider._repair_fused_segments = lambda response: None
    try:
        reply = provider("Greet the officer.")
        proposal = parse_turn_proposal(reply)
        texts = [segment.text for segment in proposal.segments]
        dropped = state.last_turn_delivery.segments_dropped
        return len(calls), "accepted", dropped, texts
    except Exception as error:  # noqa: BLE001
        return len(calls), f"raised {type(error).__name__}", 0, []


summary = collections.Counter()
detail = []
for name in ("run-officer-rows.json", "run-voice-rows.json", "smoke-officer-rows.json", "smoke-voice-rows.json"):
    for row in json.loads((RESULTS / name).read_text()):
        try:
            data = json.loads(row["narration"])
            data.pop("item_facts", None)
            parse_turn_proposal(data)
            continue  # parses cleanly: nothing to recover
        except (json.JSONDecodeError, RuntimeContractError):
            pass
        requests, status, dropped, texts = outcome(row["narration"])
        recovered = any("CLEAN SECOND ANSWER." in text for text in texts)
        kind = (
            "recovery request used, clean second answer accepted"
            if recovered
            else status + (f", {dropped} segment(s) dropped" if dropped else "")
        )
        summary[(name.split("-")[0] + "-" + name.split("-")[1], row.get("arm"), row.get("n"), requests, kind)] += 1
        detail.append((name, row.get("arm"), row.get("n"), row.get("sample"), requests, kind, texts[:2]))
for key in sorted(summary, key=str):
    print(summary[key], key)
print()
for item in detail[:6]:
    print(item)
