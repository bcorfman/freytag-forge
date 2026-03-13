from random import Random

from storygame.engine.simulation import run_command_sequence
from storygame.engine.world import build_default_state


def run_script(seed: int, commands: list[str]):
    rng = Random(seed)
    state = build_default_state(seed=seed)
    final_state = run_command_sequence(state, commands, rng)
    return final_state.replay_signature(), final_state


def test_same_seed_replays_same_state_and_log():
    commands = [
        "look",
        "north",
        "look",
        "inventory",
        "look",
        "north",
        "look",
    ]

    sig_one, state_one = run_script(123, commands)
    sig_two, state_two = run_script(123, commands)
    sig_three, _state_three = run_script(321, commands)

    assert sig_one == sig_two
    assert state_one.turn_index == state_two.turn_index
    assert state_one.progress == state_two.progress
    assert state_one.event_log != ()
    assert state_one.replay_signature() == sig_one
    assert sig_one != sig_three
