"""Builds a symmetric pairwise team-synergy weight table, blending two
real data sources scraped from Pikalytics:

1. Per-species "Common Teammates" (belief/usage_data/usage_stats.json's
   `teammates` field, ~230 species covered) — a ranked co-occurrence list
   per species. Broad coverage, coarse signal (rank order only; real
   percentages were lost to a site parsing quirk — see parse_pikalytics.
   py). Reuses the same rank-decay scoring pattern already established in
   belief/determinize.py::_bring_subset_weights (1/(rank+1)), generalized
   from "score candidates against a fixed anchor" into a full pairwise
   table.
2. "Common Team Cores" (belief/usage_data/team_cores.json, 15 entries:
   the top-5 ranked 2/3/4-Pokemon combos globally, each with a real
   tournament team count and usage %) — narrow (covers only the handful
   of most-dominant archetypes) but high-confidence, so it's folded in as
   an extra bonus on top of the broader rank-decay signal, not a
   replacement for it.

SYNERGY_WEIGHTS is computed ONCE, eagerly, at import time (mirrors
belief/usage_data/species_weights.json's _SPECIES_WEIGHTS load-once
convention — this is a static lookup table, not a per-call sampler like
sample_determinization/sample_team_preview_world) and is cheap (O(230
species x ~6 teammates) plus 15 core entries), so no offline precompute
step or checked-in JSON artifact is needed for the blend itself — only
the two raw scraped inputs (usage_stats.json, team_cores.json) are
checked-in data.

model/ never imports this module directly (the model/belief dependency
rule — see docs/solver_design.md section 1): harness/ loads SYNERGY_
WEIGHTS once and passes it into model/ functions as a plain parameter,
same as any other belief-layer output.
"""

import json
from itertools import combinations
from pathlib import Path

from belief.species_folding import base_species_id

_HERE = Path(__file__).resolve().parent
_USAGE_STATS = json.loads((_HERE / "usage_data" / "usage_stats.json").read_text(encoding="utf-8"))
_TEAM_CORES = json.loads((_HERE / "usage_data" / "team_cores.json").read_text(encoding="utf-8"))

# Team-core bonus is scaled from the core's real usage % (0-100) rather
# than a flat per-tier constant, so the single dominant core (19.5%
# usage) contributes more than a marginal 5th-ranked one (5.8%) - divided
# down to stay comparable in magnitude to the rank-decay contributions
# below (which max out around 1.0-2.0 per pair for a very tightly-linked
# species pair), not swamp them outright. Tunable.
_CORE_BONUS_SCALE = 0.1


def _bump(weights: dict[str, dict[str, float]], a: str, b: str, amount: float) -> None:
    weights.setdefault(a, {})
    weights[a][b] = weights[a].get(b, 0.0) + amount
    weights.setdefault(b, {})
    weights[b][a] = weights[b].get(a, 0.0) + amount


def build_synergy_weights() -> dict[str, dict[str, float]]:
    weights: dict[str, dict[str, float]] = {}

    # (1) per-species teammate rank-decay, mirrored into both directions
    # so the resulting table is symmetric regardless of which of a pair's
    # two teammate lists actually reported the other (sample-size
    # asymmetry between two real species' scraped pages is expected and
    # shouldn't produce a directional table).
    for species, data in _USAGE_STATS.items():
        for rank, mate in enumerate(data.get("teammates", [])):
            if mate == species:
                continue
            _bump(weights, species, mate, 1.0 / (rank + 1))

    # (2) team-core bonus: every pair within a scraped core gets a bonus
    # scaled by that core's real usage %. Core species are battle-forme
    # ids (e.g. "swampertmega") since that's how Pikalytics' Team Cores
    # table lists them - fold to base species so lookups line up with
    # usage_stats.json's (already base-id) keys.
    for core in _TEAM_CORES:
        species = [base_species_id(s) for s in core["species"]]
        bonus = _CORE_BONUS_SCALE * core["pct"]
        for a, b in combinations(species, 2):
            _bump(weights, a, b, bonus)

    return weights


SYNERGY_WEIGHTS = build_synergy_weights()
