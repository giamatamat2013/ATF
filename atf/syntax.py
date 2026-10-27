"""Untyped syntax tree."""


def _mk(name, fields):
    fields = tuple(fields.split()) if fields else ()

    def __init__(self, *args, pos=None):
        if len(args) != len(fields):
            raise TypeError("%s takes %d fields, got %d" % (name, len(fields), len(args)))
        for f, a in zip(fields, args):
            setattr(self, f, a)
        self.pos = pos

    def __repr__(self):
        return "%s(%s)" % (name, ", ".join("%s=%r" % (f, getattr(self, f)) for f in fields))

    return type(name, (), {"__slots__": fields + ("pos",), "__init__": __init__, "__repr__": __repr__, "_fields": fields})


# ---- type expressions --------------------------------------------------
TName = _mk("TName", "name args")            # int, Point, Array<int>
TArray = _mk("TArray", "elem")               # [T]
TMap = _mk("TMap", "key val")                # {K: V}
TTuple = _mk("TTuple", "elems")              # (A, B)
TFn = _mk("TFn", "params ret")               # fn(A, B) -> R
TOpt = _mk("TOpt", "inner")                  # T?
TPtr = _mk("TPtr", "elem")                   # ptr<T>

# ---- expressions -------------------------------------------------------
IntLit = _mk("IntLit", "value")
FloatLit = _mk("FloatLit", "value")
StrLit = _mk("StrLit", "parts")              # list of bytes | (Expr, spec)
CharLit = _mk("CharLit", "value")
BoolLit = _mk("BoolLit", "value")
NilLit = _mk("NilLit", "")
Ident = _mk("Ident", "name targs")
Unary = _mk("Unary", "op expr")              # - not ~
Binary = _mk("Binary", "op left right")
Call = _mk("Call", "callee args")            # args: list of Expr | NamedArg
NamedArg = _mk("NamedArg", "name expr")
Field = _mk("Field", "obj name")
Index = _mk("Index", "obj index")
Range = _mk("Range", "lo hi inclusive step")
ArrayLit = _mk("ArrayLit", "elems")
MapLit = _mk("MapLit", "pairs")
TupleLit = _mk("TupleLit", "elems")
StructLit = _mk("StructLit", "name fields")   # name: Ident/TName ; fields [(name, expr)]
Lambda = _mk("Lambda", "params ret body")     # params [(name, TypeExpr|None)] ; body Block|Expr
IfExpr = _mk("IfExpr", "cond then els")       # cond may be IfLet
MatchExpr = _mk("MatchExpr", "subject arms")
BlockExpr = _mk("BlockExpr", "block")
Cast = _mk("Cast", "expr type")
Unwrap = _mk("Unwrap", "expr")                # x!
Try = _mk("Try", "expr")                      # x?
Coalesce = _mk("Coalesce", "left right")      # a ?? b
IfLet = _mk("IfLet", "pat expr")              # `if let pat = expr`

# ---- patterns ------------------------------------------------------------
PWild = _mk("PWild", "")
PBind = _mk("PBind", "name")
PLit = _mk("PLit", "expr")
PRange = _mk("PRange", "lo hi inclusive")
PVariant = _mk("PVariant", "path args")       # path: list of names; args: list of pattern | None
PTuple = _mk("PTuple", "elems")
POr = _mk("POr", "alts")

# ---- statements ----------------------------------------------------------
Block = _mk("Block", "stmts")
Let = _mk("Let", "target type init mutable")   # target: str | list-of-targets (tuple destructure)
Assign = _mk("Assign", "target op value")      # op: '=' '+=' ...
ExprStmt = _mk("ExprStmt", "expr")
If = _mk("If", "cond then els")                # els: Block | If | None
While = _mk("While", "cond body")
Loop = _mk("Loop", "body")
For = _mk("For", "vars iter body")
Break = _mk("Break", "")
Continue = _mk("Continue", "")
Return = _mk("Return", "value")
Defer = _mk("Defer", "stmt")
MatchStmt = _mk("MatchStmt", "subject arms")
MatchArm = _mk("MatchArm", "pat guard body")   # body: Block | Expr

# ---- declarations ----------------------------------------------------------
Param = _mk("Param", "name type default")
FnDecl = _mk("FnDecl", "name tparams params ret body attrs")
StructDecl = _mk("StructDecl", "name tparams fields")       # fields [(name, TypeExpr)]
EnumDecl = _mk("EnumDecl", "name tparams variants")         # variants [(name, [TypeExpr], explicit value|None)]
ImplDecl = _mk("ImplDecl", "type tparams methods")
ConstDecl = _mk("ConstDecl", "name type value")
GlobalDecl = _mk("GlobalDecl", "name type value mutable")
ImportDecl = _mk("ImportDecl", "path")
ExternDecl = _mk("ExternDecl", "dll name params ret variadic")
TypeAlias = _mk("TypeAlias", "name tparams type")
