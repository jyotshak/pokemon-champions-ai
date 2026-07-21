"""Fast, no-server unit test for harness/actions.py::_forced_move and the
forced-continuation override in _single_order.

The bug this pins (found live on MB552's Sylveon + Hyper Beam): on the
recharge turn Showdown offers ONE synthetic move ("recharge") that is not in
the mon's real moveset. translator.py deliberately keeps OwnPokemon.moves as
the real engine-buildable set, so every real move reads "disabled" and the
policy emits NoAction - but passing is illegal, so the server answered
"[Invalid choice] Can't pass: Your Sylveon must make a move (or switch)" and
the battle stalled in a retry loop. The order boundary must therefore submit
the synthetic move itself.

Run from the project root: python -m harness.test_forced_move
"""

from types import SimpleNamespace

from poke_env.player.battle_order import PassBattleOrder

from harness.actions import _forced_move, _single_order
from schema.battle_state import MoveAction, NoAction, Position, SwitchAction, Target

failures = []


def check(name, ok, detail=""):
    print(f"  {name} [{'ok' if ok else 'FAIL'}]{'' if ok else ' ' + str(detail)}")
    if not ok:
        failures.append(name)


def move(mid):
    return SimpleNamespace(id=mid, category=SimpleNamespace(name="SPECIAL"))


def actor_with(move_ids):
    return SimpleNamespace(moves={m: move(m) for m in move_ids}, fainted=False)


SYLVEON = actor_with(["hypervoice", "hyperbeam", "quickattack", "detect"])
AERO = actor_with(["rockslide", "dualwingbeat", "wideguard", "tailwind"])


def battle_with(available_for_sylveon):
    """Aerodactyl in slot 0 (normal), Sylveon in slot 1 (the tested slot)."""
    return SimpleNamespace(
        active_pokemon=[AERO, SYLVEON],
        available_moves=[[move("rockslide"), move("tailwind")], available_for_sylveon],
    )


print("_forced_move detects the synthetic entry only when it is genuinely forced")
b_recharge = battle_with([move("recharge")])
f = _forced_move(b_recharge, SYLVEON)
check("recharge detected as the forced move", f is not None and f.id == "recharge", f)
check("the normal slot (Aerodactyl) has no forced move", _forced_move(b_recharge, AERO) is None)

b_normal = battle_with([move("hypervoice"), move("detect")])
check("normal request -> no forced move", _forced_move(b_normal, SYLVEON) is None)

b_struggle = battle_with([move("struggle")])
fs = _forced_move(b_struggle, SYLVEON)
check("struggle detected as forced", fs is not None and fs.id == "struggle", fs)

print("\n_single_order: a forced continuation must NOT pass, it submits the synthetic move")
order = _single_order(b_recharge, NoAction(), SYLVEON, Position.RIGHT)
check("NoAction on a recharge turn no longer becomes a Pass",
      not isinstance(order, PassBattleOrder), type(order).__name__)
check("the submitted order IS the recharge move",
      getattr(order, "order", None) is not None and order.order.id == "recharge",
      getattr(order, "order", None))

# The policy can also hand us a stale MoveAction for that slot; it is overridden.
order2 = _single_order(b_recharge, MoveAction(move_slot=1, target=Target.OPP_LEFT), SYLVEON, Position.RIGHT)
check("a stale MoveAction is overridden by the forced move",
      order2.order.id == "recharge", order2.order.id)

print("\nnormal turns are untouched by the override")
normal_order = _single_order(b_normal, MoveAction(move_slot=1, target=Target.OPP_LEFT), SYLVEON, Position.RIGHT)
check("normal MoveAction still maps by move_slot (hypervoice)",
      normal_order.order.id == "hypervoice", normal_order.order.id)
check("NoAction on a normal slot still passes",
      isinstance(_single_order(b_normal, NoAction(), SYLVEON, Position.RIGHT), PassBattleOrder))

print("\nStruggle: switching out stays legal (a switch is NOT overridden)")
b_struggle.team = {}
sw = SwitchAction(bench_slot=0)
# _single_order must not divert a SwitchAction into the forced move; it should
# take the switch path (which will look up the bench - we only assert it did
# not return the struggle order).
try:
    res = _single_order(b_struggle, sw, SYLVEON, Position.RIGHT)
    diverted = getattr(res, "order", None) is not None and getattr(res.order, "id", None) == "struggle"
except Exception:
    diverted = False   # bench lookup failed on the fake, which is fine here
check("SwitchAction is not diverted into Struggle", not diverted)

print(f"\n{'PASS' if not failures else 'FAIL: ' + ', '.join(failures)}")
