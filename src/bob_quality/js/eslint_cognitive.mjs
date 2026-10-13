import { createRequire } from "node:module";
import { readFileSync } from "node:fs";

const require = createRequire(import.meta.url);
const MESSAGE =
  /^Refactor this function to reduce its Cognitive Complexity from (\d+) to the (\d+) allowed\.$/;
const EXTENSIONS = "{ts,tsx,js,jsx,mjs,cjs}";
const parsed = new Map();

// sonarjs nests typescript-estree under utils, so a hoisted copy is the wrong parser.
function loadEstree() {
  const sonarRequire = createRequire(require.resolve("eslint-plugin-sonarjs/package.json"));
  const utilsEntry = sonarRequire.resolve("@typescript-eslint/utils/package.json");
  const estree = createRequire(utilsEntry)("@typescript-eslint/typescript-estree");
  if (estree.version !== "7.16.1") {
    throw new Error(`typescript-estree ${estree.version}`);
  }
  return estree;
}

const { parse } = loadEstree();
const { ESLint } = require("eslint");
const sonarjs = require("eslint-plugin-sonarjs");

function parseSource(code, filePath) {
  const hit = parsed.get(code);
  if (hit) return hit;
  const ast = parse(code, {
    loc: true,
    range: true,
    tokens: true,
    comment: true,
    jsx: true,
    filePath: filePath || "<input>",
  });
  attachParents(ast);
  parsed.set(code, ast);
  return ast;
}

function parseForESLint(code, options) {
  return { ast: parseSource(code, options.filePath ?? "") };
}

function attachParents(ast) {
  const stack = [ast];
  while (stack.length) {
    const node = stack.pop();
    for (const key of Object.keys(node)) {
      if (key === "parent") continue;
      const child = node[key];
      if (Array.isArray(child)) {
        for (const item of child) pushChild(stack, node, item);
        continue;
      }
      pushChild(stack, node, child);
    }
  }
}

function pushChild(stack, parent, child) {
  if (!child || typeof child.type !== "string") return;
  child.parent = parent;
  stack.push(child);
}

function parseEslintResults(results, sourceFor, limit) {
  const rows = [];
  for (const result of results) {
    if (isFatal(result)) continue;
    const source = sourceFor(result.filePath);
    const ast = parseSource(source, result.filePath);
    for (const message of result.messages) {
      const row = rowFor(ast, source, result.filePath, message, limit);
      if (row) rows.push(row);
    }
  }
  return rows;
}

function rowFor(ast, source, file, message, limit) {
  if (message.ruleId !== "sonarjs/cognitive-complexity") return null;
  if (message.messageId !== "refactorFunction") return null;
  const match = MESSAGE.exec(message.message);
  if (!match) throw new Error("unreadable cognitive message");
  const score = Number(match[1]);
  const threshold = Number(match[2]);
  if (threshold !== limit - 1) throw new Error("unexpected cognitive threshold");
  if (score < limit) return null;
  const functions = functionsAt(ast, source, message);
  if (functions.length !== 1) {
    throw new Error(`cognitive message matched ${functions.length} functions`);
  }
  const fn = functions[0];
  const span = spanNode(fn);
  return {
    file,
    name: displayName(fn),
    start_line: span.loc.start.line,
    end_line: inclusiveEnd(span.loc),
    score,
  };
}

function isFatal(result) {
  if (result.fatalErrorCount > 0) return true;
  return result.messages.some((message) => message.fatal);
}

function functionsAt(ast, source, message) {
  const found = [];
  walk(ast, (node) => {
    if (!isFunction(node)) return;
    const token = mainTokenLoc(node, source);
    const key = reportedKey(node);
    if ((token && sameLoc(token, message)) || (key && sameLoc(key, message))) {
      if (!found.includes(node)) found.push(node);
    }
  });
  return found;
}

function walk(node, visit) {
  if (!node || typeof node.type !== "string") return;
  visit(node);
  for (const key of Object.keys(node)) {
    if (key === "parent") continue;
    const child = node[key];
    if (Array.isArray(child)) {
      for (const item of child) walk(item, visit);
      continue;
    }
    walk(child, visit);
  }
}

function isFunction(node) {
  return (
    node.type === "FunctionDeclaration" ||
    node.type === "FunctionExpression" ||
    node.type === "ArrowFunctionExpression"
  );
}

function mainTokenLoc(fn, source) {
  if (fn.type === "FunctionDeclaration") {
    if (fn.id && fn.id.loc) return fn.id.loc;
    return keywordLoc(source, fn, "function");
  }
  if (fn.type === "FunctionExpression") {
    const parent = fn.parent;
    if (
      parent &&
      (parent.type === "MethodDefinition" || parent.type === "Property") &&
      parent.key &&
      parent.key.loc
    ) {
      return parent.key.loc;
    }
    return keywordLoc(source, fn, "function");
  }
  if (fn.type === "ArrowFunctionExpression") return arrowLoc(source, fn);
  return null;
}

function reportedKey(fn) {
  const parent = fn.parent;
  if (!parent || parent.value !== fn || !parent.key || !parent.key.loc) return null;
  if (
    parent.type !== "MethodDefinition" &&
    parent.type !== "Property" &&
    parent.type !== "PropertyDefinition"
  ) {
    return null;
  }
  return parent.key.loc;
}

function sameLoc(loc, message) {
  return (
    loc.start.line === message.line &&
    loc.start.column + 1 === message.column &&
    loc.end.line === message.endLine &&
    loc.end.column + 1 === message.endColumn
  );
}

function keywordLoc(source, fn, word) {
  if (!fn.range) return null;
  const at = source.slice(fn.range[0], fn.range[1]).indexOf(word);
  if (at < 0) return null;
  return locAt(source, fn.range[0] + at, word.length);
}

function arrowLoc(source, fn) {
  if (!fn.range || !fn.body || !fn.body.range) return null;
  const slice = source.slice(fn.range[0], fn.body.range[0]);
  const at = slice.lastIndexOf("=>");
  if (at < 0) return null;
  return locAt(source, fn.range[0] + at, 2);
}

function locAt(source, index, length) {
  return { start: position(source, index), end: position(source, index + length) };
}

function position(source, index) {
  let line = 1;
  let column = 0;
  for (let cursor = 0; cursor < index; cursor += 1) {
    if (source[cursor] === "\n") {
      line += 1;
      column = 0;
      continue;
    }
    column += 1;
  }
  return { line, column };
}

function spanNode(fn) {
  const parent = fn.parent;
  if (parent && parent.type === "MethodDefinition" && parent.value === fn) return parent;
  return fn;
}

function inclusiveEnd(loc) {
  if (loc.end.column === 0 && loc.end.line > loc.start.line) return loc.end.line - 1;
  return loc.end.line;
}

function displayName(fn) {
  const local = localName(fn);
  const outers = enclosingNames(fn);
  if (outers.length === 0) return local;
  return `${outers.join("::")}::${local}`;
}

function enclosingNames(fn) {
  const names = [];
  let current = fn.parent;
  while (current) {
    if (isFunction(current)) {
      const name = localName(current);
      if (!name.startsWith("anonymous@")) names.push(name);
    }
    current = current.parent;
  }
  names.reverse();
  return names;
}

function localName(fn) {
  if (fn.type === "FunctionDeclaration") {
    if (fn.id && fn.id.type === "Identifier" && fn.id.name) return fn.id.name;
    return "default";
  }
  const parent = fn.parent;
  if (parent && (parent.type === "MethodDefinition" || parent.type === "PropertyDefinition")) {
    const key = propertyName(parent);
    const klass = className(parent);
    if (klass && key) return `${klass}::${key}`;
    if (key) return key;
  }
  if (parent && parent.type === "VariableDeclarator") {
    const bound = bindingName(parent.id);
    if (bound) return bound;
  }
  if (parent && parent.type === "Property") {
    const key = propertyName(parent);
    if (key) return key;
  }
  return `anonymous@${fn.loc.start.line}`;
}

function propertyName(node) {
  const key = node.key;
  if (!key) return null;
  if (key.type === "Identifier" && !node.computed) return key.name;
  if (key.type === "PrivateIdentifier") return key.name;
  if (key.type === "Literal" && (typeof key.value === "string" || typeof key.value === "number")) {
    return String(key.value);
  }
  return null;
}

function className(member) {
  const body = member.parent;
  if (!body || body.type !== "ClassBody") return null;
  const klass = body.parent;
  if (!klass) return null;
  if (klass.id && klass.id.type === "Identifier") return klass.id.name;
  if (klass.parent && klass.parent.type === "VariableDeclarator") return bindingName(klass.parent.id);
  return null;
}

function bindingName(id) {
  if (id && id.type === "Identifier") return id.name;
  return null;
}

function sourceFor(filePath) {
  return readFileSync(filePath, "utf8");
}

function patterns(include) {
  const files = [];
  for (const root of include) {
    files.push(`${root}/**/*.${EXTENSIONS}`);
    files.push(`${root}/*.${EXTENSIONS}`);
  }
  return files;
}

async function main() {
  const input = JSON.parse(await readStdin());
  const files = patterns(input.include ?? []);
  if (files.length === 0) {
    process.stdout.write("[]\n");
    return;
  }
  const eslint = new ESLint({
    cwd: input.cwd,
    overrideConfigFile: true,
    ignore: false,
    errorOnUnmatchedPattern: false,
    allowInlineConfig: false,
    overrideConfig: [
      { ignores: (input.exclude ?? []).map((name) => `**/${name}/**`) },
      {
        files,
        linterOptions: { noInlineConfig: true },
        languageOptions: {
          parser: { parseForESLint },
          ecmaVersion: "latest",
          sourceType: "module",
        },
        plugins: { sonarjs },
        rules: {
          "sonarjs/cognitive-complexity": ["error", input.limit - 1],
        },
      },
    ],
  });
  const results = await eslint.lintFiles(files);
  const fatal = results.filter(isFatal);
  if (results.length > 0 && fatal.length === results.length) {
    throw new Error("every file failed to parse");
  }
  const rows = parseEslintResults(
    results.filter((result) => !isFatal(result)),
    sourceFor,
    input.limit,
  );
  process.stdout.write(`${JSON.stringify(rows)}\n`);
}

function readStdin() {
  const chunks = [];
  return new Promise((resolve, reject) => {
    process.stdin.on("data", (chunk) => chunks.push(chunk));
    process.stdin.on("end", () => resolve(Buffer.concat(chunks).toString("utf8")));
    process.stdin.on("error", reject);
  });
}

main().catch((error) => {
  const message = error instanceof Error ? error.message : String(error);
  process.stderr.write(`${message}\n`);
  process.exit(1);
});
