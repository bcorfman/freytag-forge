import json
from pathlib import Path

import pytest

import bench.cli as bench_cli
import bench.core as core
from bench.core import load_variation, score_fact_tracking_judgments
from bench.item_facts import ItemFactsProvider
from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.state import RuntimeState
from storygame.story_package.loader import load_story_package

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = load_story_package(ROOT / "data" / "stories" / "continuity-initiative")
SINGLE = ROOT / "bench" / "variations" / "item-facts-single.json"
SECOND = ROOT / "bench" / "variations" / "item-facts-second.json"


def _provider(mode="single_call"):
    state = RuntimeState.bootstrap(PACKAGE)
    return ItemFactsProvider(
        worker_url="https://worker.example/turn",
        token="",
        state=state,
        item_facts={"the lantern": ["lit"], "the gate": ["closed"]},
        mode=mode,
    )


class _Response:
    def __init__(self, body):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return json.dumps(self.body).encode()


def test_things_are_after_scene_and_rules_suppress_authored_item_facts():
    provider = _provider()
    prompt = provider.assemble_turn_prompt("Look at the back door.")
    user = provider._section_user_prompt(prompt["context"])

    assert "\n\nTHINGS:\n- the lantern: lit\n- the gate: closed\n\nCONSTRAINTS:" in user
    assert provider._placement_rules() == []
    assert provider._setting_fact_rules() == []


def test_single_call_strips_item_facts_before_strict_proposal_and_carries_them(monkeypatch):
    provider = _provider()
    payloads = iter(
        [
            {
                "segments": [{"kind": "narration", "text": "The house is quiet."}],
                "item_facts": {"the lantern": ["warm"], "the gate": ["closed"]},
            },
        ]
    )
    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", lambda *_args, **_kwargs: _Response(next(payloads)))

    provider("Look at the lantern.")
    assert provider.pending_item_facts() == {"the lantern": ["warm"], "the gate": ["closed"]}
    provider.apply_item_facts(provider.pending_item_facts())
    next_prompt = provider.assemble_turn_prompt("Look at the gate.")
    assert "- the lantern: warm" in provider._section_user_prompt(next_prompt["context"])


def test_apply_item_facts_drops_unknown_and_preserves_malformed_entries():
    provider = _provider()
    facts, issues = provider.apply_item_facts({"the lantern": ["  warm  "], "unknown thing": ["new"], "the gate": [""]})

    assert facts == {"the lantern": ["warm"], "the gate": ["closed"]}
    assert any("unknown thing" in issue for issue in issues)
    assert any("the gate" in issue for issue in issues)


def test_second_call_uses_only_things_player_and_story_and_counts_request(monkeypatch):
    provider = _provider("second_call")
    requests = []

    def open_request(request, **_kwargs):
        requests.append(json.loads(request.data))
        return _Response({"item_facts": {"the lantern": ["warm"], "the gate": ["closed"]}})

    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", open_request)
    raw = provider.second_call_update("Look at the lantern.", "The lantern feels warm.")

    assert raw == {"the lantern": ["warm"], "the gate": ["closed"]}
    assert provider.request_count == 1
    assert "CONSTRAINTS" not in requests[0]["user"]
    assert requests[0]["user"].startswith("THINGS:\n")
    assert requests[0]["system"] == (
        "You keep track of things in a story. Read THINGS, PLAYER and STORY. Return only JSON like "
        '{"item_facts": {"thing": ["fact", "fact"]}}, using only the names in THINGS. '
        "If STORY moves a thing, someone picks it up or puts it down, or it changes, write its "
        "new facts and drop facts that are no longer true. Example: if she picks up the lantern "
        'from the table, the lantern is "in her hand", not "on the table". Keep the other facts '
        "the same."
    )


@pytest.mark.parametrize("path", [SINGLE, SECOND])
def test_item_facts_variations_load_and_render_offline(path):
    variation = load_variation(path)
    prompt = core.prompt_for(variation, "1A", "Look at the back door.")
    assert "THINGS:" in prompt["user"]
    assert variation["_package_hash"]


def test_bad_item_facts_and_fact_tracking_options_are_rejected(tmp_path):
    source = json.loads(SINGLE.read_text())
    source["item_facts"] = {"mode": "single_call", "seed": {"thing": []}}
    path = tmp_path / "bad-facts.json"
    path.write_text(json.dumps(source))
    with pytest.raises(ValueError, match="item_facts"):
        load_variation(path)

    source = json.loads(SINGLE.read_text())
    source["fact_tracking_judge"] = "yes"
    path = tmp_path / "bad-judge.json"
    path.write_text(json.dumps(source))
    with pytest.raises(ValueError, match="fact_tracking_judge must be a boolean"):
        load_variation(path)


def test_fact_tracking_score_counts_verdicts_and_causes():
    result = score_fact_tracking_judgments(
        [
            {
                "turns": [
                    {
                        "facts_after_correct": "yes",
                        "missed_change": "no",
                        "invented_change": "no",
                        "narration_contradicts_given_facts": "no",
                        "changes": [{"thing": "the lantern", "change": "warm", "cause": "command"}],
                    }
                ]
            }
        ],
        1,
    )
    assert result["facts_after_correct"] == {"yes": 1, "no": 0}
    assert result["changes_by_cause"] == {"command": 1, "narrator": 0}
    assert result["turns_judged"] == 1
    assert result["judge_calls"] == 1


def test_variations_without_item_facts_keep_the_original_provider(monkeypatch):
    variation = core.resolve_variation(
        {"name": "plain", "story_package": "data/stories/continuity-initiative"},
        ROOT / "plain.json",
    )
    state = RuntimeState.bootstrap(PACKAGE)
    monkeypatch.setattr(
        CloudflareTurnProvider,
        "from_environment",
        classmethod(lambda cls, state, **kwargs: cls(worker_url="", token="", state=state)),
    )
    assert type(core.provider_for(state, variation)) is CloudflareTurnProvider


def test_fact_tracking_is_wired_into_cli_summary_and_ledger(monkeypatch, tmp_path):
    variation = json.loads(SINGLE.read_text())
    variation = core.resolve_variation(variation, SINGLE)
    record = {
        "status": "ok",
        "script": "phone-bag-door",
        "scene_id": "1A",
        "opening": "Opening.",
        "turns": [],
        "completed": True,
        "quota": None,
        "narration_turns": 0,
        "narration_requests": 1,
        "recovery_requests": 0,
        "package": variation["_package_path"],
        "entry_state": {"scene_id": "1A", "seeded_by": "none"},
        "replicate": 1,
    }
    judgment = {
        "turns": [
            {
                "facts_after_correct": "yes",
                "missed_change": "no",
                "invented_change": "no",
                "narration_contradicts_given_facts": "no",
                "changes": [],
            }
        ]
    }
    monkeypatch.setattr(bench_cli, "load_variation", lambda _: variation)
    monkeypatch.setattr(bench_cli, "scripts_for", lambda *_: [{"name": "phone-bag-door", "inputs": ["Look."]}])
    monkeypatch.setattr(bench_cli, "run_scene", lambda *_: record.copy())
    monkeypatch.setattr(bench_cli, "run_judges", lambda *_: {"judgments": [{"scene_id": "1A"}], "judge_calls": 1})
    monkeypatch.setattr(
        bench_cli,
        "run_continuity_judges",
        lambda *_: {
            "judgments": [
                {
                    "turns": [
                        {
                            "contradicts_stated_fact": "no",
                            "protagonist_acts_beyond_command": "no",
                            "restarts_scene": "no",
                        }
                    ]
                }
            ],
            "judge_calls": 1,
        },
    )
    monkeypatch.setattr(bench_cli, "run_fact_tracking_judges", lambda *_: {"judgments": [judgment], "judge_calls": 1})
    monkeypatch.setattr(bench_cli, "LEDGER_PATH", tmp_path / "ledger.jsonl")
    args = bench_cli.parser().parse_args(
        ["run", "--variation", str(SINGLE), "--scene", "1A", "--replicates", "1", "--out", str(tmp_path)]
    )
    assert bench_cli._run(args) == 0
    summary = json.loads((tmp_path / "summary.json").read_text())
    assert summary["fact_tracking"]["judge_calls"] == 1
    ledger = json.loads((tmp_path / "ledger.jsonl").read_text())
    assert ledger["fact_tracking"]["changes_by_cause"] == {"command": 0, "narrator": 0}
    assert ledger["spend"]["judge_calls"] == 3
