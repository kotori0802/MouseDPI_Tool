@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

rem First-time setup for GitHub Source ZIP / clean clone.
rem Creates .venv and installs the UI runtime extra only: pip install -e ".[ui]"
rem Supported Python: >=3.11,<3.14 (from pyproject.toml). Does not install [dev].
rem Does not download Python, require admin elevation, or alter system PATH.

echo Mouse DPI Tool — first-time install
echo Repository: %CD%
echo.

set "HOSTPY="

rem Prefer Windows py launcher with project-compatible minors (newest first).
rem Use !HOSTPY! so the FOR block sees assignments (CMD parse-time % expansion).
for %%V in (3.13 3.12 3.11) do (
  if "!HOSTPY!"=="" (
    where py >nul 2>&1
    if not errorlevel 1 (
      for /f "delims=" %%I in ('py -%%V -c "import sys; print(sys.executable)" 2^>nul') do (
        if exist "%%I" set "HOSTPY=%%I"
      )
    )
  )
)

rem Fallback: `python` on PATH if it meets requires-python.
if not defined HOSTPY (
  where python >nul 2>&1
  if not errorlevel 1 (
    python -c "import sys; raise SystemExit(0 if (3,11) <= sys.version_info[:2] < (3,14) else 1)" 1>nul 2>nul
    if not errorlevel 1 (
      for /f "delims=" %%I in ('python -c "import sys; print(sys.executable)" 2^>nul') do set "HOSTPY=%%I"
    )
  )
)

if not defined HOSTPY (
  echo ERROR: No supported Python interpreter was found.
  echo.
  echo This project requires Python ^>=3.11 and ^<3.14 ^(for example 3.11, 3.12, or 3.13^).
  echo Install a matching Python from https://www.python.org/downloads/
  echo ^(enable "Add python.exe to PATH" / py launcher if offered^), then re-run:
  echo   INSTALL_Mouse_DPI_Tool.cmd
  echo.
  echo This installer does not download Python, request Administrator rights,
  echo or modify system PATH.
  goto :fail
)

echo Using host Python:
echo   %HOSTPY%
"%HOSTPY%" -c "import sys; print('  version', sys.version.split()[0])"
if errorlevel 1 goto :fail

if not exist "%~dp0.venv\Scripts\python.exe" (
  echo Creating virtual environment: .venv
  "%HOSTPY%" -m venv "%~dp0.venv"
  if errorlevel 1 (
    echo ERROR: Failed to create .venv
    goto :fail
  )
) else (
  echo Reusing existing virtual environment: .venv
  "%~dp0.venv\Scripts\python.exe" -c "import sys; print('  existing .venv Python', sys.version.split()[0]); raise SystemExit(0 if (3,11) <= sys.version_info[:2] < (3,14) else 1)"
  if errorlevel 1 (
    echo.
    echo Existing .venv uses an unsupported Python version.
    echo Mouse DPI Tool requires Python ^>=3.11,^<3.14.
    echo Remove the existing .venv and run INSTALL_Mouse_DPI_Tool.cmd again.
    goto :fail
  )
)

set "VENVPY=%~dp0.venv\Scripts\python.exe"
if not exist "%VENVPY%" (
  echo ERROR: .venv\Scripts\python.exe was not created.
  goto :fail
)

echo Upgrading pip inside .venv ...
"%VENVPY%" -m pip install --upgrade pip
if errorlevel 1 (
  echo ERROR: pip upgrade failed.
  goto :fail
)

echo Installing Mouse DPI Tool UI runtime: pip install -e ".[ui]"
"%VENVPY%" -m pip install -e ".[ui]"
if errorlevel 1 (
  echo ERROR: Package install failed.
  echo Check network access to PyPI and that you extracted the full source tree.
  goto :fail
)

echo Verifying installation ...
"%VENVPY%" -c "import mouse_dpi_tool, PySide6; print('  mouse_dpi_tool', mouse_dpi_tool.__version__); print('  PySide6 ok')"
if errorlevel 1 (
  echo ERROR: Import verification failed.
  goto :fail
)

"%VENVPY%" -m mouse_dpi_tool version
if errorlevel 1 (
  echo ERROR: CLI version check failed.
  goto :fail
)

echo.
echo Installation complete.
echo Run RUN_Mouse_DPI_Tool.cmd to start Mouse DPI Tool.
echo.
exit /b 0

:fail
echo.
echo Installation did not complete.
pause
exit /b 1
