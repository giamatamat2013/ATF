"""Expression checking."""
import re

from . import syntax as S
from . import tir as T
from .errors import CompileError, SilentError
from .semtypes import *

END_SENTINEL = 0x7FFFFFFFFFFFFFFF
M64 = (1 << 64) - 1

ARITH_METHODS = {">>>": "op_ushr", "+": "op_add", "-": "op_sub", "*": "op_mul", "/": "op_div", "%": "op_mod", "**": "op_pow",
                 "&": "op_and", "|": "op_or", "^": "op_xor", "<<": "op_shl", ">>": "op_shr"}
INT_BIN = {"+": "add", "-": "sub", "*": "mul", "/": "div", "%": "mod", "&": "and", "|": "or", "^": "xor",
           "<<": "shl", ">>": "shr", ">>>": "ushr"}
FLT_BIN = {"+": "fadd", "-": "fsub", "*": "fmul", "/": "fdiv"}
CMP_NAMES = {"<": "lt", "<=": "le", ">": "gt", ">=": "ge", "==": "eq", "!=": "ne"}


def wrap64(v):
    v &= M64
    return v - (1 << 64) if v >> 63 else v


def is_texpr(e):
    return hasattr(e, "ty") and not hasattr(e, "_syntax")


class ExprMixin:
    # ------------------------------------------------------------------ dispatch
    def ce(self, e, expected=None):
        if hasattr(e, "ty"):
            return e
        m = getattr(self, "x_" + e.__class__.__name__, None)
        if m is None:
            raise CompileError("this kind of expression is not supported here (%s)" % e.__class__.__name__, e.pos)
        return m(e, expected)

    def ce_as(self, e, ty, what=None):
        """check an expression and coerce it to `ty`"""
        te = self.ce(e, ty)
        return self.coerce(te, ty, e.pos if hasattr(e, "pos") else None)

    def ce_value(self, e, expected=None):
        te = self.ce(e, expected)
        if te.ty == TVoid:
            raise CompileError("this expression does not produce a value", e.pos)
        return te

    # ------------------------------------------------------------------ coercion
    def mismatch(self, found, expected, pos, extra=None):
        hint = extra
        if hint is None:
            if expected == TInt and found == TFloat:
                hint = "use int(x) to convert a float to an int"
            elif expected == TStr and found in (TInt, TFloat, TBool, TByte):
                hint = "use str(x) to convert it to text"
            elif expected in (TInt, TFloat) and found == TStr:
                hint = "use int(s) or float(s) to convert text to a number"
            elif isinstance(found, TOpt) and found.inner == expected:
                hint = "this value may be nil: use  x!  to unwrap it, or  x ?? default"
            elif expected == TBool and found in (TInt, TByte):
                hint = "conditions must be true/false, e.g.  x != 0"
        raise CompileError("type mismatch: expected %s but found %s" % (expected, found), pos, hint)

    def try_coerce(self, e, target):
        t = e.ty
        if t == target:
            return e
        if t == TNever:
            return e
        if target == TFloat and t in (TInt, TByte):
            if isinstance(e, T.Const) and e.kind == "int":
                return T.Const("float", float(e.value), ty=TFloat, pos=e.pos)
            return T.Cvt("i2f", e, ty=TFloat, pos=e.pos)
        if target == TInt and t == TByte:
            if isinstance(e, T.Const):
                return T.Const("int", e.value, ty=TInt, pos=e.pos)
            return T.Cvt("nop", e, ty=TInt, pos=e.pos)
        if target == TByte and t == TInt and isinstance(e, T.Const) and e.kind == "int" and 0 <= e.value < 256:
            return T.Const("int", e.value, ty=TByte, pos=e.pos)
        if isinstance(target, TOpt):
            if t == TNil:
                return T.Const("nil", 0, ty=target, pos=e.pos)
            if isinstance(t, TOpt):
                return None
            inner = self.try_coerce(e, target.inner)
            if inner is None:
                return None
            return self.wrap_opt(inner, target)
        if isinstance(target, TPtr) and t == TNil:
            return T.Const("nil", 0, ty=target, pos=e.pos)
        if t == TNil and target == TNil:
            return e
        return None

    def coerce(self, e, target, pos=None, extra=None):
        r = self.try_coerce(e, target)
        if r is None:
            self.mismatch(e.ty, target, pos or e.pos, extra)
        return r

    def join(self, a, b, pos):
        """common type of two typed expressions (for if/match branches); returns (a', b')"""
        if a.ty == TNever:
            return a, b
        if b.ty == TNever:
            return a, b
        r = self.try_coerce(b, a.ty)
        if r is not None:
            return a, r
        r = self.try_coerce(a, b.ty)
        if r is not None:
            return r, b
        raise CompileError("the branches have different types: %s and %s" % (a.ty, b.ty), pos)

    def wrap_opt(self, e, opt):
        if self.is_value_type(opt.inner):
            return T.NewObj([e], ty=opt, pos=e.pos)
        return T.Cvt("nop", e, ty=opt, pos=e.pos)

    def unwrap_opt(self, e):
        inner = e.ty.inner
        if self.is_value_type(inner):
            return T.Load(e, 0, ty=inner, pos=e.pos)
        return T.Cvt("nop", e, ty=inner, pos=e.pos)

    def is_simple(self, e):
        return isinstance(e, (T.Const, T.VarRef, T.GlobalRef)) and not (isinstance(e, T.VarRef) and e.var.boxed)

    def bind_tmp(self, e, stmts, name="$t"):
        """returns a simple expression equal to e (adding a Decl to stmts if needed)"""
        if self.is_simple(e):
            return e
        v = self.new_tmp(e.ty, name)
        stmts.append(T.Decl(v, e, pos=e.pos))
        return T.VarRef(v, ty=e.ty, pos=e.pos)

    # ------------------------------------------------------------------ variables
    def lookup_var(self, name, ctx=None):
        ctx = ctx or self.cx
        for sc in reversed(ctx.scopes):
            v = sc.get(name)
            if v is not None:
                return v
        if ctx.parent is not None:
            outer = self.lookup_var(name, ctx.parent)
            if outer is None:
                return None
            inner = ctx.inst.capture_inner.get(outer)
            if inner is None:
                inner = T.Var(name, outer.ty, outer.mutable, pos=outer.pos)
                inner.root = outer.root
                outer.root.captured = True
                ctx.inst.captures.append(outer)
                ctx.inst.capture_inner[outer] = inner
                ctx.inst.vars.append(inner)
            return inner
        return None

    def declare_var(self, name, ty, mutable, pos, check_shadow=True):
        v = T.Var(name, ty, mutable, pos=pos)
        self.cx.inst.vars.append(v)
        self.cx.scopes[-1][name] = v
        return v

    def visible_names(self):
        names = set()
        c = self.cx
        while c is not None:
            for sc in c.scopes:
                names.update(sc.keys())
            c = c.parent
        names.update(self.fns.keys())
        names.update(self.consts.keys())
        names.update(self.globals.keys())
        names.update(n for n, f in self.fns.items() if not n.startswith("__"))
        return names

    # ------------------------------------------------------------------ literals
    def x_IntLit(self, e, expected=None):
        v = e.value
        if v >= 1 << 63:
            if v >= 1 << 64:
                raise CompileError("integer literal is too large", e.pos)
            v = wrap64(v)
        if expected == TFloat:
            return T.Const("float", float(v), ty=TFloat, pos=e.pos)
        if expected == TByte and 0 <= v < 256:
            return T.Const("int", v, ty=TByte, pos=e.pos)
        return T.Const("int", v, ty=TInt, pos=e.pos)

    def x_FloatLit(self, e, expected=None):
        return T.Const("float", e.value, ty=TFloat, pos=e.pos)

    def x_BoolLit(self, e, expected=None):
        return T.Const("bool", 1 if e.value else 0, ty=TBool, pos=e.pos)

    def x_NilLit(self, e, expected=None):
        if isinstance(expected, (TOpt, TPtr)):
            return T.Const("nil", 0, ty=expected, pos=e.pos)
        return T.Const("nil", 0, ty=TNil, pos=e.pos)

    def x_CharLit(self, e, expected=None):
        if e.value < 256:
            return T.Const("int", e.value, ty=TByte, pos=e.pos)
        return T.Const("int", e.value, ty=TInt, pos=e.pos)

    def x_StrLit(self, e, expected=None):
        parts = []
        for p in e.parts:
            if isinstance(p, bytes):
                if p:
                    if parts and isinstance(parts[-1], T.Const):
                        parts[-1] = T.Const("str", parts[-1].value + p, ty=TStr, pos=e.pos)
                    else:
                        parts.append(T.Const("str", p, ty=TStr, pos=e.pos))
            else:
                ex, spec = p
                te = self.ce_value(ex)
                s = self.format_value(te, spec, ex.pos)
                if isinstance(s, T.Const) and parts and isinstance(parts[-1], T.Const):
                    parts[-1] = T.Const("str", parts[-1].value + s.value, ty=TStr, pos=e.pos)
                else:
                    parts.append(s)
        if not parts:
            return T.Const("str", b"", ty=TStr, pos=e.pos)
        r = parts[0]
        for p in parts[1:]:
            r = self.call_rt("str_concat", [r, p], pos=e.pos)
        return r

    _spec_re = re.compile(r"^([<>^])?(0)?(\d+)?(?:\.(\d+))?([fdxXbsc])?$")

    def format_value(self, te, spec, pos):
        if spec is None:
            return self.str_of(te)
        m = self._spec_re.match(spec)
        if not m:
            raise CompileError("bad format spec '{...:%s}'" % spec, pos, "examples: {x:.2f}  {n:5}  {s:<10}  {n:05}  {n:x}")
        align, zero, width, prec, kind = m.groups()
        if kind == "f" or (prec is not None and te.ty in (TFloat,)) or (prec is not None and kind is None):
            if te.ty not in (TFloat, TInt, TByte):
                raise CompileError("':.%sf' needs a number, found %s" % (prec or "", te.ty), pos)
            f = self.coerce(te, TFloat, pos)
            s = self.call_rt("fmt_fixed", [f, self.ci(int(prec) if prec else 6)])
        elif kind in ("x", "X", "b"):
            if te.ty not in (TInt, TByte):
                raise CompileError("':%s' needs an int, found %s" % (kind, te.ty), pos)
            i = self.coerce(te, TInt, pos)
            s = self.call_rt("int_to_hex" if kind == "x" else "int_to_HEX" if kind == "X" else "int_to_bin", [i])
        else:
            s = self.str_of(te)
        if width:
            w = self.ci(int(width))
            if zero and align is None and te.ty in (TInt, TFloat, TByte):
                s = self.call_rt("pad_zero", [s, w])
            elif align == "<":
                s = self.call_rt("pad_right", [s, w])
            elif align == "^":
                s = self.call_rt("pad_center", [s, w])
            else:
                # default: numbers right aligned, text left aligned
                if align is None and te.ty == TStr and kind != "s":
                    s = self.call_rt("pad_right", [s, w])
                else:
                    s = self.call_rt("pad_left", [s, w])
        return s

    # ------------------------------------------------------------------ names
    def x_Ident(self, e, expected=None):
        name = e.name
        v = self.lookup_var(name)
        if v is not None:
            self.touch(v)
            return T.VarRef(v, ty=v.ty, pos=e.pos)
        ci = self.consts.get(name)
        if ci is not None:
            self.resolve_const(ci)
            val = ci.value
            if isinstance(val, T.Const):
                return T.Const(val.kind, val.value, ty=val.ty, pos=e.pos)
            return T.GlobalRef(val.glob, ty=val.ty, pos=e.pos)
        gi = self.globals.get(name)
        if gi is not None:
            g = self.resolve_global(gi)
            return T.GlobalRef(g, ty=g.ty, pos=e.pos)
        fi = self.fns.get(name)
        if fi is not None:
            return self.fn_value(fi, e, expected)
        if name in self.structs or name in self.enums or name in PRIMS:
            raise CompileError("'%s' is a type, not a value" % name, e.pos,
                               "to create one use  %s(...)  or  %s{ field: value }" % (name, name) if name in self.structs else None)
        from .checker import suggest
        if name in self.failed_names:
            raise SilentError("follow-up error", e.pos)
        raise CompileError("unknown name '%s'" % name, e.pos, suggest(name, self.visible_names()))

    def fn_value(self, fi, e, expected):
        """use of a top-level function as a value (closure object)"""
        if fi.is_generic:
            if isinstance(expected, TFunc):
                gp, gr = self.generic_sig(fi)
                binds = {}
                ok = len(gp) == len(expected.params) and all(unify(p, a, binds) for p, a in zip(gp, expected.params))
                ok = ok and unify(gr, expected.ret, binds)
                if ok and all(tp.key() in binds for tp in fi.tp_objs):
                    inst = self.get_inst(fi, [binds[tp.key()] for tp in fi.tp_objs])
                else:
                    raise CompileError("cannot infer the type parameters of '%s' here" % fi.name, e.pos)
            else:
                raise CompileError("generic function '%s' needs concrete types to be used as a value" % fi.name, e.pos,
                                   "call it, or give it an expected function type")
        else:
            inst = self.get_inst(fi, [])
        self.cx.inst.callees.add(inst)
        return T.FnRef(inst, ty=TFunc([p.ty for p in inst.params], inst.ret), pos=e.pos)

    # ------------------------------------------------------------------ operators
    def x_Unary(self, e, expected=None):
        op = e.op
        x = self.ce_value(e.expr, expected if op == "-" else None)
        t = x.ty
        if op == "-":
            if isinstance(x, T.Const) and x.kind in ("int", "float"):
                return T.Const(x.kind, wrap64(-x.value) if x.kind == "int" else -x.value, ty=TInt if t == TByte else t, pos=e.pos)
            if t == TFloat:
                return T.Un("fneg", x, ty=TFloat, pos=e.pos)
            if t in (TInt, TByte):
                return T.Un("neg", self.coerce(x, TInt), ty=TInt, pos=e.pos)
            return self.user_unary(x, "op_neg", e)
        if op == "not":
            if t != TBool:
                raise CompileError("'not' needs a true/false value, found %s" % t, e.pos,
                                   "to test for nil use  x == nil" if isinstance(t, TOpt) else None)
            if isinstance(x, T.Const):
                return T.Const("bool", 1 - x.value, ty=TBool, pos=e.pos)
            return T.Un("not", x, ty=TBool, pos=e.pos)
        if op == "~":
            if t not in (TInt, TByte):
                raise CompileError("'~' needs an int, found %s" % t, e.pos)
            return T.Un("bnot", self.coerce(x, TInt), ty=TInt, pos=e.pos)
        raise CompileError("unknown operator " + op, e.pos)

    def user_unary(self, x, mname, e):
        r = self.try_method(x, mname, [], e.pos)
        if r is None:
            raise CompileError("cannot apply '%s' to %s" % (e.op, x.ty), e.pos,
                               "define  fn %s(self) -> ...  in an impl block to support it" % mname)
        return r

    def num_unify(self, l, r):
        lt, rt = l.ty, r.ty
        if lt == rt and lt != TByte:
            return l, r
        if lt == TFloat or rt == TFloat:
            return self.coerce(l, TFloat), self.coerce(r, TFloat)
        return self.coerce(l, TInt), self.coerce(r, TInt)

    def fold_int(self, op, a, b):
        if op == "+":
            return wrap64(a + b)
        if op == "-":
            return wrap64(a - b)
        if op == "*":
            return wrap64(a * b)
        if op == "&":
            return a & b
        if op == "|":
            return a | b
        if op == "^":
            return a ^ b
        if op == "<<" and 0 <= b < 64:
            return wrap64(a << b)
        if op == ">>" and 0 <= b < 64:
            return a >> b
        if op == ">>>" and 0 <= b < 64:
            return wrap64((a & M64) >> b)
        if op == "/" and b != 0 and not (a == -(1 << 63) and b == -1):
            q = abs(a) // abs(b)
            return q if (a < 0) == (b < 0) else -q
        if op == "%" and b != 0 and not (a == -(1 << 63) and b == -1):
            q = abs(a) % abs(b)
            return q if a >= 0 else -q
        return None

    def x_Binary(self, e, expected=None):
        op = e.op
        pos = e.pos
        if op == "and" or op == "or":
            l = self.ce_as(e.left, TBool)
            r = self.ce_as(e.right, TBool)
            if isinstance(l, T.Const) and isinstance(r, T.Const):
                v = (l.value and r.value) if op == "and" else (l.value or r.value)
                return T.Const("bool", 1 if v else 0, ty=TBool, pos=pos)
            return (T.And if op == "and" else T.Or)(l, r, ty=TBool, pos=pos)
        if op == "in":
            return self.check_in(e)
        hint = expected if op in ("+", "-", "*", "/", "%") and expected in (TInt, TFloat) else None
        l = self.ce_value(e.left, hint)
        r = self.ce_value(e.right, l.ty if l.ty in (TInt, TFloat, TStr) else None)
        return self.binop(op, l, r, pos)

    def binop(self, op, l, r, pos):
        lt, rt = l.ty, r.ty
        if op in CMP_NAMES:
            return self.compare(op, l, r, pos)
        # strings
        if lt == TStr and op == "+":
            if rt != TStr:
                raise CompileError("cannot add str and %s" % rt, pos,
                                   'use string interpolation "{x}" or str(x) to join text with other values')
            if isinstance(l, T.Const) and isinstance(r, T.Const):
                return T.Const("str", l.value + r.value, ty=TStr, pos=pos)
            return self.call_rt("str_concat", [l, r], pos=pos)
        if lt == TStr and op == "*" and rt in (TInt, TByte):
            return self.call_rt("str_repeat", [l, self.coerce(r, TInt)], pos=pos)
        # pointer arithmetic
        if isinstance(lt, TPtr):
            if op in ("+", "-") and rt in (TInt, TByte):
                r = self.coerce(r, TInt)
                es = self.esize(lt.elem)
                off = r if es == 1 else T.Bin("mul", r, self.ci(es), ty=TInt)
                return T.Bin(INT_BIN[op], l, off, ty=lt, pos=pos)
            if op == "-" and rt == lt:
                d = T.Bin("sub", l, r, ty=TInt, pos=pos)
                es = self.esize(lt.elem)
                return d if es == 1 else T.Bin("div", d, self.ci(es), ty=TInt, pos=pos)
            raise CompileError("invalid pointer operation: %s %s %s" % (lt, op, rt), pos)
        if is_numeric(lt) and is_numeric(rt):
            return self.arith(op, l, r, pos)
        # user-defined operators
        mname = ARITH_METHODS.get(op)
        if mname:
            r_ = self.try_method(l, mname, [r], pos) if not is_numeric(lt) else None
            if r_ is not None:
                return r_
        raise CompileError("cannot apply '%s' to %s and %s" % (op, lt, rt), pos,
                           ("define  fn %s(self, other: %s) -> ...  in an impl block to support it" % (mname, rt)) if mname and isinstance(lt, (TStruct, TEnum)) else None)

    def arith(self, op, l, r, pos):
        if op == "**":
            if l.ty == TFloat or r.ty == TFloat:
                l, r = self.coerce(l, TFloat), self.coerce(r, TFloat)
                return self.call_extern("pow", [l, r], pos)
            return self.call_rt("int_pow", [self.coerce(l, TInt), self.coerce(r, TInt)], pos=pos)
        l, r = self.num_unify(l, r)
        t = l.ty
        if t == TFloat:
            if op in FLT_BIN:
                if isinstance(l, T.Const) and isinstance(r, T.Const) and not (op == "/" and r.value == 0):
                    a, b = l.value, r.value
                    v = a + b if op == "+" else a - b if op == "-" else a * b if op == "*" else a / b
                    return T.Const("float", v, ty=TFloat, pos=pos)
                return T.Bin(FLT_BIN[op], l, r, ty=TFloat, pos=pos)
            if op == "%":
                return self.call_extern("fmod", [l, r], pos)
            raise CompileError("operator '%s' does not work on floats" % op, pos)
        if op not in INT_BIN:
            raise CompileError("operator '%s' does not work on ints" % op, pos)
        if isinstance(l, T.Const) and isinstance(r, T.Const):
            v = self.fold_int(op, l.value, r.value)
            if v is not None:
                return T.Const("int", v, ty=TInt, pos=pos)
        if op in ("/", "%") and isinstance(r, T.Const) and r.value == 0:
            raise CompileError("division by zero", pos)
        return T.Bin(INT_BIN[op], l, r, ty=TInt, pos=pos)

    def compare(self, op, l, r, pos):
        lt, rt = l.ty, r.ty
        cn = CMP_NAMES[op]
        # nil comparisons
        if rt == TNil or lt == TNil:
            if op not in ("==", "!="):
                raise CompileError("nil can only be compared with == or !=", pos)
            x, y = (l, r) if rt == TNil else (r, l)
            if not isinstance(x.ty, (TOpt, TPtr)):
                raise CompileError("%s can never be nil" % x.ty, pos,
                                   "only optional types like  %s?  can be nil" % x.ty)
            return T.Bin(cn, x, T.Const("nil", 0, ty=x.ty), ty=TBool, pos=pos)
        if is_numeric(lt) and is_numeric(rt):
            l, r = self.num_unify(l, r)
            if l.ty == TFloat:
                if isinstance(l, T.Const) and isinstance(r, T.Const):
                    return T.Const("bool", int(self.pyop(op, l.value, r.value)), ty=TBool, pos=pos)
                return T.Bin("f" + cn, l, r, ty=TBool, pos=pos)
            if isinstance(l, T.Const) and isinstance(r, T.Const):
                return T.Const("bool", int(self.pyop(op, l.value, r.value)), ty=TBool, pos=pos)
            return T.Bin(cn, l, r, ty=TBool, pos=pos)
        if isinstance(lt, TOpt) and not isinstance(rt, TOpt):
            rr = self.try_coerce(r, lt)
            if rr is not None:
                r = rr
                rt = r.ty
        elif isinstance(rt, TOpt) and not isinstance(lt, TOpt):
            ll = self.try_coerce(l, rt)
            if ll is not None:
                l = ll
                lt = l.ty
        if lt != rt:
            raise CompileError("cannot compare %s with %s" % (lt, rt), pos)
        if op in ("==", "!="):
            eq = self.eq_expr(l, r, pos)
            if op == "!=":
                if isinstance(eq, T.Const):
                    return T.Const("bool", 1 - eq.value, ty=TBool, pos=pos)
                return T.Un("not", eq, ty=TBool, pos=pos)
            return eq
        c = self.cmp_expr(l, r, pos)       # int: <0 / 0 / >0
        return T.Bin(cn, c, self.ci(0), ty=TBool, pos=pos)

    def pyop(self, op, a, b):
        return {"<": a < b, "<=": a <= b, ">": a > b, ">=": a >= b, "==": a == b, "!=": a != b}[op]

    def check_in(self, e):
        pos = e.pos
        if isinstance(e.right, S.Range):
            rg = e.right
            x = self.ce_value(e.left)
            lo = self.ce_value(rg.lo) if rg.lo is not None else None
            hi = self.ce_value(rg.hi) if rg.hi is not None else None
            stmts = []
            xs = self.bind_tmp(x, stmts)
            conds = []
            if lo is not None:
                conds.append(self.compare(">=", xs, lo, pos))
            if hi is not None:
                conds.append(self.compare("<=" if rg.inclusive else "<", xs, hi, pos))
            if not conds:
                return T.Const("bool", 1, ty=TBool, pos=pos)
            c = conds[0]
            for c2 in conds[1:]:
                c = T.And(c, c2, ty=TBool, pos=pos)
            return T.Seq(stmts, c, ty=TBool, pos=pos) if stmts else c
        x = self.ce_value(e.left)
        c = self.ce_value(e.right)
        r = self.try_method(c, "op_contains", [x], pos)
        if r is None:
            raise CompileError("cannot use 'in' with %s" % c.ty, pos,
                               "'in' works with arrays, maps, strings and ranges (like  x in 1..10 )")
        return r

    # ------------------------------------------------------------------ fields / indexing
    def type_ident(self, e):
        """If e is a bare name that refers to a type (and is not shadowed by a value), return the Type-ish."""
        if not isinstance(e, S.Ident):
            return None
        n = e.name
        if self.lookup_var(n) is not None or n in self.consts or n in self.globals or n in self.fns:
            return None
        if n in self.enums or n in self.structs or n in PRIMS or n in self.aliases:
            return n
        return None

    def x_Field(self, e, expected=None):
        tn = self.type_ident(e.obj)
        if tn is not None:
            return self.static_member(tn, e, expected)
        obj = self.ce_value(e.obj)
        return self.field_of(obj, e.name, e.pos)

    def field_of(self, obj, name, pos):
        t = obj.ty
        if isinstance(t, TStruct):
            for i, (fname, fty) in enumerate(self.struct_fields(t)):
                if fname == name:
                    return T.Load(obj, i, ty=fty, pos=pos)
            names = [f for f, _ in self.struct_fields(t)]
            from .checker import suggest
            if self.find_methods(t, name):
                raise CompileError("'%s' is a method of %s; call it with parentheses: %s()" % (name, t, name), pos)
            raise CompileError("%s has no field '%s'" % (t, name), pos,
                               suggest(name, names) or ("fields: " + ", ".join(names) if names else None))
        if isinstance(t, TTuple) and isinstance(name, int):
            if name >= len(t.elems):
                raise CompileError("tuple %s has no element .%d" % (t, name), pos)
            return T.Load(obj, name, ty=t.elems[name], pos=pos)
        if isinstance(t, TOpt):
            raise CompileError("cannot use '.%s' on %s because it may be nil" % (name, t), pos,
                               "unwrap it first:  x!.%s   or   if let v = x { v.%s }" % (name, name))
        raise CompileError("%s has no field '%s'" % (t, name), pos)

    def static_member(self, tn, e, expected):
        name = e.name
        if tn in self.enums:
            info = self.enums[tn]
            et = self.enum_type_for(info, expected)
            if name in info.vindex:
                vi = info.vindex[name]
                return self.make_variant(et, vi, [], e.pos, bare=True)
        raise CompileError("'%s.%s' is not a value" % (tn, name), e.pos,
                           "static functions are called like  %s.%s(...)" % (tn, name))

    def enum_type_for(self, info, expected):
        if not info.tparams:
            return TEnum(info, [])
        if isinstance(expected, TEnum) and expected.info is info:
            return expected
        return None

    def make_variant(self, et, vi, args, pos, bare=False):
        info = et.info
        payload = self.variant_payload(et, vi)
        if len(args) != len(payload):
            if bare and payload:
                raise CompileError("%s.%s carries %d value(s): write %s.%s(...)" % (info.name, info.variants[vi][0], len(payload), info.name, info.variants[vi][0]), pos)
            raise CompileError("%s.%s takes %d value(s) but %d given" % (info.name, info.variants[vi][0], len(payload), len(args)), pos)
        if info.simple:
            return T.Const("int", info.tags[vi], ty=et, pos=pos)
        vals = [T.Const("int", vi, ty=TInt)] + [self.coerce(a, pt, pos) for a, pt in zip(args, payload)]
        return T.NewObj(vals, ty=et, pos=pos)

    def x_Index(self, e, expected=None):
        obj = self.ce_value(e.obj)
        t = obj.ty
        pos = e.pos
        if isinstance(e.index, S.Range):
            rg = e.index
            lo = self.ce_as(rg.lo, TInt) if rg.lo is not None else self.ci(0)
            if rg.hi is None:
                hi = self.ci(END_SENTINEL)
            else:
                hi = self.ce_as(rg.hi, TInt)
                if rg.inclusive:
                    hi = T.Bin("add", hi, self.ci(1), ty=TInt)
            r = self.try_method(obj, "op_slice", [lo, hi], pos)
            if r is None:
                raise CompileError("cannot slice %s" % t, pos)
            return r
        if isinstance(t, TStruct) and t.info is self.array_info:
            idx = self.ce_as(e.index, TInt)
            return T.ArrIdx(obj, idx, self.esize(t.args[0]), ty=t.args[0], pos=pos)
        if isinstance(t, TPtr):
            idx = self.ce_as(e.index, TInt)
            return T.PtrIdx(obj, idx, self.esize(t.elem), ty=t.elem, pos=pos)
        idx = self.ce_value(e.index)
        r = self.try_method(obj, "op_index", [idx], pos)
        if r is None:
            raise CompileError("%s cannot be indexed with [ ]" % t, pos,
                               "indexing works on arrays, strings and maps" if not isinstance(t, TOpt) else
                               "this value may be nil; unwrap it first with  x!")
        return r

    # ------------------------------------------------------------------ literals: containers
    def x_ArrayLit(self, e, expected=None):
        pos = e.pos
        if isinstance(expected, TOpt):
            expected = expected.inner
        elem = None
        if isinstance(expected, TStruct) and expected.info is self.array_info:
            elem = expected.args[0]
        items = []
        if elem is None:
            if not e.elems:
                raise CompileError("cannot tell the type of an empty array", pos,
                                   "add a type:  let a: [int] = []")
            first = self.ce_value(e.elems[0])
            items.append(first)
            elem = first.ty
            if elem == TNil:
                raise CompileError("cannot tell the element type from nil", pos)
            for x in e.elems[1:]:
                te = self.ce_value(x, elem)
                items.append(te)
                r = self.try_coerce(te, elem)
                if r is None:
                    # widen numeric (e.g. [1, 2.5])
                    if elem in (TInt, TByte) and te.ty == TFloat:
                        elem = TFloat
                    elif elem == TByte and te.ty == TInt:
                        elem = TInt
                    elif isinstance(elem, TOpt) is False and te.ty == TNil:
                        elem = TOpt(elem)
                    else:
                        raise CompileError("array elements must all have the same type: found %s and %s" % (elem, te.ty), x.pos)
            items = [self.coerce(i, elem) for i in items]
        else:
            items = [self.ce_as(x, elem) for x in e.elems]
        aty = TStruct(self.array_info, [elem])
        return self.build_array(items, aty, pos)

    def build_array(self, items, aty, pos):
        elem = aty.args[0]
        n = len(items)
        tmp = self.new_tmp(aty, "$arr")
        stmts = [T.Decl(tmp, self.call_rt("array_raw", [self.ci(n)], targs=[elem], pos=pos), pos=pos)]
        if n:
            data = self.new_tmp(TPtr(elem), "$data")
            stmts.append(T.Decl(data, T.Load(T.VarRef(tmp, ty=aty), 0, ty=TPtr(elem)), pos=pos))
            es = self.esize(elem)
            for i, it in enumerate(items):
                stmts.append(T.Set(T.PtrIdx(T.VarRef(data, ty=TPtr(elem)), self.ci(i), es, ty=elem), it, pos=pos))
        return T.Seq(stmts, T.VarRef(tmp, ty=aty), ty=aty, pos=pos)

    def x_MapLit(self, e, expected=None):
        pos = e.pos
        if isinstance(expected, TOpt):
            expected = expected.inner
        k = v = None
        if isinstance(expected, TStruct) and expected.info is self.map_info:
            k, v = expected.args
        elif not e.pairs:
            raise CompileError("cannot tell the type of an empty map", pos, "add a type:  let m: {str: int} = {}")
        else:
            k0 = self.ce_value(e.pairs[0][0])
            v0 = self.ce_value(e.pairs[0][1])
            k, v = k0.ty, v0.ty
        mty = TStruct(self.map_info, [k, v])
        tmp = self.new_tmp(mty, "$map")
        stmts = [T.Decl(tmp, self.call_rt("map_new", [], targs=[k, v], pos=pos), pos=pos)]
        for kx, vx in e.pairs:
            kt = self.ce_as(kx, k)
            vt = self.ce_as(vx, v)
            r = self.try_method(T.VarRef(tmp, ty=mty), "set", [kt, vt], pos)
            stmts.append(T.ExprS(r))
        return T.Seq(stmts, T.VarRef(tmp, ty=mty), ty=mty, pos=pos)

    def x_TupleLit(self, e, expected=None):
        if isinstance(expected, TOpt):
            expected = expected.inner
        if not e.elems:
            raise CompileError("the empty tuple () is not a value; use  void  functions without a return value", e.pos)
        hints = expected.elems if isinstance(expected, TTuple) and len(expected.elems) == len(e.elems) else [None] * len(e.elems)
        vals = [self.ce_value(x, h) for x, h in zip(e.elems, hints)]
        if isinstance(expected, TTuple) and len(expected.elems) == len(vals):
            vals = [self.coerce(v, h) for v, h in zip(vals, expected.elems)]
            ty = expected
        else:
            ty = TTuple([v.ty for v in vals])
        return T.NewObj(vals, ty=ty, pos=e.pos)

    # ------------------------------------------------------------------ if / block / cast
    def x_BlockExpr(self, e, expected=None):
        stmts, val = self.check_value_block(e.block, expected)
        if val is None:
            raise CompileError("this block does not end with a value", e.pos)
        return T.Seq(stmts, val, ty=val.ty, pos=e.pos)

    def x_IfExpr(self, e, expected=None):
        if e.els is None:
            raise CompileError("an 'if' used as a value needs an 'else' branch", e.pos)
        pre = []
        if isinstance(e.cond, S.IfLet):
            return self.if_let_expr(e, expected)
        c = self.ce_as(e.cond, TBool)
        a_stmts, a = self.check_value_block(e.then, expected)
        if isinstance(e.els, S.IfExpr):
            b = self.x_IfExpr(e.els, expected)
            b_stmts = []
        else:
            b_stmts, b = self.check_value_block(e.els, expected)
        if a is None or b is None:
            raise CompileError("both branches of an 'if' used as a value must end with a value", e.pos)
        a, b = self.join(a, b, e.pos)
        ty = b.ty if a.ty == TNever else a.ty
        return T.Cond(c, T.Seq(a_stmts, a, ty=a.ty) if a_stmts else a, T.Seq(b_stmts, b, ty=b.ty) if b_stmts else b, ty=ty, pos=e.pos)

    def x_Cast(self, e, expected=None):
        target = self.resolve_type(e.type, self.cx.tscope)
        src = self.ce_value(e.expr, target)
        st = src.ty
        pos = e.pos
        if st == target:
            return src
        if target == TFloat and st in (TInt, TByte):
            return self.coerce(src, TFloat)
        if target == TInt and st == TFloat:
            if isinstance(src, T.Const):
                return T.Const("int", int(src.value), ty=TInt, pos=pos)
            return T.Cvt("f2i", src, ty=TInt, pos=pos)
        if target == TByte and st in (TInt, TFloat):
            if st == TFloat:
                src = T.Cvt("f2i", src, ty=TInt, pos=pos)
            return T.Cvt("trunc8", src, ty=TByte, pos=pos)
        if target == TInt and st in (TByte, TBool):
            return T.Cvt("nop", src, ty=TInt, pos=pos)
        if target == TByte and st == TBool:
            return T.Cvt("nop", src, ty=TByte, pos=pos)
        if target == TInt and isinstance(st, (TPtr,)):
            return T.Cvt("nop", src, ty=TInt, pos=pos)
        if isinstance(target, TPtr) and (st == TInt or isinstance(st, TPtr)):
            return T.Cvt("nop", src, ty=target, pos=pos)
        if isinstance(st, TEnum) and st.info.simple and target in (TInt, TByte):
            return T.Cvt("nop", src, ty=target, pos=pos)
        if isinstance(target, TEnum) and target.info.simple and st in (TInt, TByte):
            return T.Cvt("nop", self.coerce(src, TInt), ty=target, pos=pos)
        # reinterpretations used by the low-level runtime
        if isinstance(target, TPtr) and (isinstance(st, (TStruct, TTuple, TFunc)) or st == TStr):
            return T.Cvt("nop", src, ty=target, pos=pos)
        if isinstance(st, TPtr) and (isinstance(target, (TStruct, TTuple)) or target == TStr):
            return T.Cvt("nop", src, ty=target, pos=pos)
        r = self.try_coerce(src, target)
        if r is not None:
            return r
        raise CompileError("cannot convert %s to %s" % (st, target), pos,
                           "use int(x), float(x), str(x) for common conversions")

    def x_Unwrap(self, e, expected=None):
        x = self.ce_value(e.expr)
        if not isinstance(x.ty, TOpt):
            raise CompileError("'!' can only be used on optional values (types like  int? ), found %s" % x.ty, e.pos)
        stmts = []
        xs = self.bind_tmp(x, stmts)
        inner = x.ty.inner
        fail = self.call_rt("unwrap_fail", [], pos=e.pos)
        fail.ty = inner
        c = T.Cond(T.Bin("eq", xs, T.Const("nil", 0, ty=x.ty), ty=TBool), fail, self.unwrap_opt(xs), ty=inner, pos=e.pos)
        return T.Seq(stmts, c, ty=inner, pos=e.pos) if stmts else c

    def x_Try(self, e, expected=None):
        x = self.ce_value(e.expr)
        t = x.ty
        cx = self.cx
        pos = e.pos
        ret = cx.ret
        if ret is None:
            raise CompileError("'?' needs the function to declare its return type", pos)
        stmts = []
        xs = self.bind_tmp(x, stmts)
        fail = []
        if isinstance(t, TOpt):
            if not isinstance(ret, TOpt):
                raise CompileError("'?' on an optional value needs the function to return an optional type (like %s?)" % ret, pos,
                                   "or use  x ?? default  /  x!")
            self.emit_return(T.Const("nil", 0, ty=ret, pos=pos), fail, pos)
            stmts.append(T.If(T.Bin("eq", xs, T.Const("nil", 0, ty=t), ty=TBool), fail, [], pos=pos))
            return T.Seq(stmts, self.unwrap_opt(xs), ty=t.inner, pos=pos)
        if isinstance(t, TEnum) and t.info.name == "Result" and t.info.prelude:
            if not (isinstance(ret, TEnum) and ret.info is t.info):
                raise CompileError("'?' on a Result needs the function to return a Result too, but it returns %s" % ret, pos)
            if ret.args[1] != t.args[1]:
                raise CompileError("the error types differ: %s vs %s" % (t.args[1], ret.args[1]), pos)
            err = self.make_variant(ret, 1, [T.Load(xs, 1, ty=t.args[1])], pos)
            self.emit_return(err, fail, pos)
            stmts.append(T.If(T.Bin("eq", T.Load(xs, 0, ty=TInt), self.ci(1), ty=TBool), fail, [], pos=pos))
            return T.Seq(stmts, T.Load(xs, 1, ty=t.args[0]), ty=t.args[0], pos=pos)
        raise CompileError("'?' works on optional values (like int?) and on Result values, found %s" % t, pos)

    def x_Coalesce(self, e, expected=None):
        x = self.ce_value(e.left)
        if not isinstance(x.ty, TOpt):
            raise CompileError("'??' needs an optional value on the left (like  int? ), found %s" % x.ty, e.pos)
        inner = x.ty.inner
        d = self.ce_value(e.right, inner)
        d = self.coerce(d, inner, e.right.pos) if d.ty != TNever else d
        stmts = []
        xs = self.bind_tmp(x, stmts)
        c = T.Cond(T.Bin("ne", xs, T.Const("nil", 0, ty=x.ty), ty=TBool), self.unwrap_opt(xs), d, ty=inner, pos=e.pos)
        return T.Seq(stmts, c, ty=inner, pos=e.pos) if stmts else c

    def x_Range(self, e, expected=None):
        raise CompileError("a range like a..b can only be used in a 'for' loop, a slice  x[a..b]  or a test  x in a..b", e.pos)

    def x_IfLet(self, e, expected=None):
        raise CompileError("'if let' can only be used as the condition of an 'if' or 'while'", e.pos)

    def call_extern(self, name, args, pos):
        ei = self.externs.get(name)
        if ei is None:
            raise CompileError("internal error: extern '%s' not declared in the prelude" % name, pos)
        ext = self.extern_for(ei)
        return T.CallExt(ext, args, ty=ext.ret, pos=pos)

    def extern_for(self, ei):
        if ei.ext is None:
            d = ei.decl
            ts = {"i32": TInt}
            params = [self.resolve_type(p.type, ts) for p in d.params]
            ret32 = isinstance(d.ret, S.TName) and d.ret.name == "i32"
            ret = self.resolve_type(d.ret, ts) if d.ret is not None else TVoid
            dll = d.dll if "." in d.dll else d.dll + ".dll"
            ei.ext = T.Extern(dll, d.name, params, ret, ret32)
            self.program.externs.append(ei.ext)
        return ei.ext
