"""Tokenizer for ATF."""
import re
from .errors import CompileError, Pos

KEYWORDS = {
    "fn", "let", "var", "const", "if", "else", "while", "for", "in", "loop", "break", "continue", "return",
    "struct", "enum", "impl", "match", "import", "extern", "true", "false", "and", "or", "not", "as",
    "defer", "type", "nil", "step", "unsafe", "pub",
}

OPS = [
    "..=", "<<=", ">>>", ">>=", "**=", "==", "!=", "<=", ">=", "&&", "||", "+=", "-=", "*=", "/=", "%=", "&=", "|=", "^=",
    "<<", ">>", "->", "=>", "..", "::", "??", "**",
    "+", "-", "*", "/", "%", "=", "<", ">", "!", "&", "|", "^", "~", "(", ")", "[", "]", "{", "}", ",", ":", ";",
    ".", "?", "@", "#",
]

# a newline right after one of these tokens continues the statement
CONTINUERS = {
    "+", "-", "*", "/", "%", "=", "&", "|", "^", ",", "(", "[", ".", "==", "!=", "<=", ">=", "&&", "||",
    "+=", "-=", "*=", "/=", "%=", "&=", "|=", "^=", "<<", ">>", "->", "=>", "..", "::", "??", "**", "..=", "<<=", ">>=",
    "**=", "and", "or", "not", "in", "as", ":",
}

# a line starting with one of these continues the previous statement
LEADING_CONTINUERS = (".", "&&", "||", "??")


class Token:
    __slots__ = ("kind", "val", "line", "col", "nl_before", "space_before", "end")

    def __init__(self, kind, val, line, col):
        self.kind = kind          # INT FLOAT STR CHAR IDENT KW OP NEWLINE EOF
        self.val = val
        self.line = line
        self.col = col
        self.nl_before = False
        self.space_before = False
        self.end = 0

    def __repr__(self):
        return "%s(%r)@%d:%d" % (self.kind, self.val, self.line, self.col)


_ident_re = re.compile(r"[A-Za-z_\u0080-￿][A-Za-z0-9_\u0080-￿]*")
_num_re = re.compile(r"0[xX][0-9a-fA-F_]+|0[bB][01_]+|0[oO][0-7_]+|[0-9][0-9_]*(?:\.[0-9][0-9_]*)?(?:[eE][+-]?[0-9]+)?")
_ops_sorted = sorted(OPS, key=lambda o: -len(o))


class StrPart:
    """interpolated expression inside a string literal"""
    __slots__ = ("src", "line", "col", "spec")

    def __init__(self, src, line, col, spec=None):
        self.src = src
        self.line = line
        self.col = col
        self.spec = spec


def tokenize(src, file):
    toks = []
    i = 0
    n = len(src)
    line = 1
    line_start = 0
    depth = []            # stack of bracket chars
    last_sig = None       # last significant token

    def err(msg, ln=None, col=None):
        raise CompileError(msg, Pos(file, ln or line, col or (i - line_start + 1)))

    def push(kind, val, ln, col, nl, sp):
        t = Token(kind, val, ln, col)
        t.nl_before = nl
        t.space_before = sp
        t.end = i
        toks.append(t)
        return t

    pending_nl = False
    pending_space = False
    while i < n:
        c = src[i]
        if c == "\n":
            line += 1
            i += 1
            line_start = i
            pending_nl = True
            pending_space = True
            continue
        if c in " \t\r":
            i += 1
            pending_space = True
            continue
        if c == "/" and src.startswith("//", i):
            j = src.find("\n", i)
            i = n if j < 0 else j
            continue
        if c == "#" and (i + 1 < n and src[i + 1] == "!") and i == 0:
            j = src.find("\n", i)
            i = n if j < 0 else j
            continue
        if c == "/" and src.startswith("/*", i):
            depth_c = 1
            j = i + 2
            while j < n and depth_c:
                if src.startswith("/*", j):
                    depth_c += 1
                    j += 2
                elif src.startswith("*/", j):
                    depth_c -= 1
                    j += 2
                else:
                    if src[j] == "\n":
                        line += 1
                        line_start = j + 1
                        pending_nl = True
                    j += 1
            if depth_c:
                err("unterminated block comment")
            i = j
            pending_space = True
            continue

        col = i - line_start + 1
        # ---- newline handling: decide whether the pending newline is significant
        if pending_nl:
            pending_nl = False
            sig = True
            if depth and depth[-1] in "([":
                sig = False
            elif last_sig is None:
                sig = False
            elif last_sig.kind in ("OP", "KW") and last_sig.val in CONTINUERS:
                sig = False
            else:
                for lc in LEADING_CONTINUERS:
                    if src.startswith(lc, i) and not src.startswith("..", i):
                        sig = False
                if src.startswith("&&", i) or src.startswith("||", i) or src.startswith("??", i):
                    sig = False
                if src[i] == "." and not src.startswith("..", i):
                    sig = False
            if sig and (last_sig is not None and last_sig.kind != "NEWLINE"):
                t = Token("NEWLINE", "\n", line - 1, 0)
                toks.append(t)
                last_sig = t
        sp = pending_space
        nlb = bool(toks) and toks[-1].kind == "NEWLINE"
        pending_space = False

        # ---- strings --------------------------------------------------------
        if c == '"' or (c == "r" and i + 1 < n and src[i + 1] == '"') or (c == "r" and src.startswith('r#"', i)):
            raw = c == "r"
            start_line, start_col = line, col
            if raw:
                hashes = 0
                i += 1
                while src[i] == "#":
                    hashes += 1
                    i += 1
                i += 1       # opening quote
                end = '"' + "#" * hashes
                j = src.find(end, i)
                if j < 0:
                    err("unterminated raw string", start_line, start_col)
                text = src[i:j]
                line += text.count("\n")
                if "\n" in text:
                    line_start = i + text.rfind("\n") + 1
                i = j + len(end)
                last_sig = push("STR", [text.encode("utf-8")], start_line, start_col, nlb, sp)
                continue
            triple = src.startswith('"""', i)
            i += 3 if triple else 1
            parts = []
            buf = bytearray()
            while True:
                if i >= n:
                    err("unterminated string", start_line, start_col)
                ch = src[i]
                if triple and src.startswith('"""', i):
                    i += 3
                    break
                if not triple and ch == '"':
                    i += 1
                    break
                if ch == "\n":
                    if not triple:
                        err("unterminated string (use \"\"\" for multi-line strings)", start_line, start_col)
                    line += 1
                    line_start = i + 1
                    buf += b"\n"
                    i += 1
                    continue
                if ch == "\\":
                    i += 1
                    e = src[i] if i < n else ""
                    simple = {"n": b"\n", "t": b"\t", "r": b"\r", "0": b"\0", "\\": b"\\", '"': b'"', "'": b"'",
                              "{": b"{", "}": b"}", "a": b"\a", "e": b"\x1b"}
                    if e in simple:
                        buf += simple[e]
                        i += 1
                    elif e == "x":
                        buf.append(int(src[i + 1:i + 3], 16))
                        i += 3
                    elif e == "u":
                        if src[i + 1] != "{":
                            err("expected \\u{...}")
                        j = src.index("}", i)
                        buf += chr(int(src[i + 2:j], 16)).encode("utf-8")
                        i = j + 1
                    elif e == "\n" and triple:
                        line += 1
                        line_start = i + 1
                        i += 1
                    else:
                        err("unknown escape \\%s" % e)
                    continue
                if ch == "{" and src[i + 1:i + 2] == '"':
                    buf += b"{"          # a brace right before the closing quote is literal
                    i += 1
                    continue
                if ch == "{":
                    # interpolation: scan to the matching brace
                    j = i + 1
                    d = 1
                    istart_line, istart_col = line, i - line_start + 2
                    while j < n and d:
                        cj = src[j]
                        if cj == "{":
                            d += 1
                        elif cj == "}":
                            d -= 1
                            if d == 0:
                                break
                        elif cj == '"':
                            # skip nested string
                            j += 1
                            while j < n and src[j] != '"':
                                if src[j] == "\\":
                                    j += 1
                                j += 1
                        elif cj == "'":
                            if j + 2 < n and src[j + 2] == "'":
                                j += 2
                            elif j + 3 < n and src[j + 1] == "\\" and src[j + 3] == "'":
                                j += 3
                        j += 1
                    if d:
                        err("unterminated {interpolation} in string", istart_line, istart_col)
                    inner = src[i + 1:j]
                    spec = None
                    # format spec after a top-level ':' (not inside brackets / strings / ?: ), e.g. {x:.2f}
                    m = re.search(r"(?<![:])\:([<>^]?[0-9]*(?:\.[0-9]+)?[fdxXbsc]?|0[0-9]+)\s*$", inner)
                    if m and m.group(1) != "" and not inner[:m.start()].strip().endswith(("?", "::")) and _balanced(inner[:m.start()]):
                        spec = m.group(1)
                        inner = inner[:m.start()]
                    if buf:
                        parts.append(bytes(buf))
                        buf = bytearray()
                    parts.append(StrPart(inner, istart_line, istart_col, spec))
                    line += src.count("\n", i, j)
                    if "\n" in src[i:j]:
                        line_start = src.rfind("\n", i, j) + 1
                    i = j + 1
                    continue
                buf += ch.encode("utf-8")
                i += 1
            if buf or not parts:
                parts.append(bytes(buf))
            last_sig = push("STR", parts, start_line, start_col, nlb, sp)
            continue

        # ---- char literal ---------------------------------------------------
        if c == "'":
            start_col = col
            j = i + 1
            if j < n and src[j] == "\\":
                e = src[j + 1]
                simple = {"n": 10, "t": 9, "r": 13, "0": 0, "\\": 92, "'": 39, '"': 34, "a": 7, "e": 27}
                if e in simple:
                    v = simple[e]
                    j += 2
                elif e == "x":
                    v = int(src[j + 2:j + 4], 16)
                    j += 4
                elif e == "u":
                    k = src.index("}", j)
                    v = int(src[j + 3:k], 16)
                    j = k + 1
                else:
                    err("unknown escape \\%s" % e)
            else:
                v = ord(src[j])
                j += 1
            if j >= n or src[j] != "'":
                err("unterminated character literal (character literals hold one character, like 'a')")
            i = j + 1
            last_sig = push("CHAR", v, line, start_col, nlb, sp)
            continue

        # ---- numbers --------------------------------------------------------
        if c.isdigit():
            if toks and toks[-1].kind == "OP" and toks[-1].val == "." and not sp:
                j = i
                while j < n and src[j].isdigit():
                    j += 1
                i = j
                last_sig = push("INT", int(src[col - 1 + line_start:j]), line, col, nlb, sp)
                continue
            m = _num_re.match(src, i)
            text = m.group(0)
            # don't swallow the dot of a range: 1..5
            if "." in text and src.startswith("..", i + text.index(".")):
                text = text[:text.index(".")]
            i += len(text)
            t = text.replace("_", "")
            if t[:2] in ("0x", "0X"):
                last_sig = push("INT", int(t, 16), line, col, nlb, sp)
            elif t[:2] in ("0b", "0B"):
                last_sig = push("INT", int(t, 2), line, col, nlb, sp)
            elif t[:2] in ("0o", "0O"):
                last_sig = push("INT", int(t, 8), line, col, nlb, sp)
            elif "." in t or "e" in t or "E" in t:
                last_sig = push("FLOAT", float(t), line, col, nlb, sp)
            else:
                v = int(t)
                if v >= 1 << 64:
                    err("integer literal too large")
                last_sig = push("INT", v, line, col, nlb, sp)
            continue

        # ---- identifiers / keywords -----------------------------------------
        m = _ident_re.match(src, i)
        if m:
            text = m.group(0)
            i += len(text)
            kind = "KW" if text in KEYWORDS else "IDENT"
            last_sig = push(kind, text, line, col, nlb, sp)
            continue

        # ---- operators ------------------------------------------------------
        for op in _ops_sorted:
            if src.startswith(op, i):
                break
        else:
            err("unexpected character %r" % c)
        i += len(op)
        if op in ("(", "[", "{"):
            depth.append(op)
        elif op in (")", "]", "}"):
            if not depth:
                err("unmatched %r" % op, line, col)
            depth.pop()
        last_sig = push("OP", op, line, col, nlb, sp)

    if depth:
        raise CompileError("unclosed %r" % depth[-1], Pos(file, line, 1))
    t = Token("NEWLINE", "\n", line, 0)
    toks.append(t)
    toks.append(Token("EOF", None, line, 1))
    return toks


def _balanced(s):
    d = 0
    for ch in s:
        if ch in "([{":
            d += 1
        elif ch in ")]}":
            d -= 1
    return d == 0
