"""Portada de cada estilo para el carrusel de la app (Pablo, 04-nov: «las miniaturas no se ven bien, tienen que verse más pro,
con todos los recursos»).

Sale del VIDEO APROBADO del estilo, no de un cuadro al azar, y SIEMPRE con el mismo criterio (Pablo, 07-nov: «las carátulas no
están estandarizadas»): la imagen grande es el cuadro más representativo de un APOYO sin la persona (B-roll, infografía, imagen,
motion); la tira de tres miniaturas muestra a la persona con sus textos (y, si el estilo tiene la pantalla oscura con la palabra sola, esa
como tercera). Encima, el nombre del
estilo con SU tipografía y acento, en la zona más libre y con contraste garantizado (se lee sobre cualquier fondo).
`integrar` la hace sola al aprobar un estilo.

    uv run estudio portadas            # todos los estilos aprobados
"""
import json
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from . import camara, config
from .contraste import luz as _luz

W, H = 720, 1280
DESTINO = config.RAIZ / "app" / "muestras"


def _escena(sb: dict, s: float) -> dict:
    esc = [x for x in sb.get("escenas", []) if x.get("t0", 0) <= s]
    return max(esc, key=lambda x: x["t0"]) if esc else {}


def _sin_persona(sb: dict, s: float) -> bool:
    """¿En ese segundo de la FUENTE la escena oculta a la persona (apoyo a pantalla completa)? Igual que el motor: cada escena
    manda por sí sola; sin «modo» la persona se ve."""
    return ((_escena(sb, s).get("persona") or {}).get("modo")) == "oculta"


def _activos(sb: dict, s: float) -> list:
    return [e for e in sb.get("elementos", []) if isinstance(e, dict) and e.get("t0", 0) <= s < e.get("t1", 0)]


def _riqueza(sb: dict, t_src: float) -> float:
    """Cuántos recursos se ven en ese segundo: imágenes pesan más que textos; una lámina sin la persona suma."""
    r = 0.0
    for e in _activos(sb, t_src):
        tipo = e.get("tipo")
        r += 2.0 if tipo in ("foto", "clip", "recorte", "vidrio", "panel") else 1.0 if tipo in ("texto", "etiqueta", "contador", "barra") else .5
    if _sin_persona(sb, t_src):
        r += 1.5
    return r


IMAGEN = ("foto", "clip", "recorte", "panel", "vidrio")
TEXTO = ("texto", "etiqueta", "contador", "barra")


def _golpe(sb: dict, s: float) -> bool:
    """¿Es una pantalla oscura sin la persona donde solo hay texto (la palabra sola, como el negro de Prestiggio)? La luz del fondo
    se lee del color de la escena; un fondo con nombre («muro-luz», «acento») no es oscuro."""
    fondo = (_escena(sb, s).get("persona") or {}).get("fondo")
    if not (_sin_persona(sb, s) and isinstance(fondo, str) and len(fondo) == 7 and fondo.startswith("#")):
        return False
    act = _activos(sb, s)
    return _luz(tuple(int(fondo[i:i + 2], 16) for i in (1, 3, 5))) < .03 and any(e.get("tipo") in TEXTO for e in act) \
        and not any(e.get("tipo") in IMAGEN for e in act)


def _a_fuente(sb: dict, t: float) -> float:
    """Segundo del video final → segundo de la fuente (los cortes quitan tramos)."""
    quitado = 0.0
    for a, b in sorted(sb.get("cortes", [])):
        if a <= t + quitado:
            quitado += b - a
    return t + quitado


def _hablando(palabras: list, s: float) -> bool:
    return any(not p.get("fuera") and p["s"] <= s <= p["e"] + .15 for p in palabras)


def momentos(sb: dict, dur: float, n: int = 4, separacion: float = 3.0, quien: str | None = None, palabras: list | None = None) -> list:
    """Los n segundos del video final con más recursos, separados entre sí (nunca el inicio limpio).
    quien="apoyo": solo escenas SIN la persona (B-roll, infografía, imagen, motion a pantalla completa), ya asentadas
    (>0,9 s tras entrar) y con al menos un recurso visual: es la portada grande (Pablo, 07-nov: «lo más representativo de las
    tomas de apoyo, donde no aparece la persona»).
    quien="persona": la persona en pantalla, hablando (con voz) y con TEXTO encima (Pablo, 07-nov: «las pequeñas, cómo se ven los
    textos sobre la persona»); se eligen variados (texto solo, con imagen…) para que las miniaturas muestren cómo se integra todo.
    quien="golpe": la pantalla oscura con la palabra sola, sin la persona (el negro de Prestiggio)."""
    cand = []
    t = 3.2
    while t < dur - .3:
        s = _a_fuente(sb, t)
        en_transicion = any(0 <= s - e.get("t0", 0) < (.9 if quien == "apoyo" else .7) for e in sb.get("escenas", []))
        if not en_transicion:     # nunca en medio de una transición (rack focus, flash, iris…)
            r = _riqueza(sb, s)
            act = _activos(sb, s)
            if quien == "apoyo":
                if _sin_persona(sb, s) and any(e.get("tipo") in IMAGEN + TEXTO for e in act):
                    cand.append((r + (3 if any(e.get("tipo") in IMAGEN for e in act) else 0), t))
            elif quien == "persona":
                if not _sin_persona(sb, s) and (_hablando(palabras, s) if palabras else True) and any(e.get("tipo") in TEXTO for e in act):
                    cand.append((r, t))
            elif quien == "golpe":
                if _golpe(sb, s):
                    cand.append((r, t))
            else:
                cand.append((r, t))
        t += .25
    if quien == "persona":
        return _variados(sb, cand, n, separacion)
    elegidos = []
    for r, t in sorted(cand, reverse=True):
        if all(abs(t - u) >= separacion for u in elegidos):
            elegidos.append(t)
        if len(elegidos) == n:
            break
    return elegidos or ([] if quien else [dur / 2])


def _variados(sb: dict, cand: list, n: int, separacion: float) -> list:
    """Cada miniatura aporta algo distinto: primero una con texto, luego con imagen, luego la más rica que quede."""
    def tipos(t):
        act = _activos(sb, _a_fuente(sb, t))
        return {"imagen" for e in act if e.get("tipo") in IMAGEN} | {"texto" for e in act if e.get("tipo") in TEXTO}
    elegidos, vistos = [], set()
    for _ in range(n):
        libres = [(r, t) for r, t in cand if all(abs(t - u) >= separacion for u in elegidos)]
        if not libres:
            break
        r, t = max(libres, key=lambda c: ("texto" in tipos(c[1]) - vistos, len(tipos(c[1]) - vistos), c[0]))
        elegidos.append(t)
        vistos |= tipos(t)
    return elegidos


def _cuadro(video: Path, t: float) -> Image.Image:
    ffmpeg, _ = config.ffmpeg()
    r = subprocess.run([ffmpeg, "-v", "error", "-ss", f"{t:.2f}", "-i", str(video), "-frames:v", "1", "-f", "image2pipe",
                        "-vcodec", "png", "-"], capture_output=True, check=True)
    from io import BytesIO
    return Image.open(BytesIO(r.stdout)).convert("RGB")


def _redondear(im: Image.Image, radio: int) -> Image.Image:
    m = Image.new("L", im.size, 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, im.width - 1, im.height - 1), radio, fill=255)
    im = im.convert("RGBA")
    im.putalpha(m)
    return im


LEGIBLE_MIN = 7.0   # contraste mínimo (WCAG AAA) del nombre contra lo que tiene detrás


def enredo(im: Image.Image, caja: tuple) -> float:
    """Qué tan cargado está el fondo en esa caja (0 = liso; más = bordes y detalle). Sirve para elegir la zona más libre."""
    g = im.convert("L").crop(caja).filter(ImageFilter.FIND_EDGES)
    return sum(g.getdata()) / max(1, g.width * g.height)


def contraste(im: Image.Image, caja: tuple, texto=(245, 245, 247)) -> float:
    """Contraste del texto claro contra el fondo MÁS CLARO que haya en la caja (peor caso: percentil 95)."""
    luces = sorted(_luz(px) for px in im.convert("RGB").crop(caja).resize((48, 16)).getdata())
    fondo = luces[int(len(luces) * .95) - 1]
    return (_luz(texto) + .05) / (fondo + .05)


def asegurar_legible(lienzo: Image.Image, caja: tuple, minimo: float = LEGIBLE_MIN) -> float:
    """Garantía en código de que el nombre se lee: si el fondo de su caja no da el contraste mínimo, se desenfoca y se oscurece
    esa zona (más y más) hasta darlo. Devuelve el contraste final. Cambia `lienzo` en sitio."""
    x0, y0, x1, y1 = caja
    base = lienzo.crop(caja).convert("RGB")
    for fuerza in (0, .25, .4, .55, .7, .82, .92, 1.0):
        zona = base if not fuerza else Image.blend(base.filter(ImageFilter.GaussianBlur(14 * fuerza)), Image.new("RGB", base.size, (8, 8, 10)), fuerza * .85)
        if fuerza:
            borde = Image.new("L", base.size, 0)
            ImageDraw.Draw(borde).rounded_rectangle((0, 0, base.width - 1, base.height - 1), 22, fill=255)
            lienzo.paste(zona.convert("RGBA"), (x0, y0), borde.filter(ImageFilter.GaussianBlur(6)))
        if contraste(lienzo, caja) >= minimo:
            return contraste(lienzo, caja)
    return contraste(lienzo, caja)


def cuadros_de(sb: dict, dur: float, palabras: list | None = None) -> dict:
    """Qué segundos del video final van en la portada: {"apoyo": [candidatos de la grande], "persona": [3 miniaturas con texto],
    "golpe": [la pantalla oscura con la palabra, si el estilo la tiene]}. Sin relleno: si falta lo que el criterio exige, ValueError."""
    apoyo = momentos(sb, dur, n=6, quien="apoyo", palabras=palabras)
    persona = momentos(sb, dur, n=3, quien="persona", palabras=palabras)
    if not apoyo:
        raise ValueError("no hay cuadro de apoyo sin persona")
    if len(persona) < 3:
        raise ValueError("menos de 3 cuadros de persona con texto")
    return {"apoyo": apoyo, "persona": persona, "golpe": momentos(sb, dur, n=1, quien="golpe", palabras=palabras)}


def previa(sb: dict, dur: float, palabras: list | None = None) -> tuple:
    """(persona, apoyo): segundos del video final para las dos vistas de Personalizar. Cada una se elige por separado con su criterio
    (persona hablando con texto / escena sin la persona), de modo que lo que falte en una nunca le quita a la otra su cuadro; solo si
    una no existe se usa el momento más rico que quede. Un proyecto propio puede no tener apoyos ni textos: nunca se rompe."""
    cualquiera = momentos(sb, dur, n=2)
    persona = (momentos(sb, dur, n=1, quien="persona", palabras=palabras) or cualquiera)[:1]
    apoyo = (momentos(sb, dur, n=1, quien="apoyo", palabras=palabras) or cualquiera[-1:])[:1]
    return persona[0], apoyo[0]


def es_apoyo(sb: dict, t: float) -> bool:
    """¿En ese segundo del video final la escena es un apoyo a pantalla completa (sin la persona)?"""
    return _sin_persona(sb, _a_fuente(sb, t))


def portada(estilo: str, proyecto: Path, salida: Path | None = None) -> Path:
    """Grande = el cuadro más representativo de un APOYO sin la persona; tira de 3 miniaturas = la persona con sus subtítulos,
    imágenes y textos animados; el nombre del estilo siempre legible (zona más libre + contraste garantizado)."""
    from . import motor
    proyecto = Path(proyecto)
    sb = json.loads((proyecto / "storyboard.json").read_text())
    video = proyecto / "final.mp4"
    pal = proyecto / "palabras.json"
    palabras = json.loads(pal.read_text()) if pal.exists() else None
    _, ffprobe = config.ffmpeg()
    dur = float(subprocess.run([ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(video)],
                               capture_output=True, text=True).stdout.strip() or 20)
    elegidos = cuadros_de(sb, dur, palabras)

    def nitidez(im):
        g = im.convert("L").resize((270, 480)).filter(ImageFilter.FIND_EDGES)
        return sum(g.getdata()) / (270 * 480)

    from PIL import ImageStat

    def contr(im):
        return ImageStat.Stat(im.convert("L").resize((270, 480))).stddev[0]
    cuadros = [(t, _cuadro(video, t)) for t in elegidos["apoyo"]]
    buenos = [(t, im) for t, im in cuadros if nitidez(im) > 6 and contr(im) > 38]   # ni borrosos ni lavados
    if not buenos:
        raise ValueError("ningún cuadro de apoyo es nítido y con contraste")
    heroe = buenos[0][1].resize((W, H), Image.LANCZOS)
    lienzo = heroe.convert("RGBA")
    # degradado inferior para que se lea la tira
    grad = Image.new("L", (1, H))
    for y in range(H):
        grad.putpixel((0, y), int(245 * min(1.0, max(0.0, (y - H * .45) / (H * .35))) ** 1.2))
    negro = Image.new("RGBA", (W, H), (8, 8, 10, 255))
    negro.putalpha(grad.resize((W, H)))
    lienzo.alpha_composite(negro)
    # tira de 3 miniaturas con la persona
    mini_w = (W - 4 * 22) // 3
    mini_h = int(mini_w * 16 / 9)
    y0 = H - mini_h - 40
    for k, t in enumerate(elegidos["persona"][:2] + elegidos["golpe"] if elegidos["golpe"] else elegidos["persona"][:3]):
        m = _cuadro(video, t).resize((mini_w, mini_h), Image.LANCZOS)
        sombra = Image.new("RGBA", (mini_w + 30, mini_h + 30), (0, 0, 0, 0))
        ImageDraw.Draw(sombra).rounded_rectangle((15, 15, mini_w + 15, mini_h + 15), 18, fill=(0, 0, 0, 150))
        x = 22 + k * (mini_w + 22)
        lienzo.alpha_composite(sombra.filter(ImageFilter.GaussianBlur(10)), (x - 15, y0 - 10))
        lienzo.alpha_composite(_redondear(m, 16), (x, y0))
    # nombre con la tipografía y el acento del estilo, en la zona más libre y con contraste garantizado
    presets = json.loads((config.RAIZ / "librerias" / "estilos" / "presets.json").read_text())
    pre = presets.get(estilo, {})
    est = motor.Estilo({k: v for k, v in pre.items() if k != "nombre"})
    nombre = pre.get("nombre", estilo)
    d = ImageDraw.Draw(lienzo)
    tam = 96
    f = est.font_rol("display", tam)
    while d.textlength(nombre, font=f) > W - 80 and tam > 40:
        tam -= 6
        f = est.font_rol("display", tam)
    acento = est.color("acento") if hasattr(est, "color") else (255, 255, 255)
    ancho_t = int(d.textlength(nombre, font=f))
    pos = {"abajo": y0 - tam - 54, "arriba": 250}
    cajas = {k: (24, y - 18, min(W - 24, 40 + max(ancho_t, 90) + 24), y + tam + 38) for k, y in pos.items()}
    donde = min(cajas, key=lambda k: enredo(lienzo, cajas[k]))
    ytxt, caja = pos[donde], cajas[donde]
    asegurar_legible(lienzo, caja)
    d = ImageDraw.Draw(lienzo)
    d.text((42, ytxt + 3), nombre, font=f, fill=(0, 0, 0, 160))
    d.text((40, ytxt), nombre, font=f, fill=(245, 245, 247, 255))
    d.rectangle((40, ytxt + tam + 16, 40 + 90, ytxt + tam + 22), fill=tuple(acento[:3]) + (255,))
    salida = Path(salida or DESTINO / f"{estilo}.jpg")
    lienzo.convert("RGB").save(salida, quality=90)
    return salida


FRASES_SIN_VIDEO = (("Solo", "tus", "palabras"), ("una", "por", "una"), ("y", "nada", "más"))


def portada_sin_director(estilo: str, salida=None) -> Path:
    """Portada de un estilo que no usa director (Básico: solo subtítulos). No hay video aprobado del que sacarla, así que se dibuja
    con el subtítulo REAL del motor sobre un fondo neutro, con la misma retícula que las demás: imagen grande, nombre y tres
    miniaturas (aquí, las tres formas del subtítulo: sin caja, con caja y otra frase)."""
    from . import motor, subtitulo_basico
    pre = json.loads((config.RAIZ / "librerias" / "estilos" / "presets.json").read_text())[estilo]

    def fondo(tono):   # degradado suave: el lugar donde iría la toma de la persona
        im = Image.new("RGBA", (config.W, config.H), (0, 0, 0, 255))
        d = ImageDraw.Draw(im)
        for y in range(config.H):
            v = int(tono + 26 * (1 - abs(y / config.H - .45) * 2))
            d.line([(0, y), (config.W, y)], fill=(v, v, v + 4, 255))
        return im

    def subtitulo(frase, clave, caja):   # el subtítulo solo, sobre transparente, dibujado por el motor
        est = motor.Estilo({**{k: v for k, v in pre.items() if k != "nombre"}, "sub_caja": caja})
        capa = Image.new("RGBA", (config.W, config.H), (0, 0, 0, 0))
        subtitulo_basico.dibujar(capa, 9.0, [(w, .1 * k, k == clave) for k, w in enumerate(frase)], est, est.font_rol("display", subtitulo_basico.TAM, 900))
        return capa

    def cuadro(frase, clave, caja, tono):
        im = fondo(tono)
        im.alpha_composite(subtitulo(frase, clave, caja))
        return im
    lienzo = fondo(30).resize((W, H), Image.LANCZOS)
    grande = subtitulo(FRASES_SIN_VIDEO[0], 2, False)
    grande = grande.crop(grande.getbbox())
    grande = grande.resize((W - 120, round(grande.height * (W - 120) / grande.width)), Image.LANCZOS)
    lienzo.alpha_composite(grande, (60, round(H * .34) - grande.height // 2))   # en el centro de la imagen grande, lejos del nombre y la tira
    mini_w = (W - 4 * 22) // 3
    mini_h = int(mini_w * 16 / 9)
    y0 = H - mini_h - 40
    for k, (frase, clave, caja, tono) in enumerate(((FRASES_SIN_VIDEO[0], 2, False, 44), (FRASES_SIN_VIDEO[1], 0, True, 58), (FRASES_SIN_VIDEO[2], 1, False, 36))):
        m = cuadro(frase, clave, caja, tono).resize((mini_w, mini_h), Image.LANCZOS)
        lienzo.alpha_composite(_redondear(m, 16), (22 + k * (mini_w + 22), y0))
    est = motor.Estilo({k: v for k, v in pre.items() if k != "nombre"})
    d, tam = ImageDraw.Draw(lienzo), 96
    f = est.font_rol("display", tam)
    ytxt = y0 - tam - 54
    d.text((42, ytxt + 3), pre["nombre"], font=f, fill=(0, 0, 0, 160))
    d.text((40, ytxt), pre["nombre"], font=f, fill=(245, 245, 247, 255))
    d.rectangle((40, ytxt + tam + 16, 40 + 90, ytxt + tam + 22), fill=tuple(est.color("acento")[:3]) + (255,))
    salida = Path(salida or DESTINO / f"{estilo}.jpg")
    lienzo.convert("RGB").save(salida, quality=90)
    return salida


def aprobados() -> dict:
    """{estilo: proyecto de su copia aprobada} para los estilos integrados al director (sale de su ejemplo)."""
    from .director import AQUI, _obsoletos
    obs = _obsoletos()
    out = {}
    for f in sorted((AQUI / "ejemplo").glob("*.json")):
        if f.name.endswith("palabras.json") or f.name in obs:
            continue
        cands = [config.PROYECTOS / f"c8866-{f.stem}", config.PROYECTOS / f"c8866-{f.stem}4"]
        for c in cands:
            if (c / "final.mp4").exists() and (c / "storyboard.json").exists():
                out[f.stem] = c
                break
    return out


def todas(avance=print) -> list:
    hechas = []
    presets = json.loads((config.RAIZ / "librerias" / "estilos" / "presets.json").read_text())
    for estilo in (e for e, p in presets.items() if p.get("sin_director")):
        hechas.append(str(portada_sin_director(estilo)))
        avance(f"{estilo}: portada lista")
    for estilo, proy in aprobados().items():
        try:
            hechas.append(str(portada(estilo, proy)))
            avance(f"{estilo}: portada lista")
        except Exception as e:  # noqa: BLE001 — una portada que falla no frena las demás
            avance(f"{estilo}: {e}")
    return hechas
