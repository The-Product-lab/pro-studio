"""Compuerta del storyboard: el motor solo acepta lo que sabe dibujar, y las reglas de Pablo viven aquí, en código.

`errores(sb, carpeta)` devuelve la lista de problemas (vacía = pasa). Lo usan el director (si falla, Opus lo corrige con
la lista exacta), el estilista y las pruebas. Una clave desconocida es un ERROR, no se ignora: así nadie escribe en una
guía un efecto que el motor no tiene y que en el render no aparece.

Cuando el motor aprende algo nuevo, se agrega aquí (y en GRAMATICA.md) en el mismo cambio.
"""
import colorsys
import json
import re
from pathlib import Path

from . import config, efectos, subtitulo_opciones

W, H = config.W, config.H
ZONA_TEXTO = (config.ZONA_SEGURA[1], config.ZONA_SEGURA[3])   # Instagram tapa arriba y abajo (regla de Pablo)
MARGEN = 20

ENTRADAS = {"cae", "izq", "der", "sube", "pop", "barrido", "golpe", "fundido", "enfoque", "smear", "llega"}
ROLES = {"display", "script", "mono"}
NOMBRES_COLOR = {"acento", "acento2", "tinta", "papel", "blanco", "negro"}
BASES = {"pantalla"}   # la persona en su toma completa; el collage con la persona recortada se retiró (11-nov)
SUBTITULOS = {"tira", "hud", "vidrio", "basico"}

CLAVES = {
    "raiz": {"estilo", "cortes", "escenas", "punch", "empuje", "alejar_final", "golpe", "elementos", "trazos", "cajas",
             "subtitulos", "sonido", "camara", "camara_apagar"},
    "estilo": {"id", "nombre", "base", "acento", "acento2", "tinta", "papel", "borde", "texto", "tono", "grano", "persona", "subtitulo",
               "crt", "fuente", "fuente_script", "fuente_mono", "filtro", "color", "aberracion_corte", "imagenes", "sfx", "tope_imagenes", "transicion", "flotar", "bloom", "flotar_elementos", "sonido_paleta", "camara_apagar",
               "sin_director", "lemo", *subtitulo_opciones.CLAVES},
    "escena": {"t0", "intencion", "persona", "filtro", "entrada", "franjas", "camara", "camara_mov"},
    "persona": {"x", "escala", "modo", "fondo", "contorno", "color"},
    "franja": {"filtro", "etiqueta"},
    "elemento": {"id", "tipo", "src", "ancho", "rot", "x", "y", "t0", "t1", "entra", "dur", "z", "crop", "gris", "lineas",
                 "singular", "gancho", "fondo", "pad", "brillo", "sombra", "interlineado", "radio", "letra", "rol", "colores", "celda", "cubrir", "tam", "titila", "color", "desenfoque", "reflejo", "luz", "color_luz", "fundir", "velocidad", "fusion", "desde", "hasta", "prefijo", "sufijo",
                 "decimales", "cuenta_s", "crece_s", "contorno", "caja", "flotar", "profundidad", "muestra", "tratamiento", "grupo", "velo", "tecleo", "cursor", "direccion",
                 "alto", "acercar"},
    "linea_texto": {"texto", "rol", "tam", "color", "mayus", "contorno", "trazo", "extrusion", "escala_y", "peso", "italica"},
    "trazo": {"tipo", "sobre", "centro", "radio", "desde", "hacia", "puntos", "t0", "dur", "t1", "z", "grosor", "paso", "color", "nodos", "cols", "filas", "margen", "cruces"},
    "caja": {"t0", "t1", "dur", "sobre", "etiqueta", "datos", "margen", "color"},
    "subtitulos": {"y", "bloques", "resaltar", "ocultar", "tam"},
}
MODOS = {"pantalla": {"completa", "oculta"}}   # la persona se ve entera o no se ve: no se recorta del fondo
ENTRADAS_ESCENA = {"corte", "rafaga", "flash", "zoom", "pixel", "bloques", "invertir", "wipe", "iris", "desenfoque"}
TIPOS_ELEMENTO = {"foto", "recorte", "etiqueta", "texto", "pixeles", "destello", "panel", "clip", "contador", "barra", "vidrio"}
CAMARAS = {"push", "pull", "deriva", "subida", "giro", "estatica"}
TIPOS_TRAZO = {"rect", "elipse", "rayos", "linea", "reticula"}


def es_rosa(hexa: str) -> bool:
    """Rosa / magenta prohibido (regla de Pablo): tono 290–345° con saturación y luz visibles."""
    r, g, b = (int(hexa.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4))
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    return 290 <= h * 360 <= 345 and s > .25 and .2 < l < .92


_HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")


FAMILIAS_COLOR = {"rosa": es_rosa}
REGLAS = config.RAIZ / "perfil" / "reglas.json"


DENSIDADES = ("poco", "normal", "mucho")    # Pablo 07-nov: «un dimerizable de tres puntos: poco, normal, mucho» por estilo


def densidad_de(carpeta) -> str:
    """La densidad elegida para ese video (preferencias.json › densidad); sin elegir = «normal» (la del ejemplo aprobado)."""
    f = Path(carpeta) / "preferencias.json" if carpeta else None
    try:
        d = json.loads(f.read_text()).get("densidad") if f and f.exists() else None
    except (ValueError, AttributeError):   # preferencias dañadas: se trabaja con la densidad normal, nunca se cae
        d = None
    return d if d in DENSIDADES else "normal"


def fijar_densidad(carpeta, densidad: str) -> None:
    if densidad not in DENSIDADES:
        raise ValueError(f"densidad «{densidad}»: usa {', '.join(DENSIDADES)}")
    f = Path(carpeta) / "preferencias.json"
    d = json.loads(f.read_text()) if f.exists() else {}
    d["densidad"] = densidad
    f.write_text(json.dumps(d, ensure_ascii=False, indent=1))


def reglas(estilo: str | None, densidad: str = "normal") -> dict:
    """Las reglas de Pablo para ese estilo: las globales + las del estilo (perfil/reglas.json). Sin archivo = sin reglas."""
    d = json.loads(REGLAS.read_text()) if REGLAS.exists() else {}
    g, e = d.get("global", {}), d.get("estilos", {}).get(estilo or "", {})
    out = {k: list(g.get(k, [])) + list(e.get(k, [])) for k in ("colores_prohibidos", "nota")}
    for k in ("color_toma_intocable", "filtro_max_s", "sujeto_recortado_prohibido", "variedad", "apoyo_literal_ventana_s", "texto_linea_min_px", "pantalla_principal_ancho_min",
              "flotar_elementos_max", "camara_fija", "elementos_a_la_vez_max", "apoyo_integrado", "texto_salto_max_px", "inicio_limpio_s", "ritmo",
              "texto_siempre_max_s", "recurso_hueco_max_s", "punch_max_por_min", "camara_cambio_min_s"):
        out[k] = e.get(k, g.get(k))
    return out   # el ritmo es UN techo (reglas.json › ritmo): el ejemplo aprobado ya no lo sube (es inspiración, no medida)


def _calma_e_integracion(sb: dict, r: dict) -> list:
    """Pablo (04-nov): «no me gusta cuando hay varios movimientos al mismo tiempo… solo un movimiento, el del texto y si hay una
    imagen animada» y «no me gusta cuando se ven las imágenes cuadradas… montas encima una imagen cuadrada y ya»."""
    err = []
    tope = r.get("flotar_elementos_max")
    est = sb.get("estilo") or {}
    if tope is not None:
        if float(est.get("flotar_elementos", 0) or 0) > tope:
            err.append(f"estilo.flotar_elementos = {est['flotar_elementos']}: un movimiento a la vez; los elementos no flotan cada uno por su lado (máx. {tope})")
        for i, e in enumerate(sb.get("elementos", [])):
            if isinstance(e, dict) and float(e.get("flotar", 0) or 0) > tope and e.get("tipo") not in ("foto", "recorte", "clip"):
                err.append(f"elementos[{i}] «{e.get('id')}»: flotar {e['flotar']} — solo una imagen animada puede moverse además del texto")
    if r.get("apoyo_integrado"):
        for i, e in enumerate(sb.get("elementos", [])):
            if isinstance(e, dict) and e.get("tipo") in ("foto", "clip") and not (e.get("fundir") or e.get("fusion") or e.get("cubrir")):
                err.append(f"elementos[{i}] «{e.get('id')}»: imagen cuadrada montada encima; intégrala al diseño (\"fundir\", \"fusion\" o \"cubrir\" como fondo)")
    return err


def _texto_en_recorrido(sb: dict, r: dict) -> list:
    """Pablo (04-nov, para todo el sistema): «los textos deben aparecer siempre en una posición y ubicación similar al anterior…
    se pueden mover por toda la zona segura, pero con movimiento de ubicación gradual, como una montaña rusa». Entre dos textos
    principales seguidos (≤ 4 s entre uno y otro) el centro no salta más de `texto_salto_max_px`."""
    tope = r.get("texto_salto_max_px")
    if not tope:
        return []
    def principal(e):
        if not isinstance(e, dict) or e.get("tipo") not in ("texto", "etiqueta") or "t0" not in e:
            return False
        l0 = (e.get("lineas") or [{}])[0]
        tam = l0.get("tam", 0) if isinstance(l0, dict) else (l0[1] if isinstance(l0, list) and len(l0) > 1 else 0)
        txt = (l0.get("texto", "") if isinstance(l0, dict) else l0[0] if isinstance(l0, list) and l0 else "") or ""
        return tam >= 90 and len(str(txt).strip()) > 2   # un signo suelto («?», «→») es detalle, no un texto del recorrido
    ts = sorted(((i, e) for i, e in enumerate(sb.get("elementos", [])) if principal(e)), key=lambda p: p[1]["t0"])
    err = []
    for (_, a), (j, b) in zip(ts, ts[1:]):
        if b["t0"] - a.get("t1", a["t0"]) > 4 or b.get("grupo") and b.get("grupo") == a.get("grupo"):
            continue
        d = ((b.get("x", 540) - a.get("x", 540)) ** 2 + (b.get("y", 960) - a.get("y", 960)) ** 2) ** .5
        if d > tope:
            err.append(f"elementos[{j}] «{b.get('id')}»: el texto salta {d:.0f} px desde «{a.get('id')}» (máx. {tope}); que el recorrido sea gradual")
    return err


def _paleta_sonido(sb: dict) -> list:
    from . import sonido
    pal = (sb.get("estilo") or {}).get("sonido_paleta")
    return [] if pal is None or pal in sonido.PALETAS else [f"estilo.sonido_paleta: {pal!r} no existe (hay: {sorted(sonido.PALETAS)})"]


def _fuente_de_salida(sb: dict, t_out: float) -> float:
    """Segundo del video final → segundo de la fuente (inverso de camara.salida)."""
    t, quitado = t_out, 0.0
    for a, b in sorted(sb.get("cortes", [])):
        if a <= t + quitado:
            quitado += b - a
    return t_out + quitado


GANCHO_TIPOS = {"texto", "etiqueta", "vidrio"}   # el gancho es texto o caja; nunca una imagen
GANCHO_DUR_MAX_S = .05                            # «entrada» de un gancho fijo: un fundido de esta duración o menos (es un corte)


def _gancho(sb: dict, r: dict) -> list:
    """El gancho (Pablo 10-nov: persona + texto o caja del gancho desde el cuadro 0): UN solo grupo con `gancho: true`, de texto o caja, y fijo:
    sin flotar y sin entrada animada (`entra: fundido` con `dur` mínima). Así el inicio sigue limpio salvo por él."""
    els = [(i, e) for i, e in enumerate(sb.get("elementos", [])) if isinstance(e, dict) and e.get("gancho")]
    if not els:
        return []
    err = []
    grupos = {e.get("grupo") or f"elemento:{e.get('id', i)}" for i, e in els}
    if len(grupos) > 1:
        err.append(f"gancho: {len(grupos)} grupos marcados con `gancho: true` ({', '.join(sorted(grupos))}); solo uno")
    fl = float((sb.get("estilo") or {}).get("flotar_elementos", 0) or 0)
    for i, e in els:
        if e.get("tipo") not in GANCHO_TIPOS:
            err.append(f"elementos[{i}] «{e.get('id')}»: el gancho es texto o caja ({', '.join(sorted(GANCHO_TIPOS))}), no «{e.get('tipo')}»")
        if float(e.get("flotar", fl) or 0) > 0:
            err.append(f"elementos[{i}] «{e.get('id')}»: el gancho no flota en el inicio (pon `flotar: 0`)")
        if e.get("tecleo") or e.get("titila"):
            err.append(f"elementos[{i}] «{e.get('id')}»: el gancho no se teclea ni titila: lo quieto es quieto")
        if e.get("entra") != "fundido" or float(e.get("dur", .35)) > GANCHO_DUR_MAX_S:
            err.append(f"elementos[{i}] «{e.get('id')}»: el gancho entra seco desde el cuadro 0 (`entra: fundido` con `dur` ≤ {GANCHO_DUR_MAX_S})")
    return err


def _inicio_limpio(sb: dict, r: dict) -> list:
    """Pablo (04-nov): «no uses motion al principio»: los primeros N s del final, solo la persona."""
    n = r.get("inicio_limpio_s")
    if not n:
        return []
    from . import camara
    err = []
    for i, e in enumerate(sb.get("elementos", [])):
        if isinstance(e, dict) and e.get("gancho") and "t0" in e:   # el texto o caja del gancho SÍ vive desde el cuadro 0
            if camara.salida(sb, e["t0"]) > .1:
                err.append(f"elementos[{i}] «{e.get('id')}»: el gancho entra desde el cuadro 0 (empieza en el segundo {camara.salida(sb, e['t0']):.1f})")
            continue
        if isinstance(e, dict) and "t0" in e and camara.salida(sb, e["t0"]) < n - .05 and camara.salida(sb, e.get("t1", e["t0"])) > .05:
            err.append(f"elementos[{i}] «{e.get('id')}»: aparece en el segundo {camara.salida(sb, e['t0']):.1f} del video; los primeros {n} s van limpios (solo la persona)")
    for i, z in enumerate(sb.get("trazos", [])):
        if isinstance(z, dict) and _num(z.get("t0")) and camara.salida(sb, z["t0"]) < n - .05 and camara.salida(sb, z.get("t1", z["t0"] + z.get("dur", 1))) > .05:
            err.append(f"trazos[{i}]: aparece en el segundo {camara.salida(sb, z['t0']):.1f} del video; los primeros {n} s van limpios (solo la persona)")
    for t in sb.get("punch", []):
        if _num(t) and camara.salida(sb, t) < n - .05:
            err.append(f"punch en el segundo {camara.salida(sb, t):.1f}: los primeros {n} s van limpios (sin golpes de zoom)")
    for i, e in enumerate(sb.get("escenas", [])):
        sig = [x["t0"] for x in sb.get("escenas", []) if x.get("t0", 0) > e.get("t0", 0)]
        if camara.salida(sb, e.get("t0", 0)) < n - .05 and (sig and camara.salida(sb, min(sig)) > .05 or not sig) \
                and (e.get("persona") or {}).get("modo") == "oculta":
            err.append(f"escenas[{i}]: lámina sin la persona en los primeros {n} s; el inicio va limpio, con la persona")
    return err


def limpiar_inicio(sb: dict) -> dict:
    """Lo hace el código: lo que entra en los primeros N s pasa a entrar en el segundo N, y una lámina sin persona al inicio
    empieza en N (antes, la toma de la persona)."""
    import copy
    n = reglas((sb.get("estilo") or {}).get("id")).get("inicio_limpio_s")
    if not n:
        return sb
    from . import camara
    sb = copy.deepcopy(sb)
    t_n = _fuente_de_salida(sb, n)
    for e in sb.get("elementos", []):
        if isinstance(e, dict) and "t0" in e and not e.get("gancho") and camara.salida(sb, e["t0"]) < n - .05:
            if camara.salida(sb, e.get("t1", e["t0"])) <= n + .3:
                e["t1"] = e["t0"]            # vivía solo en el inicio: se va
                e["_fuera"] = True
            else:
                e["t0"] = round(t_n, 3)
    sb["elementos"] = [e for e in sb.get("elementos", []) if not (isinstance(e, dict) and e.pop("_fuera", False))]
    for z in sb.get("trazos", []):
        if isinstance(z, dict) and _num(z.get("t0")) and camara.salida(sb, z["t0"]) < n - .05:
            if camara.salida(sb, z.get("t1", z["t0"] + z.get("dur", 1))) <= n + .3:
                z["_fuera"] = True
            else:
                z["t0"] = round(t_n, 3)
    sb["trazos"] = [z for z in sb.get("trazos", []) if not (isinstance(z, dict) and z.pop("_fuera", False))]
    if "punch" in sb:
        sb["punch"] = [t for t in sb["punch"] if not (_num(t) and camara.salida(sb, t) < n - .05)]
    escenas = sorted(sb.get("escenas", []), key=lambda e: e.get("t0", 0))
    for k, e in enumerate(escenas):
        if camara.salida(sb, e.get("t0", 0)) < n - .05 and (e.get("persona") or {}).get("modo") == "oculta":
            fin = escenas[k + 1]["t0"] if k + 1 < len(escenas) else None
            if fin is None or camara.salida(sb, fin) > n:
                escenas.insert(k + 1, {**e, "t0": round(t_n, 3),   # la lámina entra en el segundo N con rack focus
                                       "entrada": e.get("entrada") if e.get("entrada", "corte") != "corte" else "desenfoque"})
            e["persona"] = {**(e.get("persona") or {}), "modo": "completa"}
            e.pop("filtro", None)
    sb["escenas"] = sorted(escenas, key=lambda e: e.get("t0", 0))
    return sb


def _entradas(sb: dict) -> list:
    """Segundos (del video final) en que ENTRA algo que se ve: imágenes y textos grandes; lo que entra junto es una cosa."""
    from . import camara
    def visible(e):   # lo que se ve entrar: imágenes y textos grandes (no cada palabra de un subtítulo armado a mano)
        if e.get("tipo") in ("texto", "etiqueta"):
            l0 = (e.get("lineas") or [{}])[0]
            tam = l0.get("tam", 0) if isinstance(l0, dict) else (l0[1] if isinstance(l0, list) and len(l0) > 1 else 0)
            return tam >= 70
        return e.get("tipo") not in ("pixeles", "destello")
    crudo = sorted(((camara.salida(sb, e["t0"]), e.get("grupo") or "") for e in sb.get("elementos", [])
                   if isinstance(e, dict) and "t0" in e and visible(e)), key=lambda x: x[0])
    ent, vistos = [], set()
    for t, g in crudo:   # lo que entra junto (mismo grupo o < 0,5 s) es UNA cosa
        if g and g in vistos:
            continue
        if ent and t - ent[-1] < .5:
            continue
        ent.append(t)
        if g:
            vistos.add(g)
    return ent


def _ritmo(sb: dict, r: dict) -> list:
    """Pablo (04-nov): «el ritmo es muy rápido, muchos cortes y elementos en muy poco tiempo». Se mide en el video final."""
    v = r.get("ritmo")
    if not v:
        return []
    from . import camara
    err = []
    esc = sorted(camara.salida(sb, e["t0"]) for e in sb.get("escenas", []) if isinstance(e, dict) and "t0" in e)
    esc = [t for k, t in enumerate(esc) if k == 0 or t - esc[k - 1] > .05]   # una escena que cae dentro de un corte no se ve
    for a, b in zip(esc, esc[1:]):
        if b - a < v["escena_min_s"] - .05:
            err.append(f"ritmo: una escena dura {b - a:.1f} s (en el segundo {a:.1f}); mínimo {v['escena_min_s']} s: más calma, junta escenas")
            break
    ent = _entradas(sb)
    for t in ent:
        n = sum(1 for u in ent if t <= u < t + v["ventana_s"])
        if n > v["entradas_max"]:
            err.append(f"ritmo: entran {n} cosas en {v['ventana_s']} s (desde el segundo {t:.1f}); máximo {v['entradas_max']}: que cada cosa respire")
            break
    return err


def _recursos(sb: dict, r: dict, palabras) -> list:
    """Pablo (07-nov, Cine C8867, todos los estilos): «el editor no le está poniendo casi recurso». Después del inicio limpio,
    ningún tramo del video final pasa más de recurso_hueco_max_s sin un recurso que se vea (imagen, clip, panel o texto grande
    ≥ 70 px; el subtítulo no cuenta). El ritmo (máx. de entradas por ventana) sigue mandando para no saturar."""
    tope = r.get("recurso_hueco_max_s")
    if not tope or not palabras:
        return []
    from . import camara

    def visible(e):
        if e.get("tipo") in ("texto", "etiqueta"):
            l0 = (e.get("lineas") or [{}])[0]
            tam = l0.get("tam", 0) if isinstance(l0, dict) else (l0[1] if isinstance(l0, list) and len(l0) > 1 else 0)
            return tam >= 70
        return e.get("tipo") not in ("pixeles", "destello")
    iv = sorted((camara.salida(sb, e["t0"]), camara.salida(sb, e.get("t1", e["t0"]))) for e in sb.get("elementos", [])
                if isinstance(e, dict) and "t0" in e and visible(e))
    fin = camara.salida(sb, palabras[-1]["e"] + .6)
    hasta, peor = float(r.get("inicio_limpio_s") or 0), (0.0, 0.0)
    for a, b in iv + [(fin, fin)]:
        if a - hasta > peor[1] - peor[0]:
            peor = (hasta, a)
        hasta = max(hasta, b)
    if peor[1] - peor[0] > tope + 1e-6:
        return [f"recursos: {peor[1] - peor[0]:.1f} s sin ningún recurso en pantalla (segundos {peor[0]:.1f}–{peor[1]:.1f} del video; "
                f"máx. {tope} s): pon un apoyo literal de lo que se dice (imagen, clip o texto grande); el subtítulo solo no cuenta"]
    return []


def _visibles(sb: dict) -> list:
    """[(t0, t1, clave)] de todo lo que se ve además del subtítulo: elementos (un grupo = una sola cosa, p. ej. tarjeta + su texto) y trazos."""
    out = []
    for i, e in enumerate(sb.get("elementos", [])):
        if isinstance(e, dict) and _num(e.get("t0")):
            out.append((e["t0"], e.get("t1", e["t0"] + 1), e.get("grupo") or f"elemento:{e.get('id', i)}"))
    for i, z in enumerate(sb.get("trazos", [])):
        if isinstance(z, dict) and _num(z.get("t0")):
            out.append((z["t0"], z.get("t1", z["t0"] + z.get("dur", 1)), f"trazo:{z.get('id', i)}"))
    return out


def _una_cosa_a_la_vez(sb: dict, r: dict) -> list:
    """«Una sola cosa en pantalla» (Pablo): como máximo `elementos_a_la_vez_max` cosas visibles a la vez además del subtítulo (reglas.json).
    Una tarjeta y su texto (mismo `grupo`) cuentan como una. Mismos intervalos t0..t1 que ve el ojo."""
    tope = r.get("elementos_a_la_vez_max")
    vis = _visibles(sb)
    if tope is None or not vis:
        return []
    cortes = sorted({x for a, b, _ in vis for x in (a, b)})
    malos = []
    for a, b in zip(cortes, cortes[1:]):
        if b - a < .05:
            continue
        m = (a + b) / 2
        vivos = sorted({k for s, e, k in vis if s <= m < e})
        if len(vivos) > tope:
            malos.append((a, b, vivos))
    if not malos:
        return []
    a, b, vivos = malos[0]
    return [f"una cosa: {len(malos)} tramos con más de {tope} cosa(s) a la vez en pantalla; el primero entre los segundos {a:.1f} y {b:.1f}: "
            f"{', '.join(vivos)}. Una a la vez (la tarjeta y su texto son un solo `grupo`)"]


VIDRIO_VACIO_MAX_S = .3   # una tarjeta de vidrio puede estar vacía este rato (entra un instante antes que su texto); más es una cápsula vacía


def _vidrio_vacio(sb: dict) -> list:
    """Ninguna tarjeta de vidrio sin texto ni contenido: en todo su t0..t1 debe haber otro elemento de su `grupo` o con su centro dentro de ella."""
    els = [e for e in sb.get("elementos", []) if isinstance(e, dict) and _num(e.get("t0"))]
    err = []
    for v in els:
        if v.get("tipo") != "vidrio":
            continue
        a, b = v["t0"], v.get("t1", v["t0"] + 1)
        x, y, w, h = v.get("x", 540), v.get("y", 960), v.get("ancho", 800), v.get("alto", 200)
        dentro = [(e["t0"], e.get("t1", e["t0"] + 1)) for e in els if e is not v and e.get("tipo") != "vidrio" and (
            (v.get("grupo") and e.get("grupo") == v["grupo"]) or (abs(e.get("x", 540) - x) <= w / 2 and abs(e.get("y", 960) - y) <= h / 2))]
        t = a
        for s, e in sorted(dentro):
            if s > t + VIDRIO_VACIO_MAX_S:
                break
            t = max(t, e)
        if t < b - VIDRIO_VACIO_MAX_S:
            err.append(f"vidrio vacío: «{v.get('id')}» queda sin texto ni contenido desde el segundo {t:.1f} hasta el {b:.1f}; ponle su texto o quítalo")
    return err


def _camara_viva(sb: dict, r: dict, palabras, densidad: str) -> list:
    """Regla única de cámara (perfil/reglas.json, nota «Cámara»): el viaje continuo lo hace el motor; los golpes de zoom (`punch`) son POCOS y de
    la palabra más fuerte: la compuerta solo pone el TECHO (`punch_max_por_min`, el mismo número para los 13); nunca exige un mínimo."""
    tope = r.get("punch_max_por_min")
    if not tope or not palabras:
        return []
    from . import camara
    dur = camara.salida(sb, palabras[-1]["e"] + .6)
    hay = len([t for t in sb.get("punch", []) if _num(t)])
    if hay > tope * max(dur, 1.0) / 60 + 1e-9 and hay > 1:
        return [f"cámara viva: {hay} golpes de zoom (`punch`) en {dur:.0f} s; el máximo es {tope} por minuto: deja solo los de la palabra más fuerte"]
    return []


def _texto_siempre(sb: dict, r: dict, palabras) -> list:
    """Pablo (04-nov, todos los estilos, también light): «siempre debe haber movimiento de textos. Siempre aparece el texto
    sea animación sea subtítulo… no puede quedarse quieto sin ningún tipo de elementos porque se mata el ritmo».
    En el video final, ningún tramo sin subtítulo ni texto en pantalla dura más de texto_siempre_max_s."""
    tope = r.get("texto_siempre_max_s")
    if not tope or not palabras:
        return []
    from . import camara, motor
    trozos = [(a, b) for a, b, _, _ in motor.tramos_subtitulo(sb.get("subtitulos", {}), palabras)]
    trozos += [(e["t0"], e.get("t1", e["t0"])) for e in sb.get("elementos", [])
               if isinstance(e, dict) and e.get("tipo") in ("texto", "etiqueta", "contador") and "t0" in e]
    fin = camara.salida(sb, palabras[-1]["e"] + .6)
    hasta, peor = 0.0, (0.0, 0.0)
    for a, b in sorted((camara.salida(sb, a), camara.salida(sb, b)) for a, b in trozos) + [(fin, fin)]:
        if a - hasta > peor[1] - peor[0]:
            peor = (hasta, a)
        hasta = max(hasta, b)
    if peor[1] - peor[0] > tope + 1e-6:
        return [f"texto siempre: {peor[1] - peor[0]:.1f} s sin ningún texto en pantalla (segundos {peor[0]:.1f}–{peor[1]:.1f} del video; "
                f"máx. {tope} s): no ocultes el subtítulo ahí o pon un texto animado; el video nunca se queda quieto"]
    return []


_VACIAS = {"que", "con", "los", "las", "del", "una", "uno", "por", "para", "como", "este", "esta", "esto", "eso", "pero", "más",
           "mas", "muy", "tus", "sus", "mis", "les", "nos", "hay", "son", "fue", "era", "the", "and", "you"}


def _norma_txt(t: str) -> str:
    import unicodedata
    t = unicodedata.normalize("NFKD", str(t).lower())
    return re.sub(r"[^a-z0-9ñ ]", " ", "".join(c for c in t if not unicodedata.combining(c)))


def _texto_elemento(e: dict) -> str:
    out = []
    for l in e.get("lineas") or []:
        out.append(l.get("texto", "") if isinstance(l, dict) else (l[0] if isinstance(l, list) and l else str(l)))
    return " ".join(str(x) for x in out)


def duplicados(sb: dict, palabras) -> list:
    """Pablo (07-nov): «pone el texto animado y además el subtítulo normal con la misma palabra»: [(t0, t1, subtítulo, texto)] de
    cada bloque de subtítulo (segundos de la fuente) que se ve mientras un texto en pantalla ya muestra sus palabras. Cuenta
    como repetido: una palabra con contenido en común (≥ 3 letras y no vacía), dos palabras cualesquiera en común, o la palabra
    escrita con letras separadas («T A L L E R»). «Con contenido» = 3 o más letras y no vacía."""
    if not palabras:
        return []
    from . import motor
    textos = []
    for e in sb.get("elementos", []):
        if isinstance(e, dict) and e.get("tipo") in ("texto", "etiqueta", "contador") and "t0" in e:
            n = _norma_txt(_texto_elemento(e))
            textos.append((e["t0"], e.get("t1", e["t0"]), set(n.split()), n.replace(" ", ""), _texto_elemento(e)))
    out = []
    for t0, t1, i0, i1 in motor.tramos_subtitulo(sb.get("subtitulos", {}), palabras):
        sub = [w for w in _norma_txt(" ".join(p["w"] for p in palabras[i0:i1])).split() if w]
        for a, b, ws, pegado, crudo in textos:
            if min(b, t1) - max(a, t0) <= .1:
                continue
            comunes = set(sub) & ws
            # «vez» bajo «cada vez» también es repetido (Cine, 07-nov): cuenta toda palabra de 3+ letras que no sea vacía
            llenas = [w for w in sub if len(w) >= 3 and w not in _VACIAS and (w in ws or (len(w) >= 4 and w in pegado))]
            if llenas or len(comunes) >= 2:
                out.append((t0, t1, " ".join(p["w"] for p in palabras[i0:i1]), crudo))
                break
    return out


def _sin_duplicado(sb: dict, palabras) -> list:
    return [f"texto duplicado: el subtítulo «{s}» (segundo {t0:.1f} de la fuente) repite «{x[:40]}» que ya está en pantalla: "
            f"ocúltalo en subtitulos.ocultar (el texto ya lo dice)" for t0, _, s, x in duplicados(sb, palabras)]


def _sujeto(sb: dict, r: dict) -> list:
    """Pablo: «nunca nunca pongas el sujeto recortado». Ni modos de recorte, ni texto detrás de la persona sobre su toma."""
    if not r.get("sujeto_recortado_prohibido"):
        return []
    err, escenas = [], sorted((e for e in sb.get("escenas", []) if isinstance(e, dict) and "t0" in e), key=lambda e: e["t0"])
    for i, e in enumerate(escenas):
        modo = (e.get("persona") or {}).get("modo", "completa")
        if modo not in MODOS["pantalla"]:
            err.append(f"escenas[{i}]: persona.modo {modo!r} = sujeto recortado, prohibido por Pablo (la persona va en su toma completa)")
    for i, el in enumerate(sb.get("elementos", [])):
        if isinstance(el, dict) and el.get("z") == "atras" and el.get("tipo") in ("texto", "etiqueta", "pixeles", "destello"):
            esc = ([e for e in escenas if e["t0"] <= el.get("t0", 0) + 1e-6] or [{}])[-1]
            if (esc.get("persona") or {}).get("modo", "completa") == "completa":
                err.append(f"elementos[{i}] «{el.get('id', '')}»: va detrás de la persona sobre su toma, y a la persona no se la recorta: ponlo delante o en un apoyo")
    return err


def errores_acercar(d: dict) -> list:
    """C-0003: `acercar` (Ken Burns de un apoyo) solo en foto, recorte o clip, hasta ACERCAR_MAX y sin pasar .004 de zoom por cuadro."""
    ac = d.get("acercar")
    if ac is None:
        return []
    if d.get("tipo") not in ("foto", "recorte", "clip") or not _num(ac) or not 0 < ac <= efectos.ACERCAR_MAX:
        return [f"acercar: número entre 0 y {efectos.ACERCAR_MAX}, solo en foto, recorte o clip"]
    vida = (d.get("t1", 0) - d.get("t0", 0)) if _num(d.get("t1")) and _num(d.get("t0")) else 0
    if vida <= 0 or ac * 1.5 / (vida * 30) > .004:   # 1,5 = pendiente máxima del smoothstep
        return [f"acercar {ac}: brinco (más de .004 de zoom por cuadro en {vida:.2f} s); menos acercar o más vida"]
    return []


def _variedad(sb: dict, r: dict, rep: dict | None = None) -> list:
    """Pablo: «usas un movimiento de cámara o texto o imagen o B-roll similar… en todo el video». Se mide por categoría.
    Si Pablo eligió en el seleccionador menos opciones que `min_tipos` para una categoría, su elección manda: ahí no se exige
    cuántos tipos ni la proporción (sería imposible); con 2 o más se sigue pidiendo alternar."""
    v = r.get("variedad")
    if not v:
        return []
    rep = rep or {}
    escenas = sorted((e for e in sb.get("escenas", []) if isinstance(e, dict) and "t0" in e), key=lambda e: e["t0"])
    els = sorted((e for e in sb.get("elementos", []) if isinstance(e, dict) and "t0" in e), key=lambda e: e["t0"])
    cat = {
        "transición entre escenas": [e.get("entrada", "corte") for e in escenas[1:]],
        "entrada de texto": [e.get("entra", "pop") for e in els if e.get("tipo") == "texto" and (e.get("lineas") or [{}])[0].get("tam", 0) >= 90],
        "tratamiento de apoyo": [("fundida" if e.get("fundir") else "pantalla completa" if e.get("cubrir") else "caja" if e.get("caja")
                                  else "recorte" if e.get("tipo") == "recorte" else "con borde") + ("+" + e["fusion"] if e.get("fusion") else "")
                                 + ("·" + e["tratamiento"] if e.get("tratamiento") else "")
                                 for e in els if e.get("tipo") in ("foto", "recorte", "clip")],
    }
    elegidas = {"transición entre escenas": len(rep["transiciones"] | {"corte"}) if "transiciones" in rep else None,
                "entrada de texto": len(rep["entradas"]) if "entradas" in rep else None,
                "tratamiento de apoyo": len(rep["tratamientos"]) + 1 if "tratamientos" in rep else None}   # + la foto sin tratamiento
    err = []
    for nombre, seq in cat.items():
        if len(seq) < 4:
            continue
        n = elegidas.get(nombre)
        pocas = n is not None and n < v.get("min_tipos", 3)
        if pocas and n <= 1:
            continue
        racha, peor = 1, (1, seq[0])
        for a, b in zip(seq, seq[1:]):
            racha = racha + 1 if a == b else 1
            peor = max(peor, (racha, b))
        if peor[0] > v.get("max_mismo_seguido", 2):
            err.append(f"variedad ({nombre}): «{peor[1]}» {peor[0]} veces seguidas (máx. {v['max_mismo_seguido']}): alterna con otras")
        if pocas:
            continue
        top = max(set(seq), key=seq.count)
        if seq.count(top) / len(seq) > v.get("max_proporcion", .45) and len(set(seq)) < len(seq):
            err.append(f"variedad ({nombre}): «{top}» es el {seq.count(top) / len(seq):.0%} de las veces (máx. {v['max_proporcion']:.0%})")
        if len(set(seq)) < min(v.get("min_tipos", 3), len(seq)):
            err.append(f"variedad ({nombre}): solo {len(set(seq))} tipos distintos en todo el video (mín. {v.get('min_tipos', 3)})")
    return err


APOYO_CLAVES = ("fundir", "cubrir", "caja", "acercar", "luz")   # claves de un apoyo que son un tratamiento por sí solas
REPERTORIO_NOMBRES = {"transiciones": "transiciones", "entradas": "entradas de texto", "tratamientos": "tratamientos de imagen",
                      "fondos": "fondos de muro", "filtros": "efectos de color", "trazos": "trazos", "recursos": "cajas, etiquetas y datos",
                      "textos": "tipos de texto", "hooks": "tipos de hook"}
# Tipos de texto (seleccionador): cómo se dibuja un texto. El texto lleno, recto y plano siempre se puede (es no poner nada).
ESTILOS_TEXTO = {"hueca": "letra hueca (contorno)", "borde": "relleno con borde (trazo)", "extrusion": "bloque 3D (extrusión)",
                 "estirada": "palabra estirada en vertical (escala_y)", "italica": "cursiva", "fina": "peso fino (400 o menos)",
                 "luz": "texto de luz", "tecleo": "tecleo con cursor"}
# Recursos (seleccionador): piezas que no son texto ni apoyo. El destello queda fuera: está prohibido en las reglas de Pablo.
RECURSOS = {"etiqueta": "etiqueta recta", "etiqueta-redondeada": "etiqueta redondeada", "vidrio": "panel de vidrio",
            "panel": "pantalla de luz", "caja-hud": "marco HUD que sigue a la persona", "contador": "cifra que cuenta",
            "barra": "barra que crece", "barra-horizontal": "barra horizontal", "pixeles": "bloques de píxeles"}


def estilos_texto_de(d: dict) -> list:
    """Los tipos de texto (ids de ESTILOS_TEXTO) que usa un `texto` o una `etiqueta` (sus líneas van como [texto, tam, cursiva, peso])."""
    out = set()
    for ln in d.get("lineas") or []:
        if isinstance(ln, (list, tuple)):
            if len(ln) > 2 and ln[2] is True:
                out.add("italica")
            if len(ln) > 3 and _num(ln[3]) and ln[3] <= 400:
                out.add("fina")
            continue
        if not isinstance(ln, dict):
            continue
        for clave, tid in (("contorno", "hueca"), ("trazo", "borde"), ("extrusion", "extrusion"), ("italica", "italica")):
            if ln.get(clave):
                out.add(tid)
        if _num(ln.get("escala_y")) and ln["escala_y"] > 1:
            out.add("estirada")
        if _num(ln.get("peso")) and ln["peso"] <= 400:
            out.add("fina")
    if d.get("tipo") == "texto" and d.get("luz"):
        out.add("luz")
    if d.get("tecleo"):
        out.add("tecleo")
    return sorted(out)


def recurso_de(d: dict) -> str | None:
    """El id de RECURSOS de un elemento (None si es texto, apoyo o algo que no se elige en el seleccionador)."""
    t = d.get("tipo")
    if t == "etiqueta":
        return "etiqueta-redondeada" if _num(d.get("radio")) and d["radio"] > 0 else "etiqueta"
    if t == "barra":
        return "barra-horizontal" if d.get("direccion") == "horizontal" else "barra"
    return t if t in RECURSOS else None


def repertorio(carpeta) -> dict:
    """Lo que Pablo eligió en el seleccionador para ESTE video (`preferencias.json › repertorio`): {categoría: {ids}}.
    Sin archivo, sin `repertorio` o con la categoría vacía = libertad total en esa categoría."""
    f = Path(carpeta) / "preferencias.json" if carpeta else None
    if not f or not f.exists():
        return {}
    try:
        rep = json.loads(f.read_text()).get("repertorio") or {}
    except (ValueError, AttributeError):
        return {}
    return {k: {str(x) for x in v} for k, v in rep.items() if k in REPERTORIO_NOMBRES and isinstance(v, list) and v}


def tratamientos_de(d: dict) -> list:
    """Los tratamientos que usa un apoyo, con los mismos ids del catálogo (tratamiento:bn, fusion:pantalla, fundir…)."""
    out = [f"tratamiento:{d['tratamiento']}"] if d.get("tratamiento") else []
    out += [f"fusion:{d['fusion']}"] if d.get("fusion") else []
    return out + [k for k in APOYO_CLAVES if d.get(k)]


def _repertorio(sb: dict, rep: dict) -> list:
    """Compuerta del seleccionador: en una categoría que Pablo eligió, nada fuera de lo elegido (no obliga a usarlo todo).
    El corte seco y la foto sin tratamiento siempre se pueden: son no poner nada."""
    if not rep:
        return []
    err = []

    def fuera(cat, usado, donde):
        if cat in rep and usado not in rep[cat]:
            err.append(f"{donde}: «{usado}» no está entre las {REPERTORIO_NOMBRES[cat]} que Pablo eligió para este video "
                       f"({', '.join(sorted(rep[cat]))}); usa una de esas o ninguna")
    for i, e in enumerate(sb.get("escenas") or []):
        if not isinstance(e, dict):
            continue
        if e.get("entrada", "corte") != "corte":
            fuera("transiciones", e["entrada"], f"escenas[{i}].entrada")
        fondo = (e.get("persona") or {}).get("fondo") if isinstance(e.get("persona"), dict) else None
        if fondo in efectos.MUROS:
            fuera("fondos", fondo, f"escenas[{i}].persona.fondo")
        if e.get("filtro", "ninguno") != "ninguno":
            fuera("filtros", e["filtro"], f"escenas[{i}].filtro")
        for j, f in enumerate(e.get("franjas") or []):
            if isinstance(f, dict) and f.get("filtro", "ninguno") != "ninguno":
                fuera("filtros", f["filtro"], f"escenas[{i}].franjas[{j}].filtro")
    for i, d in enumerate(sb.get("elementos") or []):
        if not isinstance(d, dict):
            continue
        donde = f"elementos[{i}]" + (f" «{d.get('id')}»" if d.get("id") else "")
        if d.get("tipo") in ("texto", "etiqueta"):
            fuera("entradas", d.get("entra", "pop"), donde + ".entra" + ("" if "entra" in d else " (sin «entra» es «pop»)"))
            for t in estilos_texto_de(d):
                fuera("textos", t, donde)
        if d.get("tipo") in ("foto", "recorte", "clip"):
            for t in tratamientos_de(d):
                fuera("tratamientos", t, donde)
        if recurso_de(d):
            fuera("recursos", recurso_de(d), donde)
    for i, t in enumerate(sb.get("trazos") or []):
        if isinstance(t, dict) and t.get("tipo"):
            fuera("trazos", t["tipo"], f"trazos[{i}]")
    if sb.get("cajas"):
        fuera("recursos", "caja-hud", "cajas")
    return err


def _apoyo_literal(sb: dict, r: dict, palabras) -> list:
    """Pablo: «si dice "carpeta"… debería mostrar eso». Cada apoyo declara `muestra` y esa palabra se dice en ese momento."""
    ventana = r.get("apoyo_literal_ventana_s")
    if not ventana or palabras is None:
        return []
    import unicodedata

    def n(t):
        t = unicodedata.normalize("NFKD", str(t).lower())
        return re.sub(r"[^a-z0-9ñ ]", "", "".join(c for c in t if not unicodedata.combining(c)))
    err = []
    for i, el in enumerate(sb.get("elementos", [])):
        if not isinstance(el, dict) or el.get("tipo") not in ("foto", "recorte", "clip") or not el.get("src"):
            continue
        q = n(el.get("muestra", ""))
        if not q:
            err.append(f"elementos[{i}] «{el.get('id', '')}»: todo apoyo declara `muestra` (la palabra dicha que ilustra, literal)")
            continue
        dichas = [n(p["w"]) for p in palabras if el["t0"] + ventana[0] <= p["s"] <= el["t0"] + ventana[1]]
        from difflib import SequenceMatcher   # tolera errores de oído de la transcripción («Cloud» por Claude, «WORSHOP»)
        parecida = lambda a, b: a[:5] in b or b[:5] in a or SequenceMatcher(None, a, b).ratio() >= .7  # noqa: E731
        if not any(parecida(w, d) for w in q.split() if len(w) >= 3 for d in dichas if len(d) >= 3):
            err.append(f"elementos[{i}] «{el.get('id', '')}»: muestra «{el.get('muestra')}» pero eso no se dice entre "
                       f"{el['t0'] + ventana[0]:.1f} y {el['t0'] + ventana[1]:.1f} s: el apoyo tiene que ser literal a lo que se dice")
    return err


def _linea_minima(sb: dict, r: dict) -> list:
    """Piso de legibilidad (Pablo 10-nov: «se están creando palabras muy pequeñas… en el b-roll»): ninguna línea de texto, etiqueta o contador baja de
    `texto_linea_min_px` (reglas.json, el mismo para los 13). Con 48 px una mayúscula mide ~35 px de alto: ~2,3 mm en un celular de 6,1 pulgadas."""
    m = r.get("texto_linea_min_px")
    if not m:
        return []
    chicas = []
    for e in sb.get("elementos", []):
        if not isinstance(e, dict):
            continue
        if e.get("tipo") in ("texto", "etiqueta"):
            for l in e.get("lineas", []):
                t = l.get("tam") if isinstance(l, dict) else (l[1] if isinstance(l, list) and len(l) > 1 else None)
                if isinstance(t, (int, float)) and t < m:
                    chicas.append((e.get("id", ""), t))
        elif e.get("tipo") == "contador" and isinstance(e.get("tam", 160), (int, float)) and e.get("tam", 160) < m:
            chicas.append((e.get("id", ""), e["tam"]))
    if chicas:
        return [f"texto: {len(chicas)} línea(s) bajo el mínimo legible de {m} px (p. ej. «{chicas[0][0]}» a {chicas[0][1]} px): súbelas a {m} px"]
    return []


def _linea_principal_px(sb: dict, a: float, b: float, est) -> float | None:
    """Ancho (px) de la línea de texto más ancha de la escena [a, b) que se ve de una vez: los textos de la misma altura que están a la vez en pantalla
    cuentan como UNA línea (una frase que se arma palabra a palabra). Sin las etiquetas mono; None si la escena no tiene texto principal."""
    from . import motor
    ext = []
    for e in sb.get("elementos", []):
        if not isinstance(e, dict) or e.get("tipo") not in ("texto", "etiqueta") or not (a - 1e-6 <= e.get("t0", -1) < b):
            continue
        roles = [(l.get("rol") if isinstance(l, dict) else e.get("rol")) for l in e.get("lineas", [])]
        if not roles or all(x == "mono" for x in roles):
            continue
        try:
            w = motor.Elemento({**e, "luz": False}, est, Path(".")).img.size[0] - 60
        except Exception:  # noqa: BLE001 — lo que no se puede dibujar ya lo dice _medir_texto
            continue
        ext.append((e["t0"], e.get("t1", e["t0"] + 1), e.get("y", 960), e.get("x", 540) - w / 2, e.get("x", 540) + w / 2))
    if not ext:
        return None
    mejor = 0.0
    for t in sorted({x[0] for x in ext}):
        vivos = [x for x in ext if x[0] <= t + 1e-6 < x[1]]
        for y in {x[2] for x in vivos}:
            fila = [x for x in vivos if abs(x[2] - y) <= 14]
            mejor = max(mejor, max(x[4] for x in fila) - min(x[3] for x in fila))
    return mejor


def _pantalla_principal(sb: dict, r: dict) -> list:
    """Pantalla completa o fondo sólido (escena sin la persona): la palabra o frase principal tiene que DOMINAR el cuadro: su línea más ancha ocupa al
    menos `pantalla_principal_ancho_min` (reglas.json, fracción) del ancho del cuadro."""
    frac = r.get("pantalla_principal_ancho_min")
    if not frac:
        return []
    from . import motor
    escenas = sorted((e for e in sb.get("escenas", []) if isinstance(e, dict) and _num(e.get("t0"))), key=lambda e: e["t0"])
    try:
        est = motor.Estilo(sb.get("estilo") or {})
    except Exception:  # noqa: BLE001 — un estilo mal formado ya lo reportan las reglas del bloque `estilo`
        return []
    err = []
    for k, esc in enumerate(escenas):
        if (esc.get("persona") or {}).get("modo") != "oculta":
            continue
        a, b = esc["t0"], escenas[k + 1]["t0"] if k + 1 < len(escenas) else 1e9
        w = _linea_principal_px(sb, a, b, est)
        if w is not None and w < frac * W:
            err.append(f"pantalla completa (segundo {a:.1f}): la palabra o frase principal ocupa {w / W:.0%} del ancho; tiene que dominar el cuadro "
                       f"(mínimo {frac:.0%}): agrándala o júntala en una sola línea")
    return err


def _color_toma(sb: dict, r: dict, fin) -> list:
    """Regla de Pablo: el color de su toma no se cambia en todo el video; un filtro sobre la toma real es solo un golpe puntual."""
    if not r.get("color_toma_intocable"):
        return []
    err = []
    est = sb.get("estilo") or {}
    if est.get("filtro", "ninguno") != "ninguno":
        err.append(f"estilo.filtro = {est['filtro']!r}: el color de la toma de Pablo no se cambia en todo el video (solo golpes puntuales)")
    if (est.get("bloom") or 0) > .5:
        err.append("estilo.bloom > 0,5: el brillo se come la toma de Pablo; el bloom solo abre halo en las luces de verdad (máx. 0,5)")
    escenas = sorted((e for e in sb.get("escenas", []) if isinstance(e, dict) and "t0" in e), key=lambda e: e["t0"])
    maximo = float(r.get("filtro_max_s") or 1.5)
    for i, e in enumerate(escenas):
        if e.get("filtro", "ninguno") == "ninguno" or (e.get("persona") or {}).get("modo") == "oculta":
            continue
        hasta = escenas[i + 1]["t0"] if i + 1 < len(escenas) else (fin or e["t0"] + 99)
        cortado = sum(max(0, min(b, hasta) - max(a, e["t0"])) for a, b in sb.get("cortes", []))
        dur = hasta - e["t0"] - cortado
        if dur > maximo:
            err.append(f"escenas[{i}].filtro {e['filtro']!r} dura {dur:.1f} s sobre la toma de Pablo: máx. {maximo} s (efecto puntual)")
    return err


def _color_base(v, donde, err, prohibidos=()):
    if v in NOMBRES_COLOR:
        return
    if not isinstance(v, str) or not _HEX.match(v):
        err.append(f"{donde}: color {v!r} no existe (usa {', '.join(sorted(NOMBRES_COLOR))} o #RRGGBB)")
        return
    for familia in prohibidos:
        if FAMILIAS_COLOR.get(familia, lambda _: False)(v):
            err.append(f"{donde}: {v} es {familia}, prohibido por Pablo en este estilo (perfil/reglas.json)")


def _claves(d, tipo, donde, err):
    if not isinstance(d, dict):
        err.append(f"{donde}: debe ser un objeto")
        return False
    sobran = set(d) - CLAVES[tipo]
    if sobran:
        err.append(f"{donde}: el motor no conoce {sorted(sobran)} (permitidas: {sorted(CLAVES[tipo])})")
    return True


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def errores(sb: dict, carpeta: Path | None = None, imagenes_pendientes=False, estilo: str | None = None) -> list:
    err = []
    estilo = estilo or (sb.get("estilo") or {}).get("id") if isinstance(sb, dict) else estilo
    prohibidos = reglas(estilo)["colores_prohibidos"]

    def _color(v, donde, err):
        _color_base(v, donde, err, prohibidos)
    if not _claves(sb, "raiz", "storyboard", err):
        return err
    indice = json.loads((config.FUENTES / "indice.json").read_text())
    est = sb.get("estilo", {})
    if _claves(est, "estilo", "estilo", err):
        for k in ("acento", "acento2", "tinta", "papel", "borde"):
            if k in est:
                _color(est[k], f"estilo.{k}", err)
        for k in ("fuente", "fuente_script", "fuente_mono"):
            if k in est and est[k] not in indice:
                err.append(f"estilo.{k}: la fuente {est[k]!r} no está instalada (instálala con `uv run estudio fuentes instalar \"{est[k]}\"`)")
        if est.get("base", "pantalla") not in BASES:
            err.append(f"estilo.base: {est.get('base')!r} no existe (hay: {sorted(BASES)})")
        if est.get("subtitulo", "tira") not in SUBTITULOS:
            err.append(f"estilo.subtitulo: {est.get('subtitulo')!r} no existe (hay: {sorted(SUBTITULOS)})")
        err.extend(f"estilo.{m}" for m in subtitulo_opciones.errores(est))   # sub_*: UNA validación para todos los tipos
        if est.get("filtro", "ninguno") not in efectos.FILTROS:
            err.append(f"estilo.filtro: {est.get('filtro')!r} no existe (hay: {', '.join(efectos.FILTROS)})")
    base = est.get("base", "pantalla") if isinstance(est, dict) and est.get("base", "pantalla") in BASES else "pantalla"

    palabras = None
    if carpeta and (Path(carpeta) / "palabras.json").exists():
        palabras = json.loads((Path(carpeta) / "palabras.json").read_text())
    fin = palabras[-1]["e"] + 1 if palabras else None

    escenas = sb.get("escenas")
    if not isinstance(escenas, list) or not escenas:
        err.append("escenas: hace falta al menos una escena")
        escenas = []
    t0s = []
    for i, e in enumerate(escenas):
        donde = f"escenas[{i}]"
        if not _claves(e, "escena", donde, err):
            continue
        if not _num(e.get("t0")):
            err.append(f"{donde}: falta t0 (número)")
        else:
            t0s.append(e["t0"])
        if e.get("filtro", "ninguno") not in efectos.FILTROS:
            err.append(f"{donde}.filtro: {e['filtro']!r} no existe (hay: {', '.join(efectos.FILTROS)})")
        if base != "pantalla" and ("filtro" in e or "franjas" in e or "entrada" in e):
            err.append(f"{donde}: filtro/franjas/entrada solo existen en la base «pantalla»")
        if e.get("camara") and e["camara"] not in CAMARAS:
            err.append(f"{donde}.camara: {e['camara']!r} no existe (hay: {sorted(CAMARAS)})")
        if e.get("entrada", "corte") not in ENTRADAS_ESCENA:
            err.append(f"{donde}.entrada: {e['entrada']!r} no existe (hay: {sorted(ENTRADAS_ESCENA)})")
        pe = e.get("persona", {})
        if _claves(pe, "persona", f"{donde}.persona", err):
            if "modo" in pe and pe["modo"] not in MODOS[base]:
                err.append(f"{donde}.persona.modo: {pe['modo']!r} no existe en la base {base} (hay: {sorted(MODOS[base])})")
            for k in ("fondo", "contorno", "color"):
                if k in pe and not (k == "fondo" and pe[k] in efectos.MUROS):
                    _color(pe[k], f"{donde}.persona.{k}", err)
            if "escala" in pe and not (_num(pe["escala"]) and .3 <= pe["escala"] <= 1.3):
                err.append(f"{donde}.persona.escala: debe estar entre 0,3 y 1,3")
        fr = e.get("franjas")
        if fr is not None:
            if not isinstance(fr, list) or not 2 <= len(fr) <= 4:
                err.append(f"{donde}.franjas: van de 2 a 4")
            else:
                for j, f in enumerate(fr):
                    if _claves(f, "franja", f"{donde}.franjas[{j}]", err) and f.get("filtro", "ninguno") not in efectos.FILTROS:
                        err.append(f"{donde}.franjas[{j}].filtro: {f['filtro']!r} no existe")
    if t0s != sorted(t0s):
        err.append("escenas: los t0 deben ir en orden")

    ids = set()
    for i, d in enumerate(sb.get("elementos", [])):
        donde = f"elementos[{i}]" + (f" «{d.get('id')}»" if isinstance(d, dict) and d.get("id") else "")
        if not _claves(d, "elemento", donde, err):
            continue
        tipo = d.get("tipo")
        if tipo not in TIPOS_ELEMENTO:
            err.append(f"{donde}: tipo {tipo!r} no existe (hay: {sorted(TIPOS_ELEMENTO)})")
            continue
        err += [f"{donde}: {m}" for m in errores_acercar(d)]
        if d.get("id"):
            if d["id"] in ids:
                err.append(f"{donde}: id repetido")
            ids.add(d["id"])
        for k in ("x", "y", "t0", "t1"):
            if not _num(d.get(k)):
                err.append(f"{donde}: falta {k} (número)")
        if _num(d.get("t0")) and _num(d.get("t1")) and d["t1"] <= d["t0"]:
            err.append(f"{donde}: t1 debe ser mayor que t0")
        if d.get("entra", "pop") not in ENTRADAS:
            err.append(f"{donde}.entra: {d['entra']!r} no existe (hay: {sorted(ENTRADAS)})")
        if d.get("z", "frente") not in ("atras", "frente"):
            err.append(f"{donde}.z: solo «atras» o «frente»")
        if tipo == "clip":   # como la foto: mientras el arte está pedido (arte.json) el archivo todavía no existe
            if not d.get("src"):
                err.append(f"{donde}: clip necesita src")
            elif carpeta and not imagenes_pendientes and not (Path(carpeta) / d["src"]).exists():
                err.append(f"{donde}: el clip {d['src']} no existe")
        if tipo in ("foto", "recorte"):
            if not d.get("src") or not (_num(d.get("ancho")) or d.get("cubrir")):  # (fundir requiere ancho)
                err.append(f"{donde}: {tipo} necesita src y ancho")
            elif carpeta and not imagenes_pendientes and not (Path(carpeta) / d["src"]).exists():
                err.append(f"{donde}: la imagen {d['src']} no existe")
        if tipo == "texto":
            for j, l in enumerate(d.get("lineas") or []):
                if _claves(l, "linea_texto", f"{donde}.lineas[{j}]", err):
                    if l.get("rol", "display") not in ROLES:
                        err.append(f"{donde}.lineas[{j}].rol: {l['rol']!r} no existe (hay: {sorted(ROLES)})")
                    _color(l.get("color", "blanco"), f"{donde}.lineas[{j}].color", err)
        if tipo == "etiqueta":
            for k in ("fondo", "letra"):
                if k in d:
                    _color(d[k], f"{donde}.{k}", err)
            if d.get("rol") and d["rol"] not in ROLES:
                err.append(f"{donde}.rol: {d['rol']!r} no existe (hay: {sorted(ROLES)})")
        if tipo == "texto":
            for j, l in enumerate(d.get("lineas") or []):
                if isinstance(l, dict):
                    for k in ("trazo", "extrusion"):
                        if k in l and not (isinstance(l[k], list) and len(l[k]) == 2 and _num(l[k][0])):
                            err.append(f"{donde}.lineas[{j}].{k}: va como [px, color]")
                        elif k in l:
                            _color(l[k][1], f"{donde}.lineas[{j}].{k}", err)
        if tipo == "pixeles":
            for c in d.get("colores", []):
                _color(c, f"{donde}.colores", err)
        if tipo in ("texto", "etiqueta") and not err_en(err, donde):
            err += _medir_texto(d, est, donde, _margen_camara(sb, d.get("t0", 0), d.get("t1")))

    for i, d in enumerate(sb.get("trazos", [])):
        donde = f"trazos[{i}]"
        if not _claves(d, "trazo", donde, err):
            continue
        if d.get("tipo") not in TIPOS_TRAZO:
            err.append(f"{donde}: tipo {d.get('tipo')!r} no existe (hay: {sorted(TIPOS_TRAZO)})")
        if d.get("tipo") == "rect" and d.get("sobre") not in ids:
            err.append(f"{donde}: «sobre» debe ser el id de un elemento ({d.get('sobre')!r} no existe)")
        if d.get("tipo") == "elipse" and not (d.get("centro") and d.get("radio")):
            err.append(f"{donde}: la elipse necesita centro y radio")
        if d.get("tipo") == "elipse" and d.get("sobre") and d["sobre"] not in ids:
            err.append(f"{donde}: «sobre» {d['sobre']!r} no es el id de un elemento")

    for i, d in enumerate(sb.get("cajas", [])):
        donde = f"cajas[{i}]"
        if not _claves(d, "caja", donde, err):
            continue
        if base != "pantalla":
            err.append(f"{donde}: las cajas HUD solo existen en la base «pantalla»")
        if not isinstance(d.get("sobre"), list) and d.get("sobre", "cara") not in ("cara", "cuerpo"):
            err.append(f"{donde}.sobre: «cara», «cuerpo» o [x0, y0, x1, y1]")
        if "color" in d:
            _color(d["color"], f"{donde}.color", err)

    sub = sb.get("subtitulos", {})
    if _claves(sub, "subtitulos", "subtitulos", err):
        y = sub.get("y", 1455)
        if not (_num(y) and ZONA_TEXTO[0] <= y <= ZONA_TEXTO[1]):
            err.append(f"subtitulos.y = {y}: debe estar entre {ZONA_TEXTO[0]} y {ZONA_TEXTO[1]} (zona segura de Instagram)")
        if palabras is not None:
            n = len(palabras)
            for a, b in sub.get("bloques", []):
                if not (0 <= a < b <= n):
                    err.append(f"subtitulos.bloques: [{a}, {b}] se sale de las {n} palabras")
            malos = [i for i in sub.get("resaltar", []) if not 0 <= i < n]
            if malos:
                err.append(f"subtitulos.resaltar: índices {malos} no existen")

    r_ = reglas(estilo, densidad_de(carpeta))
    rep = repertorio(carpeta)
    err += _repertorio(sb, rep)
    err += _color_toma(sb, r_, fin) + _sujeto(sb, r_) + _linea_minima(sb, r_) + _pantalla_principal(sb, r_) + _camara_continua(sb, r_.get("camara_cambio_min_s") or 6.0) + _calma_e_integracion(sb, r_) + _texto_en_recorrido(sb, r_) + _paleta_sonido(sb) + _inicio_limpio(sb, r_)
    err += _sin_duplicado(sb, palabras)
    err += _camara_viva(sb, r_, palabras, densidad_de(carpeta)) + _gancho(sb, r_) + _una_cosa_a_la_vez(sb, r_) + _vidrio_vacio(sb)
    if carpeta:
        err += _apoyo_literal(sb, r_, palabras)
    if carpeta and not imagenes_pendientes:
        from . import montaje
        err += montaje.errores(sb, Path(carpeta))
    from . import huella
    err += huella.errores(sb, carpeta, estilo)

    for t in sb.get("punch", []):
        if not _num(t) or (fin and not 0 <= t <= fin):
            err.append(f"punch {t!r}: debe ser un tiempo dentro del video")
    for c in sb.get("cortes", []):
        if not (isinstance(c, list) and len(c) == 2 and all(map(_num, c)) and c[0] < c[1]):
            err.append(f"cortes {c!r}: cada corte es [inicio, fin] con inicio < fin")
    return err


def consejos(sb: dict, carpeta: Path | None = None) -> list:
    """Lo que ANTES bloqueaba y ahora es solo una guía (Pablo 10-nov: «déjalas que Opus decida»): hueco sin recurso, texto siempre en pantalla,
    variedad y ritmo. No frena nada: el director los anota como avisos y decide él."""
    estilo = (sb.get("estilo") or {}).get("id")
    r = reglas(estilo, densidad_de(carpeta) if carpeta else "normal")
    palabras = json.loads((Path(carpeta) / "palabras.json").read_text()) if carpeta and (Path(carpeta) / "palabras.json").exists() else None
    out = _variedad(sb, r, repertorio(carpeta) if carpeta else {}) + _ritmo(sb, r)
    if palabras:
        out += _texto_siempre(sb, r, palabras) + _recursos(sb, r, palabras)
    return out


def err_en(err, donde):
    return any(e.startswith(donde) for e in err)


# zoom sostenido y desplazamiento máximo de cada movimiento de cámara (lo que el motor hace en `cuadro_pantalla`)

def _margen_camara(sb: dict, t: float, t1=None) -> tuple:
    """(mx, my): lo más que se come la cámara en cada borde mientras el texto está en pantalla (zoom + viaje + flotar)."""
    from . import camara
    if camara.fija():   # el cuadro no se mueve ni se recorta: se ve entero
        return (0.0, 0.0)
    r = camara.Ruta(sb)
    fl = 0.0   # la flotación ya va dentro de la ruta
    peor = (0.0, 0.0)
    fin = t if t1 is None else max(t, float(t1))
    k = t
    while True:
        z, dx, dy, _ = r(camara.salida(sb, k))
        m = 1 + (abs(dx) + abs(dy)) * 2 / W + .02
        peor = (max(peor[0], (W - W / (z * m)) / 2 + abs(dx) + fl), max(peor[1], (H - H / (z * m)) / 2 + abs(dy) + fl))
        if k >= fin:
            return peor
        k = min(fin, k + .25)


def _camara_continua(sb: dict, cambio_min_s: float = 6.0) -> list:
    """Pablo (04-nov): la cámara no puede tener brincos ni ir y venir; viaja continua por todo el video."""
    from . import camara
    fin = max([e.get("t1", 0) for e in sb.get("elementos", []) if isinstance(e, dict)]
              + [e.get("t0", 0) for e in sb.get("escenas", []) if isinstance(e, dict)] + [1.0])
    dur = camara.salida(sb, fin)
    for c in sb.get("camara", []) if isinstance(sb.get("camara"), list) else []:
        malas = set(c) - {"t", *camara.CLAVES}
        if malas:
            return [f"camara: claves desconocidas {sorted(malas)} (hay: t, zoom, x, y, rot)"]
    m = camara.saltos(sb, dur)
    err = []
    if m["zoom_por_cuadro"] > .004 or m["px_por_cuadro"] > 4:
        err.append(f"camara: brinco de {m['zoom_por_cuadro']:.4f} de zoom / {m['px_por_cuadro']:.1f} px en un cuadro (máx. .004 / 4 px): keyframes más separados")
    if m["vueltas_zoom"] > max(1, dur / cambio_min_s):
        err.append(f"camara: el zoom cambia de sentido {m['vueltas_zoom']} veces (ir y venir; máx. 1 cada {cambio_min_s} s)")
    return err


def _medir_texto(d, est_d, donde, margen_cam=(0, 0)) -> list:
    """Renderiza el texto o la etiqueta de verdad y mide: nada fuera del lienzo y el texto dentro de la zona segura."""
    from . import motor
    try:
        e = motor.Elemento({**d, "luz": False}, motor.Estilo(est_d or {}), Path("."))   # se mide la letra, no su luz
    except Exception as x:  # noqa: BLE001
        return [f"{donde}: no se puede dibujar ({x})"]
    w, h = e.img.size
    margen_dibujo = 30  # el motor deja aire para sombra/brillo alrededor del texto
    x0, x1 = d["x"] - w / 2 + margen_dibujo, d["x"] + w / 2 - margen_dibujo
    y0, y1 = d["y"] - h / 2 + margen_dibujo, d["y"] + h / 2 - margen_dibujo
    out = []
    mx, my = margen_cam
    if d.get("tipo") == "etiqueta" and w - 2 * margen_dibujo >= .9 * W:   # franja a sangre (banda de borde a borde): va cortada a propósito
        mx = 0
        if x0 >= -40 and x1 <= W + 40:
            return out
    if x0 < MARGEN + mx or x1 > W - MARGEN - mx:
        out.append(f"{donde}: el texto mide {w - 2 * margen_dibujo:.0f} px de ancho y se sale de lo que se ve "
                   f"(x {x0:.0f}..{x1:.0f}; con la cámara de la escena se ve x {MARGEN + mx:.0f}..{W - MARGEN - mx:.0f}; achica «tam», "
                   f"parte la línea o cambia la cámara)")
    if y0 < my + 10 or y1 > H - my - 10:
        out.append(f"{donde}: la cámara de la escena recorta el texto por arriba o por abajo (y {y0:.0f}..{y1:.0f})")
    if y0 < ZONA_TEXTO[0] or y1 > ZONA_TEXTO[1]:
        out.append(f"{donde}: el texto ocupa y {y0:.0f}..{y1:.0f}, fuera de la zona segura {ZONA_TEXTO[0]}..{ZONA_TEXTO[1]}")
    return out


AJUSTABLE = ("se sale de lo que se ve", "fuera de la zona segura")   # lo que `acomodar` arregla solo: correr el texto o achicarlo


def ajustar_textos(sb: dict, carpeta: Path | None = None) -> tuple[dict, list]:
    """Para el momento de EXPORTAR: si un texto no cabe (se sale del cuadro o de la zona segura), se acomoda solo en vez de tumbar
    el export. → (storyboard ajustado, índices de los elementos que cambiaron). El director ya lo hace al diseñar; aquí cubre lo que
    cambia después: otra letra o tamaño elegidos en Personalizar, una corrección, o un diseño hecho en otro equipo (13-nov)."""
    if not any(a in e for e in errores(sb, carpeta) for a in AJUSTABLE):
        return sb, []
    nuevo = acomodar(sb, carpeta)
    if "subtitulos" in sb:   # aquí solo se acomodan los textos: el subtítulo queda como estaba (`acomodar` volvería a anotar los duplicados)
        nuevo["subtitulos"] = sb["subtitulos"]
    else:
        nuevo.pop("subtitulos", None)
    tocados = [i for i, (a, b) in enumerate(zip(sb.get("elementos", []), nuevo.get("elementos", []))) if a != b]
    return (nuevo, tocados) if tocados else (sb, [])


def acomodar(sb: dict, carpeta: Path | None = None) -> dict:
    """Lo medible del encuadre lo arregla el código (lote del workshop, 04-nov: el director fallaba por píxeles): cada texto que
    la cámara deja fuera o que pisa la zona segura se corre hacia adentro lo justo y, si no cabe ni corrido, se achica."""
    import copy
    import re
    sb = copy.deepcopy(sb)
    if carpeta and (Path(carpeta) / "palabras.json").exists():   # texto duplicado (Pablo, 07-nov): el subtítulo se oculta solo
        palabras = json.loads((Path(carpeta) / "palabras.json").read_text())
        dup = duplicados(sb, palabras)
        if dup:
            sub = sb.setdefault("subtitulos", {})
            sub["ocultar"] = sorted(list(sub.get("ocultar", [])) + [[round(t0, 3), round(t1, 3)] for t0, t1, _, _ in dup])
    for _ in range(4):
        malos = [e for e in errores(sb, carpeta) if "se sale de lo que se ve" in e or "fuera de la zona segura" in e]
        if not malos:
            break
        for e in malos:
            m = re.search(r"elementos\[(\d+)\]", e)
            if not m:
                continue
            el = sb["elementos"][int(m.group(1))]
            mx = re.search(r"\(x (-?\d+)\.\.(-?\d+); con la cámara de la escena se ve x (-?\d+)\.\.(-?\d+)", e)
            my = re.search(r"ocupa y (-?\d+)\.\.(-?\d+), fuera de la zona segura (\d+)\.\.(\d+)", e)
            if mx:
                a, b, c, d = map(int, mx.groups())
                if b - a > d - c - 16:   # no cabe ni corrido: se achica la letra lo justo
                    k = (d - c - 24) / (b - a)
                    for l in el.get("lineas", []):
                        if isinstance(l, dict):
                            l["tam"] = int(l.get("tam", 80) * k)
                        elif isinstance(l, list) and len(l) > 1:
                            l[1] = int(l[1] * k)
                    if isinstance(el.get("pad"), list):
                        el["pad"][0] = int(el["pad"][0] * k)
                    el["x"] = (c + d) // 2 if el.get("alinear", "centro") == "centro" else el.get("x", 540)
                else:
                    el["x"] = el.get("x", 540) + ((c - a + 8) if a < c else -(b - d + 8) if b > d else 0)
            if my:
                a, b, c, d = map(int, my.groups())
                el["y"] = el.get("y", 960) + ((c - a + 8) if a < c else -(b - d + 8) if b > d else 0)
    return sb
