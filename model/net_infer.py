"""Inference wrapper around the trained policy/value net ([[imitation-net-v1]])
for live play and depth-1 search ([[replay-net-direction]]). Framework-facing
but input-source-NEUTRAL: it consumes the same "reconstruct-state" dicts the
encoder does (model/encoding.py) and generic action LABELS, never poke-env or
schema types - the harness owns those translations (harness/net_translate.py).

Provides:
  value_batch(states)        -> win-prob (me-POV) per state, one net call.
  policy(state)              -> per me-active-slot head logits (numpy).
  score_labels(pol, i, labs) -> selection probabilities over a candidate set
                                of action labels for slot i (softmax of
                                type + move/switch logits) - used to pick the
                                top-k branches worth rolling out.
Batched on GPU; used many times per turn, so the batched value path matters.
"""

import numpy as np
import torch

from model.encoding import encode_for_inference, MOVE_VOCAB  # noqa: F401 (MOVE_VOCAB re-exported)
from model.policy_net import PolicyValueNet, ME_ACTIVE_SLOTS


def load_net(checkpoint: str, device: str | None = None) -> tuple:
    device = device or ("cuda" if torch.cuda.is_available() else "cpu")
    ckpt = torch.load(checkpoint, map_location=device, weights_only=False)
    a = ckpt.get("args", {})
    net = PolicyValueNet(d_model=a.get("d_model", 128), layers=a.get("layers", 4),
                         species_dim=a.get("species_dim", 32)).to(device)
    net.load_state_dict(ckpt["model"])
    net.eval()
    return net, device


def _collate(states: list[dict], device: str) -> dict:
    """List of reconstruct-state dicts -> one batched tensor dict for the net."""
    encs = [encode_for_inference(s) for s in states]
    out = {}
    for k in encs[0]:
        arr = np.stack([e[k] for e in encs])
        t = torch.from_numpy(arr)
        out[k] = (t.long() if arr.dtype.kind in "iu" else t.float()).to(device)
    return out


class NetEvaluator:
    def __init__(self, checkpoint: str, device: str | None = None):
        self.net, self.device = load_net(checkpoint, device)

    @torch.no_grad()
    def value_batch(self, states: list[dict]) -> np.ndarray:
        """Win probability (me-POV) for each state, in [0,1]."""
        if not states:
            return np.zeros(0, dtype=np.float32)
        out = self.net(_collate(states, self.device))
        return torch.sigmoid(out["value"]).cpu().numpy()

    def value(self, state: dict) -> float:
        return float(self.value_batch([state])[0])

    @torch.no_grad()
    def policy(self, state: dict) -> dict:
        """Per me-active-slot head logits (numpy), slot order [a, b]."""
        out = self.net(_collate([state], self.device))
        return {
            "type": out["type"][0].cpu().numpy(),      # (2, 3)
            "move": out["move"][0].cpu().numpy(),      # (2, |moves|)
            "target": out["target"][0].cpu().numpy(),  # (2, 5)
            "switch": out["switch"][0].cpu().numpy(),  # (2, |species|)
            "mega": out["mega"][0].cpu().numpy(),      # (2,)
        }

    @staticmethod
    def score_labels(pol: dict, slot: int, labels: list[dict]) -> np.ndarray:
        """Selection probabilities over a candidate set of action labels for
        one active slot. Each label is model/encoding.encode_action output
        {type, move, target, mega, switch}. Score = the SUM of every head's
        log-prob the label implies (type, move-or-switch, AND target/mega for
        a move), softmaxed over the candidate set so it's a usable branch
        prior.

        Target and mega are now INCLUDED (2026-07-21 fix,
        [[net-external-review-2026-07-21]] - a prior version left them out
        of ranking with the reasoning "the target head is weak; mega rarely
        flips choice", which meant those two trained heads had near-zero
        actual influence on play regardless of how well they were trained.
        If a head genuinely is weak/uncalibrated, that shows up naturally as
        near-uniform log-probs across labels - contributing little to the
        ranking on its own, with no need to hand-suppress it - rather than
        unconditionally silencing a signal that retraining (encoder v3,
        [[net-external-review-2026-07-21]]) might have improved anyway.
        mega is a BINARY (sigmoid) head, not a softmax category, so its
        contribution is log P(mega=lab["mega"]) via log-sigmoid, not
        log-softmax."""
        type_lp = _log_softmax(pol["type"][slot])
        move_lp = _log_softmax(pol["move"][slot])
        target_lp = _log_softmax(pol["target"][slot])
        switch_lp = _log_softmax(pol["switch"][slot])
        mega_logit = float(pol["mega"][slot])
        scores = np.empty(len(labels), dtype=np.float32)
        for k, lab in enumerate(labels):
            s = type_lp[lab["type"]]
            if lab["type"] == 1:        # move
                s += move_lp[lab["move"]]
                s += target_lp[lab["target"]]
                s += _log_sigmoid(mega_logit if lab["mega"] else -mega_logit)
            elif lab["type"] == 2:      # switch
                s += switch_lp[lab["switch"]]
            scores[k] = s
        return _softmax(scores)


def _softmax(x: np.ndarray) -> np.ndarray:
    e = np.exp(x - x.max())
    return e / e.sum()


def _log_softmax(x: np.ndarray) -> np.ndarray:
    m = x.max()
    return x - m - np.log(np.exp(x - m).sum())


def _log_sigmoid(x: float) -> float:
    return -np.logaddexp(0.0, -x)
