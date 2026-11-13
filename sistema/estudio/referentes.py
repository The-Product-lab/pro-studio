"""Referentes en imágenes, no en palabras: baja cada reel de referencia y le saca cuadros reales para aprender de ellos.

    bajar(estilo)    → referencias-estilos/<estilo>/<código>.mp4 (yt-dlp, SIN cookies: los reels públicos no las necesitan)
    cuadros(estilo)  → referencias-estilos/<estilo>/<código>/c_<t>.jpg, uno cada `PASO` s, + hoja.jpg de contacto

Cuidado con Instagram (aviso del 18-sep): nunca cookies por defecto, y una espera de `ESPERA` s entre reel y reel.
Los videos y cuadros no van a git; lo que Pablo marca que le gusta (taller) sí: db/<estilo>/gustos.json.
"""
import json
import random
import shutil
import subprocess
import time
from pathlib import Path

from . import config

RAIZ = config.RAIZ / "referencias-estilos"
DB = config.RAIZ / "librerias" / "estilos" / "db"
PASO = .5
ESPERA = (35, 50)


def _yt_dlp() -> str:
    for c in (shutil.which("yt-dlp"), str(Path.home() / ".local/bin/yt-dlp")):
        if c and Path(c).exists():
            return c
    raise RuntimeError("falta yt-dlp: `uv tool install yt-dlp`")


def codigos(estilo: str) -> list:
    """Referentes del estilo, sin los que Pablo descartó (`descartados_por_pablo`)."""
    d = json.loads((DB / "referencias.json").read_text()).get(estilo, {})
    fuera = set(d.get("descartados_por_pablo", [])) | set(d.get("no_disponibles", []))   # privados o borrados en Instagram
    return [r[0] for r in d.get("refs", []) if r[0] not in fuera]


def bajar(estilo: str, avance=print) -> list:
    carpeta = RAIZ / estilo
    carpeta.mkdir(parents=True, exist_ok=True)
    hechos, primera = [], True
    for c in codigos(estilo):
        if list(carpeta.glob(f"{c}.mp4")):
            hechos.append(c)
            continue
        if not primera:
            time.sleep(random.uniform(*ESPERA))
        primera = False
        for url in (f"https://www.instagram.com/reel/{c}/", f"https://www.instagram.com/p/{c}/"):
            r = subprocess.run([_yt_dlp(), "-q", "--no-warnings", "-f", "mp4/best", "-o", str(carpeta / "%(id)s.%(ext)s"), url],
                               capture_output=True, text=True, timeout=300)
            if r.returncode == 0 and list(carpeta.glob(f"{c}.*")):
                break
        bajado = next(iter(carpeta.glob(f"{c}.*")), None)
        if bajado and bajado.suffix != ".mp4":
            bajado.rename(bajado.with_suffix(".mp4"))
        ok = (carpeta / f"{c}.mp4").exists()
        avance(f"{estilo}/{c}: {'bajado' if ok else 'NO se pudo (privado o borrado): queda como no disponible'}")
        if not ok:
            todo = json.loads((DB / "referencias.json").read_text())
            nd = todo.setdefault(estilo, {}).setdefault("no_disponibles", [])
            if c not in nd:
                nd.append(c)
                (DB / "referencias.json").write_text(json.dumps(todo, ensure_ascii=False, indent=1))
        if ok:
            hechos.append(c)
    return hechos


def cuadros(estilo: str, avance=print) -> list:
    from PIL import Image, ImageDraw
    ffmpeg, _ = config.ffmpeg()
    out = []
    for video in sorted((RAIZ / estilo).glob("*.mp4")):
        dest = video.with_suffix("")
        if not (dest / "hoja.jpg").exists():
            dest.mkdir(exist_ok=True)
            subprocess.run([ffmpeg, "-v", "error", "-y", "-i", str(video), "-vf", f"fps={1 / PASO},scale=360:-2",
                            "-q:v", "4", str(dest / "c_%04d.jpg")], check=True)
            fotos = sorted(dest.glob("c_*.jpg"))
            for k, f in enumerate(fotos):   # nombre = segundo del reel
                f.rename(dest / f"t_{k * PASO:06.1f}.jpg")
            fotos = sorted(dest.glob("t_*.jpg"))
            if fotos:
                w, h = Image.open(fotos[0]).size
                cols = 8
                hoja = Image.new("RGB", (cols * w // 2, -(-len(fotos) // cols) * h // 2), "black")
                for k, f in enumerate(fotos):
                    im = Image.open(f).resize((w // 2, h // 2))
                    ImageDraw.Draw(im).text((4, 4), f.stem[2:], fill="yellow")
                    hoja.paste(im, ((k % cols) * w // 2, (k // cols) * h // 2))
                hoja.save(dest / "hoja.jpg", quality=80)
            avance(f"{estilo}/{video.stem}: {len(fotos)} cuadros")
        out.append(video.stem)
    return out


def gustos(estilo: str) -> list:
    f = DB / estilo / "gustos.json"
    return json.loads(f.read_text()) if f.exists() else []


# Vocabulario técnico del oficio: el taller lo ofrece al marcar y el estudio visual lo recorre propiedad por propiedad.
VOCABULARIO = {
    "color": ["paleta análoga", "complementaria", "monocroma", "triádica", "un solo acento", "desaturado", "saturado", "cálido",
              "frío", "negros levantados", "teal & orange", "duotono", "B/N", "color selectivo"],
    "luz y textura": ["halation", "bloom", "glow", "grano de película", "ruido digital", "viñeta", "aberración cromática",
                      "desenfoque / profundidad", "scanlines / CRT", "polvo y rayones", "papel", "semitono", "light leak"],
    "fusión": ["screen", "add / sobreexponer", "multiply", "overlay", "luz suave", "diferencia", "máscara de luminancia"],
    "tipografía": ["borde limpio", "borde áspero", "con trazo", "hueca", "extruida / 3D", "sombra dura", "sombra suave",
                   "condensada", "serif", "itálica", "mayúsculas", "tracking abierto", "detrás de la persona", "gigante"],
    "composición": ["centrada", "regla de tercios", "retícula visible", "simétrica", "texto detrás", "capas en profundidad",
                    "mucho aire", "denso", "persona a un lado", "marco / borde"],
    "elemento gráfico": ["tarjeta redondeada", "tag / etiqueta", "flecha a mano", "círculo a mano", "subrayado", "píxeles / glitch",
                         "ícono", "sticker", "recorte con borde", "línea fina", "caja HUD", "mapa", "cifra grande"],
    "apoyo": ["foto de archivo", "objeto recortado", "B-roll", "captura", "ilustración", "imagen generada", "dato / cifra"],
    "animación": ["retro / vintage", "stop-motion 12 cps", "elástica / rebote", "seca / corte", "suave / ease", "escritura a máquina",
                  "máscara que revela", "escala desde cero", "desenfoque a nítido", "en cascada"],
    "cámara": ["flotante", "deriva lenta", "push-in", "punch-in", "whip zoom", "whip pan", "temblor", "estática"],
    "transición": ["corte seco", "match cut", "whip", "flash", "glitch", "mosaico", "fundido", "rasgado de papel", "por oclusión"],
    "ritmo": ["al compás", "rápido", "pausado", "con respiros", "acelera hacia el final"],
    "persona": ["color natural", "B/N", "silueta", "recorte con borde", "pantalla completa", "achicada", "fondo cambiado", "luz de recorte"],
}
ASPECTOS = list(VOCABULARIO)


def marcar(estilo: str, ref: str, t: float, nota: str, me_gusta=True, aspectos=(), caja=None, cuanto="me gusta", terminos=()) -> list:
    """Lo que Pablo marca en el taller: este momento (y, si quiere, esta zona del cuadro) le gusta o no, en qué aspecto y por qué.
    `caja` = [x0, y0, x1, y1] en fracción del cuadro (0–1). Manda sobre los análisis. me_gusta=None borra la marca."""
    lista = [g for g in gustos(estilo) if not (g["ref"] == ref and abs(g["t"] - t) < 1e-3)]
    if me_gusta is not None:
        lista.append({"ref": ref, "t": round(t, 1), "me_gusta": bool(me_gusta), "cuanto": cuanto if me_gusta else "no me gusta",
                      "aspectos": [a for a in aspectos if a in ASPECTOS],
                      "terminos": [t_ for t_ in terminos if any(t_ in v for v in VOCABULARIO.values())],
                      "caja": caja, "nota": nota, "fecha": time.strftime("%Y-%m-%d")})
    (DB / estilo / "gustos.json").write_text(json.dumps(sorted(lista, key=lambda g: (g["ref"], g["t"])), ensure_ascii=False, indent=1))
    return lista


def notas_reel(estilo: str) -> dict:
    f = DB / estilo / "gustos-reel.json"
    return json.loads(f.read_text()) if f.exists() else {}


def nota_reel(estilo: str, ref: str, nota: str) -> dict:
    """Nota general de Pablo sobre un referente entero («lo que más me gusta de este reel es…»)."""
    d = notas_reel(estilo)
    d[ref] = nota
    (DB / estilo / "gustos-reel.json").write_text(json.dumps(d, ensure_ascii=False, indent=1))
    return d
