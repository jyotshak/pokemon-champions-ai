"""Evaluate two (or more) checkpoints on the SAME held-out set(s), so a
comparison like "does continuation-training on a freshly-scraped batch
help or hurt" isn't confounded by each run reporting accuracy against its
OWN (differently-distributed) validation split - e.g. a continuation run
that trains+validates only on a fresh, higher-rating-floor batch naturally
sees different move-acc/value-acc numbers than the base run's own val
split, even if the model didn't get better or worse in any absolute sense.

Both checkpoints are scored on: (a) the chronologically-latest val slice
of the ORIGINAL corpus (replays/examples/<fmt>.jsonl) and (b) the
chronologically-latest val slice of any not-yet-merged *new.jsonl batch
(if present) - each val slice built with load_train_val's own chronological
by-game split (never the training portion), so a checkpoint is never
scored on data it could have trained on.

Run: python -m model.compare_checkpoints ckpt_a.pt ckpt_b.pt [ckpt_c.pt ...]
     python -m model.compare_checkpoints --old-only ckpt_a.pt ckpt_b.pt
"""

import argparse
import glob

import torch
from torch.utils.data import DataLoader

from model.dataset import EXAMPLES_DIR, load_train_val
from model.policy_net import PolicyValueNet, compute_loss, _to_device


@torch.no_grad()
def evaluate(net, loader, dev) -> dict:
    net.eval()
    tot = {"loss": 0.0, "n": 0}
    move_ok = move_n = type_ok = type_n = val_ok = val_n = 0
    for batch in loader:
        batch = _to_device(batch, dev)
        out = net(batch["state"])
        total, _ = compute_loss(out, batch)
        bs = batch["value"].size(0)
        tot["loss"] += float(total) * bs
        tot["n"] += bs
        a = batch["actions"]
        mm = a["move_mask"].bool()
        if mm.any():
            move_ok += int((out["move"].argmax(-1)[mm] == a["move"][mm]).sum())
            move_n += int(mm.sum())
        dm = a["decision_mask"].bool()
        if dm.any():
            type_ok += int((out["type"].argmax(-1)[dm] == a["type"][dm]).sum())
            type_n += int(dm.sum())
        val_ok += int(((out["value"] > 0).float() == batch["value"]).sum())
        val_n += bs
    return {
        "loss": tot["loss"] / max(tot["n"], 1),
        "move_acc": move_ok / max(move_n, 1),
        "type_acc": type_ok / max(type_n, 1),
        "value_acc": val_ok / max(val_n, 1),
        "n": tot["n"],
    }


def load_net(ckpt_path: str, dev: str) -> PolicyValueNet:
    ckpt = torch.load(ckpt_path, map_location=dev, weights_only=False)
    a = ckpt.get("args", {})
    net = PolicyValueNet(d_model=a.get("d_model", 128), layers=a.get("layers", 4),
                         species_dim=a.get("species_dim", 32)).to(dev)
    net.load_state_dict(ckpt["model"])
    net.eval()
    return net


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("checkpoints", nargs="+", help="checkpoint paths to compare")
    ap.add_argument("--batch", type=int, default=256)
    ap.add_argument("--min-rating", type=int, default=1200)
    ap.add_argument("--val-frac", type=float, default=0.1)
    ap.add_argument("--old-only", action="store_true", help="skip the *new.jsonl val slice")
    args = ap.parse_args()
    dev = "cuda" if torch.cuda.is_available() else "cpu"

    old_paths = sorted(p for p in glob.glob(str(EXAMPLES_DIR / "*.jsonl")) if not p.endswith("new.jsonl"))
    new_paths = sorted(glob.glob(str(EXAMPLES_DIR / "*new.jsonl")))

    val_sets = {}
    if old_paths:
        print(f"building 'original corpus' val slice from {len(old_paths)} file(s)...")
        _, val_old = load_train_val(min_rating=args.min_rating, species_dropout=0.0,
                                    val_frac=args.val_frac, paths=old_paths, verbose=False)
        val_sets["original-corpus (latest val slice)"] = val_old
    if new_paths and not args.old_only:
        print(f"building 'new (not-yet-merged) batch' val slice from {len(new_paths)} file(s)...")
        _, val_new = load_train_val(min_rating=args.min_rating, species_dropout=0.0,
                                    val_frac=args.val_frac, paths=new_paths, verbose=False)
        val_sets["new-batch (latest val slice)"] = val_new

    loaders = {name: DataLoader(ds, batch_size=args.batch, shuffle=False) for name, ds in val_sets.items()}

    header = f"{'checkpoint':30s}" + "".join(f"{name:38s}" for name in loaders)
    print(f"\n{header}")
    for ckpt_path in args.checkpoints:
        net = load_net(ckpt_path, dev)
        row = f"{ckpt_path:30s}"
        for name, loader in loaders.items():
            m = evaluate(net, loader, dev)
            row += f"move {m['move_acc']:.3f} type {m['type_acc']:.3f} val {m['value_acc']:.3f} (n={m['n']:<6d})"
        print(row)


if __name__ == "__main__":
    main()
