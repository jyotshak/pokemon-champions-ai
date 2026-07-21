"""Python client for the Node engine bridge (engine/bridge.js): the real
Showdown Sim.Battle behind the solver's step() interface, via a JSON-lines
child process. Engine-specific glue — model/ never imports this; it gets
step injected (docs/solver_design.md 2.7).

Usage:
    with EngineBridge(FORMAT_ID) as bridge:
        handle, state = bridge.init_battle(full_info_state)
        result = bridge.step(handle, state, my_turn_actions, opp_turn_actions)
        # result.terminal is my-POV +1/-1/0 when the game ended, else None
        # and result.handle/result.state continue the tree

Semantics notes:
- Snapshots are immutable: stepping a handle never mutates it, and each
  step reseeds the engine RNG, so repeated steps from one parent sample
  fresh chance outcomes (what MCCFR's outcome sampling needs).
- Returned FullInfoStates carry REMAINING durations in the field/side
  *_turns fields (engine semantics), unlike BattleState's elapsed-turns
  convention — they only feed my_key/leaf_value/debugging, never re-init.
- Choice strings are built from the PARENT state's team order, which
  matches the engine's side.pokemon order by construction (init orders
  teams [active_left, active_right, bench...] and exports preserve
  engine order thereafter).
- free() releases snapshots Node-side; call it per real decision with the
  handles that solve created, or leak until the process is dropped.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import NamedTuple, Optional

from schema.battle_state import (
    Action, MoveAction, NoAction, OwnPokemon, Position, SwitchAction, Target, TeamPreviewAction, TurnActions,
)
from schema.full_info_state import FullInfoState, TeamPreviewRootState

_BRIDGE_JS = Path(__file__).resolve().parent / "bridge.js"


class StepResult(NamedTuple):
    handle: Optional[int]      # None when terminal
    state: FullInfoState
    terminal: Optional[float]  # my-POV +1 / -1 / 0, None while ongoing
    errors: list[str]          # engine choice rejections (should stay empty)


def _target_int(target: Target, actor_position: Position) -> int:
    # Same integers as harness/actions.py maps to poke-env: foes 1/2,
    # allies -1/-2, no explicit target 0. Duplicated (6 lines) rather than
    # importing harness/, which is poke-env-specific.
    if target == Target.OPP_LEFT:
        return 1
    if target == Target.OPP_RIGHT:
        return 2
    if target == Target.ALLY:
        return -2 if actor_position == Position.LEFT else -1
    return 0


def _slot_choice(action: Action, team: list[OwnPokemon], actor_position: Position) -> str:
    if isinstance(action, NoAction):
        return "pass"
    if isinstance(action, SwitchAction):
        living_benched = [i for i, m in enumerate(team) if m.position is None and not m.fainted]
        return f"switch {living_benched[action.bench_slot] + 1}"
    if isinstance(action, MoveAction):
        choice = f"move {action.move_slot}"
        target = _target_int(action.target, actor_position)
        if target:
            choice += f" {target}"
        if action.mega:
            choice += " mega"
        return choice
    raise ValueError(f"unknown action type: {action!r}")


def _turn_choice(actions: TurnActions, team: list[OwnPokemon]) -> str:
    return (
        _slot_choice(actions.slot_left, team, Position.LEFT)
        + ", "
        + _slot_choice(actions.slot_right, team, Position.RIGHT)
    )


def _ordered_team(team: list[OwnPokemon]) -> list[OwnPokemon]:
    """[active_left, active_right, bench...] — the order init sends becomes
    the engine's team-preview lead order, so slot 0/1 become active[0]/[1]
    (LEFT/RIGHT). Real Showdown always needs 2 real leads to start a
    battle, so a permanently-empty slot (that side's mon fainted with no
    living replacement - it drops its position, becoming indistinguishable
    from a never-sent bench mon) still needs SOME filler in slot 0/1 to
    seed team preview; init_battle immediately re-faints it via
    applyMonState right after, so which filler is used doesn't matter.

    Without this padding, a side with an empty LEFT and a living RIGHT
    mon would have nothing to put first, so the RIGHT mon would slide into
    slot 0 and get labeled LEFT instead — a silent position flip (caught
    via a real match crash, not by construction).
    """
    left = next((m for m in team if m.position == Position.LEFT), None)
    right = next((m for m in team if m.position == Position.RIGHT), None)
    rest = [m for m in team if m.position is None]
    if left is None:
        left, rest = rest[0], rest[1:]
    if right is None:
        right, rest = rest[0], rest[1:]
    return [left, right] + rest


def _team_preview_choice(action: TeamPreviewAction) -> str:
    # Pure index-ordering math duplicated (not imported) from harness/
    # actions.py::team_preview_action_to_order — engine/ must not depend
    # on harness/, which is poke-env-specific and additionally does
    # protocol framing ("/team " prefix) and a _selected_in_teampreview
    # mutation that don't apply bridge-side. Same "team NNNN" syntax
    # opInit's auto-answer already uses (1-based, no leading slash).
    all_indices = list(range(6))
    bring_rest = [i for i in action.bring if i not in action.lead_order]
    remaining = [i for i in all_indices if i not in action.bring]
    order = action.lead_order + bring_rest + remaining
    return "team " + "".join(str(i + 1) for i in order)


class EngineBridge:
    def __init__(self, format_id: str, node: str = "node"):
        self.format_id = format_id
        self._request_id = 0
        self._proc = subprocess.Popen(
            [node, str(_BRIDGE_JS)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            text=True, encoding="utf-8", bufsize=1,
        )
        self._rpc({"op": "ping"})  # fail fast if the sim can't load

    def _rpc(self, payload: dict) -> dict:
        self._request_id += 1
        payload["id"] = self._request_id
        self._proc.stdin.write(json.dumps(payload) + "\n")
        self._proc.stdin.flush()
        while True:
            line = self._proc.stdout.readline()
            if not line:
                raise RuntimeError("engine bridge process died")
            try:
                resp = json.loads(line)
            except json.JSONDecodeError:
                continue  # stray non-protocol output
            if resp.get("id") != self._request_id:
                continue
            if not resp.get("ok"):
                raise RuntimeError(f"engine bridge error: {resp.get('error')}")
            return resp

    def init_battle(self, state: FullInfoState) -> tuple[int, FullInfoState]:
        payload_state = {
            "turn": state.turn,
            "field": state.field.model_dump(mode="json"),
            "my_team": [m.model_dump(mode="json") for m in _ordered_team(state.my_team)],
            "opp_team": [m.model_dump(mode="json") for m in _ordered_team(state.opp_team)],
        }
        resp = self._rpc({"op": "init", "format": self.format_id, "state": payload_state})
        return resp["handle"], FullInfoState(**resp["state"])

    def init_team_preview_battle(self, state: TeamPreviewRootState) -> int:
        # Canonical roster order (index i = roster index i) — deliberately
        # NOT run through _ordered_team(): that reordering assumes an
        # already-active-first convention (mid-battle reconstruction),
        # which doesn't apply pre-send-out (nobody's active, all 6 are
        # still just a roster). TeamPreviewAction.bring/lead_order indices
        # are defined against this same canonical order.
        payload_state = {
            "my_team": [m.model_dump(mode="json") for m in state.my_team],
            "opp_team": [m.model_dump(mode="json") for m in state.opp_team],
        }
        resp = self._rpc({"op": "init_team_preview", "format": self.format_id, "state": payload_state})
        return resp["handle"]

    def step_team_preview(self, handle: int, my: TeamPreviewAction, opp: TeamPreviewAction) -> StepResult:
        # Same underlying "step" RPC as step() below, unmodified server-side
        # — Showdown's side.choose() already dispatches "team NNNN" choices
        # generically whenever the restored battle is paused at the
        # teampreview request (see bridge.js's module docstring).
        resp = self._rpc({
            "op": "step",
            "handle": handle,
            "my": _team_preview_choice(my),
            "opp": _team_preview_choice(opp),
        })
        return StepResult(
            handle=resp.get("handle"),
            state=FullInfoState(**resp["state"]),
            terminal=resp.get("terminal"),
            errors=resp.get("errors", []),
        )

    def step(self, handle: int, parent: FullInfoState, my: TurnActions, opp: TurnActions) -> StepResult:
        resp = self._rpc({
            "op": "step",
            "handle": handle,
            "my": _turn_choice(my, parent.my_team),
            "opp": _turn_choice(opp, parent.opp_team),
        })
        return StepResult(
            handle=resp.get("handle"),
            state=FullInfoState(**resp["state"]),
            terminal=resp.get("terminal"),
            errors=resp.get("errors", []),
        )

    def free(self, handles: list[int]) -> None:
        if handles:
            self._rpc({"op": "free", "handles": handles})

    def close(self) -> None:
        if self._proc.poll() is None:
            self._proc.terminate()

    def __enter__(self) -> "EngineBridge":
        return self

    def __exit__(self, *exc) -> None:
        self.close()
