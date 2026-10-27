@echo off
rem Removes what install.cmd added: the folder %LOCALAPPDATA%\atf and its entry in the user PATH.
setlocal
set "DEST=%LOCALAPPDATA%\atf"
if exist "%DEST%" rmdir /s /q "%DEST%"
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$d = Join-Path $env:LOCALAPPDATA 'atf';" ^
  "$p = [Environment]::GetEnvironmentVariable('Path', 'User'); if ($null -eq $p) { $p = '' };" ^
  "$parts = @($p -split ';' | Where-Object { $_ -ne '' -and $_ -ne $d });" ^
  "[Environment]::SetEnvironmentVariable('Path', ($parts -join ';'), 'User'); 'ATF was removed'"
