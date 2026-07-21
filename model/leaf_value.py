"""Depth-cutoff leaf evaluation for the search (docs/solver_design.md
2.4). One swappable function on the same [-1, 1] scale as terminal
values — the trained value net (predicting win probability p, returning
2p - 1) replaces this without the solver changing.
"""

import math

from schema.full_info_state import FullInfoState

# Modest, bounded field-control weights (2026-07-20). These are a
# DELIBERATE, temporary reversal of the "don't hand-patch leaf blind
# spots, the value net will learn them" stance in the module history:
# with depth_limit=2 and a small live iteration budget, a leaf position
# where Tailwind/Trick Room/screens are up scores IDENTICALLY to one
# where they aren't (pure HP differential), so the search never spends a
# turn setting them up even when doing so wins - a concrete, reported
# failure (a game-winning Tailwind+Last Respects line the solver refused
# to take). A stopgap until the value net exists, kept small ON PURPOSE:
# one full mon is worth 0.25 here, and the entire field term is bounded
# well under that (max ~0.09 swing), so a real KO always outranks any
# amount of setup - setup only ever breaks ties among HP-equal leaves,
# which is exactly where the blind spot lived.
_TAILWIND_VALUE = 0.03      # speed control for its ~4-turn window
_SCREEN_VALUE = 0.015       # per active screen (reflect/light screen/aurora veil)
_TRICK_ROOM_VALUE = 0.03    # magnitude of the turn-order inversion swing
_TRICK_ROOM_SPEED_SCALE = 50.0  # base-speed gap that saturates the tanh


def _active_mean_speed(team) -> float:
    """Mean base Speed of a side's on-field mons (falls back to all
    non-fainted if none are currently active, e.g. mid-resolution). Base
    stat only - a deliberately crude proxy; boosts/paralysis/tailwind
    itself aren't folded in (the value net's job), just enough signal to
    sign the Trick Room term correctly for a clearly-slow vs clearly-fast
    team.
    """
    speeds = [m.stats["spe"] for m in team if m.position is not None and not m.fainted and "spe" in m.stats]
    if not speeds:
        speeds = [m.stats["spe"] for m in team if not m.fainted and "spe" in m.stats]
    return sum(speeds) / len(speeds) if speeds else 0.0


def _screen_count(side) -> int:
    return (
        (1 if side.reflect_turns > 0 else 0)
        + (1 if side.light_screen_turns > 0 else 0)
        + (1 if side.aurora_veil_turns > 0 else 0)
    )


def _field_value(state: FullInfoState) -> float:
    """Small signed my-POV adjustment for active field/side control that
    the HP differential can't see. Exactly 0.0 for a clean field (all
    the existing HP-only leaf tests stay valid). FullInfoState carries
    REMAINING durations in the *_turns fields (engine semantics, see
    engine/bridge.py), so `> 0` means "still active."
    """
    f = state.field
    v = 0.0

    # Tailwind: unambiguous speed control for whichever side holds it.
    if f.my_side.tailwind_turns > 0:
        v += _TAILWIND_VALUE
    if f.opp_side.tailwind_turns > 0:
        v -= _TAILWIND_VALUE

    # Screens: defensive value for the side sitting behind them.
    v += _SCREEN_VALUE * _screen_count(f.my_side)
    v -= _SCREEN_VALUE * _screen_count(f.opp_side)

    # Trick Room: not inherently good or bad - it inverts turn order, so
    # it helps whichever side is SLOWER. Signed by the active base-speed
    # gap (positive when my side is slower, i.e. benefits from TR).
    if f.trick_room_turns > 0:
        speed_gap = _active_mean_speed(state.opp_team) - _active_mean_speed(state.my_team)
        v += _TRICK_ROOM_VALUE * math.tanh(speed_gap / _TRICK_ROOM_SPEED_SCALE)

    return v


# A living mon is worth _ALIVE_VALUE just for being on the field, PLUS up
# to _HP_VALUE scaled by its remaining HP fraction; a fainted mon is worth
# 0 (2026-07-20). The 3:1 split (0.75 vs 0.25, summing to 1.0 so a full-HP
# living mon still scores 1.0 - the old pure-HP scale) is the fix for the
# leaf's biggest flaw: pure HP% treated a KO'd mon and a 1% mon as nearly
# equal, so it would rank "I'm at 90%, they're at two 10%s" ABOVE "I'm up
# two mons, both sides' survivors at 1%" - exactly backwards, since being
# UP A MON predicts winning far more than HP% does (a 1% mon still Fake
# Outs, redirects, sets up, revenge-KOs, sacs productively; a dead one
# does nothing). Concretely this makes finishing a 10%-HP mon (KO, ~0.775
# swing in their value) ~30x more valuable than chipping a full mon by the
# same 10% (~0.025) - i.e. the leaf now rewards securing KOs and focus-
# firing, which is what actually wins games. HP still matters as the
# gradient toward the next KO; it's just no longer the whole story.
_ALIVE_VALUE = 0.75
_HP_VALUE = 0.25


def _side_value(team) -> float:
    return sum(
        _ALIVE_VALUE + _HP_VALUE * (m.hp / m.max_hp)
        for m in team if not m.fainted and m.max_hp
    )


def hp_leaf_value(state: FullInfoState) -> float:
    """KO-aware material differential over the brought 4 (see _side_value /
    the _ALIVE_VALUE:_HP_VALUE split), plus a small bounded field-control
    term for Tailwind/Trick Room/screens (_field_value). Kept on the same
    [-1, 1] scale as terminal values. Still deliberately crude on the rest
    (all mons equally valued, status invisible) - the value net's job, not
    hand-patched here.
    """
    return (_side_value(state.my_team) - _side_value(state.opp_team)) / 4.0 + _field_value(state)
