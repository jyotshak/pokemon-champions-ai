"""Test model/encoding.py: vocab invariants, the species normalizer
(exact / mega-fold / cosmetic-prefix / UNK), and encode_state tensor
shapes + token layout + None-handling. Fixture-based; also runs a
species-coverage check over replays/examples/ if that corpus exists.

Run from the project root: python -m model.test_encoding
"""

import glob
import json
from pathlib import Path

import numpy as np

from model.encoding import (
    MAX_MONS, PAD, UNK, SPECIES_VOCAB, VOCAB_SIZES, encode_state, resolve_species,
    STATIC_DIM, N_TYPES, TYPE_INDEX, FEATURE_DIMS, _WEATHER, _TERRAIN,
)

failures = []


def check(name, ok, detail=""):
    ok = bool(ok)
    print(f"  {name} [{'ok' if ok else 'FAIL'}]" + ("" if ok else f" {detail}"))
    if not ok:
        failures.append(name)


def mon(species, hp=1.0, status=None, boosts=None, item=None, ability=None, fainted=False, moves=None):
    return {"species": species, "hp": hp, "status": status, "boosts": boosts or {},
            "item": item, "ability": ability, "fainted": fainted, "moves": moves or []}


def side(active, mons, cond=None):
    return {"active": active, "mons": mons,
            "cond": cond or {"tailwind": False, "reflect": False, "light_screen": False, "aurora_veil": False}}


print("vocab invariants: PAD=0, UNK=1, non-trivial sizes")
check("PAD/UNK reserved", PAD == 0 and UNK == 1)
check("species vocab > 200", VOCAB_SIZES["species"] > 200, VOCAB_SIZES)
check("move vocab > 300", VOCAB_SIZES["move"] > 300, VOCAB_SIZES)

print("\nspecies normalizer: exact / mega-fold / cosmetic-prefix / UNK")
check("exact id resolves", resolve_species("Incineroar") != UNK)
# Mega formes are DISTINCT species_stats entries (different stats/typing),
# so they get their own token - not folded to base. Only cosmetic/battle
# formes with no stat entry of their own fold down.
check("mega is a distinct non-UNK token (own entry, not base)",
      resolve_species("Kangaskhan-Mega") == SPECIES_VOCAB.get("kangaskhanmega") != UNK
      and resolve_species("Kangaskhan-Mega") != resolve_species("Kangaskhan"),
      (resolve_species("Kangaskhan-Mega"), resolve_species("Kangaskhan")))
check("cosmetic forme folds to base (Vivillon-Fancy -> vivillon)",
      resolve_species("Vivillon-Fancy") == SPECIES_VOCAB.get("vivillon"), resolve_species("Vivillon-Fancy"))
check("battle forme folds (Palafin-Hero -> palafin)",
      resolve_species("Palafin-Hero") == SPECIES_VOCAB.get("palafin"), resolve_species("Palafin-Hero"))
check("nonsense -> UNK", resolve_species("Notamon-9000") == UNK)

print("\nencode_state: shapes, token layout, None-handling, flags")
st = {
    "me": side({"a": "Incineroar", "b": "Whimsicott"},
               {"Incineroar": mon("Incineroar", hp=0.5, status="brn", ability="Intimidate",
                                  item="Assault Vest", moves=["Fake Out", "Flare Blitz"]),
                "Whimsicott": mon("Whimsicott", boosts={"spe": 2}),
                "Sylveon": mon("Sylveon")},  # revealed but benched
               {"tailwind": True, "reflect": False, "light_screen": False, "aurora_veil": False}),
    "opp": side({"a": "Kangaskhan-Mega", "b": None},
                {"Kangaskhan-Mega": mon("Kangaskhan-Mega", hp=0.8)}),
    "weather": None, "trick_room": True, "terrain": None,
}
enc = encode_state(st)
check("12 token slots", enc["species"].shape == (2 * MAX_MONS,), enc["species"].shape)
check("moves shape (12,4)", enc["moves"].shape == (2 * MAX_MONS, 4), enc["moves"].shape)
check("numeric shape (12,11)", enc["numeric"].shape == (2 * MAX_MONS, 11), enc["numeric"].shape)
check("mask counts 4 real tokens (3 me + 1 opp)", int(enc["mask"].sum()) == 4, enc["mask"].sum())

# me tokens occupy 0..; opp tokens start at MAX_MONS
check("me active[0] is Incineroar", enc["species"][0] == resolve_species("Incineroar"), enc["species"][0])
check("me token0 flagged is_me & active", enc["numeric"][0][1] == 1.0 and enc["numeric"][0][2] == 1.0,
      enc["numeric"][0][:3])
check("me token0 hp=0.5, status=brn(idx3)", abs(enc["numeric"][0][0] - 0.5) < 1e-6 and enc["status"][0] == 3,
      (enc["numeric"][0][0], enc["status"][0]))
check("opp token starts at slot MAX_MONS", enc["species"][MAX_MONS] == resolve_species("Kangaskhan-Mega"),
      enc["species"][MAX_MONS])
check("opp token flagged NOT me", enc["numeric"][MAX_MONS][1] == 0.0, enc["numeric"][MAX_MONS][1])
check("benched Sylveon present, flagged not-active", enc["species"][2] == resolve_species("Sylveon")
      and enc["numeric"][2][2] == 0.0, (enc["species"][2], enc["numeric"][2][2]))

# field: [weather one-hot(7), terrain one-hot(6), trick_room(1), me_cond(4), opp_cond(4)]
# = 22. One-hot (not a scalar index) since 2026-07-21 - see FEATURE_DIMS's
# own comment for why.
f = enc["field"]
W, T = len(_WEATHER) + 1, len(_TERRAIN) + 1   # 7, 6
check("field len 22 (weather one-hot 7 + terrain one-hot 6 + TR + 2x4 conds)",
      f.shape == (W + T + 1 + 8,), f.shape)
check("weather None -> one-hot index 0 (the real 'no weather' category, not a raw scalar)",
      f[0] == 1.0 and f[1:W].sum() == 0.0, f[:W])
check("terrain None -> one-hot index 0 too", f[W] == 1.0 and f[W + 1:W + T].sum() == 0.0, f[W:W + T])
check("trick_room flag set", f[W + T] == 1.0, f[W + T])
check("me tailwind flag set", f[W + T + 1] == 1.0, f[W + T + 1])
check("Whimsicott spe boost +2 -> 2/6", any(abs(enc["numeric"][i][4 + 4] - 2 / 6) < 1e-6
      for i in range(MAX_MONS) if enc["species"][i] == resolve_species("Whimsicott")))

print("\nstatic features: base stats (normalized) + type multi-hot, role-generalization lever")
check("static shape (12, STATIC_DIM)", enc["static"].shape == (2 * MAX_MONS, STATIC_DIM), enc["static"].shape)
check("STATIC_DIM == 6 stats + N_TYPES", STATIC_DIM == 6 + N_TYPES, (STATIC_DIM, N_TYPES))
check("FEATURE_DIMS static matches", FEATURE_DIMS["static"] == STATIC_DIM, FEATURE_DIMS)
# Incineroar (token 0): base HP 95/255, and Fire+Dark type bits set, others clear
inc = enc["static"][0]
check("Incineroar base HP ~95/255", abs(inc[0] - 95 / 255) < 1e-6, inc[0])
check("Incineroar base Atk ~115/255", abs(inc[1] - 115 / 255) < 1e-6, inc[1])
_ty = lambda v, t: v[6 + TYPE_INDEX[t]]
check("Incineroar Fire+Dark type bits set", _ty(inc, "fire") == 1.0 and _ty(inc, "dark") == 1.0,
      (_ty(inc, "fire"), _ty(inc, "dark")))
check("Incineroar type multi-hot sums to 2 (dual type)", abs(inc[6:].sum() - 2.0) < 1e-6, inc[6:].sum())
check("empty/padded token has all-zero static", enc["static"][MAX_MONS + 1].sum() == 0.0)

print("\nrole-generalization sanity: Incineroar vs Scrafty share the Dark-bulky-pivot profile")
# Both are Dark, both Intimidate + Fake Out; the static profile is what lets
# the net transfer between them even under species dropout.
st_scr = {"me": side({"a": "Scrafty", "b": None}, {"Scrafty": mon("Scrafty")}),
          "opp": side({"a": "Incineroar", "b": None}, {"Incineroar": mon("Incineroar")}),
          "weather": None, "trick_room": False, "terrain": None}
enc_scr = encode_state(st_scr)
scr = enc_scr["static"][0]  # Scrafty me-active
check("Scrafty shares Dark type bit with Incineroar", _ty(scr, "dark") == 1.0, _ty(scr, "dark"))
check("Scrafty is bulky (def+spd base > offense)", scr[2] + scr[4] > scr[1] + scr[3],
      (scr[1], scr[2], scr[3], scr[4]))

print("\nphantom active (Illusion / mega re-key orphan): active species not in mons -> no crash")
# Zoroark disguised as Raichu leaves 'Raichu' as active while the real
# Raichu got re-keyed to 'Raichu-Mega-X' in mons. encode must not crash and
# must still carry the known species identity for that token.
st_ill = {
    "me": side({"a": "Raichu", "b": "Rotom-Heat"},
               {"Raichu-Mega-X": mon("Raichu-Mega-X"), "Rotom-Heat": mon("Rotom-Heat"),
                "Sylveon": mon("Sylveon")}),
    "opp": side({"a": "Sylveon", "b": None}, {"Sylveon": mon("Sylveon")}),
    "weather": None, "trick_room": False, "terrain": None,
}
enc_ill = encode_state(st_ill)  # must not raise
check("phantom active token carries Raichu identity", enc_ill["species"][0] == resolve_species("Raichu"),
      enc_ill["species"][0])
check("phantom active token is real (mask=1) and defaulted hp=1.0",
      enc_ill["mask"][0] == 1.0 and abs(enc_ill["numeric"][0][0] - 1.0) < 1e-6,
      (enc_ill["mask"][0], enc_ill["numeric"][0][0]))
check("phantom active has Raichu static (Electric type bit set)",
      enc_ill["static"][0][6 + TYPE_INDEX["electric"]] == 1.0)

print("\naction encoding: move (target relative to acting side + mega), switch, pass")
from model.encoding import encode_action, encode_example, MOVE_VOCAB, _lookup  # noqa: E402
# p1's Fake Out on p2b -> opp_b (idx2); mega flagged
fo = encode_action({"kind": "move", "move": "Fake Out", "target": "p2b", "mega": True}, "p1", "a")
check("move type=1, mega=1", fo["type"] == 1 and fo["mega"] == 1, fo)
check("Fake Out target opp_b (idx 2)", fo["target"] == 2, fo["target"])
check("Fake Out move idx = vocab lookup", fo["move"] == _lookup(MOVE_VOCAB, "Fake Out") != UNK, fo["move"])
# self-targeted Trick Room by slot b -> self (idx3)
tr = encode_action({"kind": "move", "move": "Trick Room", "target": "p1b", "mega": False}, "p1", "b")
check("Trick Room self-target (idx 3)", tr["target"] == 3, tr["target"])
# ally target: p1a acting, targeting p1b
ally = encode_action({"kind": "move", "move": "Follow Me", "target": "p1a", "mega": False}, "p1", "b")
check("ally target (idx 4)", ally["target"] == 4, ally["target"])
# switch and pass
sw = encode_action({"kind": "switch", "species": "Kingambit"}, "p2", "a")
check("switch type=2, switch idx set", sw["type"] == 2 and sw["switch"] == resolve_species("Kingambit"), sw)
check("pass (None) type=0", encode_action(None, "p1", "a")["type"] == 0)

print("\nencode_example: state + action labels + value + meta")
ex = {"id": "z", "side": "p1", "turn": 3, "rating": 1300, "won": True,
      "action": {"a": {"kind": "move", "move": "Flare Blitz", "target": "p2a", "mega": False},
                 "b": {"kind": "switch", "species": "Sylveon"}},
      "state": st}
rec = encode_example(ex)
check("value = 1.0 (won)", rec["value"] == 1.0, rec["value"])
check("action_a is a move", rec["actions"]["a"]["type"] == 1)
check("action_b is a switch to Sylveon", rec["actions"]["b"]["switch"] == resolve_species("Sylveon"))
check("meta aligned with tokens (opp active has nonzero item prob)",
      rec["state"]["meta_item_prob"][MAX_MONS] > 0.0, rec["state"]["meta_item_prob"][MAX_MONS])

print("\ncorpus move-label coverage (0% UNK expected) if examples exist")
if glob.glob(str(Path("replays/examples") / "*.jsonl")):
    mt = mu = 0
    for fp in glob.glob(str(Path("replays/examples") / "*.jsonl")):
        for line in open(fp, encoding="utf-8"):
            for sl in ("a", "b"):
                a = json.loads(line)["action"].get(sl)
                if a and a.get("kind") == "move":
                    mt += 1
                    mu += _lookup(MOVE_VOCAB, a["move"]) == UNK
    check(f"move UNK rate ~0 over {mt} played moves", mu == 0, f"{mu} UNK")

print("\ncorpus species coverage (0% UNK expected) if examples exist")
files = glob.glob(str(Path("replays/examples") / "*.jsonl"))
if files:
    tot = unk = 0
    for fp in files:
        for line in open(fp, encoding="utf-8"):
            state = json.loads(line)["state"]
            for s in ("me", "opp"):
                for sp in state[s]["mons"]:
                    tot += 1
                    unk += resolve_species(sp) == UNK
    check(f"species UNK rate ~0 over {tot} tokens", unk == 0, f"{unk} UNK")
else:
    print("  (no examples corpus on disk - skipped)")

print(f"\n{'PASS' if not failures else 'FAIL: ' + ', '.join(failures)}")
