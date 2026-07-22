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
var abilities_exports = {};
__export(abilities_exports, {
  Abilities: () => Abilities
});
module.exports = __toCommonJS(abilities_exports);
function attemptStatuses(battle, target, source, move, status) {
  const attackerStatused = source.trySetStatus(status, target);
  if (move.multihit && move.id !== "triplekick" && (move.lastHit || attackerStatused && status === "slp") && battle.randomChance(1, 100)) {
    const defenderStatused = target.trySetStatus(status, target, move);
    if (defenderStatused) {
      battle.hint("In Pokemon Ruby, Sapphire, FireRed, LeafGreen, and Colosseum, if the final hit of a multihit move (except for Triple Kick) that makes contact triggers an ability that inflicts status, then there is a 1% chance that the defender is afflicted by the same status.");
    }
  }
}
const Abilities = {
  effectspore: {
    inherit: true,
    onDamagingHit(damage, target, source, move) {
      if (damage && move.flags["contact"] && !source.status) {
        const r = this.random(300);
        let status = null;
        if (r < 10) {
          status = "slp";
        } else if (r < 20) {
          status = "par";
        } else if (r < 30) {
          status = "psn";
        }
        if (status) {
          attemptStatuses(this, target, source, move, status);
        }
      }
    }
  },
  flamebody: {
    inherit: true,
    onDamagingHit(damage, target, source, move) {
      if (damage && move.flags["contact"]) {
        if (this.randomChance(1, 3)) {
          attemptStatuses(this, target, source, move, "brn");
        }
      }
    }
  },
  poisonpoint: {
    inherit: true,
    onDamagingHit(damage, target, source, move) {
      if (damage && move.flags["contact"]) {
        if (this.randomChance(1, 3)) {
          attemptStatuses(this, target, source, move, "psn");
        }
      }
    }
  },
  static: {
    inherit: true,
    onDamagingHit(damage, target, source, move) {
      if (damage && move.flags["contact"]) {
        if (this.randomChance(1, 3)) {
          attemptStatuses(this, target, source, move, "par");
        }
      }
    }
  }
};
//# sourceMappingURL=abilities.js.map
