"""Fetches per-species pages from Pikalytics' AI-optimized endpoint under
the `championstournaments` category (unlike `battledataregmbs3`'s ladder
data, these pages report a real overall "Usage" % per species - confirmed
by inspecting both: battledataregmbs3/Garchomp's Quick Info table shows
"Usage: N/A", championstournaments/Garchomp's shows "Usage: 38%", matching
the category-root "Best 50 Pokemon by Usage" table already fetched into
raw_team_cores.md). That top-50 list alone only covers 50 of the 174
distinct species actually appearing across the 555 scraped team_sheet
teams, so this fetches all ~237 champions-legal base species for complete
coverage, not just the top 50 - reused for team_popularity.py's aggregate
popularity score, and reusable for anything else that wants real species-
level popularity later.

Reuses base_species_ids()/_species_to_pikalytics_name() from
fetch_pikalytics.py directly (same species-folding logic, same site,
different category - no reason to re-derive it a second time).

Run from the project root: python -m belief.usage_data.fetch_tournament_usage
"""

import time
import urllib.parse
import urllib.request
from pathlib import Path

from belief.usage_data.fetch_pikalytics import _species_to_pikalytics_name, base_species_ids

_RAW_DIR = Path(__file__).resolve().parent / "raw_championstournaments"

BASE_URL = "https://www.pikalytics.com/ai/pokedex/championstournaments/"
DELAY_SECONDS = 0.3
USER_AGENT = "Mozilla/5.0 (compatible; pokemon-champions-research-bot)"


def fetch_one(species_id: str) -> str:
    url = BASE_URL + urllib.parse.quote(_species_to_pikalytics_name(species_id))
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read().decode("utf-8")


def main():
    _RAW_DIR.mkdir(parents=True, exist_ok=True)
    targets = base_species_ids()
    print(f"{len(targets)} unique base-species query targets")

    fetched, skipped, failed = 0, 0, []
    for i, species_id in enumerate(targets):
        out_path = _RAW_DIR / f"{species_id}.md"
        if out_path.exists():
            skipped += 1
            continue
        try:
            content = fetch_one(species_id)
            out_path.write_text(content, encoding="utf-8")
            fetched += 1
        except Exception as e:
            failed.append((species_id, repr(e)))
        if (i + 1) % 25 == 0:
            print(f"  {i + 1}/{len(targets)} processed ({fetched} fetched, {skipped} cached, {len(failed)} failed)")
        time.sleep(DELAY_SECONDS)

    print(f"\nDone: {fetched} fetched, {skipped} already cached, {len(failed)} failed")
    for species_id, err in failed[:20]:
        print(f"  FAILED {species_id}: {err}")


if __name__ == "__main__":
    main()
