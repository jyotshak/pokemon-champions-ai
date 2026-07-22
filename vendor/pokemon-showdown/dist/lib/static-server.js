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
var static_server_exports = {};
__export(static_server_exports, {
  SERVER_INFO: () => SERVER_INFO,
  StaticServer: () => StaticServer,
  mimeTypes: () => mimeTypes
});
module.exports = __toCommonJS(static_server_exports);
var import_node_fs = __toESM(require("node:fs"));
var import_promises = __toESM(require("node:fs/promises"));
var import_node_http = __toESM(require("node:http"));
var import_node_path = __toESM(require("node:path"));
/**
 * Static server
 *
 * API resembles node-static, but with some differences:
 *
 * - `serve`'s callback needs to return `true` to suppress the default error page
 * - everything is Promises
 * - no customizing cache time by filename
 * - no index.json directory streaming (it was undocumented; you weren't using it)
 *
 * Forked from node-static @
 * https://github.com/cloudhead/node-static/blob/e49fbd728e93294c225f52103962e56aab86cb1a/lib/node-static.js
 *
 * @author Guangcong Luo <guangcongluo@gmail.com>, Alexis Sellier, Brett Zamir
 * @license MIT
 */
const DEBUG = false;
const SERVER_INFO = "node-static-vendored/1.0";
const mimeTypes = {
  ".html": "text/html;charset=utf-8",
  ".htm": "text/html;charset=utf-8",
  ".css": "text/css;charset=utf-8",
  ".js": "application/javascript;charset=utf-8",
  ".jsx": "application/javascript;charset=utf-8",
  ".cjs": "application/javascript;charset=utf-8",
  ".mjs": "application/javascript;charset=utf-8",
  ".json": "application/json;charset=utf-8",
  ".ts": "application/typescript;charset=utf-8",
  ".xml": "application/xml;charset=utf-8",
  ".txt": "text/plain;charset=utf-8",
  ".md": "text/markdown;charset=utf-8",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".gif": "image/gif",
  ".svg": "image/svg+xml;charset=utf-8",
  ".ico": "image/x-icon",
  ".bmp": "image/bmp",
  ".webp": "image/webp",
  ".woff": "font/woff",
  ".woff2": "font/woff2",
  ".ttf": "font/ttf",
  ".eot": "application/vnd.ms-fontobject",
  ".zip": "application/zip",
  ".tar": "application/x-tar",
  ".gz": "application/gzip",
  ".mp3": "audio/mpeg",
  ".wav": "audio/wav",
  ".ogg": "audio/ogg",
  ".mp4": "video/mp4",
  ".webm": "video/webm"
};
class StaticServer {
  constructor(root, options) {
    this.cacheTime = 3600;
    this.defaultHeaders = {};
    /** Contains the `.`, unlike options.defaultExtension */
    this.defaultExtension = "";
    if (root && typeof root === "object") {
      options = root;
      root = null;
    }
    this.root = import_node_path.default.normalize(import_node_path.default.resolve(root || "."));
    this.options = options || {};
    this.options.indexFile ||= "index.html";
    if (this.options.cacheTime !== void 0) {
      this.cacheTime = this.options.cacheTime;
    }
    if (this.options.defaultExtension) {
      this.defaultExtension = `.${this.options.defaultExtension}`;
    }
    if (this.options.serverInfo !== null) {
      this.defaultHeaders["server"] = this.options.serverInfo || SERVER_INFO;
    }
    for (const k in this.options.headers) {
      this.defaultHeaders[k] = this.options.headers[k];
    }
  }
  async serveDir(pathname, req, res) {
    const htmlIndex = import_node_path.default.join(pathname, this.options.indexFile);
    try {
      const stat = await import_promises.default.stat(htmlIndex);
      const status = 200;
      const headers = {};
      const originalPathname = decodeURIComponent(new URL(req.url, "http://localhost").pathname);
      if (originalPathname.length && !originalPathname.endsWith("/")) {
        return this.getResult(301, { "Location": originalPathname + "/" });
      } else {
        return this.respond(status, headers, htmlIndex, stat, req, res);
      }
    } catch {
      return this.getResult(404);
    }
  }
  async serveFile(pathname, status, headers, req, res, errorCallback) {
    pathname = this.resolve(pathname);
    const stat = await import_promises.default.stat(pathname);
    const result = await this.respond(status, headers, pathname, stat, req, res);
    return this.finish(result, req, res, errorCallback);
  }
  getResult(status, headers = {}, alreadySent = false) {
    if (this.defaultHeaders["server"]) {
      headers["server"] ||= this.defaultHeaders["server"];
    }
    return {
      status,
      headers,
      message: import_node_http.default.STATUS_CODES[status],
      alreadySent
    };
  }
  finish(result, req, res, errorCallback) {
    if (!result.alreadySent && !errorCallback?.(result)) {
      res.writeHead(result.status, result.headers);
      if (result.status >= 400 && req.method !== "HEAD") {
        res.write(`${result.status} ${result.message}`);
      }
      res.end();
    }
    return result;
  }
  async servePath(pathname, status, headers, req, res) {
    pathname = this.resolve(pathname);
    if (!pathname.startsWith(this.root)) {
      return this.getResult(403);
    }
    try {
      const stat = await import_promises.default.stat(pathname);
      if (stat.isFile()) {
        return this.respond(status, headers, pathname, stat, req, res);
      } else if (stat.isDirectory()) {
        return this.serveDir(pathname, req, res);
      } else {
        return this.getResult(400);
      }
    } catch {
      if (this.defaultExtension) {
        try {
          const stat = await import_promises.default.stat(pathname + this.defaultExtension);
          if (stat.isFile()) {
            return this.respond(status, headers, pathname + this.defaultExtension, stat, req, res);
          } else {
            return this.getResult(400);
          }
        } catch {
          return this.getResult(404);
        }
      } else {
        return this.getResult(404);
      }
    }
  }
  resolve(pathname) {
    return import_node_path.default.resolve(import_node_path.default.join(this.root, pathname));
  }
  async serve(req, res, errorCallback) {
    let pathname;
    try {
      pathname = decodeURIComponent(new URL(req.url, "http://localhost").pathname);
    } catch {
      return this.finish(this.getResult(400), req, res, errorCallback);
    }
    const result = await this.servePath(pathname, 200, {}, req, res);
    return this.finish(result, req, res, errorCallback);
  }
  /** Check if we should consider sending a gzip version of the file based on the
    * file content type and client's Accept-Encoding header value. */
  gzipOk(req, contentType) {
    const enable = this.options.gzip;
    if (enable === true || enable instanceof RegExp && enable.test(contentType)) {
      return req.headers["accept-encoding"]?.includes("gzip");
    }
    return false;
  }
  /** Send a gzipped version of the file if the options and the client indicate gzip is enabled and
    * we find a .gz file matching the static resource requested. */
  respondGzip(status, contentType, _headers, file, stat, req, res) {
    if (!this.gzipOk(req, contentType)) {
      return this.respondNoGzip(status, contentType, _headers, file, stat, req, res);
    }
    const gzFile = `${file}.gz`;
    return import_promises.default.stat(gzFile).catch(() => null).then((gzStat) => {
      if (gzStat?.isFile()) {
        const vary = _headers["Vary"];
        _headers["Vary"] = (vary && vary !== "Accept-Encoding" ? `${vary}, ` : "") + "Accept-Encoding";
        _headers["Content-Encoding"] = "gzip";
        stat.size = gzStat.size;
        file = gzFile;
      }
      return this.respondNoGzip(status, contentType, _headers, file, stat, req, res);
    });
  }
  parseByteRange(req, stat) {
    const byteRange = {
      from: 0,
      to: 0,
      valid: false
    };
    const rangeHeader = req.headers["range"];
    const flavor = "bytes=";
    if (rangeHeader) {
      if (rangeHeader.startsWith(flavor) && !rangeHeader.includes(",")) {
        const splitRangeHeader = rangeHeader.substr(flavor.length).split("-");
        byteRange.from = parseInt(splitRangeHeader[0]);
        byteRange.to = parseInt(splitRangeHeader[1]);
        if (isNaN(byteRange.from) && !isNaN(byteRange.to)) {
          byteRange.from = stat.size - byteRange.to;
          byteRange.to = stat.size ? stat.size - 1 : 0;
        } else if (!isNaN(byteRange.from) && isNaN(byteRange.to)) {
          byteRange.to = stat.size ? stat.size - 1 : 0;
        }
        if (!isNaN(byteRange.from) && !isNaN(byteRange.to) && 0 <= byteRange.from && byteRange.from <= byteRange.to) {
          byteRange.valid = true;
        } else {
          if (DEBUG) console.warn("Request contains invalid range header: ", splitRangeHeader);
        }
      } else {
        if (DEBUG) console.warn("Request contains unsupported range header: ", rangeHeader);
      }
    }
    return byteRange;
  }
  async respondNoGzip(status, contentType, _headers, file, stat, req, res) {
    const mtime = Date.parse(stat.mtime);
    const headers = {};
    const clientETag = req.headers["if-none-match"];
    const clientMTime = Date.parse(req.headers["if-modified-since"]);
    const byteRange = this.parseByteRange(req, stat);
    let startByte = 0;
    let length = stat.size;
    if (byteRange.valid) {
      if (byteRange.to < length) {
        startByte = byteRange.from;
        length = byteRange.to - byteRange.from + 1;
        status = 206;
        headers["Content-Range"] = `bytes ${byteRange.from}-${byteRange.to}/${stat.size}`;
      } else {
        byteRange.valid = false;
        if (DEBUG) {
          console.warn("Range request exceeds file boundaries, goes until byte no", byteRange.to, "against file size of", length, "bytes");
        }
      }
    }
    if (!byteRange.valid && req.headers["range"]) {
      if (DEBUG) console.error(new Error("Range request present but invalid, might serve whole file instead"));
    }
    for (const k in this.defaultHeaders) headers[k] = this.defaultHeaders[k];
    headers["Etag"] = JSON.stringify([stat.ino, stat.size, mtime].join("-"));
    headers["Date"] = (/* @__PURE__ */ new Date()).toUTCString();
    headers["Last-Modified"] = new Date(stat.mtime).toUTCString();
    headers["Content-Type"] = contentType;
    headers["Content-Length"] = length;
    for (const k in _headers) {
      headers[k] = _headers[k];
    }
    if ((clientMTime || clientETag) && (!clientETag || clientETag === headers["Etag"]) && (!clientMTime || clientMTime >= mtime)) {
      for (const entityHeader of [
        "Content-Encoding",
        "Content-Language",
        "Content-Length",
        "Content-Location",
        "Content-MD5",
        "Content-Range",
        "Content-Type",
        "Expires",
        "Last-Modified"
      ]) {
        delete headers[entityHeader];
      }
      return this.getResult(304, headers);
    } else if (req.method === "HEAD") {
      return this.getResult(status, headers);
    } else {
      res.writeHead(status, headers);
      try {
        await this.stream(file, length, startByte, res);
        return this.getResult(status, headers, true);
      } catch {
        return this.getResult(500, {}, true);
      }
    }
  }
  respond(status, _headers, file, stat, req, res) {
    const contentType = _headers["Content-Type"] || mimeTypes[import_node_path.default.extname(file)] || "application/octet-stream";
    _headers = this.setCacheHeaders(_headers);
    if (this.options.gzip) {
      return this.respondGzip(status, contentType, _headers, file, stat, req, res);
    } else {
      return this.respondNoGzip(status, contentType, _headers, file, stat, req, res);
    }
  }
  stream(file, length, startByte, res) {
    return new Promise((resolve, reject) => {
      let offset = 0;
      import_node_fs.default.createReadStream(file, {
        flags: "r",
        mode: 438,
        start: startByte,
        end: startByte + (length ? length - 1 : 0)
      }).on("data", (chunk) => {
        if (chunk.length && offset < length && offset >= 0) {
          offset += chunk.length;
        }
      }).on("close", () => {
        res.end();
        resolve(offset);
      }).on("error", (err) => {
        reject(err);
        console.error(err);
      }).pipe(res, { end: false });
    });
  }
  setCacheHeaders(_headers) {
    if (typeof this.cacheTime === "number") {
      _headers["cache-control"] = `max-age=${this.cacheTime}`;
    }
    return _headers;
  }
}
//# sourceMappingURL=static-server.js.map
