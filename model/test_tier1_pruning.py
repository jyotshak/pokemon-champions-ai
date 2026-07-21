"""Regression test for the Tier-1 domain pruning in model/action_space.py
(_filter_dominated_moves, 2026-07-20): the first "smart pruning" layer,
cutting obviously-never-best moves on PUBLIC information alone so a lower
per-slot cap keeps the RIGHT actions and deeper search fits the budget.

Two cuts, both world-invariant (opponent species types + my own ability/
moves only, never the opponent's sampled hidden attributes):
 1. immune (0x) attacks always cut; resisted (<=0.5x-vs-all) attacks cut
    only when a neutral-or-better attack survives; support attacks (Icy
    Wind etc.) and all status/utility moves exempt.
 2. a Prankster user's opponent-targeting status move cut when EVERY live
    opposing mon is Dark (real Prankster-into-Dark immunity).

The point the measurement makes concrete: the cut does not change the
joint-action COUNT at a low cap (branching == cap) - it changes WHICH
actions fill that cap, swapping a dead move for a tactically live one.

Run from the project root: python -m model.test_tier1_pruning
"""

from model.action_space import _pruned_slot_actions, propose_pruned_turn_actions
import model.action_space as A
from schema.battle_state import FieldState, MoveSlot, OwnPokemon, Position
from schema.full_info_state import FullInfoState

failures = []


def check(name: str, ok: bool, detail=""):
    print(f"  {name} [{'ok' if ok else 'FAIL'}]{' ' + str(detail) if detail and not ok else ''}")
    if not ok:
        failures.append(name)


def mon(species, ability, moves, pos=None):
    return OwnPokemon(
        species=species, ability=ability, position=pos, fainted=False,
        hp=100, max_hp=100, stats={"atk": 120, "def": 90, "spa": 100, "spd": 90, "spe": 100},
        moves=[MoveSlot(move=m, pp=16, max_pp=16) for m in moves],
    )


def move_ids(actions, m):
    out = []
    for a in actions:
        if type(a).__name__ == "MoveAction":
            out.append(m.moves[a.move_slot - 1].move)
    return out


print("resisted-attack cut: Incineroar's Darkest Lariat (Dark) is resisted by a "
      "Fairy + Grass/Fairy pair, so it is dropped while Flare Blitz / Fake Out / Parting Shot survive")
incin = mon("incineroar", "intimidate", ["fakeout", "darkestlariat", "flareblitz", "partingshot"], Position.LEFT)
ally = mon("garchomp", "roughskin", ["earthquake"], Position.RIGHT)
fairy_side = FullInfoState(
    turn=3, field=FieldState(),
    my_team=[incin, ally, mon("tyranitar", "sandstream", ["crunch"]), mon("kingambit", "defiant", ["crunch"])],
    opp_team=[mon("floetteeternal", "flowerveil", ["moonblast"], Position.LEFT),
              mon("whimsicott", "prankster", ["moonblast"], Position.RIGHT),
              mon("sylveon", "pixilate", ["hypervoice"]), mon("farigiraf", "armortail", ["psychic"])],
)
kept = move_ids(_pruned_slot_actions(fairy_side, "me", Position.LEFT, 6), incin)
check("Darkest Lariat dropped (resisted vs all)", "darkestlariat" not in kept, kept)
check("Flare Blitz kept (hits neutral/super)", "flareblitz" in kept, kept)
check("Fake Out kept (support-attack exempt)", "fakeout" in kept, kept)
check("Parting Shot kept (self-switch pivot)", "partingshot" in kept, kept)

print("\nresisted attack is NOT cut when it is the mon's only attack (never leave a mon unable to attack)")
onlyresist = mon("incineroar", "intimidate", ["darkestlariat", "partingshot"], Position.LEFT)
st_only = FullInfoState(
    turn=3, field=FieldState(),
    my_team=[onlyresist, ally, mon("tyranitar", "sandstream", ["crunch"]), mon("kingambit", "defiant", ["crunch"])],
    opp_team=[mon("floetteeternal", "flowerveil", ["moonblast"], Position.LEFT),
              mon("sylveon", "pixilate", ["moonblast"], Position.RIGHT),
              mon("clefable", "magicguard", ["moonblast"]), mon("farigiraf", "armortail", ["psychic"])],
)
kept_only = move_ids(_pruned_slot_actions(st_only, "me", Position.LEFT, 6), onlyresist)
check("Darkest Lariat kept as the only attack", "darkestlariat" in kept_only, kept_only)

print("\nsupport attack (Icy Wind) is NEVER cut even resisted-vs-all: its value is the Speed drop")
icy = mon("pelipper", "drizzle", ["icywind", "hurricane", "protect"], Position.LEFT)
st_icy = FullInfoState(
    turn=3, field=FieldState(),
    my_team=[icy, ally, mon("tyranitar", "sandstream", ["crunch"]), mon("kingambit", "defiant", ["crunch"])],
    # Ice resisted by Fire and Steel: Charizard (Fire/Flying) + Metagross-like Steel
    opp_team=[mon("charizard", "blaze", ["heatwave"], Position.LEFT),
              mon("kingambit", "defiant", ["ironhead"], Position.RIGHT),
              mon("sylveon", "pixilate", ["hypervoice"]), mon("farigiraf", "armortail", ["psychic"])],
)
kept_icy = move_ids(_pruned_slot_actions(st_icy, "me", Position.LEFT, 6), icy)
check("Icy Wind kept despite being resisted by both targets", "icywind" in kept_icy, kept_icy)

print("\nPrankster-into-Dark cut: Whimsicott's Encore is dropped vs an all-Dark side, kept otherwise")
whim = mon("whimsicott", "prankster", ["moonblast", "encore", "tailwind", "uturn"], Position.LEFT)
all_dark = FullInfoState(
    turn=3, field=FieldState(),
    my_team=[whim, ally, mon("tyranitar", "sandstream", ["crunch"]), mon("sylveon", "pixilate", ["moonblast"])],
    opp_team=[mon("kingambit", "defiant", ["crunch"], Position.LEFT),
              mon("incineroar", "intimidate", ["crunch"], Position.RIGHT),
              mon("sylveon", "pixilate", ["hypervoice"]), mon("farigiraf", "armortail", ["psychic"])],
)
kept_dark = move_ids(_pruned_slot_actions(all_dark, "me", Position.LEFT, 6), whim)
check("Encore dropped vs all-Dark (Prankster immunity)", "encore" not in kept_dark, kept_dark)
check("Tailwind kept (self-side status, unaffected)", "tailwind" in kept_dark, kept_dark)
check("Moonblast kept (Fairy super-effective vs Dark)", "moonblast" in kept_dark, kept_dark)

non_dark = FullInfoState(
    turn=3, field=FieldState(),
    my_team=[whim, ally, mon("tyranitar", "sandstream", ["crunch"]), mon("sylveon", "pixilate", ["moonblast"])],
    opp_team=[mon("garchomp", "roughskin", ["earthquake"], Position.LEFT),
              mon("incineroar", "intimidate", ["crunch"], Position.RIGHT),
              mon("sylveon", "pixilate", ["hypervoice"]), mon("farigiraf", "armortail", ["psychic"])],
)
kept_nd = move_ids(_pruned_slot_actions(non_dark, "me", Position.LEFT, 6), whim)
check("Encore kept vs a non-Dark side (control)", "encore" in kept_nd, kept_nd)

print("\nEncore is NOT cut for a non-Prankster user, even vs all-Dark (immunity is Prankster-specific)")
noprank = mon("sylveon", "pixilate", ["moonblast", "encore", "hypervoice", "quickattack"], Position.LEFT)
np_state = FullInfoState(
    turn=3, field=FieldState(),
    my_team=[noprank, ally, mon("tyranitar", "sandstream", ["crunch"]), mon("clefable", "magicguard", ["moonblast"])],
    opp_team=[mon("kingambit", "defiant", ["crunch"], Position.LEFT),
              mon("incineroar", "intimidate", ["crunch"], Position.RIGHT),
              mon("sylveon", "pixilate", ["hypervoice"]), mon("farigiraf", "armortail", ["psychic"])],
)
kept_np = move_ids(_pruned_slot_actions(np_state, "me", Position.LEFT, 6), noprank)
check("Encore kept for non-Prankster Sylveon vs all-Dark", "encore" in kept_np, kept_np)

print("\nthe cut swaps a dead move for a live one at a LOW cap without changing the branching (cap == count)")
# At cap=3 the un-cut pruner spends a slot on the resisted Darkest Lariat and drops Parting Shot;
# the cut keeps the same THREE-action budget but fills it with Flare Blitz / Fake Out / Parting Shot.
orig = A._filter_dominated_moves
A._filter_dominated_moves = lambda s, side, m, b: b
uncut3 = move_ids(_pruned_slot_actions(fairy_side, "me", Position.LEFT, 3), incin)
A._filter_dominated_moves = orig
cut3 = move_ids(_pruned_slot_actions(fairy_side, "me", Position.LEFT, 3), incin)
check("un-cut cap=3 wastes a slot on Darkest Lariat", "darkestlariat" in uncut3, uncut3)
check("cut cap=3 keeps Parting Shot instead", "partingshot" in cut3 and "darkestlariat" not in cut3, cut3)

print(f"\n{'PASS' if not failures else 'FAIL: ' + ', '.join(failures)}")
