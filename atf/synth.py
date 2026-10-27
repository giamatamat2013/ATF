"""Type-directed helpers: to-string, equality, ordering and hashing (built-in, derived for user types)."""
from . import tir as T
from .errors import CompileError
from .semtypes import *


class SynthMixin:
    # ------------------------------------------------------------------ synthesized functions
    def get_synth(self, kind, ty, ret, nparams, builder):
        key = (kind, ty.key())
        inst = self.synth_cache.get(key)
        if inst is not None:
            return inst
        params = []
        for i in range(nparams):
            v = T.Var("x%d" % i, ty, True)
            v.is_param = True
            params.append(v)
        inst = T.FnInst("%s<%s>" % (kind, ty), params, ret)
        inst.vars = list(params)
        inst.is_prelude = True
        self.synth_cache[key] = inst
        self.program.funcs.append(inst)
        from .checker import FnCtx
        saved = self.cx
        self.cx = FnCtx(inst, {}, None, ret)
        try:
            inst.body = builder(inst, params)
        finally:
            self.cx = saved
        return inst

    def call_synth(self, inst, args, pos):
        self.cx.inst.callees.add(inst)
        return T.Call(inst, args, ty=inst.ret, pos=pos)

    def sconst(self, s):
        return T.Const("str", s.encode() if isinstance(s, str) else s, ty=TStr)

    def concat(self, parts):
        out = []
        for p in parts:
            if isinstance(p, T.Const) and out and isinstance(out[-1], T.Const):
                out[-1] = T.Const("str", out[-1].value + p.value, ty=TStr)
            else:
                out.append(p)
        r = out[0]
        for p in out[1:]:
            r = self.call_rt("str_concat", [r, p])
        return r

    # ------------------------------------------------------------------ to string
    def str_of(self, te, nested=False):
        t = te.ty
        pos = te.pos
        if t == TStr:
            if nested:
                return self.call_rt("quote_str", [te], pos=pos)
            return te
        if t == TInt or t == TByte:
            if isinstance(te, T.Const):
                return self.sconst(str(te.value))
            return self.call_rt("int_to_str", [T.Cvt("nop", te, ty=TInt) if t == TByte else te], pos=pos)
        if t == TFloat:
            return self.call_rt("float_to_str", [te], pos=pos)
        if t == TBool:
            if isinstance(te, T.Const):
                return self.sconst("true" if te.value else "false")
            return T.Cond(te, self.sconst("true"), self.sconst("false"), ty=TStr, pos=pos)
        if t == TNil:
            return self.sconst("nil")
        if t == TVoid:
            raise CompileError("this expression does not produce a value", pos)
        if t == TNever:
            return self.sconst("")
        if isinstance(t, TOpt):
            stmts = []
            x = self.bind_tmp(te, stmts)
            inner = self.str_of(self.unwrap_opt(x), nested=True)
            c = T.Cond(T.Bin("eq", x, T.Const("nil", 0, ty=t), ty=TBool), self.sconst("nil"), inner, ty=TStr, pos=pos)
            return T.Seq(stmts, c, ty=TStr, pos=pos) if stmts else c
        if isinstance(t, TFunc):
            return self.sconst("<function>")
        if isinstance(t, TPtr):
            return self.call_rt("int_to_hex", [T.Cvt("nop", te, ty=TInt)], pos=pos)
        if isinstance(t, TStruct) and t.info is self.array_info:
            return self.call_rt("array_to_str", [te], targs=[t.args[0]], pos=pos)
        if isinstance(t, TStruct) and t.info is self.map_info:
            return self.call_rt("map_to_str", [te], targs=list(t.args), pos=pos)
        if isinstance(t, (TStruct, TEnum, TTuple)):
            found = self.find_methods(t, "to_str") if not isinstance(t, TTuple) else []
            for impl, fi, binds in found:
                if fi.has_self and len(fi.decl.params) == 1:
                    r = self.invoke(fi, dict(binds), te, [], pos)
                    if r.ty == TStr:
                        return r
            inst = self.get_synth("str", t, TStr, 1, self.build_str)
            return self.call_synth(inst, [te], pos)
        raise CompileError("cannot convert %s to text" % t, pos)

    def build_str(self, inst, params):
        p = T.VarRef(params[0], ty=params[0].ty)
        t = params[0].ty
        if isinstance(t, TStruct):
            parts = [self.sconst(t.info.name + "{")]
            for i, (fname, fty) in enumerate(self.struct_fields(t)):
                if i:
                    parts.append(self.sconst(", "))
                parts.append(self.sconst(fname + ": "))
                parts.append(self.str_of(T.Load(p, i, ty=fty), nested=True))
            parts.append(self.sconst("}"))
            return [T.Ret(self.concat(parts))]
        if isinstance(t, TTuple):
            parts = [self.sconst("(")]
            for i, et in enumerate(t.elems):
                if i:
                    parts.append(self.sconst(", "))
                parts.append(self.str_of(T.Load(p, i, ty=et), nested=True))
            parts.append(self.sconst(")"))
            return [T.Ret(self.concat(parts))]
        # enum
        info = t.info
        body = []
        for vi, v in enumerate(info.variants):
            payload = self.variant_payload(t, vi)
            full = "%s.%s" % (info.name, v[0])
            if info.simple:
                cond = T.Bin("eq", p, T.Const("int", info.tags[vi], ty=t), ty=TBool)
                body.append(T.If(cond, [T.Ret(self.sconst(full))], []))
            else:
                cond = T.Bin("eq", T.Load(p, 0, ty=TInt), self.ci(vi), ty=TBool)
                if payload:
                    parts = [self.sconst(full + "(")]
                    for i, pt in enumerate(payload):
                        if i:
                            parts.append(self.sconst(", "))
                        parts.append(self.str_of(T.Load(p, i + 1, ty=pt), nested=True))
                    parts.append(self.sconst(")"))
                    r = self.concat(parts)
                else:
                    r = self.sconst(full)
                body.append(T.If(cond, [T.Ret(r)], []))
        body.append(T.Ret(self.sconst("?")))
        return body

    # ------------------------------------------------------------------ equality
    def eq_expr(self, a, b, pos):
        t = a.ty
        if t in (TInt, TByte, TBool) or isinstance(t, (TPtr, TFunc)) or (isinstance(t, TEnum) and t.info.simple):
            if isinstance(a, T.Const) and isinstance(b, T.Const):
                return T.Const("bool", int(a.value == b.value), ty=TBool, pos=pos)
            return T.Bin("eq", a, b, ty=TBool, pos=pos)
        if t == TFloat:
            if isinstance(a, T.Const) and isinstance(b, T.Const):
                return T.Const("bool", int(a.value == b.value), ty=TBool, pos=pos)
            return T.Bin("feq", a, b, ty=TBool, pos=pos)
        if t == TStr:
            if isinstance(a, T.Const) and isinstance(b, T.Const):
                return T.Const("bool", int(a.value == b.value), ty=TBool, pos=pos)
            return self.call_rt("str_eq", [a, b], pos=pos)
        if t == TNil:
            return T.Const("bool", 1, ty=TBool, pos=pos)
        if isinstance(t, TStruct) and t.info is self.array_info:
            return self.call_rt("array_eq", [a, b], targs=[t.args[0]], pos=pos)
        if isinstance(t, TStruct) and t.info is self.map_info:
            return self.call_rt("map_eq", [a, b], targs=list(t.args), pos=pos)
        if isinstance(t, (TStruct, TEnum)):
            for impl, fi, binds in self.find_methods(t, "eq"):
                if fi.has_self and len(fi.decl.params) == 2:
                    return self.invoke(fi, dict(binds), a, [b], pos)
        if isinstance(t, (TStruct, TEnum, TTuple, TOpt)):
            inst = self.get_synth("eq", t, TBool, 2, self.build_eq)
            return self.call_synth(inst, [a, b], pos)
        raise CompileError("cannot compare values of type %s with ==" % t, pos)

    def build_eq(self, inst, params):
        a = T.VarRef(params[0], ty=params[0].ty)
        b = T.VarRef(params[1], ty=params[0].ty)
        t = params[0].ty
        false = T.Ret(T.Const("bool", 0, ty=TBool))
        true = T.Ret(T.Const("bool", 1, ty=TBool))

        def field_checks(av, bv, ftys, off):
            out = []
            for i, ft in enumerate(ftys):
                eq = self.eq_expr(T.Load(av, i + off, ty=ft), T.Load(bv, i + off, ty=ft), None)
                out.append(T.If(T.Un("not", eq, ty=TBool), [false], []))
            return out

        if isinstance(t, TOpt):
            nil = T.Const("nil", 0, ty=t)
            body = [T.If(T.Bin("eq", a, b, ty=TBool), [true], []),
                    T.If(T.Or(T.Bin("eq", a, nil, ty=TBool), T.Bin("eq", b, nil, ty=TBool), ty=TBool), [false], [])]
            eq = self.eq_expr(self.unwrap_opt(a), self.unwrap_opt(b), None)
            body.append(T.Ret(eq))
            return body
        if isinstance(t, TStruct):
            body = [T.If(T.Bin("eq", a, b, ty=TBool), [true], [])]
            body += field_checks(a, b, [ft for _, ft in self.struct_fields(t)], 0)
            body.append(true)
            return body
        if isinstance(t, TTuple):
            body = field_checks(a, b, list(t.elems), 0)
            body.append(true)
            return body
        # enum with payload
        body = [T.If(T.Bin("eq", a, b, ty=TBool), [true], [])]
        body.append(T.If(T.Bin("ne", T.Load(a, 0, ty=TInt), T.Load(b, 0, ty=TInt), ty=TBool), [false], []))
        for vi in range(len(t.info.variants)):
            payload = self.variant_payload(t, vi)
            if payload:
                chk = field_checks(a, b, payload, 1)
                body.append(T.If(T.Bin("eq", T.Load(a, 0, ty=TInt), self.ci(vi), ty=TBool), chk + [true], []))
        body.append(true)
        return body

    # ------------------------------------------------------------------ ordering
    def cmp_expr(self, a, b, pos):
        t = a.ty
        if t in (TInt, TByte, TBool) or (isinstance(t, TEnum) and t.info.simple):
            return self.call_rt("cmp_int", [T.Cvt("nop", a, ty=TInt), T.Cvt("nop", b, ty=TInt)], pos=pos)
        if t == TFloat:
            return self.call_rt("cmp_float", [a, b], pos=pos)
        if t == TStr:
            return self.call_rt("str_cmp", [a, b], pos=pos)
        if isinstance(t, (TStruct, TEnum)):
            for impl, fi, binds in self.find_methods(t, "cmp"):
                if fi.has_self and len(fi.decl.params) == 2:
                    return self.invoke(fi, dict(binds), a, [b], pos)
        if isinstance(t, TTuple):
            inst = self.get_synth("cmp", t, TInt, 2, self.build_cmp)
            return self.call_synth(inst, [a, b], pos)
        raise CompileError("values of type %s cannot be ordered with < > <= >=" % t, pos,
                           "define  fn cmp(self, other: %s) -> int  in an impl block (negative, zero, or positive)" % t
                           if isinstance(t, (TStruct, TEnum)) else None)

    def build_cmp(self, inst, params):
        t = params[0].ty
        a = T.VarRef(params[0], ty=t)
        b = T.VarRef(params[1], ty=t)
        body = []
        for i, et in enumerate(t.elems):
            c = self.new_tmp(TInt, "$c")
            body.append(T.Decl(c, self.cmp_expr(T.Load(a, i, ty=et), T.Load(b, i, ty=et), None)))
            body.append(T.If(T.Bin("ne", T.VarRef(c, ty=TInt), self.ci(0), ty=TBool), [T.Ret(T.VarRef(c, ty=TInt))], []))
        body.append(T.Ret(self.ci(0)))
        return body

    # ------------------------------------------------------------------ hashing
    def hash_expr(self, a, pos):
        t = a.ty
        if t in (TInt, TByte, TBool) or (isinstance(t, TEnum) and t.info.simple) or isinstance(t, TPtr):
            return self.call_rt("hash_int", [T.Cvt("nop", a, ty=TInt)], pos=pos)
        if t == TFloat:
            return self.call_rt("hash_int", [T.Intr("f2bits", [a], ty=TInt)], pos=pos)
        if t == TStr:
            return self.call_rt("str_hash", [a], pos=pos)
        if isinstance(t, TStruct) and t.info is self.array_info:
            return self.call_rt("array_hash", [a], targs=[t.args[0]], pos=pos)
        if isinstance(t, (TStruct, TEnum)):
            for impl, fi, binds in self.find_methods(t, "hash"):
                if fi.has_self and len(fi.decl.params) == 1:
                    return self.invoke(fi, dict(binds), a, [], pos)
        if isinstance(t, (TStruct, TEnum, TTuple, TOpt)):
            inst = self.get_synth("hash", t, TInt, 1, self.build_hash)
            return self.call_synth(inst, [a], pos)
        raise CompileError("values of type %s cannot be used as map keys" % t, pos)

    def build_hash(self, inst, params):
        t = params[0].ty
        a = T.VarRef(params[0], ty=t)
        h = self.new_tmp(TInt, "$h")
        body = [T.Decl(h, self.ci(17))]

        def mix(e):
            hv = T.VarRef(h, ty=TInt)
            mixed = self.call_rt("hash_mix", [hv, self.hash_expr(e, None)])
            return T.Set(hv, mixed)

        if isinstance(t, TStruct):
            for i, (_, ft) in enumerate(self.struct_fields(t)):
                body.append(mix(T.Load(a, i, ty=ft)))
        elif isinstance(t, TTuple):
            for i, et in enumerate(t.elems):
                body.append(mix(T.Load(a, i, ty=et)))
        elif isinstance(t, TOpt):
            body.append(T.If(T.Bin("eq", a, T.Const("nil", 0, ty=t), ty=TBool), [T.Ret(self.ci(0))], []))
            body.append(mix(self.unwrap_opt(a)))
        else:
            body.append(mix(T.Load(a, 0, ty=TInt)))
            for vi in range(len(t.info.variants)):
                payload = self.variant_payload(t, vi)
                if payload:
                    inner = [mix(T.Load(a, i + 1, ty=pt)) for i, pt in enumerate(payload)]
                    body.append(T.If(T.Bin("eq", T.Load(a, 0, ty=TInt), self.ci(vi), ty=TBool), inner, []))
        body.append(T.Ret(T.VarRef(h, ty=TInt)))
        return body
