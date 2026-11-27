"""Produce a read-only report about pull-request review outcomes."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from statistics import median
from typing import Any
from urllib.parse import urlencode

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.review_risk import classify_paths, is_documentation_only, load_policy

API = Callable[[str], Any]
GRAPHQL_API = Callable[..., Any]
MAIN_SCAN_LIMIT = 4000
COMMITS_PER_GRAPHQL_PAGE = 100
GRAPHQL_PAGE_LIMIT = MAIN_SCAN_LIMIT // COMMITS_PER_GRAPHQL_PAGE
PRODUCTION_CONTEXT = "production-promotion"


PRODUCTION_HISTORY_QUERY = """
query($owner: String!, $name: String!, $cursor: String) {
  repository(owner: $owner, name: $name) {
    ref(qualifiedName: "refs/heads/main") {
      target {
        ... on Commit {
          history(first: 100, after: $cursor) {
            pageInfo { hasNextPage endCursor }
            nodes {
              oid
              status { context(name: "production-promotion") { state } }
            }
          }
        }
      }
    }
  }
}
"""


def gh_api(endpoint: str) -> Any:
    """Call ``gh api`` once; pagination is deliberately handled by ``paginate``."""
    result = subprocess.run(["gh", "api", endpoint], check=False, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or f"gh api {endpoint} failed")
    return json.loads(result.stdout)


def gh_graphql(owner: str, name: str, cursor: str | None = None) -> Any:
    """Call the GitHub GraphQL API, omitting the cursor variable on the first page."""
    command = [
        "gh",
        "api",
        "graphql",
        "-f",
        f"query={PRODUCTION_HISTORY_QUERY}",
        "-f",
        f"owner={owner}",
        "-f",
        f"name={name}",
    ]
    if cursor is not None:
        command.extend(["-f", f"cursor={cursor}"])
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "gh api graphql failed")
    return json.loads(result.stdout)


def _endpoint(path: str, **params: Any) -> str:
    return f"{path}?{urlencode(params)}" if params else path


def paginate(api: API, path: str, **params: Any) -> list[dict[str, Any]]:
    """Fetch every page of a GitHub list endpoint."""
    page = 1
    values: list[dict[str, Any]] = []
    while True:
        payload = api(_endpoint(path, **params, per_page=100, page=page))
        if not isinstance(payload, list):
            raise ValueError(f"expected a list from {path}")
        values.extend(payload)
        if len(payload) < 100:
            return values
        page += 1


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _hours(start: str, end: str | None) -> float | None:
    return None if end is None else round((_dt(end) - _dt(start)).total_seconds() / 3600, 2)


def _paths(files: list[dict[str, Any]]) -> list[str]:
    paths: list[str] = []
    for file in files:
        for path in (file.get("previous_filename"), file.get("filename")):
            if path and path not in paths:
                paths.append(path)
    return paths


def _body_lines(body: str) -> list[str]:
    return [line.strip() for line in re.sub(r"<!--.*?-->", "", body, flags=re.DOTALL).splitlines()]


def _revert_number(title: str, body: str) -> int | None:
    if title.startswith("Revert"):
        match = re.search(r"#(\d+)", title) or re.search(r"#(\d+)", body)
        return int(match.group(1)) if match else None
    for line in _body_lines(body):
        match = re.fullmatch(r"Reverts\s+(?:[^/#\s]+/[^/#\s]+)?#(\d+)\s*", line, re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None


def _follow_ups(body: str) -> list[int]:
    values: list[int] = []
    for line in _body_lines(body):
        match = re.fullmatch(r"Follow-up-fix-for:\s*#(\d+)\s*", line, re.IGNORECASE)
        if match and int(match.group(1)) not in values:
            values.append(int(match.group(1)))
    return values


def _is_review_after_ready(review: dict[str, Any], author: str | None, ready_at: str) -> bool:
    return (
        review.get("state") != "PENDING"
        and bool(review.get("submitted_at"))
        and (review.get("user") or {}).get("login") != author
        and _dt(review["submitted_at"]) >= _dt(ready_at)
    )


def _summary(prs: list[dict[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    groups = {
        "documentation_only": [p for p in prs if p["documentation_only"]],
        "executable": [p for p in prs if not p["documentation_only"]],
    }
    for label, selected in groups.items():
        first_review = [p["hours_to_first_review"] for p in selected if p["hours_to_first_review"] is not None]
        to_merge = [p["hours_to_merge"] for p in selected if p["hours_to_merge"] is not None]
        result[label] = {
            "count": len(selected),
            "count_with_at_least_one_review": sum(p["first_review_at"] is not None for p in selected),
            "median_hours_to_first_review": median(first_review) if first_review else None,
            "median_hours_to_merge": median(to_merge) if to_merge else None,
            "total_review_rounds": sum(p["review_rounds"] for p in selected),
            "total_changes_requested": sum(p["changes_requested"] for p in selected),
            "reverts": sum(p["is_revert"] is True for p in selected),
            "explicit_follow_up_fixes": sum(len(p["follow_up_of"]) for p in selected),
        }
    return result


def _changed_tier(api: API, repo: str, previous: str | None, failed: str, policy: dict[str, Any]) -> str:
    if not previous or previous == failed:
        return "unclassified"
    comparison = api(f"repos/{repo}/compare/{previous}...{failed}")
    files = comparison.get("files", [])
    if comparison.get("status") != "ahead" or not files:
        return "unclassified"
    paths = _paths(files)
    tier = classify_paths(paths, policy)
    return "high" if tier == "high" else ("unclassified" if len(files) >= 300 else tier)


def _production_commits(graphql_api: GRAPHQL_API, repo: str) -> tuple[list[dict[str, Any]], int, bool]:
    owner, name = repo.split("/", 1)
    commits: list[dict[str, Any]] = []
    scanned = 0
    cursor: str | None = None
    history_has_next = False
    for _ in range(GRAPHQL_PAGE_LIMIT):
        response = graphql_api(owner, name, cursor)
        if response.get("errors"):
            raise RuntimeError(f"GitHub GraphQL error: {response['errors']}")
        try:
            history = response["data"]["repository"]["ref"]["target"]["history"]
        except (KeyError, TypeError) as exc:
            raise ValueError("unexpected GitHub GraphQL history response") from exc
        page_commits = history.get("nodes") or []
        scanned += len(page_commits)
        commits.extend(
            {"sha": commit["oid"]} for commit in page_commits if (commit.get("status") or {}).get("context") is not None
        )
        history_has_next = bool((history.get("pageInfo") or {}).get("hasNextPage"))
        if not history_has_next:
            break
        cursor = (history.get("pageInfo") or {}).get("endCursor")
        if not cursor:
            raise ValueError("GitHub GraphQL history page has no cursor")
    return commits, scanned, history_has_next


def _production_failures(
    api: API,
    repo: str,
    since: datetime,
    policy: dict[str, Any],
    graphql_api: GRAPHQL_API = gh_graphql,
) -> dict[str, Any]:
    commits, scanned, history_truncated = _production_commits(graphql_api, repo)
    statuses: list[tuple[datetime, str, str, str]] = []
    for commit in commits:
        sha = commit["sha"]
        for status in paginate(api, f"repos/{repo}/commits/{sha}/statuses"):
            if status.get("context") == PRODUCTION_CONTEXT and status.get("state") in {"failure", "error"}:
                statuses.append(
                    (_dt(status["created_at"]), sha, status.get("state", ""), status.get("description", ""))
                )
            elif status.get("context") == PRODUCTION_CONTEXT and status.get("state") == "success":
                statuses.append((_dt(status["created_at"]), sha, "success", status.get("description", "")))
    statuses.sort()
    failures = [entry for entry in statuses if entry[0] >= since and entry[2] in {"failure", "error"}]
    categories: dict[str, int] = {}
    details: list[dict[str, Any]] = []
    for created, sha, state, description in failures:
        successes = [entry for entry in statuses if entry[2] == "success" and entry[0] < created]
        previous = max(successes, key=lambda entry: entry[0])[1] if successes else None
        category = _changed_tier(api, repo, previous, sha, policy)
        categories[category] = categories.get(category, 0) + 1
        details.append(
            {
                "sha": sha,
                "created_at": created.isoformat(),
                "state": state,
                "category": category,
                "description": description,
            }
        )
    return {
        "count": len(failures),
        "by_category": categories,
        "failures": details,
        "main_commits_scanned": scanned,
        "scan_bound": MAIN_SCAN_LIMIT,
        "history_truncated": history_truncated,
    }


def build_report(
    api: API,
    repo: str,
    since_days: int = 30,
    now: datetime | None = None,
    graphql_api: GRAPHQL_API = gh_graphql,
) -> dict[str, Any]:
    now = now or datetime.now(UTC)
    since = now - timedelta(days=since_days)
    policy = load_policy(Path(".github/review-policy.yml"))
    prs: list[dict[str, Any]] = []
    for pr in paginate(api, f"repos/{repo}/pulls", state="closed", base="main"):
        merged_at = pr.get("merged_at")
        if not merged_at or not since <= _dt(merged_at) <= now:
            continue
        number = pr["number"]
        timeline = paginate(api, f"repos/{repo}/issues/{number}/timeline")
        ready_events = [
            event
            for event in timeline
            if event.get("event") == "ready_for_review" and _dt(event["created_at"]) <= _dt(merged_at)
        ]
        ready_event = max(ready_events, key=lambda event: event["created_at"], default=None)
        ready_at = ready_event["created_at"] if ready_event else pr["created_at"]
        ready_source = "ready_for_review" if ready_event else "created_at"
        author = (pr.get("user") or {}).get("login")
        reviews = [
            review
            for review in paginate(api, f"repos/{repo}/pulls/{number}/reviews")
            if _is_review_after_ready(review, author, ready_at)
        ]
        first = min(reviews, key=lambda review: review["submitted_at"], default=None)
        files = paginate(api, f"repos/{repo}/pulls/{number}/files")
        head_sha = (pr.get("head") or {}).get("sha")
        fresh = None
        if head_sha:
            fresh_statuses = paginate(api, f"repos/{repo}/commits/{head_sha}/statuses")
            matching_fresh = [status for status in fresh_statuses if status.get("context") == "fresh-review"]
            newest_fresh = max(matching_fresh, key=lambda status: status["created_at"], default=None)
            fresh = newest_fresh.get("state") if newest_fresh else None
        body = pr.get("body") or ""
        revert_of = _revert_number(pr.get("title", ""), body)
        prs.append(
            {
                "number": number,
                "title": pr.get("title", ""),
                "merged_at": merged_at,
                "ready_at": ready_at,
                "ready_at_source": ready_source,
                "first_review_at": first["submitted_at"] if first else None,
                "hours_to_first_review": _hours(ready_at, first["submitted_at"] if first else None),
                "hours_to_merge": _hours(ready_at, merged_at),
                "review_rounds": len({review.get("commit_id") for review in reviews if review.get("commit_id")}),
                "changes_requested": sum(review.get("state") == "CHANGES_REQUESTED" for review in reviews),
                "fresh_review": fresh,
                "documentation_only": is_documentation_only(_paths(files)),
                "risk_tier": classify_paths(_paths(files), policy),
                "changed_files": _paths(files),
                "is_revert": pr.get("title", "").startswith("Revert") or revert_of is not None,
                "revert_of": revert_of,
                "follow_up_of": _follow_ups(body),
            }
        )
    return {
        "repo": repo,
        "window": {"since": since.isoformat(), "until": now.isoformat(), "since_days": since_days},
        "pull_requests": prs,
        "summary": _summary(prs),
        "production_failures": _production_failures(api, repo, since, policy, graphql_api),
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        f"# Review outcomes: {report['repo']}",
        "",
        f"Window: {report['window']['since']} to {report['window']['until']}",
        "",
        "## Summary",
        "",
    ]
    for label, values in report["summary"].items():
        lines.append(f"### {label.replace('_', ' ').title()}")
        lines.extend(f"- {key.replace('_', ' ')}: {value}" for key, value in values.items())
        lines.append("")
    failures = report["production_failures"]
    lines += [
        "## Production promotion failures",
        "",
        f"- Count: {failures['count']}",
        f"- By category: {failures['by_category']}",
        f"- Main commits scanned: {failures['main_commits_scanned']} (bounded at {failures['scan_bound']})",
        "",
        "## What this does not measure",
        "",
        "- It covers only failures of the promotion workflow, not incidents after a successful deploy.",
        "- Elapsed review time is not active human review time, which is not measured.",
        "- Bug-introducing commits are not inferred; an inference would be an uncertain label.",
        "- The repository has a single maintainer, so reviews by the author are excluded and fresh-session reviews "
        "show up only as the fresh-review status.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY"))
    parser.add_argument("--since-days", type=int, default=30)
    parser.add_argument("--out-dir", default="artifacts/review-outcomes")
    args = parser.parse_args()
    repo = args.repo
    if not repo:
        repo = subprocess.run(
            ["gh", "repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    report = build_report(gh_api, repo, args.since_days)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (out_dir / "report.md").write_text(render_markdown(report), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
