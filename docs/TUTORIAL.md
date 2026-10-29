# ATF tutorial

Welcome! This tutorial teaches you **ATF** (*Accessible Typed Fast*; source files end in `.atf`) step by step.
You do not need to know any other programming language, but if you do, most things will look familiar.

ATF is a *compiled*, *statically typed* language: the compiler checks your program for mistakes
before it runs, and turns it into a native Windows program (`.exe`) that starts instantly and runs fast.
It is also *easy to learn*: no semicolons, no header files, no manual memory management.

Every code sample in this tutorial was compiled and run with the native compiler `bin/atf.exe`, and the output shown
is exactly what the program prints; `python tests/check_docs.py` re-checks all of them.

A Hebrew tutorial is in [TUTORIAL.he.md](TUTORIAL.he.md). Every detail of the language is described in
[REFERENCE.md](REFERENCE.md), and every library function in [STDLIB.md](STDLIB.md).

**Contents**

1. [Running your first program](#1-running-your-first-program)
2. [Comments and statements](#2-comments-and-statements)
3. [Variables: `let`, `var` and `const`](#3-variables-let-var-and-const)
4. [Basic types](#4-basic-types)
5. [Operators](#5-operators)
6. [Text: strings, interpolation and formatting](#6-text-strings-interpolation-and-formatting)
7. [Printing](#7-printing)
8. [Making decisions: `if`](#8-making-decisions-if)
9. [Loops](#9-loops)
10. [Functions](#10-functions)
11. [Arrays](#11-arrays)
12. [List comprehensions](#12-list-comprehensions)
13. [Maps](#13-maps)
14. [Sets](#14-sets)
15. [Tuples](#15-tuples)
16. [Structs and methods](#16-structs-and-methods)
17. [Enums and `match`](#17-enums-and-match)
18. [Optionals: values that may be `nil`](#18-optionals-values-that-may-be-nil)
19. [`Result` and the `?` operator](#19-result-and-the--operator)
20. [Closures and higher-order functions](#20-closures-and-higher-order-functions)
21. [Generics and interfaces](#21-generics-and-interfaces)
22. [When things go wrong: panics, `assert`, `catch_panic`, `try`/`catch`, `defer`](#22-when-things-go-wrong)
23. [Reading a traceback](#23-reading-a-traceback)
24. [Input, output and files](#24-input-output-and-files)
25. [Modules: `import`](#25-modules-import)
26. [Memory and the garbage collector](#26-memory-and-the-garbage-collector)
27. [Performance tips](#27-performance-tips)
28. [Tips, traps and where to go next](#28-tips-traps-and-where-to-go-next)

---

## 1. Running your first program

Create a file `hello.atf`:

<!-- id: hello -->
```atf
fn main() {
    println("Hello, world!")
}
```
```output
Hello, world!
```

Run it from the project folder (in `cmd` or PowerShell; `atf.cmd` simply calls the compiler `bin\atf.exe`):

```bash
atf run hello.atf                  # compile and run (in PowerShell write  .\atf run hello.atf)
atf build hello.atf                # create hello.exe next to it
atf build hello.atf -o greet.exe   # choose the name of the program
atf check hello.atf                # only check for errors, prints "ok"
atf repl                           # type code line by line and see the results at once
atf fmt hello.atf                  # fix the indentation (atf fmt hello.atf --check only reports)
atf version                        # which compiler is this?
```

In Git Bash, call the compiler directly: `bin/atf.exe run hello.atf`. The compiler is a single program with no
dependencies, and the `.exe` files it creates are stand-alone too: copy them to any 64-bit Windows computer and they run.
Arguments after the file name are passed to your program: `atf run prog.atf one two`.

On Linux, for example a remote server, install Wine once (`sudo apt install wine64`) and start the compiler through it:
`wine bin/atf.exe run hello.atf`. The `.exe` files it creates run the same way: `wine hello.exe`.

Every program starts at `fn main()`. A function body is written between `{` and `}`.
`println` prints a line of text. Text is written between double quotes.

---

## 2. Comments and statements

<!-- id: comments -->
```atf
// A line comment runs to the end of the line.
/* A block comment can span several lines
   /* and block comments can be nested */
*/
fn main() {
    println("one")       // a comment after a statement
    println("two"); println("three")   // a semicolon separates statements on one line
    println(
        "four",
        "five"
    )
    let total = 1 +
        2
    let words = "c b a".split(" ")
        .sorted()
    println(total, words)
}
```
```output
one
two
three
four five
3 ["a", "b", "c"]
```

* One statement per line is the normal style; **semicolons are optional**.
* A statement continues on the next line if the line ends with an operator or a comma, if you are inside
  `( )` or `[ ]` brackets, or if the next line starts with `.` (a method chain), `&&`, `||` or `??`.

The first line of a file can name the ATF version the file was written for. It is a comment, so it is optional, and
the compiler does not need it. When the compiler is older than the version on that line, `atf run`, `atf build` and
`atf check` print a warning on stderr and still compile the file. This is useful when a program moves to a computer
with an older ATF.

<!-- id: version-line -->
```atf
// ATF 1.2.0
fn main() {
    println("written for ATF 1.2.0")
}
```
```output
written for ATF 1.2.0
```

---

## 3. Variables: `let`, `var` and `const`

`let` creates a variable that cannot be changed. `var` creates one that can.

<!-- id: variables -->
```atf
fn main() {
    let name = "Ada"          // let: fixed once set
    var count = 0             // var: may change
    count = count + 1
    count += 1                // short for  count = count + 1
    println(name, count)

    let age: int = 36         // you may write the type; it is usually inferred
    let ratio: float = 2      // an int fits where a float is expected
    println(age, ratio)

    var total: int            // declared without a value: starts as 0
    println(total)
}
```
```output
Ada 2
36 2.0
0
```

The compiler guesses the type from the value, so you rarely write it. A variable keeps its type forever:

<!-- id: let-error -->
```atf
fn main() {
    let x = 5
    x = 6
}
```
```error
error: cannot assign to 'x' because it was declared with 'let'
  --> main.atf:3:5
 3 |     x = 6
   |     ^
  hint: declare it with 'var x = ...' to allow changes
```

Reading the message: *what* is wrong, *where* (file, line, column and a picture), and often a *hint*.

You can declare a variable again with the same name (this is called **shadowing**), also in an inner block:

<!-- id: shadowing -->
```atf
fn main() {
    let x = 1
    let x = x + 10            // a new variable that hides the old one
    println(x)
    {
        let x = "inner"       // only lives inside this block
        println(x)
    }
    println(x)
}
```
```output
11
inner
11
```

Several variables can be assigned in one statement. All the values on the right are computed first, so swapping
needs no helper variable:

<!-- id: multi-assign -->
```atf
fn main() {
    var a = 1
    var b = 2
    a, b = b, a
    println(a, b)

    var x = 0
    var y = 1
    for i in 0..10 { x, y = y, x + y }     // Fibonacci numbers
    println(x)
}
```
```output
2 1
55
```

**Constants** (`const`) and **global variables** live outside functions. A constant can never change: when its value is
known at compile time (like `3 * 10`) it is built into the program, otherwise (like `const START = clock()`) it is computed
once when the program starts. A global `var` can be changed by any function. Declarations outside functions can appear
in any order.

<!-- id: globals -->
```atf
const MAX_USERS = 3 * 10
const GREETING = "hi " + "there"
var visits = 0

fn visit() {
    visits += 1
}

fn main() {
    visit()
    visit()
    println(MAX_USERS, GREETING, visits)
}
```
```output
30 hi there 2
```

---

## 4. Basic types

| type    | what it holds                              | examples                |
|---------|--------------------------------------------|-------------------------|
| `int`   | 64-bit whole number                        | `42`, `-7`, `0xFF`, `1_000_000` |
| `float` | 64-bit decimal number                      | `3.14`, `1e-3`, `2.0`   |
| `bool`  | true or false                              | `true`, `false`         |
| `str`   | text (UTF-8, immutable)                    | `"hello"`               |
| `byte`  | a number from 0 to 255 (a "character")     | `'A'`, `byte(200)`      |

<!-- id: types -->
```atf
fn main() {
    let a = 42
    let b = 3.14
    let c = true
    let d = "text"
    let e = 'A'                 // a character literal is a byte: its number is 65
    println(a, b, c, d, e)
    println(0xFF, 0b1010, 0o17, 1_000_000)    // hex, binary, octal, digit separators
    println(1.5e3, 2.5e-3)
}
```
```output
42 3.14 true text 65
255 10 15 1000000
1500.0 0.0025
```

**Converting** between types is always explicit, with `int(...)`, `float(...)`, `str(...)`, `byte(...)`, `bool(...)`:

<!-- id: conversions -->
```atf
fn main() {
    println(int(3.99), int(-3.99))        // cuts off the decimals (towards zero)
    println(float(7), 7 as float)         // `x as type` also works
    println(str(42) + "!", int("12") + 1, float("2.5") * 2.0)
    println('A' + 1, chr(66), ord("C"))    // letters and numbers
    println(byte(300), bool(5), bool(0))
}
```
```output
3 -3
7.0 7.0
42! 13 5.0
66 B 67
44 true false
```

Integer and float mix freely in arithmetic (the int becomes a float), but a float never silently becomes an int:

<!-- id: int-float -->
```atf
fn main() {
    println(7 / 2, 7 / 2.0, 7 % 3, -7 / 2, -7 % 3)
    let big = 9223372036854775807     // the largest int
    println(big + 1)                  // integers wrap around silently
    println(INT_MAX, INT_MIN)
}
```
```output
3 3.5 1 -3 -1
-9223372036854775808
9223372036854775807 -9223372036854775808
```

Note that integer division `7 / 2` is `3` (the decimals are dropped, rounding towards zero) and that `%` has the sign of the left number.

If you forget a conversion the compiler tells you:

<!-- id: type-error -->
```atf
fn main() {
    let n: int = 3.7
    println(n)
}
```
```error
error: type mismatch: expected int but found float
  --> main.atf:2:18
 2 |     let n: int = 3.7
   |                  ^
  hint: use int(x) to convert a float to an int
```

---

## 5. Operators

| operators                    | meaning                                     |
|------------------------------|---------------------------------------------|
| `+ - * / %`                  | arithmetic                                  |
| `**`                         | power (`2 ** 10`); for ints the exponent must not be negative |
| `== !=`                      | equal / not equal: numbers, text, arrays, maps, tuples, structs, enums |
| `< > <= >=`                  | order: numbers, text, tuples, simple enums (and your types with `cmp`) |
| `and or not` (or `&& \|\| !`) | logic; `and`/`or` stop early                |
| `& \| ^ ~ << >> >>>`         | bit operations (`>>` keeps the sign, `>>>` fills with zeros) |
| `in`, `not in`               | membership: arrays, text, maps, sets, ranges `x in (1..10)` |
| `x as T`                     | conversion (`7 as float`)                   |
| `= += -= *= /= %= **= &= \|= ^= <<= >>=` | assignment                      |
| `x ?? d`, `x!`, `x?`         | optional handling (section 18)              |

<!-- id: operators -->
```atf
fn main() {
    println(2 + 3 * 4, (2 + 3) * 4, 2 ** 10, -2 ** 2, 2 ** 3 ** 2)
    println(10 / 3, 10 % 3, 10.0 / 4.0, 2.0 ** 0.5)
    println(1 < 2, 2 == 2.0, "abc" < "abd", "x" != "y")
    println(true and false, true or false, not true)
    println(5 & 3, 5 | 3, 5 ^ 3, ~5, 1 << 10, -16 >> 2, -1 >>> 60)
    println(3 in [1, 2, 3], "ell" in "hello", 7 not in [1, 2], 5 in (1..10), 10 in (1..10), 10 in (1..=10))

    var n = 7
    n *= 3
    n -= 1
    n %= 6
    println(n)
}
```
```output
14 20 1024 -4 512
3 1 2.5 1.4142135623730951
true true true true
false true false
1 7 6 -6 1024 -4 15
true true true true false true
2
```

Precedence, from tightest to loosest: `**`, unary `- ~ !`, `as`, `* / %`, `+ -`, shifts, `&`, `^`, `|`,
comparisons and `in`, `not`, `and`, `or`, `??`. So `-2 ** 2` is `-(2 ** 2)` and `not a == b` is `not (a == b)`.
Use parentheses whenever you are unsure. The full table is in the [reference](REFERENCE.md#operators-and-precedence).

> **Note:** write a range test with parentheses: `x in (1..10)`. Without them (`x in 1..10`) the compiler currently
> reports an error, because `..` binds more loosely than `in`.

---

## 6. Text: strings, interpolation and formatting

Put any expression between `{` and `}` inside a string to insert its value (**string interpolation**):

<!-- id: interpolation -->
```atf
fn main() {
    let name = "world"
    let n = 3
    println("Hello, {name}! {n} + {n} = {n + n}")
    println("upper: {name.upper()}, length: {name.len()}")
    println("a literal brace: \{ and }")       // write \{ for a literal opening brace
}
```
```output
Hello, world! 3 + 3 = 6
upper: WORLD, length: 5
a literal brace: { and }
```

After a colon you can add a **format specification**:

| spec      | meaning                                  | example            | result       |
|-----------|------------------------------------------|--------------------|--------------|
| `.2f`     | fixed number of decimals                 | `{3.14159:.2f}`    | `3.14`       |
| `8.3f`    | width 8, 3 decimals                      | `{2.5:8.3f}`       | `   2.500`   |
| `5`       | minimum width (numbers right, text left)| `{42:5}`           | `   42`      |
| `<5` `>5` `^5` | align left, right, center          | `{42:<5}`          | `42   `      |
| `05`      | pad with zeros                           | `{42:05}`          | `00042`      |
| `x` `X` `b` | hexadecimal, HEX, binary              | `{255:x}`          | `ff`         |

<!-- id: format -->
```atf
fn main() {
    let pi = 3.14159265
    let n = 255
    println("[{pi:.2f}] [{pi:10.4f}] [{pi}]")
    println("[{n:6}] [{n:<6}] [{n:>6}] [{n:^6}] [{n:06}]")
    println("hex {n:x}, HEX {n:X}, binary {n:b}, binary padded {5:08b}")
    let word = "hi"
    println("[{word:6}] [{word:>6}] [{word:^6}]")
}
```
```output
[3.14] [    3.1416] [3.14159265]
[   255] [255   ] [   255] [ 255  ] [000255]
hex ff, HEX FF, binary 11111111, binary padded 00000101
[hi    ] [    hi] [  hi  ]
```

Special characters are written with a backslash: `\n` (new line), `\t` (tab), `\"` (quote), `\\` (backslash),
`\{` and `\}` (braces), `\xHH` (a byte, in hex) and `\u{263A}` (any Unicode character).
Text can span several lines with triple quotes `"""..."""`, and **raw** strings `r"..."` ignore backslashes and braces:

<!-- id: multiline -->
```atf
fn main() {
    let poem = """Roses are red,
Violets are blue."""
    println(poem)
    println("tab:\t| quote:\" | backslash:\\ | smile:\u{263A}")
    println(r"raw: \n {not interpolated}")
}
```
```output
Roses are red,
Violets are blue.
tab:	| quote:" | backslash:\ | smile:☺
raw: \n {not interpolated}
```

### Working with text

Strings are **immutable**: methods return new strings. Indexing counts from 0, and `s[a..b]` takes a piece
(from `a` up to but not including `b`):

<!-- id: string-methods -->
```atf
fn main() {
    let s = "  Hello, World  "
    let t = s.trim()
    println("[{t}] length {t.len()}")
    println(t.upper(), t.lower(), t.reverse())
    println(t[0], t[7], t[0..5], t[7..], t[..5])
    println(t.find("World"), t.find("xyz"), t.contains("lo,"), t.starts_with("Hell"), t.ends_with("d"))
    println(t.replace("l", "L"), t.count("l"))
    println("a,b,c".split(","), ", ".join(["x", "y", "z"]), "ab" * 3)
    println("  many   spaces here ".split_whitespace())
    println("line1\nline2\nline3".lines())
    println("7".pad_left(3), "7".pad_right(3) + "|", pad_zero("7", 3))
}
```
```output
[Hello, World] length 12
HELLO, WORLD hello, world dlroW ,olleH
H W Hello World Hello
7 -1 true true true
HeLLo, WorLd 3
["a", "b", "c"] x, y, z ababab
["many", "spaces", "here"]
["line1", "line2", "line3"]
  7 7  | 007
```

Comparing text with `==`, `<` and so on compares the letters (byte by byte). Turning text into numbers:

<!-- id: parsing -->
```atf
fn main() {
    println("42".parse_int(), "4x2".parse_int())       // int?  (nil when it is not a number)
    println("3.5".parse_float(), " 12 ".parse_int())
    println("42".to_int() + 1, "2.5".to_float() * 2.0)  // these stop the program if it is not a number
    println("ff".parse_int_base(16), 255.to_hex(), 5.to_bin())
}
```
```output
42 nil
3.5 12
43 5.0
255 ff 101
```

> **Good to know:** a `str` is a sequence of bytes holding UTF-8. `len()`, indexing and `for` loops work on
> *bytes*, so they are exact for English text but see each non-English letter as several pieces.
> `chr(955)` creates the text `λ` and `ord("A")` gives 65. `s[i]` gives a one-letter `str`; `s.byte_at(i)` gives
> the raw `byte` (a number), which is handy for comparisons like `s.byte_at(i) == 'a'`.

### Python names

If you know Python, the Python names work too. They sit next to the ATF names and do exactly the same thing,
so use whichever you like:

| ATF | Python name |
|---|---|
| `s.starts_with(p)`, `s.ends_with(p)` | `s.startswith(p)`, `s.endswith(p)` |
| `s.trim()`, `trim_start()`, `trim_end()` | `s.strip()`, `lstrip()`, `rstrip()` |
| `s.pad_right(w)`, `s.pad_left(w)` | `s.ljust(w)`, `s.rjust(w)` |
| `s.is_digits()`, `s.lines()` | `s.isdigit()`, `s.splitlines()` |
| `a.push(x)` | `a.append(x)` |
| `set.remove(x)` | `set.discard(x)` |

`s.zfill(w)` pads with zeros (`"42".zfill(5)` is `00042`), and `m.update(other)` copies one map into another.

```atf
fn main() {
    let s = "  Hello  "
    let n = "7"
    println("[{s.strip()}] {s.strip().startswith("He")} {n.zfill(3)}")
    var a: [int] = []
    a.append(1)
    a.push(2)
    println("{a}")
}
```
```output
[Hello] true 007
[1, 2]
```

---

## 7. Printing

* `println(a, b, c)` prints its arguments separated by one space, then a new line.
* `print(...)` is the same without the new line.
* `eprint` / `eprintln` write to the error output (stderr).
* Whatever type you pass, it is turned into text: numbers, bools, arrays, maps, structs, enums, tuples...

<!-- id: printing -->
```atf
fn main() {
    print("no newline, ")
    print("then ")
    println("a newline")
    println(1, 2.5, true, "text", 'a', nil)
    println([1, 2, 3], ["a", "b"], {"k": 1}, (1, "two"))
    eprintln("this line goes to stderr")
    println()
}
```
```output
no newline, then a newline
1 2.5 true text 97 nil
[1, 2, 3] ["a", "b"] {"k": 1} (1, "two")
```

Notice that text *inside* a collection is shown with quotes, so you can tell `"1"` from `1`.

---

## 8. Making decisions: `if`

<!-- id: if -->
```atf
fn main() {
    let temp = 22
    if temp < 0 {
        println("freezing")
    } else if temp < 25 {
        println("pleasant")
    } else {
        println("hot")
    }

    // the condition must be a bool: no "truthy" numbers
    if temp % 2 == 0 and temp > 20 {
        println("even and above 20")
    }

    // `if` can also be an expression that has a value
    let kind = if temp > 20 { "warm" } else { "cool" }
    println(kind)
    let sign = if temp > 0 { 1 } else if temp < 0 { -1 } else { 0 }
    println(sign)
}
```
```output
pleasant
even and above 20
warm
1
```

Conditions must be `true` or `false`; writing `if temp { }` is a compile error. An `if` used as a value always needs an `else`.

---

## 9. Loops

### `while` and `loop`

<!-- id: while -->
```atf
fn main() {
    var n = 1
    while n < 100 {
        n *= 2
    }
    println(n)

    var i = 0
    loop {                    // loops forever until `break`
        i += 1
        if i % 2 == 0 { continue }     // skip even numbers
        if i > 7 { break }
        print(i, "")
    }
    println()
}
```
```output
128
1 3 5 7
```

(`print(i, "")` prints the number, a separating space and the empty string.)

### `for` and ranges

`a..b` counts from `a` up to `b - 1`; `a..=b` includes `b`; `step` changes the stride (a negative step counts down).

<!-- id: for -->
```atf
fn main() {
    for i in 0..5 { print(i, "") }
    println()
    for i in 1..=5 { print(i, "") }
    println()
    for i in 0..=20 step 5 { print(i, "") }
    println()
    for i in 10..0 step -3 { print(i, "") }
    println()

    var sum = 0
    for i in 1..=100 { sum += i }
    println("1 + 2 + ... + 100 =", sum)
}
```
```output
0 1 2 3 4
1 2 3 4 5
0 5 10 15 20
10 7 4 1
1 + 2 + ... + 100 = 5050
```

You can also loop over arrays, text and maps. With two variables you get the index (or the key):

<!-- id: for-collections -->
```atf
fn main() {
    let fruits = ["apple", "banana", "cherry"]
    for f in fruits { print(f, "") }
    println()
    for i, f in fruits { println("{i}: {f}") }

    for ch in "abc" { print(ch.upper(), "") }
    println()

    let ages = {"Ann": 31, "Bob": 25}
    for name, age in ages { println("{name} is {age}") }
    for (name, age) in ages { println(name.len(), age + 1) }

    let pairs = [("x", 1), ("y", 2)]
    for (label, n) in pairs { print("{label}={n} ") }
    println()
}
```
```output
apple banana cherry
0: apple
1: banana
2: cherry
A B C
Ann is 31
Bob is 25
3 32
3 26
x=1 y=2
```

Parentheses take each element apart: `for (a, b) in pairs` unpacks tuples, and on a map `for (key, value) in m`
means the same as `for key, value in m`.

Remember: `i` in `for i in 0..n` cannot be assigned to; to skip ahead use `continue`, or a `while` loop.
The end of a range is computed once, before the loop starts, and `step` must be a constant number.
Loops over sets are written `for x in my_set.items()`.

`break` and `continue` refer to the innermost loop. To leave or continue an outer loop, give it a **label**
(`name:` before `for`, `while` or `loop`) and write `break name` or `continue name`. Returning from a function
also leaves every loop at once:

<!-- id: nested-loops -->
```atf
fn find_pair(target: int) -> (int, int) {
    for a in 1..10 {
        for b in a..10 {
            if a * b == target { return (a, b) }
        }
    }
    return (-1, -1)
}

fn main() {
    println(find_pair(24), find_pair(97))
    for i in 0..3 {
        for j in 0..3 {
            if j > i { break }        // leaves only the inner loop
            print("{i}{j} ")
        }
    }
    println()

    let grid = [[1, 2, 3], [4, -5, 6], [7, 8, 9]]
    search: for r, row in grid {
        for c, v in row {
            if v < 0 {
                println("first negative at row {r}, column {c}")
                break search          // leaves both loops
            }
        }
    }
    rows: for row in grid {
        for v in row {
            if v % 2 == 0 { continue rows }    // next row
            print(v, "")
        }
    }
    println()
}
```
```output
(3, 8) (-1, -1)
00 10 11 20 21 22
first negative at row 1, column 1
1 7
```

---

## 10. Functions

<!-- id: functions -->
```atf
fn square(x: int) -> int {
    return x * x
}

fn greet(name: str) {            // no `->`: returns nothing
    println("Hello, {name}!")
}

fn main() {
    greet("Ada")
    println(square(7), square(square(2)))
}
```
```output
Hello, Ada!
49 16
```

Parameters need types; the result type follows `->`. A function that returns a value must return on **every** path.
For tiny functions there is a short form with `=>`:

<!-- id: short-fn -->
```atf
fn double(x: int) -> int => x * 2
fn max3(a: int, b: int, c: int) -> int => max(a, max(b, c))

fn main() {
    println(double(21), max3(4, 9, 6))
}
```
```output
42 9
```

### Default and named arguments

<!-- id: default-args -->
```atf
fn box(text: str, width: int = 20, fill: str = "*") -> str {
    let pad = fill.repeat(width - text.len() - 2)
    return text + " " + pad
}

fn main() {
    println(box("title"))
    println(box("title", 12))
    println(box("title", fill: "-"))
    println(box(fill: "=", text: "named", width: 10))
}
```
```output
title *************
title *****
title -------------
named ===
```

Named arguments may come in any order, but must come after the positional ones.

### Recursion and functions as values

A function can call itself. Function names are values too, with types like `fn(int) -> int`:

<!-- id: recursion -->
```atf
fn factorial(n: int) -> int {
    if n <= 1 { return 1 }
    return n * factorial(n - 1)
}

fn apply_twice(f: fn(int) -> int, x: int) -> int {
    return f(f(x))
}

fn inc(x: int) -> int { return x + 1 }

fn main() {
    println(factorial(10), factorial(20))
    println(apply_twice(inc, 5))
    println(apply_twice(factorial, 3))
}
```
```output
3628800 2432902008176640000
7
720
```

### Several results: tuples

<!-- id: multi-return -->
```atf
fn min_max(a: [int]) -> (int, int) {
    var lo = a[0]
    var hi = a[0]
    for x in a {
        if x < lo { lo = x }
        if x > hi { hi = x }
    }
    return (lo, hi)
}

fn main() {
    let (lo, hi) = min_max([5, 3, 9, 1, 7])
    println("smallest {lo}, largest {hi}")
}
```
```output
smallest 1, largest 9
```

---

## 11. Arrays

An array `[T]` holds any number of values of the same type `T` and grows when you `push`.

<!-- id: arrays -->
```atf
fn main() {
    var nums = [10, 20, 30]
    nums.push(40)
    println(nums, nums.len(), nums[0], nums[3])
    nums[1] = 25
    println(nums.pop(), nums)
    println(nums.first(), nums.last(), nums.contains(30), nums.index_of(30), nums.index_of(99))

    var words: [str] = []              // an empty array needs a type
    words.push("b")
    words.push("a")
    println(words, words.is_empty())

    nums.insert(1, 15)                 // insert before index 1
    println(nums)
    let removed = nums.remove(0)       // remove (and return) the element at index 0
    println(removed, nums)
    println(nums[1..], nums[..2], nums + [7, 8])
}
```
```output
[10, 20, 30, 40] 4 10 40
40 [10, 25, 30]
10 30 true 2 -1
["b", "a"] false
[10, 15, 25, 30]
10 [15, 25, 30]
[25, 30] [15, 25] [15, 25, 30, 7, 8]
```

Reading or writing outside the array stops the program with a clear message (there are no negative indexes):

<!-- id: bounds -->
```atf
fn main() {
    let a = [1, 2, 3]
    let i = 5
    println("before")
    println(a[i])
}
```
```error
panic: index 5 is out of range (length 3)
  at main (main.atf:5)
```

### Useful array methods

<!-- id: array-methods -->
```atf
fn main() {
    let nums = [5, 3, 8, 1, 9, 2]
    println(nums.sorted(), nums.reversed(), nums)      // these make new arrays
    println(nums.min(), nums.max(), nums.sum(), sum([1.5, 2.5]))
    println(nums.map(|x| x * 10))                      // |x| ... is a small function (section 20)
    println(nums.filter(|x| x > 4))
    println(nums.reduce(0, |acc, x| acc + x))
    println(nums.any(|x| x > 8), nums.all(|x| x > 0), nums.count(3))

    var a = [4, 2, 6]
    a.sort()                  // sort in place
    a.reverse()               // reverse in place
    println(a)

    var names = ["bob", "alice", "eve"]
    names.sort_by(|x, y| x.len() - y.len())     // custom order: negative, zero or positive
    println(names)
    println(range(5), range_from(3, 7), zip([1, 2, 3], ["a", "b", "c"]))
}
```
```output
[1, 2, 3, 5, 8, 9] [2, 9, 1, 8, 3, 5] [5, 3, 8, 1, 9, 2]
1 9 28 4.0
[50, 30, 80, 10, 90, 20]
[5, 8, 9]
28
true true 1
[6, 4, 2]
["bob", "eve", "alice"]
[0, 1, 2, 3, 4] [3, 4, 5, 6] [(1, "a"), (2, "b"), (3, "c")]
```

### Slicing arrays into pieces

`take` and `skip` cut the start of an array, `chunks` and `windows` produce arrays of arrays, `partition` splits by a test, and `unique` drops repeats.
`strip_prefix` and `strip_suffix` do the same for text and return `nil` when the text does not match, and `lcm` is the partner of `gcd`.

<!-- id: array-pieces -->
```atf
fn main() {
    let a = [1, 2, 3, 4, 5]
    println(a.take(2), a.skip(3))
    println(a.chunks(2))
    println(a.windows(3))
    let (even, odd) = a.partition(|x| x % 2 == 0)
    println(even, odd)
    println([3, 1, 3, 2, 1].unique())
    println("v1.2".strip_prefix("v") ?? "none", "a.atf".strip_suffix(".txt") ?? "none")
    println(lcm(4, 6))
}
```
```output
[1, 2] [4, 5]
[[1, 2], [3, 4], [5]]
[[1, 2, 3], [2, 3, 4], [3, 4, 5]]
[2, 4] [1, 3, 5]
[3, 1, 2]
1.2 none
12
```

### Arrays of arrays and comprehensions

<!-- id: grid -->
```atf
fn main() {
    var grid: [[int]] = []
    for y in 0..3 {
        var row: [int] = []
        for x in 0..4 { row.push(x * y) }
        grid.push(row)
    }
    grid[2][3] = 100
    println(grid)
    println(grid[2][3], grid[1].len())

    // a list comprehension builds an array from a loop
    let squares = [x * x for x in 1..=6]
    let evens = [x for x in 0..20 if x % 2 == 0]
    println(squares, evens)

    // array_make creates an array of zeros (or false, or empty text...)
    let zeros = array_make::<int>(5)
    println(zeros)
}
```
```output
[[0, 0, 0, 0], [0, 1, 2, 3], [0, 2, 4, 100]]
100 4
[1, 4, 9, 16, 25, 36] [0, 2, 4, 6, 8, 10, 12, 14, 16, 18]
[0, 0, 0, 0, 0]
```

Like structs, **arrays are references**: `let b = a` makes `b` another name for the same array. Use `a.copy()`
(or `copy(a)`) for an independent copy. `let` only stops you from pointing the name at another array; you can still `push` to it.

---

## 12. List comprehensions

A **list comprehension** builds a new array from a loop in a single expression:
`[expression for name in collection]`, optionally followed by `if condition` to keep only some elements.
It works with everything a `for` loop can walk over: ranges (also with `step`), arrays, text and maps,
and with two names you get the index (or the key) too.

<!-- id: comprehensions -->
```atf
fn main() {
    let nums = [3, 8, 1, 9, 4]
    println([n * 2 for n in nums])
    println([n for n in nums if n > 3])
    println([x for x in 10..=0 step -5])
    println(["{i}:{w}" for i, w in ["a", "b", "c"]])
    println([c.upper() for c in "hey"])

    let prices = {"tea": 3, "cake": 5}
    println([name for name, p in prices if p > 4])

    // nested comprehensions build a table
    let table = [[row * col for col in 1..=4] for row in 1..=3]
    println(table)

    // every pair (a, b) with a < b
    var pairs: [(int, int)] = []
    for a in 1..=3 {
        pairs.extend([(a, b) for b in (a + 1)..=3])
    }
    println(pairs)

    let words = "the quick brown fox".split(" ")
    println([w.len() for w in words].sum(), [w for w in words if "o" in w])
}
```
```output
[6, 16, 2, 18, 8]
[8, 9, 4]
[10, 5, 0]
["0:a", "1:b", "2:c"]
["H", "E", "Y"]
["cake"]
[[1, 2, 3, 4], [2, 4, 6, 8], [3, 6, 9, 12]]
[(1, 2), (1, 3), (2, 3)]
16 ["brown", "fox"]
```

A comprehension is the same as an empty array plus a `for` loop with `push`, so it is just as fast.
The element type comes from the expression before `for`; if the variable has a declared type, it is used instead,
e.g. `let as_floats: [float] = [n for n in 1..4]` gives `[1.0, 2.0, 3.0]`.

---

## 13. Maps

A map `{K: V}` connects keys to values. It remembers the order in which keys were first added.

<!-- id: maps -->
```atf
fn main() {
    var ages = {"Ann": 31, "Bob": 25}
    ages["Cy"] = 40                   // add
    ages["Bob"] = 26                  // change
    println(ages, ages.len())
    println(ages["Ann"], ages.get("Zed", -1), ages.try_get("Zed"))
    println("Ann" in ages, ages.has("Zed"), "Zed" in ages)
    println(ages.keys(), ages.values())
    println(ages.remove("Bob"), ages.remove("Bob"), ages)

    for name, age in ages {
        println("{name} -> {age}")
    }
    for pair in ages.items() {
        println(pair)
    }
}
```
```output
{"Ann": 31, "Bob": 26, "Cy": 40} 3
31 -1 nil
true false false
["Ann", "Bob", "Cy"] [31, 26, 40]
true false {"Ann": 31, "Cy": 40}
Ann -> 31
Cy -> 40
("Ann", 31)
("Cy", 40)
```

A missing key stops the program, so use `get(key, default)`, `try_get(key)` (returns an optional) or `key in map` first.

### Example: counting words

<!-- id: word-count -->
```atf
fn main() {
    let text = "the cat and the hat and the bat"
    var counts: {str: int} = {}
    for word in text.split(" ") {
        counts[word] = counts.get(word, 0) + 1
    }
    println(counts)

    // sort the entries by count, biggest first
    var entries = counts.items()
    entries.sort_by(|a, b| b.1 - a.1)
    println(entries[0], entries[1])
}
```
```output
{"the": 3, "cat": 1, "and": 2, "hat": 1, "bat": 1}
("the", 3) ("and", 2)
```

Keys can be ints, text, tuples, structs, enums... anything that can be compared with `==`.

---

## 14. Sets

A set holds each value at most once. You create one with `set_new::<T>()`.

<!-- id: sets -->
```atf
fn main() {
    let seen = set_new::<int>()
    for x in [3, 1, 3, 2, 1, 3] {
        seen.add(x)
    }
    println(seen.len(), seen.items(), seen.has(2), seen.has(9), 3 in seen)
    println(seen.remove(1), seen.items())

    // remove duplicates, keep the order
    let used = set_new::<str>()
    var unique: [str] = []
    for w in ["a", "b", "a", "c", "b"] {
        if not used.has(w) {
            used.add(w)
            unique.push(w)
        }
    }
    println(unique)
}
```
```output
3 [3, 1, 2] true false true
true [3, 2]
["a", "b", "c"]
```

---

## 15. Tuples

A tuple groups a few values of different types. Fields are numbered from 0:

<!-- id: tuples -->
```atf
fn main() {
    let person = ("Ada", 36, true)
    println(person, person.0, person.1, person.2)

    let (name, age, _) = person         // unpack into variables
    println("{name} is {age}")

    var pairs = [(2, "b"), (3, "c"), (1, "a")]
    pairs.sort()                        // tuples compare field by field
    println(pairs)

    let (a, b) = (1, 2)
    println(b, a)
}
```
```output
("Ada", 36, true) Ada 36 true
Ada is 36
[(1, "a"), (2, "b"), (3, "c")]
2 1
```

Tuples cannot be changed after they are created (`person.0 = 5` is an error). Use a struct when you want named, changeable fields.

---

## 16. Structs and methods

A **struct** groups named fields into your own type.

<!-- id: structs -->
```atf
struct Point {
    x: int,
    y: int
}

fn main() {
    let p = Point(3, 4)                  // positional
    let q = Point{ x: 1, y: 2 }          // or by name
    println(p, q)
    println(p.x + q.x, p.y + q.y)
    p.x = 10                             // fields can be changed, even through a `let`
    println(p)
    println(p == Point(10, 4), p == q)   // == compares the contents
}
```
```output
Point{x: 3, y: 4} Point{x: 1, y: 2}
4 6
Point{x: 10, y: 4}
true false
```

**Structs are references.** An assignment does not copy the struct; both names refer to the same object.
`copy(x)` makes an independent copy, `==` compares contents and `same(a, b)` asks "are these the very same object?":

<!-- id: struct-ref -->
```atf
struct Counter { value: int }

fn bump(c: Counter) {
    c.value += 1                 // changes the caller's object
}

fn main() {
    let a = Counter(0)
    let b = a                    // b is another name for the same object
    bump(a)
    bump(b)
    println(a.value, b.value)

    let c = copy(a)              // an independent copy
    bump(c)
    println(a.value, c.value)
    println(a == b, same(a, b), same(a, c), a == Counter(2))
}
```
```output
2 2
2 3
true true false true
```

A field can have a **default value**. Fields with defaults may be left out when the struct is created by name:

<!-- id: struct-defaults -->
```atf
struct Settings {
    width: int = 80,
    height: int = 24,
    title: str = "untitled",
    tags: [str] = []
}

fn main() {
    let a = Settings{}
    let b = Settings{ title: "report", width: 120 }
    println(a)
    println(b.title, b.width, b.height)
}
```
```output
Settings{width: 80, height: 24, title: "untitled", tags: []}
report 120 24
```

### Methods

Methods live in an `impl` block. The first parameter `self` is the object; a function without `self` is a *static* function,
called with the type name (`Rect.square(3)`).

<!-- id: methods -->
```atf
struct Rect {
    w: float,
    h: float
}

impl Rect {
    fn square(side: float) -> Rect {          // static: Rect.square(...)
        return Rect(side, side)
    }

    fn area(self) -> float {
        return self.w * self.h
    }

    fn scale(self, k: float) {                // changes the object
        self.w *= k
        self.h *= k
    }

    fn to_str(self) -> str {                  // used by println and "{...}"
        return "{self.w} x {self.h}"
    }
}

fn main() {
    let r = Rect(3.0, 4.0)
    println(r, r.area())
    r.scale(2.0)
    println(r, r.area())
    let s = Rect.square(5.0)
    println("square: {s}, area {s.area()}")
    println([r, s])
}
```
```output
3.0 x 4.0 12.0
6.0 x 8.0 48.0
square: 5.0 x 5.0, area 25.0
[6.0 x 8.0, 5.0 x 5.0]
```

### Operator overloading

Methods with special names make your type work with operators:

| method | operator | method | operator |
|---|---|---|---|
| `op_add` | `a + b` | `op_neg` | `-a` |
| `op_sub` | `a - b` | `op_index` | `a[i]` |
| `op_mul` | `a * b` | `op_set_index` | `a[i] = v` |
| `op_div` | `a / b` | `op_slice` | `a[lo..hi]` |
| `op_mod` | `a % b` | `op_contains` | `x in a` |
| `op_pow` | `a ** b` | `eq` | `==`, `!=` (default: compare all fields) |
| `op_and` `op_or` `op_xor` | `&` `\|` `^` | `cmp` | `<` `>` `<=` `>=`, `sort()` (negative, 0 or positive) |
| `op_shl` `op_shr` `op_ushr` | `<<` `>>` `>>>` | `to_str` | `println`, `str(x)`, `"{x}"` |

The right-hand side of a binary operator method can be any type you like (`op_mul(self, k: float)` below).

<!-- id: operators-overload -->
```atf
struct Vec2 {
    x: float,
    y: float
}

impl Vec2 {
    fn op_add(self, o: Vec2) -> Vec2 { return Vec2(self.x + o.x, self.y + o.y) }
    fn op_mul(self, k: float) -> Vec2 { return Vec2(self.x * k, self.y * k) }
    fn op_neg(self) -> Vec2 { return Vec2(-self.x, -self.y) }
    fn length(self) -> float { return sqrt(self.x * self.x + self.y * self.y) }
}

struct Money { cents: int }

impl Money {
    fn cmp(self, o: Money) -> int { return self.cents - o.cents }
}

fn main() {
    let a = Vec2(1.0, 2.0)
    let b = Vec2(3.0, 4.0)
    println(a + b, a * 3.0, -a, b.length())
    println(Money(500) < Money(700), Money(500) >= Money(700), Money(5) == Money(5))
}
```
```output
Vec2{x: 4.0, y: 6.0} Vec2{x: 3.0, y: 6.0} Vec2{x: -1.0, y: -2.0} 5.0
true false true
```

Indexing, `in` and printing can be overloaded the same way. Here is a tiny grid type:

<!-- id: operators-index -->
```atf
struct Grid {
    w: int,
    cells: [int]
}

impl Grid {
    fn new(w: int, h: int) -> Grid { return Grid(w, array_make::<int>(w * h)) }
    fn op_index(self, p: (int, int)) -> int { return self.cells[p.1 * self.w + p.0] }
    fn op_set_index(self, p: (int, int), v: int) { self.cells[p.1 * self.w + p.0] = v }
    fn op_contains(self, v: int) -> bool { return self.cells.contains(v) }
    fn to_str(self) -> str {
        var rows: [str] = []
        for y in 0..self.cells.len() / self.w {
            rows.push(" ".join([str(self[(x, y)]) for x in 0..self.w]))
        }
        return "\n".join(rows)
    }
}

fn main() {
    let g = Grid.new(3, 2)
    g[(1, 0)] = 5
    g[(2, 1)] = 7
    println(g[(1, 0)], 7 in g, 9 in g)
    println(g)
}
```
```output
5 true false
0 5 0
0 0 7
```

---

## 17. Enums and `match`

An **enum** is a type with a fixed set of possibilities (variants). Variants may carry data.

<!-- id: enums -->
```atf
enum Direction { North, East, South, West }

enum Shape {
    Circle(float),                 // radius
    Rect(float, float),            // width, height
    Point                          // no data
}

fn describe(s: Shape) -> str {
    return match s {
        Shape.Circle(r) => "circle of radius {r}"
        Shape.Rect(w, h) => "rectangle {w} x {h}"
        Shape.Point => "just a point"
    }
}

fn main() {
    let d = Direction.East
    println(d, d == Direction.East, d == Direction.West)
    println(describe(Shape.Circle(1.5)))
    println(describe(Shape.Rect(2.0, 3.0)))
    println(describe(Shape.Point))
    println(Shape.Rect(2.0, 3.0))
}
```
```output
Direction.East true false
circle of radius 1.5
rectangle 2.0 x 3.0
just a point
Shape.Rect(2.0, 3.0)
```

`match` checks the value against *patterns* from top to bottom and runs the first arm that fits.
For an enum the compiler makes sure **every variant is handled**:

<!-- id: match-exhaustive -->
```atf
enum Color { Red, Green, Blue }

fn announce(c: Color) {
    match c {
        Color.Red => println("red")
        Color.Green => println("green")
    }
}

fn main() {
    announce(Color.Red)
}
```
```error
error: this match does not cover: Color.Blue
  --> main.atf:4:5
 4 |     match c {
   |     ^
  hint: add the missing cases or a catch-all arm:  _ => ...
```

### More patterns

`match` also works on numbers, text, bools and tuples. You can combine patterns with `|`, use ranges (`a..=b`),
add a guard with `if`, bind a name, and use `_` for "anything":

<!-- id: match-patterns -->
```atf
fn classify(n: int) -> str {
    return match n {
        0 => "zero"
        1 | 2 | 3 => "small"
        4..=9 => "medium"
        x if x < 0 => "negative ({x})"
        _ => "large"
    }
}

fn fizz(n: int) -> str {
    return match (n % 3, n % 5) {
        (0, 0) => "FizzBuzz"
        (0, _) => "Fizz"
        (_, 0) => "Buzz"
        _ => str(n)
    }
}

fn main() {
    for n in [0, 2, 7, -5, 100] { println(n, classify(n)) }
    println([fizz(3), fizz(5), fizz(15), fizz(7)])

    let command = "stop"
    match command {
        "go" => println("going")
        "stop" | "halt" => println("stopping")
        _ => println("unknown")
    }
}
```
```output
0 zero
2 small
7 medium
-5 negative (-5)
100 large
["Fizz", "Buzz", "FizzBuzz", "7"]
stopping
```

**Structs** can be taken apart in a pattern too: either positionally, like the constructor call `P(x, y)`, or by
field name with `P{ x: pattern, y }` (a bare field name binds that field; fields you leave out match anything,
and you may write `..` to say so). Struct patterns nest and work in `if let`:

<!-- id: struct-patterns -->
```atf
struct Point { x: int, y: int }

fn where_is(p: Point) -> str {
    return match p {
        Point(0, 0) => "the origin"
        Point{ x: 0, y } => "on the y axis at {y}"
        Point{ y: 0, .. } => "on the x axis"
        Point(x, y) if x == y => "on the diagonal"
        _ => "somewhere else"
    }
}

fn main() {
    for p in [Point(0, 0), Point(0, 4), Point(7, 0), Point(3, 3), Point(1, 2)] {
        println(where_is(p))
    }
    if let Point{ x: 1, y } = Point(1, 42) { println("x is 1 and y is", y) }
}
```
```output
the origin
on the y axis at 4
on the x axis
on the diagonal
somewhere else
x is 1 and y is 42
```

Enums can be given numbers, and turned into ints with `int(...)`. Enums can also have methods, like structs:

<!-- id: enum-methods -->
```atf
enum Level { Low = 1, Mid = 5, High = 10 }

impl Level {
    fn is_urgent(self) -> bool {
        return self == Level.High
    }
}

fn main() {
    println(Level.Mid, int(Level.High), Level.High.is_urgent())
}
```
```output
Level.Mid 10 true
```

### Arms, `if let` and a few conveniences

* An arm can be an expression, a block `{ ... }`, an assignment, or `return` / `break` / `continue`.
* Inside a `match` on an enum you may leave out the type name: `Circle(r)` instead of `Shape.Circle(r)`.
* `if let Pattern = value { ... }` runs the block only when the pattern fits (and binds its names); `while let` repeats it.
* Patterns nest: `Expr.Add(Expr.Num(0), rhs)`.

<!-- id: match-more -->
```atf
enum Expr {
    Num(int),
    Add(Expr, Expr),
    Mul(Expr, Expr)
}

fn eval(e: Expr) -> int {
    return match e {
        Num(n) => n
        Add(a, b) => eval(a) + eval(b)
        Mul(a, b) => eval(a) * eval(b)
    }
}

fn simplify(e: Expr) -> Expr {
    match e {
        Expr.Add(Expr.Num(0), rhs) => return simplify(rhs)
        Expr.Mul(Expr.Num(1), rhs) => return simplify(rhs)
        _ => return e
    }
}

fn main() {
    let e = Expr.Add(Expr.Num(2), Expr.Mul(Expr.Num(3), Expr.Num(4)))
    println(eval(e))
    println(simplify(Expr.Add(Expr.Num(0), Expr.Mul(Expr.Num(1), Expr.Num(9)))))

    if let Expr.Add(left, _) = e {
        println("an addition whose left side is", left)
    }

    var steps = 0
    var n = 27
    loop {
        match n {
            1 => break
            x if x % 2 == 0 => n = x / 2
            x => {
                n = 3 * x + 1
            }
        }
        steps += 1
    }
    println("27 reaches 1 after", steps, "steps")
}
```
```output
14
Expr.Num(9)
an addition whose left side is Expr.Num(2)
27 reaches 1 after 111 steps
```

A `match` that is used as a value must cover every case (the compiler checks it). A `match` used as a statement on
numbers or text may leave cases out; then nothing happens for them.

---

## 18. Optionals: values that may be `nil`

`T?` means "a `T`, or `nil` (nothing)". Many functions use this: `"x".parse_int()` returns `int?`.
The compiler will not let you use an optional as if it were a plain value, so you cannot forget to check:

<!-- id: optionals -->
```atf
fn find(a: [int], x: int) -> int? {
    for i in 0..a.len() {
        if a[i] == x { return i }
    }
    return nil
}

fn main() {
    let a = [4, 8, 15, 16]
    let i = find(a, 15)
    println(i, find(a, 99))

    println(i == nil, find(a, 99) == nil)
    println(i! + 100)                // x!  unwraps: stops the program if it is nil
    println(find(a, 99) ?? -1)       // x ?? d  means "x, or d if x is nil"

    if let pos = find(a, 16) {       // runs only if there is a value, and names it
        println("found at {pos}")
    } else {
        println("not found")
    }
}
```
```output
2 nil
false true
102
-1
found at 3
```

`while let` repeats while a value is present — handy for linked structures:

<!-- id: while-let -->
```atf
struct Node {
    value: int,
    next: Node?
}

fn main() {
    let list = Node(1, Node(2, Node(3, nil)))
    var cur: Node? = list
    var total = 0
    while let n = cur {
        total += n.value
        cur = n.next
    }
    println("total", total)
}
```
```output
total 6
```

Using `!` on `nil` stops the program with a message; the compiler also tells you when you forget to unwrap:

<!-- id: optional-error -->
```atf
fn main() {
    let n = "12".parse_int()
    println(n + 1)
}
```
```error
error: cannot apply '+' to int? and int
  --> main.atf:3:15
 3 |     println(n + 1)
   |               ^
```

---

## 19. `Result` and the `?` operator

For operations that can fail **with a reason**, use `Result<T, E>`: either `Result.Ok(value)` or `Result.Err(error)`.
Put `?` after a call to either get the value or return the error from your own function immediately.

<!-- id: result -->
```atf
fn parse_age(s: str) -> Result<int, str> {
    let n = s.parse_int()
    if n == nil { return Result.Err("'{s}' is not a number") }
    if n! < 0 { return Result.Err("age cannot be negative") }
    return Result.Ok(n!)
}

fn total_age(a: str, b: str) -> Result<int, str> {
    let x = parse_age(a)?          // on Err, return that Err from total_age
    let y = parse_age(b)?
    return Result.Ok(x + y)
}

fn main() {
    println(total_age("30", "12"))
    println(total_age("30", "old"))
    println(total_age("-1", "12"))

    match total_age("5", "6") {
        Result.Ok(v) => println("sum is {v}")
        Result.Err(e) => println("failed: {e}")
    }
    println(parse_age("42").unwrap_or(0), parse_age("x").unwrap_or(0))
    println(parse_age("42").is_ok(), parse_age("x").is_err())
}
```
```output
Result.Ok(42)
Result.Err("'old' is not a number")
Result.Err("age cannot be negative")
sum is 11
42 0
true true
```

`?` also works on optionals inside a function that returns an optional: it returns `nil` early.

<!-- id: question-opt -->
```atf
fn first_word(s: str) -> str? {
    let words = s.split_whitespace()
    if words.len() == 0 { return nil }
    return words[0]
}

fn shout(s: str) -> str? {
    let w = first_word(s)?               // returns nil if there is no word
    return w.upper() + "!"
}

fn main() {
    println(shout("hello there"), shout("   "))     // an optional str is printed with quotes
}
```
```output
"HELLO!" nil
```

---

## 20. Closures and higher-order functions

A **lambda** is a small unnamed function written `|parameters| expression`, or with a block `|x| { ... }`.
It can use variables from the place where it was written (it *closes over* them), and it can even change them.

<!-- id: closures -->
```atf
fn make_counter() -> fn() -> int {
    var n = 0
    return || {
        n += 1
        return n
    }
}

fn make_adder(k: int) -> fn(int) -> int {
    return |x| x + k
}

fn main() {
    let next = make_counter()
    println(next(), next(), next())
    let other = make_counter()          // has its own n
    println(other())

    let add5 = make_adder(5)
    println(add5(1), add5(10))

    var total = 0
    let add_to_total = |x: int| { total += x }
    for i in 1..=4 { add_to_total(i) }
    println(total)
}
```
```output
1 2 3
1
6 15
10
```

Functions that take functions are called *higher-order*. The array methods `map`, `filter`, `reduce`, `any`, `all`,
`find`, `sort_by` and `for_each` are the everyday examples:

<!-- id: higher-order -->
```atf
fn compose(f: fn(int) -> int, g: fn(int) -> int) -> fn(int) -> int {
    return |x| g(f(x))
}

fn main() {
    let nums = [1, 2, 3, 4, 5, 6]
    let evens = nums.filter(|n| n % 2 == 0)
    let squares = evens.map(|n| n * n)
    let total = squares.reduce(0, |acc, n| acc + n)
    println(evens, squares, total)

    println(nums.find(|n| n > 3), nums.find(|n| n > 30))
    nums.for_each(|n| print(n * 10, ""))
    println()

    let inc_then_double = compose(|x| x + 1, |x| x * 2)
    println(inc_then_double(5))

    var people = [("Zoe", 31), ("Adam", 25), ("Mia", 31)]
    people.sort_by(|a, b| if a.1 != b.1 { a.1 - b.1 } else { str_cmp(a.0, b.0) })
    println(people)
}
```
```output
[2, 4, 6] [4, 16, 36] 56
4 nil
10 20 30 40 50 60
12
[("Adam", 25), ("Mia", 31), ("Zoe", 31)]
```

---

## 21. Generics and interfaces

A **generic** function or type works for many types. Type parameters are written in `< >`.
The compiler creates a separate, fully optimized version for each type you actually use.

<!-- id: generic-fn -->
```atf
fn first_or<T>(a: [T], default: T) -> T {
    if a.len() == 0 { return default }
    return a[0]
}

fn largest<T>(a: [T]) -> T {
    var best = a[0]
    for x in a {
        if x > best { best = x }
    }
    return best
}

fn swap_pair<A, B>(p: (A, B)) -> (B, A) {
    return (p.1, p.0)
}

fn main() {
    println(first_or([7, 8], 0), first_or(["x"], "none"))
    println(first_or([] as [int], -1))
    println(largest([3, 9, 4]), largest([2.5, 1.5]), largest(["pear", "apple", "zebra"]))
    println(swap_pair((1, "one")))
}
```
```output
7 x
-1
9 2.5 zebra
("one", 1)
```

Generic structs and `impl<T>` blocks:

<!-- id: generic-struct -->
```atf
struct Stack<T> {
    items: [T]
}

impl<T> Stack<T> {
    fn new() -> Stack<T> {
        return Stack{ items: [] }
    }
    fn push(self, x: T) { self.items.push(x) }
    fn pop(self) -> T? {
        if self.items.len() == 0 { return nil }
        return self.items.pop()
    }
    fn size(self) -> int { return self.items.len() }
}

struct Pair<A, B> { first: A, second: B }

fn main() {
    let numbers: Stack<int> = Stack.new()
    numbers.push(1)
    numbers.push(2)
    println(numbers.size(), numbers.pop(), numbers.pop(), numbers.pop())

    let words = Stack::<str>{ items: ["a", "b"] }
    println(words.pop())

    let p = Pair(1, "one")             // Pair<int, str> is inferred
    println(p, p.first, p.second)
}
```
```output
2 2 1 nil
"b"
Pair{first: 1, second: "one"} 1 one
```

When the compiler cannot work out a type parameter it asks for help, e.g. `Stack.new()` needs the annotation `let s: Stack<int>`,
and `set_new::<int>()` gets its type with `::<int>`.

A generic function may use any operation on `T` (like `>` in `largest`). There is no separate list of requirements:
the compiler checks the body again for every type you call it with. So `largest` works for numbers and text, and for a struct
only if that struct has a `cmp` method — otherwise you get an error such as
`values of type Point cannot be ordered with < > <= >=`.

### Interfaces

An **interface** names a set of methods. Any type that has those methods (with the same parameter and result types)
can be used where the interface is expected — you do not have to declare that it "implements" it. This lets one
array hold different types, and one function work with all of them:

<!-- id: interfaces -->
```atf
interface Shape {
    fn area(self) -> float
    fn name(self) -> str
}

struct Circle { r: float }
impl Circle {
    fn area(self) -> float { return PI * self.r * self.r }
    fn name(self) -> str { return "circle" }
}

struct Rect { w: float, h: float }
impl Rect {
    fn area(self) -> float { return self.w * self.h }
    fn name(self) -> str { return "rectangle" }
}

fn total_area(shapes: [Shape]) -> float {
    var t = 0.0
    for s in shapes { t += s.area() }
    return t
}

fn main() {
    let shapes: [Shape] = [Circle(1.0), Rect(2.0, 3.0)]
    for s in shapes { println("{s.name()}: {s.area():.2}") }
    println("total {total_area(shapes):.2}")
}
```
```output
circle: 3.14
rectangle: 6.00
total 9.14
```

If a type does not fit, the compiler says which method is missing or has the wrong type.

---

## 22. When things go wrong

There are three kinds of problems:

1. **Compile errors**: the compiler finds a mistake before the program runs (you have seen several above).
2. **Expected failures**: handled in your code with `nil` and `Result` (sections 18 and 19).
3. **Bugs** (impossible situations): the program stops with a *panic* and a short call trace.

### panic and assert

<!-- id: panic -->
```atf
fn withdraw(balance: int, amount: int) -> int {
    assert(amount > 0, "amount must be positive")
    if amount > balance {
        panic("insufficient funds: need {amount}, have {balance}")
    }
    return balance - amount
}

fn main() {
    println(withdraw(100, 30))
    println(withdraw(100, 300))
    println("never reached")
}
```
```error
panic: insufficient funds: need 300, have 100
  at withdraw (main.atf:4)
  at main (main.atf:11)
```

The trace lists the functions that were running, innermost first. The program ends with exit code 1.
Other runtime errors work the same way: index out of range, division by zero, a missing map key, `!` on `nil`.

### catch_panic: recovering

`catch_panic(f)` runs the function `f` (it takes no arguments and returns nothing). If anything inside it panics —
`panic`, a failed `assert`, a bad index, division by zero, a missing key, `!` on `nil` — you get the message back as a
`str?` and the program carries on; if all is well you get `nil`.

<!-- id: catch-panic -->
```atf
fn main() {
    var zero = 0
    let msg = catch_panic(|| { println(10 / zero) })
    println("caught:", msg)

    let ok = catch_panic(|| { println("this is fine") })
    println("caught:", ok)

    // a typical use: try something that may fail, and keep the result in an outer variable
    var parsed = 0
    let err = catch_panic(|| { parsed = "12x".to_int() })
    println(parsed, err ?? "no error")
    let err2 = catch_panic(|| { assert(parsed > 0, "parsed must be positive") })
    println(err2!)
}
```
```output
caught: "division by zero"
this is fine
caught: nil
0 cannot convert "12x" to an int
parsed must be positive
```

Use `catch_panic` sparingly — for example to keep a long-running program alive when one task fails.
For failures you expect, `nil` and `Result` are clearer.

### try / catch

`try { ... } catch err { ... }` is the same thing as a statement: if the try block panics, the catch block runs
with the message in `err` (a `str`); otherwise it is skipped. The name after `catch` is optional.

<!-- id: try-catch -->
```atf
fn main() {
    var total = 0
    for text in ["10", "x7", "5"] {
        try {
            total += text.to_int()
        } catch err {
            println("skipped: {err}")
        }
    }
    println("total {total}")

    try {
        assert(total > 100, "total is too small")
    } catch {
        println("the catch name is optional")
    }
}
```
```output
skipped: cannot convert "x7" to an int
total 15
the catch name is optional
```

The try block runs as a closure, so `return`, and a `break` or `continue` aimed at a loop outside the try,
are compile errors inside it: set a variable and act on it after the try. `try` and `catch` are not reserved
words, so older code that uses them as names still compiles.

### defer: cleanup code

`defer statement` runs the statement when the **block** it is written in ends: at its closing `}`, or earlier through
`return`, `break` or `continue`. In a function body this means "when the function returns"; inside a loop it runs at the end of
every iteration. Several defers run in reverse order. The statement can also be a block: `defer { ... }`.

<!-- id: defer -->
```atf
fn work(fail: bool) -> int {
    defer println("  cleanup A")
    defer println("  cleanup B")
    println("  working")
    if fail { return -1 }
    return 1
}

fn main() {
    println(work(false))
    println(work(true))
}
```
```output
  working
  cleanup B
  cleanup A
1
  working
  cleanup B
  cleanup A
-1
```

<!-- id: defer-loop -->
```atf
fn main() {
    for i in 0..3 {
        defer println("  end of round", i)
        if i == 1 { continue }
        println("round", i)
    }
    {
        defer { println("leaving the block") }
        println("inside the block")
    }
    println("done")
}
```
```output
round 0
  end of round 0
  end of round 1
round 2
  end of round 2
inside the block
leaving the block
done
```

> **Note:** a panic does not run pending `defer` statements — neither when the program stops nor when the panic is
> caught by `catch_panic`. Use `defer` for normal cleanup, not for recovering from bugs.

---

## 23. Reading a traceback

When a program panics it prints the message and then a **traceback**: one line per function that was running,
innermost first, with the file and the line number. Methods are shown as `Type.method` and lambdas as `lambda@LINE`
(the line where the lambda was written). Functions of the standard library are left out, so you only see your own code.

<!-- id: traceback -->
```atf
struct Account {
    owner: str,
    balance: int
}

impl Account {
    fn withdraw(self, amount: int) {
        if amount > self.balance {
            panic("{self.owner} cannot withdraw {amount}, balance is {self.balance}")
        }
        self.balance -= amount
    }
}

fn pay_all(acc: Account, bills: [int]) {
    bills.for_each(|b| acc.withdraw(b))
}

fn main() {
    let acc = Account("Dana", 100)
    pay_all(acc, [30, 50, 40])
}
```
```error
panic: Dana cannot withdraw 40, balance is 20
  at Account.withdraw (main.atf:9)
  at lambda@16 (main.atf:16)
  at pay_all (main.atf:16)
  at main (main.atf:21)
```

Read it from the top: the panic happened on line 9 inside `Account.withdraw`, which was called by the lambda on line 16,
which `for_each` (library code, not shown) called for each bill, inside `pay_all`, called from `main` on line 21.

* The program stops with **exit code 1**; output printed before the panic is kept.
* Very deep tracebacks (recursion) show the first 30 lines and then `... and N more calls`.
* Without a traceback: **infinite recursion** overflows the machine stack and Windows ends the program without a message
  (exit code -1073741571), and text that was printed just before may be lost because output is buffered.
  If a program "silently stops", look for a function that calls itself without end.

---

## 24. Input, output and files

### Reading from the keyboard

`input(prompt)` reads a line (an empty text at the end of the input). `read_line()` returns `str?` and gives `nil` when the input is
finished, which is the way to read "everything":

<!-- id: input -->
```atf
fn main() {
    let name = input("your name? ")
    println("Hello, {name}!")

    var total = 0
    loop {
        let line = read_line()
        if line == nil { break }
        let n = line!.trim().parse_int()
        if n == nil {
            println("skipping '{line!}'")
            continue
        }
        total += n!
    }
    println("total = {total}")
}
```
```input
Ada
10
20
oops
30
```
```output
your name? Hello, Ada!
skipping 'oops'
total = 60
```

(When you run this yourself, type the lines and finish with Ctrl+Z then Enter, or feed a file: `atf run prog.atf < numbers.txt`.)
`read_all_stdin()` returns all remaining input as one text. Output is buffered for speed and flushed automatically
when the program ends, when it reads input, and when it writes to stderr; call `flush()` to force it (for example before a long computation).

### Files

`write_file(path, text)` returns `true` on success. `read_file(path)` returns the contents as `str?` (`nil` if it cannot be read).
`file_exists`, `delete_file` and `make_dir` do what their names say.

<!-- id: files -->
```atf
fn main() {
    let path = temp_dir() + "atf_tutorial_demo.txt"
    println(write_file(path, "first line\nsecond line\n"))

    let content = read_file(path)
    if content == nil {
        println("cannot read")
        return
    }
    for line in content!.lines() {
        println("> {line}")
    }
    println(file_exists(path), delete_file(path), file_exists(path))
    println(read_file(path))
}
```
```output
true
> first line
> second line
true true false
nil
```

### Command line arguments

`main` may take the arguments as `[str]` and may return an `int`, which becomes the exit code of the program.

<!-- id: args -->
```atf
fn main(args: [str]) -> int {
    println("got {args.len()} arguments")
    for i, a in args { println("  {i}: {a}") }
    if args.len() > 0 and args[0] == "--fail" { return 3 }
    return 0
}
```
```output
got 0 arguments
```

Run it with `atf run prog.atf one "two words"` to see the arguments (`args` does not contain the program name; quotes group words).
`getenv("PATH")` returns an environment variable (or `nil`), and `exit(code)` ends the program at once.
`run_command("cmd /c dir")` and `run_process("prog.exe", ["arg"])` start another program, wait for it and return its exit code.

### Building a whole command-line program

Four modules give a program the pieces Python programmers know: `std/args` (like `argparse`), `std/log` (like `logging`),
`std/text` (like `textwrap` and `string.Template`) and `std/math` (like `math` and `statistics`).
A real program passes `main`'s `args` to `parse_or_exit`; this sample passes a list so that it can run anywhere.

<!-- id: tools -->
```atf
import "std/args"
import "std/log"
import "std/text"
import "std/math"

fn main() {
    let p = args_parser("stats", "Summarises numbers")
    p.flag("verbose", "v", "explain what happens")
    p.option("title", "t", "heading", "Report")
    p.positional("numbers", "comma separated numbers")
    let a = p.parse_or_exit(["-v", "--title=sales", "3,1,4,1,5"])   // real code: p.parse_or_exit(args)

    log_to_stdout(true)                       // log lines go to standard error by default
    if a.flag("verbose") { log_set_level(LOG_DEBUG) }
    log_debug("parsing {a.get("numbers")}")

    var nums: [float] = []
    for part in a.get("numbers").split(",") { nums.push(part.to_float()) }
    println(text_title(a.get("title")))
    print(text_table([
        ["mean", fmt_fixed(stats_mean(nums), 2)],
        ["median", fmt_fixed(stats_median(nums), 2)],
        ["max", fmt_fixed(nums.max(), 2)],
    ]))
    println(text_snake_case("MeanOfNumbers"), math_primes(20).len())
}
```
```output
DEBUG parsing 3,1,4,1,5
Sales
mean    2.80
median  3.00
max     5.00
mean_of_numbers 8
```

`--help` prints the usage that `args_parser` built from your declarations, and a mistake such as an unknown option prints a message
and exits with code 2. `std/text` also has `text_wrap`, `text_template` (`${name}` placeholders), `text_distance` for
"did you mean ...?" and the case converters; `std/math` has `math_is_prime`, `math_mod_pow`, `stats_stdev` and more. `std/algo` collects algorithms from C++ (`algo_lower_bound`,
`algo_next_permutation`), Python's itertools (`algo_combinations`, `algo_product`) and JavaScript (`algo_group_by`, `algo_flatten`, `algo_union`). `std/random` adds Python's `random` extras (`random_sample`, `random_weighted`,
`random_gauss`, `random_uuid`) and `std/bits` the bit tricks of C++ (`bits_rotl`, `bits_is_power_of_two`, `bits_to_str`).
Every function is listed in [STDLIB.md](STDLIB.md).

### Time and random numbers

<!-- id: random -->
```atf
fn main() {
    rand_seed(42)                          // a fixed seed gives the same numbers every run
    let d = rand_int(1, 6)                 // both ends included
    println(d >= 1 and d <= 6, rand_float() < 1.0)
    let names = ["Ann", "Bob", "Cy"]
    println(names.contains(rand_choice(names)))
    let deck = [1, 2, 3, 4, 5]
    shuffle(deck)                          // shuffles in place
    println(deck.sorted())

    let start = clock()                    // seconds, as a float
    var x = 0
    for i in 0..1000000 { x += i }
    println(x, clock() - start < 1.0)
}
```
```output
true true
true
[1, 2, 3, 4, 5]
499999500000 true
```

Without `rand_seed` the numbers are different each time.

---

## 25. Modules: `import`

Large programs can be split over several files. `import "path"` loads another `.atf` file (the path is relative to the
importing file, and the `.atf` ending may be left out). All the functions, types, constants and global variables of the
imported file become available. Here is a program in two files, `shapes.atf` and `main.atf`, in the same folder:

```atf module=shapes.atf
// shapes.atf - a small module
const SHAPES_VERSION = "1.0"

struct Circle {
    r: float
}

impl Circle {
    fn area(self) -> float { return PI * self.r * self.r }
}

fn shapes_total_area(cs: [Circle]) -> float {
    return cs.map(|c| c.area()).sum()
}
```

```atf nocheck uses-modules
// main.atf
import "shapes"

fn main() {
    let cs = [Circle(1.0), Circle(2.0)]
    println("shapes", SHAPES_VERSION)
    println("{shapes_total_area(cs):.3f}")
}
```
```output
shapes 1.0
15.708
```

`atf run main.atf` compiles both files into one program. A bigger example is `examples/modules.atf` with `examples/lib/geometry.atf`.
Things to remember:

* There is **one global namespace** shared by all your files and the modules they import, so give your global functions and
  types specific names (`shapes_total_area`, not `total`). Defining a name twice is a compile error ("defined twice").
  The always-available library is the exception: your own definition may reuse one of its names (see section 28).
* Importing the same file twice (also indirectly) is harmless: every file is loaded once. Files may import each other.
* `import "std/name"` loads `name.atf` from the `stdlib` folder of the installation (next to `bin`).
* `include_str("file.txt")` puts the contents of a file into your program as a string when it is compiled (the path is
  relative to the source file). The program then does not need the file at run time.

### More modules: text, files, programs, config, XML, web and tests

Besides `std/json`, `std/csv` and the other data modules, these modules cover everyday jobs. The complete list of functions
is in [STDLIB.md](STDLIB.md).

* `std/path` takes file names apart and joins them (`path_basename`, `path_stem`, `path_ext`, `path_join`, `path_normalize`).
* `std/regex` is a regular-expression engine: `regex(pattern)` gives a `Regex` with `find`, `find_all`, `is_match`,
  `replace_all` (use `$1` for a group) and `split`. Because `{` starts an interpolation in a string, write the repeat
  `a{2,3}` as `"a\{2,3}"`.

<!-- id: path-regex -->
```atf
import "std/path"
import "std/regex"

fn main() {
    println(path_basename("C:\\work\\notes.tar.gz"), path_stem("notes.md"), path_join("a", "b.txt"))
    let re = regex("(\\d+)-(\\d+)")
    if let m = re.find("tel 12-345") {
        println(m.text, m.group(1), m.start)
    }
    println(re.replace_all("1-2 and 3-4", "$2:$1"))
    println(regex_split(",\\s*", "a, b,c"))
}
```
```output
notes.tar.gz notes a\b.txt
12-345 12 4
2:1 and 4:3
["a", "b", "c"]
```

* `std/fs` lists, copies, moves and removes files and folders (`fs_list_dir`, `fs_make_dirs`, `fs_remove_all`,
  `fs_append_file`, `fs_walk`, ...). `std/process` runs a program and captures what it prints (`proc_output`), and sets
  environment variables.

<!-- id: fs-process -->
```atf
import "std/fs"
import "std/process"

fn main() {
    let dir = temp_dir() + "tutorial_fs"
    fs_make_dirs(dir + "\\sub")
    fs_append_file(dir + "\\sub\\a.log", "one\n")
    fs_append_file(dir + "\\sub\\a.log", "two\n")
    println(fs_read_lines(dir + "\\sub\\a.log") ?? [])
    fs_remove_all(dir)

    let r = proc_output("cmd /c echo hello")
    println(r.0, r.1.trim())
}
```
```output
["one", "two"]
0 hello
```

* `std/crypto` uses the Windows crypto library for secure random bytes (`crypto_random_bytes`, `crypto_random_int`), keys from passwords (`crypto_pbkdf2`, PBKDF2-HMAC-SHA256) and encryption with AES-GCM (`crypto_encrypt`, `crypto_decrypt`). The encrypted result carries a random nonce and a tag, so decrypting with a wrong key, or after a single byte changed, returns an `Err` instead of garbage. Bytes are kept in a `str`; `hash_to_hex` from `std/hash` shows them, and `std/hash` also has SHA-256 and HMAC.

<!-- id: crypto-basic -->
```atf
import "std/crypto"
import "std/hash"

fn main() {
    let salt = crypto_random_bytes(16)
    let key = crypto_pbkdf2("my password", salt, 100000)
    let box = crypto_encrypt(key, "secret text").unwrap()
    println(box.len(), crypto_decrypt(key, box).unwrap())

    let wrong = crypto_pbkdf2("guess", salt, 100000)
    match crypto_decrypt(wrong, box) {
        Result.Ok(text) => println("opened: " + text)
        Result.Err(e) => println(e)
    }
    println(hash_to_hex(crypto_pbkdf2("password", "salt", 1))[0..16])
}
```
```output
39 secret text
cannot decrypt: wrong key or the data was changed
120fb6cffcf8b32c
```

* `std/bigint` holds whole numbers of any size. `+ - * / %`, comparisons and sorting work as with `int` (division truncates toward zero), but nothing overflows. Make one with `bigint(n)` or `bigint_parse(text)`; an `int` and a `BigInt` do not mix, so write `a + bigint(1)`. `to_int()` gives an `int?` that is nil when the value does not fit.

<!-- id: bigint-basic -->
```atf
import "std/bigint"

fn main() {
    let a = bigint_parse("123456789012345678901234567890").unwrap()
    println(a * bigint(1000) + bigint(7))
    println(bigint(2).pow(100))
    println(bigint_factorial(25))
    println(a > bigint(INT_MAX), (a % bigint(1000)).to_int() ?? -1)
}
```
```output
123456789012345678901234567890007
1267650600228229401496703205376
15511210043330985984000000
true 890
```

* `std/yaml` reads and writes YAML files, the common subset that configuration files use: block maps and lists, flow `[..]` and `{..}` on one line, quoted text and `|` / `>` blocks. The result is a `JsonValue`, so `query` and the rest of `std/json` work on it.

<!-- id: yaml-basic -->
```atf
import "std/yaml"

fn main() {
    let text = "name: app\nserver:\n  port: 8080\n  hosts:\n    - a\n    - b\n"
    match yaml_parse(text) {
        Result.Ok(v) => {
            println(v.query("server.port"), v.query("server.hosts[1]"))
            print(yaml_stringify(v))
        }
        Result.Err(e) => println("bad yaml: " + e)
    }
}
```
```output
8080 "b"
name: app
server:
  port: 8080
  hosts:
    - a
    - b
```

* `std/toml` reads and writes TOML configuration files. The result is a `JsonValue`, so `get_str`, `query` and the rest of
  `std/json` work on it.

<!-- id: toml-basic -->
```atf
import "std/toml"

fn main() {
    let r = toml_parse("name = \"app\"\n[server]\nport = 8080\nhosts = [\"a\", \"b\"]\n")
    match r {
        Result.Ok(v) => println(v.get_str("name", "?"), v.query("server.port"), v.query("server.hosts[1]"))
        Result.Err(e) => println("bad toml: " + e)
    }
}
```
```output
app 8080 "b"
```

* `std/http` is an HTTP and HTTPS client: `http_get(url)`, `http_post(url, body, headers)` and `http_request`. A reply with
  any status is a normal `Ok`; check `r.ok()` or `r.status`.

```atf nocheck
import "std/http"

fn main() {
    match http_get("https://example.com/") {
        Result.Ok(r) => println(r.status, r.body.len(), r.header("content-type") ?? "?")
        Result.Err(e) => println("request failed: " + e)
    }
}
```

* `std/xml` reads and writes XML: `xml_parse(text)` gives the root `XmlNode` with `attr`, `child`, `children_named`,
  `find_all`, `query("a/b")` and `inner_text`; `xml_element(tag).set_attr(..).add(..)` builds a node and
  `xml_stringify(node, 2)` writes it with indentation.

<!-- id: xml-basic -->
```atf
import "std/xml"

fn main() {
    let doc = xml_parse("<list><item id=\"1\">apple</item><item id=\"2\">pear &amp; fig</item></list>").unwrap()
    for it in doc.children_named("item") {
        println(it.attr("id") ?? "?", it.inner_text())
    }
    let note = xml_element("note").set_attr("lang", "en").add_text("to", "Ada")
    println(xml_stringify(note))
}
```
```output
1 apple
2 pear & fig
<note lang="en"><to>Ada</to></note>
```

* `std/net` opens TCP connections: `tcp_connect(host, port)` gives a `TcpConn` with `write`, `write_line`, `read`,
  `read_line`, `read_exact`, `read_all` and `close`; `tcp_listen(port)` gives a `TcpServer` whose `accept()` waits for the
  next client. A read that waits longer than the timeout (30 seconds, `set_timeout(ms)`) returns `nil`.

<!-- id: net-basic -->
```atf
import "std/net"

fn main() {
    let server = tcp_listen(0).unwrap()              // port 0: any free port
    let client = tcp_connect("127.0.0.1", server.port).unwrap()
    let peer = server.accept().unwrap()
    client.write_line("ping")
    println(peer.read_line() ?? "nothing")
    peer.write_line("pong")
    println(client.read_line() ?? "nothing")
}
```
```output
ping
pong
```

* UDP sends single messages with no connection: `udp_bind(port)` (0 = any free port) gives a `UdpSocket` with
  `send_to(host, port, data)` and `receive()`, which returns a `UdpPacket` (`data`, `host`, `port` of the sender)
  or `nil` when nothing came within the timeout (`set_timeout(ms)`). Each message arrives whole or not at all.

<!-- id: udp-basic -->
```atf
import "std/net"

fn main() {
    let a = udp_bind().unwrap()                      // port 0: any free port
    let b = udp_bind().unwrap()
    a.send_to("127.0.0.1", b.port, "ping")
    if let m = b.receive() {
        println(m.data, m.port == a.port)
        b.send_to(m.host, m.port, "pong")            // answer the sender
    }
    if let m = a.receive() { println(m.data) }
    b.set_timeout(100)
    println(b.receive() == nil)                      // nothing more came
}
```
```output
ping true
pong
true
```

* `std/websocket` speaks WebSocket, the two-way message channel browsers use: `ws_connect("ws://host:port/path")`
  gives a `WebSocket`, and `ws_listen(port)` gives a server whose `accept()` waits for a client and answers its
  handshake. `send(text)`, `send_binary(data)` and `ping()` send; `receive()` returns a `WsMessage` (`kind` is
  `"text"`, `"binary"` or `"close"`, then `data` and `code`), answers pings by itself and returns `nil` when the
  connection broke or the read timed out. `close(code, reason)` says goodbye. Only `ws://` works, not `wss://`.
  Without threads one program cannot `ws_connect` to its own server, so the sample below does the client handshake
  in two halves.

<!-- id: websocket-basic -->
```atf
import "std/websocket"

fn main() {
    let server = ws_listen(0).unwrap()               // port 0: any free port

    // both sides in one program, so the client handshake goes in two halves
    // (a normal client just calls ws_connect("ws://host:port/chat"))
    let conn = tcp_connect("127.0.0.1", server.port).unwrap()
    let key = ws_new_key()
    conn.write(ws_handshake_request("127.0.0.1", "/chat", key))
    let srv = server.accept().unwrap()
    let cli = ws_handshake_finish(conn, key).unwrap()

    cli.send("hello")
    if let m = srv.receive() { srv.send("you said {m.data} on {srv.path}") }
    if let m = cli.receive() { println(m.kind, m.data) }
    cli.close(1000, "done")
    if let m = srv.receive() { println(m.kind, m.code, m.data) }
}
```
```output
text you said hello on /chat
close 1000 done
```

* `std/url` takes web addresses apart and builds them: `url_parse(text)` gives a `Url` (`scheme`, `host`, `port`, `path`,
  `query`, `fragment`, `param(name)`), `url_join(base, link)` follows a link the way a browser does, and `url_encode` /
  `url_decode` do the %-escapes.

<!-- id: url-basic -->
```atf
import "std/url"

fn main() {
    let u = url_parse("https://example.com:8080/a/b.html?x=1&y=two%20words#top").unwrap()
    println(u.host, u.port, u.path, u.param("y") ?? "none")
    println(url_encode("a b&c"))
    println(url_join("http://a.com/x/y.html", "../z").unwrap())
}
```
```output
example.com 8080 /a/b.html two words
a%20b%26c
http://a.com/z
```

* `std/glob` matches file names against patterns (`*`, `?`, `[a-z]`, and `**` across folders), and `glob_find(folder, pattern)`
  lists the files that match.

<!-- id: glob-basic -->
```atf
import "std/glob"

fn main() {
    println(glob_match("src/**/*.atf", "src/a/b.atf"), glob_match("*.txt", "a.atf"))
}
```
```output
true false
```

* `std/ini` reads and writes INI settings files: `ini_parse(text)` gives an `IniDoc` with `get(section, key)`,
  `get_or`, `get_int`, `get_bool`, `set` and `ini_stringify`. Keys before the first `[section]` belong to the section `""`.

<!-- id: ini-basic -->
```atf
import "std/ini"

fn main() {
    let d = ini_parse("name = app\n[server]\nport = 8080\n").unwrap()
    println(d.get_or("", "name", "?"), d.get_int("server", "port", 80))
}
```
```output
app 8080
```

* `std/httpd` is a small web server. A handler is a function from `HttpRequest` to `HttpReply`; `router_new()` collects
  routes such as `/users/:id`, and `http_listen(port)` gives a server whose `serve(handler)` answers requests one after
  another. `serve_one` answers a single request, which is handy in tests.

<!-- id: httpd-router -->
```atf
import "std/httpd"

fn main() {
    var app = router_new()
    app.get("/users/:id", |req| http_text("user " + req.params["id"]))
    println(app.handle(HttpRequest{ path: "/users/7" }).body)
    println(app.handle(HttpRequest{ path: "/nothing" }).status)
}
```
```output
user 7
404
```

```atf nocheck
import "std/httpd"

fn main() {
    var app = router_new()
    app.get("/", |req| http_html("<h1>Hello</h1>"))
    app.get("/hello/:name", |req| http_text("Hello, " + req.params["name"]))
    let server = http_listen(8080).unwrap()
    println("open http://127.0.0.1:8080/")
    server.serve(|req| app.handle(req))
}
```

* `std/html` builds web pages. `h("div")` makes an element; chain `.cls(..)`, `.id(..)`, `.attr(..)`, `.style(..)`,
  `.text(..)` (escaped) and `.add(..)`. `.anim("slide-up")` plays a ready-made animation (`fade-in`, `slide-up`,
  `slide-left`, `slide-right`, `zoom-in`, `bounce`, `pulse`, `spin`, `shake`, `float`), and `.reveal()` plays it when the
  element scrolls into view. For your own animations use `css_keyframes` and `css_animation`. `html_page` wraps everything
  into a full page, and `http_html(page)` serves it with `std/httpd`.

<!-- id: html-basic -->
```atf
import "std/html"

fn main() {
    println(h("h1").text("Hello <ATF>").anim("slide-up").render())
    println(css_animation("grow", 2.0, "ease-in-out", "infinite"))
}
```
```output
<h1 class="atf-slide-up" style="animation-duration: 0.60s;">Hello &lt;ATF&gt;</h1>
animation: grow 2.00s ease-in-out 0.00s infinite both;
```

* Animations in windows (`std/ui`): `animate("key", target, ms)` returns a value that glides to `target` whenever the
  target changes (use it for sizes, positions, opacity); `animate_color` does the same for colours, `animate_from`
  plays an entrance, and `anim_loop(seconds)` / `anim_wave(seconds)` give endless 0..1 values for spinners and pulses.
  Easing functions (`ease_out`, `ease_in_out`, `ease_out_back`, `ease_out_bounce`, `ease_out_elastic`) change the feel,
  e.g. `animate_with("k", target, 600, ease_out_bounce)`. The window redraws every frame while an animation runs, and
  stops redrawing when nothing moves. See `examples/ui/animations.atf` and `examples/web_animations.atf`.

* `std/test` is a small test framework: `test(name, || { ... })` with `expect`, `expect_eq`, `expect_ne`, `expect_near`
  and `expect_panics`, and `test_report()` for the summary and exit code.

<!-- id: test-basic -->
```atf
import "std/test"

fn main() -> int {
    test("addition", || { expect_eq(1 + 1, 2) })
    return test_report()
}
```
```output
ok   addition
1 tests, all passed
```

### Windows and design: `std/ui`

`import "std/ui"` gives you windows with buttons, text boxes and the rest of a modern interface. The ideas come from HTML
and CSS, but you write ordinary ATF: the screen is a tree of `Node` values, and every node takes chained style methods.

* A **view function** builds the screen from your data. After every click, key press or timer tick it runs again and the
  window is redrawn, so your event handlers only change data; you never update a widget by hand.
* **Elements**: `column`, `row`, `box`, `stack`, `grid(cols, ...)`, `scroll`, `text`, `button`, `textbox`, `checkbox`,
  `toggle`, `slider`, `progress`, `image`, `spacer`, `divider`.
* **Style methods** chain like CSS properties: `.padding(8, 16)`, `.bg(..)`, `.radius(12)`, `.shadow(..)`, `.font_size(18)`.
  Text styles such as `color`, `font_size` and `bold` are inherited by the children, as in CSS.
* **Reusable styles** are values, like CSS classes: `let card = style().bg(WHITE).radius(16)`, used with `.style(card)`.
  Combine them with `+`, and give them states with `.hover(style()...)`, `.pressed(..)`, `.focused(..)` and `.transition(ms)`.
* **Colors** are ints: `hex("#4f46e5")`, `hex("slate")`, `rgb(79, 70, 229)`, `rgba(0, 0, 0, 0.25)`, `fade(c, 0.5)`,
  `mix(a, b, 0.3)`, `lighten`, `darken`, `WHITE`, `BLACK`, `TRANSPARENT`.

<!-- id: ui-counter -->
```atf
import "std/ui"

struct App { count: int = 0 }

// a reusable style, like a CSS class
let PRIMARY = style().bg(hex("#4f46e5")).color(WHITE).radius(10).padding(10, 18).border(0, TRANSPARENT)
    .hover(style().bg(hex("#4338ca"))).transition(150)

fn view(app: App) -> Node {
    return column([
        text("Clicked {app.count} times").font_size(22).bold(),
        row([
            button("Reset", || { app.count = 0 }),
            button("Click me", || { app.count += 1 }).style(PRIMARY),
        ]).gap(8),
    ]).padding(24).gap(12).center().grow()
}
```

`main` opens the window with `ui_run(title, width, height, view)`. The call returns when the window is closed:

```atf nocheck
fn main() {
    let app = App()
    ui_run("Counter", 420, 260, || view(app))
}
```

How CSS ideas are written in ATF:

| CSS | ATF |
|---|---|
| `display: flex; flex-direction: column` | `column([...])` (`row([...])` for a row) |
| `gap: 12px; padding: 8px 16px` | `.gap(12).padding(8, 16)` (one to four values, like CSS) |
| `align-items` / `justify-content` | `.align(Align.Center)` / `.justify(Justify.Between)` |
| `flex-grow: 1` / `flex-wrap: wrap` | `.grow()` / `.wrap()` |
| `width: 50%` | `.width_pct(50.0)` |
| `display: grid; grid-template-columns: repeat(3, 1fr)` | `grid(3, [...])` |
| `background: linear-gradient(135deg, a, b)` | `.gradient(a, b, 135.0)` |
| `border-radius: 999px` | `.pill()` |
| `box-shadow: 0 4px 18px rgba(0,0,0,.1)` | `.shadow(0, 4, 18, rgba(0, 0, 0, 0.1))` |
| `position: absolute; top: 6px; right: 6px` | `.absolute(UNSET, 6, 6)` (left, top, right, bottom) |
| `:hover { ... }` | `.hover(style()...)` |
| `transition: 150ms` | `.transition(150)` |
| `direction: rtl` | `.rtl()` (for Hebrew and Arabic) |
| `overflow: auto` | `scroll([...])` |

Data that changes over time, such as a clock or live numbers, uses `ui_every(ms, fn)`. The view is rebuilt after each call.
To get a picture without opening a window (for tests and documentation), use `ui_screenshot(view, width, height, "file.bmp")`,
or run any UI program with the environment variable `ATF_UI_SCREENSHOT=file.bmp`.

<!-- id: ui-screenshot -->
```atf
import "std/ui"

fn main() {
    let card = style().bg(WHITE).radius(16).padding(20).gap(8).shadow(0, 8, 24, rgba(15, 23, 42, 0.12))
    let view = || column([
        column([
            text("Pro plan").font_size(20).bold(),
            text("Unlimited projects and live exports").color(hex("slate")),
            text("Upgrade").color(WHITE).bg(hex("#4f46e5")).padding(6, 14).pill(),
        ]).style(card).align(Align.Start),
    ]).padding(24).grow().gradient(hex("#eef2ff"), hex("#fdf2f8"), 135.0)
    println(ui_screenshot(view, 400, 220, "card.bmp"))
}
```
```output
true
```

#### The same program in a browser

With the environment variable `ATF_UI_WEB=8080` set, `ui_run` does not open a window. It serves the program at
`http://127.0.0.1:8080/` instead, and the program does not change. The page shows the picture the window would draw
(the same drawing code, sent to the browser as pixels) and sends the mouse, the wheel and the keyboard back to the
program. Hover styles, transitions, `ui_every` timers, text editing, shortcuts and `ui_quit` work as in the window.

```atf nocheck
import "std/ui"

struct Counter { count: int = 0 }

fn main() {
    let c = Counter()
    ui_run("Counter", 360, 260, || column([
        text("Count: {c.count}").font_size(28),
        button("+1", || { c.count += 1 }).width(120),
    ]).gap(12).padding(24))
}
```

Start it with the port number, then open the address in a browser:

```bash
ATF_UI_WEB=8080 bin/atf.exe run counter.atf
```

In PowerShell: `$env:ATF_UI_WEB = "8080"; bin\atf.exe run counter.atf`

The program keeps running until it calls `ui_quit()`; the page then says that the program has closed. Things to know:

- The page only works on the computer that runs the program: the server listens on `127.0.0.1` only, and it refuses
  requests from other sites (403), so another computer on the network cannot use it.
- Only the left mouse button is passed on, so `ui_mouse_held(1)` and `ui_mouse_held(2)` stay false in the browser.
- `ui_mouse_capture(true)` locks the pointer in the page: click the picture to lock it, and press Esc to release it.
- Dialogs (`message_box`, `confirm_box`, the file dialogs), the clipboard and the image files named by `image(path)`
  belong to the computer that runs the program. A dialog opens on that computer and waits there, so the page stops
  until it is answered.
- Fonts are the ones of the computer that runs the program.

#### A complete program: menus, text, dialogs, files

Beyond the basics, `std/ui` has what a whole application needs:

| You want | Use |
|---|---|
| a multi-line text field | `textarea(value, on_input)`, `.rows(n)` sets its height |
| a choice from a list | `select(value, ["a", "b"], on_change)` |
| tabs | `tabs(["One", "Two"], selected, on_select)`, then show the chosen content yourself |
| a menu bar | `menu_bar([menu_button("File", [menu_item("Open", open), ...])])` |
| any popup | `dropdown(trigger, content)`: `content` floats under `trigger` until a click elsewhere or Esc |
| a dialog | `dialog("Title", body, [buttons], on_close)`, or `modal(content, on_close)` for your own card |
| a hint on hover | `.tooltip("text")` |
| small symbols | `icon("save")`, `icon("search")`, ... (a list is in [STDLIB.md](STDLIB.md#stdui)) |
| drawing | `canvas(\|c\| { c.rect(..); c.circle(..); c.line(..); c.text(..) })`, with `.on_pointer(\|x, y\| ..)`. `c.pixels(x, y, w, h, colors, pw, ph)` draws a picture from an `[int]` of `0xRRGGBB` values: fast enough for software rendering. It scales with square blocks; `c.pixels_smooth(..)` takes the same arguments and scales smoothly, so a low resolution scene does not look pixelated. There is no resolution limit: `c.pixel_w()` and `c.pixel_h()` give the canvas size in real screen pixels, so a scene can be drawn at the full resolution of the window (with `.grow()` it follows the window size). `minecraft.atf` and `wolfenstein.atf` do this and lower the resolution by themselves only when a frame takes too long. For games: `ui_key_down("w")`, `ui_mouse_held(0)` (0 left, 1 right, 2 middle), and mouse look with `ui_mouse_capture(true)` + `ui_mouse_delta()` |
| shortcuts | `ui_shortcut("ctrl+s", save)` |
| standard dialogs | `message_box`, `confirm_box`, `open_file_dialog`, `save_file_dialog` |
| the clipboard | `clipboard_get()`, `clipboard_set(text)` |

Text fields (`textbox` and `textarea`) edit the way people expect: the mouse and the arrow keys with Shift to select,
double click for a word, triple click for a line, Ctrl+A / C / X / V, Ctrl+Z / Ctrl+Y (undo and redo), Ctrl with the
arrows to jump by words, Home / End, and Tab inserts spaces in a text area. A text area scrolls and does not wrap lines.

Popups, dialogs and tooltips are drawn on a layer above the rest of the window. Put a `dialog(...)` last in the
list of children, shown only while your data says so (`if asking { root.add(dialog(...)) }`). `.key("name")` gives an
element a fixed name; `focus_field("name")` moves the keyboard focus to the text field that has it.

A shortcut without Ctrl or Alt is ignored while a text field has the focus, so typing does not trigger it.
The standard dialogs return `nil` or `false` when the user cancels:

```atf nocheck
fn export(text: str) {
    let path = save_file_dialog("Export", "Text files|*.txt|All files|*.*", "txt") ?? ""
    if path.len() > 0 { write_file(path, text) }
}

fn main() {
    ui_shortcut("ctrl+s", || export("hello"))
    ui_run("Exporter", 300, 200, || column([text("Press Ctrl+S")]).center().grow())
}
```

#### Testing a program without a window

`ui_headless(view, width, height)` runs the interface without a window, and `ui_click(x, y)`, `ui_click_text("label")`,
`ui_type("text")`, `ui_keypress("ctrl+z")` and `ui_drag(...)` act like a user. The clipboard and the standard dialogs
are replaced by fakes (`ui_answers(ok, path)` chooses what the dialogs return), so a test never waits for a person.
Your program's data tells you what happened:

<!-- id: ui-headless -->
```atf
import "std/ui"

var name = ""
var color = "red"
var log = ""
var asking = false

fn view() -> Node {
    let root = column([
        textbox(name, |s| { name = s }).placeholder("Your name"),
        select(color, ["red", "green", "blue"], |c| { color = c }),
        menu_button("File", [
            menu_item("Save", || { log = "saved" }),
            menu_item("Quit", || { asking = true }),
        ]),
    ]).padding(16).gap(10).grow()
    if asking {
        root.add(dialog("Quit", text("Really quit?"), [button("No", || { asking = false })], || { asking = false }))
    }
    return root
}

fn main() {
    ui_headless(view, 320, 240)
    ui_click(50, 30)                // the text box
    ui_type("Ada")
    ui_keypress("ctrl+a")
    ui_keypress("ctrl+c")
    ui_click_text("red")            // opens the list
    ui_click_text("blue")
    ui_click_text("File")
    ui_click_text("Save")
    println(name, color, log, clipboard_get())
    ui_click_text("File")
    ui_click_text("Quit")
    println("asking:", asking)
    ui_keypress("esc")              // closes the dialog
    println("asking:", asking)
}
```
```output
Ada blue saved Ada
asking: true
asking: false
```

#### Remembering things between runs: `std/app`

`import "std/app"` gives a program its own folder (`app_dir("name")` is `%APPDATA%\name`) and a small settings file of
`key=value` lines. `settings_open("name")` loads it, `get`, `get_int`, `get_bool` read with a fallback, `set`, `set_int`,
`set_bool` change values and `save()` writes the file. `recent_add(settings, path)` keeps a most-recently-used list.
For bigger data, write a file in `app_path("name", "data.json")` with `std/json`.

<!-- id: app-settings -->
```atf
import "std/app"

fn main() {
    let file = temp_dir() + "demo_settings.txt"
    let s = settings_file(file)
    s.set("theme", "dark")
    s.set_int("width", 900)
    s.save()

    let again = settings_file(file)
    println(again.get("theme", "light"), again.get_int("width", 640), again.get_bool("maximized"))
    delete_file(file)
}
```
```output
dark 900 false
```

A whole program that uses all of this, a notes editor with a menu bar, a search box, a text area, shortcuts, file
dialogs, a dark theme and automatic saving, is in `examples/ui/notes.atf`.

The complete reference is in [STDLIB.md](STDLIB.md#stdui). Look-alikes of familiar programs are there too: `calculator.atf`,
`minesweeper.atf`, `snake.atf`, `paint.atf`, `tetris.atf`, `spreadsheet.atf` (a formula engine with cell references and
`SUM(A1:A5)`) and `wolfenstein.atf` (a 3D shooter with a ray caster, enemies and a mini map). Larger programs are in `examples/ui/`: `counter.atf`, `todo.atf` (a
task list with a text box, check boxes and filters) and `dashboard.atf` (a sidebar, gradient cards, a bar chart, settings and
a light and dark theme). `minecraft.atf` is a small first-person block world (a ray caster drawn on a `canvas`, walking, jumping,
breaking and placing blocks).

---

## 26. Memory and the garbage collector

You never free memory. Arrays, maps, strings, structs and closures are allocated on a heap that is cleaned automatically by a
garbage collector: when no variable can reach an object any more, its memory is reused. So this is fine:

<!-- id: gc -->
```atf
struct Blob {
    data: [int]
}

fn main() {
    var total = 0
    for i in 0..2000 {
        let b = Blob(array_make::<int>(100000))   // 800 KB each, 1.6 GB in total
        b.data[0] = i
        total += b.data[0]
    }
    println(total)
    println("collections happened:", gc_runs() > 0)
}
```
```output
1999000
collections happened: true
```

* `gc()` forces a collection, `gc_runs()` counts them, and `gc_live_bytes()` tells how much memory was still in use after the last one.
* Numbers (`int`, `float`, `bool`, `byte`) and enums without data are plain values. Everything else — arrays, maps, structs,
  tuples, strings, closures, enums with data, optionals — is a *reference*: assigning it copies the reference, not the object.
  Use `copy(x)` for an independent (shallow) copy.

How it works, in short: the collector is a *mark and sweep* collector. When about 32 MB have been allocated since the last
collection (or more, if your program keeps more data alive), it pauses the program, finds every object that can still be
reached from the variables of the running functions and from global variables, and frees the rest. Objects never move.
Text and arrays of numbers are never scanned for references, so big arrays of numbers are cheap for the collector.

<!-- id: gc-stats -->
```atf
struct Node {
    value: int,
    next: Node?
}

fn build(n: int) -> Node? {
    var head: Node? = nil
    for i in 0..n { head = Node(i, head) }
    return head
}

fn main() {
    var keep = build(1000000)           // about 1 million small objects stay alive
    gc()
    let with_list = gc_live_bytes()
    keep = nil                          // drop the only reference
    gc()
    let without = gc_live_bytes()
    println(with_list > 16000000, without < 1000000, gc_runs() >= 2)
}
```
```output
true true true
```

---

## 27. Performance tips

ATF programs are compiled to machine code, so ordinary code is already fast (see the numbers in the
[README](../README.md#performance)). When you need more speed, these habits help the most:

1. **Build text with `str_builder()` or `join`, not with `s = s + x` in a loop.** Every `+` copies the whole text, so a
   loop of `+` is *quadratic*: building a 100 000-letter text with `+` took 0.5 s, with a builder 0.0005 s.
2. **Create arrays at their final size** with `array_make::<T>(n)` (filled with zeros) or reserve room with
   `array_with_cap::<T>(n)` before many `push` calls.
3. **Use `s.byte_at(i)` and character literals** (`'a'`) to inspect text; `s[i]` and `for ch in s` produce one-letter strings.
4. **Prefer plain values in hot loops.** An optional number (`int?`) is stored in a small heap object; a sentinel value
   such as `-1` is about 7 times faster in a tight loop. Likewise `x * x` beats `x ** 2`.
5. **Avoid creating garbage in inner loops** (temporary arrays, strings, closures); reuse a buffer with `clear()` instead.
6. **Choose the right container**: `key in map` and `set.has(x)` are fast (hashing); `array.contains(x)` and `index_of`
   look at every element.
7. **Measure** with `clock()`: `let t = clock()` ... `println(clock() - t)`.

<!-- id: perf-builder -->
```atf
fn main() {
    // slow: s = s + ...  copies the text every time
    // fast: collect the pieces, then join them once
    var sb = str_builder()
    for i in 0..5 {
        sb.add(str(i))
        sb.add_byte(',')
    }
    println(sb.finish())

    var parts: [str] = []
    for i in 0..5 { parts.push("#{i}") }
    println(" ".join(parts))

    // count the letter a, without making one-letter strings
    let text = "banana bandana"
    var count = 0
    for i in 0..text.len() {
        if text.byte_at(i) == 'a' { count += 1 }
    }
    println(count)

    let squares = array_make::<int>(5)      // final size, no push needed
    for i in 0..5 { squares[i] = i * i }
    println(squares)
}
```
```output
0,1,2,3,4,
#0 #1 #2 #3 #4
6
[0, 1, 4, 9, 16]
```

---

## 28. Tips, traps and where to go next

**Names you cannot use** (keywords): `fn let var const if else while for in loop break continue return struct enum impl match
import extern true false and or not as defer type nil step unsafe pub interface`. In particular, `step` is a keyword, so call a parameter
`by` or `stride` instead.

**Library names can be reused.** A function, constant or global of yours may have the same name as one of the standard
library (`sum`, `min`, `max`, `zip`, `abs`, `E`, `PI`, ...): your program then uses your definition, while the library
keeps using its own (so `gcd` still works if you write your own `abs`). Methods such as `[1, 2].sum()` are not affected.
A type of yours also wins over a library value with the same name: with `enum E { A, B }`, `E.A` is your variant.
Two definitions of the same name inside your own program are an error ("defined twice").

**A literal `{` in a string is written `\{`.** A `{` directly before the closing quote is literal: `"{"` is the text `{`.

**An interpolation cannot start with a quote right after the brace.** In `"{"x"}"` the `{` counts as a literal brace;
write `{ "x" }` with a space, or put the text in a variable first. Names, calls and numbers directly after `{` are fine,
e.g. `"{pad_left("a", 3)}"`.

**A `for` loop with parentheses does not unpack tuples.** `for (a, b) in pairs` gives the index and the element. Use
`for p in pairs { let (a, b) = p ... }`.

**Range tests need parentheses:** `x in (1..10)`, not `x in 1..10`.

**Integer overflow wraps silently** (`INT_MAX + 1` is `INT_MIN`); `/` and `%` by zero stop the program with a panic.
Converting a float that is too big (or `nan`) to an int gives `INT_MIN`.

**Deep recursion** is fine up to hundreds of thousands of nested calls, but infinite recursion crashes the program without a message
(section 23).

**Text is bytes.** `len()` of `"héllo"` is 6.

**An optional text prints with quotes**: `let s: str? = "hi"` prints as `"hi"`. Unwrap it first (`s!`, `s ?? ""`) to print the plain text.

<!-- id: tips -->
```atf
fn main() {
    let name: str? = "Dana"
    println(name, name!, name ?? "nobody")
    println("{pad_left("a", 3)}|", "{ "x" }", "\{not interpolated}", "{")
    var big = 1e300
    println(INT_MAX + 1 == INT_MIN, int(big) == INT_MIN, "héllo".len())
    let max = 5                          // a local may reuse a library name
    println(max)
}
```
```output
"Dana" Dana Dana
  a| x {not interpolated} {
true true 6
5
```

**Where next?**

* `examples/` contains more than forty complete programs, from FizzBuzz to a text adventure and a calculator; all of them are tested
  with `python tests/run_examples.py`.
* [REFERENCE.md](REFERENCE.md) describes every part of the language and the whole standard library.
* `atf/stdlib/prelude.atf` is the standard library itself, written in ATF — reading it is a great way to learn.
* `bench/` has small benchmarks to measure speed.

Happy coding!
