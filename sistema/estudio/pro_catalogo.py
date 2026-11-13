"""Catálogo de «Estilos Pro»: los estilos de Lemo (laboratorio-estilos/lemo-opuscar/styles) con nombre en español, familia, temas y
la muestra ya hecha. Se elige por tema, no por gusto. Los nombres y temas viven en librerias/pro_estilos.json; lo demás sale de
la carpeta de cada estilo (style.json, poster.jpg) y de las muestras que el laboratorio ya renderizó."""
import json
from pathlib import Path

from . import config

DATOS = config.RAIZ / "librerias" / "pro_estilos.json"
# Las películas hechas a mano llevan el nombre de la pieza, no el del estilo
PELICULAS = {"cel-anime-80s": "anime-reel", "paper-popup": "papel-camara", "silent-film": "reel-mudo"}
# Aviso cuando todavía no hay un encargo Pro medido (Julián animado, 09-nov)
MEDIDO_INICIAL = {"minutos": 72, "tokens": 376_000}


def laboratorio() -> Path | None:
    """La carpeta que trae a Lemo en esta máquina (la busca `config.laboratorio`)."""
    return config.laboratorio()


def _muestra(lab: Path, slug: str) -> Path | None:
    candidatas = [lab / "muestras-lemo" / slug / f"{slug}.mp4", lab / "muestras-opus" / slug / f"{slug}.mp4"]
    if slug in PELICULAS:
        p = PELICULAS[slug]
        candidatas.append(lab / "peliculas" / p / f"{p}.mp4")
    if slug == "engraving":
        candidatas.insert(0, lab / "julian-animado" / "julian-animado.mp4")
    return next((c for c in candidatas if c.is_file()), None)


def catalogo() -> list[dict]:
    """[{slug, nombre, familia, temas, poster, muestra|None, probado, riesgo|None}] en orden alfabético por nombre.
    `poster` y `muestra` son rutas de archivo; el servidor las entrega por /pro-media/<slug>/<poster|muestra>."""
    lab = laboratorio()
    if lab is None:
        return []
    datos = json.loads(DATOS.read_text(encoding="utf-8"))
    out = []
    for carpeta in sorted((lab / "lemo-opuscar" / "styles").iterdir()):
        ficha = carpeta / "style.json"
        if carpeta.name.startswith("_") or not ficha.is_file():
            continue
        slug = carpeta.name
        propio = datos["estilos"].get(slug)
        if propio is None:   # Lemo saca estilos nuevos seguido (66 el 9-nov, 100 el 12-nov): se ofrece lo que ya tiene nombre y temas aquí
            continue
        cat = json.loads(ficha.read_text(encoding="utf-8")).get("category_en", "")
        muestra = _muestra(lab, slug)
        out.append({"slug": slug, "nombre": propio["nombre"], "familia": datos["familias"].get(cat, cat), "temas": propio["temas"],
                    "poster": str(carpeta / "poster.jpg"), "muestra": str(muestra) if muestra else None,
                    "probado": muestra is not None, "riesgo": datos["riesgos"].get(slug)})
    return sorted(out, key=lambda e: e["nombre"].lower())


def por_slug(slug: str) -> dict | None:
    return next((e for e in catalogo() if e["slug"] == slug), None)


def aviso() -> dict:
    """Tiempo y consumo que se muestran antes de lanzar: lo medido en el último encargo Pro (costos.jsonl), si no, lo de Julián animado."""
    costos = sorted(config.PROYECTOS.glob("*/pro-*/costos.jsonl"), key=lambda p: p.stat().st_mtime) if config.PROYECTOS.is_dir() else []
    filas = [json.loads(l) for l in costos[-1].read_text().splitlines() if l.strip()] if costos else []
    seg = sum(f.get("segundos") or 0 for f in filas)
    if seg:
        minutos, usd, medido = max(1, round(seg / 60)), round(sum(f.get("usd_equivalente") or 0 for f in filas), 2), True
        consumo = f"equivale a unos US$ {usd} de la suscripción (último reel Pro)"
    else:
        minutos, medido = MEDIDO_INICIAL["minutos"], False
        consumo = f"unos {MEDIDO_INICIAL['tokens'] // 1000}k tokens: un consumo alto de la suscripción"
    return {"minutos": minutos, "medido": medido, "consumo": consumo,
            "origen": "medido en tu último reel Pro" if medido else "medido en un solo reel Pro (9-nov, en el PC); en otra máquina puede cambiar",
            "texto": f"Un reel Pro tarda unos {minutos} minutos y {consumo}. El PC hace un reel Pro a la vez."}
