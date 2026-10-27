"""A small x86-64 assembler: just the instructions the ATF compiler needs.

Operands are `Reg`, `XReg`, `Mem` or plain Python ints (immediates).
Code labels are ints handed out by `new_label()`; references to symbols that live
in other sections (data, imports) become relocations resolved by the PE linker.
"""
import struct


class Reg:
    __slots__ = ("n", "name")

    def __init__(self, n, name):
        self.n = n
        self.name = name

    def __repr__(self):
        return self.name


class XReg:
    __slots__ = ("n",)

    def __init__(self, n):
        self.n = n

    def __repr__(self):
        return "xmm%d" % self.n


_names = ["rax", "rcx", "rdx", "rbx", "rsp", "rbp", "rsi", "rdi"] + ["r%d" % i for i in range(8, 16)]
RAX, RCX, RDX, RBX, RSP, RBP, RSI, RDI, R8, R9, R10, R11, R12, R13, R14, R15 = [Reg(i, n) for i, n in enumerate(_names)]
REGS = [RAX, RCX, RDX, RBX, RSP, RBP, RSI, RDI, R8, R9, R10, R11, R12, R13, R14, R15]
XMM = [XReg(i) for i in range(16)]


class Mem:
    """[base + index*scale + disp]  or  [rip + sym + disp]"""
    __slots__ = ("base", "index", "scale", "disp", "sym")

    def __init__(self, base=None, index=None, scale=1, disp=0, sym=None):
        self.base = base
        self.index = index
        self.scale = scale
        self.disp = disp
        self.sym = sym

    def __repr__(self):
        return "[%s%s%s%s]" % (self.base or "", "+%s*%d" % (self.index, self.scale) if self.index else "",
                              "%+d" % self.disp if self.disp else "", " sym=%s" % (self.sym,) if self.sym else "")


CC = {"o": 0, "no": 1, "b": 2, "c": 2, "ae": 3, "nc": 3, "e": 4, "z": 4, "ne": 5, "nz": 5, "be": 6, "a": 7,
      "s": 8, "ns": 9, "p": 10, "np": 11, "l": 12, "ge": 13, "le": 14, "g": 15}

ALU = {"add": 0, "or": 1, "and": 4, "sub": 5, "xor": 6, "cmp": 7}


def fits8(v):
    return -128 <= v <= 127


def fits32(v):
    return -(1 << 31) <= v < (1 << 31)


class Asm:
    def __init__(self):
        self.buf = bytearray()
        self.labels = {}          # label -> offset
        self.fixups = []          # (pos, label)   rel32 to code label
        self.relocs = []          # (pos, sym, end_off_adjust, addend)  rel32 to external symbol
        self._nlabel = 0
        self._pending_rip = None

    # ---- labels -----------------------------------------------------------
    def new_label(self):
        self._nlabel += 1
        return self._nlabel

    def bind(self, label):
        self.labels[label] = len(self.buf)

    def here(self):
        return len(self.buf)

    def finish(self):
        for pos, label in self.fixups:
            target = self.labels[label]
            struct.pack_into("<i", self.buf, pos, target - (pos + 4))
        self.fixups = []
        return self.buf

    # ---- raw encoding -----------------------------------------------------
    def _emit(self, opc, reg, rm, w=0, prefix=b"", imm=b"", force_rex=False):
        """prefix, REX, opcode, modrm/sib/disp, imm.  reg is an int (register number or /digit)."""
        b = self.buf
        b += prefix
        rex = 0x40 | (w << 3)
        if reg >= 8:
            rex |= 4
        if isinstance(rm, Mem):
            if rm.index is not None and rm.index.n >= 8:
                rex |= 2
            if rm.base is not None and rm.base.n >= 8:
                rex |= 1
        else:
            if rm.n >= 8:
                rex |= 1
        if rex != 0x40 or force_rex:
            b.append(rex)
        b += opc
        r = (reg & 7) << 3
        if not isinstance(rm, Mem):
            b.append(0xC0 | r | (rm.n & 7))
        else:
            self._mem(r, rm)
        b += imm
        if self._pending_rip is not None:
            pos, sym, addend = self._pending_rip
            self.relocs.append((pos, sym, len(b) - (pos + 4), addend))
            self._pending_rip = None

    def _mem(self, r, m):
        b = self.buf
        if m.sym is not None:
            b.append(0x05 | r)
            self._pending_rip = (len(b), m.sym, m.disp)
            b += b"\0\0\0\0"
            return
        base, index, disp = m.base, m.index, m.disp
        if base is None:
            # [index*scale + disp32] or [disp32]
            b.append(0x04 | r)
            idx = index.n & 7 if index is not None else 4
            ss = {1: 0, 2: 1, 4: 2, 8: 3}[m.scale]
            b.append((ss << 6) | (idx << 3) | 5)
            b += struct.pack("<i", disp)
            return
        bn = base.n & 7
        need_sib = index is not None or bn == 4
        if disp == 0 and bn != 5:
            mod = 0
        elif fits8(disp):
            mod = 1
        else:
            mod = 2
        if need_sib:
            b.append((mod << 6) | r | 4)
            idx = index.n & 7 if index is not None else 4
            ss = {1: 0, 2: 1, 4: 2, 8: 3}[m.scale]
            b.append((ss << 6) | (idx << 3) | bn)
        else:
            b.append((mod << 6) | r | bn)
        if mod == 1:
            b += struct.pack("<b", disp)
        elif mod == 2:
            b += struct.pack("<i", disp)

    # ---- moves ------------------------------------------------------------
    def mov(self, dst, src):
        if isinstance(dst, Reg):
            if isinstance(src, Reg):
                self._emit(b"\x8B", dst.n, src, 1)
            elif isinstance(src, Mem):
                self._emit(b"\x8B", dst.n, src, 1)
            else:
                self.mov_imm(dst, src)
        else:
            assert isinstance(dst, Mem)
            if isinstance(src, Reg):
                self._emit(b"\x89", src.n, dst, 1)
            else:
                assert fits32(src)
                self._emit(b"\xC7", 0, dst, 1, imm=struct.pack("<i", src))

    def mov_imm(self, dst, v):
        if v == 0:
            self._emit(b"\x33", dst.n, dst, 0)   # xor r32, r32
        elif 0 < v < (1 << 32):
            if dst.n >= 8:
                self.buf.append(0x41)
            self.buf.append(0xB8 + (dst.n & 7))
            self.buf += struct.pack("<I", v)
        elif fits32(v):
            self._emit(b"\xC7", 0, dst, 1, imm=struct.pack("<i", v))
        else:
            self.buf.append(0x48 | (1 if dst.n >= 8 else 0))
            self.buf.append(0xB8 + (dst.n & 7))
            self.buf += struct.pack("<q", v) if v < (1 << 63) else struct.pack("<Q", v & ((1 << 64) - 1))

    def mov_imm_keepflags(self, dst, v):
        """mov that never touches flags (no xor trick)."""
        if v == 0:
            if dst.n >= 8:
                self.buf.append(0x41)
            self.buf.append(0xB8 + (dst.n & 7))
            self.buf += b"\0\0\0\0"
        else:
            self.mov_imm(dst, v)

    def mov_mem_reg8(self, m, r):
        self._emit(b"\x88", r.n, m, 0, force_rex=True)

    def movzx8(self, dst, src):      # dst:reg64  src: Mem(byte) or Reg(low 8)
        self._emit(b"\x0F\xB6", dst.n, src, 0, force_rex=isinstance(src, Reg))

    def movzx16(self, dst, src):
        self._emit(b"\x0F\xB7", dst.n, src, 0)

    def mov32_load(self, dst, m):    # zero extending 32-bit load
        self._emit(b"\x8B", dst.n, m, 0)

    def mov32_store(self, m, r):
        self._emit(b"\x89", r.n, m, 0)

    def movsx32(self, dst, src):
        self._emit(b"\x63", dst.n, src, 1)

    def movsx8(self, dst, src):
        self._emit(b"\x0F\xBE", dst.n, src, 1, force_rex=isinstance(src, Reg))

    def lea(self, dst, m):
        self._emit(b"\x8D", dst.n, m, 1)

    def push(self, r):
        if r.n >= 8:
            self.buf.append(0x41)
        self.buf.append(0x50 + (r.n & 7))

    def pop(self, r):
        if r.n >= 8:
            self.buf.append(0x41)
        self.buf.append(0x58 + (r.n & 7))

    def xchg(self, a, b_):
        self._emit(b"\x87", a.n, b_, 1)

    # ---- ALU --------------------------------------------------------------
    def alu(self, op, dst, src):
        ext = ALU[op]
        if isinstance(src, int):
            if fits8(src):
                self._emit(b"\x83", ext, dst, 1, imm=struct.pack("<b", src))
            else:
                assert fits32(src), "immediate too large for %s" % op
                self._emit(b"\x81", ext, dst, 1, imm=struct.pack("<i", src))
        elif isinstance(src, Reg):
            self._emit(bytes([ext * 8 + 1]), src.n, dst, 1)
        else:
            assert isinstance(dst, Reg)
            self._emit(bytes([ext * 8 + 3]), dst.n, src, 1)

    def add(self, d, s): self.alu("add", d, s)
    def sub(self, d, s): self.alu("sub", d, s)
    def and_(self, d, s): self.alu("and", d, s)
    def or_(self, d, s): self.alu("or", d, s)
    def xor(self, d, s): self.alu("xor", d, s)
    def cmp(self, d, s): self.alu("cmp", d, s)

    def cmp8_mem_imm(self, m, v):
        self._emit(b"\x80", 7, m, 0, imm=struct.pack("<B", v & 255))

    def test(self, a, b_):
        if isinstance(b_, int):
            self._emit(b"\xF7", 0, a, 1, imm=struct.pack("<i", b_))
        else:
            self._emit(b"\x85", b_.n, a, 1)

    def imul(self, dst, src):
        self._emit(b"\x0F\xAF", dst.n, src, 1)

    def imul3(self, dst, src, imm):
        if fits8(imm):
            self._emit(b"\x6B", dst.n, src, 1, imm=struct.pack("<b", imm))
        else:
            self._emit(b"\x69", dst.n, src, 1, imm=struct.pack("<i", imm))

    def cqo(self):
        self.buf += b"\x48\x99"

    def idiv(self, src):
        self._emit(b"\xF7", 7, src, 1)

    def neg(self, r): self._emit(b"\xF7", 3, r, 1)
    def not_(self, r): self._emit(b"\xF7", 2, r, 1)
    def inc(self, r): self._emit(b"\xFF", 0, r, 1)
    def dec(self, r): self._emit(b"\xFF", 1, r, 1)

    def shift(self, kind, dst, amount):
        ext = {"shl": 4, "shr": 5, "sar": 7}[kind]
        if isinstance(amount, int):
            if amount == 1:
                self._emit(b"\xD1", ext, dst, 1)
            else:
                self._emit(b"\xC1", ext, dst, 1, imm=struct.pack("<B", amount & 63))
        else:
            self._emit(b"\xD3", ext, dst, 1)   # by cl

    def setcc(self, cc, r):
        self._emit(bytes([0x0F, 0x90 + CC[cc]]), 0, r, 0, force_rex=True)

    def cmov(self, cc, dst, src):
        self._emit(bytes([0x0F, 0x40 + CC[cc]]), dst.n, src, 1)

    def popcnt(self, dst, src):
        self._emit(b"\x0F\xB8", dst.n, src, 1, prefix=b"\xF3")

    def bsr(self, dst, src):
        self._emit(b"\x0F\xBD", dst.n, src, 1)

    def bsf(self, dst, src):
        self._emit(b"\x0F\xBC", dst.n, src, 1)

    # ---- control flow -----------------------------------------------------
    def jmp(self, label):
        self.buf.append(0xE9)
        self.fixups.append((len(self.buf), label))
        self.buf += b"\0\0\0\0"

    def jcc(self, cc, label):
        self.buf += bytes([0x0F, 0x80 + CC[cc]])
        self.fixups.append((len(self.buf), label))
        self.buf += b"\0\0\0\0"

    def call(self, label):
        self.buf.append(0xE8)
        self.fixups.append((len(self.buf), label))
        self.buf += b"\0\0\0\0"

    def call_sym(self, sym):
        """call [rip+sym]  (imports)"""
        self._emit(b"\xFF", 2, Mem(sym=sym), 0)

    def call_reg(self, r):
        self._emit(b"\xFF", 2, r, 0)

    def jmp_reg(self, r):
        self._emit(b"\xFF", 4, r, 0)

    def ret(self):
        self.buf.append(0xC3)

    def leave(self):
        self.buf.append(0xC9)

    def int3(self):
        self.buf.append(0xCC)

    def ud2(self):
        self.buf += b"\x0F\x0B"

    def rep_movsb(self):
        self.buf += b"\xF3\xA4"

    def rep_stosb(self):
        self.buf += b"\xF3\xAA"

    def lea_label(self, dst, label):
        """lea dst, [rip + code label]"""
        rex = 0x48 | (4 if dst.n >= 8 else 0)
        self.buf += bytes([rex, 0x8D, 0x05 | ((dst.n & 7) << 3)])
        self.fixups.append((len(self.buf), label))
        self.buf += b"\0\0\0\0"

    # ---- SSE2 -------------------------------------------------------------
    def movsd(self, dst, src):
        if isinstance(dst, XReg):
            if isinstance(src, XReg):
                self._emit(b"\x0F\x28", dst.n, src, 0, prefix=b"\x66")  # movapd
            else:
                self._emit(b"\x0F\x10", dst.n, src, 0, prefix=b"\xF2")
        else:
            self._emit(b"\x0F\x11", src.n, dst, 0, prefix=b"\xF2")

    def sse(self, op, dst, src):
        code = {"addsd": 0x58, "mulsd": 0x59, "subsd": 0x5C, "divsd": 0x5E, "sqrtsd": 0x51,
                "minsd": 0x5D, "maxsd": 0x5F}[op]
        self._emit(bytes([0x0F, code]), dst.n, src, 0, prefix=b"\xF2")

    def ucomisd(self, a, b_):
        self._emit(b"\x0F\x2E", a.n, b_, 0, prefix=b"\x66")

    def cvtsi2sd(self, dst, src):
        self._emit(b"\x0F\x2A", dst.n, src, 1, prefix=b"\xF2")

    def cvttsd2si(self, dst, src):
        self._emit(b"\x0F\x2C", dst.n, src, 1, prefix=b"\xF2")

    def movq_to_x(self, x, r):
        self._emit(b"\x0F\x6E", x.n, r, 1, prefix=b"\x66")

    def movq_to_r(self, r, x):
        self._emit(b"\x0F\x7E", x.n, r, 1, prefix=b"\x66")

    def xorpd(self, a, b_):
        self._emit(b"\x0F\x57", a.n, b_, 0, prefix=b"\x66")

    def andpd(self, a, b_):
        self._emit(b"\x0F\x54", a.n, b_, 0, prefix=b"\x66")

    def roundsd(self, dst, src, mode):
        # mode: 0 nearest, 1 floor, 2 ceil, 3 trunc  (| 8 = suppress precision exception)
        self._emit(b"\x0F\x3A\x0B", dst.n, src, 0, prefix=b"\x66", imm=bytes([mode | 8]))

    def movaps(self, dst, src):
        self._emit(b"\x0F\x28", dst.n, src, 0)

    def movups_load(self, dst, m):
        self._emit(b"\x0F\x10", dst.n, m, 0)

    def movups_store(self, m, src):
        self._emit(b"\x0F\x11", src.n, m, 0)
