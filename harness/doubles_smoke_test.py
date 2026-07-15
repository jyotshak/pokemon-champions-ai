"""Doubles plumbing smoke test: two random-move poke-env players battle in
the real Reg M-B format (gen9championsvgc2026regmb) with a hand-built team
of species/items/moves cross-checked against reference/champions_legal_*.txt.
Open team sheets declined, matching the real ladder's default.
"""

import asyncio
import time

from poke_env.player import RandomPlayer
from poke_env.ps_client.account_configuration import AccountConfiguration
from poke_env.teambuilder import ConstantTeambuilder

TEAM = """
Tyranitar @ Tyranitarite
Ability: Sand Stream
Level: 50
Tera Type: Water
EVs: 22 HP / 22 Atk / 22 SpD
Adamant Nature
- Rock Slide
- Crunch
- Earthquake
- Protect

Garchomp @ Life Orb
Ability: Rough Skin
Level: 50
Tera Type: Fire
EVs: 22 HP / 22 Atk / 22 Spe
Jolly Nature
- Earthquake
- Dragon Claw
- Stone Edge
- Protect

Incineroar @ Sitrus Berry
Ability: Intimidate
Level: 50
Tera Type: Ghost
EVs: 22 HP / 22 Def / 22 SpD
Careful Nature
- Fake Out
- Flare Blitz
- Darkest Lariat
- Protect

Charizard @ Charizardite Y
Ability: Blaze
Level: 50
Tera Type: Fairy
EVs: 22 HP / 22 SpA / 22 Spe
Timid Nature
- Flamethrower
- Air Slash
- Dragon Claw
- Protect

Scizor @ Leftovers
Ability: Technician
Level: 50
Tera Type: Steel
EVs: 22 HP / 22 Atk / 22 Def
Adamant Nature
- U-turn
- Iron Head
- Knock Off
- Protect

Skarmory @ Shuca Berry
Ability: Sturdy
Level: 50
Tera Type: Water
EVs: 22 HP / 22 Def / 22 SpD
Impish Nature
- Iron Head
- Brave Bird
- Whirlwind
- Protect
"""

FORMAT = "gen9championsvgc2026regmb"


async def main():
    team = ConstantTeambuilder(TEAM)
    tag = str(int(time.time()))
    p1 = RandomPlayer(
        battle_format=FORMAT, team=team, accept_open_team_sheet=False,
        account_configuration=AccountConfiguration(f"dbl1{tag}", None),
    )
    p2 = RandomPlayer(
        battle_format=FORMAT, team=team, accept_open_team_sheet=False,
        account_configuration=AccountConfiguration(f"dbl2{tag}", None),
    )

    await p1.battle_against(p2, n_battles=1)

    print(f"{p1.username}: {p1.n_won_battles} wins")
    print(f"{p2.username}: {p2.n_won_battles} wins")
    print("Battle completed successfully." if p1.n_finished_battles == 1 else "Battle did not finish.")


if __name__ == "__main__":
    asyncio.run(main())
