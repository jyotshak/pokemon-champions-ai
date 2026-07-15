"""Runs one real Reg M-B battle and calls the translator on every turn,
verifying battle_to_state() never raises and produces a sane BattleState.
Uses the same team as doubles_smoke_test.py.
"""

import asyncio
import time

from poke_env.player import RandomPlayer
from poke_env.ps_client.account_configuration import AccountConfiguration
from poke_env.teambuilder import ConstantTeambuilder

from harness.doubles_smoke_test import TEAM, FORMAT
from harness.translator import battle_to_state

turns_checked = 0
errors = []


class TranslatingPlayer(RandomPlayer):
    def choose_move(self, battle):
        global turns_checked
        try:
            state = battle_to_state(battle)
            turns_checked += 1
            if battle.turn <= 1:
                print(f"--- turn {battle.turn} sample state ---")
                print("my_active species:", [p.species for p in state.my_active])
                print("opp_active species:", [p.species for p in state.opp_active])
                print("field:", state.field.weather, state.field.terrain)
        except Exception as e:
            errors.append((battle.turn, repr(e)))
        return self.choose_random_move(battle)


async def main():
    team = ConstantTeambuilder(TEAM)
    tag = str(int(time.time()))
    p1 = TranslatingPlayer(
        battle_format=FORMAT, team=team, accept_open_team_sheet=False,
        account_configuration=AccountConfiguration(f"tr1{tag}", None),
    )
    p2 = RandomPlayer(
        battle_format=FORMAT, team=team, accept_open_team_sheet=False,
        account_configuration=AccountConfiguration(f"tr2{tag}", None),
    )

    await p1.battle_against(p2, n_battles=1)

    print(f"\nTurns checked: {turns_checked}")
    print(f"Errors: {len(errors)}")
    for turn, err in errors[:10]:
        print(f"  turn {turn}: {err}")
    print("PASS" if not errors and turns_checked > 0 else "FAIL")


if __name__ == "__main__":
    asyncio.run(main())
