"""Greedy expected-damage-maximizing baseline policy.

Not the real model - this is infrastructure: it proves the full loop
(belief-tracker -> policy -> harness -> engine -> new state) works with
genuine decision-making instead of random moves, and it's meant to serve
as a first sparring opponent once real self-play training starts (an
opponent slightly better than random is far more useful to train against
than pure randomness).

Team preview is opponent-aware (not a dumb top-4-base-stat-total sort
anymore): it shares model/team_preview_scoring.py's bring_subset_score/
lead_pair_score with the search pruner (model/action_space.py::
propose_pruned_team_preview_actions), taking the single argmax bring
subset then its single argmax lead pair instead of a pruned top-K - same
type-coverage/synergy/mega-usage scoring, just not search-based.

Depends only on schema/ + reference/ data (via damage_calc.py) - no
poke-env/CV-specific code belongs here, per the architecture-goal.
"""

import json
from itertools import combinations, permutations
from pathlib import Path

from model.damage_calc import (
    AVG_RANDOM_FACTOR, LEVEL, estimate_opponent_stats, expected_damage, is_spread_move, species_types,
    type_effectiveness,
)
from model.team_preview_scoring import bring_subset_score, lead_pair_score
from schema.battle_state import (
    Action, BattleState, MoveAction, NoAction, OwnPokemon, Position, SwitchAction, Target, TeamPreviewAction, TurnActions,
)

_ROOT = Path(__file__).resolve().parent.parent
_MOVE_DATA = json.loads((_ROOT / "reference" / "move_data.json").read_text(encoding="utf-8"))

_ALLY_TARGETS = {"adjacentAlly", "adjacentAllyOrSelf"}


def _own_stats(mon: OwnPokemon) -> dict:
    return {**mon.stats, "hp": mon.max_hp}


def choose_team_preview(
    state: BattleState, synergy_weights: dict | None = None, synergy_scale: float = 1.0,
    mega_penalty: float = 0.0,
) -> TeamPreviewAction:
    """Two-stage argmax, mirroring propose_pruned_team_preview_actions'
    shape at cap=1: pick the single best bring-4 subset via
    bring_subset_score, then that subset's single best lead-pair via
    lead_pair_score. synergy_weights/mega_penalty default to inert
    (None/0.0) - callers (harness/) inject the real belief-layer table
    for live play, same as the search pruner.
    """
    roster = state.team_preview.my_team
    enemy_roster = state.team_preview.opp_team
    n = len(roster)

    best_subset = max(
        combinations(range(n), 4),
        key=lambda subset: bring_subset_score(
            [roster[i] for i in subset], enemy_roster, synergy_weights, synergy_scale, mega_penalty,
        ),
    )
    best_pair = max(
        permutations(best_subset, 2),
        key=lambda pair: lead_pair_score([roster[i] for i in pair], enemy_roster, synergy_weights, synergy_scale),
    )
    return TeamPreviewAction(bring=list(best_subset), lead_order=list(best_pair))


def _default_target(move_target_field: str) -> Target:
    if move_target_field == "self":
        return Target.SELF
    if move_target_field in _ALLY_TARGETS:
        return Target.ALLY
    return Target.NONE


def _is_mega_stone(item: str) -> bool:
    return item is not None and item.endswith(("ite", "itex", "itey"))


_PROXY_BASE_POWER = 80  # a representative "average" attacking move's base power


def _type_proxy_damage(attacker_species: str, defender_species: str, defender_stats: dict) -> float:
    """A crude expected-damage stand-in for an opponent mon with zero
    revealed moves: assumes a representative 80-BP STAB move off
    whichever of the attacker's own types is worst for the defender,
    using estimate_opponent_stats for the attacker's own stats. Not a
    real move - just enough type/stat signal to prefer a switch-in that
    resists/is-immune-to the opponent's likely STAB coverage over one
    that doesn't, which is exactly the reasoning the old "first bench
    mon" heuristic skipped entirely (the Swampert-over-Pelipper bug this
    replaces: Pelipper is Ground-immune and Water-resists-Fire, Swampert
    only has the latter).
    """
    attacker_stats = estimate_opponent_stats(attacker_species)
    atk_stat = max(attacker_stats["atk"], attacker_stats["spa"])
    def_stat = min(defender_stats["def"], defender_stats["spd"])
    base = (((2 * LEVEL / 5 + 2) * _PROXY_BASE_POWER * atk_stat / def_stat) / 50) + 2
    worst_type_mult = max(
        type_effectiveness(t, species_types(defender_species)) for t in species_types(attacker_species)
    )
    return base * 1.5 * worst_type_mult * AVG_RANDOM_FACTOR


def _incoming_danger(candidate_species: str, opp_active: list) -> float:
    """Worst-case expected damage the candidate would face switching in
    against the CURRENT live opponent actives (whatever's been revealed
    by now - mega evolution, item, moves - since this is called at the
    moment the real mid-turn request arrives, not pre-decided earlier in
    the turn): per opponent mon, the max real expected_damage among its
    revealed_moves if any exist, else the type-based proxy above. Summed
    across every live opponent active (both could plausibly attack the
    incoming mon in doubles).
    """
    defender_stats = estimate_opponent_stats(candidate_species)
    total = 0.0
    for opp in opp_active:
        if opp.fainted:
            continue
        opp_stats = estimate_opponent_stats(opp.species)
        if opp.revealed_moves:
            total += max(
                expected_damage(move_id, opp.species, opp_stats, candidate_species, defender_stats)
                for move_id in opp.revealed_moves
            )
        else:
            total += _type_proxy_damage(opp.species, candidate_species, defender_stats)
    return total


def _choose_switch_in(state: BattleState, claimed_bench: set[int]) -> Action:
    """A position with no active mon (fainted and not yet replaced) needs a
    switch, not NoAction (that's only for Commander-hidden slots). Picks
    the living, not-already-claimed-this-turn bench mon with the LOWEST
    _incoming_danger against the opponent's CURRENT actives - a cheap,
    non-search comparison (no engine call), but a real one: it's
    evaluated at the moment this is actually called (the real mid-turn
    request), so it sees whatever's already been revealed by then (an
    opponent's mega evolution always resolves before any move, even a
    Prankster-boosted one, so it's visible in time; a just-revealed move
    or item is too) - not a stale snapshot from when the turn began.
    claimed_bench prevents sending the same replacement out for both
    slots if both need one at once.
    """
    candidates = [i for i, m in enumerate(state.my_bench) if not m.fainted and i not in claimed_bench]
    if not candidates:
        return NoAction()  # no live mon left to switch to
    best_i = min(candidates, key=lambda i: _incoming_danger(state.my_bench[i].species, state.opp_active))
    claimed_bench.add(best_i)
    return SwitchAction(bench_slot=best_i)


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

    # No usable move at all, yet this mon is alive (not caught by the
    # mon-is-None/fainted branch above): genuine Struggle territory (a
    # normal-turn request always offers SOME move otherwise - see
    # choose_forced_switches below for the far more common real cause,
    # a pending forced self-switch, which callers now route around this
    # function entirely). A living, untrapped bench mon still means
    # switching beats passing even here.
    if not mon.trapped and any(not b.fainted for b in state.my_bench):
        return _choose_switch_in(state, claimed_bench)
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


def choose_forced_switches(state: BattleState, force_switch: list[bool]) -> TurnActions:
    """The whole action for a mid-turn forced-switch request (a mon
    fainted, or a self-switching move like Parting Shot/U-turn forced its
    user out): each slot either submits a switch (force_switch[i]=True)
    or passes (False) - never a move, this request type doesn't offer one.
    Deliberately bypasses _choose_slot_action/choose_turn_actions' move-
    scoring entirely rather than computing it and discarding the result
    for the non-participating slot (the old pattern, still visible in
    harness/*_player.py's git history): Showdown doesn't re-list moves
    for a slot that isn't being asked to choose this request, which
    _choose_slot_action's Struggle-territory fallback (see above) reads
    as "no usable move, living bench available" and switches - correct
    when it's genuinely that slot's own turn to switch, wrong when it's
    just an artifact of the OTHER slot's request. Computing both slots
    via the general policy let the non-participating slot spuriously
    claim the one remaining bench mon (mutating the shared claimed_bench
    set) before the slot that actually needed it got a turn, silently
    leaving the real request unanswered - found via a real stuck-request
    loop (the same request re-issued hundreds of times, since neither
    NoAction/"pass" nor a wrongly-targeted switch ever satisfies it).
    force_switch is the caller's poke-env battle.force_switch, passed in
    rather than read here - this module stays poke-env-agnostic.
    """
    claimed_bench: set[int] = set()
    return TurnActions(
        slot_left=_choose_switch_in(state, claimed_bench) if force_switch[0] else NoAction(),
        slot_right=_choose_switch_in(state, claimed_bench) if force_switch[1] else NoAction(),
    )
