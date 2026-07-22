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
  allyswitch: {
    inherit: true,
    priority: 1
  },
  assist: {
    inherit: true,
    flags: { noassist: 1, failcopycat: 1, nosleeptalk: 1 }
  },
  copycat: {
    inherit: true,
    flags: { noassist: 1, failcopycat: 1, nosleeptalk: 1 }
  },
  darkvoid: {
    inherit: true,
    accuracy: 80,
    onTry: void 0
    // no inherit
  },
  destinybond: {
    inherit: true,
    onPrepareHit(pokemon) {
      pokemon.removeVolatile("destinybond");
    }
  },
  diamondstorm: {
    inherit: true,
    self: void 0,
    // no inherit
    secondary: {
      chance: 50,
      self: {
        boosts: {
          def: 1
        }
      }
    }
  },
  fellstinger: {
    inherit: true,
    basePower: 30,
    onAfterMoveSecondarySelf(pokemon, target, move) {
      if (!target || target.fainted || target.hp <= 0) this.boost({ atk: 2 }, pokemon, pokemon, move);
    }
  },
  flyingpress: {
    inherit: true,
    basePower: 80
  },
  heavyslam: {
    inherit: true,
    flags: { contact: 1, protect: 1, mirror: 1, nonsky: 1, metronome: 1 }
  },
  leechlife: {
    inherit: true,
    basePower: 20,
    pp: 15
  },
  mefirst: {
    inherit: true,
    flags: { protect: 1, bypasssub: 1, noassist: 1, failcopycat: 1, failmefirst: 1, nosleeptalk: 1 }
  },
  metronome: {
    inherit: true,
    flags: { noassist: 1, failcopycat: 1, nosleeptalk: 1 }
  },
  mistyterrain: {
    inherit: true,
    condition: {
      inherit: true,
      onTryAddVolatile: void 0
      // no inherit
    }
  },
  mysticalfire: {
    inherit: true,
    basePower: 65
  },
  naturepower: {
    inherit: true,
    flags: { nosleeptalk: 1, noassist: 1, failcopycat: 1 }
  },
  paraboliccharge: {
    inherit: true,
    basePower: 50
  },
  partingshot: {
    inherit: true,
    onHit(target, source) {
      this.boost({ atk: -1, spa: -1 }, target, source);
    }
  },
  phantomforce: {
    inherit: true,
    flags: { contact: 1, charge: 1, mirror: 1, metronome: 1, nosleeptalk: 1, noassist: 1, failinstruct: 1, minimize: 1 }
  },
  powder: {
    inherit: true,
    condition: {
      inherit: true,
      onTryMovePriority: 1
    }
  },
  rockblast: {
    inherit: true,
    flags: { protect: 1, mirror: 1, metronome: 1 }
  },
  shadowforce: {
    inherit: true,
    flags: { contact: 1, charge: 1, mirror: 1, metronome: 1, nosleeptalk: 1, noassist: 1, failinstruct: 1, minimize: 1 }
  },
  sheercold: {
    inherit: true,
    ohko: true
  },
  sleeptalk: {
    inherit: true,
    flags: { nosleeptalk: 1, noassist: 1, failcopycat: 1 }
  },
  stockpile: {
    inherit: true,
    condition: {
      noCopy: true,
      onStart(target) {
        this.effectState.layers = 1;
        this.add("-start", target, "stockpile" + this.effectState.layers);
        this.boost({ def: 1, spd: 1 }, target, target);
      },
      onRestart(target) {
        if (this.effectState.layers >= 3) return false;
        this.effectState.layers++;
        this.add("-start", target, "stockpile" + this.effectState.layers);
        this.boost({ def: 1, spd: 1 }, target, target);
      },
      onEnd(target) {
        const layers = this.effectState.layers * -1;
        this.effectState.layers = 0;
        this.boost({ def: layers, spd: layers }, target, target);
        this.add("-end", target, "Stockpile");
      }
    }
  },
  suckerpunch: {
    inherit: true,
    basePower: 80
  },
  swagger: {
    inherit: true,
    accuracy: 90
  },
  tackle: {
    inherit: true,
    basePower: 50
  },
  thousandarrows: {
    inherit: true,
    isNonstandard: "Unobtainable"
  },
  thousandwaves: {
    inherit: true,
    isNonstandard: "Unobtainable"
  },
  thunderwave: {
    inherit: true,
    accuracy: 100
  },
  watershuriken: {
    inherit: true,
    category: "Physical"
  },
  wideguard: {
    inherit: true,
    condition: {
      inherit: true,
      onTryHit(target, source, move) {
        if (move.category === "Status" || move?.target !== "allAdjacent" && move.target !== "allAdjacentFoes") {
          return;
        }
        if (this.checkMoveBypassesProtect(move, source, target, false)) return;
        this.add("-activate", target, "move: Wide Guard");
        const lockedmove = source.getVolatile("lockedmove");
        if (lockedmove) {
          if (source.volatiles["lockedmove"].duration === 2) {
            delete source.volatiles["lockedmove"];
          }
        }
        return null;
      }
    }
  }
};
//# sourceMappingURL=moves.js.map
