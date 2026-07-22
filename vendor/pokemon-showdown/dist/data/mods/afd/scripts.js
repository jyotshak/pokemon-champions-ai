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
  gen: 9,
  init() {
    for (const id in this.data.Pokedex) {
      const species = this.data.Pokedex[id];
      if (species.isCosmeticForme) continue;
      if (species.types.includes("Ground")) {
        if (this.data.Learnsets[id]?.learnset) this.modData("Learnsets", id).learnset.thousandarrows = ["9L1"];
      }
      if (species.types.includes("Grass") && !species.types.includes("Fire")) {
        if (this.data.Learnsets[id]?.learnset) this.modData("Learnsets", id).learnset.solarflare = ["9L1"];
      }
      const abilities = this.modData("Pokedex", id, true).abilities;
      if (species.baseStats["atk"] >= 130) {
        const hasHP = Object.values(abilities).includes("Huge Power") || Object.values(abilities).includes("Pure Power");
        if (!hasHP) {
          const slot = !abilities["1"] ? "1" : !abilities["H"] ? "H" : "S";
          abilities[slot] ||= "Huge Power";
        }
      }
      const hasRegen = Object.values(abilities).includes("Regenerator");
      if (!hasRegen) {
        const slot = !abilities["1"] ? "1" : !abilities["H"] ? "H" : "S";
        abilities[slot] ||= "Regenerator";
      }
    }
    this.modData("Learnsets", "tyranitar").learnset.shoreup = ["9L1"];
    this.modData("Learnsets", "bastiodon").learnset.blastiodon = ["9L1"];
    this.modData("Learnsets", "seaking").learnset.boltbeak = ["9L1"];
    this.modData("Learnsets", "seaking").learnset.fishiousrend = ["9L1"];
    this.modData("Learnsets", "ampharos").learnset.tailglow = ["9L1"];
    this.modData("Learnsets", "ampharos").learnset.dracometeor = ["9L1"];
    this.modData("Learnsets", "serperior").learnset.dracometeor = ["9L1"];
    this.modData("Learnsets", "serperior").learnset.overheat = ["9L1"];
    this.modData("Learnsets", "serperior").learnset.makeitrain = ["9L1"];
    this.modData("Learnsets", "rampardos").learnset.accelerock = ["9L1"];
    this.modData("Learnsets", "bibarel").learnset.bellydrum = ["9L1"];
    this.modData("Learnsets", "bibarel").learnset.storedpower = ["9L1"];
    this.modData("Learnsets", "bibarel").learnset.powertrip = ["9L1"];
    this.modData("Learnsets", "golisopod").learnset.bellydrum = ["9L1"];
    this.modData("Learnsets", "skuntank").learnset.shitpulse = ["9L1"];
    this.modData("Learnsets", "dusknoir").learnset = { explosion: ["9L1"] };
    for (const move of this.moves.all()) {
      if (move.flags["bite"]) {
        this.modData("Learnsets", "bruxish").learnset[move.id] = ["9L1"];
      }
    }
    for (const moveid in this.data.Learnsets["incineroar"].learnset) {
      if (this.moves.get(moveid).type === "Dark") {
        delete this.modData("Learnsets", "incineroar").learnset[moveid];
      }
    }
  },
  actions: {
    runMegaEvo(pokemon) {
      const speciesid = pokemon.canMegaEvo || pokemon.canUltraBurst;
      if (!speciesid) return false;
      pokemon.formeChange(speciesid, pokemon.getItem(), true);
      pokemon.canMegaEvo = null;
      this.battle.runEvent("AfterMega", pokemon);
      return true;
    },
    switchIn(pokemon, pos, sourceEffect = null, isDrag) {
      if (!pokemon || pokemon.isActive) {
        this.battle.hint("A switch failed because the Pok\xE9mon trying to switch in is already in.");
        return false;
      }
      const side = pokemon.side;
      if (pos >= side.active.length) {
        throw new Error(`Invalid switch position ${pos} / ${side.active.length}`);
      }
      const oldActive = side.active[pos];
      const unfaintedActive = oldActive?.hp ? oldActive : null;
      if (unfaintedActive) {
        oldActive.beingCalledBack = true;
        let switchCopyFlag = false;
        if (sourceEffect && typeof sourceEffect.selfSwitch === "string") {
          switchCopyFlag = sourceEffect.selfSwitch;
        }
        if (!oldActive.skipBeforeSwitchOutEventFlag && !isDrag) {
          this.battle.runEvent("BeforeSwitchOut", oldActive);
          if (this.battle.gen >= 5) {
            this.battle.eachEvent("Update");
          }
        }
        oldActive.skipBeforeSwitchOutEventFlag = false;
        if (!this.battle.runEvent("SwitchOut", oldActive)) {
          return false;
        }
        if (!oldActive.hp) {
          return "pursuitfaint";
        }
        this.battle.singleEvent("End", oldActive.getAbility(), oldActive.abilityState, oldActive);
        this.battle.singleEvent("End", oldActive.getItem(), oldActive.itemState, oldActive);
        this.battle.queue.cancelAction(oldActive);
        let newMove = null;
        if (this.battle.gen === 4 && sourceEffect) {
          newMove = oldActive.lastMove;
        }
        if (switchCopyFlag) {
          pokemon.copyVolatileFrom(oldActive, switchCopyFlag);
        }
        if (newMove) pokemon.lastMove = newMove;
        oldActive.clearVolatile();
      }
      if (oldActive) {
        oldActive.isActive = false;
        oldActive.isStarted = false;
        oldActive.usedItemThisTurn = false;
        oldActive.statsRaisedThisTurn = false;
        oldActive.statsLoweredThisTurn = false;
        oldActive.position = pokemon.position;
        if (oldActive.fainted) oldActive.status = "";
        if (this.battle.gen <= 4) {
          pokemon.lastItem = oldActive.lastItem;
          oldActive.lastItem = "";
        }
        pokemon.position = pos;
        side.pokemon[pokemon.position] = pokemon;
        side.pokemon[oldActive.position] = oldActive;
      }
      pokemon.isActive = true;
      side.active[pos] = pokemon;
      pokemon.activeTurns = 0;
      pokemon.activeMoveActions = 0;
      for (const moveSlot of pokemon.moveSlots) {
        moveSlot.used = false;
      }
      pokemon.abilityState = this.battle.initEffectState({ id: pokemon.ability, target: pokemon });
      pokemon.itemState = this.battle.initEffectState({ id: pokemon.item, target: pokemon });
      this.battle.runEvent("BeforeSwitchIn", pokemon);
      if (sourceEffect) {
        this.battle.add(isDrag ? "drag" : "switch", pokemon, pokemon.getFullDetails, `[from] ${sourceEffect}`);
      } else {
        this.battle.add(isDrag ? "drag" : "switch", pokemon, pokemon.getFullDetails);
      }
      if (isDrag && this.battle.gen === 2) pokemon.draggedIn = this.battle.turn;
      pokemon.previouslySwitchedIn++;
      if (isDrag && this.battle.gen >= 5) {
        this.runSwitch(pokemon);
      } else {
        this.battle.queue.insertChoice({ choice: "runSwitch", pokemon });
      }
      if (pokemon.hasType("Flying")) {
        this.battle.field.addPseudoWeather("Tailwind", pokemon);
      }
      return true;
    },
    useMoveInner(moveOrMoveName, pokemon, options) {
      let target = options?.target;
      let sourceEffect = options?.sourceEffect;
      const zMove = options?.zMove;
      const maxMove = options?.maxMove;
      if (!sourceEffect && this.battle.effect.id) sourceEffect = this.battle.effect;
      if (sourceEffect && ["instruct", "custapberry"].includes(sourceEffect.id)) sourceEffect = null;
      let move = this.dex.getActiveMove(moveOrMoveName);
      pokemon.lastMoveUsed = move;
      if (move.id === "weatherball" && zMove) {
        this.battle.singleEvent("ModifyType", move, null, pokemon, target, move, move);
        if (move.type !== "Normal") sourceEffect = move;
      }
      if (zMove || move.category !== "Status" && sourceEffect && sourceEffect.isZ) {
        move = this.getActiveZMove(move, pokemon);
      }
      if (maxMove && move.category !== "Status") {
        this.battle.singleEvent("ModifyType", move, null, pokemon, target, move, move);
        this.battle.runEvent("ModifyType", pokemon, target, move, move);
      }
      if (maxMove || move.category !== "Status" && sourceEffect && sourceEffect.isMax) {
        move = this.getActiveMaxMove(move, pokemon);
      }
      if (this.battle.activeMove) {
        move.priority = this.battle.activeMove.priority;
        if (!move.hasBounced) move.pranksterBoosted = this.battle.activeMove.pranksterBoosted;
      }
      const baseTarget = move.target;
      let targetRelayVar = { target };
      targetRelayVar = this.battle.runEvent("ModifyTarget", pokemon, target, move, targetRelayVar, true);
      if (targetRelayVar.target !== void 0) target = targetRelayVar.target;
      if (target === void 0) target = this.battle.getRandomTarget(pokemon, move);
      if (move.target === "self" || move.target === "allies") {
        target = pokemon;
      }
      if (sourceEffect) {
        move.sourceEffect = sourceEffect.id;
        move.ignoreAbility = sourceEffect.ignoreAbility;
      }
      let moveResult = false;
      this.battle.setActiveMove(move, pokemon, target);
      this.battle.singleEvent("ModifyType", move, null, pokemon, target, move, move);
      this.battle.singleEvent("ModifyMove", move, null, pokemon, target, move, move);
      if (baseTarget !== move.target) {
        target = this.battle.getRandomTarget(pokemon, move);
      }
      move = this.battle.runEvent("ModifyType", pokemon, target, move, move);
      move = this.battle.runEvent("ModifyMove", pokemon, target, move, move);
      if (baseTarget !== move.target) {
        target = this.battle.getRandomTarget(pokemon, move);
      }
      if (!move || pokemon.fainted) {
        return false;
      }
      let attrs = "";
      let movename = move.name;
      if (move.id === "hiddenpower") movename = "Hidden Power";
      if (sourceEffect) attrs += `|[from] ${sourceEffect.fullname}`;
      if (zMove && move.isZ === true) {
        attrs = `|[anim]${movename}${attrs}`;
        movename = `Z-${movename}`;
      }
      this.battle.addMove("move", pokemon, movename, `${target}${attrs}`);
      if (zMove) this.runZPower(move, pokemon);
      if (!target) {
        this.battle.attrLastMove("[notarget]");
        this.battle.add(this.battle.gen >= 5 ? "-fail" : "-notarget", pokemon);
        return false;
      }
      const { targets, pressureTargets } = pokemon.getMoveTargets(move, target);
      if (targets.length) {
        target = targets[targets.length - 1];
      }
      const callerMoveForPressure = sourceEffect && sourceEffect.pp ? sourceEffect : null;
      if (!sourceEffect || callerMoveForPressure || sourceEffect.id === "pursuit") {
        let extraPP = 0;
        for (const source of pressureTargets) {
          const ppDrop = this.battle.runEvent("DeductPP", source, pokemon, move);
          if (ppDrop !== true) {
            extraPP += ppDrop || 0;
          }
        }
        if (extraPP > 0) {
          pokemon.deductPP(callerMoveForPressure || moveOrMoveName, extraPP);
        }
      }
      let tryMoveResult = this.battle.singleEvent("TryMove", move, null, pokemon, target, move);
      if (tryMoveResult) {
        tryMoveResult = this.battle.runEvent("TryMove", pokemon, target, move);
      }
      if (!tryMoveResult) {
        move.mindBlownRecoil = false;
        return tryMoveResult;
      }
      this.battle.singleEvent("UseMoveMessage", move, null, pokemon, target, move);
      if (move.ignoreImmunity === void 0) {
        move.ignoreImmunity = move.category === "Status";
      }
      if (this.battle.gen !== 4 && move.selfdestruct === "always") {
        this.battle.faint(pokemon, pokemon, move);
      }
      let damage = false;
      if (move.target === "all" || move.target === "foeSide" || move.target === "allySide" || move.target === "allyTeam") {
        damage = this.tryMoveHit(targets, pokemon, move);
        if (damage === this.battle.NOT_FAIL) pokemon.moveThisTurnResult = null;
        if (damage || damage === 0 || damage === void 0) moveResult = true;
      } else {
        if (!targets.length) {
          this.battle.attrLastMove("[notarget]");
          this.battle.add(this.battle.gen >= 5 ? "-fail" : "-notarget", pokemon);
          return false;
        }
        if (this.battle.gen === 4 && move.selfdestruct === "always") {
          this.battle.faint(pokemon, pokemon, move);
        }
        moveResult = this.trySpreadMoveHit(targets, pokemon, move);
      }
      if (move.selfBoost && moveResult) this.moveHit(pokemon, pokemon, move, move.selfBoost, false, true);
      if (!pokemon.hp) {
        this.battle.faint(pokemon, pokemon, move);
      }
      if (!moveResult) {
        this.battle.singleEvent("MoveFail", move, null, target, pokemon, move);
        return false;
      }
      if (!(move.hasSheerForce && pokemon.hasAbility("sheerforce")) && !move.flags["futuremove"]) {
        const originalHp = pokemon.hp;
        this.battle.singleEvent("AfterMoveSecondarySelf", move, null, pokemon, target, move);
        this.battle.runEvent("AfterMoveSecondarySelf", pokemon, target, move);
        if (pokemon && pokemon !== target && move.category !== "Status") {
          if (pokemon.hp <= pokemon.maxhp / 2 && originalHp > pokemon.maxhp / 2) {
            this.battle.runEvent("EmergencyExit", pokemon, pokemon);
          }
        }
      }
      return true;
    },
    canTerastallize(pokemon) {
      if (this.dex.gen !== 9) {
        return null;
      }
      return pokemon.teraType;
    },
    canMegaEvo(pokemon) {
      const species = pokemon.baseSpecies;
      const altForme = species.otherFormes && this.dex.species.get(species.otherFormes[0]);
      const item = pokemon.getItem();
      if ((this.battle.gen <= 7 || this.battle.ruleTable.has("+tag:past") || this.battle.ruleTable.has("+tag:future")) && altForme?.isMega && altForme?.requiredMove && pokemon.baseMoves.includes(this.battle.toID(altForme.requiredMove)) && !item.zMove) {
        return altForme.name;
      }
      if (species.baseSpecies === "Magearna" && !species.isMega) {
        return species.name.includes("Original") ? "Magearna-Original-Mega" : "Magearna-Mega";
      }
      if (!item.megaStone) return null;
      return item.megaStone[species.name];
    },
    modifyDamage(baseDamage, pokemon, target, move, suppressMessages = false) {
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
        const pokeTypes = pokemon.getTypes(false, true);
        const isPrimarySTAB = move.forceSTAB || pokemon.hasType(type) && pokeTypes[0] === type;
        const isSecondarySTAB = move.forceSTAB || pokemon.hasType(type) && pokeTypes.length > 1 && pokeTypes[1] === type;
        const isSTAB = move.forceSTAB || pokemon.hasType(type) || pokemon.getTypes(false, true).includes(type);
        if (isPrimarySTAB) {
          stab = 1.7;
        }
        if (isSecondarySTAB) {
          stab = 1.2;
        }
        if (pokemon.terastallized === "Stellar") {
          if (!pokemon.stellarBoostedTypes.includes(type) || move.stellarBoosted) {
            stab = isSTAB ? 2.3 : [4915, 4096];
            move.stellarBoosted = true;
            if (pokemon.species.name !== "Terapagos-Stellar") {
              pokemon.stellarBoostedTypes.push(type);
            }
          }
        } else {
          if (pokemon.terastallized === type && pokeTypes.includes(type)) {
            stab = 2.3;
          }
          stab = this.battle.runEvent("ModifySTAB", pokemon, target, move, stab);
        }
        baseDamage = this.battle.modify(baseDamage, stab);
      }
      let typeMod = target.runEffectiveness(move);
      typeMod = this.battle.clampIntRange(typeMod, -6, 6);
      target.getMoveHitData(move).typeMod = typeMod;
      if (typeMod > 0) {
        if (!suppressMessages) this.battle.add("-supereffective", target);
        for (let i = 0; i < typeMod; i++) {
          baseDamage *= 2;
        }
      }
      if (typeMod < 0) {
        if (!suppressMessages) this.battle.add("-resisted", target);
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
      if (pokemon.status === "psn" && move.category === "Special") {
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
    getDamage(source, target, move, suppressMessages = false) {
      if (typeof move === "string") move = this.dex.getActiveMove(move);
      if (typeof move === "number") {
        const basePower2 = move;
        move = new this.dex.Move({
          basePower: basePower2,
          type: "???",
          category: "Physical",
          willCrit: false
        });
        move.hit = 0;
      }
      if (!target.runImmunity(move, !suppressMessages)) {
        return false;
      }
      if (move.ohko) return this.battle.gen === 3 ? target.hp : target.maxhp;
      if (move.damageCallback) return move.damageCallback.call(this.battle, source, target);
      if (move.damage === "level") {
        return source.level;
      } else if (move.damage) {
        return move.damage;
      }
      let category = this.battle.getCategory(move);
      let basePower = move.basePower;
      if (move.basePowerCallback) {
        basePower = move.basePowerCallback.call(this.battle, source, target, move);
      }
      if (!basePower) return basePower === 0 ? void 0 : basePower;
      basePower = this.battle.clampIntRange(basePower, 1);
      if (move.type === "Electric" && move.category === "Physical") {
        basePower += 15;
        category = "Special";
      }
      let critMult;
      let critRatio = this.battle.runEvent("ModifyCritRatio", source, target, move, move.critRatio || 0);
      if (this.battle.gen <= 5) {
        critRatio = this.battle.clampIntRange(critRatio, 0, 5);
        critMult = [0, 16, 8, 4, 3, 2];
      } else {
        critRatio = this.battle.clampIntRange(critRatio, 0, 4);
        if (this.battle.gen === 6) {
          critMult = [0, 16, 8, 2, 1];
        } else {
          critMult = [0, 24, 8, 2, 1];
        }
      }
      const moveHit = target.getMoveHitData(move);
      moveHit.crit = move.willCrit || false;
      if (move.willCrit === void 0) {
        if (critRatio) {
          moveHit.crit = this.battle.randomChance(1, critMult[critRatio]);
        }
      }
      if (moveHit.crit) {
        moveHit.crit = this.battle.runEvent("CriticalHit", target, null, move);
      }
      basePower = this.battle.runEvent("BasePower", source, target, move, basePower, true);
      if (!basePower) return 0;
      basePower = this.battle.clampIntRange(basePower, 1);
      if (!source.volatiles["dynamax"] && move.isMax || move.isMax && this.dex.moves.get(move.baseMove).isMax) {
        basePower = 0;
      }
      const dexMove = this.dex.moves.get(move.id);
      if (source.terastallized && (source.terastallized === "Stellar" ? !source.stellarBoostedTypes.includes(move.type) : source.hasType(move.type)) && basePower < 60 && dexMove.priority <= 0 && !dexMove.multihit && // Hard move.basePower check for moves like Dragon Energy that have variable BP
      !((move.basePower === 0 || move.basePower === 150) && move.basePowerCallback)) {
        basePower = 60;
      }
      const level = source.level;
      const attacker = move.overrideOffensivePokemon === "target" ? target : source;
      const defender = move.overrideDefensivePokemon === "source" ? source : target;
      const isPhysical = move.category === "Physical";
      let attackStat = move.overrideOffensiveStat || (isPhysical ? "atk" : "spa");
      const defenseStat = move.overrideDefensiveStat || (isPhysical ? "def" : "spd");
      const statTable = { atk: "Atk", def: "Def", spa: "SpA", spd: "SpD", spe: "Spe" };
      let atkBoosts = attacker.boosts[attackStat];
      let defBoosts = defender.boosts[defenseStat];
      let ignoreNegativeOffensive = !!move.ignoreNegativeOffensive;
      let ignorePositiveDefensive = !!move.ignorePositiveDefensive;
      if (moveHit.crit) {
        ignoreNegativeOffensive = true;
        ignorePositiveDefensive = true;
      }
      const ignoreOffensive = !!(move.ignoreOffensive || ignoreNegativeOffensive && atkBoosts < 0);
      const ignoreDefensive = !!(move.ignoreDefensive || ignorePositiveDefensive && defBoosts > 0);
      if (ignoreOffensive) {
        this.battle.debug("Negating (sp)atk boost/penalty.");
        atkBoosts = 0;
      }
      if (ignoreDefensive) {
        this.battle.debug("Negating (sp)def boost/penalty.");
        defBoosts = 0;
      }
      let attack = attacker.calculateStat(attackStat, atkBoosts, 1, source);
      let defense = defender.calculateStat(defenseStat, defBoosts, 1, target);
      attackStat = category === "Physical" ? "atk" : "spa";
      attack = this.battle.runEvent("Modify" + statTable[attackStat], source, target, move, attack);
      defense = this.battle.runEvent("Modify" + statTable[defenseStat], target, source, move, defense);
      if (this.battle.gen <= 4 && ["explosion", "selfdestruct"].includes(move.id) && defenseStat === "def") {
        defense = this.battle.clampIntRange(Math.floor(defense / 2), 1);
      }
      const tr = this.battle.trunc;
      const baseDamage = tr(tr(tr(tr(2 * level / 5 + 2) * basePower * attack) / defense) / 50);
      return this.modifyDamage(baseDamage, source, target, move, suppressMessages);
    }
  }
};
//# sourceMappingURL=scripts.js.map
