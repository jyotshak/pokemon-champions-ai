"""Populates OpponentPokemon.*_beliefs from what's currently revealed.

This is deliberately just the update-logic skeleton, using a placeholder
uniform prior (marginal probability = remaining_slots / pool_size, under a
uniform-without-replacement assumption) rather than real usage-mined data.
The prior source is meant to be swapped out later (real per-species/per-
item/per-ability usage weights instead of uniform) without touching this
module's interface — schema/battle_state.py's WeightedOption is exactly
(value, probability) regardless of where the probability came from.

Depends only on schema/ and reference/ data (see memory: architecture-goal,
data-sourcing) — no poke-env or CV-specific code belongs here.

tera_beliefs is left empty: Terastallization isn't live in Champions yet.
spread_beliefs is left empty: no EV-archetype taxonomy/data exists yet.
"""

import json
from pathlib import Path

from schema.battle_state import BattleState, OpponentPokemon, WeightedOption

_ROOT = Path(__file__).resolve().parent.parent
_SPECIES_DATA = json.loads((_ROOT / "reference" / "species_data.json").read_text(encoding="utf-8"))
_LEGAL_ITEMS = (_ROOT / "reference" / "champions_legal_items.txt").read_text(encoding="utf-8").split()


def _remaining_pool_beliefs(pool: list[str], revealed: list[str], total_slots: int) -> list[WeightedOption]:
    """Marginal P(candidate occupies one of the remaining slots): k/n where
    k = remaining slots, n = pool size excluding what's already revealed.
    """
    remaining_slots = total_slots - len(revealed)
    if remaining_slots <= 0:
        return []
    candidates = [c for c in pool if c not in revealed]
    if not candidates:
        return []
    prob = min(1.0, remaining_slots / len(candidates))
    return [WeightedOption(value=c, probability=prob) for c in candidates]


def update_beliefs(opponent: OpponentPokemon) -> OpponentPokemon:
    data = _SPECIES_DATA.get(opponent.species, {"moves": [], "abilities": []})

    opponent.move_beliefs = _remaining_pool_beliefs(data["moves"], opponent.revealed_moves, total_slots=4)

    if opponent.revealed_item:
        opponent.item_beliefs = []
    else:
        opponent.item_beliefs = _remaining_pool_beliefs(_LEGAL_ITEMS, [], total_slots=1)

    if opponent.revealed_ability:
        opponent.ability_beliefs = []
    else:
        opponent.ability_beliefs = _remaining_pool_beliefs(data["abilities"], [], total_slots=1)

    opponent.tera_beliefs = []
    opponent.spread_beliefs = []

    return opponent


def update_battle_beliefs(battle_state: BattleState) -> BattleState:
    for mon in battle_state.opp_active + battle_state.opp_bench:
        update_beliefs(mon)
    return battle_state
