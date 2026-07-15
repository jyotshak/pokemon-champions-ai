"""Human-readable, one-side-POV battle transcript formatting.

Pure functions over schema types only (BattleState, TurnActions,
TeamPreviewAction) - no poke-env/CV-specific code, per the architecture-
goal. Meant for sampling a game or two out of a batch to review what the
policy (heuristic today, the real model later) is doing turn by turn.
"""

from schema.battle_state import (
    BattleState, MoveAction, NoAction, OwnPokemon, Position, SwitchAction, TeamPreviewAction, TurnActions,
)


def _format_own_mon_full(index: int, mon: OwnPokemon) -> str:
    stats_str = ", ".join(f"{k}={v}" for k, v in mon.stats.items())
    moves_str = ", ".join(m.move for m in mon.moves)
    tera = f" | Tera: {mon.tera_type}" if mon.tera_type else ""
    return (
        f"{index + 1}. {mon.species} @ {mon.item or 'no item'} | {mon.ability}{tera}\n"
        f"   Stats: {stats_str}\n"
        f"   Moves: {moves_str}"
    )


def format_team_preview(state: BattleState, action: TeamPreviewAction) -> str:
    roster = state.my_bench  # nothing's active yet at team preview, so all 6 land here
    lines = ["=== TEAM PREVIEW ===", "", "My team (6):"]
    for i, mon in enumerate(roster):
        lines.append(_format_own_mon_full(i, mon))
    lines.append("")
    opp_names = state.team_preview.opp_team if state.team_preview else []
    lines.append(f"Opponent team (species only): {', '.join(opp_names)}")
    lines.append("")
    bring_names = [roster[i].species for i in action.bring]
    lead_names = [roster[i].species for i in action.lead_order]
    lines.append(f"Bring: {', '.join(bring_names)}")
    lines.append(f"Lead order: {', '.join(lead_names)}")
    lines.append("")
    return "\n".join(lines)


def _hp_summary(state: BattleState) -> str:
    mine = ", ".join(f"{m.species} {m.hp}/{m.max_hp}" for m in state.my_active if not m.fainted)
    theirs = ", ".join(f"{o.species} {o.hp_pct:.0f}%" for o in state.opp_active if not o.fainted)
    return f"  My side: {mine or '(none active)'}\n  Opponent: {theirs or '(none active)'}"


def _target_label(state: BattleState, mon: OwnPokemon, target) -> str:
    """{species} ({position}) for whatever the target resolves to, matching
    how the acting mon itself is displayed, instead of a bare position tag.
    """
    from schema.battle_state import Target as T

    if target == T.OPP_LEFT or target == T.OPP_RIGHT:
        want_left = target == T.OPP_LEFT
        for o in state.opp_active:
            if (o.position and o.position.value == "left") == want_left:
                return f"{o.species} ({target.value})"
        return target.value
    if target == T.ALLY:
        for other in state.my_active:
            if other is not mon:
                return f"{other.species} (ally)"
        return target.value
    if target == T.SELF:
        return f"{mon.species} (self)"
    return target.value  # NONE - spread/implicit, nothing to name


def _format_slot_action(state: BattleState, position: Position, mon: OwnPokemon | None, action) -> str:
    # mon is None when this slot's Pokemon already fainted this turn and
    # hasn't been replaced yet - still show the switch decision, just
    # without a "from" species name.
    label = mon.species if mon is not None else "(fainted)"
    if isinstance(action, NoAction):
        return f"  {label} ({position.value}): no action"
    if isinstance(action, SwitchAction):
        incoming = state.my_bench[action.bench_slot].species
        return f"  {label} ({position.value}): switches to {incoming}"
    if isinstance(action, MoveAction) and mon is not None:
        move_name = mon.moves[action.move_slot - 1].move
        extra = ""
        if action.mega:
            extra += " (Mega Evolving)"
        if action.tera:
            extra += " (Terastallizing)"
        target_label = _target_label(state, mon, action.target)
        return f"  {label} ({position.value}): uses {move_name} -> {target_label}{extra}"
    return f"  {label} ({position.value}): unrecognized action {action!r}"


def format_turn(state: BattleState, actions: TurnActions) -> str:
    lines = [f"--- Turn {state.turn} ---", _hp_summary(state)]
    left_mon = next((m for m in state.my_active if m.position == Position.LEFT), None)
    right_mon = next((m for m in state.my_active if m.position == Position.RIGHT), None)
    for position, mon, action in (
        (Position.LEFT, left_mon, actions.slot_left),
        (Position.RIGHT, right_mon, actions.slot_right),
    ):
        lines.append(_format_slot_action(state, position, mon, action))
    return "\n".join(lines)


def format_result(won: bool | None) -> str:
    if won is True:
        return "=== RESULT: WON ==="
    if won is False:
        return "=== RESULT: LOST ==="
    return "=== RESULT: UNKNOWN ==="
