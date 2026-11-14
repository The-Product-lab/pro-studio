@echo off
rem Abre Pro Studio (doble clic).
cd /d "%~dp0"
rem Python en modo UTF-8: los textos del sistema llevan acentos y en Windows (cp1252) revientan
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "PATH=%USERPROFILE%\.local\bin;%PATH%"
uv run --quiet estudio servir
