"""Reconstructs readable per-turn opponent-action log lines from poke-env's
raw internal protocol event history (battle._replay_data) — the only place
a per-turn "what did the opponent actually do" is available; our own
schema/translator only tracks revealed_* facts (accumulated so far), not a
per-turn action history. Harness/Showdown-specific (raw protocol parsing),
not something model/battle_log.py should need to know. Shared by
HeuristicPlayer and SolverPlayer so both sides' battle logs show the
opponent's real moves and switches, not just our own chosen actions.
"""


def _parse_identifier(raw: str, my_role: str) -> tuple[str, str]:
    """'p2a: Skarmory' -> ('skarmory', 'opp_left'), always labeled from
    this player's own POV (never flipped to the opponent's), matching the
    same left/right/opp_left/opp_right convention used for my own actions.
    """
    prefix, species = raw.split(": ", 1)
    role, slot = prefix[:-1], prefix[-1]
    is_left = slot == "a"
    if role == my_role:
        label = "left" if is_left else "right"
    else:
        label = "opp_left" if is_left else "opp_right"
    return species.lower().replace("-", ""), label


class OpponentActionLogger:
    """Stateful: call log_new_events(battle) once per decision (or at
    battle end) to get lines for every opponent move/switch since the
    last call — battle._replay_data accumulates for the whole battle, so
    a cursor avoids re-emitting already-logged events.
    """

    def __init__(self):
        self._cursor = 0

    def log_new_events(self, battle) -> list[str]:
        my_role = battle.player_role
        new_events = battle._replay_data[self._cursor:]
        self._cursor = len(battle._replay_data)
        lines = []
        for event in new_events:
            if len(event) < 3 or event[2].startswith(my_role):
                continue
            if event[1] == "move":
                actor_species, actor_label = _parse_identifier(event[2], my_role)
                if len(event) >= 5 and event[4]:
                    target_species, target_label = _parse_identifier(event[4], my_role)
                    target_str = f"{target_species} ({target_label})"
                else:
                    target_str = "(no target)"
                lines.append(f"  [opponent] {actor_species} ({actor_label}): uses {event[3].lower()} -> {target_str}")
            elif event[1] in ("switch", "drag"):
                incoming_species, label = _parse_identifier(event[2], my_role)
                lines.append(f"  [opponent] ({label}): switches to {incoming_species}")
        return lines
