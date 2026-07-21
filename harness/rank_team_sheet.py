"""Ranks every team in harness/team_sheet_data/teams.json (the 555
scraped+validated tournament/creator teams - see fetch_team_sheet.py/
parse_team_sheet.py) by aggregate popularity (belief/team_popularity.py:
mean of the 6 members' real tournament usage %), writing the result back
into teams.json (adds a "popularity_score" field to every team) and a
separate teams_ranked.json (team_id list, most popular first) for a
cheap top-K lookup without re-scoring.

Run from the project root: python -m harness.rank_team_sheet
"""

import json
from pathlib import Path

from belief.team_popularity import team_popularity_score

_HERE = Path(__file__).resolve().parent / "team_sheet_data"
_TEAMS_PATH = _HERE / "teams.json"
_RANKED_PATH = _HERE / "teams_ranked.json"


def main():
    teams = json.loads(_TEAMS_PATH.read_text(encoding="utf-8"))
    for team in teams.values():
        team["popularity_score"] = round(team_popularity_score(team["species"]), 2)

    _TEAMS_PATH.write_text(json.dumps(teams, indent=1), encoding="utf-8")

    ranked = sorted(teams.items(), key=lambda kv: -kv[1]["popularity_score"])
    _RANKED_PATH.write_text(json.dumps([team_id for team_id, _ in ranked], indent=1), encoding="utf-8")

    print(f"scored and wrote {_TEAMS_PATH} ({len(teams)} teams)")
    print(f"wrote {_RANKED_PATH}\n")
    print("top 15 by popularity:")
    for team_id, team in ranked[:15]:
        print(f"  {team['popularity_score']:5.1f}  {team_id}  {team['description']}  {team['species']}")
    print("\nbottom 5 by popularity:")
    for team_id, team in ranked[-5:]:
        print(f"  {team['popularity_score']:5.1f}  {team_id}  {team['description']}  {team['species']}")


if __name__ == "__main__":
    main()
