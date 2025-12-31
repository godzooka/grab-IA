@echo off
REM grab-IA CLI Wrapper for Windows
REM Automatically sets up environment and runs CLI

setlocal EnableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
set "VENV_DIR=%SCRIPT_DIR%venv"
set "PYTHON_BIN=%VENV_DIR%\Scripts\python.exe"

REM Check if virtual environment exists
if not exist "%VENV_DIR%" (
    echo Warning: Virtual environment not found. Creating...
    python -m venv "%VENV_DIR%"
    echo Virtual environment created
    
    echo Installing dependencies...
    "%VENV_DIR%\Scripts\pip.exe" install -q -r "%SCRIPT_DIR%requirements.txt"
    echo Dependencies installed
)

REM Run CLI with all arguments passed through
"%PYTHON_BIN%" "%SCRIPT_DIR%grabia_cli.py" %*
