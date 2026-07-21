"""Phase 3 standalone test for harness/net_search.py: run the depth-1
policy+value search on a hand-built, engine-valid position with a REAL
EngineBridge (no live server, no poke-env). Verifies the search completes
with zero engine rejections, returns a legal TurnActions, and produces a
well-formed value per candidate.

Run from the project root: python -m harness.test_net_search
"""

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
CKPT = "model/checkpoints/imitation_v1.pt"

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
    best, diag = net_depth1_decision(evaluator, bridge, worlds,
                                     my_netstate=full_info_state_to_netstate(state),
                                     k_my=4, k_opp=4)
    dt = time.time() - t0

check("returned a TurnActions", isinstance(best, TurnActions), type(best))
check("zero engine rejections", diag.engine_errors == 0, diag.engine_errors)
check("ran rollouts", diag.rollouts > 0, diag.rollouts)
check("a value per my-candidate", len(diag.my_values) > 0)
vals = [v for v, _ in diag.my_values]
check("all values in [0,1]", all(0.0 <= v <= 1.0 for v in vals), vals)
check("values are discriminative (not all identical)",
      len(set(round(v, 4) for v in vals)) > 1, [round(v, 3) for v in vals])

print(f"\n  rollouts={diag.rollouts}  errors={diag.engine_errors}  wall={dt:.1f}s")

# Regression guard for the engine-handle leak that killed a live match:
# net_depth1_decision must free every handle it creates. Without free(),
# repeated decisions accumulate battles in the node process until it dies
# with "Reached heap limit - JavaScript heap out of memory" (and GC-thrashes
# long before that, which looks exactly like a hang). Many decisions on ONE
# bridge is the shape that exposes it.
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
print("  top candidates by value:")
for v, ta in diag.my_values[:5]:
    print(f"    value {v:.3f}  left={_desc(ta.slot_left, state.my_team, Position.LEFT)}"
          f"  right={_desc(ta.slot_right, state.my_team, Position.RIGHT)}")

print(f"\n{'PASS' if not failures else 'FAIL: ' + ', '.join(failures)}")
