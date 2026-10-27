"""x86-64 (Windows x64 ABI) code generator for the typed IR."""
import struct

from . import tir as T
from .semtypes import *
from .x64 import *
from .pe import Image

INT_REGS = [RBX, RSI, RDI, R12, R13, R14, R15]
FLT_REGS = [XMM[i] for i in range(6, 16)]
ARG_REGS = [RCX, RDX, R8, R9]
ARG_XREGS = [XMM[0], XMM[1], XMM[2], XMM[3]]

CC_INT = {"eq": "e", "ne": "ne", "lt": "l", "le": "le", "gt": "g", "ge": "ge"}
CC_INV = {"e": "ne", "ne": "e", "l": "ge", "ge": "l", "le": "g", "g": "le", "a": "be", "be": "a", "ae": "b", "b": "ae",
          "p": "np", "np": "p"}
CC_SWAP = {"e": "e", "ne": "ne", "l": "g", "g": "l", "le": "ge", "ge": "le"}


def is_flt(ty):
    return ty == TFloat


class Walk:
    """collect variable usage weights (loop-depth weighted)"""

    def __init__(self):
        self.w = {}

    def stmts(self, ss, depth):
        for s in ss:
            self.node(s, depth)

    def node(self, n, depth):
        if n is None:
            return
        if isinstance(n, list):
            for x in n:
                self.node(x, depth)
            return
        if isinstance(n, T.VarRef):
            self.use(n.var, depth)
            return
        if isinstance(n, T.While):
            self.node(n.c, depth + 1)
            self.node(n.body, depth + 1)
            self.node(n.step, depth + 1)
            return
        if isinstance(n, T.Decl):
            self.use(n.var, depth)
            self.node(n.init, depth)
            return
        if isinstance(n, T.MkClosure):
            for c in n.caps:
                self.use(c, depth)
            return
        fields = getattr(n, "_fields", None)
        if fields:
            for f in fields:
                v = getattr(n, f)
                if isinstance(v, list) or hasattr(v, "_fields"):
                    self.node(v, depth)

    def use(self, var, depth):
        self.w[var] = self.w.get(var, 0) + (8 ** min(depth, 5))


class CodeGen:
    def __init__(self, program):
        self.prog = program
        self.a = Asm()
        self.img = Image()
        self.strs = {}
        self.flts = {}
        self.rdata = self.img.rdata
        self.nconst = 0
        self.stubs = []
        self.callsites = []        # (return offset, line, FnInst)
        self.cur_inst = None

    # ------------------------------------------------------------------ constants
    def str_sym(self, b):
        sym = self.strs.get(b)
        if sym is None:
            while len(self.rdata) % 8:
                self.rdata.append(0)
            sym = "str%d" % len(self.strs)
            self.img.symbols[sym] = ("rdata", len(self.rdata))
            self.rdata += struct.pack("<q", len(b)) + b + b"\0"
            self.strs[b] = sym
        return sym

    def flt_sym(self, v):
        bits = struct.unpack("<Q", struct.pack("<d", v))[0]
        sym = self.flts.get(bits)
        if sym is None:
            while len(self.rdata) % 16:
                self.rdata.append(0)
            sym = "flt%d" % len(self.flts)
            self.img.symbols[sym] = ("rdata", len(self.rdata))
            self.rdata += struct.pack("<Q", bits) + b"\0" * 8
            self.flts[bits] = sym
        return sym

    # ------------------------------------------------------------------ program
    def generate(self):
        a = self.a
        prog = self.prog
        for f in prog.funcs:
            f.label = a.new_label()
        # entry point
        entry_off = a.here()
        a.sub(RSP, 40)
        a.call(prog.entry.label)
        a.ud2()
        for f in prog.funcs:
            self.gen_func(f)
        # data layout for globals
        off = 0
        for g in prog.globals:
            self.img.symbols[g.sym] = ("data", off)
            off += 8
        self.img.data_size = max(off, 16)
        self.img.symbols["data_start"] = ("data", 0)
        self.img.symbols["data_end"] = ("data", off)
        self.img.text = a.finish()
        self.img.text_relocs = a.relocs
        self.build_traceback_table()
        self.img.symbols["text_start"] = ("text", 0)
        self.img.entry = entry_off
        return self.img

    def build_traceback_table(self):
        from .errors import short_path
        a = self.a
        funcs = sorted(self.prog.funcs, key=lambda f: a.labels[f.label])
        fidx = {f: i for i, f in enumerate(funcs)}
        names = bytearray()
        pool = {}

        def intern(t):
            if t not in pool:
                pool[t] = len(names)
                names.extend(t.encode("utf-8") + b"\0")
            return pool[t]

        words = [len(self.callsites), len(funcs), 0, len(a.buf)]
        calls = []
        for off, line, inst in self.callsites:
            flag = 1 << 62 if (inst is None or inst.is_prelude) else 0
            calls.append((off, line | (fidx.get(inst, 0) << 32) | flag))
        calls.sort()
        fwords = []
        import os
        for f in funcs:
            fwords += [a.labels[f.label], intern(f.name), intern(os.path.basename(f.pos.file) if f.pos and f.pos.file else "?")]
        blob = bytearray()
        names_off = (4 + 2 * len(calls) + 3 * len(funcs)) * 8
        words[2] = names_off
        for w in words:
            blob += struct.pack("<q", w)
        for off, v in calls:
            blob += struct.pack("<qq", off, v)
        for w in fwords:
            blob += struct.pack("<q", w)
        blob += names
        while len(self.rdata) % 8:
            self.rdata.append(0)
        self.img.symbols["tb"] = ("rdata", len(self.rdata))
        self.rdata += blob

    # ------------------------------------------------------------------ per-function
    def gen_func(self, inst):
        a = self.a
        self.inst = inst
        self.cur_inst = inst
        self.loops = []
        self.stubs = []
        self.free_tmps = []
        self.ret_label = a.new_label()
        a.bind(inst.label)
        # ---- usage weights → register assignment
        w = Walk()
        w.stmts(inst.body, 0)
        for p in inst.params:
            w.use(p, 0)
        self.cur = 0            # bytes allocated below rbp
        self.max = 0
        saved_regs = []
        used_int = []
        used_flt = []
        cands = sorted(inst.vars, key=lambda v: -w.w.get(v, 0))
        ints = list(INT_REGS)
        flts = list(FLT_REGS)
        for v in cands:
            v.loc = None
        for v in cands:
            wt = w.w.get(v, 0)
            if v.boxed or wt < 2:
                continue
            if is_flt(v.ty):
                if flts:
                    r = flts.pop(0)
                    v.loc = r
                    used_flt.append(r)
            else:
                if ints:
                    r = ints.pop(0)
                    v.loc = r
                    used_int.append(r)
        # frame layout
        self.save_slots = {}
        for r in used_int:
            self.save_slots[r] = self.alloc_slot(8)
        for r in used_flt:
            self.save_slots[r] = self.alloc_slot(16)
        self.env_slot = None
        if inst.is_lambda:
            self.env_slot = self.alloc_slot(8)
        nparams = len(inst.params)
        for i, p in enumerate(inst.params):
            if p.loc is None and not p.boxed:
                if i >= 4:
                    p.loc = Mem(RBP, disp=48 + 8 * (i - 4))
        for v in inst.vars:
            if v.loc is None:
                v.loc = Mem(RBP, disp=self.alloc_slot(8))
        self.max_out = 32
        # ---- prologue
        a.push(RBP)
        a.mov(RBP, RSP)
        a.buf += b"\x48\x81\xEC\0\0\0\0"          # sub rsp, imm32 (patched)
        frame_patch = len(a.buf) - 4
        for r in used_int:
            a.mov(Mem(RBP, disp=self.save_slots[r]), r)
        for r in used_flt:
            a.movups_store(Mem(RBP, disp=self.save_slots[r]), r)
        if inst.is_lambda:
            a.mov(Mem(RBP, disp=self.env_slot), R10)
        # parameters: first park every register argument, then box the ones that need cells
        boxed_params = []
        for i, p in enumerate(inst.params):
            if p.boxed:
                t = self.tmp()
                if i < 4:
                    if is_flt(p.ty):
                        a.movsd(Mem(RBP, disp=t), ARG_XREGS[i])
                    else:
                        a.mov(Mem(RBP, disp=t), ARG_REGS[i])
                else:
                    a.mov(RAX, Mem(RBP, disp=48 + 8 * (i - 4)))
                    a.mov(Mem(RBP, disp=t), RAX)
                boxed_params.append((p, t))
            else:
                self.prologue_param(p, i)
        for p, t in boxed_params:
            a.mov(RCX, 8)
            a.call(self.prog.alloc.label)
            a.mov(RCX, Mem(RBP, disp=t))
            a.mov(Mem(RAX), RCX)
            a.mov(p.loc, RAX)
            self.untmp(t)
        if inst.is_lambda:
            for i, outer in enumerate(inst.captures):
                inner = inst.capture_inner[outer]
                a.mov(RAX, Mem(RBP, disp=self.env_slot))
                a.mov(RAX, Mem(RAX, disp=8 + 8 * i))
                if inner.boxed:
                    a.mov(inner.loc, RAX)
                elif is_flt(inner.ty):
                    if isinstance(inner.loc, XReg):
                        a.movq_to_x(inner.loc, RAX)
                    else:
                        a.mov(inner.loc, RAX)
                else:
                    a.mov(inner.loc, RAX)
        # ---- body
        self.gen_stmts(inst.body)
        # fall off the end
        if inst.ret == TVoid or inst.ret == TNever:
            pass
        a.bind(self.ret_label)
        for r in used_int:
            a.mov(r, Mem(RBP, disp=self.save_slots[r]))
        for r in used_flt:
            a.movups_load(r, Mem(RBP, disp=self.save_slots[r]))
        a.leave()
        a.ret()
        # stubs (cold paths)
        for (label, kind, line, extra) in self.stubs:
            a.bind(label)
            if kind == "bounds":
                if isinstance(extra, int):
                    a.mov_imm(RDX, extra)
                else:
                    a.mov(RDX, extra)
                a.mov(R8, Mem(RAX, disp=8))
                a.mov(RCX, line)
                a.call(self.prog.rt["bounds_fail"].label)
                self.mark_call(line)
            elif kind == "bounds_c":
                a.mov(R8, Mem(RCX, disp=8))
                a.mov(RCX, line)
                a.call(self.prog.rt["bounds_fail"].label)
                self.mark_call(line)
            elif kind == "div":
                a.mov(RCX, line)
                a.call(self.prog.rt["div_fail"].label)
                self.mark_call(line)
            a.ud2()
        total = self.max + self.max_out
        total = (total + 15) & ~15
        struct.pack_into("<i", a.buf, frame_patch, total)

    def alloc_slot(self, size):
        self.cur += size
        if self.cur % 8:
            self.cur += 8 - self.cur % 8
        if size == 16 and self.cur % 16:
            pass
        self.max = max(self.max, self.cur)
        return -self.cur

    def tmp(self):
        if self.free_tmps:
            return self.free_tmps.pop()
        return self.alloc_slot(8)

    def untmp(self, off):
        self.free_tmps.append(off)

    def prologue_param(self, p, i):
        a = self.a
        if i < 4:
            if is_flt(p.ty):
                src = ARG_XREGS[i]
                if isinstance(p.loc, XReg):
                    if p.loc.n != src.n:
                        a.movsd(p.loc, src)
                else:
                    a.movsd(p.loc, src)
            else:
                a.mov(p.loc, ARG_REGS[i])
        else:
            m = Mem(RBP, disp=48 + 8 * (i - 4))
            if isinstance(p.loc, Mem) and p.loc.base is RBP and p.loc.disp == m.disp:
                return
            if is_flt(p.ty):
                a.movsd(p.loc, m)
            else:
                a.mov(p.loc, m)

    # ------------------------------------------------------------------ statements
    def gen_stmts(self, ss):
        for s in ss:
            self.gen_stmt(s)

    def gen_stmt(self, s):
        a = self.a
        if isinstance(s, T.ExprS):
            self.gen(s.e)
        elif isinstance(s, T.Decl):
            self.gen_decl(s)
        elif isinstance(s, T.Set):
            self.gen_set(s)
        elif isinstance(s, T.If):
            self.gen_if(s)
        elif isinstance(s, T.While):
            self.gen_while(s)
        elif isinstance(s, T.Ret):
            if s.e is not None:
                self.gen(s.e)
            a.jmp(self.ret_label)
        elif isinstance(s, T.Break):
            a.jmp(self.loops[-1][0])
        elif isinstance(s, T.Continue):
            a.jmp(self.loops[-1][1])
        elif isinstance(s, T.Blk):
            self.gen_stmts(s.stmts)
        else:
            raise Exception("codegen: unknown statement %r" % (s,))

    def gen_if(self, s):
        a = self.a
        if isinstance(s.c, T.Const):
            self.gen_stmts(s.then if s.c.value else s.els)
            return
        lelse = a.new_label()
        self.branch(s.c, lelse, False)
        self.gen_stmts(s.then)
        if s.els:
            lend = a.new_label()
            a.jmp(lend)
            a.bind(lelse)
            self.gen_stmts(s.els)
            a.bind(lend)
        else:
            a.bind(lelse)

    def gen_while(self, s):
        a = self.a
        lbody = a.new_label()
        lcont = a.new_label()
        lcond = a.new_label()
        lend = a.new_label()
        self.loops.append((lend, lcont))
        if not (isinstance(s.c, T.Const) and s.c.value):
            a.jmp(lcond)
        a.bind(lbody)
        self.gen_stmts(s.body)
        a.bind(lcont)
        self.gen_stmts(s.step)
        a.bind(lcond)
        if isinstance(s.c, T.Const):
            if s.c.value:
                a.jmp(lbody)
        else:
            self.branch(s.c, lbody, True)
        a.bind(lend)
        self.loops.pop()

    def gen_decl(self, s):
        a = self.a
        v = s.var
        if v.boxed:
            # allocate the cell first, then evaluate the initializer
            if s.init is not None:
                self.gen(s.init)
                t = self.tmp()
                if is_flt(v.ty):
                    a.movsd(Mem(RBP, disp=t), XMM[0])
                else:
                    a.mov(Mem(RBP, disp=t), RAX)
            a.mov(RCX, 8)
            a.call(self.prog.alloc.label)
            a.mov(v.loc, RAX)
            if s.init is not None:
                a.mov(RCX, Mem(RBP, disp=t))
                a.mov(Mem(RAX), RCX)
                self.untmp(t)
            return
        if s.init is None:
            self.zero_var(v)
            return
        self.store_var(v, s.init)

    def zero_var(self, v):
        a = self.a
        if isinstance(v.loc, Reg):
            a.mov_imm(v.loc, 0)
        elif isinstance(v.loc, XReg):
            a.xorpd(v.loc, v.loc)
        else:
            a.mov(v.loc, 0)

    def store_var(self, v, e):
        """v = e for a non-boxed variable"""
        a = self.a
        loc = v.loc
        if is_flt(v.ty):
            if isinstance(e, T.VarRef) and not e.var.boxed and isinstance(e.var.loc, XReg) and isinstance(loc, XReg):
                a.movsd(loc, e.var.loc)
                return
            self.gen(e)
            if isinstance(loc, XReg):
                if loc.n != 0:
                    a.movsd(loc, XMM[0])
            else:
                a.movsd(loc, XMM[0])
            return
        op = self.operand(e)
        if isinstance(loc, Reg):
            if isinstance(op, int):
                a.mov_imm(loc, op)
            elif op is not None:
                a.mov(loc, op)
            else:
                self.gen_to_reg(e, loc)
            return
        # memory destination
        if isinstance(op, int):
            a.mov(loc, op)
        elif isinstance(op, Reg):
            a.mov(loc, op)
        else:
            self.gen(e)
            a.mov(loc, RAX)

    def gen_to_reg(self, e, reg):
        self.gen(e)
        self.a.mov(reg, RAX)

    def gen_set(self, s):
        a = self.a
        tgt = s.target
        val = s.value
        if isinstance(tgt, T.VarRef):
            v = tgt.var
            if v.boxed:
                self.gen(val)
                a.mov(RCX, v.loc)
                if is_flt(v.ty):
                    a.movsd(Mem(RCX), XMM[0])
                else:
                    a.mov(Mem(RCX), RAX)
                return
            # in-place update  x = x op y
            if isinstance(val, T.Bin) and val.l.__class__ is T.VarRef and val.l.var is v and not is_flt(v.ty) and \
                    val.op in ("add", "sub", "and", "or", "xor"):
                ro = self.operand(val.r)
                if ro is not None and not (isinstance(v.loc, Mem) and isinstance(ro, Mem)):
                    a.alu(val.op, v.loc, ro)
                    return
            self.store_var(v, val)
            return
        if isinstance(tgt, T.GlobalRef):
            self.gen(val)
            m = Mem(sym=tgt.glob.sym)
            if is_flt(tgt.ty):
                a.movsd(m, XMM[0])
            else:
                a.mov(m, RAX)
            return
        # memory places: field / array element / raw pointer element
        fl = is_flt(tgt.ty)
        vop = None if fl else self.operand(val)
        if isinstance(tgt, T.Load):
            if self.is_cheap(tgt.obj):
                if vop is None or isinstance(vop, Mem):
                    self.gen(val)
                    vop = None
                self.load_cheap(RCX, tgt.obj)
            else:
                self.gen(val)
                t = self.tmp()
                self.spill(t, fl)
                self.gen(tgt.obj)
                a.mov(RCX, RAX)
                self.reload(t, fl)
                self.untmp(t)
                vop = None
            self.store_to(Mem(RCX, disp=8 * tgt.idx), tgt.ty, vop)
            return
        if isinstance(tgt, (T.ArrIdx, T.PtrIdx)):
            arr = tgt.arr if isinstance(tgt, T.ArrIdx) else tgt.base
            if self.is_cheap(arr) and self.is_cheap(tgt.idx):
                if vop is None or isinstance(vop, Mem):
                    self.gen(val)
                    vop = None
                self.load_cheap(RCX, arr)
                self.load_cheap(RDX, tgt.idx)
            else:
                self.gen(val)
                t = self.tmp()
                self.spill(t, fl)
                self.gen(arr)
                t2 = self.tmp()
                a.mov(Mem(RBP, disp=t2), RAX)
                self.gen(tgt.idx)
                a.mov(RDX, RAX)
                a.mov(RCX, Mem(RBP, disp=t2))
                self.untmp(t2)
                self.reload(t, fl)
                self.untmp(t)
                vop = None
            if isinstance(tgt, T.ArrIdx):
                stub = a.new_label()
                self.stubs.append((stub, "bounds_c", tgt.pos.line, None))
                a.cmp(RDX, Mem(RCX, disp=8))
                a.jcc("ae", stub)
                a.mov(RCX, Mem(RCX))
            if tgt.esize == 1:
                if isinstance(vop, int):
                    self.store8_imm(Mem(RCX, RDX, 1), vop)
                else:
                    if vop is not None:
                        a.mov(RAX, vop)
                    a.mov_mem_reg8(Mem(RCX, RDX, 1), RAX)
            else:
                self.store_to(Mem(RCX, RDX, 8), tgt.ty, vop)
            return
        raise Exception("codegen: bad assignment target %r" % (tgt,))

    def store8_imm(self, m, v):
        self.a._emit(b"\xC6", 0, m, 0, imm=bytes([v & 255]))

    def store_to(self, m, ty, vop):
        a = self.a
        if is_flt(ty):
            a.movsd(m, XMM[0])
        elif vop is None:
            a.mov(m, RAX)
        elif isinstance(vop, int):
            a.mov(m, vop)
        elif isinstance(vop, Reg):
            a.mov(m, vop)
        else:
            a.mov(RAX, vop)
            a.mov(m, RAX)

    def spill(self, off, fl):
        if fl:
            self.a.movsd(Mem(RBP, disp=off), XMM[0])
        else:
            self.a.mov(Mem(RBP, disp=off), RAX)

    def reload(self, off, fl):
        if fl:
            self.a.movsd(XMM[0], Mem(RBP, disp=off))
        else:
            self.a.mov(RAX, Mem(RBP, disp=off))

    # ------------------------------------------------------------------ operands
    def operand(self, e):
        """Reg / Mem / int immediate usable directly as a source operand (int class), else None"""
        if isinstance(e, T.Const):
            if e.kind in ("int", "bool", "nil"):
                v = e.value
                if -(1 << 31) <= v < (1 << 31):
                    return v
            return None
        if isinstance(e, T.VarRef):
            v = e.var
            if v.boxed or is_flt(v.ty):
                return None
            return v.loc
        if isinstance(e, T.GlobalRef) and not is_flt(e.ty):
            return Mem(sym=e.glob.sym)
        if isinstance(e, T.Cvt) and e.kind == "nop" and not is_flt(e.e.ty):
            return self.operand(e.e) if isinstance(self.operand(e.e), (Reg, int)) else None
        return None

    def foperand(self, e):
        if isinstance(e, T.Const) and e.kind == "float":
            return Mem(sym=self.flt_sym(e.value))
        if isinstance(e, T.VarRef):
            v = e.var
            if v.boxed:
                return None
            return v.loc
        if isinstance(e, T.GlobalRef):
            return Mem(sym=e.glob.sym)
        return None

    def is_cheap(self, e):
        """can be loaded into a register without clobbering anything"""
        if isinstance(e, T.Cvt) and e.kind == "nop":
            return self.is_cheap(e.e)
        op = self.operand(e)
        return op is not None

    def load_cheap(self, reg, e):
        op = self.operand(e)
        if isinstance(op, int):
            self.a.mov_imm(reg, op)
        elif op is reg:
            pass
        else:
            self.a.mov(reg, op)

    # ------------------------------------------------------------------ expressions
    def gen(self, e):
        """evaluate e: int-class results in RAX, floats in XMM0, void: nothing"""
        a = self.a
        m = getattr(self, "g_" + e.__class__.__name__)
        m(e)

    def g_Const(self, e):
        a = self.a
        if e.kind == "float":
            if e.value == 0.0 and str(e.value)[0] != "-":
                a.xorpd(XMM[0], XMM[0])
            else:
                a.movsd(XMM[0], Mem(sym=self.flt_sym(e.value)))
        elif e.kind == "str":
            a.lea(RAX, Mem(sym=self.str_sym(e.value)))
        else:
            if e.ty == TVoid:
                return
            a.mov_imm(RAX, e.value)

    def g_VarRef(self, e):
        a = self.a
        v = e.var
        if v.boxed:
            a.mov(RAX, v.loc)
            if is_flt(v.ty):
                a.movsd(XMM[0], Mem(RAX))
            else:
                a.mov(RAX, Mem(RAX))
            return
        if is_flt(v.ty):
            if isinstance(v.loc, XReg):
                if v.loc.n != 0:
                    a.movsd(XMM[0], v.loc)
            else:
                a.movsd(XMM[0], v.loc)
        else:
            a.mov(RAX, v.loc)

    def g_GlobalRef(self, e):
        a = self.a
        if is_flt(e.ty):
            a.movsd(XMM[0], Mem(sym=e.glob.sym))
        else:
            a.mov(RAX, Mem(sym=e.glob.sym))

    def g_FnRef(self, e):
        a = self.a
        a.mov(RCX, 8)
        a.call(self.prog.alloc.label)
        a.lea_label(RCX, e.inst.label)
        a.mov(Mem(RAX), RCX)

    def g_MkClosure(self, e):
        a = self.a
        n = len(e.caps)
        a.mov(RCX, 8 * (1 + n))
        a.call(self.prog.alloc.label)
        a.lea_label(RCX, e.inst.label)
        a.mov(Mem(RAX), RCX)
        for i, c in enumerate(e.caps):
            if c.boxed:
                a.mov(RCX, c.loc)
            elif is_flt(c.ty):
                if isinstance(c.loc, XReg):
                    a.movq_to_r(RCX, c.loc)
                else:
                    a.mov(RCX, c.loc)
            else:
                a.mov(RCX, c.loc)
            a.mov(Mem(RAX, disp=8 + 8 * i), RCX)

    def g_Seq(self, e):
        self.gen_stmts(e.stmts)
        self.gen(e.e)

    def g_Cond(self, e):
        a = self.a
        lelse = a.new_label()
        lend = a.new_label()
        self.branch(e.c, lelse, False)
        self.gen(e.a)
        a.jmp(lend)
        a.bind(lelse)
        self.gen(e.b)
        a.bind(lend)

    def g_Cvt(self, e):
        a = self.a
        k = e.kind
        if k == "nop":
            self.gen(e.e)
        elif k == "i2f":
            op = self.operand(e.e)
            if isinstance(op, (Reg, Mem)):
                a.xorpd(XMM[0], XMM[0])
                a.cvtsi2sd(XMM[0], op)
            else:
                self.gen(e.e)
                a.xorpd(XMM[0], XMM[0])
                a.cvtsi2sd(XMM[0], RAX)
        elif k == "f2i":
            self.gen(e.e)
            a.cvttsd2si(RAX, XMM[0])
        elif k == "trunc8":
            self.gen(e.e)
            a.movzx8(RAX, RAX)
        else:
            raise Exception("cvt " + k)

    def g_Un(self, e):
        a = self.a
        self.gen(e.e)
        if e.op == "neg":
            a.neg(RAX)
        elif e.op == "not":
            a.xor(RAX, 1)
        elif e.op == "bnot":
            a.not_(RAX)
        elif e.op == "fneg":
            a.mov_imm(RAX, -(1 << 63))
            a.movq_to_x(XMM[1], RAX)
            a.xorpd(XMM[0], XMM[1])
        else:
            raise Exception("un " + e.op)

    def g_And(self, e):
        self.bool_value(e)

    def g_Or(self, e):
        self.bool_value(e)

    def bool_value(self, e):
        a = self.a
        lf = a.new_label()
        lend = a.new_label()
        self.branch(e, lf, False)
        a.mov_imm_keepflags(RAX, 1)
        a.jmp(lend)
        a.bind(lf)
        a.mov_imm(RAX, 0)
        a.bind(lend)

    def g_Load(self, e):
        a = self.a
        if self.is_cheap(e.obj):
            op = self.operand(e.obj)
            base = op if isinstance(op, Reg) else None
            if base is None:
                self.load_cheap(RAX, e.obj)
                base = RAX
        else:
            self.gen(e.obj)
            base = RAX
        m = Mem(base, disp=8 * e.idx)
        if is_flt(e.ty):
            a.movsd(XMM[0], m)
        else:
            a.mov(RAX, m)

    def g_PtrIdx(self, e):
        a = self.a
        self.base_idx(e.base, e.idx)
        rb, ri, imm = self._bi
        m = Mem(rb, ri, e.esize, imm * e.esize) if ri is not None else Mem(rb, disp=imm * e.esize)
        self.load_elem(m, e)

    def load_elem(self, m, e):
        a = self.a
        if is_flt(e.ty):
            a.movsd(XMM[0], m)
        elif e.esize == 1:
            a.movzx8(RAX, m)
        else:
            a.mov(RAX, m)

    def base_idx(self, base, idx):
        """Put the base pointer in a register `rb` and the index in a register `ri` (or an immediate).
        Sets self._bi = (rb, ri, imm)."""
        a = self.a
        bop = self.operand(base)
        iop = self.operand(idx)
        if bop is not None and iop is not None:
            if isinstance(bop, Reg):
                rb = bop
            else:
                self.load_cheap(RAX, base)
                rb = RAX
        elif iop is not None:
            self.gen(base)
            rb = RAX
        elif bop is not None:
            self.gen(idx)
            a.mov(RCX, RAX)
            if isinstance(bop, Reg):
                rb = bop
            else:
                self.load_cheap(RAX, base)
                rb = RAX
            self._bi = (rb, RCX, 0)
            return
        else:
            self.gen(base)
            t = self.tmp()
            a.mov(Mem(RBP, disp=t), RAX)
            self.gen(idx)
            a.mov(RCX, RAX)
            a.mov(RAX, Mem(RBP, disp=t))
            self.untmp(t)
            self._bi = (RAX, RCX, 0)
            return
        if isinstance(iop, int):
            self._bi = (rb, None, iop)
        elif isinstance(iop, Reg):
            self._bi = (rb, iop, 0)
        else:
            a.mov(RCX, iop)
            self._bi = (rb, RCX, 0)

    def g_ArrIdx(self, e):
        a = self.a
        self.base_idx(e.arr, e.idx)
        rb, ri, imm = self._bi
        stub = a.new_label()
        if rb is not RAX:
            a.mov(RAX, rb)
        if ri is None:
            self.stubs.append((stub, "bounds", e.pos.line, imm))
            a.cmp(Mem(RAX, disp=8), imm)
            a.jcc("be", stub)
            a.mov(RAX, Mem(RAX))
            self.load_elem(Mem(RAX, disp=imm * e.esize), e)
            return
        self.stubs.append((stub, "bounds", e.pos.line, ri))
        a.cmp(ri, Mem(RAX, disp=8))
        a.jcc("ae", stub)
        a.mov(RAX, Mem(RAX))
        self.load_elem(Mem(RAX, ri, e.esize), e)

    def g_NewObj(self, e):
        a = self.a
        vals = e.values
        n = len(vals)
        pending = []
        for i, v in enumerate(vals):
            if isinstance(v, T.Const) and v.kind in ("int", "bool", "nil", "str", "float"):
                pending.append(None)
                continue
            if isinstance(v, T.VarRef) and not v.var.boxed:
                pending.append(None)
                continue
            self.gen(v)
            t = self.tmp()
            self.spill(t, is_flt(v.ty))
            pending.append(t)
        a.mov(RCX, 8 * n)
        a.call(self.prog.alloc.label)
        for i, v in enumerate(vals):
            m = Mem(RAX, disp=8 * i)
            t = pending[i]
            if t is not None:
                if is_flt(v.ty):
                    a.mov(RCX, Mem(RBP, disp=t))
                else:
                    a.mov(RCX, Mem(RBP, disp=t))
                a.mov(m, RCX)
                self.untmp(t)
            else:
                self.store_simple(m, v)

    def store_simple(self, m, v):
        a = self.a
        if isinstance(v, T.Const):
            if v.kind == "float":
                a.mov_imm(RCX, struct.unpack("<q", struct.pack("<d", v.value))[0])
                a.mov(m, RCX)
            elif v.kind == "str":
                a.lea(RCX, Mem(sym=self.str_sym(v.value)))
                a.mov(m, RCX)
            else:
                if -(1 << 31) <= v.value < (1 << 31):
                    a.mov(m, v.value)
                else:
                    a.mov_imm(RCX, v.value)
                    a.mov(m, RCX)
        else:
            var = v.var
            if is_flt(var.ty):
                if isinstance(var.loc, XReg):
                    a.movsd(m, var.loc)
                else:
                    a.mov(RCX, var.loc)
                    a.mov(m, RCX)
            elif isinstance(var.loc, Reg):
                a.mov(m, var.loc)
            else:
                a.mov(RCX, var.loc)
                a.mov(m, RCX)

    # ------------------------------------------------------------------ arithmetic
    def g_Bin(self, e):
        a = self.a
        op = e.op
        if op in ("fadd", "fsub", "fmul", "fdiv"):
            self.fbin(e)
            return
        if op in ("eq", "ne", "lt", "le", "gt", "ge", "feq", "fne", "flt", "fle", "fgt", "fge"):
            self.compare_value(e)
            return
        if op in ("div", "mod"):
            self.divmod(e)
            return
        if op in ("shl", "shr", "ushr"):
            self.shift(e)
            return
        # add sub mul and or xor
        l, r = e.l, e.r
        ro = self.operand(r)
        lo = self.operand(l)
        if op == "mul":
            if isinstance(ro, int):
                self.gen_operand_to(RAX, l)
                a.imul3(RAX, RAX, ro)
                return
            if isinstance(lo, int):
                self.gen_operand_to(RAX, r)
                a.imul3(RAX, RAX, lo)
                return
            if ro is not None:
                self.gen(l)
                a.imul(RAX, ro)
                return
            if lo is not None:
                self.gen(r)
                a.imul(RAX, lo)
                return
        else:
            if ro is not None:
                self.gen(l)
                a.alu(op, RAX, ro)
                return
            if lo is not None and op in ("add", "and", "or", "xor"):
                self.gen(r)
                a.alu(op, RAX, lo)
                return
        # general case: both operands need code
        if lo is not None:
            self.gen(r)
            a.mov(RCX, RAX)
            self.load_cheap(RAX, l)
        else:
            self.gen(l)
            t = self.tmp()
            a.mov(Mem(RBP, disp=t), RAX)
            self.gen(r)
            a.mov(RCX, RAX)
            a.mov(RAX, Mem(RBP, disp=t))
            self.untmp(t)
        if op == "mul":
            a.imul(RAX, RCX)
        else:
            a.alu(op, RAX, RCX)

    def gen_operand_to(self, reg, e):
        op = self.operand(e)
        if op is not None:
            if isinstance(op, int):
                self.a.mov_imm(reg, op)
            else:
                self.a.mov(reg, op)
        else:
            self.gen(e)
            if reg is not RAX:
                self.a.mov(reg, RAX)

    def eval_pair(self):
        pass

    def two_operands(self, l, r):
        """evaluate l into rax and r into rcx"""
        a = self.a
        lo = self.operand(l)
        ro = self.operand(r)
        if ro is not None:
            self.gen_operand_to(RAX, l)
            if isinstance(ro, int):
                a.mov_imm(RCX, ro)
            else:
                a.mov(RCX, ro)
        elif lo is not None:
            self.gen(r)
            a.mov(RCX, RAX)
            if isinstance(lo, int):
                a.mov_imm(RAX, lo)
            else:
                a.mov(RAX, lo)
        else:
            self.gen(l)
            t = self.tmp()
            a.mov(Mem(RBP, disp=t), RAX)
            self.gen(r)
            a.mov(RCX, RAX)
            a.mov(RAX, Mem(RBP, disp=t))
            self.untmp(t)

    def divmod(self, e):
        a = self.a
        r = e.r
        if isinstance(r, T.Const) and 2 <= r.value <= (1 << 30) and (r.value & (r.value - 1)) == 0:
            k = r.value.bit_length() - 1
            self.gen(e.l)
            # signed division by 2^k, rounding toward zero
            a.mov(RCX, RAX)
            a.shift("sar", RCX, 63)
            a.shift("shr", RCX, 64 - k)
            if e.op == "div":
                a.add(RAX, RCX)
                a.shift("sar", RAX, k)
            else:
                a.add(RCX, RAX)
                a.and_(RCX, -(1 << k))
                a.sub(RAX, RCX)
            return
        self.two_operands(e.l, r)
        if not (isinstance(r, T.Const) and r.value not in (0, -1)):
            stub = a.new_label()
            self.stubs.append((stub, "div", e.pos.line, None))
            a.test(RCX, RCX)
            a.jcc("z", stub)
        a.cqo()
        a.idiv(RCX)
        if e.op == "mod":
            a.mov(RAX, RDX)

    def shift(self, e):
        a = self.a
        kind = {"shl": "shl", "shr": "sar", "ushr": "shr"}[e.op]
        if isinstance(e.r, T.Const):
            self.gen(e.l)
            a.shift(kind, RAX, e.r.value & 63)
            return
        self.two_operands(e.l, e.r)
        a.shift(kind, RAX, None)

    def fbin(self, e):
        a = self.a
        op = {"fadd": "addsd", "fsub": "subsd", "fmul": "mulsd", "fdiv": "divsd"}[e.op]
        ro = self.foperand(e.r)
        if ro is not None:
            self.gen(e.l)
            a.sse(op, XMM[0], ro)
            return
        lo = self.foperand(e.l)
        if lo is not None and e.op in ("fadd", "fmul"):
            self.gen(e.r)
            a.sse(op, XMM[0], lo)
            return
        self.gen(e.l)
        t = self.tmp()
        a.movsd(Mem(RBP, disp=t), XMM[0])
        self.gen(e.r)
        a.movsd(XMM[1], XMM[0])
        a.movsd(XMM[0], Mem(RBP, disp=t))
        self.untmp(t)
        a.sse(op, XMM[0], XMM[1])

    # ------------------------------------------------------------------ comparisons / branches
    def compare_value(self, e):
        a = self.a
        if e.op.startswith("f"):
            lt = a.new_label()
            lend = a.new_label()
            self.branch(e, lt, True)
            a.mov_imm(RAX, 0)
            a.jmp(lend)
            a.bind(lt)
            a.mov_imm_keepflags(RAX, 1)
            a.bind(lend)
            return
        cc = self.int_cmp(e)
        a.setcc(cc, RAX)
        a.movzx8(RAX, RAX)

    def int_cmp(self, e):
        """emit cmp for an integer comparison, return the condition code that means `e` is true"""
        a = self.a
        l, r = e.l, e.r
        cc = CC_INT[e.op]
        lo = self.operand(l)
        ro = self.operand(r)
        if isinstance(r, T.Const) and r.value == 0 and e.op in ("eq", "ne") and isinstance(lo, Reg):
            a.test(lo, lo)
            return cc
        if ro is not None and lo is not None and not isinstance(lo, int):
            if isinstance(lo, Mem) and isinstance(ro, Mem):
                a.mov(RAX, lo)
                a.cmp(RAX, ro)
            else:
                a.cmp(lo, ro)
            return cc
        if ro is not None:
            self.gen_operand_to(RAX, l)
            a.cmp(RAX, ro)
            return cc
        if lo is not None:
            self.gen(r)
            if isinstance(lo, int):
                a.cmp(RAX, lo)
                return CC_SWAP[cc]
            a.cmp(lo, RAX)
            return cc
        self.gen(l)
        t = self.tmp()
        a.mov(Mem(RBP, disp=t), RAX)
        self.gen(r)
        a.mov(RCX, RAX)
        a.mov(RAX, Mem(RBP, disp=t))
        self.untmp(t)
        a.cmp(RAX, RCX)
        return cc

    def float_cmp_branch(self, e, target, jump_if):
        a = self.a
        op = e.op[1:]
        lo = self.foperand(e.l)
        # operands into xmm0 / xmm1 (left in xmm0)
        ro = self.foperand(e.r)
        if ro is not None:
            self.gen(e.l)
            if isinstance(ro, Mem):
                a.movsd(XMM[1], ro)
                ro = XMM[1]
        else:
            self.gen(e.l)
            t = self.tmp()
            a.movsd(Mem(RBP, disp=t), XMM[0])
            self.gen(e.r)
            a.movsd(XMM[1], XMM[0])
            a.movsd(XMM[0], Mem(RBP, disp=t))
            self.untmp(t)
            ro = XMM[1]
        x0, x1 = XMM[0], ro
        # lt/le: compare (b, a) and use above / above-or-equal; unordered → false
        if op in ("lt", "le"):
            a.ucomisd(x1, x0)
            cc = "a" if op == "lt" else "ae"
        elif op in ("gt", "ge"):
            a.ucomisd(x0, x1)
            cc = "a" if op == "gt" else "ae"
        else:
            a.ucomisd(x0, x1)
            if op == "eq":
                # true iff ZF=1 and PF=0
                if jump_if:
                    skip = a.new_label()
                    a.jcc("p", skip)
                    a.jcc("e", target)
                    a.bind(skip)
                else:
                    a.jcc("p", target)
                    a.jcc("ne", target)
                return
            else:
                # ne: true iff ZF=0 or PF=1
                if jump_if:
                    a.jcc("p", target)
                    a.jcc("ne", target)
                else:
                    skip = a.new_label()
                    a.jcc("p", skip)
                    a.jcc("e", target)
                    a.bind(skip)
                return
        if jump_if:
            a.jcc(cc, target)
        else:
            a.jcc(CC_INV[cc], target)

    def branch(self, e, target, jump_if):
        """jump to `target` if (e == jump_if), otherwise fall through"""
        a = self.a
        if isinstance(e, T.Const):
            if bool(e.value) == jump_if:
                a.jmp(target)
            return
        if isinstance(e, T.Un) and e.op == "not":
            self.branch(e.e, target, not jump_if)
            return
        if isinstance(e, T.And):
            if not jump_if:
                self.branch(e.l, target, False)
                self.branch(e.r, target, False)
            else:
                skip = a.new_label()
                self.branch(e.l, skip, False)
                self.branch(e.r, target, True)
                a.bind(skip)
            return
        if isinstance(e, T.Or):
            if jump_if:
                self.branch(e.l, target, True)
                self.branch(e.r, target, True)
            else:
                skip = a.new_label()
                self.branch(e.l, skip, True)
                self.branch(e.r, target, False)
                a.bind(skip)
            return
        if isinstance(e, T.Bin) and e.op in CC_INT:
            cc = self.int_cmp(e)
            a.jcc(cc if jump_if else CC_INV[cc], target)
            return
        if isinstance(e, T.Bin) and e.op in ("feq", "fne", "flt", "fle", "fgt", "fge"):
            self.float_cmp_branch(e, target, jump_if)
            return
        if isinstance(e, T.Seq):
            self.gen_stmts(e.stmts)
            self.branch(e.e, target, jump_if)
            return
        op = self.operand(e)
        if isinstance(op, Reg):
            a.test(op, op)
        else:
            self.gen(e)
            a.test(RAX, RAX)
        a.jcc("nz" if jump_if else "z", target)

    # ------------------------------------------------------------------ calls
    def mark_call(self, line):
        self.callsites.append((self.a.here(), line, self.cur_inst))

    def g_Call(self, e):
        def do_call():
            self.a.call(e.inst.label)
            self.mark_call(e.pos.line)
        self.call_common(e.args, [p.ty for p in e.inst.params], do_call, e.ty)

    def g_CallExt(self, e):
        ext = e.ext
        sym = self.img.import_sym(ext.dll, ext.name)
        self.call_common(e.args, ext.params, lambda: self.a.call_sym(sym), e.ty)
        if getattr(ext, "ret32", False):
            self.a.movsx32(RAX, RAX)

    def g_CallInd(self, e):
        a = self.a
        self.gen(e.f)
        t = self.tmp()
        a.mov(Mem(RBP, disp=t), RAX)

        def do_call():
            a.mov(R10, Mem(RBP, disp=t))
            a._emit(b"\xFF", 2, Mem(R10), 0)      # call [r10]

        self.call_common(e.args, [x.ty for x in e.args], do_call, e.ty)
        self.untmp(t)

    def call_common(self, args, ptypes, emit_call, rty):
        a = self.a
        n = len(args)
        self.max_out = max(self.max_out, 32 + 8 * max(0, n - 4))
        # classify: trivial args can be loaded last, others are evaluated into temps (last one directly)
        trivial = []
        for x in args:
            if isinstance(x, T.GlobalRef):
                trivial.append(False)
            elif is_flt(x.ty):
                trivial.append(self.foperand(x) is not None)
            else:
                trivial.append(self.operand(x) is not None or (isinstance(x, T.Const) and x.kind == "str"))
        nontriv = [i for i in range(n) if not trivial[i]]
        temps = {}
        for i in nontriv[:-1]:
            self.gen(args[i])
            t = self.tmp()
            self.spill(t, is_flt(args[i].ty))
            temps[i] = t
        last = nontriv[-1] if nontriv else None
        last_in_reg = False
        if last is not None:
            self.gen(args[last])
            # a float arg 0 left in xmm0 would be overwritten by the stack-arg copies below
            if last < 4 and not (last == 0 and n > 4 and is_flt(args[last].ty)):
                if is_flt(args[last].ty):
                    if last != 0:
                        a.movsd(ARG_XREGS[last], XMM[0])
                else:
                    if ARG_REGS[last] is not RAX:
                        a.mov(ARG_REGS[last], RAX)
                last_in_reg = True
            else:
                t = self.tmp()
                self.spill(t, is_flt(args[last].ty))
                temps[last] = t
        # stack args first (they use rax as scratch)
        for i in range(4, n):
            x = args[i]
            m = Mem(RSP, disp=32 + 8 * (i - 4))
            if i in temps:
                a.mov(RAX, Mem(RBP, disp=temps[i]))
                a.mov(m, RAX)
            else:
                if is_flt(x.ty):
                    fo = self.foperand(x)
                    a.movsd(XMM[0], fo)
                    a.movsd(m, XMM[0])
                else:
                    self.load_cheap_any(RAX, x)
                    a.mov(m, RAX)
        for i in range(min(n, 4)):
            if i == last and last_in_reg:
                continue
            x = args[i]
            if i in temps:
                if is_flt(x.ty):
                    a.movsd(ARG_XREGS[i], Mem(RBP, disp=temps[i]))
                else:
                    a.mov(ARG_REGS[i], Mem(RBP, disp=temps[i]))
            else:
                if is_flt(x.ty):
                    fo = self.foperand(x)
                    if isinstance(fo, XReg):
                        if fo.n != ARG_XREGS[i].n:
                            a.movsd(ARG_XREGS[i], fo)
                    else:
                        a.movsd(ARG_XREGS[i], fo)
                else:
                    self.load_cheap_any(ARG_REGS[i], x)
        for t in temps.values():
            self.untmp(t)
        emit_call()

    def load_cheap_any(self, reg, x):
        a = self.a
        if isinstance(x, T.Const) and x.kind == "str":
            a.lea(reg, Mem(sym=self.str_sym(x.value)))
            return
        if isinstance(x, T.VarRef) and not x.var.boxed:
            a.mov(reg, x.var.loc)
            return
        self.load_cheap(reg, x)

    # ------------------------------------------------------------------ intrinsics
    def g_Intr(self, e):
        a = self.a
        n = e.name
        args = e.args
        if n in ("sqrt", "floor", "ceil", "trunc"):
            self.gen(args[0])
            if n == "sqrt":
                a.sse("sqrtsd", XMM[0], XMM[0])
            else:
                a.roundsd(XMM[0], XMM[0], {"floor": 1, "ceil": 2, "trunc": 3}[n])
        elif n == "fabs":
            self.gen(args[0])
            a.movq_to_r(RAX, XMM[0])
            a.shift("shl", RAX, 1)
            a.shift("shr", RAX, 1)
            a.movq_to_x(XMM[0], RAX)
        elif n == "f2bits":
            self.gen(args[0])
            a.movq_to_r(RAX, XMM[0])
        elif n == "bits2f":
            self.gen(args[0])
            a.movq_to_x(XMM[0], RAX)
        elif n == "sp":
            a.mov(RAX, RSP)
        elif n == "setjmp":
            self.gen(args[0])
            for i, r in enumerate([RBX, RSI, RDI, R12, R13, R14, R15, RBP, RSP]):
                a.mov(Mem(RAX, disp=8 * i), r)
            for i in range(6, 16):
                a.movups_store(Mem(RAX, disp=80 + 16 * (i - 6)), XMM[i])
            lres = a.new_label()
            ldone = a.new_label()
            a.lea_label(RCX, lres)
            a.mov(Mem(RAX, disp=72), RCX)
            a.mov_imm(RAX, 0)
            a.jmp(ldone)
            a.bind(lres)
            a.mov_imm(RAX, 1)
            a.bind(ldone)
        elif n == "longjmp":
            self.gen(args[0])
            for i in range(6, 16):
                a.movups_load(XMM[i], Mem(RAX, disp=80 + 16 * (i - 6)))
            for i, r in enumerate([RBX, RSI, RDI, R12, R13, R14, R15, RBP]):
                a.mov(r, Mem(RAX, disp=8 * i))
            a.mov(RDX, Mem(RAX, disp=72))
            a.mov(RSP, Mem(RAX, disp=64))
            a.jmp_reg(RDX)
        elif n == "tb":
            a.lea(RAX, Mem(sym="tb"))
        elif n == "text_start":
            a.lea(RAX, Mem(sym="text_start"))
        elif n == "fp":
            a.mov(RAX, RBP)
        elif n == "data_start":
            a.lea(RAX, Mem(sym="data_start"))
        elif n == "data_end":
            a.lea(RAX, Mem(sym="data_end"))
        elif n == "popcnt":
            self.gen(args[0])
            a.popcnt(RAX, RAX)
        elif n == "ctz":
            self.gen(args[0])
            a.bsf(RAX, RAX)
        elif n == "clz":
            self.gen(args[0])
            a.bsr(RAX, RAX)
            a.xor(RAX, 63)
        elif n == "trap":
            a.ud2()
        elif n == "memcpy":
            self.three(args)
            a.mov(R10, RSI)
            a.mov(R11, RDI)
            a.mov(RDI, R8)
            a.mov(RSI, R9)
            a.rep_movsb()
            a.mov(RSI, R10)
            a.mov(RDI, R11)
        elif n == "memset":
            self.three(args)
            a.mov(R10, RDI)
            a.mov(RDI, R8)
            a.mov(RAX, R9)
            a.rep_stosb()
            a.mov(RDI, R10)
        elif n == "save_regs":
            self.gen(args[0])
            for i, r in enumerate([RBX, RSI, RDI, R12, R13, R14, R15]):
                a.mov(Mem(RAX, disp=8 * i), r)
        else:
            raise Exception("intrinsic " + n)

    def three(self, args):
        """rcx = args[2], r8 = args[0], r9 = args[1]"""
        a = self.a
        ts = []
        for x in args:
            self.gen(x)
            t = self.tmp()
            a.mov(Mem(RBP, disp=t), RAX)
            ts.append(t)
        a.mov(R8, Mem(RBP, disp=ts[0]))
        a.mov(R9, Mem(RBP, disp=ts[1]))
        a.mov(RCX, Mem(RBP, disp=ts[2]))
        for t in ts:
            self.untmp(t)
