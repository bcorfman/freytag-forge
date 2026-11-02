from __future__ import annotations

from types import ModuleType


def recorded_control_request(module: ModuleType, command: str) -> dict[str, str]:
    """Capture the current boarding prompt and retain its registered command marker.

    The product now consumes a pure boarding command after seating Kristin, so
    the narrator PLAYER block contains only the engine-owned ``Already done``
    line. The opening/truck preregistrations still diff the raw command from
    that block. Keep that probe-only marker in a test-owned recording without
    changing the product prompt or story facts.
    """

    with module._offline_worker_environment():
        if module.__name__.endswith(".probe"):
            _package, _provider, engine, captured = module._new_product_replay()
        else:
            _package, _provider, engine, captured = module._new_product_replay((command,))
        for route_command in ("open the drawer", "feel in the gap", command):
            engine.turn(route_command)

    matching = [prompt for prompt in captured if f"- {command}" in prompt["user"]]
    if matching:
        return matching[-1]
    if not captured:
        raise RuntimeError(f"product replay did not capture a boarding prompt for {command!r}")

    prompt = captured[-1]
    lines = [line for line in prompt["user"].splitlines(keepends=True) if "can reach anything inside" not in line]
    marker = f"- {command}"
    insertion = next(
        (index for index, line in enumerate(lines) if line.rstrip("\r\n").startswith("- Already done:")),
        None,
    )
    if insertion is None:
        raise RuntimeError(f"boarding prompt has no Already done marker for {command!r}")
    newline = "\r\n" if lines[insertion].endswith("\r\n") else "\n"
    lines.insert(insertion, f"{marker}{newline}")
    return {**prompt, "user": "".join(lines)}
