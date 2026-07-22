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
  par: {
    inherit: true,
    onBeforeMove(pokemon) {
      if (this.randomChance(1, 8)) {
        this.add("cant", pokemon, "par");
        return false;
      }
    }
  },
  slp: {
    inherit: true,
    onStart(target, source, sourceEffect) {
      if (sourceEffect && sourceEffect.effectType === "Ability") {
        this.add("-status", target, "slp", "[from] ability: " + sourceEffect.name, `[of] ${source}`);
      } else if (sourceEffect && sourceEffect.effectType === "Move") {
        this.add("-status", target, "slp", `[from] move: ${sourceEffect.name}`);
      } else {
        this.add("-status", target, "slp");
      }
      this.effectState.startTime = this.sample([2, 3, 3]);
      this.effectState.time = this.effectState.startTime;
      if (target.removeVolatile("nightmare")) {
        this.add("-end", target, "Nightmare", "[silent]");
      }
    }
  },
  frz: {
    inherit: true,
    onStart(target, source, sourceEffect) {
      if (sourceEffect && sourceEffect.effectType === "Ability") {
        this.add("-status", target, "frz", "[from] ability: " + sourceEffect.name, `[of] ${source}`);
      } else {
        this.add("-status", target, "frz");
      }
      if (target.species.name === "Shaymin-Sky" && target.baseSpecies.baseSpecies === "Shaymin") {
        target.formeChange("Shaymin", this.effect, true);
      }
      this.effectState.startTime = 3;
      this.effectState.time = this.effectState.startTime;
    },
    onBeforeMove(pokemon, target, move) {
      if (move.flags["defrost"] && !(move.id === "burnup" && !pokemon.hasType("Fire"))) return;
      pokemon.statusState.time--;
      if (pokemon.statusState.time <= 0 || this.randomChance(1, 4)) {
        pokemon.cureStatus();
        return;
      }
      this.add("cant", pokemon, "frz");
      return false;
    }
  }
};
//# sourceMappingURL=conditions.js.map
