"""Phase 6 guards for the one-runtime hosted-product cutover."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_main_contains_no_v1_runtime_or_package_execution_path() -> None:
    retired_paths = (
        "storygame/engine",
        "storygame/llm",
        "storygame/plot",
        "storygame/cli.py",
        "storygame/evaluation.py",
        "storygame/memory.py",
        "storygame/story_canon.py",
        "storygame/story_data_audit.py",
        "storygame/story_packages.py",
        "storygame/persistence/savegame_sqlite.py",
        "storygame/persistence/story_state.py",
        "data/npc_voice_cards.yaml",
        "data/opening_setup.yaml",
        "data/plot_curves.yaml",
        "data/predicates",
        "data/rules",
        "data/runtime_quality_regressions.yaml",
        "data/story_packages.yaml",
    )

    present: list[str] = []
    for path in retired_paths:
        target = ROOT / path
        if target.is_dir():
            present.extend(str(source.relative_to(ROOT)) for source in target.rglob("*.py"))
        elif target.exists():
            present.append(path)
    assert present == []


def test_hosted_product_configuration_exposes_only_v2_entrypoints() -> None:
    railway = (ROOT / "railway.toml").read_text(encoding="utf-8")
    workflow = (ROOT / ".github/workflows/test.yml").read_text(encoding="utf-8")

    assert "storygame.web_demo:app" in railway
    assert not (ROOT / "main.py").exists()
    assert "test_evaluation.py" not in workflow
    assert "test_web_api.py" not in workflow
