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
var import_dex_data = require("../../../sim/dex-data");
var import_pokemon = require("../../../sim/pokemon");
const Scripts = {
  gen: 9,
  init() {
    for (const mon of this.species.all()) {
      if (mon.name === mon.baseSpecies && this.modData("Learnsets", mon.id)?.learnset) {
        this.modData("Learnsets", mon.id).learnset.holdhands = ["9L1"];
      }
    }
    this.modData("Learnsets", "alcremie").learnset.acidarmor = ["9L1"];
    this.modData("Learnsets", "drifblim").learnset.hurricane = ["9L1"];
    this.modData("Learnsets", "drifblim").learnset.infernalparade = ["9L1"];
    this.modData("Learnsets", "electrode").learnset.healingwish = ["9L1"];
    this.modData("Learnsets", "electrode").learnset.lunardance = ["9L1"];
    this.modData("Learnsets", "electrode").learnset.memento = ["9L1"];
    this.modData("Learnsets", "electrode").learnset.mistyexplosion = ["9L1"];
    this.modData("Learnsets", "flygon").learnset.healbell = ["9L1"];
    this.modData("Learnsets", "flygon").learnset.snarl = ["9L1"];
    this.modData("Learnsets", "flygon").learnset.quiverdance = ["9L1"];
    this.modData("Learnsets", "flygon").learnset.vacuumwave = ["9L1"];
    this.modData("Learnsets", "genesect").learnset.agility = ["9L1"];
    this.modData("Learnsets", "genesect").learnset.bubblebeam = ["9L1"];
    this.modData("Learnsets", "genesect").learnset.earthquake = ["9L1"];
    this.modData("Learnsets", "genesect").learnset.firepunch = ["9L1"];
    this.modData("Learnsets", "genesect").learnset.icepunch = ["9L1"];
    this.modData("Learnsets", "genesect").learnset.megapunch = ["9L1"];
    this.modData("Learnsets", "genesect").learnset.terablast = ["9L1"];
    this.modData("Learnsets", "genesect").learnset.terrainpulse = ["9L1"];
    this.modData("Learnsets", "genesect").learnset.thunderpunch = ["9L1"];
    this.modData("Learnsets", "genesect").learnset.waterpulse = ["9L1"];
    this.modData("Learnsets", "ironvaliant").learnset.playrough = ["9L1"];
    this.modData("Learnsets", "ironvaliant").learnset.willowisp = ["9L1"];
    this.modData("Learnsets", "ironvaliant").learnset.wish = ["9L1"];
    this.modData("Learnsets", "jirachi").learnset.holdhands = ["9L1"];
    this.modData("Learnsets", "kommoo").learnset.powergem = ["9L1"];
    this.modData("Learnsets", "kommoo").learnset.stoneedge = ["9L1"];
    this.modData("Learnsets", "mesprit").learnset.recover = ["9L1"];
    this.modData("Learnsets", "mesprit").learnset.gaslight = ["9L1"];
    this.modData("Learnsets", "octillery").learnset.recover = ["9L1"];
    this.modData("Learnsets", "shaymin").learnset.floralhealing = ["9L1"];
    this.modData("Learnsets", "shaymin").learnset.flowershield = ["9L1"];
    this.modData("Learnsets", "shaymin").learnset.flowertrick = ["9L1"];
    this.modData("Learnsets", "shaymin").learnset.sappyseed = ["9L1"];
    this.modData("Learnsets", "shaymin").learnset.strengthsap = ["9L1"];
    this.modData("Learnsets", "simisear").learnset.burningjealousy = ["9L1"];
    this.modData("Learnsets", "simisear").learnset.earthpower = ["9L1"];
    this.modData("Learnsets", "simisear").learnset.eruption = ["9L1"];
    this.modData("Learnsets", "simisear").learnset.fakeout = ["9L1"];
    this.modData("Learnsets", "simisear").learnset.mudshot = ["9L1"];
    this.modData("Learnsets", "simisear").learnset.temperflare = ["9L1"];
    this.modData("Learnsets", "simisear").learnset.terablast = ["9L1"];
    this.modData("Learnsets", "simisear").learnset.stoneedge = ["9L1"];
    this.modData("Learnsets", "simisear").learnset.swordsdance = ["9L1"];
    this.modData("Learnsets", "slowking").learnset.darkpulse = ["9L1"];
    this.modData("Learnsets", "slowking").learnset.sludgebomb = ["9L1"];
    this.modData("Learnsets", "slowking").learnset.sludgewave = ["9L1"];
    this.modData("Learnsets", "stakataka").learnset.taunt = ["9L1"];
    this.modData("Learnsets", "volcarona").learnset.weatherball = ["9L1"];
    this.modData("Learnsets", "volcarona").learnset.quiverdance = ["9L1"];
    this.modData("Learnsets", "weavile").learnset.amnesia = ["9L1"];
    this.modData("Learnsets", "weavile").learnset.auroraveil = ["9L1"];
    this.modData("Learnsets", "weavile").learnset.berrier = ["9L1"];
    this.modData("Learnsets", "weavile").learnset.dive = ["9L1"];
    this.modData("Learnsets", "weavile").learnset.haze = ["9L1"];
    this.modData("Learnsets", "weavile").learnset.hypnosis = ["9L1"];
    this.modData("Learnsets", "weavile").learnset.moonlight = ["9L1"];
    this.modData("Learnsets", "weavile").learnset.obstruct = ["9L1"];
    this.modData("Learnsets", "weavile").learnset.switcheroo = ["9L1"];
    this.modData("Learnsets", "wyrdeer").learnset.auroraveil = ["9L1"];
    this.modData("Learnsets", "wyrdeer").learnset.blizzard = ["9L1"];
    this.modData("Learnsets", "wyrdeer").learnset.freezedry = ["9L1"];
    this.modData("Learnsets", "wyrdeer").learnset.icebeam = ["9L1"];
    this.modData("Learnsets", "wyrdeer").learnset.iciclespear = ["9L1"];
    this.modData("Learnsets", "wyrdeer").learnset.icywind = ["9L1"];
    this.modData("Learnsets", "wyrdeer").learnset.solarbeam = ["9L1"];
    this.modData("Learnsets", "wyrdeer").learnset.energyball = ["9L1"];
    this.modData("Learnsets", "zarude").learnset.rest = ["9L1"];
    this.modData("Learnsets", "zeraora").learnset.doubleshock = ["9L1"];
    this.modData("Learnsets", "zeraora").learnset.highjumpkick = ["9L1"];
    this.modData("Learnsets", "zeraora").learnset.quickattack = ["9L1"];
    this.modData("Learnsets", "zeraora").learnset.charge = ["9L1"];
    this.modData("Learnsets", "aurorus").learnset.primalpulse = ["9L1"];
    this.modData("Learnsets", "cofagrigus").learnset.dragonscurse = ["9L1"];
    this.modData("Learnsets", "dudunsparce").learnset.sixtongueemojis = ["9L1"];
    this.modData("Learnsets", "kecleon").learnset.kaleidostorm = ["9L1"];
    this.modData("Learnsets", "beartic").learnset.glacierfang = ["9L1"];
    this.modData("Learnsets", "stakataka").learnset.stackshield = ["9L1"];
    this.modData("Learnsets", "aegislash").learnset.soulboundslash = ["9L1"];
    this.modData("Learnsets", "landorus").learnset.generationaldeevolution = ["9L1"];
    this.modData("Learnsets", "sylveon").learnset.ribbonshift = ["9L1"];
    this.modData("Learnsets", "slowking").learnset.frostbittenreception = ["9L1"];
  },
  actions: {
    inherit: true,
    modifyDamage(baseDamage, pokemon, target, move, suppressMessages = false) {
      const tr = this.battle.trunc;
      if (!move.type) move.type = "???";
      let type = move.type;
      baseDamage += 2;
      if (move.spreadHit) {
        const spreadModifier = this.battle.gameType === "freeforall" ? 0.5 : 0.75;
        this.battle.debug(`Spread modifier: ${spreadModifier}`);
        baseDamage = this.battle.modify(baseDamage, spreadModifier);
      } else if (move.multihitType === "parentalbond" && move.hit > 1) {
        const bondModifier = this.battle.gen > 6 ? 0.25 : 0.5;
        this.battle.debug(`Parental Bond modifier: ${bondModifier}`);
        baseDamage = this.battle.modify(baseDamage, bondModifier);
        if (pokemon.ability === "aurapartner") {
          type = "Ghost";
          move.type = "Ghost";
        }
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
    canUltraBurst(pokemon) {
      if (["Necrozma-Dawn-Wings", "Necrozma-Dusk-Mane"].includes(pokemon.baseSpecies.name) && pokemon.getItem().id === "ultranecroziumz") {
        return "Necrozma-Ultra";
      } else if (pokemon.baseSpecies.name === "Simisear" && pokemon.getItem().id === "ultrasimiseariumz") {
        return "Simisear-Ultra";
      }
      return null;
    },
    runSwitch(pokemon) {
      const switchersIn = [pokemon];
      while (this.battle.queue.peek()?.choice === "runSwitch") {
        const nextSwitch = this.battle.queue.shift();
        switchersIn.push(nextSwitch.pokemon);
      }
      const allActive = this.battle.getAllActive(true);
      this.battle.speedSort(allActive);
      this.battle.speedOrder = allActive.map((a) => a.side.n * a.battle.sides.length + a.position);
      this.battle.fieldEvent("SwitchIn", switchersIn);
      for (const poke of switchersIn) {
        if (!poke.hp) continue;
        poke.isStarted = true;
        poke.draggedIn = null;
        if (poke.species.name === "Iron Valiant" && !pokemon.battle.ruleTable.has("+tag:cap"))
          pokemon.m.usedMoves = [];
        if (poke.species.name === "Sudowoodo" && !pokemon.battle.ruleTable.has("+tag:cap"))
          poke.m.grassMoves = 0;
      }
      return true;
    },
    useMove(move, pokemon, options) {
      pokemon.moveThisTurnResult = void 0;
      const oldMoveResult = pokemon.moveThisTurnResult;
      const success = this.useMoveInner(move, pokemon, options);
      if (oldMoveResult === pokemon.moveThisTurnResult) pokemon.moveThisTurnResult = success;
      if (success && pokemon.species.name === "Iron Valiant" && !pokemon.battle.ruleTable.has("+tag:cap")) {
        if (!pokemon.m.usedMoves) pokemon.m.usedMoves = [];
        if (!pokemon.m.usedMoves.includes(move.id)) pokemon.m.usedMoves.push(move.id);
        if (pokemon.moves.filter((name) => pokemon.m.usedMoves.includes(name)).toString() === pokemon.moves.toString())
          pokemon.formeChange("Iron Valiant-High-Judge", null, true);
      }
      if (success && pokemon.species.name === "Mewtwo" && !pokemon.battle.ruleTable.has("+tag:cap")) {
        if (!pokemon.m.darkMoves) pokemon.m.darkMoves = 0;
        if (move.type === "Dark") pokemon.m.darkMoves++;
        if (pokemon.m.darkMoves >= 3)
          pokemon.formeChange("Mewtwo-Evil-Scary", null, true);
      }
      if (success && pokemon.species.name === "Volcanion" && !pokemon.battle.ruleTable.has("+tag:cap")) {
        if (!pokemon.m.steamMoves) pokemon.m.steamMoves = 0;
        if (move.type === "Water" || move.type === "Fire") pokemon.m.steamMoves++;
        if (pokemon.m.steamMoves >= 3)
          pokemon.formeChange("Volcanion-Surge", null, true);
      }
      if (success && move.type === "Grass" && !pokemon.battle.ruleTable.has("+tag:cap")) {
        for (const mon of pokemon.foes()) {
          if (mon.species.name !== "Sudowoodo") continue;
          if (!mon.m.grassMoves) mon.m.grassMoves = 0;
          mon.m.grassMoves++;
          if (mon.m.grassMoves >= 2) {
            mon.formeChange("Sudowoodo-Nopseudo", null, true);
          }
        }
        for (const mon of pokemon.alliesAndSelf()) {
          if (mon.species.name !== "Sudowoodo") continue;
          if (!mon.m.grassMoves) mon.m.grassMoves = 0;
          mon.m.grassMoves++;
          if (mon.m.grassMoves >= 2) {
            mon.formeChange("Sudowoodo-Nopseudo", null, true);
          }
        }
      }
      return success;
    },
    terastallize(pokemon) {
      if (pokemon.species.baseSpecies === "Ogerpon" && !["Fire", "Grass", "Rock", "Water", "Fairy"].includes(pokemon.teraType) && (!pokemon.illusion || pokemon.illusion.species.baseSpecies === "Ogerpon")) {
        this.battle.hint("If Ogerpon Terastallizes into a type other than Fire, Grass, Rock, or Water, the game crashes.", false, pokemon.side);
        return;
      }
      if (pokemon.illusion && ["Ogerpon", "Terapagos"].includes(pokemon.illusion.species.baseSpecies)) {
        this.battle.singleEvent("End", this.dex.abilities.get("Illusion"), pokemon.abilityState, pokemon);
      }
      const type = pokemon.teraType;
      this.battle.add("-terastallize", pokemon, type);
      pokemon.terastallized = type;
      for (const ally of pokemon.side.pokemon) {
        ally.canTerastallize = null;
      }
      pokemon.addedType = "";
      pokemon.knownType = true;
      pokemon.apparentType = type;
      if (pokemon.species.baseSpecies === "Ogerpon") {
        let ogerponSpecies = (0, import_dex_data.toID)(pokemon.species.battleOnly || pokemon.species.id);
        ogerponSpecies += ogerponSpecies === "ogerpon" ? "tealtera" : "tera";
        pokemon.formeChange(ogerponSpecies, null, true);
      }
      if (pokemon.species.name === "Terapagos-Terastal") {
        pokemon.formeChange("Terapagos-Stellar", null, true);
      }
      if (pokemon.species.baseSpecies === "Morpeko" && !pokemon.transformed && pokemon.baseSpecies.id !== pokemon.species.id) {
        pokemon.formeRegression = true;
        pokemon.baseSpecies = pokemon.species;
        pokemon.details = pokemon.getUpdatedDetails();
      }
      this.battle.runEvent("AfterTerastallization", pokemon);
    }
  },
  faintMessages(lastFirst = false, forceCheck = false, checkWin = true) {
    if (this.ended) return;
    const length = this.faintQueue.length;
    if (!length) {
      if (forceCheck && this.checkWin()) return true;
      return false;
    }
    if (lastFirst) {
      this.faintQueue.unshift(this.faintQueue[this.faintQueue.length - 1]);
      this.faintQueue.pop();
    }
    let faintQueueLeft, faintData;
    while (this.faintQueue.length) {
      faintQueueLeft = this.faintQueue.length;
      faintData = this.faintQueue.shift();
      const pokemon = faintData.target;
      if (!pokemon.fainted && this.runEvent("BeforeFaint", pokemon, faintData.source, faintData.effect)) {
        if (pokemon.species.name === "Kecleon" && !this.ruleTable.has("+tag:cap")) {
          let forme = "None";
          switch (pokemon.types[0]) {
            case "Fire":
            case "Rock":
            case "Ground":
              forme = "Kecleon-Volcanic";
              break;
            case "Grass":
            case "Bug":
            case "Poison":
              forme = "Kecleon-Wild";
              break;
            case "Electric":
            case "Fairy":
            case "Psychic":
              forme = "Kecleon-Luminous";
              break;
            case "Ghost":
            case "Dragon":
            case "Steel":
              forme = "Kecleon-Storybook";
              break;
            case "Ice":
            case "Water":
            case "Flying":
              forme = "Kecleon-Phasic";
              break;
            case "Normal":
            case "Fighting":
            case "Dark":
              forme = "Kecleon-Ruffian";
              break;
            default:
              forme = "None";
          }
          if (forme !== "None") {
            pokemon.formeChange(forme, null, true);
            this.add("-message", `Kecleon was resurrected into ${pokemon.species}.`);
            pokemon.faintQueued = false;
            pokemon.subFainted = false;
            pokemon.status = "";
            pokemon.hp = 1;
            pokemon.sethp(pokemon.maxhp);
            pokemon.ability = pokemon.baseAbility;
            this.add("-heal", pokemon, pokemon.getHealth, "[from] move: Revival Blessing");
            continue;
          }
        }
        this.add("faint", pokemon);
        if (pokemon.side.pokemonLeft) pokemon.side.pokemonLeft--;
        if (pokemon.side.totalFainted < 100) pokemon.side.totalFainted++;
        this.runEvent("Faint", pokemon, faintData.source, faintData.effect);
        this.singleEvent("End", pokemon.getAbility(), pokemon.abilityState, pokemon);
        this.singleEvent("End", pokemon.getItem(), pokemon.itemState, pokemon);
        if (pokemon.formeRegression && !pokemon.transformed) {
          pokemon.baseSpecies = this.dex.species.get(pokemon.set.species || pokemon.set.name);
          pokemon.baseAbility = (0, import_dex_data.toID)(pokemon.set.ability);
        }
        pokemon.clearVolatile(false);
        pokemon.fainted = true;
        pokemon.illusion = null;
        pokemon.isActive = false;
        pokemon.isStarted = false;
        delete pokemon.terastallized;
        if (pokemon.formeRegression) {
          pokemon.details = pokemon.getUpdatedDetails();
          this.add("detailschange", pokemon, pokemon.details, "[silent]");
          pokemon.updateMaxHp();
          pokemon.formeRegression = false;
        }
        pokemon.side.faintedThisTurn = pokemon;
        if (this.faintQueue.length >= faintQueueLeft) checkWin = true;
      }
    }
    if (this.gen <= 1) {
      this.queue.clear();
    } else if (this.gen <= 3 && this.gameType === "singles") {
      for (const pokemon of this.getAllActive()) {
        if (this.gen <= 2) {
          this.queue.cancelMove(pokemon);
        } else {
          this.queue.cancelAction(pokemon);
        }
      }
    }
    if (checkWin && this.checkWin(faintData)) return true;
    if (faintData && length) {
      this.runEvent("AfterFaint", faintData.target, faintData.source, faintData.effect, length);
    }
    return false;
  },
  field: {
    setWeather(status, source = null, sourceEffect = null) {
      status = this.battle.dex.conditions.get(status);
      if (!sourceEffect && this.battle.effect) sourceEffect = this.battle.effect;
      if (!source && this.battle.event?.target) source = this.battle.event.target;
      if (source === "debug") source = this.battle.sides[0].active[0];
      if (this.weather === status.id) {
        if (sourceEffect && sourceEffect.effectType === "Ability") {
          if (this.battle.gen > 5 || this.weatherState.duration === 0) {
            return false;
          }
        } else if (this.battle.gen > 2 || status.id === "sandstorm") {
          return false;
        }
      }
      if (source) {
        const result = this.battle.runEvent("SetWeather", source, source, status);
        if (!result) {
          if (result === false) {
            if (sourceEffect?.weather) {
              this.battle.add("-fail", source, sourceEffect, "[from] " + this.weather);
            } else if (sourceEffect && sourceEffect.effectType === "Ability") {
              this.battle.add("-ability", source, sourceEffect, "[from] " + this.weather, "[fail]");
            }
          }
          return null;
        }
      }
      const prevWeather = this.weather;
      const prevWeatherState = this.weatherState;
      this.weather = status.id;
      this.weatherState = this.battle.initEffectState({ id: status.id });
      if (source) {
        this.weatherState.source = source;
        this.weatherState.sourceSlot = source.getSlot();
      }
      if (status.duration) {
        this.weatherState.duration = status.duration;
      }
      if (status.durationCallback) {
        if (!source) throw new Error(`setting weather without a source`);
        this.weatherState.duration = status.durationCallback.call(this.battle, source, source, sourceEffect);
      }
      if (!this.battle.singleEvent("FieldStart", status, this.weatherState, this, source, sourceEffect)) {
        this.weather = prevWeather;
        this.weatherState = prevWeatherState;
        return false;
      } else if (prevWeather === "snowscape" && !this.battle.ruleTable.has("+tag:cap")) {
        for (const pokemon of this.battle.getAllActive()) {
          if (pokemon.species.id === "wyrdeer") {
            pokemon.formeChange("Wyrdeer-Snowblind", this.battle.effect, true);
            this.battle.add("-activate", pokemon, "ability: Heart of Cold");
          }
        }
      }
      this.battle.eachEvent("WeatherChange", sourceEffect);
      return true;
    }
  },
  pokemon: {
    inherit: true,
    isGrounded(negateImmunity = false) {
      if ("gravity" in this.battle.field.pseudoWeather) return true;
      if ("ingrain" in this.volatiles && this.battle.gen >= 4) return true;
      if ("smackdown" in this.volatiles) return true;
      const item = this.ignoringItem() ? "" : this.item;
      if (item === "ironball") return true;
      if (!negateImmunity && this.hasType("Flying") && !(this.hasType("???") && "roost" in this.volatiles)) return false;
      if (this.hasAbility(["levitate", "eelevate"]) && !this.battle.suppressingAbility(this)) return null;
      if ("magnetrise" in this.volatiles) return false;
      if ("telekinesis" in this.volatiles) return false;
      return item !== "airballoon";
    },
    cureStatus(silent, source = null) {
      if (!this.hp || !this.status) return false;
      if (source?.ability === "herbalelixir") {
        switch (this.status) {
          case "psn":
          case "tox":
            this.setAbility("poisonheal");
            this.baseAbility = this.ability;
            return false;
          case "brn":
            this.setAbility("guts");
            this.baseAbility = this.ability;
            return false;
          case "par":
            this.setAbility("quickfeet");
            this.baseAbility = this.ability;
            return false;
          case "ber":
            this.setAbility("marvelscale");
            this.baseAbility = this.ability;
            return false;
          default:
            break;
        }
      }
      this.setStatus("");
      this.battle.add("-curestatus", this, this.status, silent ? "[silent]" : "[msg]");
      if (this.status === "slp" && this.removeVolatile("nightmare")) {
        this.battle.add("-end", this, "Nightmare", "[silent]");
      }
      if (source?.species.name === "Zarude" && !source.battle.ruleTable.has("+tag:cap")) {
        source.formeChange("Zarude-Alchemist", null, true);
      }
      return true;
    },
    eatItem(force, source, sourceEffect) {
      if (!this.item) return false;
      if (!this.hp && this.item !== "jabocaberry" && this.item !== "rowapberry" || !this.isActive) return false;
      if (!sourceEffect && this.battle.effect) sourceEffect = this.battle.effect;
      if (!source && this.battle.event?.target) source = this.battle.event.target;
      const item = this.getItem();
      if (sourceEffect?.effectType === "Item" && this.item !== sourceEffect.id && source === this) {
        return false;
      }
      if (this.battle.runEvent("UseItem", this, null, null, item) && (force || this.battle.runEvent("TryEatItem", this, null, null, item))) {
        this.battle.add("-enditem", this, item, "[eat]");
        this.battle.singleEvent("Eat", item, this.itemState, this, source, sourceEffect);
        this.battle.runEvent("EatItem", this, source, sourceEffect, item);
        if (import_pokemon.RESTORATIVE_BERRIES.has(item.id)) {
          switch (this.pendingStaleness) {
            case "internal":
              if (this.staleness !== "external") this.staleness = "internal";
              break;
            case "external":
              this.staleness = "external";
              break;
          }
          this.pendingStaleness = void 0;
        }
        this.lastItem = this.item;
        this.item = "";
        this.battle.clearEffectState(this.itemState);
        this.usedItemThisTurn = true;
        this.ateBerry = true;
        if (this.species.baseSpecies === "Alcremie" && !this.battle.ruleTable.has("+tag:cap")) {
          switch (this.species.id) {
            case "alcremierubycream":
              this.formeChange("Alcremie-Sweetened-Ruby-Cream", null, true);
              break;
            case "alcremiematchacream":
              this.formeChange("Alcremie-Sweetened-Matcha-Cream", null, true);
              break;
            case "alcremiemintcream":
              this.formeChange("Alcremie-Sweetened-Mint-Cream", null, true);
              break;
            case "alcremielemoncream":
              this.formeChange("Alcremie-Sweetened-Lemon-Cream", null, true);
              break;
            case "alcremiesaltedcream":
              this.formeChange("Alcremie-Sweetened-Salted-Cream", null, true);
              break;
            case "alcremierubyswirl":
              this.formeChange("Alcremie-Sweetened-Ruby-Swirl", null, true);
              break;
            case "alcremiecaramelswirl":
              this.formeChange("Alcremie-Sweetened-Caramel-Swirl", null, true);
              break;
            case "alcremierainbowswirl":
              this.formeChange("Alcremie-Sweetened-Rainbow-Swirl", null, true);
              break;
            default:
              this.formeChange("Alcremie-Sweetened", null, true);
              break;
          }
          switch (this.lastItem) {
            case "aguavberry":
              this.battle.boost({ spd: 1 }, this);
              break;
            case "enigmaberry":
              const type = this.battle.dex.types.names()[this.battle.random(18)];
              if (this.hasType(type)) return false;
              if (!this.addType(type)) return false;
              this.battle.add("-start", this, "typeadd", type);
              break;
            case "figyberry":
              this.battle.boost({ atk: 1 }, this);
              break;
            case "iapapaberry":
              this.battle.boost({ def: 1 }, this);
              break;
            case "magoberry":
              this.battle.boost({ spe: 1 }, this);
              break;
            case "oranberry":
              this.heal(this.maxhp);
              break;
            case "sitrusberry":
              const side = this.side.foe;
              if (!side.sideConditions["stickyweb"]) {
                side.addSideCondition("stickyweb", this.foes()[0]);
              }
              break;
            case "wikiberry":
              this.battle.boost({ spa: 1 }, this);
              break;
            default:
              break;
          }
        }
        this.battle.runEvent("AfterUseItem", this, null, null, item);
        return true;
      }
      return false;
    },
    calculateStat(statName, boost, modifier, statUser) {
      statName = (0, import_dex_data.toID)(statName);
      if (statName === "hp") throw new Error("Please read `maxhp` directly");
      let stat = this.storedStats[statName];
      if (!this.battle.ruleTable.has("+tag:cap")) {
        const mon = this;
        if (mon.timesSwitchedIn && mon.ability !== "tryingmybest") {
          stat *= (10 + mon.timesSwitchedIn) / 10;
        }
      }
      if ("wonderroom" in this.battle.field.pseudoWeather) {
        if (statName === "def") {
          stat = this.storedStats["spd"];
        } else if (statName === "spd") {
          stat = this.storedStats["def"];
        }
      }
      let boosts = {};
      const boostName = statName;
      boosts[boostName] = boost;
      boosts = this.battle.runEvent("ModifyBoost", statUser || this, null, null, boosts);
      boost = boosts[boostName];
      const boostTable = [1, 1.5, 2, 2.5, 3, 3.5, 4];
      if (boost > 6) boost = 6;
      if (boost < -6) boost = -6;
      if (boost >= 0) {
        stat = Math.floor(stat * boostTable[boost]);
      } else {
        stat = Math.floor(stat / boostTable[-boost]);
      }
      return this.battle.modify(stat, modifier || 1);
    },
    getStat(statName, unboosted, unmodified) {
      statName = (0, import_dex_data.toID)(statName);
      if (statName === "hp") throw new Error("Please read `maxhp` directly");
      let stat = this.storedStats[statName];
      if (!this.battle.ruleTable.has("+tag:cap")) {
        const mon = this;
        if (mon.timesSwitchedIn && mon.ability !== "tryingmybest") {
          stat *= (10 + mon.timesSwitchedIn) / 10;
        }
      }
      if (unmodified && "wonderroom" in this.battle.field.pseudoWeather) {
        if (statName === "def") {
          statName = "spd";
        } else if (statName === "spd") {
          statName = "def";
        }
      }
      if (!unboosted) {
        let boosts = this.boosts;
        if (!unmodified) {
          boosts = this.battle.runEvent("ModifyBoost", this, null, null, { ...boosts });
        }
        let boost = boosts[statName];
        const boostTable = [1, 1.5, 2, 2.5, 3, 3.5, 4];
        if (boost > 6) boost = 6;
        if (boost < -6) boost = -6;
        if (boost >= 0) {
          stat = Math.floor(stat * boostTable[boost]);
        } else {
          stat = Math.floor(stat / boostTable[-boost]);
        }
      }
      if (!unmodified) {
        const statTable = { atk: "Atk", def: "Def", spa: "SpA", spd: "SpD", spe: "Spe" };
        stat = this.battle.runEvent("Modify" + statTable[statName], this, null, null, stat);
      }
      if (statName === "spe" && stat > 1e4 && !this.battle.format.battle?.trunc) stat = 1e4;
      return stat;
    }
  }
};
//# sourceMappingURL=scripts.js.map
