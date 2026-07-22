"""Fast, no-checkpoint unit test for model/net_infer.py::NetEvaluator.
score_labels - constructs a fake policy-head output directly (no trained
net needed) to check the ranking math in isolation.

Regression for the 2026-07-21 fix ([[net-external-review-2026-07-21]]): a
prior version left target/mega OUT of the ranking entirely ("the target
head is weak; mega rarely flips choice"), so those two trained heads had
zero actual influence on which candidate action got selected, regardless of
what they'd learned. This pins that they now DO influence the ranking.

Run from the project root: python -m model.test_net_infer
"""

import numpy as np

from model.net_infer import NetEvaluator, _log_sigmoid

failures = []


def check(name, ok, detail=""):
    print(f"  {name} [{'ok' if ok else 'FAIL'}]{'' if ok else ' ' + str(detail)}")
    if not ok:
        failures.append(name)


def label(move=0, target=0, mega=0, switch=0, typ=1):
    return {"type": typ, "move": move, "target": target, "mega": mega, "switch": switch}


N_MOVE, N_TARGET, N_SPECIES = 20, 5, 30


def fake_pol(target_logit_boost=0.0, mega_logit=0.0):
    """A minimal policy dict, slot 0. Move id 3 is always the clear favorite
    (the type/move heads are held FIXED across labels being compared here,
    so any ranking difference must come from target/mega)."""
    type_ = np.array([[-5.0, 5.0, -5.0], [0.0, 0.0, 0.0]], dtype=np.float32)   # strongly prefers "move"
    move = np.zeros((2, N_MOVE), dtype=np.float32)
    move[0, 3] = 10.0   # move id 3 dominates
    target = np.zeros((2, N_TARGET), dtype=np.float32)
    target[0, 1] += target_logit_boost   # boost target index 1 specifically
    switch = np.zeros((2, N_SPECIES), dtype=np.float32)
    mega = np.array([mega_logit, 0.0], dtype=np.float32)
    return {"type": type_, "move": move, "target": target, "switch": switch, "mega": mega}


print("target head now influences ranking (previously ignored entirely)")
pol = fake_pol(target_logit_boost=5.0)
labels = [label(move=3, target=1, mega=0), label(move=3, target=2, mega=0)]
probs = NetEvaluator.score_labels(pol, 0, labels)
check("same move, but the net-preferred target (1) ranks higher than target (2)",
      probs[0] > probs[1], probs)

print("\nwith NO target preference, identical-except-target labels tie")
pol_flat = fake_pol(target_logit_boost=0.0)
probs_flat = NetEvaluator.score_labels(pol_flat, 0, labels)
check("no target signal -> both labels score equally", abs(probs_flat[0] - probs_flat[1]) < 1e-6, probs_flat)

print("\nmega head now influences ranking (previously ignored entirely)")
pol_mega = fake_pol(mega_logit=5.0)   # net strongly favors mega=True
mega_labels = [label(move=3, target=0, mega=1), label(move=3, target=0, mega=0)]
probs_mega = NetEvaluator.score_labels(pol_mega, 0, mega_labels)
check("net favors mega=True -> the mega=True label ranks higher",
      probs_mega[0] > probs_mega[1], probs_mega)

pol_antimega = fake_pol(mega_logit=-5.0)   # net strongly favors mega=False
probs_antimega = NetEvaluator.score_labels(pol_antimega, 0, mega_labels)
check("net favors mega=False -> the mega=False label now ranks higher",
      probs_antimega[1] > probs_antimega[0], probs_antimega)

print("\nresult is still a valid probability distribution")
check("probs sum to 1", abs(probs_mega.sum() - 1.0) < 1e-5, probs_mega.sum())
check("all probs in [0,1]", bool(np.all((probs_mega >= 0) & (probs_mega <= 1))))

print("\n_log_sigmoid sanity (used for the mega binary head)")
check("log_sigmoid(0) == log(0.5)", abs(_log_sigmoid(0.0) - np.log(0.5)) < 1e-6)
check("log_sigmoid(large positive) -> ~0 (P~1)", _log_sigmoid(20.0) > -1e-6)
check("log_sigmoid(large negative) -> very negative (P~0)", _log_sigmoid(-20.0) < -15)

print(f"\n{'PASS' if not failures else 'FAIL: ' + ', '.join(failures)}")
