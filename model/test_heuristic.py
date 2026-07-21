"""Validates model/heuristic.py:

1. choose_turn_actions' forced-self-switch fallback: a mon that's alive
   (not fainted) but has every move disabled - the shape harness/
   translator.py produces during a mid-turn switch-only request (Parting
   Shot/U-turn/Volt Switch/Baton Pass/Flip Turn all force the user to
   switch after acting) - must switch, not return NoAction (found via a
   real game where the resulting stuck request repeated 662 times).
2. choose_forced_switches, the dedicated force-switch handler that
   replaced the old "compute both slots via choose_turn_actions, then
   override the non-participating one" pattern in both harness/*_player.py
   call sites: that pattern let the non-participating slot's move-scoring
   pass (hitting fix #1's fallback, since its moves also read "disabled"
   during a request it isn't part of) spuriously claim the one remaining
   bench mon before the slot that genuinely needed it did - a second real
   stuck-request loop, found immediately after shipping fix #1.

Run from the project root: python -m model.test_heuristic
"""

import json
from pathlib import Path

from model.heuristic import choose_forced_switches, choose_turn_actions
from schema.battle_state import (
    BattleState, FieldState, MoveSlot, OpponentPokemon, OwnPokemon, Position, SwitchAction,
)

_ROOT = Path(__file__).resolve().parent.parent
_SPECIES_DATA = json.loads((_ROOT / "reference" / "species_data.json").read_text(encoding="utf-8"))

failures = []


def check(name: str, ok: bool, detail: str = ""):
    print(f"  {name} [{'ok' if ok else 'FAIL'}]{' ' + str(detail) if detail and not ok else ''}")
    if not ok:
        failures.append(name)


def own(species, position=None, fainted=False, trapped=False, all_moves_disabled=False):
    moves = [
        MoveSlot(move=m, pp=16, max_pp=16, disabled=all_moves_disabled)
        for m in _SPECIES_DATA[species]["moves"][:4]
    ]
    return OwnPokemon(
        species=species, position=position, fainted=fainted, trapped=trapped,
        hp=0 if fainted else 180, max_hp=180,
        stats={"atk": 120, "def": 120, "spa": 120, "spd": 120, "spe": 120},
        ability="intimidate", moves=moves,
    )


def opp(species, position, hp_pct=100.0):
    return OpponentPokemon(species=species, position=position, hp_pct=hp_pct)


print("forced self-switch: alive, not fainted, all moves disabled (Parting Shot's own effect)")
state = BattleState(
    format_id="gen9championsvgc2026regmb", turn=3, field=FieldState(),
    my_active=[
        own("grimmsnarl", Position.LEFT, all_moves_disabled=True),
        own("pelipper", Position.RIGHT),
    ],
    my_bench=[own("archaludon")],
    opp_active=[opp("charizard", Position.LEFT, 75.0), opp("kingambit", Position.RIGHT, 37.0)],
    opp_bench=[],
)
actions = choose_turn_actions(state)
check("forced-switch mon gets a SwitchAction, not NoAction",
      isinstance(actions.slot_left, SwitchAction), actions.slot_left)
check("switches to the living bench mon (archaludon, index 0)",
      isinstance(actions.slot_left, SwitchAction) and actions.slot_left.bench_slot == 0)

print("\ntrapped + all moves disabled: must NOT try to switch (can't - stays NoAction/Struggle)")
trapped_state = BattleState(
    format_id="gen9championsvgc2026regmb", turn=3, field=FieldState(),
    my_active=[own("grimmsnarl", Position.LEFT, trapped=True, all_moves_disabled=True), own("pelipper", Position.RIGHT)],
    my_bench=[own("archaludon")],
    opp_active=[opp("charizard", Position.LEFT), opp("kingambit", Position.RIGHT)],
    opp_bench=[],
)
trapped_actions = choose_turn_actions(trapped_state)
check("trapped mon with no usable move stays NoAction (can't switch either)",
      not isinstance(trapped_actions.slot_left, SwitchAction), trapped_actions.slot_left)

print("\ngenuine Struggle territory: no usable move AND no living bench -> still NoAction")
no_bench_state = BattleState(
    format_id="gen9championsvgc2026regmb", turn=3, field=FieldState(),
    my_active=[own("grimmsnarl", Position.LEFT, all_moves_disabled=True), own("pelipper", Position.RIGHT)],
    my_bench=[own("archaludon", fainted=True)],
    opp_active=[opp("charizard", Position.LEFT), opp("kingambit", Position.RIGHT)],
    opp_bench=[],
)
no_bench_actions = choose_turn_actions(no_bench_state)
check("no living bench -> NoAction (nothing else can be done)",
      not isinstance(no_bench_actions.slot_left, SwitchAction), no_bench_actions.slot_left)

print("\nsanity: normal turn (usable moves available) still picks a move, not a switch")
normal_state = BattleState(
    format_id="gen9championsvgc2026regmb", turn=1, field=FieldState(),
    my_active=[own("grimmsnarl", Position.LEFT), own("pelipper", Position.RIGHT)],
    my_bench=[own("archaludon")],
    opp_active=[opp("charizard", Position.LEFT), opp("kingambit", Position.RIGHT)],
    opp_bench=[],
)
normal_actions = choose_turn_actions(normal_state)
check("mon with usable moves picks a move, not a switch",
      not isinstance(normal_actions.slot_left, SwitchAction), normal_actions.slot_left)

print("\nsanity: fainted mon still switches in (pre-existing behavior preserved)")
fainted_state = BattleState(
    format_id="gen9championsvgc2026regmb", turn=3, field=FieldState(),
    my_active=[own("pelipper", Position.RIGHT)],  # left slot absent - fainted, not yet replaced
    my_bench=[own("archaludon")],
    opp_active=[opp("charizard", Position.LEFT), opp("kingambit", Position.RIGHT)],
    opp_bench=[],
)
fainted_actions = choose_turn_actions(fainted_state)
check("absent (fainted) left slot still gets a switch",
      isinstance(fainted_actions.slot_left, SwitchAction), fainted_actions.slot_left)

print("\nchoose_forced_switches: the exact stuck-loop scenario (single living bench mon,"
      " one slot genuinely fainted, the OTHER slot alive but showing no usable move)")
# Mirrors a real game: sylveon (right) fainted this turn; kingambit
# (left) is alive at 76/207 but the translator shows its moves as
# "disabled" too, since Showdown doesn't re-list moves for a slot that
# isn't part of THIS request (only sylveon's replacement is being asked
# for - force_switch is [False, True]). Only archaludon is left on the
# bench. The old "compute both via choose_turn_actions, then override"
# pattern let kingambit's Struggle-territory fallback claim archaludon
# for itself (a call that then got discarded) before sylveon's slot got
# a turn, leaving the real request unanswered forever.
one_bench_state = BattleState(
    format_id="gen9championsvgc2026regmb", turn=2, field=FieldState(),
    my_active=[own("kingambit", Position.LEFT, all_moves_disabled=True)],  # sylveon fainted, absent
    my_bench=[own("archaludon")],
    opp_active=[opp("charizard", Position.LEFT), opp("kingambit", Position.RIGHT)],
    opp_bench=[],
)
fs_actions = choose_forced_switches(one_bench_state, [False, True])
check("non-participating left slot passes (NoAction), doesn't touch the bench",
      not isinstance(fs_actions.slot_left, SwitchAction), fs_actions.slot_left)
check("the genuinely fainted right slot gets the switch to the only bench mon",
      isinstance(fs_actions.slot_right, SwitchAction) and fs_actions.slot_right.bench_slot == 0,
      fs_actions.slot_right)

print("\nchoose_forced_switches: both slots force-switching (double faint), two bench mons")
both_state = BattleState(
    format_id="gen9championsvgc2026regmb", turn=2, field=FieldState(),
    my_active=[],  # both fainted this turn
    my_bench=[own("archaludon"), own("metagross")],
    opp_active=[opp("charizard", Position.LEFT), opp("kingambit", Position.RIGHT)],
    opp_bench=[],
)
both_actions = choose_forced_switches(both_state, [True, True])
check("left gets a switch", isinstance(both_actions.slot_left, SwitchAction), both_actions.slot_left)
check("right gets a switch", isinstance(both_actions.slot_right, SwitchAction), both_actions.slot_right)
check("the two slots switch to DIFFERENT bench mons",
      both_actions.slot_left.bench_slot != both_actions.slot_right.bench_slot,
      (both_actions.slot_left, both_actions.slot_right))

print("\n_choose_switch_in is damage-aware, not 'first bench mon' (Swampert-over-Pelipper regression, 2026-07-18)")
# Garchomp's revealed Earthquake: Pelipper (Water/Flying) is immune,
# Swampert (Water/Ground) is not - real expected_damage should clearly
# prefer Pelipper even though it's listed AFTER Swampert on the bench
# (the old "first live bench mon" heuristic would have picked Swampert).
revealed_move_state = BattleState(
    format_id="gen9championsvgc2026regmb", turn=4, field=FieldState(),
    my_active=[own("garchomp", Position.LEFT), own("grimmsnarl", Position.RIGHT, all_moves_disabled=True)],
    my_bench=[own("swampert"), own("pelipper")],  # Swampert listed FIRST
    opp_active=[OpponentPokemon(species="garchomp", position=Position.LEFT, hp_pct=100.0,
                                 revealed_moves=["earthquake"])],
    opp_bench=[],
)
revealed_actions = choose_forced_switches(revealed_move_state, [False, True])
check("picks Pelipper (Ground-immune), not Swampert, despite bench order",
      isinstance(revealed_actions.slot_right, SwitchAction) and revealed_actions.slot_right.bench_slot == 1,
      revealed_actions.slot_right)

print("\n_choose_switch_in falls back to type-based reasoning when NO opponent moves are revealed yet")
# No revealed_moves at all - the type-proxy path (Charizard's own Fire/
# Flying typing) still correctly prefers the Water-type resist over
# nothing, matching the same directional preference without needing a
# specific known move.
no_moves_state = BattleState(
    format_id="gen9championsvgc2026regmb", turn=4, field=FieldState(),
    my_active=[own("garchomp", Position.LEFT), own("grimmsnarl", Position.RIGHT, all_moves_disabled=True)],
    my_bench=[own("annihilape"), own("pelipper")],  # annihilape (Fighting) listed FIRST, 4x weak to nothing here
    opp_active=[opp("charizard", Position.LEFT)],
    opp_bench=[],
)
no_moves_actions = choose_forced_switches(no_moves_state, [False, True])
check("prefers the Water-type resist (Pelipper) over the neutral option, via the type-only proxy",
      isinstance(no_moves_actions.slot_right, SwitchAction) and no_moves_actions.slot_right.bench_slot == 1,
      no_moves_actions.slot_right)

print(f"\n{'PASS' if not failures else 'FAIL: ' + ', '.join(failures)}")
