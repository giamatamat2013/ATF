"""Calls, methods, constructors, lambdas and built-in special forms."""
from . import syntax as S
from . import tir as T
from .errors import CompileError, SilentError, short_path
from .semtypes import *

INTRINSICS = {
    # name: (arg types, return type)  — None entries are checked by hand
    "__sqrt": ([TFloat], TFloat), "__floor": ([TFloat], TFloat), "__ceil": ([TFloat], TFloat),
    "__trunc": ([TFloat], TFloat), "__fabs": ([TFloat], TFloat),
    "__f2bits": ([TFloat], TInt), "__bits2f": ([TInt], TFloat),
    "__sp": ([], TInt), "__popcnt": ([TInt], TInt), "__clz": ([TInt], TInt), "__ctz": ([TInt], TInt),
    "__trap": ([], TNever),
    "__data_start": ([], TInt), "__data_end": ([], TInt),
    "__tb": ([], TInt), "__text_start": ([], TInt), "__fp": ([], TInt),
}


SPECIAL_FORMS = {"print", "println", "eprint", "eprintln", "str", "int", "float", "byte", "bool", "assert", "panic",
                 "__comprehension", "copy", "same", "include_str"}


class CallMixin:
    # ------------------------------------------------------------------ method lookup
    def find_methods(self, t, name):
        res = []
        for impl, fi in self.methods.get((self.head_of(t), name), []):
            binds = {}
            if unify(impl.self_type, t, binds):
                res.append((impl, fi, binds))
        return res

    def head_of(self, t):
        from .checker import head_key
        return head_key(t)

    def try_method(self, recv, name, args, pos, expected=None):
        found = self.find_methods(recv.ty, name)
        if not found:
            return None
        impl, fi, binds = found[0]
        if not fi.has_self:
            return None
        return self.invoke(fi, dict(binds), recv, args, pos, expected)

    # ------------------------------------------------------------------ core of every call
    def bind_args(self, fi, args, nself, pos):
        """map call arguments (positional / named) to parameter slots"""
        params = fi.decl.params[nself:]
        slots = [None] * len(params)
        npos = 0
        named_seen = False
        for a in args:
            if isinstance(a, S.NamedArg):
                named_seen = True
                for i, p in enumerate(params):
                    if p.name == a.name:
                        if slots[i] is not None:
                            raise CompileError("argument '%s' given twice" % a.name, a.pos)
                        slots[i] = a.expr
                        break
                else:
                    raise CompileError("function '%s' has no parameter named '%s'" % (fi.name, a.name), a.pos,
                                       "parameters: " + ", ".join(p.name for p in params))
            else:
                if named_seen:
                    raise CompileError("positional arguments must come before named ones", getattr(a, "pos", pos))
                if npos >= len(params):
                    self.arity_error(fi, params, len(args), pos)
                slots[npos] = a
                npos += 1
        return params, slots

    def arity_error(self, fi, params, given, pos):
        required = sum(1 for p in params if p.default is None)
        sig = ", ".join("%s: %s" % (p.name, self.type_text(p.type)) for p in params)
        raise CompileError("'%s' takes %s but %d given" % (
            fi.name, ("%d argument(s)" % len(params)) if required == len(params) else ("%d to %d arguments" % (required, len(params))), given),
            pos, "signature: %s(%s)" % (fi.name, sig))

    def type_text(self, t):
        if t is None:
            return "?"
        if isinstance(t, S.TName):
            return t.name + ("<%s>" % ", ".join(self.type_text(a) for a in t.args) if t.args else "")
        if isinstance(t, S.TArray):
            return "[%s]" % self.type_text(t.elem)
        if isinstance(t, S.TMap):
            return "{%s: %s}" % (self.type_text(t.key), self.type_text(t.val))
        if isinstance(t, S.TOpt):
            return self.type_text(t.inner) + "?"
        if isinstance(t, S.TTuple):
            return "(" + ", ".join(self.type_text(a) for a in t.elems) + ")"
        if isinstance(t, S.TFn):
            return "fn(" + ", ".join(self.type_text(a) for a in t.params) + ")" + (" -> " + self.type_text(t.ret) if t.ret else "")
        if isinstance(t, S.TPtr):
            return "ptr<%s>" % self.type_text(t.elem)
        return "?"

    def unify_arg(self, pattern, te, binds):
        t = te.ty
        if t == TNil or t == TNever:
            return True
        if not has_params(pattern):
            return self.try_coerce(te, pattern) is not None
        if unify(pattern, t, binds):
            return True
        if isinstance(pattern, TParam):
            cur = binds.get(pattern.key())
            if cur is not None and self.try_coerce(te, cur) is not None:
                return True
            if cur is not None:
                if cur in (TInt, TByte) and t == TFloat:
                    binds[pattern.key()] = TFloat
                    return True
                if cur == TByte and t == TInt:
                    binds[pattern.key()] = TInt
                    return True
                if cur in (TInt, TByte) and t in (TInt, TByte):
                    return True
                if cur == TFloat and t in (TInt, TByte):
                    return True
        return False

    def invoke(self, fi, binds, recv, args, pos, expected=None, explicit_targs=None):
        """call function/method `fi`. binds: type-parameter bindings known so far (from the receiver)."""
        gp, gr = self.generic_sig(fi)
        nself = 1 if (recv is not None) else 0
        if recv is not None and not fi.has_self:
            raise CompileError("'%s' is a static function; call it as  %s.%s(...)" % (fi.name, fi.impl.self_type if fi.impl else "Type", fi.name), pos)
        if recv is None and fi.has_self:
            raise CompileError("'%s' is a method; call it on a value like  x.%s(...)" % (fi.name, fi.name), pos)
        params, slots = self.bind_args(fi, args, nself, pos)
        if explicit_targs:
            if len(explicit_targs) > len(fi.own_tp):
                raise CompileError("'%s' takes %d type argument(s)" % (fi.name, len(fi.own_tp)), pos)
            for tp, ta in zip(fi.own_tp, explicit_targs):
                binds[tp.key()] = self.resolve_type(ta, self.cx.tscope)
        typed = [None] * len(slots)
        later = []
        for i, a in enumerate(slots):
            if a is None:
                continue
            if isinstance(a, S.Lambda):
                later.append(i)
                continue
            pt = gp[nself + i]
            hint = subst(pt, binds)
            if has_params(hint):
                hint = None
            te = self.ce_value(a, hint)
            typed[i] = te
            if not self.unify_arg(pt, te, binds):
                self.mismatch(te.ty, subst(pt, binds), getattr(a, "pos", pos))
        for i in later:
            pt = subst(gp[nself + i], binds)
            te = self.ce(slots[i], pt)
            typed[i] = te
            if not self.unify_arg(gp[nself + i], te, binds):
                self.mismatch(te.ty, subst(gp[nself + i], binds), slots[i].pos)
        # defaults
        for i, p in enumerate(params):
            if typed[i] is None:
                if p.default is None:
                    raise CompileError("missing argument '%s' in call to '%s'" % (p.name, fi.name), pos,
                                       "signature: %s(%s)" % (fi.name, ", ".join("%s: %s" % (q.name, self.type_text(q.type)) for q in params)))
                pt = subst(gp[nself + i], binds)
                typed[i] = self.ce_value(p.default, None if has_params(pt) else pt)
                self.unify_arg(gp[nself + i], typed[i], binds)
        # remaining type parameters
        if expected is not None and any(tp.key() not in binds for tp in fi.tp_objs):
            unify(gr, expected, binds)
        for tp in fi.tp_objs:
            if tp.key() not in binds:
                raise CompileError("cannot infer the type parameter '%s' of '%s'" % (tp.name, fi.name), pos,
                                   "give an explicit type, e.g. a type annotation on the variable, or  %s::<int>(...)" % fi.name)
        targs = [binds[tp.key()] for tp in fi.tp_objs]
        inst = self.get_inst(fi, targs)
        self.cx.inst.callees.add(inst)
        out = []
        if recv is not None:
            out.append(recv)
        for i, te in enumerate(typed):
            pt = inst.params[nself + i].ty
            out.append(self.coerce(te, pt, getattr(slots[i], "pos", pos) if slots[i] is not None else pos))
        return T.Call(inst, out, ty=inst.ret, pos=pos)

    # ------------------------------------------------------------------ x_Call
    def x_Call(self, e, expected=None):
        callee = e.callee
        pos = e.pos
        if isinstance(callee, S.Ident):
            return self.call_ident(e, callee, expected)
        if isinstance(callee, S.Field):
            tn = self.type_ident(callee.obj)
            if tn is not None:
                return self.call_static(tn, callee, e, expected)
            recv = self.ce_value(callee.obj)
            return self.call_method(recv, callee, e, expected)
        f = self.ce_value(callee)
        return self.call_value(f, e, expected)

    def call_value(self, f, e, expected):
        if not isinstance(f.ty, TFunc):
            raise CompileError("cannot call a value of type %s" % f.ty, e.pos)
        ft = f.ty
        if len(e.args) != len(ft.params):
            raise CompileError("this function takes %d argument(s) but %d given" % (len(ft.params), len(e.args)), e.pos,
                               "its type is %s" % ft)
        args = []
        for a, pt in zip(e.args, ft.params):
            if isinstance(a, S.NamedArg):
                raise CompileError("named arguments cannot be used when calling a function value", a.pos)
            args.append(self.ce_as(a, pt))
        return T.CallInd(f, args, ty=ft.ret, pos=e.pos)

    def call_method(self, recv, callee, e, expected):
        name = callee.name
        t = recv.ty
        # field holding a function
        if isinstance(t, TStruct) and isinstance(name, str):
            for i, (fname, fty) in enumerate(self.struct_fields(t)):
                if fname == name and isinstance(fty, TFunc):
                    return self.call_value(T.Load(recv, i, ty=fty, pos=callee.pos), e, expected)
        if isinstance(name, int):
            raise CompileError("cannot call a tuple element like a method", e.pos)
        found = self.find_methods(t, name)
        if not found:
            if isinstance(t, TOpt):
                raise CompileError("cannot call '.%s()' on %s because it may be nil" % (name, t), callee.pos,
                                   "unwrap it first:  x!.%s(...)   or   if let v = x { v.%s(...) }" % (name, name))
            self.no_method(t, name, callee.pos)
        impl, fi, binds = found[0]
        if not fi.has_self:
            raise CompileError("'%s' is a static function; call it as  %s.%s(...)" % (name, t, name), callee.pos)
        return self.invoke(fi, dict(binds), recv, e.args, e.pos, expected, self.targs_of(callee))

    def targs_of(self, callee):
        return None

    def no_method(self, t, name, pos):
        from .checker import suggest
        names = set()
        for (hk, mname), lst in self.methods.items():
            if hk == self.head_of(t) and not mname.startswith("op_") and not mname.startswith("__"):
                names.add(mname)
        if isinstance(t, TStruct):
            names.update(f for f, _ in self.struct_fields(t))
        raise CompileError("%s has no method '%s'" % (t, name), pos,
                           suggest(name, names) or ("available: " + ", ".join(sorted(names)) if names and len(names) < 14 else None))

    def call_static(self, tn, callee, e, expected):
        name = callee.name
        pos = e.pos
        if tn in self.enums:
            info = self.enums[tn]
            if name in info.vindex:
                vi = info.vindex[name]
                et = self.enum_type_for(info, expected)
                if et is None:
                    return self.generic_variant(info, vi, e, expected)
                payload = self.variant_payload(et, vi)
                if len(e.args) != len(payload):
                    raise CompileError("%s.%s takes %d value(s) but %d given" % (tn, name, len(payload), len(e.args)), pos)
                args = [self.ce_as(a, pt) for a, pt in zip(e.args, payload)]
                return self.make_variant(et, vi, args, pos)
        # static method
        dummy = None
        if tn in self.structs:
            info = self.structs[tn]
            dummy = TStruct(info, info.tparams)
        elif tn in self.enums:
            info = self.enums[tn]
            dummy = TEnum(info, info.tparams)
        elif tn in PRIMS:
            dummy = PRIMS[tn]
        elif tn in self.aliases:
            raise CompileError("call static functions on the real type name, not the alias '%s'" % tn, pos)
        cands = self.methods.get((self.head_of(dummy), name), []) if dummy is not None else []
        if not cands:
            from .checker import suggest
            names = [m for (hk, m) in self.methods if hk == self.head_of(dummy)] if dummy is not None else []
            variants = [v[0] for v in self.enums[tn].variants] if tn in self.enums else []
            raise CompileError("'%s' has no function or variant '%s'" % (tn, name), callee.pos,
                               suggest(name, names + variants))
        impl, fi = cands[0]
        if fi.has_self:
            # Type.method(obj, args) style call
            if not e.args:
                raise CompileError("'%s' is a method; call it on a value like  x.%s()" % (name, name), pos)
            recv = self.ce_value(e.args[0])
            found = self.find_methods(recv.ty, name)
            if not found:
                self.no_method(recv.ty, name, pos)
            impl, fi, binds = found[0]
            return self.invoke(fi, dict(binds), recv, e.args[1:], pos, expected)
        return self.invoke(fi, {}, None, e.args, pos, expected)

    def generic_variant(self, info, vi, e, expected):
        pos = e.pos
        tps = info.tparams
        payload_ast = info.variants[vi][1]
        ts = {p.name: p for p in tps}
        pts = [self.resolve_type(t, ts) for t in payload_ast]
        if len(e.args) != len(pts):
            raise CompileError("%s.%s takes %d value(s) but %d given" % (info.name, info.variants[vi][0], len(pts), len(e.args)), pos)
        binds = {}
        if isinstance(expected, TEnum) and expected.info is info:
            for p, a in zip(tps, expected.args):
                binds[p.key()] = a
        typed = []
        for a, pt in zip(e.args, pts):
            hint = subst(pt, binds)
            te = self.ce_value(a, None if has_params(hint) else hint)
            typed.append(te)
            self.unify_arg(pt, te, binds)
        for p in tps:
            if p.key() not in binds:
                raise CompileError("cannot infer the type parameter '%s' of %s" % (p.name, info.name), pos,
                                   "add a type annotation, e.g.  let x: %s<int> = ..." % info.name)
        et = TEnum(info, [binds[p.key()] for p in tps])
        payload = self.variant_payload(et, vi)
        args = [self.coerce(t_, pt) for t_, pt in zip(typed, payload)]
        return self.make_variant(et, vi, args, pos)

    # ------------------------------------------------------------------ calls by name
    def call_ident(self, e, callee, expected):
        name = callee.name
        pos = e.pos
        v = self.lookup_var(name)
        if v is not None:
            self.touch(v)
            return self.call_value(T.VarRef(v, ty=v.ty, pos=callee.pos), e, expected)
        fi = self.fns.get(name)
        if fi is not None and not fi.prelude:
            return self.invoke(fi, {}, None, e.args, pos, expected, callee.targs)
        sp = getattr(self, "sf_" + name.lstrip("_"), None) if name in SPECIAL_FORMS else None
        if sp is not None:
            return sp(e, expected)
        if name in INTRINSICS or name in ("__setjmp", "__longjmp", "__sizeof", "__pointer_free", "__has_default", "__default", "__eq", "__cmp", "__hash", "__str", "__debug", "__memcpy", "__memset", "__save_regs",
                                          "__call_cdecl"):
            return self.intrinsic_call(e, callee, expected)
        if fi is not None:
            return self.invoke(fi, {}, None, e.args, pos, expected, callee.targs)
        if name in self.structs:
            return self.construct(self.structs[name], e.args, [], pos, expected, callee.targs)
        ei = self.externs.get(name)
        if ei is not None:
            ext = self.extern_for(ei)
            if len(e.args) != len(ext.params):
                raise CompileError("'%s' takes %d argument(s) but %d given" % (name, len(ext.params), len(e.args)), pos)
            args = [self.ce_as(a, pt) for a, pt in zip(e.args, ext.params)]
            return T.CallExt(ext, args, ty=ext.ret, pos=pos)
        if name in self.enums:
            raise CompileError("'%s' is an enum; create a value with  %s.Variant" % (name, name), pos)
        from .checker import suggest
        if name in self.failed_names:
            raise SilentError("follow-up error", e.pos)
        raise CompileError("unknown function '%s'" % name, callee.pos, suggest(name, self.visible_names()))

    # ---- struct construction ------------------------------------------------------------
    def construct(self, info, args, named_fields, pos, expected, targs=None):
        """args: positional/NamedArg ASTs ; named_fields: [(name, AST, pos)] from a struct literal"""
        tps = info.tparams
        ts = {p.name: p for p in tps}
        fields = [(f[0], self.resolve_type(f[1], ts)) for f in info.decl.fields]
        if isinstance(expected, TOpt):
            expected = expected.inner
        binds = {}
        if isinstance(expected, TStruct) and expected.info is info:
            for p, a in zip(tps, expected.args):
                binds[p.key()] = a
        if targs:
            for p, ta in zip(tps, targs):
                binds[p.key()] = self.resolve_type(ta, self.cx.tscope)
        vals = {}
        order = [f[0] for f in fields]
        i = 0
        for a in args:
            if isinstance(a, S.NamedArg):
                vals[a.name] = (a.expr, a.pos)
            else:
                if i >= len(fields):
                    raise CompileError("%s has only %d field(s) but %d values were given" % (info.name, len(fields), len(args)), pos,
                                       "fields: " + ", ".join(order))
                vals[fields[i][0]] = (a, getattr(a, "pos", pos))
                i += 1
        for (n, a, p) in named_fields:
            if n in vals:
                raise CompileError("field '%s' is given twice" % n, p)
            vals[n] = (a, p)
        for n in vals:
            if n not in order:
                from .checker import suggest
                raise CompileError("%s has no field '%s'" % (info.name, n), vals[n][1], suggest(n, order) or "fields: " + ", ".join(order))
        for n in order:
            if n not in vals:
                raise CompileError("missing field '%s' when creating %s" % (n, info.name), pos, "fields: " + ", ".join(order))
        typed = {}
        later = []
        for n, ft in fields:
            a, p = vals[n]
            if isinstance(a, S.Lambda):
                later.append((n, ft, a, p))
                continue
            hint = subst(ft, binds)
            te = self.ce_value(a, None if has_params(hint) else hint)
            typed[n] = te
            if not self.unify_arg(ft, te, binds):
                self.mismatch(te.ty, subst(ft, binds), p)
        for n, ft, a, p in later:
            te = self.ce(a, subst(ft, binds))
            typed[n] = te
            self.unify_arg(ft, te, binds)
        for tp in tps:
            if tp.key() not in binds:
                raise CompileError("cannot infer the type parameter '%s' of %s" % (tp.name, info.name), pos,
                                   "add a type annotation, e.g.  let x: %s<int> = ..." % info.name)
        st = TStruct(info, [binds[tp.key()] for tp in tps])
        concrete = self.struct_fields(st)
        out = [self.coerce(typed[n], ct, vals[n][1]) for n, ct in concrete]
        return T.NewObj(out, ty=st, pos=pos)

    def x_StructLit(self, e, expected=None):
        name = e.name.name
        info = self.structs.get(name)
        if info is None:
            if name in self.enums:
                raise CompileError("'%s' is an enum, not a struct" % name, e.pos)
            from .checker import suggest
            raise CompileError("unknown struct '%s'" % name, e.pos, suggest(name, self.structs))
        return self.construct(info, [], e.fields, e.pos, expected, e.name.targs)

    # ---- lambdas ---------------------------------------------------------------------------
    def x_Lambda(self, e, expected=None):
        from .checker import FnCtx
        if isinstance(expected, TOpt):
            expected = expected.inner
        exp = expected if isinstance(expected, TFunc) else None
        if exp is not None and len(exp.params) != len(e.params):
            raise CompileError("this function takes %d parameter(s) here but the lambda has %d" % (len(exp.params), len(e.params)), e.pos)
        ptypes = []
        for i, (n, ty) in enumerate(e.params):
            if ty is not None:
                ptypes.append(self.resolve_type(ty, self.cx.tscope))
            elif exp is not None and not has_params(exp.params[i]):
                ptypes.append(exp.params[i])
            else:
                raise CompileError("cannot infer the type of parameter '%s'" % n, e.pos, "annotate it:  |%s: int| ..." % n)
        ret = None
        if e.ret is not None:
            ret = self.resolve_type(e.ret, self.cx.tscope)
        elif exp is not None and not has_params(exp.ret):
            ret = exp.ret
        params = []
        for (n, _), pt in zip(e.params, ptypes):
            v = T.Var(n, pt, True, pos=e.pos)
            v.is_param = True
            params.append(v)
        inst = T.FnInst("lambda@%d" % e.pos.line, params, ret)
        inst.is_lambda = True
        inst.vars = list(params)
        inst.pos = e.pos
        inst.is_prelude = self.cx.inst.is_prelude
        ctx = FnCtx(inst, self.cx.tscope, parent=self.cx, ret=ret)
        parent_ctx = self.cx
        self.cx = ctx
        try:
            for v in params:
                ctx.scopes[0][v.name] = v
            body = self.check_block_stmts(e.body.stmts, new_scope=False)
            if ctx.ret is None:
                ctx.ret = TVoid
            inst.ret = ctx.ret
            inst.body = body
            if inst.ret not in (TVoid, TNever) and not self.terminates(body):
                raise CompileError("this lambda must return a value of type %s on every path" % inst.ret, e.pos)
        finally:
            self.cx = parent_ctx
        self.program.funcs.append(inst)
        parent_ctx.inst.callees.add(inst)
        for c in inst.captures:
            c.root.weight += 1
        return T.MkClosure(inst, list(inst.captures), ty=TFunc([p.ty for p in params], inst.ret), pos=e.pos)

    # ---- intrinsics ----------------------------------------------------------------------------
    def intrinsic_call(self, e, callee, expected):
        name = callee.name
        pos = e.pos
        if name in INTRINSICS:
            ats, rt = INTRINSICS[name]
            if len(e.args) != len(ats):
                raise CompileError("%s takes %d argument(s)" % (name, len(ats)), pos)
            args = [self.ce_as(a, t) for a, t in zip(e.args, ats)]
            return T.Intr(name[2:], args, ty=rt, pos=pos)
        if name in ("__has_default", "__default"):
            if not callee.targs:
                raise CompileError("use  %s::<T>()" % name, pos)
            t = self.resolve_type(callee.targs[0], self.cx.tscope)
            has = t == TStr or (isinstance(t, TStruct) and (t.info is self.array_info or t.info is self.map_info))
            if name == "__has_default":
                return T.Const("bool", 1 if has else 0, ty=TBool, pos=pos)
            if has or t == TFloat:
                return self.default_value(t, pos)
            return T.Const("int", 0, ty=t, pos=pos)
        if name == "__pointer_free":
            if not callee.targs:
                raise CompileError("use  __pointer_free::<T>()", pos)
            t = self.resolve_type(callee.targs[0], self.cx.tscope)
            free = t in (TInt, TFloat, TBool, TByte) or (isinstance(t, TEnum) and t.info.simple)
            return T.Const("bool", 1 if free else 0, ty=TBool, pos=pos)
        if name == "__sizeof":
            if not callee.targs:
                raise CompileError("use  __sizeof::<T>()", pos)
            t = self.resolve_type(callee.targs[0], self.cx.tscope)
            return self.ci(self.esize(t), pos)
        if name in ("__memcpy", "__memset"):
            if len(e.args) != 3:
                raise CompileError("%s takes 3 arguments" % name, pos)
            a = self.ce_value(e.args[0])
            b = self.ce_value(e.args[1])
            n = self.ce_as(e.args[2], TInt)
            if name == "__memset":
                b = self.coerce(b, TInt)
            return T.Intr(name[2:], [a, b, n], ty=TVoid, pos=pos)
        if name == "__setjmp":
            a = self.ce_value(e.args[0])
            return T.Intr("setjmp", [a], ty=TInt, pos=pos)
        if name == "__longjmp":
            a = self.ce_value(e.args[0])
            return T.Intr("longjmp", [a], ty=TNever, pos=pos)
        if name == "__save_regs":
            a = self.ce_value(e.args[0])
            return T.Intr("save_regs", [a], ty=TVoid, pos=pos)
        if name == "__eq":
            a = self.ce_value(e.args[0])
            b = self.ce_as(e.args[1], a.ty)
            return self.eq_expr(a, b, pos)
        if name == "__cmp":
            a = self.ce_value(e.args[0])
            b = self.ce_as(e.args[1], a.ty)
            return self.cmp_expr(a, b, pos)
        if name == "__hash":
            a = self.ce_value(e.args[0])
            return self.hash_expr(a, pos)
        if name == "__str":
            return self.str_of(self.ce_value(e.args[0]))
        if name == "__debug":
            return self.str_of(self.ce_value(e.args[0]), nested=True)
        raise CompileError("unknown intrinsic " + name, pos)

    # ---- special forms ---------------------------------------------------------------------------
    def sf_print(self, e, expected, nl=False, err=False):
        pos = e.pos
        stmts = []
        fn = "eprint_str" if err else "print_str"
        parts = []
        for i, a in enumerate(e.args):
            if isinstance(a, S.NamedArg):
                raise CompileError("print does not take named arguments", a.pos)
            te = self.ce_value(a)
            s = self.str_of(te)
            if len(e.args) > 1 and not isinstance(s, (T.Const, T.VarRef)):
                s = self.bind_tmp(s, stmts)           # evaluate every argument before printing anything
            if i > 0:
                parts.append(T.Const("str", b" ", ty=TStr))
            parts.append(s)
        if nl:
            parts.append(T.Const("str", b"\n", ty=TStr))
        merged = []
        for p in parts:
            if isinstance(p, T.Const) and merged and isinstance(merged[-1], T.Const):
                merged[-1] = T.Const("str", merged[-1].value + p.value, ty=TStr)
            else:
                merged.append(p)
        if not merged:
            return T.Seq([], T.Const("int", 0, ty=TVoid), ty=TVoid, pos=pos)
        calls = [self.call_rt(fn, [m], pos=pos) for m in merged]
        if len(calls) == 1 and not stmts:
            return calls[0]
        return T.Seq(stmts + [T.ExprS(c) for c in calls[:-1]], calls[-1], ty=TVoid, pos=pos)

    def sf_println(self, e, expected):
        return self.sf_print(e, expected, nl=True)

    def sf_eprint(self, e, expected):
        return self.sf_print(e, expected, err=True)

    def sf_eprintln(self, e, expected):
        return self.sf_print(e, expected, nl=True, err=True)

    def one_arg(self, e, name):
        if len(e.args) != 1 or isinstance(e.args[0], S.NamedArg):
            raise CompileError("%s() takes exactly one argument" % name, e.pos)
        return self.ce_value(e.args[0])

    def sf_str(self, e, expected):
        return self.str_of(self.one_arg(e, "str"))

    def sf_int(self, e, expected):
        x = self.one_arg(e, "int")
        t = x.ty
        pos = e.pos
        if t == TInt:
            return x
        if t == TFloat:
            if isinstance(x, T.Const):
                return T.Const("int", int(x.value), ty=TInt, pos=pos)
            return T.Cvt("f2i", x, ty=TInt, pos=pos)
        if t in (TByte, TBool) or isinstance(t, TPtr) or (isinstance(t, TEnum) and t.info.simple):
            return T.Cvt("nop", x, ty=TInt, pos=pos)
        if t == TStr:
            return self.call_rt("str_to_int", [x], pos=pos)
        raise CompileError("cannot convert %s to int" % t, pos)

    def sf_float(self, e, expected):
        x = self.one_arg(e, "float")
        t = x.ty
        if t == TFloat:
            return x
        if t in (TInt, TByte):
            return self.coerce(x, TFloat)
        if t == TStr:
            return self.call_rt("str_to_float", [x], pos=e.pos)
        raise CompileError("cannot convert %s to float" % t, e.pos)

    def sf_byte(self, e, expected):
        x = self.one_arg(e, "byte")
        if x.ty == TByte:
            return x
        if x.ty == TFloat:
            x = T.Cvt("f2i", x, ty=TInt, pos=e.pos)
        if x.ty in (TInt, TBool):
            return T.Cvt("trunc8", x, ty=TByte, pos=e.pos)
        raise CompileError("cannot convert %s to byte" % x.ty, e.pos)

    def sf_bool(self, e, expected):
        x = self.one_arg(e, "bool")
        if x.ty == TBool:
            return x
        if x.ty in (TInt, TByte):
            return T.Bin("ne", self.coerce(x, TInt), self.ci(0), ty=TBool, pos=e.pos)
        if isinstance(x.ty, (TOpt, TPtr)):
            return T.Bin("ne", x, T.Const("nil", 0, ty=x.ty), ty=TBool, pos=e.pos)
        raise CompileError("cannot convert %s to bool" % x.ty, e.pos)

    def sf_include_str(self, e, expected):
        import os
        if len(e.args) != 1 or not isinstance(e.args[0], S.StrLit) or not all(isinstance(p, bytes) for p in e.args[0].parts):
            raise CompileError('include_str("file") needs a plain string with the file name', e.pos)
        name = b"".join(e.args[0].parts).decode("utf-8")
        path = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(e.pos.file)), name))
        if not os.path.exists(path):
            raise CompileError("include_str: cannot find '%s'" % name, e.pos)
        with open(path, "rb") as f:
            data = f.read()
        return T.Const("str", data, ty=TStr, pos=e.pos)

    def sf_copy(self, e, expected):
        x = self.one_arg(e, "copy")
        t = x.ty
        if isinstance(t, TStruct) and t.info is not self.array_info and t.info is not self.map_info:
            stmts = []
            xs = self.bind_tmp(x, stmts)
            vals = [T.Load(xs, i, ty=ft) for i, (_, ft) in enumerate(self.struct_fields(t))]
            return T.Seq(stmts, T.NewObj(vals, ty=t, pos=e.pos), ty=t, pos=e.pos)
        if isinstance(t, TTuple):
            stmts = []
            xs = self.bind_tmp(x, stmts)
            vals = [T.Load(xs, i, ty=et) for i, et in enumerate(t.elems)]
            return T.Seq(stmts, T.NewObj(vals, ty=t, pos=e.pos), ty=t, pos=e.pos)
        if t == TStr or t in (TInt, TFloat, TBool, TByte):
            return x
        r = self.try_method(x, "copy", [], e.pos)
        if r is None:
            raise CompileError("copy() works on structs, tuples, arrays and maps, found %s" % t, e.pos)
        return r

    def sf_same(self, e, expected):
        if len(e.args) != 2:
            raise CompileError("same(a, b) takes two values", e.pos)
        a = self.ce_value(e.args[0])
        b = self.ce_as(e.args[1], a.ty)
        if a.ty in (TInt, TFloat, TBool, TByte):
            raise CompileError("same() compares object identity; use == for numbers", e.pos)
        return T.Bin("eq", a, b, ty=TBool, pos=e.pos)

    def sf_assert(self, e, expected):
        pos = e.pos
        if not 1 <= len(e.args) <= 2:
            raise CompileError("assert(condition) or assert(condition, \"message\")", pos)
        c = self.ce_as(e.args[0], TBool)
        msg = self.ce_as(e.args[1], TStr) if len(e.args) == 2 else T.Const("str", b"assertion failed", ty=TStr)
        loc = T.Const("str", b"", ty=TStr)
        fail = self.call_rt("assert_fail", [msg, loc], pos=pos)
        return T.Seq([T.If(T.Un("not", c, ty=TBool), [T.ExprS(fail)], [])], T.Const("int", 0, ty=TVoid), ty=TVoid, pos=pos)

    def sf_panic(self, e, expected):
        pos = e.pos
        if len(e.args) != 1:
            raise CompileError('panic("message") takes one message', pos)
        msg = self.ce_value(e.args[0])
        msg = self.str_of(msg)
        loc = T.Const("str", b"", ty=TStr)
        c = self.call_rt("panic_at", [msg, loc], pos=pos)
        c.ty = TNever
        return c

    def sf_comprehension(self, e, expected):
        # [expr for names in iter if cond]  built as an array with push
        pos = e.pos
        elem_ast, names_t, iter_ast, cond_ast = e.args
        names = [p.decode() for p in (x.parts[0] for x in names_t.elems)]
        ph = []
        hint = expected.args[0] if isinstance(expected, TStruct) and expected.info is self.array_info else None
        # We build:  var $r: [?] = []  for names in iter { if cond { $r.push(expr) } }
        # element type is only known after checking `expr`, so check the loop pieces by hand.
        return self.build_comprehension(elem_ast, names, iter_ast, cond_ast, hint, pos)
