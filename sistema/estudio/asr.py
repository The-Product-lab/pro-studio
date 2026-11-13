"""Whisper: UN solo lugar que elige el dispositivo y UN solo modelo cargado para todo el estudio.

GPU (cuda, int8) si arranca; si no, CPU con aviso. Si la GPU falla a mitad de una transcripción, esa transcripción se rehace en CPU.
Las bibliotecas de CUDA (cuBLAS y cuDNN 9) vienen como paquetes pip (`nvidia-cublas-cu12`, `nvidia-cudnn-cu12`; no en Mac) y se
precargan antes de crear el modelo. `ESTUDIO_WHISPER=cpu` fuerza CPU.
"""
import ctypes
import importlib.util
import os
import sys
import threading
from pathlib import Path

from . import config

_CANDADO = threading.RLock()   # un modelo, una transcripción a la vez (la GPU de 3 GB no aguanta dos)
_estado: dict = {"modelo": None, "dispositivo": None, "sin_gpu": False}
AVISOS: list = []


def _precargar_cuda() -> None:
    """Carga cuBLAS y cuDNN de los paquetes pip para que ctranslate2 las encuentre. Falla (ImportError/OSError) si no están."""
    for paquete, patron in (("cublas", "libcublas.so.12*"), ("cudnn", "libcudnn.so.9*")):
        espec = importlib.util.find_spec(f"nvidia.{paquete}")
        if espec is None or not espec.submodule_search_locations:
            raise ImportError(f"falta el paquete nvidia-{paquete}-cu12")
        base = Path(next(iter(espec.submodule_search_locations)))
        if sys.platform == "win32":
            os.add_dll_directory(str(base / "bin"))
            continue
        libs = sorted((base / "lib").glob(patron))
        if not libs:
            raise ImportError(f"nvidia-{paquete}-cu12 no trae {patron}")
        ctypes.CDLL(str(libs[0]), mode=ctypes.RTLD_GLOBAL)


def _crear(dispositivo: str):
    from faster_whisper import WhisperModel
    return WhisperModel(str(config.WHISPER_DIR), device=dispositivo, compute_type="int8")


def _cuda_servible() -> bool:
    if _estado["sin_gpu"] or os.environ.get("ESTUDIO_WHISPER", "").lower() == "cpu":
        return False
    import ctranslate2
    if ctranslate2.get_cuda_device_count() < 1:
        return False
    _precargar_cuda()
    return True


def en_cpu() -> bool:
    """True si Whisper va a correr en el procesador (sin GPU usable): ahí pelea con todo lo demás que use el procesador."""
    if _estado["dispositivo"]:
        return _estado["dispositivo"] == "cpu"
    try:
        return not _cuda_servible()
    except Exception:  # noqa: BLE001 — sin bibliotecas de CUDA: es CPU
        return True


def modelo():
    """El modelo Whisper compartido (se crea la primera vez)."""
    with _CANDADO:
        if _estado["modelo"] is None:
            try:
                if _cuda_servible():
                    _estado["modelo"], _estado["dispositivo"] = _crear("cuda"), "cuda"
            except Exception as e:  # noqa: BLE001 — sin GPU usable: la CPU hace el mismo trabajo, más lento
                AVISOS.append(f"Whisper sin GPU ({type(e).__name__}: {str(e)[:120]}): se usa la CPU")
                print(AVISOS[-1], file=sys.stderr)
            if _estado["modelo"] is None:
                _estado["modelo"], _estado["dispositivo"] = _crear("cpu"), "cpu"
        return _estado["modelo"]


def dispositivo() -> str | None:
    return _estado["dispositivo"]


def _a_cpu(motivo: Exception) -> None:
    with _CANDADO:
        AVISOS.append(f"la GPU falló al transcribir ({type(motivo).__name__}: {str(motivo)[:120]}): se sigue en CPU")
        print(AVISOS[-1], file=sys.stderr)
        _estado.update(modelo=None, dispositivo=None, sin_gpu=True)   # no volver a intentar la GPU en este proceso


def transcribir(audio, **opciones) -> list:
    """Segmentos de Whisper (lista ya materializada, con `.words` si se pidió). Si la GPU falla, se rehace en CPU."""
    with _CANDADO:
        m = modelo()
        try:
            return list(m.transcribe(audio, language="es", **opciones)[0])
        except Exception as e:  # noqa: BLE001
            if _estado["dispositivo"] != "cuda":
                raise
            _a_cpu(e)
            return list(modelo().transcribe(audio, language="es", **opciones)[0])
