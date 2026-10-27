---
name: atf
description: Write, read, debug, compile and explain programs in ATF ("Accessible Typed Fast", files ending in .atf), a small statically typed language that compiles to native Windows .exe files. Use this skill whenever the user mentions ATF, .atf files, `atf run` / `atf build`, the atefintalode project, the ATF compiler or its standard library (std/json, std/csv, ...), or asks to write or fix code in this language, even if they just say "the language in this repo". ATF looks like a mix of Rust and Python but has its own rules, so do not guess its syntax from other languages - consult this skill first.
---

# ATF language

ATF is compiled (x86-64 machine code written directly into a Windows `.exe`), statically typed, garbage collected, with type inference. The compiler is self-hosted and lives in the ATF repo (`bin/atf.exe`, sources in `compiler/`). Its syntax resembles Rust/Python/Go, but it differs in many small ways, so write ATF from the rules below rather than from habit. Getting these wrong produces compile errors, which is the main failure mode.

## Workflow

1. Find the compiler: `bin/atf.exe` (or `atf.cmd`) in the repo root; `atf` if installed on PATH. In Git Bash call `bin/atf.exe`, in PowerShell `.\atf` or `bin\atf.exe`.
2. Write the code, then **always compile it** before reporting it works:
   ```
   atf check f.atf            # errors only, prints "ok"
   atf run f.atf [args...]    # compile + run (stdin works: atf run f.atf < in.txt)
   atf build f.atf -o f.exe   # stand-alone exe
   atf fmt f.atf [--check]    # fix indentation
   atf repl
   ```
3. Compiler errors are precise (message, `file:line:col`, a caret, often a `hint:`). Read the hint and fix; do not rewrite blindly.
4. When unsure about a library function, check `references/stdlib.md` (copy of the repo's docs/STDLIB.md) or the repo's `docs/TUTORIAL.md`, `atf/stdlib/prelude.atf` (the always-available library, in ATF), and `examples/` (45 tested programs). Prefer the repo copies if present: they are newer than this skill.

## Program shape

```atf
fn main() {                       // or: fn main(args: [str]) -> int  (return value = exit code)
    println("Hello, {name}!")     // {expr} interpolation, \{ for literal brace
}
```
No semicolons needed (optional), no imports for the core library, no header files. Declarations outside functions can appear in any order. A statement continues onto the next line if the line ends with an operator/comma, is inside brackets, or the next line starts with `.`, `&&`, `||`, `??`.

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
for i in 0..5 { }  0..=5  0..=20 step 5  10..0 step -3      // `step` is a keyword
for x in arr { }   for i, x in arr { }   for k, v in map { }   for ch in "str" { }
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
Methods: `len trim upper lower reverse find contains starts_with ends_with replace count split join lines split_whitespace repeat pad_left pad_right byte_at parse_int parse_float to_int to_float`; slicing `s[a..b]`, `s[a..]`, `s[..b]`; `"ab" * 3`; `", ".join(arr)`. `parse_int()` returns `int?`; `to_int()` panics on bad input. Use `str_builder()` (`add`, `add_byte`, `finish`) instead of `s = s + x` in loops.

### Collections
- Array: `push pop insert(i,x) remove(i) first last contains index_of len is_empty sort sort_by(|a,b| a-b) sorted reversed reverse map filter reduce(init, |acc,x| ..) any all find count sum min max extend copy for_each`, slicing, `+` concatenation. Empty needs a type: `var w: [str] = []`. Create sized: `array_make::<int>(n)`. Arrays, maps, structs are **references**; use `copy(x)` for a shallow copy.
- Map: `var m: {str: int} = {}`; `m[k] = v`, `m.get(k, default)`, `m.try_get(k)` (optional), `k in m`, `m.has(k)`, `m.keys() values() items() remove(k) len()`. A missing key panics. Insertion order is kept.
- Set: `let s = set_new::<int>()`; `add has remove len items`; `x in s`; iterate with `for x in s.items()`.
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
let shapes: [Shape] = [Circle(1.0), Rect(2.0, 3.0)]
```

### I/O, modules, misc
`println print eprintln eprint flush`; `input(prompt)`; `read_line()` -> `str?` (nil at EOF); `read_all_stdin()`; `read_file(p)` -> `str?`; `write_file(p, text)` -> bool; `file_exists delete_file make_dir temp_dir getenv exit run_command run_process`; `rand_seed rand_int(lo,hi) rand_float rand_choice shuffle clock`; math `sqrt abs min max PI E INT_MAX INT_MIN`; `chr ord range range_from zip same copy`; GC: `gc gc_runs gc_live_bytes`.
Modules: `import "other"` (path relative to the importing file) or `import "std/json"` (also base64, collections, csv, datetime, hash, hex). **One global namespace** across all files: give globals specific names; duplicate definitions are compile errors. `include_str("f.txt")` embeds a file at compile time.

## Traps (things that commonly go wrong)

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
- Windows only (64-bit Windows 10/11). Output is buffered; it is flushed on exit, on input and on stderr writes.

## Performance habits
`str_builder()` or `join` instead of `+` in loops; `array_make::<T>(n)` / `array_with_cap::<T>(n)`; `byte_at` instead of `s[i]` in hot loops; avoid `int?` in tight loops (sentinels are ~7x faster); `x * x` over `x ** 2`; `set.has` / `key in map` over `array.contains`; measure with `clock()`.

## Teaching mode
When the user wants to *learn* ATF rather than get code written, go step by step: variables and types, functions, arrays/maps, structs and methods, enums and `match`, optionals and `Result`, closures, generics, modules. Show a short runnable program and its output for each concept, and run it with `atf run` so the shown output is real. Point to `docs/TUTORIAL.md` (English) and `docs/TUTORIAL.he.md` (Hebrew) in the repo for the full course, and answer in the user's language (the user writes Hebrew; the code and identifiers stay in English).

## Reference files
- `references/stdlib.md` - every library function, method and std module (large; search it with Grep for a function name instead of reading it whole).
