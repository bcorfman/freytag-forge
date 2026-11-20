"""Command-line entry point for the deterministic dark factory."""

from __future__ import annotations

import argparse
import importlib
import json
import tempfile
import time
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from factory.breakers import BreakerConfig, CommandNotifier, FileNotifier, check_breakers, guarded_run
from factory.frozen import load_patterns
from factory.guard import Caps, ModelGuard, SpendLedger
from factory.line import FactoryLine
from factory.preflight import preflight_ok, render, run_preflight
from factory.state import FactoryState
from factory.tickets import Station, Status, TicketQueue

_SUCCESSFUL_PREFLIGHTS: set[Path] = set()


def _repository_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _load_config(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        data = json.load(stream)
    if not isinstance(data, dict):
        raise ValueError("configuration must be a JSON object")
    return data


def _paths(root: Path, config: dict[str, Any]) -> dict[str, Path]:
    result: dict[str, Path] = {}
    for name, value in config["paths"].items():
        path = Path(value)
        result[name] = path if path.is_absolute() else root / path
    return result


def _notifier(root: Path, config: dict[str, Any]):
    settings = config["notifier"]
    if settings["kind"] == "file":
        path = Path(settings["path"])
        return FileNotifier(path if path.is_absolute() else root / path)
    if settings["kind"] == "command":
        return CommandNotifier(list(settings["argv"]))
    raise ValueError(f"unknown notifier kind: {settings['kind']!r}")


def _handlers(spec: str) -> dict[Station, Callable[..., Any]]:
    module_name, separator, function_name = spec.partition(":")
    if not separator or not module_name or not function_name:
        raise ValueError("handlers must be a dotted module:function path")
    factory = getattr(importlib.import_module(module_name), function_name)
    handlers = factory()
    if not isinstance(handlers, dict):
        raise TypeError("handler factory must return a dict")
    return handlers


def _run_preflight(args: argparse.Namespace) -> int:
    items = run_preflight(args.root, args.config, run_command=args.run_command)
    print(render(items))
    try:
        state_path = Path(_load_config(args.config)["paths"]["state"])
        state_path = state_path if state_path.is_absolute() else args.root / state_path
    except Exception:
        state_path = args.root / "factory/state/state.json"
    marker = state_path.parent / "preflight.ok"
    if preflight_ok(items):
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text("successful preflight\n", encoding="utf-8")
        _SUCCESSFUL_PREFLIGHTS.add(marker.resolve())
        return 0
    marker.unlink(missing_ok=True)
    _SUCCESSFUL_PREFLIGHTS.discard(marker.resolve())
    return 1


def _status(root: Path, config_path: Path, now: datetime) -> int:
    config = _load_config(config_path)
    paths = _paths(root, config)
    queue = TicketQueue(paths["tickets"])
    state = FactoryState.load(paths["state"])
    ledger = SpendLedger(paths["ledger"])
    tickets = queue.all()
    for status in Status:
        print(f"{status.value}: {sum(ticket.status is status for ticket in tickets)}")
    sleeping = state.sleeping_lanes(now)
    print("sleeping lanes: " + (", ".join(f"{name} until {until}" for name, until in sleeping.items()) or "none"))
    if state.is_tripped():
        print(f"breaker: tripped ({state.breaker_reason() or 'unknown reason'})")
    else:
        print("breaker: clear")
    total_usd = ledger.total_usd()
    unknown_rows = ledger.unknown_cost_rows()
    unknown_note = f" (a minimum: {unknown_rows} calls of unknown cost)" if unknown_rows > 0 else ""
    print(f"total spend: {total_usd:.6f} USD{unknown_note}")
    providers = set(config.get("caps", {}).get("providers", {}))
    providers.update(config.get("caps", {}).get("daily_cap_usd", {}))
    for provider in sorted(providers):
        report = ledger.last_limits(provider)
        if report is None:
            continue
        windows = ", ".join(
            f"{window.name} {round(window.used * 100):.0f}%"
            for window in sorted(report.windows, key=lambda item: item.name)
        )
        print(f"{provider} windows: {windows}")
    for provider, limited_since in sorted(state.limited_since.items()):
        print(f"{provider} limited since {limited_since}")
    return 0


def _wake(root: Path, config_path: Path, provider: str, now: datetime) -> int:
    config = _load_config(config_path)
    paths = _paths(root, config)
    state = FactoryState.load(paths["state"])
    queue = TicketQueue(paths["tickets"])
    was_sleeping = state.wake(provider)
    woken = queue.wake_provider(provider, now)
    lane_status = "lane cleared" if was_sleeping else "lane was not sleeping"
    print(f"{provider}: {lane_status}, {woken} ticket(s) ready")
    return 0


def _run_factory(args: argparse.Namespace, now_fn: Callable[[], datetime]) -> int:
    config = _load_config(args.config)
    paths = _paths(args.root, config)
    marker = paths["state"].parent / "preflight.ok"
    if not marker.exists() or marker.resolve() not in _SUCCESSFUL_PREFLIGHTS:
        print("preflight required: run a successful preflight in this repository run")
        return 2

    state = FactoryState.load(paths["state"])
    if state.is_tripped():
        print(f"breaker already tripped: {state.breaker_reason() or 'unknown reason'}")
        return 2
    if not args.handlers:
        print("no station handlers wired")
        return 2

    try:
        handlers = _handlers(args.handlers)
        ModelGuard.from_file(paths["allowlist"])
        caps = Caps.from_dict(config["caps"])
        breaker_config = BreakerConfig(**config["breakers"])
        queue = TicketQueue(paths["tickets"])
        ledger = SpendLedger(paths["ledger"])
        load_patterns(paths["frozen"])
        notifier = _notifier(args.root, config)

        def provider_for(ticket):
            return ticket.provider or ticket.payload.get("provider")

        def breaker_reasons(now: datetime) -> list[str]:
            trips = check_breakers(
                queue=queue,
                state=state,
                ledger=ledger,
                caps=caps,
                config=breaker_config,
                now=now,
            )
            return [trip.reason for trip in trips]

        line = FactoryLine(
            queue=queue,
            state=state,
            handlers=handlers,
            provider_for=provider_for,
            check_breakers=breaker_reasons,
        )
        if state.started_at is None:
            started = now_fn()
            if started.tzinfo is None or started.utcoffset() is None:
                raise ValueError("now_fn must return a timezone-aware datetime")
            state.started_at = started.astimezone(UTC).isoformat()
            state.save()
        outcomes = guarded_run(
            lambda: line.run(clock=now_fn, sleep=time.sleep),
            state=state,
            notifier=notifier,
            now_fn=now_fn,
        )
        print(f"run completed: {len(outcomes)} step(s)")
        return 0
    except Exception as error:
        print(f"run failed: {type(error).__name__}: {error}")
        return 1


def main(
    argv: Sequence[str] | None = None,
    *,
    now_fn: Callable[[], datetime] | None = None,
    drill_fn: Callable[..., list] | None = None,
    run_command: Callable[[list[str]], tuple[int, str]] | None = None,
) -> int:
    parser = argparse.ArgumentParser(prog="factory")
    parser.add_argument("--root", type=Path, default=_repository_root())
    parser.add_argument("--config", type=Path, default=None)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("preflight")
    subparsers.add_parser("status")
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--handlers")
    wake_parser = subparsers.add_parser("wake")
    wake_parser.add_argument("provider")
    subparsers.add_parser("drill")
    args = parser.parse_args(argv)
    args.root = args.root.resolve()
    args.config = (args.config or args.root / "factory/config/factory.json").resolve()
    args.run_command = run_command
    clock = now_fn or (lambda: datetime.now(UTC))

    if args.command == "preflight":
        return _run_preflight(args)
    if args.command == "status":
        return _status(args.root, args.config, clock())
    if args.command == "run":
        return _run_factory(args, clock)
    if args.command == "wake":
        return _wake(args.root, args.config, args.provider, clock())

    with tempfile.TemporaryDirectory(prefix="factory-drill-") as directory:
        if drill_fn is None:
            from factory.drill import drill_passed, render_report, run_drill

            results = run_drill(Path(directory), clock())
        else:
            results = drill_fn(Path(directory), clock())

            def drill_passed(values) -> bool:
                return all(result.passed for result in values)

            def render_report(values) -> str:
                return "\n".join(
                    f"{'PASS' if result.passed else 'FAIL'} {result.name}: {result.detail}" for result in values
                )

    print(render_report(results))
    return 0 if drill_passed(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
