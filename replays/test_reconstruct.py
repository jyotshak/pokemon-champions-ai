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

print("\nBo3 Open Team Sheet: a mon's FULL moveset/item/ability is known at first "
      "reveal, not built up one used-move at a time")
# Regression for the reconstruction self-state gap
# ([[net-external-review-2026-07-21]]): every turn-1 example previously had 0
# known own moves even with a full sheet attached and unused. Real VGC Open
# Team Sheets reveal BOTH players' complete 6-mon rosters (item/ability/
# moves) before the set starts - confirmed on real data - so this must work
# for BOTH sides, not just "me".
SHEET_LOG = "\n".join([
    "|player|p1|Alice|1|1500",
    "|player|p2|Bob|2|1400",
    "|showteam|p1|Kang|Kangaskhan|Kangaskhanite|Scrappy|FakeOut,DoubleEdge,SuckerPunch,Protect]"
    "Farigiraf|Farigiraf||ArmorTail|TrickRoom,Psychic,Protect,FoulPlay]"
    "Sylveon|Sylveon|FairyFeather|Pixilate|HyperVoice,HyperBeam,Protect,LightScreen",
    "|showteam|p2|Incin|Incineroar||Intimidate|FakeOut,FlareBlitz,PartingShot,KnockOff]"
    "Garchomp|Garchomp||RoughSkin|Earthquake,DragonClaw,RockSlide,Protect",
    "|poke|p1|Kangaskhan, F|", "|poke|p1|Farigiraf, M|", "|poke|p1|Sylveon, F|",
    "|poke|p2|Incineroar, M|", "|poke|p2|Garchomp, M|",
    "|start",
    "|switch|p1a: Kangaskhan|Kangaskhan, L50, F|100/100",
    "|switch|p1b: Farigiraf|Farigiraf, L50, M|100/100",
    "|switch|p2a: Incineroar|Incineroar, L50, M|100/100",
    "|switch|p2b: Garchomp|Garchomp, L50, M|100/100",
    "|turn|1",
    "|move|p1a: Kangaskhan|Fake Out|p2b: Garchomp",
    "|move|p2a: Incineroar|Fake Out|p1a: Kangaskhan",
    "|turn|2",
    "|switch|p1b: Sylveon|Sylveon, L50, F|100/100",  # Sylveon only NOW switches in for real
    "|move|p1a: Kangaskhan|Fake Out|p2b: Garchomp",
    "|move|p2a: Incineroar|Fake Out|p1a: Kangaskhan",
    "|win|Alice",
])
sheet_record = parse_replay({"id": "t-2", "format": "[Gen 9 Champions] VGC 2026 Reg M-B (Bo3)",
                             "players": ["Alice", "Bob"], "rating": 1450, "log": SHEET_LOG})
check("parse_replay picked up both sheets",
      bool(sheet_record["sheets"]["p1"]) and bool(sheet_record["sheets"]["p2"]))
sheet_ex = reconstruct(sheet_record, SHEET_LOG)
sheet_by = {(e["side"], e["turn"]): e for e in sheet_ex}

s1_p1 = sheet_by[("p1", 1)]["state"]
kang = s1_p1["me"]["mons"]["Kangaskhan"]
check("MY (p1) Kangaskhan has all 4 sheet moves at turn 1, not just the 1 used so far",
      set(kang["moves"]) == {"FakeOut", "DoubleEdge", "SuckerPunch", "Protect"}, kang["moves"])
check("MY Kangaskhan's item/ability seeded from the sheet",
      kang["item"] == "Kangaskhanite" and kang["ability"] == "Scrappy", (kang["item"], kang["ability"]))
fari = s1_p1["me"]["mons"]["Farigiraf"]
check("MY Farigiraf (never yet acted) still has its full sheet moveset",
      set(fari["moves"]) == {"TrickRoom", "Psychic", "Protect", "FoulPlay"}, fari["moves"])

# Open Team Sheets are OPEN - the opponent's sheet is public knowledge too,
# a real VGC mechanic (confirmed: real Bo3 replay sheets carry both p1 AND
# p2's full 6-mon rosters). So OPP must ALSO be fully seeded from ITS OWN
# sheet, symmetrically, not just "me".
opp_incin = s1_p1["opp"]["mons"]["Incineroar"]
check("OPP (p2) Incineroar ALSO fully seeded from p2's own open sheet "
      "(Open Team Sheets reveal both rosters to both players)",
      set(opp_incin["moves"]) == {"FakeOut", "FlareBlitz", "PartingShot", "KnockOff"}, opp_incin["moves"])
check("OPP Incineroar's item/ability seeded too (item=None here, matching the fixture)",
      opp_incin["ability"] == "Intimidate", opp_incin["ability"])

s1_p2 = sheet_by[("p2", 1)]["state"]
p2_own_garchomp = s1_p2["me"]["mons"]["Garchomp"]
check("symmetric check from p2's own POV: Garchomp fully seeded from p2's sheet",
      set(p2_own_garchomp["moves"]) == {"Earthquake", "DragonClaw", "RockSlide", "Protect"},
      p2_own_garchomp["moves"])

print("\nfull BROUGHT ROSTER known from turn 1, not just the 2 mons currently active - "
      "Sylveon doesn't switch in for real until turn 2, but a real player already knows "
      "their whole brought team from team preview")
check("Sylveon present in the turn-1 snapshot despite not yet being switched in",
      "Sylveon" in s1_p1["me"]["mons"], list(s1_p1["me"]["mons"]))
sylveon_pre = s1_p1["me"]["mons"].get("Sylveon", {})
check("Sylveon's full sheet moveset already known at turn 1 (Bo3)",
      set(sylveon_pre.get("moves", [])) == {"HyperVoice", "HyperBeam", "Protect", "LightScreen"},
      sylveon_pre.get("moves"))
check("Sylveon correctly flagged not-yet-active at turn 1 (no active slot claims it)",
      "Sylveon" not in s1_p1["me"]["active"].values(), s1_p1["me"]["active"])

print("\nBo1 (no sheet) is unaffected - old incremental-reveal-only behavior")
bo1_record = record  # the module's original Bo1-format fixture from above
check("Bo1 sheets are None (nothing to seed from)",
      bo1_record["sheets"]["p1"] is None and bo1_record["sheets"]["p2"] is None)
bo1_s1 = by[("p1", 1)]["state"]
check("Bo1 turn-1 (PRE-turn snapshot): Kangaskhan has 0 known moves - Fake Out "
      "hasn't been used yet at this snapshot, and there's no sheet to seed from "
      "(this exact gap - unavoidable for Bo1 - is what the Bo3 fix above closes)",
      bo1_s1["me"]["mons"]["Kangaskhan"]["moves"] == [],
      bo1_s1["me"]["mons"]["Kangaskhan"]["moves"])
bo1_s2 = by[("p1", 2)]["state"]
check("Bo1 turn-2: Kangaskhan (now Mega) shows only Fake Out (used in turn 1), "
      "NOT the full moveset - still incremental-only, no full-set fallback exists for Bo1",
      bo1_s2["me"]["mons"]["Kangaskhan-Mega"]["moves"] == ["Fake Out"],
      bo1_s2["me"]["mons"]["Kangaskhan-Mega"]["moves"])

print(f"\n{'PASS' if not failures else 'FAIL: ' + ', '.join(failures)}")
