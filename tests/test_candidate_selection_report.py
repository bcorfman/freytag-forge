from bench.candidate_selection_report import compute_report


def test_compute_report_aggregates_all_runs_and_position_matches() -> None:
    data = {
        "scene_id": "1A",
        "package_path": "data/stories/continuity-initiative",
        "runs": [
            {
                "status": "ok",
                "turns": [
                    {
                        "candidates_offered": ["k_sl_1a_a_r1", "k_sl_1a_a_r2"],
                        "selected_knowledge_ids": ["k_sl_1a_a_r1"],
                    },
                    {"candidates_offered": [], "selected_knowledge_ids": []},
                    {
                        "candidates_offered": ["k_sl_1a_b_r1", "k_sl_1a_b_r2"],
                        "selected_knowledge_ids": [],
                    },
                    {"candidates_offered": [], "selected_knowledge_ids": []},
                ],
            },
            {
                "status": "failed",
                "turns": [
                    {
                        "candidates_offered": ["k_sl_1a_a_r1", "k_sl_1a_a_r2"],
                        "selected_knowledge_ids": [],
                    },
                    {"candidates_offered": [], "selected_knowledge_ids": []},
                    {
                        "candidates_offered": ["k_sl_1a_b_r1", "k_sl_1a_b_r2"],
                        "selected_knowledge_ids": ["k_sl_1a_b_r2"],
                    },
                    {"candidates_offered": [], "selected_knowledge_ids": []},
                    {
                        "candidates_offered": ["k_sl_1a_a_r1", "k_sl_1a_a_r2"],
                        "selected_knowledge_ids": ["k_sl_1a_a_r1"],
                    },
                ],
            },
        ],
    }

    assert compute_report(data) == {
        "total_runs": 2,
        "total_turns": 9,
        "overall_selection_rate": {"selected": 3, "offered": 5, "rate": 0.6},
        "turn1_position0_match_rate": {"matched": 2, "occurrences": 3, "rate": 0.6666666666666666},
        "turn3_position2_match_rate": {"matched": 1, "occurrences": 2, "rate": 0.5},
    }
