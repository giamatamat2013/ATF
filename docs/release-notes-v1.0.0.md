## Features

- First release of ATF: a statically typed language that compiles to native Windows x64 `.exe` files.
- Self-hosted compiler (`bin/atf.exe`, written in ATF) with a Python bootstrap compiler.
- Standard library: the always-available prelude and the importable `std/*` modules, including `std/ui` for windows.
- VS Code extension with syntax highlighting, snippets and automatic `std` imports.
- Tutorial in English and Hebrew, a standard library reference, and runnable examples.

## Install

Unzip `atf-1.0.0-windows-x64.zip` and run `install.cmd`. It copies the compiler and the standard library to `%LOCALAPPDATA%\atf` and adds that folder to your PATH. Then `atf run file.atf` works in any new terminal.
