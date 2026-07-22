"""Phase 3 standalone test for harness/net_search.py: run the depth-1
policy+value search on a hand-built, engine-valid position with a REAL
EngineBridge (no live server, no poke-env). Verifies the search completes
with zero engine rejections, returns a legal TurnActions, and produces a
well-formed MIXED STRATEGY (the matrix-game solve, not an argmax) per
candidate.

Run from the project root: python -m harness.test_net_search
"""

import random

from schema.battle_state import Boosts, FieldState, MoveSlot, OwnPokemon, Position, TurnActions
from schema.full_info_state import FullInfoState
from engine.bridge import EngineBridge
from model.net_infer import NetEvaluator
from harness.net_translate import full_info_state_to_netstate
from harness.net_search import net_depth1_decision
from schema.battle_state import MoveAction, SwitchAction
from schema.full_info_state import active_mon, bench_mons


def _desc(action, team, position):
    if isinstance(action, MoveAction):
        m = active_mon(team, position)
        return f"move({m.moves[action.move_slot - 1].move}{'+mega' if action.mega else ''})"
    if isinstance(action, SwitchAction):
        return f"switch({bench_mons(team)[action.bench_slot].species})"
    return "pass"

FORMAT = "gen9championsvgc2026regmb"
CKPT = "model/checkpoints/imitation_v4.pt"

failures = []


def check(name, ok, detail=""):
    print(f"  {name} [{'ok' if ok else 'FAIL'}]{'' if ok else ' ' + str(detail)}")
    if not ok:
        failures.append(name)


def mon(species, position=None, hp=100, max_hp=100, item=None, ability="pressure", moves=("tackle",)):
    return OwnPokemon(
        species=species, position=position, hp=hp, max_hp=max_hp,
        stats={"atk": 100, "def": 100, "spa": 100, "spd": 100, "spe": 100},
        ability=ability, item=item, boosts=Boosts(),
        moves=[MoveSlot(move=m, pp=10, max_pp=10) for m in moves],
    )


# A concrete doubles position with real moves/abilities so the engine builds
# it cleanly. My slow Farigiraf holds Trick Room; both sides have a live pair.
def make_state():
    return FullInfoState(
        turn=3, field=FieldState(),
        my_team=[
            mon("farigiraf", Position.LEFT, ability="armortail",
                moves=["trickroom", "psychic", "foulplay", "protect"]),
            mon("torkoal", Position.RIGHT, ability="drought",
                moves=["eruption", "heatwave", "protect", "bodypress"]),
        ],
        opp_team=[
            mon("dragapult", Position.LEFT, ability="clearbody",
                moves=["dragondarts", "phantomforce", "uturn", "protect"]),
            mon("whimsicott", Position.RIGHT, ability="prankster",
                moves=["tailwind", "moonblast", "encore", "protect"]),
        ],
    )


print("depth-1 search on an engine-valid position (real EngineBridge, batched value)")
evaluator = NetEvaluator(CKPT)
state = make_state()
worlds = [state, state]  # already full-info; two copies stands in for determinized worlds
import time
with EngineBridge(FORMAT) as bridge:
    t0 = time.time()
    chosen, diag = net_depth1_decision(evaluator, bridge, worlds,
                                       my_netstate=full_info_state_to_netstate(state),
                                       k_my=4, k_opp=4, rng=random.Random(0))
    dt = time.time() - t0

check("returned a TurnActions", isinstance(chosen, TurnActions), type(chosen))
check("zero engine rejections", diag.engine_errors == 0, diag.engine_errors)
check("ran rollouts", diag.rollouts > 0, diag.rollouts)
check("a probability per my-candidate", len(diag.strategy) > 0)
probs = [p for p, _ in diag.strategy]
check("all probabilities in [0,1]", all(0.0 <= p <= 1.0 for p in probs), probs)
check("probabilities sum to ~1 (a real mixed strategy)", abs(sum(probs) - 1.0) < 1e-6, sum(probs))
check("strategy is discriminative (not perfectly uniform)",
      len(set(round(p, 4) for p in probs)) > 1, [round(p, 3) for p in probs])

print(f"\n  rollouts={diag.rollouts}  errors={diag.engine_errors}  wall={dt:.1f}s")

# Regression guard for the engine-handle leak that killed a live match:
# net_depth1_decision must free every handle it creates. Without free(),
# repeated decisions accumulate battles in the node process until it dies
# with "Reached heap limit - JavaScript heap out of memory" (and GC-thrashes
# long before that, which looks exactly like a hang). Many decisions on ONE
# bridge is the shape that exposes it.
print("\nTier-1 pruning regression: the net search must never propose a "
      "resisted-into-everything attack when a better one exists")
# The exact MB552 misplay: Charizard clicked Heat Wave into a Garchomp+
# Charizard pair that BOTH resist Fire, while Charizard also knows Rock
# Slide/Solar Beam/Protect. _pruned_slot_actions (the same pruner
# SolverPlayer's propose_pruned_turn_actions uses) drops Heat Wave here
# since a neutral/better attack (Rock Slide) survives - see
# model/test_tier1_pruning.py for the pruner's own unit tests; this checks
# the net SEARCH actually draws from the pruned pool, not the raw one.
#
# NOTE: _pruned_slot_actions early-exits with the UNFILTERED list when the
# raw enumeration is already <= cap (no need to prune what already fits) -
# so this needs a real bench (raw count > cap), same as the actual MB552
# roster, or the filter never even runs and the test passes for the wrong
# reason.
from harness.net_search import _ranked_joints  # noqa: E402
from model.action_space import _pruned_slot_actions  # noqa: E402

heatwave_state = FullInfoState(
    turn=1, field=FieldState(),
    my_team=[
        mon("charizard", Position.LEFT, ability="blaze",
            moves=["heatwave", "rockslide", "solarbeam", "protect"]),
        mon("incineroar", Position.RIGHT, ability="intimidate",
            moves=["fakeout", "flareblitz", "partingshot", "knockoff"]),
        mon("kingambit", None, ability="defiant", moves=["suckerpunch"]),
        mon("sylveon", None, ability="pixilate", moves=["hypervoice"]),
    ],
    opp_team=[
        mon("garchomp", Position.LEFT, ability="roughskin", moves=["earthquake"]),
        mon("charizard", Position.RIGHT, ability="blaze", moves=["airslash"]),
    ],
)
# Check the PRUNED CANDIDATE POOL directly (model/action_space.py's
# responsibility) rather than only through _ranked_joints' top-k JOINT
# picks: with the 2026-07-21 pruning redesign now correctly offering ALL
# living switch destinations (not just the first), the candidate pool grew
# by one entry here, which dilutes the net's OWN softmax ranking enough
# that Rock Slide's joint pairings can fall outside an 8-wide top-k window
# in this hand-built position - that's the net's LEARNED policy preferring
# Protect/Solar Beam here, a separate concern from "did Tier-1 pruning
# correctly exclude Heat Wave and include Rock Slide in the pool at all",
# which is what this test actually needs to guarantee.
pruned_pool = _pruned_slot_actions(heatwave_state, "me", Position.LEFT, 6)
pool_moves = {heatwave_state.my_team[0].moves[a.move_slot - 1].move
              for a in pruned_pool if isinstance(a, MoveAction)}
check("Heat Wave never in the pruned candidate pool (resisted by both opposing mons)",
      "heatwave" not in pool_moves, pool_moves)
check("Rock Slide IS in the pruned candidate pool (neutral/super, survives the cut)",
      "rockslide" in pool_moves, pool_moves)

# And separately, confirm the SEARCH actually draws from that pool (never
# the raw one) by checking Heat Wave is absent from the net's top-k joint
# picks too - the guarantee _ranked_joints is actually responsible for.
my_cands = _ranked_joints(evaluator, full_info_state_to_netstate(heatwave_state),
                          heatwave_state, "me", heatwave_state.my_team, k=8, tier1_cap=6)
left_moves = set()
for _, ta in my_cands:
    a = ta.slot_left
    if isinstance(a, MoveAction):
        left_moves.add(active_mon(heatwave_state.my_team, Position.LEFT).moves[a.move_slot - 1].move)
check("Heat Wave never proposed for Charizard by the search either",
      "heatwave" not in left_moves, left_moves)

print("\nhandle-leak soak: many decisions on one bridge must stay fast + not crash")
N_SOAK = 25
with EngineBridge(FORMAT) as bridge:
    t0 = time.time()
    first = last = None
    for i in range(N_SOAK):
        s0 = time.time()
        _b, _d = net_depth1_decision(evaluator, bridge, worlds,
                                     my_netstate=full_info_state_to_netstate(state),
                                     k_my=4, k_opp=4)
        if i == 0:
            first = time.time() - s0
        last = time.time() - s0
    soak = time.time() - t0
check(f"{N_SOAK} sequential decisions completed on one bridge", True)
# A leak shows up as steady slowdown (GC pressure); allow generous headroom.
check("no runaway slowdown (last decision < 3x the first)", last < max(first * 3.0, 0.5),
      f"first={first:.2f}s last={last:.2f}s")
print(f"  soak: {N_SOAK} decisions in {soak:.1f}s (first {first:.2f}s, last {last:.2f}s)")
print("  mixed strategy (probability per candidate):")
for p, ta in diag.strategy[:5]:
    print(f"    p={p:.3f}  left={_desc(ta.slot_left, state.my_team, Position.LEFT)}"
          f"  right={_desc(ta.slot_right, state.my_team, Position.RIGHT)}")

print(f"\n{'PASS' if not failures else 'FAIL: ' + ', '.join(failures)}")
