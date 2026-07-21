"""Bridge the harness's typed battle schemas to the imitation net's neutral
"reconstruct-state" dict ([[imitation-net-v1]]), so the trained policy/value
net ([[replay-net-direction]]) can be driven live and used to score search
leaves. Input-source-specific, so it lives in harness/ (model/ stays
independent of poke-env/schema per the architecture-goal).

Two entry points, both producing the exact dict model/encoding.py::
encode_for_inference consumes:
  battle_state_to_netstate(BattleState)      - the LIVE observable state
      (my side full info, opp side revealed-only) for the turn decision.
  full_info_state_to_netstate(FullInfoState) - a determinized SEARCH LEAF
      (both teams full info) for the value head.

The net's tokens are POV-relative ("me" vs "opp"), matching how these
schemas already store my_/opp_ sides - so no side-flip is needed here;
scoring the opponent's policy (side-flip) is the caller's concern.
"""

from schema.battle_state import (
    BattleState, FieldState, OwnPokemon, OpponentPokemon, Position, Status, Weather, Terrain,
)
from schema.full_info_state import FullInfoState

# schema enum value -> the protocol-style string model/encoding.py expects
_WEATHER = {Weather.NONE: None, Weather.SUN: "SunnyDay", Weather.RAIN: "RainDance",
            Weather.SAND: "Sandstorm", Weather.SNOW: "Snow"}
_TERRAIN = {Terrain.NONE: None, Terrain.ELECTRIC: "Electric Terrain",
            Terrain.GRASSY: "Grassy Terrain", Terrain.MISTY: "Misty Terrain",
            Terrain.PSYCHIC: "Psychic Terrain"}
_STATUS = {Status.NONE: None, Status.BRN: "brn", Status.PAR: "par", Status.PSN: "psn",
           Status.TOX: "tox", Status.SLP: "slp", Status.FRZ: "frz"}
_SLOT = {Position.LEFT: "a", Position.RIGHT: "b"}


def _boosts(b) -> dict:
    """schema Boosts -> the boost dict keyed as model/encoding._BOOST_STATS
    (atk/def/spa/spd/spe/accuracy/evasion)."""
    return {"atk": b.atk, "def": b.defense, "spa": b.spa, "spd": b.spd,
            "spe": b.spe, "accuracy": b.acc, "evasion": b.eva}


def _own_mon(p: OwnPokemon) -> dict:
    return {
        "species": str(p.species),
        "hp": (p.hp / p.max_hp) if p.max_hp else 0.0,
        "status": _STATUS.get(p.status),
        "boosts": _boosts(p.boosts),
        "item": str(p.item) if p.item else None,
        "ability": str(p.ability) if p.ability else None,
        "fainted": p.fainted,
        "moves": [str(m.move) for m in p.moves],
    }


def _opp_mon(p: OpponentPokemon) -> dict:
    hp = p.hp_pct
    hp = hp / 100.0 if hp > 1.0 else hp          # tolerate 0-100 or 0-1 scale
    return {
        "species": str(p.species),
        "hp": max(0.0, min(1.0, hp)),
        "status": _STATUS.get(p.status),
        "boosts": _boosts(p.boosts),
        "item": str(p.revealed_item) if p.revealed_item else None,
        "ability": str(p.revealed_ability) if p.revealed_ability else None,
        "fainted": p.fainted,
        "moves": [str(m) for m in p.revealed_moves],
    }


def _side(team: list, to_mon, cond) -> dict:
    """One side: active a/b by Position, mons keyed by species (reconstruct
    format), plus the side-condition flags the field vector reads."""
    active = {"a": None, "b": None}
    mons = {}
    for p in team:
        sp = str(p.species)
        mons[sp] = to_mon(p)
        slot = _SLOT.get(p.position) if p.position is not None else None
        if slot:
            active[slot] = sp
    return {"active": active, "mons": mons, "cond": cond}


def _cond(side_conditions) -> dict:
    """SideConditions turn-counters -> the boolean flags the field vector uses."""
    return {
        "tailwind": side_conditions.tailwind_turns > 0,
        "reflect": side_conditions.reflect_turns > 0,
        "light_screen": side_conditions.light_screen_turns > 0,
        "aurora_veil": side_conditions.aurora_veil_turns > 0,
    }


def _globals(field: FieldState) -> dict:
    return {
        "weather": _WEATHER.get(field.weather),
        "trick_room": field.trick_room_turns > 0,
        "terrain": _TERRAIN.get(field.terrain),
    }


def battle_state_to_netstate(bs: BattleState) -> dict:
    """LIVE turn decision state: my side is full-info OwnPokemon, opp side is
    revealed-only OpponentPokemon (hidden attrs simply absent -> encoder PADs
    them, exactly as in the replay corpus where they weren't yet revealed).
    BattleState splits each side into active+bench lists (poke-env's shape)."""
    return {
        "me": _side(list(bs.my_active) + list(bs.my_bench), _own_mon, _cond(bs.field.my_side)),
        "opp": _side(list(bs.opp_active) + list(bs.opp_bench), _opp_mon, _cond(bs.field.opp_side)),
        **_globals(bs.field),
    }


def full_info_state_to_netstate(fis: FullInfoState) -> dict:
    """A determinized SEARCH LEAF: both teams are full-info OwnPokemon. Used to
    score the value head after a one-turn engine rollout."""
    g = _globals(fis.field)
    return {
        "me": _side(fis.my_team, _own_mon, _cond(fis.field.my_side)),
        "opp": _side(fis.opp_team, _own_mon, _cond(fis.field.opp_side)),
        **g,
    }


def flip_netstate(ns: dict) -> dict:
    """Swap me/opp so the OPPONENT becomes 'me' - to read the net's policy for
    the opponent's slots (weather/terrain/TR are global-symmetric; each side's
    conditions already travel inside its own me/opp entry)."""
    return {"me": ns["opp"], "opp": ns["me"],
            "weather": ns["weather"], "trick_room": ns["trick_room"], "terrain": ns["terrain"]}
