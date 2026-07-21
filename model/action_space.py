"""Legal-action enumeration for search nodes (docs/solver_design.md 2.5).

propose_slot_actions/propose_turn_actions are the pruning seam: today
they enumerate everything legal, later a policy net can return a top-K
subset behind the same signatures without the node logic changing.

Target handling follows Showdown's own move `target` field
(reference/move_data.json):
- normal / any / adjacentFoe  -> branch over each living opposing slot
- adjacentAlly                -> ALLY (only if the ally is on the field)
- adjacentAllyOrSelf          -> SELF, plus ALLY if present
- self                        -> SELF
- everything else (spread, sides, field, random, scripted) -> NONE
  (no targeting decision exists for these)

Mega branching: if the mon holds a stone that megas ITS species
(reference/mega_stones.json) and its side hasn't used its Mega, every
move option branches mega=True/False — mega timing is a real decision.
Megas happen with a move, never on a switch (schema already encodes
this: only MoveAction carries the flag).

Cross-slot legality in the joint product (the only two that exist —
everything else, like mid-turn target redirection, the engine resolves
itself): two slots can't switch to the same bench mon, and only one
slot can mega per turn.

Trapping and forced-continuation moves (mid-recharge, mid-two-turn-move
like Solar Beam/Fly): both are unified by the engine's own OwnPokemon.
trapped flag (docs/solver_design.md - sourced from Pokemon.
getMoveRequestData(), the real request-generation call, not a
reimplementation). trapped alone means no switch options; trapped with a
single-entry moves list means that one entry is the forced continuation
- no target selection (it was already locked in) and no mega.

Known V1 simplifications (deliberate): no deliberate ally/self-targeting
of normal attacking moves (niche tech — Weakness Policy triggers etc.),
no move-lock modeling beyond the MoveSlot.disabled flag (no Choice items
are champions-legal anyway). A slot with no legal action at all (Struggle
territory / side down to one mon) yields NoAction, which the engine
bridge maps to pass/default.
"""

import json
import re
from itertools import combinations, permutations
from pathlib import Path
from typing import Optional

from model.damage_calc import expected_damage, is_spread_move, species_types, type_effectiveness
from model.team_preview_scoring import bring_subset_score, lead_pair_score, own_support_score
from schema.full_info_state import FullInfoState, TeamPreviewRootState, active_mon, bench_mons
from schema.battle_state import (
    Action, MoveAction, NoAction, OwnPokemon, Position, SwitchAction, Target, TeamPreviewAction,
    TurnActions,
)

_ROOT = Path(__file__).resolve().parent.parent
_MOVE_DATA = json.loads((_ROOT / "reference" / "move_data.json").read_text(encoding="utf-8"))
_MEGA_STONES = json.loads((_ROOT / "reference" / "mega_stones.json").read_text(encoding="utf-8"))

_SINGLE_TARGET = {"normal", "any", "adjacentFoe"}


def _can_mega(mon: OwnPokemon, mega_used: bool) -> bool:
    if mega_used or mon.mega_activated or not mon.item:
        return False
    return mon.species in _MEGA_STONES.get(mon.item, {})


def _sides(state: FullInfoState, side: str):
    if side == "me":
        return state.my_team, state.opp_team, state.field.my_side
    return state.opp_team, state.my_team, state.field.opp_side


def propose_slot_actions(state: FullInfoState, side: str, position: Position) -> list[Action]:
    team, other_team, side_conditions = _sides(state, side)
    mon = active_mon(team, position)
    bench = bench_mons(team)

    if mon is None:
        # Empty slot at a between-turns decision point: mid-turn
        # replacements are resolved inside step(), so a still-empty slot
        # means this side has no living mon to field here — pass.
        return [NoAction()]

    if any(v.name == "must_recharge" for v in mon.volatiles):
        # A mon translated from a LIVE recharge request (harness/
        # translator.py::own_pokemon, from poke-env's Effect.MUST_RECHARGE)
        # keeps its REAL 4-move moveset (all marked disabled) rather than a
        # single synthetic entry - see that function's docstring for why
        # (a synthetic id has no PP data and breaks engine rebuilds). Left
        # to the generic move/switch enumeration below, an exhausted bench
        # produces [NoAction()] (a real Sylveon-mid-recharge-with-no-bench
        # case that stalled a live match, then broke a search rollout the
        # same way: the engine, having no idea this mon must recharge,
        # rejects the resulting pass with "Can't pass: ... must make a
        # move"). Bypass all of that: propose the single forced move
        # directly. move_slot's VALUE doesn't matter - Showdown's own
        # getLockedMove() (conditions.ts's mustrecharge: onLockMove) forces
        # the real recharge regardless of which move we name, PROVIDED
        # engine/bridge.js's applyMonState reconstructs the matching
        # volatile (see its own comment) so getLockedMove() actually fires.
        # No switch is offered either - matches the real mechanic (a
        # recharging mon cannot switch) instead of the engine wrongly
        # allowing it once the volatile is otherwise lost on reconstruction.
        return [MoveAction(move_slot=1, target=Target.NONE)]

    if mon.trapped and len(mon.moves) == 1:
        # Forced single continuation (mid-recharge, or locked into a
        # two-turn move like Solar Beam/Fly) - the engine's own request
        # generation narrows to exactly this one synthetic/real entry with
        # no target selection (the target, if any, was already locked in
        # on the original turn) and no mega/switch options. `trapped` is
        # set by the engine for both this case and genuine trapping
        # abilities (Arena Trap etc.) - the single-move-list check is what
        # narrows it to specifically this one. (This is the ENGINE-
        # RECONSTRUCTED shape, e.g. a state echoed back mid-search after a
        # real turn resolved; the must_recharge-volatile check above is the
        # LIVE-TRANSLATED shape, where the real 4-move moveset survives.)
        return [MoveAction(move_slot=1, target=Target.NONE)]

    ally_position = Position.RIGHT if position == Position.LEFT else Position.LEFT
    ally = active_mon(team, ally_position)
    opposing_targets = [
        Target.OPP_LEFT if m.position == Position.LEFT else Target.OPP_RIGHT
        for m in other_team
        if m.position is not None and not m.fainted
    ]
    can_mega = _can_mega(mon, side_conditions.mega_used)
    # A mon with exactly one move slot is mid forced-continuation (locked
    # into a synthetic single entry - recharge/struggle/a two-turn move's
    # own id, same convention as this function's own trapped+single-entry
    # branch above), never a genuine 4-move champions set. Reconstructing
    # ANY such team via model/solver_game.py's self-switch bench reorder
    # (a fresh engine/bridge.py init_battle -> buildSet) is unsafe: builds
    # a bogus moveset from that one synthetic id, which has no real PP
    # data behind it (found live, several turns into a real search tree -
    # surfaced as a pydantic ValidationError on move pp/max_pp being None,
    # and can cascade to other mons once one reconstruction is corrupted).
    # Gating switch_bench_slot branching itself (rather than fixing the
    # reconstruction) keeps this to a narrow, rare-case fallback: the move
    # still executes normally via the engine's own default forced-switch
    # auto-pick (the pre-existing, less-tactical-but-safe behavior), same
    # as the state before this feature existed. Checked across BOTH teams
    # (not just this side's): a fresh init_battle reconstructs my_team AND
    # opp_team together in one call, so a hazard on EITHER side breaks the
    # reorder regardless of which side's move triggers it.
    safe_to_reorder = all(len(m.moves) != 1 for m in state.my_team + state.opp_team)

    actions: list[Action] = []
    for slot_number, move_slot in enumerate(mon.moves, start=1):
        if move_slot.pp <= 0 or move_slot.disabled:
            continue
        target_field = _MOVE_DATA.get(move_slot.move, {}).get("target", "normal")
        if move_slot.move == "curse" and "Ghost" not in species_types(mon.species):
            # The one move in the whole dex whose effective target depends
            # on the USER's own type, not a fixed per-move property (real
            # Showdown mechanic, confirmed in data/moves.ts: Ghost-types
            # curse an opponent, everyone else self-buffs with no target
            # at all - our static move_data.json only captures the
            # Ghost-type "normal" default). A one-off special case, same
            # as how the real engine itself hardcodes it rather than
            # generalizing a "type-dependent target" mechanism for what
            # is otherwise a single move.
            target_field = "self"
        if target_field in _SINGLE_TARGET:
            targets = opposing_targets or [Target.NONE]
        elif target_field == "adjacentAlly":
            targets = [Target.ALLY] if ally else []
        elif target_field == "adjacentAllyOrSelf":
            targets = [Target.SELF] + ([Target.ALLY] if ally else [])
        elif target_field == "self":
            targets = [Target.SELF]
        else:
            targets = [Target.NONE]
        self_switch = (
            bool(_MOVE_DATA.get(move_slot.move, {}).get("selfSwitch")) and len(bench) > 0 and safe_to_reorder
        )
        for target in targets:
            for mega in ([False, True] if can_mega else [False]):
                if self_switch:
                    # Branch over every living bench mon rather than one
                    # MoveAction: the switch-in this move triggers is a
                    # real tactical decision (docs/solver_design.md's
                    # forced-switch search section), not a fixed default -
                    # bundled onto the move itself (see MoveAction.
                    # switch_bench_slot's docstring) rather than a
                    # separate downstream node, since the engine's own
                    # forced-switch auto-pick is controllable purely via
                    # which bench mon comes first in team order, with zero
                    # engine changes needed.
                    for bench_slot in range(len(bench)):
                        actions.append(MoveAction(
                            move_slot=slot_number, target=target, mega=mega, switch_bench_slot=bench_slot,
                        ))
                else:
                    actions.append(MoveAction(move_slot=slot_number, target=target, mega=mega))

    if not mon.trapped:
        for bench_slot in range(len(bench)):
            actions.append(SwitchAction(bench_slot=bench_slot))

    if not actions:
        actions.append(NoAction())
    return actions


def _switch_destination(action: Action) -> Optional[int]:
    """Which bench index this action brings in, if any - a plain
    SwitchAction, or a self-switch MoveAction (switch_bench_slot set).
    Both draw from the same bench_mons() index space, so they can
    collide with each other, not just with their own kind.
    """
    if isinstance(action, SwitchAction):
        return action.bench_slot
    if isinstance(action, MoveAction):
        return action.switch_bench_slot
    return None


def _joint(left: list[Action], right: list[Action]) -> list[TurnActions]:
    joint: list[TurnActions] = []
    for a in left:
        for b in right:
            dest_a, dest_b = _switch_destination(a), _switch_destination(b)
            if dest_a is not None and dest_a == dest_b:
                continue
            if isinstance(a, MoveAction) and isinstance(b, MoveAction) and a.mega and b.mega:
                continue
            joint.append(TurnActions(slot_left=a, slot_right=b))
    return joint


def propose_turn_actions(state: FullInfoState, side: str) -> list[TurnActions]:
    return _joint(
        propose_slot_actions(state, side, Position.LEFT),
        propose_slot_actions(state, side, Position.RIGHT),
    )


def _action_damage(state: FullInfoState, side: str, mon: OwnPokemon, action: MoveAction) -> float:
    team, other_team, _ = _sides(state, side)
    move_id = mon.moves[action.move_slot - 1].move
    attacker_stats = {**mon.stats, "hp": mon.max_hp}

    def dmg(defender: OwnPokemon) -> float:
        return expected_damage(move_id, mon.species, attacker_stats, defender.species,
                               {**defender.stats, "hp": defender.max_hp})

    live_opposing = [m for m in other_team if m.position is not None and not m.fainted]
    if is_spread_move(move_id):
        return sum(dmg(m) for m in live_opposing)
    target_position = {Target.OPP_LEFT: Position.LEFT, Target.OPP_RIGHT: Position.RIGHT}.get(action.target)
    if target_position is None:
        return 0.0
    defender = next((m for m in live_opposing if m.position == target_position), None)
    return dmg(defender) if defender else 0.0


# Attacking moves whose PRIMARY value is a guaranteed on-hit effect
# (speed/attack control, spread chip that sets up a KO next turn), not the
# damage itself - so the type-effectiveness cut below must never drop them
# just because they read as "resisted" (the user's explicit carve-out:
# don't prune a move that has non-damage value). Icy Wind/Electroweb still
# drop Speed and Snarl still drops Sp. Atk even into a resisting target.
# Kept deliberately small and meta-specific (these are the champions-legal
# support attacks actually seen); a move not listed here is treated as a
# pure damage move for pruning purposes.
_SUPPORT_ATTACK_MOVES = {
    "icywind", "electroweb", "snarl", "bulldoze", "strugglebug", "mudshot",
    "lowsweep", "rocktomb", "glaciate", "pounce", "breakingswipe", "tickle",
    "fakeout",  # priority flinch — its value is the flinch/tempo, not damage
}


def _live_opposing(state: FullInfoState, side: str) -> list[OwnPokemon]:
    _, other_team, _ = _sides(state, side)
    return [m for m in other_team if m.position is not None and not m.fainted]


def _max_type_effectiveness(move_id: str, defenders: list[OwnPokemon]) -> Optional[float]:
    """Best (max) type multiplier this move's type gets against any living
    opposing mon, or None if the move has no type / there's nothing to hit.
    Reads only opponent SPECIES types (public team-preview info), so it is
    world-invariant - safe to gate MY-side pruning on (see the keying-
    contract note on propose_pruned_team_preview_actions). Max, not min: a
    move is worth keeping if it hits ANYONE neutrally, regardless of which
    target the damage scorer ends up pointing it at.
    """
    move_type = _MOVE_DATA.get(move_id, {}).get("type")
    if move_type is None or not defenders:
        return None
    return max(type_effectiveness(move_type, species_types(d.species)) for d in defenders)


def _is_attacking_move(move_id: str) -> bool:
    m = _MOVE_DATA.get(move_id, {})
    return m.get("category") in ("Physical", "Special") and m.get("basePower", 0) > 0


def _prankster_dark_blocked(state: FullInfoState, side: str, mon: OwnPokemon,
                            move_id: str, action: MoveAction) -> bool:
    """A Prankster user's status move aimed at the opponent fails outright
    against a Dark-type (real mechanic: Dark is immune to Prankster-boosted
    status). Cut it only when EVERY living opposing mon is Dark - if a
    non-Dark target exists the move can simply aim there. Uses the user's
    OWN ability (known/world-invariant for my side; the sampled one for the
    opponent side, whose node keying is world-scoped anyway) and public
    opponent types.
    """
    if re.sub(r"[^a-z0-9]", "", (mon.ability or "").lower()) != "prankster":
        return False
    if _MOVE_DATA.get(move_id, {}).get("category") != "Status":
        return False
    if action.target not in (Target.OPP_LEFT, Target.OPP_RIGHT):
        return False
    defenders = _live_opposing(state, side)
    return bool(defenders) and all("Dark" in species_types(d.species) for d in defenders)


def _filter_dominated_moves(state: FullInfoState, side: str, mon: OwnPokemon,
                            best_per_slot: dict[int, tuple[float, MoveAction]]
                            ) -> dict[int, tuple[float, MoveAction]]:
    """Tier-1 domain pruning (2026-07-20): drop moves that are obviously
    never-best on public information alone, shrinking the per-slot option
    set so deeper search fits the same budget. Two cuts, both WORLD-
    INVARIANT (opponent species types + my own ability/moves only, never
    the opponent's SAMPLED item/ability/stats - see the keying-contract
    note on propose_pruned_team_preview_actions):

    1. A damage move that is IMMUNE (0x) against every living target is
       always cut; one that is merely RESISTED (<=0.5x) against every
       target is cut only when the slot still has a neutral-or-better
       attack to fall back on (never leave a mon unable to attack).
       Support attacks (_SUPPORT_ATTACK_MOVES) are exempt - their value
       is the guaranteed stat drop, not the damage.
    2. A Prankster status move that a Dark-type is immune to (see
       _prankster_dark_blocked).

    Status/utility moves (Protect, Tailwind, Trick Room, redirection) have
    no type-effectiveness reading and are always kept - Protect must
    survive pruning, it's the mindgame.
    """
    defenders = _live_opposing(state, side)
    move_id = lambda a: mon.moves[a.move_slot - 1].move

    attack_eff: dict[int, float] = {}
    for slot, (_, action) in best_per_slot.items():
        mid = move_id(action)
        if not _is_attacking_move(mid) or mid in _SUPPORT_ATTACK_MOVES:
            continue
        eff = _max_type_effectiveness(mid, defenders)
        if eff is not None:
            attack_eff[slot] = eff
    has_neutral_attack = any(eff > 0.5 for eff in attack_eff.values())

    kept: dict[int, tuple[float, MoveAction]] = {}
    for slot, (score, action) in best_per_slot.items():
        mid = move_id(action)
        if _prankster_dark_blocked(state, side, mon, mid, action):
            continue
        eff = attack_eff.get(slot)
        if eff is not None:
            if eff == 0:
                continue  # immune attack: strictly useless as damage
            if eff <= 0.5 and has_neutral_attack:
                continue  # resisted, and a better attack survives
        kept[slot] = (score, action)
    # Never return an empty attack set when the pre-filter set was non-empty
    # and nothing else (switch/status) will cover it: fall back to the
    # single best-damage move so the mon always has SOMETHING to do.
    if not kept and best_per_slot:
        kept = {max(best_per_slot, key=lambda s: best_per_slot[s][0]):
                max(best_per_slot.values(), key=lambda t: t[0])}
    return kept


def _pruned_slot_actions(state: FullInfoState, side: str, position: Position, cap: int) -> list[Action]:
    """The V1 heuristic pruner behind the propose seam (the policy net's
    future job): per slot keep each move once with its highest-expected-
    damage target (status moves keep their natural target, scoring 0 —
    Protect must survive pruning, it's the mindgame), the single best
    mega variant, and one switch. Cuts ~14 options/slot to <=6, i.e.
    ~96 joint actions to <=36 — what makes engine-backed search
    affordable before a trained pruner exists.

    Self-switch moves (switch_bench_slot is not None) are handled apart
    from the best-per-move_slot dedup below, keeping ONE variant PER
    BENCH DESTINATION (the best-damage target/mega for that destination):
    the switch-in choice is the tactical decision search must see, so
    every bench candidate is preserved - but the redundant target x mega
    branching within one destination is NOT (found live 2026-07-20: a
    lead Incineroar's Parting Shot enumerates 2 targets x 2 bench = 4
    variants, all kept in full, hogging the per-slot cap and squeezing
    Fake Out out of the option set entirely). An earlier version kept
    them ALL in full, which caused exactly that; keeping one-per-bench
    bounds a self-switch move's contribution to (living bench count),
    not (targets x mega x bench).
    """
    full = propose_slot_actions(state, side, position)
    if len(full) <= cap:
        return full
    team, _, _ = _sides(state, side)
    mon = active_mon(team, position)

    best_self_switch: dict[int, tuple[float, MoveAction]] = {}
    for a in full:
        if isinstance(a, MoveAction) and a.switch_bench_slot is not None:
            score = _action_damage(state, side, mon, a)
            if a.switch_bench_slot not in best_self_switch or score > best_self_switch[a.switch_bench_slot][0]:
                best_self_switch[a.switch_bench_slot] = (score, a)
    self_switch_actions = [a for _, a in best_self_switch.values()]

    best_per_slot: dict[int, tuple[float, MoveAction]] = {}
    best_mega: tuple[float, MoveAction] | None = None
    first_switch: SwitchAction | None = None
    for action in full:
        if isinstance(action, SwitchAction):
            first_switch = first_switch or action
            continue
        if not isinstance(action, MoveAction) or action.switch_bench_slot is not None:
            continue
        score = _action_damage(state, side, mon, action)
        if action.mega:
            if best_mega is None or score > best_mega[0]:
                best_mega = (score, action)
        elif action.move_slot not in best_per_slot or score > best_per_slot[action.move_slot][0]:
            best_per_slot[action.move_slot] = (score, action)

    best_per_slot = _filter_dominated_moves(state, side, mon, best_per_slot)

    kept: list[tuple[float, Action]] = sorted(best_per_slot.values(), key=lambda t: -t[0])
    if best_mega:
        kept.append(best_mega)
    actions: list[Action] = [a for _, a in kept]
    if first_switch:
        actions.append(first_switch)
    remaining_cap = max(cap - len(self_switch_actions), 0)
    actions = actions[:remaining_cap] if len(actions) > remaining_cap else actions
    return self_switch_actions + actions


def propose_pruned_turn_actions(state: FullInfoState, side: str, per_slot_cap: int = 6) -> list[TurnActions]:
    return _joint(
        _pruned_slot_actions(state, side, Position.LEFT, per_slot_cap),
        _pruned_slot_actions(state, side, Position.RIGHT, per_slot_cap),
    )


def _tp_sides(state: TeamPreviewRootState, side: str) -> tuple[list[OwnPokemon], list[OwnPokemon]]:
    if side == "me":
        return state.my_team, state.opp_team
    return state.opp_team, state.my_team


def propose_team_preview_actions(state: TeamPreviewRootState, side: str) -> list[TeamPreviewAction]:
    """Full enumeration: C(6,4)=15 bring-subsets x 12 lead-orderings (any
    ordered pair from the subset) = 180. Reference/test use only - too
    many for engine-backed search, see propose_pruned_team_preview_actions.
    """
    roster, _ = _tp_sides(state, side)
    n = len(roster)
    actions = []
    for subset in combinations(range(n), 4):
        for pair in permutations(subset, 2):
            actions.append(TeamPreviewAction(bring=list(subset), lead_order=list(pair)))
    return actions


def propose_pruned_team_preview_actions(
    state: TeamPreviewRootState, side: str, bring_cap: int = 6, lead_cap: int = 2,
    synergy_weights: dict | None = None, synergy_scale: float = 1.0, mega_penalty: float = 0.0,
) -> list[TeamPreviewAction]:
    """The team-preview pruner: two-stage enumerate-then-cap, mirroring
    _pruned_slot_actions' shape. First scores all 15 bring-subsets via
    model.team_preview_scoring.bring_subset_score (type-coverage, plus an
    optional synergy bonus and mega-usage penalty - see that module),
    keeps the top `bring_cap`. Then pools ALL kept subsets' 12-orderings-
    each lead-pair candidates, scores each via lead_pair_score (defense
    weighted higher, no mega penalty - see that function's docstring for
    why), and keeps one GLOBAL top-(bring_cap*lead_cap) — deliberately
    not an independent top-lead_cap per subset: an earlier version did
    that, and it forced even a mediocre kept subset to still contribute
    its own two "least-bad" pairs, which could rank above genuinely safe
    pairs from a better subset, defeating the point of the defensive-risk
    scoring (caught by the Archaludon+Metagross regression test below).
    Total candidates <= bring_cap * lead_cap (default 12) — comparable in
    size to a turn's pruned joint action space (per_slot_cap=6 -> <=36).

    CORRECTNESS CONSTRAINT (this project has hit this exact bug class
    three times - mega_used, boosts, the Metronome-item volatile): the
    ONLY per-mon attribute read beyond public species identity is MY OWN
    side's movesets, and ONLY for side == "me" (own_support_score, gated
    below). That is contract-safe precisely because my own team's moves
    are fully known and WORLD-INVARIANT - identical across every
    determinized world, since determinization only fills the OPPONENT's
    hidden slots (confirmed: my side is copied through byte-for-byte, see
    belief.determinize). The opponent side is still scored species-only
    (support_by_species stays None for side == "opp") - reading their
    SAMPLED moves/item/ability/stats would be world-dependent and would
    reopen the hole. This matters concretely because TeamPreviewGame.
    my_actions() is called once per determinized world, and the solver's
    keying contract requires my_actions(state) to be identical whenever
    my_key(state) matches (world-independent for my side) - violating it
    raises an n_actions mismatch, the same crash class model/solver_game.
    py's keying contract already guards against for in-battle turns. A
    careless edit that drops the side == "me" gate, or starts reading
    mon.item here, silently reopens it.
    """
    roster, enemy_team = _tp_sides(state, side)
    species = [m.species for m in roster]
    enemy_species = [m.species for m in enemy_team]
    n = len(roster)

    # My-side ONLY: score my known, world-invariant movesets for support
    # tools (Tailwind/Trick Room/Fake Out/redirection) the type chart
    # can't see. For side == "opp" this stays None, so the modeled
    # opponent is scored species-only exactly as before - reading their
    # SAMPLED moves here would be world-dependent and reopen the keying-
    # contract hole documented above. `roster` is state.my_team when
    # side == "me" (its moves identical across every determinized world),
    # so this is contract-safe by construction.
    support_by_species = (
        {m.species: own_support_score(m.moves) for m in roster} if side == "me" else None
    )

    subset_scores = sorted(
        ((bring_subset_score([species[i] for i in subset], enemy_species,
                              synergy_weights, synergy_scale, mega_penalty, support_by_species), subset)
         for subset in combinations(range(n), 4)),
        key=lambda t: -t[0],
    )
    kept_subsets = [subset for _, subset in subset_scores[:bring_cap]]

    pair_candidates = sorted(
        (
            (lead_pair_score([species[i] for i in pair], enemy_species, synergy_weights, synergy_scale,
                             support_by_species),
             subset, pair)
            for subset in kept_subsets for pair in permutations(subset, 2)
        ),
        key=lambda t: -t[0],
    )
    total_cap = bring_cap * lead_cap
    return [
        TeamPreviewAction(bring=list(subset), lead_order=list(pair))
        for _, subset, pair in pair_candidates[:total_cap]
    ]
