"""Motor de render: storyboard.json + video → mp4, cuadro por cuadro (Pillow → ffmpeg). La persona va siempre en su toma completa.

El storyboard describe QUÉ pasa (escenas, elementos, trazos, cámara, subtítulos); el motor lo hace siempre igual.
Todos los tiempos del storyboard están en segundos del video FUENTE (antes de quitar los silencios de `cortes`).
"""
import bisect
import json
import math
import shutil
import subprocess
import zlib
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

from . import camara, color, config, efectos, persona, sonido, subtitulo_basico, subtitulo_opciones

W, H, FPS = config.W, config.H, config.FPS


AIRE_TEXTO = 30   # aire para sombra/brillo que el motor deja alrededor del texto (el mismo `margen_dibujo` de validar)


SUBTITULO_VELO = 150            # opacidad (0-255) del velo oscuro bajo un subtítulo sin caja cuando el fondo no contrasta
FONDO_CLARO_LUMA = 95           # luma media (0-255) del fondo bajo el subtítulo a partir de la cual el blanco pierde contraste
FONDO_RAYADO_STD = 45           # desviación de luma (rayas, manos, bordes duros) a partir de la cual el texto se pierde


def fondo_claro_o_rayado(lienzo, caja) -> bool:
    """Mide el fondo ya dibujado bajo la caja del subtítulo: claro (luma media alta) o con mucho contraste interno (rayas)."""
    x0, y0, x1, y1 = (int(max(0, v)) for v in caja)
    zona = lienzo.crop((x0, y0, min(x1, lienzo.width), min(y1, lienzo.height))).convert("L")
    a = np.asarray(zona, np.float32)
    return bool(a.size and (a.mean() > FONDO_CLARO_LUMA or a.std() > FONDO_RAYADO_STD))


def caja_vidrio(lienzo, x0, y0, w, h, radio, p, desenfoque, velo_rgb, velo_a):
    """Vidrio esmerilado: sombra, desenfoque de lo que hay detrás, velo y borde de luz. Lo comparten el elemento `vidrio` y el subtítulo `vidrio`.
    (x0, y0) esquina de la caja en el lienzo; p = 0..1 (aparición). Devuelve la caja dibujada (x0, y0, x1, y1) o None si cae fuera."""
    if min(x0 + w, lienzo.width) <= max(0, x0) or min(y0 + h, lienzo.height) <= max(0, y0):
        return None
    mascara = Image.new("L", (w, h))
    ImageDraw.Draw(mascara).rounded_rectangle((0, 0, w - 1, h - 1), radio, fill=int(255 * p))
    sombra = Image.new("RGBA", (w + 160, h + 160))
    ImageDraw.Draw(sombra).rounded_rectangle((80, 104, 80 + w, 104 + h), radio, fill=(0, 0, 0, int(70 * p)))
    lienzo.alpha_composite(sombra.filter(ImageFilter.GaussianBlur(30)), (x0 - 80, y0 - 80))
    detras = lienzo.crop((x0, y0, x0 + w, y0 + h)).filter(ImageFilter.GaussianBlur(desenfoque))
    detras.alpha_composite(Image.new("RGBA", (w, h), tuple(velo_rgb) + (int(255 * velo_a),)))
    borde = Image.new("RGBA", (w, h))
    ImageDraw.Draw(borde).rounded_rectangle((0, 0, w - 1, h - 1), radio, outline=(255, 255, 255, int(110 * p)), width=2)
    detras.alpha_composite(borde)
    detras.putalpha(mascara)
    lienzo.alpha_composite(detras, (x0, y0))
    return (x0, y0, x0 + w, y0 + h)


def velo_suave(lienzo, caja, rgb, alfa, radio=30, margen=(20, 30), difuminar=24):
    """Velo de bordes suaves bajo el texto: la capa de dibujo es más grande que la caja para que el desenfoque no se corte."""
    x0, y0, x1, y1 = (int(v) for v in caja)
    pad = 3 * difuminar if difuminar else 0
    capa = Image.new("RGBA", (x1 - x0 + 2 * pad, y1 - y0 + 2 * pad), (0, 0, 0, 0))
    ImageDraw.Draw(capa).rounded_rectangle((pad + margen[0], pad + margen[1], capa.width - pad - margen[0] - 1, capa.height - pad - margen[1] - 1),
                                           radio, fill=tuple(rgb) + (int(255 * min(1, alfa)),))
    lienzo.alpha_composite(capa.filter(ImageFilter.GaussianBlur(difuminar)) if difuminar else capa, (x0 - pad, y0 - pad))


def recorte_fino(im, x0, y0, x1, y1):
    """Recorta y escala en un solo paso con coordenadas decimales (sin int()): el movimiento lento de cámara no avanza a saltos de píxel."""
    return im.resize((W, H), Image.BILINEAR, box=(x0, y0, x1, y1))


def _hex(c):
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def _contraste(rgb):
    """Tinta casi negra sobre fondos claros, blanco sobre fondos oscuros."""
    return (16, 16, 18) if rgb[0] * .299 + rgb[1] * .587 + rgb[2] * .114 > 150 else (250, 250, 250)


def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def ease_out(x): return 1 - (1 - clamp(x)) ** 3
def ease_io(x):
    x = clamp(x)
    return 4 * x ** 3 if x < .5 else 1 - (-2 * x + 2) ** 3 / 2
def ease_back(x):
    x, c = clamp(x), 1.9
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2


def fuente(archivo: str, size: int, wght=700):
    """Abre una fuente y, si es variable, fija el eje de PESO por su nombre (Inter y Bodoni tienen además tamaño óptico,
    que se deja acorde al tamaño pedido); el peso se recorta al rango que la fuente admite."""
    f = ImageFont.truetype(str(config.FUENTES / archivo), size)
    try:
        ejes = f.get_variation_axes()
    except OSError:
        return f
    valores = []
    for a in ejes:
        nombre = a["name"].decode() if isinstance(a["name"], bytes) else str(a["name"])
        v = wght if nombre.lower().startswith("weight") else size if nombre.lower().startswith("optical") else a["default"]
        valores.append(max(a["minimum"], min(a["maximum"], v)))
    f.set_variation_by_axes(valores)
    return f


def indice_fuentes() -> dict:
    return json.loads((config.FUENTES / "indice.json").read_text())


def singular_de(sufijo: str) -> str:
    """« citas» → « cita»: la última palabra en plural regular (…as / …os) pierde la «s». Para otros plurales el storyboard trae `singular`."""
    cuerpo = sufijo.rstrip()
    resto = sufijo[len(cuerpo):]
    palabra = cuerpo.split(" ")[-1] if cuerpo else ""
    if len(palabra) > 3 and palabra.endswith(("as", "os")):
        return cuerpo[:-1] + resto
    return sufijo


def texto_contador(d: dict, v: float) -> str:
    """El texto del contador con su valor: «1 cita», «2 citas» (singular exacto en `singular`, o el plural regular sin su «s»)."""
    dec = d.get("decimales", 0)
    sufijo = d.get("sufijo", "")
    if dec == 0 and round(v) == 1:
        sufijo = d.get("singular", singular_de(sufijo))
    return f"{d.get('prefijo', '')}{v:.{dec}f}{sufijo}"


TEXTO_CHICO = 90   # px (de 1080 de ancho): una línea más baja que esto es «texto pequeño» (conectores, rótulos, datos)


def _presets() -> dict:
    """Los presets de los estilos (una lectura por proceso)."""
    if "p" not in _PRESETS:
        _PRESETS["p"] = json.loads((config.RAIZ / "librerias" / "estilos" / "presets.json").read_text())
    return _PRESETS["p"]


_PRESETS: dict = {}


class Estilo:
    def __init__(s, d: dict):
        s.acento = _hex(d.get("acento", "#FFE800"))
        s.tinta = _hex(d.get("tinta", "#181614"))
        s.papel = _hex(d.get("papel", "#E2D6BE"))
        s.borde = _hex(d.get("borde", "#F6F1E6"))
        s.tono = d.get("tono", [1.0, .97, .9])
        s.grano = d.get("grano", 34)
        s.persona_bn = d.get("persona", "bn") == "bn"
        s.base = d.get("base", "pantalla")             # una sola base: la persona en su toma completa (el collage con la persona recortada se retiró)
        s.acento2 = _hex(d.get("acento2", "#00E5FF"))
        # `texto`: el color que la persona eligió para los textos pequeños que van en blanco sobre la toma (None = blancos, como siempre)
        s.texto = _hex(d["texto"]) if d.get("texto") else None
        # El director suele escribir el color de una línea como el #hex de la paleta del estilo, no por su nombre. Si la persona cambia
        # ese color de la paleta, la línea lo sigue: hex del preset → nombre (solo los que no se repiten dentro del preset).
        s._de_preset = {}
        preset = _presets().get(d.get("id") or "", {})
        for k in ("acento", "acento2", "tinta", "papel"):
            h = str(preset.get(k, "")).upper()
            if h and str(d.get(k, "")).upper() != h and sum(str(preset.get(x, "")).upper() == h for x in ("acento", "acento2", "tinta", "papel")) == 1:
                s._de_preset[h] = k
        s.subtitulo = d.get("subtitulo", "tira")        # tira (papel) | hud (palabra a palabra, sin caja) | vidrio (caja de vidrio) | basico (estilo Básico)
        s.basico = subtitulo_basico.opciones(d) if s.subtitulo == "basico" else None
        s.sub = subtitulo_opciones.de_estilo(d)         # sub_*: lo elegido para el subtítulo de CUALQUIER tipo (None = el de siempre)
        s.crt = d.get("crt", 0.0)                       # fuerza de la textura de pantalla de tubo (0 = nada)
        s.aberracion_corte = d.get("aberracion_corte", 0)   # px de aberración cromática en el cuadro de cada corte
        s.transicion = d.get("transicion", "corte")       # corte | desenfoque (rack focus en todos los cambios de escena)
        s.flotar = d.get("flotar", 0)                     # px de deriva de la cámara flotante (0 = fija)
        s.flotar_elementos = d.get("flotar_elementos", 0)  # px de deriva propia de cada elemento (todo flota, gusto de Pablo)
        s.bloom = d.get("bloom", 0.0)                     # fuerza del brillo que sueltan las luces altas (0 = nada)
        indice = json.loads((config.FUENTES / "indice.json").read_text())
        s.fuente = indice.get(d.get("fuente", "Playfair"), indice["Playfair"])
        s.roles = {"display": s.fuente, "script": indice[d.get("fuente_script", "Alex Brush")],
                   "mono": indice[d.get("fuente_mono", "JetBrains Mono")]}

    def font(s, size, italic=False, wght=700):
        return fuente(s.fuente["italica" if italic else "regular"], size, wght)

    def sub_font(s, size, italic=False, wght=700):
        """Fuente del subtítulo: la elegida en `sub_fuente`, y si no, la de títulos del estilo."""
        ent = indice_fuentes().get(s.sub["fuente"]) if s.sub["fuente"] else None
        return fuente((ent or s.fuente)["italica" if italic else "regular"], size, wght)

    def font_rol(s, rol, size, wght=900, italica=False):
        """display | script | mono → fuente de ese rol en el tamaño y peso pedidos (italica = su archivo itálico si lo tiene)."""
        return fuente(s.roles[rol]["italica" if italica else "regular"], size, wght)

    def color(s, nombre):
        nombre = s._de_preset.get(str(nombre).upper(), nombre)
        return {"acento": s.acento, "acento2": s.acento2, "tinta": s.tinta, "papel": s.papel,
                "blanco": (255, 255, 255), "negro": (8, 8, 10)}.get(nombre) or _hex(nombre)

    def color_linea(s, linea: dict):
        """El color de una línea de texto. Las líneas pequeñas (menos de TEXTO_CHICO px) que el director dejó en blanco toman el
        color de `texto` si la persona lo eligió (Pablo, 11-nov: «no me está dejando editar el color de los textos pequeños»)."""
        nombre = linea.get("color", "blanco")
        if s.texto and str(nombre).upper() in ("BLANCO", "#FFFFFF", "#FFF") and linea.get("tam", 120) < TEXTO_CHICO:
            return s.texto
        return s.color(nombre)

    def tonificar(s, im):
        g = ImageOps.autocontrast(im.convert("L"), cutoff=1)
        return Image.merge("RGB", [g.point(lambda v, k=k: v * k) for k in s.tono])


def _sombra(im, rot):
    im = im.rotate(rot, Image.BICUBIC, expand=True)
    m = 40
    out = Image.new("RGBA", (im.width + 2 * m, im.height + 2 * m))
    sh = Image.new("RGBA", im.size, (20, 14, 6, 0))
    sh.putalpha(im.getchannel("A").point(lambda v: v * .55))
    out.alpha_composite(sh, (m + 10, m + 16))
    out = out.filter(ImageFilter.GaussianBlur(12))
    out.alpha_composite(im, (m, m))
    return out


def aura(img, color, fuerza=1.0, margen=140):
    """Luz completa alrededor de un texto o apoyo (como en luminoso): retroiluminación + haze + glow + halation + núcleo nítido.
    Devuelve una imagen más grande (margen px por lado) con la luz ya compuesta."""
    w, h = img.size
    base = Image.new("RGBA", (w + 2 * margen, h + 2 * margen))
    base.paste(img, (margen, margen), img)
    a = base.getchannel("A")
    out = Image.new("RGBA", base.size)
    capas = [(a.filter(ImageFilter.BoxBlur(10)).filter(ImageFilter.GaussianBlur(70)), color, .55),   # retroiluminación
             (a.filter(ImageFilter.GaussianBlur(38)), color, .9),                                    # haze
             (a.filter(ImageFilter.GaussianBlur(14)), color, 1.6),                                   # glow
             (a.filter(ImageFilter.GaussianBlur(4)), tuple(min(255, int(c * .5 + 140)) for c in color), 1.3)]   # halation
    for m, col, k in capas:
        lam = Image.new("RGBA", base.size, tuple(col) + (255,))
        lam.putalpha(m.point(lambda v, k=k: min(255, int(v * k * fuerza))))
        out.alpha_composite(lam)
    out.alpha_composite(base)
    return out


def _mascara_fundida(tam, fuerza=True) -> Image.Image:
    """Alfa elíptico que se desvanece hacia los bordes (fuerza 0–1 o True = .45 del radio)."""
    w, h = tam
    k = .45 if fuerza is True else float(fuerza)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    r = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
    return Image.fromarray((np.clip((1 - r) / k, 0, 1) ** 1.5 * 255).astype(np.uint8))


def _cuadros_clip(video: Path, base: Path) -> list:
    """Cuadros de un clip a 30 cps y 1080×1920 (cubriendo, sin barras), en caché en el proyecto. A prueba de render en paralelo.
    La clave es la ruta Y el archivo (tamaño y fecha): un `arte/<id>.mp4` rehecho con el mismo nombre no reusa los cuadros viejos
    (12-nov: Lemo rehízo a1/a3/a6/a8 y el render seguía mostrando los de antes). Los cuadros de la versión vieja se borran."""
    import hashlib
    import shutil
    st = Path(video).stat()
    ruta = hashlib.sha1(str(video).encode()).hexdigest()[:10]
    clave = f"{ruta}-{hashlib.sha1(f'{st.st_size}:{st.st_mtime_ns}'.encode()).hexdigest()[:8]}"
    dest = Path(base) / ".clips" / clave
    if not (dest / "listo").exists():
        for viejo in (Path(base) / ".clips").glob(f"{ruta}*"):
            if viejo.name != clave and ".tmp" not in viejo.name:
                shutil.rmtree(viejo, ignore_errors=True)
        tmp = dest.with_name(f"{clave}.tmp{__import__('os').getpid()}")
        tmp.mkdir(parents=True, exist_ok=True)
        ffmpeg, _ = config.ffmpeg()
        subprocess.run([ffmpeg, "-v", "error", "-y", "-i", str(video), "-vf",
                        f"fps={FPS},scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}", "-q:v", "3",
                        str(tmp / "f_%04d.jpg")], check=True)
        (tmp / "listo").write_text("ok")
        try:
            tmp.rename(dest)
        except OSError:
            shutil.rmtree(tmp, ignore_errors=True)   # otro proceso ya lo dejó listo
    return sorted(dest.glob("f_*.jpg"))


# Lo que el motor sabe hacerle a un apoyo (foto): el seleccionador y el catálogo leen de aquí, nunca de una lista copiada.
TRATAMIENTOS = ("bn", "halftone", "duotono", "duotono-inverso")   # `tratamiento` de una foto
FUSIONES = ("pantalla", "multiplicar")                          # `fusion` de un apoyo


class Elemento:
    """Foto con borde, recorte con contorno o etiqueta de texto. Sabe ubicar en pantalla un punto de su imagen fuente."""

    def __init__(s, d: dict, est: Estilo, base: Path):
        s.d, s.id, s.est = d, d.get("id", ""), est
        s.t0, s.t1 = d["t0"], d["t1"]
        s.x, s.y, s.rot = d["x"], d["y"], d.get("rot", 0)
        s.entra, s.dur, s.z = d.get("entra", "pop"), d.get("dur", .35), d.get("z", "frente")
        s.borde, s.k, s.off, s.card = 0, 1.0, (0, 0), (0, 0)
        tipo = d["tipo"]
        if tipo == "foto":
            s.img = s._foto(est, base)
            if d.get("luz") and not d.get("cubrir"):
                s.img = aura(s.img, est.color(d.get("color_luz", "acento2")))
        elif tipo == "recorte":
            s.img = s._recorte(est, base)
            if d.get("luz"):
                s.img = aura(s.img, est.color(d.get("color_luz", "acento2")))
        elif tipo == "etiqueta":
            s.img = s._etiqueta(est)
        elif tipo == "texto":
            s.img = s._texto(est)
            if d.get("luz"):
                s.img = aura(s.img, est.color(d.get("color_luz", "acento2")), d.get("luz") if isinstance(d.get("luz"), (int, float)) and d.get("luz") is not True else 1.0)
        elif tipo == "clip":       # video a pantalla completa (ilustración animada): se reproduce desde t0, en su color
            s.img = None
            s.card = (W, H)
            s.cuadros_clip = _cuadros_clip(base / d["src"], base)
        elif tipo == "vidrio":     # panel de vidrio (glass): desenfoca lo que tiene detrás + velo blanco + borde de luz + sombra
            s.img = None
            s.card = (d.get("ancho", 600), d.get("alto", 360))
        elif tipo in ("contador", "barra"):   # datos: cifra que cuenta (desde→hasta) / barra que crece desde abajo
            s.img = None
            s.card = (d.get("ancho", 300), d.get("alto", 400))
        elif tipo == "destello":   # estrella de 4 puntas de luz que titila
            s.img = None
            s.card = (d.get("tam", 90),) * 2
        elif tipo == "panel":      # pantalla de luz: entra como destello blanco quemado y revela una imagen; reflejo abajo
            s.img = None
            s.card = (d.get("ancho", 320), d.get("alto", 460))
            s.contenido = None
            if d.get("src"):
                im = Image.open(base / d["src"]).convert("RGB")
                k = max(s.card[0] / im.width, s.card[1] / im.height)
                im = im.resize((math.ceil(im.width * k), math.ceil(im.height * k)), Image.LANCZOS)
                x0, y0 = (im.width - s.card[0]) // 2, (im.height - s.card[1]) // 2
                s.contenido = im.crop((x0, y0, x0 + s.card[0], y0 + s.card[1]))
        elif tipo == "pixeles":   # bloques de píxeles que se arman y desarman (glitch geométrico, 12 cambios/s)
            s.img = None
            s.colores = [est.color(c) for c in d.get("colores", ["acento", "blanco"])]
            s.card = (d.get("ancho", 120), d.get("alto", 120))
        else:
            raise ValueError(f"elemento {s.id}: tipo desconocido {tipo!r}")

    def _texto(s, est):
        """Texto libre sin caja: líneas apiladas y centradas, cada una con su rol de fuente, tamaño y color; brillo opcional."""
        d = s.d
        filas = []
        for l in d["lineas"]:  # {"texto", "rol", "tam", "color", "mayus", "contorno", "trazo", "extrusion"}
            txt = l["texto"].upper() if l.get("mayus") else l["texto"]
            f = est.font_rol(l.get("rol", "display"), l.get("tam", 120), l.get("peso", 900), l.get("italica", False))
            sw = l.get("contorno") or (l.get("trazo") or [0])[0]
            ext = (l.get("extrusion") or [0])[0]
            b = f.getbbox(txt, stroke_width=sw)
            filas.append((txt, f, (b[0], b[1], b[2] + ext, b[3] + ext), est.color_linea(l), l, sw, ext))
        gap = d.get("interlineado", -10)
        tw = max(b[2] - b[0] for _, _, b, *_ in filas) + 60
        th = sum(b[3] - b[1] for _, _, b, *_ in filas) + gap * (len(filas) - 1) + 60
        im = Image.new("RGBA", (tw, th))
        dr, yy = ImageDraw.Draw(im), 30
        for txt, f, b, col, l, sw, ext in filas:
            x, y = (tw - (b[2] - b[0])) / 2 - b[0], yy - b[1]
            if l.get("escala_y", 1) != 1:   # palabra estirada en vertical (el «WHAT» gigante de DfAE): se dibuja aparte y se estira
                ey = float(l["escala_y"])
                capa = Image.new("RGBA", (tw, int((b[3] - b[1]) * ey) + 40))
                ImageDraw.Draw(capa).text((x, 20 - b[1]), txt, font=f, fill=col + (255,), stroke_width=sw,
                                          stroke_fill=(est.color(l["trazo"][1]) + (255,)) if l.get("trazo") else None)
                capa = capa.crop((0, 0, tw, int(b[3] - b[1]) + 40)).resize((tw, int((b[3] - b[1]) * ey) + 40), Image.BICUBIC)
                if im.height < yy + capa.height + 30:
                    nuevo = Image.new("RGBA", (tw, yy + capa.height + 30))
                    nuevo.alpha_composite(im)
                    im, dr = nuevo, ImageDraw.Draw(nuevo)
                im.alpha_composite(capa, (0, yy - 20))
                yy += capa.height - 40 + gap
                continue
            if ext:   # extrusión: copias desplazadas en diagonal (bloque 3D duro)
                ce = est.color(l["extrusion"][1]) + (255,)
                for k in range(ext, 0, -1):
                    dr.text((x + k, y + k), txt, font=f, fill=ce, stroke_width=sw, stroke_fill=ce)
            if l.get("contorno"):   # hueco: solo el borde, del color de la línea
                dr.text((x, y), txt, font=f, fill=(0, 0, 0, 0), stroke_width=sw, stroke_fill=col + (255,))
                # quita el relleno que Pillow pinta dentro del trazo
                hueco = Image.new("L", im.size)
                ImageDraw.Draw(hueco).text((x, y), txt, font=f, fill=255)
                a = np.asarray(im.getchannel("A")).copy()
                a[np.asarray(hueco) > 128] = 0
                im.putalpha(Image.fromarray(a))
            elif l.get("trazo"):
                dr.text((x, y), txt, font=f, fill=col + (255,), stroke_width=sw, stroke_fill=est.color(l["trazo"][1]) + (255,))
            else:
                dr.text((x, y), txt, font=f, fill=col + (255,))
            yy += b[3] - b[1] + gap
        if d.get("brillo"):   # el texto emite luz: halo amplio del color de luz (acento2) + halo corto del propio color
            luz = Image.new("RGBA", im.size, est.acento2 + (255,))
            ancho = im.getchannel("A").filter(ImageFilter.GaussianBlur(26))
            luz.putalpha(ancho.point(lambda v: min(255, int(v * 1.9))))
            corto = im.filter(ImageFilter.GaussianBlur(7))
            corto.putalpha(corto.getchannel("A").point(lambda v: min(255, int(v * 1.6))))
            luz.alpha_composite(corto)
            luz.alpha_composite(im)
            im = luz
        if d.get("sombra", True) and not d.get("brillo"):  # sombra suave para que se lea sobre cualquier fondo (también bajo la luz)
            sombra = Image.new("RGBA", im.size, (0, 0, 0, 0))
            sombra.putalpha(im.getchannel("A").filter(ImageFilter.GaussianBlur(12)).point(lambda v: min(255, int(v * 1.2))))
            sombra.alpha_composite(im)
            im = sombra
        s.card = im.size
        return im.rotate(s.rot, Image.BICUBIC, expand=True) if s.rot else im

    def _foto(s, est, base):
        d = s.d
        im = Image.open(base / d["src"]).convert("RGB")
        if d.get("tratamiento") in TRATAMIENTOS and d["tratamiento"] != "duotono-inverso":   # fotos de fuentes distintas, de la misma familia
            im = Image.fromarray(efectos.filtrar(np.asarray(im), d["tratamiento"], est))
        elif d.get("tratamiento") == "duotono-inverso":   # fondo blanco → negro: con fusion «pantalla» el objeto flota suelto sobre lo oscuro
            im = Image.fromarray(efectos.duotono(255 - np.asarray(im), (0, 0, 0), est.acento2))
        if d.get("cubrir"):   # a pantalla completa, sin borde ni barras: recorta lo que sobre (como object-fit: cover)
            k = max(W / im.width, H / im.height)
            im = im.resize((math.ceil(im.width * k), math.ceil(im.height * k)), Image.LANCZOS)
            x0, y0 = (im.width - W) // 2, (im.height - H) // 2
            s.off, s.k = (x0 / k, y0 / k), k
            im = im.crop((x0, y0, x0 + W, y0 + H))
            if d.get("gris", True):
                im = est.tonificar(im)
            s.x, s.y, s.card = W / 2, H / 2, (W, H)
            return im.convert("RGBA")
        if d.get("crop") and (d.get("fundir") or d.get("caja")):
            im = im.crop(tuple(d["crop"]))
        if d.get("fundir"):   # apoyo sutil: sin marco ni sombra, bordes que se desvanecen en el fondo (no se nota la imagen)
            s.k = d["ancho"] / im.width
            im = im.resize((d["ancho"], round(d["ancho"] * im.height / im.width)), Image.LANCZOS)
            if d.get("gris", False):
                im = est.tonificar(im)
            out = im.convert("RGBA")
            out.putalpha(_mascara_fundida(out.size, d.get("fundir")))
            s.card = out.size
            return out
        if d.get("caja"):   # foto en caja recta, limpia: sin borde blanco ni sombra (láminas suizas, miniaturas)
            s.k = d["ancho"] / im.width
            im = im.resize((d["ancho"], round(d["ancho"] * im.height / im.width)), Image.LANCZOS)
            if d.get("gris", False):
                im = est.tonificar(im)
            s.card = im.size
            out = im.convert("RGBA")
            return out.rotate(s.rot, Image.BICUBIC, expand=True) if s.rot else out
        if d.get("crop"):
            im = im.crop(tuple(d["crop"]))
            s.off = tuple(d["crop"][:2])
        s.k = d["ancho"] / im.width
        im = im.resize((d["ancho"], round(d["ancho"] * im.height / im.width)), Image.LANCZOS)
        if d.get("gris", True):
            im = est.tonificar(im)
        s.borde = 16
        card = Image.new("RGBA", (im.width + 32, im.height + 32), est.borde + (255,))
        card.paste(im, (16, 16))
        s.card = card.size
        return _sombra(card, s.rot)

    def _recorte(s, est, base):
        d, trazo = s.d, 12
        im = Image.open(base / d["src"]).convert("RGBA")
        bbox = im.getbbox()
        im = im.crop(bbox)
        s.k = d["ancho"] / im.width
        s.off = bbox[:2]
        im = im.resize((d["ancho"], round(d["ancho"] * im.height / im.width)), Image.LANCZOS)
        pad = trazo + 4
        s.borde = pad
        big = Image.new("RGBA", (im.width + 2 * pad, im.height + 2 * pad))
        big.paste(im, (pad, pad))
        a = big.getchannel("A").point(lambda v: 255 if v > 40 else 0).filter(ImageFilter.MaxFilter(2 * trazo + 1))
        rgb = est.tonificar(big.convert("RGB")) if d.get("gris", True) else big.convert("RGB")
        blanco = Image.new("RGBA", big.size, est.borde + (255,))
        blanco.putalpha(a)
        obj = rgb.convert("RGBA")
        obj.putalpha(big.getchannel("A"))
        blanco.alpha_composite(obj)
        s.card = big.size
        return _sombra(blanco, s.rot)

    def _etiqueta(s, est):
        d = s.d
        nombre_fondo = d.get("fondo", "acento")
        fondo = est.color(nombre_fondo)
        letra = est.color(d["letra"]) if d.get("letra") else est.tinta if nombre_fondo == "acento" else \
            est.acento if nombre_fondo == "tinta" else _contraste(fondo)
        lineas = d["lineas"]  # [[texto, tamaño, cursiva, peso]]
        fuentes = [est.font_rol(d["rol"], t, w) if d.get("rol") else est.font(t, it, w) for (_, t, it, w) in lineas]
        cajas = [f.getbbox(l[0]) for f, l in zip(fuentes, lineas)]
        px, py = d.get("pad", [34, 18])
        tw = max(b[2] - b[0] for b in cajas) + 2 * px
        th = sum(b[3] - b[1] for b in cajas) + py * (len(lineas) + 1)
        im = Image.new("RGBA", (tw, th))
        ImageDraw.Draw(im).rounded_rectangle((0, 0, tw - 1, th - 1), radius=d.get("radio", 0), fill=fondo + (255,))
        dr, yy = ImageDraw.Draw(im), py
        for f, b, l in zip(fuentes, cajas, lineas):
            dr.text(((tw - (b[2] - b[0])) / 2 - b[0], yy - b[1]), l[0], font=f, fill=letra)
            yy += b[3] - b[1] + py
        s.card = im.size
        if not d.get("sombra", True):
            return im.rotate(s.rot, Image.BICUBIC, expand=True) if s.rot else im
        return _sombra(im, s.rot)

    def punto(s, px, py):
        """Punto (px, py) de la imagen fuente → coordenadas de pantalla con la pieza en reposo."""
        x = (px - s.off[0]) * s.k + s.borde - s.card[0] / 2
        y = (py - s.off[1]) * s.k + s.borde - s.card[1] / 2
        c, sn = math.cos(math.radians(-s.rot)), math.sin(math.radians(-s.rot))
        return s.x + x * c - y * sn, s.y + x * sn + y * c

    def contorno(s, margen=14):
        w, h = s.card[0] + 2 * margen, s.card[1] + 2 * margen
        c, sn = math.cos(math.radians(-s.rot)), math.sin(math.radians(-s.rot))
        pts = [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2), (-w / 2, -h / 2 - 6)]
        return [(s.x + x * c - y * sn, s.y + x * sn + y * c) for x, y in pts]

    def _vidrio(s, lienzo, t):
        d = s.d
        p = ease_out(clamp((t - s.t0) / max(.05, s.dur)))
        w, h = int(s.card[0] * (.92 + .08 * p)), int(s.card[1] * (.92 + .08 * p))
        fl = d.get("flotar", s.est.flotar_elementos)
        dx = dy = 0
        if fl:
            fase = (zlib.crc32(str(d.get("grupo") or s.id).encode()) % 628) / 100
            dx = fl * camara.ruido(t + fase * 3, "ex", 3.3)
            dy = .7 * fl * camara.ruido(t + fase * 3, "ey", 4.1)
        x0, y0 = int(s.x - w / 2 + dx), int(s.y - h / 2 + dy + 30 * (1 - p))
        caja_vidrio(lienzo, x0, y0, w, h, d.get("radio", 28), p, d.get("desenfoque", 22),
                    s.est.color(d.get("color", "blanco")), d.get("velo", .28))

    def _contador(s, lienzo, t):
        d = s.d
        p = ease_out(clamp((t - s.t0) / d.get("cuenta_s", 1.0)))
        v = d.get("desde", 0) + (d.get("hasta", 100) - d.get("desde", 0)) * p
        txt = texto_contador(d, v)
        el = Elemento({"id": s.id, "tipo": "texto", "x": s.x, "y": s.y, "t0": s.t0, "t1": s.t1, "entra": "fundido", "dur": .01,
                       "lineas": [{"texto": txt, "rol": d.get("rol", "display"), "tam": d.get("tam", 160), "color": d.get("color", "blanco")}],
                       "luz": d.get("luz", False), "sombra": d.get("sombra", True)}, s.est, Path("."))
        lienzo.alpha_composite(el.img, (int(s.x - el.img.width / 2), int(s.y - el.img.height / 2)))

    def _barra(s, lienzo, t):
        d = s.d
        w, h = s.card
        p = ease_out(clamp((t - s.t0) / d.get("crece_s", .6)))
        dr = ImageDraw.Draw(lienzo)
        if d.get("direccion") == "horizontal":                    # crece de izquierda a derecha; (x, y) = centro de la barra completa
            x0, y0 = int(s.x - w / 2), int(s.y - h / 2)
            dr.rectangle((x0, y0, x0 + max(1, int(w * p)), y0 + h), fill=s.est.color(d.get("color", "acento")) + (255,))
            if d.get("contorno", True):
                dr.rectangle((x0, y0, x0 + w, y0 + h), outline=(245, 245, 245, 255), width=1)
            return
        hh = max(1, int(h * p))
        x0, y1 = int(s.x - w / 2), int(s.y)                        # (x, y) = centro de la base
        dr.rectangle((x0, y1 - hh, x0 + w, y1), fill=s.est.color(d.get("color", "acento")) + (255,))
        if d.get("contorno", True):                                # contorno escalonado de 1 px (DRUpn)
            for k in (0, 5):
                dr.rectangle((x0 - k, y1 - hh - k, x0 + w + k, y1), outline=(245, 245, 245, 255), width=1)

    def _destello(s, lienzo, t):
        tam = s.d.get("tam", 90)
        vida = (t - s.t0) / max(.05, s.t1 - s.t0)
        k = ease_out(min(1, (t - s.t0) / .12)) * (.75 + .25 * math.sin(t * 2 * math.pi * s.d.get("titila", 3)))
        k *= 1 - max(0, (vida - .85) / .15)
        r = tam / 2 * k
        if r < 2:
            return
        capa = Image.new("RGBA", (int(tam * 3), int(tam * 3)))
        dr = ImageDraw.Draw(capa)
        cx = cy = tam * 1.5
        w = r * .16
        pts = [(cx, cy - r), (cx + w, cy - w), (cx + r, cy), (cx + w, cy + w), (cx, cy + r), (cx - w, cy + w), (cx - r, cy), (cx - w, cy - w)]
        dr.polygon(pts, fill=(255, 255, 255, 255))
        col = s.est.color(s.d.get("color", "acento2"))
        glow = capa.filter(ImageFilter.GaussianBlur(tam * .12))
        tinte = Image.new("RGBA", capa.size, col + (255,))
        tinte.putalpha(glow.getchannel("A").point(lambda v: min(255, int(v * 2.2))))
        tinte.alpha_composite(capa)
        lienzo.alpha_composite(tinte, (int(s.x - cx), int(s.y - cy)))

    def _panel(s, lienzo, t):
        w, h = s.card
        p = (t - s.t0) / .22
        blanco = 1 - ease_out(clamp((p - .35) / .65))           # quemado blanco que se abre y revela
        cara = Image.new("RGB", (w, h), (250, 250, 246))
        if s.contenido is not None:
            cara = Image.blend(s.contenido, cara, float(clamp(blanco)))
        if s.d.get("desenfoque"):
            cara = cara.filter(ImageFilter.GaussianBlur(s.d["desenfoque"]))
        esc = .6 + .4 * ease_out(clamp(p))
        cw_, ch_ = max(1, int(w * esc)), max(1, int(h * esc))
        cara = cara.resize((cw_, ch_), Image.BILINEAR)
        x0, y0 = int(s.x - cw_ / 2), int(s.y - ch_ / 2)
        # brillo que suelta la pantalla
        halo = Image.new("RGBA", (cw_ + 240, ch_ + 240))
        ImageDraw.Draw(halo).rectangle((120, 120, 120 + cw_, 120 + ch_), fill=(255, 255, 250, int(150 + 105 * blanco)))
        halo = halo.filter(ImageFilter.GaussianBlur(55))
        lienzo.alpha_composite(halo, (x0 - 120, y0 - 120))
        if blanco > .05:                                          # el estallido alumbra todo el cuadro un instante
            lienzo.alpha_composite(Image.new("RGBA", lienzo.size, (255, 255, 250, int(70 * blanco))))
        lienzo.alpha_composite(cara.convert("RGBA"), (x0, y0))
        if s.d.get("reflejo", True):                              # reflejo en la mesa
            ref = cara.transpose(Image.FLIP_TOP_BOTTOM).crop((0, 0, cw_, ch_ // 2)).convert("RGBA")
            grad = Image.linear_gradient("L").resize((cw_, ch_ // 2)).point(lambda v: int((255 - v) * .28))
            ref.putalpha(grad)
            lienzo.alpha_composite(ref.filter(ImageFilter.GaussianBlur(6)), (x0, y0 + ch_ + 4))

    def _pixeles(s, lienzo, t):
        celda = s.d.get("celda", 22)
        w, h = s.card
        paso = int(t * 12)
        vida = clamp((t - s.t0) / max(.05, s.t1 - s.t0))
        densidad = .55 * math.sin(math.pi * vida) + .1          # se arma, llena y se desarma
        rng = np.random.default_rng(zlib.crc32(f"{s.id}-{paso}".encode()))
        capa = Image.new("RGBA", lienzo.size)
        dr = ImageDraw.Draw(capa)
        x0, y0 = s.x - w / 2, s.y - h / 2
        for i in range(max(1, w // celda)):
            for j in range(max(1, h // celda)):
                if rng.random() < densidad:
                    c = s.colores[int(rng.integers(len(s.colores)))]
                    a = int(150 + 105 * rng.random())
                    dr.rectangle((x0 + i * celda, y0 + j * celda, x0 + (i + 1) * celda - 3, y0 + (j + 1) * celda - 3),
                                 fill=c + (a,))
        lienzo.alpha_composite(capa)

    @property
    def es_fondo(s):
        """Foto o recorte que cubre gran parte del cuadro (hoja, tarjeta o fondo grande; un texto ancho es contenido, no fondo): no es contenido, viaja con la cámara sin escalarse."""
        return s.d["tipo"] in ("foto", "recorte") and s.img is not None and (s.img.width >= PANTALLA_FONDO_ANCHO * W or s.img.width * s.img.height >= PANTALLA_FONDO_AREA * W * H)

    def dibujar(s, lienzo, t):
        if not (s.t0 <= t < s.t1):
            return
        if s.d.get("tecleo") and s.d["tipo"] == "texto":   # se teclea: `tecleo` letras por segundo, con cursor que parpadea
            n = int((t - s.t0) * float(s.d["tecleo"])) + 1
            total = sum(len(l.get("texto", "")) for l in s.d["lineas"])
            cursor = s.d.get("cursor", True) and (n < total or int(t * 2.5) % 2 == 0)
            cache = s.__dict__.setdefault("_tecleo", {})
            if (n, cursor) not in cache:
                resto, lineas, puesto = n, [], False
                for l in s.d["lineas"]:
                    txt = l.get("texto", "")
                    trozo = txt[:max(0, resto)]
                    resto -= len(txt)
                    if cursor and not puesto and (resto < 0 or l is s.d["lineas"][-1]):
                        trozo += "|"
                        puesto = True
                    lineas.append({**l, "texto": trozo or " "})
                cache[(n, cursor)] = Elemento({**s.d, "tecleo": None, "lineas": lineas, "entra": "fundido", "dur": .01},
                                              s.est, Path(".")).img
            img = cache[(n, cursor)]
            lienzo.alpha_composite(img, (int(s.x - img.width / 2), int(s.y - img.height / 2)))
            return
        if s.img is None:
            if s.d["tipo"] == "clip":
                if s.cuadros_clip:
                    k = min(len(s.cuadros_clip) - 1, int((t - s.t0) * s.d.get("velocidad", 1) * FPS))
                    im = Image.open(s.cuadros_clip[k]).convert("RGBA")
                    if s.d.get("acercar"):   # C-0003: el clip también se acerca solo, recortado al centro
                        z = 1 + s.d["acercar"] * efectos.acercar_k((t - s.t0) / max(.05, s.t1 - s.t0))
                        w0, h0 = im.size
                        im = im.resize((int(w0 * z), int(h0 * z)), Image.BILINEAR)
                        l, a = (im.width - w0) // 2, (im.height - h0) // 2
                        im = im.crop((l, a, l + w0, a + h0))
                    if s.d.get("ancho") and not s.d.get("cubrir"):   # apoyo sutil: chico y fundido con el fondo
                        w = int(s.d["ancho"])
                        im = im.resize((w, int(w * H / W)), Image.BILINEAR)
                        im.putalpha(_mascara_fundida(im.size, s.d.get("fundir", True)))
                        p = clamp((t - s.t0) / max(.05, s.dur))
                        if p < 1:
                            im.putalpha(im.getchannel("A").point(lambda v: int(v * p)))
                        lienzo.alpha_composite(im, (int(s.x - im.width / 2), int(s.y - im.height / 2)))
                    else:
                        lienzo.alpha_composite(im)
                return
            if s.d["tipo"] == "vidrio":
                return s._vidrio(lienzo, t)
            if s.d["tipo"] == "contador":
                return s._contador(lienzo, t)
            if s.d["tipo"] == "barra":
                return s._barra(lienzo, t)
            if s.d["tipo"] == "destello":
                return s._destello(lienzo, t)
            if s.d["tipo"] == "panel":
                return s._panel(lienzo, t)
            return s._pixeles(lienzo, t)
        p = (t - s.t0) / s.dur
        dx = dy = 0
        sc, img = 1.0, s.img
        if s.entra == "pop":
            sc = .55 + .45 * ease_back(p)
        elif s.entra == "cae":
            dy = -420 * (1 - ease_back(p))
        elif s.entra == "izq":
            dx = -900 * (1 - ease_out(p))
        elif s.entra == "der":
            dx = 900 * (1 - ease_out(p))
        elif s.entra == "sube":
            dy = 900 * (1 - ease_out(p))
        elif s.entra == "barrido":
            w = max(1, int(img.width * ease_io(p)))
            img = img.crop((0, 0, w, img.height))
            dx = -(s.img.width - w) / 2
        elif s.entra == "llega":  # rápido que desacelera suave (ease-out exponencial): escala 1,15→1 y sube 40 px
            k = 1 - (1 - 2 ** (-10 * clamp(p))) if p < 1 else 1
            sc, dy = 1.15 - .15 * k, 40 * (1 - k)
            if p < 1:
                img = img.copy()
                img.putalpha(img.getchannel("A").point(lambda v: int(v * clamp(p * 3))))
        elif s.entra == "golpe":  # entra grande y se asienta, como un punch de texto
            sc = 1 + .35 * (1 - ease_out(p))
        if s.entra == "smear" and p < 1:     # barrido horizontal de 2 cuadros (entrada seca editorial)
            k = int(60 * (1 - ease_out(p)))
            if k > 1:
                capa = Image.new("RGBA", img.size)
                for j in range(5):
                    capa.alpha_composite(img.transform(img.size, Image.AFFINE, (1, 0, -k * j / 4, 0, 1, 0)))
                img = capa
        if s.entra == "enfoque" and p < 1:   # entra desenfocado y se pone nítido (texto palabra a palabra)
            img = img.filter(ImageFilter.GaussianBlur(14 * (1 - ease_out(p))))
            img.putalpha(img.getchannel("A").point(lambda v: int(v * clamp(p * 1.8))))
        if s.entra in ("fundido", "golpe") and p < 1:
            img = img.copy()
            img.putalpha(img.getchannel("A").point(lambda v: int(v * clamp(p * 1.6))))
        if s.d.get("acercar"):   # C-0003: el apoyo se acerca solo y lento durante toda su vida (Ken Burns de cine)
            sc *= 1 + s.d["acercar"] * efectos.acercar_k((t - s.t0) / max(.05, s.t1 - s.t0))
        if sc != 1.0:
            w0, h0 = img.size
            img = img.resize((max(1, int(img.width * sc)), max(1, int(img.height * sc))), Image.BILINEAR)
            if s.d.get("cubrir") and sc > 1:   # a pantalla completa sigue cubriendo el cuadro: recorta al centro
                l, a = (img.width - w0) // 2, (img.height - h0) // 2
                img = img.crop((l, a, l + w0, a + h0))
        fl = s.d.get("flotar", s.est.flotar_elementos)
        if fl:   # cada elemento deriva (fase propia, o la de su `grupo`: la composición se mueve junta) y más cuanto más cerca está
            fase = (zlib.crc32(str(s.d.get("grupo") or s.id).encode()) % 628) / 100
            prof = .4 + .9 * s.d.get("profundidad", .5)
            dx += fl * prof * camara.ruido(t + fase * 3, "ex", 3.3)
            dy += .7 * fl * prof * camara.ruido(t + fase * 3, "ey", 4.1)
        pos = (int(s.x + dx - img.width / 2), int(s.y + dy - img.height / 2))
        if s.d["tipo"] in ("texto", "etiqueta") and img.width - 2 * AIRE_TEXTO < .9 * W:   # ningún texto se sale del margen lateral en NINGÚN cuadro (flotación, barrido, parallax)
            m = config.TEXTO_MARGEN_LATERAL_PX + getattr(s, "margen_cam", 0)
            if img.width - 2 * AIRE_TEXTO <= W - 2 * m:   # si ni centrado cabe, es asunto de la compuerta (achicar), no del margen
                pos = (int(clamp(pos[0], m - AIRE_TEXTO, W - m + AIRE_TEXTO - img.width)), pos[1])
        if s.d.get("fusion") in FUSIONES:   # el negro (pantalla) o el blanco (multiplicar) desaparecen
            x0, y0 = max(0, pos[0]), max(0, pos[1])
            x1, y1 = min(lienzo.width, pos[0] + img.width), min(lienzo.height, pos[1] + img.height)
            if x1 > x0 and y1 > y0:
                base = np.asarray(lienzo.crop((x0, y0, x1, y1)), np.float32)
                capa = np.asarray(img.crop((x0 - pos[0], y0 - pos[1], x1 - pos[0], y1 - pos[1])), np.float32)
                a_ = capa[..., 3:4] / 255
                ba = base[..., 3:4] / 255
                b_, c_ = base[..., :3] / 255, capa[..., :3] / 255
                mezcla = 1 - (1 - b_) * (1 - c_) if s.d["fusion"] == "pantalla" else b_ * c_
                # sobre una capa transparente (pantalla oculta: el contenido va aparte del fondo) no hay con qué mezclar:
                # el negro (pantalla) o el blanco (multiplicar) se vuelven transparentes y el resto se dibuja con su color
                kf = c_.max(-1, keepdims=True) if s.d["fusion"] == "pantalla" else 1 - c_.min(-1, keepdims=True)
                a_ov = a_ * (ba + (1 - ba) * kf)
                color = ba * mezcla + (1 - ba) * c_
                a_out = ba + (1 - ba) * a_ov
                out = np.empty_like(base)
                out[..., :3] = (b_ * ba * (1 - a_ov) + color * a_ov) / np.maximum(a_out, 1e-6) * 255
                out[..., 3:4] = a_out * 255
                lienzo.paste(Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)), (x0, y0))
            return
        lienzo.alpha_composite(img, pos)


def _elipse(cx, cy, rx, ry, vueltas=1.12, seed=0, n=140):
    rng, out = np.random.default_rng(seed), []
    for i in range(n):
        a = -2.2 + 2 * math.pi * vueltas * i / (n - 1)
        j = 1 + .035 * math.sin(i * .21 + seed) + rng.normal(0, .004)
        out.append((cx + rx * j * math.cos(a), cy + ry * j * math.sin(a)))
    return out


class Trazo:
    """Línea del color de acento que se dibuja sola (trim path)."""

    def __init__(s, pts, t0, dur, t1, grosor=9, z="frente", punto=False, color=None, nodos=0):
        s.pts, s.t0, s.dur, s.t1, s.grosor, s.z, s.punto = pts, t0, dur, t1, grosor, z, punto
        s.color, s.nodos = color, nodos
        s.cum = np.concatenate([[0], np.cumsum([math.dist(a, b) for a, b in zip(pts, pts[1:])])])

    def dibujar(s, lienzo, t, est):
        if not (s.t0 <= t < s.t1):
            return
        L = s.cum[-1] * ease_io((t - s.t0) / s.dur)
        k = int(np.searchsorted(s.cum, L))
        pts = s.pts[:k]
        if 0 < k < len(s.pts):
            a, b = s.pts[k - 1], s.pts[k]
            r = (L - s.cum[k - 1]) / max(1e-6, s.cum[k] - s.cum[k - 1])
            pts = pts + [(a[0] + (b[0] - a[0]) * r, a[1] + (b[1] - a[1]) * r)]
        col = est.color(s.color) if s.color else est.acento
        d = ImageDraw.Draw(lienzo)
        if len(pts) > 1 and s.nodos:   # línea de luz con nodos (línea de tiempo): glow debajo
            capa = Image.new("RGBA", lienzo.size)
            dc = ImageDraw.Draw(capa)
            dc.line(pts, fill=col + (255,), width=s.grosor * 4)
            for j in range(s.nodos):
                q = s.pts[0][0] + (s.pts[-1][0] - s.pts[0][0]) * (j + .5) / s.nodos, s.pts[0][1]
                if q[0] <= pts[-1][0]:
                    dc.ellipse((q[0] - 16, q[1] - 16, q[0] + 16, q[1] + 16), fill=col + (255,))
            lienzo.alpha_composite(capa.filter(ImageFilter.GaussianBlur(10)))
            for j in range(s.nodos):
                q = s.pts[0][0] + (s.pts[-1][0] - s.pts[0][0]) * (j + .5) / s.nodos, s.pts[0][1]
                if q[0] <= pts[-1][0]:
                    d.ellipse((q[0] - 7, q[1] - 7, q[0] + 7, q[1] + 7), fill=(235, 252, 255, 255))
        if len(pts) > 1:
            d.line(pts, fill=col + (255,), width=s.grosor, joint="curve")
        if s.punto and k >= len(s.pts):
            x, y = s.pts[-1]
            d.ellipse((x - 14, y - 14, x + 14, y + 14), fill=est.acento + (255,), outline=est.tinta + (255,), width=3)


def trazos_de(sb, elementos):
    por_id = {e.id: e for e in elementos}
    out = []
    for i, d in enumerate(sb.get("trazos", [])):
        t0, dur = d["t0"], d.get("dur", .5)
        t1, z, g = d.get("t1", t0 + dur + 1.5), d.get("z", "frente"), d.get("grosor", 9)
        if d["tipo"] == "rect":
            out.append(Trazo(por_id[d["sobre"]].contorno(), t0, dur, t1, g, z))
        elif d["tipo"] == "elipse":
            e = por_id.get(d.get("sobre"))
            cx, cy = d["centro"]
            rx, ry = d["radio"]
            pts = _elipse(cx, cy, rx, ry, seed=i)
            if e:
                pts = [e.punto(x, y) for x, y in pts]
            out.append(Trazo(pts, t0, dur, t1, g, z, color=d.get("color")))
        elif d["tipo"] == "rayos":
            ox, oy = d["desde"]
            for j, (ex, ey) in enumerate(d["hacia"]):
                pts = [(ox + (ex - ox) * .45, oy + (ey - oy) * .45),
                       (ox + (ex - ox) * .72 + (30 if j % 2 else -30), oy + (ey - oy) * .72), (ex, ey)]
                out.append(Trazo(pts, t0 + j * d.get("paso", .08), dur, t1, d.get("grosor", 7), z, punto=True))
        elif d["tipo"] == "linea":
            out.append(Trazo([tuple(p) for p in d["puntos"]], t0, dur, t1, g, z, color=d.get("color"), nodos=d.get("nodos", 0)))
        elif d["tipo"] == "reticula":   # retícula de cols×filas con cruces de registro; cada línea se dibuja sola
            cols, filas, m = d.get("cols", 3), d.get("filas", 3), d.get("margen", 60)
            x0, y0, x1, y1 = m, m + 170, W - m, H - m - 300
            for c in range(cols + 1):
                x = x0 + (x1 - x0) * c / cols
                out.append(Trazo([(x, y0), (x, y1)], t0 + c * .03, dur, t1, d.get("grosor", 1), z, color=d.get("color")))
            for f in range(filas + 1):
                y = y0 + (y1 - y0) * f / filas
                out.append(Trazo([(x0, y), (x1, y)], t0 + f * .03, dur, t1, d.get("grosor", 1), z, color=d.get("color")))
            cr = d.get("cruces", 14)
            if cr:
                for c in range(cols + 1):
                    for f in range(filas + 1):
                        x, y = x0 + (x1 - x0) * c / cols, y0 + (y1 - y0) * f / filas
                        out.append(Trazo([(x - cr, y), (x + cr, y)], t0 + dur, .05, t1, 3, z, color=d.get("color")))
                        out.append(Trazo([(x, y - cr), (x, y + cr)], t0 + dur, .05, t1, 3, z, color=d.get("color")))
        else:
            raise ValueError(f"trazo {i}: tipo desconocido {d['tipo']!r}")
    return out


def tramos_subtitulo(cfg: dict, palabras) -> list:
    """Cuándo se ve cada bloque de subtítulo (segundos de la fuente): [(t0, t1, i0, i1)]. Lo usan el motor y la compuerta."""
    bloques = cfg.get("bloques") or Subtitulos._auto(palabras)
    ocultar, out = cfg.get("ocultar", []), []
    for n, (i0, i1) in enumerate(bloques):
        t0 = palabras[i0]["s"]
        t1 = palabras[bloques[n + 1][0]]["s"] if n + 1 < len(bloques) else palabras[i1 - 1]["e"] + .6
        if not any(a <= t0 < b for a, b in ocultar):
            out.append((t0, t1, i0, i1))
    return out


# Pantallas completas (la persona no se ve): la cámara hace UN SOLO movimiento A→B que dura toda la escena, con curva que
# acelera y desacelera (ease_io). Nada más se suma ahí: ni ruta global, ni ruido, ni seguimiento de elementos, ni golpes.
# Pablo 07-nov: «un keyframe que mueve la cámara de punto A a punto B; en todo el clip solo hay un movimiento, fluido; solo uno».
# Cada tipo: (zoom_A, zoom_B, dx_A, dx_B, dy_A, dy_B) con el desplazamiento en píxeles del cuadro de salida.
PANTALLA_ZOOM_BASE = 1.00   # zoom de reposo (inicio del acercarse / fin del alejarse)
# «suave»: A→B toda la escena con ease_io. Zoom fijo del viaje con margen para desplazarse sin salirse del cuadro (W*(1-1/z)/2 >= viaje).
PANTALLA_ZOOM_CERCA = 1.28  # zoom del extremo cercano en acercarse / alejarse
PANTALLA_ZOOM_VIAJE = 1.30  # margen a 1.30 = 124 px de lado y 221 px de alto
PANTALLA_VIAJE_PX = 120     # desplazamiento lateral de A a B (de -120 a +120)
PANTALLA_SUBIDA_PX = 180    # desplazamiento vertical de la subida (de +180 a -180)
# «continuo» (Pablo 07-nov): velocidad CONSTANTE (lineal) y el MISMO recorrido que suave (más recorrido se veía «demasiado lejos»);
# sin arranque ni frenada: la escena ya "venía moviéndose" y sigue al terminar (carro en la autopista).
PANTALLA_CONT_ZOOM_CERCA = PANTALLA_ZOOM_CERCA
PANTALLA_CONT_ZOOM_VIAJE = PANTALLA_ZOOM_VIAJE
PANTALLA_CONT_VIAJE_PX = PANTALLA_VIAJE_PX
PANTALLA_CONT_SUBIDA_PX = PANTALLA_SUBIDA_PX
PANTALLA_CAMARA_MOV = ("suave", "continuo")   # `escena["camara_mov"]`; si falta, «suave»
PANTALLA_MOVIMIENTOS = {
    "acercarse": (PANTALLA_ZOOM_BASE, PANTALLA_ZOOM_CERCA, 0, 0, 0, 0),
    "alejarse": (PANTALLA_ZOOM_CERCA, PANTALLA_ZOOM_BASE, 0, 0, 0, 0),
    "izq-der": (PANTALLA_ZOOM_VIAJE, PANTALLA_ZOOM_VIAJE, -PANTALLA_VIAJE_PX, PANTALLA_VIAJE_PX, 0, 0),
    "der-izq": (PANTALLA_ZOOM_VIAJE, PANTALLA_ZOOM_VIAJE, PANTALLA_VIAJE_PX, -PANTALLA_VIAJE_PX, 0, 0),
    "subida": (PANTALLA_ZOOM_VIAJE, PANTALLA_ZOOM_VIAJE, 0, 0, PANTALLA_SUBIDA_PX, -PANTALLA_SUBIDA_PX),
}
PANTALLA_MOVIMIENTOS_CONTINUOS = {
    "acercarse": (PANTALLA_ZOOM_BASE, PANTALLA_CONT_ZOOM_CERCA, 0, 0, 0, 0),
    "alejarse": (PANTALLA_CONT_ZOOM_CERCA, PANTALLA_ZOOM_BASE, 0, 0, 0, 0),
    "izq-der": (PANTALLA_CONT_ZOOM_VIAJE, PANTALLA_CONT_ZOOM_VIAJE, -PANTALLA_CONT_VIAJE_PX, PANTALLA_CONT_VIAJE_PX, 0, 0),
    "der-izq": (PANTALLA_CONT_ZOOM_VIAJE, PANTALLA_CONT_ZOOM_VIAJE, PANTALLA_CONT_VIAJE_PX, -PANTALLA_CONT_VIAJE_PX, 0, 0),
    "subida": (PANTALLA_CONT_ZOOM_VIAJE, PANTALLA_CONT_ZOOM_VIAJE, 0, 0, PANTALLA_CONT_SUBIDA_PX, -PANTALLA_CONT_SUBIDA_PX),
}
PANTALLA_MARGEN_PX = 40     # holgura entre lo dibujado y el borde de la zona visible en el peor momento del movimiento
PANTALLA_ESCALA_MIN = 0.3   # lo más que se achica el contenido. El movimiento NUNCA se reduce (Pablo): lo que cambia es el tamaño
PANTALLA_MUESTRAS = 8       # cuadros de la escena donde se mide la caja de lo dibujado
PANTALLA_FONDO_ANCHO = 0.70  # un elemento de al menos este ancho (fracción del cuadro) o
PANTALLA_FONDO_AREA = 0.50   # esta área es fondo/hoja: no se mide ni se achica con el contenido
PANTALLA_ALFA_MIN = 24      # alfa mínimo para contar un píxel como dibujado (ignora halos casi invisibles)


def progreso_pantalla(u, modo="suave"):
    """Avance 0→1 del movimiento a lo largo de la escena (u = 0→1): «suave» acelera y frena; «continuo» es lineal (velocidad constante)."""
    return u if modo == "continuo" else ease_io(u)


def movimiento_pantalla(tipo, modo="suave"):
    """(zoom_A, zoom_B, dx_A, dx_B, dy_A, dy_B) del tipo de movimiento en el modo de la escena."""
    return (PANTALLA_MOVIMIENTOS_CONTINUOS if modo == "continuo" else PANTALLA_MOVIMIENTOS)[tipo]


def zona_visible(mov):
    """Zona del cuadro de salida que SIEMPRE se ve durante el movimiento `mov`: la intersección de las vistas de A y de B."""
    zA, zB, xA, xB, yA, yB = mov
    zona = [0.0, 0.0, float(W), float(H)]
    for z, dx, dy in ((zA, xA, yA), (zB, xB, yB)):
        cw, ch = W / z, H / z
        dx, dy = clamp(dx, -(W - cw) / 2, (W - cw) / 2), clamp(dy, -(H - ch) / 2, (H - ch) / 2)
        v = ((W - cw) / 2 + dx, (H - ch) / 2 + dy, (W + cw) / 2 + dx, (H + ch) / 2 + dy)
        zona = [max(zona[0], v[0]), max(zona[1], v[1]), min(zona[2], v[2]), min(zona[3], v[3])]
    return tuple(zona)


def ajuste_pantalla(mov, caja, margen=PANTALLA_MARGEN_PX):
    """(escala, tx, ty): el contenido (caja x0, y0, x1, y1 de lo dibujado) se achica hacia el centro del cuadro lo justo (no menos de
    PANTALLA_ESCALA_MIN) y se corre lo mínimo para quedar dentro de la zona visible común de todo el recorrido, con `margen`.
    Si ni así cabe, se centra en la zona. El movimiento no se toca. Sin contenido: (1, 0, 0)."""
    if caja is None:
        return 1.0, 0.0, 0.0
    zona = zona_visible(mov)
    k = min(1.0, (zona[2] - zona[0] - 2 * margen) / max(1, caja[2] - caja[0]), (zona[3] - zona[1] - 2 * margen) / max(1, caja[3] - caja[1]))
    k = max(PANTALLA_ESCALA_MIN, k)
    desp = []
    for lo, hi, c, z0, z1 in ((caja[0], caja[2], W / 2, zona[0], zona[2]), (caja[1], caja[3], H / 2, zona[1], zona[3])):
        a, b = c + k * (lo - c), c + k * (hi - c)
        if b - a > z1 - z0 - 2 * margen:      # no cabe ni en la escala mínima: centrado
            desp.append((z0 + z1) / 2 - (a + b) / 2)
        else:
            desp.append(max(0.0, z0 + margen - a) - max(0.0, b - (z1 - margen)))
    return k, desp[0], desp[1]


def movimientos_pantalla(nombre, escenas):
    """Tipo de movimiento de cada escena oculta (clave: su t0). Determinista: semilla = nombre del proyecto + t0; dos escenas
    ocultas seguidas nunca repiten el tipo."""
    tipos, previo, out = list(PANTALLA_MOVIMIENTOS), None, {}
    for e in escenas:
        if e.get("persona", {}).get("modo") != "oculta":
            previo = None
            continue
        k = zlib.crc32(f"{nombre}|{e['t0']:.3f}".encode()) % len(tipos)
        if tipos[k] == previo:
            k = (k + 1) % len(tipos)
        out[e["t0"]] = previo = tipos[k]
    return out


FRANJA_TAM_MIN = config.piso_texto_px()                 # el rótulo de una franja nunca baja del piso de legibilidad (reglas.json)
HUD_MONO_TAM = max(26, config.piso_texto_px())          # la letra mono de las cajas HUD respeta el mismo piso
PUNCH_ZOOM = .07      # cuánto zoom suma un golpe de zoom (`punch`); único lugar del número
PUNCH_SUBE_S = .16    # lo que tarda en subir
ENCUADRES = ((1.06, -40), (1.06, 40), (1.22, -40), (1.22, 40))   # (zoom, viaje lateral px): plano medio y plano corto
ENCUADRE_SALTO_MIN = 0.10             # el encuadre siguiente difiere del anterior al menos esto en zoom: el cambio de composición se nota
ENCUADRE_CADA_S = (2.8, 4.6)          # cada cuánto cambia el plano: al azar dentro de este rango, siempre en el arranque de una palabra
ENCUADRE_CARA_MARGEN_PX = 60          # holgura entre la cara y el borde del cuadro al reencuadrar
ENCUADRE_CARA_SUAVE_PX = 40           # zona donde el empujón de la cara entra y sale con rampa (sin quiebre de velocidad)


def empuje_suave(x: float, k: float) -> float:
    """Empujón por una violación `x` (px; >0 = la cara pasó el margen): como max(0, x) pero con la esquina redondeada.
    0 si x <= -k; rampa cuadrática en (-k, k); x desde k. Siempre >= max(0, x) (la cara nunca queda más adentro del margen que con el empujón duro)
    y con velocidad continua: el empujón duro frenaba de golpe (4,6 px por cuadro de aceleración, muestra Swiss/Prestiggio 22 s)."""
    if k <= 0 or x <= -k:
        return max(0.0, x) if k <= 0 else 0.0
    return x if x >= k else (x + k) ** 2 / (4 * k)
ENCUADRE_TRAMO_MIN_S = 1.0            # un tramo de reencuadre más corto se queda quieto: moverse 0,16 de zoom en menos tiempo sería un brinco
CARA_SUAVE_S = 1.0                    # la caja estable de la cara se suaviza dos veces con esta ventana: sus escalones eran brincos de ~90 px
CARA_ESTABLE_S = 1.2                  # ventana de la caja de la cara: se queda con la más ajustada (una mano solo la agranda)


def _suavizar_caras(caras: dict, mapa) -> dict:
    """Dos pasadas de promedio móvil (ventana CARA_SUAVE_S) sobre la caja estable: los escalones de la caja (la ventana de «la más ajustada» deja de
    ver un cuadro) pasan de un salto a una rampa suave, sin sacudir la cámara. Cuadros sin cara quedan sin cara."""
    medio = max(1, round(CARA_SUAVE_S * FPS / 2))
    for _ in range(2):
        nuevo = {}
        for k, i in enumerate(mapa):
            if caras.get(i) is None:
                nuevo[i] = None
                continue
            vec = [caras[mapa[j]] for j in range(max(0, k - medio), min(len(mapa), k + medio + 1)) if caras.get(mapa[j]) is not None]
            nuevo[i] = tuple(sum(v[c] for v in vec) / len(vec) for c in range(4))
        caras = nuevo
    return caras


def caras_estables(carpeta, mapa, cerca=None) -> dict:
    """{cuadro fuente: caja de la cara (x0, y0, x1, y1) o None} para los cuadros que quedan. La caja sale de `persona.json`
    (estudio/persona.py); con el recorte viejo una mano levantada a la altura de la cabeza la ensanchaba y el reencuadre corría la cámara
    50-70 px durante esos cuadros y volvía (Pablo 08-nov, Pop seg 2: «ahí hay un salto»). Una mano solo AGRANDA la caja, así que
    se toma la caja más ajustada dentro de CARA_ESTABLE_S alrededor del cuadro (solo cuadros que quedan): la cabeza, sin las manos.
    Se guarda en `.cara-estable.json` (clave: persona.json + mapa) para que el render y el supervisor de cámara lean lo mismo.
    `cerca` (cuadros fuente; vistas previas): si no hay caché, solo se miden esos cuadros, su ventana y los vecinos que pide el suavizado (mismas
    cajas que el cálculo completo, que lee TODAS las máscaras: minutos en un video largo) y no se guarda nada."""
    import hashlib
    carpeta = Path(carpeta)
    origen = carpeta / persona.ARCHIVO
    if not origen.exists():
        return {}
    clave = f"v3-{origen.stat().st_mtime_ns}-{hashlib.md5(json.dumps(list(mapa)).encode()).hexdigest()}"
    cache = carpeta / ".cara-estable.json"
    if cache.exists():
        try:
            d = json.loads(cache.read_text())
            if d.get("clave") == clave:
                return {int(k): (tuple(v) if v else None) for k, v in d["caras"].items()}
        except (ValueError, KeyError):
            pass
    tabla, crudas = persona.Tabla(carpeta), {}

    def cruda(j):
        if j not in crudas:
            crudas[j] = tabla.cara(mapa[j])
        return crudas[j]
    medio = round(CARA_ESTABLE_S * FPS / 2)
    from bisect import bisect_left
    pedidos = None if cerca is None else set(cerca)
    ks = range(len(mapa)) if pedidos is None else [k for k in (bisect_left(mapa, i) for i in pedidos) if k < len(mapa) and mapa[k] in pedidos]
    if pedidos is not None:   # el suavizado (dos pasadas) mira ±CARA_SUAVE_S de cada cuadro: se miden también esos vecinos para dar las mismas cajas que el cálculo completo
        hasta = 2 * max(1, round(CARA_SUAVE_S * FPS / 2))
        ks = sorted({j for k in ks for j in range(max(0, k - hasta), min(len(mapa), k + hasta + 1))})
    out = {}
    for k in ks:
        i = mapa[k]
        if cruda(k) is None:
            out[i] = None
            continue
        vecinas = [cruda(j) for j in range(max(0, k - medio), min(len(mapa), k + medio + 1))
                   if abs(mapa[j] - i) <= medio and cruda(j) is not None]
        out[i] = (float(max(v[0] for v in vecinas)), float(max(v[1] for v in vecinas)),
                  float(min(v[2] for v in vecinas)), float(min(v[3] for v in vecinas)))
    out = _suavizar_caras(out, mapa)
    if pedidos is not None:
        return {i: out[i] for i in pedidos if i in out}
    try:
        cache.write_text(json.dumps({"clave": clave, "caras": {str(k): v for k, v in out.items()}}))
    except OSError:
        pass
    return out


def encuadres(sb: dict, palabras: list, fin: float, semilla: str) -> list:
    """[(t0, t1, (zoom_A, dx_A), (zoom_B, dx_B))] en tiempo fuente: el reencuadre de la persona (Pablo 07-nov: «hacer reencuadre de la
    composición… que la persona aparezca mucho más cerca, cada 4 s, cada 3»). Entre cambios de plano (cada 2,8–4,6 s, al arrancar una
    palabra) hay UN solo movimiento fluido A→B (ease_io) de un encuadre a otro distinto; el siguiente tramo parte de donde terminó el
    anterior (sin saltos) y nunca repite el encuadre. Determinista por proyecto."""
    import hashlib
    import random
    rnd = random.Random(int(hashlib.md5(semilla.encode()).hexdigest()[:8], 16))
    cortes = sorted((float(a), float(b)) for a, b in sb.get("cortes", []))
    quedan, t = [], 0.0
    for a, b in cortes:
        if a > t:
            quedan.append((t, a))
        t = max(t, b)
    if t < fin:
        quedan.append((t, fin))
    actual = rnd.choice(ENCUADRES)
    out = []
    for a, b in quedan:
        puntos, siguiente = [a], a + rnd.uniform(*ENCUADRE_CADA_S)
        for p in palabras:
            if a < p["s"] < b - 1.0 and p["s"] >= siguiente:
                puntos.append(p["s"])
                siguiente = p["s"] + rnd.uniform(*ENCUADRE_CADA_S)
        for x, y in zip(puntos, puntos[1:] + [b]):
            destino = rnd.choice([e for e in ENCUADRES if abs(e[0] - actual[0]) >= ENCUADRE_SALTO_MIN])
            if y - x < ENCUADRE_TRAMO_MIN_S:   # (el azar se gasta igual para no cambiar el resto de la secuencia)
                destino = actual
            out.append((x, y, actual, destino))
            actual = destino
    return out


def encuadre_en(lista: list, t: float) -> tuple:
    """(zoom, dx) del encuadre de la persona en el tiempo fuente t: interpola A→B con ease_io dentro de su tramo."""
    est = lista[0][2] if lista else (1.0, 0)   # antes del primer tramo (cuadro un pelo antes de su borde) vale su encuadre de partida, no 1.0: era un brinco al arrancar
    for a, b, A, B in lista:
        if a > t + 1e-6:
            break
        est = B if t >= b else tuple(x + (y - x) * ease_io((t - a) / max(b - a, 1e-6)) for x, y in zip(A, B))
    return est


def diccionario() -> dict:
    """perfil/diccionario.json: palabra mal oída → cómo se escribe en pantalla («Cloud», «Claudio» → «Claude»)."""
    f = config.RAIZ / "perfil" / "diccionario.json"
    try:
        return {k: v for k, v in json.loads(f.read_text()).items() if not k.startswith("_")} if f.exists() else {}
    except ValueError:
        return {}


class Subtitulos:
    """Bloques de 2–4 palabras sobre una tira de papel; las palabras aparecen cuando se dicen y las clave van resaltadas."""

    def __init__(s, sb, palabras, est):
        cfg = sb.get("subtitulos", {})
        s.est, s.y = est, cfg.get("y", 1455)
        s.resaltar, s.ocultar = set(cfg.get("resaltar", [])), cfg.get("ocultar", [])
        if est.subtitulo == "basico":
            s.f_reg = s.f_hi = est.sub_font(subtitulo_basico.TAM, False, 900)
        elif est.subtitulo == "hud":
            s.f_reg = s.f_hi = est.sub_font(cfg.get("tam", 64), False, 900)
        else:
            s.f_reg, s.f_hi = est.sub_font(70, False, 700), est.sub_font(74, True, 800)
        dic = diccionario()
        def nombre(w):      # «Cloud?» → «Claude?»: el diccionario mira la palabra sin signos y se los devuelve
            nucleo = w.strip("¿?¡!.,;:")
            return w.replace(nucleo, dic.get(nucleo, nucleo)) if nucleo else w
        s.spans = [(t0, t1, [(nombre(palabras[j]["w"]).rstrip(".,"), palabras[j]["s"], j in s.resaltar) for j in range(i0, i1)])
                   for t0, t1, i0, i1 in tramos_subtitulo(cfg, palabras)]

    @staticmethod
    def _auto(palabras, maximo=3):
        bloques, i0 = [], 0
        for j, p in enumerate(palabras):
            corte = j + 1 == len(palabras) or j + 1 - i0 >= maximo or p["w"][-1:] in ".,?!" \
                or palabras[j + 1]["s"] - p["e"] > .3
            if corte:
                bloques.append([i0, j + 1])
                i0 = j + 1
        return bloques

    def _hud(s, lienzo, t, ws):
        """Solo las palabras ya dichas, en mayúsculas blancas con sombra; la clave en acento y la última entra con un pop."""
        toks = [(w.upper(), ts, h) for w, ts, h in ws if t >= ts - .03]
        if not toks:
            return
        o = s.est.sub
        col_texto, col_clave = o["color"] or (255, 255, 255), o["clave"] or s.est.acento
        f = s.f_reg
        anchos = [f.getbbox(w)[2] - f.getbbox(w)[0] for w, _, _ in toks]
        tw = sum(anchos) + 22 * (len(toks) - 1)
        capa = Image.new("RGBA", (tw + 80, 160))
        d = ImageDraw.Draw(capa)
        x = 40
        for (w, ts, h), ww in zip(toks, anchos):
            b = f.getbbox(w)
            d.text((x - b[0], 80 - (b[1] + b[3]) / 2), w, font=f, fill=(col_clave if h else col_texto) + (255,))
            x += ww + 22
        nueva = ease_out((t - toks[-1][1]) / .12)
        _, dy, esc = subtitulo_opciones.entrada(o["efecto"] or "sube", nueva, 10)   # la palabra no parpadea: del efecto solo sube el movimiento y la escala
        x0, y0 = (W - capa.width) // 2, int(s.y - 80 + dy)
        if esc != 1.0:
            capa = capa.resize((max(1, int(capa.width * esc)), max(1, int(capa.height * esc))), Image.BILINEAR)
            x0, y0 = (W - capa.width) // 2, int(s.y - capa.height / 2 + dy)
        sombra = Image.new("RGBA", capa.size, (0, 0, 0, 0))
        sombra.putalpha(capa.getchannel("A").filter(ImageFilter.GaussianBlur(10)).point(lambda v: min(255, int(v * 1.6))))
        lienzo.alpha_composite(sombra, (x0 + 4, y0 + 6))
        if fondo_claro_o_rayado(lienzo, (x0, y0, x0 + capa.width, y0 + capa.height)):   # blanco sobre camiseta de rayas / manos: velo oscuro medido, no a ojo
            velo = Image.new("RGBA", capa.size, (0, 0, 0, 0))
            ImageDraw.Draw(velo).rounded_rectangle((20, 30, capa.width - 20, capa.height - 30), 30, fill=(0, 0, 0, SUBTITULO_VELO))
            lienzo.alpha_composite(velo.filter(ImageFilter.GaussianBlur(18)), (x0, y0))
        lienzo.alpha_composite(capa, (x0, y0))

    def _ajustar(s, ws, pad_x, sep):
        """Fuentes y anchos del bloque: si no cabe en la zona segura, se achica la letra (nunca se sale)."""
        f_reg, f_hi = s.f_reg, s.f_hi
        for k in range(8):
            anchos = [(f_hi if h else f_reg).getbbox(w)[2] - (f_hi if h else f_reg).getbbox(w)[0] for w, _, h in ws]
            tw = sum(anchos) + sep * (len(ws) - 1)
            if tw + 2 * pad_x <= config.ZONA_SEGURA[2] - config.ZONA_SEGURA[0]:
                break
            f_reg = s.est.sub_font(int(70 * (.9 ** (k + 1))), False, 700)
            f_hi = s.est.sub_font(int(74 * (.9 ** (k + 1))), True, 800)
        return f_reg, f_hi, anchos, tw

    def _capa_palabras(s, ws, t, f_reg, f_hi, anchos, pad_x, sep, h_c, col_texto, col_clave):
        capa = Image.new("RGBA", (sum(anchos) + sep * (len(ws) - 1) + 2 * pad_x, h_c))
        d = ImageDraw.Draw(capa)
        x = pad_x
        for (w, ts, h), ww in zip(ws, anchos):
            if t >= ts - .05:
                f = f_hi if h else f_reg
                b = f.getbbox(w)
                d.text((x - b[0], h_c / 2 - (b[1] + b[3]) / 2), w, font=f, fill=(col_clave if h else col_texto) + (255,))
            x += ww + sep
        return capa

    def _plano(s, lienzo, t, t0, ws, nativo):
        """Bloque SIN caja (sub_caja = no en tira o vidrio): palabras con sombra, la clave de otro color, y velo oscuro medido si el fondo es claro."""
        o = s.est.sub
        zx0, zy0, zx1, zy1 = config.ZONA_SEGURA
        pad_x, sep, h_c = 40, 20, 122
        f_reg, f_hi, anchos, _ = s._ajustar(ws, pad_x, sep)
        capa = s._capa_palabras(ws, t, f_reg, f_hi, anchos, pad_x, sep, h_c, o["color"] or (255, 255, 255), o["clave"] or s.est.acento)
        a, dy, esc = subtitulo_opciones.entrada(o["efecto"] or "sube", ease_out((t - t0) / .14), nativo)
        if esc != 1.0:
            capa = capa.resize((max(1, int(capa.width * esc)), max(1, int(capa.height * esc))), Image.BILINEAR)
        x0 = int(min(max((W - capa.width) // 2, zx0), zx1 - capa.width))
        y0 = int(min(max(s.y - capa.height / 2 + dy, zy0), zy1 - capa.height))   # el desplazamiento de la entrada va ANTES de ajustar a la zona segura
        sombra = Image.new("RGBA", capa.size)
        sombra.putalpha(capa.getchannel("A").filter(ImageFilter.GaussianBlur(10)).point(lambda v: min(255, int(v * 1.6 * a))))
        capa.putalpha(capa.getchannel("A").point(lambda v: int(v * a)))
        lienzo.alpha_composite(sombra, (x0 + 4, y0 + 6))
        caja = (x0, y0, x0 + capa.width, y0 + capa.height)
        v = ((0, 0, 0), SUBTITULO_VELO / 255 * a) if fondo_claro_o_rayado(lienzo, caja) else None
        if v:
            velo_suave(lienzo, caja, v[0], v[1])
        lienzo.alpha_composite(capa, (x0, y0))

    def _vidrio(s, lienzo, t, t0, ws):
        """Caja de vidrio esmerilado (la misma de `caja_vidrio`) del tamaño de todo el bloque, dentro de la zona segura; las palabras
        aparecen cuando se dicen (blancas con sombra, la clave en acento). Entra con fundido y 10 px de subida, sin brusquedad."""
        o = s.est.sub
        if o["caja"] is False:
            return s._plano(lienzo, t, t0, ws, 10)
        zx0, zy0, zx1, zy1 = config.ZONA_SEGURA
        pad_x, pad_y, sep = 40, 26, 20
        f_reg, f_hi, anchos, tw = s._ajustar(ws, pad_x, sep)
        w_c, h_c = tw + 2 * pad_x, 70 + 2 * pad_y
        a, dy, esc = subtitulo_opciones.entrada(o["efecto"] or "sube", ease_out((t - t0) / .14), 10)
        x0 = int(min(max((W - w_c) // 2, zx0), zx1 - w_c))
        y0 = int(min(max(s.y - h_c / 2 + dy, zy0), zy1 - h_c))   # el desplazamiento de la entrada va ANTES de ajustar a la zona segura
        wb, hb = max(1, int(w_c * esc)), max(1, int(h_c * esc))
        xb, yb = x0 + (w_c - wb) // 2, y0 + (h_c - hb) // 2
        claro = o["caja_color"] is None and fondo_claro_o_rayado(lienzo, (x0, y0, x0 + w_c, y0 + h_c))   # fondo claro o rayado: el velo pasa a oscuro y el texto sigue legible
        velo, opaco = (o["caja_color"], .32) if o["caja_color"] else ((0, 0, 0), .5) if claro else ((255, 255, 255), .22)
        s.caja = caja_vidrio(lienzo, xb, yb, wb, hb, 34, a, 22, velo, opaco)
        col_texto, col_clave = o["color"] or (255, 255, 255), o["clave"] or s.est.acento
        capa = s._capa_palabras(ws, t, f_reg, f_hi, anchos, pad_x, sep, h_c, col_texto, col_clave)
        if esc != 1.0:
            capa = capa.resize((wb, hb), Image.BILINEAR)
        sombra = Image.new("RGBA", capa.size)
        sombra.putalpha(capa.getchannel("A").filter(ImageFilter.GaussianBlur(6)).point(lambda v: min(255, int(v * 1.2))))
        capa.putalpha(capa.getchannel("A").point(lambda v: int(v * a)))
        sombra.putalpha(sombra.getchannel("A").point(lambda v: int(v * a)))
        lienzo.alpha_composite(sombra, (xb + 2, yb + 4))
        lienzo.alpha_composite(capa, (xb, yb))

    def dibujar(s, lienzo, t):
        for t0, t1, ws in s.spans:
            if not (t0 <= t < t1):
                continue
            if s.est.subtitulo == "vidrio":
                s._vidrio(lienzo, t, t0, ws)
                continue
            if s.est.subtitulo == "basico":
                subtitulo_basico.dibujar(lienzo, t, ws, s.est, s.f_reg)
                continue
            if s.est.subtitulo == "hud":
                s._hud(lienzo, t, ws)
                continue
            o = s.est.sub
            if o["caja"] is False:
                s._plano(lienzo, t, t0, ws, 14)
                continue
            p = ease_out((t - t0) / .14)
            a, dy, esc = subtitulo_opciones.entrada(o["efecto"] or "sube", p, 14)
            col_texto, col_caja, col_clave = o["color"] or s.est.tinta, o["caja_color"] or s.est.borde[:3], o["clave"] or s.est.acento
            toks = [(w, ts, h, s.f_hi if h else s.f_reg) for w, ts, h in ws]
            anchos = [f.getbbox(w)[2] - f.getbbox(w)[0] for w, _, _, f in toks]
            tw = sum(anchos) + 20 * (len(toks) - 1)
            tira = Image.new("RGBA", (tw + 64, 118))
            d = ImageDraw.Draw(tira)
            d.rectangle((0, 8, tw + 64, 110), fill=col_caja + (245,))
            x = 32
            for (w, ts, h, f), ww in zip(toks, anchos):
                dicha = t >= ts - .05
                if h and dicha:
                    d.rectangle((x - 8, 24, x + ww + 8, 98), fill=col_clave + (255,))
                b = f.getbbox(w)
                d.text((x - b[0], 61 - (b[1] + b[3]) / 2), w, font=f, fill=col_texto + ((255,) if dicha else (70,)))
                x += ww + 20
            tira = tira.rotate(-1.2, Image.BICUBIC, expand=True)
            sh = Image.new("RGBA", tira.size)
            sh.putalpha(tira.getchannel("A").point(lambda v: v * .45))
            sh = sh.filter(ImageFilter.GaussianBlur(8))
            tira.putalpha(tira.getchannel("A").point(lambda v: v * a))
            if esc != 1.0:
                tam = (max(1, int(tira.width * esc)), max(1, int(tira.height * esc)))
                tira, sh = tira.resize(tam, Image.BILINEAR), sh.resize(tam, Image.BILINEAR)
            x0, y0 = (W - tira.width) // 2, int(s.y - tira.height / 2 + dy)
            lienzo.alpha_composite(sh, (x0 + 6, y0 + 10))
            lienzo.alpha_composite(tira, (x0, y0))


ESTILOS_CAMARA_PROPIA = {"julian-alborna-3d"}   # excepción escrita (reglas.json, Pablo 08-nov «déjalo quieto»): sus pantallas completas no mueven la cámara del motor


CAPAS_CAMARA = ("ruta", "encuadre", "pantalla", "flotar", "zoom")   # todo lo que mueve el cuadro; con `camara.fija()` van todas apagadas


def capas_apagadas(sb):
    """Capas de cámara genéricas apagadas: las del storyboard (supervisor), las del estilo (`estilo.camara_apagar`) y, en los estilos con la
    excepción escrita (3D), «pantalla»: sus pantallas completas quedan quietas."""
    est = sb.get("estilo") or {}
    if camara.fija():
        return set(CAPAS_CAMARA)
    apagar = set(sb.get("camara_apagar") or ()) | set(est.get("camara_apagar") or ())
    if est.get("id") in ESTILOS_CAMARA_PROPIA:
        apagar.add("pantalla")
    return apagar


class CamaraProyecto:
    pantalla_quieta = False
    camara_fija = False   # la pone `iniciar_camara` desde la regla (`camara.fija()`)

    """Todo lo que decide la cámara de un cuadro, separado del dibujo: el render y el supervisor (`camara_check`) usan ESTE código,
    así lo que se mide es lo que se ve. Necesita `sb`, `escenas` y, para el reencuadre de la cara, `_transformar` (solo si hay cara)."""

    def cara_de(s, of):
        """Caja de la cara del cuadro de SALIDA `of` sin manos de paso (`caras_estables`); None si no hay persona."""
        if not getattr(s, "mapa", None) or getattr(s, "dir", None) is None:
            return None
        if getattr(s, "_caras", None) is None:
            s._caras = caras_estables(s.dir, s.mapa)
        return s._caras.get(s.mapa[of])

    @staticmethod
    def _transformar(pe, xs, ys):
        """Punto del video fuente → pantalla, según cómo se ubique a la persona en la escena."""
        sc, dx = pe.get("escala", 1.0), pe.get("x", 0)
        return (xs - W / 2) * sc + W / 2 + dx, H - H * sc + ys * sc

    def cajas_persona(s, i):
        """(cara, cuerpo) de la persona en el cuadro fuente i, en px (estudio/persona.py); (None, None) si no hay persona."""
        if getattr(s, "_tabla", None) is None:
            s._tabla = persona.Tabla(getattr(s, "dir", None))
        return s._tabla.cajas(i)

    def iniciar_camara(s, sb, palabras, n_src, mapa, nombre):
        s.escenas = sorted(sb["escenas"], key=lambda e: e["t0"])
        s.n_src, s.mapa = n_src, mapa
        apagar = capas_apagadas(sb)   # capas que el supervisor quitó o que el estilo apaga
        s.camara_fija = "ruta" in apagar   # regla de Pablo (11-nov): el cuadro no se mueve ni se recorta
        s.encuadres = [] if "encuadre" in apagar else encuadres(sb, palabras, n_src / FPS, nombre)
        s.mov_pantalla = movimientos_pantalla(nombre, s.escenas)
        s.pantalla_quieta = "pantalla" in apagar   # el estilo trae su cámara: la pantalla completa no se mueve ni se achica
        s.ruta = camara.Ruta(sb, len(mapa) / FPS, flotar=("flotar" not in apagar))   # UNA cámara que viaja por todo el video (Pablo, 04-nov)

    def escena(s, t):
        k = max([i for i, e in enumerate(s.escenas) if t >= e["t0"] - 1e-6] or [0])
        fin = s.escenas[k + 1]["t0"] if k + 1 < len(s.escenas) else s.n_src / FPS
        return s.escenas[k], s.escenas[k]["t0"], fin

    def _reencuadre_cara(s, dx, dy, cw, ch, pe, cara):
        """(dx, dy) del recorte dentro del cuadro: sin salirse de la imagen y con la cara siempre dentro, con holgura."""
        dx, dy = clamp(dx, -(W - cw) / 2, (W - cw) / 2), clamp(dy, -(H - ch) / 2, (H - ch) / 2)
        if cara is None:
            return dx, dy
        x0, y0 = s._transformar(pe, cara[0], cara[1])
        x1, y1 = s._transformar(pe, cara[2], cara[3])
        m = ENCUADRE_CARA_MARGEN_PX
        out = []
        for lo, hi, tam, total, d in ((x0, x1, cw, W, dx), (y0, y1, ch, H, dy)):
            v0 = (total - tam) / 2 + d          # borde de la vista en el cuadro
            sobra = tam - (hi - lo + 2 * m)      # holgura que queda con la cara y sus márgenes
            if sobra >= 0:                       # si la cara no cabe con holgura no se fuerza
                k = min(ENCUADRE_CARA_SUAVE_PX, sobra / 2)   # con k <= sobra/2 los dos lados nunca empujan a la vez
                d += -empuje_suave(v0 - (lo - m), k) + empuje_suave((hi + m) - (v0 + tam), k)
            out.append(d)
        return clamp(out[0], -(W - cw) / 2, (W - cw) / 2), clamp(out[1], -(H - ch) / 2, (H - ch) / 2)

    def _cuadro_salida(s, t_src):
        """Primer cuadro de SALIDA cuyo cuadro fuente es >= t_src (segundos de la fuente): el tiempo de salida real, ya con los cortes en cuadros enteros."""
        mapa = getattr(s, "mapa", None)
        if not mapa:   # sin mapa de cuadros (pruebas sueltas): el tiempo continuo de siempre
            return camara.salida(s.sb, t_src) * FPS
        return bisect.bisect_left(mapa, round(t_src * FPS))

    def mov_de(s, esc):
        """Movimiento (zA, zB, xA, xB, yA, yB) de la escena oculta según su tipo y su `camara_mov`."""
        return movimiento_pantalla(s.mov_pantalla[esc["t0"]], esc.get("camara_mov", "suave"))

    def camara_cuadro(s, of, t, esc, s0, s1, cara=None, pe=None):
        """UNA sola fuente de verdad de la cámara de un cuadro de pantalla (la usan el render y el supervisor `camara_check`).
        Devuelve la vista final {cw, ch, dx, dy, rot, gira} y las capas que se SUMAN en ella: ruta (viaje global, con su flotación),
        encuadre (reencuadre de la persona) o pantalla (el A→B de una pantalla completa, que no suma nada más)."""
        if s.camara_fija:
            return {"cw": W, "ch": H, "dx": 0, "dy": 0, "rot": 0, "gira": False, "capas": {}}
        oculta = (esc.get("persona") or {}).get("modo") == "oculta"
        pe = pe if pe is not None else esc.get("persona", {})
        capas = {}
        if oculta:   # UN solo movimiento A→B de s0 a s1, acelera y desacelera; sin ruta global, ruido, seguimiento ni golpes
            zA, zB, xA, xB, yA, yB = (1.0, 1.0, 0, 0, 0, 0) if s.pantalla_quieta else s.mov_de(esc)
            # el avance se mide en tiempo de SALIDA: un corte real dentro de la escena no se lleva un pedazo del movimiento (brinco)
            # …y en CUADROS de salida: `camara.salida` resta la duración exacta del corte (p. ej. 0,030 s) pero el render quita cuadros
            # enteros (1/30 s); con esa mezcla el avance daba un tirón de ~10 % al pasar el corte (sacudida de 4,6 px, muestra Swiss 21,6 s)
            a_, b_ = s._cuadro_salida(s0) / FPS, s._cuadro_salida(s1) / FPS
            f_ = progreso_pantalla((s._cuadro_salida(t) / FPS - a_) / max(b_ - a_, 1e-6), esc.get("camara_mov", "suave"))
            z, cam_dx, cam_dy, cam_rot = zA + (zB - zA) * f_, xA + (xB - xA) * f_, yA + (yB - yA) * f_, 0.0
            if not s.pantalla_quieta:
                capas["pantalla"] = (z, cam_dx, cam_dy, 0.0)
        else:
            # cámara continua en tiempo de salida: no se reinicia por escena ni por corte (estudio/camara.py)
            z, cam_dx, cam_dy, cam_rot = s.ruta(of / FPS)
            capas["ruta"] = (z, cam_dx, cam_dy, cam_rot)
        enc_dx = 0.0
        if not oculta:   # reencuadre: UN movimiento fluido A→B entre cambios de plano (zoom y leve viaje lateral)
            ze, enc_dx = encuadre_en(s.encuadres, t)
            z *= ze
            capas["encuadre"] = (ze, enc_dx, 0.0, 0.0)
        cw, ch = W / z, H / z
        gira = bool(cam_dx or cam_dy or cam_rot)
        if gira:   # el viaje y la flotación ya vienen en la ruta
            dx, dy, rot = cam_dx, cam_dy, cam_rot
            if oculta:   # zoom propio del movimiento: solo se recorta el desplazamiento para no salirse del cuadro
                dx, dy = clamp(dx, -(W - cw) / 2, (W - cw) / 2), clamp(dy, -(H - ch) / 2, (H - ch) / 2)
            else:
                desp = abs(dx) + abs(dy) + abs(cam_rot) * 50
                m = 1 + (abs(dx) + abs(dy)) * 2 / W + .02 * min(1.0, desp / 2)   # el margen entra gradual: con dx=0 apenas pasa a >0 no hay salto de zoom (Pop, 1.er cuadro)
                cw, ch = cw / m, ch / m
                dx, dy = s._reencuadre_cara(dx + enc_dx, dy, cw, ch, pe, cara)
        else:
            dx = dy = rot = 0
            if not oculta:
                dx, dy = s._reencuadre_cara(enc_dx, 0, cw, ch, pe, cara)
        return {"cw": cw, "ch": ch, "dx": dx, "dy": dy, "rot": rot, "gira": gira, "capas": capas}



def mapa_de(sb: dict, n_src: int) -> list:
    """Cuadro de salida → cuadro fuente: todos los de la fuente menos los de los cortes del storyboard."""
    quitar = set()
    for a, b in sb.get("cortes", []):
        quitar.update(range(round(a * FPS), round(b * FPS)))
    return [i for i in range(n_src) if i not in quitar]


class Proyecto(CamaraProyecto):
    """Carga todo lo que el render necesita de una carpeta de proyecto."""

    def __init__(s, carpeta: Path, sb: dict | None = None, solo_en=None):
        """`solo_en` (cuadros de salida): para vistas previas, solo se arman los elementos que se ven en esos cuadros (más los que un
        trazo señala) y el que no tiene su imagen todavía se omite (`omitidos`) en vez de tumbar toda la vista. Sin `solo_en`, el
        proyecto completo y un arte que falta sigue siendo error."""
        s.dir = Path(carpeta)
        s.sb = sb or json.loads((s.dir / "storyboard.json").read_text())
        s.meta = json.loads((s.dir / "fuente.json").read_text())
        s.palabras = json.loads((s.dir / "palabras.json").read_text())
        s.est = Estilo(s.sb.get("estilo", {}))
        s.cubo = color.cubo(s.dir, s.sb.get("estilo", {}).get("color"))
        s.n_src = s.meta["cuadros"]
        s.mapa = mapa_de(s.sb, s.n_src)  # cuadro de salida → cuadro fuente
        s.omitidos = []
        dibujos = s.sb.get("elementos", [])
        if solo_en is not None:
            s._caras = caras_estables(s.dir, s.mapa, cerca={s.mapa[min(len(s.mapa) - 1, of)] for of in solo_en})
            vistos = [s.mapa[min(len(s.mapa) - 1, of)] / FPS for of in solo_en]
            señalados = {d.get("sobre") for d in s.sb.get("trazos", [])}
            dibujos = [d for d in dibujos if d.get("id") in señalados or any(d["t0"] <= t < d["t1"] for t in vistos)]
        s.elementos = []
        for d in dibujos:
            try:
                s.elementos.append(Elemento(d, s.est, s.dir))
            except FileNotFoundError:
                if solo_en is None:
                    raise
                s.omitidos.append(d)
        from . import validar
        for e in s.elementos:   # lo que la cámara se come en cada borde mientras el texto está en pantalla: el margen lateral se mide sobre lo que SE VE
            if e.d["tipo"] in ("texto", "etiqueta"):
                e.margen_cam = validar._margen_camara(s.sb, e.t0, e.t1)[0]
        sin = {d.get("id") for d in s.omitidos}
        s.trazos = trazos_de({**s.sb, "trazos": [t for t in s.sb.get("trazos", []) if t.get("sobre") not in sin]} if sin else s.sb, s.elementos)
        s.subs = Subtitulos(s.sb, s.palabras, s.est)
        s.cajas = s.sb.get("cajas", [])
        rng = np.random.default_rng(1)
        s.grano = [rng.normal(0, .1, (H // 2, W // 2)).astype(np.float32) for _ in range(8)]
        s.iniciar_camara(s.sb, s.palabras, s.n_src, s.mapa, str(s.dir.name))

    # ---------- base «pantalla»: el video a pantalla completa con filtros, capas HUD y textos ----------
    def _caja(s, c, d, t, pe, cajas):
        p = ease_out((t - d["t0"]) / d.get("dur", .3))
        if isinstance(d.get("sobre"), list):
            x0, y0, x1, y1 = d["sobre"]
        else:
            fuente = cajas[1] if d.get("sobre") == "cuerpo" else cajas[0]
            if fuente is None:
                return
            x0, y0 = s._transformar(pe, fuente[0], fuente[1])
            x1, y1 = s._transformar(pe, fuente[2], fuente[3])
            m = d.get("margen", 30)
            x0, y0, x1, y1 = x0 - m, y0 - m, x1 + m, y1 + m
        cx, cy, k = (x0 + x1) / 2, (y0 + y1) / 2, 1 + .3 * (1 - p)
        x0, x1 = cx + (x0 - cx) * k, cx + (x1 - cx) * k
        y0, y1 = cy + (y0 - cy) * k, cy + (y1 - cy) * k
        col = s.est.color(d.get("color", "acento2"))
        capa = Image.new("RGBA", (W, H))
        dr = ImageDraw.Draw(capa)
        op = int(255 * clamp(p * 1.5))
        dr.rectangle((x0, y0, x1, y1), outline=col + (int(op * .35),), width=2)
        L = min(46, (x1 - x0) / 4, (y1 - y0) / 4)
        for ex, ey, sx, sy in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)):
            dr.line([(ex, ey + sy * L), (ex, ey), (ex + sx * L, ey)], fill=col + (op,), width=5)
        mono = s.est.font_rol("mono", HUD_MONO_TAM)
        if d.get("etiqueta"):
            txt = d["etiqueta"].upper()
            b = mono.getbbox(txt)
            dr.rectangle((x0, y0 - b[3] - 18, x0 + b[2] + 20, y0 - 4), fill=col + (op,))
            dr.text((x0 + 10, y0 - b[3] - 11), txt, font=mono, fill=(8, 8, 10, op))
        for i, linea in enumerate(d.get("datos", [])):
            dr.text((x1 + 14, y0 + 6 + i * round(HUD_MONO_TAM * 1.3)), linea, font=mono, fill=col + (op,))
        c.alpha_composite(capa)

    def _franjas(s, rgb, franjas, caja):
        """La misma toma partida en N franjas verticales, cada una con su filtro y su rótulo."""
        n = len(franjas)
        ancho = W // n
        centro = (caja[0] + caja[2]) // 2 if caja else W // 2
        x0 = int(clamp(centro - ancho / 2, 0, W - ancho))
        out = Image.new("RGBA", (W, H), (8, 8, 10, 255))
        for i, fr in enumerate(franjas):
            tira = efectos.filtrar(rgb[:, x0:x0 + ancho], fr.get("filtro", "ninguno"), s.est)
            out.paste(Image.fromarray(tira), (i * ancho, 0))
            txt = fr.get("etiqueta", "").upper()
            tam = 60
            while tam > FRANJA_TAM_MIN and s.est.font_rol("display", tam).getbbox(txt)[2] > ancho - 30:
                tam -= 4
            f = s.est.font_rol("display", tam)
            b = f.getbbox(txt)
            ImageDraw.Draw(out).text((i * ancho + (ancho - b[2]) / 2, 300), txt, font=f, fill=s.est.acento + (255,))
        dr = ImageDraw.Draw(out)
        for i in range(1, n):
            dr.line([(i * ancho, 0), (i * ancho, H)], fill=(8, 8, 10, 255), width=6)
        return out

    def _capa_frente(s, t, pe, cajas, parte="todo"):
        """Lo que se dibuja delante en una pantalla completa (elementos, trazos y cajas que no son fondo), en una capa transparente.
        `parte`: «fondo» = solo los elementos que cubren gran parte del cuadro; «contenido» = todo lo demás; «todo» = ambos."""
        capa = Image.new("RGBA", (W, H))
        for e in s.elementos:
            if e.z != "atras" and (parte == "todo" or (parte == "fondo") == e.es_fondo):
                e.dibujar(capa, t)
        if parte == "fondo":
            return capa
        for tr in s.trazos:
            if tr.z != "atras":
                tr.dibujar(capa, t, s.est)
        for d in s.cajas:
            if d["t0"] <= t < d["t1"]:
                s._caja(capa, d, t, pe, cajas)
        return capa

    def ajuste_oculta(s, esc, s0, s1, pe, cajas):
        """(escala, tx, ty) de la escena oculta, medido una vez: caja de lo dibujado en varios cuadros de la escena."""
        cache = s.__dict__.setdefault("_ajuste_oculta", {})
        if esc["t0"] not in cache:
            caja = None
            for i in range(PANTALLA_MUESTRAS):
                m = np.asarray(s._capa_frente(s0 + (s1 - s0) * (i + .5) / PANTALLA_MUESTRAS, pe, cajas, "contenido").getchannel("A")) >= PANTALLA_ALFA_MIN
                ys, xs = np.where(m)
                if len(xs):
                    b = (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)
                    caja = b if caja is None else (min(caja[0], b[0]), min(caja[1], b[1]), max(caja[2], b[2]), max(caja[3], b[3]))
            cache[esc["t0"]] = ajuste_pantalla(s.mov_de(esc), caja)
        return cache[esc["t0"]]

    def cuadro_pantalla(s, of, rgb, t, esc, s0, s1):
        pe = esc.get("persona", {})
        modo = pe.get("modo", "completa")
        filtro = esc.get("filtro", s.sb.get("estilo", {}).get("filtro", "ninguno"))
        cajas = s.cajas_persona(s.mapa[of])
        filtrada = efectos.filtrar(rgb, filtro, s.est)
        if esc.get("franjas"):
            c = s._franjas(rgb, esc["franjas"], cajas[1])
        elif modo == "completa":
            c = Image.fromarray(filtrada).convert("RGBA")
        elif pe.get("fondo") in efectos.MUROS:   # el fondo VIVE: deriva y respira despacio (Pablo: «mover el fondo, el apoyo y la fuente a la vez»)
            base_m = efectos.muro(pe["fondo"], s.est)
            zm = 1.08 + .03 * camara.ruido(t, "mz", 5.0)
            mx, my = 30 * camara.ruido(t, "mx", 4.6), 40 * camara.ruido(t, "my", 5.3)
            cw_, ch_ = W / zm, H / zm
            c = recorte_fino(base_m, (W - cw_) / 2 + mx, (H - ch_) / 2 + my, (W + cw_) / 2 + mx, (H + ch_) / 2 + my)
        else:
            c = Image.new("RGBA", (W, H), s.est.color(pe.get("fondo", "negro")) + (255,))
        atras = [e for e in s.elementos if e.z == "atras" and e.t0 <= t < e.t1]
        for e in atras:
            e.dibujar(c, t)
        for tr in s.trazos:
            if tr.z == "atras":
                tr.dibujar(c, t, s.est)
        oculta = pe.get("modo") == "oculta"
        if oculta:   # el contenido se achica hacia el centro lo justo para caber en lo que la cámara deja ver en el peor momento
            k_, tx, ty = (1.0, 0.0, 0.0) if s.pantalla_quieta else s.ajuste_oculta(esc, s0, s1, pe, cajas)
            c.alpha_composite(s._capa_frente(t, pe, cajas, "fondo"))   # hojas y fondos grandes: sin escalar, viajan con la cámara
            capa = s._capa_frente(t, pe, cajas, "contenido")
            if k_ < 1.0 or tx or ty:
                capa = capa.resize((max(1, round(W * k_)), max(1, round(H * k_))), Image.LANCZOS)
                lienzo = Image.new("RGBA", (W, H))
                lienzo.alpha_composite(capa, (round((W - capa.width) / 2 + tx), round((H - capa.height) / 2 + ty)))
                capa = lienzo
            c.alpha_composite(capa)
        else:
            for e in s.elementos:
                if e.z != "atras":
                    e.dibujar(c, t)
            for tr in s.trazos:
                if tr.z != "atras":
                    tr.dibujar(c, t, s.est)
            for d in s.cajas:
                if d["t0"] <= t < d["t1"]:
                    s._caja(c, d, t, pe, cajas)
        cam = s.camara_cuadro(of, t, esc, s0, s1, s.cara_de(of), pe)
        desenfoque = 0.0
        if s.est.transicion == "desenfoque":      # rack focus: el plano sale desenfocándose y empujando; el siguiente entra y enfoca
            sal, ent = s1 - t, t - s0
            if 0 <= sal < .2 and s1 < s.n_src / FPS - .05:   # sin empujón de zoom: daba un brinco (Pablo, luminoso seg 18)
                desenfoque = 22 * (1 - sal / .2)
            if ent < .25 and s0 > 0:
                desenfoque = max(desenfoque, 22 * (1 - ent / .25))
        if not s0 and t < .4 and s.est.transicion == "desenfoque":   # el gancho entra desde desenfoque total
            desenfoque = max(desenfoque, 30 * (1 - t / .4))
        cw, ch, dx, dy, rot = cam["cw"], cam["ch"], cam["dx"], cam["dy"], cam["rot"]
        if cam["gira"]:
            c = c.rotate(rot, Image.BILINEAR, center=(W / 2 + dx, H / 2 + dy))
        c = recorte_fino(c, (W - cw) / 2 + dx, (H - ch) / 2 + dy, (W + cw) / 2 + dx, (H + ch) / 2 + dy)
        if desenfoque > .5:
            c = c.filter(ImageFilter.GaussianBlur(desenfoque))
        s.subs.dibujar(c, t)
        arr = np.asarray(c.convert("RGB"))
        if s.est.bloom:
            arr = efectos.bloom(arr, s.est.bloom)
        if s.est.crt:
            arr = efectos.crt(arr, s.est.crt)
        entrada, dt = esc.get("entrada", "corte"), t - s0
        if entrada == "rafaga" and dt < .25:
            arr = efectos.rafaga(arr, dt / .25, of)
        elif entrada == "flash" and dt < .1:
            arr = np.clip(arr.astype(np.float32) + 200 * (1 - dt / .1), 0, 255).astype(np.uint8)
        elif entrada == "zoom" and dt < efectos.ZOOM_ENTRADA_DUR:
            arr = efectos.zoom_radial(arr, dt / efectos.ZOOM_ENTRADA_DUR)
        elif entrada == "pixel" and dt < .16:
            arr = efectos.pixelar(arr, dt / .16)
        elif entrada == "iris" and dt < .4:   # viñeta oval que se abre desde el centro (transición orgánica de vox)
            k = ease_out(dt / .4)
            yy, xx = np.ogrid[0:H, 0:W]
            r = np.sqrt(((xx - W / 2) / (W * .75)) ** 2 + ((yy - H / 2) / (H * .62)) ** 2)
            m = np.clip((k * 1.25 - r) / .12, 0, 1)[..., None]
            arr = (arr.astype(np.float32) * m + np.array(s.est.tinta, np.float32) * (1 - m)).astype(np.uint8)
        elif entrada == "desenfoque" and dt < .25:   # rack focus solo en esta escena
            arr = np.asarray(Image.fromarray(arr).filter(ImageFilter.GaussianBlur(22 * (1 - dt / .25))))
        elif entrada == "wipe" and dt < .2:   # un campo del color de acento cubre el cuadro a saltos y se retira
            pasos = [.5, .55, .7, 1.0, .7, .3]
            k = pasos[min(len(pasos) - 1, int(dt * FPS))]
            ancho = int(W * k)
            arr = arr.copy()
            arr[:, :ancho] = s.est.acento
        elif entrada == "bloques" and dt < .22:
            arr = efectos.bloques(arr, dt / .22, s.est.acento, int(s0 * 100))
        elif entrada == "invertir" and dt < 2.5 / FPS:
            arr = efectos.invertir(arr)
        if s.est.aberracion_corte and dt < 2 / FPS and s0 > 0:   # pico de aberración en el cuadro del corte
            arr = efectos.aberracion(arr, s.est.aberracion_corte)
        g = np.asarray(Image.fromarray(s.grano[of % 8]).resize((W, H), Image.BILINEAR), np.float32)
        return np.clip(arr.astype(np.float32) + g[..., None] * s.est.grano, 0, 255).astype(np.uint8)

    def cuadro(s, of, rgb):
        """Un cuadro de salida. La persona va SIEMPRE en su toma completa (regla `sujeto_recortado_prohibido`): no hay recorte."""
        t = s.mapa[of] / FPS
        esc, s0, s1 = s.escena(t)
        return s.cuadro_pantalla(of, rgb, t, esc, s0, s1)


def _filtro(p: Proyecto):
    """HDR del iPhone → Rec.709 y, si hay color elegido, su LUT en 16 bits (sin tocar el color de la toma).
    La LUT se nombra relativa: ffmpeg corre con cwd = carpeta del proyecto (las rutas de Windows llevan «:»)."""
    vf = "scale=in_color_matrix=bt2020:out_color_matrix=bt709," if p.meta.get("hdr") else ""
    cubo = getattr(p, "cubo", None)
    if cubo:
        vf += f"{color.filtro(cubo)},"
    return vf + "format=rgb24"


def _un_cuadro(p: Proyecto, i: int):
    """Un solo cuadro fuente, saltando directo a él (para vistas previas rápidas); queda en caché por proyecto."""
    cubo = getattr(p, "cubo", None)
    cache = Path(getattr(p, "dir", config.CACHE)) / ".cuadros" / f"{i:05d}{'-' + cubo.stem if cubo else ''}.npy"
    if cache.exists():
        return np.load(cache)
    ffmpeg, _ = config.ffmpeg()
    b = subprocess.run([ffmpeg, "-v", "error", "-ss", f"{i / FPS:.4f}", "-i", p.meta["video"], "-frames:v", "1",
                        "-vf", _filtro(p), "-f", "rawvideo", "-"], capture_output=True, check=True,
                       cwd=getattr(p, "dir", None)).stdout
    rgb = np.frombuffer(b[:W * H * 3], np.uint8).reshape(H, W, 3)
    if hasattr(p, "dir"):
        cache.parent.mkdir(exist_ok=True)
        np.save(cache, rgb)
    return rgb


def recorrer(p: Proyecto, solo=None):
    """Genera (cuadro_salida, rgb_salida). Con `solo` (cuadros de salida) salta directo a cada uno."""
    if solo is not None:
        for of in sorted(solo):
            i = p.mapa[of]
            yield of, p.cuadro(of, _un_cuadro(p, i))
        return
    ffmpeg, _ = config.ffmpeg()
    dec = subprocess.Popen([ffmpeg, "-v", "error", "-i", p.meta["video"], "-vf", _filtro(p), "-f", "rawvideo", "-"],
                           stdout=subprocess.PIPE, cwd=p.dir)
    inv = {src: of for of, src in enumerate(p.mapa)}
    try:
        for i in range(p.n_src):
            b = dec.stdout.read(W * H * 3)
            if len(b) < W * H * 3:
                break
            of = inv.get(i)
            if of is not None:
                yield of, p.cuadro(of, np.frombuffer(b, np.uint8).reshape(H, W, 3))
    finally:
        dec.kill()


def precargar(p: Proyecto, cuadros_salida) -> None:
    """Decodifica los cuadros fuente de esos cuadros de salida; quedan en la caché de `_un_cuadro`."""
    for of in cuadros_salida:
        _un_cuadro(p, p.mapa[of])


def hoja(cuadros, salida, ancho=270, cols=6):
    """Hoja de contacto: [(etiqueta, rgb)] → jpg con la etiqueta (tiempo) en cada cuadro."""
    alto = ancho * H // W
    filas = math.ceil(len(cuadros) / cols)
    out = Image.new("RGB", (ancho * min(cols, len(cuadros)), alto * filas), "white")
    f = ImageFont.truetype(str(config.FUENTES / "PlayfairDisplay-VariableFont_wght.ttf"), 22)
    for k, (txt, rgb) in enumerate(cuadros):
        im = Image.fromarray(rgb).resize((ancho, alto))
        d = ImageDraw.Draw(im)
        d.rectangle((0, 0, 96, 30), fill="black")
        d.text((6, 2), txt, font=f, fill="white")
        out.paste(im, ((k % cols) * ancho, (k // cols) * alto))
    out.save(salida, quality=85)
    return salida


def vista_previa(carpeta, tiempos_fuente, salida, ancho=270):
    """Hoja de contacto del video editado en esos tiempos (segundos FUENTE, como el storyboard)."""
    from bisect import bisect_left
    p = Proyecto(carpeta)
    pedidos = {min(len(p.mapa) - 1, bisect_left(p.mapa, round(t * FPS))): t for t in tiempos_fuente}
    cuadros = [(f"{pedidos[of]:.2f}s", rgb) for of, rgb in recorrer(p, set(pedidos))]
    return hoja(cuadros, salida, ancho)


# El final sale en BT.709 DICHO en el archivo. Antes salía sin marcas y convertido con la matriz por defecto de ffmpeg (BT.601): cada
# reproductor adivinaba, y los que suponen BT.709 en HD (QuickTime, Instagram) mostraban la piel y los rojos corridos frente a la
# toma (Pablo, 11-nov: «en original no sale original… hay un procesamiento raro»).
# Las marcas van en el filtro (`setparams`): viajan con los cuadros. Como opción de salida ffmpeg 8 solo respeta la matriz y deja
# primarios y curva en «desconocido» (visto en el primer final del 11-nov).
COLOR_SALIDA = ("scale=out_color_matrix=bt709:out_range=tv,format=yuv420p,"
                "setparams=colorspace=bt709:color_primaries=bt709:color_trc=bt709:range=tv")
MARCAS_COLOR = ("-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv")


def _codificador(destino: Path):
    ffmpeg, _ = config.ffmpeg()
    return subprocess.Popen([ffmpeg, "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                             "-i", "-", "-vf", COLOR_SALIDA, "-c:v", "libx264", "-preset", "medium", "-crf", "17",
                             *MARCAS_COLOR, str(destino)],
                            stdin=subprocess.PIPE)


def _trozo(args):
    """Cuadros de salida [a, b) → su propio mp4. Corre en otro proceso: decodifica desde su punto, no desde el inicio."""
    carpeta, a, b, destino = args
    p = Proyecto(carpeta)
    ffmpeg, _ = config.ffmpeg()
    i0, i1 = p.mapa[a], p.mapa[b - 1]
    dec = subprocess.Popen([ffmpeg, "-v", "error", "-ss", f"{i0 / FPS:.4f}", "-i", p.meta["video"], "-vf", _filtro(p),
                            "-frames:v", str(i1 - i0 + 1), "-f", "rawvideo", "-"], stdout=subprocess.PIPE, cwd=p.dir)
    inv = {src: of for of, src in enumerate(p.mapa)}
    enc = _codificador(destino)
    escritos = 0
    try:
        for i in range(i0, i1 + 1):
            buf = dec.stdout.read(W * H * 3)
            if len(buf) < W * H * 3:
                break
            of = inv.get(i)
            if of is not None:
                enc.stdin.write(p.cuadro(of, np.frombuffer(buf, np.uint8).reshape(H, W, 3)).tobytes())
                escritos += 1
    finally:
        dec.kill()
        enc.stdin.close()
        enc.wait()
    if escritos != b - a:   # el decodificador se cortó (p. ej. sin memoria con el PC cargado): nunca un tramo corto en silencio
        Path(destino).unlink(missing_ok=True)
        raise RuntimeError(f"tramo {a}–{b}: salieron {escritos} de {b - a} cuadros")
    return b - a


def _trozo_seguro(args):
    """`_trozo` para el pool: devuelve (cuadros, None) o (0, error) en vez de tumbar todo el render."""
    try:
        return _trozo(args), None
    except Exception as e:   # noqa: BLE001 — el error vuelve al proceso principal, que repite el tramo de a uno
        return 0, str(e)


def _cuadros(video) -> int:
    """Cuadros de un video contando paquetes (rápido, sin decodificar)."""
    _, ffprobe = config.ffmpeg()
    r = subprocess.run([ffprobe, "-v", "error", "-select_streams", "v:0", "-count_packets", "-show_entries", "stream=nb_read_packets",
                        "-of", "csv=p=0", str(video)], capture_output=True, text=True)
    try:
        return int(r.stdout.strip().split(",")[0])
    except ValueError:
        return -1


def procesos() -> int:
    """Cuántos tramos a la vez: ~un proceso por núcleo físico (ESTUDIO_PROCESOS lo fija)."""
    import os
    return int(os.environ.get("ESTUDIO_PROCESOS") or max(1, min(8, (os.cpu_count() or 2) // 2)))


def render(carpeta, salida=None, avance=print, forzar=False):
    """Render por tramos en paralelo (mismo resultado cuadro a cuadro que en serie) y luego la mezcla de sonido.
    Antes, la compuerta completa (montaje, color, textos…): si falla, NO se renderiza (nadie se la salta, ni a mano)."""
    import multiprocessing as mp
    if (Path(carpeta) / "fuente.json").exists() and config.CARAS_ONNX.exists():
        persona.ubicar(Path(carpeta), avance)   # un proyecto anterior al 11-nov (con máscaras y sin `persona.json`) se pone al día aquí, en segundos
    if not forzar:
        from . import archivo, validar
        archivo.quitar_personas(carpeta, avance)   # fotos con personas (de biblioteca o ya en arte/) nunca llegan al render
        sb = json.loads((Path(carpeta) / "storyboard.json").read_text())
        problemas = [e for e in validar.errores(sb, Path(carpeta)) if not e.startswith("huella")]
        from . import machote, montaje
        mj = machote.cargar(Path(carpeta))
        if mj and machote.tolera_montaje(Path(carpeta)):     # lo medible del montaje que ya tenía el corte APROBADO no vuelve a bloquear aquí
            import re
            # mismo error = mismo texto con los segundos redondeados a 0,1 s (el director re-repara y corre bordes por centésimas)
            sin_cifras = lambda e: re.sub(r"\d+\.\d+", lambda m: f"{float(m.group()):.1f}", e)  # noqa: E731
            vistos = {sin_cifras(e) for e in montaje.errores({"cortes": mj["cortes"]}, Path(carpeta))}
            problemas = [e for e in problemas if sin_cifras(e) not in vistos]
        if problemas:
            raise ValueError("la compuerta no deja renderizar:\n- " + "\n- ".join(problemas))
        from . import camara_check
        camara_check.supervisar(carpeta, avance)   # saltos, sacudidas y movimientos superpuestos de la cámara efectiva (arregla o no renderiza)
    from . import tramos as memoria
    p = Proyecto(Path(carpeta).resolve())
    if p.mapa:   # la caja estable de la cara se calcula una vez aquí, antes de repartir el render entre procesos
        p.cara_de(0)
    ffmpeg, _ = config.ffmpeg()
    mudo = p.dir / "video_mudo.mp4"
    n, k = len(p.mapa), procesos()
    tmp = p.dir / ".tramos"
    tmp.mkdir(exist_ok=True)
    # tramos fijos con memoria (estudio/tramos.py): una corrección solo vuelve a exportar los que cambiaron
    plan = memoria.claves(p)
    sirven = memoria.reusables(p, plan, _filtro(p), avance)
    trabajos = [(str(p.dir), a, b, tmp / f"{c}.mp4") for a, b, c in plan if c not in sirven]
    nuevos = sum(t[2] - t[1] for t in trabajos)
    avance(f"render: {nuevos} de {n} cuadros por exportar ({len(trabajos)} de {len(plan)} tramos; el resto no cambió), {k} a la vez")
    hechos, fallidos = 0, []
    if trabajos:
        with mp.get_context("spawn").Pool(min(k, len(trabajos))) as pool:
            for t, (m, err) in zip(trabajos, pool.imap(_trozo_seguro, trabajos)):
                if err:
                    fallidos.append(t)
                    avance(f"render: {err}; se repite solo")
                    continue
                hechos += m
                avance(f"render {hechos}/{nuevos}")
    for t in fallidos:   # de a uno, sin competir por memoria; si vuelve a fallar, no hay final roto: error claro
        hechos += _trozo(t)
        avance(f"render {hechos}/{nuevos}")
    lista = tmp / "lista.txt"
    lista.write_text("".join(f"file '{c}.mp4'\n" for _, _, c in plan))
    subprocess.run([ffmpeg, "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lista.name, "-c", "copy", str(mudo)],
                   check=True, cwd=tmp)
    total = _cuadros(mudo)
    if total != n:
        raise RuntimeError(f"render: el video salió con {total} cuadros y debían ser {n}; no se entrega un final cortado")
    memoria.limpiar(p, plan)   # quita solo los tramos que ya no pertenecen al plan
    salida = Path(salida or p.dir / "final.mp4")
    try:
        sonido.mezclar(p, mudo, salida, volumen_sfx=float(p.sb.get("estilo", {}).get("sfx", config.SFX_VOLUMEN)))
    finally:
        limpiar_render(p.dir)
    return salida


def limpiar_render(carpeta) -> None:
    """Un render deja en el proyecto solo lo que sirve: `final.mp4` y la memoria de tramos (`.tramos/`), que sí se reusa
    para que una corrección vuelva a exportar solo los tramos que cambiaron (estudio/tramos.py). El video sin sonido no
    se reusa y se quita; los tramos que ya no pertenecen al plan los quita `memoria.limpiar`."""
    carpeta = Path(carpeta)
    (carpeta / "video_mudo.mp4").unlink(missing_ok=True)
