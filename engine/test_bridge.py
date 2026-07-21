"""Validates the engine bridge against the real Sim.Battle:

1. init echo: engine-computed stats exactly match the FullInfoState's
   (proves the champions points inversion against the real formula, not
   our reimplementation of it), hp/status/boosts/faints/turn preserved.
2. step: a real turn resolves, damage happens, turn advances, no choice
   errors for well-formed actions.
3. snapshot immutability: stepping the same parent handle twice works.
4. mega evolution via the choice flag: species/stats/mega_used all flip.
5. forced mid-turn replacement auto-resolved inside step() (KO'd lead is
   replaced by the bench mon without a switch request leaking out).
6. plays to terminal: repeated steps reach a +1 result vs an all-at-1-HP
   opponent team.
7. mega_used regression: two roots, neither side has actually mega'd
   (field.*_side.mega_used=False going in), but they differ in whether a
   CURRENT mon happens to hold a legal stone. Echoed mega_used must be
   False for both - it must reflect "already used", never "someone
   currently eligible" (a bug found via the real my_key-mismatch crash
   this regression-guards: a hidden bench mon's sampled item differing
   per determinization world was leaking into what must be a
   world-independent public fact).
8. boost/status override regression: the true observed state says a mon
   has boosts.atk=0 and no status, but reconstruction naturally produces
   nonzero (an ally's Intimidate firing on send-out) - echo must show
   the true value (0/none), not whatever the fresh reconstruction's own
   side effects computed. Same bug class as mega_used: a genuine 0/none
   is falsy, so a "set if truthy" assignment silently lets a hidden-
   info-dependent reconstruction artifact leak through as if it were the
   real public fact.
9. position-flip regression: a side with an empty LEFT (fainted, no
   living replacement) and a living RIGHT mon must echo that mon as
   RIGHT, not slide it into LEFT because it was first in team order.
10. forced-continuation regression (found only at depth-2+ search, since
    it only manifests the turn AFTER the triggering move): a two-turn
    move (Solar Beam mid-charge) or a recharge move (Hyper Beam) must
    narrow `moves` to exactly the one forced entry with `trapped=True`,
    not the mon's normal 4-move list - the old export caused "doesn't
    have move N" / "can't choose a target for recharge" rejections deep
    in search. Uses Pokemon.getMoveRequestData(), the engine's own
    request-generation call, not a reimplementation.
11. ability-trapping regression (Shadow Tag, the only champions-legal
    trapper): getMoveRequestData()'s exported `trapped` field is
    deliberately gated - it hides trapped-status from the protocol when
    caused by an undiscovered ability (p.trapped becomes the string
    'hidden', not true, precisely so a real player isn't told about a
    trapping ability they haven't found yet). Correct for the live
    protocol; wrong for search, which reasons inside an already fully-
    determinized world with nothing left to hide from itself. Must read
    p.trapped directly, not the protocol-gated req.trapped.

Needs node + the built vendor sim (vendor/pokemon-showdown/dist).
Run from the project root: python -m engine.test_bridge
"""

import json
from pathlib import Path

from engine.bridge import EngineBridge
from schema.battle_state import (
    Boosts, FieldState, MoveAction, MoveSlot, OwnPokemon, Position, Status, Target, TurnActions,
)
from schema.full_info_state import FullInfoState

_ROOT = Path(__file__).resolve().parent.parent
_SPECIES_STATS = json.loads((_ROOT / "reference" / "species_stats.json").read_text(encoding="utf-8"))

FORMAT = "gen9championsvgc2026regmb"
failures = []


def check(name: str, ok: bool, detail: str = ""):
    print(f"  {name} [{'ok' if ok else 'FAIL'}]{' ' + str(detail) if detail and not ok else ''}")
    if not ok:
        failures.append(name)


def flat(species):
    """(max_hp, stats) at zero champions points — what the engine must
    compute back for a 0-EV set, making the echo comparison exact."""
    base = _SPECIES_STATS[species]["base_stats"]
    return base["hp"] + 75, {k: base[k] + 20 for k in ("atk", "def", "spa", "spd", "spe")}


def mk(species, moves, ability, item=None, position=None, hp=None, fainted=False,
       status=Status.NONE, boosts=None):
    max_hp, stats = flat(species)
    return OwnPokemon(
        species=species, position=position, fainted=fainted,
        hp=0 if fainted else (hp if hp is not None else max_hp), max_hp=max_hp,
        status=status, stats=stats, boosts=boosts or Boosts(),
        ability=ability, item=item,
        moves=[MoveSlot(move=m, pp=16, max_pp=16) for m in moves],
    )


def base_state():
    ttar_hp = int(flat("tyranitar")[0] * 0.75)
    return FullInfoState(
        turn=4,
        field=FieldState(),
        my_team=[
            mk("charizard", ["heatwave", "airslash", "protect", "solarbeam"], "blaze",
               item="charizarditey", position=Position.LEFT),
            mk("garchomp", ["earthquake", "dragonclaw", "protect", "swordsdance"], "roughskin",
               position=Position.RIGHT),
            mk("clefable", ["moonblast", "protect"], "magicguard"),
            mk("annihilape", ["ragefist", "drainpunch"], "defiant"),
        ],
        opp_team=[
            mk("tyranitar", ["rockslide", "crunch", "protect"], "unnerve",
               position=Position.LEFT, hp=ttar_hp, status=Status.BRN, boosts=Boosts(atk=1)),
            mk("garchomp", ["earthquake", "dragonclaw", "protect"], "roughskin",
               item="garchompite", position=Position.RIGHT),
            mk("rotomwash", ["hydropump", "voltswitch"], "levitate"),
            mk("basculegion", ["wavecrash", "protect"], "adaptability", fainted=True),
        ],
    )


bridge = EngineBridge(FORMAT)
state = base_state()
handle, echo = bridge.init_battle(state)

print("1. init echo fidelity (real engine recomputes everything from sets)")
stat_mismatches = []
for sent_team, echo_team, label in ((state.my_team, echo.my_team, "me"), (state.opp_team, echo.opp_team, "opp")):
    for sent, got in zip(sent_team, echo_team):
        if got.stats != sent.stats or got.max_hp != sent.max_hp:
            stat_mismatches.append(f"{label}/{sent.species}: sent {sent.stats}/{sent.max_hp} got {got.stats}/{got.max_hp}")
check("champions stat formula inversion exact (all 8 mons)", not stat_mismatches, "; ".join(stat_mismatches))
ttar = echo.opp_team[0]
check("hp/status/boosts preserved",
      ttar.hp == state.opp_team[0].hp and ttar.status == Status.BRN and ttar.boosts.atk == 1,
      f"hp={ttar.hp} status={ttar.status} atk={ttar.boosts.atk}")
check("turn preserved", echo.turn == 4, echo.turn)
check("fainted bench mon stays fainted", echo.opp_team[3].fainted)
check("positions preserved", echo.my_team[0].position == Position.LEFT and echo.opp_team[1].position == Position.RIGHT)

print("\n2. one real turn")
my = TurnActions(
    slot_left=MoveAction(move_slot=1, target=Target.NONE),        # heat wave (spread)
    slot_right=MoveAction(move_slot=2, target=Target.OPP_LEFT),   # dragon claw -> tyranitar
)
opp = TurnActions(
    slot_left=MoveAction(move_slot=2, target=Target.OPP_LEFT),    # crunch -> my charizard
    slot_right=MoveAction(move_slot=2, target=Target.OPP_RIGHT),  # dragon claw -> my garchomp
)
r = bridge.step(handle, echo, my, opp)
check("no choice errors", not r.errors, r.errors)
check("not terminal", r.terminal is None)
check("turn advanced", r.state.turn == 5, r.state.turn)
opp_hp_before = sum(m.hp for m in echo.opp_team)
opp_hp_after = sum(m.hp for m in r.state.opp_team)
check("opponent took damage", opp_hp_after < opp_hp_before, f"{opp_hp_before} -> {opp_hp_after}")

print("\n3. snapshot immutability (same parent stepped again)")
r2 = bridge.step(handle, echo, my, opp)
check("second step from same parent works", not r2.errors and r2.state.turn == 5)

print("\n4. mega evolution")
my_mega = TurnActions(
    slot_left=MoveAction(move_slot=2, target=Target.OPP_LEFT, mega=True),  # air slash + mega
    slot_right=MoveAction(move_slot=3, target=Target.SELF),                # protect
)
opp_protect = TurnActions(
    slot_left=MoveAction(move_slot=3, target=Target.SELF),
    slot_right=MoveAction(move_slot=3, target=Target.SELF),
)
r3 = bridge.step(handle, echo, my_mega, opp_protect)
zard = r3.state.my_team[0]
mega_hp, mega_stats = flat("charizardmegay")
check("species updated to mega forme", zard.species == "charizardmegay", zard.species)
check("mega stats live", zard.stats == mega_stats, f"{zard.stats} vs {mega_stats}")
check("mega_activated + side mega_used", zard.mega_activated and r3.state.field.my_side.mega_used)
check("opp side can still mega", not r3.state.field.opp_side.mega_used)

print("\n5. forced mid-turn replacement resolved inside step")
weak = base_state()
weak.opp_team[0].hp = 1
weak.opp_team[0].status = Status.NONE
h2, echo2 = bridge.init_battle(weak)
kill = TurnActions(
    slot_left=MoveAction(move_slot=3, target=Target.SELF),        # protect
    slot_right=MoveAction(move_slot=2, target=Target.OPP_LEFT),   # dragon claw -> 1hp tyranitar
)
r4 = bridge.step(h2, echo2, kill, opp)
dead_ttar = next(m for m in r4.state.opp_team if m.species == "tyranitar")
left_replacement = next((m for m in r4.state.opp_team if m.position == Position.LEFT and not m.fainted), None)
check("tyranitar KO'd", dead_ttar.fainted)
check("bench mon auto-switched into the empty slot",
      left_replacement is not None and left_replacement.species == "rotomwash",
      left_replacement.species if left_replacement else None)
check("no switch request leaked (still a normal move turn)", r4.terminal is None and r4.handle is not None)

print("\n6. plays to terminal")
doomed = base_state()
for mon in doomed.opp_team:
    if not mon.fainted:
        mon.hp = 1
        mon.status = Status.NONE
h3, cur = bridge.init_battle(doomed)
smash = TurnActions(
    slot_left=MoveAction(move_slot=1, target=Target.NONE),
    slot_right=MoveAction(move_slot=2, target=Target.OPP_LEFT),
)
terminal = None
for _ in range(15):
    res = bridge.step(h3, cur, smash, opp)
    if res.terminal is not None:
        terminal = res.terminal
        break
    h3, cur = res.handle, res.state
check("reached terminal", terminal is not None)
check("won (+1 my POV)", terminal == 1.0, terminal)

print("\n7. mega_used regression (stone-holding must not leak as mega_used)")
# world A: nobody on either side holds a stone at all
world_a = base_state()
world_a.opp_team[0].item = None  # tyranitar's stone stripped
# world B: opp's charizard (a DIFFERENT mon than world A's stone-bearer)
# holds a legal stone - simulates two determinizations disagreeing on
# which hidden mon, if any, is the stone-holder
world_b = base_state()
world_b.opp_team[0].item = None
world_b.opp_team[2].species = "charizard"  # rotomwash slot -> charizard
world_b.opp_team[2].item = "charizarditey"
for w in (world_a, world_b):
    w.field.my_side.mega_used = False
    w.field.opp_side.mega_used = False
_, echo_a = bridge.init_battle(world_a)
_, echo_b = bridge.init_battle(world_b)
check("neither side flagged mega_used in world A",
      not echo_a.field.my_side.mega_used and not echo_a.field.opp_side.mega_used)
check("neither side flagged mega_used in world B despite a stone-holder existing",
      not echo_b.field.my_side.mega_used and not echo_b.field.opp_side.mega_used)
check("the two worlds' opp_side.mega_used agree (public-key world-independence)",
      echo_a.field.opp_side.mega_used == echo_b.field.opp_side.mega_used)

print("\n8. boost/status override regression (Intimidate on send-out must not overwrite a true 0)")
intimidate_state = FullInfoState(
    turn=1, field=FieldState(),
    my_team=[
        mk("incineroar", ["fakeout", "flareblitz", "darkestlariat", "protect"], "intimidate",
           item="sitrusberry", position=Position.LEFT),
        mk("garchomp", ["earthquake", "dragonclaw", "protect", "swordsdance"], "roughskin",
           position=Position.RIGHT),
    ],
    opp_team=[
        # true observed state: no boost, no status - despite my Incineroar's
        # Intimidate necessarily firing again during fresh reconstruction
        mk("charizard", ["heatwave", "airslash", "protect", "solarbeam"], "blaze",
           position=Position.LEFT, boosts=Boosts(atk=0), status=Status.NONE),
        mk("clefable", ["moonblast", "protect"], "magicguard", position=Position.RIGHT),
    ],
)
_, echo6 = bridge.init_battle(intimidate_state)
opp_charizard = next(m for m in echo6.opp_team if m.species == "charizard")
check("true boosts.atk=0 survives an ally's Intimidate firing during reconstruction",
      opp_charizard.boosts.atk == 0, opp_charizard.boosts.atk)
check("true status=NONE survives reconstruction", opp_charizard.status == Status.NONE, opp_charizard.status)
# repeat-call determinism: same input must give the same (correct) output every time
for i in range(3):
    _, echo_repeat = bridge.init_battle(intimidate_state)
    repeat_charizard = next(m for m in echo_repeat.opp_team if m.species == "charizard")
    check(f"repeat call {i} still shows atk=0", repeat_charizard.boosts.atk == 0, repeat_charizard.boosts.atk)

print("\n9. position-flip regression (empty LEFT, living RIGHT)")
orphaned = base_state()
orphaned.my_team[0] = mk("charizardmegay", ["flamethrower", "airslash", "protect", "solarbeam"],
                          "drought", item="charizarditey", position=None, fainted=True)
# my_team[1] (garchomp) stays position=Position.RIGHT, the only living mon
_, echo5 = bridge.init_battle(orphaned)
right_mon = next((m for m in echo5.my_team if m.species == "garchomp"), None)
check("living mon echoes its real position (RIGHT), not slid into LEFT",
      right_mon is not None and right_mon.position == Position.RIGHT,
      right_mon.position if right_mon else None)

print("\n10. forced-continuation regression (Solar Beam charge, Hyper Beam recharge)")
lock_state = base_state()
lock_state.my_team[0] = mk("charizard", ["solarbeam", "flamethrower", "protect", "airslash"], "blaze",
                            item="charizarditey", position=Position.LEFT)
handle7, echo7 = bridge.init_battle(lock_state)
charge_turn = bridge.step(
    handle7, echo7,
    my=TurnActions(slot_left=MoveAction(move_slot=1, target=Target.OPP_LEFT), slot_right=MoveAction(move_slot=3, target=Target.SELF)),
    opp=TurnActions(slot_left=MoveAction(move_slot=3, target=Target.SELF), slot_right=MoveAction(move_slot=3, target=Target.SELF)),
)
check("charging turn has no errors", not charge_turn.errors, charge_turn.errors)
charging_zard = next(m for m in charge_turn.state.my_team if m.species == "charizard")
check("moves narrowed to exactly solarbeam", [m.move for m in charging_zard.moves] == ["solarbeam"],
      [m.move for m in charging_zard.moves])
check("trapped=True while charging", charging_zard.trapped)
release_turn = bridge.step(
    charge_turn.handle, charge_turn.state,
    my=TurnActions(slot_left=MoveAction(move_slot=1, target=Target.NONE), slot_right=MoveAction(move_slot=3, target=Target.SELF)),
    opp=TurnActions(slot_left=MoveAction(move_slot=3, target=Target.SELF), slot_right=MoveAction(move_slot=3, target=Target.SELF)),
)
check("release turn (move_slot=1, no target) has no errors", not release_turn.errors, release_turn.errors)
released_zard = next(m for m in release_turn.state.my_team if m.species == "charizard")
check("moves back to normal 4 after release", len(released_zard.moves) == 4, len(released_zard.moves))
check("trapped=False after release", not released_zard.trapped)

recharge_state = base_state()
recharge_state.my_team[0] = mk("charizard", ["hyperbeam", "flamethrower", "protect", "airslash"], "blaze",
                                item="charizarditey", position=Position.LEFT)
# Hyper Beam is 90% accurate and mustrecharge only applies on a hit (real
# game mechanics, confirmed against data/moves.ts) - each step() reseeds
# the engine RNG, so retry the ~1-in-10 miss rather than treat it as a
# failure. Opponent attacks back (NOT protect - tyranitar's move_slot=3
# in base_state() IS protect, which would block Hyper Beam entirely and
# suppress recharge deterministically, not just add miss-chance noise).
recharging_zard = None
for attempt in range(8):
    handle8, echo8 = bridge.init_battle(recharge_state)
    hb_turn = bridge.step(
        handle8, echo8,
        my=TurnActions(slot_left=MoveAction(move_slot=1, target=Target.OPP_LEFT), slot_right=MoveAction(move_slot=3, target=Target.SELF)),
        opp=TurnActions(slot_left=MoveAction(move_slot=2, target=Target.OPP_LEFT), slot_right=MoveAction(move_slot=2, target=Target.OPP_LEFT)),
    )
    check(f"hyper beam turn has no errors (attempt {attempt})", not hb_turn.errors, hb_turn.errors)
    candidate = next(m for m in hb_turn.state.my_team if m.species == "charizard")
    if candidate.trapped:
        recharging_zard = candidate
        break
check("hyper beam eventually connected and locked recharge within 8 tries", recharging_zard is not None)
recharging_zard = recharging_zard or next(m for m in hb_turn.state.my_team if m.species == "charizard")
check("moves narrowed to exactly recharge", [m.move for m in recharging_zard.moves] == ["recharge"],
      [m.move for m in recharging_zard.moves])
check("trapped=True while recharging", recharging_zard.trapped)
recharge_turn = bridge.step(
    hb_turn.handle, hb_turn.state,
    my=TurnActions(slot_left=MoveAction(move_slot=1, target=Target.NONE), slot_right=MoveAction(move_slot=3, target=Target.SELF)),
    opp=TurnActions(slot_left=MoveAction(move_slot=3, target=Target.SELF), slot_right=MoveAction(move_slot=3, target=Target.SELF)),
)
check("recharge turn (move_slot=1, no target) has no errors", not recharge_turn.errors, recharge_turn.errors)

print("\n11. ability-trapping regression (Shadow Tag)")
shadowtag_state = FullInfoState(
    turn=1, field=FieldState(),
    my_team=[
        mk("garchomp", ["earthquake", "dragonclaw", "protect", "swordsdance"], "roughskin", position=Position.LEFT),
        mk("charizard", ["flamethrower", "airslash", "protect", "dragonclaw"], "blaze", position=Position.RIGHT),
    ],
    opp_team=[
        mk("gengarmega", ["shadowball", "sludgebomb"], "shadowtag", position=Position.LEFT),
        mk("rotomwash", ["hydropump", "voltswitch"], "levitate", position=Position.RIGHT),
    ],
)
_, echo9 = bridge.init_battle(shadowtag_state)
trapped_garchomp = next(m for m in echo9.my_team if m.species == "garchomp")
check("garchomp trapped by opposing Shadow Tag straight from init_battle", trapped_garchomp.trapped)
free_charizard = next(m for m in echo9.my_team if m.species == "charizard")
check("charizard (not the trap target's concern - doubles adjacency covers both) also trapped",
      free_charizard.trapped)

ghost_state = shadowtag_state.model_copy(deep=True)
ghost_state.my_team[0] = mk("gholdengo", ["shadowball", "makeitrain", "protect", "recover"], "goodasgold",
                             position=Position.LEFT)
_, echo10 = bridge.init_battle(ghost_state)
immune_gholdengo = next(m for m in echo10.my_team if m.species == "gholdengo")
check("Ghost-type Gholdengo correctly immune to Shadow Tag (real engine's own type-immunity check, "
      "not something we special-cased)", not immune_gholdengo.trapped)

bridge.free([handle, h2])
bridge.close()
print(f"\n{'PASS' if not failures else 'FAIL: ' + ', '.join(failures)}")
