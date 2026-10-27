@echo off
rem ATF launcher: uses the native compiler bin\atf.exe (falls back to the Python bootstrap compiler)
if exist "%~dp0bin\atf.exe" (
    "%~dp0bin\atf.exe" %*
) else (
    python "%~dp0run_atf.py" %*
)
