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
  RandomChampionsTeams: () => RandomChampionsTeams,
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
  "swordsdance",
  "tidyup",
  "victorydance"
];
const SPEED_SETUP = [
  "agility",
  "autotomize",
  "flamecharge",
  "raindance",
  "rockpolish",
  "snowscape",
  "sunnyday",
  "trailblaze"
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
  "nastyplot",
  "noretreat",
  "poweruppunch",
  "quiverdance",
  "raindance",
  "rockpolish",
  "shellsmash",
  "shiftgear",
  "sunnyday",
  "swordsdance",
  "tailglow",
  "takeheart",
  "tidyup",
  "trailblaze",
  "workup",
  "victorydance"
];
const NO_STAB = [
  "acidspray",
  "accelerock",
  "aquajet",
  "bounce",
  "breakingswipe",
  "bulletpunch",
  "chatter",
  "chloroblast",
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
  "mortalspin",
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
  "snaptrap",
  "strugglebug",
  "suckerpunch",
  "trailblaze",
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
const PIVOT_MOVES = [
  "chillyreception",
  "flipturn",
  "partingshot",
  "shedtail",
  "teleport",
  "uturn",
  "voltswitch"
];
const MOVE_PAIRS = [
  ["sleeptalk", "rest"],
  ["protect", "wish"],
  ["leechseed", "substitute"],
  ["reflect", "lightscreen"]
];
const PRIORITY_POKEMON = [
  "mimikyu",
  "palafin",
  "scizor",
  "scizormega"
];
class RandomChampionsTeams extends import_teams.RandomTeams {
  constructor(format, prng) {
    super(format, prng);
    this.randomSets = require("./sets.json");
    this.noStab = NO_STAB;
    this.priorityPokemon = PRIORITY_POKEMON;
    this.moveEnforcementCheckers = {
      Bug: (movePool, moves, abilities, types, counter) => !counter.get("Bug") && ["megahorn", "pinmissile", "xscissor"].some((m) => movePool.includes(m)),
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
      Normal: (movePool, moves, abilities, types, counter) => !counter.get("Normal") && (movePool.includes("boomburst") || ["Electric", "Fire", "Ghost", "Ground"].some((t) => types.has(t))),
      Poison: (movePool, moves, abilities, types, counter) => !counter.get("Poison"),
      Psychic: (movePool, moves, abilities, types, counter) => {
        if (["Dark", "Ice", "Steel", "Water"].some((m) => types.has(m))) return false;
        return !counter.get("Psychic");
      },
      Rock: (movePool, moves, abilities, types, counter, species) => !counter.get("Rock") && species.baseStats.atk >= 80,
      Steel: (movePool, moves, abilities, types, counter, species) => !counter.get("Steel") && species.baseStats.atk >= 60,
      Water: (movePool, moves, abilities, types, counter) => !counter.get("Water")
    };
    this.cachedStatusMoves = this.dex.moves.all().filter((move) => move.category === "Status").map((move) => move.id);
  }
  cullMovePool(types, moves, abilities, counter, movePool, teamDetails, species, isLead, preferredType, role) {
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
      if (movePool.includes("healbell")) this.fastPop(movePool, movePool.indexOf("healbell"));
      if (moves.size + movePool.length <= this.maxMoveCount) return;
    }
    const statusMoves = this.cachedStatusMoves;
    const statusInflictingMoves = ["nuzzle", "thunderwave", "toxic", "willowisp", "yawn"];
    const incompatiblePairs = [
      // These moves don't mesh well with other aspects of the set
      [statusMoves, ["healingwish", "switcheroo", "trick"]],
      [SETUP, PIVOT_MOVES],
      [SETUP, HAZARDS],
      [SETUP, ["defog", "haze", "toxic"]],
      [PHYSICAL_SETUP, PHYSICAL_SETUP],
      [SPEED_SETUP, "quickattack"],
      ["curse", "rapidspin"],
      ["defog", HAZARDS],
      ["uturn", "trick"],
      ["substitute", PIVOT_MOVES],
      // These attacks are redundant with each other
      [["psychic", "psychicnoise"], ["psyshock", "psychicnoise"]],
      [["surf", "waterfall"], "hydropump"],
      [["gigadrain", "hornleech", "tropkick"], ["leafstorm", "powerwhip", "woodhammer"]],
      [["fireblast", "flamethrower"], ["fierydance", "overheat"]],
      ["aurasphere", "focusblast"],
      ["closecombat", "drainpunch"],
      ["dragonpulse", "dracometeor"],
      ["risingvoltage", "volttackle"],
      // Status move incompatibilities
      ["taunt", "encore"],
      ["roar", "yawn"],
      [statusInflictingMoves, "toxicspikes"],
      [statusInflictingMoves, statusInflictingMoves]
    ];
    for (const pair of incompatiblePairs) this.incompatibleMoves(moves, movePool, pair[0], pair[1]);
    if (!types.has("Dark") && preferredType !== "Dark") {
      this.incompatibleMoves(moves, movePool, "knockoff", "suckerpunch");
    }
    if (species.id === "camerupt") this.incompatibleMoves(moves, movePool, "roar", "willowisp");
    if (species.id === "cameruptmega") this.incompatibleMoves(moves, movePool, "ancientpower", "willowisp");
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
    for (const moveid of ["auroraveil", "blizzard", "stickyweb"]) {
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
    if (movePool.includes("irondefense")) {
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
    if (species.baseSpecies === "Sharpedo") {
      if (movePool.includes("protect")) {
        counter = this.addMove(
          "protect",
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
    if (species.id === "aegislash" && role === "Bulky Attacker") {
      if (movePool.includes("kingsshield")) {
        counter = this.addMove(
          "kingsshield",
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
    if (role === "Wallbreaker" || this.priorityPokemon.includes(species.id)) {
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
    if (role.includes("Bulky")) {
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
    if (role.includes("Setup")) {
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
    if (["Fast Attacker", "Wallbreaker", "Setup Sweeper", "Bulky Attacker"].includes(role)) {
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
      case "Chlorophyll":
      case "Solar Power":
        return !teamDetails.sun;
      case "Hydration":
      case "Swift Swim":
        return !teamDetails.rain;
      case "Overgrow":
        return !counter.get("Grass");
      case "Sand Force":
      case "Sand Rush":
        return !teamDetails.sand;
      case "Slush Rush":
        return !teamDetails.snow;
      case "Sheer Force":
      case "Skill Link":
        return !counter.get((0, import_dex.toID)(ability));
    }
    return false;
  }
  getAbility(types, moves, abilities, counter, teamDetails, species) {
    if (abilities.length <= 1) return abilities[0];
    if (species.id === "toucannon") {
      if (counter.get("skilllink")) return "Skill Link";
      if (counter.get("sheerforce")) return "Sheer Force";
    }
    if (abilities.includes("Slush Rush") && moves.has("snowscape")) return "Slush Rush";
    const abilityAllowed = [];
    for (const ability of abilities) {
      if (!this.shouldCullAbility(ability, types, moves, abilities, counter, teamDetails, species)) {
        abilityAllowed.push(ability);
      }
    }
    if (abilityAllowed.length >= 1) return this.sample(abilityAllowed);
    if (!abilityAllowed.length) {
      const weatherAbilities = abilities.filter(
        (a) => ["Chlorophyll", "Sand Rush", "Slush Rush", "Solar Power", "Swift Swim"].includes(a)
      );
      if (weatherAbilities.length) return this.sample(weatherAbilities);
    }
    if (abilityAllowed.length >= 1) return this.sample(abilityAllowed);
    return this.sample(abilities);
  }
  getPriorityItem(ability, types, moves, counter, teamDetails, species, isLead, preferredType, role) {
    if (species.requiredItems) return this.sample(species.requiredItems);
    if (species.id === "pikachu") return "Light Ball";
    if (["Cheek Pouch", "Cud Chew", "Harvest"].some((m) => ability === m) || moves.has("bellydrum")) return "Sitrus Berry";
    if (species.id === "alakazam" && this.randomChance(1, 2)) return "Focus Sash";
    if (species.id === "glimmora") return "Focus Sash";
    if (species.id === "rampardos" && role === "Fast Attacker") return "Choice Scarf";
    if (species.id === "ditto") return "Choice Scarf";
    if (["healingwish", "switcheroo", "trick"].some((m) => moves.has(m))) return "Choice Scarf";
    if (ability === "Unburden") return moves.has("closecombat") ? "White Herb" : "Sitrus Berry";
    if (moves.has("shellsmash")) return "White Herb";
    if ((ability === "Magic Guard" || ability === "Sheer Force") && species.id !== "toucannon") return "Life Orb";
    if (moves.has("acrobatics")) return "";
    if (moves.has("auroraveil") || moves.has("lightscreen") && moves.has("reflect")) return "Light Clay";
    if (moves.has("rest") && !moves.has("sleeptalk") && ability !== "Natural Cure" && ability !== "Shed Skin") return "Chesto Berry";
    if (types.has("Normal") && moves.has("doubleedge") && moves.has("fakeout")) return "Silk Scarf";
    if (species.id === "froslass" && moves.has("tripleaxel") || moves.has("populationbomb") || ability === "Hustle" && counter.get("setup") && this.randomChance(1, 2)) return "Wide Lens";
  }
  getItem(ability, types, moves, counter, teamDetails, species, isLead, preferredType, role) {
    if (role === "Fast Attacker" && !counter.get("priority") && ["fakeout", "trailblaze"].every((m) => !moves.has(m)) && (!counter.get("Status") || counter.get("Status") === 1 && moves.has("partingshot"))) return "Choice Scarf";
    if (["flamecharge", "kingsshield", "nuzzle", "rapidspin", "substitute"].some((m) => moves.has(m))) return "Leftovers";
    if (moves.has("outrage") && counter.get("setup")) return "Lum Berry";
    if (role.includes("Bulky")) return "Leftovers";
    if (["Fast Attacker", "Setup Sweeper", "Wallbreaker"].includes(role)) {
      if (["basculegion", "palafin"].includes(species.id)) return "Mystic Water";
      if (this.dex.getEffectiveness("Rock", species) < 2) return "Life Orb";
    }
    if (role === "Fast Support") {
      if (isLead && !counter.get("recovery") && !counter.get("recoil") && counter.get("hazards")) return "Focus Sash";
      return counter.get("Physical") + counter.get("Special") >= 3 && this.dex.getEffectiveness("Rock", species) < 2 ? "Life Orb" : "Leftovers";
    }
    return "Leftovers";
  }
  randomSet(species, teamDetails = {}, isLead = false) {
    const ruleTable = this.dex.formats.getRuleTable(this.format);
    species = this.dex.species.get(species);
    const forme = this.getForme(species);
    const sets = this.randomSets[species.id]["sets"];
    const possibleSets = [];
    for (const set2 of sets) possibleSets.push(set2);
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
    const evs = { hp: 11, atk: 11, def: 11, spa: 11, spd: 11, spe: 11 };
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
    const level = this.getLevel(species);
    const noAttackStatMoves = [...moves].every((m) => {
      const move = this.dex.moves.get(m);
      if (move.damageCallback || move.damage) return true;
      if (move.id === "shellsidearm") return false;
      return move.category !== "Physical" || move.id === "bodypress" || move.id === "foulplay";
    });
    if (noAttackStatMoves && !moves.has("transform") && !ruleTable.has("forceofthefallenmod")) {
      evs.atk = 0;
    }
    const srImmunity = ability === "Magic Guard";
    let srWeakness = srImmunity ? 0 : this.dex.getEffectiveness("Rock", species);
    if (["axekick", "highjumpkick", "jumpkick", "supercellslam"].some((m) => moves.has(m))) srWeakness = 2;
    if (species.id === "charizardmegax") srWeakness = 2;
    while (evs.hp > 0) {
      const hp = Math.floor((2 * species.baseStats.hp + ivs.hp + Math.max(2 * evs.hp - 1, 0) + 100) * level / 100) + 10;
      if (moves.has("substitute") && item !== "Leftovers") {
        if (item === "Sitrus Berry" || item === "Salac Berry") {
          if (hp % 4 === 0) break;
        } else {
          if (hp % 4 > 0) break;
        }
      } else if ((moves.has("bellydrum") || moves.has("shedtail")) && item === "Sitrus Berry") {
        if (hp % 2 === 0) break;
      } else {
        if (srWeakness <= 0 || ability === "Regenerator") break;
        if (srWeakness === 1 && item === "Leftovers") break;
        if (item !== "Sitrus Berry" && hp % (4 / srWeakness) > 0) break;
        if (item === "Sitrus Berry" && hp % (4 / srWeakness) === 0) break;
      }
      evs.hp--;
    }
    if (["gyroball", "metalburst", "trickroom"].some((m) => moves.has(m))) evs.spe = 0;
    const shuffledMoves = Array.from(moves);
    this.prng.shuffle(shuffledMoves);
    return {
      name: species.baseSpecies,
      species: forme,
      speciesId: species.id,
      gender: species.gender || (this.random(2) ? "F" : "M"),
      shiny: this.randomChance(1, 1024),
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
    const webSetters = ["ariados", "slurpuff", "araquanid"];
    const screenSetters = [
      "ninetalesalola",
      "abomasnow",
      "abomasnowmega",
      "froslassmega",
      "vanilluxe",
      "aurorus",
      "grimmsnarl",
      "meowstic"
    ];
    const sunSetters = ["charizardmegay", "ninetales", "torkoal"];
    const incompatibilityList = [
      // These combinations are prevented to avoid double webs or screens.
      [webSetters, webSetters],
      [screenSetters, screenSetters],
      // These Pokemon are incompatible because the presence of one actively harms the other.
      // Screen Cleaner is a bad ability
      ["mrrime", screenSetters],
      // Prevent Dry Skin + sun setting ability
      [["toxicroak", "heliolisk"], sunSetters]
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
    let hasMega = false;
    const typeCount = {};
    const typeComboCount = {};
    const typeWeaknesses = {};
    const typeDoubleWeaknesses = {};
    const teamDetails = {};
    const pokemonList = Object.keys(this.randomSets);
    const [pokemonPool, baseSpeciesPool] = this.getPokemonPool(type, pokemon, isMonotype, pokemonList);
    while (baseSpeciesPool.length && pokemon.length < this.maxTeamSize) {
      const baseSpecies = this.sampleNoReplace(baseSpeciesPool);
      const currentSpeciesPool = [];
      let canMega = false;
      for (const poke of pokemonPool[baseSpecies]) {
        const species2 = this.dex.species.get(poke);
        if (!hasMega && species2.isMega) canMega = true;
      }
      for (const poke of pokemonPool[baseSpecies]) {
        const species2 = this.dex.species.get(poke);
        if (hasMega && species2.isMega) continue;
        if (canMega && !species2.isMega) continue;
        currentSpeciesPool.push(species2);
      }
      const species = this.sample(currentSpeciesPool);
      if (!species.exists) continue;
      if (baseFormes[species.baseSpecies]) continue;
      if (species.baseSpecies === "Zoroark" && pokemon.length < 1) continue;
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
        if (!this.getPokemonCompatibility(species, pokemon)) continue;
      }
      if (!this.forceMonotype && isMonotype && typeComboCount[typeCombo] >= 3 * limitFactor) continue;
      const set = this.randomSet(species, teamDetails, pokemon.length === this.maxTeamSize - 1);
      pokemon.unshift(set);
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
      if (this.dex.items.get(set.item).megaStone) hasMega = true;
      if (set.ability === "Drizzle" || set.moves.includes("raindance")) teamDetails.rain = 1;
      if (set.ability === "Drought" || set.moves.includes("sunnyday")) teamDetails.sun = 1;
      if (set.ability === "Sand Stream") teamDetails.sand = 1;
      if (set.ability === "Snow Warning" || set.moves.includes("snowscape") || set.moves.includes("chillyreception")) {
        teamDetails.snow = 1;
      }
      if (set.moves.includes("healbell")) teamDetails.statusCure = 1;
      if (set.moves.includes("spikes") || set.moves.includes("ceaselessedge")) {
        teamDetails.spikes = (teamDetails.spikes || 0) + 1;
      }
      if (set.moves.includes("toxicspikes") || set.ability === "Toxic Debris") teamDetails.toxicSpikes = 1;
      if (set.moves.includes("stealthrock") || set.moves.includes("stoneaxe")) teamDetails.stealthRock = 1;
      if (set.moves.includes("stickyweb")) teamDetails.stickyWeb = 1;
      if (set.moves.includes("defog")) teamDetails.defog = 1;
      if (set.moves.includes("rapidspin") || set.moves.includes("mortalspin")) teamDetails.rapidSpin = 1;
      if (set.moves.includes("auroraveil")) teamDetails.screens = 1;
    }
    if (pokemon.length < this.maxTeamSize && pokemon.length < 12 && !isMonotype) {
      throw new Error(`Could not build a random team for ${this.format} (seed=${seed})`);
    }
    return pokemon;
  }
}
var teams_default = RandomChampionsTeams;
//# sourceMappingURL=teams.js.map
