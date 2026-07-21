"""poke-env Player driven by the trained net's depth-1 policy+value search
([[imitation-net-v1]], [[replay-net-direction]]). Showdown glue only - the
decision lives in harness/net_search.py::net_depth1_decision (net policy
proposes the branches, the engine rolls one turn, the net value head scores
the leaves).

Reuses the exact same translate -> determinize -> chosen-TurnActions ->
poke-env order pipeline as SolverPlayer, swapping the CFR solver for the net
search. Team preview: heuristic placeholder (choose_team_preview) for now -
the LEARNED team-preview head (from replay turn-1 leads + Bo3 open-sheet opp
teams) is a separate build; this isolates "does the net play TURNS well in a
full game." Forced switches: the existing damage-aware heuristic, same as
SolverPlayer.

Single EngineBridge + the torch net both live in this (main) process - the
net stays on one GPU context, and the bridge's own Node subprocess handles
rollouts, so no model-in-worker complications.
"""

import random

from poke_env.player import Player

from belief.determinize import sample_determinization, sample_team_preview_world
from belief.team_synergy import SYNERGY_WEIGHTS
from engine.bridge import EngineBridge
from engine.pool import EngineBridgePool
from harness.actions import team_preview_action_to_order, turn_actions_to_order
from harness.net_search import net_depth1_decision
from harness.net_translate import battle_state_to_netstate
from harness.opponent_log import OpponentActionLogger
from harness.translator import battle_to_state
from model.battle_log import format_result, format_team_preview, format_turn
from model.heuristic import choose_forced_switches, choose_team_preview
from model.net_infer import NetEvaluator
from model.solver_game import solve_team_preview_decision_parallel
from schema.battle_state import Action, BattleState, MoveAction, SwitchAction, TurnActions


def _remap_bench(action: Action, state: BattleState) -> Action:
    """Search bench indices count LIVING benched mons (bench_mons); harness
    indices count all brought bench mons incl. fainted. Translate both plain
    switches and self-switch move destinations at the boundary."""
    living = [i for i, mon in enumerate(state.my_bench) if not mon.fainted]
    if isinstance(action, SwitchAction):
        return SwitchAction(bench_slot=living[action.bench_slot])
    if isinstance(action, MoveAction) and action.switch_bench_slot is not None:
        return action.model_copy(update={"switch_bench_slot": living[action.switch_bench_slot]})
    return action


class NetPlayer(Player):
    def __init__(self, *args, checkpoint: str = "model/checkpoints/imitation_v2.pt",
                 evaluator: NetEvaluator | None = None,
                 n_worlds: int = 4, k_my: int = 4, k_opp: int = 4,
                 solver_seed: int = 0, verbose: bool = False,
                 use_search_team_preview: bool = True, n_workers: int = 8,
                 tp_n_worlds: int = 3, tp_iterations: int = 24, tp_bring_cap: int = 6,
                 tp_lead_cap: int = 2, tp_turn_cap: int = 6, mega_penalty: float = 1.0,
                 **kwargs):
        super().__init__(*args, **kwargs)
        # Reuse a shared evaluator across a batch if given (avoids reloading
        # the torch model + a fresh CUDA context per game).
        self.evaluator = evaluator or NetEvaluator(checkpoint)
        self.bridge = EngineBridge(kwargs["battle_format"])
        self.n_worlds = n_worlds
        self.k_my = k_my
        self.k_opp = k_opp
        self.rng = random.Random(solver_seed)
        self.verbose = verbose
        # Team preview uses the SAME search as SolverPlayer (the stronger
        # selector) so a net-vs-solver comparison isn't decided by team
        # building. Needs a pool, not the single turn-level bridge, because
        # solve_team_preview_decision_parallel wants N generic bridges.
        # The learned team-preview head will replace this later.
        self.use_search_team_preview = use_search_team_preview
        self.tp_n_worlds = tp_n_worlds
        self.tp_iterations = tp_iterations
        self.tp_bring_cap = tp_bring_cap
        self.tp_lead_cap = tp_lead_cap
        self.tp_turn_cap = tp_turn_cap
        self.mega_penalty = mega_penalty
        self.pool = EngineBridgePool(kwargs["battle_format"], n_workers) if use_search_team_preview else None
        self.log_lines: list[str] = []
        self._opponent_log = OpponentActionLogger()

    def teampreview(self, battle):
        self.log_lines = []
        self._opponent_log = OpponentActionLogger()
        state = battle_to_state(battle)
        if self.use_search_team_preview:
            worlds = [sample_team_preview_world(state, self.rng) for _ in range(self.tp_n_worlds)]
            action, _diag = solve_team_preview_decision_parallel(
                self.pool, worlds, iterations=self.tp_iterations, depth_limit=2,
                tp_bring_cap=self.tp_bring_cap, tp_lead_cap=self.tp_lead_cap,
                turn_cap=self.tp_turn_cap, synergy_weights=SYNERGY_WEIGHTS,
                mega_penalty=self.mega_penalty, rng=self.rng,
            )
        else:
            action = choose_team_preview(state, synergy_weights=SYNERGY_WEIGHTS,
                                         mega_penalty=self.mega_penalty)
        self.log_lines.append(format_team_preview(state, action))
        if self.verbose:
            print(self.log_lines[-1])
        return team_preview_action_to_order(battle, action)

    def close(self):
        """Free the engine node + team-preview pool (call after each game)."""
        self.bridge.close()
        if self.pool is not None:
            self.pool.close()

    def choose_move(self, battle):
        self.log_lines.extend(self._opponent_log.log_new_events(battle))
        state = battle_to_state(battle)

        if any(battle.force_switch):
            actions = choose_forced_switches(state, battle.force_switch)
            self.log_lines.append(format_turn(state, actions))
            if self.verbose:
                print(self.log_lines[-1])
            return turn_actions_to_order(battle, actions)

        worlds = [sample_determinization(state, self.rng) for _ in range(self.n_worlds)]
        chosen, diag = net_depth1_decision(
            self.evaluator, self.bridge, worlds,
            my_netstate=battle_state_to_netstate(state), k_my=self.k_my, k_opp=self.k_opp,
            rng=self.rng,
        )
        chosen = TurnActions(slot_left=_remap_bench(chosen.slot_left, state),
                             slot_right=_remap_bench(chosen.slot_right, state))
        self.log_lines.append(format_turn(state, chosen))
        top = ", ".join(f"{p:.2f}" for p, _ in diag.strategy[:3])
        self.log_lines.append(
            f"  [net d1] {diag.rollouts} rollouts, {diag.engine_errors} engine rejections, top-3 probs: {top}"
        )
        if self.verbose:
            print(self.log_lines[-2])
            print(self.log_lines[-1])
        return turn_actions_to_order(battle, chosen)

    def finalize_log(self, won: bool) -> str:
        self.log_lines.append(format_result(won))
        return "\n\n".join(self.log_lines)

    def _battle_finished_callback(self, battle):
        self.log_lines.extend(self._opponent_log.log_new_events(battle))
        if self.verbose:
            print(format_result(battle.won))
