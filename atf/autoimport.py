"""Automatic imports: a program that uses a name from the standard library (json_parse, ui_run, Node, ...)
does not need  import "std/json"  at the top. stdlib/index.txt (made by tools/stdlib_index.py) says which
module defines each name. The scan is lexical (the same as compiler/autoimport.atf): it is cheap, and a name
the program defines itself never pulls a module in."""
import os
import re

DECL = re.compile(r'^(?:pub\s+)?(?:extern\s+"[^"]*"\s+)?(?:fn|struct|enum|const|var|let|interface|type)\s+([A-Za-z_]\w*)')


def _is_word(c):
    return c.isalnum() and c.isascii() or c == "_"


def _is_start(c):
    return c.isalpha() and c.isascii() or c == "_"


def auto_import_modules(std_dir, texts, user):
    """texts: {path: source} of every loaded file, user: the paths of the program's own files.
    Returns the std module names (without "std/") that the program uses and does not import."""
    found = []
    try:
        with open(os.path.join(std_dir, "index.txt"), encoding="utf-8") as f:
            data = f.read()
    except OSError:
        return found
    idx = {}
    for line in data.splitlines():
        parts = line.split(" ")
        if len(parts) == 2:
            idx[parts[0]] = parts[1]
    defined = set()
    for t in texts.values():
        for line in t.split("\n"):
            m = DECL.match(line)
            if m:
                defined.add(m.group(1))
    picked = set()
    for p in user:
        t = texts[p]
        n = len(t)
        in_str = False
        depth = 0
        i = 0
        while i < n:
            b = t[i]
            if in_str and depth == 0:
                if b == "\\":
                    i += 2
                    continue
                if b == '"':
                    in_str = False
                elif b == "{":
                    depth = 1
                i += 1
                continue
            if depth > 0:
                if b == "{":
                    depth += 1
                elif b == "}":
                    depth -= 1
                    i += 1
                    continue
                elif b == '"':
                    i += 1
                    while i < n and t[i] != '"':
                        i += 1
                    i += 1
                    continue
            else:
                if b == "/" and i + 1 < n and t[i + 1] == "/":
                    while i < n and t[i] != "\n":
                        i += 1
                    continue
                if b == '"':
                    if i + 2 < n and t[i + 1] == '"' and t[i + 2] == '"':
                        i += 3
                        while i + 2 < n and not (t[i] == '"' and t[i + 1] == '"' and t[i + 2] == '"'):
                            i += 1
                        i += 3
                        continue
                    in_str = True
                    i += 1
                    continue
            if b == "'":
                if i + 2 < n and t[i + 2] == "'":
                    i += 3
                    continue
                if i + 3 < n and t[i + 1] == "\\" and t[i + 3] == "'":
                    i += 4
                    continue
            if _is_start(b) and (i == 0 or not (_is_word(t[i - 1]) or t[i - 1] == ".")):
                j = i
                while j < n and _is_word(t[j]):
                    j += 1
                w = t[i:j]
                if w in idx and w not in defined:
                    ok = "A" <= b <= "Z"
                    if not ok:
                        k = j
                        while k < n and t[k] == " ":
                            k += 1
                        if k < n and (t[k] == "(" or (t[k] == ":" and k + 1 < n and t[k + 1] == ":")):
                            ok = True
                    m = idx[w]
                    if ok and m not in picked:
                        picked.add(m)
                        found.append(m)
                i = j
                continue
            i += 1
    return found
