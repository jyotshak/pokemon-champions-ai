"""Validates FullInfoState helpers + the legal-action enumerator against
hand-computed counts on a realistic doubles position (real move ids from
reference/move_data.json, real mega stones from mega_stones.json):

- per-slot enumeration: single-target branching, spread/self moves not
  branching, mega doubling only for the stone holder, switches
- joint product filters: same-bench double switch, double mega
- edge cases: mega already used, ally-required move with no ally, empty
  slot, all-moves-unusable (Struggle territory)
- hp_leaf_value scale checks

Run from the project root: python -m model.test_action_space
"""

import json
from pathlib import Path

from model.action_space import _pruned_slot_actions, propose_slot_actions, propose_turn_actions
from model.leaf_value import hp_leaf_value
from schema.full_info_state import FullInfoState
from schema.battle_state import (
    FieldState, MoveAction, MoveSlot, NoAction, OwnPokemon, Position, SwitchAction, SideConditions, Target,
    VolatileState,
)

_MOVE_DATA = json.loads((Path(__file__).resolve().parent.parent / "reference" / "move_data.json").read_text(encoding="utf-8"))

failures = []


def check(name: str, actual, expected):
    ok = actual == expected
    print(f"  {name}: {actual} expected {expected} [{'ok' if ok else 'MISMATCH'}]")
    if not ok:
        failures.append(name)


def mk(species, moves, item=None, position=None, hp=155, fainted=False, pp=16, trapped=False,
      disabled=False, must_recharge=False, charging_move=None):
    for m in moves:
        assert m in _MOVE_DATA, f"typo in test data: {m} not in move_data.json"
    volatiles = [VolatileState(name="must_recharge")] if must_recharge else []
    if charging_move:
        volatiles.append(VolatileState(name="two_turn_move", data={"move": charging_move}))
    return OwnPokemon(
        species=species, position=position, fainted=fainted,
        hp=0 if fainted else hp, max_hp=hp,
        stats={"atk": 120, "def": 120, "spa": 120, "spd": 120, "spe": 120},
        ability="pressure", item=item,
        moves=[MoveSlot(move=m, pp=pp, max_pp=16, disabled=disabled) for m in moves],
        trapped=trapped,
        volatiles=volatiles,
    )


state = FullInfoState(
    turn=3,
    field=FieldState(),
    my_team=[
        mk("charizard", ["heatwave", "airslash", "protect", "solarbeam"],
           item="charizarditey", position=Position.LEFT),
        mk("garchomp", ["earthquake", "dragonclaw", "protect", "swordsdance"],
           position=Position.RIGHT),
        mk("clefable", ["moonblast", "protect"]),
        mk("incineroar", ["fakeout", "knockoff"]),
    ],
    opp_team=[
        mk("tyranitar", ["rockslide", "crunch", "protect"],
           item="tyranitarite", position=Position.LEFT),
        mk("garchomp", ["earthquake", "dragonclaw"],
           item="garchompite", position=Position.RIGHT),
        mk("rotomwash", ["hydropump", "voltswitch"]),
        mk("basculegion", ["wavecrash", "protect"], fainted=True),
    ],
)

print("per-slot enumeration (my side)")
# charizard (stone holder, mega available): heatwave spread=1, airslash 2
# targets, protect self=1, solarbeam 2 targets -> 6 move options x2 mega
# branches = 12, + 2 living bench switches = 14
left = propose_slot_actions(state, "me", Position.LEFT)
check("charizard options", len(left), 14)
check("  mega variants", sum(1 for a in left if isinstance(a, MoveAction) and a.mega), 6)
check("  switches", sum(1 for a in left if isinstance(a, SwitchAction)), 2)
# garchomp (no stone): earthquake spread=1 + dragonclaw 2 + protect 1 +
# swordsdance self=1 = 5 moves + 2 switches = 7
right = propose_slot_actions(state, "me", Position.RIGHT)
check("garchomp options", len(right), 7)
check("  mega variants", sum(1 for a in right if isinstance(a, MoveAction) and a.mega), 0)

print("\njoint product (my side): 14x7=98, minus 2 same-bench double switches")
joint_me = propose_turn_actions(state, "me")
check("joint actions", len(joint_me), 96)

print("\njoint product (opp side): both hold stones -> double-mega filtered")
# tyranitar: (rockslide 1 + crunch 2 + protect 1) x2 = 8 + 1 living bench = 9
# opp garchomp: (earthquake 1 + dragonclaw 2) x2 = 6 + 1 = 7
# 9x7=63, minus 1 same-bench pair, minus 4x3=12 double-mega pairs = 50
check("tyranitar options", len(propose_slot_actions(state, "opp", Position.LEFT)), 9)
check("opp garchomp options", len(propose_slot_actions(state, "opp", Position.RIGHT)), 7)
joint_opp = propose_turn_actions(state, "opp")
check("joint actions", len(joint_opp), 50)
double_mega = sum(
    1 for t in joint_opp
    if isinstance(t.slot_left, MoveAction) and t.slot_left.mega
    and isinstance(t.slot_right, MoveAction) and t.slot_right.mega
)
check("double-mega pairs remaining", double_mega, 0)

print("\nmega already used -> no mega branches")
used = state.model_copy(deep=True)
used.field.my_side = SideConditions(mega_used=True)
check("charizard options", len(propose_slot_actions(used, "me", Position.LEFT)), 8)

print("\nally-required move with no ally on field")
solo = FullInfoState(
    turn=5, field=FieldState(),
    my_team=[mk("incineroar", ["helpinghand", "knockoff"], position=Position.RIGHT)],
    opp_team=[mk("tyranitar", ["crunch"], position=Position.LEFT)],
)
solo_actions = propose_slot_actions(solo, "me", Position.RIGHT)
# helping hand (adjacentAlly) drops entirely; knockoff has 1 live target
check("incineroar options", len(solo_actions), 1)
check("empty left slot", [type(a).__name__ for a in propose_slot_actions(solo, "me", Position.LEFT)], ["NoAction"])

print("\nno usable move, no bench (Struggle territory)")
stuck = FullInfoState(
    turn=9, field=FieldState(),
    my_team=[mk("garchomp", ["earthquake"], position=Position.LEFT, pp=0)],
    opp_team=[mk("tyranitar", ["crunch"], position=Position.LEFT)],
)
check("actions", [type(a).__name__ for a in propose_slot_actions(stuck, "me", Position.LEFT)], ["NoAction"])

print("\ntrapped, normal moveset (genuine trapping ability, e.g. Shadow Tag) -> no switches, moves unaffected")
trapped_normal = FullInfoState(
    turn=6, field=FieldState(),
    my_team=[mk("garchomp", ["earthquake", "dragonclaw", "protect", "swordsdance"], position=Position.LEFT, trapped=True)],
    opp_team=[mk("tyranitar", ["crunch"], position=Position.LEFT)],
)
trapped_actions = propose_slot_actions(trapped_normal, "me", Position.LEFT)
check("no switch offered", any(isinstance(a, SwitchAction) for a in trapped_actions), False)
check("moves still fully enumerated (earthquake+dragonclaw[1 opp]+protect+swordsdance=4)", len(trapped_actions), 4)

print("\ntrapped + single-entry moves (forced continuation, e.g. mid-Solar Beam) -> exactly one no-target move")
locked = FullInfoState(
    turn=7, field=FieldState(),
    my_team=[mk("charizard", ["solarbeam"], item="charizarditey", position=Position.LEFT, trapped=True)],
    opp_team=[mk("tyranitar", ["crunch"], position=Position.LEFT)],
)
locked_actions = propose_slot_actions(locked, "me", Position.LEFT)
check("exactly one action", locked_actions, [MoveAction(move_slot=1, target=Target.NONE)])

print("\nmust_recharge volatile (LIVE-TRANSLATED shape: real moveset kept, all disabled, "
      "harness/translator.py::own_pokemon) -> exactly one no-target move, no switch even with a live bench")
# Regression for the in-search recharge-blindness bug: without this check,
# a recharging mon with an exhausted bench fell through to [NoAction()] (the
# generic enumerator skips every disabled move and, before this fix, offered
# switches whenever trapped=False - which the live translator never sets for
# this case). That NoAction, submitted to a rebuilt engine world that has no
# idea the mon must recharge (engine/bridge.js reconstructs the matching
# volatile now - see its own comment), got rejected with "Can't pass: ...
# must make a move" - 48/48 rollouts rejected in the live match that
# surfaced this (MB552's Sylveon after Hyper Beam).
recharging = FullInfoState(
    turn=4, field=FieldState(),
    my_team=[mk("sylveon", ["hypervoice", "hyperbeam", "quickattack", "detect"],
               position=Position.LEFT, disabled=True, must_recharge=True),
             mk("kingambit", ["suckerpunch", "ironhead", "kowtowcleave", "lowkick"])],  # a LIVE bench mon
    opp_team=[mk("tyranitar", ["crunch"], position=Position.LEFT)],
)
recharge_actions = propose_slot_actions(recharging, "me", Position.LEFT)
check("exactly one action despite 4 real (disabled) moves + a live bench",
      recharge_actions, [MoveAction(move_slot=1, target=Target.NONE)])
check("no switch offered (a recharging mon cannot switch, even with one available)",
      any(isinstance(a, SwitchAction) for a in recharge_actions), False)

print("\nmust_recharge with an EXHAUSTED bench - the exact shape that used to fall through to NoAction")
recharging_no_bench = FullInfoState(
    turn=4, field=FieldState(),
    my_team=[mk("sylveon", ["hypervoice", "hyperbeam", "quickattack", "detect"],
               position=Position.LEFT, disabled=True, must_recharge=True),
             mk("kingambit", ["suckerpunch"], fainted=True)],
    opp_team=[mk("tyranitar", ["crunch"], position=Position.LEFT)],
)
check("still one real move, NOT NoAction",
      propose_slot_actions(recharging_no_bench, "me", Position.LEFT),
      [MoveAction(move_slot=1, target=Target.NONE)])

print("\ntwo_turn_move volatile (mid-charge on Solar Beam/Fly/Electro Shot without Rain, "
      "LIVE-TRANSLATED shape) -> exactly one move at the charging move's REAL slot, no switch")
# Solar Beam is real move_slot 2 here (not slot 1) - the fix must find the
# actual slot the charging move lives in, not assume 1 (must_recharge can
# assume 1 since that move is synthetic and slot content doesn't matter -
# solarbeam is a genuine moveset entry, so getting the slot right matters
# for any downstream code that reads move_slot expecting the real move).
charging = FullInfoState(
    turn=5, field=FieldState(),
    my_team=[mk("charizard", ["protect", "solarbeam", "flamethrower", "airslash"],
               position=Position.LEFT, disabled=True, charging_move="solarbeam"),
             mk("kingambit", ["suckerpunch", "ironhead", "kowtowcleave", "lowkick"])],  # a LIVE bench mon
    opp_team=[mk("tyranitar", ["crunch"], position=Position.LEFT)],
)
charging_actions = propose_slot_actions(charging, "me", Position.LEFT)
check("exactly one action, at solarbeam's real slot (2)",
      charging_actions, [MoveAction(move_slot=2, target=Target.NONE)])
check("no switch offered (a charging mon cannot switch, even with one available)",
      any(isinstance(a, SwitchAction) for a in charging_actions), False)

print("\nCurse targeting depends on the USER's type, not a fixed move property")
curse_ghost = FullInfoState(
    turn=8, field=FieldState(),
    my_team=[mk("gengar", ["curse", "shadowball"], position=Position.LEFT)],
    opp_team=[mk("tyranitar", ["crunch"], position=Position.LEFT),
              mk("garchomp", ["earthquake"], position=Position.RIGHT)],
)
ghost_curse_actions = [a for a in propose_slot_actions(curse_ghost, "me", Position.LEFT)
                        if isinstance(a, MoveAction) and a.move_slot == 1]
check("Ghost-type user: Curse targets an opponent (2 options, one per opposing slot)",
      sorted(a.target for a in ghost_curse_actions), sorted([Target.OPP_LEFT, Target.OPP_RIGHT]))

curse_nonghost = FullInfoState(
    turn=8, field=FieldState(),
    my_team=[mk("garchomp", ["curse", "earthquake"], position=Position.LEFT)],
    opp_team=[mk("tyranitar", ["crunch"], position=Position.LEFT),
              mk("charizard", ["flamethrower"], position=Position.RIGHT)],
)
nonghost_curse_actions = [a for a in propose_slot_actions(curse_nonghost, "me", Position.LEFT)
                           if isinstance(a, MoveAction) and a.move_slot == 1]
check("non-Ghost user: Curse self-targets, exactly one option, no explicit target",
      [a.target for a in nonghost_curse_actions], [Target.SELF])

print("\nself-switch moves (Parting Shot etc.) branch over every living bench mon")
# Every mon here carries a realistic 2+-move set, not just the move(s)
# under test - a genuine champions set never narrows to exactly one move
# slot outside forced continuation (recharge/struggle/a two-turn
# charge), which is exactly the signal safe_to_reorder below keys off;
# a 1-move fixture would spuriously look like that hazard and silently
# suppress the branching this test exists to check.
parting = FullInfoState(
    turn=6, field=FieldState(),
    my_team=[mk("garchomp", ["earthquake", "protect"], position=Position.LEFT),
             mk("grimmsnarl", ["partingshot", "foulplay"], position=Position.RIGHT),
             mk("pelipper", ["hurricane", "protect"]), mk("swampert", ["wavecrash", "protect"])],
    opp_team=[mk("tyranitar", ["crunch", "protect"], position=Position.LEFT)],
)
parting_actions = propose_slot_actions(parting, "me", Position.RIGHT)
parting_shot_variants = [a for a in parting_actions if isinstance(a, MoveAction) and a.move_slot == 1]
check("2 bench mons -> 2 Parting Shot variants (one per switch_bench_slot)", len(parting_shot_variants), 2)
check("switch_bench_slot values are 0 and 1, no plain (unset) Parting Shot variant",
      sorted(a.switch_bench_slot for a in parting_shot_variants), [0, 1])
foul_play_variants = [a for a in parting_actions if isinstance(a, MoveAction) and a.move_slot == 2]
check("a normal move (Foul Play) is untouched: exactly 1 option, switch_bench_slot unset",
      (len(foul_play_variants), foul_play_variants[0].switch_bench_slot), (1, None))

print("\nself-switch move with an EMPTY bench: no branching, just one plain-move option")
parting_no_bench = FullInfoState(
    turn=6, field=FieldState(),
    my_team=[mk("garchomp", ["earthquake", "protect"], position=Position.LEFT),
             mk("grimmsnarl", ["partingshot", "foulplay"], position=Position.RIGHT)],
    opp_team=[mk("tyranitar", ["crunch", "protect"], position=Position.LEFT)],
)
no_bench_actions = [a for a in propose_slot_actions(parting_no_bench, "me", Position.RIGHT)
                     if isinstance(a, MoveAction) and a.move_slot == 1]
check("exactly one Parting Shot option, switch_bench_slot unset (nothing to switch into)",
      (len(no_bench_actions), no_bench_actions[0].switch_bench_slot), (1, None))

print("\n_pruned_slot_actions must not collapse self-switch bench candidates down to one")
pruned_parting = _pruned_slot_actions(parting, "me", Position.RIGHT, cap=1)
pruned_variants = [a for a in pruned_parting if isinstance(a, MoveAction) and a.switch_bench_slot is not None]
check("both bench candidates survive an aggressively small cap",
      sorted(a.switch_bench_slot for a in pruned_variants), [0, 1])

print("\na self-switch move must not squeeze real moves (Fake Out) out of the per-slot cap (2026-07-20)")
# The live bug: Incineroar's Parting Shot enumerated 2 targets x 2 bench
# = 4 self-switch variants, all kept in full, hogging the per_slot_cap so
# Fake Out (its lowest-damage move) never made the cut. The fix keeps ONE
# self-switch variant per bench destination, freeing cap for real moves.
fakeout_squeeze = FullInfoState(
    turn=1, field=FieldState(),
    my_team=[mk("incineroar", ["fakeout", "throatchop", "partingshot", "flareblitz"], position=Position.LEFT),
             mk("garchomp", ["earthquake", "protect"], position=Position.RIGHT),
             mk("clefable", ["moonblast", "protect"]), mk("tyranitar", ["crunch", "protect"])],
    opp_team=[mk("charizard", ["heatwave", "protect"], position=Position.LEFT),
              mk("kingambit", ["ironhead", "protect"], position=Position.RIGHT)],
)
inc_opts = _pruned_slot_actions(fakeout_squeeze, "me", Position.LEFT, cap=6)
inc_moves = {fakeout_squeeze.my_team[0].moves[a.move_slot - 1].move
             for a in inc_opts if isinstance(a, MoveAction)}
check("Fake Out survives pruning despite the mon also carrying Parting Shot", "fakeout" in inc_moves, True)
ss_count = sum(1 for a in inc_opts if isinstance(a, MoveAction) and a.switch_bench_slot is not None)
check("self-switch contributes exactly one option per living bench mon (2), not targets x bench (4)",
      ss_count, 2)

print("\njoint product forbids both slots switching/self-switching into the SAME bench mon")
mixed_bench = FullInfoState(
    turn=6, field=FieldState(),
    my_team=[mk("grimmsnarl", ["partingshot", "foulplay"], position=Position.LEFT),
             mk("garchomp", ["earthquake", "protect"], position=Position.RIGHT),
             mk("pelipper", ["hurricane", "protect"])],
    opp_team=[mk("tyranitar", ["crunch", "protect"], position=Position.LEFT)],
)
mixed_joint = propose_turn_actions(mixed_bench, "me")
collisions = [
    t for t in mixed_joint
    if isinstance(t.slot_left, MoveAction) and t.slot_left.switch_bench_slot is not None
    and isinstance(t.slot_right, SwitchAction)
    and t.slot_left.switch_bench_slot == t.slot_right.bench_slot
]
check("no joint action has Parting Shot and a plain switch both targeting bench_slot=0", collisions, [])

print("\nself-switch branching is suppressed when ANY mon on EITHER side is mid forced-continuation")
# A mon locked into a synthetic single-move entry (recharge/struggle/a
# two-turn charge's own id - never a genuine 4-move champions set) makes
# a fresh engine reconstruction unsafe for the WHOLE battle, not just
# that one mon (model/solver_game.py's self-switch bench reorder rebuilds
# both teams together in one init_battle call) - found live, several
# turns into a real search tree (a pydantic ValidationError on move
# pp/max_pp being None, from feeding a bogus single "move" through
# buildSet as if it were a real learnset). Parting Shot must fall back to
# a plain MoveAction (no switch_bench_slot) rather than branch, in BOTH
# directions: a hazard on my own side, or on the opponent's.
hazard_on_opp = FullInfoState(
    turn=8, field=FieldState(),
    my_team=[mk("garchomp", ["earthquake", "protect"], position=Position.LEFT),
             mk("grimmsnarl", ["partingshot", "foulplay"], position=Position.RIGHT),
             mk("pelipper", ["hurricane", "protect"]), mk("swampert", ["wavecrash", "protect"])],
    opp_team=[mk("charizard", ["solarbeam"], position=Position.LEFT, trapped=True)],  # mid forced-continuation
)
hazard_opp_actions = [a for a in propose_slot_actions(hazard_on_opp, "me", Position.RIGHT)
                       if isinstance(a, MoveAction) and a.move_slot == 1]
check("hazard on the OPPONENT's side still suppresses MY Parting Shot branching",
      (len(hazard_opp_actions), hazard_opp_actions[0].switch_bench_slot), (1, None))

hazard_on_my_other_slot = FullInfoState(
    turn=8, field=FieldState(),
    my_team=[mk("garchomp", ["solarbeam"], position=Position.LEFT, trapped=True),  # mid forced-continuation
             mk("grimmsnarl", ["partingshot", "foulplay"], position=Position.RIGHT),
             mk("pelipper", ["hurricane", "protect"]), mk("swampert", ["wavecrash", "protect"])],
    opp_team=[mk("tyranitar", ["crunch", "protect"], position=Position.LEFT)],
)
hazard_my_actions = [a for a in propose_slot_actions(hazard_on_my_other_slot, "me", Position.RIGHT)
                      if isinstance(a, MoveAction) and a.move_slot == 1]
check("hazard on MY OTHER active slot still suppresses Parting Shot branching",
      (len(hazard_my_actions), hazard_my_actions[0].switch_bench_slot), (1, None))

print("\nhp_leaf_value (KO-aware: 0.75 alive + 0.25*hp per living mon)")
# All living mons full HP -> material value == old pure-HP value, so a
# 4-alive vs 3-alive (opp basculegion fainted) position is still 0.25.
check("even position", hp_leaf_value(state), (4.0 - 3.0) / 4.0)  # opp basculegion fainted
half = state.model_copy(deep=True)
half.my_team[1].hp = half.my_team[1].max_hp // 2
hp_frac = half.my_team[1].hp / half.my_team[1].max_hp
# my side: 3 living-full (3.0) + 1 living at hp_frac (0.75 + 0.25*hp_frac); opp: 3 living-full (3.0).
expected = ((3.0 + 0.75 + 0.25 * hp_frac) - 3.0) / 4.0
check("after damage", hp_leaf_value(half), expected)

print("\n2026-07-21 pruning redesign, after an external review found the original "
      "version silently dropped whole classes of actions ([[net-external-review-2026-07-21]])")

print("\nProtect (0-damage) MUST survive a tight cap alongside several real attacks - "
      "this is the concrete mechanism behind 'the net AND the CFR tree clicked Protect 0 times'")
protect_squeeze = FullInfoState(
    turn=3, field=FieldState(),
    my_team=[mk("garchomp", ["earthquake", "dragonclaw", "rockslide", "protect"], position=Position.LEFT),
             mk("kingambit", ["suckerpunch", "ironhead", "kowtowcleave", "lowkick"], position=Position.RIGHT)],
    opp_team=[mk("tyranitar", ["crunch"], position=Position.LEFT),
              mk("rotomwash", ["hydropump"], position=Position.RIGHT)],
)
tight = _pruned_slot_actions(protect_squeeze, "me", Position.LEFT, cap=2)
protect_kept = any(isinstance(a, MoveAction) and a.move_slot == 4 for a in tight)
check("Protect survives even at cap=2 (smaller than the 4 real moves)", protect_kept, True)

print("\ntarget diversity: a status move with a REAL targeting decision (Thunder Wave on "
      "either opponent, both score 0.0 damage) must keep BOTH targets, not just whichever "
      "was enumerated first")
thunderwave_state = FullInfoState(
    turn=3, field=FieldState(),
    my_team=[mk("whimsicott", ["thunderwave", "moonblast", "tailwind", "encore"], position=Position.LEFT),
             mk("kingambit", ["suckerpunch", "ironhead", "kowtowcleave", "lowkick"], position=Position.RIGHT)],
    opp_team=[mk("tyranitar", ["crunch"], position=Position.LEFT),
              mk("rotomwash", ["hydropump"], position=Position.RIGHT)],
)
tw_actions = [a for a in _pruned_slot_actions(thunderwave_state, "me", Position.LEFT, cap=6)
              if isinstance(a, MoveAction) and a.move_slot == 1]
tw_targets = {a.target for a in tw_actions}
check("Thunder Wave kept for BOTH opposing targets (not collapsed to one)",
      tw_targets, {Target.OPP_LEFT, Target.OPP_RIGHT})

print("\nall normal switch destinations survive a tight cap, not just the first found")
three_bench = FullInfoState(
    turn=3, field=FieldState(),
    my_team=[mk("garchomp", ["earthquake", "dragonclaw", "rockslide", "protect"], position=Position.LEFT),
             mk("kingambit", ["suckerpunch"], position=Position.RIGHT),
             mk("clefable", ["moonblast"]), mk("incineroar", ["fakeout"]), mk("sylveon", ["hypervoice"])],
    opp_team=[mk("tyranitar", ["crunch"], position=Position.LEFT)],
)
switch_actions = [a for a in _pruned_slot_actions(three_bench, "me", Position.LEFT, cap=3)
                  if isinstance(a, SwitchAction)]
check("all 3 living bench mons reachable by a voluntary switch, not just bench_slot 0",
      {a.bench_slot for a in switch_actions}, {0, 1, 2})

print("\nmega + Protect coexists with mega + best attack, not just the single highest-damage mega")
mega_utility = FullInfoState(
    turn=3, field=FieldState(),
    my_team=[mk("charizard", ["heatwave", "airslash", "protect", "solarbeam"],
               item="charizarditey", position=Position.LEFT),
             mk("kingambit", ["suckerpunch", "ironhead", "kowtowcleave", "lowkick"], position=Position.RIGHT)],
    opp_team=[mk("tyranitar", ["crunch"], position=Position.LEFT),
              mk("rotomwash", ["hydropump"], position=Position.RIGHT)],
)
mega_actions = [a for a in _pruned_slot_actions(mega_utility, "me", Position.LEFT, cap=6)
                if isinstance(a, MoveAction) and a.mega]
mega_move_slots = {a.move_slot for a in mega_actions}
print(f"  (mega move_slots present: {mega_move_slots})")
check("mega+Protect (move_slot 3) present alongside a mega+attack combo",
      3 in mega_move_slots and len(mega_move_slots) > 1, True)

print(f"\n{'PASS' if not failures else 'FAIL: ' + ', '.join(failures)}")
