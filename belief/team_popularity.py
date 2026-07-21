"""Aggregate popularity score for a full 6-mon team, from real per-species
tournament usage rates (belief/usage_data/tournament_usage.json, fetched
from Pikalytics' championstournaments category - the one that reports a
real overall Usage % per species, unlike the battledataregmbs3 ladder
data usage_stats.json is built from). Built for harness/team_sheet_data's
555 scraped tournament/creator teams (harness/rank_team_sheet.py), but
generically usable for any 6-species list - this is exactly the "top-K
popular teams to test against" lookup the project's later validation
work wants.

Score = arithmetic mean of the 6 members' individual usage %, the most
literal reading of "aggregate popularity" - a team of 6 meta staples
scores high, a team leaning on rare/off-meta picks scores low, regardless
of whether those picks are good together (that's belief/team_synergy.py's
job, a different, complementary question).
"""

import json
from pathlib import Path

from belief.species_folding import base_species_id, to_id

_HERE = Path(__file__).resolve().parent
_TOURNAMENT_USAGE = json.loads((_HERE / "usage_data" / "tournament_usage.json").read_text(encoding="utf-8"))

# Pikalytics display-name quirks that don't fold cleanly through the
# normal to_id()+base_species_id() path - verified against the actual
# 174 distinct species names appearing in harness/team_sheet_data/teams.
# json (only these 4 needed an explicit override; everything else
# resolved automatically).
_EXPLICIT_FOLD_TO_BASE = {
    "floetteeternalmega": "floetteeternal",  # our mega-forme id is "floettemega", not "floetteeternalmega"
    "mausholdfour": "maushold",  # family-of-four is a cosmetic/size variant, not separately tracked
    "sinistchamasterpiece": "sinistcha",  # alternate evolution item, not separately tracked
    "vivillonfancy": "vivillon",  # cosmetic wing-pattern variant, not separately tracked
}

# Species with no reported tournament usage at all (too rare to register)
# get a small nonzero floor rather than 0 - consistent with this project's
# established convention elsewhere (belief/usage_data/build_weights.py's
# per-move/ability/item floor=0.1) - legitimately rare, not impossible.
_FLOOR_USAGE_PCT = 0.5


def resolve_species_id(display_name: str) -> str:
    """'Charizard-Mega-Y' -> 'charizard', 'Garchomp' -> 'garchomp' - folds
    a Pikalytics/pokepaste-style display name down to the base species id
    tournament_usage.json is keyed by.
    """
    sid = to_id(display_name)
    if sid in _EXPLICIT_FOLD_TO_BASE:
        return _EXPLICIT_FOLD_TO_BASE[sid]
    return base_species_id(sid)


def species_popularity(display_name: str) -> float:
    species_id = resolve_species_id(display_name)
    entry = _TOURNAMENT_USAGE.get(species_id)
    if entry is None or entry.get("usage_pct") is None:
        return _FLOOR_USAGE_PCT
    return entry["usage_pct"]


def team_popularity_score(species_list: list[str]) -> float:
    """Arithmetic mean of the 6 members' individual usage %."""
    if not species_list:
        return 0.0
    return sum(species_popularity(sp) for sp in species_list) / len(species_list)
