"""Unit tests for harness/opponent_log.py against synthetic raw protocol
events shaped like poke-env's real battle._replay_data entries (see
poke_env.battle.abstract_battle.AbstractBattle.parse_message for the
real shapes this mimics) — no live server needed.

Run from the project root: python -m harness.test_opponent_log
"""

from types import SimpleNamespace

from harness.opponent_log import OpponentActionLogger

failures = []


def check(name: str, ok: bool, detail: str = ""):
    print(f"  {name} [{'ok' if ok else 'FAIL'}]{' ' + str(detail) if detail and not ok else ''}")
    if not ok:
        failures.append(name)


def fake_battle(player_role: str, replay_data: list[list[str]]):
    return SimpleNamespace(player_role=player_role, _replay_data=replay_data)


print("opponent moves and switches are logged, own-side events are not")
battle = fake_battle("p1", [
    ["", "move", "p1a: Garchomp", "Earthquake", ""],
    ["", "move", "p2a: Swampert", "Wave Crash", "p1a: Garchomp"],
    ["", "switch", "p2b: Archaludon", "Archaludon, L50", "100/100"],
    ["", "-damage", "p1a: Garchomp", "40/185"],
])
logger = OpponentActionLogger()
lines = logger.log_new_events(battle)
check("exactly 2 opponent lines (move + switch), own move excluded", len(lines) == 2, lines)
check("move line names the actor, move, and target with our own left/right labels",
      "swampert (opp_left): uses wave crash -> garchomp (left)" in lines[0].lower(), lines)
check("switch line names the incoming species with the opp_ slot label",
      "(opp_right): switches to archaludon" in lines[1].lower(), lines)

print("\ncursor advances: a second call with no new events returns nothing")
check("no duplicate lines on repeat call", logger.log_new_events(battle) == [])

print("\na later call only returns events added since the last call")
battle._replay_data.append(["", "move", "p2b: Archaludon", "Electro Shot", "p1b: Incineroar"])
more = logger.log_new_events(battle)
check("only the one new event is returned", len(more) == 1, more)
check("correctly parsed", "archaludon (opp_right): uses electro shot -> incineroar (right)" in more[0].lower(), more)

print("\nno-target moves (e.g. self-targeting or spread) format as (no target)")
battle2 = fake_battle("p2", [["", "move", "p1a: Sylveon", "Tailwind", ""]])
lines2 = OpponentActionLogger().log_new_events(battle2)
check("shows (no target) rather than crashing on a missing target field",
      "(no target)" in lines2[0], lines2)

print(f"\n{'PASS' if not failures else 'FAIL: ' + ', '.join(failures)}")
