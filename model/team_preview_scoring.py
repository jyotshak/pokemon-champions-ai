"""Shared team-preview scoring core, used by both model/action_space.py
(the search pruner) and model/heuristic.py (the non-search baseline) — a
shared leaf module rather than one importing "private" helpers from the
other, matching how both are already thin consumers of damage_calc.py's
primitives (same shape, not a new pattern).

Reads ONLY species identity off both rosters (species_types/reference/
mega_stones.json — static, public, world-invariant data) plus an
optionally-injected synergy_weights table (belief-layer output, passed in
as a plain parameter — model/ never imports belief/, per docs/
solver_design.md section 1's dependency rule). NEVER reads a sampled
hidden per-mon attribute (moves/item/ability/stats): this project has hit
that exact bug class three times already (mega_used, boosts, the
Metronome-item volatile) and the team-preview pruner's world-invariance
requirement depends on it — see propose_pruned_team_preview_actions'
docstring in model/action_space.py for the concrete mechanism (the
solver's keying contract requires my_actions(state) to be identical
whenever my_key(state) matches, which is world-independent for my own
side).
"""

import json
from itertools import combinations
from pathlib import Path

from model.damage_calc import species_types, type_effectiveness
from schema.battle_state import SpeciesId

_ROOT = Path(__file__).resolve().parent.parent
_MEGA_STONES = json.loads((_ROOT / "reference" / "mega_stones.json").read_text(encoding="utf-8"))

# Every species id that appears as a mega-stone's base-species key -
# public, static eligibility ("can this species ever hold a mega stone"),
# never "does it currently hold one" (that's mon.item, a hidden per-world
# attribute the pruner is contractually forbidden from reading).
_MEGA_ELIGIBLE_SPECIES: set[SpeciesId] = {
    base for mapping in _MEGA_STONES.values() for base in mapping
}


def is_mega_eligible(species: SpeciesId) -> bool:
    return species in _MEGA_ELIGIBLE_SPECIES


# High-impact support moves whose value to a lead/bring is invisible to
# pure type-chart scoring (2026-07-20). Weights are on the same scale as
# offensive_presence/defensive_risk (type multipliers, 0.25-4), so e.g.
# Tailwind (1.5) is comparable to a super-effective matchup - meaningful
# but not overwhelming. Deliberately a small curated set of the moves
# that most change lead value in this format (immediate speed control,
# redirection, turn-1 disruption), NOT an exhaustive status-move list.
_SUPPORT_MOVE_WEIGHTS: dict[str, float] = {
    "tailwind": 1.5, "trickroom": 1.5,   # immediate team-wide speed control
    "fakeout": 1.0,                       # free turn-1 disruption/chip
    "followme": 1.0, "ragepowder": 1.0,   # redirection protects the partner
    "auroraveil": 0.6,                    # dual screen (needs snow, still strong)
    "icywind": 0.6, "electroweb": 0.6,    # spread speed drop
    "thunderwave": 0.4, "reflect": 0.4, "lightscreen": 0.4,
}


def own_support_score(moves) -> float:
    """Summed support-move value for ONE of my own mons, from its known
    moveset. MY-SIDE-ONLY by contract: this is the one place team-preview
    scoring reads movesets rather than species identity alone, and it is
    sound ONLY because my own team's moves are fully known and world-
    invariant (identical across every determinized world - see the big
    CORRECTNESS CONSTRAINT note in model.action_space.
    propose_pruned_team_preview_actions). It must NEVER be fed an
    opponent mon's sampled moves - the caller gates it to side == "me".
    `moves` is a list of MoveSlot-like objects (duck-typed .move id).
    """
    return sum(_SUPPORT_MOVE_WEIGHTS.get(ms.move, 0.0) for ms in moves)


def defensive_risk(species: SpeciesId, enemy_roster: list[SpeciesId]) -> float:
    """Worst-case type effectiveness any enemy roster member's OWN types
    could inflict on this species - a species-only proxy for "how exposed
    is this pick," since actual enemy movesets aren't known yet at team
    preview (a Ground/Dragon-type enemy is assumed a plausible Ground-STAB
    threat purely from its typing, not from any revealed or sampled move).
    """
    my_types = species_types(species)
    return max(
        (type_effectiveness(enemy_type, my_types)
         for enemy in enemy_roster for enemy_type in species_types(enemy)),
        default=1.0,
    )


def offensive_presence(species: SpeciesId, enemy_roster: list[SpeciesId]) -> float:
    """Best-case type effectiveness this species' OWN types could inflict
    on any single enemy roster member - species-only proxy for coverage.
    """
    return max(
        (type_effectiveness(own_type, species_types(enemy))
         for own_type in species_types(species) for enemy in enemy_roster),
        default=1.0,
    )


def pairwise_synergy_sum(species_list: list[SpeciesId], synergy_weights: dict | None) -> float:
    """Sum of synergy_weights[a][b] over every UNORDERED pair in
    species_list (each pair counted once, not twice, despite
    synergy_weights being a symmetric a->b and b->a table). 0.0 whenever
    synergy_weights is None (the default, everywhere) - the feature is
    strictly opt-in and inert unless a caller explicitly threads a real
    table through, keeping every existing call site's behavior bit-
    identical without new kwargs.
    """
    if synergy_weights is None:
        return 0.0
    total = 0.0
    for a, b in combinations(species_list, 2):
        total += synergy_weights.get(a, {}).get(b, 0.0)
    return total


def bring_subset_score(
    subset_species: list[SpeciesId], enemy_roster: list[SpeciesId],
    synergy_weights: dict | None = None, synergy_scale: float = 1.0, mega_penalty: float = 0.0,
    support_by_species: dict[SpeciesId, float] | None = None,
) -> float:
    offense = sum(offensive_presence(sp, enemy_roster) for sp in subset_species)
    defense = sum(defensive_risk(sp, enemy_roster) for sp in subset_species)
    synergy = synergy_scale * pairwise_synergy_sum(subset_species, synergy_weights)
    # My-side-only support-tool bonus (own_support_score, gated by the
    # caller to side == "me"): None everywhere else, so opponent-side and
    # non-team-preview scoring is bit-identical. Summed over 4 mons here,
    # so a single Tailwind user is a modest fraction - "nice to have it in
    # the back," a much stronger signal in lead_pair_score's 2-mon sum.
    support = sum(support_by_species.get(sp, 0.0) for sp in subset_species) if support_by_species else 0.0
    # Flat boolean gate, not scaled by how many eligible members are
    # present: only one mon can ever actually mega per game, so 2
    # eligible members isn't better than 1. Soft (a subtraction, not a
    # filter) and deliberately not paired with hand-coded "unless X"
    # exception logic (e.g. detecting a hard-Trick-Room matchup where
    # every owned mega is fast-and-frail) - a strong offense/defense/
    # synergy score on a genuinely-correct no-mega line can already
    # outweigh a modest flat penalty on its own, which is simpler and
    # more robust than encoding exactly when the exception applies.
    penalty = mega_penalty if not any(is_mega_eligible(sp) for sp in subset_species) else 0.0
    return offense - defense + synergy - penalty + support


def lead_pair_score(
    pair_species: list[SpeciesId], enemy_roster: list[SpeciesId],
    synergy_weights: dict | None = None, synergy_scale: float = 1.0,
    support_by_species: dict[SpeciesId, float] | None = None,
) -> float:
    # Leads face the opponent's opener most directly (including spread
    # moves hitting both at once - the exact mechanism of the reported
    # bug), so defensive risk is weighted more heavily here than for the
    # broader bring-4 score. Deliberately NO mega_penalty: a 2-mon lead
    # with no mega-eligible member is normal, often-correct doubles play
    # (protect the mega, bring it in later on a good matchup) - applying
    # the bring-subset penalty here would create a bad incentive to
    # front-load the mega into every lead.
    offense = sum(offensive_presence(sp, enemy_roster) for sp in pair_species)
    defense = sum(defensive_risk(sp, enemy_roster) for sp in pair_species)
    synergy = synergy_scale * pairwise_synergy_sum(pair_species, synergy_weights)
    # My-side-only support bonus (see bring_subset_score): here it's a
    # 2-mon sum, so leading a Tailwind/Trick Room/Fake Out/redirection
    # user is proportionally a strong signal - this is the term that
    # actually gets such a setter LED rather than benched (the reported
    # "Whimsicott with Tailwind never leads" symptom, since type-only
    # scoring saw it as just a frail Fairy).
    support = sum(support_by_species.get(sp, 0.0) for sp in pair_species) if support_by_species else 0.0
    return offense - 1.5 * defense + synergy + support
