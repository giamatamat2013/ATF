# ATF repository

ATF is a statically typed language that compiles to native Windows x64 `.exe` files.

- `compiler/`: the self-hosted compiler, written in ATF. It builds `bin/atf.exe`.
- `atf/`: the Python bootstrap compiler, plus `atf/stdlib/prelude.atf`, the library that is always available.
- `stdlib/*.atf`: the importable modules (`import "std/name"`).
- `examples/`: the example programs.
- `tools/`: tools written in ATF.
- `editors/vscode/`: the VS Code extension.
- `demos.html`: a single-page demo gallery (ATF vs Python). It must be kept up to date regularly, see the rule below.

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
| `demos.html` | The demo page (ATF next to Python, with output). Add a demo to the `demos` array when a feature deserves one, and fix any demo whose code or output the change affects. Take the output from a real run (`bin/atf.exe run`), never from memory. Keep each ATF sample runnable. |
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

- Tests are written in ATF (`tests/*.atf` + `.out`); Python is only for the runners and for the bootstrap compiler `atf/`.
- Adding, renaming or removing a top-level name in `stdlib/*.atf` needs `bin/atf.exe run tools/make_stdlib_index.atf`, which rewrites `stdlib/index.txt` (`tests/stdlib_index_fresh.atf` fails when it is stale). A std module's own top-level names must not clash with another module's: a clashing name is left out of the index and needs an explicit `import`.

- A compiler fix goes into both `compiler/*.atf` and `atf/*.py`, so the two compilers stay in step.
- After changing any docs, run `python tests/check_docs.py`.
  - A sample that must not run goes in an ` ```atf nocheck ` block, e.g. one that opens a window.
  - Alternatively, run it with the `ATF_UI_SCREENSHOT` environment variable set.

## Releasing ATF

Repository: `tamat2013/ATF`. Default branch: `master`. Version number lives in `VERSION` (the single source of truth). Tag format: `vX.Y.Z`. Release workflow: `.github/workflows/release.yml`.

### Rules

1. **Never release before the change is known to work.** Besides the test suites, run the real thing: build with `rebuild_compiler.cmd` (it must reach the fixed point) and run `bin/atf.exe version` and one example.
2. Work and release directly on `master` (no feature branches).
3. Never release on top of a CI run you already know is red.
4. A bad release is deleted with its tag (`DELETE /repos/tamat2013/ATF/releases/<id>` and `DELETE /repos/tamat2013/ATF/git/refs/tags/vX.Y.Z`), then fixed and released again with the same number.
5. The GitHub token always comes from `git credential fill` and is never printed or written to a file. `gh` is not installed: use the REST API from Python.

### Version numbers

Format `FEATURE.SMALL.FIX`, always three parts, starting at `1.0.0`. The format must not change.

- A fix raises the last number by 1.
- When the last number would reach 10 (10 fixes), the middle number rises by 1 and the last resets to 0 (`1.0.9` -> `1.1.0`).
- When the middle number would reach 100 (100 such steps), the first number rises by 1 and the other two reset to 0 (`1.99.9` -> `2.0.0`).
- A release that adds a feature raises the middle number and resets the last to 0 (`1.0.4` -> `1.1.0`). Only the biggest change in the release counts.
- Any commit after a release needs a new version before the next release.
- The version appears in `VERSION`, `atf/driver.py`, `compiler/main.atf`, `compiler/main_front.atf` and `editors/vscode/package.json`. Change all of them together; `python tests/check_version.py` fails if one differs. After changing `compiler/`, run `rebuild_compiler.cmd` and commit the new `bin/atf.exe`.
- No pre-releases.

### Release notes

File: `docs/release-notes-vX.Y.Z.md` (it becomes the GitHub Release body). Sections in this order, empty ones omitted:

```
## Features
- ...

## Fixes
- ...
```

### Release dashboard

A live local page that shows percent done, what is happening now, the pipeline stages, a live log, the task list, the GitHub jobs and the local tests. Read-only: it never pushes or releases.

- Start it (runs until the version is published, at most 3 hours): `python tools/release_status/status_page.py`
- Open `tools/release_status/status.html` in a browser.
- Keep it current: `python tools/release_status/log.py "what I am doing now"` at every step; rewrite `tools/release_status/todo.json` (`[{"text": "...", "state": "todo|run|done"}]`) when a task starts or ends; `python tools/release_status/reset.py` clears it.

### Local tests

`python tools/release_status/run_local_tests.py` runs the whole set (7 suites: `language`, `examples`, `qa`, `std`, `docs`, `stages`, `version`) and writes `local-tests.json`, which the dashboard shows. Name some suites to run only those; a single name is shown in its own card.

- The suites run one after the other (they share `bin/` and `build/`); `--parallel N` overrides this.
- Pass nothing but test names or `--parallel N` / `--serial`.
- Every new suite is added to `DEFAULT` and `SCRIPTS` in `run_local_tests.py` **and** to `.github/workflows/tests.yml`.
- **Stop at the first failure.** Run `python tools/release_status/watch_tests.py` in the background: it starts the run, reads the progress every 3 seconds and, at the first failed suite, kills the run, prints the failure and exits 1; when everything passed it prints `FINISHED OK` and exits 0. Fix, then run everything again.
- A suite that failed in the full run is run again alone before it is called broken.
- Never start a second run while one is running.

### Procedure

1. Update the dashboard (`todo.json`, `log.py`).
2. Collect what goes in: `git log <last-tag>..HEAD --oneline` (and open issues). Decide the version number.
3. Bump the version in all five places and write the release notes.
4. Rebuild with `rebuild_compiler.cmd` and check the real compiler runs (see rule 1).
5. Run the local tests with the watcher.
6. Commit and push to `master`; wait until `git status -sb` shows no "ahead".
7. Check the tag does not exist: `GET /repos/tamat2013/ATF/git/ref/tags/<tag>` must be 404.
8. Dispatch: `POST /repos/tamat2013/ATF/actions/workflows/release.yml/dispatches` with `{"ref":"master"}` (204). Do not release by pushing a tag; the workflow reads `VERSION`, runs the tests, builds, creates the tag and publishes.
9. Watch it: `python tools/release_status/watch_release.py tamat2013/ATF` in the background (prints the jobs on change, exits 1 at the first failed job, 0 on success). At the first failure: read the job log (`GET /actions/jobs/<id>/logs`), cancel the run, fix, push, dispatch again.
10. On success check that the Release has its 2 assets: `atf-X.Y.Z-windows-x64.zip` and `SHA256SUMS.txt`.
11. Comment the version on every issue the release fixed and close it.
12. Finish the dashboard: `todo.json` all `done`, a last log line.

Typical durations: tests about 5 minutes on GitHub, the whole workflow about 8 minutes.

### Common problems

| Symptom | Action |
|---|---|
| Dashboard shows "everything failed" | A stale `local-tests.json` from a killed run: delete it |
| `git push` of a tag fails | Do not push tags; dispatch the workflow |
| API returns 401 | `git credential fill` returned an empty password: sign in to git again |
| `check_version.py` fails | One of the five version places was not changed |
