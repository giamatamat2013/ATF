// ATF extension: run / build / check commands, compiler diagnostics, outline.
// Plain JavaScript, no build step.
const vscode = require("vscode");
const cp = require("child_process");
const fs = require("fs");
const path = require("path");

let diagnostics;
let output;
const timers = new Map();

function cfg() {
  return vscode.workspace.getConfiguration("atf");
}

function workspaceRoot(doc) {
  const f = doc && vscode.workspace.getWorkspaceFolder(doc.uri);
  return f ? f.uri.fsPath : doc ? path.dirname(doc.uri.fsPath) : undefined;
}

// compiler executable: the "atf.path" setting, else the repository launcher, else `atf` on PATH
function compilerPath(doc) {
  const set = cfg().get("path");
  if (set) return set;
  const root = workspaceRoot(doc);
  if (root) {
    for (const rel of ["bin/atf.exe", "atf.cmd"]) {
      const p = path.join(root, rel);
      if (fs.existsSync(p)) return p;
    }
  }
  return "atf";
}

function quote(s) {
  return /[\s"]/.test(s) ? '"' + s.replace(/"/g, '\\"') + '"' : s;
}

// parse `error: msg` followed by `  --> file:line:col`
function parseOutput(text, cwd, defaultFile) {
  const result = new Map();
  const lines = text.split(/\r?\n/);
  for (let i = 0; i < lines.length; i++) {
    const m = /^(error|warning): (.*)$/.exec(lines[i]);
    if (!m) continue;
    let message = m[2];
    let file = defaultFile, line = 1, col = 1;
    for (let j = i + 1; j < lines.length && j <= i + 2; j++) {
      const loc = /^\s+--> (.*):(\d+):(\d+)\s*$/.exec(lines[j]);
      if (loc) {
        file = path.resolve(cwd, loc[1]);
        line = +loc[2];
        col = +loc[3];
        break;
      }
    }
    for (let j = i + 1; j < lines.length && j <= i + 5; j++) {
      const h = /^\s+hint: (.*)$/.exec(lines[j]);
      if (h) { message += " (hint: " + h[1] + ")"; break; }
    }
    if (/^<std>/.test(file)) file = defaultFile;
    const pos = new vscode.Position(Math.max(line - 1, 0), Math.max(col - 1, 0));
    const d = new vscode.Diagnostic(
      new vscode.Range(pos, pos.translate(0, 1)),
      message,
      m[1] === "warning" ? vscode.DiagnosticSeverity.Warning : vscode.DiagnosticSeverity.Error
    );
    d.source = "atf";
    if (!result.has(file)) result.set(file, []);
    result.get(file).push(d);
  }
  return result;
}

function check(doc) {
  if (doc.languageId !== "atf" || doc.uri.scheme !== "file") return;
  const cwd = workspaceRoot(doc);
  const file = doc.uri.fsPath;
  cp.execFile(compilerPath(doc), ["check", file], { cwd, shell: process.platform === "win32", timeout: 30000 },
    (err, stdout, stderr) => {
      if (err && err.code === "ENOENT") {
        output.appendLine("ATF compiler not found. Set the \"atf.path\" setting.");
        return;
      }
      const found = parseOutput(stderr + "\n" + stdout, cwd, file);
      // a library file (no fn main) is checked like a program, so its "no main" error is expected
      if (!/^\s*fn\s+main\s*\(/m.test(doc.getText())) {
        for (const [f, list] of found) found.set(f, list.filter((d) => !/^no 'main' function/.test(d.message)));
      }
      // the compiler checks the whole program, so only this file's diagnostics are replaced
      diagnostics.delete(doc.uri);
      for (const [f, list] of found) diagnostics.set(vscode.Uri.file(f), list);
    });
}

function activeAtf() {
  const ed = vscode.window.activeTextEditor;
  if (!ed || ed.document.languageId !== "atf") {
    vscode.window.showWarningMessage("Open an .atf file first.");
    return undefined;
  }
  return ed.document;
}

async function runInTerminal(verb, extra) {
  const doc = activeAtf();
  if (!doc) return;
  if (doc.isDirty) await doc.save();
  const term = vscode.window.createTerminal({ name: "ATF", cwd: workspaceRoot(doc) });
  term.show();
  term.sendText([quote(compilerPath(doc)), verb, quote(doc.uri.fsPath)].concat(extra || []).join(" "));
}

// ---- outline ------------------------------------------------------------------
const DECLS = [
  [/^\s*(?:pub\s+)?fn\s+([A-Za-z_]\w*)/, vscode.SymbolKind.Function],
  [/^\s*(?:pub\s+)?struct\s+([A-Za-z_]\w*)/, vscode.SymbolKind.Struct],
  [/^\s*(?:pub\s+)?enum\s+([A-Za-z_]\w*)/, vscode.SymbolKind.Enum],
  [/^\s*impl\s*(?:<[^>]*>)?\s*([A-Za-z_]\w*)/, vscode.SymbolKind.Class],
  [/^\s*(?:pub\s+)?type\s+([A-Za-z_]\w*)/, vscode.SymbolKind.TypeParameter],
  [/^\s*(?:pub\s+)?const\s+([A-Za-z_]\w*)/, vscode.SymbolKind.Constant],
];

const symbolProvider = {
  provideDocumentSymbols(doc) {
    const out = [];
    for (let i = 0; i < doc.lineCount; i++) {
      const text = doc.lineAt(i).text;
      for (const [re, kind] of DECLS) {
        const m = re.exec(text);
        if (!m) continue;
        const start = text.indexOf(m[1], m.index);
        const range = new vscode.Range(i, 0, i, text.length);
        const sel = new vscode.Range(i, start, i, start + m[1].length);
        out.push(new vscode.DocumentSymbol(m[1], "", kind, range, sel));
        break;
      }
    }
    return out;
  },
};

// ---- auto import --------------------------------------------------------------
// Fallback used when the stdlib sources cannot be found: name prefix -> module.
const PREFIX_MODULES = [
  [/^b64_/, "base64"], [/^hex_/, "hex"], [/^hash_/, "hash"], [/^csv_/, "csv"],
  [/^dt_/, "datetime"], [/^json_/, "json"],
  [/^path_/, "path"], [/^fs_/, "fs"], [/^proc_/, "process"], [/^toml_/, "toml"], [/^yaml_/, "yaml"], [/^bigint(_|$)/, "bigint"], [/^crypto_/, "crypto"],
  [/^(args_parser|ArgParser|ArgSpec|ParsedArgs)$/, "args"], [/^(log_\w+|LOG_\w+)$/, "log"],
  [/^algo_/, "algo"], [/^bits_/, "bits"], [/^random_/, "random"], [/^text_/, "text"], [/^(math_|stats_)/, "math"],
  [/^(regex|regex_\w+|Regex|RxMatch)$/, "regex"], [/^(http_\w+|Http\w+)$/, "http"],
  [/^(html_\w+|css_\w+|HtmlNode|h)$/, "html"], [/^(xml_\w+|XmlNode)$/, "xml"], [/^(url_\w+|Url)$/, "url"], [/^(ini_\w+|IniDoc)$/, "ini"], [/^glob_/, "glob"],
  [/^(http_listen|http_reply|http_text|http_html|http_json_reply|http_redirect|http_not_found|http_status_text|http_mime|http_file|http_static|http_read_request|http_write_reply|router_new|route_match|HttpRequest|HttpReply|HttpServer|Router|Route)$/, "httpd"], [/^(tcp_\w+|net_resolve|TcpConn|TcpServer)$/, "net"],
  [/^(test|test_report|expect|expect_eq|expect_ne|expect_near|expect_panics|test_fail|test_property|any_int|any_bool|any_float|any_str|any_int_list|any_of)$/, "test"],
  [/^(ai_\w+|AiChat|AiMessage)$/, "ai"], [/^markdown_\w+$/, "markdown"], [/^(semver_\w+|SemVer)$/, "semver"],
  [/^(term_\w+|red|green|yellow|blue|magenta|cyan|gray|bold|dim|italic|underline|color|color_rgb|background|strip_colors|visible_len|progress_bar|print_same_line|boxed)$/, "term"],
  [/^(Stack|Deque|PriorityQueue|LinkedList|SortedMap|SortedSet|Counter|stack_new|deque_new|deque_from|pq_\w+|linked_list_\w+|sorted_map_\w+|sorted_set_\w+|counter_\w+)$/, "collections"],
  [/^(ui_\w+|animate\w*|anim_\w+|ease_\w+|lerp|Node|Style|Align|Justify|Cursor|Canvas|style|column|row|stack|grid|scroll|button|textbox|textarea|checkbox|toggle|slider|progress|select|tabs|menu|menu_item|menu_button|menu_bar|dropdown|modal|dialog|icon|canvas|clipboard_get|clipboard_set|message_box|confirm_box|open_file_dialog|save_file_dialog|focus_field|rgb|rgba|hex)$/, "ui"],
  [/^(app_dir|app_path|Settings|settings_open|settings_file|recent_add|recent_list)$/, "app"],
];

let symbolCache; // { dir, mtime, map: Map<name, module> }

function stdlibDir(doc) {
  const root = workspaceRoot(doc);
  const cands = [];
  const set = cfg().get("path");
  if (set) cands.push(path.join(path.dirname(set), "..", "stdlib"));
  if (root) cands.push(path.join(root, "stdlib"));
  return cands.find((d) => fs.existsSync(d));
}

// top-level declarations of every std module -> Map(name -> module)
function stdSymbols(doc) {
  const dir = stdlibDir(doc);
  if (!dir) return undefined;
  if (symbolCache && symbolCache.dir === dir && Date.now() - symbolCache.at < 30000) return symbolCache.map;
  const map = new Map();
  let files = [];
  try { files = fs.readdirSync(dir).filter((f) => f.endsWith(".atf")); } catch (e) { return undefined; }
  for (const f of files) {
    const mod = f.slice(0, -4);
    let text;
    try { text = fs.readFileSync(path.join(dir, f), "utf8"); } catch (e) { continue; }
    for (const m of text.matchAll(/^(?:pub\s+)?(?:fn|struct|enum|const|type)\s+([A-Za-z_]\w*)/gm)) {
      if (!map.has(m[1])) map.set(m[1], mod);
    }
  }
  symbolCache = { dir, at: Date.now(), map };
  return map;
}

function moduleFor(name, symbols) {
  if (symbols) return symbols.get(name);
  for (const [re, mod] of PREFIX_MODULES) if (re.test(name)) return mod;
  return undefined;
}

// blank out comments and string contents so words inside them do not count
function stripNoise(text) {
  return text
    .replace(/"""[\s\S]*?"""/g, (s) => s.replace(/[^\n]/g, " "))
    .replace(/\/\/[^\n]*/g, "")
    .replace(/"(?:\\.|[^"\\\n])*"/g, '""');
}

function autoImport(doc) {
  if (doc.languageId !== "atf" || !cfg().get("autoImport")) return;
  const ed = vscode.window.visibleTextEditors.find((e) => e.document === doc);
  if (!ed) return;
  const symbols = stdSymbols(doc);
  const text = doc.getText();
  const clean = stripNoise(text);

  const imported = new Set();
  for (const m of text.matchAll(/^\s*import\s+"std\/(\w+)"/gm)) imported.add(m[1]);

  const declared = new Set();
  for (const m of clean.matchAll(/\b(?:fn|struct|enum|const|type|let|var)\s+([A-Za-z_]\w*)/g)) declared.add(m[1]);
  for (const m of clean.matchAll(/[(,|]\s*([A-Za-z_]\w*)\s*:/g)) declared.add(m[1]); // parameters

  // the std modules themselves share one namespace and never import each other implicitly
  const dir = stdlibDir(doc);
  if (dir && path.resolve(path.dirname(doc.uri.fsPath)) === path.resolve(dir)) return;

  const needed = new Set();
  // lower-case names count only when called (text(...), row(...)): plain words like `text` or `color`
  // are too often local names; capitalized names (types, enums, constants) count anywhere
  for (const m of clean.matchAll(/(?<![.\w])([A-Za-z_]\w*)\b(\s*(?:\(|::<))?/g)) {
    const name = m[1];
    if (declared.has(name)) continue;
    if (!m[2] && !/^[A-Z]/.test(name)) continue;
    const mod = moduleFor(name, symbols);
    if (mod && !imported.has(mod)) needed.add(mod);
  }
  if (!needed.size) return;

  // insert after the leading comments / blank lines / existing imports
  let line = 0, lastImport = -1;
  for (let i = 0; i < doc.lineCount; i++) {
    const t = doc.lineAt(i).text.trim();
    if (/^import\s/.test(t)) lastImport = i;
    else if (t !== "" && !t.startsWith("//") && !t.startsWith("#!")) break;
  }
  if (lastImport >= 0) line = lastImport + 1;
  else {
    while (line < doc.lineCount && /^(\/\/|#!)/.test(doc.lineAt(line).text.trim())) line++;
  }
  const block = [...needed].sort().map((m) => `import "std/${m}"\n`).join("");
  const extra = lastImport < 0 && line < doc.lineCount && doc.lineAt(line).text.trim() !== "" ? "\n" : "";
  const edit = new vscode.WorkspaceEdit();
  edit.insert(doc.uri, new vscode.Position(line, 0), block + extra);
  vscode.workspace.applyEdit(edit);
}

function scheduleAutoImport(doc) {
  if (doc.languageId !== "atf") return;
  const key = "import:" + doc.uri.toString();
  clearTimeout(timers.get(key));
  timers.set(key, setTimeout(() => { timers.delete(key); autoImport(doc); }, 700));
}

function activate(context) {
  diagnostics = vscode.languages.createDiagnosticCollection("atf");
  output = vscode.window.createOutputChannel("ATF");
  context.subscriptions.push(diagnostics, output);

  context.subscriptions.push(
    vscode.commands.registerCommand("atf.run", () => runInTerminal("run")),
    vscode.commands.registerCommand("atf.build", () => runInTerminal("build")),
    vscode.commands.registerCommand("atf.check", () => {
      const doc = activeAtf();
      if (doc) check(doc);
    }),
    vscode.languages.registerDocumentSymbolProvider({ language: "atf" }, symbolProvider),
    vscode.workspace.onDidSaveTextDocument((doc) => {
      if (cfg().get("checkOnSave")) check(doc);
    }),
    vscode.workspace.onDidChangeTextDocument((e) => {
      if (e.contentChanges.length) scheduleAutoImport(e.document);
    }),
    vscode.workspace.onDidOpenTextDocument((doc) => {
      if (cfg().get("checkOnSave")) check(doc);
    }),
    vscode.workspace.onDidCloseTextDocument((doc) => diagnostics.delete(doc.uri))
  );
  vscode.workspace.textDocuments.forEach((d) => cfg().get("checkOnSave") && check(d));
}

function deactivate() {
  for (const t of timers.values()) clearTimeout(t);
}

module.exports = { activate, deactivate };
