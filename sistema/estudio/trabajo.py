"""El trabajo en curso de cada hilo, y cómo detenerlo (Pablo, 11-nov: «poner algo que nos diga absolutamente qué está haciendo en
cada momento y cómo decirle que no»). Un trabajo de la app (preparar, dirigir, render) corre en un hilo del servidor y lanza
procesos largos (ffmpeg, `claude -p`). Detenerlo son dos cosas: matar el proceso que tenga abierto y que el siguiente paso no
arranque. Lo primero lo hace `correr` (un `subprocess.run` que queda anotado a nombre del trabajo); lo segundo, `revisar`, que el
servidor llama en cada aviso de avance. Fuera de la app (CLI, pruebas) no hay trabajo: `correr` es un `subprocess.run` normal."""
import subprocess
import threading

_hilo = threading.local()
_CANDADO = threading.Lock()
_PROCESOS: dict = {}     # id del trabajo → procesos que tiene abiertos ahora
_DETENIDOS: set = set()  # trabajos que la persona mandó detener


class Detenido(RuntimeError):
    """La persona detuvo el trabajo: no es un error."""

    def __init__(self):
        super().__init__("Detenido: lo paraste tú.")


def entrar(tid: str | None) -> None:
    """Este hilo trabaja para `tid` (lo llama el servidor al arrancar el hilo del trabajo)."""
    _hilo.tid = tid


def actual() -> str | None:
    return getattr(_hilo, "tid", None)


def heredar(fn):
    """Para el hilo que lanza un trabajo (el carril del video en `preparar`): corre a nombre del mismo trabajo."""
    tid = actual()

    def envuelto(*a, **k):
        entrar(tid)
        return fn(*a, **k)
    return envuelto


def revisar() -> None:
    """Corta aquí si el trabajo de este hilo fue detenido."""
    if actual() is not None and actual() in _DETENIDOS:
        raise Detenido()


def correr(cmd, check=False, timeout=None, **kw) -> subprocess.CompletedProcess:
    """`subprocess.run(cmd, …)` que `detener` puede cortar a la mitad."""
    revisar()
    if kw.pop("capture_output", False):
        kw.update(stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    tid = actual()
    p = subprocess.Popen(cmd, **kw)
    with _CANDADO:
        _PROCESOS.setdefault(tid, []).append(p)
    try:
        salida, error = p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        p.kill()
        p.communicate()
        raise
    finally:
        with _CANDADO:
            _PROCESOS[tid].remove(p)
    revisar()
    if check and p.returncode:
        raise subprocess.CalledProcessError(p.returncode, cmd, salida, error)
    return subprocess.CompletedProcess(cmd, p.returncode, salida, error)


def detener(tid: str) -> None:
    """Marca el trabajo como detenido y cierra lo que tenga abierto. El hilo termina solo, en su siguiente `revisar`."""
    _DETENIDOS.add(tid)
    with _CANDADO:
        abiertos = list(_PROCESOS.get(tid, []))
    for p in abiertos:
        p.terminate()


def soltar(tid: str) -> None:
    """El trabajo terminó: se olvida su marca."""
    _DETENIDOS.discard(tid)
    with _CANDADO:
        _PROCESOS.pop(tid, None)
