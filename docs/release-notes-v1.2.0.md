## Features

- Browser mode for window programs: `ATF_UI_WEB=8080 bin/atf.exe run examples/ui/counter.atf` shows the program in a browser at `http://127.0.0.1:8080/`. The program does not change. Mouse clicks (left button only), keys and the wheel go back to the program.
- A program may start with `atf "1.2.0"` to name the version it was written for. An older compiler prints a warning on stderr and still compiles the file.
- Animations in `std/ui`: `animate`, `animate_color`, `animate_with`, `animate_from`, `anim_loop`, `anim_wave` and the easing functions. Example: `examples/ui/animations.atf`.
- `std/html`: web pages with CSS animations (`h`, `html_page`, `css_keyframes`). Example: `examples/web_animations.atf`.
- New standard library modules:
  - `std/url`: parse and build web addresses, encode and decode, query strings.
  - `std/httpd`: a small web server with routes and static files.
  - `std/glob`: file name patterns (`*`, `?`, `**`).
  - `std/ini`: INI configuration files.
  - `std/xml`: parse, query and write XML.
  - `std/net`: TCP connections and servers, and name lookup.
  - `std/zlib`: compression and decompression (`zlib_compress`, `zlib_decompress`, raw deflate and inflate).
  - `std/algo`, `std/args`, `std/bits`, `std/log`, `std/math`, `std/random` and `std/text`: helpers in the style of Python and C++ for whole programs.
- New array and string methods: `take`, `skip`, `chunks`, `windows`, `partition`, `unique`, `strip_prefix`, `strip_suffix` and `lcm`.
- Python method names work next to the ATF ones: `strip`, `startswith`, `endswith`, `ljust`, `rjust`, `zfill`, `isdigit`, `splitlines`, `append`, `update` and `discard`.
- `extern "dll" fn name(...) as "Symbol"` gives an extern function its own name, when the DLL name is too short or would clash.
- `tools/convert.atf` converts programs between ATF, Python and Rust (see `docs/CONVERT.md`).
- Canvas: `Canvas.pixels_smooth` scales a software-rendered picture with smooth edges; `Canvas.pixel_w` and `Canvas.pixel_h` give the render size.
- New look-alike UI examples: a calculator, Minesweeper, Snake, a Paint-style drawing program, Tetris, a spreadsheet with a formula engine, a Wolfenstein-style 3D shooter and a Minecraft-style example.
- `demos.html` is updated for the new lesson structure.

## Fixes

- The games and the Minecraft and Wolfenstein examples render at the full window resolution, instead of a small picture scaled up.
