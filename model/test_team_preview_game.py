"""Validates TeamPreviewGame's synergy_weights/mega_penalty plumbing in
isolation (a fake bridge stub, no real engine process needed - same
"stub before the real bridge" pattern already used in model/
test_solver_game.py): the parameter threads through 6 hops in real usage
(SolverPlayer -> solve_team_preview_decision_parallel ->
_solve_team_preview_worker -> TeamPreviewGame.__init__ ->
my_actions/opp_actions -> propose_pruned_team_preview_actions), the layer
most at risk of a silently-dropped parameter - this confirms
my_actions()/opp_actions() output actually changes end to end through
TeamPreviewGame itself, not just that propose_pruned_team_preview_actions
(already tested directly in model/test_team_preview_actions.py) accepts
the arguments.

Run from the project root: python -m model.test_team_preview_game
"""

import json
from pathlib import Path

from model.solver_game import TeamPreviewGame
from schema.battle_state import FieldState, MoveSlot, OwnPokemon
from schema.full_info_state import TeamPreviewRootState

_ROOT = Path(__file__).resolve().parent.parent
_SPECIES_DATA = json.loads((_ROOT / "reference" / "species_data.json").read_text(encoding="utf-8"))

failures = []


def check(name: str, ok: bool, detail: str = ""):
    print(f"  {name} [{'ok' if ok else 'FAIL'}]{' ' + str(detail) if detail and not ok else ''}")
    if not ok:
        failures.append(name)


def own(species: str) -> OwnPokemon:
    return OwnPokemon(
        species=species, hp=180, max_hp=180,
        stats={"atk": 120, "def": 120, "spa": 120, "spd": 120, "spe": 120},
        ability="intimidate",
        moves=[MoveSlot(move=m, pp=16, max_pp=16) for m in _SPECIES_DATA[species]["moves"][:4]],
    )


class _FakeBridge:
    """Stub: only init_team_preview_battle is needed for this check (we
    never call step()), matching model/test_solver_game.py's _FakeBridge.
    """
    def init_team_preview_battle(self, state):
        return id(state)

    def free(self, handles):
        pass


ROSTER = ["archaludon", "pelipper", "sinistcha", "swampert", "metagross", "grimmsnarl"]
ENEMY = ["garchomp", "kingambit", "sylveon", "charizard", "incineroar", "aerodactyl"]
root_state = TeamPreviewRootState(field=FieldState(), my_team=[own(s) for s in ROSTER], opp_team=[own(s) for s in ENEMY])

CORE_SYNERGY = {}
for a in ("archaludon", "pelipper", "sinistcha", "swampert"):
    for b in ("archaludon", "pelipper", "sinistcha", "swampert"):
        if a != b:
            CORE_SYNERGY.setdefault(a, {})[b] = 10.0
# Also give the ENEMY roster its own synergy signal (garchomp/kingambit/
# sylveon/aerodactyl - a subset of ENEMY below) so opp_actions() has
# something to react to too - my_team's core alone wouldn't move
# opp_actions() at all, since "opp"'s bring-subset scoring is over
# state.opp_team, not state.my_team.
for a in ("garchomp", "kingambit", "sylveon", "aerodactyl"):
    for b in ("garchomp", "kingambit", "sylveon", "aerodactyl"):
        if a != b:
            CORE_SYNERGY.setdefault(a, {})[b] = 10.0

print("TeamPreviewGame.my_actions()/opp_actions() actually reflect synergy_weights/mega_penalty")
plain_game = TeamPreviewGame(_FakeBridge(), [root_state], tp_bring_cap=1, tp_lead_cap=1)
synergy_game = TeamPreviewGame(_FakeBridge(), [root_state], tp_bring_cap=1, tp_lead_cap=1,
                                synergy_weights=CORE_SYNERGY, mega_penalty=1.0)

plain_root = plain_game._roots[0]
synergy_root = synergy_game._roots[0]

plain_my = plain_game.my_actions(plain_root)
synergy_my = synergy_game.my_actions(synergy_root)
check("my_actions() output differs between a plain game and a synergy/mega-configured one",
      [(tuple(a.bring), tuple(a.lead_order)) for a in plain_my]
      != [(tuple(a.bring), tuple(a.lead_order)) for a in synergy_my],
      (plain_my, synergy_my))

plain_opp = plain_game.opp_actions(plain_root)
synergy_opp = synergy_game.opp_actions(synergy_root)
check("opp_actions() is threaded the same way (symmetric over side)",
      [(tuple(a.bring), tuple(a.lead_order)) for a in plain_opp]
      != [(tuple(a.bring), tuple(a.lead_order)) for a in synergy_opp],
      (plain_opp, synergy_opp))

check("the synergy-configured game's #1 bring subset is the real core",
      {ROSTER[i] for i in synergy_my[0].bring} == {"archaludon", "pelipper", "sinistcha", "swampert"},
      [ROSTER[i] for i in synergy_my[0].bring])

print(f"\n{'PASS' if not failures else 'FAIL: ' + ', '.join(failures)}")
