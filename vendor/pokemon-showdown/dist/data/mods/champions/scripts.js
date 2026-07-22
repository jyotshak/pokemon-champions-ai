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
var import_dex = require("../../../sim/dex");
const Scripts = {
  gen: 9,
  init() {
    for (const i in this.data.Moves) {
      if (this.data.Moves[i].pp > 20) {
        this.modData("Moves", i).pp = 20;
      }
    }
  },
  statModify(baseStats, set, statName) {
    const tr = this.trunc;
    let stat = baseStats[statName];
    const evs = set.evs[statName];
    if (this.ruleTable.has("levelclausemod")) {
      const level = set.level;
      if (statName === "hp") {
        return tr((2 * stat + 31 + Math.max(2 * evs - 1, 0)) * level / 100) + level + 10;
      }
      stat = tr((2 * stat + 31 + Math.max(2 * evs - 1, 0)) * level / 100) + 5;
    } else {
      if (statName === "hp") {
        return stat + evs + 75;
      }
      stat = stat + evs + 20;
    }
    const nature = this.dex.natures.get(set.nature);
    if (nature.plus === statName) {
      stat = this.ruleTable.has("overflowstatmod") ? Math.min(stat, 595) : stat;
      stat = tr(tr(stat * 110, 16) / 100);
    } else if (nature.minus === statName) {
      stat = this.ruleTable.has("overflowstatmod") ? Math.min(stat, 728) : stat;
      stat = tr(tr(stat * 90, 16) / 100);
    }
    return stat;
  },
  calculatePP(move, ppUps) {
    return move.noPPBoosts ? move.pp : (move.pp / 5 + 1) * 4;
  },
  pokemon: {
    // Remove Trick Room underflow
    getActionSpeed() {
      let speed = this.getStat("spe", false, false);
      const trickRoomCheck = this.battle.ruleTable.has("twisteddimensionmod") ? !this.battle.field.getPseudoWeather("trickroom") : this.battle.field.getPseudoWeather("trickroom");
      if (trickRoomCheck) {
        speed = -speed;
      }
      return speed;
    },
    // Don't revert Mega Evolutions after fainting
    // TODO: confirm interaction with Revival Blessing
    formeChange(speciesId, source, isPermanent, abilitySlot = "0", message) {
      const rawSpecies = this.battle.dex.species.get(speciesId);
      const species = this.setSpecies(rawSpecies, source);
      if (!species) return false;
      if (this.battle.gen <= 2) return true;
      const apparentSpecies = this.illusion ? this.illusion.species.name : species.baseSpecies;
      if (isPermanent) {
        this.baseSpecies = rawSpecies;
        this.details = this.getUpdatedDetails();
        let details = (this.illusion || this).details;
        if (this.terastallized) details += `, tera:${this.terastallized}`;
        this.battle.add("detailschange", this, details);
        this.updateMaxHp();
        if (!source) {
          this.formeRegression = true;
        } else if (source.effectType === "Item") {
          this.canTerastallize = null;
          if (source.zMove) {
            this.battle.add("-burst", this, apparentSpecies, species.requiredItem);
            this.moveThisTurnResult = true;
          } else if (source.isPrimalOrb) {
            if (this.illusion) {
              this.ability = "";
              this.battle.add("-primal", this.illusion, species.requiredItem);
            } else {
              this.battle.add("-primal", this, species.requiredItem);
            }
          } else {
            this.battle.add("-mega", this, apparentSpecies, species.requiredItem);
            this.moveThisTurnResult = true;
          }
        } else if (source.effectType === "Status") {
          this.battle.add("-formechange", this, species.name, message);
        }
      } else {
        if (source?.effectType === "Ability") {
          this.battle.add("-formechange", this, species.name, message, `[from] ability: ${source.name}`);
        } else {
          this.battle.add("-formechange", this, this.illusion ? this.illusion.species.name : species.name, message);
        }
      }
      if (isPermanent && (!source || !["disguise", "iceface"].includes(source.id))) {
        if (this.illusion && source) {
          this.ability = "";
        }
        const ability = species.abilities[abilitySlot] || species.abilities["0"];
        if (source || !this.getAbility().flags["cantsuppress"]) this.setAbility(ability, null, null, true);
        this.baseAbility = this.battle.toID(ability);
      }
      if (this.terastallized) {
        this.knownType = true;
        this.apparentType = this.terastallized;
      }
      return true;
    },
    // reset timesAttacked
    clearVolatile(includeSwitchFlags = true) {
      this.boosts = {
        atk: 0,
        def: 0,
        spa: 0,
        spd: 0,
        spe: 0,
        accuracy: 0,
        evasion: 0
      };
      this.moveSlots = this.baseMoveSlots.slice();
      this.transformed = false;
      this.ability = this.baseAbility;
      this.hpType = this.baseHpType;
      this.hpPower = this.baseHpPower;
      if (this.canTerastallize === false) this.canTerastallize = this.teraType;
      for (const i in this.volatiles) {
        if (this.volatiles[i].linkedStatus) {
          this.removeLinkedVolatiles(this.volatiles[i].linkedStatus, this.volatiles[i].linkedPokemon);
        }
      }
      if (this.species.name === "Eternatus-Eternamax" && this.volatiles["dynamax"]) {
        this.volatiles = { dynamax: this.volatiles["dynamax"] };
      } else {
        this.volatiles = {};
      }
      if (includeSwitchFlags) {
        this.switchFlag = false;
        this.forceSwitchFlag = false;
      }
      this.lastMove = null;
      this.lastMoveEncore = null;
      this.lastMoveUsed = null;
      this.moveThisTurn = "";
      this.moveLastTurnResult = void 0;
      this.moveThisTurnResult = void 0;
      this.lastDamage = 0;
      this.attackedBy = [];
      this.hurtThisTurn = null;
      this.newlySwitched = true;
      this.beingCalledBack = false;
      this.timesAttacked = 0;
      this.volatileStaleness = void 0;
      delete this.abilityState.started;
      delete this.itemState.started;
      this.setSpecies(this.baseSpecies);
    }
  },
  actions: {
    canTerastallize(pokemon) {
      return null;
    },
    canMegaEvo(pokemon) {
      const species = pokemon.baseSpecies;
      const altForme = species.otherFormes && this.dex.species.get(species.otherFormes[0]);
      const item = pokemon.getItem();
      if ((this.battle.gen <= 7 || this.battle.ruleTable.has("+tag:past") || this.battle.ruleTable.has("+tag:future")) && altForme?.isMega && altForme?.requiredMove && pokemon.baseMoves.includes((0, import_dex.toID)(altForme.requiredMove)) && !item.zMove) {
        return altForme.name;
      }
      return item.megaStone?.[species.name] || null;
    },
    // Announce 4x and 0.25x effectiveness
    modifyDamage(baseDamage, pokemon, target, move, suppressMessages) {
      const tr = this.battle.trunc;
      if (!move.type) move.type = "???";
      const type = move.type;
      baseDamage += 2;
      if (move.spreadHit) {
        const spreadModifier = this.battle.gameType === "freeforall" ? 0.5 : 0.75;
        this.battle.debug(`Spread modifier: ${spreadModifier}`);
        baseDamage = this.battle.modify(baseDamage, spreadModifier);
      } else if (move.multihitType === "parentalbond" && move.hit > 1) {
        const bondModifier = this.battle.gen > 6 ? 0.25 : 0.5;
        this.battle.debug(`Parental Bond modifier: ${bondModifier}`);
        baseDamage = this.battle.modify(baseDamage, bondModifier);
      }
      baseDamage = this.battle.priorityEvent("WeatherModifyDamage", pokemon, target, move, baseDamage);
      const isCrit = target.getMoveHitData(move).crit;
      if (isCrit) {
        baseDamage = tr(baseDamage * (move.critModifier || (this.battle.gen >= 6 ? 1.5 : 2)));
      }
      baseDamage = this.battle.randomizer(baseDamage);
      if (type !== "???") {
        let stab = 1;
        const isSTAB = move.forceSTAB || pokemon.hasType(type) || pokemon.getTypes(false, true).includes(type);
        if (isSTAB) {
          stab = 1.5;
        }
        if (pokemon.terastallized === "Stellar") {
          if (!pokemon.stellarBoostedTypes.includes(type) || move.stellarBoosted) {
            stab = isSTAB ? 2 : [4915, 4096];
            move.stellarBoosted = true;
            if (pokemon.species.name !== "Terapagos-Stellar") {
              pokemon.stellarBoostedTypes.push(type);
            }
          }
        } else {
          if (pokemon.terastallized === type && pokemon.getTypes(false, true).includes(type)) {
            stab = 2;
          }
          stab = this.battle.runEvent("ModifySTAB", pokemon, target, move, stab);
        }
        baseDamage = this.battle.modify(baseDamage, stab);
      }
      let typeMod = target.runEffectiveness(move);
      typeMod = this.battle.clampIntRange(typeMod, -6, 6);
      target.getMoveHitData(move).typeMod = typeMod;
      if (typeMod > 0) {
        if (!suppressMessages) this.battle.add("-supereffective", target, Math.min(typeMod, 2));
        for (let i = 0; i < typeMod; i++) {
          baseDamage *= 2;
        }
      }
      if (typeMod < 0) {
        if (!suppressMessages) this.battle.add("-resisted", target, Math.min(-typeMod, 2));
        for (let i = 0; i > typeMod; i--) {
          baseDamage = tr(baseDamage / 2);
        }
      }
      if (isCrit && !suppressMessages) this.battle.add("-crit", target);
      if (pokemon.status === "brn" && move.category === "Physical" && !pokemon.hasAbility("guts")) {
        if (this.battle.gen < 6 || move.id !== "facade") {
          baseDamage = this.battle.modify(baseDamage, 0.5);
        }
      }
      if (this.battle.gen === 5 && !baseDamage) baseDamage = 1;
      baseDamage = this.battle.runEvent("ModifyDamage", pokemon, target, move, baseDamage);
      const bypassProtect = target.getMoveHitData(move).bypassProtect;
      if (bypassProtect) {
        baseDamage = this.battle.modify(baseDamage, 0.25);
        if (bypassProtect !== true && bypassProtect.effectType === "Ability") {
          this.battle.add("-ability", pokemon, bypassProtect.name);
        }
        this.battle.add("-zbroken", target);
      }
      if (this.battle.gen !== 5 && !baseDamage) return 1;
      return tr(baseDamage, 16);
    },
    // Run `AfterHit` events even if the source fainted
    spreadMoveHit(targets, pokemon, moveOrMoveName, hitEffect, isSecondary, isSelf) {
      const target = targets[0];
      let damage = [];
      for (const i of targets.keys()) {
        damage[i] = true;
      }
      const move = this.dex.getActiveMove(moveOrMoveName);
      let hitResult = true;
      let moveData = hitEffect;
      if (!moveData) moveData = move;
      if (!moveData.flags) moveData.flags = {};
      if (move.target === "all" && !isSelf) {
        hitResult = this.battle.singleEvent("TryHitField", moveData, {}, target || null, pokemon, move);
      } else if ((move.target === "foeSide" || move.target === "allySide" || move.target === "allyTeam") && !isSelf) {
        hitResult = this.battle.singleEvent("TryHitSide", moveData, {}, target || null, pokemon, move);
      } else if (target) {
        hitResult = this.battle.singleEvent("TryHit", moveData, {}, target, pokemon, move);
      }
      if (!hitResult) {
        if (hitResult === false) {
          this.battle.add("-fail", pokemon);
          this.battle.attrLastMove("[still]");
        }
        return [[false], targets];
      }
      if (!isSecondary && !isSelf) {
        if (move.target !== "all" && move.target !== "allyTeam" && move.target !== "allySide" && move.target !== "foeSide") {
          damage = this.tryPrimaryHitEvent(damage, targets, pokemon, move, moveData, isSecondary);
        }
      }
      for (const i of targets.keys()) {
        if (damage[i] === this.battle.HIT_SUBSTITUTE) {
          damage[i] = true;
          targets[i] = null;
        }
        if (targets[i] && isSecondary && !moveData.self) {
          damage[i] = true;
        }
        if (!damage[i]) targets[i] = false;
      }
      damage = this.getSpreadDamage(damage, targets, pokemon, move, moveData, isSecondary, isSelf);
      for (const i of targets.keys()) {
        if (damage[i] === false) targets[i] = false;
      }
      damage = this.battle.spreadDamage(damage, targets, pokemon, move);
      for (const i of targets.keys()) {
        if (damage[i] === false) targets[i] = false;
      }
      damage = this.runMoveEffects(damage, targets, pokemon, move, moveData, isSecondary, isSelf);
      for (const i of targets.keys()) {
        if (!damage[i] && damage[i] !== 0) targets[i] = false;
      }
      const activeTarget = this.battle.activeTarget;
      if (moveData.self && !move.selfDropped) this.selfDrops(targets, pokemon, move, moveData, isSecondary);
      if (moveData.secondaries) this.secondaries(targets, pokemon, move, moveData, isSelf);
      this.battle.activeTarget = activeTarget;
      if (moveData.forceSwitch) damage = this.forceSwitch(damage, targets, pokemon, move);
      for (const i of targets.keys()) {
        if (!damage[i] && damage[i] !== 0) targets[i] = false;
      }
      const damagedTargets = [];
      const damagedDamage = [];
      for (const [i, t] of targets.entries()) {
        if (typeof damage[i] === "number" && t) {
          damagedTargets.push(t);
          damagedDamage.push(damage[i]);
        }
      }
      const pokemonOriginalHP = pokemon.hp;
      if (damagedDamage.length && !isSecondary && !isSelf) {
        if (this.battle.gen >= 5) {
          this.battle.runEvent("DamagingHit", damagedTargets, pokemon, move, damagedDamage);
        }
        if (moveData.onAfterHit) {
          for (const t of damagedTargets) {
            this.battle.singleEvent("AfterHit", moveData, {}, t, pokemon, move);
          }
        }
        if (this.battle.gen < 5) {
          this.battle.runEvent("DamagingHit", damagedTargets, pokemon, move, damagedDamage);
        }
        if (pokemon.hp && pokemon.hp <= pokemon.maxhp / 2 && pokemonOriginalHP > pokemon.maxhp / 2) {
          this.battle.runEvent("EmergencyExit", pokemon);
        }
      }
      return [damage, targets];
    },
    // Parental Bond shouldn't announce hit count if it only hits once
    hitStepMoveHitLoop(targets, pokemon, move) {
      let damage = [];
      for (const i of targets.keys()) {
        damage[i] = 0;
      }
      move.totalDamage = 0;
      pokemon.lastDamage = 0;
      let targetHits = move.multihit || 1;
      if (Array.isArray(targetHits)) {
        if (targetHits[0] === 2 && targetHits[1] === 5) {
          if (this.battle.gen >= 5) {
            targetHits = this.battle.sample([2, 2, 2, 2, 2, 2, 2, 3, 3, 3, 3, 3, 3, 3, 4, 4, 4, 5, 5, 5]);
            if (targetHits < 4 && pokemon.hasItem("loadeddice")) {
              targetHits = 5 - this.battle.random(2);
            }
          } else {
            targetHits = this.battle.sample([2, 2, 2, 3, 3, 3, 4, 5]);
          }
        } else {
          targetHits = this.battle.random(targetHits[0], targetHits[1] + 1);
        }
      }
      if (targetHits === 10 && pokemon.hasItem("loadeddice")) targetHits -= this.battle.random(7);
      targetHits = Math.floor(targetHits);
      let nullDamage = true;
      let moveDamage = [];
      const isSleepUsable = move.sleepUsable || this.dex.moves.get(move.sourceEffect).sleepUsable;
      let targetsCopy = targets.slice(0);
      let hit;
      for (hit = 1; hit <= targetHits; hit++) {
        if (damage.includes(false)) break;
        if (hit > 1 && pokemon.status === "slp" && (!isSleepUsable || this.battle.gen === 4)) break;
        if (targets.every((target2) => !target2?.hp)) break;
        move.hit = hit;
        move.lastHit = move.hit === targetHits;
        if (move.smartTarget && targets.length > 1) {
          targetsCopy = [targets[hit - 1]];
          damage = [damage[hit - 1]];
        } else {
          targetsCopy = targets.slice(0);
        }
        const target = targetsCopy[0];
        if (target && typeof move.smartTarget === "boolean") {
          if (hit > 1) {
            this.battle.addMove("-anim", pokemon, move.name, target);
          } else {
            this.battle.retargetLastMove(target);
          }
        }
        if (target && move.multiaccuracy && hit > 1) {
          let accuracy = move.accuracy;
          const boostTable = [1, 4 / 3, 5 / 3, 2, 7 / 3, 8 / 3, 3];
          if (accuracy !== true) {
            if (!move.ignoreAccuracy) {
              const boosts = this.battle.runEvent("ModifyBoost", pokemon, null, null, { ...pokemon.boosts });
              const boost = this.battle.clampIntRange(boosts["accuracy"], -6, 6);
              if (boost > 0) {
                accuracy *= boostTable[boost];
              } else {
                accuracy /= boostTable[-boost];
              }
            }
            if (!move.ignoreEvasion) {
              const boosts = this.battle.runEvent("ModifyBoost", target, null, null, { ...target.boosts });
              const boost = this.battle.clampIntRange(boosts["evasion"], -6, 6);
              if (boost > 0) {
                accuracy /= boostTable[boost];
              } else if (boost < 0) {
                accuracy *= boostTable[-boost];
              }
            }
          }
          accuracy = this.battle.runEvent("ModifyAccuracy", target, pokemon, move, accuracy);
          if (!move.alwaysHit) {
            accuracy = this.battle.runEvent("Accuracy", target, pokemon, move, accuracy);
            if (accuracy !== true && !this.battle.randomChance(accuracy, 100)) break;
          }
        }
        const moveData = move;
        if (!moveData.flags) moveData.flags = {};
        let moveDamageThisHit;
        [moveDamageThisHit, targetsCopy] = this.spreadMoveHit(targetsCopy, pokemon, move, moveData);
        if (move.smartTarget) {
          moveDamage.push(...moveDamageThisHit);
        } else {
          moveDamage = moveDamageThisHit;
        }
        if (!moveDamage.some((val) => val !== false)) break;
        nullDamage = false;
        for (const [i, md] of moveDamage.entries()) {
          if (move.smartTarget && i !== hit - 1) continue;
          damage[i] = md === true || !md ? 0 : md;
          move.totalDamage += damage[i];
        }
        if (move.mindBlownRecoil) {
          const hpBeforeRecoil = pokemon.hp;
          this.battle.damage(Math.round(pokemon.maxhp / 2), pokemon, pokemon, this.dex.conditions.get(move.id), true);
          move.mindBlownRecoil = false;
          if (pokemon.hp <= pokemon.maxhp / 2 && hpBeforeRecoil > pokemon.maxhp / 2) {
            this.battle.runEvent("EmergencyExit", pokemon, pokemon);
          }
        }
        this.battle.eachEvent("Update");
        if (!pokemon.hp && targets.length === 1) {
          hit++;
          break;
        }
      }
      if (hit === 1) return damage.fill(false);
      if (nullDamage) damage.fill(false);
      this.battle.faintMessages(false, false, !pokemon.hp);
      if (move.multihit && typeof move.smartTarget !== "boolean" && !(move.hit === 1 && move.multihitType === "parentalbond")) {
        this.battle.add("-hitcount", targets[0], hit - 1);
      }
      if ((move.recoil || move.id === "chloroblast") && move.totalDamage) {
        const hpBeforeRecoil = pokemon.hp;
        this.battle.damage(this.calcRecoilDamage(move.totalDamage, move, pokemon), pokemon, pokemon, "recoil");
        if (pokemon.hp <= pokemon.maxhp / 2 && hpBeforeRecoil > pokemon.maxhp / 2) {
          this.battle.runEvent("EmergencyExit", pokemon, pokemon);
        }
      }
      if (move.struggleRecoil) {
        const hpBeforeRecoil = pokemon.hp;
        let recoilDamage;
        if (this.dex.gen >= 5) {
          recoilDamage = this.battle.clampIntRange(Math.round(pokemon.baseMaxhp / 4), 1);
        } else {
          recoilDamage = this.battle.clampIntRange(this.battle.trunc(pokemon.maxhp / 4), 1);
        }
        this.battle.directDamage(recoilDamage, pokemon, pokemon, { id: "strugglerecoil" });
        if (pokemon.hp <= pokemon.maxhp / 2 && hpBeforeRecoil > pokemon.maxhp / 2) {
          this.battle.runEvent("EmergencyExit", pokemon, pokemon);
        }
      }
      if (move.smartTarget) {
        targetsCopy = targets.slice(0);
      }
      for (const [i, target] of targetsCopy.entries()) {
        if (target && pokemon !== target) {
          target.gotAttacked(move, moveDamage[i], pokemon);
          if (typeof moveDamage[i] === "number") {
            target.timesAttacked += move.smartTarget ? 1 : hit - 1;
          }
        }
      }
      if (move.ohko && !targets[0].hp) this.battle.add("-ohko");
      if (!damage.some((val) => !!val || val === 0)) return damage;
      this.battle.eachEvent("Update");
      this.afterMoveSecondaryEvent(targetsCopy.filter((val) => !!val), pokemon, move);
      if (!(move.hasSheerForce && pokemon.hasAbility("sheerforce"))) {
        for (const [i, d] of damage.entries()) {
          const curDamage = targets.length === 1 ? move.totalDamage : d;
          if (typeof curDamage === "number" && targets[i].hp) {
            const targetHPBeforeDamage = (targets[i].hurtThisTurn || 0) + curDamage;
            if (targets[i].hp <= targets[i].maxhp / 2 && targetHPBeforeDamage > targets[i].maxhp / 2) {
              this.battle.runEvent("EmergencyExit", targets[i], pokemon);
            }
          }
        }
      }
      return damage;
    }
  }
};
//# sourceMappingURL=scripts.js.map
