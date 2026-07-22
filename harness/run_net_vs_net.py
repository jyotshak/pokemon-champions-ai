"""Net vs net: two independent NetPlayer instances (same checkpoint/
evaluator, own EngineBridge + team-preview pool each) on two DIFFERENT
team sheets, head to head.

Runs BOTH team assignments (net_a gets team A then team B) so a lopsided
result can't be confounded with "one team is just stronger" - the same
2026-07-18 lesson behind every other non-mirror match script in this repo
(run_solver_match.py, run_net_vs_solver_diverse.py).

Start the local server first:
  node vendor/pokemon-showdown/pokemon-showdown start --no-security

  python -m harness.run_net_vs_net              # MB550 vs MB548, 10 games (5 each side)
  python -m harness.run_net_vs_net MB550 MB548 6  # team ids, games per side
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
from harness.team_sheet import team_by_id
from model.net_infer import NetEvaluator

TEAM_A_ID = sys.argv[1] if len(sys.argv) > 1 else "MB550"
TEAM_B_ID = sys.argv[2] if len(sys.argv) > 2 else "MB548"
N_GAMES_PER_SIDE = int(sys.argv[3]) if len(sys.argv) > 3 else 5
CHECKPOINT = "model/checkpoints/imitation_v4.pt"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "logs"

EVALUATOR = NetEvaluator(CHECKPOINT)   # one shared model for the whole batch


async def run_one_game(game_index: int, paste_a: str, paste_b: str) -> tuple[str, bool]:
    tag = uuid.uuid4().hex[:8]
    net_a = NetPlayer(
        battle_format=FORMAT, team=ConstantTeambuilder(paste_a), accept_open_team_sheet=False,
        account_configuration=AccountConfiguration(f"na{tag}", None),
        evaluator=EVALUATOR, n_worlds=3, k_my=4, k_opp=4, solver_seed=game_index,
        use_search_team_preview=True, n_workers=8,
    )
    net_b = NetPlayer(
        battle_format=FORMAT, team=ConstantTeambuilder(paste_b), accept_open_team_sheet=False,
        account_configuration=AccountConfiguration(f"nb{tag}", None),
        evaluator=EVALUATOR, n_worlds=3, k_my=4, k_opp=4, solver_seed=game_index + 100000,
        use_search_team_preview=True, n_workers=8,
    )
    try:
        await net_a.battle_against(net_b, n_battles=1)
        won = net_a.n_won_battles == 1
        return net_a.finalize_log(won), won
    finally:
        net_a.close()
        net_b.close()


async def run_assignment(seed_offset: int, team_a_in_slot_a: bool, paste_a: str, paste_b: str,
                         name_a: str, name_b: str) -> dict:
    """One block of games with a FIXED physical assignment (which team sits
    in the 'a'/'b' engine slot). Returns wins keyed by TEAM ID (not slot),
    so callers can sum across assignments regardless of which slot a team
    occupied that block."""
    slot_a_team, slot_b_team = (name_a, name_b) if team_a_in_slot_a else (name_b, name_a)
    wins = {name_a: 0, name_b: 0}
    for i in range(N_GAMES_PER_SIDE):
        start = time.perf_counter()
        log, slot_a_won = await run_one_game(seed_offset + i, paste_a if team_a_in_slot_a else paste_b,
                                             paste_b if team_a_in_slot_a else paste_a)
        winner = slot_a_team if slot_a_won else slot_b_team
        wins[winner] += 1
        print(f"[{slot_a_team} vs {slot_b_team}] game {i + 1}/{N_GAMES_PER_SIDE}: "
              f"{winner} WON ({time.perf_counter() - start:.0f}s)", flush=True)
        out = OUTPUT_DIR / f"net_{slot_a_team}_vs_net_{slot_b_team}_game{i + 1}_{'a' if slot_a_won else 'b'}won.txt"
        out.write_text(log, encoding="utf-8")

    print(f"\nblock ({slot_a_team} vs {slot_b_team}): {wins[name_a]}-{wins[name_b]} "
          f"({name_a}-{name_b})\n", flush=True)
    return wins


async def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    rec_a, rec_b = team_by_id(TEAM_A_ID), team_by_id(TEAM_B_ID)
    paste_a, paste_b = rec_a["paste"], rec_b["paste"]
    print(f"team {TEAM_A_ID}: {rec_a.get('description', '')}")
    print(f"team {TEAM_B_ID}: {rec_b.get('description', '')}")
    print(f"{N_GAMES_PER_SIDE * 2} games total, both team assignments run so a lopsided "
          f"result isn't confounded with team strength\n", flush=True)

    block1 = await run_assignment(0, True, paste_a, paste_b, TEAM_A_ID, TEAM_B_ID)
    block2 = await run_assignment(100000, False, paste_a, paste_b, TEAM_A_ID, TEAM_B_ID)
    total = {TEAM_A_ID: block1[TEAM_A_ID] + block2[TEAM_A_ID],
             TEAM_B_ID: block1[TEAM_B_ID] + block2[TEAM_B_ID]}
    n_total = 2 * N_GAMES_PER_SIDE
    print(f"=== {TEAM_A_ID} vs {TEAM_B_ID} (same net piloting both): "
          f"{total[TEAM_A_ID]}-{total[TEAM_B_ID]} out of {n_total} "
          f"({100.0 * total[TEAM_A_ID] / n_total:.0f}% for {TEAM_A_ID}) ===")
    print("    50% = the two teams are equally strong when both piloted by the same net.")


if __name__ == "__main__":
    asyncio.run(main())
