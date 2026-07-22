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

from schema.battle_state import MoveAction, SwitchAction, TurnActions, Position, Target
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


# schema Target -> model/encoding.py's _TARGET index ("none","opp_a","opp_b",
# "self","ally") - already given relative to the acting side by the
# schema's own convention, same as _TARGET's, so this is a direct lookup,
# no relative-side computation needed.
_TARGET_TO_INDEX = {Target.NONE: 0, Target.OPP_LEFT: 1, Target.OPP_RIGHT: 2,
                    Target.SELF: 3, Target.ALLY: 4}


def _action_label(action, team: list, position: Position) -> dict:
    """schema Action -> encoder action label (type/move/target/mega/switch),
    resolving move_slot/bench_slot against the acting team.

    Target now correctly reflects the real chosen target (2026-07-21 fix,
    [[net-external-review-2026-07-21]]) - it was previously hardcoded to 0
    regardless of the actual action, which would have silently defeated
    NetEvaluator.score_labels' matching fix to actually USE the target head
    in ranking (a label always claiming "no target" can never be told apart
    from one that actually targets something)."""
    if isinstance(action, MoveAction):
        mon = active_mon(team, position)
        move_name = mon.moves[action.move_slot - 1].move if mon else ""
        return {"type": 1, "move": _lookup(MOVE_VOCAB, move_name),
                "target": _TARGET_TO_INDEX.get(action.target, 0), "mega": int(action.mega), "switch": 0}
    if isinstance(action, SwitchAction):
        sp = str(bench_mons(team)[action.bench_slot].species)
        return {"type": 2, "move": 0, "target": 0, "mega": 0, "switch": resolve_species(sp)}
    return {"type": 0, "move": 0, "target": 0, "mega": 0, "switch": 0}


def _label_key(label: dict) -> tuple:
    """A hashable, canonical, WORLD-INDEPENDENT identity for one slot's
    action label - used to align matrix columns by real action identity
    rather than by rank position (see net_depth1_decision's fix note)."""
    return (label["type"], label["move"], label["target"], label["mega"], label["switch"])


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
    # are keyed by the opponent's REAL ACTION IDENTITY (2026-07-21 fix,
    # [[net-external-review-2026-07-21]]: a prior version keyed columns by
    # OPPONENT-POLICY RANK POSITION - "their j-th most likely choice" - which
    # is NOT the same real action across worlds (a determinization can give
    # the opponent's hidden mon a different real moveset), so averaging
    # column j's payoff across worlds silently blended together whatever
    # DIFFERENT real moves each world happened to rank j-th, then solved
    # that artificial construct adversarially. Keying by identity instead
    # (_label_key, built from the same canonical move/target/mega/switch
    # labels used for scoring) means a column is always the SAME real
    # action; a world whose hidden info makes that action illegal/different
    # simply contributes nothing to it, rather than smearing a different
    # move's payoff into the slot.
    #
    # One init_battle PER WORLD (not per rollout): step() branches repeatedly
    # from the same (handle, root) - the same primitive model/solver_game.py's
    # EngineGame uses. Every handle is tracked and freed below; skipping that
    # leaks battles in the engine's node process until it dies with
    # "Reached heap limit - JavaScript heap out of memory".
    leaf_states, leaf_ix = [], []          # non-terminal leaves to value in one batch
    contribs = []                          # (my_idx, col_idx, kind, payload)
    col_index: dict[tuple, int] = {}       # action-identity key -> column index (first-seen order)
    world_col_ids: list[set[int]] = []     # per world, which columns it contributed to (for averaging)
    handles: list[int] = []
    try:
        for w in worlds:
            opp_ns = flip_netstate(full_info_state_to_netstate(w))
            opp_cands = _ranked_joints(evaluator, opp_ns, w, "opp", w.opp_team, k_opp, tier1_cap)
            root_handle, root_state = bridge.init_battle(w)
            handles.append(root_handle)
            this_world_cols: set[int] = set()
            for mi, (_, m) in enumerate(my_cands):
                for _, o in opp_cands:
                    key = (_label_key(_action_label(o.slot_left, w.opp_team, _LEFT)),
                          _label_key(_action_label(o.slot_right, w.opp_team, _RIGHT)))
                    ci = col_index.setdefault(key, len(col_index))
                    this_world_cols.add(ci)
                    res = bridge.step(root_handle, root_state, m, o)
                    if res.handle is not None:
                        handles.append(res.handle)
                    diag.rollouts += 1
                    diag.engine_errors += len(res.errors)
                    if res.terminal is not None:
                        contribs.append((mi, ci, "term", (res.terminal + 1.0) / 2.0))
                    else:
                        leaf_ix.append(len(contribs))
                        leaf_states.append(full_info_state_to_netstate(res.state))
                        contribs.append((mi, ci, "leaf", None))
            world_col_ids.append(this_world_cols)
    finally:
        if handles:
            bridge.free(handles)

    leaf_vals = evaluator.value_batch(leaf_states) if leaf_states else np.zeros(0)
    for slot, ci in enumerate(leaf_ix):
        mi, oi, _, _ = contribs[ci]
        contribs[ci] = (mi, oi, "term", float(leaf_vals[slot]))

    n_cols = len(col_index)
    sums = np.zeros((n_my, n_cols), dtype=np.float64)
    counts = np.zeros(n_cols, dtype=np.float64)
    for cols in world_col_ids:
        for ci in cols:
            counts[ci] += 1.0
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
