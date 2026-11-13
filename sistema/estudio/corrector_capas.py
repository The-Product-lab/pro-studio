"""Corrector por capas (docs/PLANO-EDITOR-CAPAS.md §2.2): una corrección de Pablo (texto + opcional segundo del video final) → operaciones
de `capas.py`. Tres escalones, del más barato al más caro:
  a) reglas en código para las frases comunes: 0 tokens;
  b) UNA llamada chica a Sonnet, sin herramientas, que ve solo la corrección, el segundo y las capas de ese momento;
  c) si no es de capa (gusto general, falla del sistema, algo que el catálogo no cubre) → derivar al Agente Editor de hoy, intacto.
Ante ambigüedad no se cambia nada: la llamada chica devuelve una pregunta. Cada intento queda en `capas.jsonl` del proyecto.
"""
import json
import re
import time
import unicodedata
from datetime import datetime
from pathlib import Path

from . import capas, ia

TOPE_USD = 0.3               # tope de la llamada chica (Sonnet, sin herramientas)
TIMEOUT_S = 180
MAX_OPERACIONES = 8
REGISTRO = "capas.jsonl"
PASO_TAM = 1.25              # «más grande»: ×1,25 (con «mucho»: ×1,5); «más chico»: ×0,8 (con «mucho»: ×0,65)
PASO_TAM_MUCHO = 1.5
PASO_MOVER = 80              # px por «un poco más arriba/abajo/…»
PASO_COLOR = 0.15
PASO_SFX = 1.5
MARGEN_S = 0.2               # un texto cuenta como «el de ese segundo» con este margen
COLORES = {"rojo": "#E5322D", "amarillo": "#FFE800", "blanco": "#FFFFFF", "negro": "#111111", "azul": "#2F6FE4",
           "verde": "#2FA84F", "naranja": "#F28C28"}

_COMILLAS = r"[«\"“'‘]"
_CIERRE = r"[»\"”'’]"
_GUSTO = re.compile(r"\b(siempre|nunca|en todos|todos los (videos|reels)|de ahora en adelante|a partir de ahora|en general)\b")
_TEXTO = ("titulo", "texto", "letra", "palabra", "frase", "etiqueta", "rotulo", "letrero")
_GRAFICO = ("grafico", "imagen", "foto", "dibujo", "elemento", "recurso", "ilustracion", "figura")


def _plano(s: str) -> str:
    """Minúsculas sin tildes, del mismo largo que el original (los índices valen para las dos)."""
    return "".join(unicodedata.normalize("NFD", c)[0] for c in s.lower())


def _citas(texto: str) -> list:
    return [m.group(1) for m in re.finditer(f"{_COMILLAS}(.+?){_CIERRE}", texto)]


class _Ctx:
    """Todo lo que una regla necesita: storyboard, palabras, el segundo (fuente) y la frase."""

    def __init__(self, sb, pal, texto, segundo):
        self.sb, self.pal, self.texto, self.plano = sb, pal, texto, _plano(texto)
        self.t = capas.fuente_de(sb, segundo) if segundo is not None else None
        self.citas = _citas(texto)

    def dice(self, *claves) -> bool:
        return any(re.search(rf"\b{c}", self.plano) for c in claves)

    def activos(self, texto: bool) -> list:
        if self.t is None:
            return []
        return [e for e in self.sb.get("elementos", []) if isinstance(e, dict) and capas._activo(e, self.t, MARGEN_S)
                and (e.get("tipo") in ("texto", "etiqueta")) == texto]


def _tam(e: dict) -> float:
    ln = (e.get("lineas") or [None])[0]
    return float(ln.get("tam", 0) if isinstance(ln, dict) else ln[1] if isinstance(ln, list) and len(ln) > 1 else 0)


def _por_cita(c: _Ctx) -> list:
    """Elementos de texto cuyo contenido es una de las frases entre comillas."""
    out = []
    for q in c.citas:
        out += [e for e in c.sb.get("elementos", []) if isinstance(e, dict)
                and any(_plano(q) == _plano(t).strip() for _, t in capas.textos_de(e))]
    return out


def _objetivo(c: _Ctx):
    """El elemento al que se refiere la frase (None si no es inequívoco): por cita, o el único del segundo; «título» = el de letra mayor."""
    citados = _por_cita(c)
    if len(citados) == 1:
        return citados[0]
    if c.dice(*_GRAFICO):
        pool = [e for e in c.activos(False) if not e.get("cubrir")]
        return pool[0] if len(pool) == 1 else None
    pool = c.activos(True)
    if c.dice("titulo") and pool:
        mayor = max(_tam(e) for e in pool)
        top = [e for e in pool if _tam(e) == mayor]
        return top[0] if len(top) == 1 else None
    return pool[0] if len(pool) == 1 else None


# ---------------------------------------------------------------- reglas (cada una: ops | None | {"derivar": ...})

def _regla_subtitulo_ocultar(c: _Ctx):
    if not (c.dice("sac", "quit", "oculta", "apag", "borr", "sin") and c.dice("subtitul")) or c.t is None:
        return None
    from . import motor
    bloque = next(((a, b) for a, b, _, _ in motor.tramos_subtitulo(c.sb.get("subtitulos", {}), c.pal) if a <= c.t <= b), None)
    a, b = bloque or (c.t - 1.0, c.t + 1.0)
    return [{"op": "subtitulo.ocultar", "t0": round(a, 3), "t1": round(b, 3)}]


def _regla_quitar_palabra(c: _Ctx):
    if not (c.dice("sac", "quit", "cort", "borr", "elimin") and c.dice("palabra")):
        return None
    nucleo = lambda w: w.strip("¿?¡!.,;:").lower()    # noqa: E731
    if c.citas:
        idx = [i for i, p in enumerate(c.pal) if _plano(nucleo(p["w"])) == _plano(c.citas[0])]
    elif c.t is not None:
        idx = [i for i, p in enumerate(c.pal) if p["s"] - MARGEN_S <= c.t <= p["e"] + MARGEN_S]
    else:
        return None
    if c.t is not None and len(idx) > 1:
        idx = sorted(idx, key=lambda i: abs((c.pal[i]["s"] + c.pal[i]["e"]) / 2 - c.t))[:1]
    return [{"op": "corte.quitar", "indices": idx}] if len(idx) == 1 else None


def _regla_camara(c: _Ctx):
    if c.t is None or not c.dice("golpe", "zoom", "acercamiento", "punch"):
        return None
    if c.dice("sac", "quit", "elimin", "borr", "no quiero"):
        return [{"op": "camara.quitar", "t": round(c.t, 3)}]
    if c.dice("agreg", "pon", "met", "sum", "haz", "hace", "anad"):
        return [{"op": "camara.golpe", "t": round(c.t, 3)}]
    return None


def _regla_sonido(c: _Ctx):
    if c.dice("musica"):
        return {"derivar": "agente", "motivo": "el storyboard no guarda el volumen de la música"}
    if not c.dice("efecto", "sfx", "sonidito"):
        return None
    if c.dice("silenci", "apag", "quit", "sin"):
        return [{"op": "sonido.volumen", "valor": 0}]
    if c.dice("baj", "men", "reduc", "mas bajo", "mas suave"):
        return [{"op": "sonido.volumen", "factor": round(1 / PASO_SFX, 3)}]
    if c.dice("sub", "aument", "mas fuerte", "mas alto", "mas"):
        return [{"op": "sonido.volumen", "factor": PASO_SFX}]
    return None


_AJUSTES_COLOR = {"saturacion": ("saturacion", 1), "contraste": ("contraste", 1), "calido": ("temperatura", 1), "calida": ("temperatura", 1),
                  "frio": ("temperatura", -1), "fria": ("temperatura", -1), "brillo": ("exposicion", 1), "luz": ("exposicion", 1),
                  "claro": ("exposicion", 1), "oscuro": ("exposicion", -1), "exposicion": ("exposicion", 1)}


def _regla_color_video(c: _Ctx):
    if c.dice(*_TEXTO, *_GRAFICO):
        return None
    m = re.search(r"\b(mas|menos|sub\w*|baj\w*|aument\w*|reduc\w*|disminu\w*)\s+(?:el |la |un poco de |de )?(" + "|".join(_AJUSTES_COLOR) + r")\b",
                  c.plano)
    if not m:
        return None
    clave, signo = _AJUSTES_COLOR[m.group(2)]
    baja = m.group(1) == "menos" or m.group(1).startswith(("baj", "reduc", "disminu"))
    return [{"op": "color.ajuste", "clave": clave, "delta": PASO_COLOR * signo * (-1 if baja else 1)}]


def _regla_reemplazar(c: _Ctx):
    q, w = _COMILLAS, r"(\S+)"
    patrones = [
        rf"(?:cambi|reemplaz|sustitu|pon)\w*\W+(?:la palabra |el texto |donde dice )?{q}(.+?){_CIERRE}\s+por\s+{q}(.+?){_CIERRE}",
        rf"(?:donde dice|en vez de)\s+{q}(.+?){_CIERRE}\W+(?:que diga|pon\w*|poner)\s+{q}(.+?){_CIERRE}",
        rf"(?:cambi|reemplaz|sustitu)\w*\s+{w}\s+por\s+{w}",
    ]
    for pat in patrones:
        m = re.search(pat, c.plano)
        if m:
            x, y = (c.texto[m.start(k):m.end(k)] for k in (1, 2))
            return _reemplazo(c, x.strip(".,;:¿?¡!"), y.strip(".,;:¿?¡!"))
    m = re.search(r"que diga:?\s*(.+)$", c.plano)
    if m and c.t is not None:
        y = c.texto[m.start(1):m.end(1)].strip().strip("«»\"“”'.")
        pool = c.activos(True)
        if len(pool) == 1 and len(capas.textos_de(pool[0])) == 1:
            return [{"op": "texto.editar", "id": pool[0]["id"], "texto": y}]
    return None


def _reemplazo(c: _Ctx, x: str, y: str):
    if not x or not y:
        return None
    ops = []
    cerca = [e for e in c.sb.get("elementos", []) if isinstance(e, dict) and (c.t is None or capas._activo(e, c.t, 1.0))]
    for e in cerca or c.sb.get("elementos", []):
        for i, t in capas.textos_de(e):
            if _plano(x) in _plano(t):
                nuevo = re.sub(re.escape(x), y, t, flags=re.I)
                ops.append({"op": "texto.editar", "id": e["id"], "linea": i, "texto": nuevo})
    for i, p in enumerate(c.pal):
        nucleo = p["w"].strip("¿?¡!.,;:")
        if nucleo and _plano(nucleo) == _plano(x) and (c.t is None or abs((p["s"] + p["e"]) / 2 - c.t) <= 3.0):
            ops.append({"op": "subtitulo.palabra", "indice": i, "texto": p["w"].replace(nucleo, y)})
    return ops or None


def _regla_color_texto(c: _Ctx):
    if not c.dice(*_TEXTO):
        return None
    m = re.search(r"\b(" + "|".join(COLORES) + r")\b", c.plano)
    if not m or not c.dice("pon", "cambi", "haz", "hace", "que sea", "en ", "de color"):
        return None
    e = _objetivo(c)
    if e is None or e.get("tipo") != "texto":
        return None
    return [{"op": "texto.estilo", "id": e["id"], "color": COLORES[m.group(1)]}]


def _regla_tamano(c: _Ctx):
    if not c.dice(*_TEXTO) or c.dice("musica", "volumen", "efecto", "subtitul"):
        return None
    mucho = c.dice("mucho", "bastante", "el doble")
    if c.dice("grande", "agrand", "aument", "mas grueso"):
        factor = PASO_TAM_MUCHO if mucho else PASO_TAM
    elif c.dice("chico", "pequen", "achic", "reduc", "disminu"):
        factor = round(1 / PASO_TAM_MUCHO, 2) if mucho else round(1 / PASO_TAM, 2)
    else:
        return None
    e = _objetivo(c)
    return [{"op": "escalar", "id": e["id"], "factor": factor}] if e and e.get("tipo") in ("texto", "etiqueta") else None


def _regla_mover(c: _Ctx):
    if not c.dice(*_TEXTO, *_GRAFICO) or c.dice("musica", "volumen", "efecto", "subtitul", "palabra"):
        return None
    ejes = {"arriba": ("dy", -PASO_MOVER), "abajo": ("dy", PASO_MOVER), "izquierda": ("dx", -PASO_MOVER), "derecha": ("dx", PASO_MOVER)}  # «subí/bajá» solos = arriba/abajo
    m = re.search(r"\b(" + "|".join(ejes) + r"|sub\w*|baj\w*)\b", c.plano)
    if not m or (m.group(1) not in ejes and c.dice("grande", "chico", "pequen", "agrand", "achic")):
        return None
    eje, paso = ejes.get(m.group(1)) or ("dy", -PASO_MOVER if m.group(1).startswith("sub") else PASO_MOVER)
    e = _objetivo(c)
    return [{"op": "mover", "id": e["id"], eje: paso}] if e else None


def _regla_borrar(c: _Ctx):
    if not c.dice("sac", "quit", "borr", "elimin") or c.dice("subtitul", "palabra", "golpe", "zoom", "efecto", "musica", "corte"):
        return None
    if not (c.dice(*_TEXTO, *_GRAFICO) or c.citas):
        return None
    e = _objetivo(c)
    return [{"op": "borrar", "id": e["id"]}] if e else None


REGLAS = (_regla_subtitulo_ocultar, _regla_quitar_palabra, _regla_camara, _regla_sonido, _regla_color_video, _regla_reemplazar,
          _regla_color_texto, _regla_tamano, _regla_mover, _regla_borrar)


def por_reglas(sb: dict, pal: list, texto: str, segundo=None):
    """ops | {"derivar": ...} | None (ninguna regla lo resuelve)."""
    c = _Ctx(sb, pal, texto, segundo)
    if _GUSTO.search(c.plano):
        return {"derivar": "agente", "motivo": "mezcla un gusto general ('siempre', 'en todos…') que no es de una capa"}
    for regla in REGLAS:
        r = regla(c)
        if r:
            return r
    return None


# ---------------------------------------------------------------- la llamada chica

def _prompt(sb, pal, texto, segundo) -> str:
    c = _Ctx(sb, pal, texto, segundo)
    if c.t is not None:
        contexto = {"segundo_final": segundo, "capas_en_ese_momento": capas.vista(sb, pal, c.t)}
    else:
        contexto = {"sin_segundo": True, "textos_del_video": [capas._resumen_elemento(e) for e in sb.get("elementos", [])
                                                              if isinstance(e, dict) and e.get("tipo") in ("texto", "etiqueta")]}
    return ("Eres el intérprete de correcciones de un editor de video por capas. NO editas nada: solo traduces la corrección de Pablo "
            "a operaciones del catálogo. Responde SOLO un objeto JSON, sin texto alrededor.\n\n"
            f"Catálogo de operaciones (los tiempos t0/t1/t son segundos del video FUENTE, como en las capas):\n{capas.catalogo_texto()}\n\n"
            f"Corrección de Pablo: «{texto}»\n"
            f"Contexto: {json.dumps(contexto, ensure_ascii=False, separators=(',', ':'))}\n\n"
            'Formas válidas de respuesta:\n'
            '1. {"operaciones":[{"op":"escalar","id":"k1","factor":1.3}]}  (una o varias; ids e índices tomados del contexto)\n'
            '2. {"pregunta":"…"}  si es ambigua (varios elementos posibles, falta el segundo) y no debes adivinar\n'
            '3. {"derivar":"agente","motivo":"…"}  si NO es un cambio de capa (gusto general, falla del sistema, algo que el catálogo no cubre)')


def _gasto(carpeta: Path, antes: int) -> tuple:
    f = Path(carpeta) / "costos.jsonl"
    filas = [json.loads(x) for x in f.read_text().splitlines() if x.strip()][antes:] if f.exists() else []
    return sum(sum(r.get("tokens", {}).values()) for r in filas), round(sum(r.get("usd_equivalente") or 0 for r in filas), 4)


def _filas_costos(carpeta: Path) -> int:
    f = Path(carpeta) / "costos.jsonl"
    return len([x for x in f.read_text().splitlines() if x.strip()]) if f.exists() else 0


def por_ia(carpeta: Path, sb, pal, texto, segundo) -> tuple:
    """(respuesta, tokens, usd): UNA llamada de Sonnet sin herramientas. La respuesta ya viene validada: operaciones | pregunta | derivar."""
    antes = _filas_costos(carpeta)
    try:
        out = ia.llamar(_prompt(sb, pal, texto, segundo), "sonnet", carpeta, herramientas="", tope_usd=TOPE_USD, paso="capas", timeout=TIMEOUT_S)
        crudo = ia.json_de(out.get("result", ""))
    except (RuntimeError, ValueError) as e:
        return {"derivar": "agente", "motivo": f"la llamada chica falló: {str(e)[:160]}"}, *_gasto(carpeta, antes)
    tokens, usd = _gasto(carpeta, antes)
    ops = crudo.get("operaciones")
    if isinstance(ops, list) and 0 < len(ops) <= MAX_OPERACIONES and all(isinstance(o, dict) and o.get("op") in capas.CATALOGO for o in ops):
        return {"operaciones": ops}, tokens, usd
    if isinstance(crudo.get("pregunta"), str) and crudo["pregunta"].strip():
        return {"pregunta": crudo["pregunta"].strip()}, tokens, usd
    return {"derivar": "agente", "motivo": str(crudo.get("motivo") or "la respuesta no fue una operación del catálogo")[:200]}, tokens, usd


# ---------------------------------------------------------------- interpretar y corregir

def interpretar(carpeta, texto: str, segundo=None) -> dict:
    """{"via": reglas|ia, "operaciones"} | {"via", "pregunta"} | {"via", "derivar", "motivo"}, con "tokens" y "usd"."""
    carpeta = Path(carpeta)
    sb, pal = capas._leer(carpeta, "storyboard.json"), capas._leer(carpeta, "palabras.json", [])
    if sb is None:
        return {"via": "derivar", "derivar": "agente", "motivo": "el proyecto no tiene storyboard", "tokens": 0, "usd": 0.0}
    r = por_reglas(sb, pal, texto, segundo)
    if isinstance(r, list):
        return {"via": "reglas", "operaciones": r, "tokens": 0, "usd": 0.0}
    if isinstance(r, dict):
        return {"via": "reglas", **r, "tokens": 0, "usd": 0.0}
    resp, tokens, usd = por_ia(carpeta, sb, pal, texto, segundo)
    return {"via": "ia", **resp, "tokens": tokens, "usd": usd}


def _registrar(carpeta: Path, texto, segundo, plan: dict, estado: str, res: dict | None, segundos: float) -> None:
    fila = {"fecha": datetime.now().isoformat(timespec="seconds"), "texto": texto, "segundo": segundo, "via": plan["via"], "estado": estado,
            "operaciones": res["cambios"] if res else plan.get("operaciones", []), "tramos": res["tramos"] if res else None,
            "pregunta": plan.get("pregunta"), "motivo": plan.get("motivo"), "errores": res["errores"] if res else [],
            "tokens": plan["tokens"], "usd": plan["usd"], "segundos": round(segundos, 2)}
    with open(Path(carpeta) / REGISTRO, "a") as f:
        f.write(json.dumps(fila, ensure_ascii=False, default=str) + "\n")


def corregir(carpeta, texto: str, segundo=None, simular: bool = False) -> dict:
    """Interpreta la corrección y, si es de capa, la aplica (sin renderizar). estado: aplicado | simulado | pregunta | derivar | rechazado.
    `simular` muestra las operaciones sin tocar nada ni registrar."""
    carpeta, t0 = Path(carpeta), time.time()
    plan = interpretar(carpeta, texto, segundo)
    base = {"via": plan["via"], "tokens": plan["tokens"], "usd": plan["usd"]}
    if "operaciones" not in plan:
        estado = "pregunta" if "pregunta" in plan else "derivar"
        if not simular:
            _registrar(carpeta, texto, segundo, plan, estado, None, time.time() - t0)
        return {**base, "estado": estado, **{k: plan[k] for k in ("pregunta", "motivo") if k in plan}}
    if simular:
        return {**base, "estado": "simulado", "operaciones": plan["operaciones"]}
    res = capas.aplicar(carpeta, plan["operaciones"])
    estado = "aplicado" if res["ok"] else "rechazado"
    _registrar(carpeta, texto, segundo, plan, estado, res, time.time() - t0)
    return {**base, "estado": estado, "operaciones": plan["operaciones"], "cambios": res["cambios"], "tramos": res["tramos"],
            "errores": res["errores"]}


def _render(carpeta: Path, avance):
    """Re-exporta por tramos. Compuerta RELATIVA: un video ya aprobado puede tener avisos de reglas que nacieron después (p. ej. la
    «cámara viva» del 08-nov); una corrección de capa no los arregla ni los empeora (`capas.aplicar` ya rechaza todo cambio que sume
    errores nuevos), así que no bloquea re-exportar ESE video. Si la compuerta completa pasa, se usa la normal."""
    from . import motor
    try:
        return motor.render(carpeta, avance=avance)
    except ValueError as e:
        if not str(e).startswith("la compuerta no deja renderizar") or not _sin_errores_nuevos(carpeta):
            raise
        avance("capas: el video trae avisos de antes (no los sumó esta corrección); se re-exporta con la compuerta relativa")
        return motor.render(carpeta, avance=avance, forzar=True)


def _sin_errores_nuevos(carpeta: Path) -> bool:
    """La última corrección aplicada en este proyecto dejó los mismos errores de compuerta que había antes (o menos)."""
    f = Path(carpeta) / "capas.jsonl"
    if not f.exists():
        return False
    for linea in reversed(f.read_text().splitlines()):
        r = json.loads(linea)
        if r.get("estado") in ("aplicado", "rechazado"):
            return r["estado"] == "aplicado" and not r.get("errores")   # «aplicado» = capas.aplicar ya comprobó que no sumó errores
    return False


def resumen(r: dict) -> str:
    if r["estado"] == "pregunta":
        return f"Antes de tocar nada: {r['pregunta']}"
    ops = ", ".join(c["op"] for c in r.get("cambios", []))
    return f"Corrección por capas ({'reglas' if r['via'] == 'reglas' else 'una llamada chica'}, {r['tokens']} tokens): {ops}"


def intentar(carpeta, texto: str, segundo=None, avance=print):
    """Lo que usa /api/corregir: corrige por capas y re-exporta por tramos. Devuelve el resultado, o None si hay que ir al Agente Editor
    (no es de capa, la compuerta lo rechazó o el render falló: en ese caso se deshace y no queda nada cambiado)."""
    r = corregir(carpeta, texto, segundo)
    if r["estado"] == "pregunta":
        return {"id": "capas", "resumen": resumen(r), **r}
    if r["estado"] != "aplicado":
        avance(f"Capas no resuelve esto ({r.get('motivo') or '; '.join(r.get('errores', []))[:200] or r['estado']}): va al Agente Editor.")
        return None
    avance(f"{resumen(r)}. Exportando solo los tramos que cambiaron…")
    try:
        _render(Path(carpeta), avance)
    except Exception as e:  # noqa: BLE001 — cualquier falla del render deja el proyecto como estaba y pasa al agente
        capas.deshacer(carpeta)
        avance(f"El render no aceptó el cambio ({str(e)[:160]}): se deshizo y va al Agente Editor.")
        return None
    return {"id": "capas", "resumen": resumen(r), **r}
