"""Converts a raw Showdown export paste (species/item/ability/EVs/nature/
moves — the format most team-sharing sites give you) into a team string
usable by ConstantTeambuilder. Champions is always level 50 and pastes
from these sites typically omit the Level line, so this is the one thing
that actually needs adding — everything else (EVs in the 0-32 champions
points range, not mainline 0-252 - see memory: showdown-doubles-harness)
is already valid syntax the real server parses directly under the
champions mod, no stat computation needed on our end.

add_ev_spreads fills in the other thing these pastes are typically
missing: EVs and (if absent) Nature, using each species' top reported
build from belief/usage_data/usage_stats.json.
"""

import json
import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_DISPLAY_NAMES = json.loads((_ROOT / "reference" / "species_display_names.json").read_text(encoding="utf-8"))
_USAGE_STATS = json.loads((_ROOT / "belief" / "usage_data" / "usage_stats.json").read_text(encoding="utf-8"))


def add_level(paste: str, level: int = 50) -> str:
    """Insert a `Level: N` line right after each mon's `Ability:` line,
    unless that mon already has one (idempotent - safe to run on a paste
    that's already complete).
    """
    lines = paste.strip("\n").split("\n")
    out = []
    i = 0
    while i < len(lines):
        out.append(lines[i])
        if re.match(r"\s*Ability:", lines[i]):
            next_line = lines[i + 1] if i + 1 < len(lines) else ""
            if not re.match(r"\s*Level:", next_line):
                out.append(f"Level: {level}")
        i += 1
    return "\n".join(out) + "\n"


def _to_id(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


_NAME_TO_ID = {_to_id(name): species_id for species_id, name in _DISPLAY_NAMES.items()}

_STAT_ORDER = ["hp", "atk", "def", "spa", "spd", "spe"]
_STAT_LABEL = {"hp": "HP", "atk": "Atk", "def": "Def", "spa": "SpA", "spd": "SpD", "spe": "Spe"}

# The real 25-nature grid (boosted stat, lowered stat) -> name; the 5
# neutral natures (Hardy/Docile/Serious/Bashful/Quirky) are all
# equivalent for our purposes, so _infer_nature just picks "Serious".
_NATURE_BY_BOOST_LOWER = {
    ("atk", "def"): "Lonely", ("atk", "spe"): "Brave", ("atk", "spa"): "Adamant", ("atk", "spd"): "Naughty",
    ("def", "atk"): "Bold", ("def", "spe"): "Relaxed", ("def", "spa"): "Impish", ("def", "spd"): "Lax",
    ("spe", "atk"): "Timid", ("spe", "def"): "Hasty", ("spe", "spa"): "Jolly", ("spe", "spd"): "Naive",
    ("spa", "atk"): "Modest", ("spa", "def"): "Mild", ("spa", "spe"): "Quiet", ("spa", "spd"): "Rash",
    ("spd", "atk"): "Calm", ("spd", "def"): "Gentle", ("spd", "spe"): "Sassy", ("spd", "spa"): "Careful",
}


def _species_id_from_line(line: str) -> str | None:
    """First line of a mon block: `[Nick (]Species[ (M/F)][ @ Item]`."""
    text = line.split("@")[0].strip()
    m = re.match(r"^.*\(([^()]+)\)\s*$", text)
    if m and m.group(1).upper() not in ("M", "F"):
        text = m.group(1)
    else:
        text = re.sub(r"\s*\([MF]\)\s*$", "", text)
    return _NAME_TO_ID.get(_to_id(text))


def _infer_nature(points: list[int]) -> str:
    """Pikalytics' own nature field is unpopulated in every response
    we've scraped (a formatting bug on their end — the raw markdown
    genuinely has `a **** nature`, confirmed by inspection, not a gap in
    our parsing), so a missing nature is inferred from the spread
    itself: boost the non-HP stat with the most points, lower whichever
    non-HP, non-boosted stat has the least.
    """
    stats = dict(zip(_STAT_ORDER[1:], points[1:]))
    boost = max(stats, key=lambda s: stats[s])
    lower = min((s for s in stats if s != boost), key=lambda s: stats[s])
    if stats[boost] == stats[lower]:
        return "Serious"
    return _NATURE_BY_BOOST_LOWER[(boost, lower)]


def add_ev_spreads(paste: str) -> str:
    """Inserts an EVs line (and a Nature line if missing) for every mon
    that doesn't already have one, using that species' top reported
    build from belief/usage_data/usage_stats.json (top_spread: points on
    the champions 0-32 scale, already in the same `N Stat / N Stat`
    syntax the champions mod parses directly - see add_level's
    docstring). Species with no scraped spread at all are left
    untouched: a missing EVs/Nature line isn't invalid Showdown syntax,
    it just defaults to 0 EVs / a neutral nature.
    """
    blocks = paste.strip("\n").split("\n\n")
    out_blocks = []
    for block in blocks:
        lines = block.split("\n")
        if not lines or not lines[0].strip():
            out_blocks.append(block)
            continue

        species_id = _species_id_from_line(lines[0])
        top_spread = _USAGE_STATS.get(species_id, {}).get("top_spread") if species_id else None
        if not top_spread:
            out_blocks.append(block)
            continue
        points = top_spread["points"]

        if not any(re.search(r"\bNature\s*$", l.strip()) for l in lines):
            nature = _infer_nature(points)
            insert_at = next((i + 1 for i, l in enumerate(lines) if re.match(r"\s*(Level|Ability):", l)), len(lines))
            lines.insert(insert_at, f"{nature} Nature")

        if not any(re.match(r"\s*EVs:", l) for l in lines):
            ev_line = "EVs: " + " / ".join(
                f"{v} {_STAT_LABEL[stat]}" for stat, v in zip(_STAT_ORDER, points) if v
            )
            insert_at = next((i for i, l in enumerate(lines) if re.search(r"\bNature\s*$", l.strip())), len(lines))
            lines.insert(insert_at, ev_line)

        out_blocks.append("\n".join(lines))
    return "\n\n".join(out_blocks) + "\n"
