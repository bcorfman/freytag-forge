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
_CLAUSE_BOUNDARY = re.compile(r"\s*(?:[,;:]|\b(?:but|while|although|whereas)\b)\s*", re.IGNORECASE)
_CONJUNCTION = re.compile(r"\s+and\s+", re.IGNORECASE)
_ASSERTION = re.compile(
    r"\b(?:is|are|was|were|remains?|lies?|sits?|stands?|holds?|contains?|shows?|glows?|"
    r"opens?|overlooks?|marks?|bears?|bearing|stocked|hidden|threaded|located|positioned|"
    r"rests?|hangs?|leads?|runs?|extends?|surrounds?|covers?|blocks?|guards?)\b",
    re.IGNORECASE,
)
_RELATION = re.compile(
    r"\b(?:above|across|around|at|behind|beneath|beside|between|beyond|down|inside|near|"
    r"on|over|through|under|within|with)\b",
    re.IGNORECASE,
)
_INTENT = re.compile(
    r"\b(?:need(?:s|ed)?|want(?:s|ed)?|try(?:ies|ing|ied)?|must|should|could|would|will|"
    r"find out|follow|survive|judge|judging|choose|confirm|secure|reach|enter|expose|"
    r"escape|exploit|requires?|purpose|mission|reached|answered|drive|driving)\b",
    re.IGNORECASE,
)


def extract_frame_details(frame_text: str) -> tuple[str, ...]:
    """Extract concise observable physical details from a frame.

    The extractor splits sentences into shallow comma/conjunction clauses and
    keeps multi-word fragments, including state predicates, spatial relations,
    and coordinated physical noun phrases. It is intentionally not a parser:
    it can miss a physical description expressed only as an unmodified noun,
    nest clauses incorrectly, or retain a concrete action that resembles a
    state. Explicit goal and motivation language is discarded so the model is
    asked about observable details rather than intent.
    """
    details: list[str] = []
    sentences = re.split(r"(?<=[.!?])\s+", frame_text.strip())
    for sentence in sentences:
        for clause in _CLAUSE_BOUNDARY.split(sentence):
            for fragment in _CONJUNCTION.split(clause):
                detail = " ".join(fragment.strip(" \t\n\r\"'.,!?-").split()).casefold()
                detail = re.sub(r"^(?:and|or)\s+", "", detail)
                if (
                    len(detail.split()) > 1
                    and not _INTENT.search(detail)
                    and detail not in details
                ):
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
        "expected": ("a phone is facedown on the floor",),
        "unattested": True,
    },
    {
        "frame": "Blood marks the chair.",
        "beats": "The chair is overturned.",
        "expected": ("blood marks the chair",),
        "unattested": True,
    },
    {
        "frame": "An open drawer holds a card.",
        "beats": "The drawer is closed and empty.",
        "expected": ("an open drawer holds a card",),
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
