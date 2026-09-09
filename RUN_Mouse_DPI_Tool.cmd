@echo off
setlocal EnableExtensions
cd /d "%~dp0"

rem Canonical entry: mouse_dpi_tool.cli:main → `python -m mouse_dpi_tool ui`
rem (same as console script mouse-dpi-tool). No alternate startup architecture.

set "PYEXE="
if exist "%~dp0.venv\Scripts\python.exe" (
  set "PYEXE=%~dp0.venv\Scripts\python.exe"
) else (
  where py >nul 2>&1
  if not errorlevel 1 (
    for /f "delims=" %%I in ('py -3 -c "import sys; print(sys.executable)" 2^>nul') do set "PYEXE=%%I"
  )
)
if not defined PYEXE (
  where python >nul 2>&1
  if not errorlevel 1 (
    for /f "delims=" %%I in ('python -c "import sys; print(sys.executable)" 2^>nul') do set "PYEXE=%%I"
  )
)

if not defined PYEXE (
  echo Mouse DPI Tool launcher: Python was not found.
  echo Create a virtual environment and install the UI extra, then re-run this script:
  echo   python -m venv .venv
  echo   .venv\Scripts\python.exe -m pip install -e ".[ui]"
  exit /b 1
)

"%PYEXE%" -c "import mouse_dpi_tool" 1>nul 2>nul
if errorlevel 1 (
  echo Mouse DPI Tool launcher: package not importable with:
  echo   %PYEXE%
  echo From the repository root, install once ^(no auto-install is performed by this script^):
  echo   "%PYEXE%" -m pip install -e ".[ui]"
  exit /b 1
)

"%PYEXE%" -c "import PySide6" 1>nul 2>nul
if errorlevel 1 (
  echo Mouse DPI Tool launcher: PySide6 is not available.
  echo Install the UI extra:
  echo   "%PYEXE%" -m pip install -e ".[ui]"
  exit /b 1
)

"%PYEXE%" -m mouse_dpi_tool ui
exit /b %ERRORLEVEL%
