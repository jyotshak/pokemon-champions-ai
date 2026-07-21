"""Validates belief/team_popularity.py against real tournament_usage.json
data: the 4 explicit display-name folds resolve correctly, a real
high-usage species scores far above the floor, a genuinely rare/unlisted
species falls back to the floor (never 0 or a crash), and
team_popularity_score is a plain arithmetic mean.

Run from the project root: python -m belief.test_team_popularity
"""

from belief.team_popularity import _FLOOR_USAGE_PCT, resolve_species_id, species_popularity, team_popularity_score

failures = []


def check(name: str, ok: bool, detail: str = ""):
    print(f"  {name} [{'ok' if ok else 'FAIL'}]{' ' + str(detail) if detail and not ok else ''}")
    if not ok:
        failures.append(name)


print("resolve_species_id: standard + mega-forme + explicit-fold cases")
check("plain species", resolve_species_id("Garchomp") == "garchomp")
check("mega forme folds to base", resolve_species_id("Charizard-Mega-Y") == "charizard")
check("explicit fold: Floette-Eternal-Mega", resolve_species_id("Floette-Eternal-Mega") == "floetteeternal")
check("explicit fold: Maushold-Four", resolve_species_id("Maushold-Four") == "maushold")
check("explicit fold: Sinistcha-Masterpiece", resolve_species_id("Sinistcha-Masterpiece") == "sinistcha")
check("explicit fold: Vivillon-Fancy", resolve_species_id("Vivillon-Fancy") == "vivillon")

print("\nspecies_popularity: real high-usage species scores far above the floor")
garchomp_pop = species_popularity("Garchomp")
check("Garchomp is well above the floor (real ~38% usage)", garchomp_pop > _FLOOR_USAGE_PCT * 10, garchomp_pop)

print("\nspecies_popularity: unlisted/nonexistent species falls back to the floor, never crashes")
check("a nonsense species id returns exactly the floor",
      species_popularity("ThisSpeciesDoesNotExist") == _FLOOR_USAGE_PCT)

print("\nteam_popularity_score: plain arithmetic mean")
fake_team = ["Garchomp", "Garchomp", "Garchomp", "Garchomp", "Garchomp", "Garchomp"]
check("a 6-of-the-same-species team scores exactly that species' popularity",
      abs(team_popularity_score(fake_team) - garchomp_pop) < 1e-9)
mixed_score = team_popularity_score(["Garchomp", "ThisSpeciesDoesNotExist"])
check("a 2-mon mean averages a real value and the floor correctly",
      abs(mixed_score - (garchomp_pop + _FLOOR_USAGE_PCT) / 2) < 1e-9, mixed_score)
check("empty list doesn't crash (returns 0.0)", team_popularity_score([]) == 0.0)

print(f"\n{'PASS' if not failures else 'FAIL: ' + ', '.join(failures)}")
