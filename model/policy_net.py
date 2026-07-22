"""The imitation net ([[replay-net-direction]]): a small transformer over
per-mon tokens that outputs, per my-active slot, a Showdown-style action
(type / move / target / mega / switch) plus a scalar win-value.

Shape contract (from model/encoding.py):
- 2*MAX_MONS = 12 mon tokens: me at 0..5 (active a=0, b=1, bench 2..5),
  opp at 6..11. A 13th FIELD token carries weather/terrain/TR/side-conds.
- Each mon token embeds species/item/ability/status (+ mean-pooled moves)
  and projects numeric (battle state) + static (base stats & typing).
  Species embedding is deliberately SMALL and is randomly dropped in the
  dataset (-> UNK) so the net must lean on the static role profile - the
  Incineroar<->Scrafty generalization lever ([[net-generalization-design]]).
- META (usage-prior "likely item/ability/move") is NOT concatenated as raw
  floats (2026-07-21 fix, [[net-external-review-2026-07-21]]: vocab index
  437 is not "more" than 216). Instead each meta index is embedded through
  the SAME table as the revealed value (self.item/self.ability/self.move -
  shares weights between "revealed" and "likely" representations) and
  blended in, weighted by its probability - see _meta_blend/the move
  mean-pool below.
- A learned per-TOKEN-POSITION embedding (self.pos_embed) is added before
  the encoder (2026-07-21 fix: plain self-attention has no positional
  signal at all - a review found zero positional/role embeddings anywhere,
  meaning attention had no explicit way to reason about WHICH physical
  slot - me_a vs me_b vs opp_a, etc. - a token occupies when computing how
  tokens should interact, only an implicit, unreinforced "fixed input
  order" convention). Token index <-> role is fixed by encoding.py's
  packing scheme, so a plain positional embedding doubles as a role
  embedding here.
- Policy heads are SHARED and applied to the two me-active tokens (0, 1):
  the same policy function decides for each active mon.
- Value = masked-mean pool over real tokens + the field token -> sigmoid.

Padded (empty) mon tokens are excluded from attention via a key-padding
mask; the field token is always present.

Sanity check from the project root: python -m model.policy_net
"""

import torch
import torch.nn as nn
import torch.nn.functional as F

from model.encoding import VOCAB_SIZES, FEATURE_DIMS, MAX_MONS

# Token indices for the two me-active slots the policy heads read.
ME_ACTIVE_SLOTS = (0, 1)
N_TOKENS = 2 * MAX_MONS + 1   # 12 mon tokens + 1 field token


def _meta_blend(revealed_idx: torch.Tensor, meta_idx: torch.Tensor, meta_prob: torch.Tensor,
                embed: nn.Embedding) -> torch.Tensor:
    """revealed_idx/meta_idx: (B,T) long; meta_prob: (B,T) float; embed: the
    SAME embedding table used for the revealed value. If revealed (idx != 0,
    PAD), use ONLY that embedding - a known fact shouldn't be diluted by a
    population prior. If not revealed, use the meta (usage-prior) embedding
    scaled by its probability - low confidence shrinks toward the neutral
    PAD embedding instead of asserting a specific guess."""
    known = (revealed_idx != 0).float().unsqueeze(-1)
    return known * embed(revealed_idx) + (1.0 - known) * meta_prob.unsqueeze(-1) * embed(meta_idx)


class MonTokenEmbed(nn.Module):
    """One mon (or the field) -> a d_model token vector."""

    def __init__(self, d_model: int, species_dim: int = 32):
        super().__init__()
        self.species = nn.Embedding(VOCAB_SIZES["species"], species_dim, padding_idx=0)
        self.item = nn.Embedding(VOCAB_SIZES["item"], 32, padding_idx=0)
        self.ability = nn.Embedding(VOCAB_SIZES["ability"], 32, padding_idx=0)
        self.status = nn.Embedding(VOCAB_SIZES["status"], 16, padding_idx=0)
        self.move = nn.Embedding(VOCAB_SIZES["move"], 48, padding_idx=0)
        cat_dim = (species_dim + 32 + 32 + 16 + 48
                   + FEATURE_DIMS["numeric"] + FEATURE_DIMS["static"])
        self.proj = nn.Sequential(nn.Linear(cat_dim, d_model), nn.LayerNorm(d_model))

    def forward(self, s: dict) -> torch.Tensor:
        # mean-pool the (up to 4) REAL revealed move embeddings, plus a 5th
        # PSEUDO-SLOT for the usage-prior "likely move" (meta_move, same
        # embedding table), weighted by its probability rather than a flat
        # 1.0 like a real reveal - so it contributes proportionally LESS
        # once several real moves are already known, and fully substitutes
        # when nothing is known yet (the Bo1 moveset gap - see
        # model/encoding.py::_species_meta).
        mv = self.move(s["moves"])                          # (B, T, 4, 48)
        mv_mask = (s["moves"] != 0).float().unsqueeze(-1)   # (B, T, 4, 1)
        meta_mv = self.move(s["meta_move"]).unsqueeze(2)                    # (B, T, 1, 48)
        meta_mv_w = s["meta_move_prob"].unsqueeze(-1).unsqueeze(-1)         # (B, T, 1, 1)
        mv_all = torch.cat([mv, meta_mv], dim=2)                            # (B, T, 5, 48)
        w_all = torch.cat([mv_mask, meta_mv_w], dim=2)                      # (B, T, 5, 1)
        mv_mean = (mv_all * w_all).sum(2) / w_all.sum(2).clamp(min=1e-6)   # (B, T, 48)

        item_repr = _meta_blend(s["item"], s["meta_item"], s["meta_item_prob"], self.item)
        ability_repr = _meta_blend(s["ability"], s["meta_ability"], s["meta_ability_prob"], self.ability)

        cat = torch.cat([
            self.species(s["species"]), item_repr, ability_repr, self.status(s["status"]), mv_mean,
            s["numeric"], s["static"],
        ], dim=-1)
        return self.proj(cat)                               # (B, T, d_model)


class PolicyValueNet(nn.Module):
    def __init__(self, d_model: int = 128, nhead: int = 8, layers: int = 4,
                 ffn: int = 256, dropout: float = 0.1, species_dim: int = 32):
        super().__init__()
        self.tokens = MonTokenEmbed(d_model, species_dim)
        self.field_proj = nn.Sequential(nn.Linear(FEATURE_DIMS["field"], d_model), nn.LayerNorm(d_model))
        # Learned per-token-position embedding (2026-07-21 fix - see module
        # docstring): token index <-> role (me_a, me_b, me_bench_0..3,
        # opp_a, opp_b, opp_bench_0..3, field) is fixed by encoding.py's
        # packing, so this doubles as a role embedding.
        self.pos_embed = nn.Embedding(N_TOKENS, d_model)
        enc = nn.TransformerEncoderLayer(d_model, nhead, ffn, dropout,
                                         batch_first=True, norm_first=True)
        self.encoder = nn.TransformerEncoder(enc, layers)

        # Shared per-slot policy heads (applied to each me-active token).
        self.head_type = nn.Linear(d_model, VOCAB_SIZES["action_type"])
        self.head_move = nn.Linear(d_model, VOCAB_SIZES["move"])
        self.head_target = nn.Linear(d_model, VOCAB_SIZES["target"])
        self.head_mega = nn.Linear(d_model, 1)
        self.head_switch = nn.Linear(d_model, VOCAB_SIZES["species"])
        # Value from a masked-mean pool of all real tokens (+ field).
        self.value = nn.Sequential(nn.Linear(d_model, d_model), nn.ReLU(), nn.Linear(d_model, 1))

    def forward(self, state: dict) -> dict:
        tok = self.tokens(state)                            # (B, 12, d)
        field = self.field_proj(state["field"]).unsqueeze(1)  # (B, 1, d)
        h = torch.cat([tok, field], dim=1)                  # (B, 13, d)
        h = h + self.pos_embed(torch.arange(N_TOKENS, device=h.device)).unsqueeze(0)

        # key-padding mask: True = ignore. Empty mon tokens padded; field kept.
        B = tok.size(0)
        field_keep = torch.ones(B, 1, device=tok.device)
        keep = torch.cat([state["mask"], field_keep], dim=1)  # (B, 13), 1=real
        pad_mask = keep == 0
        h = self.encoder(h, src_key_padding_mask=pad_mask)  # (B, 13, d)

        # per-slot policy from the me-active tokens (shared heads)
        slot_h = h[:, ME_ACTIVE_SLOTS, :]                   # (B, 2, d)
        out = {
            "type": self.head_type(slot_h),                 # (B, 2, 3)
            "move": self.head_move(slot_h),                 # (B, 2, |moves|)
            "target": self.head_target(slot_h),             # (B, 2, 5)
            "mega": self.head_mega(slot_h).squeeze(-1),     # (B, 2)
            "switch": self.head_switch(slot_h),             # (B, 2, |species|)
        }
        # masked-mean pool over real tokens for value
        keep_f = keep.unsqueeze(-1)
        pooled = (h * keep_f).sum(1) / keep_f.sum(1).clamp(min=1.0)
        out["value"] = self.value(pooled).squeeze(-1)       # (B,) logit
        return out


def compute_loss(out: dict, batch: dict, value_coef: float = 1.0) -> tuple:
    """Rating-weighted, mask-gated imitation + value loss. Returns
    (total, parts_dict) with per-head scalar tensors for logging.

    Per-slot policy heads only train where the label is a real decision:
      type   -> decision_mask (slot acted at all)
      move/target/mega -> move_mask (the action was a move)
      switch -> switch_mask (the action was a switch)
    Value trains on every example (BCE on win). All terms rating-weighted.
    """
    a, w = batch["actions"], batch["weight"]                # w: (B,)
    ws = w.unsqueeze(1)                                      # (B,1) per-slot broadcast

    def masked_ce(logits, target, m):
        # logits (B,2,C) target (B,2) m (B,2); weight per slot by ws
        ce = F.cross_entropy(logits.reshape(-1, logits.size(-1)),
                             target.reshape(-1), reduction="none").reshape(target.shape)
        wm = m * ws
        return (ce * wm).sum() / wm.sum().clamp(min=1e-6)

    l_type = masked_ce(out["type"], a["type"], a["decision_mask"])
    l_move = masked_ce(out["move"], a["move"], a["move_mask"])
    l_target = masked_ce(out["target"], a["target"], a["move_mask"])
    l_switch = masked_ce(out["switch"], a["switch"], a["switch_mask"])

    mega_bce = F.binary_cross_entropy_with_logits(out["mega"], a["mega"], reduction="none")
    mm = a["move_mask"] * ws
    l_mega = (mega_bce * mm).sum() / mm.sum().clamp(min=1e-6)

    val_bce = F.binary_cross_entropy_with_logits(out["value"], batch["value"], reduction="none")
    l_value = (val_bce * w).sum() / w.sum().clamp(min=1e-6)

    total = l_type + l_move + l_target + l_switch + l_mega + value_coef * l_value
    return total, {"type": l_type, "move": l_move, "target": l_target,
                   "switch": l_switch, "mega": l_mega, "value": l_value}


def _sanity():
    from model.dataset import ReplayDataset
    from torch.utils.data import DataLoader
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    ds = ReplayDataset(min_rating=1200, species_dropout=0.15, limit=256)
    dl = DataLoader(ds, batch_size=32, shuffle=True)
    net = PolicyValueNet().to(dev)
    n_params = sum(p.numel() for p in net.parameters())
    print(f"device={dev}  params={n_params:,}")
    batch = next(iter(dl))
    batch = _to_device(batch, dev)
    out = net(batch["state"])
    for k, v in out.items():
        print(f"  out[{k}] {tuple(v.shape)}")
    total, parts = compute_loss(out, batch)
    print("initial loss", float(total), {k: round(float(v), 3) for k, v in parts.items()})
    # one backward step must run clean
    total.backward()
    gnorm = sum(p.grad.norm().item() for p in net.parameters() if p.grad is not None)
    print("backward ok, grad-norm sum", round(gnorm, 3))
    print("PASS")


def _to_device(batch: dict, dev: str) -> dict:
    return {
        "state": {k: v.to(dev) for k, v in batch["state"].items()},
        "actions": {k: v.to(dev) for k, v in batch["actions"].items()},
        "value": batch["value"].to(dev),
        "weight": batch["weight"].to(dev),
    }


if __name__ == "__main__":
    _sanity()
