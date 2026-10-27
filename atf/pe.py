"""Writes a Windows x64 PE console executable from raw machine code + data."""
import struct

IMAGE_BASE = 0x140000000
SECTION_ALIGN = 0x1000
FILE_ALIGN = 0x200


def align(v, a):
    return (v + a - 1) // a * a


class Image:
    def __init__(self):
        self.text = bytearray()
        self.text_relocs = []          # (pos, symbol, after, addend)
        self.rdata = bytearray()
        self.data_size = 0
        self.symbols = {}              # name -> (section, offset)
        self.imports = {}              # dll -> [function names]   (insertion ordered)
        self.entry = 0                 # text offset of the entry point
        self.stack_reserve = 256 * 1024 * 1024
        self.stack_commit = 1024 * 1024

    def import_sym(self, dll, name):
        lst = self.imports.setdefault(dll, [])
        if name not in lst:
            lst.append(name)
        return "imp:%s!%s" % (dll, name)

    def build(self):
        # ---- import table inside .rdata -----------------------------------
        dlls = list(self.imports.items())
        idata = bytearray()
        iat_pos = {}                   # (dll,name) -> offset in rdata
        if dlls:
            off = (len(dlls) + 1) * 20
            ilt = {}
            iat = {}
            for dll, fns in dlls:
                ilt[dll] = off
                off += (len(fns) + 1) * 8
            iat_start = off
            for dll, fns in dlls:
                iat[dll] = off
                off += (len(fns) + 1) * 8
            iat_end = off
            hn = {}
            for dll, fns in dlls:
                for f in fns:
                    hn[(dll, f)] = off
                    off += align(2 + len(f) + 1, 2)
            dn = {}
            for dll, fns in dlls:
                dn[dll] = off
                off += len(dll) + 1
            idata = bytearray(off)
            for i, (dll, fns) in enumerate(dlls):
                # rva fields are patched below once the rdata RVA is known
                pass
        else:
            iat_start = iat_end = 0
            ilt = iat = hn = dn = {}
        idata_size = len(idata)
        user_rdata_off = align(idata_size, 16)

        # ---- layout --------------------------------------------------------
        headers_size = 0x400
        text_rva = SECTION_ALIGN
        text_vsize = max(len(self.text), 1)
        rdata_rva = text_rva + align(text_vsize, SECTION_ALIGN)
        rdata_total = user_rdata_off + len(self.rdata)
        rdata_vsize = max(rdata_total, 1)
        data_rva = rdata_rva + align(rdata_vsize, SECTION_ALIGN)
        data_vsize = max(self.data_size, 16)
        image_size = data_rva + align(data_vsize, SECTION_ALIGN)

        # fill the import structures now that rdata_rva is known
        for i, (dll, fns) in enumerate(dlls):
            struct.pack_into("<IIIII", idata, i * 20, rdata_rva + ilt[dll], 0, 0, rdata_rva + dn[dll], rdata_rva + iat[dll])
            for j, f in enumerate(fns):
                p = rdata_rva + hn[(dll, f)]
                struct.pack_into("<Q", idata, ilt[dll] + j * 8, p)
                struct.pack_into("<Q", idata, iat[dll] + j * 8, p)
                iat_pos[(dll, f)] = iat[dll] + j * 8
                idata[hn[(dll, f)] + 2:hn[(dll, f)] + 2 + len(f)] = f.encode()
            idata[dn[dll]:dn[dll] + len(dll)] = dll.encode()

        rdata = bytearray(idata)
        rdata += b"\0" * (user_rdata_off - len(rdata))
        rdata += self.rdata

        # ---- symbol resolution --------------------------------------------
        base = {"text": text_rva, "rdata": rdata_rva + user_rdata_off, "data": data_rva}
        sym_rva = {}
        for name, (sec, off) in self.symbols.items():
            sym_rva[name] = base[sec] + off
        for (dll, f), off in iat_pos.items():
            sym_rva["imp:%s!%s" % (dll, f)] = rdata_rva + off
        text = bytearray(self.text)
        for pos, sym, after, addend in self.text_relocs:
            target = sym_rva[sym] + addend
            nxt = text_rva + pos + 4 + after
            struct.pack_into("<i", text, pos, target - nxt)

        # ---- write file ----------------------------------------------------
        text_raw = align(len(text), FILE_ALIGN)
        rdata_raw = align(len(rdata), FILE_ALIGN)
        text_fo = headers_size
        rdata_fo = text_fo + text_raw
        out = bytearray()

        # DOS header
        dos = bytearray(0x80)
        dos[0:2] = b"MZ"
        struct.pack_into("<I", dos, 0x3C, 0x80)
        out += dos
        out += b"PE\0\0"
        nsec = 3
        out += struct.pack("<HHIIIHH", 0x8664, nsec, 0, 0, 0, 0xF0, 0x0022)
        # optional header (PE32+)
        opt = bytearray()
        opt += struct.pack("<HBB", 0x20B, 14, 0)
        opt += struct.pack("<III", text_raw, rdata_raw, 0)
        opt += struct.pack("<II", text_rva + self.entry, text_rva)
        opt += struct.pack("<Q", IMAGE_BASE)
        opt += struct.pack("<II", SECTION_ALIGN, FILE_ALIGN)
        opt += struct.pack("<HHHHHH", 6, 0, 0, 0, 6, 0)
        opt += struct.pack("<IIII", 0, image_size, headers_size, 0)
        opt += struct.pack("<HH", 3, 0x8100 | 0x0000)         # console; NX_COMPAT | TERMINAL_SERVER_AWARE
        opt += struct.pack("<QQQQ", self.stack_reserve, self.stack_commit, 1 << 20, 1 << 12)
        opt += struct.pack("<II", 0, 16)
        dd = [(0, 0)] * 16
        dd = list(dd)
        if dlls:
            dd[1] = (rdata_rva, (len(dlls) + 1) * 20)
            dd[12] = (rdata_rva + iat_start, iat_end - iat_start)
        for rva, size in dd:
            opt += struct.pack("<II", rva, size)
        assert len(opt) == 0xF0, len(opt)
        out += opt
        # section headers
        def sh(name, vsize, rva, rsize, fo, flags):
            return struct.pack("<8sIIIIIIHHI", name, vsize, rva, rsize, fo, 0, 0, 0, 0, flags)
        out += sh(b".text", len(text), text_rva, text_raw, text_fo, 0x60000020)
        out += sh(b".rdata", len(rdata), rdata_rva, rdata_raw, rdata_fo, 0x40000040)
        out += sh(b".data", data_vsize, data_rva, 0, 0, 0xC0000080)
        out += b"\0" * (headers_size - len(out))
        out += text + b"\0" * (text_raw - len(text))
        out += rdata + b"\0" * (rdata_raw - len(rdata))
        return bytes(out)
