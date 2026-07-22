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
var battle_stream_exports = {};
__export(battle_stream_exports, {
  BattlePlayer: () => BattlePlayer,
  BattleStream: () => BattleStream,
  BattleTextStream: () => BattleTextStream,
  getPlayerStreams: () => getPlayerStreams
});
module.exports = __toCommonJS(battle_stream_exports);
var import_lib = require("../lib");
var import_teams = require("./teams");
var import_battle = require("./battle");
/**
 * Battle Stream
 * Pokemon Showdown - http://pokemonshowdown.com/
 *
 * Supports interacting with a PS battle in Stream format.
 *
 * This format is VERY NOT FINALIZED, please do not use it directly yet.
 *
 * @license MIT
 */
class BattleStream extends import_lib.Streams.ObjectReadWriteStream {
  constructor(options2 = {}) {
    super();
    this.debug = !!options2.debug;
    this.noCatch = !!options2.noCatch;
    this.replay = options2.replay || false;
    this.keepAlive = !!options2.keepAlive;
    this.battle = null;
  }
  _write(chunk) {
    if (this.noCatch) {
      this._writeLines(chunk);
    } else {
      try {
        this._writeLines(chunk);
      } catch (err) {
        this.pushError(err, true);
        return;
      }
    }
    if (this.battle) this.battle.sendUpdates();
  }
  _writeLines(chunk) {
    for (const line of chunk.split("\n")) {
      if (line.startsWith(">")) {
        const [type2, message2] = import_lib.Utils.splitFirst(line.slice(1), " ");
        this._writeLine(type2, message2);
      }
    }
  }
  pushMessage(type2, data) {
    if (this.replay) {
      if (type2 === "update") {
        if (this.replay === "spectator") {
          const channelMessages = (0, import_battle.extractChannelMessages)(data, [0]);
          this.push(channelMessages[0].join("\n"));
        } else {
          const channelMessages = (0, import_battle.extractChannelMessages)(data, [-1]);
          this.push(channelMessages[-1].join("\n"));
        }
      }
      return;
    }
    this.push(`${type2}
${data}`);
  }
  _writeLine(type, message) {
    switch (type) {
      case "start":
        const options = JSON.parse(message);
        options.send = (t, data) => {
          if (Array.isArray(data)) data = data.join("\n");
          this.pushMessage(t, data);
          if (t === "end" && !this.keepAlive) this.pushEnd();
        };
        if (this.debug) options.debug = true;
        this.battle = new import_battle.Battle(options);
        break;
      case "player":
        const [slot, optionsText] = import_lib.Utils.splitFirst(message, " ");
        this.battle.setPlayer(slot, JSON.parse(optionsText));
        break;
      case "p1":
      case "p2":
      case "p3":
      case "p4":
        if (message === "undo") {
          this.battle.undoChoice(type);
        } else {
          this.battle.choose(type, message);
        }
        break;
      case "forcewin":
      case "forcetie":
        this.battle.win(type === "forcewin" ? message : null);
        if (message) {
          this.battle.inputLog.push(`>forcewin ${message}`);
        } else {
          this.battle.inputLog.push(`>forcetie`);
        }
        break;
      case "forcelose":
        this.battle.lose(message);
        this.battle.inputLog.push(`>forcelose ${message}`);
        break;
      case "reseed":
        this.battle.resetRNG(message);
        this.battle.inputLog.push(`>reseed ${this.battle.prng.getSeed()}`);
        break;
      case "tiebreak":
        this.battle.tiebreak();
        break;
      case "chat-inputlogonly":
        this.battle.inputLog.push(`>chat ${message}`);
        break;
      case "chat":
        this.battle.inputLog.push(`>chat ${message}`);
        this.battle.add("chat", `${message}`);
        break;
      case "eval":
        const battle = this.battle;
        battle.inputLog.push(`>${type} ${message}`);
        message = message.replace(/\f/g, "\n");
        battle.add("", ">>> " + message.replace(/\n/g, "\n||"));
        try {
          const p1 = battle.sides[0];
          const p2 = battle.sides[1];
          const p3 = battle.sides[2];
          const p4 = battle.sides[3];
          const p1active = p1?.active[0];
          const p2active = p2?.active[0];
          const p3active = p3?.active[0];
          const p4active = p4?.active[0];
          const toID = battle.toID;
          const player = (input) => {
            input = toID(input);
            if (/^p[1-9]$/.test(input)) return battle.sides[parseInt(input.slice(1)) - 1];
            if (/^[1-9]$/.test(input)) return battle.sides[parseInt(input) - 1];
            for (const side2 of battle.sides) {
              if (toID(side2.name) === input) return side2;
            }
            return null;
          };
          const pokemon = (side2, input) => {
            if (typeof side2 === "string") side2 = player(side2);
            input = toID(input);
            if (/^[1-9]$/.test(input)) return side2.pokemon[parseInt(input) - 1];
            return side2.pokemon.find((p) => p.baseSpecies.id === input || p.species.id === input);
          };
          let result = eval(message);
          if (result?.then) {
            result.then((unwrappedResult) => {
              unwrappedResult = import_lib.Utils.visualize(unwrappedResult);
              battle.add("", "Promise -> " + unwrappedResult);
              battle.sendUpdates();
            }, (error) => {
              battle.add("", "<<< error: " + error.message);
              battle.sendUpdates();
            });
          } else {
            result = import_lib.Utils.visualize(result);
            result = result.replace(/\n/g, "\n||");
            battle.add("", "<<< " + result);
          }
        } catch (e) {
          battle.add("", "<<< error: " + e.message);
        }
        break;
      case "editbattle":
        try {
          this.editbattle(message);
          this.battle.inputLog.push(`>editbattle ${message}`);
        } catch (e) {
          this.battle.add("", "<<< error: " + e.message);
        }
        break;
      case "requestlog":
        this.push(`requesteddata
${this.battle.inputLog.join("\n")}`);
        break;
      case "requestexport":
        this.push(`requesteddata
${this.battle.prngSeed}
${this.battle.inputLog.join("\n")}`);
        break;
      case "requestteam":
        message = message.trim();
        const slotNum = parseInt(message.slice(1)) - 1;
        if (isNaN(slotNum) || slotNum < 0) {
          throw new Error(`Team requested for slot ${message}, but that slot does not exist.`);
        }
        const side = this.battle.sides[slotNum];
        const team = import_teams.Teams.pack(side.team);
        this.push(`requesteddata
${team}`);
        break;
      case "show-openteamsheets":
        this.battle.showOpenTeamSheets();
        break;
      case "version":
      case "version-origin":
        break;
      default:
        throw new Error(`Unrecognized command ">${type} ${message}"`);
    }
  }
  editbattle(target) {
    const battle2 = this.battle;
    const toID2 = battle2.toID;
    const getPlayer = (originalInput) => {
      const input = toID2(originalInput);
      if (/^p[1-9]$/.test(input)) return battle2.sides[parseInt(input.slice(1)) - 1];
      if (/^[1-9]$/.test(input)) return battle2.sides[parseInt(input) - 1];
      for (const side2 of battle2.sides) {
        if (toID2(side2.name) === input) return side2;
      }
      throw new Error(`Player "${originalInput}" not found`);
    };
    const getPokemon = (side2, input) => {
      if (typeof side2 === "string") side2 = getPlayer(side2);
      input = toID2(input);
      let out = null;
      if (/^[1-9]$/.test(input)) out = side2.pokemon[parseInt(input) - 1];
      else out = side2.pokemon.find((p) => p.baseSpecies.id === input || p.species.id === input);
      if (!out) throw new Error(`Pokemon "${side2.name} ${input}" not found`);
      return out;
    };
    const requireInt = (input) => {
      const num = Number(input);
      if (!Number.isInteger(num)) throw new Error(`"${input}" is not an integer`);
      return num;
    };
    let user = null;
    if (target.startsWith("user:")) {
      [user, target] = import_lib.Utils.splitFirst(target.slice(5), ",");
      target = target.trim();
    }
    battle2.add("html", import_lib.Utils.html`<div class="message-warning">${user ? `[${user}] ` : ""}<strong>/editbattle</strong> ${target}</div>`);
    let cmd;
    [cmd, target] = import_lib.Utils.splitFirst(target, " ");
    if (cmd.endsWith(",")) cmd = cmd.slice(0, -1);
    const targets = target.split(",");
    if (targets.length === 1 && targets[0] === "") targets.pop();
    switch (cmd) {
      case "hp":
      case "h": {
        if (targets.length !== 3) {
          battle2.add("||<<< Error: Format should be: hp PLAYER, POKEMON, HP");
          return;
        }
        const [player2, pokemon2, hp] = targets;
        const p = getPokemon(toID2(player2), toID2(pokemon2));
        p.sethp(requireInt(hp));
        if (p.isActive) battle2.add("-damage", p, p.getHealth);
        break;
      }
      case "status":
      case "s": {
        if (targets.length !== 3) {
          battle2.add("||<<< Error: Format should be: status PLAYER, POKEMON, STATUS");
          return;
        }
        const [player2, pokemon2, status] = targets.map(toID2);
        const pl = getPlayer(player2);
        const p = getPokemon(player2, pokemon2);
        p.setStatus(toID2(status));
        if (!p.isActive) {
          battle2.add("", "please ignore the above");
          battle2.add("-status", pl.active[0], pl.active[0].status, "[silent]");
        }
        break;
      }
      case "pp": {
        if (targets.length !== 4) {
          battle2.add("||<<< Error: Format should be: pp PLAYER, POKEMON, MOVE, PP");
          return;
        }
        const [player2, pokemon2, move, pp] = targets;
        const p = getPokemon(player2, pokemon2);
        const moveData = p.getMoveData(toID2(move)) || p.moveSlots[parseInt(move) - 1];
        if (!moveData) {
          battle2.add(`||<<< Error: Move "${move}" not found for Pokemon "${player2} ${pokemon2}"`);
          return;
        }
        moveData.pp = requireInt(pp);
        break;
      }
      case "boost":
      case "b": {
        if (targets.length !== 4) {
          battle2.add("||<<< Error: Format should be: boost PLAYER, POKEMON, STAT, VALUE");
          return;
        }
        const [player2, pokemon2, stat, boostLevel] = targets;
        const p = getPokemon(player2, pokemon2);
        const statID = toID2(stat);
        if (!["atk", "def", "spa", "spd", "spe", "accuracy", "evasion"].includes(statID)) {
          battle2.add(`||<<< Error: Invalid boost "${stat}:${boostLevel}"`);
          return;
        }
        battle2.boost({ [statID]: requireInt(boostLevel) }, p);
        break;
      }
      case "volatile":
      case "v": {
        if (targets.length !== 3) {
          battle2.add("||<<< Error: Format should be: volatile PLAYER, POKEMON, VOLATILE");
          return;
        }
        const [player2, pokemon2, volatile] = targets;
        const p = getPokemon(player2, pokemon2);
        p.addVolatile(toID2(volatile));
        break;
      }
      case "sidecondition":
      case "sc": {
        if (targets.length !== 2) {
          battle2.add("||<<< Error: Format should be: sidecondition PLAYER, SIDECONDITION");
          return;
        }
        const [player2, sideCondition] = targets;
        const side2 = getPlayer(player2);
        side2.addSideCondition(toID2(sideCondition), "debug");
        break;
      }
      case "fieldcondition":
      case "pseudoweather":
      case "fc": {
        if (targets.length !== 1) {
          battle2.add("||<<< Error: Format should be: fieldcondition FIELD, PSEUDOWEATHER");
          return;
        }
        const [pseudoWeather] = targets;
        battle2.field.addPseudoWeather(toID2(pseudoWeather), "debug");
        break;
      }
      case "weather":
      case "w": {
        if (targets.length !== 1) {
          battle2.add("||<<< Error: Format should be: weather FIELD, WEATHER");
          return;
        }
        const [weather] = targets;
        battle2.field.setWeather(toID2(weather), "debug");
        break;
      }
      case "terrain":
      case "t": {
        if (targets.length !== 1) {
          battle2.add("||<<< Error: Format should be: terrain FIELD, TERRAIN");
          return;
        }
        const [terrain] = targets;
        battle2.field.setTerrain(toID2(terrain), "debug");
        break;
      }
      case "reseed": {
        battle2.resetRNG(target);
        if (targets.length) battle2.add(`||Reseeded to ${targets.join(",")}`);
        break;
      }
      default:
        throw new Error(`Unknown editbattle command: ${cmd}`);
    }
  }
  _writeEnd() {
    if (!this.atEOF) this.pushEnd();
    this._destroy();
  }
  _destroy() {
    if (this.battle) this.battle.destroy();
  }
}
function getPlayerStreams(stream) {
  const streams = {
    omniscient: new import_lib.Streams.ObjectReadWriteStream({
      write(data) {
        void stream.write(data);
      },
      writeEnd() {
        return stream.writeEnd();
      }
    }),
    spectator: new import_lib.Streams.ObjectReadStream({
      read() {
      }
    }),
    p1: new import_lib.Streams.ObjectReadWriteStream({
      write(data) {
        void stream.write(data.replace(/(^|\n)/g, `$1>p1 `));
      }
    }),
    p2: new import_lib.Streams.ObjectReadWriteStream({
      write(data) {
        void stream.write(data.replace(/(^|\n)/g, `$1>p2 `));
      }
    }),
    p3: new import_lib.Streams.ObjectReadWriteStream({
      write(data) {
        void stream.write(data.replace(/(^|\n)/g, `$1>p3 `));
      }
    }),
    p4: new import_lib.Streams.ObjectReadWriteStream({
      write(data) {
        void stream.write(data.replace(/(^|\n)/g, `$1>p4 `));
      }
    })
  };
  (async () => {
    for await (const chunk of stream) {
      const [type2, data] = import_lib.Utils.splitFirst(chunk, `
`);
      switch (type2) {
        case "update":
          const channelMessages = (0, import_battle.extractChannelMessages)(data, [-1, 0, 1, 2, 3, 4]);
          streams.omniscient.push(channelMessages[-1].join("\n"));
          streams.spectator.push(channelMessages[0].join("\n"));
          streams.p1.push(channelMessages[1].join("\n"));
          streams.p2.push(channelMessages[2].join("\n"));
          streams.p3.push(channelMessages[3].join("\n"));
          streams.p4.push(channelMessages[4].join("\n"));
          break;
        case "sideupdate":
          const [side2, sideData] = import_lib.Utils.splitFirst(data, `
`);
          streams[side2].push(sideData);
          break;
        case "end":
          break;
      }
    }
    for (const s of Object.values(streams)) {
      s.pushEnd();
    }
  })().catch((err) => {
    for (const s of Object.values(streams)) {
      s.pushError(err, true);
    }
  });
  return streams;
}
class BattlePlayer {
  constructor(playerStream, debug = false) {
    this.stream = playerStream;
    this.log = [];
    this.debug = debug;
  }
  async start() {
    for await (const chunk of this.stream) {
      this.receive(chunk);
    }
  }
  receive(chunk) {
    for (const line of chunk.split("\n")) {
      this.receiveLine(line);
    }
  }
  receiveLine(line) {
    if (this.debug) console.log(line);
    if (!line.startsWith("|")) return;
    const [cmd, rest] = import_lib.Utils.splitFirst(line.slice(1), "|");
    if (cmd === "request") return this.receiveRequest(JSON.parse(rest));
    if (cmd === "error") return this.receiveError(new Error(rest));
    this.log.push(line);
  }
  receiveError(error) {
    throw error;
  }
  choose(choice) {
    void this.stream.write(choice);
  }
}
class BattleTextStream extends import_lib.Streams.ReadWriteStream {
  constructor(options2) {
    super();
    this.battleStream = new BattleStream(options2);
    this.currentMessage = "";
    void this._listen();
  }
  async _listen() {
    for await (let message2 of this.battleStream) {
      if (!message2.endsWith("\n")) message2 += "\n";
      this.push(message2 + "\n");
    }
    this.pushEnd();
  }
  _write(message2) {
    this.currentMessage += `${message2}`;
    const index = this.currentMessage.lastIndexOf("\n");
    if (index >= 0) {
      void this.battleStream.write(this.currentMessage.slice(0, index));
      this.currentMessage = this.currentMessage.slice(index + 1);
    }
  }
  _writeEnd() {
    return this.battleStream.writeEnd();
  }
}
//# sourceMappingURL=battle-stream.js.map
