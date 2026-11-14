"""Ingesta: video crudo → carpeta de proyecto con fuente.json, palabras.json y la posición de la persona (todo con caché).

Cualquier video que no sea vertical 1080×1920 a 30 fps (cámara 4K horizontal, 60 fps…) se NORMALIZA primero a `fuente.mp4`:
recorte vertical 9:16 sobre la persona y 30 fps. El color NO se toca (el video se usa tal cual viene): el único color es el LUT
que elija la persona, y lo aplica `color.cubo` / `color.filtro` en el render y las vistas.
"""
import hashlib
import itertools
import json
import os
import re
import shutil
import subprocess
import threading
import time
import wave
from pathlib import Path

import numpy as np

from . import color, config, persona, trabajo

W, H, FPS = config.W, config.H, config.FPS


def _probar(video: Path) -> dict:
    _, ffprobe = config.ffmpeg()
    info = json.loads(subprocess.run([ffprobe, "-v", "error", "-select_streams", "v:0",
                                      "-show_entries", "stream=width,height,color_transfer,r_frame_rate:stream_side_data=rotation"
                                      ":format=duration", "-of", "json", str(video)],
                                     capture_output=True, text=True, check=True).stdout)
    audio = subprocess.run([ffprobe, "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0",
                            str(video)], capture_output=True, text=True).stdout.strip()
    if not audio:
        raise ValueError("el video no tiene audio")
    s = info["streams"][0]
    num, den = (int(x) for x in s["r_frame_rate"].split("/"))
    ancho, alto = s["width"], s["height"]
    # la rotación puede no ser el primer dato: un iPhone en HDR (Dolby Vision) pone antes su propio registro (11-nov: un vertical 4K
    # se leyó como horizontal y se le recortó una tajada de la esquina)
    rotacion = next((abs(int(d["rotation"])) for d in s.get("side_data_list", []) if "rotation" in d), 0)
    if rotacion in (90, 270):   # cámara girada: ffmpeg entrega los cuadros ya rotados
        ancho, alto = alto, ancho
    return {"ancho": ancho, "alto": alto, "fps": num / den, "duracion": float(info["format"]["duration"]),
            "trc": s.get("color_transfer") or "", "hdr": s.get("color_transfer") in color.HDR}


def _duracion(video: Path) -> float:
    """Solo la duración (sin detectar color): para medir el normalizado y el `fuente.json` provisional."""
    _, ffprobe = config.ffmpeg()
    return float(subprocess.run([ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(video)],
                                capture_output=True, text=True, check=True).stdout.strip())


def _entero(texto: str) -> int | None:
    """El primer número entero de la salida de ffprobe; None si vino vacía o como «N/A»."""
    m = re.search(r"\d+", texto or "")
    return int(m.group()) if m and int(m.group()) > 0 else None


def _cuadros(video: Path) -> int:
    """Cuántos cuadros tiene el video. ffprobe no siempre entrega el dato (S-Log de la Sony, contenedores sin índice):
    se prueba con el contador de la cabecera, luego contando paquetes, luego cuadros, y al final duración × fps."""
    _, ffprobe = config.ffmpeg()
    for extra in (["-show_entries", "stream=nb_frames"], ["-count_packets", "-show_entries", "stream=nb_read_packets"],
                  ["-count_frames", "-show_entries", "stream=nb_read_frames"]):
        r = subprocess.run([ffprobe, "-v", "error", "-select_streams", "v:0", *extra, "-of", "csv=p=0", str(video)],
                           capture_output=True, text=True)
        n = _entero(r.stdout)
        if n:
            return n
    p = _probar(video)
    return max(1, round(p["duracion"] * p["fps"]))


def normalizar(video: Path, p: dict, carpeta: Path, avance=print) -> Path:
    """→ carpeta/fuente.mp4 vertical 1080×1920, 30 fps, en Rec.709 con el color del original (el HDR se convierte de verdad:
    `color.hdr_a_sdr`)."""
    destino = carpeta / "fuente.mp4"
    if destino.exists():
        return destino
    ffmpeg, _ = config.ffmpeg()
    vf = []
    if p["ancho"] * 16 > p["alto"] * 9 + 8:   # más ancho que 9:16 → recorte vertical sobre la persona
        alto = p["alto"]
        ancho = int(alto * 9 / 16) // 2 * 2
        cx = persona.centro(video, p, carpeta, avance)
        x0 = int(min(max(cx - ancho / 2, 0), p["ancho"] - ancho)) // 2 * 2
        vf.append(f"crop={ancho}:{alto}:{x0}:0")
    vf.append(f"scale={W}:{H}:flags=lanczos")
    if p["hdr"]:   # ya en 1080×1920: la conversión de HDR trabaja sobre la cuarta parte de los píxeles de un 4K
        vf += [color.hdr_a_sdr(p.get("trc", "")), "scale=out_color_matrix=bt709:out_range=tv"]
    vf += [f"fps={FPS}", "format=yuv420p"]
    if p["hdr"]:   # ya no es HLG: que el archivo no lo diga (las marcas viajan con los cuadros; como opción de salida ffmpeg 8 las ignora)
        vf.append("setparams=color_trc=bt709:color_primaries=bt709:colorspace=bt709")
    avance(f"normalizando a vertical {W}×{H} · {FPS} fps (la primera vez tarda)…")
    tmp = destino.with_name("fuente.part.mp4")
    for intento in (1, 2):   # ffmpeg puede cortar la lectura (memoria justa, disco de red) y salir sin error: se mide, no se confía
        trabajo.correr([ffmpeg, "-v", "error", "-y", "-i", str(video), "-vf", ",".join(vf), "-c:v", "libx264", "-preset", "medium",
                        "-crf", "15", "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-ac", "2",
                        str(tmp)], check=True, cwd=carpeta)   # el paso más largo de un 4K: se puede detener desde la app
        if _completo(tmp, p["duracion"]):
            break
        tmp.unlink(missing_ok=True)
        if intento == 2:
            raise RuntimeError("la normalización salió más corta que el video original (se cortó la lectura): vuelve a intentarlo")
        avance("la normalización salió incompleta; se repite una vez…")
    tmp.replace(destino)
    return destino


def _completo(normalizado: Path, duracion_original: float) -> bool:
    return normalizado.exists() and _duracion(normalizado) >= duracion_original - 1.0


def sondear(video: Path, carpeta: Path, avance=print) -> dict:
    p = _probar(video)
    listo = (p["ancho"], p["alto"]) == (W, H) and abs(p["fps"] - FPS) < .5 and not p["hdr"]   # un HDR siempre se convierte, aunque ya venga vertical
    usar = video if listo else normalizar(video, p, carpeta, avance)
    return {"video": str(Path(usar).resolve()), "original": str(Path(video).resolve()), "cuadros": _cuadros(usar),
            "hdr": False}   # lo que sale de aquí ya es Rec.709 (la clave queda por los proyectos viejos, que el motor sigue leyendo)


def transcribir(video: Path, destino: Path) -> list:
    if destino.exists():
        return json.loads(destino.read_text())
    ffmpeg, _ = config.ffmpeg()
    wav = destino.with_suffix(".wav")
    subprocess.run([ffmpeg, "-v", "error", "-y", "-i", str(video), "-vn", "-ac", "1", "-ar", "16000", str(wav)], check=True)
    with wave.open(str(wav)) as w:
        audio = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
    from . import asr
    segs = asr.transcribir(audio, word_timestamps=True, beam_size=5, condition_on_previous_text=False)
    palabras = [{"w": x.word.strip(), "s": round(x.start, 2), "e": round(x.end, 2), "p": round(x.probability, 2)}
                for s in segs for x in s.words]
    destino.write_text(json.dumps(palabras, ensure_ascii=False))
    wav.unlink()
    return palabras


def es_provisional(carpeta: Path) -> bool:
    """`fuente.json` provisional = solo sirve para el guion (el audio del original); aún no hay `fuente.mp4` ni alfa."""
    f = Path(carpeta) / "fuente.json"
    return f.exists() and bool(json.loads(f.read_text()).get("provisional"))


def _fuente_provisional(video: Path) -> dict:
    """Lo mínimo para que montaje y machote lean el audio del original (mismo timeline que el normalizado: 30 fps, sin recortes)."""
    return {"video": str(video), "original": str(video), "cuadros": max(1, round(_duracion(video) * FPS)),
            "hdr": False, "provisional": True}


_META = threading.Lock()   # el guion y el normalizado (hilos distintos) leen y escriben el mismo fuente.json


HUELLA_TROZO = 1 << 20


def huella(video: Path) -> str:
    """Identidad del CONTENIDO de un video (tamaño + primer y último MiB): barata aun en archivos de varios GB."""
    video = Path(video)
    tam = video.stat().st_size
    h = hashlib.sha1(str(tam).encode())
    with open(video, "rb") as f:
        h.update(f.read(HUELLA_TROZO))
        if tam > 2 * HUELLA_TROZO:
            f.seek(tam - HUELLA_TROZO)
            h.update(f.read(HUELLA_TROZO))
    return h.hexdigest()


def proyecto_para(video: Path, base: str, de_cero: bool = False) -> tuple[str, bool]:
    """→ (nombre del proyecto, ya_estaba). Un proyecto es de UN video, reconocido por su contenido y no por el nombre del archivo:
    los nombres de celular se repiten (`IMG_5339`) y, reconociendo por nombre, otro video heredaba al instante el guion del
    anterior (Pablo, 11-nov: «le subo un video, me pone un guion de otra cosa en segundos»). Mismo contenido → mismo proyecto
    (se retoma lo hecho); contenido distinto, o `de_cero`, → `base-2`, `base-3`…: lo anterior nunca se pisa.
    Un proyecto anterior a esta regla (sin `.huella`) se toma por el del mismo nombre exacto y queda marcado."""
    h = huella(video)
    for n in itertools.count(1):
        nombre = base if n == 1 else f"{base}-{n}"
        carpeta = config.PROYECTOS / nombre
        marca = carpeta / ".huella"
        if not carpeta.exists():
            carpeta.mkdir(parents=True)
            marca.write_text(h)
            return nombre, False
        if de_cero:
            continue
        if marca.exists() and marca.read_text().strip() == h:
            return nombre, True
        if not marca.exists() and n == 1:
            marca.write_text(h)
            return nombre, True


def _guardar_meta(carpeta: Path, meta: dict, solo_si_falta: bool = False) -> None:
    """`fuente.json` se escribe entero o no se escribe. `solo_si_falta`: el provisional del guion nunca pisa el definitivo."""
    destino = Path(carpeta) / "fuente.json"
    with _META:
        if solo_si_falta and destino.exists():
            return
        tmp = destino.with_name("fuente.json.part")
        tmp.write_text(json.dumps(meta))
        tmp.replace(destino)


def preparar_guion(video, nombre=None, avance=print) -> Path:
    """Paso rápido: transcribir (desde el audio del original) y decidir los cortes del machote → `palabras.json` + `machote.json`.
    No normaliza ni recorta ni llama al director. Si aún no hay `fuente.json` deja uno PROVISIONAL (ver `es_provisional`)."""
    from . import machote, montaje
    video = Path(video).resolve()
    carpeta = config.PROYECTOS / (nombre or video.stem.lower())
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / "arte").mkdir(exist_ok=True)
    meta_p = carpeta / "fuente.json"
    if not meta_p.exists():
        _guardar_meta(carpeta, _fuente_provisional(video), solo_si_falta=True)
    meta = json.loads(meta_p.read_text())
    avance("transcribiendo…")
    palabras = transcribir(Path(meta["video"]), carpeta / "palabras.json")
    if not (carpeta / ".voces_fuera").exists():   # claqueta y voces bajas de fuera de cámara que el VAD se come
        avance("re-escuchando las pausas (voces fuera de cámara)…")
        (carpeta / "palabras.json").write_text(json.dumps(montaje.voces_fuera(carpeta, palabras, avance), ensure_ascii=False))
        (carpeta / ".voces_fuera").write_text("ok")
    # los cortes se deciden aquí, una vez; el director parte de ellos. ESTUDIO_SIN_IA=1: solo los cortes de código, sin llamar a Claude
    # (la autoprueba de la instalación recorre así la app entera sin gastar ni depender de la sesión)
    machote.preparar(carpeta, con_video=False, con_ia=not os.environ.get("ESTUDIO_SIN_IA"), avance=avance)
    avance("guion listo")
    return carpeta


def preparar_media(video, nombre=None, avance=print) -> Path:
    """Paso pesado: normaliza a `fuente.mp4` (escribe el `fuente.json` DEFINITIVO) y ubica a la persona (`persona.json`). Idempotente."""
    video = Path(video).resolve()
    carpeta = config.PROYECTOS / (nombre or video.stem.lower())
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / "arte").mkdir(exist_ok=True)
    meta_p = carpeta / "fuente.json"
    with _META:
        previo = json.loads(meta_p.read_text()) if meta_p.exists() else {}
    if not previo or previo.get("provisional"):
        _guardar_meta(carpeta, sondear(video, carpeta, avance))
    meta = json.loads(meta_p.read_text())
    persona.ubicar(carpeta, avance)   # solo DÓNDE está (2 cuadros por segundo): a la persona no se la recorta del fondo
    return carpeta


def preparar(video, nombre=None, avance=print) -> Path:
    """Todo junto y en fila (lote y línea de comandos): guion y luego normalizado + alfa. La app los corre en paralelo."""
    preparar_guion(video, nombre, avance)
    return preparar_media(video, nombre, avance)


FINAL_ANTERIOR = "final-anterior.mp4"   # el último video exportado con otro diseño (uno solo; el siguiente lo reemplaza)
INTENTO_PREVIO = ("storyboard.json", "arte.json", "costos.jsonl", "_guia")   # lo que el director deja y reedita en el reintento


def limpiar_intento(carpeta: Path) -> bool:
    """Reintento limpio (T-0193 F4): el director corre con `cwd=carpeta` y LEE lo que haya, así que un storyboard fallido se
    reedita idéntico (04-nov y 07-nov salieron los mismos cortes). Se borra el intento previo (storyboard, arte.json, costos,
    `_guia`) sin guardar copias; las imágenes de `arte/` se quedan (cuestan dinero y no sesgan el montaje).
    Devuelve True si había algo que borrar."""
    carpeta = Path(carpeta)
    habia = False
    if (carpeta / "final.mp4").exists():   # ese video es del diseño ANTERIOR: se conserva, pero ya no se muestra como el de ahora
        (carpeta / "final.mp4").replace(carpeta / FINAL_ANTERIOR)   # (11-nov: tras pasar de Swiss a Básico, Exportar seguía mostrando el Swiss)
    for nombre in INTENTO_PREVIO:
        origen = carpeta / nombre
        if origen.is_dir() and not origen.is_symlink():
            shutil.rmtree(origen)
            habia = True
        elif origen.exists() or origen.is_symlink():
            habia = habia or origen.is_symlink() or origen.stat().st_size > 0
            origen.unlink()
    return habia


def derivar(base: str, nombre: str) -> Path:
    """Proyecto nuevo sobre un video YA preparado (mismo video, otro estilo): comparte el video normalizado, la
    transcripción y la posición de la persona, sin volver a transcribir. Las preferencias (color) se copian.
    Si el proyecto ya tenía un intento (storyboard, arte.json, costos, _guia), se borra y el director parte limpio."""
    origen = config.PROYECTOS / base
    if not (origen / "fuente.json").exists() or es_provisional(origen):
        raise FileNotFoundError(f"el proyecto base {base!r} no está preparado")
    carpeta = config.PROYECTOS / nombre
    if carpeta.resolve() == origen.resolve():
        raise ValueError(f"derivar: el proyecto nuevo ({nombre!r}) no puede ser el mismo que el base")
    carpeta.mkdir(parents=True, exist_ok=True)
    limpiar_intento(carpeta)
    (carpeta / "arte").mkdir(exist_ok=True)
    for f in ("fuente.json", "palabras.json", "preferencias.json", "machote.json", persona.ARCHIVO):   # los estilos parten de los cortes del machote
        if (origen / f).exists() and (f in ("fuente.json", "machote.json", persona.ARCHIVO) or not (carpeta / f).exists()):   # fuente.json: siempre la ruta actual del base
            (carpeta / f).write_text((origen / f).read_text())
    return carpeta
