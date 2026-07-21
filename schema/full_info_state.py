"""FullInfoState: one fully-concrete search-node state — what a single
belief-layer sample_determinization() call produces, what the model's
search consumes, and what the engine bridge's step() advances. It lives
in schema/ because all three packages share it as a contract (and none
of them may import from each other).

NOT the live imperfect-info picture (that's BattleState): the opponent's
side here is one committed hypothesis (exact moves/item/ability/stats
for all 4 brought mons, including the never-yet-seen bench picks), so
both sides use the same OwnPokemon type and the real engine can simulate
the position forward.

POV/position convention: each team's Position labels are from that
side's OWN perspective (LEFT = that side's slot a). Target.OPP_LEFT in
one side's action always refers to the other side's LEFT slot — matching
how the harness already maps targets to Showdown's position integers,
and keeping self-play symmetric with no flipping anywhere.
"""

from typing import Optional

from pydantic import BaseModel

from schema.battle_state import FieldState, OwnPokemon, Position


class FullInfoState(BaseModel):
    turn: int
    field: FieldState  # my_side/opp_side follow my_team/opp_team respectively
    my_team: list[OwnPokemon]   # the brought 4; active mons carry a position
    opp_team: list[OwnPokemon]  # same shape — determinized, nothing hidden


class TeamPreviewRootState(BaseModel):
    """The root state for a team-preview decision: the FULL 6-mon pool per
    side, nobody active yet (all position=None). Deliberately a distinct
    type from FullInfoState rather than "a FullInfoState with 6 mons" —
    FullInfoState's "always 4" is a load-bearing invariant elsewhere
    (hp_leaf_value hardcodes /4.0), so overloading it would silently
    violate that contract for any code not specifically updated to know
    about the 6-mon case.

    Shares FullInfoState's exact field names/shape on purpose: model/
    solver_game.py's _public_key/_full_key/_mon_public/_field_key only
    ever touch these four attributes structurally (never isinstance-check
    or assume team length), so they work on this type unchanged.

    Index i in my_team/opp_team must equal the roster index declared at
    team preview — what TeamPreviewAction.bring/lead_order indices mean.
    Unlike FullInfoState's mid-battle construction, do NOT reorder to an
    active-first convention here; nothing is active yet.
    """
    turn: int = 0
    field: FieldState
    my_team: list[OwnPokemon]   # always 6, all position=None
    opp_team: list[OwnPokemon]  # always 6, all position=None


def active_mon(team: list[OwnPokemon], position: Position) -> Optional[OwnPokemon]:
    return next((m for m in team if m.position == position and not m.fainted), None)


def bench_mons(team: list[OwnPokemon]) -> list[OwnPokemon]:
    """Living benched mons in stable team order — SwitchAction.bench_slot
    indexes into exactly this list.
    """
    return [m for m in team if m.position is None and not m.fainted]
