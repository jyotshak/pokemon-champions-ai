"""Turns the raw pastes fetched by fetch_team_sheet.py into final, usable
team strings: backfills missing EVs/nature from real usage data (reusing
harness/team_paste.py's add_ev_spreads/add_level unchanged - this is
exactly the pipeline it was built for, just fed from a new source) and
validates each result actually parses as a legal team via the same
ConstantTeambuilder check harness/test_team_paste.py already uses for
hand-built named teams.

Run from the project root: python -m harness.parse_team_sheet
"""

import json
from pathlib import Path

from poke_env.teambuilder import ConstantTeambuilder

from harness.team_paste import add_ev_spreads, add_level

_HERE = Path(__file__).resolve().parent / "team_sheet_data"
_RAW_PASTES_DIR = _HERE / "raw_pastes"
_MANIFEST_PATH = _HERE / "team_sheet.json"
_OUT_PATH = _HERE / "teams.json"


def build_team(raw_paste: str) -> str:
    return add_level(add_ev_spreads(raw_paste))


def main():
    manifest = json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))
    print(f"{len(manifest)} teams in manifest")

    built, failed = {}, []
    for team in manifest:
        team_id = team["team_id"]
        raw_path = _RAW_PASTES_DIR / f"{team_id}.txt"
        if not raw_path.exists():
            failed.append((team_id, "no cached raw paste (fetch failed earlier)"))
            continue
        raw_paste = raw_path.read_text(encoding="utf-8")
        try:
            paste = build_team(raw_paste)
            packed = ConstantTeambuilder(paste).yield_team()
            if not packed:
                raise ValueError("ConstantTeambuilder produced an empty team")
        except Exception as e:
            failed.append((team_id, repr(e)))
            continue
        built[team_id] = {**team, "paste": paste}

    _OUT_PATH.write_text(json.dumps(built, indent=1), encoding="utf-8")
    print(f"wrote {_OUT_PATH} ({len(built)} valid teams, {len(failed)} failed)")
    for team_id, err in failed[:30]:
        print(f"  FAILED {team_id}: {err}")
    if len(failed) > 30:
        print(f"  ... and {len(failed) - 30} more")


if __name__ == "__main__":
    main()
