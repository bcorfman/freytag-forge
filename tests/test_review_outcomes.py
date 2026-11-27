from datetime import UTC, datetime

from scripts.review_outcomes import _changed_tier, _follow_ups, _revert_number, _summary, build_report


def test_parsing_reverts_and_follow_ups() -> None:
    assert _revert_number("Revert #12", "") == 12
    assert _revert_number("Fix", "Reverts owner/repo#8\nFollow-up-fix-for: #4") == 8
    assert _follow_ups("<!-- Follow-up-fix-for: #9 -->\nFollow-up-fix-for: #4\nFollow-up-fix-for: #4") == [4]


def test_summary_empty_medians_and_split() -> None:
    assert _summary([])["documentation_only"]["median_hours_to_first_review"] is None
    prs = [
        {
            "documentation_only": True,
            "first_review_at": None,
            "hours_to_first_review": None,
            "hours_to_merge": 2,
            "review_rounds": 0,
            "changes_requested": 0,
            "is_revert": False,
            "follow_up_of": [],
        },
        {
            "documentation_only": False,
            "first_review_at": "2026-01-01T01:00:00Z",
            "hours_to_first_review": 1,
            "hours_to_merge": 3,
            "review_rounds": 2,
            "changes_requested": 1,
            "is_revert": True,
            "follow_up_of": [2],
        },
    ]
    summary = _summary(prs)
    assert summary["documentation_only"]["count"] == 1
    assert summary["documentation_only"]["reverts"] == 0
    assert summary["executable"]["median_hours_to_first_review"] == 1


def test_changed_tier_unclassifies_non_ahead_comparison() -> None:
    def fake_api(endpoint: str):
        assert endpoint == "repos/o/r/compare/previous...failed"
        return {"status": "behind", "files": [{"filename": "worker/app.py"}]}

    assert _changed_tier(fake_api, "o/r", "previous", "failed", {}) == "unclassified"


def test_build_report_metrics_and_failure_then_success() -> None:
    now = datetime(2026, 1, 31, tzinfo=UTC)
    data = {
        "pulls": [
            {
                "number": 7,
                "created_at": "2026-01-01T00:00:00Z",
                "merged_at": "2026-01-30T12:00:00Z",
                "title": "Docs",
                "body": "Follow-up-fix-for: #3",
                "user": {"login": "owner"},
                "head": {"sha": "head7"},
            }
        ],
        "timeline": [{"event": "ready_for_review", "created_at": "2026-01-29T00:00:00Z"}],
        "reviews": [
            {
                "state": "APPROVED",
                "submitted_at": "2026-01-29T02:00:00Z",
                "user": {"login": "reviewer"},
                "commit_id": "c1",
            },
            {
                "state": "CHANGES_REQUESTED",
                "submitted_at": "2026-01-29T03:00:00Z",
                "user": {"login": "reviewer"},
                "commit_id": "c2",
            },
        ],
        "files": [{"filename": "docs/guide.md", "previous_filename": "docs/old.md"}],
        "head_statuses": [
            {"context": "fresh-review", "state": "success", "created_at": "2026-01-29T04:00:00Z"},
            {"context": "fresh-review", "state": "failure", "created_at": "2026-01-29T01:00:00Z"},
        ],
        "main_commits": [{"sha": "failed"}, {"sha": "good"}],
        "failed_statuses": [
            {"context": "production-promotion", "state": "failure", "created_at": "2026-01-20T00:00:00Z"}
        ],
        "good_statuses": [
            {"context": "production-promotion", "state": "success", "created_at": "2026-01-19T00:00:00Z"}
        ],
        "compare": {"status": "ahead", "files": [{"filename": "worker/app.py"}]},
    }

    graphql_calls: list[str | None] = []

    def fake_graphql(owner: str, name: str, cursor: str | None = None):
        assert (owner, name) == ("o", "r")
        graphql_calls.append(cursor)
        return {
            "data": {
                "repository": {
                    "ref": {
                        "target": {
                            "history": {
                                "pageInfo": {"hasNextPage": False, "endCursor": None},
                                "nodes": [
                                    {"oid": "failed", "status": {"context": {"state": "failure"}}},
                                    {"oid": "good", "status": {"context": {"state": "success"}}},
                                ],
                            }
                        }
                    }
                }
            }
        }

    def fake_api(endpoint: str):
        if endpoint.startswith("repos/o/r/pulls?"):
            return data["pulls"]
        if endpoint == "repos/o/r/issues/7/timeline?per_page=100&page=1":
            return data["timeline"]
        if endpoint == "repos/o/r/pulls/7/reviews?per_page=100&page=1":
            return data["reviews"]
        if endpoint == "repos/o/r/pulls/7/files?per_page=100&page=1":
            return data["files"]
        if endpoint == "repos/o/r/commits/head7/statuses?per_page=100&page=1":
            return data["head_statuses"]
        if endpoint.startswith("repos/o/r/commits?sha=main"):
            return data["main_commits"]
        if endpoint == "repos/o/r/commits/failed/statuses?per_page=100&page=1":
            return data["failed_statuses"]
        if endpoint == "repos/o/r/commits/good/statuses?per_page=100&page=1":
            return data["good_statuses"]
        if endpoint == "repos/o/r/compare/good...failed":
            return data["compare"]
        raise AssertionError(endpoint)

    report = build_report(fake_api, "o/r", 30, now, fake_graphql)
    pr = report["pull_requests"][0]
    assert pr["hours_to_first_review"] == 2
    assert pr["hours_to_merge"] == 36
    assert pr["review_rounds"] == 2
    assert pr["documentation_only"] is True
    assert pr["changed_files"] == ["docs/old.md", "docs/guide.md"]
    assert pr["follow_up_of"] == [3]
    assert pr["fresh_review"] == "success"
    assert report["production_failures"]["by_category"] == {"high": 1}
    assert report["production_failures"]["main_commits_scanned"] == 2
    assert graphql_calls == [None]
