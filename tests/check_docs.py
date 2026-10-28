"""Verifies every code sample in README.md and docs/*.md by actually compiling and running it.

usage: python tests/check_docs.py [file-or-name-filter ...] [-v] [--fill]

  --fill   authoring helper: rewrites the content of every `output` / `error` block that follows an
           atf sample with what the program really printed (review the result by eye!)

Conventions inside the markdown files (fenced code blocks):

  ```atf                      a program or a piece of declarations
  ...
  ```
  ```input                    (optional) text fed to the program on standard input
  ...
  ```
  ```output                   the exact expected standard output (trailing spaces are ignored)
  ...
  ```
  ```error                    instead of `output`: the program must fail (compile error or runtime
  ...                         panic) and its standard error must match exactly. The file is
  ```                         always called main.atf, so messages show  main.atf:3:5

  * A block that contains `fn main` is compiled and run. It must exit with code 0 (non-zero for an
    `error` block). If an `output` block follows, the standard output must match.
  * A block without `fn main` is a fragment (declarations only); an empty `fn main() {}` is added
    and the result must compile.
  * Add the word `nocheck` after atf (```atf nocheck) to skip a block on purpose.
  * Other languages (text, bash, ebnf ...) are not checked.
"""
import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# samples are checked with the native compiler (the one that ships); ATF=path overrides it
ATF = os.path.abspath(os.environ.get("ATF", os.path.join(ROOT, "bin", "atf.exe")))
sys.path.insert(0, ROOT)
from atf.launch import program_argv  # noqa: E402

FENCE = re.compile(r"^(\s*)```(.*)$")


def parse_blocks(path):
    """returns (lines, blocks); a block is (lang, flags, text, first_line_number, start_idx, end_idx)"""
    blocks = []
    lines = open(path, encoding="utf8").read().replace("\r\n", "\n").split("\n")
    i = 0
    while i < len(lines):
        m = FENCE.match(lines[i])
        if m:
            info = m.group(2).strip().split()
            lang = info[0] if info else ""
            flags = info[1:]
            start = i + 1
            j = start
            while j < len(lines) and not FENCE.match(lines[j]):
                j += 1
            blocks.append((lang, flags, "\n".join(lines[start:j]) + "\n", start + 1, start, j))
            i = j + 1
        else:
            i += 1
    return lines, blocks


def norm(s):
    return "\n".join(l.rstrip() for l in s.replace("\r\n", "\n").rstrip("\n").split("\n"))


def run_program(source, stdin, tmp):
    """returns (compiled_ok, stdout, stderr, exit_code)"""
    path = os.path.join(tmp, "main.atf")
    with open(path, "w", encoding="utf8", newline="\n") as f:
        f.write(source)
    exe = os.path.join(tmp, "main.exe")
    if os.path.exists(exe):
        os.remove(exe)
    env = dict(os.environ, ATF_PATH_STYLE="base")
    c = subprocess.run(program_argv(ATF) + ["build", path, "-o", exe], capture_output=True, env=env, cwd=tmp, timeout=120)
    if c.returncode != 0 or not os.path.exists(exe):
        return False, "", c.stderr.decode("utf-8", "replace").replace("\r\n", "\n"), 1
    try:
        p = subprocess.run(program_argv(exe), input=stdin.encode("utf8"), capture_output=True, timeout=60, cwd=tmp)
    except subprocess.TimeoutExpired:
        return True, "", "TIMEOUT\n", 1
    return (True, p.stdout.decode("utf-8", "replace").replace("\r\n", "\n"),
            p.stderr.decode("utf-8", "replace").replace("\r\n", "\n"),
            p.returncode if p.returncode < (1 << 31) else p.returncode - (1 << 32))


def check_file(path, verbose, fill=False):
    lines, blocks = parse_blocks(path)
    replacements = []
    tmp = tempfile.mkdtemp(prefix="atf-docs-")
    checked = failed = skipped = 0
    rel = os.path.relpath(path, ROOT)
    for idx, (lang, flags, text, line, bstart, bend) in enumerate(blocks):
        if lang != "atf":
            continue
        if "nocheck" in flags:
            skipped += 1
            continue
        # look at the blocks that directly follow
        stdin = ""
        expected = None
        kind = None
        k = idx + 1
        if k < len(blocks) and blocks[k][0] == "input":
            stdin = blocks[k][2]
            k += 1
        if k < len(blocks) and blocks[k][0] in ("output", "error"):
            kind = blocks[k][0]
            expected = blocks[k][2]
        has_main = re.search(r"^\s*fn\s+main\s*\(", text, re.M) is not None
        source = text if has_main else text + "\nfn main() {\n}\n"
        ok, out, err, code = run_program(source, stdin, tmp)
        checked += 1
        problem = None
        if fill and kind is not None:
            new = err if kind == "error" else out
            new = norm(new) + "\n"
            replacements.append((blocks[k][4], blocks[k][5], new))
            expected = new
        if kind == "error":
            if code == 0:
                problem = "expected the program to fail, but it exited with code 0"
            elif norm(err) != norm(expected):
                problem = "stderr differs:\n--- expected\n%s\n--- actual\n%s" % (norm(expected), norm(err))
        else:
            if code != 0:
                problem = "exit code %d\n%s" % (code, err.strip())
            elif kind == "output" and norm(out) != norm(expected):
                problem = "stdout differs:\n--- expected\n%s\n--- actual\n%s" % (norm(expected), norm(out))
        if problem:
            failed += 1
            print("FAIL %s:%d" % (rel, line))
            for l in problem.splitlines()[:40]:
                print("     " + l)
        elif verbose:
            print("ok   %s:%d%s" % (rel, line, "" if kind else "  (not compared)"))
    if fill and replacements:
        for a, b, new in sorted(replacements, reverse=True):
            lines[a:b] = new.rstrip("\n").split("\n") if new.strip() else []
        with open(path, "w", encoding="utf8", newline="\n") as f:
            f.write("\n".join(lines))
        print("filled %d output block(s) in %s" % (len(replacements), rel))
    print("%-24s %3d samples checked, %d failed, %d skipped" % (rel, checked, failed, skipped))
    return failed


def main():
    argv = [a for a in sys.argv[1:] if not a.startswith("-")]
    verbose = "-v" in sys.argv
    fill = "--fill" in sys.argv
    files = [os.path.join(ROOT, "README.md")]
    ddir = os.path.join(ROOT, "docs")
    if os.path.isdir(ddir):
        files += [os.path.join(ddir, f) for f in sorted(os.listdir(ddir)) if f.endswith(".md")]
    files = [f for f in files if os.path.exists(f)]
    if argv:
        files = [f for f in files if any(a in f for a in argv)]
    failed = 0
    for f in files:
        failed += check_file(f, verbose, fill)
    print("\n%s" % ("all documentation samples are correct" if not failed else "%d sample(s) FAILED" % failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
