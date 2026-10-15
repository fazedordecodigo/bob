import fs from "node:fs";
import * as nodeModule from "node:module";
import { isMainThread } from "node:worker_threads";

const SPACE = "join(' ')";
const ARROW = "join(' > ')";
const PATCHED = Symbol.for("bob.strykerVitest5Patch");

export function rewriteSetup(source) {
  const text = String(source);
  if (text.includes(ARROW)) {
    return text;
  }
  if (text.includes(SPACE)) {
    return text.replaceAll(SPACE, ARROW);
  }
  throw new Error("vitest-runner collectTestName join is neither a space nor ' > '");
}

function runnerSource(file) {
  const normalized = String(file).replaceAll("\\", "/");
  return (
    normalized.includes("@stryker-mutator/vitest-runner/") &&
    (normalized.endsWith("/test-helpers.js") || normalized.endsWith("/stryker-setup.js"))
  );
}

export function installPatch() {
  if (globalThis[PATCHED]) {
    return;
  }
  globalThis[PATCHED] = true;
  const original = fs.promises.readFile;
  fs.promises.readFile = async function patchedReadFile(file, options) {
    const result = await original.call(fs.promises, file, options);
    if (!runnerSource(file) || typeof result !== "string") {
      return result;
    }
    return rewriteSetup(result);
  };
}

function rewriteLoaded(url, loaded) {
  if (!runnerSource(url) || loaded.source == null) {
    return loaded;
  }
  const source = loaded.source;
  const text = typeof source === "string" ? source : Buffer.from(source).toString("utf8");
  return { ...loaded, source: rewriteSetup(text) };
}

export async function load(url, context, nextLoad) {
  return rewriteLoaded(url, await nextLoad(url, context));
}

function loadSync(url, context, nextLoad) {
  return rewriteLoaded(url, nextLoad(url, context));
}

if (isMainThread) {
  // test-helpers.js is imported and becomes testNamePattern. stryker-setup.js
  // is readFile'd into the sandbox as the coverage id. Vitest 5 matches the
  // two names only when both joins use ' > '.
  installPatch();
  // Node 22.18 loads test-helpers.js on the synchronous loader while Stryker
  // is still importing plugins, so a hook registered from that import never
  // sees the file. --import installs this hook before that import.
  if (typeof nodeModule.registerHooks === "function") {
    nodeModule.registerHooks({ load: loadSync });
  } else {
    await nodeModule.register(import.meta.url, { parentURL: import.meta.url });
  }
}

export const strykerPlugins = [];
