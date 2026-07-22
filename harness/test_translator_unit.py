"""Fast, no-server unit test for harness/translator.py's own_pokemon(),
pinning the exact bug a real match hit: a move Showdown reports as
currently disabled (Fake Out after turn 1, Torment/Taunt/Disable/
choice-lock) must come through as MoveSlot.disabled=True, or a policy can
"choose" it, get rejected by the server, and stall the turn retrying it
forever. Uses lightweight stand-ins instead of a real poke-env Pokemon
object — only the attributes own_pokemon() actually reads.

Run from the project root: python -m harness.test_translator_unit
"""

from types import SimpleNamespace

from harness.translator import own_pokemon
from schema.battle_state import Position

failures = []


def check(name: str, ok: bool, detail: str = ""):
    print(f"  {name} [{'ok' if ok else 'FAIL'}]{' ' + str(detail) if detail and not ok else ''}")
    if not ok:
        failures.append(name)


def fake_move(move_id, pp=12, max_pp=16):
    return SimpleNamespace(id=move_id, current_pp=pp, max_pp=max_pp)


def fake_pokemon(moves, must_recharge=False, preparing_move=None):
    return SimpleNamespace(
        species="incineroar", level=50, fainted=False,
        current_hp=180, max_hp=192, status=None, stats={"atk": 100},
        boosts={}, ability="intimidate", item="sitrusberry",
        moves={m.id: m for m in moves}, tera_type=None, is_terastallized=False,
        effects={}, must_recharge=must_recharge, preparing_move=preparing_move,
    )


mon = fake_pokemon([fake_move("fakeout"), fake_move("flareblitz"), fake_move("protect")])

print("active mon: fake out currently disabled by Showdown, others not")
result = own_pokemon(mon, Position.LEFT, available_move_ids={"flareblitz", "protect"})
by_id = {ms.move: ms for ms in result.moves}
check("fakeout marked disabled", by_id["fakeout"].disabled is True)
check("flareblitz not disabled", by_id["flareblitz"].disabled is False)
check("protect not disabled", by_id["protect"].disabled is False)
check("pp/max_pp still passed through", by_id["fakeout"].pp == 12 and by_id["fakeout"].max_pp == 16)

print("\nno available_move_ids given (bench mon) -> nothing marked disabled")
bench_result = own_pokemon(mon, None)
check("all moves default to not disabled", all(not ms.disabled for ms in bench_result.moves))

print("\nempty available set (e.g. mid-turn switch-only request) -> all disabled, not a crash")
empty_result = own_pokemon(mon, Position.LEFT, available_move_ids=set())
check("all moves disabled, no exception", all(ms.disabled for ms in empty_result.moves))

# A forced continuation (recharge / Struggle / locked two-turn move) offers a
# SYNTHETIC move id that is not in the mon's real moveset. own_pokemon must
# keep the REAL, engine-buildable moveset here: these OwnPokemon feed
# init_battle -> buildSet for search rollouts, and rebuilding a team from a
# synthetic id yields pp/max_pp = null and a FullInfoState ValidationError.
# The "no legal move" that results is resolved at the order boundary instead
# (harness/actions.py::_forced_move) - see harness/test_actions.py.
print("\nforced continuation (recharge): real moveset preserved for engine rebuild")
recharge = own_pokemon(mon, Position.LEFT, available_move_ids={"recharge"})
check("keeps the mon's 3 REAL moves (not the synthetic id)",
      {ms.move for ms in recharge.moves} == {"fakeout", "flareblitz", "protect"},
      [ms.move for ms in recharge.moves])
check("real pp/max_pp preserved (engine-buildable, never null)",
      all(isinstance(ms.pp, int) and isinstance(ms.max_pp, int) for ms in recharge.moves))
check("all real moves marked disabled (none is legal this turn)",
      all(ms.disabled for ms in recharge.moves))

# own_pokemon must carry must_recharge/preparing_move through as volatiles -
# these are SEPARATE poke-env attributes from .effects (confirmed empirically
# against a real Pokemon object: setting must_recharge=True left .effects
# empty), so model/action_space.py's forced-continuation checks and
# engine/bridge.js's matching volatile reconstruction have nothing to key on
# unless own_pokemon reads them directly.
print("\nmust_recharge flows through as a volatile (own_pokemon, not just the disabled-move marking)")
recharging_mon = fake_pokemon([fake_move("hypervoice"), fake_move("hyperbeam")], must_recharge=True)
recharge_translated = own_pokemon(recharging_mon, Position.LEFT, available_move_ids={"recharge"})
check("must_recharge volatile present",
      any(v.name == "must_recharge" for v in recharge_translated.volatiles), recharge_translated.volatiles)

print("\ntwo-turn-move charging flows through as a volatile, carrying the real move id")
charging_move_obj = fake_move("solarbeam")
charging_mon = fake_pokemon([fake_move("solarbeam"), fake_move("flamethrower")], preparing_move=charging_move_obj)
charging_translated = own_pokemon(charging_mon, Position.LEFT, available_move_ids={"solarbeam"})
two_turn = next((v for v in charging_translated.volatiles if v.name == "two_turn_move"), None)
check("two_turn_move volatile present with the real move id",
      two_turn is not None and two_turn.data.get("move") == "solarbeam", two_turn)

print("\nnormal mon: neither volatile present")
normal_translated = own_pokemon(mon, Position.LEFT, available_move_ids={"flareblitz", "protect"})
check("no forced-continuation volatiles",
      not any(v.name in ("must_recharge", "two_turn_move") for v in normal_translated.volatiles),
      normal_translated.volatiles)

print(f"\n{'PASS' if not failures else 'FAIL: ' + ', '.join(failures)}")
