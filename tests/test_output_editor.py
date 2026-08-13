from storygame.llm.output_editor import PassthroughOutputEditor, build_output_editor


def test_output_editor_preserves_validated_prose() -> None:
    lines = ["The room holds its breath."]
    editor = build_output_editor()
    assert isinstance(editor, PassthroughOutputEditor)
    assert editor.review_opening(lines, "Find a lead.") == lines
    assert editor.review_turn(lines, "Find a lead.", 1) == lines
