---
name: atf
description: Write, read, debug, compile and explain programs in ATF ("Accessible Typed Fast", files ending in .atf), a small statically typed language that compiles to native Windows .exe files. Home of the language, compiler, docs, examples and releases - https://github.com/tamat2013/ATF. Use this skill whenever the user mentions ATF, .atf files, `atf run` / `atf build` / `atf check`, the ATF compiler, bin/atf.exe, the standard library (std/json, std/ui, std/csv, ...), GUI windows or games written in ATF, or asks to write, fix, port or explain code in this language, even if they just say "the language in this repo" or write in Hebrew (שפת ATF, תכתוב לי ב-ATF). ATF looks like a mix of Rust and Python but has its own rules, so never guess its syntax from other languages - consult this skill first, and compile what you write.
---

# ATF language

This skill is self-contained: everything needed to write correct ATF is below and in `references/stdlib.md`, with no internet needed. The GitHub repo is an optional extra for the newest docs, ready-made compiler builds and more examples: **https://github.com/tamat2013/ATF** (releases: https://github.com/tamat2013/ATF/releases, bugs and requests: its Issues page). If the repo is available locally and disagrees with this skill, the repo is newer.

## Quick start (do this first)

1. Find a compiler: `bin/atf.exe` in the current folder, or `atf` on PATH (`atf version`). If there is none, ask the user where it is, or point them to the Releases page above (`atf-X.Y.Z-windows-x64.zip`) or `git clone https://github.com/tamat2013/ATF`. Do not try to build ATF yourself. Without a compiler, still write the code from the rules below and say it was not compiled.
2. Write the code, run `atf check f.atf`, then `atf run f.atf`. Only report "works" after a real run.
3. Never invent a function. If unsure it exists, `Grep` it in `references/stdlib.md`. If it is not listed there (or in the prelude/examples of a local repo), it does not exist: write it yourself.
4. If a local repo has `examples/`, copy the structure of a similar program (window/game programs: `examples/ui/`).

ATF is compiled (x86-64 machine code written directly into a Windows `.exe`), statically typed, garbage collected, with type inference. The compiler is self-hosted and lives in the ATF repo (`bin/atf.exe`, sources in `compiler/`). Its syntax resembles Rust/Python/Go, but it differs in many small ways, so write ATF from the rules below rather than from habit. Getting these wrong produces compile errors, which is the main failure mode.

## Workflow

1. Find the compiler: `bin/atf.exe` (or `atf.cmd`) in the repo root; `atf` if installed on PATH. In Git Bash call `bin/atf.exe`, in PowerShell `.\atf` or `bin\atf.exe`. On Linux (a remote server) there is no `atf.cmd`: install Wine (`sudo apt install wine64`), then call `wine bin/atf.exe check f.atf` and `wine bin/atf.exe run f.atf`; `python3 run_atf.py run f.atf` also works (Python compiler, runs the program through Wine).
2. Write the code, then **always compile it** before reporting it works:
   ```
   atf check f.atf            # errors only, prints "ok"
   atf run f.atf [args...]    # compile + run (stdin works: atf run f.atf < in.txt)
   atf build f.atf -o f.exe   # stand-alone exe
   atf fmt f.atf [--check]    # fix indentation
   atf shell                   # interactive prompt for ATF code, CLI commands and cmd/PowerShell/Unix-style commands (cd, ls, grep, any program), with line editing, colors, history and Tab completion; exit to quit
   atf shell -c "cmd1\ncmd2"   # non-interactive: run lines, exit with the last exit code (also -f script)
   atf interpret file.atf      # use the ATF interpreter; native fallback when needed
   atf repl
   atf test [folder]          # runs test_*.atf / *_test.atf (pass = exit 0, and output == NAME.out if present)
   atf new name               # project: lib.atf + main.atf + test_lib.atf (a test has its own main: import lib, not main)
   atf doc f.atf [-o f.md]    # Markdown docs from the // comments above fns and types
   atf watch f.atf            # rerun on every save of f.atf or its local imports
   ```
3. Compiler errors are precise (message, `file:line:col`, a caret, often a `hint:`). Read the hint and fix; do not rewrite blindly.
   `atf run` remains the normal compiled execution path. `atf interpret` selects the interpreter explicitly and uses native execution for constructs the interpreter does not support directly.
4. When changing the language, compiler or library in the ATF repo, follow its `CLAUDE.md`: the same piece of work updates the tutorials (English and Hebrew), README, `docs/STDLIB.md`, this skill and the VS Code extension.
5. When unsure about a library function, check `references/stdlib.md` (copy of the repo's docs/STDLIB.md) and, if a local repo exists, its `docs/TUTORIAL.md`, `atf/stdlib/prelude.atf` (the always-available library, in ATF), and `examples/` (45 tested programs). Prefer the repo copies if present: they are newer than this skill.

## Program shape

```atf
fn main() {                       // or: fn main(args: [str]) -> int  (return value = exit code)
    println("Hello, {name}!")     // {expr} interpolation, \{ for literal brace
}
```
Optional first declaration: `atf "1.2.0"` names the version the file was written for (not a comment; must come before everything else). The compiler only warns (stderr) when it is newer than the compiler. Add it to new programs, do not require it.
No semicolons needed (optional), no imports for the core library, no header files. Declarations outside functions can appear in any order. A statement continues onto the next line if the line ends with an operator/comma, is inside brackets, or the next line starts with `.`, `&&`, `||`, `??`.

A typical small program (shows most of the idioms together):
```atf
atf "1.2.0"

import "std/json"

struct Task { title: str, done: bool = false }

impl Task {
    fn to_str(self) -> str => "[{if self.done { "x" } else { " " }}] {self.title}"
}

fn parse_count(s: str) -> Result<int, str> {
    let n = s.parse_int()
    if n == nil { return Result.Err("not a number: {s}") }
    return Result.Ok(n!)
}

fn main(args: [str]) -> int {
    var tasks: [Task] = [Task("write"), Task("test", true)]
    for i, t in tasks { println("{i + 1}. {t}") }
    let open = tasks.filter(|t| not t.done).len()
    println("open: {open}")
    match parse_count("12") {
        Result.Ok(n) => println("n = {n}")
        Result.Err(e) => { eprintln(e); return 1 }
    }
    return 0
}
```

## Core syntax cheat sheet

```atf
let x = 5            // immutable (reassigning is a compile error)
var n = 0            // mutable;  var total: int  starts at 0
const MAX = 30       // global constant; global `var` also allowed
a, b = b, a          // multi-assign (rhs evaluated first); shadowing with a new `let` is allowed

// types: int (64-bit, wraps) float bool str(UTF-8 bytes, immutable) byte   e.g. 'A' is a byte (65)
// conversions are explicit: int(3.9) float(7) str(42) "12".to_int()   `x as float` also works
// [T] array   {K: V} map   (A, B) tuple   T? optional   Result<T, E>   fn(int) -> int function type

if c { } else if d { } else { }          // condition must be bool; `if` is an expression (needs else)
while c { }    loop { break }
for i in 0..5 { }  0..=5  0..=20 step 5  10..0 step -3      // `step` only counts right after a range (still usable as a name)
for x in arr { }   for i, x in arr { }   for k, v in map { }   for ch in "str" { }
for x in it { }     // any value with  fn next(self) -> T?  (stops at nil); also for i, x in it
for (a, b) in pairs   // unpacks tuple elements
outer: for ... { for ... { break outer; continue outer } }   // labels

fn add(a: int, b: int = 1) -> int { return a + b }      // defaults, named args: add(b: 2, a: 1)
fn dbl(x: int) -> int => x * 2                          // short form
fn minmax(a: [int]) -> (int, int) { return (lo, hi) }   // tuples; let (lo, hi) = minmax(a)

|x| x * 2    |a, b| a + b    || { stmts }    |x: int| { total += x }   // closures capture & mutate
```

Operators: `+ - * / %` `**` (power, right-assoc, `-2 ** 2 == -4`), `== !=` (structural), `< > <= >=`, `and or not` (or `&& || !`), bit ops `& | ^ ~ << >> >>>`, `in` / `not in`, `??`, postfix `!` and `?`. Int `/` truncates toward zero; `%` takes the sign of the left operand. int and float mix in arithmetic; a float never becomes an int implicitly.

### Strings
`"{expr}"` interpolation with format specs: `{x:.2f}` `{x:8.3f}` `{n:5}` `{n:<5}` `{n:>5}` `{n:^5}` `{n:05}` `{n:x}` `{n:X}` `{n:b}` `{n:08b}`. Escapes `\n \t \" \\ \{ \} \xHH \u{263A}`. Multi-line `"""..."""`, raw `r"..."`.
Methods: `len trim upper lower reverse find contains starts_with ends_with replace count split join lines split_whitespace repeat strip_prefix strip_suffix pad_left pad_right byte_at parse_int parse_float to_int to_float`; slicing `s[a..b]`, `s[a..]`, `s[..b]`; `"ab" * 3`; `", ".join(arr)`. Python names work next to them and do the same: `startswith endswith strip lstrip rstrip ljust rjust isdigit splitlines` (also `zfill(w)`; byte `isdigit isalpha isspace`). `strip_prefix(p)` / `strip_suffix(p)` return `str?` (nil when no match). `parse_int()` returns `int?`; `to_int()` panics on bad input. Use `str_builder()` (`add`, `add_byte`, `finish`) instead of `s = s + x` in loops.

### Collections
- Array: `push` (also `append`) `pop insert(i,x) remove(i) first last contains index_of len is_empty sort sort_by(|a,b| a-b) sorted reversed reverse map filter reduce(init, |acc,x| ..) any all find count sum min max extend copy for_each take(n) skip(n) chunks(n) windows(n) partition(f) unique`, slicing, `+` concatenation. Empty needs a type: `var w: [str] = []`. Create sized: `array_make::<int>(n)`. Arrays, maps, structs are **references**; use `copy(x)` for a shallow copy.
- Map: `var m: {str: int} = {}`; `m[k] = v`, `m.get(k, default)`, `m.try_get(k)` (optional), `k in m`, `m.has(k)`, `m.keys() values() items() remove(k) len() update(other)`. A missing key panics. Insertion order is kept.
- Set: `let s = set_new::<int>()`; `add has remove (also `discard`) len items`; `x in s`; iterate with `for x in s.items()`.
- Comprehensions: `[x * x for x in 1..=6 if x % 2 == 0]`, `[... for i, w in arr]`, nested allowed.
- Tuples: `t.0`, `let (a, _) = t`, immutable, compare field by field.

### Structs, enums, match
```atf
struct Item { name: str, price: float, count: int = 1 }      // defaults
let a = Item("x", 1.0)   let b = Item{ name: "y", price: 2.0 }   // positional or by name
impl Item {
    fn new(n: str) -> Item { return Item(n, 0.0) }   // static: Item.new("z")
    fn total(self) -> float { return self.price * float(self.count) }
    fn to_str(self) -> str { ... }                   // used by println / "{x}"
}
// operator methods: op_add op_sub op_mul op_div op_mod op_pow op_neg op_index op_set_index
// op_slice op_contains op_and/or/xor/shl/shr/ushr, eq, cmp (-/0/+ enables < > sort)

enum Shape { Circle(float), Rect(float, float), Point }     // data-carrying variants
enum Level { Low = 1, High = 10 }                           // numbered; int(Level.High)
let area = match s {                                        // exhaustive for enums (compile error otherwise)
    Shape.Circle(r) => PI * r * r
    Shape.Rect(w, h) => w * h
    Shape.Point => 0.0
}
// patterns: literals, 1 | 2, 4..=9, x if x < 0 (guard), _, tuples (0, _), nested Expr.Add(Expr.Num(0), rhs),
// struct patterns Point(0, 0), Point{ x: 0, y }, Point{ y: 0, .. }; variant type name optional inside match
// array patterns [] [x] [a, b] [first, ..rest] [.., last] [a, .., z]: `..` = zero or more elements,
// `..name` binds them as a new array; [] + [x, ..rest] together are exhaustive
if let Pattern = value { } else { }     while let n = cur { }
```
Arms are separated by newlines (no commas). An arm may be an expression, a `{ block }`, an assignment, `return`, `break`, `continue`. A `match` used as a value must be exhaustive; add `_ =>` otherwise.

### Optionals and errors
```atf
fn find(a: [int], x: int) -> int? { ...; return nil }
find(a, 3) ?? -1        i!          // `!` panics on nil;  `?? default`
if let p = find(a, 3) { }
fn parse(s: str) -> Result<int, str> {
    let n = s.parse_int()
    if n == nil { return Result.Err("bad") }
    return Result.Ok(n!)
}
let v = parse("1")?          // on Err: return it from the current fn (also works for T? -> returns nil)
r.unwrap_or(0)  r.is_ok()  r.is_err()
panic("msg")  assert(cond, "msg")  catch_panic(|| { ... }) // returns str? (the message)
try { risky() } catch err { println(err) }   // statement form of catch_panic; name optional: catch { }
                             // no `return`, nor break/continue to an outer loop, inside the try block
defer println("cleanup")     // runs at end of the enclosing block, LIFO; NOT run on panic
```
An optional cannot be used as a plain value (`n + 1` with `n: int?` is a compile error): unwrap with `!`, `??` or `if let`.

### Generics and interfaces
```atf
fn largest<T>(a: [T]) -> T { ... }                   // checked per instantiation, no bounds syntax
struct Stack<T> { items: [T] }
impl<T> Stack<T> { fn new() -> Stack<T> { return Stack{ items: [] } } ... }
let s: Stack<int> = Stack.new()      set_new::<int>()      Stack::<str>{ items: [] }
interface Shape { fn area(self) -> float }           // structural: any type with these methods fits
interface Named { fn name(self) -> str
    fn hi(self) -> str => "hi " + self.name() }   // default body: used by types without hi();
                                                    // inside it self is the interface (only its methods)
let shapes: [Shape] = [Circle(1.0), Rect(2.0, 3.0)]
```

### I/O, modules, misc
`println print eprintln eprint flush`; `input(prompt)`; `read_line()` -> `str?` (nil at EOF); `read_all_stdin()`; `read_file(p)` -> `str?`; `write_file(p, text)` -> bool; `file_exists delete_file make_dir temp_dir getenv exit run_command run_process`; `rand_seed rand_int(lo,hi) rand_float rand_choice shuffle clock`; math `sqrt abs min max PI E INT_MAX INT_MIN`; `chr ord range range_from zip same copy`; GC: `gc gc_runs gc_live_bytes`.
Std modules need no `import`: using a name from one (`json_parse`, `ui_run`, `Node`) makes the compiler import it (table: `stdlib/index.txt`, made by `bin/atf.exe run tools/make_stdlib_index.atf` after changing a `stdlib/*.atf` top-level name); a hand-written import still works, also partial, and a name your program defines wins. Modules: `import "other"` (path relative to the importing file) or `import "std/json"` (also algo, app, args, shell (`shell_exec("ls -l")`, `shell_capture`, `shell_script`: the commands of `atf shell` from a program), base64, bigint, bits, collections, crypto, image, iter, csv, datetime, fs, hash, hex, glob, html, http, httpd, ini, json, log, math, net, path, process, random, regex, test, text, toml, ui, url, websocket, xml, yaml).
Python-style helpers for whole programs: `std/args` (`let p = args_parser("tool", "about")`, `p.flag/option/required_option/positional`, `p.parse_or_exit(argv)` with `fn main(argv: [str])`, then `a.get/get_int/flag/has`), `std/log` (`log_info(..)`, `log_set_level(LOG_DEBUG)`, `log_set_file(path)`, output on stderr), `std/text` (`text_wrap text_title text_snake_case text_template text_table text_distance`; in `text_template` write the `${name}` placeholders in a raw string `r"..."`), `std/algo` (C++ / itertools / lodash style, all `algo_*`: `lower_bound upper_bound binary_search prefix_sums rotate next_permutation permutations combinations product subsets flatten flat_map group_by count_by unique_by take_while argmin argmax union intersection difference`), `std/random` (`random_range random_sample random_choices random_weighted random_gauss random_string random_uuid`; `rand_seed` makes it repeatable), `std/bits` (`bits_length bits_rotl bits_reverse bits_set bits_get bits_is_power_of_two bits_to_str`; there is no `>>>=`, write `x = x >>> 1`), `std/math` (`math_is_prime math_primes math_factorial math_mod_pow stats_mean stats_median stats_stdev stats_percentile`). **One global namespace** across all files: give globals specific names; duplicate definitions are compile errors. `include_str("f.txt")` embeds a file at compile time.

### Windows and design (`import "std/ui"`)
HTML/CSS ideas written as ATF. A view function returns a `Node` tree. It is rebuilt after every click, key press or timer tick, so handlers only change data.
```atf
import "std/ui"
struct App { count: int = 0, name: str = "" }
let CARD = style().bg(WHITE).radius(16).padding(20).gap(12).shadow(0, 8, 24, rgba(15, 23, 42, 0.1))  // like a CSS class
let PRIMARY = style().bg(hex("#4f46e5")).color(WHITE).border(0, TRANSPARENT).hover(style().bg(hex("#4338ca"))).transition(150)
fn view(app: App) -> Node {
    return column([
        text("Hello {app.name}").font_size(22).bold(),
        textbox(app.name, |s| { app.name = s }).placeholder("Your name"),
        row([button("-", || { app.count -= 1 }), spacer(), button("+", || { app.count += 1 }).style(PRIMARY)]).gap(8),
    ]).style(CARD).margin(24)
}
fn main() { let app = App(); ui_run("Demo", 420, 300, || view(app)) }
```
- **Elements**: `column row box stack grid(cols, [..]) scroll text spacer divider image(path) button(label, fn()) textbox(value, fn(str)) checkbox(b, label, fn(bool)) toggle(b, fn(bool)) slider(f, fn(float)) progress(f)`. A `row` centres its children vertically by default.
- **Style methods** chain on a `Node` or on a `style()` value:
  - size: `width height size min_/max_width min_/max_height width_pct(50.0) height_pct grow(g=1.0)`
  - spacing: `padding(a,b?,c?,d?) margin(..) gap` (CSS shorthand order)
  - layout: `align(Align.Start|Center|End|Stretch) justify(Justify.Start|Center|End|Between|Around|Evenly) center wrap rtl`
  - box: `bg gradient(from, to, angle=180.0) border(w, c) border_color radius(a,b?,c?,d?) pill shadow(x, y, blur, c, spread=0) opacity clip`
  - text: `color font_size weight(100..900) bold italic underline family text_align(Align) line_height(f) nowrap`. Text styles are inherited by children.
  - interaction: `cursor(Cursor.Pointer) hover(Style) pressed(Style) focused(Style) transition(ms) absolute(left?, top?, right?, bottom?)` (`UNSET` skips a side)
  - combine styles: `.style(st)` or `a + b`
- **Drag and drop**: `.draggable(payload: str, label = "")` picks a node up, `.on_drop(fn(str))` on a `.key("k")` node receives the payload; `ui_drag_over()` is the key under the pointer (highlight it), `ui_dragging()`; a press that moves under 5 px is a click; dragging near the edge of a `scroll` scrolls it by itself. A `scroll(..).grow()` gets the space it is given, not its content height, so it scrolls; a `scroll` without `grow`/height takes its content height and cannot scroll. Writing code from a program: `TEXT_LBRACE`, `TEXT_RBRACE`, `text_braces(s)` (`std/text`) avoid the `\{` escapes.
- **Node-only methods**: `on_click(fn()) on_drag(fn(float)) on_submit(fn()) placeholder(s) password() key(k) add(child)`.
- **Colors** are ints 0xAARRGGBB: `hex("#4f46e5")`, `hex("#fff")`, `hex("slate")` (Tailwind-like names), `rgb(r,g,b)`, `rgba(r,g,b,0.25)`, `fade(c, a)`, `mix(a, b, t)`, `lighten(c, t)`, `darken(c, t)`, `WHITE BLACK TRANSPARENT`.
- **App functions**: `ui_run(title, w, h, view)`, `ui_every(ms, fn)` (timer; the view is rebuilt after it), `ui_refresh() ui_quit() ui_title(s)`.
- **Without a window**: `ui_screenshot(view, w, h, "f.bmp") -> bool`, or run any UI program with the env var `ATF_UI_SCREENSHOT=f.bmp`. Use one of these to check a layout, or to test a UI program without blocking.
- **In a browser**: `ATF_UI_WEB=8080 bin/atf.exe run prog.atf` serves the same program at `http://127.0.0.1:8080/` instead of opening a window (no code change). Loopback only (other sites get 403) unless `ATF_UI_WEB_HOST=0.0.0.0` is also set (any host name, Origin must match, no password). To publish: `python tools/build_site.py` builds the static site for GitHub Pages / Netlify / Vercel (`.github/workflows/pages.yml`, custom domain via repo variable `ATF_PAGES_DOMAIN`); the `Dockerfile` (Wine, `ATF_APP`, `PORT`) runs a live program on any Docker host (`render.yaml`, `fly.toml`). Left mouse button only, dialogs and clipboard belong to the server machine and a dialog blocks it, `ui_quit()` ends the run.
- **Application widgets**: `textarea(value, fn(str))` (+ `.rows(n)`; no soft wrap), `select(value, [options], fn(str))`, `tabs([labels], selected, fn(int))` (you show the content), `menu_bar([menu_button("File", [menu_item("Open", fn())])])`, `dropdown(trigger, content)` (floating popup under the trigger), `dialog(title, body, [buttons], on_close)` / `modal(content, on_close)` (add last: `if open { root.add(dialog(..)) }`), `.tooltip(s)`, `icon("save")` (names in STDLIB.md), `canvas(|c| { c.rect(x,y,w,h,col); c.circle; c.line; c.text })` + `.on_pointer(|x, y| ..)`.
  - Text fields edit like a normal app (selection, double/triple click, undo/redo, clipboard, Ctrl+arrows). `.key("name")` + `focus_field("name")` moves the focus.
  - `ui_shortcut("ctrl+s", fn())` (keys like `ctrl+shift+n`, `f5`, `delete`; a key without ctrl/alt is ignored while a text field is focused). Dialogs: `message_box(t, msg)`, `confirm_box(t, q) -> bool`, `open_file_dialog(title, "Text|*.txt|All|*.*") -> str?`, `save_file_dialog(title, filter, "txt") -> str?`. `clipboard_get() clipboard_set(s)`.
  - Popups, dialogs and tooltips are layers on top; they set their own light colours, so in a dark theme give `menu_bar(..)` and fields `.bg(..).color(..)` explicitly.
- **Testing a UI program** (no window, no dialogs): `ui_headless(view, w, h)`, then `ui_click(x, y)`, `ui_click_text("Save")`, `ui_type("abc")`, `ui_keypress("ctrl+z")`, `ui_drag(..)`, `ui_mouse_move(x, y)`, `ui_answers(yes, path)` for the dialogs, `ui_last_dialog()`; check your own data afterwards. Keep the program's data in variables or structs the test can read.
- **Mouse without a click**: `ui_mouse_pos() -> (int, int)` ((-1, -1) outside the window) and, inside a `canvas`, `c.mouse_x()`, `c.mouse_y()` (-1 when outside) and `c.hovered()`. Asking makes the window redraw on every mouse move. `.on_pointer` still fires only on press and drag.
- **Sound, pictures, background jobs**: `std/sound` (`sound_tone(hz, ms, volume=0.5)`, `sound_noise(ms)`, `sound_sweep(a, b, ms)` build a 16 bit WAV in a `str`; `sound_play(wav)` / `sound_play_file(path)` return at once, one voice at a time; `sound_stop() sound_mute(bool) sound_save(path, wav) sound_samples(wav)`); `std/image` (`Image{w, h, pix}` with 0xRRGGBB ints, draw with `c.pixels(x, y, w, h, img.pix, img.w, img.h)`; `image_new(w, h, color)`, `image_load(path) -> Image?` for 24/32 bit BMP, `image_save(img, path)`, `img.get(x, y)` (wraps around), `img.set`, `image_scale/crop/flip_x/flip_y/blit/shade`); `std/task` (`task_spawn(|| -> bool)` returns true when finished, `task_each(n, |k| ..)`, call `task_run(budget_ms)` once per frame, `task_finish() task_pending() task_clear()`).
- Small helpers in the always-available library: `lerp(a, b, t)`, `fract(x)`, `ln(x)`, `array_repeat(value, n)`. `x >>>= n` exists next to `<<=` and `>>=`. A line that starts with `and` / `or` continues the previous expression.
- **Lazy iterators**: `std/iter` (`Iter<T>`; make with `iter_of(arr) iter_range(lo, hi) iter_count(start) iter_repeat(x) iter_lines(text) iter_successors(first, f) iter_from(fn() -> T? {...})`; lazy `map filter filter_map take skip take_while skip_while every enumerate zip chain inspect`; running `collect count sum(start) fold(init, f) for_each first last nth find any all min max join(sep)`; single use; `iter_count`/`iter_repeat` never end, so `take` first).
- **Text, files, programs, config, XML, web, tests**: `std/path` (`path_basename path_dirname path_ext path_stem path_join path_normalize`, `\` is the separator); `std/fs` (`fs_exists fs_is_dir fs_list_dir fs_make_dirs fs_remove_all fs_copy fs_move fs_append_file fs_read_lines fs_write_lines fs_walk fs_cwd`); `std/process` (`proc_output(cmdline) -> (int, str)`, `proc_setenv`, `proc_pid`, `proc_cpu_count`; background: `proc_start(cmdline)` / `proc_start_args(path, args)` -> `Result<Proc, str>` with `read()` (non-blocking, what was printed so far), `running()`, `exit_code()` (-1 while running), `wait() -> (int, str)`, `kill()`; poll it from `ui_every`); `std/regex` (`regex(p)` or `regex_compile(p)` -> `Regex` with `find` (returns `RxMatch?` with `.text .start .group(i)`), `find_all is_match full_match replace_all("$1") split`; **write `{` in a pattern as `\{`**, e.g. `"a\{2,3}"`, and backslashes doubled: `"\\d+"`); `std/toml` (`toml_parse(text) -> Result<JsonValue, str>`, `toml_stringify`); `std/yaml` (`yaml_parse(text) -> Result<JsonValue, str>`, `yaml_stringify(v)`; block and flow styles, `|` and `>` text blocks; no anchors or tags); `std/bigint` (`bigint(n)`, `bigint_parse(s) -> Result<BigInt, str>`, then `+ - * / %`, unary `-`, `== < >` and sorting work; `pow(e: int)`, `pow_mod(e, m)`, `divmod`, `abs sign is_zero digits`, `to_int() -> int?`, `bigint_gcd`, `bigint_factorial`; mixing with int needs `bigint(n)`, `a + 1` is a compile error); `std/crypto` (bcrypt.dll: `crypto_random_bytes(n)`, `crypto_random_int(lo, hi)`, `crypto_pbkdf2(password, salt, iterations, length = 32)`, `crypto_encrypt(key, text, extra = "") -> Result<str, str>` (AES-GCM, key of 16/24/32 bytes, result is nonce + ciphertext + tag), `crypto_decrypt(key, data, extra = "")` (Err on a wrong key or changed data), `crypto_equal(a, b)` (constant time); bytes are in a `str`, show them with `hash_to_hex` from `std/hash`, which also has `hash_sha256` and `hash_hmac_sha256`); `std/xml` (`xml_parse(text) -> Result<XmlNode, str>`, node `tag attrs children attr(name) child(tag) children_named find_all query("a/b") inner_text`, build with `xml_element(tag).set_attr(k, v).add(node)` / `.add_text(tag, text)`, `xml_stringify(n, indent)`); `std/http` (`http_get(url)`, `http_post(url, body, headers)`, `http_request`, `http_download` -> `Result<HttpResponse, str>`; any status is `Ok`, check `r.ok()`); `std/net` (`tcp_connect(host, port) -> Result<TcpConn, str>` with `write write_line read read_line read_exact read_all set_timeout close`, `tcp_listen(port)` (0 = any free port, see `.port`) and `server.accept()`, `net_resolve(host)`; UDP: `udp_bind(port = 0, host = "127.0.0.1") -> Result<UdpSocket, str>` (`.port`), `sock.send_to(host, port, data) -> bool`, `sock.receive(max = 65536) -> UdpPacket?` (`.data .host .port`, nil after the timeout), `set_timeout(ms)`, `close()`; `std/websocket` (`ws_connect("ws://host:port/path") -> Result<WebSocket, str>`, `ws_listen(port)` + `server.accept()`; `ws.send(text) send_binary(data) ping() close(code = 1000, reason = "")`, `ws.receive() -> WsMessage?` with `.kind` ("text", "binary", "close") `.data .code`, pings answered automatically; ws:// only, no wss://; one program cannot `ws_connect` to its own `ws_listen` (no threads): use `ws_handshake_request` + `server.accept()` + `ws_handshake_finish(conn, key)`); a timed-out read returns nil); `std/ini` (`ini_parse(text) -> Result<IniDoc, str>`, `doc.get(section, key) -> str?`, `get_or get_int get_bool set`, keys before a [section] are in section "", `ini_stringify`); `std/url` (`url_parse(s) -> Result<Url, str>` with `scheme host port path query fragment param(name)`, `url_join(base, ref)`, `url_encode(s, plus: false)`, `url_decode`, `url_query_parse`, `url_query_build`); `std/glob` (`glob_match(pattern, text)` with `* ? [a-z] **`, `glob_find(folder, pattern) -> [str]`); `std/httpd` (handler = `fn(HttpRequest) -> HttpReply`; `router_new()` + `app.get("/users/:id", |req| http_text(req.params["id"]))`, `app.handle(req)`; `http_listen(port).unwrap().serve(handler)` answers one connection at a time, `serve_one` answers a single request; replies: `http_text http_html http_json_reply http_redirect http_file http_static(req, folder)`); Websites: the starter site is `app/` (`site.atf` routes, `main.atf`, `public/` served at `/static/*`); a `main` is `http_run(|req| app.handle(req))`, which listens on `$PORT` (open to everyone when PORT is set, else 127.0.0.1:8080, `ATF_HOST` overrides) and `http_listen_env()` only listens; test routes with `app.handle(HttpRequest{ path: "/x" })`; the root `Dockerfile` runs `app/main.atf` on any Docker host; `std/test` (`test(name, || {...})`, `expect expect_eq expect_ne expect_near expect_panics`, `return test_report()` from main).
- **Saving settings and data** (`import "std/app"`): `settings_open("myapp")` -> `Settings` with `get(k, fallback) get_int get_bool set set_int set_bool remove save()`; `app_dir("myapp")` / `app_path("myapp", "data.json")` is the program's folder in APPDATA; `recent_add(s, path)`. Use `std/json` (`json_read_file`, `json_write_file`) for bigger data.
- **Pitfalls**:
  - Names starting with `ui_` / `UI_` are taken by the library, and so are `Node`, `Style`, `Align`, `Justify`, `Cursor`, `Canvas`.
  - In a reassigned chain use `var n = text(..)` then `n = n.style(..)`.
  - Typed closure params need annotations when inferred types are unclear: `|label: str, c: Node| -> Node { ... }`.
  - Build the view from data every time; never keep a `Node` between calls. A `ui_shortcut` registered again with the same keys replaces the old one.
- **Animations** (`std/ui`): `animate("key", target, ms)` glides a float to its target (keys are strings, one per animated value; call it in the view every time), `animate_color`, `animate_with(key, t, ms, ease)`, `animate_from(key, start, target, ms, ease)` (entrance), `anim_loop(seconds)` (0..1 sawtooth), `anim_wave(seconds)` (0..1..0), `anim_keys(t, [..])`, `lerp`, easings `ease_linear ease_in ease_out ease_in_out ease_out_back ease_out_bounce ease_out_elastic`. The window rebuilds the view each frame only while something moves. `anim_set_time(ms)` freezes the clock for tests. Example: `examples/ui/animations.atf`.
- **Web pages** (`import "std/html"`): `h("div", [kids])` then chain `.cls .id .attr .style .text (escaped) .raw .add .add_all .anim("fade-in"|"slide-up"|"slide-left"|"slide-right"|"zoom-in"|"bounce"|"pulse"|"spin"|"shake"|"float", seconds, delay) .reveal() .render()`; `html_page(title, [nodes], css, js, lang, dir)` makes a whole page; `css_keyframes(name, [(pct, css)])`, `css_animation(name, seconds, easing, repeat, delay)`, `css_rule`; serve with `http_html(page)` from `std/httpd`. In a normal string write a literal CSS brace as `\{`. Example: `examples/web_animations.atf`.
- **Examples**: `examples/ui/counter.atf`, `todo.atf`, `dashboard.atf`, look-alikes `calculator.atf`, `minesweeper.atf`, `snake.atf` (canvas + held keys) `paint.atf` (canvas + `on_pointer`), `tetris.atf`, `spreadsheet.atf` (a formula parser/evaluator, good model for a recursive descent parser) and `wolfenstein.atf` (ray caster + sprites + `c.pixels`), and `notes.atf` (a complete program: menus, shortcuts, file dialogs, settings, dark theme), and `minecraft.atf` (a game: `canvas` drawing, a `ui_every` loop, held keys, mouse look and a software rendered picture with `c.pixels`).
- **Games**: `c.pixels_smooth(..)` is the same as `c.pixels(..)` but scales with bilinear filtering, so a low resolution software rendered scene does not look pixelated (use it by default for 3D scenes). There is no resolution limit: `c.pixel_w()` / `c.pixel_h()` are the canvas size in real screen pixels, so render the scene at that size with a `.grow()` canvas (see `minecraft.atf`, which also drops the resolution by itself when frames get slow). `c.pixels(x, y, w, h, colors, pw, ph)` blits an `[int]` of 0xRRGGBB (pw*ph values) stretched to w x h, far faster than a `c.rect` per pixel. `ui_key_down("w")` / `ui_key_down("space")` (held, only while the window is active), `ui_mouse_held(0|1|2)` (left, right, middle), `ui_mouse_capture(true)` hides the pointer and keeps it centred, `ui_mouse_delta() -> (dx, dy)` is the movement since the last call. `ui_pointer_button()` inside an `.on_pointer` handler says which button (0 left, 1 right; a right click reaches only `on_pointer`; tests use `ui_click_right(x, y)`). `c.frect/fcircle/fline` take float coordinates; `floor_int/ceil_int/round_int(x)` return an int. A small 2D sandbox: `examples/ui/2D_minecraft.atf`. Drive the game from `ui_every(30, step)`. The names `ui_mouse_down`, `ui_key` and similar are already taken by the library.

## Traps (things that commonly go wrong)

- `extern "dll" fn local_name(a: i32) -> i32 as "DllSymbol"` calls a Windows DLL function under your own name; without `as` the ATF name is the DLL symbol. Library externs should always use `as` with a module prefix so they do not take short global names.
- Keywords you cannot use as names: `fn let var const if else while for in loop break continue return struct enum impl match import extern true false and or not as defer type nil step unsafe pub interface`. Name a stride parameter `by`, not `step`.
- Range membership needs parentheses: `x in (1..10)`, not `x in 1..10`.
- `for (a, b) in pairs` unpacks tuples (verified with the current compiler; one tip in the tutorial's section 28 saying otherwise is outdated). Without parens, `for a, b in arr` means index and element, and `for k, v in map` means key and value.
- A literal `{` in a string is `\{`. Interpolation cannot start with a quote right after the brace: write `{ "x" }`.
- `if` conditions must be `bool` (no truthy ints). `let` forbids reassigning a name but struct fields and array contents stay mutable.
- A function with a return type must return on every path.
- Text is bytes: `"héllo".len() == 6`; `s[i]` is a one-letter `str`, `s.byte_at(i)` is a byte (compare with `'a'`).
- An optional `str?` prints with quotes; unwrap first.
- Integer overflow wraps silently; `/` or `%` by zero, bad index, missing map key, `!` on nil all panic with a traceback (exit code 1). Infinite recursion kills the process silently (exit -1073741571).
- Assigning a struct/array/map aliases it; use `copy(x)` (shallow) for an independent one.
- Windows only (64-bit Windows 10/11; on Linux the programs run through Wine). Output is buffered; it is flushed on exit, on input and on stderr writes.

## Most common compile errors and their fix

| Mistake | Fix |
|---|---|
| Reassigning a `let` | use `var` |
| `int?` used in arithmetic or as a plain value | `!`, `?? default` or `if let` |
| `var a = []` | give a type: `var a: [int] = []` |
| `if n {` with an int | write a bool: `if n != 0 {` |
| `x in 1..10` | `x in (1..10)` |
| Missing `_ =>` or a variant in `match` | add the arm |
| Literal `{` in a string | `\{` |
| Mixing int and float in a call or assignment | `float(n)` / `int(x)` |
| A function name that already exists in another file or the library | one global namespace: rename it (prefix it) |
| Using `step`, `type`, `pub`, `in`... as a name | pick another name (`by`) |
| Python/Rust habits (`def`, `elif`, `;` required, `&mut`, `self` without `fn`) | `fn`, `else if`, no `&`, `fn f(self)` |

## Converting to and from Python and Rust
`atf run tools/convert.atf prog.py --to atf` (also `.rs`, and `--to py|rs`, `-o out`) translates between ATF, Python and Rust. The result is a starting point, not a finished port: comments are dropped, types and ownership are guessed, and library functions with no counterpart (`str_builder`, `regex`, `std/ui`) are kept as they are. Notes about guesses go to stderr as `note: ...`. After converting to ATF, always run `atf check` and fix what it reports. Details: `docs/CONVERT.md`.

## Performance habits
`str_builder()` or `join` instead of `+` in loops; `array_make::<T>(n)` / `array_with_cap::<T>(n)`; `byte_at` instead of `s[i]` in hot loops; avoid `int?` in tight loops (sentinels are ~7x faster); `x * x` over `x ** 2`; `set.has` / `key in map` over `array.contains`; measure with `clock()`.

## Teaching mode
When the user wants to *learn* ATF rather than get code written, go step by step: variables and types, functions, arrays/maps, structs and methods, enums and `match`, optionals and `Result`, closures, generics, modules. Show a short runnable program and its output for each concept, and run it with `atf run` so the shown output is real. Point to `docs/TUTORIAL.md` (English) and `docs/TUTORIAL.he.md` (Hebrew) in the repo for the full course, and answer in the user's language (the user writes Hebrew; the code and identifiers stay in English).

## Reference files
- `references/stdlib.md` - every library function, method and std module (large; search it with Grep for a function name instead of reading it whole).
- Optional, online: https://github.com/tamat2013/ATF (tutorial, STDLIB, examples, releases, issues).
