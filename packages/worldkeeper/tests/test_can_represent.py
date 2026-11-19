from worldkeeper import WorldSchema


def make_schema():
    return WorldSchema.from_data(
        {
            "kinds": [
                {"id": "phone", "is": ["thing"]},
                {"id": "guard", "is": ["character"]},
                {"id": "seat", "is": ["supporter"], "enterable": True},
            ],
            "entities": [],
        }
    )


def test_every_relation_has_representable_and_nonrepresentable_pairs():
    schema = make_schema()
    representable = {
        "exist": ("thing", None),
        "hold": ("thing", "character"),
        "reach": ("character", "area"),
        "hidden": ("thing", "container"),
        "seated": ("character", "container"),
        "companion": ("character", "character"),
        "axis": ("thing", None),
        "know": ("character", None),
    }
    nonrepresentable = {
        "exist": ("character", "missing"),
        "hold": ("character", "thing"),
        "reach": ("thing", "thing"),
        "hidden": ("character", "character"),
        "seated": ("character", "character"),
        "companion": ("character", "thing"),
        "axis": ("area", "missing"),
        "know": ("thing", None),
    }
    for relation, kinds in representable.items():
        assert schema.can_represent(relation, *kinds).ok
    for relation, kinds in nonrepresentable.items():
        result = schema.can_represent(relation, *kinds)
        assert not result.ok
        assert relation in result.reason or any(kind in result.reason for kind in kinds if kind is not None)


def test_unknown_relation_and_kinds_are_rejected():
    schema = make_schema()
    assert "bogus" in schema.can_represent("bogus", "thing").reason
    assert "mystery" in schema.can_represent("exist", "mystery").reason
    assert "mystery" in schema.can_represent("exist", "thing", "mystery").reason


def test_missing_object_kind_is_rejected_for_binary_relations():
    schema = make_schema()
    for relation in ("hold", "reach", "hidden", "seated", "companion"):
        result = schema.can_represent(relation, "character")
        assert not result.ok and relation in result.reason


def test_story_declared_and_enterable_kinds_follow_schema_rules():
    schema = make_schema()
    assert schema.can_represent("hold", "phone", "guard").ok
    assert schema.can_represent("companion", "guard", "character").ok
    assert schema.can_represent("seated", "character", "seat").ok


def test_can_represent_does_not_mutate_schema():
    schema = make_schema()
    kinds_before = dict(schema.kinds)
    entities_before = dict(schema.entities)

    schema.can_represent("hidden", "phone", "container")

    assert schema.kinds == kinds_before
    assert schema.entities == entities_before
