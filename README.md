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
  missing cases), generics, closures, interfaces, optional values (`int?`) and `Result` errors with `?`,
  operator overloading, string interpolation with formatting, list comprehensions, modules, `defer`,
  labeled loops, a garbage collector, readable crash reports with tracebacks, a REPL and a code formatter.
- **Batteries included.** Strings, arrays, maps, sets, files, processes, time and random numbers are always
  available; modules add JSON, CSV, TOML, Base64, hex, hashes (MD5, SHA-1, SHA-256, CRC32), dates and times,
  collections (deque, priority queue, sorted map and set, counter, linked list), program settings (`std/app`),
  regular expressions (`std/regex`), file paths and folders (`std/path`, `std/fs`), running programs (`std/process`),
  XML (`std/xml`), an HTTP/HTTPS client (`std/http`), TCP connections and servers (`std/net`), a small web server (`std/httpd`), HTML pages with CSS animations (`std/html`), window animations (`animate`, easing, `anim_loop` in `std/ui`), web addresses (`std/url`), INI files (`std/ini`),
  file name patterns (`std/glob`), a test framework (`std/test`), and the Python-style tools for whole programs:
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

  ```atf nocheck
  button("Save", || save(doc)).bg(hex("#4f46e5")).color(WHITE).radius(10).hover(style().bg(hex("#4338ca")))
  ```
- **Self-hosted.** The compiler is written in ATF itself (`compiler/`) and compiles itself.

## Getting started

Requirements: 64-bit Windows 10 or 11. Nothing else is needed to compile and run programs.

```text
atf run hello.atf              compile and run a program
atf build hello.atf -o hello.exe
atf check hello.atf            only look for errors
atf repl                       try things interactively
atf fmt hello.atf              fix the indentation of a file (--check only reports)
atf version
```

`atf` is `bin\atf.exe` (or `atf.cmd` in the repository root). To install it for your user, run
`install.cmd`: it copies the compiler and the standard library to `%LOCALAPPDATA%\atf` and adds
that folder to your PATH. Note: Windows may ask for confirmation the first time you run a newly built,
unsigned program.

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
stdlib/                importable modules:  import "std/json", import "std/ui", import "std/app"
docs/                  tutorial, reference and library documentation
examples/              example programs with their expected output
tests/                 test suites (see below)
bench/                 benchmarks
editors/               editor support
tools/                 tools written in ATF (tools/stdlib_docs.atf writes docs/STDLIB.md,
                       tools/convert.atf converts between ATF, Python and Rust, see docs/CONVERT.md)
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
python tests/qa/run_qa.py          more than 100 focused tests, including compiler error messages
python tests/std/run_std_tests.py  the standard library modules
python tests/check_docs.py         every code sample in the documentation
python tests/compare_stages.py     programs built by the bootstrap and by the native compiler behave the same
```
