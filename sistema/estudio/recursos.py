"""Descarga lo pesado una sola vez (ffmpeg, modelos). Idempotente: lo que ya existe no se vuelve a bajar."""
import contextlib
import shutil
import threading
import urllib.request

from . import config

LATIDO_S = 30


@contextlib.contextmanager
def latido(avance=print, cada_s: float | None = None):
    """Señal de vida mientras baja algo grande: con internet lento son minutos y una pantalla quieta parece colgada (10-nov)."""
    fin, n = threading.Event(), 0

    def avisar():
        nonlocal n
        paso = LATIDO_S if cada_s is None else cada_s
        while not fin.wait(paso):
            n += 1
            avance(f"  …sigue bajando ({round(n * paso / 60, 1):g} min; es normal)")
    hilo = threading.Thread(target=avisar, daemon=True)
    hilo.start()
    try:
        yield
    finally:
        fin.set()
        hilo.join()


def ffmpeg() -> tuple[str, str]:
    import io
    from static_ffmpeg import run
    with contextlib.redirect_stdout(io.StringIO()):   # su barra de descarga ensucia el instalador; el doctor confirma que quedó
        return run.get_or_fetch_platform_executables_else_raise()


def rvm() -> None:
    if config.RVM_ONNX.exists():
        return
    config.MODELOS.mkdir(parents=True, exist_ok=True)
    tmp = config.RVM_ONNX.with_suffix(".part")
    with urllib.request.urlopen(config.RVM_URL, timeout=120) as r, open(tmp, "wb") as f:
        shutil.copyfileobj(r, f)
    tmp.replace(config.RVM_ONNX)


def caras() -> None:
    """Detector de caras (YuNet, OpenCV Zoo; 230 KB): ubica a la persona en la toma. Se comprueba que sea el archivo esperado."""
    import hashlib
    if config.CARAS_ONNX.exists():
        return
    config.MODELOS.mkdir(parents=True, exist_ok=True)
    tmp = config.CARAS_ONNX.with_suffix(".part")
    with urllib.request.urlopen(config.CARAS_URL, timeout=120) as r, open(tmp, "wb") as f:
        shutil.copyfileobj(r, f)
    if hashlib.sha256(tmp.read_bytes()).hexdigest() != config.CARAS_SHA256:
        tmp.unlink()
        raise RuntimeError("el detector de caras no bajó completo: vuelve a correr el instalador")
    tmp.replace(config.CARAS_ONNX)


def whisper() -> None:
    if (config.WHISPER_DIR / "model.bin").exists():
        return
    from faster_whisper.utils import download_model
    download_model(config.WHISPER_MODELO, output_dir=str(config.WHISPER_DIR))


def instalar() -> None:
    for nombre, paso in (("ffmpeg", ffmpeg), ("detector de caras", caras), ("personas en fotos (RVM)", rvm), ("whisper large-v3", whisper)):
        print(f"· {nombre}…", flush=True)
        with latido(lambda m: print(m, flush=True)):
            paso()
    print("✓ recursos listos")
