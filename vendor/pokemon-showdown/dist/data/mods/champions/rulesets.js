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
var rulesets_exports = {};
__export(rulesets_exports, {
  Rulesets: () => Rulesets
});
module.exports = __toCommonJS(rulesets_exports);
const Rulesets = {
  standardag: {
    inherit: true,
    ruleset: [
      "Obtainable",
      "Team Preview",
      "Cancel Mod",
      "Endless Battle Clause",
      "Adjust Level = 50",
      "Species Clause",
      "Item Clause = 1",
      "Min Team Size = 6"
    ]
  },
  standard: {
    inherit: true,
    ruleset: [
      "Standard AG",
      "Sleep Moves Clause",
      "Nickname Clause",
      "OHKO Clause",
      "Evasion Clause"
    ]
  },
  standarddraft: {
    inherit: true,
    ruleset: [
      "Standard AG",
      "Nickname Clause",
      "Sleep Clause Mod",
      "OHKO Clause",
      "Evasion Clause",
      "!Item Clause"
    ],
    onBegin() {
      this.reportPercentages = true;
    }
    // timer: {starting: 60 * 60, grace: 0, addPerTurn: 10, maxPerTurn: 100, timeoutAutoChoose: true},
  },
  flatrules: {
    inherit: true,
    desc: "The in-game Flat Rules: Adjust Level 50, Species Clause, Item Clause = 1, -Mythical, -Restricted Legendary, Bring 6 Pick 3-6 depending on game type.",
    ruleset: ["Obtainable", "Team Preview", "Species Clause", "Nickname Clause", "Item Clause = 1", "Adjust Level = 50", "Picked Team Size = Auto", "Min Team Size = 6", "Cancel Mod"],
    banlist: ["Mythical", "Restricted Legendary"]
  },
  teampreview: {
    inherit: true,
    onTeamPreview() {
      this.add("clearpoke");
      for (const pokemon of this.getAllPokemon()) {
        const details = pokemon.details.replace(/(Xerneas|Zacian|Zamazenta)(-[a-zA-Z?-]+)?/g, "$1-*");
        this.add("poke", pokemon.side.id, details, "");
      }
      if (this.ruleTable.has(`teratypepreview`)) {
        for (const side of this.sides) {
          let buf = ``;
          for (const pokemon of side.pokemon) {
            buf += buf ? ` / ` : `raw|${side.name}'s Tera Types:<br />`;
            buf += `<psicon pokemon="${pokemon.species.id}" /><psicon type="${pokemon.teraType}" />`;
          }
          this.add(`${buf}`);
        }
      }
      this.makeRequest("teampreview");
    }
  },
  levelclausemod: {
    effectType: "Rule",
    name: "Level Clause Mod",
    desc: "Changes stat calculation to depend on the Pok&eacute;mon's level, which need not be 50.",
    onBegin() {
      this.add("rule", "Level Clause Mod: Pok\xE9mon levels are not fixed at 50, with stats calculated accordingly.");
    }
    // Implemented in mods/champions/scripts.ts
  },
  natdexmod: {
    effectType: "ValidatorRule",
    name: "NatDex Mod",
    desc: "Mechanics for National Dex formats",
    ruleset: [
      "+Unobtainable",
      "+Past",
      "Sketch Post-Gen 7 Moves"
    ]
    // implemented in the champions natdex draft format
  }
};
//# sourceMappingURL=rulesets.js.map
