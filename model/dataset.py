"""Torch dataset over reconstructed replay examples for the imitation net
([[replay-net-direction]]). Reads replays/examples/*.jsonl, runs each record
through model/encoding.py::encode_example, and serves fixed-shape tensors.

Design choices:
- **Pre-encode once into RAM.** encode_example does real work (species
  resolution, usage-prior meta lookups); doing it per epoch would waste it.
  The filtered corpus is small enough (~40k x a few KB) to hold encoded, so
  epochs are just tensor indexing.
- **Species dropout is applied per __getitem__, not baked in.** It must be
  random each epoch (the whole point is to sometimes hide identity so the
  net leans on the static role profile - base stats/types/moves/ability,
  the Incineroar<->Scrafty lever, [[net-generalization-design]]). A dropped
  token's species index becomes UNK (identity unknown) while its mask stays
  1 (the token is still a real mon) - so attention still sees it, just
  without the name.
- **Rating filter + weight.** Policy imitates the acting player; higher-
  rated games get more weight and a floor filter drops noisy low-ladder
  play. Unrated games (rating None) fail any positive floor.

Per-slot action labels carry a DECISION MASK: a slot only contributes
policy loss when its acting mon actually chose (moved/switched); an empty
or passed slot (type 0) is masked out. move/target/mega heads train only on
move slots; the switch head only on switch slots; the value head always.

Run a quick self-check from the project root: python -m model.dataset
"""

import glob
import json
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import Dataset

from model.encoding import UNK, encode_example, MAX_MONS

_ROOT = Path(__file__).resolve().parent.parent
EXAMPLES_DIR = _ROOT / "replays" / "examples"


def rating_weight(rating) -> float:
    """Higher-rated actors weighted more (imitate the stronger player).
    Centered so 1300 -> 1.0, clamped to [0.5, 2.0]; None -> 0.5."""
    if rating is None:
        return 0.5
    return float(max(0.5, min(2.0, 1.0 + (rating - 1300) / 400.0)))


def _stack_actions(actions: dict) -> dict:
    """encode_example's {a:{...}, b:{...}} -> per-field (2,) long tensors in
    slot order [a, b], plus decision/move/switch masks for loss gating."""
    slots = [actions["a"], actions["b"]]
    typ = torch.tensor([s["type"] for s in slots], dtype=torch.long)      # 0 pass,1 move,2 switch
    return {
        "type": typ,
        "move": torch.tensor([s["move"] for s in slots], dtype=torch.long),
        "target": torch.tensor([s["target"] for s in slots], dtype=torch.long),
        "mega": torch.tensor([s["mega"] for s in slots], dtype=torch.float32),
        "switch": torch.tensor([s["switch"] for s in slots], dtype=torch.long),
        "decision_mask": (typ != 0).float(),   # slot actually acted
        "move_mask": (typ == 1).float(),        # move/target/mega heads
        "switch_mask": (typ == 2).float(),      # switch head
    }


def _to_tensors(enc: dict) -> dict:
    """encode_example output (numpy) -> a flat dict of torch tensors, the
    unit __getitem__ serves (before per-call species dropout)."""
    s = enc["state"]
    state = {
        "species": torch.from_numpy(s["species"]).long(),
        "item": torch.from_numpy(s["item"]).long(),
        "ability": torch.from_numpy(s["ability"]).long(),
        "status": torch.from_numpy(s["status"]).long(),
        "moves": torch.from_numpy(s["moves"]).long(),
        "numeric": torch.from_numpy(s["numeric"]).float(),
        "static": torch.from_numpy(s["static"]).float(),
        "meta": torch.from_numpy(s["meta"]).float(),
        "field": torch.from_numpy(s["field"]).float(),
        "mask": torch.from_numpy(s["mask"]).float(),
    }
    return {
        "state": state,
        "actions": _stack_actions(enc["actions"]),
        "value": torch.tensor(enc["value"], dtype=torch.float32),
        "weight": torch.tensor(rating_weight(enc["rating"]), dtype=torch.float32),
    }


class ReplayDataset(Dataset):
    def __init__(self, paths=None, min_rating: int = 1200, species_dropout: float = 0.15,
                 limit: int = 0, verbose: bool = True):
        """paths: jsonl files (default: all of replays/examples/). min_rating:
        drop examples whose actor rating is below this (None counts as below
        any positive floor). species_dropout: per-token probability of hiding
        a real mon's species (-> UNK) each __getitem__. limit: cap examples
        (0 = all), for quick runs."""
        self.species_dropout = species_dropout
        if paths is None:
            paths = sorted(glob.glob(str(EXAMPLES_DIR / "*.jsonl")))
        self.records: list[dict] = []
        kept = skipped_rating = skipped_value = 0
        for fp in paths:
            for line in open(fp, encoding="utf-8"):
                ex = json.loads(line)
                if ex.get("won") is None:        # no value target
                    skipped_value += 1
                    continue
                r = ex.get("rating")
                if min_rating > 0 and (r is None or r < min_rating):
                    skipped_rating += 1
                    continue
                self.records.append(_to_tensors(encode_example(ex)))
                kept += 1
                if limit and kept >= limit:
                    break
            if limit and kept >= limit:
                break
        if verbose:
            print(f"ReplayDataset: kept {kept} examples "
                  f"(min_rating={min_rating}; dropped {skipped_rating} sub-rating, "
                  f"{skipped_value} unlabeled), species_dropout={species_dropout}")

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, i: int) -> dict:
        return _apply(self.records[i], self.species_dropout)


def _apply(rec: dict, species_dropout: float) -> dict:
    """Serve one record, optionally hiding some real tokens' species (->UNK)."""
    state = dict(rec["state"])
    if species_dropout > 0.0:
        sp = state["species"].clone()
        real = state["mask"] > 0                            # only real tokens
        drop = (torch.rand_like(sp, dtype=torch.float32) < species_dropout) & real
        sp[drop] = UNK                                      # identity hidden, token still present
        state["species"] = sp
    return {"state": state, "actions": rec["actions"],
            "value": rec["value"], "weight": rec["weight"]}


class _RecordView(Dataset):
    """A thin Dataset over a shared, already-encoded record list with its own
    species_dropout - so train (dropout on) and val (dropout off) can share a
    single expensive encode pass."""

    def __init__(self, records: list, species_dropout: float):
        self.records = records
        self.species_dropout = species_dropout

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, i: int) -> dict:
        return _apply(self.records[i], self.species_dropout)


def load_train_val(min_rating: int = 1200, species_dropout: float = 0.15,
                   val_frac: float = 0.1, limit: int = 0, seed: int = 0, verbose: bool = True):
    """Encode the filtered corpus ONCE, then split into a train view (species
    dropout on) and a val view (dropout OFF - measure imitation with full
    info). Returns (train_view, val_view)."""
    base = ReplayDataset(min_rating=min_rating, species_dropout=species_dropout,
                         limit=limit, verbose=verbose)
    idx = np.arange(len(base.records))
    np.random.default_rng(seed).shuffle(idx)
    n_val = max(1, int(len(idx) * val_frac))
    val_recs = [base.records[i] for i in idx[:n_val]]
    train_recs = [base.records[i] for i in idx[n_val:]]
    if verbose:
        print(f"split: {len(train_recs)} train / {len(val_recs)} val "
              f"(val species_dropout=0.0)")
    return _RecordView(train_recs, species_dropout), _RecordView(val_recs, 0.0)


def _selfcheck():
    ds = ReplayDataset(min_rating=1200, species_dropout=0.15, limit=2000)
    from torch.utils.data import DataLoader
    dl = DataLoader(ds, batch_size=32, shuffle=True)
    batch = next(iter(dl))
    st = batch["state"]
    print("batch state shapes:")
    for k, v in st.items():
        print(f"  {k:8s} {tuple(v.shape)} {v.dtype}")
    print("actions:")
    for k, v in batch["actions"].items():
        print(f"  {k:13s} {tuple(v.shape)} {v.dtype}")
    print("value", tuple(batch["value"].shape), "weight range",
          float(batch["weight"].min()), float(batch["weight"].max()))
    # species-dropout sanity: over many draws of one item, some real tokens go UNK
    idx = 0
    real = (ds.records[idx]["state"]["mask"] > 0)
    n_unk = 0
    for _ in range(200):
        sp = ds[idx]["state"]["species"]
        n_unk += int(((sp == UNK) & real).sum())
    print(f"species-dropout: {n_unk} UNK-hits over 200 draws of item 0 "
          f"({int(real.sum())} real tokens) -> {'ok' if n_unk > 0 else 'FAIL (no dropout)'}")
    # me-active tokens are slots 0 and 1 (fixed positions) - policy heads read these
    print("me-active token indices for per-slot policy heads: 0 (a), 1 (b)")
    print("PASS" if len(ds) > 0 else "FAIL: empty dataset")


if __name__ == "__main__":
    _selfcheck()
