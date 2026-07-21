"""Converts our TurnActions/TeamPreviewAction into poke-env BattleOrders —
the reverse direction of translator.py. Showdown-protocol-specific glue,
same as translator.py: no decision logic lives here.

Target-position integers (opponent slots = 1/2, ally slots = -1/-2, no
explicit target = 0) come directly from poke-env's own
DoubleBattle.{POKEMON,OPPONENT}_{1,2}_POSITION constants, not guessed.
"""

from poke_env.battle.double_battle import DoubleBattle
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
    """The synthetic move Showdown offers during a FORCED CONTINUATION
    (recharge after Hyper Beam, Struggle, a locked two-turn move), or None.

    Showdown replaces that slot's move list with a single entry whose id is
    NOT in the mon's own moveset, so nothing in our schema can name it:
    harness/translator.py deliberately keeps OwnPokemon.moves as the real,
    engine-buildable moveset (a synthetic id has no PP data and breaks
    init_battle's buildSet), which leaves every real move "disabled" and makes
    the policy emit NoAction. Passing is illegal here - the server answers
    "[Invalid choice] Can't pass: Your <mon> must make a move (or switch)" and
    the battle stalls retrying. So we resolve it at THIS boundary, where the
    live request is still in hand, and submit the synthetic move itself.
    Found live on MB552's Sylveon + Hyper Beam.
    """
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
