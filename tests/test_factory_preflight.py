import json
from pathlib import Path

import factory.preflight as preflight_module
from factory.preflight import preflight_ok, render, run_preflight

SOURCE_CONFIG = Path(__file__).parents[1] / "factory/config"


def make_config(tmp_path: Path, *, budget: float = 10.0, notifier: dict | None = None) -> Path:
    config_dir = tmp_path / "factory/config"
    config_dir.mkdir(parents=True)
    for name in ("allowlist.json", "frozen.json"):
        (config_dir / name).write_bytes((SOURCE_CONFIG / name).read_bytes())
    data = json.loads((SOURCE_CONFIG / "factory.json").read_text(encoding="utf-8"))
    data["caps"]["total_budget_usd"] = budget
    data["caps"]["daily_cap_usd"] = {"claude_code": 5.0, "codex": 5.0, "cloudflare": 5.0}
    if notifier is not None:
        data["notifier"] = notifier
    path = config_dir / "factory.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def successful_command(argv: list[str]) -> tuple[int, str]:
    return 0, ""


def patch_harness(monkeypatch) -> None:
    monkeypatch.setattr(preflight_module, "changed_paths", lambda root, base: [])


def test_shipped_config_fails_only_for_zero_caps(tmp_path, monkeypatch):
    config = make_config(tmp_path, budget=0.0)
    patch_harness(monkeypatch)

    items = run_preflight(tmp_path, config, run_command=successful_command)

    assert not preflight_ok(items)
    assert [item.name for item in items if not item.ok] == ["caps_set"]
    assert "FAIL caps_set" in render(items)


def test_real_caps_pass_all_checks(tmp_path, monkeypatch):
    config = make_config(tmp_path)
    patch_harness(monkeypatch)

    items = run_preflight(tmp_path, config, run_command=successful_command)

    assert preflight_ok(items)


def test_preflight_items_fail_independently(tmp_path, monkeypatch):
    config = make_config(tmp_path)
    patch_harness(monkeypatch)

    dirty = run_preflight(tmp_path, config, run_command=lambda argv: (0, " M file.py") if argv[0] == "git" else (0, ""))
    assert not next(item for item in dirty if item.name == "git_clean").ok
    assert next(item for item in dirty if item.name == "headless_claude").ok

    missing_claude = run_preflight(
        tmp_path,
        config,
        run_command=lambda argv: (127, "not found") if argv[0] == "claude" else (0, ""),
    )
    assert not next(item for item in missing_claude if item.name == "headless_claude").ok
    assert next(item for item in missing_claude if item.name == "git_clean").ok

    missing_notifier = make_config(tmp_path / "notifier", notifier={"kind": "command", "argv": ["no-such-command"]})
    missing = run_preflight(tmp_path / "notifier", missing_notifier, run_command=successful_command)
    assert not next(item for item in missing if item.name == "notifier_configured").ok

    allowlist = tmp_path / "allowlist"
    allowlist_config = make_config(allowlist)
    (allowlist / "factory/config/allowlist.json").unlink()
    missing_allowlist = run_preflight(allowlist, allowlist_config, run_command=successful_command)
    assert not next(item for item in missing_allowlist if item.name == "allowlist_loads").ok
    assert not next(item for item in missing_allowlist if item.name == "allowlist_refuses_fable").ok
