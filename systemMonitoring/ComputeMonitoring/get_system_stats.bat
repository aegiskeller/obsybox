@echo off
REM get_system_stats.bat - wrapper that runs get_system_stats.py in the same directory
SETLOCAL
set SCRIPT_DIR=%~dp0
python "%SCRIPT_DIR%get_system_stats.py" %*
ENDLOCAL
