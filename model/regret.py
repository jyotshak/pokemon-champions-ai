"""Regret-matching core for the CFR-based solver. Engine-agnostic and
game-agnostic: a RegretNode is just a bag of cumulative regrets/strategy
weights over N abstract actions, and solve_matrix_game() runs plain
regret-matching self-play on a fully-known two-player zero-sum payoff
matrix. The Pokemon-specific tree (external-sampling traversal, node
keying, determinizations) is built on top of this, not inside it.

Two standard CFR facts this module encodes, so consumers don't have to
re-learn them:
- The strategy that converges to equilibrium is the *time-averaged* one
  (average_strategy), not the current iterate (current_strategy), which
  can oscillate forever.
- Regret matching plays proportional to positive cumulative regret, and
  uniform when nothing is positive yet.
"""

from __future__ import annotations


def _uniform(n: int) -> list[float]:
    return [1.0 / n] * n


class RegretNode:
    """Cumulative regret + average-strategy accumulator for one decision
    point with a fixed list of N actions. Knows nothing about what the
    actions are — callers keep their own index -> action mapping.
    """

    def __init__(self, n_actions: int):
        if n_actions < 1:
            raise ValueError("a decision node needs at least one action")
        self.n_actions = n_actions
        self.cumulative_regret = [0.0] * n_actions
        self.cumulative_strategy = [0.0] * n_actions

    def current_strategy(self) -> list[float]:
        positive = [r if r > 0.0 else 0.0 for r in self.cumulative_regret]
        total = sum(positive)
        if total <= 0.0:
            return _uniform(self.n_actions)
        return [p / total for p in positive]

    def update_regret(self, action_values: list[float], node_value: float, weight: float = 1.0) -> None:
        """Add instantaneous regret (how much better each action would have
        done than what the current strategy actually achieved). `weight` is
        the reach/sample probability weighting used by CFR variants; 1.0
        for plain matrix-game self-play.
        """
        for i, av in enumerate(action_values):
            self.cumulative_regret[i] += weight * (av - node_value)

    def accumulate_strategy(self, strategy: list[float], weight: float = 1.0) -> None:
        for i, p in enumerate(strategy):
            self.cumulative_strategy[i] += weight * p

    def average_strategy(self) -> list[float]:
        total = sum(self.cumulative_strategy)
        if total <= 0.0:
            return _uniform(self.n_actions)
        return [w / total for w in self.cumulative_strategy]


def solve_matrix_game(payoffs: list[list[float]], iterations: int) -> tuple[list[float], list[float]]:
    """Solve a two-player zero-sum matrix game by regret-matching self-play.

    payoffs[i][j] = ROW player's payoff when row plays i and column plays j
    (column player receives the negation). Returns (row_strategy,
    col_strategy) — the time-averaged strategies, which converge to a Nash
    equilibrium as iterations grow.

    This full-expectation version (no sampling) is for small matrices:
    the base-mechanic tests, and later the per-node subgame at the root
    where exact values per cell are affordable. The big-tree traversal
    uses the same RegretNode but with sampled counterfactual values.
    """
    n_rows = len(payoffs)
    n_cols = len(payoffs[0])
    row = RegretNode(n_rows)
    col = RegretNode(n_cols)

    for _ in range(iterations):
        s_row = row.current_strategy()
        s_col = col.current_strategy()

        row_action_values = [
            sum(s_col[j] * payoffs[i][j] for j in range(n_cols)) for i in range(n_rows)
        ]
        col_action_values = [
            sum(s_row[i] * -payoffs[i][j] for i in range(n_rows)) for j in range(n_cols)
        ]
        row_value = sum(s_row[i] * row_action_values[i] for i in range(n_rows))
        col_value = -row_value

        row.update_regret(row_action_values, row_value)
        col.update_regret(col_action_values, col_value)
        row.accumulate_strategy(s_row)
        col.accumulate_strategy(s_col)

    return row.average_strategy(), col.average_strategy()


def best_response_value(payoffs: list[list[float]], row_strategy: list[float], col_strategy: list[float]) -> tuple[float, float]:
    """(best row payoff vs col_strategy, best column payoff vs row_strategy).
    Their sum is the exploitability gap: 0 at an exact equilibrium, small
    positive when close. Used by tests to check convergence quality in a
    way that doesn't depend on knowing the equilibrium in closed form.
    """
    n_rows = len(payoffs)
    n_cols = len(payoffs[0])
    best_row = max(
        sum(col_strategy[j] * payoffs[i][j] for j in range(n_cols)) for i in range(n_rows)
    )
    best_col = max(
        sum(row_strategy[i] * -payoffs[i][j] for i in range(n_rows)) for j in range(n_cols)
    )
    return best_row, best_col
