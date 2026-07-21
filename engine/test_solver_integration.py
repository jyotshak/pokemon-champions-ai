"""End-to-end solver pipeline smoke test, no server needed:
hand-built mid-battle BattleState -> sample_determinization (K worlds) ->
EngineGame (real Sim.Battle rollouts) -> external-sampling MCCFR ->
TurnActions.

Asserts the pipeline holds together where it can actually break:
- ZERO engine choice rejections across every rollout (enumerator, choice
  translation, and engine legality all agree)
- a valid root strategy over the pruned joint action space
- a sanity decision: with both opponent actives at 1 HP and the solver's
  own side healthy, the chosen actions are attacks, not switches

Also prints rollout throughput — the number that sets real-turn budgets.

Run from the project root: python -m engine.test_solver_integration
"""

import json
import random
import time
from pathlib import Path

from belief.determinize import sample_determinization
from engine.bridge import EngineBridge
from model.solver_game import solve_decision
from schema.battle_state import (
    BattleState, FieldState, MoveAction, MoveSlot, OpponentPokemon, OwnPokemon, Position,
)

_ROOT = Path(__file__).resolve().parent.parent
_SPECIES_STATS = json.loads((_ROOT / "reference" / "species_stats.json").read_text(encoding="utf-8"))
_SPECIES_DATA = json.loads((_ROOT / "reference" / "species_data.json").read_text(encoding="utf-8"))

FORMAT = "gen9championsvgc2026regmb"
failures = []


def check(name: str, ok: bool, detail: str = ""):
    print(f"  {name} [{'ok' if ok else 'FAIL'}]{' ' + str(detail) if detail and not ok else ''}")
    if not ok:
        failures.append(name)


def own(species, moves, ability, item=None, position=None):
    base = _SPECIES_STATS[species]["base_stats"]
    return OwnPokemon(
        species=species, position=position,
        hp=base["hp"] + 75, max_hp=base["hp"] + 75,
        stats={k: base[k] + 20 for k in ("atk", "def", "spa", "spd", "spe")},
        ability=ability, item=item,
        moves=[MoveSlot(move=m, pp=16, max_pp=16) for m in moves],
    )


def opp(species, position, hp_pct=100.0, revealed_moves=()):
    return OpponentPokemon(species=species, position=position, hp_pct=hp_pct,
                           revealed_moves=list(revealed_moves))


def make_state(opp_hp_pct: float) -> BattleState:
    return BattleState(
        format_id=FORMAT, turn=4, field=FieldState(),
        opp_roster=["tyranitar", "charizard", "rotomwash", "talonflame", "gengar", "basculegion"],
        my_active=[
            own("charizard", ["heatwave", "airslash", "protect", "solarbeam"], "blaze",
                item="charizarditey", position=Position.LEFT),
            own("garchomp", ["earthquake", "dragonclaw", "protect", "swordsdance"], "roughskin",
                position=Position.RIGHT),
        ],
        my_bench=[
            own("clefable", ["moonblast", "protect", "thunderwave", "followme"], "magicguard"),
            own("annihilape", ["ragefist", "drainpunch", "protect", "finalgambit"], "defiant"),
        ],
        opp_active=[
            opp("tyranitar", Position.LEFT, opp_hp_pct, ["rockslide"]),
            opp("charizard", Position.RIGHT, opp_hp_pct),
        ],
        opp_bench=[],
    )


rng = random.Random(7)
bridge = EngineBridge(FORMAT)

print("solve on a fresh mid-battle position (2 determinized worlds)")
worlds = [sample_determinization(make_state(100.0), rng) for _ in range(2)]
t0 = time.perf_counter()
best, diag = solve_decision(bridge, worlds, iterations=24, depth_limit=1, per_slot_cap=6, rng=rng)
elapsed = time.perf_counter() - t0
print(f"  ({diag.step_count} engine rollouts in {elapsed:.1f}s -> {diag.step_count / elapsed:.0f} rollouts/s)")

check("zero engine choice rejections", diag.error_count == 0, diag.error_count)
total_prob = sum(p for _, p in diag.strategy)
check("root strategy is a distribution", abs(total_prob - 1.0) < 1e-6, total_prob)
check("pruned action space bounded", len(diag.strategy) <= 36, len(diag.strategy))
check("argmax has real mass", diag.strategy[0][1] > 0.0)

print("\nsanity decision: opponent actives at 1 HP -> attack, don't switch")
worlds_low = [sample_determinization(make_state(1.0), rng) for _ in range(2)]
best_low, diag_low = solve_decision(bridge, worlds_low, iterations=24, depth_limit=1, per_slot_cap=6, rng=rng)
check("zero rejections here too", diag_low.error_count == 0, diag_low.error_count)
check("both slots attack", isinstance(best_low.slot_left, MoveAction) and isinstance(best_low.slot_right, MoveAction),
      f"{type(best_low.slot_left).__name__}/{type(best_low.slot_right).__name__}")

bridge.close()
print(f"\n{'PASS' if not failures else 'FAIL: ' + ', '.join(failures)}")
