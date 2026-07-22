"""Phase 1 test for harness/net_translate.py: the schema -> net "reconstruct
state" bridge. Verifies field/enum mapping (weather/status/boost keys/slots),
active-vs-bench placement, and that the result actually encodes through
model/encoding.py::encode_for_inference without error and with the right
tokens.

Run from the project root: python -m harness.test_net_translate
"""

from harness.net_translate import battle_state_to_netstate, full_info_state_to_netstate
from schema.battle_state import (
    BattleState, FieldState, SideConditions, Boosts, MoveSlot, OwnPokemon, OpponentPokemon,
    Position, Status, Weather, Terrain,
)
from schema.full_info_state import FullInfoState
from model.encoding import encode_for_inference, resolve_species, MAX_MONS, _lookup, ITEM_VOCAB

failures = []


def check(name, ok, detail=""):
    print(f"  {name} [{'ok' if ok else 'FAIL'}]{'' if ok else ' ' + str(detail)}")
    if not ok:
        failures.append(name)


def own(species, position=None, hp=100, max_hp=100, status=Status.NONE, boosts=None,
        item=None, ability="Intimidate", moves=("Fake Out",), fainted=False):
    return OwnPokemon(
        species=species, position=position, fainted=fainted, hp=hp, max_hp=max_hp,
        status=status, stats={"atk": 100, "def": 100, "spa": 100, "spd": 100, "spe": 100},
        boosts=boosts or Boosts(), ability=ability, item=item,
        moves=[MoveSlot(move=m, pp=5, max_pp=5) for m in moves],
    )


def opp(species, position=None, hp_pct=100.0, status=Status.NONE, boosts=None,
        revealed_moves=(), revealed_item=None, revealed_ability=None, fainted=False):
    return OpponentPokemon(
        species=species, position=position, fainted=fainted, hp_pct=hp_pct, status=status,
        boosts=boosts or Boosts(), revealed_moves=list(revealed_moves),
        revealed_item=revealed_item, revealed_ability=revealed_ability,
    )


print("battle_state_to_netstate: live state (my full-info, opp revealed-only)")
bs = BattleState(
    format_id="gen9championsvgc2026regmb", turn=3,
    field=FieldState(weather=Weather.SUN, terrain=Terrain.NONE, trick_room_turns=0,
                     my_side=SideConditions(tailwind_turns=3),
                     opp_side=SideConditions(reflect_turns=5)),
    my_active=[own("Incineroar", Position.LEFT, hp=50, status=Status.BRN,
                   boosts=Boosts(atk=-1, spe=2), item="Assault Vest",
                   moves=["Fake Out", "Flare Blitz"]),
               own("Whimsicott", Position.RIGHT, ability="Prankster", moves=["Tailwind"])],
    my_bench=[own("Sylveon", None, ability="Pixilate", moves=["Hyper Voice"])],
    opp_active=[opp("Garchomp", Position.LEFT, hp_pct=80.0, revealed_moves=["Rock Slide"]),
                opp("Kingambit", Position.RIGHT, hp_pct=100.0)],
    opp_bench=[opp("Amoonguss", None)],
)
ns = battle_state_to_netstate(bs)
check("weather sun -> SunnyDay", ns["weather"] == "SunnyDay", ns["weather"])
check("trick_room False", ns["trick_room"] is False)
check("me tailwind flag from turns>0", ns["me"]["cond"]["tailwind"] is True)
check("opp reflect flag from turns>0", ns["opp"]["cond"]["reflect"] is True)
check("me active a=Incineroar (LEFT), b=Whimsicott (RIGHT)",
      ns["me"]["active"] == {"a": "Incineroar", "b": "Whimsicott"}, ns["me"]["active"])
check("Sylveon benched (not active)", "Sylveon" in ns["me"]["mons"]
      and ns["me"]["active"]["a"] != "Sylveon" and ns["me"]["active"]["b"] != "Sylveon")
inc = ns["me"]["mons"]["Incineroar"]
check("Incineroar hp 50/100 -> 0.5", abs(inc["hp"] - 0.5) < 1e-9, inc["hp"])
check("Incineroar brn status", inc["status"] == "brn", inc["status"])
check("Incineroar boost keys mapped (atk -1, spe +2)",
      inc["boosts"]["atk"] == -1 and inc["boosts"]["spe"] == 2, inc["boosts"])
check("Incineroar item carried", inc["item"] == "Assault Vest", inc["item"])
check("Incineroar moves carried", inc["moves"] == ["Fake Out", "Flare Blitz"], inc["moves"])
gar = ns["opp"]["mons"]["Garchomp"]
check("opp Garchomp hp 80% -> 0.8", abs(gar["hp"] - 0.8) < 1e-9, gar["hp"])
check("opp Garchomp revealed move only", gar["moves"] == ["Rock Slide"], gar["moves"])
check("opp hidden item absent (None)", gar["item"] is None)

print("\nencode_for_inference on the bridged live state (must not crash; tokens right)")
enc = encode_for_inference(ns)
check("me token0 is Incineroar", enc["species"][0] == resolve_species("Incineroar"), enc["species"][0])
check("opp token starts at MAX_MONS = Garchomp",
      enc["species"][MAX_MONS] == resolve_species("Garchomp"), enc["species"][MAX_MONS])
check("me token0 flagged is_me & active", enc["numeric"][0][1] == 1.0 and enc["numeric"][0][2] == 1.0)
check("meta present, shape (12,)", enc["meta_item"].shape == (2 * MAX_MONS,), enc["meta_item"].shape)

print("\nfull_info_state_to_netstate: determinized leaf (both sides full-info)")
fis = FullInfoState(
    turn=4,
    field=FieldState(weather=Weather.RAIN, terrain=Terrain.ELECTRIC, trick_room_turns=2),
    my_team=[own("Pelipper", Position.LEFT, ability="Drizzle", moves=["Hurricane"]),
             own("Archaludon", Position.RIGHT, moves=["Electro Shot"])],
    opp_team=[own("Garchomp", Position.LEFT, item="Life Orb", moves=["Earthquake"]),
              own("Kingambit", Position.RIGHT, item="Leftovers", moves=["Sucker Punch"])],
)
ns2 = full_info_state_to_netstate(fis)
check("leaf weather rain -> RainDance", ns2["weather"] == "RainDance", ns2["weather"])
check("leaf terrain electric -> 'Electric Terrain'", ns2["terrain"] == "Electric Terrain", ns2["terrain"])
check("leaf trick_room True (turns>0)", ns2["trick_room"] is True)
check("leaf opp is full-info (Garchomp item Life Orb visible)",
      ns2["opp"]["mons"]["Garchomp"]["item"] == "Life Orb", ns2["opp"]["mons"]["Garchomp"]["item"])
enc2 = encode_for_inference(ns2)
check("leaf encodes, opp token0 item = Life Orb idx",
      enc2["item"][MAX_MONS] == _lookup(ITEM_VOCAB, "Life Orb"), enc2["item"][MAX_MONS])

print(f"\n{'PASS' if not failures else 'FAIL: ' + ', '.join(failures)}")
