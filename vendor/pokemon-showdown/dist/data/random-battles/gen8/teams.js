"use strict";
var __defProp = Object.defineProperty;
var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
var __getOwnPropNames = Object.getOwnPropertyNames;
var __hasOwnProp = Object.prototype.hasOwnProperty;
var __export = (target, all) => {
  for (var name in all)
    __defProp(target, name, { get: all[name], enumerable: true });
};
var __copyProps = (to, from, except, desc) => {
  if (from && typeof from === "object" || typeof from === "function") {
    for (let key of __getOwnPropNames(from))
      if (!__hasOwnProp.call(to, key) && key !== except)
        __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
  }
  return to;
};
var __toCommonJS = (mod) => __copyProps(__defProp({}, "__esModule", { value: true }), mod);
var teams_exports = {};
__export(teams_exports, {
  RandomGen8Teams: () => RandomGen8Teams,
  default: () => teams_default
});
module.exports = __toCommonJS(teams_exports);
var import_teams = require("../gen9/teams");
var import_dex = require("../../../sim/dex");
const RECOVERY_MOVES = [
  "healorder",
  "milkdrink",
  "moonlight",
  "morningsun",
  "recover",
  "recycle",
  "roost",
  "shoreup",
  "slackoff",
  "softboiled",
  "strengthsap",
  "synthesis"
];
const PHYSICAL_SETUP = [
  "bellydrum",
  "bulkup",
  "coil",
  "curse",
  "dragondance",
  "honeclaws",
  "howl",
  "meditate",
  "poweruppunch",
  "swordsdance"
];
const SPEED_SETUP = [
  "agility",
  "autotomize",
  "flamecharge",
  "rockpolish"
];
const SETUP = [
  "acidarmor",
  "agility",
  "autotomize",
  "bellydrum",
  "bulkup",
  "calmmind",
  "clangoroussoul",
  "coil",
  "cosmicpower",
  "curse",
  "dragondance",
  "flamecharge",
  "growth",
  "honeclaws",
  "howl",
  "irondefense",
  "meditate",
  "meteorbeam",
  "nastyplot",
  "noretreat",
  "poweruppunch",
  "quiverdance",
  "raindance",
  "rockpolish",
  "shellsmash",
  "shiftgear",
  "swordsdance",
  "tailglow",
  "workup"
];
const NO_STAB = [
  "acidspray",
  "accelerock",
  "aquajet",
  "breakingswipe",
  "bulletpunch",
  "chatter",
  "clearsmog",
  "covet",
  "dragontail",
  "doomdesire",
  "electroweb",
  "eruption",
  "explosion",
  "fakeout",
  "feint",
  "flamecharge",
  "flipturn",
  "futuresight",
  "grassyglide",
  "iceshard",
  "icywind",
  "incinerate",
  "infestation",
  "machpunch",
  "meteorbeam",
  "nuzzle",
  "pluck",
  "pursuit",
  "quickattack",
  "rapidspin",
  "reversal",
  "selfdestruct",
  "shadowsneak",
  "skydrop",
  "snarl",
  "strugglebug",
  "suckerpunch",
  "uturn",
  "vacuumwave",
  "voltswitch",
  "watershuriken",
  "waterspout"
];
const HAZARDS = [
  "spikes",
  "stealthrock",
  "stickyweb",
  "toxicspikes"
];
const PROTECT_MOVES = [
  "banefulbunker",
  "kingsshield",
  "protect",
  "spikyshield"
];
const PIVOT_MOVES = [
  "flipturn",
  "partingshot",
  "teleport",
  "uturn",
  "voltswitch"
];
const MOVE_PAIRS = [
  ["lightscreen", "reflect"],
  ["sleeptalk", "rest"],
  ["protect", "wish"],
  ["spikyshield", "wish"],
  ["leechseed", "substitute"],
  ["focuspunch", "substitute"]
];
const PRIORITY_POKEMON = [
  "aegislash",
  "doublade",
  "golisopod",
  "mimikyu",
  "scizor"
];
class RandomGen8Teams extends import_teams.RandomTeams {
  constructor(format, prng) {
    super(format, prng);
    this.randomSets = require("./sets.json");
    this.randomCAP1v1Sets = require("./cap-1v1-sets.json");
    this.randomOldGenFactorySets = require("./factory-sets.json");
    this.randomBSSFactorySets = require("./bss-factory-sets.json");
    this.noStab = NO_STAB;
    this.priorityPokemon = PRIORITY_POKEMON;
    this.moveEnforcementCheckers = {
      Bug: (movePool, moves, abilities, types, counter) => movePool.includes("megahorn") || !counter.get("Bug") && (types.has("Electric") || types.has("Psychic")),
      Dark: (movePool, moves, abilities, types, counter) => !counter.get("Dark"),
      Dragon: (movePool, moves, abilities, types, counter) => !counter.get("Dragon"),
      Electric: (movePool, moves, abilities, types, counter) => !counter.get("Electric"),
      Fairy: (movePool, moves, abilities, types, counter) => !counter.get("Fairy"),
      Fighting: (movePool, moves, abilities, types, counter) => !counter.get("Fighting"),
      Fire: (movePool, moves, abilities, types, counter) => !counter.get("Fire"),
      Flying: (movePool, moves, abilities, types, counter, species) => !counter.get("Flying"),
      Ghost: (movePool, moves, abilities, types, counter) => !counter.get("Ghost"),
      Grass: (movePool, moves, abilities, types, counter, species) => !counter.get("Grass") && (species.baseStats.atk >= 100 || movePool.includes("leafstorm") || types.has("Ghost")),
      Ground: (movePool, moves, abilities, types, counter) => !counter.get("Ground"),
      Ice: (movePool, moves, abilities, types, counter) => !counter.get("Ice"),
      Normal: (movePool, moves, abilities, types, counter) => movePool.includes("hypervoice") || !counter.get("Normal") && types.has("Ground"),
      Poison: (movePool, moves, abilities, types, counter) => !counter.get("Poison"),
      Psychic: (movePool, moves, abilities, types, counter) => !counter.get("Psychic") && (movePool.includes("calmmind") || ["Bug", "Electric", "Fairy", "Fighting", "Flying", "Poison"].some((t) => types.has(t))),
      Rock: (movePool, moves, abilities, types, counter, species) => !counter.get("Rock") && species.baseStats.atk >= 80,
      Steel: (movePool, moves, abilities, types, counter, species) => !counter.get("Steel") && species.baseStats.atk >= 100,
      Water: (movePool, moves, abilities, types, counter) => !counter.get("Water")
    };
    this.cachedStatusMoves = this.dex.moves.all().filter((move) => move.category === "Status" && move.id !== "naturepower").map((move) => move.id);
  }
  cullMovePool(types, moves, abilities, counter, movePool, teamDetails, species, isLead, preferredType, role) {
    let hasHiddenPower = false;
    for (const move of moves) {
      if (move.startsWith("hiddenpower")) hasHiddenPower = true;
    }
    if (hasHiddenPower) {
      let movePoolHasHiddenPower = true;
      while (movePoolHasHiddenPower) {
        movePoolHasHiddenPower = false;
        for (const moveid of movePool) {
          if (moveid.startsWith("hiddenpower")) {
            this.fastPop(movePool, movePool.indexOf(moveid));
            movePoolHasHiddenPower = true;
            break;
          }
        }
      }
    }
    if (moves.size + movePool.length <= this.maxMoveCount) return;
    if (moves.size === this.maxMoveCount - 2) {
      const unpairedMoves = [...movePool];
      for (const pair of MOVE_PAIRS) {
        if (movePool.includes(pair[0]) && movePool.includes(pair[1])) {
          this.fastPop(unpairedMoves, unpairedMoves.indexOf(pair[0]));
          this.fastPop(unpairedMoves, unpairedMoves.indexOf(pair[1]));
        }
      }
      if (unpairedMoves.length === 1) {
        this.fastPop(movePool, movePool.indexOf(unpairedMoves[0]));
      }
    }
    if (moves.size === this.maxMoveCount - 1) {
      for (const pair of MOVE_PAIRS) {
        if (movePool.includes(pair[0]) && movePool.includes(pair[1])) {
          this.fastPop(movePool, movePool.indexOf(pair[0]));
          this.fastPop(movePool, movePool.indexOf(pair[1]));
        }
      }
    }
    if (teamDetails.screens && movePool.length >= this.maxMoveCount + 2) {
      if (movePool.includes("reflect")) this.fastPop(movePool, movePool.indexOf("reflect"));
      if (movePool.includes("lightscreen")) this.fastPop(movePool, movePool.indexOf("lightscreen"));
      if (moves.size + movePool.length <= this.maxMoveCount) return;
    }
    if (teamDetails.stickyWeb) {
      if (movePool.includes("stickyweb")) this.fastPop(movePool, movePool.indexOf("stickyweb"));
      if (moves.size + movePool.length <= this.maxMoveCount) return;
    }
    if (teamDetails.stealthRock) {
      if (movePool.includes("stealthrock")) this.fastPop(movePool, movePool.indexOf("stealthrock"));
      if (moves.size + movePool.length <= this.maxMoveCount) return;
    }
    if (teamDetails.defog || teamDetails.rapidSpin) {
      if (movePool.includes("defog")) this.fastPop(movePool, movePool.indexOf("defog"));
      if (movePool.includes("rapidspin")) this.fastPop(movePool, movePool.indexOf("rapidspin"));
      if (moves.size + movePool.length <= this.maxMoveCount) return;
    }
    if (teamDetails.toxicSpikes) {
      if (movePool.includes("toxicspikes")) this.fastPop(movePool, movePool.indexOf("toxicspikes"));
      if (moves.size + movePool.length <= this.maxMoveCount) return;
    }
    if (teamDetails.spikes && teamDetails.spikes >= 2) {
      if (movePool.includes("spikes")) this.fastPop(movePool, movePool.indexOf("spikes"));
      if (moves.size + movePool.length <= this.maxMoveCount) return;
    }
    if (teamDetails.statusCure) {
      if (movePool.includes("aromatherapy")) this.fastPop(movePool, movePool.indexOf("aromatherapy"));
      if (movePool.includes("healbell")) this.fastPop(movePool, movePool.indexOf("healbell"));
      if (moves.size + movePool.length <= this.maxMoveCount) return;
    }
    const statusMoves = this.cachedStatusMoves;
    const statusInflictingMoves = ["nuzzle", "thunderwave", "toxic", "willowisp", "yawn"];
    const incompatiblePairs = [
      // These moves don't mesh well with other aspects of the set
      [statusMoves, ["healingwish", "switcheroo", "trick"]],
      [PIVOT_MOVES, PIVOT_MOVES],
      [SETUP, PIVOT_MOVES],
      [SETUP, HAZARDS],
      [SETUP, ["defog", "haze", "toxic"]],
      [PHYSICAL_SETUP, PHYSICAL_SETUP],
      [SPEED_SETUP, "quickattack"],
      ["curse", ["irondefense", "rapidspin"]],
      ["defog", HAZARDS],
      ["uturn", "trick"],
      ["substitute", PIVOT_MOVES],
      // These attacks are redundant with each other
      ["psychic", "psyshock"],
      [["scald", "surf"], ["hydropump", "originpulse"]],
      [["flamethrower", "lavaplume"], ["fireblast", "magmastorm", "overheat"]],
      ["hornleech", "woodhammer"],
      ["gigadrain", "leafstorm"],
      ["airslash", "hurricane"],
      ["thunderbolt", "discharge"],
      ["dracometeor", "dragonpulse"],
      ["dragonclaw", "outrage"],
      // Status move incompatibilities
      ["taunt", "encore"],
      [statusInflictingMoves, "toxicspikes"],
      // Assorted hardcodes go here:
      // Jirachi
      ["bodyslam", "healingwish"],
      // Druddigon
      ["glare", "suckerpunch"],
      // Zapdos-Galar
      ["stompingtantrum", "throatchop"]
    ];
    for (const pair of incompatiblePairs) this.incompatibleMoves(moves, movePool, pair[0], pair[1]);
    if (!types.has("Dark") && preferredType !== "Dark") {
      this.incompatibleMoves(moves, movePool, "knockoff", "suckerpunch");
    }
    if (role !== "Staller") {
      this.incompatibleMoves(moves, movePool, statusInflictingMoves, statusInflictingMoves);
    }
    if (species.id === "corsolagalar") this.incompatibleMoves(moves, movePool, "haze", "stealthrock");
  }
  // Generate random moveset for a given species, role, preferred type.
  randomMoveset(types, abilities, teamDetails, species, isLead, movePool, preferredType, role) {
    const moves = /* @__PURE__ */ new Set();
    let counter = this.queryMoves(moves, species, preferredType, abilities);
    this.cullMovePool(
      types,
      moves,
      abilities,
      counter,
      movePool,
      teamDetails,
      species,
      isLead,
      preferredType,
      role
    );
    if (movePool.length <= this.maxMoveCount) {
      while (movePool.length) {
        const moveid = this.sample(movePool);
        counter = this.addMove(
          moveid,
          moves,
          types,
          abilities,
          teamDetails,
          species,
          isLead,
          movePool,
          preferredType,
          role
        );
      }
      return moves;
    }
    const runEnforcementChecker = (checkerName) => {
      if (!this.moveEnforcementCheckers[checkerName]) return false;
      return this.moveEnforcementCheckers[checkerName](
        movePool,
        moves,
        abilities,
        types,
        counter,
        species,
        teamDetails,
        isLead,
        false,
        preferredType,
        role
      );
    };
    if (species.requiredMove) {
      const move = this.dex.moves.get(species.requiredMove).id;
      counter = this.addMove(
        move,
        moves,
        types,
        abilities,
        teamDetails,
        species,
        isLead,
        movePool,
        preferredType,
        role
      );
    }
    if (movePool.includes("facade") && abilities.includes("Guts")) {
      counter = this.addMove(
        "facade",
        moves,
        types,
        abilities,
        teamDetails,
        species,
        isLead,
        movePool,
        preferredType,
        role
      );
    }
    for (const moveid of ["auroraveil", "blizzard", "nightshade", "seismictoss", "spore", "stickyweb"]) {
      if (movePool.includes(moveid)) {
        counter = this.addMove(
          moveid,
          moves,
          types,
          abilities,
          teamDetails,
          species,
          isLead,
          movePool,
          preferredType,
          role
        );
      }
    }
    if (role === "Bulky Support" && !teamDetails.defog && !teamDetails.rapidSpin) {
      if (movePool.includes("rapidspin")) {
        counter = this.addMove(
          "rapidspin",
          moves,
          types,
          abilities,
          teamDetails,
          species,
          isLead,
          movePool,
          preferredType,
          role
        );
      }
      if (movePool.includes("defog")) {
        counter = this.addMove(
          "defog",
          moves,
          types,
          abilities,
          teamDetails,
          species,
          isLead,
          movePool,
          preferredType,
          role
        );
      }
    }
    if (types.size === 1 && (types.has("Normal") || types.has("Fighting"))) {
      if (movePool.includes("knockoff")) {
        counter = this.addMove(
          "knockoff",
          moves,
          types,
          abilities,
          teamDetails,
          species,
          isLead,
          movePool,
          preferredType,
          role
        );
      }
    }
    if (movePool.includes("acidarmor") || movePool.includes("irondefense")) {
      if (movePool.includes("bodypress")) {
        counter = this.addMove(
          "bodypress",
          moves,
          types,
          abilities,
          teamDetails,
          species,
          isLead,
          movePool,
          preferredType,
          role
        );
      }
    }
    if (["Bulky Attacker", "Wallbreaker"].includes(role) || this.priorityPokemon.includes(species.id)) {
      const priorityMoves = [];
      for (const moveid of movePool) {
        const move = this.dex.moves.get(moveid);
        const moveType = this.getMoveType(move, species, abilities, preferredType);
        if (types.has(moveType) && move.priority > 0 && (move.basePower || move.basePowerCallback)) {
          priorityMoves.push(moveid);
        }
      }
      if (priorityMoves.length) {
        const moveid = this.sample(priorityMoves);
        counter = this.addMove(
          moveid,
          moves,
          types,
          abilities,
          teamDetails,
          species,
          isLead,
          movePool,
          preferredType,
          role
        );
      }
    }
    for (const type of types) {
      const stabMoves = [];
      for (const moveid of movePool) {
        const move = this.dex.moves.get(moveid);
        const moveType = this.getMoveType(move, species, abilities, preferredType);
        if (!this.noStab.includes(moveid) && (move.basePower || move.basePowerCallback) && type === moveType) {
          stabMoves.push(moveid);
        }
      }
      while (runEnforcementChecker(type)) {
        if (!stabMoves.length) break;
        const moveid = this.sampleNoReplace(stabMoves);
        counter = this.addMove(
          moveid,
          moves,
          types,
          abilities,
          teamDetails,
          species,
          isLead,
          movePool,
          preferredType,
          role
        );
      }
    }
    if (!counter.get(preferredType)) {
      const stabMoves = [];
      for (const moveid of movePool) {
        const move = this.dex.moves.get(moveid);
        const moveType = this.getMoveType(move, species, abilities, preferredType);
        if (!this.noStab.includes(moveid) && (move.basePower || move.basePowerCallback) && preferredType === moveType) {
          stabMoves.push(moveid);
        }
      }
      if (stabMoves.length) {
        const moveid = this.sample(stabMoves);
        counter = this.addMove(
          moveid,
          moves,
          types,
          abilities,
          teamDetails,
          species,
          isLead,
          movePool,
          preferredType,
          role
        );
      }
    }
    if (!counter.get("stab")) {
      const stabMoves = [];
      for (const moveid of movePool) {
        const move = this.dex.moves.get(moveid);
        const moveType = this.getMoveType(move, species, abilities, preferredType);
        if (!this.noStab.includes(moveid) && (move.basePower || move.basePowerCallback) && types.has(moveType)) {
          stabMoves.push(moveid);
        }
      }
      if (stabMoves.length) {
        const moveid = this.sample(stabMoves);
        counter = this.addMove(
          moveid,
          moves,
          types,
          abilities,
          teamDetails,
          species,
          isLead,
          movePool,
          preferredType,
          role
        );
      }
    }
    if (["Bulky Support", "Bulky Attacker", "Bulky Setup", "Staller"].includes(role)) {
      const recoveryMoves = movePool.filter((moveid) => RECOVERY_MOVES.includes(moveid));
      if (recoveryMoves.length) {
        const moveid = this.sample(recoveryMoves);
        counter = this.addMove(
          moveid,
          moves,
          types,
          abilities,
          teamDetails,
          species,
          isLead,
          movePool,
          preferredType,
          role
        );
      }
    }
    if (role === "Staller") {
      const enforcedMoves = [...PROTECT_MOVES, "toxic"];
      for (const move of enforcedMoves) {
        if (movePool.includes(move)) {
          counter = this.addMove(
            move,
            moves,
            types,
            abilities,
            teamDetails,
            species,
            isLead,
            movePool,
            preferredType,
            role
          );
        }
      }
    }
    if (role === "AV Pivot") {
      const pivotMoves = movePool.filter((moveid) => ["uturn", "voltswitch"].includes(moveid));
      if (pivotMoves.length) {
        const moveid = this.sample(pivotMoves);
        counter = this.addMove(
          moveid,
          moves,
          types,
          abilities,
          teamDetails,
          species,
          isLead,
          movePool,
          preferredType,
          role
        );
      }
    }
    if (role.includes("Setup") || role === "Dynamax User") {
      const nonSpeedSetupMoves = movePool.filter((moveid) => SETUP.includes(moveid) && !SPEED_SETUP.includes(moveid));
      if (nonSpeedSetupMoves.length) {
        const moveid = this.sample(nonSpeedSetupMoves);
        counter = this.addMove(
          moveid,
          moves,
          types,
          abilities,
          teamDetails,
          species,
          isLead,
          movePool,
          preferredType,
          role
        );
      } else {
        const setupMoves = movePool.filter((moveid) => SETUP.includes(moveid));
        if (setupMoves.length) {
          const moveid = this.sample(setupMoves);
          counter = this.addMove(
            moveid,
            moves,
            types,
            abilities,
            teamDetails,
            species,
            isLead,
            movePool,
            preferredType,
            role
          );
        }
      }
    }
    if (role === "Dynamax User") {
      if (!counter.get("Fighting")) {
        const fightingMoves = [];
        for (const moveid of movePool) {
          const move = this.dex.moves.get(moveid);
          const moveType = this.getMoveType(move, species, abilities, preferredType);
          if (!this.noStab.includes(moveid) && (move.basePower || move.basePowerCallback) && moveType === "Fighting") {
            fightingMoves.push(moveid);
          }
        }
        if (fightingMoves.length) {
          const moveid = this.sample(fightingMoves);
          counter = this.addMove(
            moveid,
            moves,
            types,
            abilities,
            teamDetails,
            species,
            isLead,
            movePool,
            preferredType,
            role
          );
        }
      }
      if (!counter.get("Flying")) {
        const flyingMoves = [];
        for (const moveid of movePool) {
          const move = this.dex.moves.get(moveid);
          const moveType = this.getMoveType(move, species, abilities, preferredType);
          if (!this.noStab.includes(moveid) && (move.basePower || move.basePowerCallback) && moveType === "Flying") {
            flyingMoves.push(moveid);
          }
        }
        if (flyingMoves.length) {
          const moveid = this.sample(flyingMoves);
          counter = this.addMove(
            moveid,
            moves,
            types,
            abilities,
            teamDetails,
            species,
            isLead,
            movePool,
            preferredType,
            role
          );
        }
      }
    }
    if (!counter.damagingMoves.size) {
      const attackingMoves = [];
      for (const moveid of movePool) {
        const move = this.dex.moves.get(moveid);
        if (!this.noStab.includes(moveid) && move.category !== "Status") attackingMoves.push(moveid);
      }
      if (attackingMoves.length) {
        const moveid = this.sample(attackingMoves);
        counter = this.addMove(
          moveid,
          moves,
          types,
          abilities,
          teamDetails,
          species,
          isLead,
          movePool,
          preferredType,
          role
        );
      }
    }
    if (["Fast Attacker", "Setup Sweeper", "Bulky Attacker", "Wallbreaker", "Dynamax User"].includes(role)) {
      if (counter.damagingMoves.size === 1) {
        const currentAttackType = counter.damagingMoves.values().next().value.type;
        const coverageMoves = [];
        for (const moveid of movePool) {
          const move = this.dex.moves.get(moveid);
          const moveType = this.getMoveType(move, species, abilities, preferredType);
          if (!this.noStab.includes(moveid) && (move.basePower || move.basePowerCallback)) {
            if (currentAttackType !== moveType) coverageMoves.push(moveid);
          }
        }
        if (coverageMoves.length) {
          const moveid = this.sample(coverageMoves);
          counter = this.addMove(
            moveid,
            moves,
            types,
            abilities,
            teamDetails,
            species,
            isLead,
            movePool,
            preferredType,
            role
          );
        }
      }
    }
    while (moves.size < this.maxMoveCount && movePool.length) {
      const moveid = this.sample(movePool);
      counter = this.addMove(
        moveid,
        moves,
        types,
        abilities,
        teamDetails,
        species,
        isLead,
        movePool,
        preferredType,
        role
      );
      for (const pair of MOVE_PAIRS) {
        if (moveid === pair[0] && movePool.includes(pair[1])) {
          counter = this.addMove(
            pair[1],
            moves,
            types,
            abilities,
            teamDetails,
            species,
            isLead,
            movePool,
            preferredType,
            role
          );
        }
        if (moveid === pair[1] && movePool.includes(pair[0])) {
          counter = this.addMove(
            pair[0],
            moves,
            types,
            abilities,
            teamDetails,
            species,
            isLead,
            movePool,
            preferredType,
            role
          );
        }
      }
    }
    return moves;
  }
  shouldCullAbility(ability, types, moves, abilities, counter, teamDetails, species) {
    switch (ability) {
      case "Prankster":
        return !counter.get("Status");
      case "Rock Head":
        return !counter.get("recoil");
      case "Swarm":
        return !counter.get("Bug");
    }
    return false;
  }
  getAbility(types, moves, abilities, counter, teamDetails, species) {
    if (abilities.length <= 1) return abilities[0];
    if (species.baseSpecies === "Venusaur") return counter.get("Grass") ? "Overgrow" : "Chlorophyll";
    if (["tornadus", "thundurus"].includes(species.id) && (counter.get("Status") || !counter.get("Physical"))) {
      return "Prankster";
    }
    if (species.id === "marowak" && counter.get("recoil")) return "Rock Head";
    if (species.id === "clefable" && moves.has("teleport")) return "Magic Guard";
    const abilityAllowed = [];
    for (const ability of abilities) {
      if (!this.shouldCullAbility(ability, types, moves, abilities, counter, teamDetails, species)) {
        abilityAllowed.push(ability);
      }
    }
    if (abilityAllowed.length >= 1) return this.sample(abilityAllowed);
    return this.sample(abilities);
  }
  getPriorityItem(ability, types, moves, counter, teamDetails, species, isLead, preferredType, role) {
    if (species.requiredItems) return this.sample(species.requiredItems);
    if (species.id === "pikachu") return "Light Ball";
    if (species.id === "pheromosa") return "Life Orb";
    if (role === "AV Pivot") return "Assault Vest";
    if (species.id === "regieleki") return "Magnet";
    if (["farfetchd", "sirfetchd"].includes(species.id)) return "Leek";
    if (species.baseSpecies === "Marowak") return "Thick Club";
    if (species.id === "unfezant" || moves.has("focusenergy")) return "Scope Lens";
    if (species.id === "wobbuffet") return "Custap Berry";
    if (ability === "Harvest" || ability === "Cheek Pouch") return "Sitrus Berry";
    if (species.id === "ditto" || species.id === "magnezone" && role === "Fast Attacker") return "Choice Scarf";
    if (species.id === "froslass") return "Wide Lens";
    if (ability === "Speed Boost") return "Life Orb";
    if (types.has("Normal") && counter.get("Normal") && moves.has("fakeout")) return "Silk Scarf";
    if (moves.has("clangoroussoul") || species.id === "toxtricity" && moves.has("shiftgear")) return "Throat Spray";
    if (species.id === "palkia" && counter.get("Status")) return "Lustrous Orb";
    if (species.id === "xurkitree" && moves.has("hypnosis")) return "Blunder Policy";
    if (["healingwish", "switcheroo", "trick"].some((m) => moves.has(m))) {
      if (species.baseStats.spe >= 60 && species.baseStats.spe <= 108 && role !== "Wallbreaker" && !counter.get("priority")) {
        return "Choice Scarf";
      } else {
        return counter.get("Physical") > counter.get("Special") ? "Choice Band" : "Choice Specs";
      }
    }
    if (["latias", "latios"].includes(species.id)) return "Soul Dew";
    if (moves.has("bellydrum")) {
      if (ability === "Gluttony") {
        return `${this.sample(["Aguav", "Figy", "Iapapa", "Mago", "Wiki"])} Berry`;
      } else if (moves.has("substitute")) {
        return "Salac Berry";
      } else {
        return "Sitrus Berry";
      }
    }
    if (moves.has("dragonenergy") || moves.has("waterspout")) return "Choice Scarf";
    if (moves.has("boltbeak") || moves.has("fishiousrend")) return role === "Fast Attacker" ? "Choice Scarf" : "Choice Band";
    if (moves.has("geomancy") || moves.has("meteorbeam")) return "Power Herb";
    if (moves.has("shellsmash")) return ability === "Sturdy" ? "Heavy-Duty Boots" : "White Herb";
    if (ability === "Guts" && moves.has("facade")) return types.has("Fire") ? "Toxic Orb" : "Flame Orb";
    if (ability === "Magic Guard") return moves.has("counter") ? "Focus Sash" : "Life Orb";
    if (ability === "Sheer Force" && counter.get("sheerforce")) return "Life Orb";
    if (ability === "Unburden") return moves.has("closecombat") ? "White Herb" : "Sitrus Berry";
    if (moves.has("acrobatics")) return "";
    if (moves.has("auroraveil") || moves.has("lightscreen") && moves.has("reflect")) return "Light Clay";
    if (this.dex.getEffectiveness("Rock", species) >= 2 || ability === "Multiscale") return "Heavy-Duty Boots";
    if (species.nfe) return "Eviolite";
    if (moves.has("rest") && !moves.has("sleeptalk") && !["Natural Cure", "Shed Skin"].includes(ability)) {
      return "Chesto Berry";
    }
    if (role === "Staller" && PROTECT_MOVES.some((m) => moves.has(m))) return "Leftovers";
  }
  getItem(ability, types, moves, counter, teamDetails, species, isLead, preferredType, role) {
    const lifeOrbReqs = ["flamecharge", "nuzzle", "rapidspin"].every((m) => !moves.has(m));
    const defensiveStatTotal = species.baseStats.hp + species.baseStats.def + species.baseStats.spd;
    if (species.id !== "jirachi" && counter.get("Physical") >= moves.size && ["dragontail", "fakeout", "firstimpression", "flamecharge", "nuzzle", "rapidspin"].every((m) => !moves.has(m))) {
      const scarfReqs = role !== "Wallbreaker" && (role !== "Dynamax User" || !counter.get("Flying")) && (species.baseStats.atk >= 100 || ability === "Huge Power" || ability === "Pure Power") && species.baseStats.spe >= 60 && species.baseStats.spe <= 109 && !counter.get("priority");
      return scarfReqs && this.randomChance(1, 2) ? "Choice Scarf" : "Choice Band";
    }
    if (counter.get("Special") >= moves.size || counter.get("Special") >= moves.size - 1 && ["flipturn", "uturn"].some((m) => moves.has(m))) {
      const scarfReqs = role !== "Wallbreaker" && species.baseStats.spa >= 100 && species.baseStats.spe >= 60 && species.baseStats.spe <= 108 && ability !== "Tinted Lens" && !moves.has("uturn") && !counter.get("priority");
      return scarfReqs && this.randomChance(1, 2) ? "Choice Scarf" : "Choice Specs";
    }
    if (role === "Bulky Setup" && !!counter.get("speedsetup") && counter.get("Status") <= 1) {
      return "Weakness Policy";
    }
    if (!counter.get("Status") && ["Fast Support", "Bulky Support", "Bulky Attacker"].some((m) => role === m)) {
      return "Assault Vest";
    }
    if (moves.has("substitute")) return "Leftovers";
    if (moves.has("stickyweb") && isLead && species.baseStats.hp + species.baseStats.def + species.baseStats.spd <= 235) return "Focus Sash";
    if (this.dex.getEffectiveness("Rock", species) >= 1 || species.id === "sawk" && ability === "Sturdy") return "Heavy-Duty Boots";
    if (moves.has("teleport") || role === "Fast Support" && [...PIVOT_MOVES, "defog", "rapidspin"].some((m) => moves.has(m)) && !types.has("Flying") && ability !== "Levitate") return "Heavy-Duty Boots";
    if (moves.has("dragondance") && role === "Bulky Setup") return "Weakness Policy";
    if (moves.has("outrage") && counter.get("setup")) return "Lum Berry";
    if (ability === "Rough Skin" || ability === "Regenerator" && (role === "Bulky Support" || role === "Bulky Attacker") && species.baseStats.hp + species.baseStats.def >= 180 && this.randomChance(1, 2) || ability !== "Regenerator" && !counter.get("setup") && counter.get("recovery") && this.dex.getEffectiveness("Fighting", species) < 1 && species.baseStats.hp + species.baseStats.def > 200 && this.randomChance(1, 2)) return "Rocky Helmet";
    if (["kingsshield", "protect", "spikyshield"].some((m) => moves.has(m))) return "Leftovers";
    if (["Bulky Attacker", "Bulky Support", "Bulky Setup"].some((m) => role === m)) return "Leftovers";
    if (role === "Fast Support" && isLead && defensiveStatTotal < 255 && !counter.get("recovery") && (counter.get("hazards") || counter.get("setup")) && !counter.get("recoil")) return "Focus Sash";
    if (role === "Fast Support") {
      return counter.get("Physical") + counter.get("Special") > counter.get("Status") && lifeOrbReqs ? "Life Orb" : "Leftovers";
    }
    if (lifeOrbReqs && ["Fast Attacker", "Setup Sweeper", "Wallbreaker", "Dynamax User"].some((m) => role === m)) return "Life Orb";
    return "Leftovers";
  }
  randomSet(species, teamDetails = {}, isLead = false) {
    const ruleTable = this.dex.formats.getRuleTable(this.format);
    species = this.dex.species.get(species);
    const forme = this.getForme(species);
    const gmax = species.name.endsWith("-Gmax");
    const sets = this.randomSets[species.id]["sets"];
    const possibleSets = [];
    for (const set2 of sets) {
      if (teamDetails.dynamaxUser && set2.role === "Dynamax User") continue;
      possibleSets.push(set2);
    }
    const set = this.sampleIfArray(possibleSets);
    const role = set.role;
    const movePool = [];
    for (const movename of set.movepool) {
      movePool.push(this.dex.moves.get(movename).id);
    }
    const preferredTypes = set.preferredTypes;
    const preferredType = this.sampleIfArray(preferredTypes) || "";
    let ability = "";
    let item = void 0;
    const evs = { hp: 85, atk: 85, def: 85, spa: 85, spd: 85, spe: 85 };
    const ivs = { hp: 31, atk: 31, def: 31, spa: 31, spd: 31, spe: 31 };
    const types = new Set(species.types);
    const baseAbilities = set.abilities;
    const abilities = species.battleOnly && !species.requiredAbility ? Object.values(species.abilities) : baseAbilities;
    const moves = this.randomMoveset(
      types,
      abilities,
      teamDetails,
      species,
      isLead,
      movePool,
      preferredType,
      role
    );
    const counter = this.queryMoves(moves, species, preferredType, abilities);
    ability = this.getAbility(types, moves, baseAbilities, counter, teamDetails, species);
    item = this.getPriorityItem(ability, types, moves, counter, teamDetails, species, isLead, preferredType, role);
    if (item === void 0) {
      item = this.getItem(ability, types, moves, counter, teamDetails, species, isLead, preferredType, role);
    }
    if (item === "Leftovers" && types.has("Poison")) {
      item = "Black Sludge";
    }
    const level = this.getLevel(species);
    const noAttackStatMoves = [...moves].every((m) => {
      const move = this.dex.moves.get(m);
      if (move.damageCallback || move.damage) return true;
      if (move.id === "shellsidearm") return false;
      return move.category !== "Physical" || move.id === "bodypress";
    });
    if (noAttackStatMoves && !moves.has("copycat") && !moves.has("transform") && this.format.mod !== "partnersincrime" && !ruleTable.has("forceofthefallenmod")) {
      evs.atk = 0;
      ivs.atk = 0;
    }
    if (ability === "Beast Boost" && !counter.get("Special")) {
      evs.spa = 0;
      ivs.spa = 0;
    }
    const srImmunity = ability === "Magic Guard" || item === "Heavy-Duty Boots";
    const srWeakness = srImmunity ? 0 : this.dex.getEffectiveness("Rock", species);
    while (evs.hp > 1) {
      const hp = Math.floor(Math.floor(2 * species.baseStats.hp + ivs.hp + Math.floor(evs.hp / 4) + 100) * level / 100 + 10);
      if (moves.has("substitute") && !["Black Sludge", "Leftovers"].includes(item)) {
        if (item === "Sitrus Berry" || item === "Salac Berry" || ability === "Power Construct") {
          if (hp % 4 === 0) break;
        } else {
          if (hp % 4 > 0) break;
        }
      } else if (moves.has("bellydrum") && (item === "Sitrus Berry" || ability === "Gluttony")) {
        if (hp % 2 === 0) break;
      } else if (["highjumpkick", "jumpkick"].some((m) => moves.has(m))) {
        if (hp % 2 > 0) break;
      } else {
        if (srWeakness <= 0 || ability === "Regenerator") break;
        if (srWeakness === 1 && ["Black Sludge", "Leftovers", "Life Orb"].includes(item)) break;
        if (item !== "Sitrus Berry" && hp % (4 / srWeakness) > 0) break;
        if (item === "Sitrus Berry" && hp % (4 / srWeakness) === 0) break;
      }
      evs.hp -= 4;
    }
    if (forme === "Nihilego") {
      while (evs.spd > 1) {
        const spa = Math.floor(Math.floor(2 * species.baseStats.spa + ivs.spa + Math.floor(evs.spa / 4)) * level / 100 + 5);
        const spd = Math.floor(Math.floor(2 * species.baseStats.spd + ivs.spd + Math.floor(evs.spd / 4)) * level / 100 + 5);
        if (spa >= spd) break;
        evs.spd -= 4;
      }
    }
    if (["gyroball", "metalburst", "trickroom"].some((m) => moves.has(m))) {
      evs.spe = 0;
      ivs.spe = 0;
    }
    const shuffledMoves = Array.from(moves);
    this.prng.shuffle(shuffledMoves);
    return {
      name: species.baseSpecies,
      species: forme,
      speciesId: species.id,
      gender: species.gender || (this.random(2) ? "F" : "M"),
      shiny: this.randomChance(1, 1024),
      gigantamax: gmax,
      level,
      moves: shuffledMoves,
      ability,
      evs,
      ivs,
      item,
      role
    };
  }
  /**
   * Checks if the new species is compatible with the other mons currently on the team.
   */
  getPokemonCompatibility(species, pokemon) {
    const webSetters = [
      "shuckle",
      "galvantula",
      "vikavolt",
      "ribombee",
      "araquanid",
      "orbeetle"
    ];
    const screenSetters = ["meowstic", "grimmsnarlgmax", "ninetalesalola", "abomasnow", "vanilluxe", "aurorus"];
    const noDynamaxMons = ["zacian", "zaciancrowned", "zamazenta", "zamazentacrowned", "eternatus"];
    const sunSetters = ["ninetales", "torkoal", "groudon"];
    const sandSetters = ["tyranitar", "hippowdon", "gigalith"];
    const hailSetters = ["ninetalesalola", "abomasnow", "vanilluxe", "aurorus"];
    const incompatibilityList = [
      // These Pokemon with support roles are considered too similar to each other.
      ["blissey", "chansey"],
      // These combinations are prevented to avoid double webs or screens.
      [webSetters, webSetters],
      [screenSetters, screenSetters],
      // These Pokemon are incompatible because the presence of one actively harms the other.
      // Screen Cleaner is a bad ability
      ["mrrime", screenSetters],
      // Prevent Dry Skin + sun setting ability
      [["jynx", "toxicroak", "heliolisk"], sunSetters],
      // Prevent Shedinja + sand/hail setting ability
      ["shedinja", [...sandSetters, ...hailSetters]],
      // Prevent Zoroark + Pokemon that can't dynamax
      ["zoroark", noDynamaxMons]
    ];
    for (const pair of incompatibilityList) {
      const monsArrayA = Array.isArray(pair[0]) ? pair[0] : [pair[0]];
      const monsArrayB = Array.isArray(pair[1]) ? pair[1] : [pair[1]];
      if (monsArrayB.includes(species.id)) {
        if (pokemon.some((m) => monsArrayA.includes(m.speciesId))) return false;
      }
      if (monsArrayA.includes(species.id)) {
        if (pokemon.some((m) => monsArrayB.includes(m.speciesId))) return false;
      }
    }
    return true;
  }
  randomTeam() {
    this.enforceNoDirectCustomBanlistChanges();
    const seed = this.prng.getSeed();
    const ruleTable = this.dex.formats.getRuleTable(this.format);
    const pokemon = [];
    const isMonotype = !!this.forceMonotype || ruleTable.has("sametypeclause");
    const typePool = this.dex.types.names().filter((name) => name !== "Stellar");
    const type = this.forceMonotype || this.sample(typePool);
    const baseFormes = {};
    const typeCount = {};
    const typeComboCount = {};
    const typeWeaknesses = {};
    const typeDoubleWeaknesses = {};
    const teamDetails = {};
    let numMaxLevelPokemon = 0;
    const pokemonList = Object.keys(this.randomSets);
    const [pokemonPool, baseSpeciesPool] = this.getPokemonPool(type, pokemon, isMonotype, pokemonList);
    while (baseSpeciesPool.length && pokemon.length < this.maxTeamSize) {
      const baseSpecies = this.sampleNoReplace(baseSpeciesPool);
      const species = this.dex.species.get(this.sample(pokemonPool[baseSpecies]));
      if (!species.exists) continue;
      if (baseFormes[species.baseSpecies]) continue;
      if (species.name === "Zoroark" && pokemon.length >= this.maxTeamSize - 1) continue;
      if (teamDetails.dynamaxUser && this.randomSets[species.id]["sets"].length === 1 && this.randomSets[species.id]["sets"][0]["role"] === "Dynamax User") continue;
      const types = species.types;
      const typeCombo = types.slice().sort().join();
      const weakToFreezeDry = this.dex.getEffectiveness("Ice", species) > 0 || this.dex.getEffectiveness("Ice", species) > -2 && types.includes("Water");
      const limitFactor = Math.round(this.maxTeamSize / 6) || 1;
      if (!isMonotype && !this.forceMonotype) {
        let skip = false;
        for (const typeName of types) {
          if (typeCount[typeName] >= 2 * limitFactor) {
            skip = true;
            break;
          }
        }
        if (skip) continue;
        for (const typeName of this.dex.types.names()) {
          if (this.dex.getEffectiveness(typeName, species) > 0) {
            if (!typeWeaknesses[typeName]) typeWeaknesses[typeName] = 0;
            if (typeWeaknesses[typeName] >= 3 * limitFactor) {
              skip = true;
              break;
            }
          }
          if (this.dex.getEffectiveness(typeName, species) > 1) {
            if (!typeDoubleWeaknesses[typeName]) typeDoubleWeaknesses[typeName] = 0;
            if (typeDoubleWeaknesses[typeName] >= limitFactor) {
              skip = true;
              break;
            }
          }
        }
        if (skip) continue;
        if (this.dex.getEffectiveness("Fire", species) === 0 && Object.values(species.abilities).filter((a) => ["Dry Skin", "Fluffy"].includes(a)).length) {
          if (!typeWeaknesses["Fire"]) typeWeaknesses["Fire"] = 0;
          if (typeWeaknesses["Fire"] >= 3 * limitFactor) continue;
        }
        if (weakToFreezeDry) {
          if (!typeWeaknesses["Freeze-Dry"]) typeWeaknesses["Freeze-Dry"] = 0;
          if (typeWeaknesses["Freeze-Dry"] >= 4 * limitFactor) continue;
        }
        if (!this.adjustLevel && this.getLevel(species) === 100 && numMaxLevelPokemon >= limitFactor) {
          continue;
        }
        if (!this.getPokemonCompatibility(species, pokemon)) continue;
      }
      if (!this.forceMonotype && isMonotype && typeComboCount[typeCombo] >= 3 * limitFactor) continue;
      const set = this.randomSet(
        species,
        teamDetails,
        pokemon.length === 0 && !ruleTable.has("pickedteamsize") && !ruleTable.has("teampreview")
      );
      pokemon.push(set);
      if (pokemon.length === this.maxTeamSize) break;
      baseFormes[species.baseSpecies] = 1;
      for (const typeName of types) {
        if (typeName in typeCount) {
          typeCount[typeName]++;
        } else {
          typeCount[typeName] = 1;
        }
      }
      if (typeCombo in typeComboCount) {
        typeComboCount[typeCombo]++;
      } else {
        typeComboCount[typeCombo] = 1;
      }
      for (const typeName of this.dex.types.names()) {
        if (this.dex.getEffectiveness(typeName, species) > 0) {
          typeWeaknesses[typeName]++;
        }
        if (this.dex.getEffectiveness(typeName, species) > 1) {
          typeDoubleWeaknesses[typeName]++;
        }
      }
      if (["Dry Skin", "Fluffy"].includes(set.ability) && this.dex.getEffectiveness("Fire", species) === 0) {
        typeWeaknesses["Fire"]++;
      }
      if (weakToFreezeDry) typeWeaknesses["Freeze-Dry"]++;
      if (set.level === 100) numMaxLevelPokemon++;
      if (set.moves.includes("aromatherapy") || set.moves.includes("healbell")) teamDetails.statusCure = 1;
      if (set.moves.includes("spikes")) teamDetails.spikes = (teamDetails.spikes || 0) + 1;
      if (set.moves.includes("toxicspikes")) teamDetails.toxicSpikes = 1;
      if (set.moves.includes("stealthrock")) teamDetails.stealthRock = 1;
      if (set.moves.includes("stickyweb")) teamDetails.stickyWeb = 1;
      if (set.moves.includes("defog")) teamDetails.defog = 1;
      if (set.moves.includes("rapidspin")) teamDetails.rapidSpin = 1;
      if (set.moves.includes("auroraveil") || set.moves.includes("reflect") && set.moves.includes("lightscreen")) {
        teamDetails.screens = 1;
      }
      if (set.role === "Dynamax User") teamDetails.dynamaxUser = 1;
    }
    if (pokemon.length < this.maxTeamSize && pokemon.length < 12) {
      throw new Error(`Could not build a random team for ${this.format} (seed=${seed})`);
    }
    return pokemon;
  }
  randomCAP1v1Team() {
    this.enforceNoDirectCustomBanlistChanges();
    const pokemon = [];
    const pokemonPool = Object.keys(this.randomCAP1v1Sets);
    while (pokemonPool.length && pokemon.length < this.maxTeamSize) {
      const species = this.dex.species.get(this.sampleNoReplace(pokemonPool));
      if (!species.exists) throw new Error(`Invalid Pokemon "${species}" in ${this.format}`);
      if (this.forceMonotype && !species.types.includes(this.forceMonotype)) continue;
      const setData = this.sample(this.randomCAP1v1Sets[species.name]);
      const set = {
        name: species.baseSpecies,
        species: species.name,
        gender: species.gender || (this.random(2) ? "F" : "M"),
        item: this.sampleIfArray(setData.item) || "",
        ability: this.sampleIfArray(setData.ability),
        shiny: this.randomChance(1, 1024),
        level: this.adjustLevel || 100,
        evs: { hp: 0, atk: 0, def: 0, spa: 0, spd: 0, spe: 0, ...setData.evs },
        nature: setData.nature,
        ivs: { hp: 31, atk: 31, def: 31, spa: 31, spd: 31, spe: 31, ...setData.ivs },
        moves: setData.moves.map((move) => this.sampleIfArray(move))
      };
      if (this.adjustLevel) set.level = this.adjustLevel;
      pokemon.push(set);
    }
    return pokemon;
  }
  randomFactorySet(species, teamData, tier) {
    const id = (0, import_dex.toID)(species.name);
    const setList = this.randomOldGenFactorySets[tier][id].sets;
    const itemsMax = {
      choicespecs: 1,
      choiceband: 1,
      choicescarf: 1
    };
    const movesMax = {
      rapidspin: 1,
      batonpass: 1,
      stealthrock: 1,
      defog: 1,
      spikes: 1,
      toxicspikes: 1
    };
    const requiredMoves = {
      stealthrock: "hazardSet",
      rapidspin: "hazardClear",
      defog: "hazardClear"
    };
    const weatherAbilities = ["drizzle", "drought", "snowwarning", "sandstream"];
    let effectivePool = [];
    const priorityPool = [];
    for (const curSet of setList) {
      const allowedItems = [];
      for (const itemString of curSet.item) {
        const item2 = this.dex.items.get(itemString);
        if (itemsMax[item2.id] && teamData.has[item2.id] >= itemsMax[item2.id]) continue;
        allowedItems.push(itemString);
      }
      if (allowedItems.length === 0) continue;
      const curSetItem = this.sample(allowedItems);
      const allowedAbilities = [];
      for (const abilityString of curSet.ability) {
        const ability2 = this.dex.abilities.get(abilityString);
        if (teamData.weather && weatherAbilities.includes(ability2.id)) continue;
        allowedAbilities.push(abilityString);
      }
      if (allowedAbilities.length === 0) continue;
      const curSetAbility = this.sample(allowedAbilities);
      let reject = false;
      let hasRequiredMove = false;
      const curSetVariants = [];
      for (const move of curSet.moves) {
        const variantIndex = this.random(move.length);
        const moveId = (0, import_dex.toID)(move[variantIndex]);
        if (movesMax[moveId] && teamData.has[moveId] >= movesMax[moveId]) {
          reject = true;
          break;
        }
        if (requiredMoves[moveId] && !teamData.has[requiredMoves[moveId]]) {
          hasRequiredMove = true;
        }
        curSetVariants.push(variantIndex);
      }
      if (reject) continue;
      const fullSetSpec = { set: curSet, moveVariants: curSetVariants, item: curSetItem, ability: curSetAbility };
      effectivePool.push(fullSetSpec);
      if (hasRequiredMove) priorityPool.push(fullSetSpec);
    }
    if (priorityPool.length) effectivePool = priorityPool;
    if (!effectivePool.length) {
      if (!teamData.forceResult) return null;
      for (const curSet of setList) {
        effectivePool.push({ set: curSet });
      }
    }
    const setData = this.sample(effectivePool);
    const moves = [];
    for (const [i, moveSlot] of setData.set.moves.entries()) {
      moves.push(setData.moveVariants ? moveSlot[setData.moveVariants[i]] : this.sample(moveSlot));
    }
    const item = setData.item || this.sampleIfArray(setData.set.item);
    const ability = setData.ability || this.sampleIfArray(setData.set.ability);
    const nature = this.sampleIfArray(setData.set.nature);
    const level = this.adjustLevel || setData.set.level || (tier === "LC" ? 5 : 100);
    return {
      name: setData.set.name || species.baseSpecies,
      species: setData.set.species,
      gender: setData.set.gender || species.gender || (this.randomChance(1, 2) ? "M" : "F"),
      item: item || "",
      ability: ability || species.abilities["0"],
      shiny: typeof setData.set.shiny === "undefined" ? this.randomChance(1, 1024) : setData.set.shiny,
      level,
      happiness: typeof setData.set.happiness === "undefined" ? 255 : setData.set.happiness,
      evs: { hp: 0, atk: 0, def: 0, spa: 0, spd: 0, spe: 0, ...setData.set.evs },
      ivs: { hp: 31, atk: 31, def: 31, spa: 31, spd: 31, spe: 31, ...setData.set.ivs },
      nature: nature || "Serious",
      moves
    };
  }
  randomFactoryTeam(side, depth = 0) {
    this.enforceNoDirectCustomBanlistChanges();
    const forceResult = depth >= 12;
    if (!this.factoryTier) {
      this.factoryTier = this.sample(["Uber", "OU", "UU", "RU", "NU", "PU", "LC"]);
    }
    const tierValues = {
      Uber: 5,
      OU: 4,
      UUBL: 4,
      UU: 3,
      RUBL: 3,
      RU: 2,
      NUBL: 2,
      NU: 1,
      PUBL: 1,
      PU: 0
    };
    const pokemon = [];
    const pokemonPool = Object.keys(this.randomOldGenFactorySets[this.factoryTier]);
    const teamData = {
      typeCount: {},
      typeComboCount: {},
      baseFormes: {},
      has: {},
      forceResult,
      weaknesses: {},
      resistances: {}
    };
    const requiredMoveFamilies = ["hazardSet", "hazardClear"];
    const requiredMoves = {
      stealthrock: "hazardSet",
      rapidspin: "hazardClear",
      defog: "hazardClear"
    };
    const weatherAbilitiesSet = {
      drizzle: "raindance",
      drought: "sunnyday",
      snowwarning: "hail",
      sandstream: "sandstorm"
    };
    const resistanceAbilities = {
      dryskin: ["Water"],
      waterabsorb: ["Water"],
      stormdrain: ["Water"],
      flashfire: ["Fire"],
      heatproof: ["Fire"],
      lightningrod: ["Electric"],
      motordrive: ["Electric"],
      voltabsorb: ["Electric"],
      sapsipper: ["Grass"],
      thickfat: ["Ice", "Fire"],
      levitate: ["Ground"]
    };
    while (pokemonPool.length && pokemon.length < this.maxTeamSize) {
      const species = this.dex.species.get(this.sampleNoReplace(pokemonPool));
      if (!species.exists) continue;
      if (this.factoryTier in tierValues && species.tier in tierValues && tierValues[species.tier] > tierValues[this.factoryTier]) continue;
      if (teamData.baseFormes[species.baseSpecies]) continue;
      const set = this.randomFactorySet(species, teamData, this.factoryTier);
      if (!set) continue;
      const itemData = this.dex.items.get(set.item);
      const types = species.types;
      const limitFactor = Math.round(this.maxTeamSize / 6) || 1;
      {
        let skip = false;
        for (const typeName of types) {
          if (teamData.typeCount[typeName] >= 2 * limitFactor && this.randomChance(4, 5)) {
            skip = true;
            break;
          }
        }
        if (skip) continue;
        let typeCombo2 = types.slice().sort().join();
        if (set.ability === "Drought" || set.ability === "Drizzle") {
          typeCombo2 = set.ability;
        }
        if (teamData.typeComboCount[typeCombo2] >= limitFactor) continue;
      }
      pokemon.push(set);
      const typeCombo = types.slice().sort().join();
      for (const typeName of types) {
        if (typeName in teamData.typeCount) {
          teamData.typeCount[typeName]++;
        } else {
          teamData.typeCount[typeName] = 1;
        }
      }
      teamData.typeComboCount[typeCombo] = teamData.typeComboCount[typeCombo] + 1 || 1;
      teamData.baseFormes[species.baseSpecies] = 1;
      if (itemData.id in teamData.has) {
        teamData.has[itemData.id]++;
      } else {
        teamData.has[itemData.id] = 1;
      }
      const abilityState = this.dex.abilities.get(set.ability);
      if (abilityState.id in weatherAbilitiesSet) {
        teamData.weather = weatherAbilitiesSet[abilityState.id];
      }
      for (const move of set.moves) {
        const moveId = (0, import_dex.toID)(move);
        if (moveId in teamData.has) {
          teamData.has[moveId]++;
        } else {
          teamData.has[moveId] = 1;
        }
        if (moveId in requiredMoves) {
          teamData.has[requiredMoves[moveId]] = 1;
        }
      }
      for (const typeName of this.dex.types.names()) {
        if (teamData.resistances[typeName] >= 1) continue;
        if (resistanceAbilities[abilityState.id]?.includes(typeName) || !this.dex.getImmunity(typeName, types)) {
          teamData.resistances[typeName] = (teamData.resistances[typeName] || 0) + 1;
          if (teamData.resistances[typeName] >= 1) teamData.weaknesses[typeName] = 0;
          continue;
        }
        const typeMod = this.dex.getEffectiveness(typeName, types);
        if (typeMod < 0) {
          teamData.resistances[typeName] = (teamData.resistances[typeName] || 0) + 1;
          if (teamData.resistances[typeName] >= 1) teamData.weaknesses[typeName] = 0;
        } else if (typeMod > 0) {
          teamData.weaknesses[typeName] = (teamData.weaknesses[typeName] || 0) + 1;
        }
      }
    }
    if (pokemon.length < this.maxTeamSize) return this.randomFactoryTeam(side, ++depth);
    if (!teamData.forceResult) {
      for (const requiredFamily of requiredMoveFamilies) {
        if (!teamData.has[requiredFamily]) return this.randomFactoryTeam(side, ++depth);
      }
      for (const typeName in teamData.weaknesses) {
        if (teamData.weaknesses[typeName] >= 3) return this.randomFactoryTeam(side, ++depth);
      }
    }
    return pokemon;
  }
  randomBSSFactorySet(species, teamData) {
    const id = (0, import_dex.toID)(species.name);
    const setList = this.randomBSSFactorySets[id].sets;
    const movesMax = {
      batonpass: 1,
      stealthrock: 1,
      toxicspikes: 1,
      trickroom: 1,
      auroraveil: 1
    };
    const requiredMoves = {};
    let effectivePool = [];
    const priorityPool = [];
    for (const curSet of setList) {
      let reject = false;
      let hasRequiredMove = false;
      const curSetMoveVariants = [];
      for (const move of curSet.moves) {
        const variantIndex = this.random(move.length);
        const moveId = (0, import_dex.toID)(move[variantIndex]);
        if (movesMax[moveId] && teamData.has[moveId] >= movesMax[moveId]) {
          reject = true;
          break;
        }
        if (requiredMoves[moveId] && !teamData.has[requiredMoves[moveId]]) {
          hasRequiredMove = true;
        }
        curSetMoveVariants.push(variantIndex);
      }
      if (reject) continue;
      const set = { set: curSet, moveVariants: curSetMoveVariants };
      effectivePool.push(set);
      if (hasRequiredMove) priorityPool.push(set);
    }
    if (priorityPool.length) effectivePool = priorityPool;
    if (!effectivePool.length) {
      if (!teamData.forceResult) return null;
      for (const curSet of setList) {
        effectivePool.push({ set: curSet });
      }
    }
    const setData = this.sample(effectivePool);
    const moves = [];
    for (const [i, moveSlot] of setData.set.moves.entries()) {
      moves.push(setData.moveVariants ? moveSlot[setData.moveVariants[i]] : this.sample(moveSlot));
    }
    const setDataAbility = this.sampleIfArray(setData.set.ability);
    return {
      name: setData.set.nickname || setData.set.name || species.baseSpecies,
      species: setData.set.species,
      gigantamax: setData.set.gigantamax,
      gender: setData.set.gender || species.gender || (this.randomChance(1, 2) ? "M" : "F"),
      item: this.sampleIfArray(setData.set.item) || "",
      ability: setDataAbility || species.abilities["0"],
      shiny: typeof setData.set.shiny === "undefined" ? this.randomChance(1, 1024) : setData.set.shiny,
      level: setData.set.level || 50,
      happiness: typeof setData.set.happiness === "undefined" ? 255 : setData.set.happiness,
      evs: { hp: 0, atk: 0, def: 0, spa: 0, spd: 0, spe: 0, ...setData.set.evs },
      ivs: { hp: 31, atk: 31, def: 31, spa: 31, spd: 31, spe: 31, ...setData.set.ivs },
      nature: setData.set.nature || "Serious",
      moves
    };
  }
  randomBSSFactoryTeam(side, depth = 0) {
    this.enforceNoDirectCustomBanlistChanges();
    const forceResult = depth >= 4;
    const pokemon = [];
    const pokemonPool = Object.keys(this.randomBSSFactorySets);
    const teamData = {
      typeCount: {},
      typeComboCount: {},
      baseFormes: {},
      has: {},
      forceResult,
      weaknesses: {},
      resistances: {}
    };
    const weatherAbilitiesSet = {
      drizzle: "raindance",
      drought: "sunnyday",
      snowwarning: "hail",
      sandstream: "sandstorm"
    };
    const resistanceAbilities = {
      waterabsorb: ["Water"],
      flashfire: ["Fire"],
      lightningrod: ["Electric"],
      voltabsorb: ["Electric"],
      thickfat: ["Ice", "Fire"],
      levitate: ["Ground"]
    };
    const limitFactor = Math.ceil(this.maxTeamSize / 6);
    const shuffledSpecies = [];
    for (const speciesName of pokemonPool) {
      const sortObject = {
        speciesName,
        score: this.prng.random() ** (1 / this.randomBSSFactorySets[speciesName].usage)
      };
      shuffledSpecies.push(sortObject);
    }
    shuffledSpecies.sort((a, b) => a.score - b.score);
    while (shuffledSpecies.length && pokemon.length < this.maxTeamSize) {
      const specie = shuffledSpecies.pop().speciesName;
      const species = this.dex.species.get(specie);
      if (!species.exists) continue;
      if (this.forceMonotype && !species.types.includes(this.forceMonotype)) continue;
      if (teamData.baseFormes[species.baseSpecies]) continue;
      const types = species.types;
      let skip = false;
      if (!this.forceMonotype) {
        for (const type of types) {
          if (teamData.typeCount[type] >= 2 * limitFactor && this.randomChance(4, 5)) {
            skip = true;
            break;
          }
        }
      }
      if (skip) continue;
      const set = this.randomBSSFactorySet(species, teamData);
      if (!set) continue;
      let typeCombo = types.slice().sort().join();
      if (set.ability === "Drought" || set.ability === "Drizzle") {
        typeCombo = set.ability;
      }
      if (!this.forceMonotype && teamData.typeComboCount[typeCombo] >= limitFactor) continue;
      const itemData = this.dex.items.get(set.item);
      if (teamData.has[itemData.id]) continue;
      pokemon.push(set);
      for (const type of types) {
        if (type in teamData.typeCount) {
          teamData.typeCount[type]++;
        } else {
          teamData.typeCount[type] = 1;
        }
      }
      if (typeCombo in teamData.typeComboCount) {
        teamData.typeComboCount[typeCombo]++;
      } else {
        teamData.typeComboCount[typeCombo] = 1;
      }
      teamData.baseFormes[species.baseSpecies] = 1;
      teamData.has[itemData.id] = 1;
      const abilityState = this.dex.abilities.get(set.ability);
      if (abilityState.id in weatherAbilitiesSet) {
        teamData.weather = weatherAbilitiesSet[abilityState.id];
      }
      for (const move of set.moves) {
        const moveId = (0, import_dex.toID)(move);
        if (moveId in teamData.has) {
          teamData.has[moveId]++;
        } else {
          teamData.has[moveId] = 1;
        }
      }
      for (const typeName of this.dex.types.names()) {
        if (teamData.resistances[typeName] >= 1) continue;
        if (resistanceAbilities[abilityState.id]?.includes(typeName) || !this.dex.getImmunity(typeName, types)) {
          teamData.resistances[typeName] = (teamData.resistances[typeName] || 0) + 1;
          if (teamData.resistances[typeName] >= 1) teamData.weaknesses[typeName] = 0;
          continue;
        }
        const typeMod = this.dex.getEffectiveness(typeName, types);
        if (typeMod < 0) {
          teamData.resistances[typeName] = (teamData.resistances[typeName] || 0) + 1;
          if (teamData.resistances[typeName] >= 1) teamData.weaknesses[typeName] = 0;
        } else if (typeMod > 0) {
          teamData.weaknesses[typeName] = (teamData.weaknesses[typeName] || 0) + 1;
        }
      }
    }
    if (!teamData.forceResult && pokemon.length < this.maxTeamSize) return this.randomBSSFactoryTeam(side, ++depth);
    if (!teamData.forceResult && !this.forceMonotype) {
      for (const type in teamData.weaknesses) {
        if (teamData.weaknesses[type] >= 3 * limitFactor) return this.randomBSSFactoryTeam(side, ++depth);
      }
    }
    return pokemon;
  }
}
var teams_default = RandomGen8Teams;
//# sourceMappingURL=teams.js.map
