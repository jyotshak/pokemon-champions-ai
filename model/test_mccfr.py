"""Validates the external-sampling MCCFR solver on tiny stub games with
known answers, before any Pokemon-specific structure exists:

1. Single-world RPS with noisy payoffs -> uniform (traversal reduces to
   the plain matrix case; sampled chance denoises across iterations).
2. Two-world decision problem -> the anti-strategy-fusion check with an
   exact number: naive per-world solving + averaging provably scores
   1.0, the correct joint solve scores 1.5.
3. Two-world Bayesian matrix game (opponent knows the world, I don't) ->
   known equilibrium (1/2, 1/2) worth 0.25 guaranteed; the naive fused
   strategy (3/4, 1/4) only guarantees 0.125.
4. Two-round matching pennies -> uniform everywhere, value ~0 (recursion
   and per-turn node keying).
5. Depth-limited game where only leaf_value differentiates actions ->
   solver must follow the leaf signal (depth cutoff path works).

Run from the project root: python -m model.test_mccfr
"""

import random

from model.mccfr import ExternalSamplingSolver

failures = []


def check(name: str, actual: list[float], expected: list[float], tol: float):
    ok = all(abs(a - e) <= tol for a, e in zip(actual, expected))
    print(f"  {name}: {[round(x, 3) for x in actual]} expected {[round(e, 3) for e in expected]} [{'ok' if ok else 'MISMATCH'}]")
    if not ok:
        failures.append(name)


def check_value(name: str, actual: float, minimum: float):
    ok = actual >= minimum
    print(f"  {name}: {actual:.4f} (needs >= {minimum}) [{'ok' if ok else 'TOO LOW'}]")
    if not ok:
        failures.append(name)


class MatrixWorldGame:
    """One simultaneous turn. Each world is a payoff matrix (my POV);
    the opponent knows which matrix is live, I don't. Optional zero-mean
    payoff noise exercises the sampled-chance path without moving the
    equilibrium (which depends on expected payoffs only).
    States: ("root", world_id) or ("done", payoff).
    """

    def __init__(self, matrices: list[tuple[list[list[float]], float]], noise: float = 0.0):
        self.matrices = matrices
        self.noise = noise

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
        matrix = self.matrices[state[1]][0]
        payoff = matrix[my_action][opp_action]
        if self.noise:
            payoff += rng.uniform(-self.noise, self.noise)
        return ("done", payoff)

    def my_key(self, state):
        return "root"  # I cannot tell worlds apart

    def opp_key(self, state):
        return ("root", state[1])  # they know their own world


def bayes_value(matrices, x):
    """Exact value my mixed strategy x guarantees when the opponent knows
    the world and best-responds in each: sum_w p(w) * min_col x.M_w[:,j].
    """
    total = 0.0
    for matrix, prob in matrices:
        n_cols = len(matrix[0])
        total += prob * min(
            sum(x[i] * matrix[i][j] for i in range(len(matrix))) for j in range(n_cols)
        )
    return total


print("1. single-world RPS, noisy payoffs (equilibrium: uniform)")
rps = MatrixWorldGame(
    [([[0, -1, 1], [1, 0, -1], [-1, 1, 0]], 1.0)],
    noise=0.5,
)
solver = ExternalSamplingSolver(rps, depth_limit=5, rng=random.Random(1))
strategy = solver.run(60_000)
check("my strategy", strategy, [1 / 3, 1 / 3, 1 / 3], tol=0.03)


print("\n2. anti-fusion decision problem (worlds: reward (1,0) vs (0,3), 50/50)")
# Per-world solves pick action 0 in world 1 and action 1 in world 2;
# averaging those gives (0.5, 0.5) worth 0.5*0.5*1 + 0.5*0.5*3 = 1.0.
# The correct single strategy is pure action 1, worth 0.5*0 + 0.5*3 = 1.5.
fusion = MatrixWorldGame([
    ([[1.0], [0.0]], 0.5),
    ([[0.0], [3.0]], 0.5),
])
solver = ExternalSamplingSolver(fusion, depth_limit=5, rng=random.Random(2))
strategy = solver.run(60_000)
check("my strategy", strategy, [0.0, 1.0], tol=0.02)
ev_solver = 0.5 * (strategy[0] * 1.0) + 0.5 * (strategy[1] * 3.0)
ev_naive = 1.0
check_value("solver EV (naive fused strategy scores 1.0)", ev_solver, 1.45)


print("\n3. Bayesian matrix game (world 1: matching pennies; world 2: top row dominates)")
# Closed form: V(x) = 0.5*(-|2x-1|) + 0.5*x, maximized at x = 1/2, value 1/4.
# Naive fusion: world equilibria (1/2,1/2) and (1,0) average to (3/4,1/4),
# which only guarantees V(3/4) = 1/8 against a world-aware opponent.
bayes_matrices = [
    ([[1.0, -1.0], [-1.0, 1.0]], 0.5),
    ([[1.0, 1.0], [0.0, 0.0]], 0.5),
]
bayes = MatrixWorldGame(bayes_matrices)
solver = ExternalSamplingSolver(bayes, depth_limit=5, rng=random.Random(3))
strategy = solver.run(200_000)
check("my strategy", strategy, [0.5, 0.5], tol=0.05)
v_solver = bayes_value(bayes_matrices, strategy)
v_naive = bayes_value(bayes_matrices, [0.75, 0.25])
print(f"  guaranteed value: solver {v_solver:.4f} vs naive fused {v_naive:.4f} (optimum 0.25)")
check_value("solver guaranteed value", v_solver, 0.22)
if not v_naive < v_solver:
    failures.append("naive should be strictly worse")


class TwoRoundPennies:
    """Two consecutive rounds of matching pennies, one world. Terminal
    value is the normalized sum. Uniform play everywhere is the unique
    equilibrium, value 0. Exercises recursion + per-turn node keying.
    States: (round, cumulative_payoff).
    """

    MATRIX = [[1.0, -1.0], [-1.0, 1.0]]

    def worlds(self):
        return [((0, 0.0), 1.0)]

    def is_terminal(self, state):
        rnd, cum = state
        return cum / 2.0 if rnd == 2 else None

    def leaf_value(self, state):
        return state[1] / 2.0

    def my_actions(self, state):
        return [0, 1]

    def opp_actions(self, state):
        return [0, 1]

    def step(self, state, my_action, opp_action, rng):
        rnd, cum = state
        return (rnd + 1, cum + self.MATRIX[my_action][opp_action])

    def my_key(self, state):
        return state  # public: round + running score

    def opp_key(self, state):
        return state


print("\n4. two-round matching pennies (uniform everywhere, value 0)")
pennies = TwoRoundPennies()
solver = ExternalSamplingSolver(pennies, depth_limit=2, rng=random.Random(4))
strategy = solver.run(100_000)
check("root strategy", strategy, [0.5, 0.5], tol=0.03)
for key, node in solver.my_nodes.items():
    avg = node.average_strategy()
    if abs(avg[0] - 0.5) > 0.05:
        failures.append(f"non-uniform interior node {key}: {avg}")
print(f"  interior nodes created: {len(solver.my_nodes)} (all ~uniform: "
      f"{'yes' if not any(f.startswith('non-uniform') for f in failures) else 'NO'})")


class LeafBiasGame:
    """Never terminates within the depth limit — only leaf_value tells the
    actions apart (+1 if my first action was 0, else -1). The solver must
    follow the leaf signal: checks the depth-cutoff path actually steers.
    """

    def worlds(self):
        return [("root", 1.0)]

    def is_terminal(self, state):
        return None

    def leaf_value(self, state):
        return 1.0 if state == ("mid", 0) else -1.0

    def my_actions(self, state):
        return [0, 1]

    def opp_actions(self, state):
        return [0]

    def step(self, state, my_action, opp_action, rng):
        return ("mid", my_action)

    def my_key(self, state):
        return state

    def opp_key(self, state):
        return state


print("\n5. depth-cutoff leaf steering (leaf prefers action 0)")
solver = ExternalSamplingSolver(LeafBiasGame(), depth_limit=1, rng=random.Random(5))
strategy = solver.run(20_000)
check("my strategy", strategy, [1.0, 0.0], tol=0.02)


print(f"\n{'PASS' if not failures else 'FAIL: ' + ', '.join(failures)}")
