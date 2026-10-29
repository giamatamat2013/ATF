# ATF for Visual Studio Code

Language support for [ATF](https://github.com/tamat2013) (*Accessible Typed Fast*), a small compiled programming language (`.atf` files).

Created by **TAMAT2013**.

## Features

- **Syntax highlighting** for ATF, including the pipe `|>`, string interpolation, format specs, generics, lambdas and attributes. Also inside ```` ```atf ```` blocks in Markdown.
- **Snippets** for functions, structs, enums, `impl`, `match`, loops and more. Window programs with `std/ui`: `uiapp` (a whole program), `uistyle`, `uirow`, `uicol`, `uimenu`, `uitextarea`, `uiselect`, `uidialog`, `uicanvas`, `uishortcut`, `uifile`, `uitest` (a test without a window) and `uisettings` (`std/app`). Also `argsparse` (`std/args` and `std/log`), `regex` (`std/regex`), `test` and `testprop` (`std/test`, a property test), `pipe` (the `|>` operator), `iterator` (a type a `for` loop can walk) and `iterchain` (`std/iter`), `aiask` (`std/ai`), `term` (`std/term`), `httpget` (`std/http`), `xmlread` (`std/xml`), `tcpclient` (`std/net`) and `httpserve` (`std/httpd`).
- **Automatic imports.** When you use a standard library name such as `json_parse`, `counter_from` or `button(...)`, the matching `import "std/..."` line is added at the top of the file.
- **Compiler errors in the editor.** `atf check` runs when an `.atf` file is opened or saved, and the errors show up as red squiggles and in the Problems panel.
- **Run and build commands** from the Command Palette:
  - `ATF: Run File` (also `F5`, `Ctrl+F5` and the play button in the editor title bar)
  - `ATF: Build File`
  - `ATF: Check File`
  - `ATF: Run File on Every Save` (`atf watch`)
  - `ATF: Run Tests` (`atf test` in the workspace folder: every `test_*.atf` and `*_test.atf`)
- **Outline** and *Go to Symbol* for `fn`, `struct`, `enum`, `impl`, `type` and `const`.
- Bracket matching, auto-closing pairs, comment toggling and indentation rules.

## Requirements

The ATF compiler. The extension looks for it in this order:

1. the `atf.path` setting
2. `bin\atf.exe` or `atf.cmd` in the workspace folder
3. `atf` on your `PATH`

Opening the ATF repository as the workspace is enough; running `install.cmd` from the repository puts `atf` on your `PATH`.

## Settings

| Setting | Default | Description |
| --- | --- | --- |
| `atf.path` | `""` | Path to the ATF compiler. |
| `atf.checkOnSave` | `true` | Run `atf check` on open and save and show the errors in the editor. |
| `atf.autoImport` | `true` | Add missing `import "std/..."` lines automatically. |

## Install from source

Copy this folder to `%USERPROFILE%\.vscode\extensions\tamat2013.atf-0.4.0` and reload VS Code, or package it with `npx @vscode/vsce package` and install the `.vsix`.

## License

PolyForm Noncommercial 1.0.0. See [LICENSE](LICENSE).
