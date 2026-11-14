"""Fuentes: el catálogo completo de Google Fonts (~1.950 familias, todas de licencia libre: OFL, Apache o UFL) a un comando.

    buscar("condensada")        → familias que calzan, por popularidad (categoría, nombre o clasificación)
    instalar("Bebas Neue")      → baja los .ttf oficiales de github.com/google/fonts y los registra en librerias/fuentes/indice.json

Solo se instala lo que se usa (nada de bajar 1 GB de fuentes). Fuente oficial única: el repo google/fonts y su catálogo
fonts.google.com/metadata/fonts. Así cualquier estilo puede pedir la tipografía exacta de sus referencias.
"""
import json
import re
import time
import urllib.request

from . import config

CATALOGO_URL = "https://fonts.google.com/metadata/fonts"
REPO = "https://api.github.com/repos/google/fonts/contents"
RAW = "https://raw.githubusercontent.com/google/fonts/main"
LICENCIAS = {"ofl": "OFL", "apache": "Apache-2.0", "ufl": "UFL"}
CACHE = config.CACHE / "fuentes-catalogo.json"
INDICE = config.FUENTES / "indice.json"
UA = {"User-Agent": "the-product-studio"}

# palabras en español → cómo las nombra el catálogo
SINONIMOS = {"condensada": "condensed", "serif": "Serif", "sans": "Sans Serif", "mono": "Monospace", "manuscrita": "Handwriting",
             "display": "Display", "maquina": "typewriter", "máquina": "typewriter", "redondeada": "rounded"}


def abrir(ruta, tam: int):
    """ÚNICA puerta para abrir una letra con la que se dibuja o se mide texto. Siempre con la composición BÁSICA de Pillow.
    Sin decirlo, Pillow elige sola: si el equipo tiene la librería `fribidi` (llega con Homebrew al instalar ffmpeg, pango o libass) usa
    la composición avanzada (Raqm), que aplica el interletrado y las sustituciones de la fuente, y el MISMO texto mide otro ancho que
    en un equipo que no la tiene. Así un diseño acomodado en una Mac se salía del cuadro en otra y la compuerta frenaba el export
    (Pablo, 13-nov: «en otros Mac los textos salen más grandes»; su Mac no tiene fribidi). Fijando el motor, mide igual en todas."""
    from PIL import ImageFont
    return ImageFont.truetype(str(ruta), tam, layout_engine=ImageFont.Layout.BASIC)


# Cuánto mide cada texto de referencia (familia, tamaño, texto, ancho en px, peso 700). Es igual en TODOS los equipos: si en uno
# cambia, ahí los textos saldrían de otro tamaño. Lo comprueban `estudio doctor` (renglón «textos») y tests/test_texto_igual.py.
REFERENCIA = [("Inter", 90, "Hola mundo", 506.0), ("Playfair", 120, "AVANZAR, ya.", 776.0),
              ("Bebas Neue", 140, "TODO EL TIEMPO", 677.0), ("EB Garamond", 80, "Tipografía fija", 490.0)]


def medidas_distintas() -> list[str]:
    """Los textos de REFERENCIA que en este equipo NO miden lo debido (vacío = todo mide igual que en cualquier otro)."""
    from . import motor
    indice = motor.indice_fuentes()
    out = []
    for familia, tam, texto, ancho in REFERENCIA:
        mide = motor.fuente(indice[familia]["regular"], tam, 700).getlength(texto)
        if abs(mide - ancho) > .5:
            out.append(f"{familia} {tam} px «{texto}» mide {mide:.0f} y debe medir {ancho:.0f}")
    return out


def _get(url: str) -> bytes:
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return r.read()


def catalogo(refrescar=False) -> list:
    if CACHE.exists() and not refrescar and time.time() - CACHE.stat().st_mtime < 30 * 86400:
        return json.loads(CACHE.read_text())
    d = json.loads(_get(CATALOGO_URL).decode().lstrip(")]}'\n"))
    out = [{"familia": f["family"], "categoria": f["category"], "clases": f.get("classifications", []),
            "popularidad": f["popularity"], "estilos": sorted(f.get("fonts", {})), "ejes": [a["tag"] for a in f.get("axes", [])],
            "latin": "latin" in f.get("subsets", [])} for f in d["familyMetadataList"] if f.get("isOpenSource", True)]
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(out, ensure_ascii=False))
    return out


def buscar(texto: str = "", categoria: str = "", n: int = 20) -> list:
    t = SINONIMOS.get(texto.lower(), texto).lower()
    cat = SINONIMOS.get(categoria.lower(), categoria).lower()
    res = [f for f in catalogo() if f["latin"]
           and (not t or t in f["familia"].lower() or t in f["categoria"].lower() or any(t in c.lower() for c in f["clases"]))
           and (not cat or cat == f["categoria"].lower())]
    return sorted(res, key=lambda f: f["popularidad"])[:n]


def _slug(familia: str) -> str:
    return re.sub(r"[^a-z0-9]", "", familia.lower())


def instalar(familia: str) -> dict:
    """Baja la familia (variable si existe, si no Regular/Bold/Black + itálica) y la registra. Devuelve su ficha."""
    indice = json.loads(INDICE.read_text())
    if familia in indice:
        return indice[familia]
    if not any(f["familia"] == familia for f in catalogo()):
        parecidas = [f["familia"] for f in buscar(familia.split()[0], n=5)]
        raise ValueError(f"«{familia}» no está en Google Fonts. Parecidas: {', '.join(parecidas) or 'ninguna'}")
    for carpeta, lic in LICENCIAS.items():
        try:
            archivos = [a["name"] for a in json.loads(_get(f"{REPO}/{carpeta}/{_slug(familia)}")) if a["name"].endswith(".ttf")]
        except Exception:  # noqa: BLE001 — 404: está en otra carpeta de licencia
            continue
        if archivos:
            break
    else:
        raise ValueError(f"no encontré los archivos de «{familia}» en google/fonts")

    def elegir(italica: bool):
        cands = [a for a in archivos if ("Italic" in a) == italica]
        for pref in ("[", "-Black.", "-ExtraBold.", "-Bold.", "-Regular."):
            hit = [a for a in cands if pref in a]
            if hit:
                return hit[0]
        return cands[0] if cands else None
    regular = elegir(False) or archivos[0]
    italica = elegir(True) or regular
    for a in {regular, italica}:
        destino = config.FUENTES / a
        if not destino.exists():
            destino.write_bytes(_get(f"{RAW}/{carpeta}/{_slug(familia)}/{urllib.request.quote(a)}"))
    ficha = {"regular": regular, "italica": italica, "licencia": lic, "nota": f"Google Fonts ({carpeta}/{_slug(familia)})"}
    indice = json.loads(INDICE.read_text())
    indice[familia] = ficha
    INDICE.write_text(json.dumps(indice, ensure_ascii=False, indent=1))
    return ficha
