"""Validates the placeholder determinizer's structural guarantees over
many samples of a hand-built mid-battle BattleState:

- always exactly 4 opponent mons: the revealed ones (facts preserved
  exactly) + hypothesized back picks drawn only from unseen roster
  species, with sampling variety across calls
- all sampled moves come from the species' real learnset, no duplicates,
  revealed moves always present
- item clause holds; revealed items preserved; mega stones only on
  species they actually mega; sampled abilities legal
- champions stat floor + hp% -> concrete hp conversion
- my side copied through unchanged

Run from the project root: python -m belief.test_determinize
"""

import json
import random
from pathlib import Path

from belief.determinize import sample_determinization, sample_team_preview_world
from schema.battle_state import (
    BattleState, Boosts, FieldState, MoveSlot, OpponentPokemon, OwnPokemon, Position, Status, TeamPreviewInfo,
)

_ROOT = Path(__file__).resolve().parent.parent
_SPECIES_DATA = json.loads((_ROOT / "reference" / "species_data.json").read_text(encoding="utf-8"))
_SPECIES_STATS = json.loads((_ROOT / "reference" / "species_stats.json").read_text(encoding="utf-8"))
_MEGA_STONES = json.loads((_ROOT / "reference" / "mega_stones.json").read_text(encoding="utf-8"))
_LEGAL_ITEMS = set((_ROOT / "reference" / "champions_legal_items.txt").read_text(encoding="utf-8").split())

failures = []


def check(name: str, ok: bool, detail: str = ""):
    print(f"  {name} [{'ok' if ok else 'FAIL'}]{' ' + detail if detail and not ok else ''}")
    if not ok:
        failures.append(name)


def own(species, position=None):
    assert species in _SPECIES_DATA, f"typo: {species}"
    return OwnPokemon(
        species=species, position=position, hp=180, max_hp=180,
        stats={"atk": 120, "def": 120, "spa": 120, "spd": 120, "spe": 120},
        ability="intimidate",
        moves=[MoveSlot(move=m, pp=16, max_pp=16) for m in _SPECIES_DATA[species]["moves"][:4]],
    )


ROSTER = ["tyranitar", "charizard", "skarmory", "pyroar", "archaludon", "basculegion"]
for s in ROSTER:
    assert s in _SPECIES_DATA, f"typo: {s}"

state = BattleState(
    format_id="gen9championsvgc2026regmb",
    turn=4,
    field=FieldState(),
    opp_roster=ROSTER,
    my_active=[own("garchomp", Position.LEFT), own("incineroar", Position.RIGHT)],
    my_bench=[own("clefable"), own("annihilape")],
    opp_active=[
        OpponentPokemon(
            species="tyranitar", position=Position.LEFT, hp_pct=75.0,
            status=Status.BRN, boosts=Boosts(atk=1),
            revealed_moves=["rockslide"],
        ),
        OpponentPokemon(
            species="charizard", position=Position.RIGHT, hp_pct=100.0,
            revealed_item="charizarditey", revealed_ability="solarpower",
        ),
    ],
    opp_bench=[],
)

N = 300
rng = random.Random(42)
samples = [sample_determinization(state, rng) for _ in range(N)]
unseen = {"skarmory", "pyroar", "archaludon", "basculegion"}

check("always 4 opponent mons", all(len(s.opp_team) == 4 for s in samples))
check("revealed leads first, positions kept", all(
    s.opp_team[0].species == "tyranitar" and s.opp_team[0].position == Position.LEFT
    and s.opp_team[1].species == "charizard" and s.opp_team[1].position == Position.RIGHT
    for s in samples
))

hyp_pairs = [tuple(m.species for m in s.opp_team[2:]) for s in samples]
check("hypothesized only from unseen roster", all(
    set(pair) <= unseen and len(set(pair)) == 2 for pair in hyp_pairs
))
distinct_species = {sp for pair in hyp_pairs for sp in pair}
check("sampling variety (all 4 unseen appear across samples)", distinct_species == unseen,
      f"saw {distinct_species}")

tyranitar_learnset = set(_SPECIES_DATA["tyranitar"]["moves"])
check("revealed move always kept", all(
    "rockslide" in [m.move for m in s.opp_team[0].moves] for s in samples
))
check("4 legal, distinct moves per mon", all(
    len(mon.moves) == 4
    and len({m.move for m in mon.moves}) == 4
    and {m.move for m in mon.moves} <= set(_SPECIES_DATA[mon.species]["moves"])
    for s in samples for mon in s.opp_team
))

check("revealed item/ability preserved", all(
    s.opp_team[1].item == "charizarditey" and s.opp_team[1].ability == "solarpower"
    for s in samples
))
check("item clause (no duplicates)", all(
    len({mon.item for mon in s.opp_team if mon.item}) ==
    len([mon for mon in s.opp_team if mon.item])
    for s in samples
))
check("items legal", all(
    mon.item in _LEGAL_ITEMS for s in samples for mon in s.opp_team if mon.item
))
check("stones only on their own species", all(
    mon.species in _MEGA_STONES[mon.item]
    for s in samples for mon in s.opp_team
    if mon.item in _MEGA_STONES and mon is not s.opp_team[1]  # charizard's is revealed
))
check("abilities legal", all(
    mon.ability in _SPECIES_DATA[mon.species]["abilities"]
    for s in samples for mon in s.opp_team
    if mon is not s.opp_team[1]
))

ttar_max_hp = _SPECIES_STATS["tyranitar"]["base_stats"]["hp"] + 75
check("champions stat floor + hp% conversion", all(
    s.opp_team[0].max_hp == ttar_max_hp
    and s.opp_team[0].hp == int(round(ttar_max_hp * 0.75))
    and s.opp_team[0].stats["atk"] == _SPECIES_STATS["tyranitar"]["base_stats"]["atk"] + 20
    for s in samples
))
check("status/boosts carried over", all(
    s.opp_team[0].status == Status.BRN and s.opp_team[0].boosts.atk == 1 for s in samples
))

check("my side copied through", all(
    [m.species for m in s.my_team] == ["garchomp", "incineroar", "clefable", "annihilape"]
    for s in samples
))

print("\nweighted sampling actually reflects real usage skew (not just uniform-but-doesn't-crash)")
# Garchomp's real Pikalytics data: Dragon Claw 89.4% vs Dragon Tail 2.0%
# (belief/usage_data/usage_stats.json) - if weighting works, sampling
# Garchomp's unrevealed moveset many times should pick Dragon Claw far
# more often than Dragon Tail, not roughly the same rate a flat uniform
# draw over its ~10-15 legal moves would give both.
weight_state = BattleState(
    format_id="gen9championsvgc2026regmb", turn=1, field=FieldState(),
    opp_roster=["garchomp", "tyranitar", "charizard", "incineroar", "clefable", "annihilape"],
    my_active=[own("garchomp", Position.LEFT), own("incineroar", Position.RIGHT)],
    my_bench=[own("clefable"), own("annihilape")],
    opp_active=[OpponentPokemon(species="garchomp", position=Position.LEFT, hp_pct=100.0)],
    opp_bench=[],
)
N = 400
rng2 = random.Random(1)
gc_samples = [sample_determinization(weight_state, rng2) for _ in range(N)]
dragonclaw_count = sum(
    1 for s in gc_samples for m in s.opp_team[0].moves if m.move == "dragonclaw"
)
dragontail_count = sum(
    1 for s in gc_samples for m in s.opp_team[0].moves if m.move == "dragontail"
)
print(f"  dragonclaw appeared in {dragonclaw_count}/{N} samples, dragontail in {dragontail_count}/{N}")
check("real top move (dragonclaw, 89.4% usage) sampled far more than a rare legal move (dragontail, 2.0%)",
      dragonclaw_count > dragontail_count * 3, f"{dragonclaw_count} vs {dragontail_count}")
check("real top move sampled the clear majority of the time", dragonclaw_count > N * 0.6, str(dragonclaw_count))

print("\nsample_team_preview_world: team-preview-time determinizer (all 6 opponent mons, nothing revealed yet)")
TP_MY_ROSTER = ["garchomp", "incineroar", "clefable", "annihilape", "tyranitar", "skarmory"]
TP_OPP_ROSTER = ["charizard", "sylveon", "archaludon", "pelipper", "grimmsnarl", "metagross"]
tp_my_bench = [own(s) for s in TP_MY_ROSTER]  # own() defaults position=None
tp_state = BattleState(
    format_id="gen9championsvgc2026regmb", turn=0, field=FieldState(),
    team_preview=TeamPreviewInfo(my_team=[m.species for m in tp_my_bench], opp_team=TP_OPP_ROSTER),
    opp_roster=TP_OPP_ROSTER,
    my_active=[], my_bench=tp_my_bench,
    opp_active=[], opp_bench=[],
)
N = 300
rng3 = random.Random(7)
tp_samples = [sample_team_preview_world(tp_state, rng3) for _ in range(N)]

check("always exactly 6 opponent mons", all(len(s.opp_team) == 6 for s in tp_samples))
check("opponent species match the roster, in roster order", all(
    [m.species for m in s.opp_team] == TP_OPP_ROSTER for s in tp_samples
))
check("all opponent mons unassigned (nobody active yet)", all(
    m.position is None for s in tp_samples for m in s.opp_team
))
check("4 legal, distinct moves per opponent mon", all(
    len(mon.moves) == 4
    and len({m.move for m in mon.moves}) == 4
    and {m.move for m in mon.moves} <= set(_SPECIES_DATA[mon.species]["moves"])
    for s in tp_samples for mon in s.opp_team
))
check("item clause across all 6 opponent mons", all(
    len({mon.item for mon in s.opp_team if mon.item}) == len([mon for mon in s.opp_team if mon.item])
    for s in tp_samples
))
check("items legal", all(
    mon.item in _LEGAL_ITEMS for s in tp_samples for mon in s.opp_team if mon.item
))
check("stones only on their own species", all(
    mon.species in _MEGA_STONES[mon.item]
    for s in tp_samples for mon in s.opp_team if mon.item in _MEGA_STONES
))
check("abilities legal", all(
    mon.ability in _SPECIES_DATA[mon.species]["abilities"] for s in tp_samples for mon in s.opp_team
))
charizard_max_hp = _SPECIES_STATS["charizard"]["base_stats"]["hp"] + 75
check("champions stat floor", all(
    s.opp_team[0].max_hp == charizard_max_hp
    and s.opp_team[0].stats["atk"] == _SPECIES_STATS["charizard"]["base_stats"]["atk"] + 20
    for s in tp_samples
))

check("my side copied through byte-for-byte unchanged, not resampled", all(
    s.my_team == tp_my_bench for s in tp_samples
))
check("my-side / team_preview.my_team ordering is consistent (same species order)", all(
    [m.species for m in s.my_team] == tp_state.team_preview.my_team for s in tp_samples
))

print(f"\n{'PASS' if not failures else 'FAIL: ' + ', '.join(failures)}")
