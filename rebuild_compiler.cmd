@echo off
rem Rebuilds the self-hosted compiler.  Uses the current bin\atf.exe if present, otherwise the Python bootstrap.
setlocal
cd /d "%~dp0"
if exist bin\atf.exe (
    bin\atf.exe build compiler\main.atf -o bin\atf_new.exe || exit /b 1
) else (
    python run_atf.py build compiler\main.atf -o bin\atf_new.exe || exit /b 1
)
bin\atf_new.exe build compiler\main.atf -o bin\atf_check.exe || exit /b 1
fc /b bin\atf_new.exe bin\atf_check.exe >nul && (echo fixed point reached: the compiler compiles itself to identical code) || (echo WARNING: second generation differs)
move /y bin\atf_new.exe bin\atf.exe >nul
del bin\atf_check.exe
