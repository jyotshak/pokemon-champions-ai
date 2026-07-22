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
const Scripts = {
  gen: 9,
  inherit: "gen9",
  // A Pokémon transformed into Ogerpon should accept the Terastallization choice, but not Terastallize
  actions: {
    inherit: true,
    terastallize(pokemon) {
      if (pokemon.transformed && ["Ogerpon", "Terapagos"].includes(pokemon.species.baseSpecies)) {
        this.battle.hint("A Pok\xE9mon terastallized into Ogerpon or Terapagos cannot terastallize.");
        return;
      }
      if (pokemon.species.baseSpecies === "Ogerpon" && !["Fire", "Grass", "Rock", "Water"].includes(pokemon.teraType) && (!pokemon.illusion || pokemon.illusion.species.baseSpecies === "Ogerpon")) {
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
  pokemon: {
    inherit: true,
    transformInto(pokemon, effect) {
      const species = pokemon.species;
      if (pokemon.fainted || this.illusion || pokemon.illusion || pokemon.volatiles["substitute"] && this.battle.gen >= 5 || pokemon.transformed && this.battle.gen >= 2 || this.transformed && this.battle.gen >= 5 || species.name === "Eternatus-Eternamax" || ["Ogerpon", "Terapagos"].includes(species.baseSpecies) && (this.terastallized || pokemon.terastallized) || this.terastallized === "Stellar") {
        return false;
      }
      if (this.battle.dex.currentMod === "gen1stadium" && (species.name === "Ditto" || this.species.name === "Ditto" && pokemon.moves.includes("transform"))) {
        return false;
      }
      if (!this.setSpecies(species, effect, true)) return false;
      this.transformed = true;
      this.weighthg = pokemon.weighthg;
      const types = pokemon.getTypes(true, true);
      this.setType(pokemon.volatiles["roost"] ? pokemon.volatiles["roost"].typeWas : types, true);
      this.addedType = pokemon.addedType;
      this.knownType = this.isAlly(pokemon) && pokemon.knownType;
      this.apparentType = pokemon.apparentType;
      let statName;
      for (statName in this.storedStats) {
        this.storedStats[statName] = pokemon.storedStats[statName];
        if (this.modifiedStats) this.modifiedStats[statName] = pokemon.modifiedStats[statName];
      }
      this.moveSlots = [];
      this.hpType = this.battle.gen >= 5 ? this.hpType : pokemon.hpType;
      this.hpPower = this.battle.gen >= 5 ? this.hpPower : pokemon.hpPower;
      this.timesAttacked = pokemon.timesAttacked;
      for (const [i, moveSlot] of pokemon.moveSlots.entries()) {
        let moveName = moveSlot.move;
        if (moveSlot.id === "hiddenpower") {
          moveName = "Hidden Power " + this.hpType;
        }
        const move = this.battle.dex.moves.get(moveSlot.id);
        const pp = Math.min(5, move.pp);
        this.moveSlots.push({
          move: moveName,
          id: moveSlot.id,
          pp,
          maxpp: this.battle.gen >= 5 ? pp : this.battle.calculatePP(move, this.ppUps[i] || 0),
          target: moveSlot.target,
          disabled: false,
          used: false,
          virtual: true
        });
      }
      let boostName;
      for (boostName in pokemon.boosts) {
        this.boosts[boostName] = pokemon.boosts[boostName];
      }
      if (this.battle.gen >= 6) {
        const volatilesToCopy = ["dragoncheer", "focusenergy", "gmaxchistrike", "laserfocus"];
        for (const volatile of volatilesToCopy) this.removeVolatile(volatile);
        for (const volatile of volatilesToCopy) {
          if (pokemon.volatiles[volatile]) {
            this.addVolatile(volatile);
            if (volatile === "gmaxchistrike") this.volatiles[volatile].layers = pokemon.volatiles[volatile].layers;
            if (volatile === "dragoncheer") this.volatiles[volatile].hasDragonType = pokemon.volatiles[volatile].hasDragonType;
          }
        }
      }
      if (effect) {
        this.battle.add("-transform", this, pokemon, "[from] " + effect.fullname);
      } else {
        this.battle.add("-transform", this, pokemon);
      }
      if (this.terastallized) {
        this.knownType = true;
        this.apparentType = this.terastallized;
      }
      if (this.battle.gen > 2) this.setAbility(pokemon.ability, this, null, true, true);
      if (this.battle.gen === 4) {
        if (this.species.num === 487) {
          if (this.species.name === "Giratina" && this.item === "griseousorb") {
            this.formeChange("Giratina-Origin");
          } else if (this.species.name === "Giratina-Origin" && this.item !== "griseousorb") {
            this.formeChange("Giratina");
          }
        }
        if (this.species.num === 493) {
          const item = this.getItem();
          const targetForme = item?.onPlate ? "Arceus-" + item.onPlate : "Arceus";
          if (this.species.name !== targetForme) {
            this.formeChange(targetForme);
          }
        }
      }
      return true;
    }
  }
};
//# sourceMappingURL=scripts.js.map
