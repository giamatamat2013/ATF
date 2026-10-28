@echo off
rem Installs ATF for the current user (no administrator rights needed):
rem copies the compiler, the standard library and the icon to %LOCALAPPDATA%\atf, adds that folder
rem to the user PATH, so  atf run file.atf  works in every new terminal, and makes ATF the program
rem that opens .atf files in Explorer.   Undo with uninstall.cmd.
setlocal
set "SRC=%~dp0"
set "DEST=%LOCALAPPDATA%\atf"
set "UC=HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\.atf\UserChoice"
if not exist "%SRC%bin\atf.exe" (
    echo bin\atf.exe was not found: build it first with rebuild_compiler.cmd
    exit /b 1
)
if not exist "%DEST%\stdlib" mkdir "%DEST%\stdlib" || exit /b 1
copy /y "%SRC%bin\atf.exe" "%DEST%\atf.exe" >nul || exit /b 1
copy /y "%SRC%stdlib\*.atf" "%DEST%\stdlib\" >nul || exit /b 1
copy /y "%SRC%assets\atf.ico" "%DEST%\atf.ico" >nul || exit /b 1
echo installed the compiler and the standard library in %DEST%
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$d = Join-Path $env:LOCALAPPDATA 'atf';" ^
  "$p = [Environment]::GetEnvironmentVariable('Path', 'User'); if ($null -eq $p) { $p = '' };" ^
  "if (($p -split ';') -contains $d) { 'the folder is already in your PATH' }" ^
  "else { [Environment]::SetEnvironmentVariable('Path', (($p.TrimEnd(';') + ';' + $d).TrimStart(';')), 'User'); 'added the folder to your PATH: open a new terminal and try  atf version' }"
rem .atf files: ATF is the program that Open with uses for them, and they show the ATF icon.
reg add "HKCU\Software\Classes\.atf" /ve /d "ATF.File" /f >nul || exit /b 1
reg add "HKCU\Software\Classes\ATF.File" /ve /d "ATF program" /f >nul || exit /b 1
reg add "HKCU\Software\Classes\ATF.File\DefaultIcon" /ve /d "\"%DEST%\atf.ico\",0" /f >nul || exit /b 1
reg add "HKCU\Software\Classes\ATF.File\shell\open\command" /ve /d "\"%DEST%\atf.exe\" run \"%%1\"" /f >nul || exit /b 1
reg add "HKCU\Software\Classes\.atf\OpenWithProgids" /v ATF.File /t REG_NONE /f >nul || exit /b 1
rem Windows keeps the choice made in Open with in UserChoice. If that names another program, only the user can change it.
reg query "%UC%" >nul 2>nul && (reg query "%UC%" /v ProgId | find "ATF.File" >nul || echo Windows has another default program for .atf: right-click a .atf file, choose Open with, pick ATF and tick Always use this app)
echo .atf files now open with ATF
