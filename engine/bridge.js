'use strict';

/**
 * Search-rollout engine bridge: drives Showdown's real Sim.Battle in-process
 * (no server, no websocket) over a JSON-lines stdio protocol, for the
 * solver's step() calls (docs/solver_design.md 2.7).
 *
 * Snapshot model: battles are stored as immutable serialized snapshots
 * (Battle.toJSON strings). Every step restores the parent snapshot into a
 * fresh Battle, RESEEDS ITS RNG (so repeated steps from the same parent
 * sample fresh chance outcomes - MCCFR needs that), advances one full turn,
 * auto-resolves any forced mid-turn replacements with the engine's default
 * choice (= first available switch-in, the documented V1 heuristic), and
 * stores the child as a new snapshot. Parents are never mutated.
 *
 * Root reconstruction (init) builds a real battle from a FullInfoState:
 * teams as set objects (points recovered exactly from final stats via the
 * champions formula's linear inverse: points = stat - base - 20, hp - 75,
 * neutral nature), team preview ordered so actives lead, then direct state
 * mutation (turn, hp, status, boosts, pp, faints, field/side conditions
 * with elapsed->remaining duration conversion, one-mega-per-side flags).
 * Known V1 fidelity gaps, deliberate: volatiles are not reconstructed at
 * the root (Protect streaks, Encore, etc. - they DO evolve correctly for
 * turns simulated below the root), duration items (Light Clay etc.) are
 * assumed absent in remaining-duration math, sleep counters default to 2.
 *
 * Ops: init {format, state} -> {handle, state}
 *      init_team_preview {format, state} -> {handle}  (fresh battle, PAUSED
 *      at the teampreview request - see opInitTeamPreview. Submit the
 *      actual bring/lead choices afterward through the existing step op:
 *      Showdown's side.choose() already dispatches to chooseTeam()
 *      generically whenever requestState === 'teampreview', the same way
 *      it dispatches move/switch choices - opStep needs no changes.)
 *      step {handle, my, opp} -> {handle?, state, terminal?, errors}
 *      free {handles} -> {}
 *      ping -> {}
 * Every request carries an id, echoed in the response. Errors: {ok: false,
 * error}. The exported state mirrors schema/full_info_state.py field names
 * exactly; field/side-condition *_turns carry REMAINING duration (engine
 * semantics), not elapsed - only my_key/leaf/debugging consume them.
 */

const path = require('path');
const readline = require('readline');

const SIM = path.join(__dirname, '..', 'vendor', 'pokemon-showdown', 'dist', 'sim');
const { Battle, Dex } = require(SIM);
const { PRNG } = require(path.join(SIM, 'prng'));

const snapshots = new Map();
let nextHandle = 1;

const WEATHER_TO_ENGINE = { sun: 'sunnyday', rain: 'raindance', sand: 'sandstorm', snow: 'snowscape' };
const ENGINE_TO_WEATHER = {
  sunnyday: 'sun', desolateland: 'sun', raindance: 'rain', primordialsea: 'rain',
  sandstorm: 'sand', hail: 'snow', snowscape: 'snow',
};
const TERRAIN_TO_ENGINE = {
  electric: 'electricterrain', grassy: 'grassyterrain', misty: 'mistyterrain', psychic: 'psychicterrain',
};
const ENGINE_TO_TERRAIN = {
  electricterrain: 'electric', grassyterrain: 'grassy', mistyterrain: 'misty', psychicterrain: 'psychic',
};
const BOOST_FROM_SCHEMA = { atk: 'atk', defense: 'def', spa: 'spa', spd: 'spd', spe: 'spe', acc: 'accuracy', eva: 'evasion' };
const STATS = ['atk', 'def', 'spa', 'spd', 'spe'];
// [schema field, engine condition id, base duration in turns]
const TIMED_SIDE_CONDITIONS = [
  ['reflect_turns', 'reflect', 5], ['light_screen_turns', 'lightscreen', 5],
  ['aurora_veil_turns', 'auroraveil', 5], ['tailwind_turns', 'tailwind', 4],
  ['safeguard_turns', 'safeguard', 5], ['mist_turns', 'mist', 5],
];

function clampDuration(n) {
  return Math.max(1, Math.min(8, n | 0));
}

function buildSet(mon, dex) {
  const species = dex.species.get(mon.species);
  if (!species.exists) throw new Error(`unknown species: ${mon.species}`);
  const base = species.baseStats;
  const evs = { hp: Math.max(0, mon.max_hp - base.hp - 75) };
  for (const s of STATS) evs[s] = Math.max(0, mon.stats[s] - base[s] - 20);
  return {
    name: species.name,
    species: species.name,
    item: mon.item || '',
    ability: mon.ability,
    moves: mon.moves.map(ms => ms.move),
    nature: 'Serious', // neutral: keeps the champions stat formula exactly invertible
    evs,
    ivs: { hp: 31, atk: 31, def: 31, spa: 31, spd: 31, spe: 31 },
    level: mon.level || 50,
  };
}

function applyMonState(p, mon) {
  if (mon.fainted) {
    p.hp = 0;
    p.fainted = true;
    p.status = '';
    p.side.pokemonLeft--;
    return;
  }
  p.hp = Math.max(1, Math.min(mon.hp, p.maxhp));
  if (mon.status && mon.status !== 'none') {
    p.setStatus(mon.status, null, null, true);
    if (p.status !== mon.status) { // immunity from a hypothesized ability - force it anyway
      p.status = mon.status;
      p.statusState = { id: mon.status, target: p };
    }
    if (mon.status === 'slp') p.statusState.time = 2;
    if (mon.status === 'tox') p.statusState.stage = Math.max(1, mon.status_turns || 1);
  } else if (p.status) {
    // True state says no status, but team-preview/send-out setup (e.g. a
    // hypothesized ability or item reacting to something) gave the fresh
    // reconstruction one anyway. Authoritative source always wins - same
    // principle as boosts below, and the same bug class as mega_used: a
    // hidden-info-dependent side effect of reconstruction must never leak
    // through as if it were the true, publicly-observed fact.
    p.status = '';
    p.statusState = { id: '', target: p };
  }
  // Unconditional assignment, not "set if truthy": a genuine 0 must
  // overwrite whatever the engine's own reconstruction produced (e.g.
  // Intimidate firing from an ally's send-out, then a hidden item like
  // Clear Amulet/White Herb - which varies per determinization world -
  // blocking or undoing it). Skipping on falsy 0 let that hidden-item-
  // dependent outcome leak through as if it were the true observed
  // boost, silently diverging the same public fact across worlds.
  for (const [schemaKey, engineKey] of Object.entries(BOOST_FROM_SCHEMA)) {
    p.boosts[engineKey] = (mon.boosts && mon.boosts[schemaKey]) || 0;
  }
  mon.moves.forEach((ms, j) => {
    if (p.moveSlots[j]) {
      p.moveSlots[j].pp = Math.min(ms.pp, p.moveSlots[j].maxpp);
      if (ms.disabled) p.moveSlots[j].disabled = true;
    }
  });
  // Volatiles are otherwise NOT reconstructed at the root (this module's
  // header comment, "Known V1 fidelity gaps") - these two targeted
  // exceptions exist because losing them broke both live play and search
  // rollouts the same way: a mon translated from a real recharge or
  // mid-two-turn-move request (harness/translator.py's
  // _forced_continuation_volatiles, from poke-env's DIRECT must_recharge/
  // preparing_move tracking - model/action_space.py's matching checks key
  // on these exact volatile names) keeps its real moveset with everything
  // disabled, and without the engine's OWN lock volatile it has no idea
  // the mon is locked - it demands a normal choice and rejects whatever
  // gets submitted for an exhausted-bench mon ("Can't pass: ... must make
  // a move"), or wrongly allows an illegal switch otherwise.
  if (mon.volatiles && mon.volatiles.some(v => v.name === 'must_recharge')) {
    // addVolatile (not a raw flag) is what makes Pokemon.getLockedMove()
    // return 'recharge' - the actual mechanism side.ts's chooseMove() uses
    // to force the real move regardless of what we submit, and what makes
    // the engine's own choice validation correctly refuse a switch too.
    p.addVolatile('mustrecharge');
  }
  const twoTurn = mon.volatiles && mon.volatiles.find(v => v.name === 'two_turn_move');
  if (twoTurn) {
    // Same mechanism, generalized to Solar Beam/Fly/Electro Shot-without-
    // Rain/etc.: conditions.ts's twoturnmove.onLockMove returns
    // effectState.move, so addVolatile + directly setting .move (rather
    // than relying on onStart's automatic derivation, which expects to run
    // inside the actual move-execution event context we don't have here)
    // is enough for getLockedMove() to force the real charging move
    // regardless of what slot we submit - same direct-state-mutation
    // reconstruction style as the moveSlots/boosts handling above.
    p.addVolatile('twoturnmove');
    if (p.volatiles.twoturnmove) p.volatiles.twoturnmove.move = twoTurn.data.move;
  }
}

function applySideConditions(side, sc) {
  const source = side.active[0] || side.pokemon[0];
  for (const [schemaKey, id, baseDuration] of TIMED_SIDE_CONDITIONS) {
    if (sc[schemaKey] > 0) {
      side.addSideCondition(id, source);
      if (side.sideConditions[id]) {
        side.sideConditions[id].duration = clampDuration(baseDuration - sc[schemaKey]);
      }
    }
  }
  if (sc.stealth_rock) side.addSideCondition('stealthrock', source);
  if (sc.sticky_web) side.addSideCondition('stickyweb', source);
  for (let i = 0; i < (sc.spikes_layers || 0); i++) side.addSideCondition('spikes', source);
  for (let i = 0; i < (sc.toxic_spikes_layers || 0); i++) side.addSideCondition('toxicspikes', source);
  // Tracked as an explicit flag, not inferred from canMegaEvo: whether any
  // CURRENT mon happens to hold a legal stone varies by determinized world
  // (a hidden bench mon's sampled item differs per world), so canMegaEvo
  // is world-dependent even before any mega has actually happened - using
  // it for mega_used leaked hidden info into the public key and broke the
  // solver's world-independence contract. A plain boolean here survives
  // Battle.toJSON/fromJSON via state.ts's generic own-key walk, so it
  // persists correctly across snapshot/restore through the whole tree.
  side.initialMegaUsed = !!sc.mega_used;
  if (sc.mega_used) {
    for (const p of side.pokemon) p.canMegaEvo = false;
  }
}

function applyField(battle, field) {
  const source = battle.p1.active[0] || battle.p1.pokemon[0];
  if (field.weather && field.weather !== 'none') {
    battle.field.setWeather(WEATHER_TO_ENGINE[field.weather], source);
    battle.field.weatherState.duration = clampDuration(5 - (field.weather_turns || 0));
  } else {
    battle.field.clearWeather(); // squash anything a start-of-battle ability set
  }
  if (field.terrain && field.terrain !== 'none') {
    battle.field.setTerrain(TERRAIN_TO_ENGINE[field.terrain], source);
    battle.field.terrainState.duration = clampDuration(5 - (field.terrain_turns || 0));
  } else {
    battle.field.clearTerrain();
  }
  if (field.trick_room_turns > 0) {
    battle.field.addPseudoWeather('trickroom', source);
    if (battle.field.pseudoWeather['trickroom']) {
      battle.field.pseudoWeather['trickroom'].duration = clampDuration(5 - field.trick_room_turns);
    }
  }
  if (field.gravity_turns > 0) {
    battle.field.addPseudoWeather('gravity', source);
    if (battle.field.pseudoWeather['gravity']) {
      battle.field.pseudoWeather['gravity'].duration = clampDuration(5 - field.gravity_turns);
    }
  }
  applySideConditions(battle.p1, field.my_side);
  applySideConditions(battle.p2, field.opp_side);
}

function exportMoves(p) {
  // Pokemon.getMoveRequestData() is the SAME call the engine's own request
  // generation uses - not a reimplementation. It narrows `moves` to a
  // single synthetic entry ({id:'recharge'} or {id:'struggle'}) or a
  // single real entry (a two-turn move like Solar Beam mid-charge) when
  // the mon has no free choice, instead of the normal 4-move list with
  // per-move `disabled` flags. Real pp/maxpp aren't included on locked/
  // synthetic entries (they're not being spent from a normal moveslot),
  // so those fall back to a placeholder of 1 - just needs to be nonzero
  // so the pp<=0 filter in propose_slot_actions doesn't wrongly drop the
  // only legal action.
  const req = p.getMoveRequestData();
  // p.trapped (NOT req.trapped) for the trapped flag: getMoveRequestData()
  // deliberately HIDES trapped-status from the exported request when the
  // cause is an undiscovered ability (Shadow Tag/Arena Trap) - it sets
  // p.trapped to the string 'hidden' rather than true, and its own export
  // logic uses a strict `=== true` check that excludes it, matching what
  // a real player genuinely wouldn't be told yet. That's correct for the
  // live protocol (poke-env's battle.trapped mirrors it) but wrong here:
  // search reasons inside an already-fully-determinized world, so there's
  // no information left to hide from ourselves. Confirmed via a
  // standalone diagnostic against the real engine (not guessed): the
  // ability/event system itself was never broken, only this one read.
  return {
    moves: req.moves.map(m => {
      const real = p.moveSlots.find(ms => ms.id === m.id);
      return {
        move: m.id,
        pp: real ? real.pp : 1,
        max_pp: real ? real.maxpp : 1,
        disabled: !!m.disabled,
      };
    }),
    trapped: !!p.trapped,
  };
}

function exportMon(p, side) {
  const activeIdx = side.active.indexOf(p);
  const position = activeIdx === 0 ? 'left' : activeIdx === 1 ? 'right' : null;
  const boosts = {
    atk: p.boosts.atk, defense: p.boosts.def, spa: p.boosts.spa, spd: p.boosts.spd,
    spe: p.boosts.spe, acc: p.boosts.accuracy, eva: p.boosts.evasion,
  };
  const stats = {};
  for (const s of STATS) stats[s] = p.storedStats[s];
  const { moves, trapped } = exportMoves(p);
  return {
    species: p.species.id,
    level: p.level,
    position: p.fainted ? null : position,
    fainted: !!p.fainted,
    hp: p.hp,
    max_hp: p.maxhp,
    status: (p.status && p.status !== 'fnt') ? p.status : 'none', // fnt is carried by `fainted`, not a schema Status
    status_turns: (p.statusState && p.statusState.time) || null,
    stats,
    boosts,
    ability: p.ability,
    item: p.item || null,
    moves,
    mega_activated: !!p.species.isMega,
    volatiles: Object.keys(p.volatiles).map(name => ({ name })),
    trapped,
  };
}

function conditionDuration(sc, id) {
  return (sc[id] && sc[id].duration) || 0;
}

function exportSide(side) {
  const sc = side.sideConditions;
  const out = {
    stealth_rock: !!sc.stealthrock,
    spikes_layers: (sc.spikes && sc.spikes.layers) || 0,
    toxic_spikes_layers: (sc.toxicspikes && sc.toxicspikes.layers) || 0,
    sticky_web: !!sc.stickyweb,
    // "already used" is set explicitly at init (side.initialMegaUsed) and
    // otherwise detected by species.isMega, which is permanent once a mega
    // evolution actually happens (even after the mon later faints, per the
    // champions mod's formeChange override) - NOT by scanning canMegaEvo,
    // which is contaminated by per-world item-holding uncertainty (see
    // applySideConditions above).
    mega_used: !!side.initialMegaUsed || side.pokemon.some(p => !!p.species.isMega),
    tera_used: false,
  };
  for (const [schemaKey, id] of TIMED_SIDE_CONDITIONS.map(([k, i]) => [k, i])) {
    out[schemaKey] = conditionDuration(sc, id);
  }
  return out;
}

function exportState(battle) {
  const f = battle.field;
  return {
    turn: battle.turn,
    field: {
      weather: ENGINE_TO_WEATHER[f.weather] || 'none',
      weather_turns: (f.weatherState && f.weatherState.duration) || 0,
      terrain: ENGINE_TO_TERRAIN[f.terrain] || 'none',
      terrain_turns: (f.terrainState && f.terrainState.duration) || 0,
      trick_room_turns: (f.pseudoWeather['trickroom'] && f.pseudoWeather['trickroom'].duration) || 0,
      gravity_turns: (f.pseudoWeather['gravity'] && f.pseudoWeather['gravity'].duration) || 0,
      my_side: exportSide(battle.p1),
      opp_side: exportSide(battle.p2),
    },
    my_team: battle.p1.pokemon.map(p => exportMon(p, battle.p1)),
    opp_team: battle.p2.pokemon.map(p => exportMon(p, battle.p2)),
  };
}

function store(battle) {
  const handle = nextHandle++;
  snapshots.set(handle, JSON.stringify(battle.toJSON()));
  return handle;
}

function resolveForcedSwitches(battle) {
  // A mon fainted mid-turn: the engine wants replacements before the next
  // full turn. Default choice = first available switch-in (the V1 in-search
  // heuristic; the live game solves these as their own decision instead).
  let guard = 0;
  while (!battle.ended && battle.requestState === 'switch' && guard++ < 12) {
    battle.makeChoices();
  }
}

function opInit(req) {
  const format = Dex.formats.get(req.format, true);
  const dex = Dex.forFormat(format);
  const battle = new Battle({
    formatid: format.id,
    strictChoices: false,
    debug: false,
    p1: { name: 'me', team: req.state.my_team.map(m => buildSet(m, dex)) },
    p2: { name: 'opp', team: req.state.opp_team.map(m => buildSet(m, dex)) },
  });
  if (battle.requestState === 'teampreview') {
    const order = n => 'team ' + '123456'.slice(0, n);
    battle.makeChoices(order(req.state.my_team.length), order(req.state.opp_team.length));
  }
  battle.turn = req.state.turn;
  req.state.my_team.forEach((mon, i) => applyMonState(battle.p1.pokemon[i], mon));
  req.state.opp_team.forEach((mon, i) => applyMonState(battle.p2.pokemon[i], mon));
  applyField(battle, req.state.field);
  return { handle: store(battle), state: exportState(battle) };
}

function opInitTeamPreview(req) {
  // A genuinely fresh battle for the team-preview decision itself - NOT a
  // mid-battle reconstruction (that's opInit: auto-answers team preview
  // with everyone in submitted order, then hand-mutates turn/hp/status/
  // boosts to match an already-in-progress position). Here nothing is
  // mutated or recomputed: req.state.my_team/opp_team are the full 6-mon
  // rosters (schema/full_info_state.py's TeamPreviewRootState), buildSet
  // is reused unchanged (already generic over roster size/position), and
  // the battle is returned exactly where `new Battle(...)` naturally
  // leaves it - paused at requestState 'teampreview' - so the caller can
  // branch multiple different bring/lead choices off the same snapshot
  // via the existing step op.
  const format = Dex.formats.get(req.format, true);
  const dex = Dex.forFormat(format);
  const battle = new Battle({
    formatid: format.id,
    strictChoices: false,
    debug: false,
    p1: { name: 'me', team: req.state.my_team.map(m => buildSet(m, dex)) },
    p2: { name: 'opp', team: req.state.opp_team.map(m => buildSet(m, dex)) },
  });
  return { handle: store(battle) };
}

function opStep(req) {
  const serialized = snapshots.get(req.handle);
  if (!serialized) throw new Error(`unknown handle ${req.handle}`);
  const battle = Battle.fromJSON(serialized);
  battle.resetRNG(PRNG.generateSeed());

  const errors = [];
  if (!battle.p1.choose(req.my)) {
    errors.push(`p1 "${req.my}": ${(battle.p1.choice && battle.p1.choice.error) || 'invalid'}`);
  }
  if (!battle.p2.choose(req.opp)) {
    errors.push(`p2 "${req.opp}": ${(battle.p2.choice && battle.p2.choice.error) || 'invalid'}`);
  }
  battle.makeChoices(); // auto-completes any failed side, then commits
  resolveForcedSwitches(battle);

  const out = { state: exportState(battle), errors };
  if (battle.ended) {
    out.terminal = battle.winner === 'me' ? 1 : battle.winner === 'opp' ? -1 : 0;
  } else {
    out.handle = store(battle);
  }
  return out;
}

const rl = readline.createInterface({ input: process.stdin, crlfDelay: Infinity });
rl.on('line', line => {
  if (!line.trim()) return;
  let req;
  try {
    req = JSON.parse(line);
  } catch {
    return;
  }
  let resp;
  try {
    if (req.op === 'init') resp = opInit(req);
    else if (req.op === 'init_team_preview') resp = opInitTeamPreview(req);
    else if (req.op === 'step') resp = opStep(req);
    else if (req.op === 'free') { for (const h of req.handles) snapshots.delete(h); resp = {}; }
    else if (req.op === 'ping') resp = { snapshots: snapshots.size };
    else throw new Error(`unknown op ${req.op}`);
    resp.ok = true;
  } catch (err) {
    resp = { ok: false, error: err.stack || String(err) };
  }
  resp.id = req.id;
  process.stdout.write(JSON.stringify(resp) + '\n');
});
