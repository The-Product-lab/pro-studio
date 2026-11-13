"""Errores sin trazas: lo que ve Pablo es una frase clara en español; el detalle técnico queda solo en el registro
(`proyectos/_errores.log`, fuera de git). La app nunca muestra una traza ni el texto crudo de ffmpeg o Python."""
import subprocess
import time
import traceback

from . import config


def frase(e: BaseException) -> str:
    """Qué le decimos a Pablo. Los ValueError y FileNotFoundError que escribimos nosotros ya vienen en español claro."""
    if isinstance(e, subprocess.CalledProcessError):
        return "No pude leer o convertir ese video. Prueba con otro archivo o vuelve a exportarlo desde la cámara."
    if isinstance(e, (ValueError, FileNotFoundError)) and _en_espanol(str(e)):
        return str(e)
    if isinstance(e, (ValueError, KeyError, IndexError, TypeError)):
        return "Algo en ese video no salió como esperaba. Ya quedó anotado; prueba otra vez o con otro archivo."
    if isinstance(e, TimeoutError):
        return "Esto tardó demasiado y lo detuve. Prueba de nuevo."
    return "Algo falló y ya quedó anotado. Prueba de nuevo; si se repite, avísale a Isis."


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
