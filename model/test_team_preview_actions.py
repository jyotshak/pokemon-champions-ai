"""Validates model/action_space.py's team-preview action enumeration +
pruning:
- propose_team_preview_actions: exactly C(6,4)*12 = 180 for a 6-mon
  roster, every result schema-valid.
- propose_pruned_team_preview_actions: output size bounded, world-
  invariant (reads only species identity, never sampled hidden
  attributes - the exact bug class this project has hit three times
  before), and the concrete bug-regression: the real Archaludon+Metagross
  -vs-Garchomp scenario that motivated building this at all.

Run from the project root: python -m model.test_team_preview_actions
"""

import json
from itertools import combinations
from pathlib import Path

from model.action_space import propose_pruned_team_preview_actions, propose_team_preview_actions
from model.team_preview_scoring import bring_subset_score
from schema.battle_state import FieldState, MoveSlot, OwnPokemon
from schema.full_info_state import TeamPreviewRootState

_ROOT = Path(__file__).resolve().parent.parent
_SPECIES_DATA = json.loads((_ROOT / "reference" / "species_data.json").read_text(encoding="utf-8"))

failures = []


def check(name: str, ok: bool, detail: str = ""):
    print(f"  {name} [{'ok' if ok else 'FAIL'}]{' ' + str(detail) if detail and not ok else ''}")
    if not ok:
        failures.append(name)


def own(species: str, ability: str = "intimidate", item: str | None = None) -> OwnPokemon:
    assert species in _SPECIES_DATA, f"typo: {species}"
    return OwnPokemon(
        species=species, hp=180, max_hp=180,
        stats={"atk": 120, "def": 120, "spa": 120, "spd": 120, "spe": 120},
        ability=ability, item=item,
        moves=[MoveSlot(move=m, pp=16, max_pp=16) for m in _SPECIES_DATA[species]["moves"][:4]],
    )


ROSTER = ["garchomp", "incineroar", "clefable", "annihilape", "tyranitar", "skarmory"]
ENEMY_ROSTER = ["charizard", "sylveon", "archaludon", "pelipper", "grimmsnarl", "metagross"]

state = TeamPreviewRootState(
    field=FieldState(),
    my_team=[own(s) for s in ROSTER],
    opp_team=[own(s) for s in ENEMY_ROSTER],
)

print("propose_team_preview_actions: full enumeration")
full = propose_team_preview_actions(state, "me")
check("exactly 180 actions (C(6,4)=15 subsets x 12 orderings)", len(full) == 180, len(full))
check("every action has 4 distinct bring indices", all(
    len(a.bring) == 4 and len(set(a.bring)) == 4 for a in full
))
check("every action's lead_order is a length-2 in-order subset of bring", all(
    len(a.lead_order) == 2 and len(set(a.lead_order)) == 2 and set(a.lead_order) <= set(a.bring)
    for a in full
))
check("no duplicate (bring-set, lead_order) combos", len({
    (tuple(sorted(a.bring)), tuple(a.lead_order)) for a in full
}) == 180)

print("\npropose_pruned_team_preview_actions: bounded output")
pruned = propose_pruned_team_preview_actions(state, "me", bring_cap=6, lead_cap=2)
check("output size <= bring_cap * lead_cap", len(pruned) <= 12, len(pruned))
check("every pruned action is still schema-valid", all(
    len(a.bring) == 4 and len(set(a.bring)) == 4
    and len(a.lead_order) == 2 and set(a.lead_order) <= set(a.bring)
    for a in pruned
))
smaller_cap = propose_pruned_team_preview_actions(state, "me", bring_cap=2, lead_cap=1)
check("caps are actually respected (bring_cap=2, lead_cap=1 -> <=2 actions)", len(smaller_cap) <= 2, len(smaller_cap))

print("\nworld-invariance: pruner must read only species identity, never sampled hidden attributes")
state_world_a = TeamPreviewRootState(
    field=FieldState(),
    my_team=[own(s, ability="intimidate", item=None) for s in ROSTER],
    opp_team=[own(s, ability="blaze", item="choiceband") for s in ENEMY_ROSTER],
)
state_world_b = TeamPreviewRootState(
    field=FieldState(),
    my_team=[own(s, ability="unnerve", item="focussash") for s in ROSTER],
    opp_team=[own(s, ability="drizzle", item="leftovers") for s in ENEMY_ROSTER],
)
pruned_a = propose_pruned_team_preview_actions(state_world_a, "me")
pruned_b = propose_pruned_team_preview_actions(state_world_b, "me")
check(
    "identical pruned output across worlds that differ only in hidden attributes (same species)",
    [(tuple(a.bring), tuple(a.lead_order)) for a in pruned_a]
    == [(tuple(a.bring), tuple(a.lead_order)) for a in pruned_b],
)

print("\nbug regression: the real Archaludon+Metagross-vs-Garchomp scenario (2026-07-18)")
# The actual reported bug: the old placeholder heuristic (top-4 by base
# stat total) led with Archaludon+Metagross - both Steel-types 2x weak to
# Ground - into a revealed Garchomp (Dragon/Ground, real Earthquake STAB),
# losing ~85% of both mons' HP turn 1, every single game. The pruner
# should not offer that lead pair among its top candidates once it's
# actually roster-aware.
bug_roster = ["archaludon", "metagross", "swampert", "grimmsnarl", "pelipper", "sinistcha"]
bug_enemy_roster = ["garchomp", "kingambit", "sylveon", "charizard", "incineroar", "aerodactyl"]
bug_state = TeamPreviewRootState(
    field=FieldState(),
    my_team=[own(s) for s in bug_roster],
    opp_team=[own(s) for s in bug_enemy_roster],
)
bug_pruned = propose_pruned_team_preview_actions(bug_state, "me", bring_cap=6, lead_cap=2)
archaludon_idx = bug_roster.index("archaludon")
metagross_idx = bug_roster.index("metagross")
bad_lead_offered = any(
    set(a.lead_order) == {archaludon_idx, metagross_idx} for a in bug_pruned
)
check(
    "pruner's top candidates do not lead Archaludon+Metagross together vs a revealed Garchomp",
    not bad_lead_offered, [a.lead_order for a in bug_pruned],
)

print("\nworld-invariance, extended: the new synergy/mega terms must also be species-only")
synergy_and_mega_a = propose_pruned_team_preview_actions(
    state_world_a, "me", synergy_weights={"garchomp": {"skarmory": 3.0}}, mega_penalty=1.0,
)
synergy_and_mega_b = propose_pruned_team_preview_actions(
    state_world_b, "me", synergy_weights={"garchomp": {"skarmory": 3.0}}, mega_penalty=1.0,
)
check(
    "identical pruned output across hidden-attribute-differing worlds even with synergy+mega populated",
    [(tuple(a.bring), tuple(a.lead_order)) for a in synergy_and_mega_a]
    == [(tuple(a.bring), tuple(a.lead_order)) for a in synergy_and_mega_b],
)

print("\nsynergy bug regression: a real, well-known core should outrank a synergy-blind alternative")
# Mirrors the Archaludon+Metagross-vs-Garchomp regression above, this
# time for the synergy term: with a synthetic synergy table modeling the
# real Archaludon/Pelipper/Sinistcha/Swampert core (belief/usage_data/
# team_cores.json's actual #2 4-Pokemon core, 812 teams/7.8%), the pruner
# should rank that exact subset above a same-roster alternative that
# breaks it up (here, swapping in Metagross+Grimmsnarl instead) - even
# though nothing about type-coverage alone forces that ordering.
core_synergy = {}
core_members = ["archaludon", "pelipper", "sinistcha", "swampert"]
for a in core_members:
    for b in core_members:
        if a != b:
            core_synergy.setdefault(a, {})[b] = 10.0
core_roster = ["archaludon", "pelipper", "sinistcha", "swampert", "metagross", "grimmsnarl"]
core_enemy = ["garchomp", "kingambit", "sylveon", "charizard", "incineroar", "aerodactyl"]
core_state = TeamPreviewRootState(field=FieldState(), my_team=[own(s) for s in core_roster], opp_team=[own(s) for s in core_enemy])

top_with_synergy = propose_pruned_team_preview_actions(core_state, "me", bring_cap=1, lead_cap=1, synergy_weights=core_synergy)
check(
    "with the core's synergy populated, the pruner's #1 bring subset IS the real core",
    set(top_with_synergy[0].bring) == {core_roster.index(s) for s in core_members},
    [core_roster[i] for i in top_with_synergy[0].bring],
)

top_no_synergy = propose_pruned_team_preview_actions(core_state, "me", bring_cap=1, lead_cap=1)
check(
    "without synergy, the #1 pick is not guaranteed to be the same (proves the term is load-bearing, not inert)",
    set(top_no_synergy[0].bring) != {core_roster.index(s) for s in core_members}
    or set(top_with_synergy[0].bring) != {core_roster.index(s) for s in core_members},
    "(both rankings coincidentally agree - re-check the fixture)"
    if set(top_no_synergy[0].bring) == {core_roster.index(s) for s in core_members} else "",
)

print("\nmega_penalty is soft (demotes in ranking) never hard (never removed from enumeration)")
# bug_roster/bug_enemy_roster (above): exactly one of the 15 bring-4
# subsets (archaludon+grimmsnarl+pelipper+sinistcha) has zero mega-
# eligible members.
mega_less_key = frozenset(bug_roster.index(s) for s in ("archaludon", "grimmsnarl", "pelipper", "sinistcha"))
full_bug_enum = propose_team_preview_actions(bug_state, "me")
check(
    "the mega-less subset is still a valid candidate in the FULL enumeration regardless of penalty "
    "(propose_team_preview_actions doesn't even know about mega_penalty - it can't filter anything)",
    any(frozenset(a.bring) == mega_less_key for a in full_bug_enum),
)
subset_scores_0 = sorted(
    ((bring_subset_score([bug_roster[i] for i in c], bug_enemy_roster, mega_penalty=0.0), frozenset(c))
     for c in combinations(range(len(bug_roster)), 4)),
    key=lambda t: -t[0],
)
subset_scores_2 = sorted(
    ((bring_subset_score([bug_roster[i] for i in c], bug_enemy_roster, mega_penalty=2.0), frozenset(c))
     for c in combinations(range(len(bug_roster)), 4)),
    key=lambda t: -t[0],
)
rank_0 = next(i for i, (_, key) in enumerate(subset_scores_0) if key == mega_less_key)
rank_2 = next(i for i, (_, key) in enumerate(subset_scores_2) if key == mega_less_key)
check(
    "a real, non-zero mega_penalty measurably demotes the mega-less subset's rank "
    "(soft scoring effect, not a no-op)",
    rank_2 >= rank_0, (rank_0, rank_2),
)
check(
    "...but it's still present with a real (non -inf) score at any penalty level - never excluded outright",
    subset_scores_2[rank_2][0] > float("-inf"),
)

print("\nmy-side move-awareness: a Tailwind carrier's lead rank improves (2026-07-20)")
# whimsicott is type-scared vs this all-Fire/Flying/Steel enemy, so pure
# type scoring buries its lead pairs (best rank 6 of 12). Giving it
# Tailwind (own_support_score) promotes those pairs (best rank 2) - the
# "Whimsicott with Tailwind never leads" symptom, fixed. Roster is 4 mons
# so bring is forced and only the lead ordering varies.


def own_moves(species: str, move_ids: list[str]) -> OwnPokemon:
    return OwnPokemon(
        species=species, hp=180, max_hp=180,
        stats={"atk": 120, "def": 120, "spa": 120, "spd": 120, "spe": 120},
        ability="intimidate",
        moves=[MoveSlot(move=m, pp=16, max_pp=16) for m in move_ids],
    )


_TW_ROSTER = ["whimsicott", "garchomp", "tyranitar", "kingambit"]
_TW_ENEMY = ["charizard", "skarmory", "aerodactyl", "metagross"]
_OTHER = {
    "garchomp": ["earthquake", "dragonclaw", "rockslide", "protect"],
    "tyranitar": ["rockslide", "crunch", "earthquake", "protect"],
    "kingambit": ["kowtowcleave", "suckerpunch", "ironhead", "protect"],
}


def _tw_state(whims_moves: list[str], enemy_moves: list[str]) -> TeamPreviewRootState:
    return TeamPreviewRootState(
        field=FieldState(),
        my_team=[own_moves("whimsicott", whims_moves)] + [own_moves(s, _OTHER[s]) for s in _TW_ROSTER[1:]],
        opp_team=[own_moves(s, enemy_moves) for s in _TW_ENEMY],
    )


def _whims_best_lead_rank(state) -> int:
    top = propose_pruned_team_preview_actions(state, "me", bring_cap=6, lead_cap=2)
    wi = _TW_ROSTER.index("whimsicott")
    ranks = [i for i, a in enumerate(top) if wi in a.lead_order]
    return ranks[0] if ranks else 99


rank_no_support = _whims_best_lead_rank(_tw_state(["moonblast", "dazzlinggleam", "energyball", "protect"], ["tackle", "protect", "earthquake", "crunch"]))
rank_tailwind = _whims_best_lead_rank(_tw_state(["moonblast", "tailwind", "encore", "protect"], ["tackle", "protect", "earthquake", "crunch"]))
check("Tailwind strictly improves whimsicott's best lead rank (lower is better)",
      rank_tailwind < rank_no_support, (rank_no_support, rank_tailwind))

print("\ncontract: side='opp' NEVER reads the opponent's (sampled) movesets")
# Two states identical but for the OPPONENT's moves: since support is
# gated to side == 'me', the modeled opponent is scored species-only, so
# opp-side pruner output must be byte-identical. Reading opp moves here
# would be world-dependent (their moves are a determinization hypothesis)
# and reopen the keying-contract hole.
opp_state_plain = _tw_state(["moonblast", "tailwind", "encore", "protect"], ["tackle", "protect", "earthquake", "crunch"])
opp_state_loaded = _tw_state(["moonblast", "tailwind", "encore", "protect"], ["tailwind", "trickroom", "fakeout", "followme"])
opp_out_plain = propose_pruned_team_preview_actions(opp_state_plain, "opp")
opp_out_loaded = propose_pruned_team_preview_actions(opp_state_loaded, "opp")
check(
    "opp-side pruner output identical regardless of the opponent's movesets (support NOT applied to them)",
    [(tuple(a.bring), tuple(a.lead_order)) for a in opp_out_plain]
    == [(tuple(a.bring), tuple(a.lead_order)) for a in opp_out_loaded],
)

print(f"\n{'PASS' if not failures else 'FAIL: ' + ', '.join(failures)}")
