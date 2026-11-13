"""Lo que cambia entre Windows y POSIX, en un solo lugar: si un proceso vive, el candado de un archivo y el modo UTF-8 de Python."""
import contextlib
import os
import sys
import time

STILL_ACTIVE = 259   # GetExitCodeProcess de un proceso que sigue corriendo


def proceso_vivo(pid, windows: bool | None = None) -> bool:
    """True si el proceso `pid` sigue corriendo. En Windows `os.kill(pid, 0)` no consulta: manda una señal de verdad."""
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return False
    if pid <= 0:
        return False
    if (os.name == "nt") if windows is None else windows:
        import ctypes
        k32 = ctypes.windll.kernel32
        k32.OpenProcess.restype = ctypes.c_void_p
        h = k32.OpenProcess(0x1000, False, pid)   # PROCESS_QUERY_LIMITED_INFORMATION
        if not h:
            return False
        try:
            codigo = ctypes.c_ulong()
            return bool(k32.GetExitCodeProcess(ctypes.c_void_p(h), ctypes.byref(codigo))) and codigo.value == STILL_ACTIVE
        finally:
            k32.CloseHandle(ctypes.c_void_p(h))
    try:
        os.kill(pid, 0)
    except PermissionError:
        return True   # existe, es de otro usuario
    except OSError:
        return False
    return True


@contextlib.contextmanager
def candado(f, espera_s: float = 60):
    """Candado exclusivo sobre un archivo ya abierto (`open(..., "r+")`), mientras dure el bloque: dos procesos no lo escriben a la vez.
    POSIX: flock. Windows: msvcrt.locking sobre el primer byte (se reintenta hasta `espera_s`)."""
    if os.name != "nt":
        import fcntl
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            yield
        finally:
            f.flush()   # lo escrito tiene que estar en disco ANTES de soltar el candado, o el siguiente lee a medias
            fcntl.flock(f, fcntl.LOCK_UN)
        return
    import msvcrt
    pos = f.tell()
    limite = time.time() + espera_s
    while True:
        try:
            f.seek(0)
            msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
            break
        except OSError:
            if time.time() > limite:
                raise
            time.sleep(.1)
    f.seek(pos)
    try:
        yield
    finally:
        f.flush()
        f.seek(0)
        with contextlib.suppress(OSError):
            msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)


def relanzar_utf8(argv: list[str], windows: bool | None = None, utf8_activo: bool | None = None) -> list[str] | None:
    """Windows lee y escribe texto en cp1252 si nadie dice lo contrario y los .md del sistema (acentos, ñ) revientan. Devuelve la orden
    que relanza el estudio con el modo UTF-8 de Python (`-X utf8`) o None si no hace falta. Los procesos hijos heredan PYTHONUTF8."""
    nt = (os.name == "nt") if windows is None else windows
    activo = bool(sys.flags.utf8_mode) if utf8_activo is None else utf8_activo
    if not nt or activo:
        return None
    return [sys.executable, "-X", "utf8", "-m", "estudio.cli", *argv]
