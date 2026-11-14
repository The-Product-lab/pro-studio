"""Storyboard en imagen (para Pablo): un cuadro real por escena con su tiempo en el video editado, qué pasa, el texto que se ve y
los recursos que usa. Sale del storyboard.json del proyecto; sirve para corregir plano por plano."""
import json
import textwrap
from bisect import bisect_left
from pathlib import Path

from PIL import Image, ImageDraw

from . import config, motor


def _recursos(esc, sb, a, b):
    r = []
    pe = esc.get("persona", {})
    if pe.get("modo") and pe["modo"] != "completa":
        r.append({"oculta": "pantalla completa sin persona"}.get(pe["modo"], pe["modo"]))
    if pe.get("fondo"):
        r.append(f"fondo {pe['fondo']}")
    if esc.get("filtro", "ninguno") != "ninguno":
        r.append(f"filtro {esc['filtro']}")
    if esc.get("entrada", "corte") != "corte":
        r.append(f"entra con {esc['entrada']}")
    for e in sb.get("elementos", []):
        if a <= e["t0"] < b and e["tipo"] != "texto":
            r.append({"panel": "panel de luz", "destello": "destello", "clip": "animación", "foto": "imagen", "etiqueta": "tag",
                      "pixeles": "píxeles", "recorte": "objeto recortado"}.get(e["tipo"], e["tipo"]))
    vistos = []
    return [x for x in r if not (x in vistos or vistos.append(x))]


def hoja(carpeta: Path, salida: Path, titulo: str = "") -> Path:
    carpeta = Path(carpeta)
    sb = json.loads((carpeta / "storyboard.json").read_text())
    p = motor.Proyecto(carpeta, sb)
    escenas = sorted(sb["escenas"], key=lambda e: e["t0"])
    fin = p.n_src / config.FPS
    tramos = []
    for i, e in enumerate(escenas):
        a, b = e["t0"], escenas[i + 1]["t0"] if i + 1 < len(escenas) else fin
        vivos = [of for of, src in enumerate(p.mapa) if a * config.FPS <= src < b * config.FPS]   # lo que QUEDA de la escena
        if not vivos:
            continue
        of = vivos[min(len(vivos) - 1, int(len(vivos) * .62))]     # pasado el desenfoque de entrada y con el texto ya armado
        tramos.append((i, e, a, b, of))
    cuadros = {of: rgb for of, rgb in motor.recorrer(p, {t[4] for t in tramos})}
    cols, cw, ch, txt_h = 4, 300, 533, 230
    filas = -(-len(tramos) // cols)
    im = Image.new("RGB", (cols * (cw + 20) + 20, 110 + filas * (ch + txt_h + 20)), (14, 14, 16))
    d = ImageDraw.Draw(im)
    f = lambda n, w=500: motor.fuente("Inter[opsz,wght].ttf", n, w)  # noqa: E731
    d.text((20, 30), titulo or carpeta.name, font=f(44, 800), fill=(250, 250, 250))
    for k, (i, e, a, b, of) in enumerate(tramos):
        x, y = 20 + (k % cols) * (cw + 20), 110 + (k // cols) * (ch + txt_h + 20)
        im.paste(Image.fromarray(cuadros[of]).resize((cw, ch)), (x, y))
        ed = of / config.FPS
        d.text((x, y + ch + 8), f"ESCENA {k + 1} · {ed:.1f} s", font=f(24, 700), fill=(255, 214, 10))
        yy = y + ch + 40
        for lin in textwrap.wrap(e.get("intencion", ""), 30)[:3]:
            d.text((x, yy), lin, font=f(20, 500), fill=(225, 225, 230))
            yy += 26
        textos = [" ".join(l["texto"] for l in el.get("lineas", []) if isinstance(l, dict)) for el in sb.get("elementos", [])
                  if el["tipo"] == "texto" and a <= el["t0"] < b]
        if textos:
            for lin in textwrap.wrap("texto: " + " / ".join(dict.fromkeys(textos)), 34)[:2]:
                d.text((x, yy), lin, font=f(18, 400), fill=(160, 200, 210))
                yy += 23
        rec = _recursos(e, sb, a, b)
        if rec:
            for lin in textwrap.wrap("recursos: " + ", ".join(rec), 34)[:2]:
                d.text((x, yy), lin, font=f(18, 400), fill=(150, 150, 156))
                yy += 23
    im.save(salida, quality=86)
    return salida
