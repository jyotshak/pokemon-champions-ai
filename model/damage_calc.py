"""Core damage-calculation engine.

V1 scope: level scaling, base power, Atk/Def stat ratio, STAB, type
effectiveness, doubles spread-move penalty, accuracy-weighted expected
damage. Deliberately NOT modeled yet (a known simplification, not an
oversight - see model/heuristic.py for where this is used): ability
modifiers (Technician, Sheer Force, Guts, etc.), item modifiers (Life
Orb, Choice items), weather/terrain damage modifiers, critical hits,
burn's physical-damage halving.

Depends only on schema/ + reference/ data (see memory: data-sourcing,
architecture-goal) - no poke-env or CV-specific code belongs here.
"""

import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_MOVE_DATA = json.loads((_ROOT / "reference" / "move_data.json").read_text(encoding="utf-8"))
_SPECIES_STATS = json.loads((_ROOT / "reference" / "species_stats.json").read_text(encoding="utf-8"))
_TYPE_CHART = json.loads((_ROOT / "reference" / "type_chart.json").read_text(encoding="utf-8"))

LEVEL = 50  # VGC/Champions is always level 50
_SPREAD_TARGETS = {"allAdjacent", "allAdjacentFoes"}

AVG_RANDOM_FACTOR = 0.925  # average of the 16 possible 0.85-1.00 rolls


def species_types(species: str) -> list[str]:
    return _SPECIES_STATS[species]["types"]


def is_spread_move(move_id: str) -> bool:
    return _MOVE_DATA.get(move_id, {}).get("target") in _SPREAD_TARGETS


def estimate_opponent_stats(species: str) -> dict:
    """Placeholder opponent-stat estimate: base stat + 0 invested stat
    points + neutral nature, using the champions stat formula (base +
    points + 20, +75 for HP - see memory: showdown-doubles-harness). This
    is the damage-calc-side equivalent of the belief-tracker's placeholder
    uniform prior - swap for a real spread_beliefs-derived estimate once
    that exists.
    """
    base = _SPECIES_STATS[species]["base_stats"]
    return {
        "hp": base["hp"] + 75,
        "atk": base["atk"] + 20,
        "def": base["def"] + 20,
        "spa": base["spa"] + 20,
        "spd": base["spd"] + 20,
        "spe": base["spe"] + 20,
    }


def type_effectiveness(move_type: str, defender_types: list[str]) -> float:
    mult = 1.0
    for t in defender_types:
        mult *= _TYPE_CHART.get(t.lower(), {}).get(move_type, 1.0)
    return mult


def expected_damage(
    move_id: str,
    attacker_species: str, attacker_stats: dict,
    defender_species: str, defender_stats: dict,
) -> float:
    """Accuracy-weighted average expected damage in raw HP points, using
    AVG_RANDOM_FACTOR in place of the real 0.85-1.00 random roll. Meant
    for greedy move comparison, not exact damage-range display.
    """
    move = _MOVE_DATA.get(move_id)
    if move is None or move["category"] == "Status" or move["basePower"] == 0:
        return 0.0

    atk_stat = attacker_stats["atk"] if move["category"] == "Physical" else attacker_stats["spa"]
    def_stat = defender_stats["def"] if move["category"] == "Physical" else defender_stats["spd"]

    base = (((2 * LEVEL / 5 + 2) * move["basePower"] * atk_stat / def_stat) / 50) + 2

    stab = 1.5 if move["type"] in species_types(attacker_species) else 1.0
    type_mult = type_effectiveness(move["type"], species_types(defender_species))
    spread_mult = 0.75 if is_spread_move(move_id) else 1.0

    damage = base * stab * type_mult * spread_mult * AVG_RANDOM_FACTOR

    accuracy = move["accuracy"]
    acc_mult = 1.0 if accuracy is True else accuracy / 100
    return damage * acc_mult
