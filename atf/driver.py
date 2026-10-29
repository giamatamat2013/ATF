"""Compiler driver: load source files, check, generate code, write the executable."""
import hashlib
import os
import shlex
import subprocess
import sys
import tempfile

from . import errors
from .errors import CompileError
from .launch import program_argv
from .parser import parse_source, DECLARED_VERSION
from . import syntax as S

HERE = os.path.dirname(os.path.abspath(__file__))
STDLIB = os.path.join(HERE, "stdlib")                                   # prelude.atf lives here
STD_MODULES = os.path.join(os.path.dirname(HERE), "stdlib")             # importable as  import "std/name"
VERSION = "1.2.0"


def read_source(path):
    with open(path, "rb") as f:
        data = f.read()
    if data.startswith(b"\xef\xbb\xbf"):
        data = data[3:]
    text = data.decode("utf-8")
    errors.SOURCES[path] = text.replace("\r\n", "\n")
    return text.replace("\r\n", "\n")


def version_value(v):
    """'1.2.3' -> 1002003, so that versions compare as numbers; 0 when v is not three numbers"""
    parts = v.split(" ")[0].split(".")
    if len(parts) != 3 or not all(p != "" and all("0" <= c <= "9" for c in p) for p in parts):
        return 0
    n = 0
    for p in parts:
        n = n * 1000 + int(p)
    return n


def warn_if_newer(path):
    """a program written for a newer ATF may not compile here: say so, but compile it anyway"""
    want = DECLARED_VERSION.get(os.path.abspath(path), "")
    if want and version_value(want) > version_value(VERSION):
        print("warning: this file was written for ATF %s, but this compiler is ATF %s; it may not compile"
              % (want, VERSION), file=sys.stderr)


def resolve_import(name, from_file):
    if not name.endswith(".atf"):
        name += ".atf"
    if name.startswith("std/"):
        p = os.path.join(STD_MODULES, name[4:])
        return p, True
    base = os.path.dirname(os.path.abspath(from_file))
    p = os.path.normpath(os.path.join(base, name))
    if os.path.exists(p):
        return p, False
    p2 = os.path.join(STD_MODULES, name)
    if os.path.exists(p2):
        return p2, True
    return p, False


def load_program(path):
    """returns list of (items, is_prelude) in dependency order: prelude first"""
    modules = []
    seen = set()

    def load(p, prelude, from_pos=None):
        p = os.path.abspath(p)
        if p in seen:
            return
        seen.add(p)
        if not os.path.exists(p):
            raise CompileError("cannot find file '%s'" % p, from_pos)
        src = read_source(p)
        items = parse_source(src, p)
        for it in items:
            if isinstance(it, S.ImportDecl):
                ip, ipre = resolve_import(it.path, p)
                if not os.path.exists(ip):
                    raise CompileError("cannot find module '%s'" % it.path, it.pos,
                                       "imports are relative to this file, or  import \"std/name\"  for the standard library")
                load(ip, ipre or prelude, it.pos)
        modules.append((items, prelude))

    load(os.path.join(STDLIB, "prelude.atf"), True)
    load(path, False)
    # std modules the program uses without importing them (see autoimport.py)
    from .autoimport import auto_import_modules
    texts = {}
    user = []
    for p in seen:
        texts[p] = read_source(p)
        if not p.startswith(os.path.abspath(STDLIB)) and not p.startswith(os.path.abspath(STD_MODULES)):
            user.append(p)
    for m in auto_import_modules(STD_MODULES, texts, user):
        load(os.path.join(STD_MODULES, m + ".atf"), True)
    return modules


def compile_file(path, check_only=False):
    from .checker import Checker, MultiError
    from .codegen import CodeGen
    modules = load_program(path)
    warn_if_newer(path)
    chk = Checker()
    for items, prelude in modules:
        chk.declare_module(items, prelude)
    program = chk.run()
    if check_only:
        return None
    cg = CodeGen(program)
    img = cg.generate()
    return img.build()


def disasm(path, pattern):
    from .checker import Checker, MultiError
    from .codegen import CodeGen
    try:
        import capstone
    except ImportError:
        print("the 'asm' command needs the capstone package (pip install capstone)")
        return 1
    modules = load_program(path)
    chk = Checker()
    for items, prelude in modules:
        chk.declare_module(items, prelude)
    program = chk.run()
    cg = CodeGen(program)
    img = cg.generate()
    code = bytes(img.text)
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
    funcs = sorted(program.funcs, key=lambda f: cg.a.labels[f.label])
    offs = [cg.a.labels[f.label] for f in funcs] + [len(code)]
    for i, f in enumerate(funcs):
        if pattern in f.name:
            print()
            print(f.name + ":")
            for ins in md.disasm(code[offs[i]:offs[i + 1]], offs[i]):
                print("  %05x  %s %s" % (ins.address, ins.mnemonic, ins.op_str))
    return 0


def exe_path_for(path, out=None):
    if out:
        return out
    base = os.path.splitext(os.path.abspath(path))[0]
    return base + ".exe"


def build(path, out=None, check_only=False):
    from .checker import MultiError
    try:
        data = compile_file(path, check_only)
    except MultiError as e:
        print(e.render(), file=sys.stderr)
        return None
    except CompileError as e:
        print(e.render(), file=sys.stderr)
        return None
    if check_only:
        return path
    target = exe_path_for(path, out)
    with open(target, "wb") as f:
        f.write(data)
    return target


def run(path, args):
    from .checker import MultiError
    try:
        data = compile_file(path)
    except MultiError as e:
        print(e.render(), file=sys.stderr)
        return 1
    except CompileError as e:
        print(e.render(), file=sys.stderr)
        return 1
    h = hashlib.sha1(os.path.abspath(path).encode()).hexdigest()[:8]
    d = os.path.join(tempfile.gettempdir(), "atf")
    os.makedirs(d, exist_ok=True)
    exe = os.path.join(d, "%s-%s.exe" % (os.path.splitext(os.path.basename(path))[0], h))
    with open(exe, "wb") as f:
        f.write(data)
    try:
        argv = program_argv(exe)
    except RuntimeError as e:
        print("error: %s" % e, file=sys.stderr)
        return 1
    try:
        return subprocess.call(argv + list(args))
    except OSError as e:
        print("error: cannot run the compiled program (%s)" % e, file=sys.stderr)
        if sys.platform == "win32":
            print("hint: Windows may be blocking unsigned executables (Smart App Control / Application Control).", file=sys.stderr)
        return 1


USAGE = """ATF %s - a small, fast, compiled programming language

usage:
  atf run   file.atf [args...]     compile and run
  atf shell                         interactive command line for ATF commands
  atf interpret file.atf            interpret; use native backend when needed
  atf build file.atf [-o out.exe]  compile to a native executable
  atf check file.atf               check for errors only
  atf version
""" % VERSION


def shell():
    native = os.path.join(os.path.dirname(HERE), "bin", "atf.exe")
    if os.path.isfile(native):
        try:
            return subprocess.call(program_argv(native) + ["shell"])
        except (OSError, RuntimeError):
            pass
    print("ATF %s command line. Enter an ATF command; type exit to quit." % VERSION)
    while True:
        try:
            line = input("ATF> ").strip()
        except EOFError:
            break
        if not line:
            continue
        if line in ("exit", "quit"):
            break
        if line in ("help", "--help", "-h"):
            print(USAGE)
            continue
        if line.startswith("atf "):
            line = line[4:].lstrip()
        if line == "shell":
            print("already in the ATF command line; type exit to quit")
            continue
        if not line:
            print(USAGE)
            continue
        main(["atf"] + shlex.split(line))

def main(argv):
    if len(argv) < 2 or argv[1] in ("-h", "--help", "help"):
        print(USAGE)
        return 0
    cmd = argv[1]
    if cmd == "shell":
        return shell() or 0
    if cmd == "interpret":
        native = os.path.join(os.path.dirname(HERE), "bin", "atf.exe")
        if os.path.isfile(native):
            try:
                return subprocess.call(program_argv(native) + ["interpret"] + argv[2:])
            except (OSError, RuntimeError) as e:
                print("error: cannot start the ATF interpreter (%s)" % e, file=sys.stderr)
                return 1
        print("error: the interpreter requires the self-hosted compiler (bin/atf.exe)", file=sys.stderr)
        return 1
    if cmd == "version":
        print("ATF " + VERSION)
        return 0
    if cmd == "asm":
        return disasm(argv[2], argv[3] if len(argv) > 3 else "")
    if cmd in ("run", "build", "check"):
        if len(argv) < 3:
            print("error: missing file name\n\n" + USAGE, file=sys.stderr)
            return 2
        path = argv[2]
        if not os.path.exists(path):
            print("error: file not found: %s" % path, file=sys.stderr)
            return 2
        if cmd == "run":
            return run(path, argv[3:])
        out = None
        if "-o" in argv:
            out = argv[argv.index("-o") + 1]
        r = build(path, out, check_only=(cmd == "check"))
        if r is None:
            return 1
        if cmd == "build":
            print("built %s" % r)
        else:
            print("ok")
        return 0
    print("error: unknown command '%s'\n\n%s" % (cmd, USAGE), file=sys.stderr)
    return 2
