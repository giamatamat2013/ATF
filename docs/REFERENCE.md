# ATF language reference

The exact rules of the language in one place. To learn ATF step by step, read the [tutorial](TUTORIAL.md);
for every library function see [STDLIB.md](STDLIB.md).

## Contents

- [Programs](#programs)
- [Lexical rules](#lexical-rules)
- [Types](#types)
- [Operators and precedence](#operators-and-precedence)
- [Statements](#statements)
- [Functions and closures](#functions-and-closures)
- [Structs, enums and `match`](#structs-enums-and-match)
- [Optionals and errors](#optionals-and-errors)
- [Generics and interfaces](#generics-and-interfaces)
- [Modules](#modules)
- [Memory](#memory)
- [Command line](#command-line)

## Programs

A program starts at `fn main()`. It may also be `fn main(args: [str])`, and either form may return an `int`, which
becomes the exit code. Declarations outside functions (functions, structs, enums, constants, global variables) may
appear in any order. All files of a program share **one global namespace**: a name defined twice is a compile error.

A file may start with a line that names the ATF version it was written for, `// ATF 1.2.0`. The line is optional and
is only a comment, except for one thing: when the compiler is older than the version on that line, `atf run`,
`atf build` and `atf check` print a warning on stderr and go on. The version is read from the first line of the main
file only.

## Lexical rules

- Comments start with `//` and end at the end of the line.
- Semicolons are optional. A statement continues onto the next line when the line ends with an operator or a comma,
  when it is inside brackets, or when the next line starts with `.`, `&&`, `||` or `??`.
- Integer literals: `42`, `1_000`, `0xFF`, `0b1010`. Floats: `3.14`, `1e-9`. Character literals such as `'A'` are
  `byte` values.
- Strings are UTF-8 byte sequences. `"..."` may contain `{expression}` (interpolation, with an optional format
  after a colon: `{x:.2f}`, `{n:05}`, `{n:x}`) and the escapes `\n \t \r \" \\ \{ \} \xHH \u{263A}`.
  `"""..."""` spans lines and `r"..."` is raw.
- Keywords: `fn let var const if else while for in loop break continue return struct enum impl match import extern
  true false and or not as defer type nil step unsafe pub interface`.

## Types

| Type | Meaning |
|---|---|
| `int` | 64-bit signed, arithmetic wraps around |
| `float` | 64-bit floating point |
| `bool` | `true` or `false` |
| `str` | immutable text (bytes, UTF-8) |
| `byte` | 0 to 255 |
| `[T]` | growable array |
| `{K: V}` | map that keeps insertion order |
| `(A, B)` | tuple, immutable |
| `T?` | optional: a `T` or `nil` |
| `Result<T, E>` | `Result.Ok(T)` or `Result.Err(E)` |
| `fn(A) -> B` | function value |

Types are inferred for `let` and `var`. Conversions are always explicit: `int(3.9)`, `float(7)`, `str(42)`,
`"12".to_int()`, or `x as float`. A float never becomes an `int` implicitly, and an optional never behaves as a plain value.
Arrays, maps and structs are **references**: assigning one does not copy it (use `copy(x)` for a shallow copy).

## Operators and precedence

From tightest to loosest:

| Level | Operators |
|---|---|
| 1 | `**` (power, right-associative) |
| 2 | unary `-`, `~`, `!` |
| 3 | `as` |
| 4 | `*`, `/`, `%` |
| 5 | `+`, `-` |
| 6 | `<<`, `>>`, `>>>` |
| 7 | `&` |
| 8 | `^` |
| 9 | `\|` |
| 10 | `==`, `!=`, `<`, `>`, `<=`, `>=`, `in`, `not in` |
| 11 | `not` |
| 12 | `and` (`&&`) |
| 13 | `or` (`\|\|`) |
| 14 | `??` |

So `-2 ** 2` is `-4` and `not a == b` is `not (a == b)`. Integer `/` truncates toward zero and `%` takes the sign of the
left operand. `int` and `float` mix in arithmetic. `==` compares structurally (arrays, maps, structs, tuples by content).
Postfix `!` unwraps an optional (panics on `nil`) and postfix `?` returns early (see [Optionals and errors](#optionals-and-errors)).
Assignment operators: `= += -= *= /= %= &= |= ^= <<= >>=`. Multiple assignment: `a, b = b, a`.

## Statements

```atf nocheck
let x = 5                 // immutable
var n = 0                 // mutable;  var total: int  starts at 0
const MAX = 30            // constant, also allowed at the top level

if c { } else if d { } else { }       // the condition must be a bool; if is also an expression (with else)
while c { }
loop { break }
for i in 0..5 { }                     // 0..=5 includes the end; 0..=20 step 5; 10..0 step -3
for x in arr { }  for i, x in arr { }  for k, v in map { }  for ch in "text" { }
outer: for a in xs { for b in ys { continue outer } }   // labels
defer cleanup()                       // runs when the block ends, last in first out
```

## Functions and closures

```atf nocheck
fn add(a: int, b: int = 1) -> int { return a + b }     // default values; named arguments: add(b: 2, a: 1)
fn twice(x: int) -> int => x * 2                       // short form
fn range_of(a: [int]) -> (int, int) { return (lo, hi) } // several results as a tuple
let f = |x| x * 2                                      // closures capture and may change variables
```

A function that ends without a value returns nothing. `never` marks a function that does not return (`panic`).

## Structs, enums and `match`

```atf nocheck
struct Item { name: str, price: float, count: int = 1 }
let a = Item("x", 1.0)               // positional ...
let b = Item{ name: "y", price: 2.0 } // ... or by name

impl Item {
    fn new(n: str) -> Item { return Item(n, 0.0) }        // called as Item.new("z")
    fn total(self) -> float { return self.price * float(self.count) }
    fn to_str(self) -> str { return "{self.name}" }       // used by println and "{x}"
}
```

Operator methods: `op_add op_sub op_mul op_div op_mod op_pow op_neg op_index op_set_index op_slice op_contains` and
the bit operators, plus `eq` and `cmp` (negative, zero or positive: enables `<`, `>` and sorting).

```atf nocheck
enum Shape { Circle(float), Rect(float, float), Point }
enum Level { Low = 1, High = 10 }                          // numbered; int(Level.High)

let area = match s {
    Shape.Circle(r) => 3.14 * r * r
    Shape.Rect(w, h) => w * h
    Shape.Point => 0.0
}
```

A `match` used as a value must cover every case (or end with `_ =>`). Patterns: literals, `1 | 2`, ranges `4..=9`,
guards `x if x < 0`, `_`, tuples, nested enum variants, and structs (`Point(0, 0)`, `Point{ x: 0, y }`,
`Point{ y: 0, .. }`). Arms are separated by newlines. `if let` and `while let` take one pattern.

## Optionals and errors

```atf nocheck
fn find(a: [int], x: int) -> int? { return nil }
let i = find(a, 3) ?? -1              // a default when nil
let j = find(a, 3)!                   // panics when nil
if let p = find(a, 3) { }

fn parse(s: str) -> Result<int, str> {
    let n = s.parse_int()
    if n == nil { return Result.Err("bad number") }
    return Result.Ok(n!)
}
let v = parse("1")?                   // on Err, returns that Err from the current function
```

`x?` is allowed only in a function whose result type is a `Result` (or an optional, which then returns `nil`).
`panic(msg)` stops the program with a traceback; `assert(cond, msg)` panics when `cond` is false;
`catch_panic(|| { ... })` runs code and returns the panic message as a `str?`. `defer` blocks do not run on a panic.

## Generics and interfaces

```atf nocheck
fn largest<T>(a: [T]) -> T { ... }                   // checked for each type it is used with
struct Stack<T> { items: [T] }
impl<T> Stack<T> { fn len(self) -> int { return self.items.len() } }
let s: Stack<int> = Stack{ items: [] }

interface Shape { fn area(self) -> float }           // structural: any type with these methods fits
let shapes: [Shape] = [Circle(1.0), Rect(2.0, 3.0)]
```

## Modules

`import "other"` loads `other.atf` (the path is relative to the importing file, the ending may be left out).
`import "std/json"` loads a library module: `algo`, `app`, `args`, `base64`, `bigint`, `bits`, `collections`, `csv`, `datetime`,
`fs`, `glob`, `hash`, `hex`, `http`, `httpd`, `ini`, `json`, `log`, `math`, `net`, `path`, `process`, `random`, `regex`, `test`, `text`,
`toml`, `ui`, `url`, `xml` and `yaml` (all described in [STDLIB.md](STDLIB.md)). Everything in an imported file becomes part of the one global namespace. `include_str("f.txt")` embeds a
file in the program at compile time.

## Memory

Memory is managed by a garbage collector. Programs never free memory. `gc()` forces a collection; `gc_runs()` and
`gc_live_bytes()` report what it did. Unsafe pointer operations (`ptr<T>`, `__alloc`) exist for the standard library and for
calling Windows functions with `extern`; ordinary programs do not need them.

## Calling Windows functions: `extern`

`extern "dll" fn name(params) -> T` declares a function from a Windows DLL; the program then calls it like any
other function. Add `as "Symbol"` to give it your own name when the DLL's name is too short or would clash
with another function (the standard library uses this for names like `send` and `connect`).

<!-- id: extern-as -->
```atf
extern "kernel32" fn process_id() -> i32 as "GetCurrentProcessId"

fn main() {
    println(process_id() > 0)
}
```
```output
true
```

## Command line

```text
atf run f.atf [args...]       compile and run (standard input works)
atf build f.atf -o f.exe      write a stand-alone program
atf check f.atf               report errors only
atf fmt f.atf [--check]       fix indentation
atf repl                      interactive prompt
atf version
```
