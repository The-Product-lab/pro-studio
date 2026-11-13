"""Estilo «básico» (Pablo, 08-nov): SOLO subtítulo palabra por palabra, sobre la toma con su color. Referente DcT81r7Otdh.

Todo es determinista desde palabras.json (sin director, sin Opus): `armar` escribe el storyboard y `dibujar` pinta el subtítulo.
Opciones (claves de `estilo`, se cambian por `preferencias.json` como el resto): sub_color (texto), sub_clave (palabras clave),
sub_caja (sí/no), sub_caja_color, sub_efecto (corte | pop | sube). Los números van aquí, en un solo lugar."""
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from . import subtitulo_opciones
from .subtitulo_opciones import EFECTOS  # (una sola definición para todos los tipos)

TAM = 60                 # cuerpo de la letra. Pablo, 11-nov: «únicamente subtítulos, abajito, chiquitos y ya» (antes 92)
Y = 1410                 # centro del bloque: lo más abajo que cabe en la zona segura de Instagram (230–1500) con dos líneas y su caja
ANCHO_MAX = 860          # ancho máximo de una línea (cuadro 1080)
PALABRAS_BLOQUE = 3      # palabras por bloque (el referente: 1–3 por línea)
PAUSA_BLOQUE = .3        # una pausa mayor corta el bloque
INTERLINEA = 1.12
DUR_ENTRADA = {"pop": .16, "sube": .14}
CAJA_PAD = (30, 14)      # px de aire dentro de la caja de color (x, y)
CAJA_RADIO = 26
SOMBRA = (8, 6, 140)     # blur, desplazamiento y, opacidad 0–255 (el referente: blur 6–8, 30–40 %)
VACIAS = {"que", "con", "los", "las", "del", "una", "uno", "por", "para", "como", "este", "esta", "esto", "eso", "pero", "más", "mas",
          "muy", "tus", "sus", "mis", "les", "nos", "hay", "son", "fue", "era", "the", "and", "you", "when", "cuando", "porque", "donde"}


def _limpia(w: str) -> str:
    return w.strip("¿?¡!.,;:()\"'").lower()


def claves(palabras: list, bloques: list) -> list:
    """Índices de las palabras clave: la más larga con contenido de cada bloque (mín. 5 letras), y nunca en bloques seguidos."""
    out, ultimo = [], -9
    for n, (i0, i1) in enumerate(bloques):
        cand = [j for j in range(i0, i1) if len(_limpia(palabras[j]["w"])) >= 5 and _limpia(palabras[j]["w"]) not in VACIAS]
        if cand and n - ultimo > 1:
            out.append(max(cand, key=lambda j: len(_limpia(palabras[j]["w"]))))
            ultimo = n
    return out


def bloques(palabras: list) -> list:
    out, i0 = [], 0
    for j, p in enumerate(palabras):
        if j + 1 == len(palabras) or j + 1 - i0 >= PALABRAS_BLOQUE or p["w"][-1:] in ".,?!;:" or palabras[j + 1]["s"] - p["e"] > PAUSA_BLOQUE:
            out.append([i0, j + 1])
            i0 = j + 1
    return out


def armar(carpeta: Path) -> dict:
    """Storyboard completo del estilo: la toma entera (cortes del machote), cámara fija, sin elementos, subtítulo por bloques."""
    from . import machote
    palabras = json.loads((carpeta / "palabras.json").read_text())
    bl = bloques(palabras)
    mj = machote.cargar(carpeta) or {}
    sb = {"cortes": mj.get("cortes", []),
          "escenas": [{"t0": 0.0, "intencion": "Estilo básico: solo la toma con su color y el subtítulo palabra por palabra",
                       "persona": {"modo": "completa"}}],
          "elementos": [], "trazos": [],
          "camara": [{"t": 0.0, "zoom": 1.0, "x": 0.0, "y": 0.0, "rot": 0.0}],   # cámara fija: la toma tal cual
          "subtitulos": {"y": Y, "bloques": bl, "resaltar": claves(palabras, bl)}}
    (carpeta / "storyboard.json").write_text(json.dumps(sb, ensure_ascii=False, indent=1))
    return sb


def _rgb(c, defecto):
    c = (c or defecto).lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def _lineas(toks: list, f) -> list:
    """Parte las palabras en líneas que caben en ANCHO_MAX: [[(índice, ancho)...]]; el bloque se mide completo para que nada se mueva."""
    esp = f.getlength(" ")
    lineas, actual, ancho = [], [], 0
    for k, (w, _, _) in enumerate(toks):
        a = f.getlength(w)
        if actual and ancho + esp + a > ANCHO_MAX:
            lineas.append(actual)
            actual, ancho = [], 0
        ancho += (esp if actual else 0) + a
        actual.append((k, a))
    return lineas + [actual] if actual else lineas


def dibujar(lienzo, t: float, ws: list, est, fuente) -> None:
    """Pinta el bloque `ws` [(texto, inicio, es_clave)] en el instante t: cada palabra aparece cuando se dice (el bloque ya está
    medido, nada se corre), mayúsculas pesadas, clave de otro color, sombra suave, caja de color opcional."""
    cfg = est.basico
    toks = [(w.upper(), ts, h) for w, ts, h in ws]
    dichas = [k for k, (_, ts, _) in enumerate(toks) if t >= ts - .03]
    if not dichas:
        return
    f = fuente
    esp = f.getlength(" ")
    lineas = _lineas(toks, f)
    alto_l = int(TAM * INTERLINEA)
    alto = alto_l * len(lineas)
    cw = int(max(sum(a for _, a in l) + esp * (len(l) - 1) for l in lineas)) + 2 * (CAJA_PAD[0] + 30)
    capa = Image.new("RGBA", (cw, alto + 2 * (CAJA_PAD[1] + 30)))
    d = ImageDraw.Draw(capa)
    texto_c, clave_c = cfg["color"], cfg["clave"]
    pos = {}
    for n, l in enumerate(lineas):
        ancho_l = sum(a for _, a in l) + esp * (len(l) - 1)
        x = (cw - ancho_l) / 2
        yc = CAJA_PAD[1] + 30 + alto_l * n + alto_l / 2
        if cfg["caja"] and any(k in dichas for k, _ in l):
            d.rounded_rectangle((x - CAJA_PAD[0], yc - alto_l / 2 - CAJA_PAD[1] + 8, x + ancho_l + CAJA_PAD[0], yc + alto_l / 2 + CAJA_PAD[1] - 8),
                                CAJA_RADIO, fill=cfg["caja_color"] + (255,))
        for k, a in l:
            pos[k] = (x, yc, a)
            x += a + esp
    sombra = Image.new("RGBA", capa.size)
    sw = Image.new("RGBA", capa.size)
    ds = ImageDraw.Draw(sw)
    for k in dichas:
        w, ts, h = toks[k]
        x, yc, a = pos[k]
        p = 1.0
        efecto = cfg["efecto"]
        if efecto in DUR_ENTRADA:
            p = min(1.0, max(0.0, (t - ts) / DUR_ENTRADA[efecto]))
        pal = Image.new("RGBA", (int(a) + 80, alto_l + 40))
        dp = ImageDraw.Draw(pal)
        dp.text((40, 20 + alto_l / 2), w, font=f, fill=(clave_c if h else texto_c) + (255,), anchor="lm")
        if efecto == "pop" and p < 1.0:
            e = 1 - (1 - p) ** 3
            esc = .72 + .28 * e + .10 * math.sin(p * 3.14159)   # sube a ~1,06 y asienta en 1
            pal = pal.resize((max(1, int(pal.width * esc)), max(1, int(pal.height * esc))), Image.BILINEAR)
            pal.putalpha(pal.getchannel("A").point(lambda v: int(v * min(1.0, p * 2.5))))
        elif efecto == "sube" and p < 1.0:
            e = 1 - (1 - p) ** 3
            pal.putalpha(pal.getchannel("A").point(lambda v: int(v * e)))
        dy = int(26 * (1 - p) ** 3) if efecto == "sube" else 0
        ox, oy = int(x - 40 + a / 2 - pal.width / 2 + 40), int(yc - 20 - alto_l / 2 + (alto_l + 40) / 2 - pal.height / 2 + dy)
        capa.alpha_composite(pal, (max(0, ox), max(0, oy)))
        sombra.alpha_composite(pal, (max(0, ox), max(0, oy)))
    blur, off, op = SOMBRA
    sb_ = sombra.getchannel("A").filter(ImageFilter.GaussianBlur(blur)).point(lambda v: min(255, int(v * op / 255 * 1.0)))
    sh = Image.new("RGBA", capa.size, (0, 0, 0, 0))
    sh.putalpha(sb_)
    W = lienzo.width
    x0, y0 = (W - capa.width) // 2, int(Y - capa.height / 2)
    lienzo.alpha_composite(sh, (x0, y0 + off))
    lienzo.alpha_composite(capa, (x0, y0))


def opciones(est: dict) -> dict:
    """Las opciones del estilo, ya validadas, desde el bloque `estilo` del storyboard (la lectura es la común de todos los tipos)."""
    o = subtitulo_opciones.de_estilo(est)
    return {"color": o["color"] or _rgb(None, "#FFFFFF"), "clave": o["clave"] or _rgb(None, est.get("acento", "#E5252A")),
            "caja": bool(o["caja"]), "caja_color": o["caja_color"] or _rgb(None, "#111111"), "efecto": o["efecto"] or "corte"}
