"""Parses the raw markdown Pikalytics AI-endpoint responses (fetched by
fetch_pikalytics.py) into structured per-species usage data.

Deliberately tolerant of the site's own known quirks (found by inspecting
real responses, not assumed): "N/A" win rate/record for some species,
"undefined%" on every teammate entry (the % is broken on their end - we
keep the ranked name list, drop the percentage), and an empty nature name
in the EV-spread sentence (`a **** nature` - keep the spread numbers,
nature comes back as None). A species with too little tournament data to
report anything meaningful returns mostly-empty fields, not an error —
that's exactly the case belief/usage_data/fallback.py's global-popularity
fallback exists for.

Run from the project root: python -m belief.usage_data.parse_pikalytics
"""

import json
import re
from pathlib import Path

from belief.species_folding import to_id as _to_id

_RAW_DIR = Path(__file__).resolve().parent / "raw_battledataregmbs3"
_OUT_PATH = Path(__file__).resolve().parent / "usage_stats.json"

_PCT_LINE = re.compile(r"-\s*\*\*(.+?)\*\*:\s*([\d.]+|undefined)%")
_SECTION = re.compile(r"^## (.+)$", re.M)
_RECORD = re.compile(r"\*\*Record\*\*\s*\|\s*([\d]+)-([\d]+)-([\d]+)")
_WIN_RATE = re.compile(r"\*\*Win Rate\*\*\s*\|\s*([\d.]+)%")
_EV_SPREAD = re.compile(
    r"a \*\*(.*?)\*\* nature with an EV spread of `([\d/]+)`\. This configuration accounts for ([\d.]+)%"
)


def _section_body(markdown: str, heading: str) -> str:
    """Text between `## {heading}` and the next `##` heading (or end)."""
    m = re.search(rf"^## {re.escape(heading)}\s*$", markdown, re.M)
    if not m:
        return ""
    rest = markdown[m.end():]
    nxt = _SECTION.search(rest)
    return rest[: nxt.start()] if nxt else rest


def _pct_dict(body: str) -> dict[str, float]:
    out = {}
    for name, pct in _PCT_LINE.findall(body):
        if pct == "undefined":
            continue
        out[_to_id(name)] = float(pct)
    return out


def _teammate_list(body: str) -> list[str]:
    return [_to_id(name) for name, _ in _PCT_LINE.findall(body)]


def parse_one(markdown: str) -> dict:
    win_rate_m = _WIN_RATE.search(markdown)
    record_m = _RECORD.search(markdown)
    ev_m = _EV_SPREAD.search(markdown)

    result = {
        "win_rate": float(win_rate_m.group(1)) if win_rate_m else None,
        "record": [int(x) for x in record_m.groups()] if record_m else None,
        "moves": _pct_dict(_section_body(markdown, "Common Moves")),
        "abilities": _pct_dict(_section_body(markdown, "Common Abilities")),
        "items": _pct_dict(_section_body(markdown, "Common Items")),
        "teammates": _teammate_list(_section_body(markdown, "Common Teammates")),
        "top_spread": None,
    }
    if ev_m:
        nature, spread, pct = ev_m.groups()
        result["top_spread"] = {
            "nature": nature.strip() or None,
            "points": [int(x) for x in spread.split("/")],  # HP/Atk/Def/SpA/SpD/Spe
            "pct": float(pct),
        }
    return result


def main():
    files = sorted(_RAW_DIR.glob("*.md"))
    print(f"parsing {len(files)} cached responses")

    parsed = {}
    empties = []
    for f in files:
        species_id = f.stem
        data = parse_one(f.read_text(encoding="utf-8"))
        parsed[species_id] = data
        if not data["moves"] and not data["items"]:
            empties.append(species_id)

    _OUT_PATH.write_text(json.dumps(parsed, indent=1, sort_keys=True), encoding="utf-8")
    print(f"wrote {_OUT_PATH} ({len(parsed)} species)")
    print(f"{len(empties)} species with no usable moves/items data (fallback territory): {empties[:20]}"
          + (" ..." if len(empties) > 20 else ""))


if __name__ == "__main__":
    main()
