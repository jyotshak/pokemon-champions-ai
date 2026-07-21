"""Parse cached Showdown replays (replays/raw/, from scrape_replays.py)
into structured records - stage two of the replay -> imitation-net
pipeline. One JSON record per replay written to replays/parsed/<fmt>.jsonl.

What each record captures (the imitation/belief training skeleton):
  - meta: id, format, is_bo3, players [{slot, name, rating}], winner_slot
  - preview: {p1, p2} team-preview species reveals (|poke|)
  - sheets: {p1, p2} full sets from |showteam| open sheets (Bo3 only) -
      species/item/ability/moves/nature/level, the hidden-attribute
      ground truth for the belief model; None for Bo1
  - turns: per-turn resolved events (|move| with actor+target+mega,
      |switch| with incoming species, |faint|) - the action labels

DELIBERATELY not done here (the next slice - state/encoding): folding
per-turn events into a full board STATE tensor (HP/status/field tracked
across the log) and segmenting turn-start joint decisions vs post-faint
forced replacements. This stage produces clean, inspectable structured
events + ground-truth sheets + outcomes; the encoder consumes them.

Run from the project root:
  python -m replays.parse_replays               # parse everything cached
  python -m replays.parse_replays --limit 5 --dump   # show a few decoded
"""

import argparse
import json
from pathlib import Path

_HERE = Path(__file__).resolve().parent
RAW_DIR = _HERE / "raw"
PARSED_DIR = _HERE / "parsed"

# Packed-team field order (Showdown's Teams.pack format), '|'-separated
# per mon, ']'-separated between mons:
#   nickname|species|item|ability|moves|nature|evs|gender|ivs|shiny|level|misc
_PACK_FIELDS = ["nickname", "species", "item", "ability", "moves", "nature",
                "evs", "gender", "ivs", "shiny", "level", "misc"]


def parse_packed_team(packed: str) -> list[dict]:
    """A |showteam| payload -> list of set dicts. species falls back to
    nickname when the species field is blank (Showdown omits it when the
    two match), moves split on comma, level defaults to 50 (Champions)."""
    sets = []
    for chunk in packed.split("]"):
        if not chunk:
            continue
        f = chunk.split("|")
        f += [""] * (len(_PACK_FIELDS) - len(f))
        species = f[1] or f[0]
        sets.append({
            "species": species,
            "item": f[2] or None,
            "ability": f[3] or None,
            "moves": [m for m in f[4].split(",") if m],
            "nature": f[5] or None,
            "level": int(f[10]) if f[10].isdigit() else 50,
        })
    return sets


def _actor_slot(ident: str) -> str:
    """'p1a: Koraidon' -> 'p1a' (the position tag), ignoring the name."""
    return ident.split(":", 1)[0].strip()


def _species_from_details(details: str) -> str:
    """'Charizard, M' / 'Raichu, F' / 'Ditto' -> the species token."""
    return details.split(",", 1)[0].strip()


def parse_replay(data: dict) -> dict:
    log = data.get("log", "")
    players_meta = data.get("players", [])
    rating = data.get("rating")
    fmt = data.get("format", "")
    is_bo3 = "Bo3" in fmt or data.get("id", "").startswith("gen9championsvgc2026regmbbo3")

    names = {}          # slot -> name
    slot_ratings = {}   # slot -> per-player ladder rating (from the |player| line)
    preview = {"p1": [], "p2": []}
    sheets = {"p1": None, "p2": None}
    winner_name = None
    turns = []
    cur = None          # current turn's event bucket
    megas_this_turn = set()

    def flush():
        if cur is not None:
            turns.append(cur)

    for line in log.split("\n"):
        if not line.startswith("|"):
            continue
        parts = line.split("|")
        tag = parts[1] if len(parts) > 1 else ""

        if tag == "player" and len(parts) > 3 and parts[3]:
            # Guard on a non-empty name: Showdown emits a trailing
            # `|player|p1|` (blank) when a player leaves, which would
            # otherwise wipe the real name. Line is
            # `|player|<slot>|<name>|<avatar>|<rating>` - rating is index
            # 5 (index 4 is the avatar), and is per-player, finer than
            # the single game-level rating.
            names[parts[2]] = parts[3]
            if len(parts) > 5 and parts[5].strip().isdigit():
                slot_ratings[parts[2]] = int(parts[5].strip())
        elif tag == "poke" and len(parts) > 3:
            side = parts[2]
            if side in preview:
                preview[side].append(_species_from_details(parts[3]))
        elif tag == "showteam" and len(parts) > 3:
            side = parts[2]
            # The packed payload itself contains '|', so it must be taken
            # with a bounded split (not the fully-split `parts`).
            if side in sheets:
                sheets[side] = parse_packed_team(line.split("|", 3)[3])
        elif tag == "turn":
            flush()
            megas_this_turn = set()
            cur = {"turn": int(parts[2]), "moves": [], "switches": [], "faints": []}
        elif tag == "-mega" and len(parts) > 2:
            megas_this_turn.add(_actor_slot(parts[2]))
        elif tag == "move" and cur is not None and len(parts) > 3:
            actor = _actor_slot(parts[2])
            target = _actor_slot(parts[4]) if len(parts) > 4 and ":" in parts[4] else None
            cur["moves"].append({
                "slot": actor, "move": parts[3], "target": target,
                "mega": actor in megas_this_turn,
            })
        elif tag == "switch" and len(parts) > 3:
            actor = _actor_slot(parts[2])
            entry = {"slot": actor, "species": _species_from_details(parts[3])}
            if cur is not None:
                cur["switches"].append(entry)   # else: turn-0 lead send-out, ignored
        elif tag == "faint" and cur is not None and len(parts) > 2:
            cur["faints"].append(_actor_slot(parts[2]))
        elif tag == "win" and len(parts) > 2:
            winner_name = parts[2].strip()
    flush()

    # winner name -> slot
    winner_slot = None
    for slot, name in names.items():
        if name == winner_name:
            winner_slot = slot

    # ratings: prefer the per-player rating from the |player| line, fall
    # back to the top-level game rating when a slot didn't report one.
    players = [{"slot": p, "name": names.get(p), "rating": slot_ratings.get(p, rating)}
               for p in sorted(names)]

    return {
        "id": data.get("id"),
        "format": fmt,
        "is_bo3": is_bo3,
        "rating": rating,
        "players": players,
        "winner_slot": winner_slot,
        "winner_name": winner_name,
        "preview": preview,
        "sheets": sheets,
        "turns": turns,
    }


def parse_format_dir(format_id: str) -> list[dict]:
    out = []
    raw = RAW_DIR / format_id
    if not raw.exists():
        return out
    for path in sorted(raw.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            out.append(parse_replay(data))
        except Exception as e:
            print(f"  [parse {path.name}] failed ({e})", flush=True)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--limit", type=int, default=0, help="only decode this many per format (0 = all)")
    ap.add_argument("--dump", action="store_true", help="print a compact decode of each record instead of writing")
    args = ap.parse_args()

    PARSED_DIR.mkdir(parents=True, exist_ok=True)
    for fmt_dir in sorted(p.name for p in RAW_DIR.iterdir()) if RAW_DIR.exists() else []:
        records = parse_format_dir(fmt_dir)
        if args.limit:
            records = records[:args.limit]
        if not records:
            continue

        with_sheets = sum(1 for r in records if r["sheets"]["p1"] and r["sheets"]["p2"])
        resolved_winner = sum(1 for r in records if r["winner_slot"])
        total_turns = sum(len(r["turns"]) for r in records)
        print(f"[{fmt_dir}] {len(records)} replays, {total_turns} turns, "
              f"winner resolved {resolved_winner}/{len(records)}, full sheets {with_sheets}/{len(records)}")

        if args.dump:
            for r in records[:5]:
                ps = ", ".join(f"{p['name']}({p['rating']})" for p in r["players"])
                print(f"  {r['id']}  [{ps}]  winner={r['winner_slot']}  turns={len(r['turns'])}")
                if r["sheets"]["p1"]:
                    s0 = r["sheets"]["p1"][0]
                    print(f"     p1 sheet[0]: {s0['species']} @ {s0['item']} / {s0['ability']} / {s0['moves']} / {s0['nature']}")
                if r["turns"]:
                    t = r["turns"][0]
                    print(f"     turn 1 moves: {[(m['slot'], m['move'], m['target'], m['mega']) for m in t['moves']]}")
        else:
            out_path = PARSED_DIR / f"{fmt_dir}.jsonl"
            out_path.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
            print(f"    -> wrote {out_path}")


if __name__ == "__main__":
    main()
