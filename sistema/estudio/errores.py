"""Errores sin trazas: lo que ve Pablo es una frase clara en español; el detalle técnico queda solo en el registro
(`proyectos/_errores.log`, fuera de git). La app nunca muestra una traza ni el texto crudo de ffmpeg o Python.

`Aviso` es el error que YA viene dicho para la persona (qué pasó y qué hacer): llega a la pantalla tal cual. Lo que una máquina
recién instalada puede tener distinto (Claude sin sesión, disco lleno, una pieza que no bajó, un video sin editar) tiene su frase
aquí; la genérica queda solo para lo que de verdad no se conoce (13-nov: en una Mac nueva «Exportar» decía «Algo falló» por un
video que aún no estaba editado, y sin sesión de Claude decía lo mismo)."""
import errno
import subprocess
import time
import traceback

from . import config

GENERICA = "Algo falló y ya quedó anotado. Prueba de nuevo; si se repite, avísale a Isis."
SIN_SESION = ("Claude no tiene la sesión iniciada en este equipo. Abre la Terminal, escribe «claude» y entra con la cuenta de la "
              "suscripción; después vuelve a intentarlo.")
SIN_CLAUDE = "No encuentro Claude Code en este equipo. Abre otra vez «Instalar Pro Studio» para que lo instale y vuelve a intentarlo."
REINSTALAR = "A la instalación le falta una pieza. Abre otra vez «Instalar Pro Studio» (con internet) y vuelve a intentarlo."
_DISCO_LLENO = {errno.ENOSPC, getattr(errno, "EDQUOT", errno.ENOSPC)}


class Aviso(RuntimeError):
    """Un error que ya está dicho para la persona, en español y con lo que tiene que hacer. La pantalla lo muestra tal cual."""


def frase(e: BaseException) -> str:
    """Qué le decimos a Pablo. Los ValueError y FileNotFoundError que escribimos nosotros ya vienen en español claro."""
    if isinstance(e, Aviso):
        return str(e)
    if type(e).__name__ == "LimiteAgotado":   # estudio.ia (por nombre: ia importa este módulo, no al revés)
        cuando = getattr(e, "reanuda_en", None)
        return ("Claude llegó al límite de uso de la suscripción" + (f" y vuelve a las {cuando:%H:%M}" if cuando else "")
                + ". Lo ya hecho se conserva; inténtalo de nuevo cuando vuelva.")
    if isinstance(e, subprocess.CalledProcessError):
        return "No pude leer o convertir ese video. Prueba con otro archivo o vuelve a exportarlo desde la cámara."
    if isinstance(e, (ValueError, FileNotFoundError)) and _en_espanol(str(e)):
        return str(e)
    if isinstance(e, MemoryError) or (isinstance(e, OSError) and e.errno == errno.ENOMEM):
        return "Este equipo se quedó sin memoria. Cierra otros programas y prueba de nuevo."
    if isinstance(e, OSError) and e.errno in _DISCO_LLENO:
        return "El disco está lleno. Libera espacio (o borra videos viejos) y prueba de nuevo."
    if isinstance(e, PermissionError):
        return "No tengo permiso para escribir en la carpeta de Pro Studio. Cierra lo que tenga abierto ese video y prueba de nuevo."
    if isinstance(e, ImportError):
        return REINSTALAR
    if isinstance(e, (ValueError, KeyError, IndexError, TypeError)):
        return "Algo en ese video no salió como esperaba. Ya quedó anotado; prueba otra vez o con otro archivo."
    if isinstance(e, TimeoutError):
        return "Esto tardó demasiado y lo detuve. Prueba de nuevo."
    return GENERICA


def _en_espanol(texto: str) -> bool:
    """Frases nuestras: cortas, con espacios, sin rastro de Python (comillas de objeto, «invalid literal», rutas, líneas de código)."""
    t = texto.strip()
    malo = ("invalid literal", "Traceback", "object ", "line ", "'", ".py", "ffprobe", "ffmpeg", "None", "Errno")
    return 8 <= len(t) <= 200 and " " in t and not any(m in t for m in malo)


def registrar(donde: str, e: BaseException) -> None:
    """El detalle técnico, completo, al registro (nunca a la pantalla)."""
    try:
        archivo = config.PROYECTOS / "_errores.log"
        archivo.parent.mkdir(parents=True, exist_ok=True)
        with open(archivo, "a", encoding="utf-8") as f:
            f.write(f"--- {time.strftime('%Y-%m-%d %H:%M:%S')} · {donde}\n{''.join(traceback.format_exception(e))}\n")
    except OSError:
        pass   # el registro nunca debe tumbar a quien lo usa


def amable(donde: str, e: BaseException) -> str:
    """Registra el detalle y devuelve la frase para la pantalla."""
    registrar(donde, e)
    return frase(e)
