"""Fetches per-species usage data from Pikalytics' AI-optimized endpoint
(https://www.pikalytics.com/ai/pokedex/battledataregmbs3/{species}) for
every champions-legal BASE species (mega formes fold into their base
species' page — a mega stone just shows up as a top item, e.g. Charizard
carries "Charizardite Y: 95.4%"; confirmed against the live site, not
assumed) and saves the raw markdown responses to disk, one file per
species, for the parser (parse_pikalytics.py) to consume separately.

Explicitly permitted by pikalytics.com/robots.txt, which names ClaudeBot/
claude-web/anthropic-ai and calls out the /ai/ path specifically as an
AI-optimized data endpoint. Rate-limited out of politeness regardless.

Run from the project root: python -m belief.usage_data.fetch_pikalytics
"""

import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent
_RAW_DIR = Path(__file__).resolve().parent / "raw_battledataregmbs3"
_MEGA_STONES = json.loads((_ROOT / "reference" / "mega_stones.json").read_text(encoding="utf-8"))
_SPECIES_DATA = json.loads((_ROOT / "reference" / "species_data.json").read_text(encoding="utf-8"))
_DISPLAY_NAMES = json.loads((_ROOT / "reference" / "species_display_names.json").read_text(encoding="utf-8"))

BASE_URL = "https://www.pikalytics.com/ai/pokedex/battledataregmbs3/"
DELAY_SECONDS = 0.3
USER_AGENT = "Mozilla/5.0 (compatible; pokemon-champions-research-bot)"


# Non-mega mid-battle transformations that Pikalytics also folds into
# their base species' page (confirmed: Aegislash-Blade 404s on its own,
# same shape as a mega - it's the base's in-battle King's Shield/attack
# transformation, not a separately brought Pokemon). Castform's weather
# formes are the same idea but not worth adding here: negligible usage,
# explicitly left to the fallback layer instead of chased further.
_EXPLICIT_FOLD_TO_BASE = {"aegislashblade": "aegislash"}


def base_species_ids() -> list[str]:
    """All 314 champions-legal species, deduplicated to unique Pikalytics
    query targets: mega formes map to their base species (see module
    docstring); every non-mega species queries under its own id.
    """
    forme_to_base = {}
    for mapping in _MEGA_STONES.values():
        for base, forme in mapping.items():
            forme_to_base[forme] = base
    forme_to_base.update(_EXPLICIT_FOLD_TO_BASE)
    targets = {forme_to_base.get(sp, sp) for sp in _SPECIES_DATA}
    return sorted(targets)


def _species_to_pikalytics_name(species_id: str) -> str:
    """Single-word species ids (garchomp, incineroar...) happen to match
    Pikalytics' slugs directly, which is what made the first test batch
    look fine — but multi-word formes need the real hyphenated display
    name (Rotom-Wash, not rotomwash; Arcanine-Hisui, not arcaninehisui).
    Getting this wrong doesn't 404 - Pikalytics returns HTTP 200 with an
    empty "N/A" template, which silently looks like "no data" instead of
    "wrong URL" (found via rotomwash/tauros coming back suspiciously
    empty despite being real, commonly-used mons). Use the authoritative
    name straight from the vendored dex (reference/species_display_names.
    json, extracted from data/pokedex.ts) rather than guessing
    hyphenation rules ourselves.
    """
    return _DISPLAY_NAMES.get(species_id, species_id)


def fetch_one(species_id: str) -> str:
    # quote(): display names like "Mr. Rime" contain characters (space,
    # period) that aren't valid unencoded in a URL path segment.
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
