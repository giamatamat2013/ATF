# ATF

**ATF** (*Accessible Typed Fast*) is a small programming language that is easy to learn and compiles to fast native
Windows programs. Its syntax is short and readable, the compiler explains mistakes in plain words, and
the result is a stand-alone `.exe` that needs nothing else to run.

> Former name: the project and its Python package were previously called `atefintalode`.

```atf
struct Item {
    name: str,
    price: float,
    count: int = 1
}

fn total(items: [Item]) -> float {
    return items.map(|it| it.price * float(it.count)).sum()
}

fn main() {
    let cart = [Item{ name: "apple", price: 0.5, count: 6 }, Item{ name: "bread", price: 2.25 }]
    for it in cart {
        println("{it.name:<8} x{it.count}  {it.price * float(it.count):>6.2}")
    }
    println("total: {total(cart):.2}")
}
```
```output
apple    x6    3.00
bread    x1    2.25
total: 5.25
```

## Why ATF

- **Easy to learn.** One way to write things, few symbols, type inference (`let x = 5`), no header files,
  no manual memory management. Error messages point at the exact place and suggest a fix:

  ```text
  error: unknown name 'totl'
    --> shop.atf:3:13
   3 |     println(totl + 1)
     |             ^
    hint: did you mean 'total'?
  ```
- **Compiled and fast.** The compiler writes x86-64 machine code directly into a Windows executable (no C
  compiler, assembler or linker is used). Measured on an Intel i5-12600K:

  | program | ATF | Python 3.14 |
  |---|---|---|
  | `fib(38)`, recursive | 0.20 s | 4.3 s |
  | prime sieve up to 20 million | 0.07 s | 7.4 s |
  | the compiler compiling itself (14,500 lines) | 0.16 s | |

  A "hello world" program is a 17 KB `.exe`.
- **Many features.** Structs with methods and field defaults, enums with data and `match` (checked for
  missing cases, with array patterns like `[first, ..rest]`), generics, closures, interfaces (with default methods), optional values (`int?`) and `Result` errors with `?`,
  operator overloading, string interpolation with formatting, list comprehensions, the pipe
  (`text |> str.trim |> parse`, where `x |> f(a)` means `f(x, a)`), modules, `defer`,
  `try`/`catch`, labeled loops, a garbage collector, readable crash reports with tracebacks, a REPL and a code formatter.
- **Batteries included.** Strings, arrays, maps, sets, files, processes, time and random numbers are always
  available; the standard library modules need no `import` line either: use a name such as `json_parse` or
  `ui_run` and the compiler imports its module itself (a hand-written `import "std/json"` still works). Modules add JSON, CSV, TOML, Base64, hex, hashes (MD5, SHA-1, SHA-256, CRC32), dates and times,
  collections (deque, priority queue, sorted map and set, counter, linked list), sounds (`std/sound`), BMP pictures (`std/image`), time-sliced background jobs (`std/task`), lazy iterators (`std/iter`, and
  `for` loops over any type with `next()`), program settings (`std/app`),
  regular expressions (`std/regex`), file paths and folders (`std/path`, `std/fs`), running programs (`std/process`),
  XML (`std/xml`), an HTTP/HTTPS client (`std/http`), TCP connections and servers and UDP messages (`std/net`), a small web server (`std/httpd`), HTML pages with CSS animations (`std/html`), window animations (`animate`, easing, `anim_loop` in `std/ui`), web addresses (`std/url`), INI files (`std/ini`), YAML files (`std/yaml`), whole numbers of any size (`std/bigint`), encryption, secure random bytes and keys from passwords (`std/crypto`), WebSocket clients and servers (`std/websocket`),
  file name patterns (`std/glob`), a test framework with property tests on random values (`std/test`),
  colors, progress bars and boxes in the console (`std/term`), Markdown to HTML (`std/markdown`),
  version numbers and rules like `^1.2` (`std/semver`), the commands of `atf shell` from a program (`std/shell`), questions to Claude, Anthropic's AI model (`std/ai`),
  and the Python-style tools for whole programs:
  command-line parsing (`std/args`, like argparse), leveled logging (`std/log`), text helpers (`std/text`:
  wrap, title, snake_case, templates, tables), number theory and statistics (`std/math`), and algorithms from
  C++, itertools and JavaScript (`std/algo`: binary search, permutations, combinations, group_by, flatten, set operations), Python's `random` extras
  (`std/random`: sample, weighted choice, gauss, UUID) and C++ bit tricks (`std/bits`: rotate, reverse, power of two, Gray code).
  Python method names work next to the ATF ones (`strip`, `startswith`, `endswith`, `ljust`, `rjust`, `zfill`, `isdigit`, `splitlines`, `append`, `update`, `discard`).
- **Windows and design.** `std/ui` builds graphical programs the way HTML and CSS do, written as ATF code: a view function
  returns a tree of elements (`column`, `row`, `text`, `button`, `textbox`, ...), styled with chained methods
  (`.padding(8, 16).bg(hex("#4f46e5")).radius(12).shadow(..)`). It supports flexbox and grid layout, gradients, soft shadows,
  hover styles with transitions, reusable styles, images, scrolling, right-to-left text and high-DPI screens.
  It also has what a whole application needs: multi-line text editing with selection, undo and the clipboard, menus and
  menu bars, select lists, tabs, dialogs, tooltips, keyboard shortcuts, standard file dialogs, a drawing canvas, and a
  way to test the interface without a window (`ui_headless`, `ui_click`, `ui_type`). `std/app` keeps settings between runs.
  The same program also runs in a browser, without any change to it: `ATF_UI_WEB=8080 bin/atf.exe run examples/ui/counter.atf`,
  then open `http://127.0.0.1:8080/`. The page shows the picture the window would draw and sends the mouse and keyboard back.
  To serve it to other people, add `ATF_UI_WEB_HOST=0.0.0.0` or use the `Dockerfile` (any host that takes Docker; see
  "Serving on the web" in the tutorial). The demo gallery and docs publish to GitHub Pages, Netlify or Vercel with
  `tools/build_site.py`, and to a custom domain through the `ATF_PAGES_DOMAIN` repository variable.

  ```atf nocheck
  button("Save", || save(doc)).bg(hex("#4f46e5")).color(WHITE).radius(10).hover(style().bg(hex("#4338ca")))
  ```
- **Self-hosted.** The compiler is written in ATF itself (`compiler/`) and compiles itself.

## Getting started

Requirements: 64-bit Windows 10 or 11 (or Linux with Wine, see below). Nothing else is needed to compile and run programs.

```text
atf run hello.atf              compile and run a program
atf build hello.atf -o hello.exe
atf check hello.atf            only look for errors
atf shell                     open the interactive ATF command line
atf interpret file.atf        run with the ATF interpreter (native fallback when needed)
atf repl                       try things interactively
atf fmt hello.atf              fix the indentation of a file (--check only reports)
atf new myapp                  start a project folder: lib.atf, main.atf, test_lib.atf
atf test [folder]              run every test_*.atf and *_test.atf (and compare with NAME.out when there is one)
atf doc lib.atf [-o lib.md]    Markdown documentation from the comments above functions and types
atf watch hello.atf            run again every time the file or a file it imports is saved
atf version
```

`atf shell` opens an interactive prompt for ATF commands. Type `run hello.atf` or `atf run hello.atf`, use `help` to list commands, and `exit` to leave. The prompt has a built-in line editor (like Clink for cmd.exe): arrow keys, Home/End, Ctrl+Left/Right, Ctrl+W/U/K, Up/Down history kept in `%USERPROFILE%\.atf_history`, and Tab completion of commands and file names (press Tab twice to list the choices). Ctrl+C cancels the line being typed, or stops the running command; Ctrl+D on an empty line quits. The prompt is `ATF <current folder>>`. Typing shows Clink-style syntax colors (a command the shell can run is green, an unknown one red, `-flags` blue, strings yellow, existing files cyan) and a dim suggestion from the history (Right or End accepts it). The shell replaces cmd.exe and PowerShell: `cd`, `pushd`, `alias`, `set`, `history`, a colored `ls`, Unix names (`grep`, `cat`, `cp -r`, `rm -rf`, `head`, `tail`, `wc`, ...), any program on PATH, PowerShell cmdlets and `$variables`, and ATF code (`let x = 1`). `commands` lists them all; `~/.atfrc` runs at start; `atf shell -c "cmd1
cmd2"` and `atf shell -f script` run non-interactively and exit with the last exit code. The same commands work in a program with `std/shell` (`shell_exec("ls -l")`). For a Windows Terminal profile, use the full path to `bin\atf.exe` followed by `shell`.

ATF remains a compiled language by default: `atf run` compiles to native code. `atf interpret file.atf` explicitly selects the interpreter; it uses native execution for features the interpreter cannot handle directly.

It also evaluates ATF code and keeps values between lines:
```text
ATF> println("test")
test
ATF> let n = 4
ATF> n * 2
8
ATF> exit
```

`atf` is `bin\atf.exe` (or `atf.cmd` in the repository root). To install it for your user, run
`install.cmd`: it copies the compiler, the standard library and the icon to `%LOCALAPPDATA%\atf`, adds
that folder to your PATH, and makes ATF the program that opens `.atf` files in Explorer (with the ATF
icon). `uninstall.cmd` removes all of it again. Note: Windows may ask for confirmation the first time you run a newly built,
unsigned program.

**On Linux** (for example a remote server where an AI assistant works), the compiler runs through
[Wine](https://www.winehq.org/). Install it once with `sudo apt install wine64`. Then `wine bin/atf.exe run hello.atf`
runs a program with the native compiler, and `python3 run_atf.py run hello.atf` runs it with the Python compiler.
`python3 run_atf.py check` and `build` need only Python 3. The test scripts run the same way. The first run creates
the Wine folder `~/.wine` and takes a little longer. If `wine` is not on the PATH, set `ATF_WINE` to the Wine program.

A program may start with the declaration `atf "1.2.0"` to say which version it was written for. It is optional; a
compiler older than that version only prints a warning (see the tutorial, section 2).

A first program, `hello.atf`:

```atf
fn main() {
    let name = input("What is your name? ")
    println("Hello, {name}!")
}
```
```input
Ada
```
```output
What is your name? Hello, Ada!
```

## A short tour

```atf
enum Shape {
    Circle(float),
    Rect(float, float)
}

fn area(s: Shape) -> float {
    return match s {
        Shape.Circle(r) => PI * r * r
        Shape.Rect(w, h) => w * h
    }
}

fn parse_age(text: str) -> Result<int, str> {
    let n = text.parse_int()
    if n == nil { return Result.Err("'{text}' is not a number") }
    if n! < 0 { return Result.Err("an age cannot be negative") }
    return Result.Ok(n!)
}

fn main() {
    let shapes = [Shape.Circle(1.0), Shape.Rect(2.0, 3.5)]
    for s in shapes { println(s, "area {area(s):.3}") }

    var counts: {str: int} = {}
    for w in "the cat and the hat".split(" ") { counts[w] = counts.get(w, 0) + 1 }
    println(counts)

    let squares = [x * x for x in 1..=6 if x % 2 == 0]
    println(squares)

    for t in ["42", "-3", "abc"] {
        match parse_age(t) {
            Result.Ok(a) => println("age", a)
            Result.Err(e) => println("error:", e)
        }
    }
}
```
```output
Shape.Circle(1.0) area 3.142
Shape.Rect(2.0, 3.5) area 7.000
{"the": 2, "cat": 1, "and": 1, "hat": 1}
[4, 16, 36]
age 42
error: an age cannot be negative
error: 'abc' is not a number
```

## Documentation

- [docs/TUTORIAL.md](docs/TUTORIAL.md) - learn the language step by step (English)
- [docs/TUTORIAL.he.md](docs/TUTORIAL.he.md) - מדריך בעברית
- [docs/REFERENCE.md](docs/REFERENCE.md) - the exact rules of the language
- [docs/STDLIB.md](docs/STDLIB.md) - every library function, method and module
- [examples/](examples/) - 46 example programs, from `fizzbuzz` to a `bigint` calculator and a text adventure
- [examples/ui/](examples/ui/) - window programs: a counter, a task list, an analytics dashboard and a complete notes editor (menus, files, shortcuts, saved settings), and look-alikes of familiar programs: a calculator, Minesweeper, Snake, a Paint-style drawing program, Tetris, a spreadsheet with a formula engine and a Wolfenstein-style 3D shooter, and `animations.atf` (easing, tweened values, loops); [examples/web_animations.atf](examples/web_animations.atf) builds and serves an animated web page with `std/html`

Every code sample in these documents is compiled and run by `python tests/check_docs.py`.

## Editor support

- **VS Code**: `editors/vscode` (syntax highlighting, snippets, brackets and indentation). Copy the folder to
  `%USERPROFILE%\.vscode\extensions\atf` and restart VS Code.
- **Notepad++**: import `editors/notepadpp/atf.xml` with *Language > User Defined Language > Define
  your language > Import*.

## Repository layout

```text
bin/atf.exe            the compiler (built from compiler/)
compiler/              the compiler, written in ATF
atf/                   the bootstrap compiler in Python (stage 0) and the prelude (stdlib/prelude.atf)
stdlib/                standard library modules (imported by the compiler when used, or by hand:  import "std/json");
                       index.txt maps each name to its module (bin/atf.exe run tools/make_stdlib_index.atf)
docs/                  tutorial, reference and library documentation
examples/              example programs with their expected output
tests/                 test suites (see below)
bench/                 benchmarks
editors/               editor support
tools/                 tools written in ATF (tools/stdlib_docs.atf writes docs/STDLIB.md,
                       tools/convert.atf converts between ATF, Python and Rust, see docs/CONVERT.md)
app/                   a starter website in ATF (routes, pages, static files); `atf run app/main.atf`
Dockerfile, deploy/    run the website (or a window program) in a browser on any Docker host (render.yaml, fly.toml)
netlify.toml, vercel.json, .github/workflows/pages.yml   publish the static site (tools/build_site.py)
CLAUDE.md              rules for Claude Code: every change also updates the docs, tutorials and the ATF skill
.claude/skills/atf/    the Claude skill that teaches the language
```

## Building the compiler

The compiler compiles itself:

```text
rebuild_compiler.cmd
```

builds `compiler/main.atf` with the current `bin\atf.exe`, builds it a second time with the result, checks
that both generations are byte-for-byte identical (a fixed point), and installs the new compiler. The
Python compiler in `atf/` is the original bootstrap: `python run_atf.py build compiler/main.atf -o
bin/atf.exe` recreates the compiler from scratch without any existing binary.

## License

ATF is source-available under the [PolyForm Noncommercial 1.0.0](LICENSE) license: you may use, copy,
modify and share it for any noncommercial purpose, with the license and copyright notice kept in every copy.
It is **not** open source as defined by the OSI, because commercial use is restricted.

The software is provided as is, without warranty.

**Request (not required):** if you publish changes or a project built with ATF, we would appreciate it if
your code were available too, and if you credited ATF and its original author, tamat2013.

## Tests

```text
python tests/run_tests.py          language tests (tests/*.atf with expected output and errors)
python tests/run_examples.py       every program in examples/
python tests/qa/run_qa.py          focused tests, including compiler errors and ATF shell startup
python tests/std/run_std_tests.py  the standard library modules
python tests/check_docs.py         every code sample in the documentation
python tests/compare_stages.py     programs built by the bootstrap and by the native compiler behave the same
```

On Linux the same commands work when Wine is installed (see Getting started).
