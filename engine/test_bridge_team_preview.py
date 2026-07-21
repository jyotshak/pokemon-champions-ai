"""Validates the engine bridge's team-preview extension (init_team_preview
+ step_team_preview) against the real Sim.Battle:

1. init_team_preview_battle returns a valid handle, no crash, for a
   hand-built 6v6 roster.
2. Foundational check (the thing everything downstream assumes): after
   step_team_preview resolves a bring/lead choice on both sides, the
   engine has trimmed each side down to exactly the picked 4 (not 6),
   and turn is 1 - i.e. the result is a genuine FullInfoState, matching
   its "always 4" contract.
3. Zero engine errors for well-formed team-preview choices.
4. Index-fidelity regression (same bug class as the mid-battle position-
   flip regression in test_bridge.py): a known TeamPreviewAction must
   land the intended species in the intended LEFT/RIGHT slots, not
   silently scrambled.
5. Send-out-effects check: a picked lead with Intimidate against enemy
   leads with no immunity must actually apply -1 Atk to both of them
   (doubles-wide) - proves team preview resolves through the REAL
   engine (abilities firing on send-out), not a hand-constructed
   zero-effect turn-1 state.
6. Snapshot immutability: two step_team_preview calls off the same
   parent handle both still work (parent never mutated).

Needs node + the built vendor sim (vendor/pokemon-showdown/dist).
Run from the project root: python -m engine.test_bridge_team_preview
"""

import json
from pathlib import Path

from engine.bridge import EngineBridge
from schema.battle_state import FieldState, OwnPokemon, Position, TeamPreviewAction
from schema.full_info_state import TeamPreviewRootState

_ROOT = Path(__file__).resolve().parent.parent
_SPECIES_STATS = json.loads((_ROOT / "reference" / "species_stats.json").read_text(encoding="utf-8"))
_SPECIES_DATA = json.loads((_ROOT / "reference" / "species_data.json").read_text(encoding="utf-8"))

FORMAT = "gen9championsvgc2026regmb"
failures = []


def check(name: str, ok: bool, detail: str = ""):
    print(f"  {name} [{'ok' if ok else 'FAIL'}]{' ' + str(detail) if detail and not ok else ''}")
    if not ok:
        failures.append(name)


def flat(species):
    base = _SPECIES_STATS[species]["base_stats"]
    return base["hp"] + 75, {k: base[k] + 20 for k in ("atk", "def", "spa", "spd", "spe")}


def mk(species: str, ability: str, item: str | None = None) -> OwnPokemon:
    from schema.battle_state import MoveSlot
    max_hp, stats = flat(species)
    return OwnPokemon(
        species=species, position=None, hp=max_hp, max_hp=max_hp, stats=stats,
        ability=ability, item=item,
        moves=[MoveSlot(move=m, pp=16, max_pp=16) for m in _SPECIES_DATA[species]["moves"][:4]],
    )


# incineroar (Intimidate) leads LEFT, garchomp leads RIGHT
MY_ROSTER = [
    mk("incineroar", "intimidate"), mk("garchomp", "roughskin", "lifeorb"),
    mk("clefable", "unaware"), mk("annihilape", "defiant"),
    mk("tyranitar", "sandstream"), mk("skarmory", "sturdy"),
]
# charizard leads LEFT, sylveon leads RIGHT - neither has intimidate immunity
OPP_ROSTER = [
    mk("charizard", "blaze"), mk("sylveon", "pixilate"),
    mk("archaludon", "stamina"), mk("pelipper", "drizzle"),
    mk("grimmsnarl", "prankster"), mk("metagross", "clearbody"),
]
MY_ACTION = TeamPreviewAction(bring=[0, 1, 2, 3], lead_order=[0, 1])   # incineroar L, garchomp R
OPP_ACTION = TeamPreviewAction(bring=[0, 1, 2, 3], lead_order=[0, 1])  # charizard L, sylveon R

tp_state = TeamPreviewRootState(field=FieldState(), my_team=MY_ROSTER, opp_team=OPP_ROSTER)

with EngineBridge(FORMAT) as bridge:
    print("init_team_preview_battle")
    handle = bridge.init_team_preview_battle(tp_state)
    check("returns a handle", isinstance(handle, int) and handle > 0, handle)

    print("\nstep_team_preview: foundational trim-to-4 + turn check")
    result = bridge.step_team_preview(handle, MY_ACTION, OPP_ACTION)
    check("no engine errors", result.errors == [], result.errors)
    check("my_team trimmed to exactly 4", len(result.state.my_team) == 4, len(result.state.my_team))
    check("opp_team trimmed to exactly 4", len(result.state.opp_team) == 4, len(result.state.opp_team))
    check("turn is 1", result.state.turn == 1, result.state.turn)
    check("a new handle is returned (not terminal)", result.handle is not None, result.terminal)

    print("\nindex fidelity: intended species land in the intended LEFT/RIGHT slots")
    my_left = next((m for m in result.state.my_team if m.position == Position.LEFT), None)
    my_right = next((m for m in result.state.my_team if m.position == Position.RIGHT), None)
    opp_left = next((m for m in result.state.opp_team if m.position == Position.LEFT), None)
    opp_right = next((m for m in result.state.opp_team if m.position == Position.RIGHT), None)
    check("my LEFT is incineroar", my_left is not None and my_left.species == "incineroar",
          my_left.species if my_left else None)
    check("my RIGHT is garchomp", my_right is not None and my_right.species == "garchomp",
          my_right.species if my_right else None)
    check("opp LEFT is charizard", opp_left is not None and opp_left.species == "charizard",
          opp_left.species if opp_left else None)
    check("opp RIGHT is sylveon", opp_right is not None and opp_right.species == "sylveon",
          opp_right.species if opp_right else None)

    print("\nsend-out effects: my Incineroar's Intimidate actually fires through the real engine")
    check("opp charizard (LEFT) took -1 Atk from Intimidate", opp_left is not None and opp_left.boosts.atk == -1,
          opp_left.boosts.atk if opp_left else None)
    check("opp sylveon (RIGHT) took -1 Atk from Intimidate (doubles-wide)",
          opp_right is not None and opp_right.boosts.atk == -1, opp_right.boosts.atk if opp_right else None)

    print("\nsnapshot immutability: stepping the same parent handle twice")
    result_a = bridge.step_team_preview(handle, MY_ACTION, OPP_ACTION)
    result_b = bridge.step_team_preview(handle, MY_ACTION, OPP_ACTION)
    check("first repeat call succeeds with no errors", result_a.errors == [], result_a.errors)
    check("second repeat call succeeds with no errors", result_b.errors == [], result_b.errors)

print(f"\n{'PASS' if not failures else 'FAIL: ' + ', '.join(failures)}")
