"""Validates the self-switch action mechanism (MoveAction.switch_bench_slot,
model/action_space.py's branching, model/solver_game.py's
_resolve_self_switches) against the real engine - no engine/bridge.js
changes were needed for this: the destination is controlled purely by
which bench mon comes first in team order when _resolve_self_switches
re-inits, exploiting the real, unmodified Showdown engine's own
deterministic forced-switch auto-pick (Side.chooseSwitch() with no slot
given always takes the lowest-index living bench mon - confirmed by
reading vendor/pokemon-showdown/sim/side.ts directly, not assumed).

This replaces the earlier (reverted) pending_switch/ForcedSwitchGame
approach, which required engine changes and turned out to have no way to
feed a genuinely-hidden opponent action into the reconstructed request at
all (Showdown's own request model never asks a side that already has an
active choice a second time mid-turn). Folding the switch-in choice into
the SAME turn-decision node (as an extra dimension on the self-switching
move) sidesteps that entirely - it's just one atomic joint-turn step()
call, exactly like every other turn decision already handled by
EngineGame.

Run from the project root: python -m engine.test_self_switch_actions
"""

import json
import random
import time
from pathlib import Path

from engine.bridge import EngineBridge
from model.solver_game import EngineGame, solve_decision
from schema.battle_state import (
    Boosts, FieldState, MoveAction, MoveSlot, OwnPokemon, Position, Status, SwitchAction,
    Target, TurnActions, Weather,
)
from schema.full_info_state import FullInfoState

_ROOT = Path(__file__).resolve().parent.parent
_SPECIES_STATS = json.loads((_ROOT / "reference" / "species_stats.json").read_text(encoding="utf-8"))

FORMAT = "gen9championsvgc2026regmb"
failures = []


def check(name: str, ok: bool, detail: str = ""):
    print(f"  {name} [{'ok' if ok else 'FAIL'}]{' ' + str(detail) if detail and not ok else ''}")
    if not ok:
        failures.append(name)


def flat(species):
    base = _SPECIES_STATS[species]["base_stats"]
    return base["hp"] + 75, {k: base[k] + 20 for k in ("atk", "def", "spa", "spd", "spe")}


def mk(species, moves, ability, item=None, position=None, fainted=False, status=Status.NONE):
    max_hp, stats = flat(species)
    return OwnPokemon(
        species=species, position=position, fainted=fainted,
        hp=0 if fainted else max_hp, max_hp=max_hp,
        status=status, stats=stats, boosts=Boosts(),
        ability=ability, item=item,
        moves=[MoveSlot(move=m, pp=16, max_pp=16) for m in moves],
    )


def bug_state() -> FullInfoState:
    # my_team order [garchomp, grimmsnarl, pelipper, swampert] ->
    # bench_mons() gives bench[0]=pelipper, bench[1]=swampert.
    return FullInfoState(
        turn=4,
        field=FieldState(weather=Weather.SUN, weather_turns=3),
        my_team=[
            mk("garchomp", ["earthquake", "dragonclaw", "protect", "swordsdance"], "roughskin",
               position=Position.LEFT),
            mk("grimmsnarl", ["partingshot", "foulplay", "reflect", "lightscreen"], "prankster",
               position=Position.RIGHT),
            mk("pelipper", ["hurricane", "weatherball", "tailwind", "wideguard"], "drizzle"),
            mk("swampert", ["wavecrash", "earthquake", "icepunch", "protect"], "damp"),
        ],
        opp_team=[
            mk("charizard", ["heatwave", "solarbeam", "weatherball", "protect"], "blaze",
               item="charizarditey", position=Position.LEFT),
            mk("garchomp", ["earthquake", "dragonclaw", "rockslide", "protect"], "roughskin",
               position=Position.RIGHT),
            mk("kingambit", ["kowtowcleave", "suckerpunch", "ironhead", "protect"], "defiant"),
            mk("sylveon", ["hypervoice", "hyperbeam", "quickattack", "detect"], "pixilate"),
        ],
    )


bridge = EngineBridge(FORMAT)

print("1. a self-switch move's switch_bench_slot deterministically controls the real send-in")
# Once _resolve_self_switches re-inits, the fresh battle is a genuine
# 'move'-type request for the WHOLE turn (not a synthetic switch-only
# pause) - both sides' other slots need REAL actions, same as any real
# joint turn (propose_pruned_turn_actions never hands NoAction() for a
# living slot either); Protect is a harmless real action for this test.
state = bug_state()
game = EngineGame(bridge, [state], per_slot_cap=6)
node = game._roots[0]
left_protect = MoveAction(move_slot=3, target=Target.SELF)  # garchomp's protect
# Charizard must NOT use Protect here: it's Parting Shot's target
# (Target.OPP_LEFT below) and real Protect would correctly block the
# stat drop AND the switch-out with it (Parting Shot's switch is tied to
# the move actually succeeding) - that's genuine game behavior, not a
# bug, but it would silently defeat these tests. Opp garchomp (untargeted
# by anything here) can safely use Protect as an inert placeholder.
opp_pass = TurnActions(
    slot_left=MoveAction(move_slot=1, target=Target.NONE),   # charizard's heat wave
    slot_right=MoveAction(move_slot=4, target=Target.SELF),  # opp garchomp's protect
)

result_pelipper = game.step(
    node,
    my=TurnActions(slot_left=left_protect,
                    slot_right=MoveAction(move_slot=1, target=Target.OPP_LEFT, switch_bench_slot=0)),
    opp=opp_pass, rng=random.Random(0),
)
right_mon = next((m for m in result_pelipper.state.my_team if m.position == Position.RIGHT), None)
check("switch_bench_slot=0 -> pelipper actually comes in", right_mon is not None and right_mon.species == "pelipper",
      right_mon.species if right_mon else None)
check("no engine rejections", game.error_count == 0, game.error_count)

result_swampert = game.step(
    node,
    my=TurnActions(slot_left=left_protect,
                    slot_right=MoveAction(move_slot=1, target=Target.OPP_LEFT, switch_bench_slot=1)),
    opp=opp_pass, rng=random.Random(0),
)
right_mon2 = next((m for m in result_swampert.state.my_team if m.position == Position.RIGHT), None)
check("switch_bench_slot=1 -> swampert actually comes in", right_mon2 is not None and right_mon2.species == "swampert",
      right_mon2.species if right_mon2 else None)
check("no engine rejections", game.error_count == 0, game.error_count)

print("\n2. the opponent's own real still-pending move actually fires against the switched-in mon")
# Charizard (opp LEFT) clicks Heat Wave for real, targeting nobody in
# particular (spread move) - since this is all one atomic step, Heat
# Wave genuinely executes against whichever mon Parting Shot brought in,
# no separate hidden-opponent-request machinery needed.
opp_heatwave = TurnActions(
    slot_left=MoveAction(move_slot=1, target=Target.NONE),
    slot_right=MoveAction(move_slot=4, target=Target.SELF),  # opp garchomp's protect
)
result_hw = game.step(
    node,
    my=TurnActions(slot_left=left_protect,
                    slot_right=MoveAction(move_slot=1, target=Target.OPP_LEFT, switch_bench_slot=0)),
    opp=opp_heatwave, rng=random.Random(0),
)
check("no engine rejections", game.error_count == 0, game.error_count)
right_mon3 = next((m for m in result_hw.state.my_team if m.position == Position.RIGHT), None)
check("pelipper switched in and is still alive/undamaged-ish (resists Fire, Drizzle reverses to Rain)",
      right_mon3 is not None and right_mon3.species == "pelipper" and right_mon3.hp > 0,
      (right_mon3.species, right_mon3.hp) if right_mon3 else None)
check("Drizzle actually fired: weather flipped from Sun to Rain", result_hw.state.field.weather.value == "rain",
      result_hw.state.field.weather)

print("\n3. remap correctness: a self-switch on one slot + a plain voluntary switch on the other, same turn")
# LEFT (garchomp) voluntarily switches to swampert (bench index 1, PRE-
# reorder indexing) while RIGHT (grimmsnarl) self-switches via Parting
# Shot to pelipper (bench index 0) - _resolve_self_switches reorders the
# bench for Parting Shot's benefit, which must NOT corrupt the plain
# SwitchAction's bench_slot=1 reference (_remap_switches' whole job).
result_both = game.step(
    node,
    my=TurnActions(
        slot_left=SwitchAction(bench_slot=1),  # pre-reorder index 1 = swampert
        slot_right=MoveAction(move_slot=1, target=Target.OPP_LEFT, switch_bench_slot=0),  # pre-reorder index 0 = pelipper
    ),
    opp=opp_pass, rng=random.Random(0),
)
check("no engine rejections", game.error_count == 0, game.error_count)
left_mon = next((m for m in result_both.state.my_team if m.position == Position.LEFT), None)
right_mon4 = next((m for m in result_both.state.my_team if m.position == Position.RIGHT), None)
check("LEFT's plain switch still correctly lands on swampert despite the reorder",
      left_mon is not None and left_mon.species == "swampert", left_mon.species if left_mon else None)
check("RIGHT's self-switch still correctly lands on pelipper",
      right_mon4 is not None and right_mon4.species == "pelipper", right_mon4.species if right_mon4 else None)

bridge.free(game.handles)

print("\n4. full-pipeline bug regression: Swampert-over-Pelipper mispick (2026-07-18)")
# model/heuristic.py::choose_forced_switches picked Swampert purely
# because it comes first in bench order, never comparing against
# Pelipper (Ground-immune to the opponent's Garchomp, and whose Drizzle
# reverses the opponent's Sun to Rain on send-out, cutting the still-
# pending Heat Wave's power) - among Parting Shot's two switch-in
# branches specifically, the solver must weight Pelipper higher.
bridge2 = EngineBridge(FORMAT)
rng = random.Random(11)
bug = bug_state()
t0 = time.perf_counter()
best, diag = solve_decision(bridge2, [bug], iterations=200, depth_limit=1, per_slot_cap=6, rng=rng)
elapsed = time.perf_counter() - t0
print(f"  {diag.step_count} engine rollouts in {elapsed:.1f}s -> top action = {best}")
check("zero engine choice rejections", diag.error_count == 0, diag.error_count)

# Sum across every LEFT-slot pairing that shares the same RIGHT-slot
# Parting Shot destination (many different LEFT actions each combine
# with both switch_bench_slot variants) - the fair comparison is total
# probability mass behind "Parting Shot into Pelipper" vs "...into
# Swampert" regardless of what LEFT does that same turn, not whichever
# single pairing happens to appear last in the ranked list.
parting_shot_mass = {0: 0.0, 1: 0.0}
for action, prob in diag.strategy:
    if isinstance(action.slot_right, MoveAction) and action.slot_right.switch_bench_slot is not None:
        parting_shot_mass[action.slot_right.switch_bench_slot] += prob
check("both Parting Shot switch-destinations get real probability mass",
      all(v > 0 for v in parting_shot_mass.values()), parting_shot_mass)
check("solver weights Parting-Shot-into-Pelipper (bench_slot=0) above Parting-Shot-into-Swampert (bench_slot=1)",
      parting_shot_mass[0] > parting_shot_mass[1], parting_shot_mass)
bridge2.close()

print("\n5. regression: a self-switch reorder must NOT drop an already-fainted bench mon (found live, 2026-07-18)")
# _reorder_bench originally rebuilt the team from bench_mons() (LIVING
# bench only) + actives, silently shrinking the roster whenever a bench
# mon had already fainted somewhere earlier in a real game/search tree -
# a fresh init_battle() on that shrunk team desynced every downstream
# index, surfacing as a pydantic ValidationError deep inside a live
# match (move pp coming back None) rather than a clean rejection.
bridge3 = EngineBridge(FORMAT)
faint_state = bug_state()
# swampert (my_team[3]) already fainted this game - only pelipper is a
# real living switch-in candidate now, but the fainted mon must still
# round-trip through the reorder+re-init.
faint_state.my_team[3] = faint_state.my_team[3].model_copy(update={"fainted": True, "hp": 0})
game3 = EngineGame(bridge3, [faint_state], per_slot_cap=6)
node3 = game3._roots[0]
result_faint = game3.step(
    node3,
    my=TurnActions(slot_left=left_protect,
                    slot_right=MoveAction(move_slot=1, target=Target.OPP_LEFT, switch_bench_slot=0)),
    opp=opp_pass, rng=random.Random(0),
)
check("no engine rejections (no ValidationError, no crash)", game3.error_count == 0, game3.error_count)
check("team size still 4 (fainted swampert preserved, not silently dropped)",
      len(result_faint.state.my_team) == 4, len(result_faint.state.my_team))
right_mon5 = next((m for m in result_faint.state.my_team if m.position == Position.RIGHT), None)
check("pelipper (the only living bench mon) correctly switched in",
      right_mon5 is not None and right_mon5.species == "pelipper", right_mon5.species if right_mon5 else None)
still_fainted = next((m for m in result_faint.state.my_team if m.species == "swampert"), None)
check("swampert is still tracked, still fainted",
      still_fainted is not None and still_fainted.fainted, still_fainted)
bridge3.free(game3.handles)
bridge3.close()

print(f"\n{'PASS' if not failures else 'FAIL: ' + ', '.join(failures)}")
