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
var config_loader_exports = {};
__export(config_loader_exports, {
  cacheGroupData: () => cacheGroupData,
  checkRipgrepAvailability: () => checkRipgrepAvailability,
  ensureLoaded: () => ensureLoaded,
  flushLog: () => flushLog,
  load: () => load,
  watch: () => watch
});
module.exports = __toCommonJS(config_loader_exports);
var defaults = __toESM(require("../config/config-example"));
var import_lib = require("../lib");
/**
 * Config loader
 * Pokemon Showdown - http://pokemonshowdown.com/
 *
 * @license MIT
 */
const FLAG_PRESETS = /* @__PURE__ */ new Map([
  ["--no-security", ["nothrottle", "noguestsecurity", "noipchecks"]]
]);
const processTypes = [
  "localartemis",
  "remoteartemis",
  "battlesearch",
  "datasearch",
  "friends",
  "chatdb",
  "pm",
  "modlog",
  "network",
  "simulator",
  "validator",
  "verifier"
];
const CONFIG_PATH = (0, import_lib.FS)("./config/config.js").path;
const errors = [];
function load(invalidate = false) {
  if (global.Config) {
    if (!invalidate) return global.Config;
    delete require.cache[CONFIG_PATH];
  }
  const config = { ...defaults, ...require(CONFIG_PATH) };
  config.routes = { ...defaults.routes, ...config.routes };
  if (!process.send) {
    if (config.usesqlite) {
      try {
        require.resolve("better-sqlite3");
      } catch {
        throw new Error(`better-sqlite3 is not installed or could not be loaded, but Config.usesqlite is enabled.`);
      }
    }
    if (config.ofemain) {
      try {
        require.resolve("node-oom-heapdump");
      } catch {
        throw new Error(
          `node-oom-heapdump is not installed, but it is a required dependency if Config.ofemain is set to true! Run npm install node-oom-heapdump and restart the server.`
        );
      }
    }
  }
  for (const [preset, values] of FLAG_PRESETS) {
    if (process.argv.includes(preset)) {
      for (const value of values) config[value] = true;
    }
  }
  cacheSubProcesses(config);
  cacheGroupData(config);
  global.Config = config;
  return config;
}
function cacheSubProcesses(config) {
  if (config.subprocesses !== void 0) {
    const value = config.subprocesses || 0;
    if (value === 0 || value === 1) {
      config.subprocessescache = Object.fromEntries(
        processTypes.map((k) => [k, value])
      );
    } else if (typeof value === "object" && !Array.isArray(value)) {
      config.subprocessescache = value;
    } else {
      pushError("error", `Invalid \`subprocesses\` specification. Use any of 0, 1, or a plain old object.`);
    }
  }
  config.subprocessescache ??= {};
  const deprecatedKeys = [];
  if ("workers" in config) {
    deprecatedKeys.push("workers");
    config.subprocessescache.network = config.workers;
  }
  for (const processType of processTypes) {
    if (processType === "network") continue;
    const compatKey = `${processType}processes`;
    if (compatKey in config) {
      deprecatedKeys.push(compatKey);
      config.subprocessescache[processType] = config[compatKey];
    }
  }
  for (const compatKey of deprecatedKeys) {
    pushError(
      "warning",
      `You are using \`${compatKey}\`, which is deprecated
Support for this may be removed.
Please ensure that you update your config.js to use \`subprocesses\` (see config-example.js, line 80).
`
    );
  }
}
function cacheGroupData(config) {
  if (config.groups) {
    pushError(
      "warning",
      `You are using a deprecated version of user group specification in config.
Support for this may be removed.
Please ensure that you update your config.js to the new format (see config-example.js, line 521).
`
    );
  } else {
    config.punishgroups = /* @__PURE__ */ Object.create(null);
    config.groups = /* @__PURE__ */ Object.create(null);
    config.groupsranking = [];
    config.greatergroupscache = /* @__PURE__ */ Object.create(null);
  }
  const groups = config.groups;
  const punishgroups = config.punishgroups;
  const cachedGroups = {};
  function isPermission(key) {
    return !["symbol", "id", "name", "rank", "globalGroupInPersonalRoom"].includes(key);
  }
  function cacheGroup(symbol, groupData) {
    if (cachedGroups[symbol] === "processing") {
      throw new Error(`Cyclic inheritance in group config for symbol "${symbol}"`);
    }
    if (cachedGroups[symbol] === true) return;
    for (const key in groupData) {
      if (isPermission(key)) {
        const jurisdiction = groupData[key];
        if (typeof jurisdiction === "string" && jurisdiction.includes("s")) {
          pushError("warning", `Outdated jurisdiction for permission "${key}" of group "${symbol}": 's' is no longer a supported jurisdiction; we now use 'ipself' and 'altsself'`);
          delete groupData[key];
        }
      }
    }
    if (groupData["inherit"]) {
      cachedGroups[symbol] = "processing";
      const inheritGroup = groups[groupData["inherit"]];
      cacheGroup(groupData["inherit"], inheritGroup);
      for (const key in inheritGroup) {
        if (key in groupData) continue;
        if (!isPermission(key)) continue;
        groupData[key] = inheritGroup[key];
      }
      delete groupData["inherit"];
    }
    cachedGroups[symbol] = true;
  }
  if (config.grouplist) {
    const grouplist = config.grouplist;
    const numGroups = grouplist.length;
    for (let i = 0; i < numGroups; i++) {
      const groupData = grouplist[i];
      if (groupData.punishgroup) {
        punishgroups[groupData.id] = groupData;
        continue;
      }
      groupData.rank = numGroups - i - 1;
      groups[groupData.symbol] = groupData;
      config.groupsranking.unshift(groupData.symbol);
    }
  }
  for (const sym in groups) {
    const groupData = groups[sym];
    cacheGroup(sym, groupData);
  }
  if (!punishgroups.locked) {
    punishgroups.locked = {
      name: "Locked",
      id: "locked",
      symbol: "\u203D"
    };
  }
  if (!punishgroups.muted) {
    punishgroups.muted = {
      name: "Muted",
      id: "muted",
      symbol: "!"
    };
  }
}
function checkRipgrepAvailability() {
  if (Config.ripgrepmodlog === void 0) {
    const cwd = import_lib.FS.ROOT_PATH;
    Config.ripgrepmodlog = (async () => {
      try {
        await import_lib.ProcessManager.exec(["rg", "--version"], { cwd });
        await import_lib.ProcessManager.exec(["tac", "--version"], { cwd });
        return true;
      } catch {
        return false;
      }
    })();
  }
  return Config.ripgrepmodlog;
}
function pushError(logLevel, msg) {
  if (process.send) return;
  errors.push([logLevel, `[CONFIG] ${msg}`]);
}
function flushLog() {
  for (const entry of errors) {
    Monitor.logWithLevel(entry[0], entry[1]);
  }
  errors.length = 0;
}
function ensureLoaded() {
}
function watch() {
  (0, import_lib.FS)("config/config.js").onModify(() => {
    if (!Config.watchconfig) return;
    try {
      load(true);
      flushLog();
      Chat.plugins["username-prefixes"]?.prefixManager.refreshConfig(true);
      Monitor.notice("Reloaded ../config/config.js");
    } catch (e) {
      Monitor.adminlog("Error reloading ../config/config.js: " + e.stack);
    }
  });
}
load();
//# sourceMappingURL=config-loader.js.map
