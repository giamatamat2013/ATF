"""Checks that every place that carries the version number agrees with the VERSION file,
and that the release notes for that version exist.
usage: python tests/check_version.py"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (file, regex whose group 1 is the version in it)
PLACES = [
    ("atf/driver.py", r'^VERSION = "([^"]+)"'),
    ("compiler/main.atf", r'^const VERSION = "(\d+\.\d+\.\d+)'),
    ("compiler/main_front.atf", r'^const VERSION = "(\d+\.\d+\.\d+)'),
    ("editors/vscode/package.json", r'"version"\s*:\s*"([^"]+)"'),
]


def read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return f.read()


def main():
    version = read("VERSION").strip()
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        print("FAIL VERSION is not FEATURE.SMALL.FIX: " + version)
        return 1
    bad = 0
    for rel, rx in PLACES:
        m = re.search(rx, read(rel), re.M)
        found = m.group(1) if m else "(not found)"
        if found == version:
            print("PASS " + rel + " " + found)
        else:
            print("FAIL %s has %s, VERSION says %s" % (rel, found, version))
            bad += 1
    notes = "docs/release-notes-v%s.md" % version
    if os.path.exists(os.path.join(ROOT, notes)):
        print("PASS " + notes)
    else:
        print("FAIL missing " + notes)
        bad += 1
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
