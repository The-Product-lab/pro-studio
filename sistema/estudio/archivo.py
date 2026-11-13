"""Banco de apoyos LITERALES y gratis: fotos de dominio público (CC0 / PDM) de Openverse (api.openverse.org, sin llave).

    buscar("carpeta", n=8, en="folder")   → candidatas [{titulo, url, ancho, alto, licencia, pagina}]
    bajar(carpeta_proyecto, "carpeta", n=3, en="folder") → arte/arch_<palabra>_<k>.jpg + créditos en arte/CREDITOS-archivo.csv

Para apoyos literales (la vida la dan los textos y las animaciones; Pablo, 10-nov: menos imágenes) sin gastar créditos ni que se note la IA: fotos reales del objeto que se nombra. Se tratan en el
motor (`tratamiento`: bn | halftone | duotono) para que todas parezcan de la misma familia, y `fusion: "multiplicar"` borra el
blanco de fondo de los objetos de catálogo.
"""
import csv
import io
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image

API = "https://api.openverse.org/v1/images/"
UA = {"User-Agent": "the-product-studio"}
MIN_LADO = 700
# Pablo (07-nov, regla 4): nada de personas en el banco de archivo (fotos de mujeres prohibidas; en Glass salió un chico)
PALABRAS_PERSONA = re.compile(
    r"\b(person|people|persons|man|men|woman|women|girl|girls|boy|boys|guy|lady|ladies|child|children|kid|kids|portrait|face|faces|"
    r"selfie|worker|workers|crowd|couple|family|baby|student|students|model|clerk|typist|secretary|operator|operators|"
    r"hombre|hombres|mujer|mujeres|persona|personas|gente|retrato|rostro|chico|chica|niño|niña|niños)\b", re.I)
PERSONA_AREA_MIN = 0.0008    # fracción de la foto que el recorte (RVM) marca como persona; bajo a propósito: una foto de salón con muchas caras chicas da ~0,002


def habla_de_personas(titulo: str, etiquetas=()) -> bool:
    """El título o las etiquetas de Openverse nombran a una persona."""
    return bool(PALABRAS_PERSONA.search(" ".join([titulo or "", *map(str, etiquetas)])))


def tiene_persona(im: Image.Image) -> bool:
    """La foto muestra a una persona (cara o cuerpo), medido con el mismo recorte de personas de la ingesta (RVM, local)."""
    import numpy as np
    from . import config
    if not config.RVM_ONNX.exists():
        return False
    ses = _sesion_rvm(str(config.RVM_ONNX))
    ch = im.convert("RGB").copy()
    ch.thumbnail((640, 640))
    x = (np.asarray(ch, np.float32) / 255).transpose(2, 0, 1)[None]
    z = [np.zeros((1, 1, 1, 1), np.float32)] * 4
    pha = ses.run(None, {"src": x, "r1i": z[0], "r2i": z[1], "r3i": z[2], "r4i": z[3],
                         "downsample_ratio": np.array([.5], np.float32)})[1][0, 0]
    return float((pha > .5).mean()) >= PERSONA_AREA_MIN


_SESIONES: dict = {}


def _sesion_rvm(ruta: str):
    if ruta not in _SESIONES:
        import onnxruntime as ort
        _SESIONES[ruta] = ort.InferenceSession(ruta, providers=["CPUExecutionProvider"])
    return _SESIONES[ruta]


def buscar(palabra: str, n: int = 8, en: str | None = None) -> list:
    """`en` = la búsqueda en inglés (Openverse indexa sobre todo en inglés); si falta se usa la palabra tal cual."""
    q = en or palabra
    url = API + "?" + urllib.parse.urlencode({"q": q, "license": "cc0,pdm", "page_size": 20, "mature": "false"})
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        res = json.loads(r.read()).get("results", [])
    buenas = [x for x in res if min(x.get("width") or 0, x.get("height") or 0) >= MIN_LADO and x.get("url")
              and not habla_de_personas(x.get("title", ""), [t.get("name", "") for t in x.get("tags") or []])]
    return [{"titulo": x.get("title", ""), "url": x["url"], "ancho": x.get("width"), "alto": x.get("height"),
             "licencia": x.get("license"), "pagina": x.get("foreign_landing_url", "")} for x in buenas[:n]]


def bajar(proyecto: Path, palabra: str, n: int = 3, en: str | None = None) -> list:
    arte = Path(proyecto) / "arte"
    arte.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", palabra.lower()).strip("-")
    hechos = []
    with open(arte / "CREDITOS-archivo.csv", "a", newline="") as fc:
        w = csv.writer(fc)
        for k, c in enumerate(buscar(palabra, n * 2, en)):
            if len(hechos) >= n:
                break
            destino = arte / f"arch_{slug}_{k + 1}.jpg"
            try:
                with urllib.request.urlopen(urllib.request.Request(c["url"], headers=UA), timeout=60) as r:
                    im = Image.open(io.BytesIO(r.read())).convert("RGB")
            except Exception:  # noqa: BLE001 — enlace roto: la siguiente
                continue
            if tiene_persona(im):   # el título no la nombraba, pero se ve una persona
                continue
            im.thumbnail((2000, 2000))
            im.save(destino, quality=90)
            w.writerow([destino.name, palabra, c["titulo"], c["licencia"], c["pagina"]])
            hechos.append(str(destino.relative_to(proyecto)))
    return hechos


def quitar_personas(carpeta: Path, avance=print) -> list:
    """Pablo (07-nov, regla 4): ninguna foto con personas, venga de donde venga (Openverse, --biblioteca o arte ya presente).
    Mira cada foto de archivo (arch_*) que el storyboard usa; si muestra una persona, la mueve a arte/_personas/ (el director ya no la lista) y quita
    su apoyo del storyboard (la compuerta de densidad dirá si hace falta otro recurso). Devuelve los src descartados."""
    import shutil
    carpeta = Path(carpeta)
    f = carpeta / "storyboard.json"
    sb = json.loads(f.read_text())
    malas, vistas = [], {}
    for e in sb.get("elementos", []):
        src = e.get("src") if isinstance(e, dict) and e.get("tipo") == "foto" else None
        if src and Path(src).name.startswith("arch_") and src not in vistas and (carpeta / src).exists():
            vistas[src] = tiene_persona(Image.open(carpeta / src))
    malas = sorted(s for s, v in vistas.items() if v)
    if malas:
        sb["elementos"] = [e for e in sb["elementos"] if not (isinstance(e, dict) and e.get("src") in malas)]
        f.write_text(json.dumps(sb, ensure_ascii=False, indent=1))
        (carpeta / "arte" / "_personas").mkdir(exist_ok=True)
        for s in malas:
            shutil.move(str(carpeta / s), str(carpeta / "arte" / "_personas" / Path(s).name))
            avance(f"archivo: {s} muestra una persona: descartada")
    return malas
