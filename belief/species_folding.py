"""Mega-forme -> base-species id folding, shared across belief/'s usage-
data pipeline (fetch_pikalytics.py's queries, build_weights.py, determinize.
py, and now team_synergy.py all need the same fold: moves/abilities/
teammates are identical pre- and post-mega, so a mega-forme species id
(e.g. "charizardmegay") should resolve to its base ("charizard") wherever
usage/teammate data is looked up, without duplicating separate rows for
every forme). Hoisted here once a third near-identical copy (in the new
team-synergy code) would have made it needless within-layer duplication -
this project's convention only justifies duplication *across* the model/
belief boundary, not within belief/ itself.

Depends only on reference/ data (mega_stones.json), consistent with
belief/'s own dependency rule.
"""

import json
import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_MEGA_STONES = json.loads((_ROOT / "reference" / "mega_stones.json").read_text(encoding="utf-8"))

# Non-mega mid-battle transformations that Pikalytics folds into their
# base species' page too (see belief/usage_data/fetch_pikalytics.py's
# original docstring: Aegislash-Blade 404s on its own, same shape as a
# mega - it's the base's in-battle transformation, not a separately
# brought Pokemon), plus meowsticfmega's base "meowsticf" never got a
# separate entry in reference/species_data.json (a gap from the original
# species extraction) - male/female Meowstic share the same movepool, so
# folding to base "meowstic" is a reasonable direct fix.
_EXPLICIT_FOLD_TO_BASE = {"aegislashblade": "aegislash", "meowsticfmega": "meowstic"}


def base_species_id(species_id: str) -> str:
    """Maps any species id (mega or not) down to its base/query-target id."""
    if species_id in _EXPLICIT_FOLD_TO_BASE:
        return _EXPLICIT_FOLD_TO_BASE[species_id]
    for mapping in _MEGA_STONES.values():
        if species_id in mapping.values():
            return next(base for base, forme in mapping.items() if forme == species_id)
    return species_id


def to_id(name: str) -> str:
    """Free-text display name -> species id: lowercase, strip everything
    but alphanumerics ("Charizard-Mega-Y" -> "charizardmegay").
    """
    return re.sub(r"[^a-z0-9]", "", name.lower())
