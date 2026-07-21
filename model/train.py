"""Train the imitation net ([[replay-net-direction]]): rating-weighted
policy imitation (type/move/target/mega/switch) + win-value regression over
the reconstructed replay corpus, on CUDA.

The metrics that matter for "is it learning to play":
  move-acc   : top-1 match of the played move on move slots (the core
               imitation signal - does it pick what a real player picked)
  type-acc   : move-vs-switch decision accuracy
  value-acc  : win/loss prediction accuracy (the board-eval signal)
Validation runs with species dropout OFF, so these measure real, full-info
imitation - while training sees dropout, forcing role-based play
([[net-generalization-design]]).

Examples:
  python -m model.train --epochs 8                 # full corpus (rating>=1200)
  python -m model.train --limit 4000 --epochs 5    # quick sanity run
  python -m model.train --resume model/checkpoints/imitation_v1.pt \
      --value-coef 4.0 --epochs 60 --lr 1e-4 --out model/checkpoints/imitation_v2.pt
      # continuation run targeting value-head convergence ([[imitation-net-v1]]):
      # v1's value-acc was still rising at 0.58/epoch 25 when training stopped,
      # and value_coef=1.0 (the default) lets the value BCE (capped at ln2=0.69)
      # get drowned out by the five policy losses (summing to several nats
      # early on) in the shared backward pass - value_coef re-balances that.
"""

import argparse
import time

import torch
from torch.utils.data import DataLoader

from model.dataset import load_train_val
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
    net.train()
    return {
        "loss": tot["loss"] / max(tot["n"], 1),
        "move_acc": move_ok / max(move_n, 1),
        "type_acc": type_ok / max(type_n, 1),
        "value_acc": val_ok / max(val_n, 1),
    }


def train(args):
    dev = "cuda" if torch.cuda.is_available() and not args.cpu else "cpu"
    train_ds, val_ds = load_train_val(min_rating=args.min_rating,
                                      species_dropout=args.species_dropout,
                                      val_frac=args.val_frac, limit=args.limit, seed=args.seed)
    train_dl = DataLoader(train_ds, batch_size=args.batch, shuffle=True, drop_last=True)
    val_dl = DataLoader(val_ds, batch_size=args.batch, shuffle=False)

    # --resume: continue training an existing checkpoint (e.g. imitation_v1.pt)
    # instead of starting fresh - architecture dims come from the checkpoint's
    # own saved args so the state_dict always loads cleanly, overriding
    # whatever --d-model/--layers/--species-dim were passed on this run.
    ckpt = torch.load(args.resume, map_location=dev, weights_only=False) if args.resume else None
    arch = ckpt["args"] if ckpt else vars(args)
    net = PolicyValueNet(d_model=arch.get("d_model", args.d_model), layers=arch.get("layers", args.layers),
                         species_dim=arch.get("species_dim", args.species_dim)).to(dev)
    if ckpt:
        net.load_state_dict(ckpt["model"])
        print(f"resumed from {args.resume}")
    n_params = sum(p.numel() for p in net.parameters())
    opt = torch.optim.AdamW(net.parameters(), lr=args.lr, weight_decay=args.wd)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=max(args.epochs, 1))
    print(f"device={dev}  params={n_params:,}  "
          f"train={len(train_ds)} val={len(val_ds)}  batch={args.batch}  value_coef={args.value_coef}")

    base = evaluate(net, val_dl, dev)
    print(f"epoch 0 (init)  val loss {base['loss']:.3f}  "
          f"move-acc {base['move_acc']:.3f}  type-acc {base['type_acc']:.3f}  "
          f"value-acc {base['value_acc']:.3f}")

    best_value_acc = base["value_acc"]
    for ep in range(1, args.epochs + 1):
        t0 = time.time()
        run = n = 0
        for batch in train_dl:
            batch = _to_device(batch, dev)
            out = net(batch["state"])
            total, parts = compute_loss(out, batch, value_coef=args.value_coef)
            opt.zero_grad()
            total.backward()
            torch.nn.utils.clip_grad_norm_(net.parameters(), 5.0)
            opt.step()
            run += float(total) * batch["value"].size(0)
            n += batch["value"].size(0)
        sched.step()
        ev = evaluate(net, val_dl, dev)
        improved = ev["value_acc"] > best_value_acc
        best_value_acc = max(best_value_acc, ev["value_acc"])
        print(f"epoch {ep:2d}  train {run/max(n,1):.3f}  |  val {ev['loss']:.3f}  "
              f"move-acc {ev['move_acc']:.3f}  type-acc {ev['type_acc']:.3f}  "
              f"value-acc {ev['value_acc']:.3f}{'*' if improved else ' '}  "
              f"lr {sched.get_last_lr()[0]:.2e}  ({time.time()-t0:.1f}s)")
        if improved and args.out:
            torch.save({"model": net.state_dict(), "args": vars(args)}, args.out)

    if args.out:
        print(f"best value-acc {best_value_acc:.3f} -> saved to {args.out}")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--epochs", type=int, default=8)
    ap.add_argument("--batch", type=int, default=128)
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--wd", type=float, default=1e-2)
    ap.add_argument("--min-rating", type=int, default=1200)
    ap.add_argument("--species-dropout", type=float, default=0.15)
    ap.add_argument("--val-frac", type=float, default=0.1)
    ap.add_argument("--limit", type=int, default=0, help="cap examples (0=all), for quick runs")
    ap.add_argument("--d-model", type=int, default=128)
    ap.add_argument("--layers", type=int, default=4)
    ap.add_argument("--species-dim", type=int, default=32)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--cpu", action="store_true")
    ap.add_argument("--out", type=str, default="", help="save the BEST value-acc checkpoint here (overwritten each improvement)")
    ap.add_argument("--resume", type=str, default="", help="continue training from this checkpoint (arch dims taken from it)")
    ap.add_argument("--value-coef", type=float, default=1.0,
                    help="weight on the value BCE term - raise this to fix value convergence "
                         "(the value loss is capped at ln2~=0.69 vs several nats for the summed "
                         "policy losses early in training, so at 1.0 it's easily drowned out)")
    args = ap.parse_args()
    train(args)


if __name__ == "__main__":
    main()
