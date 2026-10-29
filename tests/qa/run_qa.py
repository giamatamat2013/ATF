"""QA test runner for ATF.

Every tests/qa/NAME.atf is compiled with bin/atf.exe, run (stdin from NAME.in if it exists, arguments
from NAME.args if it exists) and its output is compared with NAME.expected.

Output format (same convention as tests/run_tests.py):
  * a program that compiles: its stdout; if the exit code is not 0, then "[exit N]" and "[stderr] ..." lines
  * a program that does not compile: "COMPILE ERROR" followed by the compiler's messages
The compiler is run with ATF_PATH_STYLE=base so file names in messages are base names.

A compiler crash ("internal compiler error", or a compiler exit code other than 0/1) is always
reported as a failure, even if the output happens to match.

usage:
  python tests/qa/run_qa.py [filters...] [-v] [--show] [-j N] [--keep]
    filters   only run tests whose name contains one of the filters
    -v        show a diff for every failure
    --show    print the actual output of every selected test
    -j N      number of tests run in parallel (default: number of CPUs)
    --keep    keep the build directory (its path is printed)
The actual output of failed tests is written to tests/qa/_actual/NAME.actual.
"""
import concurrent.futures
import difflib
import os
import shutil
import subprocess
import sys
import tempfile
import time

QA = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(QA))
ATF = os.path.join(ROOT, "bin", "atf.exe")
sys.path.insert(0, ROOT)
from atf.launch import program_argv  # noqa: E402
ACTUAL_DIR = os.path.join(QA, "_actual")
RUN_TIMEOUT = 120
COMPILE_TIMEOUT = 120


def norm(b):
    return b.decode("utf-8", "replace").replace("\r\n", "\n")


def run_compiler(args, env):
    # the lead may be rebuilding bin/atf.exe: retry a few times if it is missing or locked
    for attempt in range(10):
        if os.path.exists(ATF):
            try:
                return subprocess.run(program_argv(ATF) + args, capture_output=True, env=env, cwd=ROOT,
                                      timeout=COMPILE_TIMEOUT)
            except PermissionError:
                pass
            except OSError:
                pass
        time.sleep(3)
    raise RuntimeError("bin/atf.exe is not available")


def run_one(name, build_dir):
    src = os.path.join(QA, name + ".atf")
    exe = os.path.join(build_dir, name + ".exe")
    env = dict(os.environ, ATF_PATH_STYLE="base")
    crash = None
    t0 = time.time()
    try:
        p = run_compiler(["build", src, "-o", exe], env)
    except subprocess.TimeoutExpired:
        return name, "COMPILER TIMEOUT\n", "compiler timed out", time.time() - t0
    err = norm(p.stderr)
    if "internal compiler error" in err.lower() or p.returncode not in (0, 1):
        crash = "compiler crashed (exit code %d)" % p.returncode
    if p.returncode != 0 or not os.path.exists(exe):
        if err and not err.endswith("\n"):
            err += "\n"
        out = norm(p.stdout)
        return name, "COMPILE ERROR\n" + out + err, crash, time.time() - t0
    stdin = b""
    if os.path.exists(os.path.join(QA, name + ".in")):
        with open(os.path.join(QA, name + ".in"), "rb") as f:
            stdin = f.read()
    args = []
    if os.path.exists(os.path.join(QA, name + ".args")):
        with open(os.path.join(QA, name + ".args"), encoding="utf8") as f:
            args = f.read().split()
    try:
        r = subprocess.run(program_argv(exe) + args, input=stdin, capture_output=True, timeout=RUN_TIMEOUT, cwd=build_dir)
    except subprocess.TimeoutExpired:
        return name, "TIMEOUT\n", crash, time.time() - t0
    actual = norm(r.stdout)
    if r.returncode != 0:
        code = r.returncode if r.returncode < 1 << 31 else r.returncode - (1 << 32)
        if actual and not actual.endswith("\n"):
            actual += "\n"
        actual += "[exit %d]\n" % code
        e = norm(r.stderr)
        if e:
            actual += "[stderr] " + e
            if not actual.endswith("\n"):
                actual += "\n"
    return name, actual, crash, time.time() - t0


def run_shell_smoke():
    env = dict(os.environ, ATF_PATH_STYLE="base")
    try:
        result = subprocess.run(program_argv(ATF) + ["shell"], input=b"print(\"raw\")\nprintln(\"test\")\nlet shell_value = 7\nshell_value + 1\natf interpret tests/qa/interpreter.atf\natf interpret tests/qa/interpreter_native_fallback.atf\natf version\nexit\n",
                                capture_output=True, env=env, cwd=ROOT, timeout=15)
    except (OSError, subprocess.TimeoutExpired) as e:
        return False, str(e)
    output = norm(result.stdout)
    version = open(os.path.join(ROOT, "VERSION"), encoding="utf8").read().strip()
    expected = "> ATF " + version
    return (result.returncode == 0 and "raw\nATF " in output and "test" in output and "8" in output and "21" in output and "42" in output
            and expected in output and output.endswith("> ")), output

def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    argv = sys.argv[1:]
    verbose = "-v" in argv
    show = "--show" in argv
    keep = "--keep" in argv
    jobs = os.cpu_count() or 4
    filters = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "-j":
            jobs = int(argv[i + 1])
            i += 2
            continue
        if not a.startswith("-"):
            filters.append(a)
        i += 1
    names = sorted(f[:-4] for f in os.listdir(QA) if f.endswith(".atf"))
    if filters:
        names = [n for n in names if any(f in n for f in filters)]
    # inside build/, not the temp folder: Windows Defender blocks the programs built in the temp folder
    qa_root = os.path.join(ROOT, "build", "qa")
    os.makedirs(qa_root, exist_ok=True)
    build_dir = tempfile.mkdtemp(prefix="atf-qa-", dir=qa_root)
    os.makedirs(ACTUAL_DIR, exist_ok=True)
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as ex:
        futs = [ex.submit(run_one, n, build_dir) for n in names]
        for f in concurrent.futures.as_completed(futs):
            results.append(f.result())
    results.sort()
    passed = []
    failed = []
    missing = []
    for name, actual, crash, dt in results:
        exp_path = os.path.join(QA, name + ".expected")
        act_path = os.path.join(ACTUAL_DIR, name + ".actual")
        if show:
            print("=" * 20, name)
            print(actual, end="")
        if not os.path.exists(exp_path):
            missing.append(name)
            with open(act_path, "w", encoding="utf8", newline="\n") as f:
                f.write(actual)
            print("NOEXP  %-34s (%.2fs)" % (name, dt))
            continue
        with open(exp_path, encoding="utf8") as f:
            expected = f.read().replace("\r\n", "\n")
        if expected == actual and not crash:
            passed.append(name)
            if os.path.exists(act_path):
                os.remove(act_path)
            if not show:
                print("ok     %-34s (%.2fs)" % (name, dt))
            continue
        failed.append(name)
        with open(act_path, "w", encoding="utf8", newline="\n") as f:
            f.write(actual)
        print("FAIL   %-34s (%.2fs)%s" % (name, dt, "  [" + crash + "]" if crash else ""))
        if verbose:
            diff = list(difflib.unified_diff(expected.splitlines(), actual.splitlines(),
                                             "expected", "actual", lineterm=""))
            for line in diff[:60]:
                print("    " + line)
            if len(diff) > 60:
                print("    ... (%d more diff lines)" % (len(diff) - 60))
    if not filters or any("shell" in f for f in filters):
        shell_ok, shell_output = run_shell_smoke()
        if shell_ok:
            passed.append("shell")
            print("ok     %-34s" % "shell")
        else:
            failed.append("shell")
            with open(os.path.join(ACTUAL_DIR, "shell.actual"), "w", encoding="utf8", newline="\n") as f:
                f.write(shell_output)
            print("FAIL   %-34s" % "shell")
            if verbose:
                print("    " + shell_output.replace("\n", "\n    "))
    if keep:
        print("build directory:", build_dir)
    else:
        shutil.rmtree(build_dir, ignore_errors=True)
    print("\n%d passed, %d failed, %d without .expected" % (len(passed), len(failed), len(missing)))
    if failed:
        print("failures:")
        for n in failed:
            print("  " + n)
    return 1 if failed or missing else 0


if __name__ == "__main__":
    sys.exit(main())
