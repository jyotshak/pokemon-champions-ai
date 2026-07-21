"""Validates model/team_preview_scoring.py's primitives in isolation:
- synergy_weights=None -> zero synergy contribution (bit-identical to the
  pre-synergy formula).
- a populated synergy table strictly raises bring_subset_score/
  lead_pair_score for a subset/pair containing a high-affinity pair.
- mega_penalty=0.0 (default) leaves scores unchanged; mega_penalty>0.0
  lowers exactly the subsets with zero mega-eligible members.
- lead_pair_score has no mega_penalty parameter/effect at all.

Run from the project root: python -m model.test_team_preview_scoring
"""

from model.team_preview_scoring import (
    bring_subset_score, is_mega_eligible, lead_pair_score, offensive_presence, defensive_risk,
    own_support_score, pairwise_synergy_sum,
)
from schema.battle_state import MoveSlot

failures = []


def check(name: str, ok: bool, detail: str = ""):
    print(f"  {name} [{'ok' if ok else 'FAIL'}]{' ' + str(detail) if detail and not ok else ''}")
    if not ok:
        failures.append(name)


SUBSET = ["archaludon", "metagross", "swampert", "grimmsnarl"]
ENEMY = ["garchomp", "kingambit", "sylveon", "charizard"]
PAIR = ["archaludon", "swampert"]

print("synergy_weights=None -> zero contribution")
check("pairwise_synergy_sum is 0.0 with no table", pairwise_synergy_sum(SUBSET, None) == 0.0)
base_bring = bring_subset_score(SUBSET, ENEMY)
base_lead = lead_pair_score(PAIR, ENEMY)
check("bring_subset_score with no synergy/mega args == with explicit inert args",
      base_bring == bring_subset_score(SUBSET, ENEMY, None, 1.0, 0.0))
check("lead_pair_score with no synergy arg == with explicit inert arg",
      base_lead == lead_pair_score(PAIR, ENEMY, None, 1.0))

print("\na populated synergy table strictly raises scores for a high-affinity pair")
strong_synergy = {"archaludon": {"metagross": 5.0, "swampert": 3.0, "grimmsnarl": 0.0},
                   "metagross": {"archaludon": 5.0, "swampert": 0.0, "grimmsnarl": 0.0},
                   "swampert": {"archaludon": 3.0, "metagross": 0.0, "grimmsnarl": 0.0},
                   "grimmsnarl": {"archaludon": 0.0, "metagross": 0.0, "swampert": 0.0}}
check("pairwise_synergy_sum picks up the populated pairs (5.0+3.0=8.0 for this subset)",
      pairwise_synergy_sum(SUBSET, strong_synergy) == 8.0, pairwise_synergy_sum(SUBSET, strong_synergy))
synergy_bring = bring_subset_score(SUBSET, ENEMY, strong_synergy)
check("bring_subset_score strictly higher with synergy populated", synergy_bring > base_bring,
      (synergy_bring, base_bring))
synergy_lead = lead_pair_score(PAIR, ENEMY, strong_synergy)
check("lead_pair_score strictly higher with synergy populated", synergy_lead > base_lead,
      (synergy_lead, base_lead))

print("\nsynergy_scale actually scales the contribution")
scaled = bring_subset_score(SUBSET, ENEMY, strong_synergy, synergy_scale=2.0)
check("doubling synergy_scale doubles the synergy delta",
      abs((scaled - base_bring) - 2 * (synergy_bring - base_bring)) < 1e-9, (scaled, synergy_bring, base_bring))

print("\nmega_penalty: soft subtraction, bring-subset only, boolean gate not count-scaled")
check("mega_penalty=0.0 (default) leaves bring_subset_score unchanged",
      bring_subset_score(SUBSET, ENEMY, mega_penalty=0.0) == base_bring)
no_mega_subset = ["grimmsnarl", "sinistcha", "pelipper", "incineroar"]  # none of these hold a stone
check("sanity: this filler subset really has zero mega-eligible members",
      not any(is_mega_eligible(sp) for sp in no_mega_subset))
penalized = bring_subset_score(no_mega_subset, ENEMY, mega_penalty=1.0)
unpenalized = bring_subset_score(no_mega_subset, ENEMY, mega_penalty=0.0)
check("mega_penalty>0 lowers a zero-mega-eligible subset's score", penalized < unpenalized,
      (penalized, unpenalized))
check("penalty magnitude matches exactly (flat subtraction)", abs((unpenalized - penalized) - 1.0) < 1e-9)

has_mega_subset = ["metagross", "sinistcha", "pelipper", "incineroar"]  # metagross can mega
check("sanity: this subset has one mega-eligible member", any(is_mega_eligible(sp) for sp in has_mega_subset))
check("mega_penalty does NOT lower a subset that already has a mega-eligible member",
      bring_subset_score(has_mega_subset, ENEMY, mega_penalty=1.0)
      == bring_subset_score(has_mega_subset, ENEMY, mega_penalty=0.0))

two_mega_subset = ["metagross", "swampert", "pelipper", "incineroar"]  # metagross AND swampert
check("sanity: this subset has two mega-eligible members", sum(is_mega_eligible(sp) for sp in two_mega_subset) == 2)
delta_one_mega = (bring_subset_score(has_mega_subset, ENEMY, mega_penalty=0.0)
                   - bring_subset_score(has_mega_subset, ENEMY, mega_penalty=1.0))
delta_two_mega = (bring_subset_score(two_mega_subset, ENEMY, mega_penalty=0.0)
                   - bring_subset_score(two_mega_subset, ENEMY, mega_penalty=1.0))
check("boolean gate: the penalty's effect (0.0 vs 1.0 delta) is identical whether a "
      "subset has one or two mega-eligible members - both are just 'not penalized'",
      delta_one_mega == delta_two_mega == 0.0, (delta_one_mega, delta_two_mega))

print("\nlead_pair_score has NO mega_penalty parameter or effect at all")
no_mega_pair = ["grimmsnarl", "pelipper"]
has_mega_pair = ["metagross", "pelipper"]
try:
    lead_pair_score(no_mega_pair, ENEMY, mega_penalty=1.0)  # type: ignore[call-arg]
    check("lead_pair_score rejects a mega_penalty kwarg (no such parameter exists)", False)
except TypeError:
    check("lead_pair_score rejects a mega_penalty kwarg (no such parameter exists)", True)
check("a mega-less lead pair isn't structurally disadvantaged vs a mega-holding one "
      "beyond ordinary offense/defense/synergy differences (no hidden mega term)",
      lead_pair_score(no_mega_pair, ENEMY) == offensive_presence("grimmsnarl", ENEMY)
      + offensive_presence("pelipper", ENEMY)
      - 1.5 * (defensive_risk("grimmsnarl", ENEMY) + defensive_risk("pelipper", ENEMY)))

print("\nown_support_score: sums support-move weights, ignores everything else")


def moves(*ids):
    return [MoveSlot(move=m, pp=16, max_pp=16) for m in ids]


check("no support moves -> 0.0", own_support_score(moves("tackle", "protect", "earthquake", "crunch")) == 0.0)
check("Tailwind is weighted (1.5)", own_support_score(moves("tailwind", "moonblast", "encore", "protect")) == 1.5,
      own_support_score(moves("tailwind", "moonblast", "encore", "protect")))
check("multiple support moves stack (Fake Out 1.0 + Parting-Shot-not-listed + redirection)",
      own_support_score(moves("fakeout", "followme", "flareblitz", "protect")) == 2.0,
      own_support_score(moves("fakeout", "followme", "flareblitz", "protect")))

print("\nsupport_by_species strictly raises the score of a subset/pair containing a supporter")
support = {"whimsicott": 1.5, "incineroar": 1.0, "garchomp": 0.0, "charizard": 0.0}
tw_pair = ["whimsicott", "garchomp"]
base_tw_lead = lead_pair_score(tw_pair, ENEMY)
supported_tw_lead = lead_pair_score(tw_pair, ENEMY, support_by_species=support)
check("lead_pair_score higher when the pair holds a Tailwind user", supported_tw_lead > base_tw_lead,
      (supported_tw_lead, base_tw_lead))
check("lead support delta equals exactly the summed weight (1.5 + 0.0)",
      abs((supported_tw_lead - base_tw_lead) - 1.5) < 1e-9)
tw_subset = ["whimsicott", "incineroar", "garchomp", "charizard"]
base_tw_bring = bring_subset_score(tw_subset, ENEMY)
supported_tw_bring = bring_subset_score(tw_subset, ENEMY, support_by_species=support)
check("bring_subset_score higher when the subset holds supporters (1.5 + 1.0)",
      abs((supported_tw_bring - base_tw_bring) - 2.5) < 1e-9, (supported_tw_bring, base_tw_bring))

print("\nsupport_by_species=None (default) leaves both scores bit-identical (opponent-side / non-TP callers)")
check("bring_subset_score unchanged with support=None", bring_subset_score(tw_subset, ENEMY) == base_tw_bring)
check("lead_pair_score unchanged with support=None", lead_pair_score(tw_pair, ENEMY) == base_tw_lead)

print(f"\n{'PASS' if not failures else 'FAIL: ' + ', '.join(failures)}")
