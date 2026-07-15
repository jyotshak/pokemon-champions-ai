"""Greedy expected-damage-maximizing baseline policy.

Not the real model - this is infrastructure: it proves the full loop
(belief-tracker -> policy -> harness -> engine -> new state) works with
genuine decision-making instead of random moves, and it's meant to serve
as a first sparring opponent once real self-play training starts (an
opponent slightly better than random is far more useful to train against
than pure randomness).

Team preview is a placeholder too (bring the 4 highest base-stat-total
mons, lead with the top 2) - not the real evaluator-based search
discussed for team preview; that needs the real model to exist first.

Depends only on schema/ + reference/ data (via damage_calc.py) - no
poke-env/CV-specific code belongs here, per the architecture-goal.
"""

import json
from pathlib import Path

from model.damage_calc import estimate_opponent_stats, expected_damage, is_spread_move
from schema.battle_state import (
    Action, BattleState, MoveAction, NoAction, OwnPokemon, Position, SwitchAction, Target, TeamPreviewAction, TurnActions,
)

_ROOT = Path(__file__).resolve().parent.parent
_MOVE_DATA = json.loads((_ROOT / "reference" / "move_data.json").read_text(encoding="utf-8"))
_SPECIES_STATS = json.loads((_ROOT / "reference" / "species_stats.json").read_text(encoding="utf-8"))

_ALLY_TARGETS = {"adjacentAlly", "adjacentAllyOrSelf"}


def _own_stats(mon: OwnPokemon) -> dict:
    return {**mon.stats, "hp": mon.max_hp}


def choose_team_preview(state: BattleState) -> TeamPreviewAction:
    roster = state.team_preview.my_team
    ranked = sorted(range(len(roster)), key=lambda i: -sum(_SPECIES_STATS[roster[i]]["base_stats"].values()))
    bring = ranked[:4]
    return TeamPreviewAction(bring=bring, lead_order=bring[:2])


def _default_target(move_target_field: str) -> Target:
    if move_target_field == "self":
        return Target.SELF
    if move_target_field in _ALLY_TARGETS:
        return Target.ALLY
    return Target.NONE


def _is_mega_stone(item: str) -> bool:
    return item is not None and item.endswith(("ite", "itex", "itey"))


def _choose_switch_in(state: BattleState, claimed_bench: set[int]) -> Action:
    """A position with no active mon (fainted and not yet replaced) needs a
    switch, not NoAction (that's only for Commander-hidden slots). Picks
    the first live, not-already-claimed-this-turn bench mon - no real
    "best switch-in" evaluation in V1. claimed_bench prevents sending the
    same replacement out for both slots if both faint in the same turn.
    """
    for i, bench_mon in enumerate(state.my_bench):
        if not bench_mon.fainted and i not in claimed_bench:
            claimed_bench.add(i)
            return SwitchAction(bench_slot=i)
    return NoAction()  # no live mon left to switch to


def _choose_slot_action(state: BattleState, mon: OwnPokemon | None, claimed_bench: set[int]) -> Action:
    if mon is None or mon.fainted:
        return _choose_switch_in(state, claimed_bench)

    attacker_stats = _own_stats(mon)
    live_opponents = [o for o in state.opp_active if not o.fainted]

    best = None      # (expected_damage, move_slot_number, target)
    fallback = None  # (move_slot_number, target) - first legal move, used if nothing scores > 0

    for i, move_slot in enumerate(mon.moves, start=1):
        if move_slot.pp <= 0 or move_slot.disabled:
            continue
        move_id = move_slot.move
        meta = _MOVE_DATA.get(move_id, {})
        move_target_field = meta.get("target", "normal")

        if fallback is None:
            fallback = (i, _default_target(move_target_field))

        if not live_opponents:
            continue

        if is_spread_move(move_id):
            dmg = sum(
                expected_damage(move_id, mon.species, attacker_stats, opp.species, estimate_opponent_stats(opp.species))
                for opp in live_opponents
            )
            candidate = (dmg, i, Target.NONE)
        elif move_target_field in ("normal", "any", "adjacentFoe"):
            candidate = None
            for opp in live_opponents:
                dmg = expected_damage(move_id, mon.species, attacker_stats, opp.species, estimate_opponent_stats(opp.species))
                target = Target.OPP_LEFT if opp.position == Position.LEFT else Target.OPP_RIGHT
                if candidate is None or dmg > candidate[0]:
                    candidate = (dmg, i, target)
        else:
            candidate = None  # status/support move - not scored in V1

        if candidate and (best is None or candidate[0] > best[0]):
            best = candidate

    if best is not None and best[0] > 0:
        _, move_slot_idx, target = best
        mega = not state.field.my_side.mega_used and _is_mega_stone(mon.item) and not mon.mega_activated
        return MoveAction(move_slot=move_slot_idx, target=target, mega=mega)

    if fallback is not None:
        move_slot_idx, target = fallback
        return MoveAction(move_slot=move_slot_idx, target=target)

    return NoAction()


def choose_turn_actions(state: BattleState) -> TurnActions:
    # state.my_active is variable-length (only currently-populated slots),
    # so it must be looked up by .position, never by list index - a slot
    # can be entirely absent from the list (fainted, not yet replaced),
    # which silently shifts list indices otherwise.
    left_mon = next((m for m in state.my_active if m.position == Position.LEFT), None)
    right_mon = next((m for m in state.my_active if m.position == Position.RIGHT), None)
    claimed_bench: set[int] = set()
    return TurnActions(
        slot_left=_choose_slot_action(state, left_mon, claimed_bench),
        slot_right=_choose_slot_action(state, right_mon, claimed_bench),
    )
