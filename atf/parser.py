"""Recursive-descent / Pratt parser for ATF."""
from . import syntax as S
from .errors import CompileError, Pos
from .lexer import tokenize, StrPart

BINARY_PREC = {
    "??": (2, "R"),
    "or": (3, "L"), "||": (3, "L"),
    "and": (4, "L"), "&&": (4, "L"),
    "==": (6, "L"), "!=": (6, "L"), "<": (6, "L"), ">": (6, "L"), "<=": (6, "L"), ">=": (6, "L"), "in": (6, "L"),
    "|": (7, "L"), "^": (8, "L"), "&": (9, "L"),
    "<<": (10, "L"), ">>": (10, "L"), ">>>": (10, "L"),
    "+": (11, "L"), "-": (11, "L"),
    "*": (12, "L"), "/": (12, "L"), "%": (12, "L"),
    "as": (13, "L"),
    "**": (15, "R"),
}
PREC_UNARY = 14
ASSIGN_OPS = {"=", "+=", "-=", "*=", "/=", "%=", "&=", "|=", "^=", "<<=", ">>=", "**="}


class Parser:
    def __init__(self, toks, file):
        self.toks = toks
        self.i = 0
        self.file = file
        self.no_struct = False

    # ---- token helpers --------------------------------------------------
    @property
    def tok(self):
        return self.toks[self.i]

    def peek(self, k=1):
        j = self.i + k
        return self.toks[j] if j < len(self.toks) else self.toks[-1]

    def pos(self, t=None):
        t = t or self.tok
        return Pos(self.file, t.line, t.col)

    def error(self, msg, tok=None, hint=None):
        raise CompileError(msg, self.pos(tok), hint)

    def describe(self, t):
        if t.kind == "EOF":
            return "end of file"
        if t.kind == "NEWLINE":
            return "end of line"
        if t.kind == "STR":
            return "a string"
        return "'%s'" % (t.val,)

    def at_op(self, v):
        t = self.tok
        return t.kind == "OP" and t.val == v

    def at_kw(self, v):
        t = self.tok
        return t.kind == "KW" and t.val == v

    def eat_op(self, v):
        if self.at_op(v):
            self.i += 1
            return True
        return False

    def eat_kw(self, v):
        if self.at_kw(v):
            self.i += 1
            return True
        return False

    def expect_op(self, v, what=None):
        if not self.at_op(v):
            self.error("expected '%s'%s but found %s" % (v, " " + what if what else "", self.describe(self.tok)))
        t = self.tok
        self.i += 1
        return t

    def expect_kw(self, v):
        if not self.at_kw(v):
            self.error("expected '%s' but found %s" % (v, self.describe(self.tok)))
        self.i += 1

    def expect_ident(self, what="a name"):
        t = self.tok
        if t.kind != "IDENT":
            if t.kind == "KW":
                self.error("expected %s but found keyword '%s'" % (what, t.val), hint="'%s' is a reserved word" % t.val)
            self.error("expected %s but found %s" % (what, self.describe(t)))
        self.i += 1
        return t

    def skip_nl(self):
        while self.tok.kind == "NEWLINE" or self.at_op(";"):
            self.i += 1

    def end_stmt(self):
        t = self.tok
        if t.kind == "NEWLINE" or (t.kind == "OP" and t.val == ";"):
            self.skip_nl()
            return
        if t.kind == "EOF" or (t.kind == "OP" and t.val == "}"):
            return
        self.error("unexpected %s (expected end of statement)" % self.describe(t))

    def expect_gt(self):
        t = self.tok
        if t.kind == "OP":
            if t.val == ">":
                self.i += 1
                return
            if t.val in (">>", ">=", ">>=", ">>>"):
                t.val = t.val[1:]
                return
        self.error("expected '>' but found %s" % self.describe(t))

    # ---- program ----------------------------------------------------------
    def parse_program(self):
        items = []
        self.skip_nl()
        while self.tok.kind != "EOF":
            items.append(self.parse_item())
            self.skip_nl()
        return items

    def parse_item(self):
        t = self.tok
        pos = self.pos()
        attrs = []
        while self.at_op("#"):
            self.i += 1
            self.expect_op("[")
            name = self.expect_ident("an attribute name").val
            attrs.append(name)
            self.expect_op("]")
            self.skip_nl()
        self.eat_kw("pub")
        t = self.tok
        if t.kind == "KW":
            k = t.val
            if k == "fn":
                return self.parse_fn(attrs)
            if k == "struct":
                return self.parse_struct()
            if k == "enum":
                return self.parse_enum()
            if k == "impl":
                return self.parse_impl()
            if k == "const":
                self.i += 1
                name = self.expect_ident("a constant name").val
                ty = None
                if self.eat_op(":"):
                    ty = self.parse_type()
                self.expect_op("=")
                val = self.parse_expr()
                self.end_stmt()
                return S.ConstDecl(name, ty, val, pos=pos)
            if k in ("let", "var"):
                self.i += 1
                name = self.expect_ident("a variable name").val
                ty = None
                if self.eat_op(":"):
                    ty = self.parse_type()
                val = None
                if self.eat_op("="):
                    val = self.parse_expr()
                self.end_stmt()
                return S.GlobalDecl(name, ty, val, k == "var", pos=pos)
            if k == "import":
                self.i += 1
                if self.tok.kind != "STR":
                    self.error("expected a file name in quotes after 'import'", hint='example: import "std/random"')
                parts = self.tok.val
                self.i += 1
                self.end_stmt()
                return S.ImportDecl(b"".join(p for p in parts if isinstance(p, bytes)).decode("utf-8"), pos=pos)
            if k == "extern":
                return self.parse_extern()
            if k == "type":
                self.i += 1
                name = self.expect_ident("a type name").val
                tps = self.parse_tparams()
                self.expect_op("=")
                ty = self.parse_type()
                self.end_stmt()
                return S.TypeAlias(name, tps, ty, pos=pos)
        self.error("expected a declaration (fn, struct, enum, impl, const, let, var, import) but found %s" % self.describe(t))

    def parse_tparams(self):
        tps = []
        if self.at_op("<"):
            self.i += 1
            while True:
                tps.append(self.expect_ident("a type parameter").val)
                if not self.eat_op(","):
                    break
            self.expect_gt()
        return tps

    def parse_fn(self, attrs=(), anonymous=False):
        pos = self.pos()
        self.expect_kw("fn")
        name = None
        tps = []
        if not anonymous:
            name = self.expect_ident("a function name").val
            tps = self.parse_tparams()
        self.expect_op("(")
        params = self.parse_params()
        ret = None
        if self.eat_op("->"):
            ret = self.parse_type()
        if self.eat_op("=>"):
            e = self.parse_expr()
            body = S.Block([S.Return(e, pos=e.pos)], pos=e.pos)
            if not anonymous:
                self.end_stmt()
        else:
            self.skip_nl_before_brace()
            body = self.parse_block()
        return S.FnDecl(name, tps, params, ret, body, list(attrs), pos=pos)

    def skip_nl_before_brace(self):
        # allow `fn f()\n{` Allman style
        if self.tok.kind == "NEWLINE" and self.peek().kind == "OP" and self.peek().val == "{":
            self.i += 1

    def parse_params(self):
        params = []
        self.skip_nl()
        while not self.at_op(")"):
            ppos = self.pos()
            if self.at_kw("var"):
                self.i += 1
            name = self.expect_ident("a parameter name").val
            ty = None
            default = None
            if self.eat_op(":"):
                ty = self.parse_type()
            elif name != "self":
                self.error("parameter '%s' needs a type, like  %s: int" % (name, name))
            if self.eat_op("="):
                default = self.parse_expr()
            params.append(S.Param(name, ty, default, pos=ppos))
            self.skip_nl()
            if not self.eat_op(","):
                break
            self.skip_nl()
        self.skip_nl()
        self.expect_op(")")
        return params

    def parse_extern(self):
        pos = self.pos()
        self.expect_kw("extern")
        if self.tok.kind != "STR":
            self.error('expected the DLL name in quotes, like  extern "kernel32" fn ...')
        dll = b"".join(p for p in self.tok.val if isinstance(p, bytes)).decode()
        self.i += 1
        self.expect_kw("fn")
        name = self.expect_ident("a function name").val
        self.expect_op("(")
        params = self.parse_params()
        ret = None
        if self.eat_op("->"):
            ret = self.parse_type()
        sym = name
        if self.eat_kw("as"):
            if self.tok.kind != "STR":
                self.error('expected the name the DLL uses in quotes, like  as "send"')
            sym = b"".join(p for p in self.tok.val if isinstance(p, bytes)).decode()
            self.i += 1
        self.end_stmt()
        return S.ExternDecl(dll, name, params, ret, False, sym, pos=pos)

    def parse_struct(self):
        pos = self.pos()
        self.expect_kw("struct")
        name = self.expect_ident("a struct name").val
        tps = self.parse_tparams()
        self.skip_nl_before_brace()
        self.expect_op("{")
        self.skip_nl()
        fields = []
        while not self.at_op("}"):
            fname = self.expect_ident("a field name")
            self.expect_op(":")
            fty = self.parse_type()
            fields.append((fname.val, fty, self.pos(fname)))
            if not self.eat_op(","):
                if not (self.tok.kind == "NEWLINE" or self.at_op("}") or self.at_op(";")):
                    self.error("expected ',' or a new line between struct fields")
            self.skip_nl()
        self.expect_op("}")
        self.end_stmt()
        return S.StructDecl(name, tps, fields, pos=pos)

    def parse_enum(self):
        pos = self.pos()
        self.expect_kw("enum")
        name = self.expect_ident("an enum name").val
        tps = self.parse_tparams()
        self.skip_nl_before_brace()
        self.expect_op("{")
        self.skip_nl()
        variants = []
        while not self.at_op("}"):
            vt = self.expect_ident("a variant name")
            payload = []
            value = None
            if self.eat_op("("):
                self.skip_nl()
                while not self.at_op(")"):
                    # allow optional `name: Type`
                    if self.tok.kind == "IDENT" and self.peek().kind == "OP" and self.peek().val == ":":
                        self.i += 2
                    payload.append(self.parse_type())
                    self.skip_nl()
                    if not self.eat_op(","):
                        break
                    self.skip_nl()
                self.expect_op(")")
            elif self.eat_op("="):
                neg = self.eat_op("-")
                if self.tok.kind != "INT":
                    self.error("enum values must be integer constants")
                value = -self.tok.val if neg else self.tok.val
                self.i += 1
            variants.append((vt.val, payload, value, self.pos(vt)))
            if not self.eat_op(","):
                if not (self.tok.kind == "NEWLINE" or self.at_op("}") or self.at_op(";")):
                    self.error("expected ',' or a new line between enum variants")
            self.skip_nl()
        self.expect_op("}")
        self.end_stmt()
        return S.EnumDecl(name, tps, variants, pos=pos)

    def parse_impl(self):
        pos = self.pos()
        self.expect_kw("impl")
        tps = self.parse_tparams()
        ty = self.parse_type()
        self.skip_nl_before_brace()
        self.expect_op("{")
        self.skip_nl()
        methods = []
        while not self.at_op("}"):
            attrs = []
            while self.at_op("#"):
                self.i += 1
                self.expect_op("[")
                attrs.append(self.expect_ident().val)
                self.expect_op("]")
                self.skip_nl()
            self.eat_kw("pub")
            if not self.at_kw("fn"):
                self.error("only functions can appear inside 'impl' (found %s)" % self.describe(self.tok))
            methods.append(self.parse_fn(attrs))
            self.skip_nl()
        self.expect_op("}")
        self.end_stmt()
        return S.ImplDecl(ty, tps, methods, pos=pos)

    # ---- types --------------------------------------------------------------
    def parse_type(self):
        t = self.parse_type_primary()
        while self.at_op("?") and not self.tok.space_before:
            self.i += 1
            t = S.TOpt(t, pos=t.pos)
        return t

    def parse_type_primary(self):
        t = self.tok
        pos = self.pos()
        if t.kind == "OP":
            if t.val == "[":
                self.i += 1
                e = self.parse_type()
                self.expect_op("]")
                return S.TArray(e, pos=pos)
            if t.val == "{":
                self.i += 1
                k = self.parse_type()
                self.expect_op(":")
                v = self.parse_type()
                self.expect_op("}")
                return S.TMap(k, v, pos=pos)
            if t.val == "(":
                self.i += 1
                elems = []
                while not self.at_op(")"):
                    elems.append(self.parse_type())
                    if not self.eat_op(","):
                        break
                self.expect_op(")")
                if not elems:
                    return S.TName("void", [], pos=pos)
                if len(elems) == 1:
                    return elems[0]
                return S.TTuple(elems, pos=pos)
        if t.kind == "KW" and t.val == "fn":
            self.i += 1
            self.expect_op("(")
            params = []
            while not self.at_op(")"):
                params.append(self.parse_type())
                if not self.eat_op(","):
                    break
            self.expect_op(")")
            ret = None
            if self.eat_op("->"):
                ret = self.parse_type()
            return S.TFn(params, ret, pos=pos)
        if t.kind == "IDENT":
            self.i += 1
            args = []
            if self.at_op("<"):
                self.i += 1
                while True:
                    args.append(self.parse_type())
                    if not self.eat_op(","):
                        break
                self.expect_gt()
            if t.val == "ptr" and len(args) == 1:
                return S.TPtr(args[0], pos=pos)
            return S.TName(t.val, args, pos=pos)
        self.error("expected a type but found %s" % self.describe(t))

    # ---- statements -----------------------------------------------------------
    def parse_block(self):
        pos = self.pos()
        self.expect_op("{")
        stmts = []
        saved = self.no_struct
        self.no_struct = False
        self.skip_nl()
        while not self.at_op("}"):
            if self.tok.kind == "EOF":
                self.error("this '{' is never closed", None)
            stmts.append(self.parse_stmt())
            self.skip_nl()
        self.expect_op("}")
        self.no_struct = saved
        return S.Block(stmts, pos=pos)

    def parse_stmt(self):
        t = self.tok
        pos = self.pos()
        if t.kind == "KW":
            k = t.val
            if k in ("let", "var", "const"):
                return self.parse_let()
            if k == "if":
                s = self.parse_if(S.If)
                return s
            if k == "while":
                self.i += 1
                cond = self.parse_cond()
                self.skip_nl_before_brace()
                body = self.parse_block()
                self.end_stmt_soft()
                return S.While(cond, body, pos=pos)
            if k == "loop":
                self.i += 1
                self.skip_nl_before_brace()
                body = self.parse_block()
                self.end_stmt_soft()
                return S.Loop(body, pos=pos)
            if k == "for":
                return self.parse_for()
            if k == "break":
                self.i += 1
                self.end_stmt()
                return S.Break(pos=pos)
            if k == "continue":
                self.i += 1
                self.end_stmt()
                return S.Continue(pos=pos)
            if k == "return":
                self.i += 1
                val = None
                if not (self.tok.kind in ("NEWLINE", "EOF") or self.at_op("}") or self.at_op(";")):
                    val = self.parse_expr()
                self.end_stmt()
                return S.Return(val, pos=pos)
            if k == "defer":
                self.i += 1
                st = self.parse_stmt()
                return S.Defer(st, pos=pos)
            if k == "match":
                m = self.parse_match(S.MatchStmt)
                self.end_stmt_soft()
                return m
        if t.kind == "OP" and t.val == "{":
            b = self.parse_block()
            self.end_stmt_soft()
            return b
        # expression or assignment
        e = self.parse_expr()
        if self.tok.kind == "OP" and self.tok.val in ASSIGN_OPS:
            op = self.tok.val
            self.i += 1
            self.skip_nl()
            val = self.parse_expr()
            self.end_stmt()
            return S.Assign(e, op, val, pos=pos)
        self.end_stmt()
        return S.ExprStmt(e, pos=pos)

    def end_stmt_soft(self):
        """after a block-ending statement a terminator is optional"""
        t = self.tok
        if t.kind == "NEWLINE" or (t.kind == "OP" and t.val == ";"):
            self.skip_nl()

    def parse_let(self):
        pos = self.pos()
        kw = self.tok.val
        self.i += 1
        mutable = kw == "var"
        if self.at_op("("):
            self.i += 1
            names = []
            while not self.at_op(")"):
                if self.tok.kind == "IDENT":
                    names.append(self.tok.val)
                    self.i += 1
                else:
                    self.error("expected a name in the tuple pattern")
                if not self.eat_op(","):
                    break
            self.expect_op(")")
            target = names
        else:
            target = self.expect_ident("a variable name").val
        ty = None
        if self.eat_op(":"):
            ty = self.parse_type()
        init = None
        if self.eat_op("="):
            self.skip_nl()
            init = self.parse_expr()
        elif ty is None:
            self.error("'%s %s' needs a value:  %s %s = ..." % (kw, target if isinstance(target, str) else "(..)", kw, target if isinstance(target, str) else "(a, b)"))
        elif not mutable:
            self.error("'let %s' needs a value (use 'var' for a variable you assign later)" % target)
        self.end_stmt()
        return S.Let(target, ty, init, mutable, pos=pos)

    def parse_cond(self):
        saved = self.no_struct
        self.no_struct = True
        try:
            if self.at_kw("let"):
                pos = self.pos()
                self.i += 1
                pat = self.parse_pattern()
                self.expect_op("=")
                e = self.parse_expr()
                return S.IfLet(pat, e, pos=pos)
            return self.parse_expr()
        finally:
            self.no_struct = saved

    def parse_if(self, cls):
        pos = self.pos()
        self.expect_kw("if")
        cond = self.parse_cond()
        self.skip_nl_before_brace()
        then = self.parse_block()
        els = None
        # `else` may be on the next line
        j = self.i
        while self.toks[j].kind == "NEWLINE":
            j += 1
        if self.toks[j].kind == "KW" and self.toks[j].val == "else":
            self.i = j + 1
            if self.at_kw("if"):
                els = self.parse_if(cls)
            else:
                self.skip_nl_before_brace()
                els = self.parse_block()
        if cls is S.If:
            self.end_stmt_soft()
        return cls(cond, then, els, pos=pos)

    def parse_for(self):
        pos = self.pos()
        self.expect_kw("for")
        names = []
        paren = self.eat_op("(")
        while True:
            names.append(self.expect_ident("a loop variable").val)
            if not self.eat_op(","):
                break
        if paren:
            self.expect_op(")")
        self.expect_kw("in")
        saved = self.no_struct
        self.no_struct = True
        it = self.parse_expr()
        self.no_struct = saved
        self.skip_nl_before_brace()
        body = self.parse_block()
        self.end_stmt_soft()
        return S.For(names, it, body, pos=pos)

    def parse_match(self, cls):
        pos = self.pos()
        self.expect_kw("match")
        saved = self.no_struct
        self.no_struct = True
        subject = self.parse_expr()
        self.no_struct = saved
        self.skip_nl_before_brace()
        self.expect_op("{")
        self.skip_nl()
        arms = []
        saved = self.no_struct
        self.no_struct = False
        while not self.at_op("}"):
            apos = self.pos()
            pat = self.parse_pattern()
            guard = None
            if self.eat_kw("if"):
                guard = self.parse_expr()
            self.expect_op("=>")
            self.skip_nl()
            if self.at_op("{"):
                body = self.parse_block()
            elif self.tok.kind == "KW" and self.tok.val in ("return", "break", "continue"):
                st = self.parse_stmt()
                body = S.Block([st], pos=apos)
                arms.append(S.MatchArm(pat, guard, body, pos=apos))
                self.skip_nl()
                continue
            else:
                body = self.parse_expr()
                if self.tok.kind == "OP" and self.tok.val in ASSIGN_OPS:
                    op = self.tok.val
                    self.i += 1
                    self.skip_nl()
                    val = self.parse_expr()
                    body = S.Block([S.Assign(body, op, val, pos=body.pos)], pos=apos)
            arms.append(S.MatchArm(pat, guard, body, pos=apos))
            if not self.eat_op(","):
                if not (self.tok.kind == "NEWLINE" or self.at_op("}") or self.at_op(";")):
                    self.error("expected ',' or a new line after the match arm")
            self.skip_nl()
        self.no_struct = saved
        self.expect_op("}")
        return cls(subject, arms, pos=pos)

    # ---- patterns ------------------------------------------------------------
    def parse_pattern(self):
        pos = self.pos()
        alts = [self.parse_pattern_atom()]
        while self.at_op("|"):
            self.i += 1
            alts.append(self.parse_pattern_atom())
        return alts[0] if len(alts) == 1 else S.POr(alts, pos=pos)

    def parse_pattern_atom(self):
        t = self.tok
        pos = self.pos()
        if t.kind == "IDENT":
            if t.val == "_":
                self.i += 1
                return S.PWild(pos=pos)
            path = [t.val]
            self.i += 1
            while self.at_op(".") and self.peek().kind == "IDENT":
                self.i += 1
                path.append(self.tok.val)
                self.i += 1
            args = None
            if self.at_op("("):
                self.i += 1
                args = []
                self.skip_nl()
                while not self.at_op(")"):
                    args.append(self.parse_pattern())
                    self.skip_nl()
                    if not self.eat_op(","):
                        break
                    self.skip_nl()
                self.expect_op(")")
            if args is None and len(path) == 1:
                return S.PBind(path[0], pos=pos)
            return S.PVariant(path, args, pos=pos)
        if t.kind == "OP" and t.val == "(":
            self.i += 1
            elems = []
            while not self.at_op(")"):
                elems.append(self.parse_pattern())
                if not self.eat_op(","):
                    break
            self.expect_op(")")
            return S.PTuple(elems, pos=pos)
        # literal or range
        lo = self.parse_pattern_literal()
        if self.at_op("..") or self.at_op("..="):
            inclusive = self.tok.val == "..="
            self.i += 1
            hi = self.parse_pattern_literal()
            return S.PRange(lo, hi, inclusive, pos=pos)
        return S.PLit(lo, pos=pos)

    def parse_pattern_literal(self):
        t = self.tok
        pos = self.pos()
        neg = False
        if t.kind == "OP" and t.val == "-":
            neg = True
            self.i += 1
            t = self.tok
        if t.kind == "INT":
            self.i += 1
            return S.IntLit(-t.val if neg else t.val, pos=pos)
        if t.kind == "FLOAT":
            self.i += 1
            return S.FloatLit(-t.val if neg else t.val, pos=pos)
        if t.kind == "CHAR":
            self.i += 1
            return S.CharLit(t.val, pos=pos)
        if t.kind == "STR":
            self.i += 1
            return self.make_str(t, pos)
        if t.kind == "KW" and t.val in ("true", "false"):
            self.i += 1
            return S.BoolLit(t.val == "true", pos=pos)
        if t.kind == "KW" and t.val == "nil":
            self.i += 1
            return S.NilLit(pos=pos)
        self.error("expected a pattern (a value, a name, a range, or '_') but found %s" % self.describe(t))

    # ---- expressions -----------------------------------------------------------
    def parse_expr(self, min_prec=0):
        pos = self.pos()
        left = self.parse_range_or_prefix(min_prec)
        while True:
            t = self.tok
            if t.kind == "OP":
                op = t.val
            elif t.kind == "KW" and t.val in ("and", "or", "in", "as", "not"):
                op = t.val
            else:
                break
            if op == "not":
                # `a not in b`
                if self.peek().kind == "KW" and self.peek().val == "in":
                    info = BINARY_PREC["in"]
                    if info[0] < min_prec:
                        break
                    self.i += 2
                    rhs = self.parse_expr(info[0] + 1)
                    left = S.Unary("not", S.Binary("in", left, rhs, pos=pos), pos=pos)
                    continue
                break
            info = BINARY_PREC.get(op)
            if info is None:
                break
            prec, assoc = info
            if prec < min_prec:
                break
            opos = self.pos()
            self.i += 1
            if op == "as":
                ty = self.parse_type()
                left = S.Cast(left, ty, pos=opos)
                continue
            self.skip_nl()
            rhs = self.parse_expr(prec if assoc == "R" else prec + 1)
            if op == "??":
                left = S.Coalesce(left, rhs, pos=opos)
            elif op in ("and", "&&"):
                left = S.Binary("and", left, rhs, pos=opos)
            elif op in ("or", "||"):
                left = S.Binary("or", left, rhs, pos=opos)
            else:
                left = S.Binary(op, left, rhs, pos=opos)
        if min_prec <= 1 and (self.at_op("..") or self.at_op("..=")):
            inclusive = self.tok.val == "..="
            self.i += 1
            hi = None
            if self.starts_expr():
                hi = self.parse_expr(2)
            step = None
            if self.eat_kw("step"):
                step = self.parse_expr(2)
            return S.Range(left, hi, inclusive, step, pos=pos)
        return left

    def starts_expr(self):
        t = self.tok
        if t.kind in ("INT", "FLOAT", "STR", "CHAR", "IDENT"):
            return True
        if t.kind == "KW":
            return t.val in ("true", "false", "nil", "not", "fn", "if", "match")
        if t.kind == "OP":
            if t.val == "{":
                return not self.no_struct
            return t.val in ("(", "[", "-", "~", "!", "|", "||")
        return False

    def parse_range_or_prefix(self, min_prec):
        pos = self.pos()
        if min_prec <= 1 and (self.at_op("..") or self.at_op("..=")):
            inclusive = self.tok.val == "..="
            self.i += 1
            hi = None
            if self.starts_expr():
                hi = self.parse_expr(2)
            step = None
            if self.eat_kw("step"):
                step = self.parse_expr(2)
            return S.Range(None, hi, inclusive, step, pos=pos)
        return self.parse_unary(min_prec)

    def parse_unary(self, min_prec):
        t = self.tok
        pos = self.pos()
        if t.kind == "OP":
            if t.val == "-":
                self.i += 1
                e = self.parse_expr(PREC_UNARY)
                if isinstance(e, S.IntLit):
                    return S.IntLit(-e.value, pos=pos)
                if isinstance(e, S.FloatLit):
                    return S.FloatLit(-e.value, pos=pos)
                return S.Unary("-", e, pos=pos)
            if t.val == "+":
                self.i += 1
                return self.parse_expr(PREC_UNARY)
            if t.val == "!":
                self.i += 1
                return S.Unary("not", self.parse_expr(PREC_UNARY), pos=pos)
            if t.val == "~":
                self.i += 1
                return S.Unary("~", self.parse_expr(PREC_UNARY), pos=pos)
        elif t.kind == "KW" and t.val == "not":
            self.i += 1
            return S.Unary("not", self.parse_expr(6), pos=pos)
        return self.parse_postfix()

    def parse_postfix(self):
        e = self.parse_primary()
        while True:
            t = self.tok
            if t.kind != "OP":
                break
            v = t.val
            pos = self.pos()
            if v == "(":
                self.i += 1
                args = self.parse_args()
                e = S.Call(e, args, pos=pos)
            elif v == "[":
                self.i += 1
                saved = self.no_struct
                self.no_struct = False
                self.skip_nl()
                idx = self.parse_expr()
                self.skip_nl()
                self.no_struct = saved
                self.expect_op("]")
                e = S.Index(e, idx, pos=pos)
            elif v == ".":
                self.i += 1
                nt = self.tok
                if nt.kind == "IDENT":
                    self.i += 1
                    e = S.Field(e, nt.val, pos=self.pos(nt))
                elif nt.kind == "INT":
                    self.i += 1
                    e = S.Field(e, nt.val, pos=self.pos(nt))
                else:
                    self.error("expected a field or method name after '.' but found %s" % self.describe(nt))
            elif v == "!" and not t.space_before:
                self.i += 1
                e = S.Unwrap(e, pos=pos)
            elif v == "?" and not t.space_before:
                self.i += 1
                e = S.Try(e, pos=pos)
            else:
                break
        return e

    def parse_args(self):
        args = []
        saved = self.no_struct
        self.no_struct = False
        self.skip_nl()
        while not self.at_op(")"):
            if self.tok.kind == "IDENT" and self.peek().kind == "OP" and self.peek().val == ":" and not self.peek().space_before:
                npos = self.pos()
                name = self.tok.val
                self.i += 2
                self.skip_nl()
                args.append(S.NamedArg(name, self.parse_expr(), pos=npos))
            else:
                args.append(self.parse_expr())
            self.skip_nl()
            if not self.eat_op(","):
                break
            self.skip_nl()
        self.no_struct = saved
        self.skip_nl()
        self.expect_op(")", "to close the call")
        return args

    def make_str(self, t, pos):
        parts = []
        for p in t.val:
            if isinstance(p, bytes):
                parts.append(p)
            else:
                toks = tokenize(p.src, self.file)
                for tk in toks:
                    if tk.line == 1:
                        tk.col += p.col - 1
                    tk.line += p.line - 1
                sub = Parser(toks, self.file)
                if sub.tok.kind == "NEWLINE" and sub.peek().kind == "EOF":
                    raise CompileError("empty {} in string (write \\{ for a literal brace)", Pos(self.file, p.line, p.col))
                e = sub.parse_expr()
                while sub.tok.kind == "NEWLINE":
                    sub.i += 1
                if sub.tok.kind != "EOF":
                    sub.error("unexpected %s inside string interpolation" % sub.describe(sub.tok))
                parts.append((e, p.spec))
        return S.StrLit(parts, pos=pos)

    def parse_primary(self):
        t = self.tok
        pos = self.pos()
        k = t.kind
        if k == "INT":
            self.i += 1
            return S.IntLit(t.val, pos=pos)
        if k == "FLOAT":
            self.i += 1
            return S.FloatLit(t.val, pos=pos)
        if k == "STR":
            self.i += 1
            return self.make_str(t, pos)
        if k == "CHAR":
            self.i += 1
            return S.CharLit(t.val, pos=pos)
        if k == "IDENT":
            self.i += 1
            targs = None
            if self.at_op("::") and self.peek().kind == "OP" and self.peek().val == "<":
                self.i += 2
                targs = []
                while True:
                    targs.append(self.parse_type())
                    if not self.eat_op(","):
                        break
                self.expect_gt()
            if (not self.no_struct and self.at_op("{") and t.val[0].isupper() and self.looks_like_struct_lit()):
                return self.parse_struct_lit(t, pos, targs)
            return S.Ident(t.val, targs, pos=pos)
        if k == "KW":
            v = t.val
            if v == "true" or v == "false":
                self.i += 1
                return S.BoolLit(v == "true", pos=pos)
            if v == "nil":
                self.i += 1
                return S.NilLit(pos=pos)
            if v == "if":
                return self.parse_if(S.IfExpr)
            if v == "match":
                return self.parse_match(S.MatchExpr)
            if v == "fn":
                f = self.parse_fn(anonymous=True)
                return S.Lambda([(p.name, p.type) for p in f.params], f.ret, f.body, pos=pos)
            if v == "unsafe":
                self.i += 1
                return S.BlockExpr(self.parse_block(), pos=pos)
        if k == "OP":
            v = t.val
            if v == "(":
                self.i += 1
                saved = self.no_struct
                self.no_struct = False
                self.skip_nl()
                if self.at_op(")"):
                    self.i += 1
                    self.no_struct = saved
                    return S.TupleLit([], pos=pos)
                e = self.parse_expr()
                self.skip_nl()
                if self.at_op(","):
                    elems = [e]
                    while self.eat_op(","):
                        self.skip_nl()
                        if self.at_op(")"):
                            break
                        elems.append(self.parse_expr())
                        self.skip_nl()
                    self.no_struct = saved
                    self.expect_op(")")
                    return S.TupleLit(elems, pos=pos)
                self.no_struct = saved
                self.expect_op(")", "to close this '('")
                return e
            if v == "[":
                self.i += 1
                saved = self.no_struct
                self.no_struct = False
                self.skip_nl()
                elems = []
                while not self.at_op("]"):
                    elems.append(self.parse_expr())
                    self.skip_nl()
                    if len(elems) == 1 and self.at_kw("for"):
                        return self.parse_comprehension(elems[0], pos, saved)
                    if not self.eat_op(","):
                        break
                    self.skip_nl()
                self.no_struct = saved
                self.skip_nl()
                self.expect_op("]", "to close this '['")
                return S.ArrayLit(elems, pos=pos)
            if v == "{":
                self.i += 1
                saved = self.no_struct
                self.no_struct = False
                self.skip_nl()
                pairs = []
                while not self.at_op("}"):
                    kx = self.parse_expr()
                    self.skip_nl()
                    self.expect_op(":", "between key and value")
                    self.skip_nl()
                    vx = self.parse_expr()
                    pairs.append((kx, vx))
                    self.skip_nl()
                    if not self.eat_op(","):
                        break
                    self.skip_nl()
                self.no_struct = saved
                self.skip_nl()
                self.expect_op("}")
                return S.MapLit(pairs, pos=pos)
            if v == "|" or v == "||":
                self.i += 1
                params = []
                if v == "|":
                    while not self.at_op("|"):
                        n = self.expect_ident("a parameter name").val
                        ty = None
                        if self.eat_op(":"):
                            ty = self.parse_type()
                        params.append((n, ty))
                        if not self.eat_op(","):
                            break
                    self.expect_op("|")
                ret = None
                if self.eat_op("->"):
                    ret = self.parse_type()
                    body = self.parse_block()
                elif self.at_op("{"):
                    body = self.parse_block()
                else:
                    saved = self.no_struct
                    e = self.parse_expr(1)
                    self.no_struct = saved
                    body = S.Block([S.Return(e, pos=e.pos)], pos=e.pos)
                return S.Lambda(params, ret, body, pos=pos)
        self.error("expected an expression but found %s" % self.describe(t))

    def parse_comprehension(self, elem, pos, saved):
        # [expr for x in iter if cond]
        self.expect_kw("for")
        names = []
        while True:
            names.append(self.expect_ident("a loop variable").val)
            if not self.eat_op(","):
                break
        self.expect_kw("in")
        self.no_struct = True
        it = self.parse_expr()
        cond = None
        if self.eat_kw("if"):
            cond = self.parse_expr()
        self.no_struct = saved
        self.skip_nl()
        self.expect_op("]")
        return S.Call(S.Ident("__comprehension", None, pos=pos), [elem, S.TupleLit([S.StrLit([n.encode()], pos=pos) for n in names], pos=pos), it,
                                                                  cond if cond is not None else S.NilLit(pos=pos)], pos=pos)

    def looks_like_struct_lit(self):
        # self.tok is '{'
        j = self.i + 1
        toks = self.toks
        while toks[j].kind == "NEWLINE":
            j += 1
        t = toks[j]
        if t.kind == "OP" and t.val == "}":
            return True
        if t.kind == "IDENT":
            n = toks[j + 1]
            return n.kind == "OP" and n.val in (":", ",", "}")
        if t.kind == "NEWLINE":
            return False
        return False

    def parse_struct_lit(self, t, pos, targs):
        self.expect_op("{")
        self.skip_nl()
        fields = []
        saved = self.no_struct
        self.no_struct = False
        while not self.at_op("}"):
            fname = self.expect_ident("a field name")
            if self.eat_op(":"):
                self.skip_nl()
                val = self.parse_expr()
            else:
                val = S.Ident(fname.val, None, pos=self.pos(fname))
            fields.append((fname.val, val, self.pos(fname)))
            self.skip_nl()
            if not self.eat_op(","):
                break
            self.skip_nl()
        self.no_struct = saved
        self.skip_nl()
        self.expect_op("}")
        return S.StructLit(S.Ident(t.val, targs, pos=pos), fields, pos=pos)


def parse_source(src, file):
    toks = tokenize(src, file)
    return Parser(toks, file).parse_program()
