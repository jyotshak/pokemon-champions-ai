"""Runs N heuristic-vs-heuristic Reg M-B battles, then randomly samples a
couple of them and writes their full one-side-POV transcripts to logs/.
Useful now for sanity-checking the whole loop end to end, and later for
explaining what the policy does well or poorly.
"""

import asyncio
import random
import time
from pathlib import Path

from poke_env.ps_client.account_configuration import AccountConfiguration
from poke_env.teambuilder import ConstantTeambuilder

from harness.doubles_smoke_test import FORMAT, TEAM
from harness.heuristic_player import HeuristicPlayer

N_GAMES = 10
N_SAMPLES = 2
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "logs"


async def run_one_game(tag: str) -> tuple[str, bool]:
    team = ConstantTeambuilder(TEAM)
    p1 = HeuristicPlayer(
        battle_format=FORMAT, team=team, accept_open_team_sheet=False,
        account_configuration=AccountConfiguration(f"h1{tag}", None),
    )
    p2 = HeuristicPlayer(
        battle_format=FORMAT, team=team, accept_open_team_sheet=False,
        account_configuration=AccountConfiguration(f"h2{tag}", None),
    )
    await p1.battle_against(p2, n_battles=1)
    won = p1.n_won_battles == 1
    return p1.finalize_log(won), won


async def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    logs = []
    wins = 0
    for i in range(N_GAMES):
        tag = f"{int(time.time())}{i}"
        log, won = await run_one_game(tag)
        logs.append(log)
        wins += won
        print(f"game {i + 1}/{N_GAMES} done (p1 {'won' if won else 'lost'})")

    print(f"\np1 won {wins}/{N_GAMES}")

    sampled = random.sample(range(N_GAMES), min(N_SAMPLES, N_GAMES))
    for idx in sampled:
        out_path = OUTPUT_DIR / f"sample_game_{idx}.txt"
        out_path.write_text(logs[idx], encoding="utf-8")
        print(f"wrote {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
