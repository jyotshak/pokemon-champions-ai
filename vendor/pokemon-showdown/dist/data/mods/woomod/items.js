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
var items_exports = {};
__export(items_exports, {
  Items: () => Items
});
module.exports = __toCommonJS(items_exports);
const Items = {
  belliboltkeychain: {
    name: "Bellibolt Keychain",
    shortDesc: "Tadbulb: moves lower the target's SpD by 1.",
    onSourceDamagingHit(damage, target, source, move) {
      if (source.baseSpecies.name !== "Tadbulb") return;
      this.boost({ spd: -1 }, target, source, null, true);
    },
    onTakeItem(item, source) {
      if (source.baseSpecies.name === "Tadbulb") return false;
      return true;
    },
    itemUser: ["Tadbulb"]
  },
  stormbringermask: {
    name: "Stormbringer Mask",
    shortDesc: "Farfetch'd: 1.2x power attacks; Ivy Cudgel is Electric type.",
    fling: {
      basePower: 60
    },
    onBasePowerPriority: 15,
    onBasePower(basePower, source, target, move) {
      if (source.species.id === "farfetchd") {
        return this.chainModify([4915, 4096]);
      }
    },
    onTakeItem(item, source) {
      if (source.species.id === "farfetchd") return false;
      return true;
    },
    itemUser: ["Farfetch'd"]
  },
  hearthflamemask: {
    inherit: true,
    shortDesc: "Farfetch'd: 1.2x power attacks; Ivy Cudgel is Fire type.",
    onBasePowerPriority: 15,
    onBasePower(basePower, user, target, move) {
      if (user.species.id === "farfetchd") {
        return this.chainModify([4915, 4096]);
      }
    },
    onTakeItem(item, source) {
      if (source.species.id === "farfetchd") return false;
      return true;
    },
    itemUser: ["Farfetch'd"]
  },
  wellspringmask: {
    inherit: true,
    shortDesc: "Farfetch'd: 1.2x power attacks; Ivy Cudgel is Water type.",
    onBasePowerPriority: 15,
    onBasePower(basePower, user, target, move) {
      if (user.species.id === "farfetchd") {
        return this.chainModify([4915, 4096]);
      }
    },
    onTakeItem(item, source) {
      if (source.species.id === "farfetchd") return false;
      return true;
    },
    itemUser: ["Farfetch'd"]
  },
  cornerstonemask: {
    inherit: true,
    shortDesc: "Farfetch'd: 1.2x power attacks; Ivy Cudgel is Rock type.",
    onBasePowerPriority: 15,
    onBasePower(basePower, user, target, move) {
      if (user.species.id === "farfetchd") {
        return this.chainModify([4915, 4096]);
      }
    },
    onTakeItem(item, source) {
      if (source.species.id === "farfetchd") return false;
      return true;
    },
    itemUser: ["Farfetch'd"]
  },
  leek: {
    inherit: true,
    onTakeItem(item, source) {
      if (source.species.id === "farfetchd") return false;
      return true;
    },
    itemUser: ["Farfetch'd"]
  },
  dragonairite: {
    name: "Dragonairite",
    megaStone: { "Dragonair": "Dragonair-Mega" },
    itemUser: ["Dragonair"],
    onTakeItem(item, source) {
      return !item.megaStone?.[source.baseSpecies.baseSpecies];
    },
    shortDesc: "If held by a Dragonair, this item allows it to Mega Evolve in battle."
  },
  amaurite: {
    name: "Amaurite",
    megaStone: { "Amaura": "Amaura-Mega" },
    itemUser: ["Amaura"],
    onTakeItem(item, source) {
      return !item.megaStone?.[source.baseSpecies.baseSpecies];
    },
    shortDesc: "If held by an Amaura, this item allows it to Mega Evolve in battle."
  },
  superpikachumegastone: {
    name: "Super Pikachu Mega Stone",
    megaStone: { "Pikachu": "Pikachu-Mega" },
    itemUser: ["Pikachu"],
    onTakeItem(item, source) {
      return !item.megaStone?.[source.baseSpecies.baseSpecies];
    },
    shortDesc: "pikachu mega evolve"
  }
};
//# sourceMappingURL=items.js.map
