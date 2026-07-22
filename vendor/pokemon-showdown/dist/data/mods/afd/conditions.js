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
var conditions_exports = {};
__export(conditions_exports, {
  Conditions: () => Conditions
});
module.exports = __toCommonJS(conditions_exports);
const Conditions = {
  sandstorm: {
    inherit: true,
    onWeatherModifyDamage(damage, attacker, defender, move) {
      if (defender.hasItem("utilityumbrella")) return;
      if (move.type === "Rock") {
        this.debug("Sandstorm rock boost");
        return this.chainModify(1.5);
      }
    }
  },
  snowscape: {
    inherit: true,
    onModifySpePriority: 10,
    onModifySpe(spe, pokemon) {
      if (!pokemon.getTypes(false, true).includes("Ice") && !pokemon.getTypes(false, true).includes("Steel") && !pokemon.hasAbility(["slushrush", "snowcloak", "iceface", "icebody"]) && pokemon.effectiveWeather() === "snowscape") {
        return this.modify(spe, 0.5);
      }
    }
  }
};
//# sourceMappingURL=conditions.js.map
