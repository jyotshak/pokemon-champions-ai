"""The real skill test for the replay-net direction ([[imitation-net-v1]]):
NetPlayer (depth-1, Tier-1-pruned, mixed-strategy, value-converged v2) vs
SolverPlayer (engine-backed MCCFR) on DIVERSE, non-mirror teams - unlike the
earlier MB552 mirror match, this actually differentiates skill instead of
mostly measuring speed-tie coin flips on an all-OHKO roster ([[imitation-
net-v1]]'s diagnostics).

Runs BOTH team assignments (net gets Aero, then net gets Swampert) so a
lopsided result can't be confounded with "one team is just stronger" - the
same 2026-07-18 lesson from run_solver_match.py's own non-mirror redesign.
Both sides use the SAME search-based team preview (NetPlayer borrows
SolverPlayer's own team-preview solve), so team-building is controlled for
too - the per-turn decision engine is the only variable.

Start the local server first:
  node vendor/pokemon-showdown/pokemon-showdown start --no-security

  python -m harness.run_net_vs_solver_diverse            # default N_GAMES_PER_SIDE each
  python -m harness.run_net_vs_solver_diverse 8           # override games per side
"""

import asyncio
import sys
import time
import uuid
from pathlib import Path

from poke_env.ps_client.account_configuration import AccountConfiguration
from poke_env.teambuilder import ConstantTeambuilder

from harness.doubles_smoke_test import FORMAT
from harness.net_player import NetPlayer
from harness.solver_player import SolverPlayer
from harness.teams import TEAM_AERO_HO, TEAM_SWAMPERT_TR
from model.net_infer import NetEvaluator

N_GAMES_PER_SIDE = int(sys.argv[1]) if len(sys.argv) > 1 else 6
CHECKPOINT = "model/checkpoints/imitation_v4.pt"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "logs"
EVALUATOR = NetEvaluator(CHECKPOINT)   # one shared model for the whole batch


async def run_one_game(game_index: int, net_team: str, solver_team: str) -> tuple[str, bool]:
    tag = uuid.uuid4().hex[:8]
    net = NetPlayer(
        battle_format=FORMAT, team=ConstantTeambuilder(net_team), accept_open_team_sheet=False,
        account_configuration=AccountConfiguration(f"n{tag}", None),
        evaluator=EVALUATOR, n_worlds=3, k_my=4, k_opp=4, solver_seed=game_index,
        use_search_team_preview=True, n_workers=8,
    )
    solver = SolverPlayer(
        battle_format=FORMAT, team=ConstantTeambuilder(solver_team), accept_open_team_sheet=False,
        account_configuration=AccountConfiguration(f"s{tag}", None),
        n_worlds=3, iterations=16, depth_limit=2, per_slot_cap=6, n_workers=8,
        solver_seed=game_index, use_search_team_preview=True,
    )
    try:
        await net.battle_against(solver, n_battles=1)
        won = net.n_won_battles == 1
        return net.finalize_log(won), won
    finally:
        net.close()
        solver.pool.close()


async def run_assignment(net_gets_aero: bool) -> int:
    net_team, net_name = (TEAM_AERO_HO, "aero") if net_gets_aero else (TEAM_SWAMPERT_TR, "swampert")
    solver_team, solver_name = (TEAM_SWAMPERT_TR, "swampert") if net_gets_aero else (TEAM_AERO_HO, "aero")

    wins = 0
    for i in range(N_GAMES_PER_SIDE):
        start = time.perf_counter()
        log, won = await run_one_game(i, net_team, solver_team)
        wins += won
        print(f"[net={net_name} vs solver={solver_name}] game {i + 1}/{N_GAMES_PER_SIDE}: "
              f"net {'WON ' if won else 'lost'} ({time.perf_counter() - start:.0f}s)   "
              f"running: {wins}/{i + 1}", flush=True)
        out = OUTPUT_DIR / f"net_{net_name}_vs_solver_{solver_name}_game{i + 1}_{'won' if won else 'lost'}.txt"
        out.write_text(log, encoding="utf-8")

    print(f"\nnet ({net_name}) vs solver ({solver_name}): {wins}/{N_GAMES_PER_SIDE}\n", flush=True)
    return wins


async def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    aero_wins = await run_assignment(net_gets_aero=True)
    swampert_wins = await run_assignment(net_gets_aero=False)
    total = aero_wins + swampert_wins
    n_total = 2 * N_GAMES_PER_SIDE
    print(f"=== NetPlayer (depth-1, v2) vs SolverPlayer (MCCFR), diverse teams: "
          f"{total}/{n_total} ({100.0 * total / n_total:.0f}%) ===")
    print(f"    aero: {aero_wins}/{N_GAMES_PER_SIDE}   swampert: {swampert_wins}/{N_GAMES_PER_SIDE}")
    print("    50% = the two decision engines are equally strong.")


if __name__ == "__main__":
    asyncio.run(main())
