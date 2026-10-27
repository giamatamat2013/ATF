# Converting between ATF, Python and Rust

`tools/convert.atf` translates a program between ATF, Python and Rust, in all six directions:
Python to ATF, Rust to ATF, ATF to Python, ATF to Rust, Python to Rust and Rust to Python.

```text
bin/atf.exe run tools/convert.atf prog.py --to atf             print the ATF version
bin/atf.exe run tools/convert.atf prog.atf --to rs -o prog.rs  write a Rust version to a file
bin/atf.exe run tools/convert.atf prog.rs --to py
```

| Option | Meaning |
|---|---|
| `--to atf\|py\|rs` | The language of the result (required). |
| `--from atf\|py\|rs` | The language of the input. By default it comes from the file extension. |
| `-o file` | Write the result to a file instead of the screen. |

Anything the converter had to guess is reported on stderr as `note: ...`.

## How it works

Each input language is read into one shared syntax tree (`tools/convert/ast.atf`), and each output language is
printed from that tree. Library calls are renamed to the ATF names while reading (`append` becomes `push`,
`len(x)` becomes `x.len()`, `println!` becomes `println`) and renamed again for the target when printing.
The tool is a set of small modules in `tools/convert/`: `lex`, `parse_base`, `parse_brace` (ATF and Rust),
`parse_py`, `lower`, `infer`, `emit_atf`, `emit_py`, `emit_rs`, and `api` (the function `cv_convert(src, from, to)`).

## What is supported

Functions, structs and classes (dataclasses), enums with and without data, `impl` blocks and methods, generics,
`if`/`while`/`for`, ranges, `match` with patterns and guards, closures and lambdas, comprehensions, tuples,
arrays/lists, maps/dicts, string interpolation (f-strings, `format!`), optionals and `Result`.

## Limits

The output is a starting point, not a finished port. Always compile or run it and fix what is reported.

- Comments are dropped.
- Types are guessed where the source has none (Python parameters, empty collections). Python parameters without
  a type stay without a type in ATF.
- Python: `try`/`with`/`yield` and decorators other than `@dataclass` are not supported.
- Rust: ownership, borrows, lifetimes and traits are not modelled. The generated Rust guesses `&`, `&mut` and
  `.clone()` and has not been compiled by the test suite (no Rust toolchain is required).
- ATF to Python: `defer`, labelled `break` and a `match` inside a larger expression are lost or rejected.
  Integer `/` becomes `//`.
- Library functions of ATF with no counterpart (`str_builder`, `regex`, `std/ui`, `args_parser`, ...) are
  copied unchanged, so the result will not run until you replace them.
- Whether a variable is a map or an array is detected by a heuristic.

The ATF to ATF direction is a good check of the tool: converting every program in `examples/` and running the
result gives the expected output for all of them (`tests/qa/convert_tool.atf` checks a few samples).
