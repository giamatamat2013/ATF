"""Starts a compiled ATF program. On Windows the .exe runs by itself; elsewhere (for example a Linux server) it runs through Wine."""
import os
import shutil
import sys


def program_argv(exe):
    """the command line that starts the program `exe`, as a list for subprocess"""
    if sys.platform == "win32":
        return [exe]
    wine = os.environ.get("ATF_WINE") or shutil.which("wine") or shutil.which("wine64")
    if not wine:
        raise RuntimeError("ATF programs are Windows programs. On Linux install Wine (sudo apt install wine64), "
                           "or set ATF_WINE to the wine program")
    os.environ.setdefault("WINEDEBUG", "-all")   # Wine's own messages would end up in the program's output
    return [wine, exe]
