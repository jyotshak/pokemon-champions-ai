"""Validates belief/team_synergy.py's SYNERGY_WEIGHTS table:
- symmetry (weights[a][b] == weights[b][a]) for real pairs.
- a known real teammate pair scores above the floor (present, positive).
- a known tournament-core pair scores meaningfully above what pure
  teammate-rank-decay alone would give it - isolates the core-bonus
  contribution (belief/usage_data/team_cores.json) from the broader
  rank-decay contribution (belief/usage_data/usage_stats.json).
- build_synergy_weights() is deterministic and makes no network calls
  (only reads the two already-checked-in JSON artifacts) - critical
  since it's called eagerly at import time.

Run from the project root: python -m belief.test_team_synergy
"""

import json
import urllib.request
from pathlib import Path

from belief.team_synergy import SYNERGY_WEIGHTS, _CORE_BONUS_SCALE, build_synergy_weights

_HERE = Path(__file__).resolve().parent
_USAGE_STATS = json.loads((_HERE / "usage_data" / "usage_stats.json").read_text(encoding="utf-8"))
_TEAM_CORES = json.loads((_HERE / "usage_data" / "team_cores.json").read_text(encoding="utf-8"))

failures = []


def check(name: str, ok: bool, detail: str = ""):
    print(f"  {name} [{'ok' if ok else 'FAIL'}]{' ' + str(detail) if detail and not ok else ''}")
    if not ok:
        failures.append(name)


print("symmetry")
sample_pairs = [("archaludon", "pelipper"), ("garchomp", "kingambit"), ("archaludon", "sableye")]
for a, b in sample_pairs:
    check(f"SYNERGY_WEIGHTS[{a}][{b}] == SYNERGY_WEIGHTS[{b}][{a}]",
          SYNERGY_WEIGHTS.get(a, {}).get(b) == SYNERGY_WEIGHTS.get(b, {}).get(a),
          (SYNERGY_WEIGHTS.get(a, {}).get(b), SYNERGY_WEIGHTS.get(b, {}).get(a)))

print("\na known real teammate pair scores above the floor")
check("archaludon/pelipper (each other's rank-0 teammate) has a positive weight",
      SYNERGY_WEIGHTS["archaludon"]["pelipper"] > 0.0, SYNERGY_WEIGHTS["archaludon"]["pelipper"])

print("\ncore-bonus contribution isolated from rank-decay contribution")


def _rank_decay_only(a: str, b: str) -> float:
    """Recomputes just the usage_stats.json teammate-rank contribution
    for a pair, from source, independent of team_synergy.py's own logic
    (so this test doesn't just re-assert the implementation against
    itself) - mirrors build_synergy_weights()'s rank-decay half exactly.
    """
    total = 0.0
    a_mates = _USAGE_STATS.get(a, {}).get("teammates", [])
    if b in a_mates:
        total += 1.0 / (a_mates.index(b) + 1)
    b_mates = _USAGE_STATS.get(b, {}).get("teammates", [])
    if a in b_mates:
        total += 1.0 / (b_mates.index(a) + 1)
    return total


def _core_bonus_only(a: str, b: str) -> float:
    total = 0.0
    for core in _TEAM_CORES:
        from belief.species_folding import base_species_id
        folded = {base_species_id(s) for s in core["species"]}
        if a in folded and b in folded:
            total += _CORE_BONUS_SCALE * core["pct"]
    return total


a, b = "archaludon", "pelipper"
rank_only = _rank_decay_only(a, b)
core_only = _core_bonus_only(a, b)
check("archaludon/pelipper is genuinely a scraped core pair (test fixture sanity)", core_only > 0.0, core_only)
check("SYNERGY_WEIGHTS == rank-decay contribution + core-bonus contribution, exactly",
      abs(SYNERGY_WEIGHTS[a][b] - (rank_only + core_only)) < 1e-9,
      (SYNERGY_WEIGHTS[a][b], rank_only, core_only))
check("the core-bonus contribution alone is a meaningful (not negligible) share of the total",
      core_only > rank_only * 0.5, (core_only, rank_only))

c, d = "archaludon", "sableye"
check("archaludon/sableye is a real (rank-decay-only) teammate pair but NOT a scraped core",
      _rank_decay_only(c, d) > 0.0 and _core_bonus_only(c, d) == 0.0,
      (_rank_decay_only(c, d), _core_bonus_only(c, d)))
check("the core pair (archaludon/pelipper) scores meaningfully above the non-core teammate "
      "pair (archaludon/sableye), driven by the core bonus specifically",
      SYNERGY_WEIGHTS[a][b] > SYNERGY_WEIGHTS[c][d] * 2,
      (SYNERGY_WEIGHTS[a][b], SYNERGY_WEIGHTS[c][d]))

print("\nbuild_synergy_weights() is deterministic and makes no network calls")


def _no_network(*args, **kwargs):
    raise AssertionError("build_synergy_weights() must not touch the network")


_orig_urlopen = urllib.request.urlopen
urllib.request.urlopen = _no_network
try:
    rebuilt = build_synergy_weights()
    check("succeeds with network access blocked", True)
except AssertionError:
    check("succeeds with network access blocked", False)
finally:
    urllib.request.urlopen = _orig_urlopen

check("rebuilding gives an identical table (deterministic)", rebuilt == SYNERGY_WEIGHTS)

print(f"\n{'PASS' if not failures else 'FAIL: ' + ', '.join(failures)}")
