## Features

- VS Code: `F5` now runs the ATF file you are editing (the same as `ATF: Run File`). `Ctrl+F5` and the play button still work.
- New standard library modules:
  - `std/regex`: regular expressions (groups, classes, repeats, alternation, anchors, lazy repeats) with `find`, `find_all`, `replace_all` and `split`.
  - `std/path`: take file names apart and join them.
  - `std/fs`: list, copy, move, remove and walk files and folders; read and write lines.
  - `std/process`: run a program and capture its output; environment variables, process id, CPU count.
  - `std/toml`: parse and write TOML configuration files.
  - `std/http`: an HTTP and HTTPS client (`http_get`, `http_post`, `http_request`, `http_download`).
  - `std/test`: a small test framework (`test`, `expect_eq`, `test_report`, ...).
- VS Code: snippets `regex`, `test` and `httpget`, and automatic imports for the new modules.

## Fixes

- The "first defined at" hint for a function defined twice now follows `ATF_PATH_STYLE=base`, so it no longer prints a full path from the machine that built the compiler.
- CI creates the `build/` folder before the tests, so a clean checkout passes.
