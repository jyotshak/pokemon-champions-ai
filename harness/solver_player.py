"""poke-env Player wired to the CFR solver: every non-forced decision
runs the full pipeline (translate -> determinize K worlds -> engine-backed
MCCFR solve -> chosen TurnActions -> poke-env order). Showdown glue only —
the decision-making lives in model/solver_game.py.

Self-switch moves (Parting Shot/U-turn/Volt Switch/Baton Pass/Flip Turn):
the search itself already weighs the switch-in as part of the ORIGINAL
turn decision (model/action_space.py's MoveAction.switch_bench_slot
branching, resolved through the real engine via model/solver_game.py's
_resolve_self_switches - no engine changes, no separate search node).
That pre-decided destination is deliberately NOT threaded through to the
live mid-turn poke-env request below, though: by the time that request
actually arrives, MORE has been revealed live (mega evolution always
resolves before any move, even a Prankster-boosted one) than was known
at turn-submission time, so choose_forced_switches (model/heuristic.py)
is called fresh at that moment instead - a cheap, damage-aware (not
"first bench mon") comparison against the CURRENT battle state, picking
up whatever's newly visible for free. See model/heuristic.py::
_choose_switch_in for the actual comparison.

Team preview: search-based by default (use_search_team_preview=True) via
model/solver_game.py::solve_team_preview_decision_parallel (depth_limit=2
— team preview resolves through the real engine at depth 1, a real
turn-1 exchange resolves at depth 2, hp_leaf_value cuts there). Validated
live 2026-07-18 (docs/solver_design.md's team preview section): the
mechanical bug this replaces (a fixed placeholder deterministically
leading two Ground-weak mons into a revealed Garchomp, every game) is
gone — bring/lead now varies game to game and never repeats that pair.
choose_team_preview (model/heuristic.py) remains available as an opt-out
fallback/comparison baseline via use_search_team_preview=False — note
this now ALSO gets the real synergy/mega scoring below (belief.
team_synergy.SYNERGY_WEIGHTS + mega_penalty), so the opt-out toggle
compares "scored heuristic vs search," not "dumb BST-sort vs search"
like it did before the team-synergy work landed.

Team-synergy scoring (belief/team_synergy.py's SYNERGY_WEIGHTS, plus a
soft mega_penalty for bring-4 subsets with zero mega-eligible members —
see model/team_preview_scoring.py) is threaded into BOTH the search path
and the opt-out fallback, loaded once here and passed down as a plain
parameter — model/ never imports belief/ directly, same pattern as
sample_determinization/sample_team_preview_world.
"""

import random
from typing import Optional

from poke_env.player import Player

from belief.determinize import sample_determinization, sample_team_preview_world
from belief.team_synergy import SYNERGY_WEIGHTS
from engine.pool import EngineBridgePool
from harness.actions import team_preview_action_to_order, turn_actions_to_order
from harness.opponent_log import OpponentActionLogger
from harness.translator import battle_to_state
from model.battle_log import format_result, format_team_preview, format_turn
from model.heuristic import choose_forced_switches, choose_team_preview
from model.solver_game import solve_decision_parallel, solve_team_preview_decision_parallel
from schema.battle_state import Action, BattleState, SwitchAction, TeamPreviewAction, TurnActions


def _remap_bench(action: Action, state: BattleState) -> Action:
    """Solver bench indices count LIVING benched mons (schema/
    full_info_state.bench_mons); harness bench indices count all brought
    benched mons including fainted ones. Translate at the boundary.
    """
    if isinstance(action, SwitchAction):
        living = [i for i, mon in enumerate(state.my_bench) if not mon.fainted]
        return SwitchAction(bench_slot=living[action.bench_slot])
    return action


class SolverPlayer(Player):
    def __init__(self, *args, n_worlds: int = 2, iterations: int = 48, depth_limit: int = 1,
                 per_slot_cap: int = 6, solver_seed: int | None = None, n_workers: int = 8,
                 verbose: bool = False, use_search_team_preview: bool = True,
                 tp_n_worlds: int = 3, tp_iterations: int = 24, tp_bring_cap: int = 6,
                 tp_lead_cap: int = 2, tp_turn_cap: int = 6, mega_penalty: float = 1.0,
                 forced_team_preview: Optional[TeamPreviewAction] = None, **kwargs):
        super().__init__(*args, **kwargs)
        # Diagnostic override: when set, teampreview() skips BOTH the
        # search and the heuristic fallback and returns this action
        # directly - everything else (every in-battle turn decision)
        # still goes through the real solver unchanged. For isolating
        # "is team-preview selection the problem" from "is turn-by-turn
        # play the problem" by hand-fixing bring/lead to a specific,
        # human-chosen line and letting real search handle the rest.
        self.forced_team_preview = forced_team_preview
        self.n_worlds = n_worlds
        self.iterations = iterations
        self.depth_limit = depth_limit
        self.per_slot_cap = per_slot_cap
        self.rng = random.Random(solver_seed)
        self.verbose = verbose  # print live diagnostics to console, for interactive play
        self.use_search_team_preview = use_search_team_preview
        self.tp_n_worlds = tp_n_worlds
        self.tp_iterations = tp_iterations
        self.tp_bring_cap = tp_bring_cap
        self.tp_lead_cap = tp_lead_cap
        self.tp_turn_cap = tp_turn_cap
        # A real, non-zero default for live play - the tunable constants
        # only need to default to zero INSIDE the pure scoring functions
        # (for test neutrality); this harness layer is where "actually
        # turn it on" belongs, same as use_search_team_preview itself
        # already defaulting True here while individual components
        # default conservatively.
        self.mega_penalty = mega_penalty
        # A pool, not a single bridge: startup is cheap (~0.2s for 8
        # workers) and kept alive for the whole match, since every real
        # decision reuses it — see engine/pool.py + model/solver_game.py's
        # solve_decision_parallel (docs/solver_design.md). Reused as-is
        # for team-preview solves too (solve_team_preview_decision_parallel
        # just needs N generic EngineBridges, same as the turn-level solve).
        self.pool = EngineBridgePool(kwargs["battle_format"], n_workers)
        self.log_lines: list[str] = []
        self._opponent_log = OpponentActionLogger()

    def teampreview(self, battle):
        self.log_lines = []  # fresh per battle — relevant when accepting many challenges in a row
        self._opponent_log = OpponentActionLogger()
        state = battle_to_state(battle)
        if self.forced_team_preview is not None:
            action = self.forced_team_preview
        elif self.use_search_team_preview:
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

    def choose_move(self, battle):
        self.log_lines.extend(self._opponent_log.log_new_events(battle))
        state = battle_to_state(battle)

        if any(battle.force_switch):
            # A mid-turn forced-switch request only ever offers a switch,
            # never a move - choose_forced_switches handles both slots
            # directly instead of running the general move-picking policy
            # and discarding/overriding its result (see that function's
            # docstring: the old pattern let the non-participating slot's
            # move-scoring pass spuriously claim the one remaining bench
            # mon before the slot that actually needed it did).
            actions = choose_forced_switches(state, battle.force_switch)
            self.log_lines.append(format_turn(state, actions))
            if self.verbose:
                print(self.log_lines[-1])
            return turn_actions_to_order(battle, actions)

        worlds = [sample_determinization(state, self.rng) for _ in range(self.n_worlds)]
        best, diag = solve_decision_parallel(
            self.pool, worlds,
            iterations=self.iterations, depth_limit=self.depth_limit,
            per_slot_cap=self.per_slot_cap, rng=self.rng,
        )
        best = TurnActions(
            slot_left=_remap_bench(best.slot_left, state),
            slot_right=_remap_bench(best.slot_right, state),
        )
        self.log_lines.append(format_turn(state, best))
        top = ", ".join(f"{p:.2f}" for _, p in diag.strategy[:3])
        self.log_lines.append(
            f"  [solver] {diag.step_count} rollouts, {diag.error_count} engine rejections, top-3 probs: {top}"
        )
        if self.verbose:
            print(self.log_lines[-2])
            print(self.log_lines[-1])
        return turn_actions_to_order(battle, best)

    def finalize_log(self, won: bool) -> str:
        self.log_lines.append(format_result(won))
        return "\n\n".join(self.log_lines)

    def _battle_finished_callback(self, battle):
        # flush the last turn's opponent moves/switches - no further
        # choose_move call happens after the battle ends to pick them up
        self.log_lines.extend(self._opponent_log.log_new_events(battle))
        if self.verbose:
            print(f"\n=== Battle finished: solver {'WON' if battle.won else 'LOST'} ===\n")
