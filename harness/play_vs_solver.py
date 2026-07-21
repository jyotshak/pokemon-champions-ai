"""Play against the CFR solver yourself, in your browser — no external
tooling needed. Same mechanism any poke-env human-vs-bot setup uses
(confirmed against the KoriKosmos/Showdown-Singleplayer repo, which does
exactly this): a poke-env bot waits for challenges on the local Showdown
server; a human connects with an ordinary browser to that same server
and challenges it directly through Showdown's own web client.

Setup:
  1. Start the local Showdown server, if it isn't already running:
       node vendor/pokemon-showdown/pokemon-showdown start --no-security
  2. Run this script:
       python -m harness.play_vs_solver
  3. Open http://localhost:8000 in your browser.
     - Pick any username, "Choose name".
     - "Find a user" -> search for the bot's name (see BOT_NAME below).
     - Click the bot's name -> "Challenge".
     - Format: "[Gen 9 Champions] VGC 2026 Reg M-B".
     - Send the challenge with your own team (paste it in the teambuilder
       first, or use "Randomize" if you just want to try the flow).
  4. The bot auto-accepts and plays live — solver diagnostics (rollout
     count, engine rejections, top-3 action probabilities) print to this
     console after every one of its turns, and again as a full match log
     when the battle ends, so you can see decision quality as you play.

Each run accepts N_GAMES challenges in a row, then exits (rerun to keep
playing). Solver strength/speed settings mirror harness/run_solver_match.py.
"""

import asyncio

from poke_env.ps_client.account_configuration import AccountConfiguration
from poke_env.teambuilder import ConstantTeambuilder

from harness.doubles_smoke_test import FORMAT, TEAM
from harness.solver_player import SolverPlayer

BOT_NAME = "SolverBot"
N_GAMES = 10


async def main():
    team = ConstantTeambuilder(TEAM)
    solver = SolverPlayer(
        battle_format=FORMAT, team=team, accept_open_team_sheet=False,
        account_configuration=AccountConfiguration(BOT_NAME, None),
        n_worlds=3, iterations=64, depth_limit=2, per_slot_cap=6, n_workers=8,
        verbose=True,
    )
    print(f"Waiting for challenges as '{BOT_NAME}' in format: [Gen 9 Champions] VGC 2026 Reg M-B")
    print("Open http://localhost:8000 in your browser, pick a username, "
          f"find '{BOT_NAME}', and send a challenge.\n")
    try:
        await solver.accept_challenges(None, N_GAMES)
    finally:
        solver.pool.close()
    print(f"\nDone — accepted {N_GAMES} challenge(s). Rerun this script to play more.")


if __name__ == "__main__":
    asyncio.run(main())
