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
  standard: {
    effectType: "ValidatorRule",
    name: "Standard",
    desc: "The standard ruleset for all official Smogon singles tiers (Ubers, OU, etc.)",
    ruleset: [
      "Standard AG",
      "Sleep Clause Mod",
      "Switch Priority Clause Mod",
      "Species Clause",
      "Nickname Clause",
      "OHKO Clause",
      "Evasion Items Clause",
      "Evasion Moves Clause"
    ]
  },
  standarddraft: {
    effectType: "ValidatorRule",
    name: "Standard Draft",
    desc: "The custom Draft League ruleset",
    ruleset: [
      "Obtainable",
      "Nickname Clause",
      "Beat Up Nicknames Mod",
      "+Unreleased",
      "Sleep Clause Mod",
      "OHKO Clause",
      "Evasion Clause",
      "Endless Battle Clause",
      "HP Percentage Mod",
      "Cancel Mod",
      "One Boost Passer Clause",
      "Freeze Clause Mod",
      "Accuracy Moves Clause",
      "Baton Pass Trap Clause"
    ],
    banlist: [
      "Uber",
      "Smeargle + Ingrain",
      "Swagger",
      "Focus Band",
      "King's Rock",
      "Quick Claw",
      "Baton Pass + Ancient Power",
      "Baton Pass + Silver Wind"
    ]
    // timer: {starting: 60 * 60, grace: 0, addPerTurn: 10, maxPerTurn: 100, timeoutAutoChoose: true},
  },
  obtainable: {
    inherit: true,
    onValidateSet(set) {
      const species = this.dex.species.get(set.species);
      if (["entei", "raikou", "suicune"].includes(species.id)) {
        if (!set.ivs) set.ivs = { hp: 31, atk: 31, def: 31, spa: 31, spd: 31, spe: 31 };
        for (const stat in set.ivs) {
          if (stat === "atk" && set.ivs[stat] > 7 || stat !== "hp" && set.ivs[stat] > 0) {
            return [
              `${set.name} must have 7 or fewer Attack IVs and 0 IVs in all other stats except HP, due to the Roaming IVs glitch.`
            ];
          }
        }
      }
    }
  }
};
//# sourceMappingURL=rulesets.js.map
