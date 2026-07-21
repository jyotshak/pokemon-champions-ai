"""Combines real Pikalytics data (usage_stats.json) with a global-
popularity fallback into ONE complete weight table covering every
champions-legal base species' full legal move/ability/item pool — not
just the ~23 species with no Pikalytics data at all, but also the long
tail of any species' own learnset beyond whatever top-N list Pikalytics
reports (confirmed with the user: fallback quality is fine even for
edge-case unique abilities/moves on mons that are never seen in
practice, since correctness only matters where it's actually exercised).

Fallback design: for any (species, move) pair, use the real reported %
if Pikalytics has it; otherwise use that move's GLOBAL popularity (its
average reported % across every species that does report it), computed
once from the whole real dataset. Same for abilities and items. This is
a per-move/per-ability/per-item fallback, not a per-species switch — a
species with 8 of 10 moves reported still gets real weights for those 8
and only falls back for the other 2.

Output covers the 238 base-species query targets (see fetch_pikalytics.
py for why mega formes aren't separate entries here — moves/abilities
don't change on mega evolution, so mega-forme species ids resolve to
their base species' table at lookup time, not duplicated here).

Run from the project root: python -m belief.usage_data.build_weights
"""

import json
import re
from pathlib import Path

from belief.species_folding import base_species_id as _base_species_id


def _to_id(name: str) -> str:
    """Showdown-style id (lowercase, alphanumerics only): 'Armor Tail' ->
    'armortail'. reference/species_data.json stores ABILITY legal pools
    as display names, but usage_stats.json keys abilities by id - so the
    reported/global lookup must normalize (moves and items are already
    id-on-both-sides, only abilities carry this mismatch)."""
    return re.sub(r"[^a-z0-9]", "", name.lower())

_ROOT = Path(__file__).resolve().parent.parent.parent
_HERE = Path(__file__).resolve().parent
_USAGE_STATS = json.loads((_HERE / "usage_stats.json").read_text(encoding="utf-8"))
_SPECIES_DATA = json.loads((_ROOT / "reference" / "species_data.json").read_text(encoding="utf-8"))
_LEGAL_ITEMS = (_ROOT / "reference" / "champions_legal_items.txt").read_text(encoding="utf-8").split()


def compute_global_popularity(field: str) -> dict[str, float]:
    """Average reported % for each move/ability, across every species
    that reports it at all. Broadly-splashable options (Protect)
    naturally end up ranked highly since they're reported often AND at
    decent %; a move only good on one niche species still scores
    reasonably if that's the only data point, which is fine — it's only
    ever consulted after intersecting with a specific species' actual
    legal pool anyway (moves/abilities are gated by that species' own
    real learnset, info["moves"]/info["abilities"] in build() below, a
    small and already-thematically-relevant universe).

    NOT used for items (see compute_global_item_popularity) - items have
    no per-species legal-pool gate the way moves/abilities do (build()
    passes the full champions-legal item list to every species alike),
    so this function's "average only among species that report it"
    denominator is unsafe there: a highly species-specific item reported
    by just one or two species at very high % (Light Ball on Pikachu/
    Raichu, ~97%) would leak through as an inflated fallback weight for
    every OTHER species too, competing directly with that species' own
    real, correctly-reported items - found live (2026-07-19): Charizard's
    built fallback showed lightball at 97.1, nearly tying its own real
    charizarditey usage (95.4) in the sampler's weighted pool, because
    lightball is reported by essentially nobody except Pikachu/Raichu.
    """
    totals: dict[str, list[float]] = {}
    for species in _USAGE_STATS.values():
        for name, pct in species[field].items():
            totals.setdefault(name, []).append(pct)
    return {name: sum(pcts) / len(pcts) for name, pcts in totals.items()}


def compute_global_item_popularity(total_species: int) -> dict[str, float]:
    """Same idea as compute_global_popularity, but correctly normalized
    for items: divides by the TOTAL number of species considered, not
    just the count that happen to report the item at all - a species
    that doesn't report an item is real signal that the item is rarely
    if ever used on it (unlike moves/abilities, items have no learnset
    gate, so "didn't report" can't be explained away as "couldn't legally
    hold it" the way an unreported move can be explained by the species
    just not knowing it). This makes a hyper-specific item's fallback
    weight for an unrelated species correctly small (~97 * 2/238 mons
    that report it ≈ 0.8, not 97) instead of leaking its ONE reporting
    species' near-100% usage straight through as if it were universal.
    """
    totals: dict[str, float] = {}
    for species in _USAGE_STATS.values():
        for name, pct in species["items"].items():
            totals[name] = totals.get(name, 0.0) + pct
    return {name: total / total_species for name, total in totals.items()}


def _species_weights(species_id: str, legal_pool: list[str], reported: dict[str, float],
                      global_pop: dict[str, float], key_for_lookup=lambda x: x) -> dict[str, float]:
    """reported wins where present; global popularity fills every other
    legal option; anything with zero global signal at all (never once
    reported on any species) gets a small nonzero floor rather than 0,
    so sampling still has SOME chance of covering it rather than a hard
    exclusion — legality was already the hard gate (see belief/
    determinize.py), this is just a soft prior on top of it.

    key_for_lookup maps a legal-pool entry to the key used to look it up
    in reported/global_pop. Identity for moves/items (id-keyed on both
    sides), but _to_id for abilities: the OUTPUT stays keyed by the
    legal-pool's display name (that is what belief/determinize.py's
    _weighted_choice looks up against species_data's display-name pool),
    while the reported/global lookup uses the id. Without this every
    ability lookup missed and fell to the floor, making the ability prior
    UNIFORM over each species' legal set for all 237 species (found live
    2026-07-20: Farigiraf's real Armor Tail 99.9% flattened to 0.1, so
    only ~1/3 of sampled worlds gave it the priority-blocking ability -
    same for Intimidate, Pixilate, every meta-defining ability).
    """
    floor = 0.1
    return {
        name: reported.get(key_for_lookup(name), global_pop.get(key_for_lookup(name), floor))
        for name in legal_pool
    }


def build() -> dict:
    fold_targets = {_base_species_id(sp) for sp in _SPECIES_DATA}

    global_moves = compute_global_popularity("moves")
    global_abilities = compute_global_popularity("abilities")
    global_items = compute_global_item_popularity(len(fold_targets))

    weights = {}
    for species_id in sorted(fold_targets):
        info = _SPECIES_DATA.get(species_id)
        if info is None:
            continue
        reported = _USAGE_STATS.get(species_id, {"moves": {}, "abilities": {}, "items": {}})
        weights[species_id] = {
            "moves": _species_weights(species_id, info["moves"], reported["moves"], global_moves),
            "abilities": _species_weights(species_id, info["abilities"], reported["abilities"],
                                          global_abilities, key_for_lookup=_to_id),
            "items": _species_weights(species_id, _LEGAL_ITEMS, reported["items"], global_items),
        }
    return weights


def main():
    weights = build()
    out_path = _HERE / "species_weights.json"
    out_path.write_text(json.dumps(weights, indent=1, sort_keys=True), encoding="utf-8")
    print(f"wrote {out_path} ({len(weights)} species)")

    fully_fallback = [
        sp for sp, d in weights.items()
        if not _USAGE_STATS.get(sp, {}).get("moves")
    ]
    print(f"{len(fully_fallback)} species using pure fallback for moves (no Pikalytics move data at all)")


if __name__ == "__main__":
    main()
