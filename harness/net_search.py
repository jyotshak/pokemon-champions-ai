"""Depth-1 policy+value search driven by the trained net ([[imitation-net-v1]],
[[replay-net-direction]]). This is the "incorporate current-turn branches"
step: the imitation policy alone under-picks rare-but-strong reads (Wide Guard
in the position eval), so instead of clicking the policy we let it PROPOSE the
few branches worth simulating and let the VALUE head judge the outcomes.

Per turn:
  1. Net policy ranks my legal joint actions -> keep top-k_my (the branches).
  2. For each determinized world, net policy (side-flipped) ranks the
     opponent's legal joint actions -> top-k_opp (a policy-weighted opponent
     model, not a uniform or worst-case one).
  3. Engine rolls each (my, opp) one real turn forward; a terminal turn gives
     a true +-1, otherwise the value head scores the leaf.
  4. My action's score = mean over worlds of the opp-policy-weighted leaf
     value; pick the argmax.

Reuses the EXISTING legal-action enumeration (model/action_space.py) so every
candidate is engine-ready, and the EXISTING encoder action labels
(model/encoding.py) so the net can score them - no new action logic. Schema/
engine-facing, so it lives in harness/ (model/ stays input-neutral).
"""

from dataclasses import dataclass, field

import numpy as np

from schema.battle_state import MoveAction, SwitchAction, TurnActions, Position
from schema.full_info_state import FullInfoState, active_mon, bench_mons
from model.action_space import propose_slot_actions, _switch_destination
from model.encoding import resolve_species, _lookup, MOVE_VOCAB
from model.net_infer import NetEvaluator
from harness.net_translate import full_info_state_to_netstate, flip_netstate

_LEFT, _RIGHT = Position.LEFT, Position.RIGHT


@dataclass
class SearchDiagnostics:
    rollouts: int = 0
    engine_errors: int = 0
    my_values: list = field(default_factory=list)   # (value, TurnActions) sorted desc


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


def _ranked_joints(evaluator, netstate, world, side, team, k):
    """Top-k (prob, TurnActions) for `side`, ranked by net policy prob =
    p_left * p_right over each slot's legal actions."""
    left = propose_slot_actions(world, side, _LEFT)
    right = propose_slot_actions(world, side, _RIGHT)
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
                        my_netstate: dict, k_my: int = 4, k_opp: int = 4) -> tuple:
    """Return (best TurnActions, SearchDiagnostics). my_netstate is the me-POV
    state for MY policy (ideally the live observable one); `worlds` are
    determinized full states for the engine rollout + the opponent model."""
    diag = SearchDiagnostics()
    my_cands = _ranked_joints(evaluator, my_netstate, worlds[0], "me", worlds[0].my_team, k_my)

    # Gather every (world, my, opp) leaf, batching value-head calls.
    # One init_battle PER WORLD (not per rollout): step() branches repeatedly
    # from the same (handle, root) - the same primitive model/solver_game.py's
    # EngineGame uses. Every handle is tracked and freed below; skipping that
    # leaks battles in the engine's node process until it dies with
    # "Reached heap limit - JavaScript heap out of memory".
    leaf_states, leaf_ix = [], []          # non-terminal leaves to value in one batch
    contribs = []                          # (my_idx, weight, kind, payload)
    handles: list[int] = []
    try:
        for w in worlds:
            opp_ns = flip_netstate(full_info_state_to_netstate(w))
            opp_cands = _ranked_joints(evaluator, opp_ns, w, "opp", w.opp_team, k_opp)
            z = sum(p for p, _ in opp_cands) or 1.0
            root_handle, root_state = bridge.init_battle(w)
            handles.append(root_handle)
            for mi, (_, m) in enumerate(my_cands):
                for po, o in opp_cands:
                    res = bridge.step(root_handle, root_state, m, o)
                    if res.handle is not None:
                        handles.append(res.handle)
                    diag.rollouts += 1
                    diag.engine_errors += len(res.errors)
                    w_opp = (po / z) / len(worlds)   # opp-policy weight, averaged over worlds
                    if res.terminal is not None:
                        contribs.append((mi, w_opp, "term", (res.terminal + 1.0) / 2.0))
                    else:
                        leaf_ix.append(len(contribs))
                        leaf_states.append(full_info_state_to_netstate(res.state))
                        contribs.append((mi, w_opp, "leaf", None))
    finally:
        if handles:
            bridge.free(handles)

    leaf_vals = evaluator.value_batch(leaf_states) if leaf_states else np.zeros(0)
    for slot, ci in enumerate(leaf_ix):
        mi, w_opp, _, _ = contribs[ci]
        contribs[ci] = (mi, w_opp, "term", float(leaf_vals[slot]))

    agg = np.zeros(len(my_cands), dtype=np.float64)
    for mi, w_opp, _, v in contribs:
        agg[mi] += w_opp * v
    order = np.argsort(-agg)
    diag.my_values = [(float(agg[i]), my_cands[i][1]) for i in order]
    return my_cands[int(order[0])][1], diag
