"""Compiles and runs every tests/std/test_*.atf with the native compiler (bin/atf.exe) and compares
its standard output with tests/std/test_NAME.out.

usage: python tests/std/run_std_tests.py [name-filter] [--update] [--keep]

  test_NAME.in   (optional) is fed to the program as standard input
  test_NAME.args (optional) one command-line argument per line, passed to the program
  test_NAME.out  is the expected standard output; the program must also exit with code 0
  --update       rewrites test_NAME.out files from the current output (check the diff before committing!)
  --keep         keeps the temporary directory with the built executables
"""
import difflib
import os
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
ATF = os.path.join(ROOT, "bin", "atf.exe")


def build(path, exe):
    """returns (ok, error text). Retries a few times in case bin/atf.exe is being rebuilt."""
    last = ""
    for attempt in range(5):
        if not os.path.exists(ATF):
            last = "bin/atf.exe not found"
            time.sleep(3)
            continue
        try:
            p = subprocess.run([ATF, "build", path, "-o", exe], capture_output=True, timeout=300, cwd=ROOT)
        except (OSError, PermissionError) as e:  # locked while the lead rebuilds the compiler
            last = str(e)
            time.sleep(3)
            continue
        except subprocess.TimeoutExpired:
            return False, "COMPILE TIMEOUT"
        out = (p.stdout + p.stderr).decode("utf-8", "replace").replace("\r\n", "\n")
        if p.returncode == 0 and os.path.exists(exe):
            return True, ""
        return False, out
    return False, last


def run(exe, stdin, args):
    try:
        p = subprocess.run([exe] + args, input=stdin, capture_output=True, timeout=120, cwd=ROOT)
    except subprocess.TimeoutExpired:
        return "", 1, "TIMEOUT\n"
    return (p.stdout.decode("utf-8", "replace").replace("\r\n", "\n"), p.returncode,
            p.stderr.decode("utf-8", "replace").replace("\r\n", "\n"))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    update = "--update" in sys.argv
    keep = "--keep" in sys.argv
    names = sorted(f for f in os.listdir(HERE) if f.startswith("test_") and f.endswith(".atf"))
    if args:
        names = [n for n in names if args[0] in n]
    out_dir = tempfile.mkdtemp(prefix="atf-std-tests-")
    passed = failed = 0
    for n in names:
        path = os.path.join(HERE, n)
        base = path[:-4]
        expected_file = base + ".out"
        stdin_file = base + ".in"
        args_file = base + ".args"
        stdin = open(stdin_file, "rb").read() if os.path.exists(stdin_file) else b""
        prog_args = []
        if os.path.exists(args_file):
            prog_args = [l for l in open(args_file, encoding="utf8").read().splitlines()]
        t0 = time.time()
        exe = os.path.join(out_dir, n[:-4] + ".exe")
        ok, err = build(path, exe)
        if ok:
            actual, code, err = run(exe, stdin, prog_args)
        else:
            actual, code, err = "", 1, "COMPILE ERROR\n" + err
        dt = time.time() - t0
        problem = None
        if code != 0:
            problem = "exit code %d\n%s" % (code, err)
        if update and problem is None:
            with open(expected_file, "w", encoding="utf8", newline="\n") as f:
                f.write(actual)
            print("WROTE  %-28s (%.2fs)" % (n, dt))
            continue
        if problem is None and not os.path.exists(expected_file):
            failed += 1
            print("FAIL   %-28s no %s (run with --update to create it)" % (n, os.path.basename(expected_file)))
            continue
        expected = open(expected_file, encoding="utf8").read().replace("\r\n", "\n") if os.path.exists(expected_file) else ""
        if problem is None and expected == actual:
            passed += 1
            print("ok     %-28s (%.2fs)" % (n, dt))
        else:
            failed += 1
            print("FAIL   %-28s (%.2fs)" % (n, dt))
            if problem:
                for line in problem.splitlines()[:20]:
                    print("   " + line)
            else:
                diff = difflib.unified_diff(expected.splitlines(), actual.splitlines(), "expected", "actual", lineterm="")
                for line in list(diff)[:40]:
                    print("   " + line)
    if keep:
        print("executables kept in", out_dir)
    else:
        shutil.rmtree(out_dir, ignore_errors=True)
    print("\n%d passed, %d failed" % (passed, failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
