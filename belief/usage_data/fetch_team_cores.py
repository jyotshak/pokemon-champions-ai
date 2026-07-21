"""Fetches Pikalytics' championstournaments category-root AI markdown page
(https://www.pikalytics.com/ai/pokedex/championstournaments) — unlike
fetch_pikalytics.py's per-species pages, this is the category root itself,
which carries a "Common Team Cores" section (top-5 ranked 2/3/4-Pokemon
combos with real tournament team counts and usage %, e.g. "Archaludon,
Pelipper, Swampert-Mega | 1271 teams | 12.2%") that no per-species page has.
A single one-shot page, so unlike fetch_pikalytics.py there's no per-
species loop or rate limiting to do.

Same robots.txt permission as fetch_pikalytics.py (pikalytics.com allows
ClaudeBot/claude-web/anthropic-ai and calls out /ai/ specifically as an
AI-optimized data endpoint).

Run from the project root: python -m belief.usage_data.fetch_team_cores
"""

import urllib.request
from pathlib import Path

_OUT_PATH = Path(__file__).resolve().parent / "raw_team_cores.md"

URL = "https://www.pikalytics.com/ai/pokedex/championstournaments"
USER_AGENT = "Mozilla/5.0 (compatible; pokemon-champions-research-bot)"


def main():
    req = urllib.request.Request(URL, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=20) as resp:
        content = resp.read().decode("utf-8")
    _OUT_PATH.write_text(content, encoding="utf-8")
    print(f"wrote {_OUT_PATH} ({len(content)} bytes)")


if __name__ == "__main__":
    main()
