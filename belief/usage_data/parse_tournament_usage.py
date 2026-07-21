"""Parses the raw championstournaments per-species pages (fetched by
fetch_tournament_usage.py) into a simple species -> real usage %
lookup (tournament_usage.json), for team_popularity.py's aggregate team
popularity score. Tolerant of "N/A" (species with too little tournament
data to report anything meaningful - same convention as parse_pikalytics.
py's per-species parser).

Run from the project root: python -m belief.usage_data.parse_tournament_usage
"""

import json
import re
from pathlib import Path

_RAW_DIR = Path(__file__).resolve().parent / "raw_championstournaments"
_OUT_PATH = Path(__file__).resolve().parent / "tournament_usage.json"

_USAGE = re.compile(r"\*\*Usage\*\*\s*\|\s*([\d.]+)%")
_WIN_RATE = re.compile(r"\*\*Win Rate\*\*\s*\|\s*([\d.]+)%")


def parse_one(markdown: str) -> dict:
    usage_m = _USAGE.search(markdown)
    win_rate_m = _WIN_RATE.search(markdown)
    return {
        "usage_pct": float(usage_m.group(1)) if usage_m else None,
        "win_rate": float(win_rate_m.group(1)) if win_rate_m else None,
    }


def main():
    files = sorted(_RAW_DIR.glob("*.md"))
    print(f"parsing {len(files)} cached responses")

    parsed = {}
    no_usage = []
    for f in files:
        species_id = f.stem
        data = parse_one(f.read_text(encoding="utf-8"))
        parsed[species_id] = data
        if data["usage_pct"] is None:
            no_usage.append(species_id)

    _OUT_PATH.write_text(json.dumps(parsed, indent=1, sort_keys=True), encoding="utf-8")
    print(f"wrote {_OUT_PATH} ({len(parsed)} species)")
    print(f"{len(no_usage)} species with no usage % reported (fallback territory): {no_usage[:20]}"
          + (" ..." if len(no_usage) > 20 else ""))


if __name__ == "__main__":
    main()
