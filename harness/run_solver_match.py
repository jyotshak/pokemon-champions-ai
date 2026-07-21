"""The integration milestone match: SolverPlayer (CFR + real-engine
rollouts) vs the greedy HeuristicPlayer baseline, on the local Showdown
server (start it first: node vendor/pokemon-showdown/pokemon-showdown
start --no-security). Each side gets a DIFFERENT real team (harness/
teams.py's TEAM_AERO_HO / TEAM_SWAMPERT_TR) rather than a mirror match —
see docs/solver_design.md and memory: the mirror-match testing gap found
2026-07-18, team preview is deterministic given a roster so identical
rosters on both sides meant team-building never differentiated solver
from heuristic in any earlier test run.

Runs BOTH team assignments (N_GAMES_PER_SIDE each) in one go, since a
single fixed assignment confounds "solver plays better" with "this team
is just stronger" (confirmed 2026-07-18: solver+Aero went 18/20, then
solver+Swampert went 0/20 - whichever side had Aero won almost every
game regardless of pilot). Every game's full log is written to logs/, not
just a sample, so a lopsided result can actually be diagnosed turn by
turn afterward.
"""

import asyncio
import time
from pathlib import Path

from poke_env.ps_client.account_configuration import AccountConfiguration
from poke_env.teambuilder import ConstantTeambuilder

from harness.doubles_smoke_test import FORMAT
from harness.heuristic_player import HeuristicPlayer
from harness.solver_player import SolverPlayer
from harness.teams import TEAM_AERO_HO, TEAM_SWAMPERT_TR

N_GAMES_PER_SIDE = 5
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "logs"


async def run_one_game(tag: str, game_index: int, solver_team: str, heuristic_team: str) -> tuple[str, bool]:
    solver = SolverPlayer(
        battle_format=FORMAT, team=ConstantTeambuilder(solver_team), accept_open_team_sheet=False,
        account_configuration=AccountConfiguration(f"s{tag}", None),
        n_worlds=3, iterations=16, depth_limit=2, per_slot_cap=6, n_workers=8,
        solver_seed=game_index,
    )
    baseline = HeuristicPlayer(
        battle_format=FORMAT, team=ConstantTeambuilder(heuristic_team), accept_open_team_sheet=False,
        account_configuration=AccountConfiguration(f"h{tag}", None),
    )
    await solver.battle_against(baseline, n_battles=1)
    won = solver.n_won_battles == 1
    log = solver.finalize_log(won)
    solver.pool.close()
    return log, won


async def run_assignment(solver_gets_aero: bool) -> int:
    solver_team, solver_name = (TEAM_AERO_HO, "aero") if solver_gets_aero else (TEAM_SWAMPERT_TR, "swampert")
    heuristic_team, heuristic_name = (TEAM_SWAMPERT_TR, "swampert") if solver_gets_aero else (TEAM_AERO_HO, "aero")

    wins = 0
    for i in range(N_GAMES_PER_SIDE):
        tag = f"{int(time.time())}{i}"
        start = time.perf_counter()
        log, won = await run_one_game(tag, i, solver_team, heuristic_team)
        wins += won
        print(f"[solver={solver_name}] game {i + 1}/{N_GAMES_PER_SIDE}: solver {'WON' if won else 'lost'} "
              f"({time.perf_counter() - start:.0f}s)")

        result_tag = "won" if won else "lost"
        out_path = OUTPUT_DIR / f"solver_{solver_name}_vs_heuristic_{heuristic_name}_game{i + 1}_{result_tag}.txt"
        out_path.write_text(log, encoding="utf-8")

    print(f"\nsolver ({solver_name}) won {wins}/{N_GAMES_PER_SIDE} vs heuristic ({heuristic_name}) baseline")
    return wins


async def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    aero_solver_wins = await run_assignment(solver_gets_aero=True)
    swampert_solver_wins = await run_assignment(solver_gets_aero=False)

    print(
        f"\n=== summary ===\n"
        f"solver+aero vs heuristic+swampert: {aero_solver_wins}/{N_GAMES_PER_SIDE}\n"
        f"solver+swampert vs heuristic+aero: {swampert_solver_wins}/{N_GAMES_PER_SIDE}\n"
        f"aero-team side won {aero_solver_wins + (N_GAMES_PER_SIDE - swampert_solver_wins)}"
        f"/{2 * N_GAMES_PER_SIDE} total (team-assignment effect, collapsing over pilot)"
    )


if __name__ == "__main__":
    asyncio.run(main())
