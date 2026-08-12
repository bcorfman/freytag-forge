from storygame.engine.parser import ActionKind, parse_command, parse_control_command


def test_only_slash_prefixed_controls_are_intercepted_from_player_input():
    for line in ("leave me alone", "save your breath", "take a seat", "walk me through it", "look, I tried"):
        assert parse_control_command(line).kind == ActionKind.UNKNOWN

    assert parse_control_command("/quit").kind == ActionKind.QUIT
    assert parse_control_command("/save case one").target == "case_one"
    assert parse_control_command("/load case one").target == "case_one"
    assert parse_control_command("/help").kind == ActionKind.HELP


def test_parse_look_variants():
    assert parse_command("look").kind == ActionKind.LOOK
    assert parse_command("l").kind == ActionKind.LOOK


def test_parse_empty_and_help_shortcuts():
    assert parse_command("").kind == ActionKind.HELP
    assert parse_command("h").kind == ActionKind.HELP
    assert parse_command("?").kind == ActionKind.HELP


def test_parse_named_destination_movement():
    command = parse_command("go to market lane")
    assert command.kind == ActionKind.MOVE
    assert command.target == "market_lane"

    assert parse_command("east").kind == ActionKind.UNKNOWN
    assert parse_command("n").kind == ActionKind.UNKNOWN
    assert parse_command("go north").target == "north"
    assert parse_command("climb tower").target == "tower"
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
