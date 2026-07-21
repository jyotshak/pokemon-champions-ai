"""Small loader over harness/team_sheet_data/ (555 scraped, EV-backfilled,
validated real teams - see fetch_team_sheet.py/parse_team_sheet.py - each
scored for aggregate popularity by rank_team_sheet.py) - the "top-K
popular teams to test against" lookup for future validation batches.
"""

import json
from pathlib import Path

_HERE = Path(__file__).resolve().parent / "team_sheet_data"
_TEAMS_PATH = _HERE / "teams.json"
_RANKED_PATH = _HERE / "teams_ranked.json"


def top_k_teams(k: int) -> list[dict]:
    """The k most popular teams, most popular first. Each entry is the
    full teams.json record (paste, species, popularity_score, tournament/
    rank/owner metadata, ...).
    """
    teams = json.loads(_TEAMS_PATH.read_text(encoding="utf-8"))
    ranked_ids = json.loads(_RANKED_PATH.read_text(encoding="utf-8"))
    return [teams[team_id] for team_id in ranked_ids[:k]]


def team_by_id(team_id: str) -> dict:
    teams = json.loads(_TEAMS_PATH.read_text(encoding="utf-8"))
    return teams[team_id]
