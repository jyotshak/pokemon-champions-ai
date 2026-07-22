"""Converts a poke-env DoubleBattle (as observed live against the local
Showdown server) into our BattleState schema. One direction only for now —
BattleState -> Showdown choice-string goes in actions.py once this side is
validated against a real battle.

Belief fields (move_beliefs/item_beliefs/ability_beliefs/tera_beliefs/
spread_beliefs) are left empty here on purpose: populating them is the
belief-tracker's job (a separate, not-yet-built component), not the
translator's. This module only carries over what poke-env has actually
observed/revealed.
"""

from typing import Optional

from poke_env.battle.double_battle import DoubleBattle
from poke_env.battle.pokemon import Pokemon

from schema.battle_state import (
    BattleState,
    Boosts,
    FieldState,
    MoveSlot,
    OpponentPokemon,
    OwnPokemon,
    Position,
    SideConditions,
    Status,
    Terrain,
    TeamPreviewInfo,
    VolatileState,
    Weather,
)

_BOOST_FIELD_MAP = {"atk": "atk", "def": "defense", "spa": "spa", "spd": "spd", "spe": "spe", "accuracy": "acc", "evasion": "eva"}

_STATUS_MAP = {
    "brn": Status.BRN, "par": Status.PAR, "psn": Status.PSN,
    "tox": Status.TOX, "slp": Status.SLP, "frz": Status.FRZ, "fnt": Status.NONE,
}

_WEATHER_MAP = {
    "sunnyday": Weather.SUN, "desolateland": Weather.SUN,
    "raindance": Weather.RAIN, "primordialsea": Weather.RAIN,
    "sandstorm": Weather.SAND,
    "hail": Weather.SNOW, "snowscape": Weather.SNOW,
}

_TERRAIN_MAP = {
    "electric_terrain": Terrain.ELECTRIC, "grassy_terrain": Terrain.GRASSY,
    "misty_terrain": Terrain.MISTY, "psychic_terrain": Terrain.PSYCHIC,
}


def _boosts(poke_mon: Pokemon) -> Boosts:
    kwargs = {}
    for src_key, dst_key in _BOOST_FIELD_MAP.items():
        val = poke_mon.boosts.get(src_key)
        if val:
            kwargs[dst_key] = val
    return Boosts(**kwargs)


def _volatiles(poke_mon: Pokemon) -> list[VolatileState]:
    return [
        VolatileState(name=effect.name.lower(), data={"value": value})
        for effect, value in poke_mon.effects.items()
    ] + _forced_continuation_volatiles(poke_mon)


def _forced_continuation_volatiles(poke_mon: Pokemon) -> list[VolatileState]:
    """must_recharge (after Hyper Beam etc.) and mid-charge on a two-turn
    move (Solar Beam, Fly, Electro Shot without Rain, ...) are tracked by
    poke-env as DEDICATED attributes (must_recharge, preparing_move), set
    directly from the real -mustrecharge/-prepare protocol lines and
    cleared the instant the mon actually moves (Pokemon.moved()) - NOT via
    poke_mon.effects, which the list above reads and which was confirmed
    (empirically, on a real Pokemon object) to NEVER carry either of these.
    Without this, neither model/action_space.py::propose_slot_actions'
    forced-continuation check nor engine/bridge.js's matching volatile
    reconstruction ever actually engage in live play - they'd only ever be
    exercised by hand-built test fixtures, not the real translation path.
    harness/actions.py::_forced_move reads these same two properties
    directly (not through this schema) for the live order-submission side
    of the same fix.
    """
    out = []
    if poke_mon.must_recharge:
        out.append(VolatileState(name="must_recharge"))
    if poke_mon.preparing_move is not None:
        out.append(VolatileState(name="two_turn_move", data={"move": poke_mon.preparing_move.id}))
    return out


def _is_mega(poke_mon: Pokemon) -> bool:
    return "mega" in poke_mon.species


def _status(poke_mon: Pokemon) -> Status:
    if poke_mon.status is None:
        return Status.NONE
    return _STATUS_MAP.get(poke_mon.status.name.lower(), Status.NONE)


def _position(index: int) -> Position:
    return Position.LEFT if index == 0 else Position.RIGHT


def own_pokemon(
    poke_mon: Pokemon, position: Optional[Position], available_move_ids: Optional[set] = None,
    trapped: bool = False,
) -> OwnPokemon:
    # available_move_ids, when given (active mons only - see battle_to_state),
    # is battle.available_moves[i] reduced to ids: poke-env's own filtering of
    # the request's per-move "disabled" flag (Showdown sends this for things
    # like Fake Out after turn 1, Torment, Taunt, Disable, choice-lock - not
    # just PP). Without this, every move always looked pickable regardless of
    # legality, so a policy could "choose" a genuinely unusable move, get
    # rejected by the server, and stall the turn retrying it forever.
    # NOTE on FORCED CONTINUATIONS (recharge after Hyper Beam, Struggle, a
    # locked two-turn move): Showdown replaces the request's move list with one
    # SYNTHETIC entry whose id is not in the mon's real moveset, which marks
    # every real move disabled here. That is deliberate - `moves` must stay the
    # mon's REAL, buildable moveset, because these OwnPokemon feed
    # engine/bridge.py's init_battle -> buildSet for search rollouts, and a
    # synthetic id has no PP data behind it (rebuilding one yields
    # pp/max_pp = null and a FullInfoState ValidationError). The resulting
    # "no legal move" is resolved at the ORDER boundary instead, where the live
    # request is still available - see harness/actions.py::_forced_move.
    moves = [
        MoveSlot(
            move=move.id, pp=move.current_pp, max_pp=move.max_pp,
            disabled=available_move_ids is not None and move.id not in available_move_ids,
        )
        for move in poke_mon.moves.values()
    ]
    stats = {k: v for k, v in poke_mon.stats.items() if k != "hp" and v is not None}
    return OwnPokemon(
        species=poke_mon.species,
        level=poke_mon.level,
        position=position,
        fainted=poke_mon.fainted,
        hp=poke_mon.current_hp or 0,
        max_hp=poke_mon.max_hp or 0,
        status=_status(poke_mon),
        stats=stats,
        boosts=_boosts(poke_mon),
        ability=poke_mon.ability or "",
        item=poke_mon.item or None,
        moves=moves,
        tera_type=str(poke_mon.tera_type) if poke_mon.tera_type else None,
        tera_activated=poke_mon.is_terastallized,
        mega_activated=_is_mega(poke_mon),
        # A mon locked into a forced continuation (recharge after Hyper
        # Beam, an in-progress two-turn move) needs THIS to survive so a
        # rebuilt search/engine world doesn't see a totally free mon: no
        # move data says why every real move is disabled, and nothing
        # marks it unable to switch. poke-env already tracks this live as
        # Effect.MUST_RECHARGE (Effect.name.lower() -> "must_recharge");
        # model/action_space.py::propose_slot_actions and
        # engine/bridge.js::applyMonState both key on that exact string -
        # see their own comments for the two ends of this fix. (This field
        # was already wired here before that fix - the actual gap was that
        # nothing downstream READ it for the recharge case.)
        volatiles=_volatiles(poke_mon),
        trapped=trapped,
    )


def opponent_pokemon(poke_mon: Pokemon, position: Optional[Position]) -> OpponentPokemon:
    revealed_item = poke_mon.item if poke_mon.item and poke_mon.item != "unknown_item" else None
    return OpponentPokemon(
        species=poke_mon.species,
        level=poke_mon.level,
        position=position,
        fainted=poke_mon.fainted,
        hp_pct=poke_mon.current_hp_fraction * 100,
        status=_status(poke_mon),
        boosts=_boosts(poke_mon),
        revealed_moves=list(poke_mon.moves.keys()),
        revealed_item=revealed_item,
        revealed_ability=poke_mon.ability or None,
        tera_activated=poke_mon.is_terastallized,
        revealed_tera_type=str(poke_mon.tera_type) if poke_mon.is_terastallized and poke_mon.tera_type else None,
        mega_activated=_is_mega(poke_mon),
        volatiles=_volatiles(poke_mon),
    )


def _field_state(battle: DoubleBattle) -> FieldState:
    weather = Weather.NONE
    weather_turns = 0
    for w, start_turn in battle.weather.items():
        weather = _WEATHER_MAP.get(w.name.lower(), Weather.NONE)
        weather_turns = battle.turn - start_turn
        break

    terrain = Terrain.NONE
    terrain_turns = 0
    trick_room_turns = 0
    gravity_turns = 0
    for f, start_turn in battle.fields.items():
        key = f.name.lower()
        if key in _TERRAIN_MAP:
            terrain = _TERRAIN_MAP[key]
            terrain_turns = battle.turn - start_turn
        elif key == "trick_room":
            trick_room_turns = battle.turn - start_turn
        elif key == "gravity":
            gravity_turns = battle.turn - start_turn

    return FieldState(
        weather=weather, weather_turns=weather_turns,
        terrain=terrain, terrain_turns=terrain_turns,
        trick_room_turns=trick_room_turns, gravity_turns=gravity_turns,
        my_side=_side_conditions(battle.side_conditions, battle.turn, battle.used_mega_evolve, battle.used_tera),
        opp_side=_side_conditions(battle.opponent_side_conditions, battle.turn, battle.opponent_used_mega_evolve, battle.opponent_used_tera),
    )


def _side_conditions(conditions: dict, turn: int, mega_used: bool, tera_used: bool) -> SideConditions:
    sc = SideConditions(mega_used=mega_used, tera_used=tera_used)
    for cond, value in conditions.items():
        name = cond.name.lower()
        if name == "reflect":
            sc.reflect_turns = turn - value
        elif name == "light_screen":
            sc.light_screen_turns = turn - value
        elif name == "aurora_veil":
            sc.aurora_veil_turns = turn - value
        elif name == "tailwind":
            sc.tailwind_turns = turn - value
        elif name == "safeguard":
            sc.safeguard_turns = turn - value
        elif name == "mist":
            sc.mist_turns = turn - value
        elif name == "stealth_rock":
            sc.stealth_rock = True
        elif name == "spikes":
            sc.spikes_layers = value
        elif name == "toxic_spikes":
            sc.toxic_spikes_layers = value
        elif name == "sticky_web":
            sc.sticky_web = True
    return sc


def battle_to_state(battle: DoubleBattle) -> BattleState:
    # battle.available_moves[i] can read empty for a still-alive slot during
    # a mid-turn switch-only request (Showdown doesn't re-list its moves
    # when only the fainted slot is being asked to act), which would mark
    # that mon's moves all "disabled" here - harmless in practice, since
    # both SolverPlayer and HeuristicPlayer already override the
    # non-force-switch slot to NoAction() during those requests regardless
    # of what battle_to_state produced for it.
    my_active = [
        own_pokemon(mon, _position(i), {m.id for m in battle.available_moves[i]}, battle.trapped[i])
        for i, mon in enumerate(battle.active_pokemon) if mon is not None
    ]
    # battle.team always holds all 6 submitted Pokemon, but only 4 are
    # actually brought into a given battle (VGC bring-4-of-6). During team
    # preview itself, none are marked selected_in_teampreview yet (that
    # decision hasn't been made), so all 6 correctly show up here - that's
    # exactly what's needed to choose which 4 to bring. Once team preview
    # ends, only the actually-brought ones should remain (see actions.py's
    # team_preview_action_to_order, which sets the flag).
    my_bench = [
        own_pokemon(mon, None) for mon in battle.team.values()
        if mon not in battle.active_pokemon and (battle.in_team_preview or mon.selected_in_teampreview)
    ]
    opp_active = [
        opponent_pokemon(mon, _position(i)) for i, mon in enumerate(battle.opponent_active_pokemon) if mon is not None
    ]
    opp_bench = [
        opponent_pokemon(mon, None) for mon in battle.opponent_team.values() if mon not in battle.opponent_active_pokemon
    ]

    team_preview = None
    if battle.in_team_preview:
        # battle.teampreview_team is never actually populated by poke-env
        # (confirmed by reading its source - nothing calls its setter);
        # poke-env's own default random_teampreview uses battle.team
        # directly, so we do too.
        team_preview = TeamPreviewInfo(
            my_team=[mon.species for mon in battle.team.values()],
            opp_team=[mon.species for mon in battle.teampreview_opponent_team],
        )

    return BattleState(
        format_id=battle.format or "",
        turn=battle.turn,
        team_preview=team_preview,
        # teampreview_opponent_team (unlike teampreview_team, which poke-env
        # never populates) IS filled from the |poke| protocol messages and
        # persists after preview ends - the full 6-species roster stays
        # available all battle, which the belief layer needs for
        # hypothesizing the opponent's unseen back slots.
        opp_roster=[mon.species for mon in battle.teampreview_opponent_team],
        field=_field_state(battle),
        my_active=my_active,
        my_bench=my_bench,
        opp_active=opp_active,
        opp_bench=opp_bench,
    )
