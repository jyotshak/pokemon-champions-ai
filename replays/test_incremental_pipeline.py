"""End-to-end fixture test for the incremental scrape/reconstruct/merge
flow: reconstruct.py's --new-only path (via reconstruct_format_dir +
trained_manifest) and merge_new.py, wired together the way a real
"weekly re-scrape" cycle would use them, on tiny hand-built replay logs
so no network/real cache is touched.

Simulates: 2 replays already trained on (id-1, id-2) -> a fresh scrape
adds id-3 -> --new-only reconstructs ONLY id-3 into <fmt>new.jsonl ->
merge_new.py folds it into <fmt>.jsonl and updates the manifest -> a
second --new-only run (nothing new) reconstructs nothing.

Run from the project root: python -m replays.test_incremental_pipeline
"""

import json
import shutil
import tempfile
from pathlib import Path

from replays import merge_new, reconstruct, trained_manifest

failures = []


def check(name, ok, detail=""):
    print(f"  {name} [{'ok' if ok else 'FAIL'}]{' ' + str(detail) if detail and not ok else ''}")
    if not ok:
        failures.append(name)


def _log(win_name: str) -> str:
    return "\n".join([
        "|player|p1|Alice|1|1500", "|player|p2|Bob|2|1400",
        "|poke|p1|Kangaskhan, F|", "|poke|p2|Incineroar, M|",
        "|switch|p1a: Kangaskhan|Kangaskhan, L50, F|100/100",
        "|switch|p2a: Incineroar|Incineroar, L50, M|100/100",
        "|turn|1",
        "|move|p1a: Kangaskhan|Fake Out|p2a: Incineroar",
        "|move|p2a: Incineroar|Flare Blitz|p1a: Kangaskhan",
        "|-damage|p1a: Kangaskhan|40/100",
        f"|win|{win_name}",
    ])


def _write_raw(fmt_dir: Path, replay_id: str) -> None:
    data = {"id": replay_id, "format": "[Gen 9 Champions] VGC 2026 Reg M-B",
            "players": ["Alice", "Bob"], "rating": 1450, "log": _log("Alice")}
    (fmt_dir / f"{replay_id}.json").write_text(json.dumps(data), encoding="utf-8")


tmp = Path(tempfile.mkdtemp(prefix="incremental_pipeline_test_"))
originals = {
    "reconstruct.RAW_DIR": reconstruct.RAW_DIR, "reconstruct.EXAMPLES_DIR": reconstruct.EXAMPLES_DIR,
    "merge_new.EXAMPLES_DIR": merge_new.EXAMPLES_DIR,
    "trained_manifest.RAW_DIR": trained_manifest.RAW_DIR, "trained_manifest.MANIFEST_PATH": trained_manifest.MANIFEST_PATH,
}
try:
    raw_dir, examples_dir = tmp / "raw", tmp / "examples"
    examples_dir.mkdir(parents=True)
    fmt = "gen9championsvgc2026regmb"
    fmt_raw = raw_dir / fmt
    fmt_raw.mkdir(parents=True)

    reconstruct.RAW_DIR = raw_dir
    reconstruct.EXAMPLES_DIR = examples_dir
    merge_new.EXAMPLES_DIR = examples_dir
    trained_manifest.RAW_DIR = raw_dir
    trained_manifest.MANIFEST_PATH = tmp / "trained_ids.json"

    print("step 1: two replays already 'trained on' - a full reconstruct + manifest stamp")
    _write_raw(fmt_raw, "gen9championsvgc2026regmb-1")
    _write_raw(fmt_raw, "gen9championsvgc2026regmb-2")
    examples = reconstruct.reconstruct_format_dir(fmt)
    (examples_dir / f"{fmt}.jsonl").write_text("".join(json.dumps(e) + "\n" for e in examples), encoding="utf-8")
    trained_manifest.save({fmt: sorted(trained_manifest.raw_ids(fmt))})
    main_lines_before = (examples_dir / f"{fmt}.jsonl").read_text(encoding="utf-8").splitlines()
    check("main corpus has examples from both seed replays",
          {json.loads(l)["id"] for l in main_lines_before} == {"gen9championsvgc2026regmb-1", "gen9championsvgc2026regmb-2"})
    check("manifest knows both seed ids", trained_manifest.load()[fmt] == ["gen9championsvgc2026regmb-1", "gen9championsvgc2026regmb-2"])

    print("\nstep 2: a fresh scrape adds a 3rd replay - --new-only must touch ONLY it")
    _write_raw(fmt_raw, "gen9championsvgc2026regmb-3")
    manifest = trained_manifest.load()
    fresh = trained_manifest.new_ids(manifest, fmt)
    check("new_ids identifies exactly the 3rd replay", fresh == {"gen9championsvgc2026regmb-3"}, fresh)
    new_examples = reconstruct.reconstruct_format_dir(fmt, only_ids=fresh)
    check("new-only reconstruct produced examples", len(new_examples) > 0)
    check("new-only reconstruct touched only the 3rd replay",
          {e["id"] for e in new_examples} == {"gen9championsvgc2026regmb-3"})
    new_path = examples_dir / f"{fmt}new.jsonl"
    new_path.write_text("".join(json.dumps(e) + "\n" for e in new_examples), encoding="utf-8")
    check("main corpus file is untouched by --new-only (still just the 2 seed replays)",
          {json.loads(l)["id"] for l in (examples_dir / f'{fmt}.jsonl').read_text(encoding='utf-8').splitlines()}
          == {"gen9championsvgc2026regmb-1", "gen9championsvgc2026regmb-2"})

    print("\nstep 3: merge_new.py folds the new batch in and advances the manifest")
    n_examples, n_ids = merge_new.merge_one(fmt)
    check("merge_one reports the merged example count", n_examples == len(new_examples), n_examples)
    check("merge_one reports 1 id newly marked known", n_ids == 1, n_ids)
    check("<fmt>new.jsonl is removed after merging", not new_path.exists())
    merged_ids = {json.loads(l)["id"] for l in (examples_dir / f"{fmt}.jsonl").read_text(encoding="utf-8").splitlines()}
    check("main corpus now includes all 3 replays", merged_ids == {
        "gen9championsvgc2026regmb-1", "gen9championsvgc2026regmb-2", "gen9championsvgc2026regmb-3"}, merged_ids)
    check("manifest now includes the 3rd replay too", trained_manifest.load()[fmt] == sorted([
        "gen9championsvgc2026regmb-1", "gen9championsvgc2026regmb-2", "gen9championsvgc2026regmb-3"]))

    print("\nstep 4: a second --new-only run (nothing new scraped) finds nothing to do")
    manifest2 = trained_manifest.load()
    fresh2 = trained_manifest.new_ids(manifest2, fmt)
    check("no new ids on a repeat run", fresh2 == set(), fresh2)

    print("\nstep 5: merge_new.py is idempotent when there's nothing to merge")
    check("merge_one returns (0, 0) when neither the new file nor sidecar exist", merge_new.merge_one(fmt) == (0, 0))

    print("\nstep 6: merge_new.main() skips formats with no *new.jsonl/*attempted_ids cleanly (no crash)")
    merge_new.main()  # should just print "nothing to merge" and return

    print("\nstep 7: a replay that reconstructs to ZERO examples (e.g. an instant "
          "forfeit with no real turns) must still be marked known via the "
          "attempted_ids sidecar, not retried forever")
    empty_log = "\n".join(["|player|p1|Alice|1|1500", "|player|p2|Bob|2|1400", "|win|Alice"])
    data = {"id": "gen9championsvgc2026regmb-4", "format": "[Gen 9 Champions] VGC 2026 Reg M-B",
            "players": ["Alice", "Bob"], "rating": 1450, "log": empty_log}
    (fmt_raw / "gen9championsvgc2026regmb-4.json").write_text(json.dumps(data), encoding="utf-8")
    manifest3 = trained_manifest.load()
    fresh3 = trained_manifest.new_ids(manifest3, fmt)
    check("the empty-log replay is detected as new", fresh3 == {"gen9championsvgc2026regmb-4"}, fresh3)
    empty_examples = reconstruct.reconstruct_format_dir(fmt, only_ids=fresh3)
    check("it genuinely produces zero examples (nothing to decide, no turns)", empty_examples == [])
    sidecar_path = examples_dir / f"{fmt}new.attempted_ids.json"
    sidecar_path.write_text(json.dumps(sorted(fresh3)), encoding="utf-8")
    check("no <fmt>new.jsonl was written (nothing to write)", not (examples_dir / f"{fmt}new.jsonl").exists())
    n_examples2, n_ids2 = merge_new.merge_one(fmt)
    check("merge_one merges 0 examples but marks 1 id known via the sidecar",
          (n_examples2, n_ids2) == (0, 1), (n_examples2, n_ids2))
    check("attempted_ids sidecar is cleaned up after merging", not sidecar_path.exists())
    manifest4 = trained_manifest.load()
    check("the empty-log replay is now known (won't be retried)",
          "gen9championsvgc2026regmb-4" in manifest4[fmt])
    check("a follow-up --new-only run finds nothing new",
          trained_manifest.new_ids(manifest4, fmt) == set())
finally:
    reconstruct.RAW_DIR = originals["reconstruct.RAW_DIR"]
    reconstruct.EXAMPLES_DIR = originals["reconstruct.EXAMPLES_DIR"]
    merge_new.EXAMPLES_DIR = originals["merge_new.EXAMPLES_DIR"]
    trained_manifest.RAW_DIR = originals["trained_manifest.RAW_DIR"]
    trained_manifest.MANIFEST_PATH = originals["trained_manifest.MANIFEST_PATH"]
    shutil.rmtree(tmp, ignore_errors=True)

print(f"\n{'PASS' if not failures else 'FAIL: ' + ', '.join(failures)}")
