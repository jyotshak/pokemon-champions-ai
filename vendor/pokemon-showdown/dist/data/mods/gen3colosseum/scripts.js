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
var scripts_exports = {};
__export(scripts_exports, {
  Scripts: () => Scripts
});
module.exports = __toCommonJS(scripts_exports);
const Scripts = {
  inherit: "gen3",
  gen: 3,
  checkWin(faintData) {
    if (this.sides.every((side) => !side.pokemonLeft)) {
      let isSelfKo = false;
      if (faintData?.effect) {
        isSelfKo = isSelfKo || this.dex.moves.getByID(faintData?.effect?.id).selfdestruct !== void 0;
        isSelfKo = isSelfKo || this.dex.moves.getByID(faintData?.effect?.id).recoil !== void 0;
      }
      if (isSelfKo) {
        this.win(faintData ? faintData.target.side : null);
        return true;
      } else {
        this.win(void 0);
        return true;
      }
    }
    for (const side of this.sides) {
      if (!side.foePokemonLeft()) {
        this.win(side);
        return true;
      }
    }
  }
};
//# sourceMappingURL=scripts.js.map
