"""Operator command for explicit, hash-bound candidate approval."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from storygame.authoring.candidate_review import CandidateReview, promote_candidate, required_review_checklist
from storygame.authoring.causal_profiles import CausalProfileRegistry
from storygame.authoring.compiler import CompilationError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="storygame-blueprint-review")
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--notes", required=True)
    parser.add_argument("--approve", action="store_true", help="record the reviewer's explicit approval")
    parser.add_argument("--check", action="append", choices=required_review_checklist(), default=[])
    parser.add_argument("--profile-root", type=Path, default=Path("data/genre_profiles"))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        review = CandidateReview(
            reviewer=args.reviewer,
            approved=args.approve,
            checklist=tuple(args.check),
            notes=args.notes,
        )
        artifact = promote_candidate(
            args.candidate, args.output, review, CausalProfileRegistry.from_directory(args.profile_root)
        )
    except (CompilationError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc
    print(
        json.dumps(
            {"reviewed_artifact": str(args.output), "candidate_sha256": artifact.candidate_sha256}, sort_keys=True
        )
    )
    return 0
