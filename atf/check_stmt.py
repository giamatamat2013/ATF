"""Statements, control flow, pattern matching."""
from . import syntax as S
from . import tir as T
from .errors import CompileError, SilentError
from .semtypes import *


class StmtMixin:
    # ------------------------------------------------------------------ blocks
    def check_block_stmts(self, stmts, new_scope=True):
        cx = self.cx
        if new_scope:
            cx.push()
        out = []
        try:
            for s in stmts:
                depth = len(cx.scopes)
                try:
                    self.check_stmt(s, out)
                except CompileError as e:
                    # report the error and keep checking the following statements
                    del cx.scopes[depth:]
                    del cx.defers[depth:]
                    if not isinstance(e, SilentError):
                        self.errors.append(e)
                    if isinstance(s, S.Let):
                        names = s.target if isinstance(s.target, list) else [s.target]
                        for n in names:
                            self.failed_names.add(n)
            if cx.defers[-1] and not self.terminates(out):
                self.emit_defers([cx.defers[-1]], out)
        finally:
            if new_scope:
                cx.pop()
        return out

    def check_value_block(self, block, expected=None):
        """check a block used as a value; returns (stmts, final_expr_or_None)"""
        cx = self.cx
        cx.push()
        out = []
        val = None
        stmts = block.stmts
        for i, s in enumerate(stmts):
            if i == len(stmts) - 1:
                s = self.stmt_as_expr(s)
                if isinstance(s, S.ExprStmt):
                    val = self.ce(s.expr, expected)
                    if val.ty == TVoid:
                        out.append(T.ExprS(val, pos=s.pos))
                        val = None
                    break
            self.check_stmt(s, out)
        if cx.defers[-1] and not self.terminates(out):
            self.emit_defers([cx.defers[-1]], out)
        cx.pop()
        return out, val

    def stmt_as_expr(self, s):
        if isinstance(s, S.If) and s.els is not None:
            return S.ExprStmt(S.IfExpr(s.cond, s.then, self.if_chain_as_expr(s.els), pos=s.pos), pos=s.pos)
        if isinstance(s, S.MatchStmt):
            return S.ExprStmt(S.MatchExpr(s.subject, s.arms, pos=s.pos), pos=s.pos)
        return s

    def if_chain_as_expr(self, e):
        if isinstance(e, S.If):
            return S.IfExpr(e.cond, e.then, self.if_chain_as_expr(e.els) if e.els is not None else None, pos=e.pos)
        return e

    # ------------------------------------------------------------------ termination analysis
    def terminates(self, stmts):
        for s in stmts:
            if self.stmt_terminates(s):
                return True
        return False

    def stmt_terminates(self, s):
        if isinstance(s, T.Ret):
            return True
        if isinstance(s, T.Blk):
            return self.terminates(s.stmts)
        if isinstance(s, T.If):
            if isinstance(s.c, T.Const) and s.c.value:
                return self.terminates(s.then)
            return bool(s.els) and self.terminates(s.then) and self.terminates(s.els)
        if isinstance(s, T.While):
            return isinstance(s.c, T.Const) and s.c.value == 1 and not self.has_break(s.body)
        if isinstance(s, T.ExprS):
            return self.expr_never(s.e)
        return False

    def expr_never(self, e):
        if e.ty == TNever:
            return True
        if isinstance(e, T.Seq):
            return self.terminates(e.stmts) or self.expr_never(e.e)
        return False

    def has_break(self, stmts):
        for s in stmts:
            if isinstance(s, T.Break):
                return True
            if isinstance(s, T.Blk) and self.has_break(s.stmts):
                return True
            if isinstance(s, T.If) and (self.has_break(s.then) or self.has_break(s.els or [])):
                return True
        return False

    # ------------------------------------------------------------------ defers / return
    def emit_defers(self, scope_lists, out):
        for lst in scope_lists:
            for d in reversed(lst):
                self.check_stmt(d, out)

    def all_defers(self, from_scope=0):
        return [self.cx.defers[i] for i in range(len(self.cx.defers) - 1, from_scope - 1, -1) if self.cx.defers[i]]

    # ------------------------------------------------------------------ dispatch
    def check_stmt(self, s, out):
        m = getattr(self, "s_" + s.__class__.__name__, None)
        if m is None:
            raise CompileError("unsupported statement %s" % s.__class__.__name__, s.pos)
        m(s, out)

    def s_ExprStmt(self, s, out):
        e = self.ce(s.expr)
        out.append(T.ExprS(e, pos=s.pos))

    def s_Block(self, s, out):
        out.append(T.Blk(self.check_block_stmts(s.stmts), pos=s.pos))

    def s_Defer(self, s, out):
        self.cx.defers[-1].append(s.stmt)

    # ------------------------------------------------------------------ let
    def default_value(self, ty, pos):
        if ty in (TInt, TByte):
            return T.Const("int", 0, ty=ty, pos=pos)
        if ty == TFloat:
            return T.Const("float", 0.0, ty=ty, pos=pos)
        if ty == TBool:
            return T.Const("bool", 0, ty=ty, pos=pos)
        if ty == TStr:
            return T.Const("str", b"", ty=ty, pos=pos)
        if isinstance(ty, (TOpt, TPtr)):
            return T.Const("nil", 0, ty=ty, pos=pos)
        if isinstance(ty, TEnum) and ty.info.simple:
            return T.Const("int", ty.info.tags[0], ty=ty, pos=pos)
        if isinstance(ty, TStruct) and ty.info is self.array_info:
            return self.call_rt("array_make", [self.ci(0)], targs=[ty.args[0]], pos=pos)
        if isinstance(ty, TStruct) and ty.info is self.map_info:
            return self.call_rt("map_new", [], targs=list(ty.args), pos=pos)
        raise CompileError("a variable of type %s needs an initial value" % ty, pos)

    def s_Let(self, s, out):
        cx = self.cx
        ty = self.resolve_type(s.type, cx.tscope) if s.type is not None else None
        init = None
        if s.init is not None:
            init = self.ce(s.init, ty)
            if init.ty == TVoid:
                raise CompileError("this expression does not produce a value", s.init.pos,
                                   "the function called here returns nothing")
            if ty is not None:
                init = self.coerce(init, ty, s.init.pos)
            else:
                if init.ty == TNil:
                    raise CompileError("cannot tell the type from 'nil'", s.pos, "add a type:  %s x: int? = nil" % ("var" if s.mutable else "let"))
                if init.ty == TNever:
                    raise CompileError("this expression never produces a value", s.init.pos)
        if isinstance(s.target, list):
            if init is None or not isinstance(init.ty, TTuple) or len(init.ty.elems) != len(s.target):
                raise CompileError("this pattern needs a tuple of %d values" % len(s.target), s.pos)
            stmts = []
            tup = self.bind_tmp(init, out)
            for i, name in enumerate(s.target):
                v = self.declare_var(name, init.ty.elems[i], s.mutable, s.pos)
                if name != "_":
                    out.append(T.Decl(v, T.Load(tup, i, ty=init.ty.elems[i]), pos=s.pos))
            return
        if init is None:
            init = self.default_value(ty, s.pos)
        v = self.declare_var(s.target, init.ty if ty is None else ty, s.mutable, s.pos)
        out.append(T.Decl(v, init, pos=s.pos))

    # ------------------------------------------------------------------ assignment
    def lvalue(self, t):
        """typed assignable place"""
        if isinstance(t, S.Ident):
            v = self.lookup_var(t.name)
            if v is not None:
                if not v.mutable:
                    raise CompileError("cannot assign to '%s' because it was declared with 'let'" % t.name, t.pos,
                                       "declare it with 'var %s = ...' to allow changes" % t.name)
                v.root.assigned = True
                self.touch(v)
                return T.VarRef(v, ty=v.ty, pos=t.pos)
            gi = self.globals.get(t.name)
            if gi is not None:
                g = self.resolve_global(gi)
                if not gi.decl.mutable:
                    raise CompileError("cannot assign to '%s' because it was declared with 'let'" % t.name, t.pos,
                                       "declare it with 'var' to allow changes")
                return T.GlobalRef(g, ty=g.ty, pos=t.pos)
            if t.name in self.consts:
                raise CompileError("cannot assign to the constant '%s'" % t.name, t.pos)
            raise CompileError("unknown variable '%s'" % t.name, t.pos, self.suggest_name(t.name))
        if isinstance(t, S.Field):
            obj = self.ce_value(t.obj)
            place = self.field_of(obj, t.name, t.pos)
            if isinstance(obj.ty, TTuple):
                raise CompileError("tuples cannot be modified", t.pos, "create a new tuple instead")
            return place
        if isinstance(t, S.Index):
            obj = self.ce_value(t.obj)
            ot = obj.ty
            if isinstance(ot, TStruct) and ot.info is self.array_info:
                return T.ArrIdx(obj, self.ce_as(t.index, TInt), self.esize(ot.args[0]), ty=ot.args[0], pos=t.pos)
            if isinstance(ot, TPtr):
                return T.PtrIdx(obj, self.ce_as(t.index, TInt), self.esize(ot.elem), ty=ot.elem, pos=t.pos)
            idx = self.ce_value(t.index)
            return ("index", obj, idx, t.pos)
        if isinstance(t, S.Unwrap):
            raise CompileError("cannot assign to the result of '!'", t.pos)
        raise CompileError("this cannot be assigned to", getattr(t, "pos", None))

    def suggest_name(self, name):
        from .checker import suggest
        return suggest(name, self.visible_names())

    def stabilize(self, place, out):
        if isinstance(place, T.Load):
            return T.Load(self.bind_tmp(place.obj, out), place.idx, ty=place.ty, pos=place.pos)
        if isinstance(place, T.ArrIdx):
            return T.ArrIdx(self.bind_tmp(place.arr, out), self.bind_tmp(place.idx, out), place.esize, ty=place.ty, pos=place.pos)
        if isinstance(place, T.PtrIdx):
            return T.PtrIdx(self.bind_tmp(place.base, out), self.bind_tmp(place.idx, out), place.esize, ty=place.ty, pos=place.pos)
        return place

    def s_Assign(self, s, out):
        place = self.lvalue(s.target)
        pos = s.pos
        if isinstance(place, tuple):                  # obj[idx] = v through op_set_index
            _, obj, idx, ipos = place
            if s.op == "=":
                # element type from op_set_index's value parameter
                hint = obj.ty.args[1] if isinstance(obj.ty, TStruct) and obj.ty.info is self.map_info else None
                val = self.ce_value(s.value, hint)
                call = self.try_method(obj, "op_set_index", [idx, val], pos)
                if call is None:
                    raise CompileError("%s does not support  x[i] = v" % obj.ty, pos)
                out.append(T.ExprS(call, pos=pos))
                return
            obj = self.bind_tmp(obj, out)
            idx = self.bind_tmp(idx, out)
            cur = self.try_method(obj, "op_index", [idx], pos)
            if cur is None:
                raise CompileError("%s cannot be indexed" % obj.ty, pos)
            rhs = self.ce_value(s.value, cur.ty if cur.ty in (TInt, TFloat) else None)
            val = self.binop(s.op[:-1], cur, rhs, pos)
            val = self.coerce(val, cur.ty, pos)
            call = self.try_method(obj, "op_set_index", [idx, val], pos)
            out.append(T.ExprS(call, pos=pos))
            return
        if s.op == "=":
            val = self.ce_value(s.value, place.ty)
            val = self.coerce(val, place.ty, s.value.pos)
            out.append(T.Set(place, val, pos=pos))
            return
        place = self.stabilize(place, out)
        rhs = self.ce_value(s.value, place.ty if place.ty in (TInt, TFloat) else None)
        val = self.binop(s.op[:-1], place, rhs, pos)
        val = self.coerce(val, place.ty, pos)
        out.append(T.Set(place, val, pos=pos))

    def touch(self, v):
        v.root.weight += 8 ** min(len(self.cx.loop_scope_depth), 5)

    # ------------------------------------------------------------------ return
    def s_Return(self, s, out):
        cx = self.cx
        pos = s.pos
        val = None
        if s.value is not None:
            val = self.ce(s.value, cx.ret if cx.ret not in (None, TVoid) else None)
        if cx.ret is None:                      # lambda with inferred return type
            if val is None or val.ty == TVoid:
                cx.ret = TVoid
            else:
                cx.ret = val.ty if val.ty != TNil else TNil
        ret = cx.ret
        if ret == TVoid or ret == TNever:
            if val is not None:
                if val.ty != TVoid:
                    raise CompileError("this function does not return a value", pos,
                                       "remove the value, or declare a return type:  fn name() -> int")
                out.append(T.ExprS(val, pos=pos))
            val = None
        else:
            if val is None:
                raise CompileError("this function must return a value of type %s" % ret, pos)
            val = self.coerce(val, ret, s.value.pos)
        self.emit_return(val, out, pos)

    def emit_return(self, val, out, pos):
        defers = self.all_defers()
        if defers:
            if val is not None:
                val = self.bind_tmp(val, out, "$ret")
            self.emit_defers(defers, out)
        out.append(T.Ret(val, pos=pos))

    # ------------------------------------------------------------------ if
    def s_If(self, s, out):
        cx = self.cx
        pos = s.pos
        if isinstance(s.cond, S.IfLet):
            out.append(self.if_let_stmt(s))
            return
        c = self.ce_as(s.cond, TBool)
        then = self.check_block_stmts(s.then.stmts)
        els = []
        if s.els is not None:
            if isinstance(s.els, S.If):
                self.s_If(s.els, els)
            else:
                els = self.check_block_stmts(s.els.stmts)
        out.append(T.If(c, then, els, pos=pos))

    def if_let_stmt(self, s):
        cx = self.cx
        subj = self.ce_value(s.cond.expr)
        pre = []
        subj = self.bind_tmp(subj, pre)
        cx.push()
        try:
            cond, decls = self.pattern_cond(s.cond.pat, subj, s.pos, True)
            then = decls + self.check_block_stmts(s.then.stmts)
        finally:
            cx.pop()
        els = []
        if s.els is not None:
            if isinstance(s.els, S.If):
                self.s_If(s.els, els)
            else:
                els = self.check_block_stmts(s.els.stmts)
        if cond is None:
            cond = T.Const("bool", 1, ty=TBool)
        return T.Blk(pre + [T.If(cond, then, els, pos=s.pos)], pos=s.pos)

    def if_let_expr(self, e, expected):
        cx = self.cx
        subj = self.ce_value(e.cond.expr)
        pre = []
        subj = self.bind_tmp(subj, pre)
        cx.push()
        try:
            cond, decls = self.pattern_cond(e.cond.pat, subj, e.pos, True)
            a_stmts, a = self.check_value_block(e.then, expected)
        finally:
            cx.pop()
        if isinstance(e.els, S.IfExpr):
            b = self.x_IfExpr(e.els, expected)
            b_stmts = []
        else:
            b_stmts, b = self.check_value_block(e.els, expected)
        if a is None or b is None:
            raise CompileError("both branches of an 'if' used as a value must end with a value", e.pos)
        a, b = self.join(a, b, e.pos)
        ty = b.ty if a.ty == TNever else a.ty
        if cond is None:
            cond = T.Const("bool", 1, ty=TBool)
        return T.Seq(pre, T.Cond(cond, T.Seq(decls + a_stmts, a, ty=a.ty), T.Seq(b_stmts, b, ty=b.ty), ty=ty, pos=e.pos), ty=ty, pos=e.pos)

    # ------------------------------------------------------------------ loops
    def loop_body(self, body_fn):
        cx = self.cx
        cx.loop_scope_depth.append(len(cx.scopes))
        try:
            return body_fn()
        finally:
            cx.loop_scope_depth.pop()

    def s_While(self, s, out):
        cx = self.cx
        pos = s.pos
        if isinstance(s.cond, S.IfLet):
            subj_ast = s.cond.expr

            def body_fn():
                stmts = []
                subj = self.ce_value(subj_ast)
                subj = self.bind_tmp(subj, stmts)
                cx.push()
                try:
                    cond, decls = self.pattern_cond(s.cond.pat, subj, pos, True)
                    inner = decls + self.check_block_stmts(s.body.stmts)
                finally:
                    cx.pop()
                if cond is not None:
                    stmts.append(T.If(T.Un("not", cond, ty=TBool), [T.Break()], []))
                return stmts + inner
            out.append(T.While(T.Const("bool", 1, ty=TBool), self.loop_body(body_fn), [], pos=pos))
            return
        c = self.ce_as(s.cond, TBool)
        body = self.loop_body(lambda: self.check_block_stmts(s.body.stmts))
        out.append(T.While(c, body, [], pos=pos))

    def s_Loop(self, s, out):
        body = self.loop_body(lambda: self.check_block_stmts(s.body.stmts))
        out.append(T.While(T.Const("bool", 1, ty=TBool), body, [], pos=s.pos))

    def break_defers(self, out):
        cx = self.cx
        depth = cx.loop_scope_depth[-1]
        lists = [cx.defers[i] for i in range(len(cx.defers) - 1, depth - 1, -1) if cx.defers[i]]
        if lists:
            self.emit_defers(lists, out)

    def s_Break(self, s, out):
        if not self.cx.loop_scope_depth:
            raise CompileError("'break' can only be used inside a loop", s.pos)
        self.break_defers(out)
        out.append(T.Break(pos=s.pos))

    def s_Continue(self, s, out):
        if not self.cx.loop_scope_depth:
            raise CompileError("'continue' can only be used inside a loop", s.pos)
        self.break_defers(out)
        out.append(T.Continue(pos=s.pos))

    def s_For(self, s, out):
        out.extend(self.lower_for(s.vars, s.iter, lambda: self.check_block_stmts(s.body.stmts), s.pos))

    def lower_for(self, names, it, body_fn, pos):
        cx = self.cx
        out = []
        # ---- range loops
        if isinstance(it, S.Range):
            if len(names) != 1:
                raise CompileError("a range loop has one variable:  for i in a..b", pos)
            if it.lo is None or it.hi is None:
                if it.hi is None and it.lo is not None:
                    pass
                else:
                    raise CompileError("a range loop needs a start:  for i in 0..n", pos)
            lo = self.ce_as(it.lo, TInt)
            hi = self.ce_as(it.hi, TInt) if it.hi is not None else None
            step = 1
            if it.step is not None:
                st = self.ce_as(it.step, TInt)
                if not isinstance(st, T.Const) or st.value == 0:
                    raise CompileError("'step' must be a non-zero constant number", it.step.pos)
                step = st.value
            cx.push()
            try:
                user = self.declare_var(names[0], TInt, False, pos)
                body = self.loop_body(body_fn)
            finally:
                cx.pop()
            end = None
            if hi is not None:
                end = hi
                if not isinstance(hi, T.Const):          # the end bound is evaluated once
                    ev = self.new_tmp(TInt, "$end")
                    out.append(T.Decl(ev, hi, pos=pos))
                    end = T.VarRef(ev, ty=TInt)
            if user.root.assigned or user.root.captured:
                cnt = self.new_tmp(TInt, "$i")
                out.append(T.Decl(cnt, lo, pos=pos))
                cur = T.VarRef(cnt, ty=TInt)
                body = [T.Decl(user, T.VarRef(cnt, ty=TInt), pos=pos)] + body
            else:
                out.append(T.Decl(user, lo, pos=pos))
                cur = T.VarRef(user, ty=TInt)
            if end is None:
                cond = T.Const("bool", 1, ty=TBool)
            else:
                if step > 0:
                    op = "le" if it.inclusive else "lt"
                else:
                    op = "ge" if it.inclusive else "gt"
                cond = T.Bin(op, cur, end, ty=TBool)
            inc = T.Set(cur, T.Bin("add", cur, self.ci(step), ty=TInt), pos=pos)
            weight_var = cur.var
            weight_var.root.weight += 8 ** min(len(cx.loop_scope_depth) + 1, 5) * 3
            out.append(T.While(cond, body, [inc], pos=pos))
            return out
        # ---- everything else: evaluate the iterable once
        coll = self.ce_value(it)
        ct = coll.ty
        coll = self.bind_tmp(coll, out, "$coll")
        if isinstance(ct, TStruct) and ct.info is self.array_info:
            elem = ct.args[0]
            es = self.esize(elem)
            if len(names) > 2:
                raise CompileError("for loops over arrays take at most two variables:  for i, x in arr", pos)
            idx = self.new_tmp(TInt, "$i")
            out.append(T.Decl(idx, self.ci(0), pos=pos))
            idxr = T.VarRef(idx, ty=TInt)
            cx.push()
            try:
                if len(names) == 2:
                    iv = self.declare_var(names[0], TInt, False, pos)
                    xv = self.declare_var(names[1], elem, False, pos)
                else:
                    iv = None
                    xv = self.declare_var(names[0], elem, False, pos)
                body = self.loop_body(body_fn)
            finally:
                cx.pop()
            data = T.PtrIdx(T.Load(coll, 0, ty=TPtr(elem)), idxr, es, ty=elem)
            pre = []
            if iv is not None:
                pre.append(T.Decl(iv, idxr, pos=pos))
            pre.append(T.Decl(xv, data, pos=pos))
            cond = T.Bin("lt", idxr, T.Load(coll, 1, ty=TInt), ty=TBool)
            inc = T.Set(idxr, T.Bin("add", idxr, self.ci(1), ty=TInt))
            idx.weight += 8 ** min(len(cx.loop_scope_depth) + 1, 5) * 3
            out.append(T.While(cond, pre + body, [inc], pos=pos))
            return out
        if ct == TStr:
            if len(names) > 2:
                raise CompileError("for loops over text take at most two variables:  for i, c in text", pos)
            idx = self.new_tmp(TInt, "$i")
            out.append(T.Decl(idx, self.ci(0), pos=pos))
            idxr = T.VarRef(idx, ty=TInt)
            cx.push()
            try:
                if len(names) == 2:
                    iv = self.declare_var(names[0], TInt, False, pos)
                    xv = self.declare_var(names[1], TStr, False, pos)
                else:
                    iv = None
                    xv = self.declare_var(names[0], TStr, False, pos)
                body = self.loop_body(body_fn)
            finally:
                cx.pop()
            pre = []
            if iv is not None:
                pre.append(T.Decl(iv, idxr, pos=pos))
            pre.append(T.Decl(xv, self.call_rt("char_str", [T.PtrIdx(T.Cvt("nop", coll, ty=TPtr(TByte)), T.Bin("add", idxr, self.ci(8), ty=TInt), 1, ty=TByte)]), pos=pos))
            cond = T.Bin("lt", idxr, T.Load(coll, 0, ty=TInt), ty=TBool)
            inc = T.Set(idxr, T.Bin("add", idxr, self.ci(1), ty=TInt))
            out.append(T.While(cond, pre + body, [inc], pos=pos))
            return out
        if isinstance(ct, TStruct) and ct.info is self.map_info:
            kt, vt = ct.args
            if len(names) > 2:
                raise CompileError("for loops over maps take at most two variables:  for k, v in map", pos)
            ks = self.new_tmp(TStruct(self.array_info, [kt]), "$keys")
            out.append(T.Decl(ks, self.try_method(coll, "keys", [], pos), pos=pos))
            vs = None
            if len(names) == 2:
                vs = self.new_tmp(TStruct(self.array_info, [vt]), "$vals")
                out.append(T.Decl(vs, self.try_method(coll, "values", [], pos), pos=pos))
            idx = self.new_tmp(TInt, "$i")
            out.append(T.Decl(idx, self.ci(0), pos=pos))
            idxr = T.VarRef(idx, ty=TInt)
            cx.push()
            try:
                kv = self.declare_var(names[0], kt, False, pos)
                vv = self.declare_var(names[1], vt, False, pos) if len(names) == 2 else None
                body = self.loop_body(body_fn)
            finally:
                cx.pop()
            pre = [T.Decl(kv, T.PtrIdx(T.Load(T.VarRef(ks, ty=ks.ty), 0, ty=TPtr(kt)), idxr, self.esize(kt), ty=kt), pos=pos)]
            if vv is not None:
                pre.append(T.Decl(vv, T.PtrIdx(T.Load(T.VarRef(vs, ty=vs.ty), 0, ty=TPtr(vt)), idxr, self.esize(vt), ty=vt), pos=pos))
            cond = T.Bin("lt", idxr, T.Load(T.VarRef(ks, ty=ks.ty), 1, ty=TInt), ty=TBool)
            inc = T.Set(idxr, T.Bin("add", idxr, self.ci(1), ty=TInt))
            out.append(T.While(cond, pre + body, [inc], pos=pos))
            return out
        raise CompileError("cannot loop over a value of type %s" % ct, pos,
                           "you can loop over ranges (0..10), arrays, text and maps")

    def build_comprehension(self, elem_ast, names, iter_ast, cond_ast, hint, pos):
        arr = T.Var("$comp", None, True)
        self.cx.inst.vars.append(arr)

        def body_fn():
            stmts = []
            self.cx.push()
            try:
                cond = None
                if not isinstance(cond_ast, S.NilLit):
                    cond = self.ce_as(cond_ast, TBool)
                el = self.ce_value(elem_ast, hint)
                if hint is not None:
                    el = self.coerce(el, hint, elem_ast.pos)
                if arr.ty is None:
                    if el.ty in (TNil, TNever):
                        raise CompileError("cannot tell the element type", pos)
                    arr.ty = TStruct(self.array_info, [el.ty])
                push = self.try_method(T.VarRef(arr, ty=arr.ty), "push", [el], pos)
                st = T.ExprS(push, pos=pos)
                if cond is not None:
                    stmts.append(T.If(cond, [st], [], pos=pos))
                else:
                    stmts.append(st)
            finally:
                self.cx.pop()
            return stmts

        if hint is not None:
            arr.ty = TStruct(self.array_info, [hint])
        loop = self.lower_for(names, iter_ast, body_fn, pos)
        decl = T.Decl(arr, self.call_rt("array_make", [self.ci(0)], targs=[arr.ty.args[0]], pos=pos), pos=pos)
        return T.Seq([decl] + loop, T.VarRef(arr, ty=arr.ty), ty=arr.ty, pos=pos)

    # ------------------------------------------------------------------ match
    def s_MatchStmt(self, s, out):
        out.extend(self.lower_match(s.subject, s.arms, False, None, s.pos)[0])

    def x_MatchExpr(self, e, expected=None):
        stmts, res = self.lower_match(e.subject, e.arms, True, expected, e.pos)
        return T.Seq(stmts, res, ty=res.ty, pos=e.pos)

    def pattern_cond(self, pat, subj, pos, unwrap=False):
        """returns (cond or None, [Decl...]) and declares the bound variables in the current scope.
        unwrap=True is used by `if let` / `while let`: a plain name then binds the unwrapped value of an optional."""
        binds = []
        cond = self.compile_pattern(pat, subj, binds, pos, unwrap)
        decls = []
        for name, val in binds:
            v = self.declare_var(name, val.ty, False, pos)
            decls.append(T.Decl(v, val, pos=pos))
        return cond, decls

    def and_(self, a, b):
        if a is None:
            return b
        if b is None:
            return a
        return T.And(a, b, ty=TBool)

    def compile_pattern(self, pat, subj, binds, pos, top=False):
        t = subj.ty
        if isinstance(pat, S.PWild):
            return None
        if isinstance(pat, S.PBind):
            n = pat.name
            if isinstance(t, TEnum) and n in t.info.vindex:
                return self.compile_pattern(S.PVariant([n], None, pos=pat.pos), subj, binds, pos)
            if isinstance(t, TOpt) and top:
                # `if let v = opt`  binds the unwrapped value; the condition is "not nil"
                binds.append((n, self.unwrap_opt(subj)))
                return T.Bin("ne", subj, T.Const("nil", 0, ty=t), ty=TBool)
            binds.append((n, subj))
            return None
        if isinstance(pat, S.PLit):
            lit = self.ce(pat.expr, t if not isinstance(t, TOpt) else None)
            if lit.ty == TNil:
                if not isinstance(t, (TOpt, TPtr)):
                    raise CompileError("%s can never be nil" % t, pat.pos)
                return T.Bin("eq", subj, T.Const("nil", 0, ty=t), ty=TBool)
            if isinstance(t, TOpt):
                raise CompileError("matching an optional against a value: bind it first with a name, or use  if let", pat.pos)
            if is_numeric(t) and is_numeric(lit.ty):
                return self.compare("==", subj, lit, pat.pos)
            if lit.ty != t:
                raise CompileError("this pattern has type %s but the value being matched is %s" % (lit.ty, t), pat.pos)
            return self.compare("==", subj, lit, pat.pos)
        if isinstance(pat, S.PRange):
            lo = self.ce(pat.lo, t)
            hi = self.ce(pat.hi, t)
            if not is_numeric(t):
                raise CompileError("range patterns work on numbers", pat.pos)
            c1 = self.compare(">=", subj, lo, pat.pos)
            c2 = self.compare("<=" if pat.inclusive else "<", subj, hi, pat.pos)
            return T.And(c1, c2, ty=TBool)
        if isinstance(pat, S.PTuple):
            if not isinstance(t, TTuple) or len(t.elems) != len(pat.elems):
                raise CompileError("this pattern has %d parts but the value is %s" % (len(pat.elems), t), pat.pos)
            c = None
            for i, p in enumerate(pat.elems):
                sub = T.Load(subj, i, ty=t.elems[i])
                c = self.and_(c, self.compile_pattern(p, sub, binds, pos))
            return c
        if isinstance(pat, S.POr):
            conds = []
            for alt in pat.alts:
                b2 = []
                c = self.compile_pattern(alt, subj, b2, pos)
                if b2:
                    raise CompileError("alternatives with '|' cannot bind names", alt.pos)
                conds.append(c)
            if any(c is None for c in conds):
                return None
            r = conds[0]
            for c in conds[1:]:
                r = T.Or(r, c, ty=TBool)
            return r
        if isinstance(pat, S.PVariant):
            if not isinstance(t, TEnum):
                raise CompileError("this pattern names an enum variant, but the value being matched is %s" % t, pat.pos)
            path = pat.path
            vname = path[-1]
            if len(path) == 2 and path[0] != t.info.name:
                raise CompileError("this pattern is for %s but the value is %s" % (path[0], t), pat.pos)
            if len(path) > 2:
                raise CompileError("bad pattern", pat.pos)
            if vname not in t.info.vindex:
                from .checker import suggest
                raise CompileError("%s has no variant '%s'" % (t.info.name, vname), pat.pos,
                                   suggest(vname, [v[0] for v in t.info.variants]))
            vi = t.info.vindex[vname]
            payload = self.variant_payload(t, vi)
            args = pat.args or []
            if pat.args is not None and len(args) != len(payload):
                raise CompileError("%s.%s carries %d value(s) but the pattern has %d" % (t.info.name, vname, len(payload), len(args)), pat.pos)
            if pat.args is None and payload:
                args = [S.PWild(pos=pat.pos)] * len(payload)
            if t.info.simple:
                cond = T.Bin("eq", subj, T.Const("int", t.info.tags[vi], ty=t), ty=TBool)
            else:
                cond = T.Bin("eq", T.Load(subj, 0, ty=TInt), self.ci(vi), ty=TBool)
            for i, (p, pt) in enumerate(zip(args, payload)):
                sub = T.Load(subj, i + 1, ty=pt)
                cond = self.and_(cond, self.compile_pattern(p, sub, binds, pos))
            return cond
        raise CompileError("unsupported pattern", pat.pos)

    def is_nil_like(self, n):
        return False

    def arm_covers(self, pat, subj_ty):
        """names of enum variants this pattern fully covers, or 'ALL'"""
        if isinstance(pat, S.PWild):
            return "ALL"
        if isinstance(pat, S.PBind):
            if isinstance(subj_ty, TEnum) and pat.name in subj_ty.info.vindex:
                return {pat.name}
            return "ALL"
        if isinstance(pat, S.PVariant):
            irrefutable = pat.args is None or all(self.arm_covers(a, None) == "ALL" for a in pat.args)
            return {pat.path[-1]} if irrefutable else set()
        if isinstance(pat, S.POr):
            res = set()
            for a in pat.alts:
                c = self.arm_covers(a, subj_ty)
                if c == "ALL":
                    return "ALL"
                res |= c
            return res
        if isinstance(pat, S.PLit) and isinstance(pat.expr, S.BoolLit):
            return {"true" if pat.expr.value else "false"}
        return set()

    def lower_match(self, subject_ast, arms, is_expr, expected, pos):
        cx = self.cx
        subj0 = self.ce_value(subject_ast)
        out = []
        subj = self.bind_tmp(subj0, out, "$m")
        st = subj.ty
        # exhaustiveness
        covered = set()
        total = False
        for arm in arms:
            if arm.guard is None:
                c = self.arm_covers(arm.pat, st)
                if c == "ALL":
                    total = True
                else:
                    covered |= c
        exhaustive = total
        if not total:
            if isinstance(st, TEnum):
                missing = [v[0] for v in st.info.variants if v[0] not in covered]
                if missing:
                    raise CompileError("this match does not cover: %s" % ", ".join("%s.%s" % (st.info.name, m) for m in missing), pos,
                                       "add the missing cases or a catch-all arm:  _ => ...")
                exhaustive = True
            elif st == TBool and covered >= {"true", "false"}:
                exhaustive = True
            elif is_expr:
                raise CompileError("a match used as a value must cover every case", pos, "add a catch-all arm:  _ => ...")
        result = None
        arm_vals = []
        compiled = []
        for arm in arms:
            cx.push()
            try:
                cond, decls = self.pattern_cond(arm.pat, subj, arm.pos)
                if arm.guard is not None:
                    g = self.ce_as(arm.guard, TBool)
                    gexpr = T.Seq(decls, g, ty=TBool)
                    cond = self.and_(cond, gexpr)
                    decls = []
                if is_expr:
                    if isinstance(arm.body, S.Block):
                        stmts, val = self.check_value_block(arm.body, expected)
                    else:
                        stmts, val = [], self.ce(arm.body, expected)
                    if val is None and self.terminates(stmts):
                        val = T.Const("int", 0, ty=TNever)
                    if val is None:
                        raise CompileError("this arm must end with a value", arm.pos)
                    if val.ty == TVoid:
                        raise CompileError("this arm does not produce a value", arm.pos)
                    arm_vals.append(val)
                    compiled.append((cond, decls, stmts, val))
                else:
                    if isinstance(arm.body, S.Block):
                        stmts = self.check_block_stmts(arm.body.stmts)
                    else:
                        be = self.ce(arm.body)
                        stmts = [T.ExprS(be, pos=arm.pos)]
                    compiled.append((cond, decls, stmts, None))
            finally:
                cx.pop()
        if is_expr:
            # common type
            ty = None
            for v in arm_vals:
                if v.ty == TNever:
                    continue
                if ty is None:
                    ty = v.ty
                elif self.try_coerce(v, ty) is not None:
                    pass
                elif is_numeric(ty) and is_numeric(v.ty) and v.ty == TFloat:
                    ty = TFloat
                elif isinstance(v.ty, TOpt) and self.try_coerce(T.Const("int", 0, ty=ty), v.ty) is not None:
                    ty = v.ty
                elif v.ty == TNil and isinstance(ty, (TStruct, TStr, TTuple, TFunc, TEnum)):
                    ty = TOpt(ty)
                elif isinstance(ty, TNil) or ty == TNil:
                    ty = TOpt(v.ty)
                else:
                    raise CompileError("the arms of this match have different types: %s and %s" % (ty, v.ty), pos)
            if ty is None:
                ty = TNever
            res = self.new_tmp(ty if ty != TNever else TInt, "$mr")
            resr = T.VarRef(res, ty=ty)
            out.append(T.Decl(res, None, pos=pos))
            chain = []
            tail = None
            if not exhaustive:
                if is_expr:
                    tail = [T.ExprS(self.call_rt("match_fail", [], pos=pos))]
            else:
                tail = [T.ExprS(self.call_rt("match_fail", [], pos=pos))]
            for (cond, decls, stmts, val), v in reversed(list(zip(compiled, arm_vals))):
                if val.ty != TNever:
                    val = self.coerce(val, ty, pos)
                    body = decls + stmts + [T.Set(T.VarRef(res, ty=ty), val, pos=pos)]
                else:
                    body = decls + stmts + [T.ExprS(val)]
                if cond is None:
                    cond = T.Const("bool", 1, ty=TBool)
                tail = [T.If(cond, body, tail or [], pos=pos)]
            out.extend(tail or [])
            return out, T.VarRef(res, ty=ty, pos=pos)
        tail = []
        if exhaustive:
            tail = [T.ExprS(self.call_rt("match_fail", [], pos=pos))]
        for (cond, decls, stmts, _) in reversed(compiled):
            if cond is None:
                cond = T.Const("bool", 1, ty=TBool)
            tail = [T.If(cond, decls + stmts, tail, pos=pos)]
        out.extend(tail)
        return out, None
