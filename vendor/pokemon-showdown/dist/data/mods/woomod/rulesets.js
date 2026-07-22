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
var rulesets_exports = {};
__export(rulesets_exports, {
  Rulesets: () => Rulesets
});
module.exports = __toCommonJS(rulesets_exports);
const Rulesets = {
  megadatamod: {
    effectType: "Rule",
    name: "Mega Data Mod",
    desc: "Gives data on stats, Ability and types when a Pok\xE9mon Mega Evolves or undergoes Ultra Burst.",
    onSwitchIn(pokemon) {
      if (pokemon.species.forme.startsWith("Mega") || pokemon.species.forme.startsWith("Ultra")) {
        this.add("-start", pokemon, "typechange", pokemon.getTypes(true).join("/"), "[silent]");
      }
    },
    onAfterMega(pokemon) {
      this.add("-start", pokemon, "typechange", pokemon.getTypes(true).join("/"), "[silent]");
      const species = pokemon.species;
      let buf = `<span class="col pokemonnamecol" style="white-space: nowrap">${species.name}</span> `;
      buf += `<span class="col typecol">`;
      buf += `<img src="https://play.pokemonshowdown.com/sprites/types/${species.types[0]}.png" alt="${species.types[0]}" height="14" width="32">`;
      if (species.types[1]) {
        buf += `<img src="https://play.pokemonshowdown.com/sprites/types/${species.types[1]}.png" alt="${species.types[1]}" height="14" width="32">`;
      }
      buf += `</span> `;
      buf += `<span style="float: left ; min-height: 26px"><span class="col abilitycol">${species.abilities[0]}</span><span class="col abilitycol"></span></span>`;
      const stats = [];
      let stat;
      for (stat in species.baseStats) {
        const statNames = { hp: "HP", atk: "Atk", def: "Def", spa: "SpA", spd: "SpD", spe: "Spe" };
        stats.push(`<span class="col statcol"><em>${statNames[stat]}</em><br>${species.baseStats[stat]}</span>`);
      }
      buf += `<span style="float: left ; min-height: 26px">${stats.join(" ")}</span>`;
      buf += `</span>`;
      this.add(`raw|<ul class="utilichart"><li class="result">${buf}</li><li style="clear: both"></li></ul>`);
    }
  }
};
//# sourceMappingURL=rulesets.js.map
