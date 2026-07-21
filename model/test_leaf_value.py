"""Validates model/leaf_value.py's field-control stopgap terms (Tailwind/
Trick Room/screens) added 2026-07-20: they must be exactly inert on a
clean field (so the pure-HP leaf semantics are unchanged), correctly
signed per side, bounded well under one mon's worth (0.25) so a KO always
outranks setup, and Trick Room signed by the active speed gap.

Run from the project root: python -m model.test_leaf_value
"""

from model.leaf_value import _TRICK_ROOM_VALUE, hp_leaf_value
from schema.battle_state import FieldState, MoveSlot, OwnPokemon, Position, SideConditions
from schema.full_info_state import FullInfoState

failures = []


def check(name: str, ok: bool, detail: str = ""):
    print(f"  {name} [{'ok' if ok else 'FAIL'}]{' ' + str(detail) if detail and not ok else ''}")
    if not ok:
        failures.append(name)


def mon(species, spe, position=None, fainted=False, hp=100, max_hp=100):
    return OwnPokemon(
        species=species, position=position, fainted=fainted,
        hp=0 if fainted else hp, max_hp=max_hp,
        stats={"atk": 100, "def": 100, "spa": 100, "spd": 100, "spe": spe},
        ability="pressure", moves=[MoveSlot(move="tackle", pp=16, max_pp=16)],
    )


def state(field=None, my_speeds=(100, 100), opp_speeds=(100, 100)):
    return FullInfoState(
        turn=5,
        field=field or FieldState(),
        my_team=[mon("garchomp", my_speeds[0], Position.LEFT), mon("incineroar", my_speeds[1], Position.RIGHT),
                 mon("clefable", 60), mon("tyranitar", 61)],
        opp_team=[mon("charizard", opp_speeds[0], Position.LEFT), mon("kingambit", opp_speeds[1], Position.RIGHT),
                  mon("sylveon", 60), mon("aerodactyl", 130)],
    )


base = state()
base_val = hp_leaf_value(base)

print("clean field is inert: full HP both sides (4v4) scores exactly 0.0, no field drift")
check("clean field == pure HP diff (0.0 here)", base_val == 0.0, base_val)

print("\nmy Tailwind strictly raises my leaf value; opp Tailwind strictly lowers it")
my_tw = state(FieldState(my_side=SideConditions(tailwind_turns=4)))
opp_tw = state(FieldState(opp_side=SideConditions(tailwind_turns=4)))
check("my tailwind > clean", hp_leaf_value(my_tw) > base_val, hp_leaf_value(my_tw))
check("opp tailwind < clean", hp_leaf_value(opp_tw) < base_val, hp_leaf_value(opp_tw))
check("tailwind is symmetric", abs((hp_leaf_value(my_tw) - base_val) + (hp_leaf_value(opp_tw) - base_val)) < 1e-9)

print("\nscreens: more active screens on my side => more value (reflect+lightscreen > reflect alone)")
one_screen = state(FieldState(my_side=SideConditions(reflect_turns=5)))
two_screen = state(FieldState(my_side=SideConditions(reflect_turns=5, light_screen_turns=5)))
check("one screen > clean", hp_leaf_value(one_screen) > base_val)
check("two screens > one screen", hp_leaf_value(two_screen) > hp_leaf_value(one_screen))

print("\nTrick Room is signed by the active speed gap: helps my SLOW team, hurts my FAST team")
tr = FieldState(trick_room_turns=4)
slow_me = state(tr, my_speeds=(50, 55), opp_speeds=(120, 130))
fast_me = state(tr, my_speeds=(120, 130), opp_speeds=(50, 55))
check("TR with my slow actives > clean", hp_leaf_value(slow_me) > base_val, hp_leaf_value(slow_me))
check("TR with my fast actives < clean", hp_leaf_value(fast_me) < base_val, hp_leaf_value(fast_me))
check("TR contribution stays within its cap", abs(hp_leaf_value(slow_me) - base_val) <= _TRICK_ROOM_VALUE + 1e-9)

print("\nthe whole field term is bounded well under one mon's worth (0.25): a KO always outranks setup")
# Everything stacked in my favor at once:
stacked = state(FieldState(
    my_side=SideConditions(tailwind_turns=4, reflect_turns=5, light_screen_turns=5),
    trick_room_turns=4,
), my_speeds=(50, 55), opp_speeds=(150, 160))
check("max stacked field swing < 0.25 (one KO)", abs(hp_leaf_value(stacked) - base_val) < 0.25,
      hp_leaf_value(stacked) - base_val)

print("\nKO-awareness: being UP A MON must outrank an HP% lead where I'm DOWN a mon (2026-07-20)")


def ko_state(my_hps, opp_hps):
    # my_hps/opp_hps: list of hp fractions, or None for a fainted mon.
    def team(hps, prefix):
        out = []
        for i, h in enumerate(hps):
            fainted = h is None
            out.append(mon(f"{prefix}{i}", 100, position=(Position.LEFT if i == 0 else Position.RIGHT if i == 1 else None),
                           fainted=fainted, hp=int((h or 0) * 100), max_hp=100))
        return out
    return FullInfoState(turn=6, field=FieldState(), my_team=team(my_hps, "m"), opp_team=team(opp_hps, "o"))


sit1 = hp_leaf_value(ko_state([0.90, None], [0.10, 0.10]))   # I'm DOWN a mon but high HP%
sit2 = hp_leaf_value(ko_state([0.01, 0.01], [None, None]))   # I'm UP two mons, everyone low
sit3 = hp_leaf_value(ko_state([0.01, 0.10], [None, 1.0]))    # I'm UP one mon, they have a full-HP survivor
check("up-two-mons (sit2) scores positive despite tiny HP%", sit2 > 0, sit2)
check("down-a-mon-but-high-HP% (sit1) scores negative", sit1 < 0, sit1)
check("up-one-mon (sit3) scores positive despite their full-HP survivor", sit3 > 0, sit3)
check("ranking is sit2 > sit3 > sit1 (up-2 > up-1 > down-1), the opposite of pure-HP",
      sit2 > sit3 > sit1, (sit2, sit3, sit1))

print("\nsecuring a KO is worth far more than equal chip on a healthy mon (focus-fire incentive)")
# KO a 10%-HP opponent mon vs chip a full-HP opponent mon by the same 10%.
before = ko_state([1.0, 1.0], [0.10, 1.0])
finish_ko = ko_state([1.0, 1.0], [None, 1.0])            # the 10% mon is now KO'd
chip_equal = ko_state([1.0, 1.0], [0.10, 0.90])         # the full mon lost 10% instead
check("finishing the 10% mon (KO) gains far more leaf value than 10% chip elsewhere",
      (hp_leaf_value(finish_ko) - hp_leaf_value(before)) > 5 * (hp_leaf_value(chip_equal) - hp_leaf_value(before)),
      (hp_leaf_value(finish_ko) - hp_leaf_value(before), hp_leaf_value(chip_equal) - hp_leaf_value(before)))

print(f"\n{'PASS' if not failures else 'FAIL: ' + ', '.join(failures)}")
