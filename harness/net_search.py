"""Depth-1 policy+value search driven by the trained net ([[imitation-net-v1]],
[[replay-net-direction]]). This is the "incorporate current-turn branches"
step: the imitation policy alone under-picks rare-but-strong reads (Wide Guard
in the position eval), so instead of clicking the policy we let it PROPOSE the
few branches worth simulating and let the VALUE head judge the outcomes.

Per turn:
  1. Net policy ranks my legal joint actions -> keep top-k_my (the branches
     - the search's ROWS).
  2. For each determinized world, net policy (side-flipped) ranks the
     opponent's legal joint actions -> top-k_opp (the search's COLUMNS; a
     policy-weighted proposal, not uniform or worst-case).
  3. Engine rolls every (my, opp) pair one real turn forward, per world; a
     terminal turn gives a true +-1, otherwise the value head scores the
     leaf. Averaging over worlds gives one k_my x k_opp PAYOFF MATRIX.
  4. Solve that small zero-sum matrix game (model/regret.py's
     solve_matrix_game - the same regret-matching primitive the CFR tree
     uses, just at a single node) for a MIXED strategy over my actions, and
     SAMPLE from it rather than taking the argmax.

Why mixed, not argmax (2026-07-20, replacing the original argmax version):
VGC is a SIMULTANEOUS-MOVE game, so the game-theoretic solution is generally
mixed - a pure best-response is exploitable, and in a volatile spot (both
sides can KO each other depending on who's read right) there is no single
"best" action to always repeat. Argmax against a single averaged value also
silently collapsed the net's own learned probability mass: the policy
already assigns real weight to Protect (~12% on average, matching the human
base rate - see [[imitation-net-v1]]'s diagnostics), but argmax-over-value
never once selected it in live testing (0/75 across a 10-game batch). Sampling
a genuine mixed equilibrium both restores that behavior and is required for
sound self-play later (a pure-strategy improvement step can cycle instead of
converging in a simultaneous-move game).

Reuses the EXISTING legal-action enumeration (model/action_space.py, via the
same Tier-1-pruned candidates model.solver_game's CFR tree uses) so every
candidate is engine-ready, the EXISTING encoder action labels
(model/encoding.py) so the net can score them, and the EXISTING regret-
matching matrix solver (model/regret.py) - no new action logic, no new
equilibrium-finding code. Schema/engine-facing, so it lives in harness/
(model/ stays input-neutral).
"""

import random
from dataclasses import dataclass, field

import numpy as np

from schema.battle_state import MoveAction, SwitchAction, TurnActions, Position
from schema.full_info_state import FullInfoState, active_mon, bench_mons
from model.action_space import _pruned_slot_actions, _switch_destination
from model.encoding import resolve_species, _lookup, MOVE_VOCAB
from model.net_infer import NetEvaluator
from model.regret import solve_matrix_game
from harness.net_translate import full_info_state_to_netstate, flip_netstate

_LEFT, _RIGHT = Position.LEFT, Position.RIGHT


@dataclass
class SearchDiagnostics:
    rollouts: int = 0
    engine_errors: int = 0
    strategy: list = field(default_factory=list)     # (prob, TurnActions) sorted desc, MY mixed strategy
    matrix: list = field(default_factory=list)        # the solved payoff matrix (my_cands x opp columns)


def _action_label(action, team: list, position: Position) -> dict:
    """schema Action -> encoder action label (type/move/switch), resolving
    move_slot/bench_slot against the acting team. Target/mega omitted from
    scoring (see NetEvaluator.score_labels)."""
    if isinstance(action, MoveAction):
        mon = active_mon(team, position)
        move_name = mon.moves[action.move_slot - 1].move if mon else ""
        return {"type": 1, "move": _lookup(MOVE_VOCAB, move_name),
                "target": 0, "mega": int(action.mega), "switch": 0}
    if isinstance(action, SwitchAction):
        sp = str(bench_mons(team)[action.bench_slot].species)
        return {"type": 2, "move": 0, "target": 0, "mega": 0, "switch": resolve_species(sp)}
    return {"type": 0, "move": 0, "target": 0, "mega": 0, "switch": 0}


def _legal_pair(a, b) -> bool:
    """Same joint-legality _joint() enforces: two slots can't switch to the
    same bench mon, and only one mega per turn."""
    da, db = _switch_destination(a), _switch_destination(b)
    if da is not None and da == db:
        return False
    if isinstance(a, MoveAction) and isinstance(b, MoveAction) and a.mega and b.mega:
        return False
    return True


def _ranked_joints(evaluator, netstate, world, side, team, k, tier1_cap):
    """Top-k (prob, TurnActions) for `side`, ranked by net policy prob =
    p_left * p_right over each slot's legal actions.

    Candidates come from the SAME Tier-1 domain pruning the CFR solver uses
    (_pruned_slot_actions - immune/dominated-resisted attacks and Prankster-
    into-Dark cut, world-invariant/public-info only per the keying contract
    in model/action_space.py), not the raw enumeration. Without this the net
    search would happily propose e.g. Heat Wave into a double-resist target
    that the solver would never even consider - found live on MB552
    (Charizard Heat Wave into Garchomp+Charizard, both resist)."""
    left = _pruned_slot_actions(world, side, _LEFT, tier1_cap)
    right = _pruned_slot_actions(world, side, _RIGHT, tier1_cap)
    pol = evaluator.policy(netstate)
    p_left = evaluator.score_labels(pol, 0, [_action_label(a, team, _LEFT) for a in left])
    p_right = evaluator.score_labels(pol, 1, [_action_label(b, team, _RIGHT) for b in right])
    joints = []
    for i, a in enumerate(left):
        for j, b in enumerate(right):
            if _legal_pair(a, b):
                joints.append((float(p_left[i] * p_right[j]), TurnActions(slot_left=a, slot_right=b)))
    joints.sort(key=lambda t: -t[0])
    return joints[:k]


def net_depth1_decision(evaluator: NetEvaluator, bridge, worlds: list[FullInfoState],
                        my_netstate: dict, k_my: int = 4, k_opp: int = 4,
                        tier1_cap: int = 6, matrix_iterations: int = 200,
                        rng: random.Random | None = None) -> tuple:
    """Return (SAMPLED TurnActions, SearchDiagnostics). my_netstate is the
    me-POV state for MY policy (ideally the live observable one); `worlds`
    are determinized full states for the engine rollout + the opponent
    model. tier1_cap is the per-slot Tier-1 pruning cap (matches
    SolverPlayer's per_slot_cap default of 6) - the candidate pool BEFORE
    net-policy top-k narrows it further to k_my/k_opp. matrix_iterations is
    the regret-matching iteration count for the k_my x k_opp matrix solve
    (pure arithmetic on a tiny matrix, no engine calls - cheap even at a
    few hundred). rng samples the returned action from the solved mixed
    strategy; pass one for reproducible tests/self-play, otherwise a fresh
    random.Random() is used (non-reproducible)."""
    rng = rng or random.Random()
    diag = SearchDiagnostics()
    my_cands = _ranked_joints(evaluator, my_netstate, worlds[0], "me", worlds[0].my_team, k_my, tier1_cap)
    n_my = len(my_cands)

    # Gather every (world, my, opp) leaf, batching value-head calls. Columns
    # are OPPONENT-POLICY RANK POSITIONS (0 = their top choice, ...), not a
    # single literal action: each world's determinization can give the
    # opponent's hidden mon a different real moveset, so the action at
    # column j can differ world to world. That's fine for what we need -
    # a legitimate MIXED STRATEGY over MY OWN fixed candidate set - we just
    # average column j's payoff over the worlds that had a j-th candidate
    # (a world with fewer legal opponent options simply skips the missing
    # columns; every world always has at least a column 0).
    #
    # One init_battle PER WORLD (not per rollout): step() branches repeatedly
    # from the same (handle, root) - the same primitive model/solver_game.py's
    # EngineGame uses. Every handle is tracked and freed below; skipping that
    # leaks battles in the engine's node process until it dies with
    # "Reached heap limit - JavaScript heap out of memory".
    leaf_states, leaf_ix = [], []          # non-terminal leaves to value in one batch
    contribs = []                          # (my_idx, opp_col_idx, kind, payload)
    world_opp_counts: list[int] = []       # len(opp_cands) per world, for column averaging
    handles: list[int] = []
    try:
        for w in worlds:
            opp_ns = flip_netstate(full_info_state_to_netstate(w))
            opp_cands = _ranked_joints(evaluator, opp_ns, w, "opp", w.opp_team, k_opp, tier1_cap)
            world_opp_counts.append(len(opp_cands))
            root_handle, root_state = bridge.init_battle(w)
            handles.append(root_handle)
            for mi, (_, m) in enumerate(my_cands):
                for oi, (_, o) in enumerate(opp_cands):
                    res = bridge.step(root_handle, root_state, m, o)
                    if res.handle is not None:
                        handles.append(res.handle)
                    diag.rollouts += 1
                    diag.engine_errors += len(res.errors)
                    if res.terminal is not None:
                        contribs.append((mi, oi, "term", (res.terminal + 1.0) / 2.0))
                    else:
                        leaf_ix.append(len(contribs))
                        leaf_states.append(full_info_state_to_netstate(res.state))
                        contribs.append((mi, oi, "leaf", None))
    finally:
        if handles:
            bridge.free(handles)

    leaf_vals = evaluator.value_batch(leaf_states) if leaf_states else np.zeros(0)
    for slot, ci in enumerate(leaf_ix):
        mi, oi, _, _ = contribs[ci]
        contribs[ci] = (mi, oi, "term", float(leaf_vals[slot]))

    max_cols = max(world_opp_counts)
    sums = np.zeros((n_my, max_cols), dtype=np.float64)
    counts = np.zeros(max_cols, dtype=np.float64)
    for n in world_opp_counts:
        counts[:n] += 1.0
    for mi, oi, _, v in contribs:
        sums[mi, oi] += v
    keep_cols = np.flatnonzero(counts > 0)
    M = sums[:, keep_cols] / counts[keep_cols]   # my-POV payoff matrix, n_my x n_cols

    # Solve the small zero-sum matrix game (model/regret.py - the same
    # regret-matching primitive the CFR tree uses) for MY mixed strategy,
    # and SAMPLE from it rather than taking the argmax: VGC is simultaneous-
    # move, so a pure best-response is exploitable, and argmax silently
    # never selects moves the policy itself considers likely-but-not-best
    # (Protect was 0/75 in live testing despite ~12% average policy mass -
    # see [[imitation-net-v1]]'s diagnostics). Sampling restores that
    # behavior and is required for sound self-play (pure-strategy
    # improvement can cycle in a simultaneous-move game).
    row_strategy, _col_strategy = solve_matrix_game(M.tolist(), matrix_iterations)
    order = np.argsort(-np.asarray(row_strategy))
    diag.strategy = [(float(row_strategy[i]), my_cands[i][1]) for i in order]
    diag.matrix = M.tolist()

    chosen = rng.choices(range(n_my), weights=row_strategy, k=1)[0]
    return my_cands[chosen][1], diag
