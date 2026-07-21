"""Browse/search the scraped team sheet yourself (harness/team_sheet_data/
teams.json, 555 popularity-ranked real teams) without hand-opening the
JSON. Prints one line per team, most popular first, with quick
speed-control flags (Trick Room / Tailwind) since those aren't visible
from the species list alone.

Filters: every positional argument is a required, case-insensitive
substring matched against the team's FULL paste text (species + moves +
items + abilities) - so multiple args are AND-ed. Examples:

    python -m harness.list_teams                      # all 555, ranked
    python -m harness.list_teams tailwind             # teams that run Tailwind
    python -m harness.list_teams "trick room"         # Trick Room teams
    python -m harness.list_teams "trick room" farigiraf   # both must appear
    python -m harness.list_teams --limit 20 tailwind  # top 20 matches
    python -m harness.list_teams --show MB187          # dump one team's full paste

Use the ids it prints (e.g. MB187) directly in the match scripts.
"""

import sys

from harness.team_sheet import team_by_id, top_k_teams

_TR = "trick room"
_TW = "tailwind"


def _flags(paste_lower: str) -> str:
    tr = "TR" if _TR in paste_lower else "  "
    tw = "TW" if _TW in paste_lower else "  "
    return f"{tr} {tw}"


def main(argv: list[str]) -> None:
    limit = None
    terms = []
    i = 0
    while i < len(argv):
        if argv[i] == "--limit" and i + 1 < len(argv):
            limit = int(argv[i + 1])
            i += 2
        elif argv[i] == "--show" and i + 1 < len(argv):
            t = team_by_id(argv[i + 1])
            print(f"# {t['team_id']}  pop={t['popularity_score']:.1f}  — {t.get('description', '')}\n")
            print(t["paste"])
            return
        else:
            terms.append(argv[i].lower())
            i += 1

    teams = top_k_teams(10_000)  # all of them, ranked
    shown = 0
    for t in teams:
        paste_lower = t["paste"].lower()
        if any(term not in paste_lower for term in terms):
            continue
        species = ", ".join(t["species"])
        desc = t.get("description", "")
        print(f"{t['team_id']:7s} pop={t['popularity_score']:5.1f}  [{_flags(paste_lower)}]  {species}  — {desc}")
        shown += 1
        if limit is not None and shown >= limit:
            break

    print(f"\n{shown} team(s)" + (f" matching {terms}" if terms else "") + f" of {len(teams)} total")


if __name__ == "__main__":
    main(sys.argv[1:])
