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
  pursuit: {
    inherit: true,
    beforeTurnCallback(pokemon) {
      const linkedMoves = pokemon.getLinkedMoves();
      if (linkedMoves.length) {
        if (linkedMoves[0].id !== "pursuit" && linkedMoves[1].id === "pursuit") return;
      }
      for (const target of pokemon.foes()) {
        target.addVolatile("pursuit");
        const data = target.volatiles["pursuit"];
        if (!data.sources) {
          data.sources = [];
        }
        data.sources.push(pokemon);
      }
    }
  },
  mefirst: {
    inherit: true,
    onTryHit(target, pokemon) {
      const action = this.queue.willMove(target);
      if (!action) return false;
      const move = this.dex.getActiveMove(action.linked?.[0] || action.move.id);
      if (action.zmove || move.isZ || move.isMax) return false;
      if (target.volatiles["mustrecharge"]) return false;
      if (move.category === "Status" || move.flags["failmefirst"]) return false;
      pokemon.addVolatile("mefirst");
      this.actions.useMove(move, pokemon, { target });
      return null;
    }
  },
  // Modify Sucker Punch to check if both moves in a link are status
  suckerpunch: {
    inherit: true,
    onTry(source, target) {
      const action = this.queue.willMove(target);
      if (!action || action.choice !== "move") return false;
      if (!action.linked) {
        const move = action.move;
        if (move.category === "Status" && move.id !== "mefirst") {
          return false;
        }
      } else {
        if (action.linked.every((move) => move.category === "Status" && move.id !== "mefirst")) {
          return false;
        }
      }
      if (target.volatiles["mustrecharge"] && target.volatiles["mustrecharge"].duration < 2) {
        return false;
      }
    }
  },
  thunderclap: {
    inherit: true,
    onTry(source, target) {
      const action = this.queue.willMove(target);
      if (!action || action.choice !== "move") return false;
      if (!action.linked) {
        const move = action.move;
        if (move.category === "Status" && move.id !== "mefirst") {
          return false;
        }
      } else {
        if (action.linked.every((move) => move.category === "Status" && move.id !== "mefirst")) {
          return false;
        }
      }
      if (target.volatiles["mustrecharge"] && target.volatiles["mustrecharge"].duration < 2) {
        return false;
      }
    }
  },
  upperhand: {
    inherit: true,
    onTry(source, target) {
      const action = this.queue.willMove(target);
      if (!action || action.choice !== "move") return false;
      if (!action.linked) {
        const move = action.move;
        if (move.priority < 0.1 || move.category === "Status") {
          return false;
        }
      } else {
        if (action.linked.every((move) => move.priority < 0.1 || move.category === "Status")) {
          return false;
        }
      }
      if (target.volatiles["mustrecharge"] && target.volatiles["mustrecharge"].duration < 2) {
        return false;
      }
    }
  },
  encore: {
    inherit: true,
    condition: {
      duration: 3,
      noCopy: true,
      // doesn't get copied by Z-Baton Pass
      onStart(target) {
        let move = target.lastMove;
        if (!move || target.volatiles["dynamax"]) return false;
        if (move.isMax && move.baseMove) move = this.dex.moves.get(move.baseMove);
        const linkedMoves = target.getLinkedMoves(true);
        const moveSlot = target.getMoveData(move.id);
        const isLinkedMove = linkedMoves.some((x) => x.id === move.id);
        if (isLinkedMove && linkedMoves.every((m) => !!m.flags["failencore"])) {
          delete target.volatiles["encore"];
          return false;
        }
        if (move.isZ || move.isMax || move.flags["failencore"] || !moveSlot || moveSlot.pp <= 0) {
          return false;
        }
        this.effectState.timesActivated = {};
        this.effectState.move = move.id;
        this.add("-start", target, "Encore");
        if (isLinkedMove) {
          this.effectState.move = linkedMoves;
        }
        if (!this.queue.willMove(target)) {
          this.effectState.duration++;
        }
      },
      onOverrideAction(pokemon, target, move) {
        if (!this.effectState.timesActivated[this.turn]) {
          this.effectState.timesActivated[this.turn] = 0;
        } else if (this.effectState.timesActivated[this.turn] >= (Array.isArray(this.effectState.move) ? this.effectState.move.length : 1)) {
          return;
        }
        this.effectState.timesActivated[this.turn]++;
        if (!Array.isArray(this.effectState.move)) {
          this.queue.cancelAction(pokemon);
          if (move.id !== this.effectState.move) return this.effectState.move;
        } else {
          switch (this.effectState.timesActivated[this.turn]) {
            case 1: {
              if (this.effectState.move[0] !== move.id) return this.effectState.move[0];
              return;
            }
            case 2:
              if (this.effectState.move[1] !== move.id) return this.effectState.move[1];
              return;
          }
        }
      },
      onResidualOrder: 13,
      onResidual(target) {
        if (Array.isArray(this.effectState.move)) {
          if (this.effectState.move.map((move) => target.getMoveData(move)).some((moveSlot) => !moveSlot || moveSlot.pp <= 0)) {
            target.removeVolatile("encore");
          }
        } else {
          const moveSlot = target.getMoveData(this.effectState.move);
          if (!moveSlot || moveSlot.pp <= 0) {
            target.removeVolatile("encore");
          }
        }
      },
      onEnd(target) {
        this.add("-end", target, "Encore");
      },
      onDisableMove(pokemon) {
        if (!this.effectState.move) return;
        if (Array.isArray(this.effectState.move)) {
          if (this.effectState.move.every((move) => !pokemon.hasMove(move))) return;
          for (const moveSlot of pokemon.moveSlots) {
            if (!this.effectState.move.map((move) => move.id).includes(moveSlot.id)) {
              pokemon.disableMove(moveSlot.id);
            }
          }
        } else {
          if (!pokemon.hasMove(this.effectState.move)) return;
          for (const moveSlot of pokemon.moveSlots) {
            if (moveSlot.id !== this.effectState.move) {
              pokemon.disableMove(moveSlot.id);
            }
          }
        }
      }
    }
  },
  torment: {
    inherit: true,
    condition: {
      noCopy: true,
      onStart(pokemon, source, effect) {
        if (pokemon.volatiles["dynamax"]) {
          delete pokemon.volatiles["torment"];
          return false;
        }
        if (effect?.id === "gmaxmeltdown") this.effectState.duration = 3;
        this.add("-start", pokemon, "Torment");
      },
      onEnd(pokemon) {
        this.add("-end", pokemon, "Torment");
      },
      onDisableMove(pokemon) {
        const lastMove = pokemon.lastMove;
        if (!lastMove || lastMove.id === "struggle") return;
        pokemon.disableMove(lastMove.id);
        const { linkIndex, linkedMoves } = pokemon.queryLinkMove(lastMove);
        if (linkIndex >= 0) pokemon.disableMove(linkedMoves[1 - linkIndex].id);
      }
    }
  },
  // PP-decreasing moves
  grudge: {
    inherit: true,
    condition: {
      onStart(pokemon) {
        this.add("-singlemove", pokemon, "Grudge");
      },
      onFaint(target, source, effect) {
        if (!source || source.fainted || !effect) return;
        let move = source.lastMove;
        if (effect.effectType === "Move" && !effect.flags["futuremove"] && move) {
          if (move.isMax && move.baseMove) move = this.dex.moves.get(move.baseMove);
          for (const moveSlot of source.moveSlots) {
            if (moveSlot.id === move.id) {
              moveSlot.pp = 0;
              this.add("-activate", source, "move: Grudge", move.name);
            }
          }
        }
      },
      onBeforeMovePriority: 100,
      onBeforeMove(pokemon) {
        if (pokemon.moveThisTurn) return;
        this.debug("removing Grudge before attack");
        pokemon.removeVolatile("grudge");
      }
    }
  },
  // Other lastMove checks
  destinybond: {
    inherit: true,
    condition: {
      onStart(pokemon) {
        this.add("-singlemove", pokemon, "Destiny Bond");
      },
      onFaint(target, source, effect) {
        if (!source || !effect || target.isAlly(source)) return;
        if (effect.effectType === "Move" && !effect.flags["futuremove"]) {
          if (source.volatiles["dynamax"]) {
            this.add("-hint", "Dynamaxed Pok\xE9mon are immune to Destiny Bond.");
            return;
          }
          this.add("-activate", target, "move: Destiny Bond");
          source.faint();
        }
      },
      onBeforeMovePriority: -1,
      onBeforeMove(pokemon, target, move) {
        if (pokemon.moveThisTurn || move.id === "destinybond") return;
        this.debug("removing Destiny Bond before attack");
        pokemon.removeVolatile("destinybond");
      },
      onMoveAborted(pokemon, target, move) {
        pokemon.removeVolatile("destinybond");
      }
    }
  }
};
//# sourceMappingURL=moves.js.map
