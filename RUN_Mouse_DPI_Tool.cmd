@echo off
setlocal EnableExtensions
cd /d "%~dp0"

rem Launch only. Does not create .venv or run pip.
rem Canonical entry: mouse_dpi_tool.cli:main → `python -m mouse_dpi_tool ui`
rem Prepare the environment first with INSTALL_Mouse_DPI_Tool.cmd

set "VENVPY=%~dp0.venv\Scripts\python.exe"

if not exist "%VENVPY%" (
  echo Mouse DPI Tool is not installed yet.
  echo Run INSTALL_Mouse_DPI_Tool.cmd first.
  echo.
  echo The GitHub Source code ZIP does not include a prepared Python environment.
  echo.
  pause
  exit /b 1
)

"%VENVPY%" -c "import mouse_dpi_tool" 1>nul 2>nul
if errorlevel 1 (
  echo Mouse DPI Tool is not installed yet.
  echo Run INSTALL_Mouse_DPI_Tool.cmd first.
  echo.
  pause
  exit /b 1
)

"%VENVPY%" -c "import PySide6" 1>nul 2>nul
if errorlevel 1 (
  echo Mouse DPI Tool is not installed yet.
  echo The project UI dependency ^(PySide6^) is missing from .venv.
  echo Run INSTALL_Mouse_DPI_Tool.cmd first.
  echo.
  pause
  exit /b 1
)

"%VENVPY%" -m mouse_dpi_tool ui
exit /b %ERRORLEVEL%
