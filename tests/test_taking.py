from dataclasses import dataclass

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


class Result:
    def __init__(self, ok=True, reason="blocked"):
        self.ok = ok
        self.reason = reason


class World:
    def __init__(self, items, parents, areas, fixed=(), vehicles=()):
        self.items = items
        self.parents = dict(parents)
        self.areas = dict(areas)
        self.fixed = set(fixed)
        self.vehicles = set(vehicles)
        self.schema = self

    def is_fixed(self, item_id):
        return item_id in self.fixed

    def is_visible(self, _item_id):
        return True

    def holder(self, item_id):
        parent = self.parents.get(item_id)
        return parent if parent == "kristin" else None

    def area(self, item_id):
        return self.areas.get(item_id)

    def names(self, item_id):
        item = next(item for item in self.items if item.id == item_id)
        return (item.name, *item.aliases)

    def name(self, item_id):
        if item_id == "kristin":
            return "Kristin"
        return {
            "park_bench": "park bench",
            "park": "park",
            "other_area": "other area",
        }.get(item_id, next((item.name for item in self.items if item.id == item_id), item_id))

    def parent(self, item_id):
        return self.parents.get(item_id)

    def is_a(self, item_id, kind):
        if kind == "vehicle":
            return item_id in self.vehicles
        return kind == "area" and item_id in {"park", "other_area"}

    def move(self, item_id, parent):
        self.parents[item_id] = parent
        return Result()


def package(items):
    class WorldPackage:
        npcs = [NPC("kristin", "Kristin")]
        protagonist_id = "kristin"

    WorldPackage.items = items
    return type("Package", (), {"world": WorldPackage, "protagonist_id": "kristin"})()


def make_world(items, parents=None, areas=None, fixed=(), vehicles=()):
    parents = parents or {item.id: "park_bench" for item in items}
    areas = areas or {"kristin": "park", **{item.id: "park" for item in items}}
    return World(items, parents, areas, fixed, vehicles)


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

    assert world.parents["truck"] == "park_bench"
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
