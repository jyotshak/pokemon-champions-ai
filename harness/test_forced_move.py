"""Fast, no-server unit test for harness/actions.py::_forced_move and the
forced-continuation override in _single_order.

Two distinct bugs this pins:

1. (original) On the recharge turn Showdown offers ONE synthetic move
   ("recharge") not in the mon's real moveset. Passing is illegal -
   "[Invalid choice] Can't pass: Your Sylveon must make a move (or switch)"
   - so the order boundary must submit the synthetic move itself.

2. (found after #1 shipped) The FIRST fix detected this by diffing
   battle.available_moves against the mon's real moveset - which breaks
   specifically when the recharge/charge request is COMBINED with an
   ally's post-faint replacement: Showdown does not re-list a still-alive,
   non-participating slot's moves during a switch-only request, so
   available_moves reads EMPTY there even though the mon is genuinely
   locked. The diff then finds nothing and a plain pass goes out, silently
   deferring the real requirement to the NEXT turn (where it resurfaces
   identically - found live on MB552's Sylveon, whose ally fainted the
   same turn her Hyper Beam locked her into recharging).

The fix reads poke-env's own direct, protocol-driven properties
(actor.must_recharge / actor.preparing_move) instead, which stay correct
regardless of what available_moves shows for this request.

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


def actor_with(move_ids, must_recharge=False, preparing_move=None):
    return SimpleNamespace(moves={m: move(m) for m in move_ids}, fainted=False,
                           must_recharge=must_recharge, preparing_move=preparing_move)


def battle_with(active_pokemon, available_for_slot1, gen=9):
    """Slot 0 (a normal mon) + slot 1 (the tested mon)."""
    return SimpleNamespace(
        gen=gen, active_pokemon=active_pokemon,
        available_moves=[[move("rockslide"), move("tailwind")], available_for_slot1],
    )


NORMAL = actor_with(["rockslide", "dualwingbeat", "wideguard", "tailwind"])


print("recharge, NORMAL request (available_moves correctly shows the synthetic entry)")
sylveon_recharging = actor_with(["hypervoice", "hyperbeam", "quickattack", "detect"], must_recharge=True)
b_normal_recharge = battle_with([NORMAL, sylveon_recharging], [move("recharge")])
f = _forced_move(b_normal_recharge, sylveon_recharging)
check("recharge detected via the direct property", f is not None and f.id == "recharge", f)
check("the OTHER slot has no forced move", _forced_move(b_normal_recharge, NORMAL) is None)

print("\nrecharge, COMBINED request (available_moves EMPTY - the actual bug) "
      "- must still be detected via the direct property, not the (empty) move-list diff")
b_combined = battle_with([NORMAL, sylveon_recharging], [])   # <- the exact gap: nothing re-listed
f_combined = _forced_move(b_combined, sylveon_recharging)
check("recharge STILL detected despite empty available_moves",
      f_combined is not None and f_combined.id == "recharge", f_combined)

print("\ntwo-turn-move mid-charge (Solar Beam/Electro Shot without Rain), normal AND combined request")
charging_move = move("solarbeam")
charizard_charging = actor_with(["solarbeam", "flamethrower", "protect", "airslash"],
                                preparing_move=charging_move)
b_charge_normal = battle_with([NORMAL, charizard_charging], [move("solarbeam")])
fc = _forced_move(b_charge_normal, charizard_charging)
check("charging move returned directly (normal request)", fc is charging_move, fc)
b_charge_combined = battle_with([NORMAL, charizard_charging], [])
fc2 = _forced_move(b_charge_combined, charizard_charging)
check("charging move returned directly (combined request, empty available_moves)",
      fc2 is charging_move, fc2)

print("\nnormal request, no lock -> no forced move")
b_normal = battle_with([NORMAL, actor_with(["hypervoice", "detect"])],
                       [move("hypervoice"), move("detect")])
check("no forced move", _forced_move(b_normal, b_normal.active_pokemon[1]) is None)

print("\nStruggle (PP-based, no dedicated property - still via the available_moves fallback)")
struggler = actor_with(["hypervoice", "hyperbeam", "quickattack", "detect"])
b_struggle = battle_with([NORMAL, struggler], [move("struggle")])
fs = _forced_move(b_struggle, struggler)
check("struggle detected via the fallback diff", fs is not None and fs.id == "struggle", fs)

print("\n_single_order: a forced continuation must NOT pass, it submits the forced move")
order = _single_order(b_normal_recharge, NoAction(), sylveon_recharging, Position.RIGHT)
check("NoAction on a recharge turn no longer becomes a Pass",
      not isinstance(order, PassBattleOrder), type(order).__name__)
check("the submitted order IS the recharge move",
      getattr(order, "order", None) is not None and order.order.id == "recharge",
      getattr(order, "order", None))
order_combined = _single_order(b_combined, NoAction(), sylveon_recharging, Position.RIGHT)
check("same override fires for the COMBINED (empty-available_moves) request",
      not isinstance(order_combined, PassBattleOrder))

# The policy can also hand us a stale MoveAction for that slot; it is overridden.
order2 = _single_order(b_normal_recharge, MoveAction(move_slot=1, target=Target.OPP_LEFT),
                       sylveon_recharging, Position.RIGHT)
check("a stale MoveAction is overridden by the forced move",
      order2.order.id == "recharge", order2.order.id)

print("\nnormal turns are untouched by the override")
free_actor = b_normal.active_pokemon[1]
normal_order = _single_order(b_normal, MoveAction(move_slot=1, target=Target.OPP_LEFT), free_actor, Position.RIGHT)
check("normal MoveAction still maps by move_slot (hypervoice)",
      normal_order.order.id == "hypervoice", normal_order.order.id)
check("NoAction on a normal slot still passes",
      isinstance(_single_order(b_normal, NoAction(), free_actor, Position.RIGHT), PassBattleOrder))

print("\nStruggle: switching out stays legal (a switch is NOT overridden)")
b_struggle.team = {}
sw = SwitchAction(bench_slot=0)
try:
    res = _single_order(b_struggle, sw, struggler, Position.RIGHT)
    diverted = getattr(res, "order", None) is not None and getattr(res.order, "id", None) == "struggle"
except Exception:
    diverted = False   # bench lookup failed on the fake, which is fine here
check("SwitchAction is not diverted into Struggle", not diverted)

print(f"\n{'PASS' if not failures else 'FAIL: ' + ', '.join(failures)}")
