"""Replay the saved Scene 3C A11 prompt with one knowledge-line subtraction."""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import sys
from pathlib import Path
from urllib.request import Request, urlopen

LINE = "- Exposure and escape are both immediate under the collapsing operation."
MAX_CALLS = 24


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=Path, required=True)
    parser.add_argument("--samples", type=int, required=True)
    parser.add_argument("--dry", action="store_true")
    parser.add_argument("--confirm", action="store_true")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.samples < 1:
        parser.error("samples must be at least 1")
    if args.samples * 2 > MAX_CALLS:
        parser.error(f"refusing more than {MAX_CALLS} calls")
    if not args.dry and not args.confirm:
        parser.error("live replay requires --confirm")
    return args


def _rows(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        raise ValueError("rows file must contain a list")
    return [row for row in value if isinstance(row, dict)]


def _resolve_rows_path(path: Path) -> Path:
    if path.is_file():
        return path
    if path.is_absolute():
        try:
            path = path.relative_to(Path.cwd())
        except ValueError:
            return path
    git_file = Path.cwd().joinpath(".git")
    if not git_file.is_file():
        git_file = Path(__file__).resolve().parents[3].joinpath(".git")
    try:
        marker = git_file.read_text(encoding="utf-8").strip()
        if marker.startswith("gitdir: "):
            gitdir = Path(marker.removeprefix("gitdir: ").strip())
            if not gitdir.is_absolute():
                gitdir = git_file.parent.joinpath(gitdir)
            main_checkout = gitdir.parents[2]
            shared_path = main_checkout.joinpath(path)
            if shared_path.is_file():
                return shared_path
    except (OSError, IndexError, ValueError):
        pass
    return path


def saved_prompt(path: Path) -> tuple[dict[str, str], str, int]:
    path = _resolve_rows_path(path)
    rows = _rows(json.loads(path.read_text(encoding="utf-8")))
    row = next(row for row in rows if row.get("arm") == "item-facts")
    turns = row.get("turns")
    if not isinstance(turns, list):
        raise ValueError("item-facts row has no turns")
    turn = next(turn for turn in turns if isinstance(turn, dict) and turn.get("scene_turn") == 11)
    capture = turn.get("world_capture")
    prompt = capture["after"]["narration_prompt"] if isinstance(capture, dict) else None
    if (
        not isinstance(prompt, dict)
        or not isinstance(prompt.get("system"), str)
        or not isinstance(prompt.get("user"), str)
    ):
        raise ValueError("scene turn 11 has no saved narration prompt")
    return {"system": prompt["system"], "user": prompt["user"]}, str(row.get("row_id", "unknown")), 11


def build_arms(prompt: dict[str, str]) -> dict[str, dict[str, str]]:
    control = prompt["user"]
    assert control.count(LINE + "\n") == 1, "entry line must occur exactly once with its newline"
    before, after = control.split(LINE + "\n", 1)
    subtraction = before + after
    assert subtraction != control
    assert before + LINE + "\n" + after == control
    return {
        "control": {"system": prompt["system"], "user": control},
        "subtraction": {"system": prompt["system"], "user": subtraction},
    }


def _write_texts(out: Path, arms: dict[str, dict[str, str]]) -> None:
    out.mkdir(parents=True, exist_ok=True)
    out.joinpath("control.user.txt").write_text(arms["control"]["user"], encoding="utf-8")
    out.joinpath("subtraction.user.txt").write_text(arms["subtraction"]["user"], encoding="utf-8")
    out.joinpath("system.txt").write_text(arms["control"]["system"], encoding="utf-8")
    diff = difflib.unified_diff(
        arms["control"]["user"].splitlines(keepends=True),
        arms["subtraction"]["user"].splitlines(keepends=True),
        fromfile="control.user.txt",
        tofile="subtraction.user.txt",
    )
    out.joinpath("prompt.diff").write_text("".join(diff), encoding="utf-8")
    out.joinpath("sha256.json").write_text(
        json.dumps(
            {
                name: hashlib.sha256(value.encode("utf-8")).hexdigest()
                for name, value in {
                    "control.user.txt": arms["control"]["user"],
                    "subtraction.user.txt": arms["subtraction"]["user"],
                    "system.txt": arms["control"]["system"],
                }.items()
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def prose_from_text(text: str) -> str:
    try:
        return " ".join(segment["text"] for segment in json.loads(text)["segments"])
    except Exception:  # noqa: BLE001
        return text


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    prompt, row_id, scene_turn = saved_prompt(args.rows)
    arms = build_arms(prompt)
    _write_texts(args.out, arms)
    plan = {
        "arms": ["control", "subtraction"],
        "sample_count": args.samples,
        "call_count": args.samples * 2,
        "call_cap": MAX_CALLS,
        "source_row": row_id,
        "source_turn": scene_turn,
    }
    args.out.joinpath("plan.json").write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    print(f"source: {row_id}, scene_turn: {scene_turn}; arms: control, subtraction; calls: {args.samples * 2}")
    if args.dry:
        return

    sys.path.insert(0, ".")
    from storygame.runtime.cloudflare import BROWSER_USER_AGENT  # noqa: PLC0415

    url = os.environ["CLOUDFLARE_WORKER_URL"]
    token = os.environ.get("CLOUDFLARE_WORKER_TOKEN", "")
    rows_path = args.out.joinpath("rows.json")
    replies: list[dict[str, object]] = []
    for sample in range(args.samples):
        for arm in ("control", "subtraction"):
            payload = {**arms[arm], "max_tokens": 1024, "response_format": {"type": "json_object"}}
            headers = {"Content-Type": "application/json", "User-Agent": BROWSER_USER_AGENT}
            if token:
                headers["Authorization"] = f"Bearer {token}"
            record: dict[str, object] = {"sample": sample, "arm": arm, "text": None, "prose": None, "error": None}
            try:
                request = Request(url, data=json.dumps(payload).encode(), headers=headers, method="POST")
                with urlopen(request, timeout=60) as response:  # noqa: S310
                    body = json.loads(response.read())
                text = body.get("narration") if isinstance(body, dict) else None
                record["text"] = text if isinstance(text, str) else json.dumps(body)
                record["prose"] = prose_from_text(str(record["text"]))
            except Exception as error:  # noqa: BLE001
                record["error"] = repr(error)
            replies.append(record)
            rows_path.write_text(json.dumps(replies, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
