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
  RandomChatBatsTeams: () => RandomChatBatsTeams,
  default: () => teams_default
});
module.exports = __toCommonJS(teams_exports);
var import_teams = require("../gen9/teams");
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
  "victorydance",
  "filletaway"
];
const SPECIAL_SETUP = [
  "calmmind",
  "chargebeam",
  "geomancy",
  "nastyplot",
  "quiverdance",
  "tailglow",
  "takeheart",
  "torchsong",
  "filletaway"
];
const SPEED_SETUP = [
  "agility",
  "autotomize",
  "flamecharge",
  "rockpolish",
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
  "filletaway",
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
  "rockpolish",
  "shellsmash",
  "shiftgear",
  "swordsdance",
  "tailglow",
  "takeheart",
  "tidyup",
  "trailblaze",
  "trickroom",
  "workup",
  "victorydance"
];
const SPEED_CONTROL = [
  "electroweb",
  "glare",
  "icywind",
  "lowsweep",
  "quash",
  "stringshot",
  "tailwind",
  "thunderwave",
  "trickroom"
];
const HAZARDS = [
  "spikes",
  "stealthrock",
  "stickyweb",
  "toxicspikes"
];
const PROTECT_MOVES = [
  "banefulbunker",
  "burningbulwark",
  "protect",
  "silktrap",
  "spikyshield"
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
  ["lightscreen", "reflect"],
  ["sleeptalk", "rest"],
  ["protect", "wish"],
  ["leechseed", "protect"],
  ["leechseed", "substitute"],
  ["leechseed", "burningbulwark"]
];
const PRIORITY_POKEMON = [
  "breloom",
  "brutebonnet",
  "cacturne",
  "honchkrow",
  "mimikyu",
  "ragingbolt",
  "scizor"
];
const NO_LEAD_POKEMON = [
  "Zacian",
  "Zamazenta"
];
const DOUBLES_NO_LEAD_POKEMON = [
  "Basculegion",
  "Houndstone",
  "Iron Bundle",
  "Roaring Moon",
  "Zacian",
  "Zamazenta"
];
class RandomChatBatsTeams extends import_teams.RandomTeams {
  constructor() {
    super(...arguments);
    this.randomSets = require("./random-sets.json");
  }
  cullMovePool(types, moves, abilities, counter, movePool, teamDetails, species, isLead, teraType, role, isDoubles) {
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
    const statusMoves = this.cachedStatusMoves;
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
      if (movePool.includes("healbell")) this.fastPop(movePool, movePool.indexOf("healbell"));
      if (moves.size + movePool.length <= this.maxMoveCount) return;
    }
    if (isDoubles) {
      const doublesIncompatiblePairs = [
        // In order of decreasing generalizability
        [SPEED_CONTROL, SPEED_CONTROL],
        [HAZARDS, HAZARDS],
        [PROTECT_MOVES, PROTECT_MOVES],
        ["rockslide", "stoneedge"],
        [SETUP, ["fakeout", "helpinghand"]],
        [PROTECT_MOVES, "wideguard"],
        [["fierydance", "fireblast"], "heatwave"],
        ["dazzlinggleam", ["fleurcannon", "moonblast"]],
        ["poisongas", ["toxicspikes", "willowisp"]],
        [RECOVERY_MOVES, "healpulse"],
        ["lifedew", "healpulse"],
        ["haze", "icywind"],
        [["hydropump", "muddywater"], ["muddywater", "scald"]],
        ["disable", "encore"],
        ["freezedry", "icebeam"],
        ["energyball", "leafstorm"],
        ["wildcharge", "thunderbolt"],
        ["earthpower", "sandsearstorm"],
        ["coaching", ["helpinghand", "howl"]]
      ];
      for (const pair of doublesIncompatiblePairs) this.incompatibleMoves(moves, movePool, pair[0], pair[1]);
      if (role !== "Offensive Protect") this.incompatibleMoves(moves, movePool, PROTECT_MOVES, ["flipturn", "uturn"]);
    }
    const incompatiblePairs = [
      // These moves don't mesh well with other aspects of the set
      [statusMoves, ["healingwish", "switcheroo", "trick"]],
      [SETUP, PIVOT_MOVES],
      [SETUP, HAZARDS],
      [SETUP, ["defog", "nuzzle", "toxic", "yawn", "haze"]],
      [PHYSICAL_SETUP, PHYSICAL_SETUP],
      [SPECIAL_SETUP, "thunderwave"],
      ["substitute", PIVOT_MOVES],
      [SPEED_SETUP, ["aquajet", "rest", "trickroom"]],
      ["curse", ["irondefense", "rapidspin"]],
      ["dragondance", "dracometeor"],
      // These attacks are redundant with each other
      ["surf", "hydropump"],
      ["liquidation", "wavecrash"],
      ["aquajet", "flipturn"],
      ["gigadrain", "leafstorm"],
      ["powerwhip", "hornleech"],
      [["airslash", "bravebird", "hurricane"], ["airslash", "bravebird", "hurricane"]],
      ["knockoff", "foulplay"],
      ["throatchop", ["crunch", "lashout"]],
      ["doubleedge", ["bodyslam", "headbutt"]],
      ["fireblast", ["fierydance", "flamethrower"]],
      ["lavaplume", "magmastorm"],
      ["thunderpunch", "wildcharge"],
      [["thunderbolt", "discharge", "thunder"], ["thunderbolt", "discharge", "thunder"]],
      ["gunkshot", ["direclaw", "poisonjab", "sludgebomb"]],
      ["aurasphere", "focusblast"],
      ["closecombat", "drainpunch"],
      ["bugbite", "pounce"],
      [["dragonpulse", "spacialrend"], "dracometeor"],
      ["heavyslam", "flashcannon"],
      ["alluringvoice", "dazzlinggleam"],
      // These status moves are redundant with each other
      ["taunt", "disable"],
      [["thunderwave", "toxic"], ["thunderwave", "willowisp"]],
      [["thunderwave", "toxic", "willowisp"], "toxicspikes"]
    ];
    for (const pair of incompatiblePairs) this.incompatibleMoves(moves, movePool, pair[0], pair[1]);
    if (!types.has("Ice")) this.incompatibleMoves(moves, movePool, "icebeam", "icywind");
    if (!isDoubles) this.incompatibleMoves(moves, movePool, ["taunt", "strengthsap"], "encore");
    if (!types.has("Dark") && teraType !== "Dark") this.incompatibleMoves(moves, movePool, "knockoff", "suckerpunch");
    if (!abilities.includes("Prankster")) this.incompatibleMoves(moves, movePool, "thunderwave", "yawn");
    if (species.id === "lurantis") this.incompatibleMoves(moves, movePool, "leafstorm", "powerwhip");
    if (species.id === "ironcrown") this.incompatibleMoves(moves, movePool, "kingsshield", "stealthrock");
    if (species.id === "ironcrown") this.incompatibleMoves(moves, movePool, "kingsshield", "rest");
    if (species.id === "ironcrown") this.incompatibleMoves(moves, movePool, "rest", "stealthrock");
    if (species.id === "carbink") this.incompatibleMoves(moves, movePool, "spikes", "stealthrock");
    if (species.id === "moltres") this.incompatibleMoves(moves, movePool, "bravebird", "woodhammer");
    if (species.id === "moltres") this.incompatibleMoves(moves, movePool, "flareblitz", "wavecrash");
    if (species.id === "kommoo") this.incompatibleMoves(moves, movePool, "aurasphere", "closecombat");
    if (species.id === "archaludon") this.incompatibleMoves(moves, movePool, "scald", "hydropump");
    if (species.id === "abomasnowmega") this.incompatibleMoves(moves, movePool, "iceshard", "snowscape");
    if (species.id === "regieleki") this.incompatibleMoves(moves, movePool, "blazingtorque", "soak");
    if (species.id === "golurk") this.incompatibleMoves(moves, movePool, "icepunch", "dynamicpunch");
    if (species.id === "ogerponhearthflame") this.incompatibleMoves(moves, movePool, "crabhammer", "stoneedge");
    if (species.id === "hitmontop") this.incompatibleMoves(moves, movePool, "bulkup", "rapidspin");
    if (species.id === "mesprit") this.incompatibleMoves(moves, movePool, "psychic", "storedpower");
    if (species.id === "primeape") this.incompatibleMoves(moves, movePool, "knockoff", "earthquake");
    if (species.id === "feraligatrmega") this.incompatibleMoves(moves, movePool, "thunderfang", "poisonfang");
    if (species.id === "salazzle") this.incompatibleMoves(moves, movePool, "malignantchain", "venoshock");
    if (species.id === "glimmora") this.incompatibleMoves(moves, movePool, "powergem", "meteorbeam");
    if (species.id === "wobbuffet") this.incompatibleMoves(moves, movePool, "shedtail", "encore");
    if (species.id === "wobbuffet") this.incompatibleMoves(moves, movePool, "nightshade", "guillotine");
  }
  randomMoveset(types, abilities, teamDetails, species, isLead, movePool, teraType, role, isDoubles) {
    const moves = /* @__PURE__ */ new Set();
    let counter = this.queryMoves(moves, species, teraType, abilities);
    this.cullMovePool(types, moves, abilities, counter, movePool, teamDetails, species, isLead, teraType, role, isDoubles);
    if (movePool.length <= this.maxMoveCount) {
      for (const moveid of movePool) {
        moves.add(moveid);
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
        isDoubles,
        teraType,
        role
      );
    };
    if (role === "Tera Blast user") {
      counter = this.addMove(
        "terablast",
        moves,
        types,
        abilities,
        teamDetails,
        species,
        isLead,
        movePool,
        teraType,
        role,
        isDoubles
      );
    }
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
        teraType,
        role,
        isDoubles
      );
    }
    if (species.id === "chiyu") {
      if (movePool.includes("splash")) {
        counter = this.addMove(
          "splash",
          moves,
          types,
          abilities,
          teamDetails,
          species,
          isLead,
          movePool,
          teraType,
          role,
          isDoubles
        );
      }
    }
    if (species.id === "infernape" && movePool.includes("mindblown")) {
      counter = this.addMove(
        "mindblown",
        moves,
        types,
        abilities,
        teamDetails,
        species,
        isLead,
        movePool,
        teraType,
        role,
        isDoubles
      );
      counter = this.addMove(
        "alloutassault",
        moves,
        types,
        abilities,
        teamDetails,
        species,
        isLead,
        movePool,
        teraType,
        role,
        isDoubles
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
        teraType,
        role,
        isDoubles
      );
    }
    for (const moveid of ["nightshade", "revelationdance", "revivalblessing", "stickyweb"]) {
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
          teraType,
          role,
          isDoubles
        );
      }
    }
    if (movePool.includes("trickroom") && role === "Doubles Wallbreaker") {
      counter = this.addMove(
        "trickroom",
        moves,
        types,
        abilities,
        teamDetails,
        species,
        isLead,
        movePool,
        teraType,
        role,
        isDoubles
      );
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
          teraType,
          role,
          isDoubles
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
          teraType,
          role,
          isDoubles
        );
      }
    }
    if (!isDoubles && types.size === 1 && (types.has("Normal") || types.has("Fighting"))) {
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
          teraType,
          role,
          isDoubles
        );
      }
    }
    if (types.size === 1 && types.has("Water") && role === "Wallbreaker" && movePool.includes("flipturn")) {
      counter = this.addMove(
        "flipturn",
        moves,
        types,
        abilities,
        teamDetails,
        species,
        isLead,
        movePool,
        teraType,
        role,
        isDoubles
      );
    }
    if (species.id === "smeargle") {
      if (movePool.includes("spore")) {
        counter = this.addMove(
          "spore",
          moves,
          types,
          abilities,
          teamDetails,
          species,
          isLead,
          movePool,
          teraType,
          role,
          isDoubles
        );
      }
    }
    if (isDoubles) {
      const doublesEnforcedMoves = ["auroraveil", "mortalspin", "spore"];
      for (const moveid of doublesEnforcedMoves) {
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
            teraType,
            role,
            isDoubles
          );
        }
      }
      if (movePool.includes("fakeout") && species.baseStats.spe <= 50) {
        counter = this.addMove(
          "fakeout",
          moves,
          types,
          abilities,
          teamDetails,
          species,
          isLead,
          movePool,
          teraType,
          role,
          isDoubles
        );
      }
      if (movePool.includes("tailwind") && (abilities.includes("Prankster") || abilities.includes("Gale Wings"))) {
        counter = this.addMove(
          "tailwind",
          moves,
          types,
          abilities,
          teamDetails,
          species,
          isLead,
          movePool,
          teraType,
          role,
          isDoubles
        );
      }
      if (movePool.includes("thunderwave") && abilities.includes("Prankster")) {
        counter = this.addMove(
          "thunderwave",
          moves,
          types,
          abilities,
          teamDetails,
          species,
          isLead,
          movePool,
          teraType,
          role,
          isDoubles
        );
      }
    }
    if (["Bulky Attacker", "Bulky Setup", "Wallbreaker", "Doubles Wallbreaker"].includes(role) || PRIORITY_POKEMON.includes(species.id)) {
      const priorityMoves = [];
      for (const moveid of movePool) {
        const move = this.dex.moves.get(moveid);
        const moveType = this.getMoveType(move, species, abilities, teraType);
        if (types.has(moveType) && (move.priority > 0 || moveid === "grassyglide" && abilities.includes("Grassy Surge")) && (move.basePower || move.basePowerCallback)) {
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
          teraType,
          role,
          isDoubles
        );
      }
    }
    if (species.id === "moltres") {
      const typeToEnforce = this.randomChance(1, 2) ? "Fire" : "Flying";
      const stabMoves = [];
      for (const moveid of movePool) {
        const move = this.dex.moves.get(moveid);
        const moveType = this.getMoveType(move, species, abilities, teraType);
        if (!this.noStab.includes(moveid) && (move.basePower || move.basePowerCallback) && typeToEnforce === moveType) {
          stabMoves.push(moveid);
        }
      }
      while (runEnforcementChecker(typeToEnforce)) {
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
          teraType,
          role,
          isDoubles
        );
      }
    }
    for (const type of types) {
      if (species.id === "moltres") break;
      if (species.id === "meowscarada") break;
      const stabMoves = [];
      for (const moveid of movePool) {
        const move = this.dex.moves.get(moveid);
        const moveType = this.getMoveType(move, species, abilities, teraType);
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
          teraType,
          role,
          isDoubles
        );
      }
    }
    if (!counter.get("stabtera") && !["Bulky Support", "Doubles Support"].includes(role) && !abilities.includes("Protean")) {
      const stabMoves = [];
      for (const moveid of movePool) {
        const move = this.dex.moves.get(moveid);
        const moveType = this.getMoveType(move, species, abilities, teraType);
        if (!this.noStab.includes(moveid) && (move.basePower || move.basePowerCallback) && teraType === moveType) {
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
          teraType,
          role,
          isDoubles
        );
      }
    }
    if (!counter.get("stab") && !abilities.includes("Protean")) {
      const stabMoves = [];
      for (const moveid of movePool) {
        const move = this.dex.moves.get(moveid);
        const moveType = this.getMoveType(move, species, abilities, teraType);
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
          teraType,
          role,
          isDoubles
        );
      }
    }
    if (["Bulky Support", "Bulky Attacker", "Bulky Setup"].includes(role)) {
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
          teraType,
          role,
          isDoubles
        );
      }
    }
    if (role.includes("Setup") || role === "Tera Blast user") {
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
          teraType,
          role,
          isDoubles
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
            teraType,
            role,
            isDoubles
          );
        }
      }
    }
    if (role === "Doubles Support") {
      for (const moveid of ["fakeout", "followme", "ragepowder"]) {
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
            teraType,
            role,
            isDoubles
          );
        }
      }
    }
    if (role.includes("Protect")) {
      const protectMoves = movePool.filter((moveid) => PROTECT_MOVES.includes(moveid));
      if (protectMoves.length) {
        const moveid = this.sample(protectMoves);
        counter = this.addMove(
          moveid,
          moves,
          types,
          abilities,
          teamDetails,
          species,
          isLead,
          movePool,
          teraType,
          role,
          isDoubles
        );
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
          teraType,
          role,
          isDoubles
        );
      }
    }
    if (!["AV Pivot", "Fast Support", "Bulky Support", "Bulky Protect", "Doubles Support"].includes(role)) {
      if (counter.damagingMoves.size === 1) {
        const currentAttackType = counter.damagingMoves.values().next().value.type;
        const coverageMoves = [];
        for (const moveid of movePool) {
          const move = this.dex.moves.get(moveid);
          const moveType = this.getMoveType(move, species, abilities, teraType);
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
            teraType,
            role,
            isDoubles
          );
        }
      }
    }
    while (moves.size < this.maxMoveCount && movePool.length) {
      if (moves.size + movePool.length <= this.maxMoveCount) {
        for (const moveid2 of movePool) {
          moves.add(moveid2);
        }
        break;
      }
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
        teraType,
        role,
        isDoubles
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
            teraType,
            role,
            isDoubles
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
            teraType,
            role,
            isDoubles
          );
        }
      }
    }
    return moves;
  }
  getPriorityItem(ability, types, moves, counter, teamDetails, species, isLead, teraType, role, isDoubles) {
    if (!isDoubles) {
      if (role === "Fast Bulky Setup" && (ability === "Quark Drive" || ability === "Protosynthesis")) {
        return "Booster Energy";
      }
      if (species.id === "lokix") {
        return role === "Fast Attacker" ? "Silver Powder" : "Life Orb";
      }
    }
    if (species.requiredItems) {
      if (species.baseSpecies === "Arceus") {
        return species.requiredItems[0];
      }
      return this.sample(species.requiredItems);
    }
    if (role === "AV Pivot") return "Assault Vest";
    if (species.id === "pikachu") return "Light Ball";
    if (species.id === "regieleki") return "Magnet";
    if (species.id === "smeargle") return "Focus Sash";
    if (species.id === "volcarona") return "Heavy-Duty Boots";
    if (species.id === "golemalola") return "Life Orb";
    if (species.id === "ironcrown") return moves.has("rest") ? "Chesto Berry" : "Leftovers";
    if (species.id === "lurantis") return this.sample(["Life Orb", "Leftovers"]);
    if (species.id === "carbink") return "Leftovers";
    if (species.id === "moltres") return "Life Orb";
    if (species.id === "kommoo") return "Throat Spray";
    if (species.id === "volbeat") return "Focus Sash";
    if (species.id === "illumise") return "Focus Sash";
    if (species.id === "abomasnow") return "Light Clay";
    if (species.id === "dugtrio" && moves.has("swordsdance")) return "Focus Sash";
    if (species.id === "dugtrio") return "Choice Band";
    if (species.id === "tyranitar") return "Choice Scarf";
    if (species.id === "mimikyu") return "Red Card";
    if (species.id === "mesprit" && moves.has("aquaring")) return "Leftovers";
    if (species.id === "mesprit") return "Throat Spray";
    if (species.id === "electrode" && moves.has("rapidspin")) return "Heavy-Duty Boots";
    if (species.id === "electrode") return this.sample(["Normal Gem", "Heavy-Duty Boots"]);
    if (species.id === "taurospaldeacombat") return "Expert Belt";
    if (species.id === "chiyu") return "Normalium Z";
    if (species.id === "wochien") return "Big Root";
    if (species.id === "staraptor") return "Choice Scarf";
    if (species.id === "archaludon" && ability === "Hydroelectric Dam") return "Assault Vest";
    if (species.id === "archaludon" && ability === "Stamina") return "Leftovers";
    if (species.id === "malamar") return this.sample(["Mirror Herb", "Leftovers"]);
    if (species.id === "empoleon") return moves.has("watershuriken") ? "Loaded Dice" : "Leftovers";
    if (species.id === "glastrier" && moves.has("swordsdance")) return "Heavy-Duty Boots";
    if (species.id === "glastrier") return "Assault Vest";
    if (species.id === "lycanrocmidnight") return "Loaded Dice";
    if (species.id === "lycanroc") return this.sample(["Leftovers", "Heavy-Duty Boots"]);
    if (species.id === "lycanrocdusk") return "Expert Belt";
    if (species.id === "dodrio" && moves.has("drillpeck")) return "Life Orb";
    if (species.id === "dodrio" && moves.has("bravebird")) return "Heavy-Duty Boots";
    if (species.id === "whiscash") return "Rocky Helmet";
    if (species.id === "hippowdon") return this.sample(["Leftovers", "Rocky Helmet"]);
    if (species.id === "cramorant") return "Heavy-Duty Boots";
    if (species.id === "grafaiai") return this.sample(["Red Card", "Mirror Herb"]);
    if (species.id === "tatsugiri") return "Choice Scarf";
    if (species.id === "kyurem") return "Heavy-Duty Boots";
    if (species.id === "roaringmoon") return "Heavy-Duty Boots";
    if (species.id === "milotic") return "Rocky Helmet";
    if (species.id === "gogoat") return "Leftovers";
    if (species.id === "clodsire") return this.sample(["Leftovers", "Rocky Helmet"]);
    if (species.id === "masquerain") return "Heavy-Duty Boots";
    if (species.id === "kyuremblack" && moves.has("roost")) return "Heavy-Duty Boots";
    if (species.id === "kyuremblack") return this.sample(["Choice Band", "Heavy-Duty Boots"]);
    if (species.id === "ironthorns") return "Rocky Helmet";
    if (species.id === "dudunsparce") return "Leftovers";
    if (species.id === "chienpao") return "Heavy Duty Boots";
    if (species.id === "pelipper" && moves.has("roost")) return "Heavy-Duty Boots";
    if (species.id === "pelipper") return "Choice Specs";
    if (species.id === "kleavor") return "Choice Scarf";
    if (species.id === "araquanid") return "Heavy-Duty Boots";
    if (species.id === "avalugghisui") return "Heavy-Duty Boots";
    if (species.id === "swalot") return "Leftovers";
    if (species.id === "zapdosgalar") return this.sample(["Choice Scarf", "Expert Belt"]);
    if (species.id === "phione") return "Leftovers";
    if (species.id === "sudowoodo") return "Choice Band";
    if (species.id === "dondozo") return "Leftovers";
    if (species.id === "golurk") return this.sample(["Life Orb", "Punching Glove", "Colbur Berry"]);
    if (species.id === "meowscarada") return "Heavy-Duty Boots";
    if (species.id === "infernape") return this.sample(["Life Orb", "Sitrus Berry", "Air Balloon"]);
    if (species.id === "urshifu") return this.sample(["Life Orb", "Protective Pads"]);
    if (species.id === "urshifurapidstrike") return this.sample(["Life Orb", "Protective Pads"]);
    if (species.id === "salamence") return this.sample(["Life Orb", "Heavy-Duty Boots", "Sky Plate"]);
    if (species.id === "stonjourner") return "Choice Scarf";
    if (species.id === "veluza") return "Sitrus Berry";
    if (species.id === "ogerponhearthflame") return "Hearthflame Mask";
    if (species.id === "dachsbun") return "Rocky Helmet";
    if (species.id === "mew") return "Starf Berry";
    if (species.id === "magneton") return this.sample(["Air Balloon", "Chople Berry"]);
    if (species.id === "delibird") return "Heavy-Duty Boots";
    if (species.id === "hitmontop") return this.sample(["Protective Pads", "Wide Lens"]);
    if (species.id === "articunogalar" && moves.has("roost")) return "Heavy-Duty Boots";
    if (species.id === "articunogalar" && moves.has("aurasphere")) return "Choice Specs";
    if (species.id === "vaporeon") return "Flame Orb";
    if (species.id === "garganacl") return "Poisonium Z";
    if (species.id === "swanna") return "Heavy-Duty Boots";
    if (species.id === "terapagos") return "Leftovers";
    if (species.id === "flapple") return "Tart Apple";
    if (species.id === "genesectburn" && moves.has("sunsteelstrike")) return "Burn Drive";
    if (species.id === "genesectchill" && moves.has("behemothblade")) return "Chill Drive";
    if (species.id === "genesectdouse" && moves.has("makeitrain")) return "Douse Drive";
    if (species.id === "genesectshock" && moves.has("tachyoncutter")) return "Shock Drive";
    if (species.id === "honchkrow") return "Heavy-Duty Boots";
    if (species.id === "primeape") return "Eviolite";
    if (species.id === "rillaboom") return "Heavy-Duty Boots";
    if (species.id === "mandibuzz") return "Thick Club";
    if (species.id === "feraligatr") return "Life Orb";
    if (species.id === "salazzle") return "Heavy-Duty Boots";
    if (species.id === "kyogre") return "Waterium Z";
    if (species.id === "azelf") return "Focus Band";
    if (species.id === "decidueye") return this.sample(["Life Orb", "Heavy-Duty Boots", "Leftovers"]);
    if (species.id === "ogerponcornerstone") return "Cornerstone Mask";
    if (species.id === "glimmora" && moves.has("meteorbeam")) return "Power Herb";
    if (species.id === "glimmora") return "Air Balloon";
    if (species.id === "wobbuffet") return "Covert Cloak";
  }
  randomSet(s, teamDetails = {}, isLead = false, isDoubles = false) {
    const species = this.dex.species.get(s);
    const forme = this.getForme(species);
    const sets = this.randomSets[species.id]["sets"];
    const possibleSets = [];
    const ruleTable = this.dex.formats.getRuleTable(this.format);
    for (const set2 of sets) {
      const abilities2 = set2.abilities;
      if (isLead && (abilities2.includes("Protosynthesis") || abilities2.includes("Quark Drive")) && set2.role === "Fast Bulky Setup") continue;
      if ((teamDetails.teraBlast || ruleTable.has("terastalclause")) && set2.role === "Tera Blast user") {
        continue;
      }
      possibleSets.push(set2);
    }
    const set = this.sampleIfArray(possibleSets);
    const role = set.role;
    const movePool = [];
    for (const movename of set.movepool) {
      movePool.push(this.dex.moves.get(movename).id);
    }
    const teraTypes = set.teraTypes;
    let teraType = this.sampleIfArray(teraTypes);
    let ability = "";
    let item = void 0;
    const evs = { hp: 85, atk: 85, def: 85, spa: 85, spd: 85, spe: 85 };
    const ivs = { hp: 31, atk: 31, def: 31, spa: 31, spd: 31, spe: 31 };
    const types = new Set(species.types);
    const abilities = set.abilities;
    const moves = this.randomMoveset(types, abilities, teamDetails, species, isLead, movePool, teraType, role, isDoubles);
    const counter = this.queryMoves(moves, species, teraType, abilities);
    ability = this.getAbility(types, moves, abilities, counter, teamDetails, species, isLead, isDoubles, teraType, role);
    item = this.getPriorityItem(ability, types, moves, counter, teamDetails, species, isLead, teraType, role, isDoubles);
    if (item === void 0) {
      if (isDoubles) {
        item = this.getDoublesItem(ability, types, moves, counter, teamDetails, species, isLead, teraType, role);
      } else {
        item = this.getItem(ability, types, moves, counter, teamDetails, species, isLead, teraType, role);
      }
    }
    const level = this.getLevel(species, isDoubles);
    const srImmunity = ability === "Magic Guard" || ability === "Frost Cloak" || item === "Heavy-Duty Boots";
    let srWeakness = srImmunity ? 0 : this.dex.getEffectiveness("Rock", species);
    if (["axekick", "highjumpkick", "jumpkick"].some((m) => moves.has(m))) srWeakness = 2;
    while (evs.hp > 1) {
      const hp = Math.floor(Math.floor(2 * species.baseStats.hp + ivs.hp + Math.floor(evs.hp / 4) + 100) * level / 100 + 10);
      if (moves.has("substitute") && ["Sitrus Berry", "Salac Berry"].includes(item)) {
        if (hp % 4 === 0) break;
      } else if ((moves.has("bellydrum") || moves.has("filletaway")) && (item === "Sitrus Berry" || ability === "Gluttony")) {
        if (hp % 2 === 0) break;
      } else if (moves.has("substitute") && moves.has("endeavor")) {
        if (hp % 4 > 0) break;
      } else {
        if (srWeakness <= 0 || ability === "Regenerator" || ["Leftovers", "Life Orb"].includes(item)) break;
        if (item !== "Sitrus Berry" && hp % (4 / srWeakness) > 0) break;
        if (item === "Sitrus Berry" && hp % (4 / srWeakness) === 0) break;
      }
      evs.hp -= 4;
    }
    const noAttackStatMoves = [...moves].every((m) => {
      const move = this.dex.moves.get(m);
      if (move.damageCallback || move.damage) return true;
      if (move.id === "shellsidearm") return false;
      if (move.id === "terablast" && (species.id === "porygon2" || moves.has("shiftgear") || species.baseStats.atk > species.baseStats.spa)) return false;
      return move.category !== "Physical" || move.id === "bodypress" || move.id === "foulplay";
    });
    if (noAttackStatMoves && !moves.has("transform") && this.format.mod !== "partnersincrime" && species.id !== "illumise") {
      evs.atk = 0;
      ivs.atk = 0;
    }
    if (moves.has("gyroball") || moves.has("trickroom") || moves.has("archaicglare")) {
      evs.spe = 0;
      ivs.spe = 0;
    }
    if (this.forceTeraType) teraType = this.forceTeraType;
    const shuffledMoves = Array.from(moves);
    this.prng.shuffle(shuffledMoves);
    return {
      name: species.baseSpecies,
      species: forme,
      gender: species.baseSpecies === "Greninja" ? "M" : species.gender || (this.random(2) ? "F" : "M"),
      shiny: this.randomChance(1, 1024),
      level,
      moves: shuffledMoves,
      ability,
      evs,
      ivs,
      item,
      teraType,
      role
    };
  }
  randomChatBatsTeam() {
    this.enforceNoDirectCustomBanlistChanges();
    const seed = this.prng.getSeed();
    const ruleTable = this.dex.formats.getRuleTable(this.format);
    const pokemon = [];
    const isMonotype = !!this.forceMonotype || ruleTable.has("sametypeclause");
    const isDoubles = this.format.gameType !== "singles";
    const typePool = this.dex.types.names().filter((name) => name !== "Stellar");
    const type = this.forceMonotype || this.sample(typePool);
    const baseFormes = {};
    let hasMega = false;
    const typeCount = {};
    const typeComboCount = {};
    const typeWeaknesses = {};
    const typeDoubleWeaknesses = {};
    const teamDetails = {};
    let numMaxLevelPokemon = 0;
    const pokemonList = Object.keys(this.randomSets);
    const [pokemonPool, baseSpeciesPool] = this.getPokemonPool(type, pokemon, isMonotype, pokemonList);
    let leadsRemaining = this.format.gameType === "doubles" ? 2 : 1;
    while (baseSpeciesPool.length && pokemon.length < this.maxTeamSize) {
      const baseSpecies = this.sampleNoReplace(baseSpeciesPool);
      if (hasMega && (baseSpecies === "Typhlosion" || baseSpecies === "Altaria" || baseSpecies === "Raticate")) continue;
      const currentSpeciesPool = [];
      for (const poke of pokemonPool[baseSpecies]) {
        const species2 = this.dex.species.get(poke);
        if (hasMega && species2.isMega) continue;
        currentSpeciesPool.push(species2);
      }
      const species = this.sample(currentSpeciesPool);
      if (!species.exists) continue;
      if (baseFormes[species.baseSpecies]) continue;
      if (hasMega && species.isMega) continue;
      if ((species.baseSpecies === "Ogerpon" || species.baseSpecies === "Terapagos") && teamDetails.teraBlast) continue;
      if (species.baseSpecies === "Zoroark" && pokemon.length >= this.maxTeamSize - 1) continue;
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
            if (typeDoubleWeaknesses[typeName] >= 1 * Number(limitFactor)) {
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
        if (!this.adjustLevel && this.getLevel(species, isDoubles) === 100 && numMaxLevelPokemon >= limitFactor) {
          continue;
        }
      }
      if (!this.forceMonotype && isMonotype && typeComboCount[typeCombo] >= 3 * limitFactor) continue;
      let set;
      if (leadsRemaining) {
        if (isDoubles && DOUBLES_NO_LEAD_POKEMON.includes(species.baseSpecies) || !isDoubles && NO_LEAD_POKEMON.includes(species.baseSpecies)) {
          if (pokemon.length + leadsRemaining === this.maxTeamSize) continue;
          set = this.randomSet(species, teamDetails, false, isDoubles);
          pokemon.push(set);
        } else {
          set = this.randomSet(species, teamDetails, true, isDoubles);
          pokemon.unshift(set);
          leadsRemaining--;
        }
      } else {
        set = this.randomSet(species, teamDetails, false, isDoubles);
        pokemon.push(set);
      }
      const item = this.dex.items.get(set.item);
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
      if (item.megaStone) hasMega = true;
      if (set.ability === "Drizzle" || set.moves.includes("raindance")) teamDetails.rain = 1;
      if (set.ability === "Drought" || set.ability === "Orichalcum Pulse" || set.moves.includes("sunnyday")) {
        teamDetails.sun = 1;
      }
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
      if (set.moves.includes("auroraveil") || set.moves.includes("reflect") && set.moves.includes("lightscreen")) {
        teamDetails.screens = 1;
      }
      if (set.role === "Tera Blast user" || species.baseSpecies === "Ogerpon" || species.baseSpecies === "Terapagos") {
        teamDetails.teraBlast = 1;
      }
    }
    if (pokemon.length < this.maxTeamSize && pokemon.length < 12) {
      throw new Error(`Could not build a random team for ${this.format} (seed=${seed})`);
    }
    return pokemon;
  }
}
var teams_default = RandomChatBatsTeams;
//# sourceMappingURL=teams.js.map
