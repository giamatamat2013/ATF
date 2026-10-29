## Features

- Interactive shell: `atf shell` has a built-in line editor (history, colors, Tab completion) and understands ATF code, compiler commands and cmd, PowerShell and Unix-style commands (`cd`, `ls`, `grep`, any program). `atf shell -c "..."` and `atf shell -f script` run non-interactively. The same commands are available from a program with `std/shell`.
- `atf interpret file.atf` runs a program with the ATF interpreter backend, with native fallback for what it does not support.
- Automatic standard library imports: using a name from a `std/` module (`json_parse`, `ui_run`, `Node`, ...) imports the module by itself (`stdlib/index.txt`, made by `tools/make_stdlib_index.atf`). Hand-written imports still work.
- New commands: `atf test`, `atf new`, `atf doc` and `atf watch`.
- Language: `try { ... } catch err { ... }` statements, array patterns in `match` (`[first, ..rest]`), default methods in interfaces, `for` loops over any value with `next()`, `>>>=`, `and`/`or` line continuation, and `step` is a normal name again.
- Language and library helpers: `lerp`, `fract`, `ln`, `array_repeat`, `floor_int`, `ceil_int`, `round_int`.
- New standard library modules: `std/yaml`, `std/bigint`, `std/crypto` (random, PBKDF2, AES-GCM), `std/websocket`, `std/semver`, `std/term`, `std/iter` (lazy iterators), `std/sound`, `std/image`, `std/task`, `std/shell`. `std/net` now also has UDP (`udp_bind`, `send_to`, `receive`).
- Serving ATF on the web: open a window program in a browser, build a static site, a Dockerfile and a starter website (`app/`).
- `std/ui`: drag and drop (`.draggable(payload, label)`, `.on_drop(fn(str))`, `ui_dragging()`, `ui_drag_over()`) with a label that follows the pointer, and automatic scrolling of a `scroll` box when dragging near its edge. Canvas: right-click, float drawing (`frect`, `fcircle`, `fline`) and the mouse position.
- `std/process`: programs in the background with `proc_start` and `proc_start_args` (`Proc` with `read`, `running`, `exit_code`, `wait`, `kill`).
- `std/text`: `text_braces`, `TEXT_LBRACE` and `TEXT_RBRACE` for programs that write code.
- `tools/blocks.atf` and `tools/blocks_kids.atf`: block-programming editors written in ATF (drag and drop, value blocks, background Run and Stop, save and export).
- New examples: `examples/ui/2D_minecraft.atf` and the Blockworld version of `examples/ui/minecraft.atf` (with sounds and hover).
- ATF programs and tests also run through Wine on Linux.
- The installer and uninstaller set the icon and the `.atf` file association.

## Fixes

- `std/ui`: a `scroll(...).grow()` box now takes the space it is given instead of the height of its content, so it scrolls with the mouse wheel.
- `demos.html`: HTML escaping in the output of the XML example, and new lessons for `std/xml`, `std/net`, `std/url`, `std/ini`, `std/glob`, `std/httpd` and `extern ... as`.
