@echo off
rem Instalador de un paso (Windows). Copia la app a %LOCALAPPDATA%\Pro Studio y sigue desde alli (la carpeta descargada se puede borrar).
rem Solo consigue uv; TODO lo demas lo hace "uv run estudio instalar". Se puede correr las veces que quieras. TPS_EN_SITIO=1 instala donde esta.
cd /d "%~dp0"
rem Python en modo UTF-8: los textos del sistema llevan acentos y en Windows (cp1252) revientan
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "DEST=%LOCALAPPDATA%\Pro Studio"
if not defined TPS_EN_SITIO if /i not "%CD%\"=="%DEST%\" goto :copiar
goto :instalar

:copiar
echo Pro Studio: copiando la app...
rem Reinstalar NO pisa lo aprendido: si el destino ya tiene perfil\ y librerias\estilos\, de esas dos carpetas solo entran los archivos
rem NUEVOS (robocopy /XC /XN /XO salta los que ya existen). El presets.json del paquete se deja aparte y "estudio instalar" lo fusiona.
set "EXCL="
set "P1="
set "P2="
if exist "%DEST%\perfil" set "P1=1"
if exist "%DEST%\librerias\estilos" set "P2=1"
if defined P1 set EXCL=%EXCL% "%CD%\perfil"
if defined P2 set EXCL=%EXCL% "%CD%\librerias\estilos"
if defined P2 if not exist "%DEST%\.tps" mkdir "%DEST%\.tps"
if defined P2 copy /y "%CD%\librerias\estilos\presets.json" "%DEST%\.tps\presets-paquete.json" >nul
robocopy "%CD%" "%DEST%" /E /XD proyectos .tps .venv %EXCL% /NFL /NDL /NJH /NJS /NP >nul
if errorlevel 8 goto :error
if defined P1 robocopy "%CD%\perfil" "%DEST%\perfil" /E /XC /XN /XO /NFL /NDL /NJH /NJS /NP >nul
if defined P1 if errorlevel 8 goto :error
if defined P2 robocopy "%CD%\librerias\estilos" "%DEST%\librerias\estilos" /E /XC /XN /XO /NFL /NDL /NJH /NJS /NP >nul
if defined P2 if errorlevel 8 goto :error
call "%DEST%\instalar.bat"
exit /b

:instalar
if not exist .tps mkdir .tps
set "LOG=%CD%\.tps\instalacion.log"
where uv >nul 2>nul
if errorlevel 1 (
  echo Pro Studio: instalando el gestor de Python ^(1 de 3^)
  powershell -ExecutionPolicy ByPass -NoProfile -Command "irm https://astral.sh/uv/install.ps1 | iex" >>"%LOG%" 2>&1
  set "PATH=%USERPROFILE%\.local\bin;%PATH%"
)
echo Pro Studio: instalando el motor ^(2 de 3^)
uv sync --quiet >>"%LOG%" 2>&1 || goto :error
echo Pro Studio: bajando herramientas y modelos; la primera vez tarda ^(3 de 3^)
uv run --quiet estudio instalar 2>>"%LOG%"
echo Pro Studio: abriendo la app
call abrir.bat
exit /b 0
:error
powershell -NoProfile -Command "Add-Type -AssemblyName System.Windows.Forms; [void][System.Windows.Forms.MessageBox]::Show('No se pudo instalar Pro Studio. Copia el archivo instalacion.log de la carpeta .tps y mandaselo a Claude.','Pro Studio')"
exit /b 1
