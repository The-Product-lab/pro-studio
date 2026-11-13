"""Vista previa AL INSTANTE del video que Pablo subió, mientras el editor prepara todo lo demás.

Pablo (04-nov): «cuando quiera escoger el estilo, los colores y demás, me muestre de una la imagen estática del video que subí;
el primero como que transcribe antes y luego el pantallazo».

Se toma un pedazo de 2 s del crudo (copia directa, sin recodificar todo el video), se normaliza solo ese pedazo con la misma
cadena del editor (tamaño) y sobre él se dibuja el estilo elegido con el motor real (`previas.con_toma`): su letra, su
acento, su subtítulo y el color de cine que se elija; la segunda vista es una muestra del estilo a pantalla completa. No transcribe ni
recorta a la persona: la persona va en su toma completa.
"""
import json
import subprocess
import threading
from pathlib import Path


from . import config, ingesta

FRASE = ["así", "se", "verá", "tu", "video", "con", "este", "estilo"]


CUADROS = (25, 50)   # los cuadros del trozo que `previas.con_toma` dibuja (persona y apoyo)


def carpeta_de(nombre: str) -> Path:
    return config.PROYECTOS / "_rapida" / nombre


_CANDADO = threading.Lock()   # un video pesado (S-Log) tarda: dos peticiones a la vez no deben pisarse la misma carpeta


def preparar(video: Path, nombre: str) -> Path:
    """Pedazo de 2 s del crudo, listo para el motor (una sola vez por video)."""
    with _CANDADO:
        return _preparar(video, nombre)


def _preparar(video: Path, nombre: str) -> Path:
    c = carpeta_de(nombre)
    if (c / "fuente.json").exists():
        return c
    c.mkdir(parents=True, exist_ok=True)
    ffmpeg, ffprobe = config.ffmpeg()
    dur = float(subprocess.run([ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(video)],
                               capture_output=True, text=True).stdout.strip() or 10)
    trozo = c / "trozo.mp4"
    subprocess.run([ffmpeg, "-v", "error", "-y", "-ss", f"{max(0, dur * .35):.2f}", "-i", str(video), "-t", "2", "-c", "copy",
                    str(trozo)], check=True)
    meta = ingesta.sondear(trozo, c, lambda *_: None)
    (c / "fuente.json").write_text(json.dumps(meta))
    paso = 2.0 / len(FRASE)
    (c / "palabras.json").write_text(json.dumps([{"w": w, "s": round(.1 + k * paso, 2), "e": round(.1 + (k + .8) * paso, 2)}
                                                 for k, w in enumerate(FRASE)], ensure_ascii=False))
    return c
