"""Regression test for belief/usage_data/build_weights.py's ability-key
normalization (2026-07-20 bug: species_data ability legal pools are
display names 'Intimidate' but usage_stats keys abilities by id
'intimidate', so every lookup missed and the ability prior collapsed to
a UNIFORM floor over each species' legal set - for all 237 species).

Runs build() against the real data files and asserts the ability prior
reflects real usage, keyed by display names (what determinize's
_weighted_choice looks up).

Run from the project root: python -m belief.usage_data.test_build_weights
"""

from belief.usage_data.build_weights import _to_id, build

failures = []


def check(name: str, ok: bool, detail: str = ""):
    print(f"  {name} [{'ok' if ok else 'FAIL'}]{' ' + str(detail) if detail and not ok else ''}")
    if not ok:
        failures.append(name)


print("_to_id normalizes display names to Showdown ids")
check("'Armor Tail' -> 'armortail'", _to_id("Armor Tail") == "armortail")
check("'Queenly Majesty' -> 'queenlymajesty'", _to_id("Queenly Majesty") == "queenlymajesty")

weights = build()

print("\nability prior reflects real usage (not a uniform floor) and is keyed by DISPLAY names")
inc = weights["incineroar"]["abilities"]
check("Incineroar ability keys are display names (Intimidate present, not 'intimidate')",
      "Intimidate" in inc and "intimidate" not in inc, list(inc))
check("Incineroar's Intimidate strongly dominates Blaze (real ~99.8 vs ~0.2)",
      inc["Intimidate"] > 10 * max(inc["Blaze"], 0.1), inc)

print("\nthe priority-blocking abilities you actually face are near-certain, not 1/N")
check("Farigiraf Armor Tail dominant", weights["farigiraf"]["abilities"]["Armor Tail"] > 50,
      weights["farigiraf"]["abilities"])
check("Tsareena Queenly Majesty dominant", weights["tsareena"]["abilities"]["Queenly Majesty"] > 50,
      weights["tsareena"]["abilities"])
check("Sylveon Pixilate dominant (Cute Charm rare)", weights["sylveon"]["abilities"]["Pixilate"] > 50,
      weights["sylveon"]["abilities"])

print("\nno species is left with a fully-uniform ability prior (the bug's signature)")
uniform = [
    sp for sp, d in weights.items()
    if len(d["abilities"]) > 1 and len(set(round(v, 3) for v in d["abilities"].values())) == 1
]
# A species with genuinely no usage data can still be uniform (real
# fallback), but a meta staple never should be. Assert the specific ones
# we care about aren't, and report the count for visibility.
print(f"    ({len(uniform)} species still uniform - expected only genuinely data-less ones)")
for staple in ("incineroar", "garchomp", "kingambit", "charizard", "whimsicott"):
    check(f"{staple} is NOT uniform", staple not in uniform)

print(f"\n{'PASS' if not failures else 'FAIL: ' + ', '.join(failures)}")
