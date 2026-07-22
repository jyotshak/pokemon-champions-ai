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
  acid: {
    inherit: true,
    secondary: {
      chance: 33,
      boosts: {
        def: -1
      }
    },
    target: "normal"
  },
  amnesia: {
    inherit: true,
    boosts: {
      spa: 2,
      spd: 2
    }
  },
  aurorabeam: {
    inherit: true,
    secondary: {
      chance: 33,
      boosts: {
        atk: -1
      }
    }
  },
  bide: {
    inherit: true,
    accuracy: true,
    condition: {
      onStart(pokemon) {
        this.effectState.damage = 0;
        this.effectState.time = this.random(2, 4);
        this.add("-start", pokemon, "Bide");
      },
      onBeforeMove(pokemon, t, move) {
        const currentMove = this.dex.getActiveMove("bide");
        this.effectState.damage += this.lastDamage;
        this.effectState.time--;
        if (!this.effectState.time) {
          this.add("-end", pokemon, currentMove);
          if (!this.effectState.damage) {
            this.debug("Bide failed because no damage was stored");
            this.add("-fail", pokemon);
            pokemon.removeVolatile("bide");
            return false;
          }
          const target = this.getRandomTarget(pokemon, "Pound");
          this.actions.moveHit(target, pokemon, currentMove, { damage: this.effectState.damage * 2 });
          pokemon.removeVolatile("bide");
          return false;
        }
        this.add("-activate", pokemon, "Bide");
        return false;
      },
      onSemiLockMove: "bide",
      onDisableMove(target) {
        target.maybeLocked = false;
      }
    },
    type: "???"
    // Will look as Normal but it's STAB-less
  },
  bind: {
    inherit: true,
    ignoreImmunity: true,
    self: {
      volatileStatus: "partialtrappinglock"
    },
    onTryMove(source, target) {
      if (target.volatiles["mustrecharge"]) {
        target.removeVolatile("mustrecharge");
        this.hint("In Gen 1, partial trapping moves negate the recharge turn of Hyper Beam, even if they miss.", true);
      }
    }
  },
  bite: {
    inherit: true,
    category: "Physical",
    secondary: {
      chance: 10,
      volatileStatus: "flinch"
    },
    type: "Normal"
  },
  blizzard: {
    inherit: true,
    accuracy: 90,
    target: "normal"
  },
  bubble: {
    inherit: true,
    secondary: {
      chance: 33,
      boosts: {
        spe: -1
      }
    },
    target: "normal"
  },
  bubblebeam: {
    inherit: true,
    secondary: {
      chance: 33,
      boosts: {
        spe: -1
      }
    }
  },
  clamp: {
    inherit: true,
    accuracy: 75,
    pp: 10,
    self: {
      volatileStatus: "partialtrappinglock"
    },
    onTryMove(source, target) {
      if (target.volatiles["mustrecharge"]) {
        target.removeVolatile("mustrecharge");
        this.hint("In Gen 1, partial trapping moves negate the recharge turn of Hyper Beam, even if they miss.", true);
      }
    }
  },
  constrict: {
    inherit: true,
    secondary: {
      chance: 33,
      boosts: {
        spe: -1
      }
    }
  },
  conversion: {
    inherit: true,
    target: "normal",
    onHit(target, source) {
      source.setType(target.getTypes(true));
      this.add("-start", source, "typechange", source.types.join("/"), "[from] move: Conversion", `[of] ${target}`);
    }
  },
  counter: {
    inherit: true,
    ignoreImmunity: true,
    willCrit: false,
    basePower: 1,
    damageCallback(pokemon, target) {
      const isCounterable = (move) => {
        if (!move) {
          throw new Error(`Gen 1 Counter: move is null. It should have been initialized to {basePower: 0, type: 'Normal'}.`);
        }
        return ["Normal", "Fighting"].includes(move.type) && move.basePower > 0;
      };
      const isLastEnemySelectedMoveCounterable = target.side.lastEnemySelectedMove !== "counter";
      const isLastEnemyMoveCounterable = isCounterable(target.side.lastEnemyMove);
      const isLastSelectedMoveCounterable = target.side.lastSelectedMove !== "counter";
      const isLastMoveCounterable = isCounterable(target.side.lastMove);
      const isLastDamageNonZero = this.lastDamage > 0;
      const willCounterSucceed = isLastEnemySelectedMoveCounterable && isLastEnemyMoveCounterable && isLastDamageNonZero;
      if (!willCounterSucceed) {
        if (isLastDamageNonZero) {
          if (!isLastEnemySelectedMoveCounterable && isLastSelectedMoveCounterable) {
            if (isLastEnemyMoveCounterable) {
              this.hint("Desync Clause Mod activated!");
              this.hint(
                "In Gen 1, if Counter is used against a target that switched in and spent the turn sleeping, from the Counter user's perspective, it will fail if the move in the target's first slot is also Counter."
              );
            }
          } else if (!isLastEnemyMoveCounterable && isLastMoveCounterable) {
            this.hint("Desync Clause Mod activated!", false, target.side);
            this.hint(
              "In Gen 1, from the Counter user's perspective, Counter uses the last announced move by the target's team to determine if it will succeed.",
              false,
              target.side
            );
          }
        }
        this.add("-fail", pokemon);
        return false;
      }
      if (!isLastSelectedMoveCounterable) {
      } else if (!isLastMoveCounterable) {
        this.hint("Desync Clause Mod activated!", false, target.side);
        this.hint(
          "In Gen 1, from the Counter user's perspective, Counter uses the last announced move by the target's team to determine if it will succeed.",
          false,
          target.side
        );
      }
      return 2 * this.lastDamage;
    },
    flags: { contact: 1, protect: 1, metronome: 1 }
  },
  crabhammer: {
    inherit: true,
    critRatio: 2
  },
  dig: {
    inherit: true,
    basePower: 100,
    condition: {},
    onTryMove(attacker, defender, move) {
      if (attacker.removeVolatile("twoturnmove")) {
        attacker.removeVolatile("invulnerability");
        return;
      }
      this.add("-prepare", attacker, move.name);
      attacker.addVolatile("twoturnmove", defender);
      attacker.addVolatile("invulnerability", defender);
      return null;
    }
  },
  disable: {
    inherit: true,
    onTryHit(target) {
      return target.moveSlots.some((ms) => ms.pp > 0);
    },
    condition: {
      inherit: true,
      durationCallback: void 0,
      // no inherit
      onStart(pokemon) {
        const [slotIndex, moveSlot] = this.sample(Array.from(pokemon.moveSlots.entries()).filter(([i, ms]) => ms.pp > 0));
        this.debug(`Disable: disabling move ${moveSlot.move} in slot ${slotIndex}`);
        this.add("-start", pokemon, "Disable", moveSlot.move);
        this.effectState.move = moveSlot.id;
        this.effectState.slotIndex = slotIndex;
        this.effectState.time = this.random(1, 9);
      },
      onBeforeMovePriority: 6,
      onBeforeMove(pokemon, target, move) {
        pokemon.volatiles["disable"].time--;
        if (!pokemon.volatiles["disable"].time) {
          pokemon.removeVolatile("disable");
          return;
        }
        if (pokemon.volatiles["bide"]) move = this.dex.getActiveMove("bide");
        if (move.id === this.effectState.move) {
          this.add("cant", pokemon, "Disable", move);
          pokemon.removeVolatile("twoturnmove");
          return false;
        }
      },
      onDisableMove(pokemon) {
        if (pokemon.moveSlots.length > this.effectState.slotIndex) {
          pokemon.moveSlots[this.effectState.slotIndex].disabled = true;
          pokemon.moveSlots[this.effectState.slotIndex].disabledSource = this.effect.name;
        }
      }
    }
  },
  dizzypunch: {
    inherit: true,
    secondary: void 0
    // no inherit
  },
  doubleedge: {
    inherit: true,
    basePower: 100
  },
  dragonrage: {
    inherit: true,
    basePower: 1
  },
  explosion: {
    inherit: true,
    basePower: 170,
    target: "normal"
  },
  fireblast: {
    inherit: true,
    secondary: {
      chance: 30,
      status: "brn"
    }
  },
  firespin: {
    inherit: true,
    accuracy: 70,
    basePower: 15,
    self: {
      volatileStatus: "partialtrappinglock"
    },
    onTryMove(source, target) {
      if (target.volatiles["mustrecharge"]) {
        target.removeVolatile("mustrecharge");
        this.hint("In Gen 1, partial trapping moves negate the recharge turn of Hyper Beam, even if they miss.", true);
      }
    }
  },
  fly: {
    inherit: true,
    condition: {},
    onTryMove(attacker, defender, move) {
      if (attacker.removeVolatile("twoturnmove")) {
        attacker.removeVolatile("invulnerability");
        return;
      }
      this.add("-prepare", attacker, move.name);
      attacker.addVolatile("twoturnmove", defender);
      attacker.addVolatile("invulnerability", defender);
      return null;
    }
  },
  focusenergy: {
    inherit: true,
    condition: {
      inherit: true,
      // This does nothing as it's dealt with on critical hit calculation.
      onModifyCritRatio: void 0
      // no inherit
    }
  },
  glare: {
    inherit: true,
    ignoreImmunity: true
  },
  growth: {
    inherit: true,
    boosts: {
      spa: 1,
      spd: 1
    }
  },
  gust: {
    inherit: true,
    type: "Normal"
  },
  haze: {
    inherit: true,
    onHit(target, source) {
      this.add("-activate", target, "move: Haze");
      this.add("-clearallboost", "[silent]");
      for (const pokemon of this.getAllActive()) {
        pokemon.clearBoosts();
        if (pokemon !== source) {
          if (["frz", "slp"].includes(pokemon.status)) {
            pokemon.side.lastSelectedMove = "cannotmove";
            pokemon.side.lastEnemySelectedMove = "cannotmove";
            if (this.queue.willMove(pokemon)) {
              this.queue.changeAction(pokemon, { choice: "move", pokemon, moveid: "cannotmove" });
            }
          }
          pokemon.cureStatus(true);
        }
        if (pokemon.status === "tox") {
          pokemon.setStatus("psn", null, null, true);
        }
        pokemon.updateSpeed();
        const silentHack = "|[silent]";
        const silentHackVolatiles = ["disable", "confusion"];
        const hazeVolatiles = {
          "disable": "",
          "confusion": "",
          "mist": "Mist",
          "focusenergy": "move: Focus Energy",
          "leechseed": "move: Leech Seed",
          "lightscreen": "Light Screen",
          "reflect": "Reflect",
          "residualdmg": "Toxic counter"
        };
        for (const v in hazeVolatiles) {
          if (!pokemon.removeVolatile(v)) {
            continue;
          }
          if (silentHackVolatiles.includes(v)) {
            this.log[this.log.length - 1] += silentHack;
          } else {
            this.add("-end", pokemon, hazeVolatiles[v], "[silent]");
          }
        }
      }
    },
    target: "self"
  },
  highjumpkick: {
    inherit: true,
    onMoveFail(target, source, move) {
      this.directDamage(1, source, target);
    }
  },
  jumpkick: {
    inherit: true,
    onMoveFail(target, source, move) {
      this.directDamage(1, source, target);
    }
  },
  karatechop: {
    inherit: true,
    critRatio: 2,
    type: "Normal"
  },
  leechseed: {
    inherit: true,
    onHit: void 0,
    // no inherit
    condition: {
      inherit: true,
      onAfterMoveSelfPriority: 1,
      onAfterMoveSelf(pokemon) {
        const leecher = this.getAtSlot(pokemon.volatiles["leechseed"].sourceSlot);
        if (!leecher || leecher.fainted || leecher.hp <= 0) {
          this.debug("Nothing to leech into");
          return;
        }
        let toxicCounter = 1;
        const residualdmg = pokemon.volatiles["residualdmg"];
        if (residualdmg) {
          residualdmg.counter++;
          toxicCounter = residualdmg.counter;
        }
        const toLeech = this.clampIntRange(Math.floor(pokemon.baseMaxhp / 16), 1) * toxicCounter;
        const damage = this.damage(toLeech, pokemon, leecher);
        if (residualdmg) this.hint("In Gen 1, Leech Seed's damage is affected by Toxic's counter.", true);
        if (!damage || toLeech > damage) {
          this.hint("In Gen 1, Leech Seed recovery is not limited by the remaining HP of the seeded Pokemon.", true);
        }
        this.heal(toLeech, leecher, pokemon);
      }
    }
  },
  lightscreen: {
    inherit: true,
    volatileStatus: "lightscreen",
    sideCondition: void 0,
    // no inherit
    onTryHit(pokemon) {
      if (pokemon.volatiles["lightscreen"]) {
        return false;
      }
    },
    condition: {
      onStart(pokemon) {
        this.add("-start", pokemon, "Light Screen");
      }
    },
    target: "self"
  },
  metronome: {
    inherit: true,
    onHit(pokemon) {
      const moves = this.dex.moves.all().filter((move) => (!move.isNonstandard || move.isNonstandard === "Unobtainable") && move.flags["metronome"]);
      let randomMove = "";
      if (moves.length) {
        moves.sort((a, b) => a.num - b.num);
        randomMove = this.sample(moves).id;
      }
      if (!randomMove) return false;
      pokemon.side.lastSelectedMove = this.toID(randomMove);
      pokemon.side.lastEnemySelectedMove = pokemon.side.lastSelectedMove;
      this.actions.useMove(randomMove, pokemon);
    }
  },
  mimic: {
    inherit: true,
    flags: { protect: 1, bypasssub: 1, metronome: 1 },
    onHit(target, source) {
      const moveslot = source.side.lastSelectedMoveSlot;
      const moves = target.moves;
      const moveid = this.sample(moves);
      if (!moveid) return false;
      const move = this.dex.moves.get(moveid);
      source.moveSlots[moveslot] = {
        move: move.name,
        id: move.id,
        pp: source.moveSlots[moveslot].pp,
        maxpp: this.calculatePP(move, source.ppUps[moveslot] || 0),
        target: move.target,
        disabled: false,
        used: false,
        virtual: true
      };
      this.add("-start", source, "Mimic", move.name);
    }
  },
  minimize: {
    inherit: true,
    condition: {
      inherit: true,
      onSourceModifyDamage: void 0
      // no inherit
    }
  },
  mirrormove: {
    inherit: true,
    onHit(pokemon) {
      const foe = pokemon.side.foe.active[0];
      if (!foe?.lastMove || foe.lastMove.id === "mirrormove") {
        return false;
      }
      pokemon.side.lastSelectedMove = foe.lastMove.id;
      pokemon.side.lastEnemySelectedMove = pokemon.side.lastSelectedMove;
      this.actions.useMove(foe.lastMove.id, pokemon);
    }
  },
  mist: {
    inherit: true,
    condition: {
      inherit: true,
      onTryBoost(boost, target, source, effect) {
        if (effect.effectType === "Move" && effect.category !== "Status") return;
        if (source && target !== source) {
          let showMsg = false;
          let i;
          for (i in boost) {
            if (boost[i] < 0) {
              delete boost[i];
              showMsg = true;
            }
          }
          if (showMsg && !effect.secondaries) {
            this.add("-activate", target, "move: Mist");
          }
        }
      }
    }
  },
  nightshade: {
    inherit: true,
    ignoreImmunity: true,
    basePower: 1
  },
  petaldance: {
    inherit: true,
    onMoveFail: void 0
    // no inherit
  },
  poisonsting: {
    inherit: true,
    secondary: {
      chance: 20,
      status: "psn"
    }
  },
  psychic: {
    inherit: true,
    secondary: {
      chance: 33,
      boosts: {
        spa: -1,
        spd: -1
      }
    }
  },
  psywave: {
    inherit: true,
    basePower: 1,
    damageCallback(pokemon) {
      if ((pokemon.level + (pokemon.level >> 1) & 255) < 2) {
        this.hint("In Gen 1, if a Pok\xE9mon at level 0, 1 or 171 uses Psywave, the game softlocks.");
        return false;
      }
      const psywaveDamage = this.random(1, this.trunc(1.5 * pokemon.level));
      return psywaveDamage;
    }
  },
  rage: {
    inherit: true,
    self: {
      volatileStatus: "rage"
    },
    condition: {
      // Rage lock
      onStart(target, source, effect) {
        this.effectState.move = "rage";
        this.effectState.accuracy = 255;
      },
      onLockMove: "rage",
      onHit(target, source, move) {
        if (target.boosts.atk < 6 && (move.category !== "Status" && !move.selfdestruct)) {
          this.boost({ atk: 1 });
        }
      }
    }
  },
  razorleaf: {
    inherit: true,
    critRatio: 2,
    target: "normal"
  },
  razorwind: {
    inherit: true,
    critRatio: 1,
    target: "normal",
    onTryMove(attacker, defender, move) {
      if (attacker.removeVolatile("twoturnmove")) {
        attacker.removeVolatile("invulnerability");
        return;
      }
      this.add("-prepare", attacker, move.name);
      attacker.addVolatile("twoturnmove", defender);
      return null;
    }
  },
  recover: {
    inherit: true,
    heal: void 0,
    // no inherit
    onHit(target) {
      if (target.hp === target.maxhp) return false;
      if (target.hp === target.maxhp || (target.hp === target.maxhp - 255 || target.hp === target.maxhp - 511) && target.hp % 256 !== 0) {
        this.hint(
          "In Gen 1, recovery moves fail if (user's maximum HP - user's current HP + 1) is divisible by 256, unless the current hp is also divisible by 256."
        );
        return false;
      }
      this.heal(Math.floor(target.maxhp / 2), target, target);
    }
  },
  reflect: {
    inherit: true,
    volatileStatus: "reflect",
    sideCondition: void 0,
    // no inherit
    onTryHit(pokemon) {
      if (pokemon.volatiles["reflect"]) {
        return false;
      }
    },
    condition: {
      onStart(pokemon) {
        this.add("-start", pokemon, "Reflect");
      }
    },
    target: "self"
  },
  rest: {
    inherit: true,
    onTry: void 0,
    // no inherit
    onHit(target, source, move) {
      if (target.hp === target.maxhp) return false;
      if (target.hp === target.maxhp || (target.hp === target.maxhp - 255 || target.hp === target.maxhp - 511) && target.hp % 256 !== 0) {
        this.hint(
          "In Gen 1, recovery moves fail if (user's maximum HP - user's current HP + 1) is divisible by 256, unless the current hp is also divisible by 256."
        );
        return false;
      }
      if (!target.setStatus("slp", source, move)) return false;
      target.statusState.time = 2;
      target.statusState.startTime = 2;
      this.heal(target.maxhp);
    }
  },
  roar: {
    inherit: true,
    forceSwitch: false,
    onTryHit: void 0,
    // no inherit
    priority: 0
  },
  rockslide: {
    inherit: true,
    secondary: void 0,
    // no inherit
    target: "normal"
  },
  rockthrow: {
    inherit: true,
    accuracy: 65
  },
  sandattack: {
    inherit: true,
    ignoreImmunity: true,
    type: "Normal"
  },
  seismictoss: {
    inherit: true,
    ignoreImmunity: true,
    basePower: 1
  },
  selfdestruct: {
    inherit: true,
    basePower: 130,
    target: "normal"
  },
  skullbash: {
    inherit: true,
    onTryMove(attacker, defender, move) {
      if (attacker.removeVolatile("twoturnmove")) {
        attacker.removeVolatile("invulnerability");
        return;
      }
      this.add("-prepare", attacker, move.name);
      attacker.addVolatile("twoturnmove", defender);
      return null;
    }
  },
  skyattack: {
    inherit: true,
    onTryMove(attacker, defender, move) {
      if (attacker.removeVolatile("twoturnmove")) {
        attacker.removeVolatile("invulnerability");
        return;
      }
      this.add("-prepare", attacker, move.name);
      attacker.addVolatile("twoturnmove", defender);
      return null;
    }
  },
  slash: {
    inherit: true,
    critRatio: 2
  },
  sludge: {
    inherit: true,
    secondary: {
      chance: 40,
      status: "psn"
    }
  },
  solarbeam: {
    inherit: true,
    onTryMove(attacker, defender, move) {
      if (attacker.removeVolatile("twoturnmove")) {
        attacker.removeVolatile("invulnerability");
        return;
      }
      this.add("-prepare", attacker, move.name);
      attacker.addVolatile("twoturnmove", defender);
      return null;
    }
  },
  sonicboom: {
    inherit: true,
    ignoreImmunity: true,
    basePower: 1
  },
  softboiled: {
    inherit: true,
    heal: void 0,
    // no inherit
    onHit(target) {
      if (target.hp === target.maxhp) return false;
      if (target.hp === target.maxhp || (target.hp === target.maxhp - 255 || target.hp === target.maxhp - 511) && target.hp % 256 !== 0) {
        this.hint(
          "In Gen 1, recovery moves fail if (user's maximum HP - user's current HP + 1) is divisible by 256, unless the current hp is also divisible by 256."
        );
        return false;
      }
      this.heal(Math.floor(target.maxhp / 2), target, target);
    }
  },
  struggle: {
    inherit: true,
    pp: 10,
    recoil: [1, 2],
    onModifyMove: void 0
    // no inherit
  },
  substitute: {
    inherit: true,
    onTryHit(target) {
      if (target.volatiles["substitute"]) {
        this.add("-fail", target, "move: Substitute");
        return null;
      }
      if (target.hp < target.maxhp / 4) {
        this.add("-fail", target, "move: Substitute", "[weak]");
        return null;
      }
    },
    onHit(target) {
      if (target.maxhp > 3) {
        this.directDamage(target.maxhp / 4, target, target);
      }
    },
    condition: {
      inherit: true,
      onStart(target) {
        this.add("-start", target, "Substitute");
        this.effectState.hp = Math.floor(target.maxhp / 4) + 1;
        if (target.volatiles["partiallytrapped"]) {
          this.add("-end", target, target.volatiles["partiallytrapped"].sourceEffect, "[partiallytrapped]", "[silent]");
          delete target.volatiles["partiallytrapped"];
        }
      },
      onTryPrimaryHit: void 0,
      // no inherit
      onTryHitPriority: -1,
      onTryHit(target, source, move) {
        if (move.category === "Status") {
          const SubBlocked = ["lockon", "meanlook", "mindreader", "nightmare"];
          if (move.status === "psn" || move.status === "tox" || move.boosts && target !== source || move.volatileStatus === "confusion" || SubBlocked.includes(move.id)) {
            return false;
          }
          return;
        }
        if (move.volatileStatus && target === source) return;
        let uncappedDamage = move.hit > 1 ? this.lastDamage : this.actions.getDamage(source, target, move);
        if (move.id === "bide") uncappedDamage = source.volatiles["bide"].damage * 2;
        if (!uncappedDamage && uncappedDamage !== 0) return null;
        this.lastDamage = uncappedDamage;
        target.volatiles["substitute"].hp -= uncappedDamage > target.volatiles["substitute"].hp ? target.volatiles["substitute"].hp : uncappedDamage;
        if (target.volatiles["substitute"].hp <= 0) {
          target.removeVolatile("substitute");
          target.subFainted = true;
        } else {
          this.add("-activate", target, "Substitute", "[damage]");
        }
        if (target.volatiles["substitute"]) {
          if (move.recoil) {
            this.damage(
              this.clampIntRange(Math.floor(uncappedDamage * move.recoil[0] / move.recoil[1]), 1),
              source,
              target,
              "recoil"
            );
          }
          if (move.drain) {
            const amount = this.clampIntRange(Math.floor(uncappedDamage * move.drain[0] / move.drain[1]), 1);
            this.lastDamage = amount;
            this.heal(amount, source, target, "drain");
          }
          if (move.secondary?.volatileStatus === "confusion") {
            const secondary = move.secondary;
            if (secondary.chance === void 0 || this.randomChance(Math.ceil(secondary.chance * 256 / 100) - 1, 256)) {
              target.addVolatile(move.secondary.volatileStatus, source, move);
              this.hint(
                "In Gen 1, moves that inflict confusion as a secondary effect can confuse targets with a Substitute, as long as the move does not break the Substitute."
              );
            }
          }
        }
        this.runEvent("AfterSubDamage", target, source, move, uncappedDamage);
        const lastAttackedBy = target.getLastAttackedBy();
        if (!lastAttackedBy) {
          target.attackedBy.push({ source, move: move.id, damage: uncappedDamage, slot: source.getSlot(), thisTurn: true });
        } else {
          lastAttackedBy.move = move.id;
          lastAttackedBy.damage = uncappedDamage;
        }
        return 0;
      }
    }
  },
  superfang: {
    inherit: true,
    ignoreImmunity: true,
    basePower: 1
  },
  thrash: {
    inherit: true,
    onMoveFail: void 0
    // no inherit
  },
  thunder: {
    inherit: true,
    secondary: {
      chance: 10,
      status: "par"
    }
  },
  triattack: {
    inherit: true,
    onHit: void 0,
    // no inherit
    secondary: void 0
    // no inherit
  },
  whirlwind: {
    inherit: true,
    accuracy: 85,
    forceSwitch: false,
    onTryHit: void 0,
    // no inherit
    priority: 0
  },
  wingattack: {
    inherit: true,
    basePower: 35
  },
  wrap: {
    inherit: true,
    accuracy: 85,
    ignoreImmunity: true,
    self: {
      volatileStatus: "partialtrappinglock"
    },
    onTryMove(source, target) {
      if (target.volatiles["mustrecharge"]) {
        target.removeVolatile("mustrecharge");
        this.hint("In Gen 1, partial trapping moves negate the recharge turn of Hyper Beam, even if they miss.", true);
      }
    }
  }
};
//# sourceMappingURL=moves.js.map
