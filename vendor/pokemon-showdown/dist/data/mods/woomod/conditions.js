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
  frz: {
    onStart(target, source, sourceEffect) {
      this.add("-message", `${target.name} was frozen!`);
      this.hint(`Freeze halves SpA + 1/16 chip, like in Pokemon Legends: Arceus`);
      if (sourceEffect && sourceEffect.effectType === "Ability") {
        this.add("-status", target, "frz", "[from] ability: " + sourceEffect.name, `[of] ${source}`);
      } else {
        this.add("-status", target, "frz");
      }
    },
    onResidualOrder: 10,
    onResidual(pokemon) {
      this.damage(pokemon.baseMaxhp / 16);
    },
    onModifySpA(spa, pokemon) {
      return this.chainModify(0.5);
    }
  }
};
//# sourceMappingURL=conditions.js.map
