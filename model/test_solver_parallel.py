"""Validates parallel-solve correctness in isolation, no engine process
needed:

1. _merge_regret_tables is a pure unit: sums matching keys, includes
   keys present in only one table as-is, raises on an action-count
   mismatch (a real bug it would otherwise mask silently).
2. On a toy matrix-world game with a known equilibrium (reused from
   test_mccfr.py's setup): splitting the SAME total iteration count
   across several independent workers and merging their regret tables
   converges to the same equilibrium as one worker running all the
   iterations sequentially - confirming the parallelization is a valid
   approximation, not just "doesn't crash".

Run from the project root: python -m model.test_solver_parallel
"""

import random

from model.mccfr import ExternalSamplingSolver
from model.regret import RegretNode
from model.solver_game import _merge_regret_tables

failures = []


def check(name: str, ok: bool, detail: str = ""):
    print(f"  {name} [{'ok' if ok else 'FAIL'}]{' ' + str(detail) if detail and not ok else ''}")
    if not ok:
        failures.append(name)


print("_merge_regret_tables unit tests")
a = RegretNode(2)
a.cumulative_regret = [1.0, -2.0]
a.cumulative_strategy = [3.0, 4.0]
b = RegretNode(2)
b.cumulative_regret = [0.5, 1.0]
b.cumulative_strategy = [1.0, 1.0]
merged = _merge_regret_tables([{"k": a}, {"k": b}])
check("sums matching keys' regret", merged["k"].cumulative_regret == [1.5, -1.0], merged["k"].cumulative_regret)
check("sums matching keys' strategy", merged["k"].cumulative_strategy == [4.0, 5.0], merged["k"].cumulative_strategy)

only_in_one = _merge_regret_tables([{"k": a}, {"other": b}])
check("key present in only one table included as-is",
      only_in_one["k"].cumulative_regret == [1.0, -2.0] and only_in_one["other"].cumulative_regret == [0.5, 1.0])

bad = RegretNode(3)
try:
    _merge_regret_tables([{"k": a}, {"k": bad}])
    check("raises on action-count mismatch", False)
except ValueError:
    check("raises on action-count mismatch", True)


print("\nparallel split-and-merge converges to the same equilibrium as one sequential solve")


class MatrixWorldGame:
    """Same fixture shape as test_mccfr.py: one simultaneous turn, the
    opponent knows the world, I don't. Asymmetric mixed equilibrium
    (row 2/3-1/3, col 1/2-1/2), so a wrong merge would visibly miss it.
    """

    def __init__(self, matrices):
        self.matrices = matrices

    def worlds(self):
        return [(("root", w), prob) for w, (_, prob) in enumerate(self.matrices)]

    def is_terminal(self, state):
        return state[1] if state[0] == "done" else None

    def leaf_value(self, state):
        raise AssertionError("depth limit should never bind in a one-turn game")

    def my_actions(self, state):
        return list(range(len(self.matrices[0][0])))

    def opp_actions(self, state):
        return list(range(len(self.matrices[0][0][0])))

    def step(self, state, my_action, opp_action, rng):
        return ("done", self.matrices[state[1]][0][my_action][opp_action])

    def my_key(self, state):
        return "root"

    def opp_key(self, state):
        return ("root", state[1])


mixed = [([[0.0, 2.0], [3.0, -1.0]], 1.0)]
TOTAL_ITERATIONS = 60_000

baseline_game = MatrixWorldGame(mixed)
baseline_solver = ExternalSamplingSolver(baseline_game, depth_limit=5, rng=random.Random(1))
baseline_strategy = baseline_solver.run(TOTAL_ITERATIONS)
check("baseline (single sequential solve) finds the known equilibrium",
      abs(baseline_strategy[0] - 2 / 3) < 0.02, baseline_strategy)

N_WORKERS = 6
per_worker = TOTAL_ITERATIONS // N_WORKERS
worker_solvers = []
for i in range(N_WORKERS):
    game = MatrixWorldGame(mixed)
    solver = ExternalSamplingSolver(game, depth_limit=5, rng=random.Random(100 + i))
    solver.run(per_worker, traverser_offset=i % 2)
    worker_solvers.append(solver)

merged_my = _merge_regret_tables([s.my_nodes for s in worker_solvers])
merged_strategy = merged_my[worker_solvers[0].root_key].average_strategy()
check("merged parallel solve (6 workers) also finds the known equilibrium",
      abs(merged_strategy[0] - 2 / 3) < 0.03, merged_strategy)
check("merged strategy close to the true sequential baseline",
      abs(merged_strategy[0] - baseline_strategy[0]) < 0.03,
      f"merged={merged_strategy} baseline={baseline_strategy}")

print(f"\n{'PASS' if not failures else 'FAIL: ' + ', '.join(failures)}")
