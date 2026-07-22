"""Fixture test for replays/trained_manifest.py: the id-manifest that lets
reconstruct.py --new-only and merge_new.py tell "already trained on" apart
from "freshly scraped" without touching the real replays/ cache.

Run from the project root: python -m replays.test_trained_manifest
"""

import shutil
import tempfile
from pathlib import Path

from replays import trained_manifest

failures = []


def check(name, ok, detail=""):
    print(f"  {name} [{'ok' if ok else 'FAIL'}]{' ' + str(detail) if detail and not ok else ''}")
    if not ok:
        failures.append(name)


tmp = Path(tempfile.mkdtemp(prefix="trained_manifest_test_"))
orig_raw_dir, orig_manifest_path = trained_manifest.RAW_DIR, trained_manifest.MANIFEST_PATH
try:
    trained_manifest.RAW_DIR = tmp / "raw"
    trained_manifest.MANIFEST_PATH = tmp / "trained_ids.json"

    fmt = "gen9championsvgc2026regmb"
    fmt_dir = trained_manifest.RAW_DIR / fmt
    fmt_dir.mkdir(parents=True)
    for rid in ("a-1", "a-2", "a-3"):
        (fmt_dir / f"{rid}.json").write_text("{}", encoding="utf-8")

    print("no manifest file yet: load() is empty, raw_ids() reads the cache directly")
    m0 = trained_manifest.load()
    check("load() returns {} when the file doesn't exist", m0 == {}, m0)
    check("raw_ids() lists the 3 cached ids", trained_manifest.raw_ids(fmt) == {"a-1", "a-2", "a-3"})

    print("\nfirst-ever run (no manifest entry for this format): known_ids falls back to "
          "the FULL current raw cache - correct for this project's actual history "
          "(the current corpus was already fully reconstructed before this manifest existed)")
    known = trained_manifest.known_ids(m0, fmt)
    check("known_ids falls back to raw_ids when format is unmapped", known == {"a-1", "a-2", "a-3"})
    check("new_ids is empty on first run (nothing 'new' relative to the existing cache)",
          trained_manifest.new_ids(m0, fmt) == set())

    print("\nsave()/load() round-trip")
    trained_manifest.save({fmt: ["a-1", "a-2"]})
    check("manifest file was written", trained_manifest.MANIFEST_PATH.exists())
    m1 = trained_manifest.load()
    check("round-trips the saved ids", m1.get(fmt) == ["a-1", "a-2"], m1)

    print("\nwith an explicit (partial) manifest entry, new_ids reports exactly the delta - "
          "simulates a fresh scrape adding a-3 after a-1/a-2 were already trained on")
    check("known_ids uses the manifest, not the raw fallback, once mapped",
          trained_manifest.known_ids(m1, fmt) == {"a-1", "a-2"})
    check("new_ids == {a-3}", trained_manifest.new_ids(m1, fmt) == {"a-3"})

    print("\na genuinely fresh scrape (a-4, a-5 land in raw/) grows the delta accordingly")
    (fmt_dir / "a-4.json").write_text("{}", encoding="utf-8")
    (fmt_dir / "a-5.json").write_text("{}", encoding="utf-8")
    check("new_ids now == {a-3, a-4, a-5}", trained_manifest.new_ids(m1, fmt) == {"a-3", "a-4", "a-5"})

    print("\nsave() de-dupes and sorts")
    trained_manifest.save({fmt: ["a-2", "a-1", "a-1", "a-3"]})
    m2 = trained_manifest.load()
    check("de-duped and sorted", m2.get(fmt) == ["a-1", "a-2", "a-3"], m2)

    print("\na format with no cached raw replays at all -> empty, not an error")
    check("raw_ids on a nonexistent format dir is empty", trained_manifest.raw_ids("nope") == set())
    check("new_ids on a nonexistent format dir is empty", trained_manifest.new_ids(m2, "nope") == set())
finally:
    trained_manifest.RAW_DIR, trained_manifest.MANIFEST_PATH = orig_raw_dir, orig_manifest_path
    shutil.rmtree(tmp, ignore_errors=True)

print(f"\n{'PASS' if not failures else 'FAIL: ' + ', '.join(failures)}")
