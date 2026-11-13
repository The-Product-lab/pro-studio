"""Ficha de un estilo para que Pablo apruebe lo que se estudió: una imagen vertical (para el celular) con sus referentes,
la paleta medida, las letras escritas con la fuente real, lo que sí y lo que no, y el ritmo. Sale de la huella y del resumen."""
import json
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw

from . import config, fuentes as gf, motor, referentes

W = 1080


def _f(nombre, tam, peso=700):
    ind = json.loads((config.FUENTES / "indice.json").read_text())
    if nombre not in ind:
        try:
            gf.instalar(nombre)
            ind = json.loads((config.FUENTES / "indice.json").read_text())
        except Exception:  # noqa: BLE001
            nombre = "Inter"
    return motor.fuente(ind[nombre]["regular"], tam, peso)


def ficha(estilo: str, salida: Path) -> Path:
    h = json.loads((config.RAIZ / "librerias/estilos/huellas" / f"{estilo}.json").read_text())
    d = json.loads((referentes.DB / "referencias.json").read_text()).get(estilo, {})
    alto = 3600
    im = Image.new("RGB", (W, alto), (14, 14, 16))
    dr = ImageDraw.Draw(im)
    t, s, m = _f("Inter", 64, 800), _f("Inter", 30, 400), _f("Inter", 26, 600)
    y = 50
    dr.text((50, y), estilo.upper(), font=t, fill=(250, 250, 250))
    y += 90
    for linea in textwrap.wrap(h.get("identidad", ""), 62)[:5]:
        dr.text((50, y), linea, font=s, fill=(190, 190, 196))
        y += 40
    y += 20
    # referentes (los de Pablo primero)
    duenno = set(d.get("del_duenno", [])) | {r[0] for r in d.get("refs", []) if "tu referencia" in str(r) or "dueño" in str(r)}
    duenno |= {r for r, n in referentes.notas_reel(estilo).items() if n} | {g["ref"] for g in referentes.gustos(estilo) if g.get("me_gusta")}
    codigos = sorted(referentes.codigos(estilo), key=lambda c: c not in duenno)[:8]
    x, tw = 50, 230
    for k, c in enumerate(codigos):
        fotos = sorted((referentes.RAIZ / estilo / c).glob("t_*.jpg"))
        if not fotos:
            continue
        p = Image.open(fotos[len(fotos) // 3]).convert("RGB")
        p.thumbnail((tw, int(tw * 16 / 9)))                       # proporción real (Pablo: no achatar los 4:3 ni los 16:9)
        marco = Image.new("RGB", (tw, int(tw * 16 / 9)), (24, 24, 28))
        marco.paste(p, ((tw - p.width) // 2, (marco.height - p.height) // 2))
        im.paste(marco, (50 + (k % 4) * (tw + 13), y + (k // 4) * (int(tw * 16 / 9) + 50)))
        dr.text((50 + (k % 4) * (tw + 13), y + (k // 4) * (int(tw * 16 / 9) + 50) + int(tw * 16 / 9) + 6),
                ("★ " if c in duenno else "") + c, font=m, fill=(255, 214, 10) if c in duenno else (150, 150, 156))
    y += 2 * (int(tw * 16 / 9) + 50) + 10 if len(codigos) > 4 else int(tw * 16 / 9) + 60
    # paleta
    dr.text((50, y), "COLOR", font=m, fill=(150, 150, 156))
    y += 40
    for k, p in enumerate([p for p in h.get("paleta", []) if isinstance(p, dict)][:6]):
        try:
            col = motor._hex(p["hex"])
        except Exception:  # noqa: BLE001
            continue
        dr.rounded_rectangle((50 + k * 165, y, 200 + k * 165, y + 90), 14, fill=col)
        for j, lin in enumerate(textwrap.wrap(f"{p['hex']} {p.get('rol', '')}", 14)[:3]):
            dr.text((50 + k * 165, y + 98 + j * 28), lin, font=_f("Inter", 22, 500), fill=(200, 200, 205))
    y += 200
    # letras
    dr.text((50, y), "LETRAS", font=m, fill=(150, 150, 156))
    y += 40
    tip = h.get("tipografia", {})
    for rol in ("display", "script", "mono"):
        nombre = tip.get(rol)
        if not nombre:
            continue
        dr.text((50, y), {"display": "Títulos", "script": "Conectores", "mono": "Datos"}[rol] + f" · {nombre}", font=_f("Inter", 24, 500),
                fill=(150, 150, 156))
        tam = 70 if rol == "display" else 52
        while tam > 24 and _f(nombre, tam).getbbox("Tu celular está lleno de videos")[2] > W - 100:
            tam -= 4                                               # que la muestra de letra quepa en el ancho
        dr.text((50, y + 30), "Tu celular está lleno de videos", font=_f(nombre, tam), fill=(240, 240, 240))
        y += 120
    # sí / no / ritmo
    for titulo, lista, col in (("LO QUE SÍ HACE", h.get("si", []), (52, 199, 89)), ("LO QUE NO HACE", h.get("no", []), (255, 69, 58))):
        dr.text((50, y), titulo, font=m, fill=col)
        y += 40
        for item in lista[:8]:
            for j, lin in enumerate(textwrap.wrap(item, 64)[:3]):
                dr.text((70, y), ("• " if j == 0 else "  ") + lin, font=_f("Inter", 26, 400), fill=(220, 220, 224))
                y += 34
        y += 16
    rit = h.get("ritmo", {})
    rango = lambda r: "–".join(f"{v:g}".replace(".", ",") for v in r) if isinstance(r, list) else str(r)  # noqa: E731
    dr.text((50, y), f"RITMO: un cambio cada {rango(rit.get('cambio_cada_s'))} s · gancho cada {rango(rit.get('gancho_cambio_cada_s'))} s", font=m,
            fill=(190, 190, 196))
    y += 60
    im.crop((0, 0, W, min(alto, y + 30))).save(salida, quality=88)
    return salida
