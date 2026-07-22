"""Converts our TurnActions/TeamPreviewAction into poke-env BattleOrders —
the reverse direction of translator.py. Showdown-protocol-specific glue,
same as translator.py: no decision logic lives here.

Target-position integers (opponent slots = 1/2, ally slots = -1/-2, no
explicit target = 0) come directly from poke-env's own
DoubleBattle.{POKEMON,OPPONENT}_{1,2}_POSITION constants, not guessed.
"""

from poke_env.battle.double_battle import DoubleBattle
from poke_env.battle.move import Move
from poke_env.player.battle_order import DoubleBattleOrder, PassBattleOrder, SingleBattleOrder

from schema.battle_state import (
    Action, MoveAction, NoAction, Position, SwitchAction, Target, TeamPreviewAction, TurnActions,
)


def _target_to_int(target: Target, actor_position: Position) -> int:
    if target == Target.OPP_LEFT:
        return 1
    if target == Target.OPP_RIGHT:
        return 2
    if target == Target.ALLY:
        # the ally is whichever slot the actor isn't in
        return -2 if actor_position == Position.LEFT else -1
    return 0  # SELF, NONE - spread/self-targeting moves need no explicit target


def _bench_pokemon(battle: DoubleBattle, bench_slot: int):
    # battle.team always holds all 6 submitted Pokemon, but only 4 are
    # actually brought into a given battle (VGC bring-4-of-6) - filtering
    # on "not currently active" alone wrongly offers the other 2, never-
    # brought mons as switch targets. selected_in_teampreview (set in
    # team_preview_action_to_order below) is what actually narrows this
    # to the real bench.
    bench = [
        mon for mon in battle.team.values()
        if mon not in battle.active_pokemon and mon.selected_in_teampreview
    ]
    return bench[bench_slot]


def _forced_move(battle: DoubleBattle, actor):
    """The forced move for a FORCED CONTINUATION (recharge after Hyper Beam,
    or mid-charge on a two-turn move like Solar Beam/Fly/Electro Shot
    without Rain), or None.

    Checks poke-env's own DIRECT, protocol-driven tracking - actor.
    must_recharge / actor.preparing_move, set straight from the real
    -mustrecharge/-prepare log lines and cleared the instant the mon
    actually moves (poke_env.battle.pokemon.Pokemon.moved()) - rather than
    diffing battle.available_moves against the mon's real moveset. That
    diff-based approach (the original fix here) breaks specifically when
    this request is COMBINED with an ally's post-faint replacement:
    Showdown does not re-list a still-alive, non-participating slot's
    moves during a switch-only request (harness/translator.py's own
    documented gotcha - battle.available_moves[i] reads EMPTY there), so
    the diff finds nothing, falls through to a plain pass, and the real
    outstanding requirement goes unanswered - silently deferred to the
    NEXT request, where it resurfaces as the exact same problem one turn
    later (found live on MB552's Sylveon: Garchomp fainted the same turn
    Sylveon's Hyper Beam locked her into recharging).

    Confirmed empirically that poke_mon.effects (what harness/
    translator.py::_volatiles reads) never carries either of these - they
    are separate dedicated attributes - so this must read the properties
    directly rather than go through that path.
    """
    if actor is None:
        return None
    if actor.must_recharge:
        return Move("recharge", gen=battle.gen)
    if actor.preparing_move is not None:
        return actor.preparing_move
    # Fallback for anything else needing a forced single move (Struggle -
    # genuinely PP-based, not tracked by a dedicated property, and unaffected
    # by the switch-only-request gap since it doesn't depend on recharge/
    # charge state at all): the original available_moves-diff detection.
    try:
        i = list(battle.active_pokemon).index(actor)
    except ValueError:
        return None
    available = battle.available_moves[i] if i < len(battle.available_moves) else []
    extras = [m for m in available if m.id not in actor.moves]
    return extras[0] if len(extras) == 1 else None


def _single_order(battle: DoubleBattle, action: Action, actor, position: Position) -> SingleBattleOrder:
    # A forced continuation overrides whatever the policy chose for this slot:
    # it is the only legal move. Switches are left alone - Struggle is a forced
    # continuation you CAN legally switch out of (recharge sets trapped, so the
    # policy won't offer a switch there anyway).
    if actor is not None and not isinstance(action, SwitchAction):
        forced = _forced_move(battle, actor)
        if forced is not None:
            return SingleBattleOrder(forced)
    if isinstance(action, NoAction):
        return PassBattleOrder()
    if isinstance(action, SwitchAction):
        return SingleBattleOrder(_bench_pokemon(battle, action.bench_slot))
    if isinstance(action, MoveAction):
        # Own moveset order is assumed stable (team-declared order), since
        # OwnPokemon's full 4 moves are known up front, unlike an opponent's
        # moves dict which only grows as they're revealed.
        move = list(actor.moves.values())[action.move_slot - 1]
        return SingleBattleOrder(
            move,
            mega=action.mega,
            terastallize=action.tera,
            move_target=_target_to_int(action.target, position),
        )
    raise ValueError(f"Unknown action type: {action!r}")


def turn_actions_to_order(battle: DoubleBattle, actions: TurnActions) -> DoubleBattleOrder:
    # Do NOT default to Pass just because active_pokemon[i] is None - that's
    # exactly the fainted-needs-a-switch case, where the actor object isn't
    # needed anyway (SwitchAction/NoAction in _single_order don't use it,
    # only MoveAction does, and a fainted slot should never receive one).
    left_mon, right_mon = battle.active_pokemon
    first = _single_order(battle, actions.slot_left, left_mon, Position.LEFT)
    second = _single_order(battle, actions.slot_right, right_mon, Position.RIGHT)
    return DoubleBattleOrder(first_order=first, second_order=second)


def team_preview_action_to_order(battle: DoubleBattle, action: TeamPreviewAction) -> str:
    """`action.bring`/`lead_order` are 0-based indices into the 6-mon roster
    (the schema's convention); Showdown's /team string is 1-based, so the
    +1 offset is applied only here, at the protocol boundary.

    battle.teampreview_team is never actually populated by poke-env (see
    translator.py) so battle.team is used instead, same fix.
    """
    roster = list(battle.team.values())
    all_indices = list(range(len(roster)))
    bring_rest = [i for i in action.bring if i not in action.lead_order]
    remaining = [i for i in all_indices if i not in action.bring]
    order = action.lead_order + bring_rest + remaining

    # Mirrors poke-env's own random_teampreview: mark the actually-brought
    # mons so bench lookups (translator.py, _bench_pokemon above) can tell
    # them apart from the 2 that were never brought into this battle.
    for i in action.bring:
        roster[i]._selected_in_teampreview = True

    return "/team " + "".join(str(i + 1) for i in order)
