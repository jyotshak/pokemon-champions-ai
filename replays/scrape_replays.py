"""Scrape Pokemon Showdown replays for the Champions Reg M-B format(s)
into a local raw cache - the first stage of the replay -> imitation-net
pipeline (docs/solver_design.md, the value/policy-net direction).

Two public, no-auth endpoints:
  search.json?format=<fmt>&page=<n>  -> paginated list (51/page) of
      {uploadtime, id, format, players, rating, private, password}
  <id>.json                          -> the full replay: the same
      metadata PLUS "log" (the raw Showdown protocol) - so one saved
      file per replay carries everything (rating/players/winner/turns,
      and for Bo3 the open team sheets via |showteam|).

Design mirrors belief/usage_data/fetch_*.py (a data-source layer, kept
out of model/ per the architecture-goal memory): rating-filtered at the
cheap metadata stage BEFORE downloading logs, resumable (skips ids
already cached), and polite (a small delay between requests). The raw
cache (replays/raw/) is gitignored - it is a reproducible download, not
source.

Run from the project root, e.g.:
  python -m replays.scrape_replays --format both --min-rating 1200 --max-pages 40
  python -m replays.scrape_replays --format bo3 --min-rating 0 --max-pages 5
  python -m replays.scrape_replays --sort rating --max-pages 100   # higher-floor corpus

Downloads are id-keyed and skip-if-cached (download_replay), so re-running
this periodically (with either --sort) against an already-populated
replays/raw/ only ever adds genuinely new replays - safe to schedule
regularly. See replays/trained_manifest.py + reconstruct.py's --new-only
for turning freshly-scraped raw replays into training examples without
touching the ones already folded into the main corpus.
"""

import argparse
import json
import time
import urllib.request
from pathlib import Path

_HERE = Path(__file__).resolve().parent
RAW_DIR = _HERE / "raw"

# The two ladder formats. Bo3 additionally carries |showteam| open sheets
# (full item/ability/move/nature ground truth for both teams).
FORMATS = {
    "bo1": "gen9championsvgc2026regmb",
    "bo3": "gen9championsvgc2026regmbbo3",
}
_SEARCH = "https://replay.pokemonshowdown.com/search.json?format={fmt}&page={page}"
_REPLAY = "https://replay.pokemonshowdown.com/{id}.json"
_UA = "champions-solver-research/0.1 (personal replay study)"


def _get(url: str, timeout: float = 20.0) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def list_page(format_id: str, page: int, sort: str = "date") -> list[dict]:
    """One search page of replay metadata (up to 51). Empty list = past
    the last page (the natural stop condition). sort='rating' asks the
    same search.json endpoint the site's own UI uses for a rating-sorted
    listing (confirmed live 2026-07-21: page 1 runs ~1700+, monotonically
    descending) - a much higher floor than the default upload-time order,
    which mixes in a lot of unrated/casual games."""
    url = _SEARCH.format(fmt=format_id, page=page)
    if sort == "rating":
        url += "&sort=rating"
    return json.loads(_get(url).decode("utf-8"))


def iter_replay_meta(format_id: str, min_rating: int, max_pages: int, sleep: float, sort: str = "date"):
    """Yield replay metadata dicts across pages, keeping only public,
    rating>=min_rating games. Stops at max_pages or the first empty page.
    Filtering here (metadata) means we never download a log we'd discard.

    sort='rating': results arrive rating-descending, so once a REAL rating
    dips below the floor every later entry (this page and all following
    pages) is guaranteed to be too, and we can stop early instead of
    paging all the way to 100 for nothing. Only a perf optimization - the
    min_rating check below still applies unconditionally either way, so a
    wrong assumption here would cost extra requests, never a correctness
    bug."""
    for page in range(1, max_pages + 1):
        try:
            entries = list_page(format_id, page, sort=sort)
        except Exception as e:  # transient network / rate hiccup - report, stop this format
            print(f"  [page {page}] fetch failed ({e}); stopping this format", flush=True)
            return
        if not entries:
            return
        for e in entries:
            if e.get("private") or e.get("password"):
                continue
            rating = e.get("rating")
            # min_rating>0: keep only rated games at/above the floor. floor
            # of 0: cache everything, INCLUDING unrated (rating=null) games
            # - the raw cache stays maximally inclusive so we can subset any
            # way later (rating, team popularity, ...); rating is preserved
            # per-record for a train-time filter. Unrated Bo3 games still
            # carry open sheets, valuable for the belief model regardless.
            if min_rating > 0 and (rating is None or rating < min_rating):
                if sort == "rating" and rating is not None:
                    return   # monotonically descending -> nothing further can qualify
                continue
            yield e
        time.sleep(sleep)


def download_replay(replay_id: str, out_dir: Path, sleep: float) -> bool:
    """Save <id>.json verbatim (metadata + log). Returns False if already
    cached (resumable) or on failure, True if freshly written."""
    out_path = out_dir / f"{replay_id}.json"
    if out_path.exists():
        return False
    try:
        raw = _get(_REPLAY.format(id=replay_id))
    except Exception as e:
        print(f"  [dl {replay_id}] failed ({e})", flush=True)
        return False
    out_path.write_bytes(raw)
    time.sleep(sleep)
    return True


def scrape(format_key: str, min_rating: int, max_pages: int, sleep: float, sort: str = "date") -> dict:
    format_id = FORMATS[format_key]
    out_dir = RAW_DIR / format_id
    out_dir.mkdir(parents=True, exist_ok=True)
    seen = kept = downloaded = 0
    for meta in iter_replay_meta(format_id, min_rating, max_pages, sleep, sort=sort):
        seen += 1
        kept += 1
        if download_replay(meta["id"], out_dir, sleep):
            downloaded += 1
        if kept % 25 == 0:
            print(f"  [{format_key}] kept {kept}, downloaded {downloaded} new...", flush=True)
    total_cached = len(list(out_dir.glob("*.json")))
    print(f"[{format_key}] {format_id}: kept {kept} (rating>={min_rating}, sort={sort}), "
          f"{downloaded} newly downloaded, {total_cached} total cached in {out_dir}", flush=True)
    return {"format": format_id, "kept": kept, "downloaded": downloaded, "cached": total_cached}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--format", choices=["bo1", "bo3", "both"], default="both")
    ap.add_argument("--min-rating", type=int, default=1200,
                    help="skip replays rated below this (Bo3 unrated games have rating=null and are skipped)")
    ap.add_argument("--max-pages", type=int, default=40, help="search pages per format (51 replays/page)")
    ap.add_argument("--sleep", type=float, default=0.3, help="seconds between requests (be polite)")
    ap.add_argument("--sort", choices=["date", "rating"], default="date",
                    help="'rating' pulls a much higher-floor corpus (page 1 ~1700+, descending) "
                         "and can early-stop once ratings drop below --min-rating")
    args = ap.parse_args()

    keys = ["bo1", "bo3"] if args.format == "both" else [args.format]
    for k in keys:
        scrape(k, args.min_rating, args.max_pages, args.sleep, sort=args.sort)


if __name__ == "__main__":
    main()
