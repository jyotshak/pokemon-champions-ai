"""Qualitative eval of the trained imitation net ([[imitation-net-v1]]) on
KNOWN positions - the "does it play sensibly" gate before wiring it into
full games. Unlike move-acc (which just asks "did it match the replay"),
this constructs board states whose right answer we understand and prints the
net's policy + value so we can eyeball whether 0.46 move-acc is SENSIBLE
play or lucky matching.

Not a pass/fail test - a readout. For each scenario it prints, per my active
mon: action-type distribution (pass/move/switch), the move policy masked to
that mon's known moves (what a real inference wrapper would do), the argmax
target, and the state's win-value.

Run: python -m model.eval_positions [path/to/checkpoint.pt]
"""

import sys

import numpy as np
import torch

from model.encoding import (
    encode_for_inference, resolve_species, _lookup, MOVE_VOCAB, _TARGET,
)
from model.policy_net import PolicyValueNet, ME_ACTIVE_SLOTS

CKPT = sys.argv[1] if len(sys.argv) > 1 else "model/checkpoints/imitation_v1.pt"


def _mon(species, moves, hp=1.0, item=None, ability=None, status=None, boosts=None):
    return {"species": species, "hp": hp, "status": status, "boosts": boosts or {},
            "item": item, "ability": ability, "fainted": False, "moves": moves}


def _side(a, b, mons, cond=None):
    return {"active": {"a": a, "b": b}, "mons": mons,
            "cond": cond or {"tailwind": False, "reflect": False, "light_screen": False, "aurora_veil": False}}


def _state(me, opp, weather=None, tr=False, terrain=None):
    return {"me": me, "opp": opp, "weather": weather, "trick_room": tr, "terrain": terrain}


def _batch(state_dict, device):
    """encode_for_inference (numpy) -> a batch-of-1 tensor dict for the net."""
    enc = encode_for_inference(state_dict)
    out = {}
    for k, v in enc.items():
        t = torch.from_numpy(v)
        t = t.long() if v.dtype.kind in "iu" else t.float()
        out[k] = t.unsqueeze(0).to(device)
    return out


def _softmax(x):
    e = np.exp(x - x.max())
    return e / e.sum()


@torch.no_grad()
def show(net, device, title, state_dict, inspect):
    """inspect: list of (slot_letter, species, [candidate moves]) to read out."""
    print(f"\n=== {title} ===")
    out = net(_batch(state_dict, device))
    val = torch.sigmoid(out["value"])[0].item()
    print(f"  state win-value (me): {val:.3f}")
    slot_idx = {"a": 0, "b": 1}
    for letter, species, cand_moves in inspect:
        si = slot_idx[letter]
        tok = ME_ACTIVE_SLOTS[si]  # me-active token index for this slot
        typ = _softmax(out["type"][0, si].cpu().numpy())
        tgt = out["target"][0, si].cpu().numpy()
        move_logits = out["move"][0, si].cpu().numpy()
        # mask move head to this mon's known moves (as a real inference wrapper does)
        idxs = [_lookup(MOVE_VOCAB, m) for m in cand_moves]
        masked = _softmax(move_logits[idxs])
        ranked = sorted(zip(cand_moves, masked), key=lambda t: -t[1])
        print(f"  [{letter}] {species}: type p(pass/move/switch)="
              f"[{typ[0]:.2f} {typ[1]:.2f} {typ[2]:.2f}]  target*={_TARGET[int(tgt.argmax())]}")
        print("       move policy: " + ", ".join(f"{m} {p:.2f}" for m, p in ranked))


def main():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    ckpt = torch.load(CKPT, map_location=device, weights_only=False)
    a = ckpt.get("args", {})
    net = PolicyValueNet(d_model=a.get("d_model", 128), layers=a.get("layers", 4),
                         species_dim=a.get("species_dim", 32)).to(device)
    net.load_state_dict(ckpt["model"])
    net.eval()
    print(f"loaded {CKPT}  (device={device})")

    # --- Scenario A: Wide Guard read ------------------------------------
    # Opp Garchomp threatens Rock Slide (spread, hits both my mons); Aerodactyl
    # holds Wide Guard. Sensible: Aero values Wide Guard highly.
    A = _state(
        me=_side("Aerodactyl", "Charizard", {
            "Aerodactyl": _mon("Aerodactyl", ["Wide Guard", "Rock Slide", "Tailwind", "Protect"]),
            "Charizard": _mon("Charizard", ["Heat Wave", "Protect", "Air Slash", "Solar Beam"]),
        }),
        opp=_side("Garchomp", "Sylveon", {
            "Garchomp": _mon("Garchomp", ["Rock Slide", "Earthquake"]),   # revealed spread threats
            "Sylveon": _mon("Sylveon", ["Hyper Voice"]),
        }))
    show(net, device, "A. Wide Guard vs Garchomp Rock Slide (expect Aero -> Wide Guard high)", A,
         [("a", "Aerodactyl", ["Wide Guard", "Rock Slide", "Tailwind", "Protect"])])

    # --- Scenario B: Fake Out ------------------------------------------
    # Incineroar leads with Fake Out available vs two healthy threats.
    B = _state(
        me=_side("Incineroar", "Whimsicott", {
            "Incineroar": _mon("Incineroar", ["Fake Out", "Flare Blitz", "Knock Off", "Parting Shot"],
                               ability="Intimidate"),
            "Whimsicott": _mon("Whimsicott", ["Tailwind", "Moonblast", "Encore", "Protect"]),
        }),
        opp=_side("Garchomp", "Landorus", {
            "Garchomp": _mon("Garchomp", ["Rock Slide", "Earthquake"]),
            "Landorus": _mon("Landorus", ["Earth Power", "Sludge Bomb"]),
        }))
    show(net, device, "B. Incineroar lead (expect Fake Out prominent)", B,
         [("a", "Incineroar", ["Fake Out", "Flare Blitz", "Knock Off", "Parting Shot"])])

    # --- Scenario C: Trick Room ----------------------------------------
    # Slow setter (Farigiraf) vs a fast opponent side. Sensible: Trick Room high.
    C = _state(
        me=_side("Farigiraf", "Torkoal", {
            "Farigiraf": _mon("Farigiraf", ["Trick Room", "Psychic", "Foul Play", "Protect"]),
            "Torkoal": _mon("Torkoal", ["Eruption", "Heat Wave", "Protect", "Body Press"]),
        }),
        opp=_side("Dragapult", "Whimsicott", {
            "Dragapult": _mon("Dragapult", ["Dragon Darts", "Phantom Force"]),
            "Whimsicott": _mon("Whimsicott", ["Tailwind", "Moonblast"]),
        }))
    show(net, device, "C. Slow Farigiraf vs fast opp (expect Trick Room high)", C,
         [("a", "Farigiraf", ["Trick Room", "Psychic", "Foul Play", "Protect"])])


if __name__ == "__main__":
    main()
