"""Solver vs heuristic on real popular teams (harness/team_sheet.py's
popularity-ranked scrape), generalizing run_solver_match.py's team-swap
pattern to arbitrary team-id pairups instead of the two hand-built teams.

Both players get the SAME search-based team-preview layer
(use_search_team_preview=True on both SolverPlayer and HeuristicPlayer) -
deliberately, so a pairup only differentiates on turn-by-turn play
(the actual thing being compared), not confounded by one side getting a
smarter lead/bring choice too.

Runs BOTH team assignments (N_GAMES_PER_SIDE each) per pairup, same
reasoning as run_solver_match.py: a single fixed assignment confounds
"solver plays better" with "this team is just stronger."

Run from the project root: python -m harness.run_popularity_pairup_match
(needs the local Showdown server running)
"""

import asyncio
import time
from pathlib import Path

from poke_env.ps_client.account_configuration import AccountConfiguration
from poke_env.teambuilder import ConstantTeambuilder

from harness.doubles_smoke_test import FORMAT
from harness.heuristic_player import HeuristicPlayer
from harness.solver_player import SolverPlayer
from harness.team_sheet import team_by_id

N_GAMES_PER_SIDE = 5
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "logs"

PAIRUPS = [("MB501", "MB496")]  # Trick Room (MB501) vs Tailwind/sun (MB496)

# Turn-search / team-preview iteration budgets. Bumped from the old 16/24
# (2026-07-20) alongside the leaf-value field terms + my-side team-preview
# move-awareness: at 16 the root strategy was near-flat ("top-3 probs:
# 0.11, 0.07, 0.06"), i.e. barely converged, so the argmax was close to
# arbitrary among plausible moves and biased toward immediate damage
# (all the crude HP leaf could see). More iterations let the now-richer
# leaf/pruning signal actually separate the candidates. Games were ~50s
# at 16; ~32 roughly doubles that - still affordable for a batch.
ITERATIONS = 32
TP_ITERATIONS = 32


async def run_one_game(tag: str, game_index: int, solver_team: str, heuristic_team: str) -> tuple[str, bool]:
    solver = SolverPlayer(
        battle_format=FORMAT, team=ConstantTeambuilder(solver_team), accept_open_team_sheet=False,
        account_configuration=AccountConfiguration(f"s{tag}", None),
        n_worlds=3, iterations=ITERATIONS, depth_limit=2, per_slot_cap=6, n_workers=8,
        solver_seed=game_index, use_search_team_preview=True, tp_iterations=TP_ITERATIONS,
    )
    baseline = HeuristicPlayer(
        battle_format=FORMAT, team=ConstantTeambuilder(heuristic_team), accept_open_team_sheet=False,
        account_configuration=AccountConfiguration(f"h{tag}", None),
        use_search_team_preview=True, solver_seed=game_index, n_workers=8, tp_iterations=TP_ITERATIONS,
    )
    await solver.battle_against(baseline, n_battles=1)
    won = solver.n_won_battles == 1
    log = solver.finalize_log(won)
    solver.pool.close()
    baseline.pool.close()
    return log, won


async def run_assignment(pairup_tag: str, solver_id: str, solver_team: str,
                          heuristic_id: str, heuristic_team: str) -> int:
    wins = 0
    for i in range(N_GAMES_PER_SIDE):
        tag = f"{int(time.time())}{i}"
        start = time.perf_counter()
        log, won = await run_one_game(tag, i, solver_team, heuristic_team)
        wins += won
        print(f"[{pairup_tag}] [solver={solver_id}] game {i + 1}/{N_GAMES_PER_SIDE}: "
              f"solver {'WON' if won else 'lost'} ({time.perf_counter() - start:.0f}s)", flush=True)

        result_tag = "won" if won else "lost"
        out_path = OUTPUT_DIR / f"popmatch_{pairup_tag}_solver{solver_id}_vs_heuristic{heuristic_id}_game{i + 1}_{result_tag}.txt"
        out_path.write_text(log, encoding="utf-8")

    print(f"\n[{pairup_tag}] solver ({solver_id}) won {wins}/{N_GAMES_PER_SIDE} vs heuristic ({heuristic_id})", flush=True)
    return wins


async def run_pairup(id_a: str, id_b: str) -> None:
    team_a = team_by_id(id_a)["paste"]
    team_b = team_by_id(id_b)["paste"]
    pairup_tag = f"{id_a}v{id_b}"

    a_solver_wins = await run_assignment(pairup_tag, id_a, team_a, id_b, team_b)
    b_solver_wins = await run_assignment(pairup_tag, id_b, team_b, id_a, team_a)

    total_games = 2 * N_GAMES_PER_SIDE
    a_side_total = a_solver_wins + (N_GAMES_PER_SIDE - b_solver_wins)
    print(
        f"\n=== {pairup_tag} summary ===\n"
        f"solver+{id_a} vs heuristic+{id_b}: {a_solver_wins}/{N_GAMES_PER_SIDE}\n"
        f"solver+{id_b} vs heuristic+{id_a}: {b_solver_wins}/{N_GAMES_PER_SIDE}\n"
        f"{id_a}-team side won {a_side_total}/{total_games} total (team-assignment effect, collapsing over pilot)\n"
        f"solver (either team) won {a_solver_wins + b_solver_wins}/{total_games} total "
        f"(pilot effect, collapsing over team assignment)\n", flush=True,
    )


async def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    for id_a, id_b in PAIRUPS:
        await run_pairup(id_a, id_b)


if __name__ == "__main__":
    asyncio.run(main())
