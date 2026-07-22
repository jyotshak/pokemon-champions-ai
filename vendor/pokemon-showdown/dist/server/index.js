"use strict";
var __create = Object.create;
var __defProp = Object.defineProperty;
var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
var __getOwnPropNames = Object.getOwnPropertyNames;
var __getProtoOf = Object.getPrototypeOf;
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
var __toESM = (mod, isNodeMode, target) => (target = mod != null ? __create(__getProtoOf(mod)) : {}, __copyProps(
  // If the importer is in node compatibility mode or this is not an ESM
  // file that has been converted to a CommonJS file using a Babel-
  // compatible transform (i.e. "__esModule" has not been set), then set
  // "default" to the CommonJS "module.exports" for node compatibility.
  isNodeMode || !mod || !mod.__esModule ? __defProp(target, "default", { value: mod, enumerable: true }) : target,
  mod
));
var __toCommonJS = (mod) => __copyProps(__defProp({}, "__esModule", { value: true }), mod);
var server_exports = {};
__export(server_exports, {
  readyPromise: () => readyPromise
});
module.exports = __toCommonJS(server_exports);
var import_lib = require("../lib");
var ConfigLoader = __toESM(require("./config-loader"));
var import_sockets = require("./sockets");
/**
 * Main file
 * Pokemon Showdown - http://pokemonshowdown.com/
 *
 * This is the main Pokemon Showdown app, and the file that the
 * `pokemon-showdown` script runs if you start Pokemon Showdown normally.
 *
 * This file sets up our SockJS server, which handles communication
 * between users and your server, and also sets up globals. You can
 * see details in their corresponding files, but here's an overview:
 *
 * Users - from users.ts
 *
 *   Most of the communication with users happens in users.ts, we just
 *   forward messages between the sockets.js and users.ts.
 *
 *   It exports the global tables `Users.users` and `Users.connections`.
 *
 * Rooms - from rooms.ts
 *
 *   Every chat room and battle is a room, and what they do is done in
 *   rooms.ts. There's also a global room which every user is in, and
 *   handles miscellaneous things like welcoming the user.
 *
 *   It exports the global table `Rooms.rooms`.
 *
 * Dex - from sim/dex.ts
 *
 *   Handles getting data about Pokemon, items, etc.
 *
 * Ladders - from ladders.ts and ladders-remote.ts
 *
 *   Handles Elo rating tracking for players.
 *
 * Chat - from chat.ts
 *
 *   Handles chat and parses chat commands like /me and /ban
 *
 * Sockets - from sockets.js
 *
 *   Used to abstract out network connections. sockets.js handles
 *   the actual server and connection set-up.
 *
 * @license MIT
 */
try {
  require("source-map-support").install();
} catch (e) {
}
try {
  fetch;
} catch (e) {
  throw new Error("We require Node.js version 22 or later; you're using " + process.version);
}
try {
  require.resolve("ts-chacha20");
} catch (e) {
  throw new Error("Dependencies are unmet; run `npm ci` before launching Pokemon Showdown again.");
}
function cleanupStale() {
  return import_lib.Repl.cleanup();
}
function setupGlobals() {
  const { Monitor: Monitor2 } = require("./monitor");
  global.Monitor = Monitor2;
  global.__version = { head: "" };
  void Monitor2.version().then((hash) => {
    global.__version.tree = hash;
  });
  const { Dex } = require("../sim/dex");
  global.Dex = Dex;
  global.toID = Dex.toID;
  const { Chat: Chat2 } = require("./chat");
  global.Chat = Chat2;
  const { Rooms: Rooms2 } = require("./rooms");
  global.Rooms = Rooms2;
  Rooms2.global = new Rooms2.GlobalRoomState();
  const { Teams } = require("../sim/teams");
  global.Teams = Teams;
  const { LoginServer } = require("./loginserver");
  global.LoginServer = LoginServer;
  const { Ladders } = require("./ladders");
  global.Ladders = Ladders;
  const { Users } = require("./users");
  global.Users = Users;
  const { Punishments } = require("./punishments");
  global.Punishments = Punishments;
  const Verifier2 = require("./verifier");
  global.Verifier = Verifier2;
  const { Tournaments } = require("./tournaments");
  global.Tournaments = Tournaments;
  const { IPTools } = require("./ip-tools");
  global.IPTools = IPTools;
  void IPTools.loadHostsAndRanges();
  const TeamValidatorAsync2 = require("./team-validator-async");
  global.TeamValidatorAsync = TeamValidatorAsync2;
  global.Sockets = import_sockets.Sockets;
  if (!Config.lazysockets) {
    import_sockets.Sockets.start(Config.subprocessescache);
  }
}
const readyPromise = cleanupStale().then(() => {
  setupGlobals();
}).then(() => {
  if (Config.usesqlite) {
    require("./modlog").start(Config.subprocessescache);
  }
  Rooms.global.start(Config.subprocessescache);
  Verifier.start(Config.subprocessescache);
  TeamValidatorAsync.start(Config.subprocessescache);
  Chat.start(Config.subprocessescache);
  if (Config.watchconfig) {
    ConfigLoader.watch();
  }
  ConfigLoader.flushLog();
  if (Config.crashguard) {
    process.on("uncaughtException", (err) => {
      Monitor.crashlog(err, "The main process");
    });
    process.on("unhandledRejection", (err) => {
      Monitor.crashlog(err, "A main process Promise");
    });
  }
  import_lib.Repl.startGlobal("app");
  if (Config.startuphook) {
    process.nextTick(Config.startuphook);
  }
  if (Config.ofemain) {
    global.nodeOomHeapdump = require("node-oom-heapdump")({
      addTimestamp: true
    });
  }
});
//# sourceMappingURL=index.js.map
