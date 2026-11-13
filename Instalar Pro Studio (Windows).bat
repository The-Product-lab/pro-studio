@echo off
rem Pro Studio: instalador para Windows (doble clic). Solo revisa que el ZIP este extraido; TODO lo demas lo hace sistema\instalar.bat.
cd /d "%~dp0"
if not exist "sistema\instalar.bat" (
  powershell -NoProfile -Command "Add-Type -AssemblyName System.Windows.Forms; [void][System.Windows.Forms.MessageBox]::Show('Primero extrae el ZIP: clic derecho - Extraer todo. Despues abre este archivo otra vez.','Pro Studio')"
  exit /b 1
)
attrib +h "sistema" >nul 2>nul
call "sistema\instalar.bat"
