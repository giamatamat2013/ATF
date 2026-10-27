# ATF repository

ATF is a statically typed language that compiles to native Windows x64 `.exe` files.

- `compiler/`: the self-hosted compiler, written in ATF. It builds `bin/atf.exe`.
- `atf/`: the Python bootstrap compiler, plus `atf/stdlib/prelude.atf`, the library that is always available.
- `stdlib/*.atf`: the importable modules (`import "std/name"`).
- `examples/`: the example programs.
- `tools/`: tools written in ATF.
- `editors/vscode/`: the VS Code extension.

Before writing or changing ATF code, load the `atf` skill (`.claude/skills/atf`).

## Rule: every change updates the docs and the skill

A change to the language, the compiler, the standard library, the command line or the editor support is not finished until everything that teaches or describes it is updated in the same piece of work. This covers new features, changed behaviour, removed things, new modules and new functions.

Go through this list for every change. Update whatever the change touches:

| File | What to update |
|---|---|
| `README.md` | Feature list, commands, repository layout, the test list |
| `docs/TUTORIAL.md` | How to use the feature, with a runnable sample |
| `docs/TUTORIAL.he.md` | The same content in Hebrew. Keep it in step with the English tutorial. |
| `docs/STDLIB.md` | Generated. Regenerate it with `bin/atf.exe run tools/stdlib_docs.atf` from the repo root. A new module must also be added to `MODULES` in `tools/stdlib_docs.atf`. Edit the doc comments in the source, not the generated file. |
| `.claude/skills/atf/SKILL.md` | The syntax rules, cheat sheet and pitfalls Claude needs in order to write correct code with the feature |
| `.claude/skills/atf/references/stdlib.md` | A copy of `docs/STDLIB.md`. Copy it again after you regenerate. |
| `editors/vscode/` | `snippets/atf.json`. The grammar in `syntaxes/` for new keywords. `PREFIX_MODULES` and the auto-import in `extension.js` for new module functions. `README.md` for anything user-facing. |
| `examples/` | Add or adjust an example when the feature deserves one. Every top-level `examples/*.atf` needs a matching `.out` file. Window programs go in `examples/ui/`. |
| `tests/` | Add a regression test: `tests/*.atf` + `.out`, or `tests/std/test_<module>.atf` + `.out` |

When you finish, say which of these files you updated. If you skipped any that the change touches, say which and why.

## Building and testing

```
rebuild_compiler.cmd               rebuild bin/atf.exe after changing compiler/ (checks for a fixed point)
python tests/run_tests.py          language tests
python tests/run_examples.py       every program in examples/
python tests/qa/run_qa.py          focused tests, including compiler error messages
python tests/std/run_std_tests.py  standard library modules
python tests/check_docs.py         compiles and runs every code sample in README.md and docs/*.md
python tests/compare_stages.py     bootstrap and native compiler behave the same
```

- A compiler fix goes into both `compiler/*.atf` and `atf/*.py`, so the two compilers stay in step.
- After changing any docs, run `python tests/check_docs.py`.
  - A sample that must not run goes in an ` ```atf nocheck ` block, e.g. one that opens a window.
  - Alternatively, run it with the `ATF_UI_SCREENSHOT` environment variable set.
