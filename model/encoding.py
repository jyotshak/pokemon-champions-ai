"""State/action encoding for the imitation net ([[replay-net-direction]]):
turns a reconstructed replay example (replays/reconstruct.py's neutral
JSON) into fixed numeric tensors the torch model consumes. Kept framework-
neutral (numpy only, no torch) so the vocab/feature logic is testable
without the training stack and so model/ stays independent of replays/ and
poke-env (architecture-goal): the encoder reads plain dicts + reference/
data, nothing input-source-specific.

Representation is per-ENTITY tokens (each mon a token) rather than one
flat vector - the shape a transformer wants. encode_state returns, for a
fixed MAX_MONS budget (6 per side):
  species/item/ability/status : int indices  -> embedding lookups
  moves                       : int indices (MAX_MOVES per mon, PAD-filled)
  numeric                     : hp + 7 boosts + is_me/active/fainted flags
  static                      : species-derived base stats + typing multi-hot
                                (role features that survive species dropout)
  mask                        : which token slots are real
plus a field vector: weather/terrain are ONE-HOT (not a raw scalar index -
categorical, not ordinal - see FEATURE_DIMS's comment), trick-room flag,
and per-side conditions.

encode_for_inference additionally returns 3 (index, probability) pairs -
meta_item/meta_ability/meta_move - the belief usage-prior's most-likely
item/ability/move for this species. These are int64 VOCAB INDICES, meant
to be routed through the SAME embedding tables as the revealed value
(model/policy_net.py), not concatenated as raw floats - a vocab index is
categorical, and a species' usual moveset is exactly the substitute prior
a Bo1 replay's genuinely-unrecoverable unrevealed moves need (see
[[net-external-review-2026-07-21]]).

Vocabularies are built once from reference/ at import (stable indices):
species from species_stats, moves from move_data, items from the legal
list, abilities from species_data. Index 0 is always PAD, 1 is UNK.
"""

import json
import re
from pathlib import Path

import numpy as np

from belief.species_folding import base_species_id

_ROOT = Path(__file__).resolve().parent.parent
_SPECIES_STATS = json.loads((_ROOT / "reference" / "species_stats.json").read_text(encoding="utf-8"))
_MOVE_DATA = json.loads((_ROOT / "reference" / "move_data.json").read_text(encoding="utf-8"))
_SPECIES_DATA = json.loads((_ROOT / "reference" / "species_data.json").read_text(encoding="utf-8"))
_LEGAL_ITEMS = (_ROOT / "reference" / "champions_legal_items.txt").read_text(encoding="utf-8").split()
_TYPE_CHART = json.loads((_ROOT / "reference" / "type_chart.json").read_text(encoding="utf-8"))

MAX_MONS = 6          # per side
MAX_MOVES = 4
PAD, UNK = 0, 1

_STATUS = ["", "par", "slp", "brn", "psn", "tox", "frz"]         # index 0 == no status
_WEATHER = ["", "RainDance", "SunnyDay", "Sandstorm", "Snow", "Hail"]
_TERRAIN = ["", "Electric Terrain", "Grassy Terrain", "Misty Terrain", "Psychic Terrain"]
_BOOST_STATS = ["atk", "def", "spa", "spd", "spe", "accuracy", "evasion"]

# Species-derived STATIC profile (base stats + typing), fed per mon token
# separately from the species-identity embedding. This is the role-
# generalization lever ([[net-generalization-design]]): with base stats +
# types present as their own features, two mons with the same profile
# (Incineroar <-> Scrafty: bulky, Dark, Intimidate, Fake Out) look alike to
# the net regardless of identity - and training-time species dropout can
# zero the species embedding while these survive, forcing play-by-role.
_STAT_KEYS = ["hp", "atk", "def", "spa", "spd", "spe"]
_STAT_NORM = 255.0        # base stats ~1..255 -> ~0..1
# Canonical types from the type chart, excluding "stellar" (a Tera-only
# type, never a species' base defensive typing). Multi-hot per mon.
TYPE_LIST = [t for t in sorted(_TYPE_CHART.keys()) if t != "stellar"]
TYPE_INDEX = {t: i for i, t in enumerate(TYPE_LIST)}
N_TYPES = len(TYPE_LIST)                       # 18
STATIC_DIM = len(_STAT_KEYS) + N_TYPES         # 6 + 18 = 24


def to_id(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (name or "").lower())


def _build_vocab(ids) -> dict[str, int]:
    """PAD=0, UNK=1, then the sorted unique ids from index 2 on."""
    vocab = {"": PAD, "<unk>": UNK}
    for i, key in enumerate(sorted(set(ids)), start=2):
        vocab[key] = i
    return vocab


# Species vocab keyed by species_stats id; longest keys first for the
# cosmetic/battle-forme prefix fallback below.
SPECIES_VOCAB = _build_vocab(_SPECIES_STATS.keys())
_SPECIES_KEYS_BY_LEN = sorted(_SPECIES_STATS.keys(), key=len, reverse=True)
MOVE_VOCAB = _build_vocab(_MOVE_DATA.keys())
ITEM_VOCAB = _build_vocab(to_id(i) for i in _LEGAL_ITEMS)
ABILITY_VOCAB = _build_vocab(
    to_id(a) for info in _SPECIES_DATA.values() for a in info.get("abilities", [])
)


def resolve_species_id(name: str) -> str | None:
    """Protocol species name -> canonical species_stats id, or None if
    unresolvable. Exact id, else mega fold (base_species_id), else the
    longest species key that prefixes the id (folds cosmetic/battle
    formes: Vivillon-Fancy -> vivillon, Palafin-Hero -> palafin)."""
    i = to_id(name)
    if i in _SPECIES_STATS:
        return i
    b = base_species_id(i)
    if b in _SPECIES_STATS:
        return b
    for key in _SPECIES_KEYS_BY_LEN:
        if i.startswith(key):
            return key
    return None


def resolve_species(name: str) -> int:
    """Canonical id -> SPECIES_VOCAB index (UNK if unresolvable)."""
    sid = resolve_species_id(name)
    return SPECIES_VOCAB[sid] if sid else UNK


def _lookup(vocab: dict, name: str) -> int:
    if not name:
        return PAD
    return vocab.get(to_id(name), UNK)


def _species_static(species_id: str | None) -> np.ndarray:
    """Species-derived static profile: 6 normalized base stats followed by
    an N_TYPES multi-hot typing. Zeros if the species is unknown. Kept in
    its own tensor (not folded into `numeric`) so species dropout at train
    time can null the species embedding while these role features remain -
    the Incineroar<->Scrafty generalization lever ([[net-generalization-design]])."""
    vec = np.zeros(STATIC_DIM, dtype=np.float32)
    entry = _SPECIES_STATS.get(species_id) if species_id else None
    if not entry:
        return vec
    bs = entry.get("base_stats") or {}
    for j, k in enumerate(_STAT_KEYS):
        vec[j] = bs.get(k, 0) / _STAT_NORM
    for t in entry.get("types") or []:
        idx = TYPE_INDEX.get(to_id(t))
        if idx is not None:
            vec[len(_STAT_KEYS) + idx] = 1.0
    return vec


def _mon_features(mon: dict, is_me: int, is_active: int):
    """Return (cat_dict, numeric_vec, move_idx_vec, static_vec) for one mon."""
    st = mon.get("status") or ""   # None -> "" (the no-status slot, index 0)
    sid = resolve_species_id(mon["species"])   # resolve once: index + static both need it
    cat = {
        "species": SPECIES_VOCAB[sid] if sid else UNK,
        "item": _lookup(ITEM_VOCAB, mon.get("item")),
        "ability": _lookup(ABILITY_VOCAB, mon.get("ability")),
        "status": _STATUS.index(st) if st in _STATUS else UNK,
    }
    boosts = [mon.get("boosts", {}).get(s, 0) / 6.0 for s in _BOOST_STATS]
    numeric = np.array([mon.get("hp", 1.0), float(is_me), float(is_active),
                        float(mon.get("fainted", False)), *boosts], dtype=np.float32)
    moves = [_lookup(MOVE_VOCAB, m) for m in mon.get("moves", [])[:MAX_MOVES]]
    moves += [PAD] * (MAX_MOVES - len(moves))
    return cat, numeric, np.array(moves, dtype=np.int64), _species_static(sid)


def _side_token_species(side: dict) -> list[str | None]:
    """Fixed token positions for one side: [active_a, active_b, then the
    revealed benched mons], padded with None to MAX_MONS. Fixed (not
    active-first-packed) so a per-slot policy head always reads the same
    token index for slot a / slot b even when a slot is empty."""
    a, b = side["active"].get("a"), side["active"].get("b")
    actives = {a, b} - {None}
    bench = [sp for sp in side["mons"] if sp not in actives]
    order = ([a, b] + bench)[:MAX_MONS]
    return order + [None] * (MAX_MONS - len(order))


def encode_state(state: dict) -> dict:
    """Reconstructed state dict ('me'/'opp' sides) -> fixed tensors.
    Tokens are packed me-side first then opp-side, each side's active mons
    first, up to MAX_MONS per side (2*MAX_MONS token slots total)."""
    n = 2 * MAX_MONS
    species = np.zeros(n, dtype=np.int64)
    item = np.zeros(n, dtype=np.int64)
    ability = np.zeros(n, dtype=np.int64)
    status = np.zeros(n, dtype=np.int64)
    moves = np.zeros((n, MAX_MOVES), dtype=np.int64)
    numeric = np.zeros((n, 4 + len(_BOOST_STATS)), dtype=np.float32)
    static = np.zeros((n, STATIC_DIM), dtype=np.float32)
    mask = np.zeros(n, dtype=np.float32)

    for side_key, is_me, base in (("me", 1, 0), ("opp", 0, MAX_MONS)):
        side = state[side_key]
        actives = {side["active"].get("a"), side["active"].get("b")} - {None}
        for i, sp in enumerate(_side_token_species(side)):
            if sp is None:
                continue          # slot reserved but empty (masked)
            t = base + i
            # A slot can point at a species not in `mons` when reconstruct's
            # species-name keying is confounded (e.g. Zoroark's Illusion makes
            # a disguised mon share the copied species' key, which is then
            # re-keyed away on the real mon's mega). The species is still known
            # public info (what the opponent sees), so encode identity-only
            # with default battle state instead of crashing.
            mon = side["mons"].get(sp) or {"species": sp}
            cat, num, mv, stat = _mon_features(mon, is_me, int(sp in actives))
            species[t], item[t], ability[t], status[t] = cat["species"], cat["item"], cat["ability"], cat["status"]
            numeric[t] = num
            moves[t] = mv
            static[t] = stat
            mask[t] = 1.0

    field = _encode_field(state)
    return {"species": species, "item": item, "ability": ability, "status": status,
            "moves": moves, "numeric": numeric, "static": static, "mask": mask, "field": field}


def _one_hot(value: str, categories: list[str]) -> np.ndarray:
    """CATEGORICAL one-hot, not an ordinal scalar index (2026-07-21 fix,
    [[net-external-review-2026-07-21]]): weather/terrain were previously a
    single float index fed straight into a Linear layer, which treats
    "Sandstorm" (whatever index it happens to land on) as quantitatively
    "more" than "RainDance" - nonsense for a category. A small, fixed
    vocabulary (5-6 values) makes one-hot the natural fit here (a Linear
    layer over one-hot is mathematically equivalent to summing learned
    per-category embeddings - the same reasoning that already made the
    `static` type multi-hot correct); large vocabularies (items/abilities/
    moves) instead route through the real embedding tables - see
    model/policy_net.py's meta handling.

    An unrecognized value gets its OWN explicit trailing slot, separate
    from `categories[0]` (the real "none" state) - the old scalar-index
    version used UNK=1 for this, which happens to collide with whichever
    real category sits at index 1 (e.g. an unrecognized weather string
    would have silently encoded as "RainDance").
    """
    vec = np.zeros(len(categories) + 1, dtype=np.float32)
    vec[categories.index(value) if value in categories else len(categories)] = 1.0
    return vec


def _encode_field(state: dict) -> np.ndarray:
    weather = state.get("weather") or ""   # None -> "" (the real "no weather" category)
    terrain = state.get("terrain") or ""
    w = _one_hot(weather, _WEATHER)      # len(_WEATHER)+1
    ter = _one_hot(terrain, _TERRAIN)    # len(_TERRAIN)+1
    cond_keys = ["tailwind", "reflect", "light_screen", "aurora_veil"]
    me_c = [float(state["me"]["cond"].get(k, False)) for k in cond_keys]
    opp_c = [float(state["opp"]["cond"].get(k, False)) for k in cond_keys]
    return np.concatenate([w, ter, [float(state.get("trick_room", False))], me_c, opp_c]).astype(np.float32)


# ---------------------------------------------------------------------------
# Meta layer: the belief usage prior as MODEL INPUT (the meta conditioning
# the user asked for - so the net keys off "what this species usually runs",
# not just what's been revealed, and stays robust when the meta shifts as
# long as this table is refreshed). Per token we expose the single most-
# likely item and ability (vocab index + probability), folded to the base
# species the weights are keyed by. Items are id-keyed, abilities display-
# name-keyed in the table (both normalized via to_id on lookup).
# ---------------------------------------------------------------------------
_WEIGHTS = json.loads(
    (_ROOT / "belief" / "usage_data" / "species_weights.json").read_text(encoding="utf-8")
)


def _top(dist: dict[str, float]) -> tuple[str, float]:
    if not dist:
        return "", 0.0
    name, w = max(dist.items(), key=lambda t: t[1])
    return name, max(0.0, min(1.0, w / 100.0))   # usage % -> rough probability


def _species_meta(species_id: str | None) -> tuple[int, float, int, float, int, float]:
    """(top_item_idx, top_item_prob, top_ability_idx, top_ability_prob,
    top_move_idx, top_move_prob) from the usage prior for this species
    (folded to its base), all zeros if unknown.

    The move entry (2026-07-21 addition, [[net-external-review-2026-07-21]])
    closes the Bo1 gap: replays/reconstruct.py can seed a mon's FULL
    moveset from a Bo3 Open Team Sheet, but Bo1 replays carry no sheet, so
    an unrevealed Bo1 move is genuinely unrecoverable after the fact - the
    usage-prior "what does this species usually run" is the correct
    ceiling there, not a bug to chase further. The data was already being
    scraped (belief/usage_data/species_weights.json's `moves` distribution)
    but nothing downstream ever read it until now.
    """
    if not species_id:
        return PAD, 0.0, PAD, 0.0, PAD, 0.0
    w = _WEIGHTS.get(base_species_id(species_id))
    if not w:
        return PAD, 0.0, PAD, 0.0, PAD, 0.0
    item, ip = _top(w.get("items", {}))
    abil, ap = _top(w.get("abilities", {}))
    move, mp = _top(w.get("moves", {}))
    return _lookup(ITEM_VOCAB, item), ip, _lookup(ABILITY_VOCAB, abil), ap, _lookup(MOVE_VOCAB, move), mp


# Target slots, from the acting side's point of view.
_TARGET = ["none", "opp_a", "opp_b", "self", "ally"]


def _target_index(target: str | None, side: str, slot: str) -> int:
    if not target:
        return 0
    tside, tslot = target[:2], target[2:]
    opp = "p2" if side == "p1" else "p1"
    if tside == opp:
        return 1 if tslot == "a" else 2
    if tside == side:
        return 3 if tslot == slot else 4
    return 0


def encode_action(action: dict | None, side: str, slot: str) -> dict:
    """A reconstructed per-slot action -> integer policy-head labels:
      type   : 0 pass/none, 1 move, 2 switch
      move   : MOVE_VOCAB index (PAD unless a move)
      target : _TARGET index, relative to the acting side (PAD unless move)
      mega   : 0/1
      switch : SPECIES_VOCAB index of the incoming mon (PAD unless switch)
    The net masks move/switch to the acting mon's legal set at inference;
    for the imitation TARGET the identity is unambiguous, so no mask needed.
    """
    if action is None:
        return {"type": 0, "move": PAD, "target": 0, "mega": 0, "switch": PAD}
    if action.get("kind") == "switch":
        return {"type": 2, "move": PAD, "target": 0, "mega": 0,
                "switch": resolve_species(action["species"])}
    return {"type": 1, "move": _lookup(MOVE_VOCAB, action.get("move")),
            "target": _target_index(action.get("target"), side, slot),
            "mega": int(action.get("mega", False)), "switch": PAD}


def encode_for_inference(state_dict: dict) -> dict:
    """A reconstructed board state ('me'/'opp' sides) -> encoded state tensors
    WITH per-token meta features, ready to batch into the net. The single
    entry point for inference (position eval, live play): no action/value
    labels, just the observable state the policy/value heads consume.

    Meta is 3 (idx, prob) pairs - item/ability/move - kept as SEPARATE
    int64-index / float32-prob arrays (not one packed float array) so
    model/policy_net.py can route the indices through the SAME embedding
    tables used for the revealed item/ability/move, weighted by prob
    (2026-07-21 fix, [[net-external-review-2026-07-21]]): the old packed
    float array fed vocab indices straight into a Linear layer as if they
    were continuous - item id 437 is not "more" than id 216.
    """
    n = 2 * MAX_MONS
    state = encode_state(state_dict)
    meta_item = np.zeros(n, dtype=np.int64)
    meta_item_prob = np.zeros(n, dtype=np.float32)
    meta_ability = np.zeros(n, dtype=np.int64)
    meta_ability_prob = np.zeros(n, dtype=np.float32)
    meta_move = np.zeros(n, dtype=np.int64)
    meta_move_prob = np.zeros(n, dtype=np.float32)
    for t, sid in enumerate(_token_species_ids(state_dict)):
        ii, ip, ai, ap, mi, mp = _species_meta(sid)
        meta_item[t], meta_item_prob[t] = ii, ip
        meta_ability[t], meta_ability_prob[t] = ai, ap
        meta_move[t], meta_move_prob[t] = mi, mp
    state["meta_item"] = meta_item
    state["meta_item_prob"] = meta_item_prob
    state["meta_ability"] = meta_ability
    state["meta_ability_prob"] = meta_ability_prob
    state["meta_move"] = meta_move
    state["meta_move_prob"] = meta_move_prob
    return state


def encode_example(example: dict) -> dict:
    """A full reconstructed example (replays/reconstruct.py) -> one training
    record: encoded state tensors (+ per-token meta features), per-slot
    action labels from the acting side's POV, the value target (did this
    side win), and the actor rating (for the >=cutoff filter / weighting).
    """
    state = encode_for_inference(example["state"])
    side = example["side"]
    return {
        "state": state,
        "actions": {sl: encode_action(example["action"].get(sl), side, sl) for sl in ("a", "b")},
        "value": (1.0 if example["won"] else 0.0) if example.get("won") is not None else None,
        "rating": example.get("rating"),
    }


def _token_species_ids(state: dict) -> list[str | None]:
    """Canonical species id per token slot, same packing as encode_state
    (me first at 0.., opp at MAX_MONS..), None for empty slots - so meta
    features line up with the state tokens."""
    ids: list[str | None] = [None] * (2 * MAX_MONS)
    for side_key, base in (("me", 0), ("opp", MAX_MONS)):
        for i, sp in enumerate(_side_token_species(state[side_key])):
            if sp is not None:
                ids[base + i] = resolve_species_id(sp)
    return ids


VOCAB_SIZES = {
    "species": len(SPECIES_VOCAB), "item": len(ITEM_VOCAB),
    "ability": len(ABILITY_VOCAB), "move": len(MOVE_VOCAB),
    "status": len(_STATUS), "weather": len(_WEATHER), "terrain": len(_TERRAIN),
    "target": len(_TARGET), "action_type": 3,
}

# Continuous per-token / field feature widths, for the net's linear
# projections. `static` = 6 base stats + N_TYPES multi-hot typing.
# `meta` no longer has a flat float width - meta_item/meta_ability/meta_move
# are int64 vocab indices routed through the SAME embedding tables as the
# revealed item/ability/move (model/policy_net.py), weighted by their
# *_prob float siblings, not concatenated as raw floats (2026-07-21 fix).
FEATURE_DIMS = {
    "numeric": 4 + len(_BOOST_STATS),   # hp + 3 flags + 7 boosts = 11
    "static": STATIC_DIM,               # 6 base stats + 18 types = 24
    # weather/terrain are now ONE-HOT (+1 explicit UNK slot each) rather
    # than a single ordinal scalar index - a Linear layer over one-hot is
    # mathematically equivalent to summing per-category embeddings, the
    # same reasoning already used for `static`'s type multi-hot.
    "field": (len(_WEATHER) + 1) + (len(_TERRAIN) + 1) + 1 + 2 * 4,  # weather,terrain,TR + per-side conds
}
