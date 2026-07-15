"""Runs one real Reg M-B battle, translates each turn to BattleState, runs
the belief-tracker over it, and checks: no crash, all probabilities in
[0, 1], and any move once it's revealed no longer appears in that mon's
move_beliefs (consistency between revealed_* facts and the belief pool).
"""

import asyncio
import time

from poke_env.player import RandomPlayer
from poke_env.ps_client.account_configuration import AccountConfiguration
from poke_env.teambuilder import ConstantTeambuilder

from belief.tracker import update_battle_beliefs
from harness.doubles_smoke_test import FORMAT, TEAM
from harness.translator import battle_to_state

turns_checked = 0
errors = []


class BeliefCheckingPlayer(RandomPlayer):
    def choose_move(self, battle):
        global turns_checked
        try:
            state = battle_to_state(battle)
            update_battle_beliefs(state)
            for mon in state.opp_active + state.opp_bench:
                for belief_list in (mon.move_beliefs, mon.item_beliefs, mon.ability_beliefs, mon.tera_beliefs, mon.spread_beliefs):
                    for opt in belief_list:
                        assert 0.0 <= opt.probability <= 1.0, f"bad probability {opt}"
                revealed_set = set(mon.revealed_moves)
                for opt in mon.move_beliefs:
                    assert opt.value not in revealed_set, f"{opt.value} revealed but still in move_beliefs"
            turns_checked += 1
            if battle.turn <= 1:
                for mon in state.opp_active:
                    print(f"turn {battle.turn} {mon.species}: revealed_moves={mon.revealed_moves} "
                          f"move_beliefs_count={len(mon.move_beliefs)} "
                          f"sample={mon.move_beliefs[:3]}")
        except Exception as e:
            errors.append((battle.turn, repr(e)))
        return self.choose_random_move(battle)


async def main():
    team = ConstantTeambuilder(TEAM)
    tag = str(int(time.time()))
    p1 = BeliefCheckingPlayer(
        battle_format=FORMAT, team=team, accept_open_team_sheet=False,
        account_configuration=AccountConfiguration(f"bel1{tag}", None),
    )
    p2 = RandomPlayer(
        battle_format=FORMAT, team=team, accept_open_team_sheet=False,
        account_configuration=AccountConfiguration(f"bel2{tag}", None),
    )
    await p1.battle_against(p2, n_battles=1)

    print(f"\nTurns checked: {turns_checked}")
    print(f"Errors: {len(errors)}")
    for turn, err in errors[:10]:
        print(f"  turn {turn}: {err}")
    print("PASS" if not errors and turns_checked > 0 else "FAIL")


if __name__ == "__main__":
    asyncio.run(main())
