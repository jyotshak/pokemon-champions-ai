"""Validates the parallel engine pool against the real engine and measures
actual speedup vs the single-bridge path — the whole point of building
this. Not a permanent regression test (timing-sensitive, machine-
dependent); a one-off/rerunnable measurement script.

Run from the project root: python -m engine.test_pool_speedup
"""

import random
import time

from belief.determinize import sample_determinization
from engine.bridge import EngineBridge
from engine.pool import EngineBridgePool
from engine.test_solver_integration import make_state
from model.solver_game import solve_decision, solve_decision_parallel

FORMAT = "gen9championsvgc2026regmb"
DEPTH = 2
ITERATIONS = 16
N_WORKERS = 8

failures = []


def check(name: str, ok: bool, detail: str = ""):
    print(f"  {name} [{'ok' if ok else 'FAIL'}]{' ' + str(detail) if detail and not ok else ''}")
    if not ok:
        failures.append(name)


rng = random.Random(7)
worlds = [sample_determinization(make_state(100.0), rng) for _ in range(3)]

print(f"single bridge: depth={DEPTH} iterations={ITERATIONS}")
single_bridge = EngineBridge(FORMAT)
t0 = time.perf_counter()
best_single, diag_single = solve_decision(
    single_bridge, worlds, iterations=ITERATIONS, depth_limit=DEPTH, per_slot_cap=6, rng=rng,
)
single_elapsed = time.perf_counter() - t0
single_bridge.close()
print(f"  {diag_single.step_count} rollouts in {single_elapsed:.1f}s "
      f"({diag_single.step_count / single_elapsed:.0f}/s), errors={diag_single.error_count}")
check("single-bridge path: zero errors", diag_single.error_count == 0, diag_single.error_count)

print(f"\npool of {N_WORKERS}: depth={DEPTH} iterations={ITERATIONS}")
t0 = time.perf_counter()
pool = EngineBridgePool(FORMAT, N_WORKERS)
pool_startup = time.perf_counter() - t0
print(f"  pool startup: {pool_startup:.1f}s (one-time cost, amortized across a whole match)")

t0 = time.perf_counter()
best_pool, diag_pool = solve_decision_parallel(
    pool, worlds, iterations=ITERATIONS, depth_limit=DEPTH, per_slot_cap=6, rng=rng,
)
pool_elapsed = time.perf_counter() - t0
print(f"  {diag_pool.step_count} rollouts in {pool_elapsed:.1f}s "
      f"({diag_pool.step_count / pool_elapsed:.0f}/s), errors={diag_pool.error_count}")
check("pool path: zero errors", diag_pool.error_count == 0, diag_pool.error_count)

print(f"\nspeedup (solve time only, excludes one-time pool startup): "
      f"{single_elapsed / pool_elapsed:.1f}x")
check("meaningful speedup (>=3x with 8 workers)", single_elapsed / pool_elapsed >= 3.0,
      f"{single_elapsed / pool_elapsed:.1f}x")

# A second decision on the SAME pool, to show startup cost doesn't recur
t0 = time.perf_counter()
best_pool2, diag_pool2 = solve_decision_parallel(
    pool, worlds, iterations=ITERATIONS, depth_limit=DEPTH, per_slot_cap=6, rng=rng,
)
second_elapsed = time.perf_counter() - t0
print(f"\nsecond decision on same (already-warm) pool: {second_elapsed:.1f}s, "
      f"errors={diag_pool2.error_count}")
check("second decision also zero errors", diag_pool2.error_count == 0, diag_pool2.error_count)

pool.close()
print(f"\n{'PASS' if not failures else 'FAIL: ' + ', '.join(failures)}")
