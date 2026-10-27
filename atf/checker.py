"""Semantic analysis: name resolution, type checking, generics (monomorphization) and lowering to typed IR."""
import difflib

from . import syntax as S
from . import tir as T
from .errors import CompileError, Pos, NOPOS, short_path
from .semtypes import *


def suggest(name, candidates):
    m = difflib.get_close_matches(name, list(candidates), n=1, cutoff=0.6)
    return "did you mean '%s'?" % m[0] if m else None


# ---------------------------------------------------------------------------------------------
class StructInfo:
    def __init__(self, decl, prelude):
        self.name = decl.name
        self.decl = decl
        self.pos = decl.pos
        self.prelude = prelude
        self.tparams = [TParam(n, id(decl) + i) for i, n in enumerate(decl.tparams)]
        self.builtin = prelude and decl.name in ("Array", "Map")
        self.cache = {}
        self.fieldnames = [f[0] for f in decl.fields]

    kind = "struct"


class EnumInfo:
    def __init__(self, decl, prelude):
        self.name = decl.name
        self.decl = decl
        self.pos = decl.pos
        self.prelude = prelude
        self.tparams = [TParam(n, id(decl) + i) for i, n in enumerate(decl.tparams)]
        self.variants = decl.variants          # (name, [TypeExpr], value, pos)
        self.simple = all(not v[1] for v in decl.variants)
        self.vindex = {v[0]: i for i, v in enumerate(decl.variants)}
        self.cache = {}
        # tag values
        tags = []
        nxt = 0
        for v in decl.variants:
            if v[2] is not None:
                nxt = v[2]
            tags.append(nxt)
            nxt += 1
        self.tags = tags

    kind = "enum"


class ImplInfo:
    def __init__(self, decl, prelude):
        self.decl = decl
        self.prelude = prelude
        self.tp_objs = [TParam(n, id(decl) + i) for i, n in enumerate(decl.tparams)]
        self.self_type = None


class FnInfo:
    def __init__(self, decl, prelude, impl=None):
        self.decl = decl
        self.name = decl.name
        self.prelude = prelude
        self.impl = impl
        own = [TParam(n, id(decl) + i + 1000) for i, n in enumerate(decl.tparams)]
        self.own_tp = own
        self.tp_objs = (impl.tp_objs if impl else []) + own
        self.has_self = bool(decl.params) and decl.params[0].name == "self"
        self._sig = None
        self.pos = decl.pos
        self.is_generic = bool(self.tp_objs)

    def qualname(self):
        if self.impl is not None and self.impl.self_type is not None:
            return "%s.%s" % (self.impl.self_type, self.name)
        return self.name


class ExternInfo:
    def __init__(self, decl):
        self.decl = decl
        self.name = decl.name
        self.pos = decl.pos
        self.ext = None


class ConstInfo:
    def __init__(self, decl, prelude):
        self.decl = decl
        self.name = decl.name
        self.prelude = prelude
        self.state = 0          # 0 unresolved, 1 resolving, 2 done
        self.value = None       # typed Const


class GlobalInfo:
    def __init__(self, decl, prelude):
        self.decl = decl
        self.name = decl.name
        self.prelude = prelude
        self.glob = None
        self.state = 0


def head_key(t):
    if isinstance(t, TPrim):
        return ("prim", t.name)
    if isinstance(t, (TStruct, TEnum)):
        return (t.info.kind, id(t.info))
    if isinstance(t, TTuple):
        return ("tuple",)
    if isinstance(t, TFunc):
        return ("fn",)
    if isinstance(t, TPtr):
        return ("ptr",)
    if isinstance(t, TOpt):
        return ("opt",)
    return ("?",)


# ---------------------------------------------------------------------------------------------
class Scope(dict):
    pass


class FnCtx:
    def __init__(self, inst, tscope, parent=None, ret=None):
        self.inst = inst
        self.tscope = tscope
        self.parent = parent
        self.ret = ret                  # Type, or None when being inferred (lambdas)
        self.scopes = [Scope()]
        self.defers = [[]]
        self.loop_scope_depth = []      # scope depth at loop entry
        self.is_lambda = parent is not None
        self.ret_seen = False

    def push(self):
        self.scopes.append(Scope())
        self.defers.append([])

    def pop(self):
        self.scopes.pop()
        return self.defers.pop()


from .check_expr import ExprMixin
from .check_stmt import StmtMixin
from .synth import SynthMixin
from .check_call import CallMixin


class Checker(ExprMixin, StmtMixin, SynthMixin, CallMixin):
    def __init__(self):
        self.structs = {}
        self.enums = {}
        self.aliases = {}
        self.fns = {}
        self.consts = {}
        self.globals = {}
        self.externs = {}
        self.impls = []
        self.methods = {}               # (head_key, name) -> [(ImplInfo, FnInfo)]
        self.insts = {}
        self.queue = []
        self.program = T.Program()
        self.synth_cache = {}
        self.cx = None
        self.errors = []
        self.array_info = None
        self.map_info = None
        self.user_fns = []
        self.global_inits = []          # (GlobalVar, typed expr) list built lazily
        self.glob_order = []
        self.tmp_n = 0
        self.user_modules = set()
        self.failed_names = set()

    # ---- declarations -------------------------------------------------------
    def declare_module(self, items, prelude):
        for it in items:
            if isinstance(it, S.StructDecl):
                self.dup_check(it.name, it.pos, self.structs, self.enums, self.aliases)
                self.structs[it.name] = StructInfo(it, prelude)
            elif isinstance(it, S.EnumDecl):
                self.dup_check(it.name, it.pos, self.structs, self.enums, self.aliases)
                self.enums[it.name] = EnumInfo(it, prelude)
            elif isinstance(it, S.TypeAlias):
                self.dup_check(it.name, it.pos, self.structs, self.enums, self.aliases)
                self.aliases[it.name] = it
            elif isinstance(it, S.FnDecl):
                if it.name in self.fns:
                    raise CompileError("function '%s' is defined twice" % it.name, it.pos,
                                       "first defined at %s:%d:%d" % (short_path(self.fns[it.name].pos.file),
                                                                      self.fns[it.name].pos.line, self.fns[it.name].pos.col))
                fi = FnInfo(it, prelude)
                self.fns[it.name] = fi
                if not prelude:
                    self.user_fns.append(fi)
            elif isinstance(it, S.ImplDecl):
                self.impls.append(ImplInfo(it, prelude))
            elif isinstance(it, S.ConstDecl):
                if it.name in self.consts or it.name in self.globals:
                    raise CompileError("'%s' is defined twice" % it.name, it.pos)
                self.consts[it.name] = ConstInfo(it, prelude)
            elif isinstance(it, S.GlobalDecl):
                if it.name in self.consts or it.name in self.globals:
                    raise CompileError("'%s' is defined twice" % it.name, it.pos)
                gi = GlobalInfo(it, prelude)
                self.globals[it.name] = gi
                self.glob_order.append(gi)
            elif isinstance(it, S.ExternDecl):
                self.externs[it.name] = ExternInfo(it)
            elif isinstance(it, S.ImportDecl):
                pass

    def dup_check(self, name, pos, *tables):
        if name in PRIMS:
            raise CompileError("'%s' is a built-in type name" % name, pos)
        for t in tables:
            if name in t:
                raise CompileError("type '%s' is defined twice" % name, pos)

    def finish_declare(self):
        self.array_info = self.structs.get("Array")
        self.map_info = self.structs.get("Map")
        for impl in self.impls:
            d = impl.decl
            ts = {n: p for n, p in zip(d.tparams, impl.tp_objs)}
            try:
                impl.self_type = self.resolve_type(d.type, ts)
            except CompileError as e:
                self.errors.append(e)
                continue
            ts["Self"] = impl.self_type
            hk = head_key(impl.self_type)
            for m in d.methods:
                fi = FnInfo(m, impl.prelude, impl)
                lst = self.methods.setdefault((hk, m.name), [])
                for (oi, ofi) in lst:
                    if oi.self_type == impl.self_type:
                        self.errors.append(CompileError("method '%s' is defined twice for %s" % (m.name, impl.self_type), m.pos))
                lst.append((impl, fi))
                if not impl.prelude:
                    self.user_fns.append(fi)

    # ---- type resolution ----------------------------------------------------
    def resolve_type(self, t, ts):
        if isinstance(t, S.TName):
            n = t.name
            if n in ts:
                if t.args:
                    raise CompileError("type parameter '%s' takes no arguments" % n, t.pos)
                return ts[n]
            if n in PRIMS:
                if t.args:
                    raise CompileError("'%s' takes no type arguments" % n, t.pos)
                return PRIMS[n]
            if n in self.aliases:
                al = self.aliases[n]
                if len(al.tparams) != len(t.args):
                    raise CompileError("type alias '%s' needs %d type argument(s)" % (n, len(al.tparams)), t.pos)
                sub = dict(ts)
                for pn, a in zip(al.tparams, t.args):
                    sub[pn] = self.resolve_type(a, ts)
                return self.resolve_type(al.type, sub)
            info = self.structs.get(n) or self.enums.get(n)
            if info is not None:
                args = [self.resolve_type(a, ts) for a in t.args]
                if len(args) != len(info.tparams):
                    if not args and info.tparams:
                        raise CompileError("'%s' needs type arguments: %s<%s>" % (n, n, ", ".join(p.name for p in info.tparams)), t.pos)
                    raise CompileError("'%s' takes %d type argument(s) but %d given" % (n, len(info.tparams), len(args)), t.pos)
                return TStruct(info, args) if info.kind == "struct" else TEnum(info, args)
            cands = list(ts) + list(PRIMS) + list(self.structs) + list(self.enums) + list(self.aliases)
            raise CompileError("unknown type '%s'" % n, t.pos, suggest(n, cands))
        if isinstance(t, S.TArray):
            return TStruct(self.array_info, [self.resolve_type(t.elem, ts)])
        if isinstance(t, S.TMap):
            return TStruct(self.map_info, [self.resolve_type(t.key, ts), self.resolve_type(t.val, ts)])
        if isinstance(t, S.TTuple):
            return TTuple([self.resolve_type(e, ts) for e in t.elems])
        if isinstance(t, S.TFn):
            return TFunc([self.resolve_type(p, ts) for p in t.params], self.resolve_type(t.ret, ts) if t.ret else TVoid)
        if isinstance(t, S.TOpt):
            inner = self.resolve_type(t.inner, ts)
            return inner if isinstance(inner, TOpt) else TOpt(inner)
        if isinstance(t, S.TPtr):
            return TPtr(self.resolve_type(t.elem, ts))
        raise CompileError("bad type", getattr(t, "pos", None))

    def struct_fields(self, st):
        """[(name, Type)] of a concrete struct type"""
        key = tuple(a.key() for a in st.args)
        c = st.info.cache.get(key)
        if c is None:
            ts = {p.name: a for p, a in zip(st.info.tparams, st.args)}
            c = [(f[0], self.resolve_type(f[1], ts)) for f in st.info.decl.fields]
            st.info.cache[key] = c
        return c

    def variant_payload(self, et, vi):
        key = tuple(a.key() for a in et.args)
        c = et.info.cache.get(key)
        if c is None:
            ts = {p.name: a for p, a in zip(et.info.tparams, et.args)}
            c = [[self.resolve_type(t, ts) for t in v[1]] for v in et.info.variants]
            et.info.cache[key] = c
        return c[vi]

    def is_value_type(self, t):
        """True if values of t are stored directly (not as heap pointers); optionals of them are boxed."""
        if t in (TInt, TFloat, TBool, TByte):
            return True
        if isinstance(t, TPtr):
            return True
        if isinstance(t, TEnum) and t.info.simple:
            return True
        return False

    def esize(self, t):
        return 1 if (t == TByte or t == TBool) else 8

    # ---- function signatures / instances --------------------------------------------
    def generic_sig(self, fi):
        if fi._sig is None:
            ts = {tp.name: tp for tp in fi.tp_objs}
            if fi.impl is not None:
                ts["Self"] = fi.impl.self_type
            ptypes = []
            for i, p in enumerate(fi.decl.params):
                if p.name == "self" and p.type is None:
                    if fi.impl is None:
                        raise CompileError("'self' can only be used inside an impl block", p.pos)
                    ptypes.append(fi.impl.self_type)
                else:
                    ptypes.append(self.resolve_type(p.type, ts))
            ret = self.resolve_type(fi.decl.ret, ts) if fi.decl.ret is not None else TVoid
            fi._sig = (ptypes, ret)
        return fi._sig

    def get_inst(self, fi, targs):
        key = (id(fi), tuple(t.key() for t in targs))
        inst = self.insts.get(key)
        if inst is not None:
            return inst
        binds = {tp.key(): a for tp, a in zip(fi.tp_objs, targs)}
        gp, gr = self.generic_sig(fi)
        params = []
        for p, pt in zip(fi.decl.params, gp):
            v = T.Var(p.name, subst(pt, binds), True, pos=p.pos)
            v.is_param = True
            params.append(v)
        inst = T.FnInst(fi.qualname() if not targs else "%s<%s>" % (fi.qualname(), ", ".join(str(a) for a in targs)),
                        params, subst(gr, binds))
        inst.info = fi
        inst.targs = tuple(targs)
        inst.pos = fi.pos
        inst.is_prelude = fi.prelude
        inst.vars = list(params)
        self.insts[key] = inst
        self.queue.append(inst)
        self.program.funcs.append(inst)
        return inst

    def check_inst(self, inst):
        fi = inst.info
        binds = {tp.key(): a for tp, a in zip(fi.tp_objs, inst.targs)}
        ts = {tp.name: a for tp, a in zip(fi.tp_objs, inst.targs)}
        if fi.impl is not None:
            ts["Self"] = subst(fi.impl.self_type, binds)
        ctx = FnCtx(inst, ts, None, inst.ret)
        saved = self.cx
        self.cx = ctx
        try:
            for v in inst.params:
                ctx.scopes[0][v.name] = v
            body = self.check_block_stmts(fi.decl.body.stmts, new_scope=False)
            inst.body = body
            if inst.ret != TVoid and inst.ret != TNever and not self.terminates(body):
                raise CompileError("function '%s' must return a value of type %s on every path" % (fi.name, inst.ret),
                                   fi.decl.body.pos,
                                   "add a 'return' at the end of the function")
        finally:
            self.cx = saved

    # ---- helpers -----------------------------------------------------------------
    def rt(self, name, targs=()):
        fi = self.fns.get(name)
        if fi is None or not fi.prelude:
            raise CompileError("internal error: runtime function '%s' missing from the prelude" % name)
        return self.get_inst(fi, list(targs))

    def call_rt(self, name, args, targs=(), pos=None):
        inst = self.rt(name, targs)
        self.cx.inst.callees.add(inst)
        return T.Call(inst, args, ty=inst.ret, pos=pos)

    def new_tmp(self, ty, name="$t"):
        v = T.Var(name, ty, True, pos=None)
        v.is_temp = True
        self.cx.inst.vars.append(v)
        return v

    def ci(self, v, pos=None):
        return T.Const("int", v, ty=TInt, pos=pos)

    def error(self, msg, pos, hint=None):
        raise CompileError(msg, pos, hint)

    # ---- driver ----------------------------------------------------------------------
    def run(self, check_all_user=True):
        self.finish_declare()
        if self.errors:
            raise MultiError(self.errors)
        self.program.alloc = self.rt("__alloc")
        main = self.fns.get("main")
        if main is None or main.prelude:
            raise CompileError("no 'main' function found", None, "every program starts at:  fn main() { ... }")
        entry = self.build_entry(main)
        self.program.entry = entry
        for gi in self.glob_order:
            self.guarded(self.resolve_global, gi)
        for ci in self.consts.values():
            self.guarded(self.resolve_const, ci)
        if check_all_user:
            for fi in self.user_fns:
                if not fi.is_generic and not (fi.impl is not None and fi.impl.tp_objs):
                    self.guarded(self.get_inst, fi, [])
        self.drain()
        self.finalize_entry(main)
        self.drain()
        if self.errors:
            raise MultiError(self.errors)
        # drop unreachable instances
        reach = set()
        stack = [entry]
        while stack:
            f = stack.pop()
            if f in reach:
                continue
            reach.add(f)
            for c in f.callees:
                stack.append(c)
        self.program.funcs = [f for f in self.program.funcs if f in reach]
        return self.program

    def guarded(self, fn, *args):
        try:
            return fn(*args)
        except CompileError as e:
            self.errors.append(e)

    def drain(self):
        while self.queue:
            inst = self.queue.pop()
            if inst.body is not None:
                continue
            try:
                self.check_inst(inst)
            except CompileError as e:
                self.errors.append(e)
                inst.body = []

    def build_entry(self, main):
        """__entry: runtime init, global initializers, main(), exit."""
        inst = T.FnInst("__entry", [], TVoid)
        inst.pos = main.pos
        inst.is_prelude = True
        inst.body = []
        self.entry_ctx = FnCtx(inst, {}, None, TVoid)
        self.program.funcs.append(inst)
        saved = self.cx
        self.cx = self.entry_ctx
        try:
            rt_init = self.rt("__rt_init")
            inst.callees.add(rt_init)
            self.entry_body = [T.ExprS(T.Call(rt_init, [], ty=TVoid))]
            for nm in ("bounds_fail", "div_fail"):
                f = self.rt("rt_" + nm)
                inst.callees.add(f)
                self.program.rt[nm] = f
        finally:
            self.cx = saved
        return inst

    def finalize_entry(self, main):
        inst = self.program.entry
        saved = self.cx
        self.cx = self.entry_ctx
        try:
            gp, gr = self.generic_sig(main)
            mi = self.get_inst(main, [])
            inst.callees.add(mi)
            args = []
            if gp:
                if len(gp) != 1 or gp[0] != TStruct(self.array_info, [TStr]):
                    raise CompileError("main can be  fn main()  or  fn main(args: [str])", main.pos)
                args.append(self.call_rt("__rt_args", []))
            call = T.Call(mi, args, ty=gr)
            if gr == TInt:
                code = call
            else:
                self.entry_body.append(T.ExprS(call))
                code = self.ci(0)
            self.entry_body.append(T.ExprS(self.call_rt("__rt_exit", [code])))
            inst.body = self.entry_body
        finally:
            self.cx = saved

    def resolve_global(self, gi):
        """create the GlobalVar for a `let`/`var` at top level and emit its initializer into __entry"""
        if gi.state == 2:
            return gi.glob
        if gi.state == 1:
            raise CompileError("global '%s' depends on itself" % gi.name, gi.decl.pos)
        gi.state = 1
        saved = self.cx
        self.cx = self.entry_ctx
        try:
            d = gi.decl
            ts = {}
            ty = self.resolve_type(d.type, ts) if d.type is not None else None
            init = None
            if d.value is not None:
                init = self.ce(d.value, ty)
                if ty is None:
                    if init.ty in (TNil, TVoid, TNever):
                        raise CompileError("cannot infer the type of '%s'" % gi.name, d.pos, "add a type:  let %s: T = ..." % gi.name)
                    ty = init.ty
                else:
                    init = self.coerce(init, ty, d.value.pos)
            elif ty is None:
                raise CompileError("global '%s' needs a type or a value" % gi.name, d.pos)
            g = T.GlobalVar(gi.name, ty, d.pos)
            gi.glob = g
            gi.state = 2
            self.program.globals.append(g)
            zero = isinstance(init, T.Const) and (init.value == 0 or init.value == b"" and False)
            if init is not None and not zero:
                self.entry_body.append(T.Set(T.GlobalRef(g, ty=ty), init, pos=d.pos))
            elif ty == TStr or ty == TFloat:
                pass
            return g
        finally:
            self.cx = saved

    def resolve_const(self, ci):
        if ci.state == 2:
            return ci
        if ci.state == 1:
            raise CompileError("constant '%s' depends on itself" % ci.name, ci.decl.pos)
        ci.state = 1
        saved = self.cx
        self.cx = self.entry_ctx
        try:
            d = ci.decl
            ty = self.resolve_type(d.type, {}) if d.type is not None else None
            val = self.ce(d.value, ty)
            if ty is not None:
                val = self.coerce(val, ty, d.value.pos)
            if isinstance(val, T.Const) and val.kind != "nil":
                ci.value = val
            else:
                g = T.GlobalVar(ci.name, val.ty, d.pos)
                self.program.globals.append(g)
                self.entry_body.append(T.Set(T.GlobalRef(g, ty=val.ty), val, pos=d.pos))
                ci.value = T.GlobalRef(g, ty=val.ty)
            ci.state = 2
            return ci
        finally:
            self.cx = saved


class MultiError(Exception):
    def __init__(self, errors):
        Exception.__init__(self, "%d errors" % len(errors))
        self.errors = errors

    def render(self):
        seen = set()
        out = []
        for e in self.errors[:10]:
            r = e.render()
            if r in seen:
                continue
            seen.add(r)
            out.append(r)
        if len(self.errors) > 10:
            out.append("... and %d more errors" % (len(self.errors) - 10))
        return "\n\n".join(out)
