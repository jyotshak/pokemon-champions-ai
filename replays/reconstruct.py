"""Reconstruct per-decision (state -> action) training examples from a
cached replay - stage three of the replay -> imitation-net pipeline
([[replay-net-direction]]). The parser (parse_replays.py) gives resolved
turn EVENTS; this walks the protocol maintaining board STATE and emits,
at each turn boundary, one example per side:

  {id, side, turn, rating, is_bo3, winner_side, replacement,
   state:  <board snapshot BEFORE the turn resolves>,
   action: {a: <slot action>, b: <slot action>},
   sheet:  <that side's Bo3 open-sheet sets, else None>}

state is deliberately framework-neutral (plain JSON), so the torch
encoder in model/ consumes it without depending on replays/ or poke-env
(architecture-goal). The value target is winner_side; the policy target
is action; rating is for the >=cutoff filter / rating-weighting.

Output keyed by SIDE, not "to move": in doubles both players commit
simultaneously each turn, so every turn yields a p1 example and a p2
example. A slot's turn action is its first move (with target/mega) or a
voluntary switch; a switch that follows that slot fainting the same turn
is a forced replacement, emitted as a separate example (replacement=True)
snapshotted at the faint, not folded into the turn-start joint action.

V1 scope (documented, hardened later): HP fraction, status, boosts
(cleared on switch-out), faint, revealed item/ability/moves, weather,
Trick Room, terrain, and per-side conditions (Tailwind/Reflect/Light
Screen/Aurora Veil) are tracked. NOT yet: exact residual-damage
attribution, volatile statuses beyond the above, ally-target nuance, and
Illusion (Zoroark/Zorua): a disguised mon shares the copied species' key,
which the real mon's mega re-key can orphan (rare; encode_state tolerates
the resulting phantom active pointer rather than the state being exact).

Run: python -m replays.reconstruct            # full rebuild: write examples/*.jsonl
                                                # from ALL cached raw replays, and
                                                # stamp trained_manifest.py to match
     python -m replays.reconstruct --new-only  # incremental: reconstruct only raw
                                                # replays not yet in the manifest,
                                                # into examples/<fmt>new.jsonl - lets
                                                # a periodic re-scrape be trained on
                                                # (model/train.py --paths) without
                                                # touching the existing corpus until
                                                # merge_new.py folds it in
     python -m replays.reconstruct --dump 3
"""

import argparse
import json
from pathlib import Path

from replays import trained_manifest
from replays.parse_replays import parse_replay

_HERE = Path(__file__).resolve().parent
RAW_DIR = _HERE / "raw"
EXAMPLES_DIR = _HERE / "examples"

_SIDE_COND = {  # protocol name -> state key
    "Reflect": "reflect", "Light Screen": "light_screen", "Aurora Veil": "aurora_veil",
    "move: Tailwind": "tailwind", "Tailwind": "tailwind",
}


def _slot(ident: str) -> tuple[str, str]:
    """'p1a: Gengar' -> ('p1', 'a'); side condition 'p2: Name' -> ('p2', '')."""
    tag = ident.split(":", 1)[0].strip()
    return tag[:2], tag[2:] if len(tag) > 2 else ""


def _species(details: str) -> str:
    return details.split(",", 1)[0].strip()


def _hp_frac(token: str) -> float:
    token = token.strip()
    if token.startswith("0") and "fnt" in token:
        return 0.0
    num = token.split()[0]  # drop any trailing status word
    if "/" in num:
        cur, mx = num.split("/")
        try:
            return max(0.0, min(1.0, float(cur) / float(mx))) if float(mx) else 0.0
        except ValueError:
            return 0.0
    return 0.0


def _sheet_id(species: str) -> str:
    return "".join(ch for ch in species.lower() if ch.isalnum())


def _sheet_lookup(sheet: list[dict] | None) -> dict[str, dict]:
    """A parsed Bo3 open-team-sheet -> {normalized species id -> sheet set}."""
    if not sheet:
        return {}
    return {_sheet_id(s["species"]): s for s in sheet}


def _fresh_mon(species: str, sheet_by_id: dict[str, dict] | None = None) -> dict:
    """A newly-revealed mon's starting record. When an Open Team Sheet entry
    matches (Bo3 only - real VGC Open Team Sheets reveal BOTH full 6-mon
    rosters, item/ability/moves included, before either game of the set even
    starts - confirmed on real data: a Bo3 replay's sheets carry 6 mons per
    side, for both p1 and p2), seed the FULL declared moveset/item/ability
    immediately at first reveal instead of leaving them to accumulate one at
    a time as the battle happens to use them.

    This only ever touches mons that actually get switched in during the
    battle (the other 2 of the 6 sheet mons, never brought, never trigger a
    switch/drag event and so never get a _fresh_mon call at all) - so it
    naturally seeds exactly the 4 brought mons, never the full 6, with no
    separate team-preview-aware bookkeeping needed.

    Without this, EVERY turn-1 example had exactly 2 known own mons and 0
    known own moves, even when a full sheet was sitting right there unused -
    a severe mismatch against live inference, which always sees the
    complete brought roster + full 4-move sets because we ARE the player
    (harness/translator.py::own_pokemon). Bo1 has no sheet to look up, so
    this silently falls through to the old incremental-reveal-only
    behavior there - a real, currently-unrecoverable data limitation
    (no way to know an unrevealed Bo1 move after the fact), not a bug.
    See [[net-external-review-2026-07-21]].
    """
    entry = (sheet_by_id or {}).get(_sheet_id(species))
    if entry is None:
        return {"species": species, "hp": 1.0, "status": None, "boosts": {},
                "item": None, "ability": None, "fainted": False, "moves": []}
    return {"species": species, "hp": 1.0, "status": None, "boosts": {},
            "item": entry.get("item"), "ability": entry.get("ability"),
            "fainted": False, "moves": list(entry.get("moves") or [])}


def _new_state() -> dict:
    def side():
        return {"mons": {}, "active": {"a": None, "b": None},
                "cond": {"tailwind": False, "reflect": False, "light_screen": False, "aurora_veil": False}}
    return {"p1": side(), "p2": side(), "weather": None, "trick_room": False, "terrain": None}


def _snapshot(state: dict, side: str) -> dict:
    """Deep-ish copy of the state from `side`'s point of view (its own
    board as 'me', the opponent as 'opp')."""
    opp = "p2" if side == "p1" else "p1"
    import copy
    return {
        "me": copy.deepcopy(state[side]),
        "opp": copy.deepcopy(state[opp]),
        "weather": state["weather"], "trick_room": state["trick_room"], "terrain": state["terrain"],
    }


def _mon_in_slot(state: dict, side: str, slot: str) -> dict | None:
    sp = state[side]["active"].get(slot)
    return state[side]["mons"].get(sp) if sp else None


def reconstruct(record: dict, raw_log: str) -> list[dict]:
    """record: parse_replay() output (for meta/sheets/winner). raw_log:
    the same replay's protocol string. Returns training examples."""
    state = _new_state()
    examples: list[dict] = []
    lines = raw_log.split("\n")
    winner_side = record.get("winner_slot")
    is_bo3 = record.get("is_bo3", False)
    ratings = {p["slot"]: p["rating"] for p in record.get("players", [])}
    sheets = record.get("sheets", {"p1": None, "p2": None})
    # Bo3-only (Bo1 sheets are always None): normalized-species-id -> sheet
    # set, per side, for _fresh_mon's first-reveal enrichment.
    sheet_by_id = {s: _sheet_lookup(sheets.get(s)) for s in ("p1", "p2")}

    # Pre-seed each side's state with its FULL BROUGHT ROSTER, not just
    # whichever 2 mons happen to be active at a given moment: every species
    # that ever appears in a switch/drag event across the WHOLE game is,
    # necessarily, one of the brought 4 (nothing else can ever be switched
    # in), so one pass over the raw log recovers the true roster with no
    # separate team-preview-bring-decision parsing needed. A real player
    # already knows their complete brought team (species always; for Bo3,
    # the full sheet-derived item/ability/moveset) from the moment team
    # preview ends - not one bench mon at a time as it happens to be sent
    # out. Turn-processing's own switch/drag handling below still uses
    # setdefault, so it just finds these already present and does nothing.
    for line in lines:
        if not line.startswith("|"):
            continue
        parts = line.split("|")
        if (parts[1] if len(parts) > 1 else "") in ("switch", "drag") and len(parts) > 3:
            side, _pre_slot = _slot(parts[2])
            if side in state:
                sp = _species(parts[3])
                state[side]["mons"].setdefault(sp, _fresh_mon(sp, sheet_by_id[side]))

    # Split into turn segments: everything from a |turn|N marker up to the
    # next. Pre-turn lines (team preview / leads) form segment 0.
    segments: list[tuple[int, list[str]]] = []
    cur_turn, buf = 0, []
    for line in lines:
        if line.startswith("|turn|"):
            segments.append((cur_turn, buf))
            cur_turn = int(line.split("|")[2])
            buf = []
        else:
            buf.append(line)
    segments.append((cur_turn, buf))

    def apply_line(parts: list[str], line: str):
        tag = parts[1] if len(parts) > 1 else ""
        if tag in ("switch", "drag"):
            side, slot = _slot(parts[2])
            sp = _species(parts[3])
            prev = state[side]["active"].get(slot)
            if prev and prev in state[side]["mons"]:
                state[side]["mons"][prev]["boosts"] = {}  # boosts reset on switch-out
            state[side]["mons"].setdefault(sp, _fresh_mon(sp, sheet_by_id[side]))
            if len(parts) > 4:
                state[side]["mons"][sp]["hp"] = _hp_frac(parts[4])
            state[side]["mons"][sp]["fainted"] = False
            state[side]["active"][slot] = sp
        elif tag == "detailschange" and len(parts) > 3:
            side, slot = _slot(parts[2])
            old = state[side]["active"].get(slot)
            new_sp = _species(parts[3])
            if old and old in state[side]["mons"] and new_sp != old:
                m = state[side]["mons"].pop(old)
                m["species"] = new_sp
                state[side]["mons"][new_sp] = m
                state[side]["active"][slot] = new_sp
        elif tag in ("-damage", "-heal") and len(parts) > 3:
            side, slot = _slot(parts[2])
            m = _mon_in_slot(state, side, slot)
            if m:
                m["hp"] = _hp_frac(parts[3])
        elif tag == "faint":
            side, slot = _slot(parts[2])
            m = _mon_in_slot(state, side, slot)
            if m:
                m["hp"] = 0.0
                m["fainted"] = True
        elif tag == "-status" and len(parts) > 3:
            side, slot = _slot(parts[2])
            m = _mon_in_slot(state, side, slot)
            if m:
                m["status"] = parts[3]
        elif tag == "-curestatus" and len(parts) > 3:
            side, slot = _slot(parts[2])
            m = _mon_in_slot(state, side, slot)
            if m:
                m["status"] = None
        elif tag in ("-boost", "-unboost") and len(parts) > 4:
            side, slot = _slot(parts[2])
            m = _mon_in_slot(state, side, slot)
            if m:
                amt = int(parts[4]) * (1 if tag == "-boost" else -1)
                m["boosts"][parts[3]] = m["boosts"].get(parts[3], 0) + amt
        elif tag == "-weather":
            w = parts[2] if len(parts) > 2 else "none"
            state["weather"] = None if w in ("none", "") else w
        elif tag == "-fieldstart" and len(parts) > 2:
            if "Trick Room" in parts[2]:
                state["trick_room"] = True
            elif "Terrain" in parts[2]:
                state["terrain"] = parts[2].replace("move: ", "")
        elif tag == "-fieldend" and len(parts) > 2:
            if "Trick Room" in parts[2]:
                state["trick_room"] = False
            elif "Terrain" in parts[2]:
                state["terrain"] = None
        elif tag in ("-sidestart", "-sideend") and len(parts) > 3:
            side, _ = _slot(parts[2])
            key = _SIDE_COND.get(parts[3].replace("move: ", "")) or _SIDE_COND.get(parts[3])
            if key:
                state[side]["cond"][key] = (tag == "-sidestart")
        elif tag in ("-item", "-enditem") and len(parts) > 3:
            side, slot = _slot(parts[2])
            m = _mon_in_slot(state, side, slot)
            if m:
                m["item"] = parts[3] if tag == "-item" else None
        elif tag == "-ability" and len(parts) > 3:
            side, slot = _slot(parts[2])
            m = _mon_in_slot(state, side, slot)
            if m:
                m["ability"] = parts[3]

    def record_move_reveal(side, slot, move):
        m = _mon_in_slot(state, side, slot)
        if m and move not in m["moves"]:
            m["moves"].append(move)

    def extract_actions(seg_lines: list[str]) -> dict:
        """Per side -> {slot -> action} for turn-start decisions, plus a
        list of (side, slot, species) forced replacements after faints."""
        actions = {"p1": {}, "p2": {}}
        fainted = set()          # (side, slot) that fainted this turn
        replacements = []
        acted = set()            # (side, slot) that already took a turn-start action
        megas = set()
        for line in seg_lines:
            if not line.startswith("|"):
                continue
            p = line.split("|")
            tag = p[1] if len(p) > 1 else ""
            if tag == "-mega" and len(p) > 2:
                megas.add(_slot(p[2]))
            elif tag == "move" and len(p) > 3:
                side, slot = _slot(p[2])
                key = (side, slot)
                if key not in acted:
                    tgt = _slot(p[4]) if len(p) > 4 and ":" in p[4] else (None, None)
                    actions[side][slot] = {"kind": "move", "move": p[3],
                                           "target": f"{tgt[0]}{tgt[1]}" if tgt[0] else None,
                                           "mega": key in megas}
                    acted.add(key)
            elif tag == "cant" and len(p) > 2:
                acted.add(_slot(p[2]))   # couldn't act -> no decision label
            elif tag == "faint" and len(p) > 2:
                fainted.add(_slot(p[2]))
            elif tag in ("switch", "drag") and len(p) > 3:
                side, slot = _slot(p[2])
                key = (side, slot)
                if key in fainted or key in acted:
                    replacements.append((side, slot, _species(p[3])))
                else:
                    actions[side][slot] = {"kind": "switch", "species": _species(p[3])}
                    acted.add(key)
        return {"actions": actions, "replacements": replacements}

    for turn_no, seg in segments:
        if turn_no == 0:
            for line in seg:  # apply leads / preview, no decision emitted
                if line.startswith("|"):
                    apply_line(line.split("|"), line)
            continue

        # snapshot BEFORE the turn resolves = the decision state
        for side in ("p1", "p2"):
            snap = _snapshot(state, side)
            ext = extract_actions(seg)
            act = ext["actions"][side]
            if act:  # only emit if this side made at least one turn-start choice
                examples.append({
                    "id": record.get("id"), "side": side, "turn": turn_no,
                    "rating": ratings.get(side), "is_bo3": is_bo3,
                    "winner_side": winner_side,
                    "won": (winner_side == side) if winner_side else None,
                    "replacement": False,
                    "state": snap,
                    "action": {"a": act.get("a"), "b": act.get("b")},
                    "sheet": sheets.get(side) if is_bo3 else None,
                })

        # advance state through the turn, revealing moves as they resolve
        for line in seg:
            if not line.startswith("|"):
                continue
            p = line.split("|")
            tag = p[1] if len(p) > 1 else ""
            if tag == "move" and len(p) > 3:
                s, sl = _slot(p[2])
                record_move_reveal(s, sl, p[3])
            apply_line(p, line)

    return examples


def reconstruct_format_dir(format_id: str, limit: int = 0, only_ids: set[str] | None = None) -> list[dict]:
    """only_ids: if given, reconstruct only raw replays whose id is in this
    set (the --new-only path) instead of everything cached."""
    out = []
    raw = RAW_DIR / format_id
    if not raw.exists():
        return out
    paths = sorted(raw.glob("*.json"))
    if only_ids is not None:
        paths = [p for p in paths if p.stem in only_ids]
    if limit:
        paths = paths[:limit]
    for path in paths:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            out.extend(reconstruct(parse_replay(data), data.get("log", "")))
        except Exception as e:
            print(f"  [reconstruct {path.name}] failed ({e})", flush=True)
    return out


def _summarize(fmt_dir: str, examples: list[dict]) -> None:
    moves = sum(1 for e in examples for a in (e["action"]["a"], e["action"]["b"]) if a and a["kind"] == "move")
    switches = sum(1 for e in examples for a in (e["action"]["a"], e["action"]["b"]) if a and a["kind"] == "switch")
    labeled = sum(1 for e in examples if e["won"] is not None)
    print(f"[{fmt_dir}] {len(examples)} examples (per side/turn), "
          f"{moves} move-actions, {switches} switch-actions, {labeled} outcome-labeled")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dump", type=int, default=0, help="print N examples instead of writing")
    ap.add_argument("--limit", type=int, default=0, help="replays per format (0 = all)")
    ap.add_argument("--new-only", action="store_true",
                    help="reconstruct only raw replays not yet in trained_ids.json, into "
                         "examples/<fmt>new.jsonl - leaves the main corpus untouched "
                         "(see replays/trained_manifest.py, replays/merge_new.py)")
    args = ap.parse_args()

    EXAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    fmt_dirs = sorted(p.name for p in RAW_DIR.iterdir()) if RAW_DIR.exists() else []

    if args.new_only:
        manifest = trained_manifest.load()
        for fmt_dir in fmt_dirs:
            fresh_ids = trained_manifest.new_ids(manifest, fmt_dir)
            if not fresh_ids:
                print(f"[{fmt_dir}] no new replays since the last merge (0 candidates)")
                continue
            examples = reconstruct_format_dir(fmt_dir, args.limit, only_ids=fresh_ids)
            if not args.dump and not args.limit:
                # Persist the FULL attempted id set (not just ids that ended up
                # contributing an example) so merge_new.py can mark truly-empty
                # replays (e.g. instant forfeits with no real turns - confirmed
                # to happen, ~0.2% of a batch) as known too. Without this they'd
                # silently retry forever: every future --new-only run would keep
                # re-finding them as "new" since an empty replay never appears
                # in <fmt>new.jsonl's content for merge_new.py to pick up.
                sidecar = EXAMPLES_DIR / f"{fmt_dir}new.attempted_ids.json"
                sidecar.write_text(json.dumps(sorted(fresh_ids)), encoding="utf-8")
            if not examples:
                print(f"[{fmt_dir}] 0 examples from {len(fresh_ids)} candidate replay(s) "
                      f"(likely forfeits/empty logs - marked known regardless, see attempted_ids sidecar)")
                continue
            _summarize(fmt_dir, examples)
            if args.dump:
                for e in examples[:args.dump]:
                    a = e["state"]["me"]
                    print(f"  {e['id']} t{e['turn']} {e['side']} won={e['won']} rating={e['rating']}")
                    print(f"     me active: {a['active']}  weather={e['state']['weather']} TR={e['state']['trick_room']}")
                    print(f"     action: {e['action']}")
            else:
                out_path = EXAMPLES_DIR / f"{fmt_dir}new.jsonl"
                out_path.write_text("".join(json.dumps(e) + "\n" for e in examples), encoding="utf-8")
                print(f"    -> wrote {out_path} ({len(examples)} examples from {len(fresh_ids)} new replays)")
        return

    manifest = {}
    for fmt_dir in fmt_dirs:
        examples = reconstruct_format_dir(fmt_dir, args.limit)
        if not examples:
            continue
        _summarize(fmt_dir, examples)
        if args.dump:
            for e in examples[:args.dump]:
                a = e["state"]["me"]
                print(f"  {e['id']} t{e['turn']} {e['side']} won={e['won']} rating={e['rating']}")
                print(f"     me active: {a['active']}  weather={e['state']['weather']} TR={e['state']['trick_room']}")
                print(f"     action: {e['action']}")
        else:
            out_path = EXAMPLES_DIR / f"{fmt_dir}.jsonl"
            out_path.write_text("".join(json.dumps(e) + "\n" for e in examples), encoding="utf-8")
            print(f"    -> wrote {out_path} ({len(examples)} examples)")
            # a full rebuild always covers 100% of the current raw cache -
            # keep the manifest in exact sync so --new-only's next delta is
            # computed against what this run actually produced.
            manifest[fmt_dir] = sorted(trained_manifest.raw_ids(fmt_dir))
    if not args.dump and manifest:
        trained_manifest.save(manifest)
        print(f"    -> trained_ids.json refreshed ({', '.join(f'{k}: {len(v)}' for k, v in manifest.items())})")


if __name__ == "__main__":
    main()
