"""Catálogo VIVO de todo lo seleccionable, leído del código (docs/PLANO-SELECCIONADOR.md). Nunca una lista copiada a mano:
si alguien le agrega una transición, un filtro, un trazo o una fuente al motor, aparece sola en el seleccionador
(lo prueba tests/test_seleccionador.py). Los tipos de hook salen de cómo abren las copias aprobadas (`director/ejemplo`).

Cada categoría dice a dónde va lo que Pablo marque en `proyectos/<p>/preferencias.json`:
- `destino: "estilo"`  → un valor único en `estilo` (lo aplica `director._fijar_estilo`, como el color de Personalizar);
- `destino: "paleta"`  → varios colores de `estilo` a la vez (acento, acento2, tinta, papel) tomados de un estilo;
- `destino: "color"`   → una parte de `estilo.color` (look);
- `destino: "preset"`  → el estilo base del video;
- `destino: "repertorio"` → una lista: el director usa en ESA categoría solo lo elegido (no todo); sin elegir = libertad total.
Los nombres bonitos son solo texto de pantalla: si una opción nueva no tiene nombre, sale con su id.
"""
import json

from . import camara, color, config, efectos, motor, sonido, subtitulo_opciones, validar

LIB = config.RAIZ / "librerias"
MUESTRAS = config.RAIZ / "app" / "muestras"
SEL = MUESTRAS / "sel"

# Texto de pantalla (no decide qué opciones existen).
NOMBRES = {
    "corte": "Corte seco", "rafaga": "Ráfaga", "flash": "Flash", "zoom": "Zoom suave", "pixel": "Pixelado", "bloques": "Bloques",
    "invertir": "Negativo", "wipe": "Barrido de color", "iris": "Iris", "desenfoque": "Rack focus",
    "cae": "Cae", "izq": "Desde la izquierda", "der": "Desde la derecha", "sube": "Sube", "pop": "Pop", "barrido": "Barrido",
    "golpe": "Golpe", "fundido": "Fundido", "enfoque": "Enfoque", "smear": "Smear", "llega": "Llega y desacelera",
    "tratamiento:bn": "Blanco y negro", "tratamiento:halftone": "Semitono", "tratamiento:duotono": "Duotono",
    "tratamiento:duotono-inverso": "Duotono inverso", "fusion:pantalla": "Fusión pantalla (borra el negro)",
    "fusion:multiplicar": "Fusión multiplicar (borra el blanco)", "fundir": "Fundida con el fondo", "cubrir": "Pantalla completa",
    "caja": "Caja limpia", "acercar": "Se acerca sola (Ken Burns)", "luz": "Con luz y halo",
    "muro-luz": "Muro con luz", "muro-claro": "Muro claro", "tira": "Tira", "hud": "HUD palabra a palabra", "vidrio": "Vidrio",
    "suave": "Suave", "papel": "Papel", "papel-maquina": "Papel + máquina de escribir", "digital": "Digital", "cine": "Cine",
    "bn": "Blanco y negro", "color": "Color",
    "penumbra": "Penumbra", "termico": "Térmico", "rayosx": "Rayos X", "duotono": "Duotono", "halftone": "Semitono",
    "blueprint": "Plano técnico",
    "rect": "Marco", "elipse": "Círculo a mano", "rayos": "Rayos", "linea": "Línea · subrayado", "reticula": "Retícula",
}
NOTAS = {
    "corte": "siempre permitido: es no poner transición", "cine": "calla los textos; solo cortes y golpes",
    "fusion:pantalla": "para apoyos con fondo negro", "fusion:multiplicar": "para apoyos con fondo blanco",
}
# Efectos de estilo con valor: (clave en `estilo`, nombre, mínimo, máximo, paso, valor de la muestra).
EFECTOS = (("grano", "Grano", 0, 40, 1, 30), ("crt", "Textura de tele vieja", 0, 1, .05, .8),
           ("aberracion_corte", "Aberración en los cortes", 0, 12, 1, 10), ("bloom", "Brillo en las luces (bloom)", 0, 1, .05, .5),
           ("flotar", "Cámara que flota", 0, 20, 1, 16), ("flotar_elementos", "Todo flota (elementos)", 0, 14, 1, 12))
INTERRUPTORES = (("transicion", "Rack focus en todos los cortes", "corte", "desenfoque"),)
EFECTOS_DE_MOVIMIENTO = {"flotar_elementos", "transicion"} | (set() if camara.fija() else {"flotar"})   # el resto de EFECTOS (grano, crt, bloom…) ya no se elige en pantalla
# Pablo (11-nov): «quiero dejar varias cosas que las decida Opus y no yo, para hacerlo más sencillo; tipografías básicas y ya».
# Siguen vivas en el motor y en las preferencias ya guardadas; solo dejan de preguntarse en pantalla (queda UNA letra: la de títulos).
FUERA_DE_PANTALLA = ("fuente_script", "fuente_mono", "cajas", "transiciones", "efectos_mov")
DATOS = {"contador", "barra", "barra-horizontal"}                       # recursos que se muestran en «Contadores y barras»

# Tipos de hook: cómo abren las copias aprobadas. `tipos_de_hook` reconoce cada uno en un storyboard; el seleccionador muestra
# solo los que alguna copia aprobada hace (aparecen solos cuando se integra un estilo nuevo que abre distinto).
VENTANA_HOOK = 2.6   # segundos desde el primer elemento: lo que se ve como hook
HOOKS = {
    "caja-hook": ("Caja del hook", "la frase del hook dentro de una caja (vidrio o panel) sobre la toma"),
    "palabra-gigante": ("Palabra gigante", "una palabra enorme que golpea la pantalla"),
    "lamina": ("Lámina", "una imagen a pantalla completa detrás de la frase"),
    "maquina": ("Máquina de escribir", "la frase se escribe letra a letra"),
    "etiquetas": ("Etiquetas", "la frase en etiquetas con fondo de color"),
    "palabra-a-palabra": ("Palabra a palabra", "texto chico que aparece palabra por palabra"),
    "pregunta": ("Pregunta", "abre con una pregunta en pantalla"),
    "golpe-filtro": ("Golpe de filtro", "la toma abre con un filtro de un instante"),
    "apertura": ("Apertura de cine", "la primera toma entra con una transición (iris, desenfoque…)"),
}


# Estilos que Pablo quiere SIEMPRE al principio de la lista, antes de los aprobados (Básico: «que sea el PRIMERO», 08-nov).
PRIMEROS = ("basico",)
# Estilos que siguen vivos en el motor (director, presets, guías) pero no se muestran en ninguna pantalla. Maestro calma: Pablo,
# 11-nov, «quita ese maestro calma»; el motor no pierde el estilo aprobado (un video viejo hecho con él se sigue pudiendo abrir).
OCULTOS = ("maestro-calma", "lemo")   # «lemo» se elige desde Estilos Pro (con uno de los estilos de Lemo), no como tarjeta
MAX_HOOK = 120   # caracteres del hook que escribe la persona


def nombre(oid: str) -> str:
    return NOMBRES.get(oid, oid.replace("-", " ").replace("_", " ").capitalize())


def archivo_muestra(categoria: str, opcion: str) -> str:
    """Nombre base del archivo de la muestra (sin extensión), seguro para el disco."""
    return f"{categoria}-" + "".join(c if c.isalnum() or c == "-" else "_" for c in str(opcion))


def _url(f) -> str:
    """URL de un archivo de app/muestras con su versión (el navegador lo guarda en caché y lo pide de nuevo solo si cambió)."""
    return f"/app/muestras/{f.relative_to(MUESTRAS).as_posix()}?v={int(f.stat().st_mtime)}"


def muestra(categoria: str, opcion: str) -> str | None:
    base = archivo_muestra(categoria, opcion)
    for ext in (".mp4", ".jpg"):
        if (SEL / (base + ext)).exists():
            return _url(SEL / (base + ext))
    return None


def poster(categoria: str, opcion: str) -> str | None:
    """Imagen fija de una muestra en video (se ve al instante; el video carga solo al pasar el mouse o al verse)."""
    f = SEL / (archivo_muestra(categoria, opcion) + ".poster.jpg")
    return _url(f) if f.exists() else None


def _op(categoria, oid, **extra):
    m = muestra(categoria, oid)
    po = poster(categoria, oid) if m and ".mp4" in m else None
    return {"id": oid, "nombre": extra.pop("nombre", None) or nombre(oid), "nota": extra.pop("nota", NOTAS.get(oid, "")),
            "muestra": m, **({"poster": po} if po else {}),
            **({} if m else {"aviso": "sin muestra todavía: corre «uv run estudio muestras»"}), **extra}


def _cat(cid, nombre_, grupo, destino, opciones, clave=None, **extra):
    return {"id": cid, "nombre": nombre_, "grupo": grupo, "destino": destino, "clave": clave or cid,
            "opciones": opciones, **extra}


def tratamientos() -> list:
    return [f"tratamiento:{t}" for t in motor.TRATAMIENTOS] + [f"fusion:{f}" for f in motor.FUSIONES] + list(validar.APOYO_CLAVES)


def filtros() -> list:
    return [f for f in efectos.FILTROS if f != "ninguno"]


def presets() -> dict:
    return json.loads((LIB / "estilos" / "presets.json").read_text())


def fuentes() -> dict:
    return json.loads((LIB / "fuentes" / "indice.json").read_text())


def aprobados() -> list:
    """Estilos aprobados por Pablo (integrados al director: tienen ejemplo y no están en OBSOLETOS), en orden."""
    from .director import AQUI, _obsoletos
    obs = _obsoletos()
    return [f.stem for f in sorted((AQUI / "ejemplo").glob("*.json")) if not f.name.endswith("palabras.json") and f.name not in obs]


def _ejemplo(estilo: str) -> dict:
    from .director import AQUI
    try:
        return json.loads((AQUI / "ejemplo" / f"{estilo}.json").read_text())
    except (OSError, ValueError):
        return {}


def _lineas(d: dict) -> list:
    """[(texto, tam)] de un texto ([{texto, tam}]) o de una etiqueta ([[texto, tam, …]])."""
    out = []
    for ln in d.get("lineas") or []:
        if isinstance(ln, dict):
            out.append((str(ln.get("texto", "")), ln.get("tam", 0) if validar._num(ln.get("tam")) else 0))
        elif isinstance(ln, (list, tuple)) and ln:
            out.append((str(ln[0]), ln[1] if len(ln) > 1 and validar._num(ln[1]) else 0))
    return out


def tipos_de_hook(sb: dict) -> list:
    """Qué tipos de HOOKS hace la apertura de un storyboard (los primeros VENTANA_HOOK segundos desde el primer elemento)."""
    els = sorted((e for e in sb.get("elementos") or [] if isinstance(e, dict) and validar._num(e.get("t0"))), key=lambda e: e["t0"])
    escenas = sorted((e for e in sb.get("escenas") or [] if isinstance(e, dict) and validar._num(e.get("t0"))), key=lambda e: e["t0"])
    if not els:
        return []
    ini = els[0]["t0"]
    ap = [e for e in els if e["t0"] <= ini + VENTANA_HOOK]
    e0 = escenas[0] if escenas else {}   # la escena con la que abre el video
    textuales = [e for e in ap if e.get("tipo") in ("texto", "etiqueta")]
    frases = [" ".join(t for t, _ in _lineas(e)).strip() for e in textuales]
    tipos = set()
    if any(e.get("tipo") in ("vidrio", "panel") for e in ap) and textuales:
        tipos.add("caja-hook")
    if any(tam >= 160 for e in textuales if e.get("tipo") == "texto" for _, tam in _lineas(e)):
        tipos.add("palabra-gigante")
    if any(e.get("tipo") in ("foto", "clip") and e.get("cubrir") for e in ap):
        tipos.add("lamina")
    crece = sum(1 for a, b in zip(frases, frases[1:]) if a and len(b) > len(a) and b.startswith(a))
    if any(e.get("tecleo") for e in ap) or crece >= 3:
        tipos.add("maquina")
    if textuales and textuales[0].get("tipo") == "etiqueta" and len(frases[0]) > 1:
        tipos.add("etiquetas")
    textos = [e for e in textuales if e.get("tipo") == "texto"]
    if len(textos) >= 4 and max((tam for e in textos for _, tam in _lineas(e)), default=0) <= 90:
        tipos.add("palabra-a-palabra")
    if any("?" in f or "¿" in f for f in frases):
        tipos.add("pregunta")
    if e0.get("filtro", "ninguno") not in ("ninguno", None):
        tipos.add("golpe-filtro")
    if e0.get("entrada", "corte") not in ("corte", None):
        tipos.add("apertura")
    return [h for h in HOOKS if h in tipos]


def hooks_aprobados() -> dict:
    """{tipo de hook: [estilos aprobados que abren así]} (solo los tipos que alguna copia aprobada hace)."""
    out, tipos = {}, {est: tipos_de_hook(_ejemplo(est)) for est in aprobados()}
    for est, hs in tipos.items():
        for h in hs:
            out.setdefault(h, []).append(est)
    # primero la copia que abre SOLO así (la que más claro lo muestra): de ella sale la muestra
    return {h: sorted(out[h], key=lambda e: len(tipos[e])) for h in HOOKS if h in out}


def _colores_texto() -> list:
    """Para los textos pequeños: blanco (como vienen), negro y los claros que ya usan los estilos como segundo color."""
    base = [{"id": "#FFFFFF", "nombre": "#FFFFFF", "nota": "blanco (como viene)", "muestra": None, "hex": "#FFFFFF"},
            {"id": "#111111", "nombre": "#111111", "nota": "negro", "muestra": None, "hex": "#111111"}]
    return base + [c for c in _colores("acento2") if c["id"] not in ("#FFFFFF", "#111111")]


def _colores(clave) -> list:
    """Los colores que ya usan los estilos, con de qué estilo vienen (sin rosa: prohibido por Pablo). Otro color: el gotero."""
    vistos = {}
    for p in presets().values():
        c = str(p.get(clave, "")).upper()
        if validar._HEX.match(c) and not validar.es_rosa(c):
            vistos.setdefault(c, []).append(p.get("nombre", ""))
    return [{"id": c, "nombre": c, "nota": "de " + ", ".join(n[:2]) + ("…" if len(n) > 2 else ""), "muestra": None, "hex": c}
            for c, n in vistos.items()]


PALETA = ("acento", "acento2", "tinta", "papel")


def _paletas(orden) -> list:
    """La paleta completa de cada estilo (acento, segundo, tinta y papel), para tomarla de una vez."""
    ps, out, vistas = presets(), [], set()
    for pid in orden:
        p = ps[pid]
        cols = {k: str(p[k]).upper() for k in PALETA if validar._HEX.match(str(p.get(k, ""))) and not validar.es_rosa(str(p[k]))}
        firma = tuple(sorted(cols.items()))
        if len(cols) < 2 or firma in vistas:
            continue
        vistas.add(firma)
        out.append({"id": pid, "nombre": p.get("nombre", pid), "nota": "", "muestra": None, "colores": cols})
    return out


def _usos_fuente() -> dict:
    """{fuente: [estilos que la usan]} para decir en la tarjeta dónde se ve cada letra."""
    out = {}
    for p in presets().values():
        for k in ("fuente", "fuente_script", "fuente_mono"):
            if p.get(k):
                out.setdefault(p[k], []).append(p.get("nombre", ""))
    return out


def en_pantalla() -> list:
    """Los estilos que la persona ve para elegir, en orden: primero PRIMEROS (Básico: solo subtítulos), luego los aprobados; nunca
    los OCULTOS. ÚNICA lista: la usan la pantalla de Estilos (/api/librerias) y Edición avanzada. Antes la pantalla de Estilos armaba
    la suya («los que tienen ejemplo del director») y por eso Básico, que no usa director, no salía, y Maestro calma sí, sin
    portada (Pablo, 11-nov: «le falta el estilo simple… quita ese maestro calma, que ni siquiera se ve la foto»)."""
    ps = presets()
    return [a for a in PRIMEROS if a in ps] + [a for a in aprobados() if a in ps and a not in PRIMEROS and a not in OCULTOS]


def catalogo(todas: bool = False) -> dict:
    """Los carriles de Edición avanzada. `todas`: también lo que el motor sabe y ya no se pregunta en pantalla (`FUERA_DE_PANTALLA`)."""
    ps = presets()
    apro = en_pantalla()
    orden = [p for p in apro + [p for p in ps if p not in apro] if p not in OCULTOS]
    estilos = []
    for pid in orden:
        p = ps[pid]
        m = muestra("estilo", pid) or (_url(MUESTRAS / f"{pid}.jpg") if (MUESTRAS / f"{pid}.jpg").exists() else None)
        po = _url(MUESTRAS / f"{pid}.jpg") if (MUESTRAS / f"{pid}.jpg").exists() else poster("estilo", pid)
        estilos.append({"id": pid, "nombre": p.get("nombre", pid), "nota": "" if pid in apro else "anterior",
                        "aprobado": pid in apro, "muestra": m, **({"poster": po} if po and m and ".mp4" in m else {}),
                        "acento": p.get("acento"), **({} if m else {"aviso": "sin muestra: hace falta un video final de este estilo"})})
    hooks = [_op("hook", h, nombre=HOOKS[h][0], nota=HOOKS[h][1], ejemplos=[ps.get(e, {}).get("nombre", e) for e in ests],
                 ejemplos_id=ests)
             for h, ests in hooks_aprobados().items()]
    usos = _usos_fuente()
    luts = [l for l in color.looks() if l["id"].startswith("mio:")]
    looks = [l for l in color.looks() if not l["id"].startswith("mio:")]
    letras = [{"id": f, "nombre": f, "nota": v.get("nota", ""), "muestra": None, "fuente": f"/api/fuente/{f}",
               "usos": usos.get(f, [])[:3]} for f, v in fuentes().items()]
    efecto = lambda k, n, **x: _op("efecto", k, nombre=n, **x)  # noqa: E731
    cats = [   # los carriles de Edición avanzada, en este orden (Pablo, 07-nov): Estilo · Color · Tipografía · Texto · Movimiento
        _cat("preset", "Estilo", "Estilo", "preset", estilos),
        _cat("look", "Looks", "Color", "color",
             [_op("look", l["id"], nombre=f"Look {i}", nota="", fuerza=l["fuerza"]) for i, l in enumerate(looks + luts, 1)]),
        _cat("filtros", "Efectos rápidos", "Color", "repertorio", [_op("filtro", f) for f in filtros()]),
        _cat("paleta", "Paletas de los estilos", "Color", "paleta", _paletas(orden)),
        _cat("acento", "Color de énfasis", "Color", "estilo", _colores("acento"), gotero=True),
        _cat("acento2", "Color del brillo y la luz", "Color", "estilo", _colores("acento2"), gotero=True),
        _cat("texto", "Color de los textos pequeños", "Color", "estilo", _colores_texto(), gotero=True),
        _cat("papel", "Color del fondo", "Color", "estilo", _colores("papel"), gotero=True),
        _cat("fuente", "Tipografía de títulos", "Tipografía", "estilo", letras, buscar=True),
        _cat("fuente_script", "Tipografía de conectores", "Tipografía", "estilo", letras, buscar=True),
        _cat("fuente_mono", "Tipografía de datos", "Tipografía", "estilo", letras, buscar=True),
        _cat("hooks", "Hook", "Texto", "repertorio", hooks),
        _cat("subtitulo", "Subtítulos", "Texto", "estilo", [_op("subtitulo", s) for s in sorted(validar.SUBTITULOS)]),
        _cat("borde", "Color de la caja", "Texto", "estilo", _colores("borde"), gotero=True),
        _cat("cajas", "Cajas y etiquetas", "Texto", "repertorio",
             [_op("recurso", r, nombre=n.capitalize()) for r, n in validar.RECURSOS.items() if r not in DATOS],
             clave="recursos"),
        _cat("transiciones", "Transiciones", "Movimiento", "repertorio",
             [_op("transicion", e) for e in sorted(validar.ENTRADAS_ESCENA)]),
        _cat("efectos_mov", "Cámara y flotación", "Movimiento", "estilo",
             [efecto(k, n, rango=[a, b, paso], valor=v) for k, n, a, b, paso, v in EFECTOS if k in EFECTOS_DE_MOVIMIENTO]
             + [efecto(k, n, apagado=off, encendido=on) for k, n, off, on in INTERRUPTORES], clave=None, valores=True),
    ]
    if not todas:
        cats = [c for c in cats if c["id"] not in FUERA_DE_PANTALLA]
    return {"categorias": cats, "subtitulo": subtitulo_opciones.para_pantalla()}


_CACHE: dict = {}


def _firma() -> tuple:
    from .director import AQUI
    rutas = (SEL, SEL / "huellas.json", MUESTRAS, LIB / "estilos" / "presets.json", LIB / "fuentes" / "indice.json",
             color.LIB / "looks.json", color.LIB / "recetas", color.MIS_LUTS, AQUI / "ejemplo", AQUI / "ejemplo" / "OBSOLETOS.txt")
    return tuple(r.stat().st_mtime_ns if r.exists() else 0 for r in rutas)


def catalogo_cacheado() -> dict:
    """El catálogo para la pantalla: se arma una vez y se rehace solo si cambia algo en disco (muestras, estilos, fuentes, looks)."""
    f = _firma()
    if _CACHE.get("firma") != f:
        _CACHE.update(firma=f, valor=catalogo())
    return _CACHE["valor"]


def opciones(cid: str) -> set:
    return {o["id"] for c in catalogo(todas=True)["categorias"] if c["id"] == cid for o in c["opciones"]}


def permitidos_repertorio() -> dict:
    """{categoría de repertorio: ids posibles} (las mismas de validar.REPERTORIO_NOMBRES), para validar lo que llega del seleccionador."""
    return {"transiciones": set(validar.ENTRADAS_ESCENA), "entradas": set(validar.ENTRADAS), "tratamientos": set(tratamientos()),
            "fondos": set(efectos.MUROS), "filtros": set(filtros()), "trazos": set(validar.TIPOS_TRAZO),
            "recursos": set(validar.RECURSOS), "textos": set(validar.ESTILOS_TEXTO), "hooks": set(HOOKS)}


# ---------- lo que Pablo marca en el seleccionador → proyectos/<p>/preferencias.json (mezcla por clave, no pisa) ----------
PERSONAS = ("bn", "color")


def leer(carpeta) -> dict:
    f = carpeta / "preferencias.json"
    try:
        return json.loads(f.read_text()) if f.exists() else {}
    except ValueError:
        return {}


def _valor_estilo(k, v, err):
    """Comprueba un valor de `estilo` que llega de la pantalla (cualquier entrada: la pantalla no es de fiar)."""
    numericos = {e[0]: e[2:4] for e in EFECTOS} | {"sfx": (0, 1)}
    if k not in validar.CLAVES["estilo"] or k in ("id", "nombre", "base", "imagenes", "tope_imagenes"):
        err.append(f"{k}: no se elige aquí")
    elif k in ("acento", "acento2", "papel", "tinta", "borde", "texto"):
        if not (isinstance(v, str) and validar._HEX.match(v)) or validar.es_rosa(v):
            err.append(f"{k}: {v!r} no es un color válido (#RRGGBB, sin rosa)")
    elif k in subtitulo_opciones.CLAVES:
        if m := subtitulo_opciones.error(k, v):
            err.append(m)
    elif k in ("fuente", "fuente_script", "fuente_mono"):
        if v not in fuentes():
            err.append(f"{k}: la fuente {v!r} no está instalada")
    elif k == "subtitulo" and v not in validar.SUBTITULOS:
        err.append(f"subtitulo: {v!r} no existe")
    elif k == "sonido_paleta" and v not in sonido.PALETAS:
        err.append(f"sonido_paleta: {v!r} no existe")
    elif k == "persona" and v not in PERSONAS:
        err.append(f"persona: {v!r} no existe")
    elif k == "transicion" and v not in {x for i in INTERRUPTORES for x in i[2:]}:
        err.append(f"transicion: {v!r} no existe")
    elif k in numericos:
        a, b = numericos[k]
        if not validar._num(v) or not a <= v <= b:
            err.append(f"{k}: número entre {a} y {b}")
    elif k == "color":
        if not isinstance(v, dict) or set(v) - {"receta", "look", "fuerza", "ajustes"}:
            err.append("color: va como {receta, look, fuerza, ajustes}")
        elif "ajustes" in v and (not isinstance(v["ajustes"], dict) or set(v["ajustes"]) - set(color.AJUSTES)
                                 or not all(validar._num(x) and -1 <= x <= 1 for x in v["ajustes"].values())):
            err.append(f"color.ajustes: {', '.join(color.AJUSTES)}, cada uno entre -1 y 1")
        elif v.get("receta") and v["receta"] not in color.recetas():
            err.append(f"color.receta: {v['receta']!r} no existe")
        elif v.get("look") and v["look"] not in {l["id"] for l in color.looks()}:
            err.append(f"color.look: {v['look']!r} no está en esta máquina")
        elif "fuerza" in v and not (validar._num(v["fuerza"]) and 0 <= v["fuerza"] <= 1):
            err.append("color.fuerza: entre 0 y 1")


def aplicar_estilo(base: dict, cambios: dict, estilo_id=None) -> dict:
    """`base` con `cambios` encima. Un valor `null` es «Del estilo»: vuelve al valor del preset (Básico trae sus propios sub_*) o, si el preset
    no lo trae, se quita. Lo usan Personalizar (/api/previa) y /api/seleccion: una sola regla para las dos pantallas."""
    pre = presets().get(estilo_id or base.get("id") or "", {})
    out = dict(base)
    for k, v in cambios.items():
        if v is not None:
            out[k] = v
        elif k in pre and k != "nombre":
            out[k] = pre[k]
        else:
            out.pop(k, None)
    return out



def _sin_entrada(v):
    """Migración: los proyectos viejos guardaron `color.entrada` (perfil LOG, ya eliminado). Es una clave muerta: se descarta en silencio."""
    return {a: b for a, b in v.items() if a != "entrada"} if isinstance(v, dict) else v


def guardar(carpeta, d: dict) -> dict:
    """Mezcla lo elegido en `preferencias.json` (null o lista vacía = volver a «libre»). Si el video ya tiene storyboard, el estilo
    elegido se le aplica igual que en Personalizar. Devuelve {preferencias, avisos} o lanza ValueError con todo lo que no vale."""
    prefs, err = leer(carpeta), []
    est = dict(prefs.get("estilo") or {})
    d = {**d, "estilo": {k: _sin_entrada(v) if k == "color" else v for k, v in (d.get("estilo") or {}).items()}}
    for k, v in d["estilo"].items():
        if v is None:
            est.pop(k, None)
            continue
        _valor_estilo(k, v, err)
        est[k] = v
    rep = dict(prefs.get("repertorio") or {})
    posibles = permitidos_repertorio()
    for k, v in (d.get("repertorio") or {}).items():
        if k not in posibles:
            err.append(f"repertorio.{k}: esa categoría no existe (hay: {', '.join(posibles)})")
        elif not v:
            rep.pop(k, None)
        elif not isinstance(v, list) or set(map(str, v)) - posibles[k]:
            err.append(f"repertorio.{k}: {sorted(set(map(str, v if isinstance(v, list) else [v])) - posibles[k])} no existe")
        elif len(set(map(str, v))) > 1:   # Pablo (10-nov): una sola opción por categoría; lo que llega REEMPLAZA, nunca se acumula
            err.append(f"repertorio.{k}: una sola opción por categoría (llegaron {len(set(map(str, v)))})")
        else:
            rep[k] = [str(v[0])]
    hook = prefs.get("hook_texto")
    if "hook_texto" in d:
        if d["hook_texto"] is not None and not isinstance(d["hook_texto"], str):
            err.append("hook_texto: va como texto")
        else:
            hook = (d["hook_texto"] or "").strip()
            if len(hook) > MAX_HOOK:
                err.append(f"hook_texto: máximo {MAX_HOOK} caracteres")
    hook_caja, hook_color = prefs.get("hook_caja"), prefs.get("hook_color")
    if "hook_caja" in d:   # con caja (True) o solo texto (False); None = lo que decida el estilo
        if d["hook_caja"] is not None and not isinstance(d["hook_caja"], bool):
            err.append("hook_caja: va como sí o no")
        hook_caja = d["hook_caja"]
    if "hook_color" in d:
        if d["hook_color"] is not None and not (isinstance(d["hook_color"], str) and validar._HEX.match(d["hook_color"])
                                               and not validar.es_rosa(d["hook_color"])):
            err.append(f"hook_color: {d['hook_color']!r} no es un color válido (#RRGGBB, sin rosa)")
        hook_color = d["hook_color"].upper() if isinstance(d["hook_color"], str) else None
    aprobado = prefs.get("guion_aprobado")
    if "guion_aprobado" in d:   # la persona aprobó el texto que quedará (lo lee el motor al cortar: pendiente del PC)
        if d["guion_aprobado"] is not None and not isinstance(d["guion_aprobado"], bool):
            err.append("guion_aprobado: va como sí o no")
        aprobado = d["guion_aprobado"]
    preset = prefs.get("preset")
    if "preset" in d:
        if d["preset"] is not None and d["preset"] not in presets():
            err.append(f"preset: el estilo {d['preset']!r} no existe")
        preset = d["preset"]
    if err:
        raise ValueError("; ".join(err))
    for k, v in (("estilo", est), ("repertorio", rep), ("preset", preset), ("hook_texto", hook), ("hook_color", hook_color)):
        if v:
            prefs[k] = v
        else:
            prefs.pop(k, None)
    for k, v in (("hook_caja", hook_caja), ("guion_aprobado", aprobado)):
        if v is None:
            prefs.pop(k, None)
        else:
            prefs[k] = v
    (carpeta / "preferencias.json").write_text(json.dumps(prefs, ensure_ascii=False, indent=1))
    avisos = []
    sbf = carpeta / "storyboard.json"
    if sbf.exists():
        sb = json.loads(sbf.read_text())
        if d.get("preset"):
            sb["estilo"] = {**sb.get("estilo", {}), **{k: v for k, v in presets()[d["preset"]].items() if k != "nombre"}}
        sb["estilo"] = aplicar_estilo(sb.get("estilo", {}), d.get("estilo") or {}, d.get("preset"))
        sbf.write_text(json.dumps(sb, ensure_ascii=False, indent=1))
        avisos = [e for e in validar._repertorio(sb, validar.repertorio(carpeta))]
    return {"preferencias": prefs, "avisos": avisos}
