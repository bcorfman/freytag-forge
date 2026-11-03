"""Embellishments touch the real backend only to commit, and clone it once per batch."""

from typing import ClassVar

from test_incidental import make_policy, make_world, one_prop

from worldkeeper import MemoryBackend, TraitProposal, World


class SpyBackend(MemoryBackend):
    clones = 0
    subjects: ClassVar[list[str]] = []

    def assert_fact(self, fact):
        type(self).subjects.append(fact.subject)
        super().assert_fact(fact)

    def clone(self):
        type(self).clones += 1
        copy = MemoryBackend()
        copy._facts = set(self._facts)
        return copy


def spied_world():
    world = make_world()
    spy = SpyBackend()
    for fact in world.backend.matching_all():
        MemoryBackend.assert_fact(spy, fact)
    SpyBackend.clones, SpyBackend.subjects = 0, []
    return World(world.schema, spy)


def test_check_clones_the_backend_exactly_once():
    world, policy = spied_world(), make_policy()
    traits = (TraitProposal("tin whistle", "color", "red"), TraitProposal("cup", "color", "blue"))
    assert world.check_embellishments(policy, "kitchen", one_prop("tin whistle", "table"), traits).ok
    assert SpyBackend.clones == 1


def test_apply_clones_once_and_never_writes_placeholder_facts():
    world, policy = spied_world(), make_policy()
    traits = (TraitProposal("tin whistle", "color", "red"), TraitProposal("cup", "color", "blue"))
    result = world.apply_embellishments(policy, "kitchen", one_prop("tin whistle", "table"), traits)
    assert result.ok
    assert SpyBackend.clones == 1
    assert "__pending__" not in SpyBackend.subjects


def test_a_refused_apply_writes_nothing_to_the_real_backend():
    world, policy = spied_world(), make_policy()
    result = world.apply_embellishments(policy, "kitchen", one_prop("tin whistle", "locket"), ())
    assert not result.ok
    assert SpyBackend.subjects == []
