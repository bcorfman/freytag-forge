from storygame.engine.parser import ActionKind, parse_command


def test_parse_look_variants():
    assert parse_command("look").kind == ActionKind.LOOK
    assert parse_command("l").kind == ActionKind.LOOK


def test_parse_empty_and_help_shortcuts():
    assert parse_command("").kind == ActionKind.HELP
    assert parse_command("h").kind == ActionKind.HELP
    assert parse_command("?").kind == ActionKind.HELP


def test_parse_move_parsing():
    command = parse_command("go north")
    assert command.kind == ActionKind.MOVE
    assert command.target == "north"

    assert parse_command("east").kind == ActionKind.MOVE
    assert parse_command("walk east").target == "east"
    assert parse_command("n").target == "north"
    assert parse_command("S").target == "south"
    assert parse_command("E").target == "east"
    assert parse_command("w").target == "west"
    assert parse_command("u").target == "up"
    assert parse_command("D").target == "down"
    assert parse_command("go").kind == ActionKind.UNKNOWN


def test_parse_shortcuts():
    assert parse_command("i").kind == ActionKind.INVENTORY
    assert parse_command("l").kind == ActionKind.LOOK


def test_parse_take_with_spaces():
    action = parse_command("take route key")
    assert action.kind == ActionKind.TAKE
    assert action.target == "route_key"


def test_parse_take_pick_up_aliases():
    action = parse_command("pick up old coin")
    assert action.kind == ActionKind.TAKE
    assert action.target == "old_coin"


def test_parse_take_strips_articles_and_trailing_compound_phrase():
    action = parse_command("pick up the ledger page and read it")
    assert action.kind == ActionKind.TAKE
    assert action.target == "ledger_page"


def test_parse_talk_and_use():
    talk = parse_command("talk to oracle")
    speak = parse_command("speak to oracle")
    speak_to_alias = parse_command("speak_to oracle")
    use = parse_command("use torch on altar")
    assert talk.kind == ActionKind.TALK
    assert talk.target == "oracle"
    assert speak.target == "oracle"
    assert speak_to_alias.target == "oracle"
    assert use.kind == ActionKind.USE
    assert use.target == "torch:altar"


def test_parse_inventory_and_unknown():
    assert parse_command("inventory").kind == ActionKind.INVENTORY
    assert parse_command("jump around").kind == ActionKind.UNKNOWN


def test_parse_save_and_load_commands():
    save_action = parse_command("save 1")
    load_action = parse_command("load autosave")

    assert save_action.kind == ActionKind.SAVE
    assert save_action.target == "1"
    assert load_action.kind == ActionKind.LOAD
    assert load_action.target == "autosave"
