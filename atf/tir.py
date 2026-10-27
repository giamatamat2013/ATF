"""Typed, lowered intermediate representation (output of the checker, input of the code generator)."""
from .errors import NOPOS


def _mk(name, fields, expr):
    fields = tuple(fields.split()) if fields else ()
    slots = fields + (("ty",) if expr else ()) + ("pos",)

    def __init__(self, *args, ty=None, pos=None):
        if len(args) != len(fields):
            raise TypeError("%s takes %d fields, got %d" % (name, len(fields), len(args)))
        for f, a in zip(fields, args):
            setattr(self, f, a)
        if expr:
            self.ty = ty
        self.pos = pos if pos is not None else NOPOS

    def __repr__(self):
        return "%s(%s)" % (name, ", ".join("%s=%r" % (f, getattr(self, f)) for f in fields))

    return type(name, (), {"__slots__": slots, "__init__": __init__, "__repr__": __repr__, "_fields": fields})


def E(name, fields=""):
    return _mk(name, fields, True)


def St(name, fields=""):
    return _mk(name, fields, False)


# ---- expressions ----
Const = E("Const", "kind value")              # kind: int float bool str nil
VarRef = E("VarRef", "var")
GlobalRef = E("GlobalRef", "glob")
FnRef = E("FnRef", "inst")
Un = E("Un", "op e")                          # neg fneg not bnot
Bin = E("Bin", "op l r")                      # see codegen for op names
And = E("And", "l r")
Or = E("Or", "l r")
Cvt = E("Cvt", "kind e")                      # i2f f2i trunc8 box unbox
Call = E("Call", "inst args")
CallExt = E("CallExt", "ext args")
CallInd = E("CallInd", "f args")
Load = E("Load", "obj idx")                   # [obj + 8*idx]
PtrIdx = E("PtrIdx", "base idx esize")        # raw pointer element
ArrIdx = E("ArrIdx", "arr idx esize")         # bounds-checked Array<T> element
NewObj = E("NewObj", "values")                # heap object of len(values) 8-byte slots
Intr = E("Intr", "name args")
Cond = E("Cond", "c a b")
Seq = E("Seq", "stmts e")
MkClosure = E("MkClosure", "inst caps")
Env = E("Env")                                # the closure environment pointer of the current lambda

# ---- statements ----
Decl = St("Decl", "var init")
Set = St("Set", "target value")
ExprS = St("ExprS", "e")
If = St("If", "c then els")
While = St("While", "c body step")
Break = St("Break")
Continue = St("Continue")
Ret = St("Ret", "e")
Blk = St("Blk", "stmts")


class Var:
    __slots__ = ("name", "ty", "mutable", "uid", "captured", "assigned", "is_param", "weight", "owner", "pos",
                 "loc", "addr_taken", "decl_seen", "root", "is_temp")
    _n = 0

    def __init__(self, name, ty, mutable=False, owner=None, pos=None):
        Var._n += 1
        self.uid = Var._n
        self.name = name
        self.ty = ty
        self.mutable = mutable
        self.captured = False
        self.assigned = False
        self.is_param = False
        self.weight = 0
        self.owner = owner
        self.pos = pos
        self.loc = None
        self.addr_taken = False
        self.decl_seen = False
        self.root = self
        self.is_temp = False

    @property
    def boxed(self):
        r = self.root
        return r.captured and r.assigned

    def __repr__(self):
        return "Var(%s#%d:%s)" % (self.name, self.uid, self.ty)


class GlobalVar:
    __slots__ = ("name", "ty", "uid", "sym", "pos")
    _n = 0

    def __init__(self, name, ty, pos=None):
        GlobalVar._n += 1
        self.uid = GlobalVar._n
        self.name = name
        self.ty = ty
        self.sym = "g%d_%s" % (self.uid, name)
        self.pos = pos


class Extern:
    __slots__ = ("dll", "name", "params", "ret", "ret32")

    def __init__(self, dll, name, params, ret, ret32=False):
        self.dll = dll
        self.name = name
        self.params = params
        self.ret = ret
        self.ret32 = ret32


class FnInst:
    _n = 0

    def __init__(self, name, params, ret):
        FnInst._n += 1
        self.uid = FnInst._n
        self.name = name
        self.params = params            # [Var]
        self.ret = ret
        self.body = None                # [stmt]
        self.vars = []                  # all Vars declared (including params)
        self.callees = set()
        self.is_lambda = False
        self.captures = []              # [Var] of the enclosing function captured by this lambda
        self.capture_inner = {}         # outer Var -> inner Var
        self.label = None
        self.pos = NOPOS
        self.info = None
        self.targs = ()
        self.line_of_decl = 0
        self.is_prelude = False

    def __repr__(self):
        return "FnInst(%s#%d)" % (self.name, self.uid)


class Program:
    def __init__(self):
        self.funcs = []                 # FnInst, all checked instances
        self.globals = []
        self.externs = []
        self.entry = None
        self.alloc = None               # FnInst of __alloc
        self.panic_bounds = None        # FnInst for bounds errors
        self.panic_msg = None
        self.rt = {}                    # runtime helper FnInsts by name
