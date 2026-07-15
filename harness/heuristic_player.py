"""poke-env Player wired to the heuristic policy, accumulating a
readable one-side-POV battle log (model/battle_log.py) as it plays.
Showdown-specific glue - the actual decisions live in model/heuristic.py.
"""

from poke_env.player import Player

from harness.actions import team_preview_action_to_order, turn_actions_to_order
from harness.translator import battle_to_state
from model.battle_log import format_result, format_team_preview, format_turn
from model.heuristic import choose_team_preview, choose_turn_actions
from schema.battle_state import NoAction


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


class HeuristicPlayer(Player):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.log_lines: list[str] = []
        self._replay_cursor = 0

    def _log_opponent_moves(self, battle):
        # battle._replay_data is the raw protocol event log poke-env keeps
        # internally (for replay reconstruction); scanning the slice added
        # since the last call is how we see what the opponent actually did,
        # since our own schema only tracks revealed_* facts, not a
        # per-turn action history. Harness/Showdown-specific (raw protocol
        # parsing), not something model/battle_log.py should need to know.
        my_role = battle.player_role
        new_events = battle._replay_data[self._replay_cursor:]
        self._replay_cursor = len(battle._replay_data)
        for event in new_events:
            if len(event) >= 3 and event[1] == "move" and not event[2].startswith(f"{my_role}"):
                actor_species, actor_label = _parse_identifier(event[2], my_role)
                if len(event) >= 5 and event[4]:
                    target_species, target_label = _parse_identifier(event[4], my_role)
                    target_str = f"{target_species} ({target_label})"
                else:
                    target_str = "(no target)"
                self.log_lines.append(
                    f"  [opponent] {actor_species} ({actor_label}): uses {event[3].lower()} -> {target_str}"
                )

    def choose_move(self, battle):
        self._log_opponent_moves(battle)
        state = battle_to_state(battle)
        actions = choose_turn_actions(state)

        # When a mon faints mid-turn, Showdown issues a switch-only request
        # for just that slot - the other (still-active) slot isn't being
        # asked to act this request and must Pass, not submit a fresh move.
        # This is Showdown request-protocol mechanics, not a model decision,
        # so it's handled here rather than in model/heuristic.py.
        force_switch = battle.force_switch
        if any(force_switch) and not all(force_switch):
            if not force_switch[0]:
                actions.slot_left = NoAction()
            if not force_switch[1]:
                actions.slot_right = NoAction()

        self.log_lines.append(format_turn(state, actions))
        return turn_actions_to_order(battle, actions)

    def teampreview(self, battle):
        state = battle_to_state(battle)
        action = choose_team_preview(state)
        self.log_lines.append(format_team_preview(state, action))
        return team_preview_action_to_order(battle, action)

    def finalize_log(self, won: bool) -> str:
        self.log_lines.append(format_result(won))
        return "\n\n".join(self.log_lines)
