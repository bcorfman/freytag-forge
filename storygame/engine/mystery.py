from __future__ import annotations

from storygame.engine.state import GameState, Item, Npc, Room

ACTIONABLE_ITEM_KINDS = {"tool", "clue", "evidence"}


def is_actionable_item(item: Item) -> bool:
    if "quest" in item.tags:
        return True
    return item.kind in ACTIONABLE_ITEM_KINDS


def room_item_groups(state: GameState, room: Room) -> tuple[tuple[str, ...], int]:
    actionable: list[str] = []
    junk_count = 0
    for item_id in room.item_ids:
        item = state.world.items[item_id]
        if is_actionable_item(item):
            actionable.append(item_id)
        else:
            junk_count += 1
    return tuple(actionable), junk_count


def filtered_inventory(state: GameState) -> tuple[str, ...]:
    inventory: list[str] = []
    for item_id in state.player.inventory:
        item = state.world.items.get(item_id)
        if item is None:
            continue
        if is_actionable_item(item):
            inventory.append(item_id)
    return tuple(inventory)


def take_item_message(item: Item) -> str:
    if item.kind == "evidence" and item.proves:
        return f"Evidence secured: {item.name}. It proves {item.proves}."
    if item.kind == "clue" and item.clue_text:
        return f"Clue noted: {item.clue_text}"
    if item.kind == "tool":
        return f"Tool acquired: {item.name}."
    return "take_success"


def npc_talk_message(state: GameState, npc: Npc, first_talk: bool) -> str:
    has_key = "bronze_key" in state.player.inventory
    has_map = "sea_map" in state.player.inventory
    has_lens = "glass_lens" in state.player.inventory
    has_moonstone = "moonstone" in state.player.inventory
    talked_keeper = state.player.flags.get("talked_keeper", False)

    if npc.id == "ferryman":
        if has_map and has_lens:
            return "Rumor from dock crews: forged tones are loudest near the sanctuary stair. Use your map marks there."
        return (
            "Rumor from dock crews: the emergency pattern sounded wrong before dawn. Someone wanted the streets empty."
        )

    if npc.id == "keeper":
        if not has_key:
            return (
                "Archive record: the north gate key was signed out to the salt market lockbox. "
                "Take the bronze key and open the north gate."
            )
        if not has_moonstone:
            return (
                "Archive record: harbor levy ledgers, emergency signal codebook, and conviction docket were edited "
                "during the false alarm window. Recover the moonstone from the inner vault and compare seal residue."
            )
        return (
            "Archive record cross-check: the altered harbor levy ledgers and conviction docket share wax from the "
            "Port Chancellor's seal. Bring that evidence to the sanctuary relay."
        )

    if npc.id == "warden":
        if not has_map or not has_lens:
            return (
                "Maintenance record: the bell frame is shattered; no one could ring it. "
                "Track the relay path before confronting the relay chamber."
            )
        return (
            "Maintenance record: brace the frame with rope and bell pin at the tower top, "
            "then align the moonstone in the sanctuary."
        )

    if npc.id == "oracle":
        if not talked_keeper:
            return "Witness account: names without records are only rumors. Verify the ledgers first in the archives."
        if not has_moonstone:
            return (
                "Witness account: the hidden relay answers only to moonstone resonance. "
                "Retrieve it from the inner vault."
            )
        return (
            "Witness account: once the relay is exposed, publish the codebook and conviction docket together "
            "or the cover-up survives."
        )

    if first_talk:
        return npc.dialogue
    return f"{npc.knowledge_source.title()} source offers nothing new."


def caseboard_lines(state: GameState) -> tuple[str, ...]:
    known_facts = [
        "False emergency tones cleared the harbor before dawn.",
        "The physical bell is broken; a hidden relay produced the signal.",
    ]
    if "talked_keeper" in state.player.flags:
        known_facts.append("Archive records were altered during the alarm window.")
    if "moonstone" in state.player.inventory:
        known_facts.append("Moonstone resonance can expose the sanctuary relay.")
    if state.player.flags.get("transmitter_exposed", False):
        known_facts.append("The hidden transmitter is exposed and tied to seal tampering.")

    open_questions = [
        "Who authorized the false alarm pattern?",
        "Who altered the harbor levy and conviction records?",
    ]
    if "talked_keeper" in state.player.flags:
        open_questions[1] = "Which official chain links altered ledgers to the Port Chancellor?"

    leads: list[str] = []
    location = state.player.location
    if "bronze_key" not in state.player.inventory:
        leads.append("Retrieve bronze key from the market lockbox.")
    elif location == "archives" and "moonstone" not in state.player.inventory:
        leads.append("Unlock the north gate and search the inner archive vault.")

    if "sea_map" not in state.player.inventory:
        leads.append("Collect the sea map at the harbor.")
    if "glass_lens" not in state.player.inventory:
        leads.append("Collect the glass lens in the market.")
    if state.player.flags.get("relay_route_confirmed", False) and not state.player.flags.get("frame_braced", False):
        leads.append("Brace the tower frame with rope and bell pin.")
    if "moonstone" in state.player.inventory and not state.player.flags.get("transmitter_exposed", False):
        leads.append("Use moonstone in the sanctuary to expose the relay.")

    if not leads:
        leads.append("Correlate ledger evidence with signal codebook and publish the chain.")

    return (
        "Caseboard:",
        "Known facts: " + " | ".join(known_facts[:3]),
        "Open questions: " + " | ".join(open_questions[:2]),
        "Active leads: " + " | ".join(leads[:3]),
    )
