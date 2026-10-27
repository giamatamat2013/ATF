"""Compiler access for the test scripts.

By default the native self-hosted compiler bin/atf.exe is used.  Set ATF_STAGE0=1 to use the Python
bootstrap compiler (atf/) instead.
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NATIVE = os.path.join(ROOT, "bin", "atf.exe")


def use_stage0():
    return os.environ.get("ATF_STAGE0") == "1" or not os.path.exists(NATIVE)


def compile_to(path, exe):
    """Compiles `path` into `exe`. Returns (ok, error_text). Error paths are shown as base names."""
    if use_stage0():
        sys.path.insert(0, ROOT)
        from atf import driver, errors
        from atf.checker import MultiError
        from atf.errors import CompileError
        errors.PATH_STYLE = "base"
        try:
            data = driver.compile_file(path)
        except (CompileError, MultiError) as e:
            return False, e.render() + "\n"
        with open(exe, "wb") as f:
            f.write(data)
        return True, ""
    env = dict(os.environ, ATF_PATH_STYLE="base")
    if os.path.exists(exe):
        os.remove(exe)
    p = subprocess.run([NATIVE, "build", path, "-o", exe], capture_output=True, env=env, cwd=ROOT)
    if p.returncode != 0 or not os.path.exists(exe):
        err = p.stderr.decode("utf-8", "replace").replace("\r\n", "\n")
        return False, err if err.endswith("\n") else err + "\n"
    return True, ""
