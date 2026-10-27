@echo off
rem Installs ATF for the current user (no administrator rights needed):
rem copies the compiler and the standard library to %LOCALAPPDATA%\atf and adds that folder
rem to the user PATH, so  atf run file.atf  works in every new terminal.   Undo with uninstall.cmd.
setlocal
set "SRC=%~dp0"
set "DEST=%LOCALAPPDATA%\atf"
if not exist "%SRC%bin\atf.exe" (
    echo bin\atf.exe was not found: build it first with rebuild_compiler.cmd
    exit /b 1
)
if not exist "%DEST%\stdlib" mkdir "%DEST%\stdlib" || exit /b 1
copy /y "%SRC%bin\atf.exe" "%DEST%\atf.exe" >nul || exit /b 1
copy /y "%SRC%stdlib\*.atf" "%DEST%\stdlib\" >nul || exit /b 1
echo installed the compiler and the standard library in %DEST%
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$d = Join-Path $env:LOCALAPPDATA 'atf';" ^
  "$p = [Environment]::GetEnvironmentVariable('Path', 'User'); if ($null -eq $p) { $p = '' };" ^
  "if (($p -split ';') -contains $d) { 'the folder is already in your PATH' }" ^
  "else { [Environment]::SetEnvironmentVariable('Path', (($p.TrimEnd(';') + ';' + $d).TrimStart(';')), 'User'); 'added the folder to your PATH: open a new terminal and try  atf version' }"
