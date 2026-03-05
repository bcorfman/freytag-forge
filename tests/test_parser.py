from storygame.engine.parser import ActionKind, parse_command


def test_parse_look_variants():
    assert parse_command("look").kind == ActionKind.LOOK
    assert parse_command("l").kind == ActionKind.LOOK


def test_parse_move_parsing():
    command = parse_command("go north")
    assert command.kind == ActionKind.MOVE
    assert command.target == "north"

    assert parse_command("east").kind == ActionKind.MOVE
    assert parse_command("walk east").target == "east"


def test_parse_take_with_spaces():
    action = parse_command("take bronze key")
    assert action.kind == ActionKind.TAKE
    assert action.target == "bronze_key"


def test_parse_talk_and_use():
    talk = parse_command("talk to oracle")
    use = parse_command("use torch on altar")
    assert talk.kind == ActionKind.TALK
    assert talk.target == "oracle"
    assert use.kind == ActionKind.USE
    assert use.target == "torch:altar"


def test_parse_inventory_and_unknown():
    assert parse_command("inventory").kind == ActionKind.INVENTORY
    assert parse_command("jump around").kind == ActionKind.UNKNOWN
