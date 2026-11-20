"""Owner-facing checks that must pass before the factory can run."""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from factory.frozen import changed_paths, load_patterns, touches_frozen
from factory.guard import Caps, ModelGuard, ModelNotAllowed, ProviderPolicy


@dataclass(frozen=True)
class PreflightItem:
    name: str
    ok: bool
    detail: str


def _default_run_command(argv: list[str]) -> tuple[int, str]:
    """Run one bounded, shell-free command and return its combined output."""

    try:
        completed = subprocess.run(
            argv,
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
            shell=False,
        )
    except FileNotFoundError as exc:
        return 127, str(exc)
    except subprocess.TimeoutExpired as exc:
        output = (exc.stdout or "") + (exc.stderr or "")
        return 124, f"timed out after 20 seconds: {output}".strip()
    return completed.returncode, (completed.stdout or "") + (completed.stderr or "")


def _load_config(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        data = json.load(stream)
    if not isinstance(data, dict):
        raise ValueError("configuration must be a JSON object")
    return data


def _path(root: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root / path


def _detail(error: BaseException) -> str:
    message = str(error)
    return f"{type(error).__name__}: {message}" if message else type(error).__name__


def _item(name: str, action: Callable[[], str]) -> PreflightItem:
    try:
        return PreflightItem(name, True, action())
    except Exception as error:
        return PreflightItem(name, False, _detail(error))


def run_preflight(
    root: Path,
    config_path: Path,
    *,
    run_command: Callable[[list[str]], tuple[int, str]] | None = None,
) -> list[PreflightItem]:
    """Run all preflight checks, retaining an item for every independent check."""

    root = Path(root)
    config_path = Path(config_path)
    command = run_command or _default_run_command

    def config() -> dict[str, Any]:
        return _load_config(config_path)

    def paths() -> dict[str, Path]:
        data = config()
        configured = data["paths"]
        return {name: _path(root, value) for name, value in configured.items()}

    items: list[PreflightItem] = []
    items.append(_item("config_loads", lambda: "configuration loaded" if config() is not None else ""))

    def check_caps() -> str:
        data = config()
        caps = Caps.from_dict(data["caps"])
        problems: list[str] = []
        if caps.total_budget_usd <= 0:
            problems.append("total_budget_usd must be above zero")
        providers = tuple(dict.fromkeys(("claude_code", "codex", "cloudflare", *caps.daily_cap_usd, *caps.providers)))
        missing_or_zero = [
            provider
            for provider in providers
            if caps.providers.get(provider, ProviderPolicy("reported", {})).kind == "reported"
            if caps.daily_cap_usd.get(provider, 0.0) <= 0
        ]
        if missing_or_zero:
            problems.append("reported daily caps must be above zero for: " + ", ".join(missing_or_zero))
        missing_or_invalid_ceilings = []
        for provider, policy in caps.providers.items():
            if policy.kind != "subscription":
                continue
            for window in ("five_hour", "seven_day"):
                ceiling = policy.ceilings.get(window)
                if ceiling is None or ceiling <= 0 or ceiling >= 1:
                    missing_or_invalid_ceilings.append(f"{provider}.{window}")
        if missing_or_invalid_ceilings:
            problems.append(
                "subscription ceilings must be above zero and below one for: " + ", ".join(missing_or_invalid_ceilings)
            )
        if problems:
            raise ValueError("; ".join(problems))
        reported = [
            provider
            for provider in providers
            if caps.providers.get(provider, ProviderPolicy("reported", {})).kind == "reported"
        ]
        subscriptions = [provider for provider, policy in caps.providers.items() if policy.kind == "subscription"]
        return (
            "budget set; reported daily caps set for: "
            + ", ".join(reported)
            + "; subscription ceilings set for: "
            + ", ".join(subscriptions)
        )

    items.append(_item("caps_set", check_caps))

    def load_allowlist() -> str:
        ModelGuard.from_file(paths()["allowlist"])
        return "allowlist loaded"

    items.append(_item("allowlist_loads", load_allowlist))

    def refuse_fable() -> str:
        guard = ModelGuard.from_file(paths()["allowlist"])
        try:
            guard.check("prose", "claude-fable-5-2", "high")
        except ModelNotAllowed:
            return "denied model was refused"
        raise ValueError("allowlist accepted claude-fable-5-2")

    items.append(_item("allowlist_refuses_fable", refuse_fable))

    def load_frozen() -> str:
        load_patterns(paths()["frozen"])
        return "frozen patterns loaded"

    items.append(_item("frozen_loads", load_frozen))

    def configure_notifier() -> str:
        data = config()["notifier"]
        kind = data.get("kind")
        if kind == "file":
            notifier_path = _path(root, data["path"])
            notifier_path.parent.mkdir(parents=True, exist_ok=True)
            if not notifier_path.parent.is_dir():
                raise ValueError(f"notifier parent is not a directory: {notifier_path.parent}")
            return "file notifier configured"
        if kind == "command":
            argv = data.get("argv")
            if not isinstance(argv, list) or not argv or not all(isinstance(value, str) for value in argv):
                raise ValueError("command notifier argv must be a non-empty list of strings")
            executable = shutil.which(argv[0])
            if executable is None:
                raise ValueError(f"notifier executable not found: {argv[0]}")
            return f"command notifier configured: {executable}"
        raise ValueError(f"notifier kind must be file or command, got {kind!r}")

    items.append(_item("notifier_configured", configure_notifier))

    def writable_state_dir() -> str:
        state_dir = paths()["state"].parent
        state_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=state_dir, prefix=".preflight-", delete=True):
            pass
        return f"writable: {state_dir}"

    items.append(_item("state_dir_writable", writable_state_dir))

    def clean_git() -> str:
        returncode, output = command(["git", "-C", str(root), "status", "--porcelain"])
        if returncode != 0:
            raise ValueError(f"git status returned {returncode}: {output.strip()}")
        if output.strip():
            raise ValueError(f"working tree is dirty: {output.strip()}")
        return "working tree is clean"

    items.append(_item("git_clean", clean_git))

    def has_claude() -> str:
        returncode, output = command(["claude", "--version"])
        if returncode != 0:
            raise ValueError(f"claude --version returned {returncode}: {output.strip()}")
        return (
            "CLI exists; this only proves the CLI exists and the owner still confirms it bills the subscription, "
            "not the API"
        )

    items.append(_item("headless_claude", has_claude))

    def unchanged_harness() -> str:
        patterns = load_patterns(paths()["frozen"])
        paths_changed = changed_paths(root, "origin/main")
        touched = touches_frozen(paths_changed, patterns)
        if touched:
            raise ValueError("frozen harness paths changed: " + ", ".join(touched))
        return "no frozen harness paths changed against origin/main"

    items.append(_item("harness_unchanged_vs_main", unchanged_harness))
    return items


def preflight_ok(items: list[PreflightItem]) -> bool:
    return all(item.ok for item in items)


def render(items: list[PreflightItem]) -> str:
    return "\n".join(f"{'OK' if item.ok else 'FAIL'} {item.name}: {item.detail}" for item in items)
