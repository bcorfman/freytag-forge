"""Cheap, injected-asker semantic checks for authored scene frames.

The deterministic auditor decides which details are worth checking; this
module asks the existing narration Worker one closed-form entailment question
per scene.  Importing it never performs I/O.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from pathlib import Path
from urllib.request import Request, urlopen

import yaml

from storygame.audit import _finding, _plot_scenes

Ask = Callable[[str], str]
_PHYSICAL_NOUNS = (
    "archive|bag|battery|bench|blood|bottle|box|card|chair|door|drawer|file|floor|gate|hardware|"
    "laptop|memory|phone|radio|recording|server|terminal|track|vent|water|workstation"
)
_DETAIL = re.compile(
    rf"(?:(?:undamaged|damaged|dead|gone|missing|overturned|forced|open|closed|unattended|recent)\s+){{0,2}}"
    rf"(?:{_PHYSICAL_NOUNS})\b|\b(?:face[- ]?down|face[- ]?up|facedown|faceup)\b",
    re.IGNORECASE,
)


def extract_frame_details(frame_text: str) -> tuple[str, ...]:
    """Extract concise observable physical details from a frame.

    This is intentionally a small phrase matcher, not a general noun or
    event parser.  It can miss unfamiliar objects and relations, but avoids
    sending every abstraction in a frame to the model.
    """
    details: list[str] = []
    for match in _DETAIL.finditer(frame_text):
        detail = " ".join(match.group(0).split()).casefold()
        if detail not in details:
            details.append(detail)
    return tuple(details)


def _ask_prompt(details: tuple[str, ...], beats_text: str) -> str:
    numbered = "\n".join(f"{index}. {detail}" for index, detail in enumerate(details, 1))
    return (
        "For each numbered physical detail, decide whether the SCENE BEATS state that exact detail.\n"
        "Answer false if the beats do not state it, EVEN IF they say something similar or related about "
        "the same object. A detail that adds position, orientation, condition, or damage the beats never "
        "mention is false.\n"
        "Return JSON only: an object with an 'attested' array of booleans in the same order.\n\n"
        f"DETAILS:\n{numbered}\n\nSCENE BEATS:\n{beats_text}"
    )


def _verdicts(reply: str, count: int) -> tuple[bool, ...]:
    try:
        payload = json.loads(reply)
        values = payload.get("attested", payload) if isinstance(payload, dict) else payload
        if isinstance(values, list):
            return tuple(
                value if isinstance(value, bool) else str(value).casefold() in {"yes", "true"}
                for value in values[:count]
            ) + (True,) * max(0, count - len(values))
    except (TypeError, ValueError, json.JSONDecodeError):
        pass
    tokens = re.findall(r"\b(?:yes|no|true|false)\b", reply.casefold())
    values = tuple(token in {"yes", "true"} for token in tokens[:count])
    return values + (True,) * max(0, count - len(values))


def unattested_frame_details(frame_text: str, beats_text: str, ask: Ask) -> tuple[str, ...]:
    """Return frame details not attested by the beats after exactly one ask."""
    details = extract_frame_details(frame_text)
    verdicts = _verdicts(ask(_ask_prompt(details, beats_text)), len(details))
    return tuple(detail for detail, attested in zip(details, verdicts, strict=True) if not attested)


def _default_ask(prompt: str) -> str:
    """Ask the configured narration Worker; configuration is read only on call."""
    import os

    url = os.getenv("CLOUDFLARE_WORKER_URL", "").strip()
    if not url:
        raise RuntimeError("CLOUDFLARE_WORKER_URL is not configured")
    from storygame.runtime.cloudflare import BROWSER_USER_AGENT

    headers = {"Content-Type": "application/json", "User-Agent": BROWSER_USER_AGENT}
    token = os.getenv("CLOUDFLARE_WORKER_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    payload = {
        "system": "You are a binary entailment checker. Follow the requested JSON format exactly.",
        "user": prompt,
        "max_tokens": 256,
        "response_format": {"type": "json_object"},
    }
    request = Request(url, data=json.dumps(payload).encode(), headers=headers, method="POST")
    with urlopen(request, timeout=float(os.getenv("CLOUDFLARE_TIMEOUT", "15"))) as response:  # noqa: S310
        body = json.loads(response.read())
    if isinstance(body, dict) and isinstance(body.get("narration"), str):
        return body["narration"]
    return json.dumps(body)


def audit_frames(root: Path, ask: Ask = _default_ask) -> list[dict[str, str]]:
    """Audit every authored scene frame with one injected model call per frame."""
    root = Path(root)
    plot = (root / "plot.md").read_text(encoding="utf-8")
    scenes = _plot_scenes(plot)
    knowledge = yaml.safe_load((root / "knowledge.yaml").read_text(encoding="utf-8")) or {}
    findings: list[dict[str, str]] = []
    for frame in knowledge.get("scene_frames", []):
        scene_id = str(frame.get("scene_id"))
        details = unattested_frame_details(str(frame.get("situation", "")), scenes.get(scene_id, ""), ask)
        for detail in details:
            findings.append(
                _finding("unattested_detail", scene_id, f"Frame detail '{detail}' is not stated in scene beats.")
            )
    return findings


LABELLED_CASES = (
    {
        "frame": "A phone is facedown on the floor.",
        "beats": "A phone lies on the floor.",
        "expected": ("facedown",),
        "unattested": True,
    },
    {
        "frame": "Blood marks the chair.",
        "beats": "The chair is overturned.",
        "expected": ("blood",),
        "unattested": True,
    },
    {
        "frame": "An open drawer holds a card.",
        "beats": "The drawer is closed and empty.",
        "expected": ("open drawer", "card"),
        "unattested": True,
    },
    {
        "frame": "A phone is undamaged on the floor.",
        "beats": "The undamaged phone remains on the floor.",
        "expected": (),
        "unattested": False,
    },
    {
        "frame": "A damaged bench holds a card.",
        "beats": "The damaged bench holds a card.",
        "expected": (),
        "unattested": False,
    },
    {
        "frame": "A dead battery is beside a laptop.",
        "beats": "The dead battery is beside a laptop.",
        "expected": (),
        "unattested": False,
    },
)


def score(ask: Ask) -> dict[str, object]:
    """Score the injected asker against the labelled closed-form cases."""
    outcomes = []
    true_positive = false_positive = false_negative = 0
    for case in LABELLED_CASES:
        actual = unattested_frame_details(case["frame"], case["beats"], ask)
        expected = tuple(case["expected"])
        actual_set, expected_set = set(actual), set(expected)
        true_positive += len(actual_set & expected_set)
        false_positive += len(actual_set - expected_set)
        false_negative += len(expected_set - actual_set)
        outcomes.append({"frame": case["frame"], "expected": expected, "actual": actual, "passed": actual == expected})
    precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 1.0
    recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 1.0
    return {"precision": precision, "recall": recall, "outcomes": outcomes}
