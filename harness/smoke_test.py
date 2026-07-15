"""Plumbing smoke test: two random-move poke-env players battle each other
against the local Showdown server in the actual Reg M-B format, with open
team sheets declined. Proves the local server + poke-env connection works
before any translator/model code is written.
"""

import asyncio
import time

from poke_env.player import RandomPlayer
from poke_env.ps_client.account_configuration import AccountConfiguration

# Random Battle auto-generates legal teams server-side, so this sidesteps
# needing to already know Champions' curated item/species/move legality
# pool. Proves server + poke-env + battle-completion plumbing; doubles
# action selection against a real Reg M-B team comes once we have a proper
# legal-team generator for that format instead of a hand-guessed one.
FORMAT = "gen9championsrandombattle"


async def main():
    tag = str(int(time.time()))
    p1 = RandomPlayer(
        battle_format=FORMAT, accept_open_team_sheet=False,
        account_configuration=AccountConfiguration(f"smoke1{tag}", None),
    )
    p2 = RandomPlayer(
        battle_format=FORMAT, accept_open_team_sheet=False,
        account_configuration=AccountConfiguration(f"smoke2{tag}", None),
    )

    await p1.battle_against(p2, n_battles=1)

    print(f"{p1.username}: {p1.n_won_battles} wins")
    print(f"{p2.username}: {p2.n_won_battles} wins")
    print("Battle completed successfully." if p1.n_finished_battles == 1 else "Battle did not finish.")


if __name__ == "__main__":
    asyncio.run(main())
