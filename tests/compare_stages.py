"""Differential test: programs built by the Python compiler (stage 0, the frozen bootstrap) and by the
self-hosted compiler (stage 1) must behave the same. Identical executables count as the same; otherwise both
are run (stdin from NAME.in when it exists) and their stdout and exit codes are compared.
Error messages and tracebacks (stderr) may differ, since stage 1 reports more detail.

usage: python tests/compare_stages.py [stage1.exe] [name-filter]"""
import os
import re
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from atf import driver, errors  # noqa: E402
from atf.checker import MultiError  # noqa: E402
from atf.errors import CompileError  # noqa: E402

errors.PATH_STYLE = "base"
RUN_TIMEOUT = 60


def run_exe(exe, stdin):
    try:
        r = subprocess.run([exe], input=stdin, capture_output=True, timeout=RUN_TIMEOUT, cwd=ROOT)
    except subprocess.TimeoutExpired:
        return ("timeout", b"")
    out = r.stdout.replace(b"\r\n", b"\n")
    # benchmarks print their running time:  time 0.123 ...
    out = re.sub(rb"(?m)^time [0-9.e-]+", b"time ?", out)
    return (r.returncode, out)


def write_exe(path, data):
    # On Windows the open can fail for a moment right after the file was run (a scanner may still hold it).
    for attempt in range(10):
        try:
            with open(path, "wb") as fh:
                fh.write(data)
            return
        except OSError:
            if attempt == 9:
                raise
            time.sleep(0.5)


def main():
    stage1 = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "bin", "atf.exe")
    stage1 = os.path.abspath(stage1)
    filt = sys.argv[2] if len(sys.argv) > 2 else ""
    files = []
    for d in ("tests", "examples", "bench"):
        for n in sorted(os.listdir(os.path.join(ROOT, d))):
            if n.endswith(".atf") and filt in n:
                files.append(os.path.join(d, n))
    env = dict(os.environ, ATF_PATH_STYLE="base")
    same = bad = 0
    out0 = os.path.join(ROOT, "build", "stage0_out.exe")
    out1 = os.path.join(ROOT, "build", "stage1_out.exe")
    for f in files:
        path = os.path.join(ROOT, f)
        try:
            exp = driver.compile_file(path)
        except (CompileError, MultiError):
            exp = None
        if os.path.exists(out1):
            os.remove(out1)
        p = subprocess.run([stage1, "build", path, "-o", out1], capture_output=True, env=env, cwd=ROOT)
        got = open(out1, "rb").read() if os.path.exists(out1) else None
        if exp is None and got is not None:
            print("stage 1 only        %s  (uses features the frozen bootstrap does not have)" % f)
            same += 1
            continue
        if exp is None and got is None:
            print("same (both reject)  %s" % f)
            same += 1
            continue
        if got is None:
            bad += 1
            print("DIFFERENT           %s  (stage 1 rejects it)" % f)
            print("   " + p.stderr.decode("utf-8", "replace").strip().replace("\n", "\n   ")[:600])
            continue
        if exp == got:
            print("same binary         %s" % f)
            same += 1
            continue
        write_exe(out0, exp)
        stdin = b""
        inp = path[:-4] + ".in"
        if os.path.exists(inp):
            with open(inp, "rb") as fh:
                stdin = fh.read()
        r0 = run_exe(out0, stdin)
        r1 = run_exe(out1, stdin)
        if r0 == r1:
            print("same behaviour      %s" % f)
            same += 1
        else:
            bad += 1
            print("DIFFERENT           %s  (exit %s vs %s)" % (f, r0[0], r1[0]))
            a = r0[1].decode("utf-8", "replace").splitlines()
            b = r1[1].decode("utf-8", "replace").splitlines()
            for i in range(max(len(a), len(b))):
                la = a[i] if i < len(a) else "<none>"
                lb = b[i] if i < len(b) else "<none>"
                if la != lb:
                    print("   line %d: stage0 %r / stage1 %r" % (i + 1, la[:120], lb[:120]))
                    break
    print("\n%d same, %d different" % (same, bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
