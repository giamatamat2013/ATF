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
