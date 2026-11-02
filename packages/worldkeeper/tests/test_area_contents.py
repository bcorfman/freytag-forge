from test_world import make


def test_visible_area_contents_lists_only_visible_direct_children():
    world = make()
    assert world.place("ada", "parlour").ok
    assert world.place("chest", "parlour").ok
    assert world.place("desk1", "parlour").ok
    assert world.place("lamp", "desk1").ok
    assert world.place("key", "parlour").ok
    assert world.place("bo", "parlour").ok
    assert world.set_status("bo", "missing").ok
    assert world.set_axis("chest", "closed").ok

    assert world.visible_area_contents("parlour") == ("ada", "chest", "desk1")
    assert world.parent("lamp") == "desk1"
    assert not world.is_visible("key")
    assert not world.is_visible("bo")
    assert not world.is_visible("chest_quills")


def test_visible_area_contents_excludes_subareas_and_empty_areas():
    world = make()

    assert world.visible_area_contents("village") == ()
    assert world.visible_area_contents("parlour") == ()


def test_visible_area_contents_returns_empty_for_unknown_area():
    world = make()

    assert world.visible_area_contents("missing") == ()
