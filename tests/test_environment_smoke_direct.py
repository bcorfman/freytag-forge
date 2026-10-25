from __future__ import annotations

import json
import socket
from pathlib import Path
from urllib.error import HTTPError

import pytest

from scripts.ringer.environment_narration import smoke_direct

VARIANT_LABELS = [
    "llama-3.1-8b",
    "gemma-4-26b-a4b",
    "qwen3-30b-a3b",
    "gpt-oss-20b",
]
TOKEN = "dummy-secret-token"
QUOTE_REPAIR_FIXTURES = [
    (
        """{"segments":[{"kind":"narration","text":"Kristin looks around the truck, her eyes falling on her laptop"""
        """ on the passenger seat."},"""
        """{"kind":"narration","text":"She says to herself, "I need to find some clues"""
        """ about Shelly's disappearance.""},"""
        """{"kind":"narration","text":"She reaches for her laptop, saying, "Maybe I can find something on here.""}],"""
        """"selected_knowledge_ids":[],"item_facts":{"Kristin":{"place":"driver's seat"},"""
        """"Kristin's laptop":{"place":"passenger seat"}}}"""
    ),
    (
        """{"segments":[{"kind":"narration","text":"Kristin looks around the truck, taking in her surroundings."},"""
        """{"kind":"narration","text":"Her eyes land on her laptop, which is sitting on the passenger seat."},"""
        '''{"kind":"narration","text":"She says to herself, "I should check if I have any messages from Shelly,"'''
        """ and reaches for the laptop."}],"""
        """"selected_knowledge_ids":[],"item_facts":{"Kristin":{"place":"driver's seat"},"""
        """"Kristin's laptop":{"place":"passenger seat"}}}"""
    ),
    (
        """{"segments":[{"kind":"narration","text":"Kristin looks around the truck, taking in her surroundings."},"""
        """{"kind":"narration","text":"Her eyes land on her laptop, which is sitting on the passenger seat."},"""
        """{"kind":"narration","text":"She says to herself, "I should check if I have any messages from Shelly.""}],"""
        """"selected_knowledge_ids":[],"item_facts":{"Kristin":{"place":"driver's seat"},"""
        """"Kristin's laptop":{"place":"passenger seat"}}}"""
    ),
]
NEW_VARIANT_LABELS = [
    "llama-3.3-70b-nojson",
    "qwen3-think-off-kwargs",
    "qwen3-think-off-soft",
]
PROBE_VARIANT = "llama-3.3-70b-default-temp"
WIDE_SLOTS = [
    ("S1", "proposed", 0),
    ("S1", "proposed", 1),
    ("S1", "proposed", 2),
    ("S1", "existing", 0),
    ("S2", "proposed", 0),
    ("S2", "proposed", 1),
    ("S2", "proposed", 2),
    ("S2", "existing", 0),
    ("S3", "proposed", 0),
    ("S3", "proposed", 1),
    ("S4", "proposed", 0),
    ("S4", "proposed", 1),
    ("S5b", "proposed", 0),
    ("S5b", "proposed", 1),
    ("S5b", "proposed", 2),
    ("S5b", "existing", 0),
    ("S5b", "existing", 1),
    ("S6", "proposed", 0),
    ("S6", "proposed", 1),
    ("S6", "proposed", 2),
]


@pytest.fixture(autouse=True)
def hermetic_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_socket(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("network access is forbidden in smoke direct tests")

    monkeypatch.setattr(socket, "socket", fail_socket)
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "dummy-account")
    monkeypatch.setenv("CLOUDFLARE_AI_TOKEN", TOKEN)
    monkeypatch.delenv("CF_API_TOKEN", raising=False)


def _prompt_document(path: Path) -> Path:
    starts = []
    for number in range(1, 7):
        contexts = {
            name: {
                "system": "system prompt",
                "user": (
                    f"user S{number} {name}\n"
                    "- The drawer holds nothing else the player can find.\n"
                    "- What presses on the drawer is a hidden latch.\n"
                    "- The narrator may say this aloud.\n"
                    if number == 5
                    else f"user S{number} {name}"
                ),
            }
            for name in ("existing", "proposed")
        }
        starts.append({"id": f"S{number}", "contexts": contexts})
    path.write_text(json.dumps({"starts": starts}), encoding="utf-8")
    return path


def test_wide_plan_is_20_calls_and_two_variants_interleave(tmp_path: Path) -> None:
    prompts = _prompt_document(tmp_path / "prompts.json")
    out = tmp_path / "plan.json"

    assert (
        smoke_direct.main(
            [
                "--dry",
                "--prompts",
                str(prompts),
                "--out",
                str(out),
                "--slots",
                "wide",
                "--variants",
                "llama-3.3-70b-nojson",
            ]
        )
        == 0
    )
    plan = _read_json(out)
    assert len(plan["calls"]) == 20
    assert [(call["start"], call["context"], call["sample"]) for call in plan["calls"]] == WIDE_SLOTS
    assert plan["ceiling_usd"] == pytest.approx(sum(call["ceiling_usd"] for call in plan["calls"]))

    two_out = tmp_path / "two-plan.json"
    assert (
        smoke_direct.main(
            [
                "--dry",
                "--prompts",
                str(prompts),
                "--out",
                str(two_out),
                "--slots",
                "wide",
                "--variants",
                "llama-3.3-70b-nojson,llama-3.3-70b-schema",
            ]
        )
        == 0
    )
    two_plan = _read_json(two_out)
    assert len(two_plan["calls"]) == 40
    assert [(call["start"], call["variant"]) for call in two_plan["calls"][:4]] == [
        ("S1", "llama-3.3-70b-nojson"),
        ("S1", "llama-3.3-70b-schema"),
        ("S1", "llama-3.3-70b-nojson"),
        ("S1", "llama-3.3-70b-schema"),
    ]


def test_s5b_is_derived_without_reveal_cues(tmp_path: Path) -> None:
    path = _prompt_document(tmp_path / "prompts.json")
    document = smoke_direct._load_prompts(path)
    assert "may say this aloud" in document["S5"]["existing"]["user"]
    assert "may say this aloud" not in document["S5b"]["existing"]["user"]
    assert document["S5b"]["existing"]["user"] == (
        "user S5 existing\n- The drawer holds nothing else the player can find.\n"
        "- What presses on the drawer is a hidden latch.\n"
    )
    assert document["S5b"]["proposed"]["system"] == document["S5"]["proposed"]["system"]
    assert document["S5b"]["proposed"]["user"] == (
        "user S5 proposed\n- The drawer holds nothing else the player can find.\n"
        "- What presses on the drawer is a hidden latch.\n"
    )


def test_s5b_requires_cue_in_each_context(tmp_path: Path) -> None:
    path = _prompt_document(tmp_path / "prompts.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["starts"][4]["contexts"]["existing"]["user"] = "no cue"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="S5 existing context.*may say this aloud"):
        smoke_direct._load_prompts(path)


def test_probe_prompts_apply_only_the_stated_proposed_line_edits(tmp_path: Path) -> None:
    path = _prompt_document(tmp_path / "prompts.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    proposed_user = (
        "before\n"
        "- The drawer holds nothing else the player can find.\n"
        "- What presses on the drawer is a hidden latch.\n"
        "after\n"
    )
    existing_user = "existing unchanged\n"
    payload["starts"][4]["contexts"]["proposed"]["user"] = proposed_user + "- The narrator may say this aloud.\n"
    payload["starts"][4]["contexts"]["existing"]["user"] = existing_user + "- The narrator may say this aloud.\n"
    path.write_text(json.dumps(payload), encoding="utf-8")

    prompts = smoke_direct._load_prompts(path)
    s5b = prompts["S5b"]["proposed"]["user"].splitlines()
    a = prompts["S5bA"]["proposed"]["user"].splitlines()
    b = prompts["S5bB"]["proposed"]["user"].splitlines()
    c = prompts["S5bC"]["proposed"]["user"].splitlines()
    assert prompts["S5bA"]["proposed"]["system"] == prompts["S5b"]["proposed"]["system"]
    assert prompts["S5bA"]["existing"] == prompts["S5b"]["existing"]
    assert a == [
        "before",
        "- Nothing is left in or under the drawer. Searching the drawer finds nothing.",
        "- What presses on the drawer is a hidden latch.",
        "after",
    ]
    assert b == ["before", "- The drawer holds nothing else the player can find.", "after"]
    assert c == ["before", "- Nothing is left in or under the drawer. Searching the drawer finds nothing.", "after"]
    assert [line for line in a if line not in s5b] == [
        "- Nothing is left in or under the drawer. Searching the drawer finds nothing."
    ]
    assert [line for line in s5b if line not in a] == ["- The drawer holds nothing else the player can find."]


@pytest.mark.parametrize("arm,missing", [("S5bA", "holds nothing else"), ("S5bB", "What presses on")])
def test_probe_prompt_missing_line_names_arm(tmp_path: Path, arm: str, missing: str) -> None:
    path = _prompt_document(tmp_path / "prompts.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["starts"][4]["contexts"]["proposed"]["user"] = (
        "- What presses on the drawer is a hidden latch.\n"
        "- The drawer holds nothing else the player can find.\n"
        "- The narrator may say this aloud.\n"
    )
    if arm == "S5bA":
        payload["starts"][4]["contexts"]["proposed"]["user"] = (
            "- What presses on the drawer is a hidden latch.\n- The narrator may say this aloud.\n"
        )
    else:
        payload["starts"][4]["contexts"]["proposed"]["user"] = (
            "- The drawer holds nothing else the player can find.\n- The narrator may say this aloud.\n"
        )
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match=arm):
        smoke_direct._load_prompts(path)


def test_default_temperature_profile_omits_temperature_and_defaults_are_unchanged(tmp_path: Path) -> None:
    prompts = smoke_direct._load_prompts(_prompt_document(tmp_path / "prompts.json"))
    default_plan = smoke_direct._build_plan(prompts, tuple(smoke_direct._DEFAULT_VARIANT_ORDER))
    assert len(default_plan) == 24
    wide_plan = smoke_direct._build_plan(
        prompts, (smoke_direct._DEFAULT_VARIANT_ORDER[0],), smoke_direct._WIDE_SLOT_ORDER
    )
    assert len(wide_plan) == 20
    assert smoke_direct._request_body(default_plan[0])["temperature"] == 0
    probe = smoke_direct._build_plan(prompts, (PROBE_VARIANT,), smoke_direct._SLOT_ORDERS["probe"])
    assert len(probe) == 32
    assert smoke_direct._request_body(probe[0]).get("temperature") is None
    assert "temperature" not in smoke_direct._request_body(probe[0])
    assert (
        smoke_direct._request_body(smoke_direct._build_plan(prompts, ("llama-3.3-70b-nojson",))[0])["temperature"] == 0
    )


def test_probe_plan_has_stated_order_and_single_variant(tmp_path: Path) -> None:
    prompts = smoke_direct._load_prompts(_prompt_document(tmp_path / "prompts.json"))
    plan = smoke_direct._build_plan(prompts, (PROBE_VARIANT,), smoke_direct._SLOT_ORDERS["probe"])
    assert [(call["start"], call["context"], call["sample"]) for call in plan] == [
        (arm, "proposed", sample) for sample in range(8) for arm in ("S5b", "S5bA", "S5bB", "S5bC")
    ]
    assert {call["variant"] for call in plan} == {PROBE_VARIANT}


def test_confirm_plan_has_stated_order_and_separate_report_counts(tmp_path: Path) -> None:
    prompts = smoke_direct._load_prompts(_prompt_document(tmp_path / "prompts.json"))
    plan = smoke_direct._build_plan(
        prompts,
        (PROBE_VARIANT,),
        smoke_direct._SLOT_ORDERS["confirm"],
    )
    assert len(plan) == 30
    assert [(call["start"], call["context"], call["sample"]) for call in plan] == [
        (arm, "proposed", sample) for sample in range(15) for arm in ("S5b", "S5bA")
    ]
    assert [call["variant"] for call in plan] == [PROBE_VARIANT] * 30
    assert plan[0]["start"] == "S5b"
    assert plan[1]["start"] == "S5bA"
    assert plan[0]["sample"] == plan[1]["sample"] == 0
    assert plan[-2]["sample"] == plan[-1]["sample"] == 14
    dry_out = tmp_path / "confirm-plan.json"
    assert (
        smoke_direct.main(
            [
                "--dry",
                "--prompts",
                str(tmp_path / "prompts.json"),
                "--out",
                str(dry_out),
                "--slots",
                "confirm",
                "--variants",
                PROBE_VARIANT,
            ]
        )
        == 0
    )
    dry_document = _read_json(dry_out)
    assert dry_document["ceiling_usd"] == pytest.approx(sum(call["ceiling_usd"] for call in plan))

    rows = tmp_path / "rows.json"
    report = tmp_path / "report.md"
    rows.write_text(
        json.dumps(
            {
                "ceiling_usd": sum(call["ceiling_usd"] for call in plan),
                "rows": [
                    {
                        "variant": PROBE_VARIANT,
                        "start": call["start"],
                        "status": 200,
                        "latency_ms": 1,
                        "usable": True,
                    }
                    for call in plan
                ],
            }
        ),
        encoding="utf-8",
    )
    assert smoke_direct.main(["--report", "--rows", str(rows), "--out", str(report)]) == 0
    assert "- By start: S5b 15/15, S5bA 15/15" in report.read_text(encoding="utf-8")


def test_schema_profile_body_deep_copies_schema_and_nojson_is_unchanged(tmp_path: Path) -> None:
    prompts = smoke_direct._load_prompts(_prompt_document(tmp_path / "prompts.json"))
    plan = smoke_direct._build_plan(prompts, ("llama-3.3-70b-schema", "llama-3.3-70b-nojson"), smoke_direct._SLOT_ORDER)
    schema_call = plan[0]
    schema_body = smoke_direct._request_body(schema_call)
    assert schema_body["response_format"]["type"] == "json_schema"
    assert schema_body["response_format"]["json_schema"] == smoke_direct.RESPONSE_SCHEMA
    schema_body["response_format"]["json_schema"]["properties"]["segments"]["minItems"] = 99
    assert smoke_direct.RESPONSE_SCHEMA["properties"]["segments"]["minItems"] == 1
    nojson_call = next(call for call in plan if call["variant"] == "llama-3.3-70b-nojson")
    assert "response_format" not in smoke_direct._request_body(nojson_call)


def test_extract_text_serializes_object_result_response() -> None:
    value = {"segments": [{"kind": "narration", "text": "hello"}]}
    assert smoke_direct._extract_text({"result": {"response": value}}) == (
        json.dumps(value, ensure_ascii=False),
        "result.response(object)",
    )


@pytest.mark.parametrize("reply", QUOTE_REPAIR_FIXTURES)
def test_quote_repair_makes_real_failing_replies_repair_usable(reply: str) -> None:
    call = {
        "call_index": 1,
        "variant": "llama-3.3-70b",
        "model": "model",
        "start": "S1",
        "context": "proposed",
        "sample": 0,
        "request_bytes": 1,
    }
    row = smoke_direct._row_from_response(call, json.dumps({"result": {"response": reply}}).encode(), 200, 1.0)

    assert row["usable"] is False
    assert row["repair_usable"] is True
    assert row["narration_repaired"] is not None
    assert '"' in row["narration_repaired"]


def test_repair_fields_are_present_on_strict_transport_and_skipped_rows() -> None:
    call = {
        "call_index": 1,
        "variant": "llama-3.3-70b",
        "model": "model",
        "start": "S1",
        "context": "proposed",
        "sample": 0,
        "request_bytes": 1,
    }
    strict = smoke_direct._row_from_response(
        call, json.dumps({"result": {"response": json.dumps({"segments": [{"text": "ok"}]})}}).encode(), 200, 1.0
    )
    assert strict["usable"] is True
    assert strict["repair_usable"] is True
    assert strict["narration_repaired"] == strict["narration"]

    transport = smoke_direct._transport_row(call, RuntimeError("offline"), 1.0)
    skipped = smoke_direct._skipped_row(call, "skipped")
    for row in (transport, skipped):
        assert row["repair_usable"] is False
        assert row["narration_repaired"] is None


def test_report_counts_strict_and_repaired_rows_and_only_prints_repaired_text(tmp_path: Path) -> None:
    rows = tmp_path / "rows.json"
    report = tmp_path / "report.md"
    rows.write_text(
        json.dumps(
            {
                "ceiling_usd": 0.01,
                "rows": [
                    {
                        "call_index": 1,
                        "variant": "llama-3.3-70b",
                        "model": "model",
                        "start": "S1",
                        "context": "proposed",
                        "sample": 0,
                        "status": 200,
                        "latency_ms": 1,
                        "narration": "strict",
                        "usable": True,
                        "repair_usable": True,
                        "narration_repaired": "strict",
                        "final_text": "strict raw",
                        "skipped": False,
                    },
                    {
                        "call_index": 2,
                        "variant": "llama-3.3-70b",
                        "model": "model",
                        "start": "S1",
                        "context": "proposed",
                        "sample": 1,
                        "status": 200,
                        "latency_ms": 1,
                        "narration": None,
                        "usable": False,
                        "repair_usable": True,
                        "narration_repaired": "repaired speech",
                        "final_text": "bad raw",
                        "skipped": False,
                    },
                    {
                        "call_index": 3,
                        "variant": "llama-3.3-70b",
                        "model": "model",
                        "start": "S1",
                        "context": "proposed",
                        "sample": 2,
                        "status": None,
                        "latency_ms": 0,
                        "narration": None,
                        "usable": False,
                        "repair_usable": False,
                        "narration_repaired": None,
                        "final_text": None,
                        "skipped": True,
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    assert smoke_direct.main(["--report", "--rows", str(rows), "--out", str(report)]) == 0
    report_text = report.read_text(encoding="utf-8")
    assert "- Valid JSON: strict 1 / 2; after the product's quote repair 2 / 2" in report_text
    assert "- Repaired reply text: repaired speech" in report_text
    assert "- Repaired reply text: strict" not in report_text


def test_unknown_slots_are_rejected(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    prompts = _prompt_document(tmp_path / "prompts.json")
    with pytest.raises(SystemExit, match="2"):
        smoke_direct.main(["--dry", "--prompts", str(prompts), "--out", str(tmp_path / "out"), "--slots", "nope"])
    assert "invalid choice" in capsys.readouterr().err


class FakeResponse:
    def __init__(self, status: int, body: object) -> None:
        self.status = status
        self.code = status
        self.headers: dict[str, str] = {}
        self._body = json.dumps(body).encode("utf-8") if not isinstance(body, bytes) else body

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *_args: object) -> None:
        return None


class FakeOpener:
    def __init__(self, responses: list[object]) -> None:
        self.responses = responses
        self.requests: list[object] = []

    def __call__(self, request: object, timeout: float) -> FakeResponse:
        self.requests.append((request, timeout))
        if not self.responses:
            raise AssertionError("fake opener was called after the run should have stopped")
        response = self.responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        return response


def _run_args(prompt_path: Path, out_path: Path) -> list[str]:
    return [
        "--run",
        "--prompts",
        str(prompt_path),
        "--out",
        str(out_path),
        "--confirm",
        "--max-calls",
        "24",
        "--max-usd",
        "1",
    ]


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_plan_is_24_calls_per_variant_round_robin_and_priced(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    prompts = _prompt_document(tmp_path / "prompts.json")
    out = tmp_path / "plan.json"

    assert smoke_direct.main(["--dry", "--prompts", str(prompts), "--out", str(out)]) == 0
    plan = _read_json(out)
    calls = plan["calls"]

    assert len(calls) == 24
    assert plan["ceiling_usd"] > 0
    assert [call["variant"] for call in calls[:4]] == VARIANT_LABELS
    assert all(calls[index]["variant"] != calls[index + 1]["variant"] for index in range(23))
    assert {label: sum(call["variant"] == label for call in calls) for label in VARIANT_LABELS} == {
        label: 6 for label in VARIANT_LABELS
    }
    for label in VARIANT_LABELS:
        variant_calls = [call for call in calls if call["variant"] == label]
        assert [(call["start"], call["context"]) for call in variant_calls] == [
            ("S1", "proposed"),
            ("S1", "proposed"),
            ("S1", "proposed"),
            ("S1", "existing"),
            ("S2", "proposed"),
            ("S5", "proposed"),
        ]
    assert "24 calls" in capsys.readouterr().out
    assert "ceiling" in capsys.readouterr().out.lower() or plan["ceiling_usd"] > 0

    expected = 0.0
    for call in calls:
        profile = next(profile for profile in smoke_direct.VARIANTS if profile["label"] == call["variant"])
        input_tokens = (len((call["system"] + call["user"]).encode("utf-8")) + 2) // 3
        expected += (
            input_tokens * profile["input_price"] + profile["max_tokens"] * profile["output_price"]
        ) / 1_000_000
    assert plan["ceiling_usd"] == pytest.approx(expected)


def test_llama_70b_variant_builds_six_calls_with_expected_request_profile(tmp_path: Path) -> None:
    prompts = _prompt_document(tmp_path / "prompts.json")
    out = tmp_path / "plan.json"

    assert (
        smoke_direct.main(["--dry", "--prompts", str(prompts), "--out", str(out), "--variants", "llama-3.3-70b"]) == 0
    )
    plan = _read_json(out)
    assert len(plan["calls"]) == 6
    assert {call["model"] for call in plan["calls"]} == {"@cf/meta/llama-3.3-70b-instruct-fp8-fast"}
    assert plan["ceiling_usd"] == pytest.approx(sum(call["ceiling_usd"] for call in plan["calls"]))
    body = smoke_direct._request_body(plan["calls"][0])
    assert body["max_tokens"] == 1024
    assert "max_completion_tokens" not in body
    assert body["response_format"] == {"type": "json_object"}
    assert body["temperature"] == 0


def test_new_variants_are_selectable_with_expected_bodies_and_ceiling(tmp_path: Path) -> None:
    prompts = _prompt_document(tmp_path / "prompts.json")
    out = tmp_path / "plan.json"
    variants = ",".join(NEW_VARIANT_LABELS)

    assert smoke_direct.main(["--dry", "--prompts", str(prompts), "--out", str(out), "--variants", variants]) == 0
    plan = _read_json(out)
    assert len(plan["calls"]) == 18
    assert {call["variant"] for call in plan["calls"]} == set(NEW_VARIANT_LABELS)
    assert all(sum(call["variant"] == label for call in plan["calls"]) == 6 for label in NEW_VARIANT_LABELS)
    assert plan["ceiling_usd"] == pytest.approx(sum(call["ceiling_usd"] for call in plan["calls"]))

    bodies = {
        label: smoke_direct._request_body(next(call for call in plan["calls"] if call["variant"] == label))
        for label in NEW_VARIANT_LABELS
    }
    assert "response_format" not in bodies["llama-3.3-70b-nojson"]
    assert bodies["qwen3-think-off-kwargs"]["chat_template_kwargs"] == {"enable_thinking": False}
    assert bodies["qwen3-think-off-soft"]["messages"][-1]["content"].endswith("\n\n/no_think")
    assert (
        bodies["qwen3-think-off-soft"]["messages"][-1]["content"]
        != bodies["qwen3-think-off-kwargs"]["messages"][-1]["content"]
    )
    assert all(
        body["response_format"] == {"type": "json_object"}
        for label, body in bodies.items()
        if label != "llama-3.3-70b-nojson"
    )

    kwargs_call = next(call for call in plan["calls"] if call["variant"] == "qwen3-think-off-kwargs")
    bodies["qwen3-think-off-kwargs"]["chat_template_kwargs"]["enable_thinking"] = True
    assert smoke_direct._request_body(kwargs_call)["chat_template_kwargs"]["enable_thinking"] is False


def test_new_variant_notes_are_in_report(tmp_path: Path) -> None:
    rows = tmp_path / "rows.json"
    report = tmp_path / "report.md"
    rows.write_text(
        json.dumps(
            {
                "ceiling_usd": 0.01,
                "rows": [
                    {
                        "call_index": 1,
                        "variant": "llama-3.3-70b-nojson",
                        "model": "@cf/meta/llama-3.3-70b-instruct-fp8-fast",
                        "start": "S1",
                        "context": "proposed",
                        "sample": 0,
                        "status": 200,
                        "latency_ms": 1,
                        "narration": "ok",
                        "usable": True,
                        "skipped": False,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    assert smoke_direct.main(["--report", "--rows", str(rows), "--out", str(report)]) == 0
    assert "- Note: omits response_format to avoid forced JSON mode" in report.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "variants,expected",
    [("no-such-model", "no-such-model"), ("llama-3.1-8b,llama-3.1-8b", "llama-3.1-8b")],
)
def test_invalid_variant_selection_uses_error_without_network(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], variants: str, expected: str
) -> None:
    prompts = _prompt_document(tmp_path / "prompts.json")
    out = tmp_path / "plan.json"

    assert smoke_direct.main(["--run", "--prompts", str(prompts), "--out", str(out), "--variants", variants]) == 2
    assert expected in capsys.readouterr().err
    assert not out.exists()


def test_report_only_lists_variants_present_in_rows(tmp_path: Path) -> None:
    rows = tmp_path / "rows.json"
    report = tmp_path / "report.md"
    rows.write_text(
        json.dumps(
            {
                "ceiling_usd": 0.01,
                "rows": [
                    {
                        "call_index": index,
                        "variant": "llama-3.3-70b",
                        "model": "@cf/meta/llama-3.3-70b-instruct-fp8-fast",
                        "start": "S1",
                        "context": "proposed",
                        "sample": 0,
                        "status": 200,
                        "latency_ms": 1,
                        "narration": "ok",
                        "usable": True,
                        "skipped": False,
                        "prompt_tokens": 1,
                        "completion_tokens": 1,
                        "actual_cost_usd": 0.000001,
                        "truncated": False,
                        "top_level_keys": [],
                        "result_keys": [],
                        "final_text_path": "result.response",
                        "reasoning_fields": [],
                    }
                    for index in range(1, 7)
                ],
            }
        ),
        encoding="utf-8",
    )

    assert smoke_direct.main(["--report", "--rows", str(rows), "--out", str(report)]) == 0
    report_text = report.read_text(encoding="utf-8")
    assert "### llama-3.3-70b (@cf/meta/llama-3.3-70b-instruct-fp8-fast)" in report_text
    for label in VARIANT_LABELS:
        assert f"### {label} (" not in report_text


@pytest.mark.parametrize(
    "extra_args,missing_credentials",
    [
        (["--max-usd", "1"], False),
        (["--confirm", "--max-calls", "23", "--max-usd", "1"], False),
        (["--confirm", "--max-calls", "24", "--max-usd", "0"], False),
        (["--confirm", "--max-calls", "24"], False),
        (["--confirm", "--max-calls", "24", "--max-usd", "1"], True),
    ],
)
def test_run_refusals_make_zero_calls(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    extra_args: list[str],
    missing_credentials: bool,
) -> None:
    prompts = _prompt_document(tmp_path / "prompts.json")
    out = tmp_path / "rows.json"
    opener = FakeOpener([])
    monkeypatch.setattr(smoke_direct, "urlopen", opener)
    if missing_credentials:
        monkeypatch.delenv("CLOUDFLARE_AI_TOKEN", raising=False)

    assert smoke_direct.main(["--run", "--prompts", str(prompts), "--out", str(out), *extra_args]) != 0
    assert opener.requests == []


def test_request_profiles_and_success_extraction_redact_credentials(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    prompts = _prompt_document(tmp_path / "prompts.json")
    out = tmp_path / "rows.json"
    responses = []
    for index in range(24):
        if index == 1:
            body = {
                "success": True,
                "result": {
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps({"segments": [{"text": "Deep narration."}]}),
                                "reasoning_content": "private chain of thought",
                            },
                            "finish_reason": "stop",
                        }
                    ],
                    "usage": {"prompt_tokens": 11, "completion_tokens": 7},
                },
            }
        else:
            body = {
                "success": True,
                "result": {
                    "response": json.dumps({"segments": [{"text": f"Narration {index}."}]}),
                    "usage": {"prompt_tokens": 10, "completion_tokens": 5},
                    "reasoning_trace": "must not become narration",
                },
            }
        responses.append(FakeResponse(200, body))
    opener = FakeOpener(responses)
    monkeypatch.setattr(smoke_direct, "urlopen", opener)

    assert smoke_direct.main([*_run_args(prompts, out), "--max-usd", "1"]) == 0
    result = _read_json(out)
    assert len(result["rows"]) == 24
    requests = [request for request, _timeout in opener.requests]
    bodies = [json.loads(request.data) for request in requests]
    assert bodies[0]["max_tokens"] == 1024
    assert "max_completion_tokens" not in bodies[0]
    assert bodies[1]["max_completion_tokens"] == 2048
    assert "max_tokens" not in bodies[1]
    expected_limits = [
        ("max_tokens", 1024),
        ("max_completion_tokens", 2048),
        ("max_tokens", 2048),
        ("max_tokens", 2048),
    ]
    for body, (parameter, value) in zip(bodies[:4], expected_limits, strict=True):
        assert body[parameter] == value
        assert body.get("max_tokens", body.get("max_completion_tokens")) == value
        other_parameter = "max_completion_tokens" if parameter == "max_tokens" else "max_tokens"
        assert other_parameter not in body
    for body in bodies:
        assert body["response_format"] == {"type": "json_object"}
        assert body["temperature"] == 0
        assert [message["role"] for message in body["messages"]] == ["system", "user"]
    assert requests[0].get_header("Authorization") == f"Bearer {TOKEN}"

    llama = result["rows"][0]
    assert llama["final_text_path"] == "result.response"
    assert llama["narration"] == "Narration 0."
    assert llama["top_level_keys"] == ["success", "result"]
    assert "response" in llama["result_keys"]
    assert "reasoning_trace" in llama["reasoning_fields"]
    gemma = result["rows"][1]
    assert gemma["final_text_path"] == "result.choices[0].message.content"
    assert gemma["narration"] == "Deep narration."
    assert "reasoning_content" in gemma["reasoning_fields"]
    assert "private chain of thought" not in gemma["narration"]

    report = tmp_path / "report.md"
    assert smoke_direct.main(["--report", "--rows", str(out), "--out", str(report)]) == 0
    report_text = report.read_text(encoding="utf-8")
    assert "Narration 0." in report_text and "Deep narration." in report_text
    assert "usable" in report_text and "response" in report_text
    assert TOKEN not in out.read_text(encoding="utf-8")
    assert TOKEN not in report_text


def test_auth_and_rate_limit_stop_without_retry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    prompts = _prompt_document(tmp_path / "prompts.json")
    auth_out = tmp_path / "auth.json"
    auth_opener = FakeOpener(
        [FakeResponse(401, {"errors": [{"code": 1001, "message": "bad auth"}]}), FakeResponse(200, {})]
    )
    monkeypatch.setattr(smoke_direct, "urlopen", auth_opener)
    assert smoke_direct.main([*_run_args(prompts, auth_out), "--max-usd", "1"]) == 0
    auth_result = _read_json(auth_out)
    assert len(auth_opener.requests) == 1
    assert auth_result["stop_reason"] == "AUTH"
    assert auth_result["rows"][0]["error_class"] == "AUTH"

    rate_out = tmp_path / "rate.json"
    rate_opener = FakeOpener(
        [
            FakeResponse(429, {"errors": [{"code": "AI_QUOTA_EXCEEDED", "message": "try later"}]}),
            FakeResponse(200, {}),
        ]
    )
    monkeypatch.setattr(smoke_direct, "urlopen", rate_opener)
    assert smoke_direct.main([*_run_args(prompts, rate_out), "--max-usd", "1"]) == 0
    rate_result = _read_json(rate_out)
    assert len(rate_opener.requests) == 1
    assert "AI_QUOTA_EXCEEDED" in rate_result["stop_reason"]
    assert "try later" in rate_result["rows"][0]["error_message"]


def test_http_200_malformed_reply_is_unusable_but_variant_continues(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    prompts = _prompt_document(tmp_path / "prompts.json")
    out = tmp_path / "rows.json"
    malformed_reply = '{"segments\':[{": "narration", "text": "..."}'
    malformed = {"success": True, "result": {"response": malformed_reply}}
    success = {
        "success": True,
        "result": {"response": json.dumps({"segments": [{"text": "ok"}]})},
    }
    opener = FakeOpener([FakeResponse(200, malformed), *[FakeResponse(200, success) for _ in range(5)]])
    monkeypatch.setattr(smoke_direct, "urlopen", opener)

    assert smoke_direct.main([*_run_args(prompts, out), "--variants", "llama-3.3-70b", "--max-usd", "1"]) == 0
    result = _read_json(out)
    rows = result["rows"]
    assert len(opener.requests) == 6
    assert len(rows) == 6
    assert rows[0]["status"] == 200
    assert rows[0]["usable"] is False
    assert rows[0]["narration"] is None
    assert rows[0]["final_text"] == malformed_reply
    assert "error_class" not in rows[0]
    assert all(row["usable"] for row in rows[1:])
    assert result["failed_variants"] == {}


def test_report_prints_raw_final_text_for_unusable_row(tmp_path: Path) -> None:
    rows = tmp_path / "rows.json"
    report = tmp_path / "report.md"
    raw_reply = '{"segments\':[{": "narration", "text": "..."}'
    rows.write_text(
        json.dumps(
            {
                "ceiling_usd": 0.01,
                "rows": [
                    {
                        "call_index": 1,
                        "variant": "llama-3.3-70b",
                        "model": "@cf/meta/llama-3.3-70b-instruct-fp8-fast",
                        "start": "S1",
                        "context": "proposed",
                        "sample": 0,
                        "status": 200,
                        "latency_ms": 1,
                        "narration": None,
                        "usable": False,
                        "skipped": False,
                        "final_text": raw_reply,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    assert smoke_direct.main(["--report", "--rows", str(rows), "--out", str(report)]) == 0
    report_text = report.read_text(encoding="utf-8")
    assert "- Narration: (unusable)" in report_text
    assert f"- Raw reply text: {raw_reply}" in report_text


def test_second_transport_failure_stops_and_does_not_retry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    prompts = _prompt_document(tmp_path / "prompts.json")
    out = tmp_path / "rows.json"
    opener = FakeOpener([RuntimeError("transport one"), RuntimeError(f"transport {TOKEN}"), FakeResponse(200, {})])
    monkeypatch.setattr(smoke_direct, "urlopen", opener)

    assert smoke_direct.main([*_run_args(prompts, out), "--max-usd", "1"]) == 0
    result = _read_json(out)
    assert len(opener.requests) == 2
    assert result["stop_reason"] == "TRANSPORT_FAILURES"
    assert TOKEN not in out.read_text(encoding="utf-8")


def test_http_error_body_is_recorded_without_leaking_token(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    prompts = _prompt_document(tmp_path / "prompts.json")
    out = tmp_path / "rows.json"
    error = HTTPError(
        "https://api.example.invalid",
        401,
        "Unauthorized",
        {},
        __import__("io").BytesIO(json.dumps({"message": TOKEN}).encode()),
    )
    opener = FakeOpener([error])
    monkeypatch.setattr(smoke_direct, "urlopen", opener)

    assert smoke_direct.main([*_run_args(prompts, out), "--max-usd", "1"]) == 0
    assert TOKEN not in out.read_text(encoding="utf-8")


@pytest.mark.parametrize("status", [400, 404])
def test_nonfatal_http_failure_skips_only_failed_variant_and_continues(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, status: int
) -> None:
    prompts = _prompt_document(tmp_path / "prompts.json")
    out = tmp_path / "rows.json"
    error_body = b'{"error":"gemma-4-26b-a4b unavailable","detail":"raw model error"}'
    success = {
        "success": True,
        "result": {"response": json.dumps({"segments": [{"text": "ok"}]})},
    }
    opener = FakeOpener(
        [FakeResponse(200, success), FakeResponse(status, error_body)] + [FakeResponse(200, success)] * 18
    )
    monkeypatch.setattr(smoke_direct, "urlopen", opener)

    assert smoke_direct.main([*_run_args(prompts, out), "--max-usd", "1"]) == 0
    result = _read_json(out)
    assert len(opener.requests) == 19
    assert len(result["rows"]) == 24
    failed_rows = [row for row in result["rows"] if row["variant"] == "gemma-4-26b-a4b"]
    assert failed_rows[0]["status"] == status
    assert failed_rows[0]["error_class"] == "VARIANT_FAILED"
    assert failed_rows[0]["raw_response"] == error_body.decode()
    assert len(failed_rows) == 6
    assert all(row.get("skipped") is True for row in failed_rows[1:])
    assert all(row.get("status") == 200 for row in result["rows"] if row["variant"] != "gemma-4-26b-a4b")
    assert result["stop_reason"] is None

    report = tmp_path / "report.md"
    assert smoke_direct.main(["--report", "--rows", str(out), "--out", str(report)]) == 0
    assert error_body.decode() in report.read_text(encoding="utf-8")
