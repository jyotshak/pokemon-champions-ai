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
const Abilities = {
  angershell: {
    inherit: true,
    onDamage(damage, target, source, effect) {
      this.effectState.checkedAngerShell = !(effect.effectType === "Move" && !effect.multihit);
    }
  },
  berserk: {
    inherit: true,
    onDamage(damage, target, source, effect) {
      this.effectState.checkedBerserk = !(effect.effectType === "Move" && !effect.multihit);
    }
  },
  disguise: {
    inherit: true,
    onEffectiveness(typeMod, target, type, move) {
      if (!target || move.category === "Status") return;
      if (move.hit === 1) delete this.effectState.neutral;
      if (this.effectState.neutral) return 0;
      if (!["mimikyu", "mimikyutotem"].includes(target.species.id)) {
        return;
      }
      const hitSub = target.volatiles["substitute"] && !move.flags["bypasssub"] && !(move.infiltrates && this.gen >= 6);
      if (hitSub) return;
      if (!target.runImmunity(move)) return;
      this.effectState.neutral = true;
      return 0;
    }
  },
  dragonize: {
    inherit: true,
    isNonstandard: null
  },
  eelevate: {
    inherit: true,
    isNonstandard: null
  },
  firemane: {
    inherit: true,
    isNonstandard: null
  },
  healer: {
    inherit: true,
    onResidual(pokemon) {
      for (const allyActive of pokemon.adjacentAllies()) {
        if (allyActive.status && this.randomChance(1, 2)) {
          this.add("-activate", pokemon, "ability: Healer");
          allyActive.cureStatus();
        }
      }
    },
    desc: "50% chance this Pokemon's ally has its non-volatile status condition cured at the end of each turn.",
    shortDesc: "50% chance this Pokemon's ally has its status cured at the end of each turn."
  },
  megasol: {
    inherit: true,
    isNonstandard: null
  },
  naturalcure: {
    inherit: true,
    onCheckShow: void 0,
    // no inherit
    onSwitchOut(pokemon) {
      if (!pokemon.status || pokemon.status === "fnt") return;
      this.add("-curestatus", pokemon, pokemon.status, "[from] ability: Natural Cure", "[silent]");
      pokemon.clearStatus();
    }
  },
  piercingdrill: {
    inherit: true,
    isNonstandard: null
  },
  regenerator: {
    inherit: true,
    onSwitchOut(pokemon) {
      if (pokemon.heal(pokemon.baseMaxhp / 3)) {
        this.add("-heal", pokemon, pokemon.getHealth, "[from] ability: Regenerator", "[silent]");
      }
    }
  },
  spicyspray: {
    inherit: true,
    isNonstandard: null
  },
  unseenfist: {
    onModifyMove: void 0,
    // no inherit
    onHitProtect(source, target, move) {
      if (move.flags["contact"]) {
        target.getMoveHitData(move).bypassProtect = this.effect;
        return false;
      }
    },
    inherit: true,
    shortDesc: "This Pokemon's contact moves ignore a target's protection and deal 1/4 the usual damage."
  }
};
//# sourceMappingURL=abilities.js.map
