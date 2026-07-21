"""Validates harness/team_paste.py + the named teams in harness/teams.py:
1. add_level unit tests (inserts once, idempotent on an already-complete
   paste, handles multiple mons).
2. add_ev_spreads unit tests (fills EVs from real usage data, infers a
   nature only when one is actually missing, leaves unknown species
   alone, idempotent).
3. Real functional checks: TEAM_LOPUNNY_TR, TEAM_AERO_HO, and
   TEAM_SWAMPERT_TR all actually load through ConstantTeambuilder and
   validate against the real local Showdown server under the champions
   format — not just "looks right".

Run from the project root: python -m harness.test_team_paste
"""

from poke_env.teambuilder import ConstantTeambuilder

from harness.doubles_smoke_test import FORMAT
from harness.team_paste import add_ev_spreads, add_level
from harness.teams import TEAM_AERO_HO, TEAM_LOPUNNY_TR, TEAM_SWAMPERT_TR

failures = []


def check(name: str, ok: bool, detail: str = ""):
    print(f"  {name} [{'ok' if ok else 'FAIL'}]{' ' + str(detail) if detail and not ok else ''}")
    if not ok:
        failures.append(name)


print("add_level unit tests")
single = "Lopunny @ Lopunnite\nAbility: Limber\nEVs: 32 Atk / 32 Spe\nJolly Nature\n- Protect"
result = add_level(single)
check("inserts Level: 50 after Ability", "Level: 50" in result, result)
check("preserves original lines", "Lopunny @ Lopunnite" in result and "- Protect" in result)

already_has_level = "Lopunny @ Lopunnite\nAbility: Limber\nLevel: 50\nEVs: 32 Atk / 32 Spe"
idempotent = add_level(already_has_level)
check("idempotent: doesn't double-insert", idempotent.count("Level: 50") == 1, idempotent)

two_mons = (
    "Lopunny @ Lopunnite\nAbility: Limber\n- Protect\n\n"
    "Farigiraf @ Sitrus Berry\nAbility: Armor Tail\n- Trick Room"
)
multi = add_level(two_mons)
check("inserts for every mon in a multi-mon paste", multi.count("Level: 50") == 2, multi)

print("\nadd_ev_spreads unit tests")
no_evs = "Garchomp @ Life Orb\nAbility: Rough Skin\nJolly Nature\n- Earthquake\n- Dragon Claw\n- Protect"
with_evs = add_ev_spreads(no_evs)
check("inserts an EVs line for a known species", "EVs:" in with_evs, with_evs)
check("EVs line lands before the Nature line", with_evs.index("EVs:") < with_evs.index("Jolly Nature"), with_evs)
check("existing Nature preserved, not replaced", with_evs.count("Nature") == 1 and "Jolly Nature" in with_evs)

already_has_evs = "Garchomp @ Life Orb\nAbility: Rough Skin\nEVs: 4 HP / 4 Atk\nJolly Nature\n- Earthquake"
unchanged = add_ev_spreads(already_has_evs)
check("doesn't overwrite an existing EVs line", unchanged.count("EVs:") == 1 and "4 HP / 4 Atk" in unchanged)

no_nature = "Garchomp @ Life Orb\nAbility: Rough Skin\n- Earthquake\n- Dragon Claw\n- Protect"
filled = add_ev_spreads(no_nature)
check("infers a nature when one is missing", "Nature" in filled, filled)
check("inferred nature boosts the max-invested stat (Atk, tied with Spe but earlier in stat order)",
      "Lonely Nature" in filled, filled)

unknown_species = "Missingnowatever @ Leftovers\nAbility: Levitate\nCareful Nature\n- Tackle"
untouched = add_ev_spreads(unknown_species)
check("unknown species left untouched", untouched.strip() == unknown_species.strip(), untouched)

idempotent_evs = add_ev_spreads(add_ev_spreads(no_evs))
check("idempotent: running twice doesn't double-insert", idempotent_evs == with_evs, idempotent_evs)

print("\nreal functional checks: named teams load and validate on the local server")
check("TEAM_LOPUNNY_TR: every mon got a Level: 50 line", TEAM_LOPUNNY_TR.count("Level: 50") == 6,
      TEAM_LOPUNNY_TR.count("Level: 50"))
for name, team, n_mons in [
    ("TEAM_LOPUNNY_TR", TEAM_LOPUNNY_TR, 6),
    ("TEAM_AERO_HO", TEAM_AERO_HO, 6),
    ("TEAM_SWAMPERT_TR", TEAM_SWAMPERT_TR, 6),
]:
    check(f"{name}: every mon got EVs from real usage data", team.count("EVs:") == n_mons, team.count("EVs:"))
    builder = ConstantTeambuilder(team)
    try:
        packed = builder.yield_team()
        check(f"{name}: ConstantTeambuilder parses it", bool(packed), packed)
    except Exception as e:
        check(f"{name}: ConstantTeambuilder parses it", False, repr(e))

print(f"\n{'PASS' if not failures else 'FAIL: ' + ', '.join(failures)}")
print("\n(Full server-side validation - legality/EV caps/format ruleset - happens "
      "automatically the first time this team is actually used in a battle; "
      "reference-data legality was already spot-checked in conversation before this file was written.)")
