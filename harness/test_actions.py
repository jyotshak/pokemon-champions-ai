"""Round-trip validation for actions.py: builds TurnActions/TeamPreviewAction
from our schema each turn using a trivial fixed rule (NOT a real policy —
none exists yet), converts them via actions.py, and confirms poke-env/
Showdown accepts the resulting orders across a full real battle.
"""

import asyncio
import time

from poke_env.player import Player, RandomPlayer
from poke_env.ps_client.account_configuration import AccountConfiguration
from poke_env.teambuilder import ConstantTeambuilder

from harness.actions import team_preview_action_to_order, turn_actions_to_order
from harness.doubles_smoke_test import FORMAT, TEAM
from schema.battle_state import MoveAction, NoAction, Target, TeamPreviewAction, TurnActions

turns_ok = 0
failures = []


class SchemaDrivenPlayer(Player):
    def choose_move(self, battle):
        global turns_ok
        try:
            slot_actions = []
            for i, mon in enumerate(battle.active_pokemon):
                available = battle.available_moves[i] if i < len(battle.available_moves) else []
                if mon is None or mon.fainted or not available:
                    slot_actions.append(NoAction())
                    continue
                move = available[0]
                move_slot = list(mon.moves.values()).index(move) + 1
                needs_target = move.category.name != "STATUS"
                target = Target.OPP_LEFT if needs_target else Target.NONE
                slot_actions.append(MoveAction(move_slot=move_slot, target=target))
            actions = TurnActions(slot_left=slot_actions[0], slot_right=slot_actions[1])
            order = turn_actions_to_order(battle, actions)
            turns_ok += 1
            return order
        except Exception as e:
            failures.append((battle.turn, repr(e)))
            return self.choose_random_move(battle)

    def teampreview(self, battle):
        try:
            n = len(battle.teampreview_team)
            bring = list(range(min(4, n)))
            action = TeamPreviewAction(bring=bring, lead_order=bring[:2])
            return team_preview_action_to_order(battle, action)
        except Exception as e:
            failures.append(("teampreview", repr(e)))
            return self.random_teampreview(battle)


async def main():
    team = ConstantTeambuilder(TEAM)
    tag = str(int(time.time()))
    p1 = SchemaDrivenPlayer(
        battle_format=FORMAT, team=team, accept_open_team_sheet=False,
        account_configuration=AccountConfiguration(f"act1{tag}", None),
    )
    p2 = RandomPlayer(
        battle_format=FORMAT, team=team, accept_open_team_sheet=False,
        account_configuration=AccountConfiguration(f"act2{tag}", None),
    )
    await p1.battle_against(p2, n_battles=1)
    print("turns_ok:", turns_ok)
    print("failures:", failures[:10])
    print("PASS" if not failures and turns_ok > 0 else "FAIL")


if __name__ == "__main__":
    asyncio.run(main())
