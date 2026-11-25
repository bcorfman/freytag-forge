"""Real-story pacing link declarations."""

from storygame.story_package.default_root import default_package_root
from storygame.story_package.loader import load_story_package
from storygame.story_package.pacing_links import pacing_link_problems

EXPECTED_DECLARATIONS = {
    ("transfer_withdrawal_1c", "k_bridge_1c_infiltration"),
    ("inspection_window_2a", "k_inspection_window_missed"),
    ("inspection_nudge_2a", "k_supervisor_escorting"),
    ("inspection_recovery_2a", "k_inspection_recovery_ready"),
    ("audit_recovery_2b", "k_audit_recovery_ready"),
    ("audit_window_2b", "k_audit_window_missed"),
    ("purge_recovery_2c", "k_purge_recovery_ready"),
    ("purge_nudge_2c", "k_sl_2c_e_route_effects"),
    ("purge_window_2c", "k_purge_window_missed"),
    ("evacuation_nudge_3c", "k_evacuation_recovery_ready"),
    ("evacuation_window_3c", "k_sl_3c_h_route_effects"),
    ("evacuation_recovery_3c", "k_sl_3c_h_route_effects"),
}


def test_real_story_declares_all_pacing_links() -> None:
    package = load_story_package(default_package_root())

    assert pacing_link_problems(package) == []
    declarations = {(event.id, item) for event in package.pacing.events for item in event.delivers}
    assert declarations == EXPECTED_DECLARATIONS

    knowledge = {item.id: item for item in package.knowledge.knowledge}
    assert all(knowledge[item].earn_when is None and not knowledge[item].action_evidence for _, item in declarations)
