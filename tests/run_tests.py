"""Runs every tests/*.atf, compares stdout with the matching .out file.
usage: python tests/run_tests.py [name-filter] [--update]"""
import os
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests"))
import atfc  # noqa: E402


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    update = "--update" in sys.argv
    tdir = os.path.join(ROOT, "tests")
    names = sorted(f for f in os.listdir(tdir) if f.endswith(".atf"))
    if args:
        names = [n for n in names if args[0] in n]
    out_dir = tempfile.mkdtemp(prefix="atf-tests-")
    passed = failed = 0
    for n in names:
        path = os.path.join(tdir, n)
        base = path[:-4]
        expected_file = base + ".out"
        stdin_file = base + ".in"
        t0 = time.time()
        exe = os.path.join(out_dir, n[:-4] + ".exe")
        ok, err = atfc.compile_to(path, exe)
        if not ok:
            actual = "COMPILE ERROR\n" + err
            code = 0
        else:
            stdin = open(stdin_file, "rb").read() if os.path.exists(stdin_file) else b""
            try:
                p = subprocess.run([exe], input=stdin, capture_output=True, timeout=60)
                actual = p.stdout.decode("utf-8", "replace").replace("\r\n", "\n")
                if p.returncode != 0:
                    actual += "[exit %d]\n" % (p.returncode if p.returncode < 1 << 31 else p.returncode - (1 << 32))
                    err = p.stderr.decode("utf-8", "replace").replace("\r\n", "\n")
                    actual += "[stderr] " + err
            except subprocess.TimeoutExpired:
                actual = "TIMEOUT\n"
        dt = time.time() - t0
        if update or not os.path.exists(expected_file):
            with open(expected_file, "w", encoding="utf8", newline="\n") as f:
                f.write(actual)
            print("WROTE  %-28s (%.2fs)" % (n, dt))
            continue
        expected = open(expected_file, encoding="utf8").read().replace("\r\n", "\n")
        if expected == actual:
            passed += 1
            print("ok     %-28s (%.2fs)" % (n, dt))
        else:
            failed += 1
            print("FAIL   %-28s (%.2fs)" % (n, dt))
            import difflib
            for line in list(difflib.unified_diff(expected.splitlines(), actual.splitlines(), "expected", "actual", lineterm=""))[:30]:
                print("   " + line)
    print("\n%d passed, %d failed" % (passed, failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
