"""Tracks which replay ids are already folded into the main
replays/examples/<format>.jsonl training corpus, so a periodic re-scrape
can turn ONLY the newly-cached raw replays into examples
(reconstruct.py --new-only -> <format>new.jsonl) instead of re-running a
full reconstruct + full retrain every time a handful of new games land.

Single JSON file, {format_id: [replay_id, ...]}. Two writers:
  - reconstruct.py's default (full) mode stamps it to exactly "every raw
    id that format currently has cached", since that mode always
    regenerates <format>.jsonl from 100% of replays/raw/<format>/.
  - merge_new.py adds a format's newly-merged ids after folding
    <format>new.jsonl into <format>.jsonl.
reconstruct.py --new-only reads it (never writes) to compute the delta.

If the file doesn't exist yet, every format's "known" set is treated as
CURRENT replays/raw/<format>/ contents - correct for this project's
actual history (imitation_v3.pt was trained from a full reconstruct over
everything in raw/ at the time), and it means no manual bootstrap step is
needed the first time this tooling runs.
"""

import json
from pathlib import Path

_HERE = Path(__file__).resolve().parent
RAW_DIR = _HERE / "raw"
MANIFEST_PATH = _HERE / "trained_ids.json"


def load() -> dict[str, list[str]]:
    if not MANIFEST_PATH.exists():
        return {}
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def save(manifest: dict[str, list[str]]) -> None:
    ordered = {fmt: sorted(set(ids)) for fmt, ids in manifest.items()}
    MANIFEST_PATH.write_text(json.dumps(ordered, indent=1, sort_keys=True), encoding="utf-8")


def raw_ids(format_id: str) -> set[str]:
    """Every replay id currently cached under replays/raw/<format_id>/."""
    fmt_dir = RAW_DIR / format_id
    if not fmt_dir.exists():
        return set()
    return {p.stem for p in fmt_dir.glob("*.json")}


def known_ids(manifest: dict[str, list[str]], format_id: str) -> set[str]:
    """Ids already considered 'trained on' for this format. Falls back to
    the full current raw cache when the format has no manifest entry yet
    (first-ever run - see module docstring)."""
    if format_id in manifest:
        return set(manifest[format_id])
    return raw_ids(format_id)


def new_ids(manifest: dict[str, list[str]], format_id: str) -> set[str]:
    """raw ids not yet marked as trained-on for this format."""
    return raw_ids(format_id) - known_ids(manifest, format_id)
