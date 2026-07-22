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
var pokedex_exports = {};
__export(pokedex_exports, {
  Pokedex: () => Pokedex
});
module.exports = __toCommonJS(pokedex_exports);
const Pokedex = {
  pikachu: {
    inherit: true,
    evos: ["Raichu"]
  },
  quilava: {
    inherit: true,
    evos: ["Typhlosion-Hisui"]
  },
  cherrimsunshine: {
    inherit: true,
    baseStats: { hp: 70, atk: 90, def: 70, spa: 87, spd: 117, spe: 85 }
  },
  mimejr: {
    inherit: true,
    evos: ["Mr. Mime"]
  },
  dewott: {
    inherit: true,
    evos: ["Samurott-Hisui"]
  },
  petilil: {
    inherit: true,
    evos: ["Lilligant-Hisui"]
  },
  rufflet: {
    inherit: true,
    evos: ["Braviary-Hisui"]
  },
  goomy: {
    inherit: true,
    evos: ["Sliggoo-Hisui"]
  },
  bergmite: {
    inherit: true,
    evos: ["Avalugg-Hisui"]
  },
  dartrix: {
    inherit: true,
    evos: ["Decidueye-Hisui"]
  }
};
//# sourceMappingURL=pokedex.js.map
