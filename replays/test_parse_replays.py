"""Fixture-based test for replays/parse_replays.py - runs against a
hand-built protocol log (not the live cache, which is gitignored and
varies), pinning the exact quirks that already bit during the spike:
 - a trailing `|player|p1|` (blank) leave-event must NOT wipe the name
 - per-player rating is |player| index 5 (index 4 is the avatar)
 - a |showteam| packed payload contains '|' and must survive splitting
 - |move| actor/target slots, mega flag, and |win|->slot resolution

Run from the project root: python -m replays.test_parse_replays
"""

from replays.parse_replays import parse_packed_team, parse_replay

failures = []


def check(name, ok, detail=""):
    print(f"  {name} [{'ok' if ok else 'FAIL'}]{' ' + str(detail) if detail and not ok else ''}")
    if not ok:
        failures.append(name)


PACKED = ("Raichu||RaichuniteY|LightningRod|ZapCannon,FocusBlast,FakeOut,Protect|Bold||F|||50|"
          "]Basculegion||ChoiceScarf|Adaptability|WaveCrash,LastRespects,AquaJet,IcyWind|Adamant||M|||50|")

LOG = "\n".join([
    "|player|p1|Alice|101|1480",
    "|player|p2|Bob|skier|1523",
    "|poke|p1|Raichu, F|",
    "|poke|p1|Basculegion, M|",
    "|poke|p2|Incineroar, M|",
    f"|showteam|p1|{PACKED}",
    "|showteam|p2|Incineroar||AssaultVest|Intimidate|FakeOut,Flareblitz,KnockOff,UTurn|Adamant||M|||50|",
    "|teampreview",
    "|start",
    "|switch|p1a: Raichu|Raichu, F|100/100",
    "|switch|p2a: Incineroar|Incineroar, M|100/100",
    "|turn|1",
    "|move|p2a: Incineroar|Fake Out|p1a: Raichu",
    "|-mega|p1a: Raichu|Raichunite Y",
    "|move|p1a: Raichu|Zap Cannon|p2a: Incineroar",
    "|turn|2",
    "|switch|p1a: Basculegion|Basculegion, M|100/100",
    "|move|p2a: Incineroar|Flare Blitz|p1a: Basculegion",
    "|faint|p1a: Basculegion",
    "|player|p1|",          # trailing leave-event: must not blank Alice
    "|win|Bob",
])


rec = parse_replay({"id": "x-1", "format": "[Gen 9 Champions] VGC 2026 Reg M-B (Bo3)",
                    "players": ["Alice", "Bob"], "rating": 1400, "log": LOG})

print("packed-team parse (the '|'-in-payload case)")
sets = parse_packed_team(PACKED)
check("two mons parsed", len(sets) == 2, len(sets))
check("Raichu item/ability", sets[0]["item"] == "RaichuniteY" and sets[0]["ability"] == "LightningRod", sets[0])
check("Raichu 4 moves", sets[0]["moves"] == ["ZapCannon", "FocusBlast", "FakeOut", "Protect"], sets[0]["moves"])
check("Basculegion nature/level", sets[1]["nature"] == "Adamant" and sets[1]["level"] == 50, sets[1])

print("\nplayer names + per-player ratings (rating is index 5, not the avatar)")
p = {x["slot"]: x for x in rec["players"]}
check("p1 name survives the trailing blank leave-event", p["p1"]["name"] == "Alice", p["p1"])
check("p1 rating = 1480 (not avatar 101)", p["p1"]["rating"] == 1480, p["p1"]["rating"])
check("p2 rating = 1523", p["p2"]["rating"] == 1523, p["p2"]["rating"])

print("\nsheets (Bo3 open teams) fully populated for both sides")
check("p1 sheet has 2 sets", rec["sheets"]["p1"] and len(rec["sheets"]["p1"]) == 2)
check("p2 sheet parsed (Incineroar AV/Intimidate)",
      rec["sheets"]["p2"][0]["item"] == "AssaultVest" and rec["sheets"]["p2"][0]["ability"] == "Intimidate",
      rec["sheets"]["p2"][0])

print("\npreview species reveals")
check("p1 preview = [Raichu, Basculegion]", rec["preview"]["p1"] == ["Raichu", "Basculegion"], rec["preview"]["p1"])

print("\nturn events: moves (actor/target/mega), switches, faints, and winner slot")
check("2 turns", len(rec["turns"]) == 2, len(rec["turns"]))
t1 = rec["turns"][0]
raichu_move = next(m for m in t1["moves"] if m["slot"] == "p1a")
check("Raichu move targets p2a", raichu_move["target"] == "p2a", raichu_move)
check("Raichu flagged mega this turn", raichu_move["mega"] is True, raichu_move)
fakeout = next(m for m in t1["moves"] if m["slot"] == "p2a")
check("Incineroar Fake Out NOT mega", fakeout["mega"] is False, fakeout)
t2 = rec["turns"][1]
check("turn 2 switch to Basculegion", any(s["species"] == "Basculegion" for s in t2["switches"]), t2["switches"])
check("turn 2 faint on p1a", "p1a" in t2["faints"], t2["faints"])
check("winner resolves to p2 (Bob)", rec["winner_slot"] == "p2", rec["winner_slot"])
check("is_bo3 detected from format", rec["is_bo3"] is True)

print(f"\n{'PASS' if not failures else 'FAIL: ' + ', '.join(failures)}")
