"""Fold replays/examples/<fmt>new.jsonl (produced by `python -m
replays.reconstruct --new-only`) into the main <fmt>.jsonl corpus and mark
those replay ids as trained-on in trained_manifest.py.

Run this AFTER a training run on the new-only file has been checked and
kept (e.g. `python -m model.train --resume imitation_v3.pt --paths
"replays/examples/*new.jsonl" --out imitation_v4.pt`) - merging first
would make a later `reconstruct.py --new-only` see those replays as
already-trained even if the run on them was discarded.

Idempotent: a format with no <fmt>new.jsonl (nothing new since the last
merge) is silently skipped. Safe to run with an empty/all-duplicate new
file - both merge to nothing.

Run: python -m replays.merge_new
"""

import json
from pathlib import Path

from replays import trained_manifest

_HERE = Path(__file__).resolve().parent
EXAMPLES_DIR = _HERE / "examples"


def merge_one(fmt_dir: str) -> tuple[int, int]:
    """Append <fmt>new.jsonl into <fmt>.jsonl, update the manifest, remove
    the new file (+ its attempted_ids sidecar, if any). Returns (examples
    merged, ids newly marked known) - both 0 if nothing to do."""
    new_path = EXAMPLES_DIR / f"{fmt_dir}new.jsonl"
    sidecar_path = EXAMPLES_DIR / f"{fmt_dir}new.attempted_ids.json"
    if not new_path.exists() and not sidecar_path.exists():
        return 0, 0

    lines = new_path.read_text(encoding="utf-8").splitlines(keepends=True) if new_path.exists() else []
    ids = {json.loads(line)["id"] for line in lines}
    # The attempted set (reconstruct.py --new-only's sidecar) also covers
    # replays that produced zero examples (forfeits/empty logs) - fold those
    # in too so they're marked known and never retried, even though they
    # contributed nothing to <fmt>.jsonl. Falls back to just `ids` if the
    # sidecar is missing (e.g. a hand-built new.jsonl in a test).
    if sidecar_path.exists():
        ids |= set(json.loads(sidecar_path.read_text(encoding="utf-8")))

    if lines:
        main_path = EXAMPLES_DIR / f"{fmt_dir}.jsonl"
        with open(main_path, "a", encoding="utf-8") as f:
            f.writelines(lines)

    if ids:
        manifest = trained_manifest.load()
        known = trained_manifest.known_ids(manifest, fmt_dir)
        manifest[fmt_dir] = sorted(known | ids)
        trained_manifest.save(manifest)

    if new_path.exists():
        new_path.unlink()
    if sidecar_path.exists():
        sidecar_path.unlink()
    return len(lines), len(ids)


def main():
    # A format can have a *new.jsonl (real examples), a *new.attempted_ids.json
    # sidecar only (every candidate this round turned out empty), or both -
    # union both patterns so an all-empty batch still gets marked known
    # instead of being silently skipped.
    from_jsonl = {p.name[:-len("new.jsonl")] for p in EXAMPLES_DIR.glob("*new.jsonl")}
    from_sidecar = {p.name[:-len("new.attempted_ids.json")] for p in EXAMPLES_DIR.glob("*new.attempted_ids.json")}
    fmt_dirs = sorted(from_jsonl | from_sidecar)
    if not fmt_dirs:
        print("nothing to merge (no *new.jsonl / *new.attempted_ids.json files in replays/examples/)")
        return
    for fmt_dir in fmt_dirs:
        n_examples, n_ids = merge_one(fmt_dir)
        if n_ids:
            print(f"[{fmt_dir}] merged {n_examples} examples into {fmt_dir}.jsonl, "
                  f"marked {n_ids} replay id(s) known in trained_ids.json")
        else:
            print(f"[{fmt_dir}] nothing to merge")


if __name__ == "__main__":
    main()
