"""Fetches the community-maintained "VGCPastes Repository (Champions M-B)"
Google Sheet (~555 real tournament/content-creator teams, each linking a
pokepast.es paste) plus every linked pokepaste's raw Showdown export.

Two-stage, same shape as belief/usage_data's fetch scripts:
1. The sheet itself, via Google Sheets' CSV export endpoint (no auth/API
   key needed for a publicly-viewable sheet - appending
   `/export?format=csv&gid=...` to the sheet URL returns a plain CSV,
   avoiding the JS-rendered UI entirely).
2. Every distinct pokepaste URL found in it, via pokepast.es's own
   `/raw` endpoint (a feature the site provides specifically for
   plain-text consumption of a paste - same idea as GitHub's "raw" view).
   pokepast.es has no robots.txt (confirmed: 404), and paste pages are
   public-by-design (the whole point of a paste-sharing site); fetched
   politely rate-limited regardless.

Caches raw paste text to raw_pastes/{team_id}.txt and writes the sheet's
own metadata (minus paste content) to team_sheet.json - parse_team_sheet.
py turns the two into final, EV-backfilled team strings.

Run from the project root: python -m harness.fetch_team_sheet
"""

import csv
import io
import json
import re
import time
import urllib.request
from pathlib import Path

_HERE = Path(__file__).resolve().parent / "team_sheet_data"
_RAW_PASTES_DIR = _HERE / "raw_pastes"
_MANIFEST_PATH = _HERE / "team_sheet.json"

SHEET_ID = "1axlwmzPA49rYkqXh7zHvAtSP-TKbM0ijGYBPRflLSWw"
SHEET_GID = "1458357160"
SHEET_CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={SHEET_GID}"

USER_AGENT = "Mozilla/5.0 (compatible; pokemon-champions-research-bot)"
DELAY_SECONDS = 0.3

# 0-based column indices in the sheet's header row (row 3, 0-indexed row 2) -
# there are two blank spacer columns after most headers, so these are NOT
# consecutive integers. Verified by reading the actual exported CSV, not
# guessed from the visual layout.
_COL_TEAM_ID = 0
_COL_DESCRIPTION = 1
_COL_POKEPASTE_URL = 24
_COL_EVS_PRESENT = 25
_COL_TOURNAMENT = 30
_COL_RANK = 31
_COL_OWNER = 35
_COL_SPECIES_START = 37  # 6 consecutive columns: "Pokemon Text for Copypasta"


def _normalize_line_endings(text: str) -> str:
    """Collapses any run of \\r (optionally followed by \\n) to a single
    bare \\n. NOT the naive `.replace("\\r\\n", "\\n").replace("\\r",
    "\\n")` chain (mishandles an already-doubled "\\r\\r\\n": the first
    replace only consumes the trailing "\\r\\n", leaving one "\\r"
    behind, which the second replace turns into a SECOND "\\n" - a
    doubled line ending becomes a blank line instead of collapsing to
    one). Also NOT `\\r\\n|\\r` (same failure mode: at the position of
    the FIRST "\\r" in "\\r\\r\\n", the next char is another "\\r" not
    "\\n", so the "\\r\\n" branch can't match there either - it falls
    back to matching the lone "\\r" alone, then matches the trailing
    "\\r\\n" as a SEPARATE match, again producing two newlines instead
    of one. Found live, 2026-07-19, on the SECOND attempt at this exact
    fix.) `\\r+\\n?` greedily consumes the WHOLE run of CRs plus at most
    one trailing LF as a single match, so a doubled, tripled, or lone CR
    all collapse to exactly one "\\n".
    """
    return re.sub(r"\r+\n?", "\n", text)


def _fetch_text(url: str) -> str:
    # Normalize to bare \n right away: pokepast.es's raw export (and the
    # sheet CSV) come back with \r\n line endings, and Path.write_text's
    # default text-mode translation on Windows turns every embedded \n
    # into \r\n again - doubling the existing \r into \r\n\r -> \r\r\n
    # rather than leaving it alone. That corrupts every downstream line-
    # based parse (add_ev_spreads/add_level split on blank lines) into
    # treating each SINGLE line as its own paragraph, since \n\n now
    # appears between every line, not just between mons - found live
    # (2026-07-19): parse_team_sheet.py's cached raw_pastes/*.txt files
    # all had this exact corruption, silently produced malformed
    # 50+-fragment "teams" from clean 6-mon source pastes.
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return _normalize_line_endings(resp.read().decode("utf-8"))


def fetch_sheet_rows() -> list[dict]:
    csv_text = _fetch_text(SHEET_CSV_URL)
    rows = list(csv.reader(io.StringIO(csv_text)))
    data_rows = rows[4:]  # header is row index 2; row 3 is a sub-header; data starts row 4

    teams = []
    for row in data_rows:
        if len(row) <= _COL_POKEPASTE_URL or not row[_COL_TEAM_ID].strip():
            continue
        pokepaste_url = row[_COL_POKEPASTE_URL].strip()
        if not pokepaste_url:
            continue
        teams.append({
            "team_id": row[_COL_TEAM_ID].strip(),
            "description": row[_COL_DESCRIPTION].strip(),
            "pokepaste_url": pokepaste_url,
            "evs_present": row[_COL_EVS_PRESENT].strip() == "Yes",
            "tournament": row[_COL_TOURNAMENT].strip(),
            "rank": row[_COL_RANK].strip(),
            "owner": row[_COL_OWNER].strip(),
            "species": [row[_COL_SPECIES_START + i].strip() for i in range(6)
                        if len(row) > _COL_SPECIES_START + i and row[_COL_SPECIES_START + i].strip()],
        })
    return teams


def _raw_url(pokepaste_url: str) -> str:
    return pokepaste_url.rstrip("/") + "/raw"


def main():
    _RAW_PASTES_DIR.mkdir(parents=True, exist_ok=True)
    teams = fetch_sheet_rows()
    print(f"{len(teams)} teams found in the sheet")

    fetched, skipped, failed = 0, 0, []
    for i, team in enumerate(teams):
        out_path = _RAW_PASTES_DIR / f"{team['team_id']}.txt"
        if out_path.exists():
            skipped += 1
            continue
        try:
            content = _fetch_text(_raw_url(team["pokepaste_url"]))
            out_path.write_text(content, encoding="utf-8")
            fetched += 1
        except Exception as e:
            failed.append((team["team_id"], repr(e)))
        if (i + 1) % 50 == 0:
            print(f"  {i + 1}/{len(teams)} processed ({fetched} fetched, {skipped} cached, {len(failed)} failed)")
        time.sleep(DELAY_SECONDS)

    _MANIFEST_PATH.write_text(json.dumps(teams, indent=1), encoding="utf-8")
    print(f"\nwrote {_MANIFEST_PATH} ({len(teams)} teams)")
    print(f"pastes: {fetched} fetched, {skipped} already cached, {len(failed)} failed")
    for team_id, err in failed[:20]:
        print(f"  FAILED {team_id}: {err}")


if __name__ == "__main__":
    main()
