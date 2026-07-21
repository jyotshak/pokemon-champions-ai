"""sample_determinization(): the meta-layer -> logic-layer interface
(docs/solver_design.md section 1). One call returns ONE complete,
internally-coherent hypothesis of the opponent's side as a FullInfoState
the search can hand to the engine: which unseen species were actually
brought (VGC bring-4-of-6), plus every hidden attribute (moves, item,
ability, stats) for all 4 — revealed facts preserved exactly.

The solver samples this K times per decision and never touches marginal
distributions directly: all cross-attribute/cross-mon correlation logic
belongs INSIDE this function, so a smarter sampler upgrades every
consumer with no interface change.

V2: weighted by real usage data (belief/usage_data/ — Pikalytics Reg M-B
S3, per-move/ability/item/teammate popularity, with a global-popularity
fallback for anything a species has no specific reported data for; see
belief/usage_data/build_weights.py for exactly how those two blend).
Hard constraints are unchanged from V1 and still always enforced
regardless of weighting:
- revealed moves/item/ability are kept, never resampled
- moves come from the species' actual legal learnset
- item clause (no duplicate items on a team)
- mega stones only go to a species they can actually mega-evolve, and
  no stones at all once the side has already used its Mega
- an already-mega'd mon gets exactly its own stone
Stats are still the champions zero-investment floor (base + 0 points +
20, +75 HP) — real spread sampling (belief/usage_data/ already has each
species' top reported EV spread) is a separate, not-yet-wired piece.

Depends only on schema/ + reference/ (never model/ or harness/).
"""

import json
import random
from pathlib import Path

from belief.species_folding import base_species_id
from schema.battle_state import BattleState, MoveSlot, OpponentPokemon, OwnPokemon, SpeciesId
from schema.full_info_state import FullInfoState, TeamPreviewRootState

_ROOT = Path(__file__).resolve().parent.parent
_SPECIES_DATA = json.loads((_ROOT / "reference" / "species_data.json").read_text(encoding="utf-8"))
_SPECIES_STATS = json.loads((_ROOT / "reference" / "species_stats.json").read_text(encoding="utf-8"))
_MEGA_STONES = json.loads((_ROOT / "reference" / "mega_stones.json").read_text(encoding="utf-8"))
_LEGAL_ITEMS = (_ROOT / "reference" / "champions_legal_items.txt").read_text(encoding="utf-8").split()
_SPECIES_WEIGHTS = json.loads((_ROOT / "belief" / "usage_data" / "species_weights.json").read_text(encoding="utf-8"))
_USAGE_STATS = json.loads((_ROOT / "belief" / "usage_data" / "usage_stats.json").read_text(encoding="utf-8"))

_PLACEHOLDER_PP = 16  # opponent PP isn't tracked in BattleState yet

_TOP_K = 8  # see _top_candidates


def _top_candidates(weights: dict[str, float], pool: list[str], top_k: int) -> list[str]:
    """Restricts a pool to its top-K by weight before sampling. Without
    this, a species' FULL legal pool (moves: often 20-40+; items: 148)
    dilutes real signal into noise: dozens of never-used options each
    carrying a small nonzero floor weight sum to enough mass that even a
    move used 89% of the time on a real team only got drawn ~29% of the
    time in testing — barely better than plain uniform sampling would
    give, and not what "weighted by real usage" is supposed to mean.
    Restricting to the top ~12 candidates (a mix of real top-reported
    picks and the best fallback options for any gaps) keeps the
    competition to genuinely plausible choices, matching how a real
    player's actual consideration set for a species is a similarly-sized
    shortlist, not its entire learnset.
    """
    return sorted(pool, key=lambda x: -weights.get(x, 0.1))[:top_k]


def _weighted_choice(rng: random.Random, weights: dict[str, float], pool: list[str], top_k: int = _TOP_K) -> str:
    candidates = _top_candidates(weights, pool, top_k)
    return rng.choices(candidates, weights=[weights.get(x, 0.1) for x in candidates], k=1)[0]


def _weighted_sample(rng: random.Random, weights: dict[str, float], pool: list[str], k: int,
                      top_k: int = _TOP_K) -> list[str]:
    """Weighted sampling WITHOUT replacement, restricted to the top-K
    candidates by weight first (see _top_candidates): draw one at a time
    with random.choices (with replacement), remove what was drawn from
    the remaining pool, repeat. Standard sequential technique — not an
    exact joint distribution, but doesn't need to be for this use.
    """
    remaining = _top_candidates(weights, pool, top_k)
    chosen = []
    for _ in range(min(k, len(remaining))):
        pick = rng.choices(remaining, weights=[weights.get(x, 0.1) for x in remaining], k=1)[0]
        chosen.append(pick)
        remaining.remove(pick)
    return chosen


def _placeholder_stats(species: SpeciesId) -> tuple[int, dict[str, int]]:
    """(max_hp, stats) at the champions zero-investment floor: stat =
    base + points + 20 (+75 for HP), 0 points everywhere. Same convention
    as model/damage_calc.estimate_opponent_stats (duplicated rather than
    imported: belief/ must not depend on model/).
    """
    base = _SPECIES_STATS[species]["base_stats"]
    return base["hp"] + 75, {k: base[k] + 20 for k in ("atk", "def", "spa", "spd", "spe")}


def _own_stone(species: SpeciesId) -> str | None:
    for stone, formes in _MEGA_STONES.items():
        if species in formes or species in formes.values():
            return stone
    return None


def _sample_item(species: SpeciesId, used_items: set[str], stones_allowed: bool, rng: random.Random) -> str | None:
    pool = []
    for item in _LEGAL_ITEMS:
        if item in used_items:
            continue
        if item in _MEGA_STONES:
            # a stone is dead weight unless it megas THIS species (and the
            # side can still mega at all)
            if not stones_allowed or species not in _MEGA_STONES[item]:
                continue
        pool.append(item)
    weights = _SPECIES_WEIGHTS.get(base_species_id(species), {}).get("items", {})
    item = _weighted_choice(rng, weights, pool)
    used_items.add(item)
    return item


def _sample_moves(species: SpeciesId, revealed: list[str], rng: random.Random) -> list[MoveSlot]:
    learnset = _SPECIES_DATA[species]["moves"]
    remaining = [m for m in learnset if m not in revealed]
    weights = _SPECIES_WEIGHTS.get(base_species_id(species), {}).get("moves", {})
    fill = _weighted_sample(rng, weights, remaining, 4 - len(revealed))
    return [MoveSlot(move=m, pp=_PLACEHOLDER_PP, max_pp=_PLACEHOLDER_PP) for m in list(revealed) + fill]


def _concretize(opp: OpponentPokemon, used_items: set[str], stones_allowed: bool, rng: random.Random) -> OwnPokemon:
    """A revealed opponent mon -> one concrete hypothesis, observed facts
    carried over exactly, hidden slots sampled.
    """
    max_hp, stats = _placeholder_stats(opp.species)
    if opp.known_stats:
        stats = dict(opp.known_stats)

    if opp.revealed_item:
        item = opp.revealed_item
        used_items.add(item)
    elif opp.mega_activated:
        item = _own_stone(opp.species)  # species is the forme id post-mega
        if item:
            used_items.add(item)
    else:
        item = _sample_item(opp.species, used_items, stones_allowed, rng)

    ability_weights = _SPECIES_WEIGHTS.get(base_species_id(opp.species), {}).get("abilities", {})
    ability = opp.revealed_ability or _weighted_choice(rng, ability_weights, _SPECIES_DATA[opp.species]["abilities"])

    return OwnPokemon(
        species=opp.species,
        level=opp.level,
        position=opp.position,
        fainted=opp.fainted,
        hp=0 if opp.fainted else int(round(max_hp * opp.hp_pct / 100)),
        max_hp=max_hp,
        status=opp.status,
        status_turns=opp.status_turns,
        stats=stats,
        boosts=opp.boosts.model_copy(),
        ability=ability,
        item=item,
        moves=_sample_moves(opp.species, opp.revealed_moves, rng),
        mega_activated=opp.mega_activated,
        volatiles=[v.model_copy(deep=True) for v in opp.volatiles],
    )


def _fresh(species: SpeciesId, used_items: set[str], stones_allowed: bool, rng: random.Random) -> OwnPokemon:
    """A hypothesized never-seen back-slot mon: everything sampled."""
    max_hp, stats = _placeholder_stats(species)
    ability_weights = _SPECIES_WEIGHTS.get(base_species_id(species), {}).get("abilities", {})
    return OwnPokemon(
        species=species,
        position=None,
        hp=max_hp,
        max_hp=max_hp,
        stats=stats,
        ability=_weighted_choice(rng, ability_weights, _SPECIES_DATA[species]["abilities"]),
        item=_sample_item(species, used_items, stones_allowed, rng),
        moves=_sample_moves(species, [], rng),
    )


def _is_seen(roster_species: SpeciesId, revealed_species: set[SpeciesId]) -> bool:
    # a mega'd revealed mon carries its forme id (e.g. charizardmegay) while
    # the preview roster showed the base (charizard) — prefix-match covers it
    return any(seen == roster_species or seen.startswith(roster_species) for seen in revealed_species)


def _bring_subset_weights(unseen: list[SpeciesId], revealed_species: set[SpeciesId]) -> dict[str, float]:
    """Weights each still-unseen roster species by how strongly it's
    associated with the mons already confirmed brought (their "Common
    Teammates" rank from usage_stats.json — see belief/usage_data/), so
    e.g. Pelipper gets weighted up once Archaludon is already revealed,
    instead of every unseen combination being equally likely. Rank-based
    (1/(rank+1)), summed across every revealed mon's teammate list, with
    a floor for candidates that show up in none of them (still possible,
    just not indicated by the data) — teammate lists are short (~6), so
    this is a coarse but directionally correct signal, not a precise
    co-occurrence model.
    """
    floor = 0.2
    scores = {s: floor for s in unseen}
    for revealed in revealed_species:
        teammates = _USAGE_STATS.get(base_species_id(revealed), {}).get("teammates", [])
        for rank, mate in enumerate(teammates):
            if mate in scores:
                scores[mate] += 1.0 / (rank + 1)
    return scores


def sample_determinization(state: BattleState, rng: random.Random) -> FullInfoState:
    revealed = list(state.opp_active) + list(state.opp_bench)
    revealed_species = {m.species for m in revealed}
    unseen = [s for s in state.opp_roster if not _is_seen(s, revealed_species)]

    n_hypothesized = max(0, 4 - len(revealed))
    bring_weights = _bring_subset_weights(unseen, revealed_species)
    hypothesized = _weighted_sample(rng, bring_weights, unseen, n_hypothesized)

    stones_allowed = not state.field.opp_side.mega_used
    used_items: set[str] = set()
    opp_team = [_concretize(m, used_items, stones_allowed, rng) for m in revealed]
    opp_team += [_fresh(s, used_items, stones_allowed, rng) for s in hypothesized]

    return FullInfoState(
        turn=state.turn,
        field=state.field.model_copy(deep=True),
        my_team=[m.model_copy(deep=True) for m in list(state.my_active) + list(state.my_bench)],
        opp_team=opp_team,
    )


def sample_team_preview_world(state: BattleState, rng: random.Random) -> TeamPreviewRootState:
    """The team-preview-time determinizer: one hypothesis of the
    opponent's FULL 6-mon roster (every hidden attribute for all 6, not
    just an already-fixed bring-4 subset), for the team-preview search to
    choose a bring/lead action against. Requires state.team_preview to be
    set (state.my_bench then holds all 6 of my own real, fully-known
    mons — see harness/translator.py's battle_to_state, which populates
    my_bench with the whole roster during battle.in_team_preview since
    nothing is active yet).

    Deliberately does NOT sample which 4-of-6 the opponent brings: that
    is exactly the action the opponent-side CFR search enumerates and
    mixes over (model/action_space.py's propose_pruned_team_preview_
    actions), symmetric to how sample_determinization never pre-samples
    "what move will the opponent pick" for an in-battle decision. Only
    hidden per-mon attributes (moves/item/ability/stats) are sampled
    here, via the same _fresh() used for never-seen back-bench mons in
    sample_determinization — called 6 times instead of 4, sharing one
    used_items set across all 6 for the item clause.
    """
    my_team = [m.model_copy(deep=True) for m in state.my_bench]

    stones_allowed = True  # pre-battle: nobody's mega'd yet
    used_items: set[str] = set()
    opp_team = [_fresh(species, used_items, stones_allowed, rng) for species in state.opp_roster]

    return TeamPreviewRootState(field=state.field.model_copy(deep=True), my_team=my_team, opp_team=opp_team)
