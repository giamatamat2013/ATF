"""Semantic types."""


class Type:
    __slots__ = ()

    def __eq__(self, other):
        return isinstance(other, Type) and self.key() == other.key()

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.key())

    def __repr__(self):
        return str(self)


class TPrim(Type):
    __slots__ = ("name",)

    def __init__(self, name):
        self.name = name

    def key(self):
        return ("prim", self.name)

    def __str__(self):
        return self.name


TInt = TPrim("int")
TFloat = TPrim("float")
TBool = TPrim("bool")
TByte = TPrim("byte")
TStr = TPrim("str")
TVoid = TPrim("void")
TNever = TPrim("never")
TNil = TPrim("nil")          # the type of the `nil` literal
TAnyPtr = TPrim("ptr")       # untyped pointer (nil literal for ptr)

PRIMS = {"int": TInt, "float": TFloat, "bool": TBool, "byte": TByte, "str": TStr, "void": TVoid, "never": TNever}


class TPtr(Type):
    __slots__ = ("elem",)

    def __init__(self, elem):
        self.elem = elem

    def key(self):
        return ("ptr", self.elem.key())

    def __str__(self):
        return "ptr<%s>" % self.elem


class TTuple(Type):
    __slots__ = ("elems",)

    def __init__(self, elems):
        self.elems = tuple(elems)

    def key(self):
        return ("tuple",) + tuple(e.key() for e in self.elems)

    def __str__(self):
        return "(" + ", ".join(str(e) for e in self.elems) + ")"


class TFunc(Type):
    __slots__ = ("params", "ret")

    def __init__(self, params, ret):
        self.params = tuple(params)
        self.ret = ret

    def key(self):
        return ("fn", tuple(p.key() for p in self.params), self.ret.key())

    def __str__(self):
        r = "" if self.ret == TVoid else " -> %s" % self.ret
        return "fn(" + ", ".join(str(p) for p in self.params) + ")" + r


class TOpt(Type):
    __slots__ = ("inner",)

    def __init__(self, inner):
        self.inner = inner

    def key(self):
        return ("opt", self.inner.key())

    def __str__(self):
        return "%s?" % self.inner


class TParam(Type):
    """generic type parameter placeholder"""
    __slots__ = ("name", "uid")

    def __init__(self, name, uid=0):
        self.name = name
        self.uid = uid

    def key(self):
        return ("param", self.name, self.uid)

    def __str__(self):
        return self.name


class TStruct(Type):
    __slots__ = ("info", "args")

    def __init__(self, info, args=()):
        self.info = info
        self.args = tuple(args)

    def key(self):
        return ("struct", id(self.info)) + tuple(a.key() for a in self.args)

    def __str__(self):
        n = self.info.name
        if n == "Array" and self.info.builtin and len(self.args) == 1:
            return "[%s]" % self.args[0]
        if n == "Map" and self.info.builtin and len(self.args) == 2:
            return "{%s: %s}" % tuple(self.args)
        if self.args:
            return "%s<%s>" % (n, ", ".join(str(a) for a in self.args))
        return n


class TEnum(Type):
    __slots__ = ("info", "args")

    def __init__(self, info, args=()):
        self.info = info
        self.args = tuple(args)

    def key(self):
        return ("enum", id(self.info)) + tuple(a.key() for a in self.args)

    def __str__(self):
        n = self.info.name
        if self.args:
            return "%s<%s>" % (n, ", ".join(str(a) for a in self.args))
        return n


def subst(t, m):
    """replace TParam placeholders using mapping m: TParam.key -> Type"""
    if not m:
        return t
    if isinstance(t, TParam):
        return m.get(t.key(), t)
    if isinstance(t, TPrim):
        return t
    if isinstance(t, TPtr):
        return TPtr(subst(t.elem, m))
    if isinstance(t, TOpt):
        r = subst(t.inner, m)
        return r if isinstance(r, TOpt) else TOpt(r)
    if isinstance(t, TTuple):
        return TTuple([subst(e, m) for e in t.elems])
    if isinstance(t, TFunc):
        return TFunc([subst(p, m) for p in t.params], subst(t.ret, m))
    if isinstance(t, TStruct):
        return TStruct(t.info, [subst(a, m) for a in t.args]) if t.args else t
    if isinstance(t, TEnum):
        return TEnum(t.info, [subst(a, m) for a in t.args]) if t.args else t
    return t


def has_params(t):
    if isinstance(t, TParam):
        return True
    if isinstance(t, TPrim):
        return False
    if isinstance(t, TPtr):
        return has_params(t.elem)
    if isinstance(t, TOpt):
        return has_params(t.inner)
    if isinstance(t, TTuple):
        return any(has_params(e) for e in t.elems)
    if isinstance(t, TFunc):
        return any(has_params(p) for p in t.params) or has_params(t.ret)
    if isinstance(t, (TStruct, TEnum)):
        return any(has_params(a) for a in t.args)
    return False


def unify(pattern, actual, binds):
    """Match `pattern` (containing TParams) against `actual`. Fills binds (TParam.key -> Type).
    Returns True on success."""
    if isinstance(pattern, TParam):
        k = pattern.key()
        if k in binds:
            return binds[k] == actual or _compatible(binds[k], actual)
        binds[k] = actual
        return True
    if not has_params(pattern):
        return pattern == actual or _compatible(pattern, actual)
    if isinstance(pattern, TPtr):
        return isinstance(actual, TPtr) and unify(pattern.elem, actual.elem, binds)
    if isinstance(pattern, TOpt):
        if isinstance(actual, TOpt):
            return unify(pattern.inner, actual.inner, binds)
        return unify(pattern.inner, actual, binds)
    if isinstance(pattern, TTuple):
        return (isinstance(actual, TTuple) and len(actual.elems) == len(pattern.elems)
                and all(unify(p, a, binds) for p, a in zip(pattern.elems, actual.elems)))
    if isinstance(pattern, TFunc):
        return (isinstance(actual, TFunc) and len(actual.params) == len(pattern.params)
                and all(unify(p, a, binds) for p, a in zip(pattern.params, actual.params))
                and unify(pattern.ret, actual.ret, binds))
    if isinstance(pattern, (TStruct, TEnum)):
        return (type(actual) is type(pattern) and actual.info is pattern.info and len(actual.args) == len(pattern.args)
                and all(unify(p, a, binds) for p, a in zip(pattern.args, actual.args)))
    return False


def _compatible(a, b):
    return False


def is_numeric(t):
    return t == TInt or t == TFloat or t == TByte


def is_intlike(t):
    return t == TInt or t == TByte
