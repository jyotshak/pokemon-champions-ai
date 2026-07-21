"""Validates model/solver_game.py's keying contract in isolation (no
engine process needed) — the exact property whose violation crashed a
real match twice: my_key must be identical across states that differ
only in opponent hidden info, even when that hidden info manifests as
something engine-visible like a bookkeeping volatile.

Run from the project root: python -m model.test_solver_game
"""

from model.solver_game import EngineGame, _full_key, _public_key
from schema.battle_state import Boosts, FieldState, MoveSlot, OwnPokemon, Position

failures = []


def check(name: str, ok: bool, detail: str = ""):
    print(f"  {name} [{'ok' if ok else 'FAIL'}]{' ' + str(detail) if detail and not ok else ''}")
    if not ok:
        failures.append(name)


def mon(species, position=None, fainted=False, hp=100, max_hp=100, item=None,
        volatiles=(), moves=("tackle",)):
    return OwnPokemon(
        species=species, position=position, fainted=fainted, hp=hp, max_hp=max_hp,
        stats={"atk": 100, "def": 100, "spa": 100, "spd": 100, "spe": 100},
        ability="pressure", item=item, boosts=Boosts(),
        moves=[MoveSlot(move=m, pp=10, max_pp=10) for m in moves],
        volatiles=[__import__("schema.battle_state", fromlist=["VolatileState"]).VolatileState(name=v) for v in volatiles],
    )


def state(opp_incineroar_volatiles):
    from schema.full_info_state import FullInfoState
    return FullInfoState(
        turn=4, field=FieldState(),
        my_team=[mon("charizard", Position.LEFT), mon("incineroar", Position.RIGHT)],
        opp_team=[
            mon("charizard", Position.LEFT, hp=49, max_hp=100),
            mon("incineroar", Position.RIGHT, hp=68, max_hp=100, item="metronome",
                volatiles=opp_incineroar_volatiles),
        ],
    )


print("opponent bookkeeping volatile from a hidden item must not affect my_key")
world_no_volatile = state(opp_incineroar_volatiles=())
world_with_volatile = state(opp_incineroar_volatiles=("metronome",))
check("public keys match despite differing opponent volatiles",
      _public_key(world_no_volatile) == _public_key(world_with_volatile))

print("\nEngineGame root construction must not raise for this exact case")
class _FakeBridge:
    def init_battle(self, s):
        return id(s), s

try:
    EngineGame(_FakeBridge(), [world_no_volatile, world_with_volatile])
    check("no root my_key ValueError", True)
except ValueError as e:
    check("no root my_key ValueError", False, str(e)[:80])

print("\nmy own volatiles still affect my_key (I fully observe myself)")
mine_a = state(opp_incineroar_volatiles=())
mine_b = state(opp_incineroar_volatiles=())
mine_b.my_team[1].volatiles = [__import__("schema.battle_state", fromlist=["VolatileState"]).VolatileState(name="confusion")]
check("my_key differs when MY volatiles differ", _public_key(mine_a) != _public_key(mine_b))

print("\nopponent's own full key (opp_key basis) still sees their volatiles within one world")
full_no = _full_key(world_no_volatile)
full_with = _full_key(world_with_volatile)
check("full key differs (opponent conditions on their own true volatiles)", full_no != full_with)

print("\ntrapped must affect my_key (it changes my legal action set - switch offered or not)")
free = state(opp_incineroar_volatiles=())
trapped_state = state(opp_incineroar_volatiles=())
trapped_state.my_team[1].trapped = True
check("my_key differs when MY trapped status differs", _public_key(free) != _public_key(trapped_state))

print(f"\n{'PASS' if not failures else 'FAIL: ' + ', '.join(failures)}")
