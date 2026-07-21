"""poke-env Player wired to the heuristic policy, accumulating a
readable one-side-POV battle log (model/battle_log.py) as it plays.
Showdown-specific glue - the actual decisions live in model/heuristic.py.

Team preview uses the same real synergy/mega scoring as SolverPlayer's
opt-out fallback (belief.team_synergy.SYNERGY_WEIGHTS + mega_penalty —
see model/team_preview_scoring.py), loaded once here and passed down as
a plain parameter (model/ never imports belief/ directly).

Team preview can ALSO opt into the same search-based selection
SolverPlayer uses (use_search_team_preview=True, mirroring that class's
constructor param and teampreview() body almost verbatim) - for isolating
"is turn-by-turn play better with search" from "is team selection better
with search": giving BOTH players the search-based team-preview layer
means a head-to-head match only differentiates on the thing actually
being compared (turn-by-turn policy), not confounded by one side getting
a smarter lead/bring choice too. choose_turn_actions/choose_forced_switches
(the real heuristic, not search) still handle every in-battle turn
regardless of this flag - it only ever changes teampreview().
"""

import random

from poke_env.player import Player

from belief.determinize import sample_team_preview_world
from belief.team_synergy import SYNERGY_WEIGHTS
from engine.pool import EngineBridgePool
from harness.actions import team_preview_action_to_order, turn_actions_to_order
from harness.opponent_log import OpponentActionLogger
from harness.translator import battle_to_state
from model.battle_log import format_result, format_team_preview, format_turn
from model.heuristic import choose_forced_switches, choose_team_preview, choose_turn_actions
from model.solver_game import solve_team_preview_decision_parallel


class HeuristicPlayer(Player):
    def __init__(self, *args, mega_penalty: float = 1.0, use_search_team_preview: bool = False,
                 tp_n_worlds: int = 3, tp_iterations: int = 24, tp_bring_cap: int = 6,
                 tp_lead_cap: int = 2, tp_turn_cap: int = 6, solver_seed: int | None = None,
                 n_workers: int = 8, verbose: bool = False, **kwargs):
        super().__init__(*args, **kwargs)
        self.mega_penalty = mega_penalty
        self.use_search_team_preview = use_search_team_preview
        self.tp_n_worlds = tp_n_worlds
        self.tp_iterations = tp_iterations
        self.tp_bring_cap = tp_bring_cap
        self.tp_lead_cap = tp_lead_cap
        self.tp_turn_cap = tp_turn_cap
        self.rng = random.Random(solver_seed)
        self.verbose = verbose
        # Only stood up when actually needed - a plain heuristic-only
        # HeuristicPlayer (the common case, the deliberate no-search
        # baseline) shouldn't pay for an engine pool it never uses.
        self.pool = EngineBridgePool(kwargs["battle_format"], n_workers) if use_search_team_preview else None
        self.log_lines: list[str] = []
        self._opponent_log = OpponentActionLogger()

    def choose_move(self, battle):
        self.log_lines.extend(self._opponent_log.log_new_events(battle))
        state = battle_to_state(battle)

        # A mid-turn forced-switch request (a mon fainted, or a self-
        # switching move forced its user out) only ever offers a switch,
        # never a move - choose_forced_switches handles both slots
        # directly rather than running the general move-picking policy
        # and discarding/overriding its result (see that function's
        # docstring for the bug this used to cause: the non-participating
        # slot's move-scoring pass could spuriously claim the one
        # remaining bench mon before the slot that actually needed it did).
        if any(battle.force_switch):
            actions = choose_forced_switches(state, battle.force_switch)
        else:
            actions = choose_turn_actions(state)

        self.log_lines.append(format_turn(state, actions))
        return turn_actions_to_order(battle, actions)

    def teampreview(self, battle):
        self.log_lines = []  # fresh per battle — relevant when accepting many challenges in a row
        self._opponent_log = OpponentActionLogger()
        state = battle_to_state(battle)
        if self.use_search_team_preview:
            worlds = [sample_team_preview_world(state, self.rng) for _ in range(self.tp_n_worlds)]
            action, diag = solve_team_preview_decision_parallel(
                self.pool, worlds, iterations=self.tp_iterations, depth_limit=2,
                tp_bring_cap=self.tp_bring_cap, tp_lead_cap=self.tp_lead_cap,
                turn_cap=self.tp_turn_cap, synergy_weights=SYNERGY_WEIGHTS,
                mega_penalty=self.mega_penalty, rng=self.rng,
            )
            top = ", ".join(f"{p:.2f}" for _, p in diag.strategy[:3])
            self.log_lines.append(
                f"  [team-preview solver] {diag.step_count} rollouts, "
                f"{diag.error_count} engine rejections, top-3 probs: {top}"
            )
        else:
            action = choose_team_preview(state, synergy_weights=SYNERGY_WEIGHTS, mega_penalty=self.mega_penalty)
        self.log_lines.append(format_team_preview(state, action))
        if self.verbose:
            print(self.log_lines[-1])
        return team_preview_action_to_order(battle, action)

    def _battle_finished_callback(self, battle):
        # flush the last turn's opponent moves/switches - no further
        # choose_move call happens after the battle ends to pick them up
        self.log_lines.extend(self._opponent_log.log_new_events(battle))

    def finalize_log(self, won: bool) -> str:
        self.log_lines.append(format_result(won))
        return "\n\n".join(self.log_lines)
