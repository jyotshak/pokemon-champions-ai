"""Validates the regret-matching core against tiny matrix games with known
answers, before any Pokemon-specific structure is built on top of it:

1. Rock-paper-scissors -> both players' average strategies must converge
   to uniform (its unique equilibrium).
2. A game with a strictly dominant action -> all mass on that action.
3. An asymmetric 2x2 mixed game (Protect-mindgame shaped: each side must
   randomize or become exploitable) -> the known closed-form equilibrium.
4. Every game also gets an exploitability check: the sum of both sides'
   best-response payoffs against the average strategies must approach 0,
   which certifies "close to equilibrium" without needing the closed form.

Run from the project root: python -m model.test_regret
"""

from model.regret import best_response_value, solve_matrix_game

ITERATIONS = 200_000
failures = []


def check(name: str, actual: list[float], expected: list[float], tol: float = 0.02):
    ok = all(abs(a - e) <= tol for a, e in zip(actual, expected))
    status = "ok" if ok else "MISMATCH"
    print(f"  {name}: {[round(x, 3) for x in actual]} expected {expected} [{status}]")
    if not ok:
        failures.append(name)


def check_exploitability(name: str, payoffs: list[list[float]], row_s: list[float], col_s: list[float], tol: float = 0.02):
    best_row, best_col = best_response_value(payoffs, row_s, col_s)
    gap = best_row + best_col
    ok = gap <= tol
    print(f"  {name} exploitability gap: {gap:.4f} [{'ok' if ok else 'TOO EXPLOITABLE'}]")
    if not ok:
        failures.append(f"{name} exploitability")


print("rock-paper-scissors (unique equilibrium: uniform)")
rps = [
    [0.0, -1.0, 1.0],
    [1.0, 0.0, -1.0],
    [-1.0, 1.0, 0.0],
]
row_s, col_s = solve_matrix_game(rps, ITERATIONS)
check("row", row_s, [1 / 3, 1 / 3, 1 / 3])
check("col", col_s, [1 / 3, 1 / 3, 1 / 3])
check_exploitability("rps", rps, row_s, col_s)

print("\nstrict dominance (row action 0 always better)")
dominant = [
    [1.0, 2.0],
    [0.0, -1.0],
]
row_s, col_s = solve_matrix_game(dominant, ITERATIONS)
check("row", row_s, [1.0, 0.0])
# column's best reply to row playing action 0 is action 0 (concede 1, not 2)
check("col", col_s, [1.0, 0.0])
check_exploitability("dominance", dominant, row_s, col_s)

print("\nasymmetric mixed game (Protect-mindgame shape)")
# payoffs[i][j] for the row player; closed-form equilibrium:
# row plays (2/3, 1/3), column plays (1/2, 1/2), game value 1.
mixed = [
    [0.0, 2.0],
    [3.0, -1.0],
]
row_s, col_s = solve_matrix_game(mixed, ITERATIONS)
check("row", row_s, [2 / 3, 1 / 3])
check("col", col_s, [1 / 2, 1 / 2])
check_exploitability("mixed", mixed, row_s, col_s)

print(f"\n{'PASS' if not failures else 'FAIL: ' + ', '.join(failures)}")
