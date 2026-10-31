from dataclasses import dataclass

from worldkeeper import MemoryBackend, World, WorldSchema

from storygame.runtime.taking import take_before_put


@dataclass
class Item:
    id: str
    name: str
    aliases: tuple[str, ...] = ()
    fixed: bool | None = None
    take_text: str | None = None


@dataclass
class NPC:
    id: str
    name: str
    aliases: tuple[str, ...] = ()


def package(items):
    class WorldPackage:
        npcs = [NPC("kristin", "Kristin")]
        protagonist_id = "kristin"

    WorldPackage.items = items
    return type("Package", (), {"world": WorldPackage, "protagonist_id": "kristin"})()


def make_world(items, parents=None, areas=None, fixed=(), vehicles=()):
    parents = parents or {item.id: "park_bench" for item in items}
    areas = areas or {"kristin": "park", **{item.id: "park" for item in items}}
    item_ids = {item.id for item in items}
    area_ids = set(areas.values())
    area_refs = {area_id: area_id if area_id not in item_ids else f"{area_id}_location" for area_id in area_ids}
    helper_ids = {parent_id for parent_id in parents.values() if parent_id not in item_ids | area_ids | {"kristin"}}
    helper_names = {"park_bench": "park bench", "other_area": "other area"}
    entities = [{"id": area_refs[area_id], "name": area_id, "kind": "area"} for area_id in sorted(area_ids)]
    entities.append({"id": "kristin", "name": "Kristin", "kind": "character"})
    entities.extend(
        {"id": helper_id, "name": helper_names.get(helper_id, helper_id), "kind": "supporter"}
        for helper_id in sorted(helper_ids)
    )
    for item in items:
        entity = {
            "id": item.id,
            "name": item.name,
            "kind": "vehicle" if item.id in vehicles else "thing",
            "aliases": list(item.aliases),
        }
        if item.fixed is not None or item.id in fixed:
            entity["fixed"] = item.fixed is True or item.id in fixed
        entities.append(entity)

    world = World(WorldSchema.from_data({"entities": entities}), MemoryBackend())
    assert world.seed().ok
    assert world.move("kristin", area_refs[areas["kristin"]]).ok
    for helper_id in sorted(helper_ids):
        helper_area = next(
            area_refs[areas[item_id]] for item_id in item_ids if parents.get(item_id) == helper_id and item_id in areas
        )
        assert world.place(helper_id, helper_area).ok
    for item in items:
        parent_id = area_refs.get(parents[item.id], parents[item.id])
        assert world.place(item.id, parent_id).ok
    return world


def test_takes_named_photograph_and_formats_command():
    item = Item("photo", "Michelle's photograph")
    world = make_world([item])
    result = take_before_put(world, package([item]), "Put Michelle's photograph in my pocket.", lambda *_: True)
    assert result.steps == ("Kristin picked up Michelle's photograph from the park bench.",)
    assert result.command == (
        "Kristin picked up Michelle's photograph from the park bench. Put Michelle's photograph in my pocket."
    )
    assert world.holder("photo") == "kristin"


def test_question_answers_and_candidate_filters():
    photo = Item("photo", "photograph")
    held = Item("held", "held thing")
    fixed = Item("bench", "park bench")
    other = Item("other", "other thing")
    world = make_world(
        [photo, held, fixed, other],
        {"photo": "park_bench", "held": "kristin", "bench": "park", "other": "other_area"},
        {"kristin": "park", "photo": "park", "held": "park", "bench": "park", "other": "other"},
        fixed=("bench",),
    )
    seen = []
    result = take_before_put(
        world,
        package([photo, held, fixed, other]),
        "Put the photograph in my pocket.",
        lambda *args: seen.append(args) or False,
    )
    assert result.asked is True and result.steps == () and seen == [("Put the photograph in my pocket.", "photograph")]
    assert (
        take_before_put(
            world, package([photo]), "Look at the bench.", lambda *_: (_ for _ in ()).throw(AssertionError())
        ).asked
        is False
    )


def test_take_before_put_never_takes_a_vehicle():
    truck = Item("truck", "Kristin's truck")
    token = Item("token", "Transit token")
    world = make_world([truck, token], vehicles=("truck",))
    asked_names = []

    result = take_before_put(
        world,
        package([truck, token]),
        "Put the transit token in my truck.",
        lambda _command, name: asked_names.append(name) or True,
    )

    assert world.parent("truck") == "park_bench"
    assert all("truck" not in step.lower() for step in result.steps)
    assert "Kristin's truck" not in asked_names


def test_no_answer_and_article_area_and_authored_text():
    token = Item("token", "Transit token")
    sequence = Item("sequence", "handwritten number sequence", aliases=("number sequence",))
    laptop = Item("laptop", "Kristin's laptop", take_text="Kristin picked up her laptop.")
    world = make_world([token, sequence, laptop], {"token": "park_bench", "sequence": "park", "laptop": "park_bench"})
    result = take_before_put(
        world,
        package([token, sequence, laptop]),
        "Put the transit token and number sequence and laptop in my pocket.",
        lambda _command, name: None if name == "Transit token" else True,
    )
    assert result.issues == ("taking question unanswered for 'Transit token'",)
    assert result.steps == ("Kristin picked up her laptop.", "Kristin picked up the handwritten number sequence.")
