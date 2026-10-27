"""Compiler diagnostics with source excerpts."""


class Pos:
    __slots__ = ("file", "line", "col")

    def __init__(self, file, line, col):
        self.file = file
        self.line = line
        self.col = col

    def __repr__(self):
        return "%s:%d:%d" % (self.file, self.line, self.col)


NOPOS = Pos("<builtin>", 0, 0)

# source text of every loaded file, for error excerpts
SOURCES = {}

PATH_STYLE = "relative"      # "relative" | "base" (used by the test-suite for stable output)


def short_path(p):
    import os
    if PATH_STYLE == "base":
        return os.path.basename(p)
    try:
        if p.startswith(os.path.join(os.path.dirname(os.path.abspath(__file__)), "stdlib")):
            return "<std>/" + os.path.basename(p)
        rel = os.path.relpath(p)
        if not rel.startswith(".."):
            return rel
    except ValueError:
        pass
    return p


class CompileError(Exception):
    def __init__(self, msg, pos=None, hint=None):
        Exception.__init__(self, msg)
        self.msg = msg
        self.pos = pos
        self.hint = hint

    def render(self):
        out = []
        if self.pos is not None and self.pos.line > 0:
            out.append("error: %s" % self.msg)
            out.append("  --> %s:%d:%d" % (short_path(self.pos.file), self.pos.line, self.pos.col))
            src = SOURCES.get(self.pos.file)
            if src is not None:
                lines = src.split("\n")
                if 0 < self.pos.line <= len(lines):
                    text = lines[self.pos.line - 1].rstrip("\r")
                    gutter = str(self.pos.line)
                    out.append(" %s | %s" % (gutter, text))
                    out.append(" %s | %s^" % (" " * len(gutter), " " * max(self.pos.col - 1, 0)))
        else:
            out.append("error: %s" % self.msg)
        if self.hint:
            out.append("  hint: %s" % self.hint)
        return "\n".join(out)


class SilentError(CompileError):
    """a follow-up error caused by an earlier (already reported) one"""
