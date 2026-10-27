"""Compiles and runs every examples/*.atf and compares its standard output with examples/NAME.out.

usage: python tests/run_examples.py [name-filter] [--update] [--cli]

  NAME.in   (optional) is fed to the program as standard input
  NAME.out  is the expected standard output; the program must also exit with code 0
  --update  rewrites NAME.out files from the current output (check the diff before committing!)
  --cli     runs each example through the real command line  `python run_atf.py run examples/NAME.atf`
            instead of compiling in-process (slower, but tests exactly what a user types)
"""
import os
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests"))
import atfc  # noqa: E402


def run_in_process(path, stdin, out_dir):
    """returns (stdout text, exit code, stderr text)"""
    exe = os.path.join(out_dir, os.path.basename(path)[:-4] + ".exe")
    ok, err = atfc.compile_to(path, exe)
    if not ok:
        return "", 1, "COMPILE ERROR\n" + err
    try:
        p = subprocess.run([exe], input=stdin, capture_output=True, timeout=120)
    except subprocess.TimeoutExpired:
        return "", 1, "TIMEOUT\n"
    return (p.stdout.decode("utf-8", "replace").replace("\r\n", "\n"), p.returncode,
            p.stderr.decode("utf-8", "replace").replace("\r\n", "\n"))


def run_cli(path, stdin, out_dir):
    try:
        p = subprocess.run([sys.executable, os.path.join(ROOT, "run_atf.py"), "run", path], input=stdin,
                           capture_output=True, timeout=180, cwd=ROOT)
    except subprocess.TimeoutExpired:
        return "", 1, "TIMEOUT\n"
    return (p.stdout.decode("utf-8", "replace").replace("\r\n", "\n"), p.returncode,
            p.stderr.decode("utf-8", "replace").replace("\r\n", "\n"))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    update = "--update" in sys.argv
    cli = "--cli" in sys.argv
    edir = os.path.join(ROOT, "examples")
    names = sorted(f for f in os.listdir(edir) if f.endswith(".atf"))
    if args:
        names = [n for n in names if args[0] in n]
    out_dir = tempfile.mkdtemp(prefix="atf-examples-")
    passed = failed = 0
    for n in names:
        path = os.path.join(edir, n)
        base = path[:-4]
        expected_file = base + ".out"
        stdin_file = base + ".in"
        stdin = open(stdin_file, "rb").read() if os.path.exists(stdin_file) else b""
        t0 = time.time()
        actual, code, err = (run_cli if cli else run_in_process)(path, stdin, out_dir)
        dt = time.time() - t0
        problem = None
        if code != 0:
            problem = "exit code %d\n%s" % (code, err)
        if update and problem is None:
            with open(expected_file, "w", encoding="utf8", newline="\n") as f:
                f.write(actual)
            print("WROTE  %-22s (%.2fs)" % (n, dt))
            continue
        if not os.path.exists(expected_file):
            failed += 1
            print("FAIL   %-22s no %s (run with --update to create it)" % (n, os.path.basename(expected_file)))
            continue
        expected = open(expected_file, encoding="utf8").read().replace("\r\n", "\n")
        if problem is None and expected == actual:
            passed += 1
            print("ok     %-22s (%.2fs)" % (n, dt))
        else:
            failed += 1
            print("FAIL   %-22s (%.2fs)" % (n, dt))
            if problem:
                for line in problem.splitlines()[:15]:
                    print("   " + line)
            else:
                import difflib
                for line in list(difflib.unified_diff(expected.splitlines(), actual.splitlines(), "expected", "actual", lineterm=""))[:30]:
                    print("   " + line)
    print("\n%d passed, %d failed" % (passed, failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
