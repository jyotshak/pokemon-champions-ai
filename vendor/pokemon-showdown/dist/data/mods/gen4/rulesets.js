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
      "HP Percentage Mod",
      "Cancel Mod",
      "Beat Up Nicknames Mod",
      "Endless Battle Clause"
    ]
  },
  standard: {
    inherit: true,
    ruleset: [
      "Standard AG",
      "Sleep Clause Mod",
      "Species Clause",
      "Nickname Clause",
      "OHKO Clause",
      "Evasion Items Clause",
      "Evasion Moves Clause"
    ]
  },
  flatrules: {
    inherit: true,
    ruleset: ["Obtainable", "Species Clause", "Nickname Clause", "Item Clause = 1", "Adjust Level Down = 50", "Picked Team Size = Auto", "Cancel Mod"]
  },
  teampreview: {
    inherit: true,
    onTeamPreview() {
      this.add("clearpoke");
      for (const pokemon of this.getAllPokemon()) {
        const details = pokemon.details.replace(", shiny", "").replace(/(Arceus|Genesect|Gourgeist|Pumpkaboo|Xerneas|Silvally|Urshifu|Dudunsparce)(-[a-zA-Z?-]+)?/g, "$1-*").replace(/(Zacian|Zamazenta)(?!-Crowned)/g, "$1-*").replace(/(Greninja)(?!-Ash)/g, "$1-*");
        this.add("poke", pokemon.side.id, details, pokemon.item ? "item" : "");
      }
      this.makeRequest("teampreview");
    }
  }
};
//# sourceMappingURL=rulesets.js.map
