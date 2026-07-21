"""Diagnostic match: isolates "is team-preview selection the problem" from
"is turn-by-turn play the problem." Both sides are SolverPlayer (real
depth-2 search for every in-battle turn decision, unchanged) - the only
difference is TEAM_SWAMPERT_TR's team preview is hand-forced to bring
Grimmsnarl/Swampert/Pelipper/Archaludon, leading Archaludon+Grimmsnarl
(bench: Pelipper, Swampert), instead of letting the solver's own pruner+
search choose it. TEAM_AERO_HO plays exactly as it does everywhere else
(use_search_team_preview=True, no override).

Motivation (2026-07-18 conversation): the pruner's type-coverage/synergy
scoring has zero mechanism knowledge (abilities, mega evolution, weather)
and was found to rank Pelipper into literally every one of its top-12
team-preview candidates against this exact enemy roster - Grimmsnarl
never survives pruning as a lead option at all, regardless of what real
search might have found if given the chance. This match answers a
narrower question first: assuming a human-correct lead, can the solver's
own real-time tactical play actually execute the rest of the game well?

Run from the project root: python -m harness.run_forced_lead_match
(needs the local Showdown server running)
"""

import asyncio
import time
from pathlib import Path

from poke_env.ps_client.account_configuration import AccountConfiguration
from poke_env.teambuilder import ConstantTeambuilder

from harness.doubles_smoke_test import FORMAT
from harness.solver_player import SolverPlayer
from harness.teams import TEAM_AERO_HO, TEAM_SWAMPERT_TR
from schema.battle_state import TeamPreviewAction

N_GAMES = 5
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "logs"

# TEAM_SWAMPERT_TR paste order: Grimmsnarl(0), Swampert(1), Pelipper(2),
# Archaludon(3), Sinistcha(4), Metagross(5). Bring Grimmsnarl/Swampert/
# Pelipper/Archaludon, lead Archaludon+Grimmsnarl.
FORCED_RAIN_LEAD = TeamPreviewAction(bring=[3, 0, 2, 1], lead_order=[3, 0])


async def run_one_game(tag: str, game_index: int) -> tuple[str, str, bool]:
    rain_solver = SolverPlayer(
        battle_format=FORMAT, team=ConstantTeambuilder(TEAM_SWAMPERT_TR), accept_open_team_sheet=False,
        account_configuration=AccountConfiguration(f"r{tag}", None),
        n_worlds=3, iterations=16, depth_limit=2, per_slot_cap=6, n_workers=8,
        solver_seed=game_index, forced_team_preview=FORCED_RAIN_LEAD,
    )
    sun_solver = SolverPlayer(
        battle_format=FORMAT, team=ConstantTeambuilder(TEAM_AERO_HO), accept_open_team_sheet=False,
        account_configuration=AccountConfiguration(f"s{tag}", None),
        n_worlds=3, iterations=16, depth_limit=2, per_slot_cap=6, n_workers=8,
        solver_seed=game_index,
    )
    await rain_solver.battle_against(sun_solver, n_battles=1)
    rain_won = rain_solver.n_won_battles == 1
    rain_log = rain_solver.finalize_log(rain_won)
    sun_log = sun_solver.finalize_log(not rain_won)
    rain_solver.pool.close()
    sun_solver.pool.close()
    return rain_log, sun_log, rain_won


async def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    wins = 0
    for i in range(N_GAMES):
        tag = f"{int(time.time())}{i}"
        start = time.perf_counter()
        rain_log, sun_log, rain_won = await run_one_game(tag, i)
        wins += rain_won
        print(f"game {i + 1}/{N_GAMES}: rain(forced-lead) {'WON' if rain_won else 'lost'} "
              f"({time.perf_counter() - start:.0f}s)")

        result_tag = "won" if rain_won else "lost"
        (OUTPUT_DIR / f"forcedlead_rain_vs_sun_game{i + 1}_{result_tag}.txt").write_text(rain_log, encoding="utf-8")
        (OUTPUT_DIR / f"forcedlead_sun_vs_rain_game{i + 1}_{'lost' if rain_won else 'won'}.txt").write_text(
            sun_log, encoding="utf-8")

    print(f"\nrain (forced Archaludon+Grimmsnarl lead) won {wins}/{N_GAMES} vs sun (full search) solver")


if __name__ == "__main__":
    asyncio.run(main())
