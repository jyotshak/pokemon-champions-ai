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
var typechart_exports = {};
__export(typechart_exports, {
  TypeChart: () => TypeChart
});
module.exports = __toCommonJS(typechart_exports);
const TypeChart = {
  fairy: {
    damageTaken: {
      Bug: 2,
      Dark: 2,
      Dragon: 3,
      Electric: 0,
      Fairy: 0,
      Fighting: 2,
      Fire: 0,
      Flying: 0,
      Ghost: 0,
      Grass: 0,
      Ground: 0,
      Ice: 0,
      Normal: 1,
      Poison: 1,
      Psychic: 0,
      Rock: 0,
      Steel: 1,
      Stellar: 0,
      Water: 0
    }
  },
  ghost: {
    inherit: true,
    damageTaken: {
      Bug: 3,
      Dark: 1,
      Dragon: 1,
      Electric: 1,
      Fairy: 3,
      Fighting: 3,
      Fire: 1,
      Flying: 3,
      Ghost: 3,
      Grass: 1,
      Ground: 3,
      Ice: 1,
      Normal: 3,
      Poison: 3,
      Psychic: 1,
      Rock: 3,
      Steel: 3,
      Stellar: 0,
      Water: 1
    }
  }
};
//# sourceMappingURL=typechart.js.map
