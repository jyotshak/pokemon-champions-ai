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
  slp: {
    inherit: true,
    onBeforeMove(pokemon, target, move) {
      if (this.effectState.timerDecreased !== this.turn) {
        this.effectState.timerDecreased = this.turn;
        if (pokemon.hasAbility("earlybird")) {
          pokemon.statusState.time--;
        }
        pokemon.statusState.time--;
        if (pokemon.statusState.time <= 0) {
          pokemon.cureStatus();
          return;
        }
        this.add("cant", pokemon, "slp");
      }
      if (move.sleepUsable) return;
      return false;
    }
  },
  frz: {
    inherit: true,
    onBeforeMove(pokemon, target, move) {
      if (move.flags["defrost"] && !(move.id === "burnup" && !pokemon.hasType("Fire"))) return;
      if (this.effectState.durationRolled !== this.turn && this.randomChance(1, 5)) {
        pokemon.cureStatus();
        return;
      }
      if (this.effectState.durationRolled !== this.turn) {
        this.effectState.durationRolled = this.turn;
        this.add("cant", pokemon, "frz");
      }
      return false;
    }
  },
  confusion: {
    inherit: true,
    onBeforeMove(pokemon) {
      if (this.effectState.timerDecreased !== this.turn) {
        this.effectState.timerDecreased = this.turn;
        pokemon.volatiles.confusion.time--;
        if (!pokemon.volatiles.confusion.time) {
          pokemon.removeVolatile("confusion");
          return;
        }
      }
      this.add("-activate", pokemon, "confusion");
      if (!this.randomChance(33, 100)) {
        return;
      }
      this.activeTarget = pokemon;
      const damage = this.actions.getConfusionDamage(pokemon, 40);
      if (typeof damage !== "number") throw new Error("Confusion damage not dealt");
      const activeMove = { id: this.toID("confused"), effectType: "Move", type: "???" };
      this.damage(damage, pokemon, pokemon, activeMove);
      return false;
    }
  },
  gem: {
    inherit: true,
    onBeforeMove(pokemon) {
      if (pokemon.moveThisTurn) pokemon.removeVolatile("gem");
    }
  },
  // Prior to Gen 9, using these moves as part of a link resulted in locking into an entire link.
  // However, such behavior has since been deemed counter-intuitive.
  // https://www.smogon.com/forums/threads/3776838
  //
  // Outrage/Thrash/Petal Dance should be consistent with Choice items.
  lockedmove: {
    inherit: true,
    onStart(target, source, effect) {
      this.effectState.trueDuration = this.random(2, 4);
      this.effectState.move = effect.id;
      this.queue.cancelMove(source);
    }
  },
  // A general rule of thumb to keep in mind is that all effects of move 1
  // will follow through before the next move activates. However, apparently,
  // moves such as Skull Bash/Meteor Beam/etc never respected that prior to Gen 9.
  //
  // Ensure we lock into Skull Bash/Meteor Beam/etc.
  twoturnmove: {
    inherit: true,
    onOverrideAction(pokemon, target, move) {
      return this.effectState.move;
    }
  }
};
//# sourceMappingURL=conditions.js.map
