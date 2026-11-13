"""Comandos de Windows desde WSL. Un lote desatendido corre sin el PATH de Windows (07-nov: `FileNotFoundError: 'attrib.exe'`
mató el lote), así que se busca por ruta absoluta y un fallo de entorno nunca detiene el trabajo."""
import shutil
import subprocess
from pathlib import Path

SYSTEM32 = Path("/mnt/c/Windows/System32")
RUTAS = {"powershell.exe": SYSTEM32 / "WindowsPowerShell" / "v1.0" / "powershell.exe"}


def en_wsl() -> bool:
    """True dentro de WSL (Ubuntu sobre Windows)."""
    try:
        return "microsoft" in Path("/proc/version").read_text().lower()
    except OSError:
        return False


def windows_exe(nombre: str) -> str | None:
    """Ruta del ejecutable de Windows: primero el PATH, si no la carpeta estándar. None si no existe (fuera de WSL)."""
    encontrado = shutil.which(nombre)
    if encontrado:
        return encontrado
    candidata = RUTAS.get(nombre, SYSTEM32 / nombre)
    return str(candidata) if candidata.exists() else None


def correr_windows(nombre: str, args: list, timeout=60) -> subprocess.CompletedProcess | None:
    """Corre un ejecutable de Windows. None si no se pudo (no existe, tardó demasiado, falló al lanzar): nunca lanza."""
    exe = windows_exe(nombre)
    if not exe:
        return None
    try:
        return subprocess.run([exe, *args], capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return None
