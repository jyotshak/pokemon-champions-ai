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
var moves_exports = {};
__export(moves_exports, {
  Moves: () => Moves
});
module.exports = __toCommonJS(moves_exports);
const Moves = {
  perishsong: {
    inherit: true,
    onTryMove(attacker, defender, move) {
      if (attacker.side.pokemonLeft === 1) {
        this.add("-fail", attacker, "move: Perish Song");
        this.hint("Self KO Clause: The last pokemon on a team cannot use moves that force fainting");
        return false;
      }
    }
  },
  destinybond: {
    inherit: true,
    onTryMove(attacker, defender, move) {
      if (attacker.side.pokemonLeft === 1) {
        this.add("-fail", attacker, "move: Perish Song");
        this.hint("Self KO Clause: The last pokemon on a team cannot use moves that force fainting");
        return false;
      }
    }
  }
};
//# sourceMappingURL=moves.js.map
