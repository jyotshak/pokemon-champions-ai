"""Fixture test for replays/reconstruct.py: a hand-built protocol log
exercising the state-tracking that matters for training examples -
HP fractions, mega via |detailschange|, Trick Room via |-fieldstart|,
side conditions, boosts (and their reset on switch-out), move-reveal,
turn-start action extraction, and outcome labeling per side.

Run from the project root: python -m replays.test_reconstruct
"""

from replays.parse_replays import parse_replay
from replays.reconstruct import reconstruct

failures = []


def check(name, ok, detail=""):
    print(f"  {name} [{'ok' if ok else 'FAIL'}]{' ' + str(detail) if detail and not ok else ''}")
    if not ok:
        failures.append(name)


LOG = "\n".join([
    "|player|p1|Alice|1|1500",
    "|player|p2|Bob|2|1400",
    "|poke|p1|Kangaskhan, F|", "|poke|p1|Farigiraf, M|",
    "|poke|p2|Incineroar, M|", "|poke|p2|Garchomp, M|",
    "|start",
    "|switch|p1a: Kangaskhan|Kangaskhan, L50, F|100/100",
    "|switch|p1b: Farigiraf|Farigiraf, L50, M|100/100",
    "|switch|p2a: Incineroar|Incineroar, L50, M|100/100",
    "|switch|p2b: Garchomp|Garchomp, L50, M|100/100",
    "|turn|1",
    "|-mega|p1a: Kangaskhan|Kangaskhanite",
    "|detailschange|p1a: Kangaskhan|Kangaskhan-Mega, L50, F",
    "|move|p1a: Kangaskhan|Fake Out|p2b: Garchomp",
    "|move|p1b: Farigiraf|Trick Room|p1b: Farigiraf",
    "|-fieldstart|move: Trick Room|[of] p1b: Farigiraf",
    "|move|p2a: Incineroar|Fake Out|p1a: Kangaskhan",
    "|-unboost|p1a: Kangaskhan|atk|1",
    "|move|p2b: Garchomp|Earthquake|p1a: Kangaskhan",
    "|-damage|p1a: Kangaskhan|50/100",
    "|-sidestart|p2: Bob|move: Tailwind",
    "|turn|2",
    "|switch|p1a: Farigiraf|Farigiraf, L50, M|100/100",  # NOTE: illustrative
    "|move|p2a: Incineroar|Flare Blitz|p1b: Farigiraf",
    "|-damage|p1b: Farigiraf|0 fnt",
    "|faint|p1b: Farigiraf",
    "|win|Alice",
])

record = parse_replay({"id": "t-1", "format": "[Gen 9 Champions] VGC 2026 Reg M-B",
                       "players": ["Alice", "Bob"], "rating": 1450, "log": LOG})
ex = reconstruct(record, LOG)
by = {(e["side"], e["turn"]): e for e in ex}

print("per-side examples emitted for each turn a side acted")
check("p1 turn-1 example exists", ("p1", 1) in by)
check("p2 turn-1 example exists", ("p2", 1) in by)

print("\nturn-1 decision state is PRE-turn (no TR yet, full HP, no mega applied)")
s1 = by[("p1", 1)]["state"]
check("turn-1 TR still False (set up DURING the turn)", s1["trick_room"] is False, s1["trick_room"])
check("turn-1 Kangaskhan still base forme, full HP",
      s1["me"]["mons"]["Kangaskhan"]["hp"] == 1.0 and "Kangaskhan-Mega" not in s1["me"]["mons"], s1["me"]["mons"])

print("\nturn-1 actions: mega flagged on the move, correct targets")
a1 = by[("p1", 1)]["action"]
check("Kangaskhan Fake Out flagged mega", a1["a"]["mega"] is True and a1["a"]["move"] == "Fake Out", a1["a"])
check("Fake Out targets p2b", a1["a"]["target"] == "p2b", a1["a"])
check("Farigiraf Trick Room (self-target)", a1["b"]["move"] == "Trick Room", a1["b"])

print("\nturn-2 decision state reflects turn-1 resolution (TR up, mega forme, Tailwind, damage, unboost)")
s2 = by[("p1", 2)]["state"]
check("turn-2 TR now True", s2["trick_room"] is True, s2["trick_room"])
check("turn-2 Kangaskhan is Mega forme", "Kangaskhan-Mega" in s2["me"]["mons"], list(s2["me"]["mons"]))
check("turn-2 Kangaskhan-Mega HP halved (~0.5)", abs(s2["me"]["mons"]["Kangaskhan-Mega"]["hp"] - 0.5) < 1e-9,
      s2["me"]["mons"].get("Kangaskhan-Mega", {}).get("hp"))
check("turn-2 opp Tailwind is up", s2["opp"]["cond"]["tailwind"] is True, s2["opp"]["cond"])
check("turn-2 Kangaskhan-Mega atk unboosted (-1)", s2["me"]["mons"]["Kangaskhan-Mega"]["boosts"].get("atk") == -1,
      s2["me"]["mons"]["Kangaskhan-Mega"]["boosts"])

print("\noutcome labeling per side (Alice/p1 won)")
check("p1 example won=True", by[("p1", 1)]["won"] is True)
check("p2 example won=False", by[("p2", 1)]["won"] is False)
check("per-side rating carried (p1=1500, p2=1400)",
      by[("p1", 1)]["rating"] == 1500 and by[("p2", 1)]["rating"] == 1400)

print(f"\n{'PASS' if not failures else 'FAIL: ' + ', '.join(failures)}")
