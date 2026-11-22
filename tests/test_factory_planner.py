from __future__ import annotations

import json
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest

from factory.guard import CallResult, Caps, ModelGuard, ModelNotAllowed, SpendLedger
from factory.limits import LimitReport
from factory.stations import fix_plan
from factory.stations import planner as planner_module
from factory.stations.planner import PLANNER_BRIEF, build_prompt, claude_call, extract_plan, make_planner
from factory.tickets import Station, Ticket
from storygame.story_package.dependencies import producers
from storygame.story_package.loader import load_story_package

ROOT = Path(__file__).parents[1]
FIXTURE = ROOT / "tests/fixtures/factory/claude_planner_stream.jsonl"
DEFAULT_STORY = ROOT / "data/stories/continuity-initiative"
PACKAGE = load_story_package(DEFAULT_STORY)
NOW = datetime(2026, 1, 1, tzinfo=UTC)


def test_planner_brief_mentions_redundant_fact_rule() -> None:
    assert "opposite value" in PLANNER_BRIEF
    assert (
        "A beat's sets field must name at least one story fact, because a beat with no effect cannot compile."
        in PLANNER_BRIEF
    )


def test_planner_brief_asks_for_precedents_first() -> None:
    assert "precedents" in PLANNER_BRIEF
    assert "Precedent:" in PLANNER_BRIEF
    assert "Precedent: none" in PLANNER_BRIEF


def test_planner_brief_mentions_the_causes() -> None:
    assert "cause of each failing turn" in PLANNER_BRIEF
    assert "how many turns share each cause" in PLANNER_BRIEF
    assert "most common cause" in PLANNER_BRIEF
    assert (
        "A claim_wording_miss turn names a claim that misses only one wording; "
        "edit_claim_evidence fits it when the failing turn's own words supply the phrase." in PLANNER_BRIEF
    )


def test_planner_brief_contains_the_opus_fun_sentences() -> None:
    collapsed = re.sub(r"\s+", " ", PLANNER_BRIEF)
    expected = (
        "Among the fixes that would have let the failing turns succeed, choose the one the player would enjoy most.",
        "Fun means Freytag pacing, quality characters, and continuity in and between scenes.",
        "A fix is more fun when it uses a detail already in the scene to plant a clue, pay off an earlier detail, "
        "show a character, or sharpen the stakes.",
        "Never invent a new fact, object, person, or place to make a fix more fun.",
        "Choose the smaller fix only when two fixes would be equally fun.",
        "For edit_claim_evidence, the fun is letting the player's own words reach the intended moment.",
        "Never choose a phrase so broad that it lets a player skip a puzzle, a clue, or a reward.",
        "After the cause, name in a few words the detail that makes the fix fun.",
        "When a story editor's block is shown, treat its fun_advice as the owner's taste and follow it.",
        "The advice never overrides the evidence, the precedents, or the lint.",
        "Never resubmit the blocked fix with only its words moved around.",
    )
    assert all(sentence in collapsed for sentence in expected)


def _plan(ticket_id: str = "wrong", *, at_turn: int = 10, text: str | None = None) -> dict:
    fact_id = next(
        fact
        for fact in sorted(fix_plan._declared_facts(PACKAGE))
        if not producers(PACKAGE, fact, True) and not producers(PACKAGE, fact, False)
    )
    return {
        "version": 1,
        "ticket_id": ticket_id,
        "scene": "wrong-scene",
        "kind": "add_pacing_beat",
        "reason": "Precedent: fact-gated pacing beat; a small beat keeps the failing turn inside the scene.",
        "evidence_keys": ["turn-1"],
        "beat": {
            "id": "planner_retry_1a",
            "at_turn": at_turn,
            "text": text or "The patrol pauses while the player checks the truck and laptop.",
            "verbatim": True,
            "trailing": True,
            "when": {},
            "sets": {fact_id: True},
        },
    }


def _ticket(token_budget: int = 1000) -> Ticket:
    return Ticket(
        id="planner-ticket",
        scene="1A",
        station=Station.WIRING,
        token_budget=token_budget,
        created_at=NOW.isoformat(),
        updated_at=NOW.isoformat(),
        payload={"failing_turns": [{"key": "turn-1", "scene": "1A", "narration": "A short miss."}]},
    )


def _guard_and_caps(tmp_path: Path):
    guard = ModelGuard.from_file(ROOT / "factory/config/allowlist.json")
    config = json.loads((ROOT / "factory/config/factory.json").read_text(encoding="utf-8"))
    return guard, Caps.from_dict(config["caps"]), SpendLedger(tmp_path / "ledger.jsonl")


def _fake_claude(monkeypatch, outputs: list[CallResult], prompts: list[str]):
    def fake(prompt: str, **_kwargs) -> CallResult:
        prompts.append(prompt)
        return outputs.pop(0)

    monkeypatch.setattr(planner_module, "claude_call", fake)


def test_build_prompt_is_brief_evidence_then_verbatim_retry_context() -> None:
    evidence = {"scene": "1A", "fix_menu": [{"kind": "set_text"}]}
    previous = {"kind": "set_text", "reason": "Precedent: old"}
    problems = ["plan.text text is too short", "plan.evidence evidence is missing"]

    prompt = build_prompt(evidence, problems, previous)

    assert prompt.startswith(PLANNER_BRIEF)
    assert prompt.index('{"scene":"1A"') > prompt.index(PLANNER_BRIEF)
    assert prompt.index("Previous plan:") < prompt.index("Lint problems:")
    assert "plan.text text is too short\nplan.evidence evidence is missing" in prompt
    assert '"why"' not in prompt


def test_build_prompt_adds_check_output_after_previous_plan() -> None:
    evidence = {"scene": "1A", "fix_menu": [{"kind": "set_text"}]}
    previous = {"kind": "set_text", "reason": "Precedent: old"}
    check_output = "CHECK FAILED: compiled claim text differs from plan.json\n"

    prompt = build_prompt(evidence, previous_plan=previous, check_output=check_output)

    assert "Check output (this plan was applied and the check failed):" in prompt
    assert check_output in prompt
    assert prompt.index("Previous plan:") < prompt.index("Check output (this plan was applied and the check failed):")
    without_check = build_prompt(evidence, previous_plan=previous)
    assert "Check output (this plan was applied and the check failed):" not in without_check
    assert build_prompt(evidence, previous_plan=previous, check_output=None) == without_check


def test_build_prompt_default_check_section_is_byte_stable_and_accepts_probe_label() -> None:
    evidence = {"scene": "1A"}
    check_output = "verdict reject control 1 2 0 0 0 0 candidate 2 2 0 0 0 0"
    old_label = "Check output (this plan was applied and the check failed):"

    prompt = build_prompt(evidence, check_output=check_output)
    assert f"{old_label}\n{check_output}" in prompt

    probe_label = "Check output (this plan was applied and tried in play; the replay verdict follows):"
    probe_prompt = build_prompt(evidence, check_output=check_output, check_label=probe_label)
    assert f"{probe_label}\n{check_output}" in probe_prompt
    assert old_label not in probe_prompt


def test_planner_prompt_includes_the_precedents_text(tmp_path: Path, monkeypatch) -> None:
    precedents_path = tmp_path / "precedents.md"
    precedents_path.write_text("TEMP PRECEDENT MARKER", encoding="utf-8")
    ticket = _ticket()
    ticket.payload["precedents_path"] = str(precedents_path)
    guard, caps, ledger = _guard_and_caps(tmp_path)
    prompts: list[str] = []
    _fake_claude(monkeypatch, [CallResult(json.dumps(_plan()), 1)], prompts)

    outcome = make_planner(guard=guard, ledger=ledger, caps=caps)(ticket, load_story_package(DEFAULT_STORY), NOW)

    assert outcome.plan is not None
    assert "TEMP PRECEDENT MARKER" in prompts[0]


def test_planner_prompt_includes_diagnosis_from_payload(tmp_path: Path, monkeypatch) -> None:
    ticket = _ticket()
    ticket.payload["diagnosis"] = {
        "counts": {"claim_not_offered": 1},
        "rows": [{"key": "turn-1", "cause": "claim_not_offered", "why": "The claim was not offered."}],
    }
    guard, caps, ledger = _guard_and_caps(tmp_path)
    prompts: list[str] = []
    _fake_claude(monkeypatch, [CallResult(json.dumps(_plan()), 1)], prompts)

    make_planner(guard=guard, ledger=ledger, caps=caps)(ticket, load_story_package(DEFAULT_STORY), NOW)

    assert '"diagnosis":{"counts":{"claim_not_offered":1},"rows":[{"key":"turn-1"' in prompts[0]


@pytest.mark.parametrize(
    "text, expected",
    [
        ('{"kind":"set_text"}', {"kind": "set_text"}),
        ('```json\n{"kind":"set_text"}\n```', {"kind": "set_text"}),
        ('Here is the plan: {"kind":"set_text"}.', {"kind": "set_text"}),
        ('{"first":1}{"second":2}', {"first": 1}),
        ('{"text":"a brace } and { in a string"}', {"text": "a brace } and { in a string"}),
        ("not json", None),
    ],
)
def test_extract_plan(text: str, expected: dict | None) -> None:
    assert extract_plan(text) == expected


def test_claude_call_parses_fixture_and_uses_tool_free_argv() -> None:
    fixture = FIXTURE.read_text(encoding="utf-8")
    calls = []

    def run(argv, **kwargs):
        calls.append((argv, kwargs))
        return subprocess.CompletedProcess(argv, 0, fixture, "")

    result = claude_call("evidence prompt", model_id="claude-sonnet-5-5", effort="high", run=run)

    assert "planner_pause_1a" in result.output
    assert '"kind":"add_pacing_beat"' in result.output
    assert result.tokens == 46
    assert result.usd == pytest.approx(0.0042)
    assert isinstance(result.limits, LimitReport)
    assert [window.name for window in result.limits.windows] == ["five_hour", "seven_day"]
    assert calls == [
        (
            [
                "claude",
                "-p",
                "--model",
                "claude-sonnet-5-5",
                "--effort",
                "high",
                "--output-format",
                "stream-json",
                "--verbose",
                "--tools",
                "",
                "--disable-slash-commands",
                "--no-session-persistence",
            ],
            {
                "input": "evidence prompt",
                "text": True,
                "capture_output": True,
                "timeout": 900,
            },
        )
    ]


@pytest.mark.parametrize(
    "stdout, returncode, error",
    [
        ("429 too many requests", 1, "rate"),
        ("provider overloaded", 1, "overloaded"),
        (
            '{"type":"rate_limit_event","rate_limit_info":{"unifiedWindows":{"five_hour":{"utilization":1,"status":"rejected"}}}}',
            1,
            "provider",
        ),
        ("The usage limit was reached.", 0, "provider"),
    ],
)
def test_claude_call_maps_provider_failures(stdout: str, returncode: int, error: str) -> None:
    def run(argv, **_kwargs):
        return subprocess.CompletedProcess(argv, returncode, stdout, "")

    expected = {
        "rate": planner_module.RateLimited,
        "overloaded": planner_module.Overloaded,
        "provider": planner_module.ProviderLimit,
    }[error]
    with pytest.raises(expected):
        claude_call("prompt", model_id="claude-sonnet-5-5", effort="high", run=run)


def test_claude_call_keeps_tail_for_other_failures() -> None:
    def run(argv, **_kwargs):
        return subprocess.CompletedProcess(argv, 2, "first\nlast failure", "stderr")

    with pytest.raises(RuntimeError, match="last failure"):
        claude_call("prompt", model_id="claude-sonnet-5-5", effort="high", run=run)


def test_make_planner_accepts_clean_first_reply_and_records_subscription_row(tmp_path: Path, monkeypatch) -> None:
    guard, caps, ledger = _guard_and_caps(tmp_path)
    prompts: list[str] = []
    _fake_claude(monkeypatch, [CallResult(json.dumps(_plan()), 46, 0.0042)], prompts)
    planner = make_planner(guard=guard, ledger=ledger, caps=caps)
    package = load_story_package(DEFAULT_STORY)

    outcome = planner(_ticket(), package, NOW)

    assert outcome.plan is not None
    assert outcome.plan["ticket_id"] == "planner-ticket"
    assert outcome.plan["scene"] == "1A"
    assert outcome.attempts == 1 and outcome.tokens == 46
    assert len(ledger._read()) == 1
    usage = ledger._read()[0]
    assert usage.cost_kind == "subscription"
    assert usage.list_usd == pytest.approx(0.0042)


def test_make_planner_retries_garbage_and_then_accepts(tmp_path: Path, monkeypatch) -> None:
    guard, caps, ledger = _guard_and_caps(tmp_path)
    prompts: list[str] = []
    _fake_claude(monkeypatch, [CallResult("garbage", 4), CallResult(json.dumps(_plan()), 5, 0.01)], prompts)

    outcome = make_planner(guard=guard, ledger=ledger, caps=caps)(_ticket(), load_story_package(DEFAULT_STORY), NOW)

    assert outcome.plan is not None and outcome.attempts == 2 and outcome.tokens == 9
    assert len(ledger._read()) == 2
    assert "plan.shape no JSON object in the reply" in prompts[1]


def test_make_planner_retries_lint_failure_with_verdict(tmp_path: Path, monkeypatch) -> None:
    guard, caps, ledger = _guard_and_caps(tmp_path)
    prompts: list[str] = []
    bad = _plan(text="too short")
    _fake_claude(monkeypatch, [CallResult(json.dumps(bad), 3), CallResult(json.dumps(_plan()), 4)], prompts)

    outcome = make_planner(guard=guard, ledger=ledger, caps=caps)(_ticket(), load_story_package(DEFAULT_STORY), NOW)

    assert outcome.plan is not None and outcome.attempts == 2
    assert "plan.text beat text violates the bounded authored-text rules" in prompts[1]


def test_make_planner_puts_check_feedback_in_first_prompt(tmp_path: Path, monkeypatch) -> None:
    guard, caps, ledger = _guard_and_caps(tmp_path)
    prompts: list[str] = []
    feedback_plan = _plan()
    check_output = "CHECK FAILED: the compiled package differs from plan.json"
    _fake_claude(monkeypatch, [CallResult(json.dumps(_plan()), 4)], prompts)

    outcome = make_planner(guard=guard, ledger=ledger, caps=caps)(
        _ticket(),
        load_story_package(DEFAULT_STORY),
        NOW,
        feedback_plan=feedback_plan,
        check_output=check_output,
    )

    assert outcome.plan is not None
    assert prompts[0].index("Previous plan:") < prompts[0].index(
        "Check output (this plan was applied and the check failed):"
    )
    assert (
        '"reason":"Precedent: fact-gated pacing beat; a small beat keeps the failing turn inside the scene."'
        in prompts[0]
    )
    assert check_output in prompts[0]


def test_make_planner_returns_last_problems_after_three_bad_replies(tmp_path: Path, monkeypatch) -> None:
    guard, caps, ledger = _guard_and_caps(tmp_path)
    prompts: list[str] = []
    _fake_claude(monkeypatch, [CallResult("no", 1), CallResult("still no", 2), CallResult("last no", 3)], prompts)

    outcome = make_planner(guard=guard, ledger=ledger, caps=caps)(_ticket(), load_story_package(DEFAULT_STORY), NOW)

    assert outcome.plan is None
    assert outcome.problems == ["plan.shape no JSON object in the reply"]
    assert outcome.attempts == 3 and outcome.tokens == 6


def test_make_planner_stops_after_token_budget(tmp_path: Path, monkeypatch) -> None:
    guard, caps, ledger = _guard_and_caps(tmp_path)
    prompts: list[str] = []
    _fake_claude(monkeypatch, [CallResult("garbage", 10), CallResult(json.dumps(_plan()), 10)], prompts)

    outcome = make_planner(guard=guard, ledger=ledger, caps=caps)(_ticket(10), load_story_package(DEFAULT_STORY), NOW)

    assert outcome.plan is None and outcome.attempts == 1 and outcome.tokens == 10
    assert len(prompts) == 1


def test_make_planner_rejects_unpinned_model_before_call(tmp_path: Path, monkeypatch) -> None:
    guard, caps, ledger = _guard_and_caps(tmp_path)
    called = False

    def fake(*_args, **_kwargs):
        nonlocal called
        called = True
        return CallResult("unused", 1)

    monkeypatch.setattr(planner_module, "claude_call", fake)
    planner = make_planner(guard=guard, ledger=ledger, caps=caps, model_id="not-pinned")

    with pytest.raises(ModelNotAllowed):
        planner(_ticket(), load_story_package(DEFAULT_STORY), NOW)
    assert not called
