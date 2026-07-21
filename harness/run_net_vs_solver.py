"""The skill test: NetPlayer (depth-1 net policy+value search) vs SolverPlayer
(engine-backed MCCFR) head-to-head on a MIRROR team - does the replay-trained
net actually out-play the CFR solver? ([[imitation-net-v1]])

Why a mirror team: the net-vs-heuristic batches were dominated by team strength
(whoever held Aero won regardless of pilot - the 2026-07-18 confound). Giving
BOTH sides the same roster removes team quality from the result entirely.

Team preview: BOTH sides use the same search-based TP (the stronger selector -
NetPlayer borrows SolverPlayer's solve_team_preview_decision_parallel via its
own pool). Using the identical TP algorithm on an identical roster means any
bring/lead difference is just RNG, not a systematic edge, so the per-turn
decision engine (net depth-1 vs MCCFR) stays the only real variable - while
both sides still play from well-chosen teams rather than a handicapped
heuristic.

Start the local server first:
  node vendor/pokemon-showdown/pokemon-showdown start --no-security

  python -m harness.run_net_vs_solver              # MB552, 10 games
  python -m harness.run_net_vs_solver MB501 6      # team id, games
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
from harness.team_sheet import team_by_id
from model.net_infer import NetEvaluator

TEAM_ID = sys.argv[1] if len(sys.argv) > 1 else "MB552"
N_GAMES = int(sys.argv[2]) if len(sys.argv) > 2 else 10
CHECKPOINT = "model/checkpoints/imitation_v2.pt"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "logs"

EVALUATOR = NetEvaluator(CHECKPOINT)   # one shared model for the whole batch


async def run_one_game(game_index: int, paste: str) -> tuple[str, bool]:
    tag = uuid.uuid4().hex[:8]
    net = NetPlayer(
        battle_format=FORMAT, team=ConstantTeambuilder(paste), accept_open_team_sheet=False,
        account_configuration=AccountConfiguration(f"n{tag}", None),
        evaluator=EVALUATOR, n_worlds=3, k_my=4, k_opp=4, solver_seed=game_index,
        use_search_team_preview=True, n_workers=8,   # same search TP as the solver
    )
    solver = SolverPlayer(
        battle_format=FORMAT, team=ConstantTeambuilder(paste), accept_open_team_sheet=False,
        account_configuration=AccountConfiguration(f"s{tag}", None),
        n_worlds=3, iterations=16, depth_limit=2, per_slot_cap=6, n_workers=8,
        solver_seed=game_index,
        use_search_team_preview=True,   # both sides on the stronger selector
    )
    try:
        await net.battle_against(solver, n_battles=1)
        won = net.n_won_battles == 1
        return net.finalize_log(won), won
    finally:
        net.close()
        solver.pool.close()


async def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    record = team_by_id(TEAM_ID)
    paste = record["paste"]
    print(f"team {TEAM_ID}: {record.get('description', '')}", flush=True)
    print(f"mirror match, {N_GAMES} games, both sides identical roster + identical "
          f"search team preview\n-> the per-turn decision engine is the only variable\n", flush=True)

    wins = 0
    for i in range(N_GAMES):
        start = time.perf_counter()
        log, won = await run_one_game(i, paste)
        wins += won
        print(f"game {i + 1}/{N_GAMES}: net {'WON ' if won else 'lost'} vs solver "
              f"({time.perf_counter() - start:.0f}s)   running: {wins}/{i + 1}", flush=True)
        out = OUTPUT_DIR / f"net_vs_solver_{TEAM_ID}_game{i + 1}_{'won' if won else 'lost'}.txt"
        out.write_text(log, encoding="utf-8")

    pct = 100.0 * wins / N_GAMES
    print(f"\n=== NetPlayer (depth-1) {wins}/{N_GAMES} ({pct:.0f}%) vs SolverPlayer (MCCFR) "
          f"on mirror team {TEAM_ID} ===", flush=True)
    print("   50% = the two decision engines are equally strong on this team.", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
