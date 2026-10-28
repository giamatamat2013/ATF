@echo off
rem Removes what install.cmd added: the folder %LOCALAPPDATA%\atf, its entry in the user PATH
rem and the .atf file association.
setlocal
set "DEST=%LOCALAPPDATA%\atf"
set "UC=HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\.atf\UserChoice"
if exist "%DEST%" rmdir /s /q "%DEST%"
reg delete "HKCU\Software\Classes\ATF.File" /f >nul 2>nul
reg delete "HKCU\Software\Classes\.atf\OpenWithProgids" /v ATF.File /f >nul 2>nul
reg query "HKCU\Software\Classes\.atf" /ve 2>nul | find "ATF.File" >nul && reg delete "HKCU\Software\Classes\.atf" /f >nul
reg query "%UC%" /v ProgId 2>nul | find "ATF.File" >nul && reg delete "%UC%" /f >nul
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$d = Join-Path $env:LOCALAPPDATA 'atf';" ^
  "$p = [Environment]::GetEnvironmentVariable('Path', 'User'); if ($null -eq $p) { $p = '' };" ^
  "$parts = @($p -split ';' | Where-Object { $_ -ne '' -and $_ -ne $d });" ^
  "[Environment]::SetEnvironmentVariable('Path', ($parts -join ';'), 'User'); 'ATF was removed'"
