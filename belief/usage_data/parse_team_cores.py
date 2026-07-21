"""Parses the raw "Common Team Cores" markdown tables (belief/usage_data/
raw_team_cores.md, fetched by fetch_team_cores.py) into structured core
data: the top-5 ranked 2/3/4-Pokemon combos, each with a real tournament
team count and usage percentage. Table-shaped, unlike parse_pikalytics.py's
per-species bullet-list sections, so this is a small dedicated parser
rather than bending the existing regexes to also match tables.

Run from the project root: python -m belief.usage_data.parse_team_cores
"""

import json
import re
from pathlib import Path

from belief.species_folding import to_id

_RAW_PATH = Path(__file__).resolve().parent / "raw_team_cores.md"
_OUT_PATH = Path(__file__).resolve().parent / "team_cores.json"

_SECTION = re.compile(r"^### \d-Pokemon Cores\s*$", re.M)
_ROW = re.compile(r"^\|\s*\d+\s*\|\s*(.+?)\s*\|\s*(\d+)\s*\|\s*([\d.]+)%\s*\|\s*$", re.M)


def _section_body(markdown: str, start: re.Match) -> str:
    """Text between one "### N-Pokemon Cores" heading and the next
    "##"/"###" heading (or end) - the table for that tier.
    """
    rest = markdown[start.end():]
    nxt = re.search(r"^#{2,3} ", rest, re.M)
    return rest[: nxt.start()] if nxt else rest


def parse(markdown: str) -> list[dict]:
    cores = []
    for section_match in _SECTION.finditer(markdown):
        body = _section_body(markdown, section_match)
        for species_cell, team_count, pct in _ROW.findall(body):
            species = [to_id(name) for name in species_cell.split(",")]
            cores.append({"species": species, "team_count": int(team_count), "pct": float(pct)})
    return cores


def main():
    markdown = _RAW_PATH.read_text(encoding="utf-8")
    cores = parse(markdown)
    _OUT_PATH.write_text(json.dumps(cores, indent=1), encoding="utf-8")
    print(f"wrote {_OUT_PATH} ({len(cores)} cores)")
    for c in cores:
        print(f"  {len(c['species'])}-core: {c['species']} ({c['team_count']} teams, {c['pct']}%)")


if __name__ == "__main__":
    main()
