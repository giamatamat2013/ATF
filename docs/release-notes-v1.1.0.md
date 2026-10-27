## Features

- VS Code: `F5` now runs the ATF file you are editing (the same as `ATF: Run File`). `Ctrl+F5` and the play button still work.

## Fixes

- The "first defined at" hint for a function defined twice now follows `ATF_PATH_STYLE=base`, so it no longer prints a full path from the machine that built the compiler.
- CI creates the `build/` folder before the tests, so a clean checkout passes.
