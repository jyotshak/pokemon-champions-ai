"""Milestone match for the replay-net direction ([[imitation-net-v1]]):
NetPlayer (depth-1 net policy+value search) vs the greedy HeuristicPlayer
baseline, on the local Showdown server (start it first:
  node vendor/pokemon-showdown/pokemon-showdown start --no-security).

Mirrors run_solver_match.py exactly, including running BOTH team assignments
(NetPlayer gets Aero HO, then Swampert TR) so a lopsided result can't be
confounded with "one team is just stronger" - the same 2026-07-18 lesson
that motivated the non-mirror setup for the solver. Every game's full log is
written to logs/ for turn-by-turn diagnosis.

  python -m harness.run_net_match            # default N_GAMES_PER_SIDE each side
  python -m harness.run_net_match 2          # override games per side
"""

import asyncio
import sys
import uuid
from pathlib import Path

from poke_env.ps_client.account_configuration import AccountConfiguration
from poke_env.teambuilder import ConstantTeambuilder

from harness.doubles_smoke_test import FORMAT
from harness.heuristic_player import HeuristicPlayer
from harness.net_player import NetPlayer
from harness.teams import TEAM_AERO_HO, TEAM_SWAMPERT_TR
from model.net_infer import NetEvaluator

N_GAMES_PER_SIDE = int(sys.argv[1]) if len(sys.argv) > 1 else 5
CHECKPOINT = "model/checkpoints/imitation_v1.pt"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "logs"
# One shared model for the whole batch (no per-game reload / CUDA-context churn).
EVALUATOR = NetEvaluator(CHECKPOINT)


async def run_one_game(game_index: int, net_team: str, heuristic_team: str) -> tuple[str, bool]:
    # Unique account names per game so a stale connection can never collide.
    tag = uuid.uuid4().hex[:8]
    net = NetPlayer(
        battle_format=FORMAT, team=ConstantTeambuilder(net_team), accept_open_team_sheet=False,
        account_configuration=AccountConfiguration(f"n{tag}", None),
        evaluator=EVALUATOR, n_worlds=3, k_my=4, k_opp=4, solver_seed=game_index,
    )
    baseline = HeuristicPlayer(
        battle_format=FORMAT, team=ConstantTeambuilder(heuristic_team), accept_open_team_sheet=False,
        account_configuration=AccountConfiguration(f"h{tag}", None),
    )
    try:
        await net.battle_against(baseline, n_battles=1)
        won = net.n_won_battles == 1
        return net.finalize_log(won), won
    finally:
        net.close()   # always free the engine node + TP pool, even on error/timeout


async def run_assignment(net_gets_aero: bool) -> int:
    net_team, net_name = (TEAM_AERO_HO, "aero") if net_gets_aero else (TEAM_SWAMPERT_TR, "swampert")
    heuristic_team, heuristic_name = (TEAM_SWAMPERT_TR, "swampert") if net_gets_aero else (TEAM_AERO_HO, "aero")

    wins = 0
    for i in range(N_GAMES_PER_SIDE):
        import time
        start = time.perf_counter()
        log, won = await run_one_game(i, net_team, heuristic_team)
        wins += won
        print(f"[net={net_name}] game {i + 1}/{N_GAMES_PER_SIDE}: net {'WON' if won else 'lost'} "
              f"({time.perf_counter() - start:.0f}s)", flush=True)
        result_tag = "won" if won else "lost"
        out_path = OUTPUT_DIR / f"net_{net_name}_vs_heuristic_{heuristic_name}_game{i + 1}_{result_tag}.txt"
        out_path.write_text(log, encoding="utf-8")

    print(f"\nnet ({net_name}) won {wins}/{N_GAMES_PER_SIDE} vs heuristic ({heuristic_name}) baseline", flush=True)
    return wins


async def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    aero_wins = await run_assignment(net_gets_aero=True)
    swampert_wins = await run_assignment(net_gets_aero=False)
    total = aero_wins + swampert_wins
    print(f"\n=== NetPlayer total: {total}/{2 * N_GAMES_PER_SIDE} "
          f"(aero {aero_wins}/{N_GAMES_PER_SIDE}, swampert {swampert_wins}/{N_GAMES_PER_SIDE}) ===", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
