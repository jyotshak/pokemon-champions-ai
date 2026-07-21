"""End-to-end team-preview solver pipeline test, no local Showdown server
needed: hand-built pre-battle BattleState -> sample_team_preview_world (K
worlds) -> TeamPreviewGame (real Sim.Battle rollouts, depth_limit=2: team
preview resolves at depth 1 through the real engine, a real turn-1 move
exchange resolves at depth 2, hp_leaf_value cuts there) -> external-
sampling MCCFR -> TeamPreviewAction.

Three things this asserts:
1. Zero engine choice/rejections across every rollout, valid root
   strategy over the pruned team-preview action space.
2. The full-pipeline bug-regression test: the real Archaludon+Metagross-
   vs-Garchomp scenario (2026-07-18) that motivated building this at
   all, through determinize -> prune -> CFR -> engine end to end - the
   solver's top-probability action must not lead them together.
3. Rollout throughput and wall-clock time at realistic settings (the
   number that decides whether depth_limit=2 is actually affordable -
   see docs/solver_design.md's team-preview section).

Run from the project root: python -m engine.test_team_preview_integration
"""

import json
import random
import time
from pathlib import Path

from belief.determinize import sample_team_preview_world
from engine.bridge import EngineBridge
from engine.pool import EngineBridgePool
from model.solver_game import solve_team_preview_decision, solve_team_preview_decision_parallel
from schema.battle_state import BattleState, FieldState, MoveSlot, OwnPokemon, TeamPreviewInfo

_ROOT = Path(__file__).resolve().parent.parent
_SPECIES_DATA = json.loads((_ROOT / "reference" / "species_data.json").read_text(encoding="utf-8"))

FORMAT = "gen9championsvgc2026regmb"
failures = []


def check(name: str, ok: bool, detail: str = ""):
    print(f"  {name} [{'ok' if ok else 'FAIL'}]{' ' + str(detail) if detail and not ok else ''}")
    if not ok:
        failures.append(name)


def own(species: str, ability: str = "intimidate") -> OwnPokemon:
    return OwnPokemon(
        species=species, hp=180, max_hp=180,
        stats={"atk": 120, "def": 120, "spa": 120, "spd": 120, "spe": 120},
        ability=ability,
        moves=[MoveSlot(move=m, pp=16, max_pp=16) for m in _SPECIES_DATA[species]["moves"][:4]],
    )


def tp_battle_state(my_roster: list[str], opp_roster: list[str]) -> BattleState:
    my_bench = [own(s) for s in my_roster]
    return BattleState(
        format_id=FORMAT, turn=0, field=FieldState(),
        team_preview=TeamPreviewInfo(my_team=[m.species for m in my_bench], opp_team=opp_roster),
        opp_roster=opp_roster,
        my_active=[], my_bench=my_bench, opp_active=[], opp_bench=[],
    )


rng = random.Random(11)

print("correctness smoke test (single bridge, small settings)")
GENERIC_MY = ["garchomp", "incineroar", "clefable", "annihilape", "tyranitar", "skarmory"]
GENERIC_OPP = ["charizard", "sylveon", "archaludon", "pelipper", "grimmsnarl", "metagross"]
generic_state = tp_battle_state(GENERIC_MY, GENERIC_OPP)
worlds = [sample_team_preview_world(generic_state, rng) for _ in range(2)]

bridge = EngineBridge(FORMAT)
t0 = time.perf_counter()
best, diag = solve_team_preview_decision(
    bridge, worlds, iterations=8, depth_limit=2, tp_bring_cap=4, tp_lead_cap=2, turn_cap=6, rng=rng,
)
elapsed = time.perf_counter() - t0
print(f"  {diag.step_count} engine rollouts in {elapsed:.1f}s ({diag.step_count / elapsed:.0f}/s)")
check("zero engine choice rejections", diag.error_count == 0, diag.error_count)
total_prob = sum(p for _, p in diag.strategy)
check("root strategy is a distribution", abs(total_prob - 1.0) < 1e-6, total_prob)
check("action space bounded (<= tp_bring_cap*tp_lead_cap)", len(diag.strategy) <= 8, len(diag.strategy))
check("argmax has real mass", diag.strategy[0][1] > 0.0)
check("chosen action is schema-valid", len(best.bring) == 4 and len(best.lead_order) == 2)
bridge.close()

print("\nfull-pipeline bug regression: Archaludon+Metagross-vs-Garchomp (2026-07-18)")
BUG_MY = ["archaludon", "metagross", "swampert", "grimmsnarl", "pelipper", "sinistcha"]
BUG_OPP = ["garchomp", "kingambit", "sylveon", "charizard", "incineroar", "aerodactyl"]
bug_state = tp_battle_state(BUG_MY, BUG_OPP)
bug_worlds = [sample_team_preview_world(bug_state, rng) for _ in range(3)]

bridge2 = EngineBridge(FORMAT)
t0 = time.perf_counter()
bug_best, bug_diag = solve_team_preview_decision(
    bridge2, bug_worlds, iterations=16, depth_limit=2, tp_bring_cap=6, tp_lead_cap=2, turn_cap=6, rng=rng,
)
bug_elapsed = time.perf_counter() - t0
print(f"  {bug_diag.step_count} engine rollouts in {bug_elapsed:.1f}s -> "
      f"top action bring={bug_best.bring} lead_order={bug_best.lead_order}")
check("zero engine choice rejections", bug_diag.error_count == 0, bug_diag.error_count)
archaludon_idx = BUG_MY.index("archaludon")
metagross_idx = BUG_MY.index("metagross")
check(
    "solver's top-probability action does not lead Archaludon+Metagross together",
    set(bug_best.lead_order) != {archaludon_idx, metagross_idx},
    bug_best.lead_order,
)
bridge2.close()

print("\ncost measurement at realistic settings (pool of 8, the number that decides depth_limit=2 viability)")
pool = EngineBridgePool(FORMAT, 8)
realistic_worlds = [sample_team_preview_world(bug_state, rng) for _ in range(3)]
for iterations in (16, 24):
    t0 = time.perf_counter()
    _, diag_r = solve_team_preview_decision_parallel(
        pool, realistic_worlds, iterations=iterations, depth_limit=2,
        tp_bring_cap=6, tp_lead_cap=2, turn_cap=6, rng=rng,
    )
    elapsed_r = time.perf_counter() - t0
    print(f"  iterations={iterations}: {diag_r.step_count} rollouts in {elapsed_r:.1f}s "
          f"({diag_r.step_count / elapsed_r:.0f}/s), errors={diag_r.error_count}")
    check(f"iterations={iterations}: zero engine choice rejections", diag_r.error_count == 0, diag_r.error_count)
pool.close()

print(f"\n{'PASS' if not failures else 'FAIL: ' + ', '.join(failures)}")
