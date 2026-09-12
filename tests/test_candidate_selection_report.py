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
                        "model_selected_knowledge_ids": ["k_sl_1a_a_r1"],
                        "grounding_ids": ["k_sl_1a_a_r1"],
                        "model_grounding_ids": ["k_sl_1a_a_r1"],
                    },
                    {"candidates_offered": [], "selected_knowledge_ids": []},
                    {
                        "candidates_offered": ["k_sl_1a_b_r1", "k_sl_1a_b_r2"],
                        "selected_knowledge_ids": [],
                        "grounding_ids": ["k_scene_1a_entry"],
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

    report = compute_report(data)

    assert report["total_runs"] == 2
    assert report["total_turns"] == 9
    assert report["overall_selection_rate"] == {"selected": 3, "offered": 5, "rate": 0.6}
    assert report["turn1_position0_match_rate"] == {
        "matched": 2,
        "occurrences": 3,
        "rate": 0.6666666666666666,
    }
    assert report["turn3_position2_match_rate"] == {"matched": 1, "occurrences": 2, "rate": 0.5}
    assert len(report["per_turn"]) == 9
    assert report["per_turn"][0] == {
        "replicate": 1,
        "turn": 1,
        "player_input": "",
        "candidates_offered": ["k_sl_1a_a_r1", "k_sl_1a_a_r2"],
        "selected_knowledge_ids": ["k_sl_1a_a_r1"],
        "model_selected_knowledge_ids": ["k_sl_1a_a_r1"],
        "grounding_ids": ["k_sl_1a_a_r1"],
        "model_grounding_ids": ["k_sl_1a_a_r1"],
        "expected_candidate_ids": ["k_sl_1a_a_r1", "k_sl_1a_a_r2"],
        "expected_match": True,
    }
    assert report["per_turn"][2]["expected_candidate_ids"] == ["k_sl_1a_b_r1", "k_sl_1a_b_r2"]
    assert report["per_turn"][2]["expected_match"] is False
    assert report["per_turn"][2]["selected_knowledge_ids"] == []
    assert report["per_turn"][2]["grounding_ids"] == ["k_scene_1a_entry"]
    assert report["per_turn"][2]["model_grounding_ids"] == []
    assert report["per_turn"][1]["expected_candidate_ids"] == []
    assert report["per_turn"][1]["expected_match"] is None
