from __future__ import annotations

from storygame.engine.state import GameState, Item, Npc, PlayerState, Room, WorldState


def _expanded_items() -> dict[str, Item]:
    return {
        "sea_map": Item(id="sea_map", name="Sea Map", description="A worn map of old roads.", tags=("map",)),
        "bronze_key": Item(
            id="bronze_key",
            name="Bronze Gate Key",
            description="A cold bronze key for the archive gate.",
            tags=("key", "quest"),
            delta_progress=0.12,
        ),
        "moonstone": Item(
            id="moonstone",
            name="Moonstone",
            description="A pale stone etched with faint runes.",
            tags=("artifact", "quest"),
            delta_progress=0.16,
        ),
        "torch": Item(id="torch", name="Torch", description="Burns with steady fire."),
        "iron_ring": Item(id="iron_ring", name="Iron Ring", description="A small ring with two hooks."),
        "old_coin": Item(id="old_coin", name="Old Coin", description="A rusted copper coin."),
        "chalk": Item(id="chalk", name="Chalk", description="Used for route markings."),
        "ropes": Item(id="ropes", name="Ropes", description="A coil of thick rope."),
        "altar_thread": Item(id="altar_thread", name="Altar Thread", description="A red thread used for seals."),
        "herb_bundle": Item(id="herb_bundle", name="Herb Bundle", description="A scent of earth and lemon."),
        "glass_lens": Item(id="glass_lens", name="Glass Lens", description="A lens from a survey scope."),
        "salt_badge": Item(id="salt_badge", name="Salt Guild Badge", description="A weathered brass token."),
        "ink_vial": Item(id="ink_vial", name="Ink Vial", description="Half full of black ink."),
        "wax_stamp": Item(id="wax_stamp", name="Wax Stamp", description="A crest used by archivists."),
        "harbor_pass": Item(id="harbor_pass", name="Harbor Pass", description="Stamped with yesterday's date."),
        "river_reed": Item(id="river_reed", name="River Reed", description="A hollow reed cut for whistles."),
        "bell_pin": Item(id="bell_pin", name="Bell Pin", description="A steel pin from the bell rigging."),
        "charcoal": Item(id="charcoal", name="Charcoal", description="Smudges hands and maps alike."),
        "linen_wrap": Item(id="linen_wrap", name="Linen Wrap", description="Bandage cloth from the sanctuary."),
        "amber_shard": Item(
            id="amber_shard",
            name="Amber Shard",
            description="A warm shard that glints in torchlight.",
        ),
    }


def _expanded_npcs() -> dict[str, Npc]:
    return {
        "ferryman": Npc(
            id="ferryman",
            name="Harbor Ferryman",
            description="An old ferryman that knows the tide.",
            dialogue="The city breathes at dawn and midnight.",
            identity="male dockworker and river guide",
            pronouns="he/him",
        ),
        "keeper": Npc(
            id="keeper",
            name="Archive Keeper",
            description="An archivist with ink-blackened fingers.",
            dialogue="The signal is stronger when the moonstone is found.",
            identity="female archivist and keeper of sealed records",
            pronouns="she/her",
            tags=("quest",),
            delta_progress=0.12,
        ),
        "warden": Npc(
            id="warden",
            name="Tower Warden",
            description="A hard-eyed guardian in a soot-lined coat.",
            dialogue="No key can open that gate while the bell remains silent.",
            identity="male tower guardian of the inner vault",
            pronouns="he/him",
            tags=("quest",),
            delta_progress=0.12,
        ),
        "oracle": Npc(
            id="oracle",
            name="High Oracle",
            description="A robed figure with a quiet, distant gaze.",
            dialogue="At the hour the city sleeps, the answer arrives.",
            identity="female mystic and bell interpreter",
            pronouns="she/her",
            tags=("quest",),
            delta_progress=0.14,
        ),
    }


def _expanded_rooms() -> dict[str, Room]:
    return {
        "harbor": Room(
            id="harbor",
            name="Harbor Steps",
            description="Wind whistles off the water and gulls circle the dock.",
            exits={"north": "market", "east": "quay"},
            item_ids=("sea_map", "old_coin", "salt_badge"),
            npc_ids=("ferryman",),
        ),
        "quay": Room(
            id="quay",
            name="South Quay",
            description="Stacked cargo and ropes line the breakwater.",
            exits={"west": "harbor", "north": "archives"},
            item_ids=("iron_ring", "harbor_pass", "river_reed"),
        ),
        "market": Room(
            id="market",
            name="Salt Market",
            description="Bright awnings and bargaining voices fill the plaza.",
            exits={"south": "harbor", "east": "archives", "north": "museum"},
            item_ids=("bronze_key", "glass_lens", "ink_vial"),
        ),
        "museum": Room(
            id="museum",
            name="City Museum",
            description="Broken statues and cracked glass guard forgotten relics.",
            exits={"south": "market", "up": "tower_base"},
            item_ids=("chalk", "herb_bundle", "charcoal"),
        ),
        "archives": Room(
            id="archives",
            name="Royal Archives",
            description="Rows of locked cabinets stretch under soot-dark rafters.",
            exits={"west": "market", "south": "quay", "north": "inner_archive"},
            locked_exits={"north": "bronze_key"},
            item_ids=("altar_thread", "wax_stamp", "linen_wrap"),
            npc_ids=("keeper",),
        ),
        "inner_archive": Room(
            id="inner_archive",
            name="Inner Archive Vault",
            description="A narrow vault with one sealed door and one humming glyph.",
            exits={"south": "archives", "east": "tower_base"},
            item_ids=("moonstone", "amber_shard"),
            npc_ids=("warden",),
        ),
        "tower_base": Room(
            id="tower_base",
            name="Tower Base",
            description="Cold stone and a metal stairwell above.",
            exits={"west": "inner_archive", "down": "museum", "up": "tower_top"},
            item_ids=("ropes", "bell_pin"),
        ),
        "tower_top": Room(
            id="tower_top",
            name="Tower Top",
            description="Wind cuts the night beside a broken bell rope.",
            exits={"down": "tower_base", "east": "sanctuary"},
            item_ids=("torch", "amber_shard"),
            npc_ids=("oracle",),
        ),
        "sanctuary": Room(
            id="sanctuary",
            name="Harbor Sanctuary",
            description="A tiny chapel where the old bell sits silent.",
            exits={"west": "tower_top"},
            item_ids=("altar_thread", "linen_wrap"),
        ),
    }


def build_default_state(seed: int) -> GameState:
    world = WorldState(rooms=_expanded_rooms(), items=_expanded_items(), npcs=_expanded_npcs())
    player = PlayerState(location="harbor", inventory=("torch",), flags={"started": True})
    return GameState(seed=seed, player=player, world=world)


def build_tiny_state(seed: int) -> GameState:
    items = {
        "torch": Item(id="torch", name="Torch", description="A steady light."),
        "bronze_key": Item(
            id="bronze_key",
            name="Bronze Key",
            description="Fits the archive lock.",
            tags=("quest",),
            delta_progress=0.35,
        ),
        "moonstone": Item(
            id="moonstone",
            name="Moonstone",
            description="The object of your search.",
            tags=("quest",),
            delta_progress=0.35,
        ),
        "note": Item(id="note", name="Note", description="A warning from the keeper."),
    }
    npcs = {
        "keeper": Npc(
            id="keeper",
            name="Archive Keeper",
            description="Watches silently.",
            dialogue="Find the moonstone and ring the bell.",
            identity="female archivist who tracks vault access",
            pronouns="she/her",
            tags=("quest",),
            delta_progress=0.25,
        )
    }
    rooms = {
        "harbor": Room(
            id="harbor",
            name="Harbor",
            description="The docks are quiet.",
            exits={"north": "market"},
            item_ids=("torch",),
        ),
        "market": Room(
            id="market",
            name="Market",
            description="Stalls and salt barrels.",
            exits={"south": "harbor", "east": "archives"},
            item_ids=("bronze_key", "note"),
        ),
        "archives": Room(
            id="archives",
            name="Archives",
            description="Locked doors and dusty shelves.",
            exits={"west": "market", "north": "vault"},
            locked_exits={"north": "bronze_key"},
            npc_ids=("keeper",),
        ),
        "vault": Room(
            id="vault",
            name="Vault",
            description="A narrow room with a stone dais.",
            exits={"south": "archives"},
            item_ids=("moonstone",),
        ),
    }

    world = WorldState(rooms=rooms, items=items, npcs=npcs)
    player = PlayerState(location="harbor", inventory=(), flags={"started": True})
    return GameState(seed=seed, player=player, world=world, active_goal="Recover the moonstone.")
