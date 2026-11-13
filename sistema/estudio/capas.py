"""Editor por capas (docs/PLANO-EDITOR-CAPAS.md, Pablo 09-nov): una corrección de capa cambia SOLO su pieza del storyboard, sin IA y sin
rehacer nada más. Es aditivo: lee y escribe `storyboard.json`/`palabras.json`, valida con `validar.py` y mide qué tramos tocó con
`tramos.py`, sin modificar ninguno de los dos.

  · `vista(...)`: qué hay en un segundo (elementos, trazos, subtítulos, cortes, cámara, estilo), en JSON compacto.
  · `CATALOGO`: las operaciones cerradas. Cada una cambia solo su pieza y devuelve (antes, después).
  · `aplicar(...)`: aplica varias operaciones juntas o ninguna; una operación que deje errores NUEVOS de `validar.errores` no entra.
    Guarda el estado anterior (un paso, `capas-deshacer.json` en el proyecto) y devuelve los tramos de salida afectados.
  · `deshacer(...)`: vuelve al estado guardado.
Los tiempos del storyboard son segundos del video FUENTE; `fuente_de` pasa de segundos del video final a fuente.
"""
import copy
import json
import re
from pathlib import Path

from . import config

DESHACER = "capas-deshacer.json"
FACTOR_MIN, FACTOR_MAX = 0.2, 5.0
AJUSTE_COLOR_MAX = 1.0


class OperacionInvalida(ValueError):
    """La operación no se puede aplicar tal como llegó (id que no existe, parámetro fuera de rango…): no cambia nada."""


# ---------------------------------------------------------------- lectura

def _leer(carpeta: Path, nombre: str, defecto=None):
    f = Path(carpeta) / nombre
    return json.loads(f.read_text()) if f.exists() else defecto


def fuente_de(sb: dict, t_salida: float) -> float:
    """Segundo del video FUENTE que corresponde a un segundo del video final (los cortes quitan tramos de la fuente)."""
    t = float(t_salida)
    for a, b in sorted(sb.get("cortes", [])):
        if a <= t:
            t += b - a
        else:
            break
    return t


def salida_de(sb: dict, t_fuente: float) -> float:
    """Segundo del video final que corresponde a un segundo de la fuente (al revés de `fuente_de`)."""
    quitado = sum(min(b, t_fuente) - a for a, b in sorted(sb.get("cortes", [])) if a < t_fuente)
    return t_fuente - quitado


def _activo(x: dict, t: float, margen: float = 0.0) -> bool:
    t0, t1 = x.get("t0"), x.get("t1")
    return isinstance(t0, (int, float)) and isinstance(t1, (int, float)) and t0 - margen <= t <= t1 + margen


def textos_de(e: dict) -> list:
    """Los textos de un elemento: [(línea, texto)]. Las líneas de `texto` son dicts; las de `etiqueta`, listas [texto, tam, cursiva, peso]."""
    out = []
    for i, ln in enumerate(e.get("lineas") or []):
        t = ln.get("texto") if isinstance(ln, dict) else ln[0] if isinstance(ln, list) and ln else None
        if isinstance(t, str):
            out.append((i, t))
    return out


def _resumen_elemento(e: dict) -> dict:
    r = {k: e[k] for k in ("id", "tipo", "x", "y", "t0", "t1", "ancho") if k in e}
    if e.get("tipo") in ("texto", "etiqueta"):
        r["texto"] = " / ".join(t for _, t in textos_de(e))
        ln = (e.get("lineas") or [None])[0]
        r["tam"] = ln.get("tam") if isinstance(ln, dict) else ln[1] if isinstance(ln, list) and len(ln) > 1 else None
        if isinstance(ln, dict) and ln.get("color"):
            r["color"] = ln["color"]
    elif e.get("src"):
        r["src"] = e["src"]
    return r


def vista(sb: dict, palabras: list, t_fuente: float, ventana: float = 1.5) -> dict:
    """Lo que hay en `t_fuente` (y a ±`ventana` s para palabras, cortes y cámara), compacto para mostrarlo o dárselo a la IA."""
    t = float(t_fuente)
    els = [_resumen_elemento(e) for e in sb.get("elementos", []) if isinstance(e, dict) and _activo(e, t)]
    trazos = [{"n": i, **{k: x[k] for k in ("tipo", "sobre", "t0", "t1") if k in x}}
              for i, x in enumerate(sb.get("trazos", [])) if isinstance(x, dict) and _activo(x, t)]
    cerca = [(i, p) for i, p in enumerate(palabras) if p["e"] >= t - ventana and p["s"] <= t + ventana]
    sub = sb.get("subtitulos", {})
    estilo = sb.get("estilo", {})
    return {
        "t_fuente": round(t, 2), "t_final": round(salida_de(sb, t), 2),
        "elementos": els, "trazos": trazos,
        "subtitulos": {"palabras": [{"i": i, "w": p["w"], "s": p["s"], "clave": i in sub.get("resaltar", [])} for i, p in cerca],
                       "ocultos": [r for r in sub.get("ocultar", []) if r[0] - ventana <= t <= r[1] + ventana]},
        "cortes": [c for c in sb.get("cortes", []) if c[1] >= t - ventana and c[0] <= t + ventana],
        "camara": {"golpes": [g for g in sb.get("punch", []) if abs((g[0] if isinstance(g, list) else g) - t) <= ventana + 1],
                   "claves": [c for c in (sb.get("camara") or []) if isinstance(c, dict) and abs(c.get("t", -99) - t) <= ventana + 2]},
        "estilo": {k: estilo[k] for k in ("id", "acento", "tinta", "papel", "fuente", "sfx", "color") if k in estilo},
    }


# ---------------------------------------------------------------- operaciones

def _elemento(sb: dict, id_: str) -> dict:
    e = next((x for x in sb.get("elementos", []) if isinstance(x, dict) and x.get("id") == id_), None)
    if e is None:
        raise OperacionInvalida(f"no hay un elemento con id {id_!r}")
    return e


def _trazo(sb: dict, n) -> dict:
    try:
        return sb["trazos"][int(n)]
    except (KeyError, IndexError, TypeError, ValueError):
        raise OperacionInvalida(f"no hay un trazo número {n!r}") from None


def _pieza(sb: dict, id=None, trazo=None) -> dict:
    return _trazo(sb, trazo) if trazo is not None else _elemento(sb, id)


def _numero(v, nombre: str) -> float:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise OperacionInvalida(f"{nombre} debe ser un número, llegó {v!r}")
    return float(v)


def _factor(v) -> float:
    f = _numero(v, "factor")
    if not FACTOR_MIN <= f <= FACTOR_MAX:
        raise OperacionInvalida(f"factor {f} fuera de {FACTOR_MIN}–{FACTOR_MAX}")
    return f


def _texto_op(v, nombre="texto") -> str:
    if not isinstance(v, str) or not v.strip():
        raise OperacionInvalida(f"{nombre} no puede estar vacío")
    return v


def _linea(e: dict, n: int):
    ls = e.get("lineas") or []
    if e.get("tipo") not in ("texto", "etiqueta") or not 0 <= n < len(ls):
        raise OperacionInvalida(f"{e.get('id')!r} no tiene la línea {n} de texto")
    return ls[n]


def op_texto_editar(sb, pal, id, texto, linea=0):
    e = _elemento(sb, id)
    ln = _linea(e, int(linea))
    antes = dict(textos_de(e)).get(int(linea))
    if isinstance(ln, dict):
        ln["texto"] = _texto_op(texto)
    else:
        ln[0] = _texto_op(texto)
    return antes, texto


def op_texto_estilo(sb, pal, id, linea=None, tam=None, color=None, peso=None, factor=None):
    e = _elemento(sb, id)
    if e.get("tipo") not in ("texto", "etiqueta"):
        raise OperacionInvalida(f"{id!r} no es un texto")
    idx = range(len(e.get("lineas") or [])) if linea is None else [int(linea)]
    antes, despues = [], []
    for i in idx:
        ln = _linea(e, i)
        a = copy.deepcopy(ln)
        if isinstance(ln, dict):
            if factor is not None:
                ln["tam"] = max(8, round(ln.get("tam", 60) * _factor(factor)))
            if tam is not None:
                ln["tam"] = round(_numero(tam, "tam"))
            if color is not None:
                ln["color"] = _texto_op(color, "color")
            if peso is not None:
                ln["peso"] = round(_numero(peso, "peso"))
        else:          # etiqueta: [texto, tam, cursiva, peso]; el color es el de la caja, no de la línea
            if color is not None:
                raise OperacionInvalida("el color de una etiqueta es el de su caja (estilo), no de la línea")
            while len(ln) < 4:
                ln.append(False if len(ln) == 2 else 700)
            if factor is not None:
                ln[1] = max(8, round(ln[1] * _factor(factor)))
            if tam is not None:
                ln[1] = round(_numero(tam, "tam"))
            if peso is not None:
                ln[3] = round(_numero(peso, "peso"))
        antes.append(a)
        despues.append(copy.deepcopy(ln))
    return antes, despues


def op_mover(sb, pal, id=None, trazo=None, dx=None, dy=None, x=None, y=None):
    if trazo is not None:
        raise OperacionInvalida("los trazos siguen a su elemento: mové el elemento")
    e = _elemento(sb, id)
    antes = {"x": e.get("x"), "y": e.get("y")}
    if x is not None:
        e["x"] = round(_numero(x, "x"))
    if y is not None:
        e["y"] = round(_numero(y, "y"))
    if dx is not None:
        e["x"] = round(e.get("x", 540) + _numero(dx, "dx"))
    if dy is not None:
        e["y"] = round(e.get("y", 960) + _numero(dy, "dy"))
    if (x, y, dx, dy) == (None,) * 4:
        raise OperacionInvalida("mover necesita dx, dy, x o y")
    return antes, {"x": e.get("x"), "y": e.get("y")}


def op_escalar(sb, pal, id, factor):
    e, f = _elemento(sb, id), _factor(factor)
    if e.get("tipo") in ("texto", "etiqueta"):
        return op_texto_estilo(sb, pal, id, factor=f)
    if not isinstance(e.get("ancho"), (int, float)):
        raise OperacionInvalida(f"{id!r} no tiene tamaño (ancho) que escalar")
    antes = e["ancho"]
    e["ancho"] = round(antes * f)
    return antes, e["ancho"]


def op_tiempo(sb, pal, id=None, trazo=None, t0=None, t1=None, corrimiento=None):
    p = _pieza(sb, id, trazo)
    antes = {"t0": p.get("t0"), "t1": p.get("t1")}
    if corrimiento is not None:
        c = _numero(corrimiento, "corrimiento")
        p["t0"], p["t1"] = round(p["t0"] + c, 3), round(p["t1"] + c, 3)
    if t0 is not None:
        p["t0"] = round(_numero(t0, "t0"), 3)
    if t1 is not None:
        p["t1"] = round(_numero(t1, "t1"), 3)
    if (t0, t1, corrimiento) == (None,) * 3:
        raise OperacionInvalida("tiempo necesita t0, t1 o corrimiento")
    if p["t0"] < 0 or p["t1"] <= p["t0"]:
        raise OperacionInvalida(f"tiempo inválido: {p['t0']}–{p['t1']}")
    return antes, {"t0": p["t0"], "t1": p["t1"]}


def op_borrar(sb, pal, id=None, trazo=None):
    if trazo is not None:
        t = _trazo(sb, trazo)
        sb["trazos"].remove(t)
        return t, None
    e = _elemento(sb, id)
    sb["elementos"].remove(e)
    huerfanos = [t for t in sb.get("trazos", []) if isinstance(t, dict) and t.get("sobre") == id]
    sb["trazos"] = [t for t in sb.get("trazos", []) if t not in huerfanos]    # un trazo «sobre» un elemento que ya no existe no vale
    return {"elemento": e, "trazos": huerfanos}, None


def op_agregar_texto(sb, pal, texto, t0, t1, x=540, y=800, tam=90, color=None, peso=800, entra="pop", id=None):
    _texto_op(texto)
    est = sb.get("estilo", {})
    nuevo_id = id or next(f"cap{n}" for n in range(1, 10_000) if all(e.get("id") != f"cap{n}" for e in sb.get("elementos", [])))
    if any(e.get("id") == nuevo_id for e in sb.get("elementos", [])):
        raise OperacionInvalida(f"ya existe un elemento {nuevo_id!r}")
    e = {"id": nuevo_id, "tipo": "texto", "z": "frente", "x": round(_numero(x, "x")), "y": round(_numero(y, "y")),
         "t0": round(_numero(t0, "t0"), 3), "t1": round(_numero(t1, "t1"), 3), "entra": entra, "dur": 0.3, "sombra": True,
         "lineas": [{"texto": texto, "rol": "display", "tam": round(_numero(tam, "tam")), "color": color or est.get("papel", "#FFFFFF"),
                     "peso": round(_numero(peso, "peso"))}]}
    if e["t1"] <= e["t0"]:
        raise OperacionInvalida("el texto nuevo debe terminar después de empezar")
    sb.setdefault("elementos", []).append(e)
    return None, e


def op_subtitulo_palabra(sb, pal, indice, texto):
    i = int(indice)
    if not 0 <= i < len(pal):
        raise OperacionInvalida(f"no hay palabra número {i}")
    antes = pal[i]["w"]
    pal[i]["w"] = _texto_op(texto)
    return antes, pal[i]["w"]


def op_subtitulo_ocultar(sb, pal, t0, t1):
    a, b = round(_numero(t0, "t0"), 3), round(_numero(t1, "t1"), 3)
    if b <= a:
        raise OperacionInvalida("ocultar: t1 debe ser mayor que t0")
    sb.setdefault("subtitulos", {}).setdefault("ocultar", []).append([a, b])
    return None, [a, b]


def op_camara_golpe(sb, pal, t):
    from . import camara
    if camara.fija():
        raise OperacionInvalida("la cámara es fija en todo el editor (regla de Pablo, 11-nov): no hay golpes de zoom")
    t = round(_numero(t, "t"), 3)
    sb["punch"] = sorted(set(list(sb.get("punch", [])) + [t]))
    return None, t


def op_camara_quitar(sb, pal, t, tolerancia=0.6):
    t, tol = _numero(t, "t"), _numero(tolerancia, "tolerancia")
    punch = [g for g in sb.get("punch", []) if abs((g[0] if isinstance(g, list) else g) - t) <= tol]
    claves = [c for c in (sb.get("camara") or []) if isinstance(c, dict) and abs(c.get("t", -99) - t) <= tol]
    if not punch and not claves:
        raise OperacionInvalida(f"no hay golpe ni movimiento de cámara cerca del segundo {t}")
    sb["punch"] = [g for g in sb.get("punch", []) if g not in punch]
    if claves:
        sb["camara"] = [c for c in sb["camara"] if c not in claves]
    return {"golpes": punch, "claves": claves}, None


def op_color_ajuste(sb, pal, clave, valor=None, delta=None):
    from . import color
    if clave not in color.AJUSTES:
        raise OperacionInvalida(f"ajuste de color desconocido: {clave!r} (hay: {', '.join(color.AJUSTES)})")
    aj = sb.setdefault("estilo", {}).setdefault("color", {}).setdefault("ajustes", {})
    antes = aj.get(clave, 0)
    nuevo = _numero(valor, "valor") if valor is not None else antes + _numero(delta, "delta") if delta is not None else None
    if nuevo is None:
        raise OperacionInvalida("color.ajuste necesita valor o delta")
    aj[clave] = round(max(-AJUSTE_COLOR_MAX, min(AJUSTE_COLOR_MAX, nuevo)), 3)
    return antes, aj[clave]


def op_sonido_volumen(sb, pal, que="sfx", valor=None, factor=None):
    if que != "sfx":
        raise OperacionInvalida("el storyboard no guarda volumen de música; solo el de los efectos (que='sfx')")
    est = sb.setdefault("estilo", {})
    antes = est.get("sfx", config.SFX_VOLUMEN)
    nuevo = _numero(valor, "valor") if valor is not None else antes * _factor(factor) if factor is not None else None
    if nuevo is None:
        raise OperacionInvalida("sonido.volumen necesita valor o factor")
    est["sfx"] = round(max(0.0, min(1.0, nuevo)), 3)
    return antes, est["sfx"]


def _rango_palabras(pal, indices, t0, t1) -> tuple:
    if indices:
        ii = [int(i) for i in indices]
        if any(not 0 <= i < len(pal) for i in ii):
            raise OperacionInvalida("palabra que no existe")
        return min(pal[i]["s"] for i in ii), max(pal[i]["e"] for i in ii)
    if t0 is None or t1 is None:
        raise OperacionInvalida("hace falta indices o t0 y t1")
    return round(_numero(t0, "t0"), 3), round(_numero(t1, "t1"), 3)


def _unir(cortes: list) -> list:
    out = []
    for a, b in sorted([list(c) for c in cortes]):
        if out and a <= out[-1][1] + 1e-6:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out


def op_corte_quitar(sb, pal, indices=None, t0=None, t1=None):
    a, b = _rango_palabras(pal, indices, t0, t1)
    if b <= a:
        raise OperacionInvalida("el corte debe tener duración")
    antes = copy.deepcopy(sb.get("cortes", []))
    sb["cortes"] = _unir(antes + [[a, b]])
    return antes, sb["cortes"]


def op_corte_restaurar(sb, pal, indices=None, t0=None, t1=None):
    a, b = _rango_palabras(pal, indices, t0, t1)
    antes, nuevo = copy.deepcopy(sb.get("cortes", [])), []
    for c0, c1 in antes:
        if c1 <= a or c0 >= b:
            nuevo.append([c0, c1])
            continue
        if c0 < a:
            nuevo.append([c0, a])
        if c1 > b:
            nuevo.append([b, c1])
    if nuevo == antes:
        raise OperacionInvalida("ahí no hay ningún corte que restaurar")
    sb["cortes"] = nuevo
    return antes, nuevo


# nombre → (función, descripción para la IA y la ayuda)
CATALOGO = {
    "texto.editar": (op_texto_editar, "id, texto, linea=0: cambia lo que dice un texto o etiqueta"),
    "texto.estilo": (op_texto_estilo, "id, linea=todas, tam | factor, color (#hex), peso: tamaño, color o peso de un texto"),
    "mover": (op_mover, "id, dx, dy (px relativos) o x, y (px absolutos): mueve un elemento"),
    "escalar": (op_escalar, "id, factor (0.2–5): agranda o achica un elemento o texto"),
    "tiempo": (op_tiempo, "id | trazo, t0, t1, corrimiento (s FUENTE): cuándo entra y sale una pieza"),
    "borrar": (op_borrar, "id | trazo: quita un elemento (y los trazos sobre él) o un trazo"),
    "agregar_texto": (op_agregar_texto, "texto, t0, t1, x=540, y=800, tam=90, color, peso=800, entra=pop: texto nuevo"),
    "subtitulo.palabra": (op_subtitulo_palabra, "indice, texto: cambia cómo se escribe una palabra del subtítulo"),
    "subtitulo.ocultar": (op_subtitulo_ocultar, "t0, t1: sin subtítulos en ese tramo"),
    "camara.golpe": (op_camara_golpe, "t: acercamiento de énfasis en ese segundo"),
    "camara.quitar": (op_camara_quitar, "t, tolerancia=0.6: quita el golpe o movimiento de cámara de ese segundo"),
    "color.ajuste": (op_color_ajuste, "clave (exposicion|contraste|saturacion|temperatura|tinte), valor | delta (-1…1)"),
    "sonido.volumen": (op_sonido_volumen, "que='sfx', valor (0–1) | factor: volumen de los efectos de sonido"),
    "corte.quitar": (op_corte_quitar, "indices (de palabras) o t0, t1: sacar ese tramo del video"),
    "corte.restaurar": (op_corte_restaurar, "indices (de palabras) o t0, t1: devolver lo que estaba cortado ahí"),
}


def catalogo_texto() -> str:
    return "\n".join(f"- {n}: {d}" for n, (_, d) in CATALOGO.items())


# ---------------------------------------------------------------- aplicar / deshacer

def _norma_error(e: str) -> str:
    return re.sub(r"\[\d+\]", "[]", e)       # borrar un elemento corre los índices: el mismo error no es uno nuevo


def _errores(sb: dict, carpeta: Path) -> list:
    from . import validar
    return validar.errores(sb, Path(carpeta))


def _claves_tramos(carpeta: Path, sb: dict, palabras: list) -> list:
    """Claves de tramos de `tramos.claves` sobre un proyecto liviano (sin video ni imágenes): solo para saber qué tramos cambian."""
    from . import camara, tramos
    meta = _leer(carpeta, "fuente.json", {})
    quitar = set()
    for a, b in sb.get("cortes", []):
        quitar.update(range(round(a * config.FPS), round(b * config.FPS)))
    mapa = [i for i in range(int(meta.get("cuadros", 0))) if i not in quitar]
    p = type("P", (), {"sb": sb, "mapa": mapa, "ruta": camara.Ruta(sb, len(mapa) / config.FPS), "dir": Path(carpeta), "meta": meta,
                       "palabras": palabras, "cubo": None})()
    return tramos.claves(p)


def tramos_afectados(carpeta: Path, sb0: dict, pal0: list, sb1: dict, pal1: list):
    """Segundos de SALIDA [a, b] cuyos tramos cambian de clave entre los dos estados; "todos" si cambia lo global; None si no se pudo medir."""
    try:
        antes, despues = _claves_tramos(carpeta, sb0, pal0), _claves_tramos(carpeta, sb1, pal1)
    except (OSError, ValueError, KeyError):
        return None
    if len(antes) != len(despues) or all(x[2] != y[2] for x, y in zip(antes, despues)):
        return "todos"
    fps = config.FPS
    return [[a / fps, b / fps] for (a, b, k), (_, _, k2) in zip(despues, antes) if k != k2]


def _guardar(carpeta: Path, sb: dict, pal: list, cambia_pal: bool) -> None:
    Path(carpeta, "storyboard.json").write_text(json.dumps(sb, ensure_ascii=False, indent=1))
    if cambia_pal:
        Path(carpeta, "palabras.json").write_text(json.dumps(pal, ensure_ascii=False, indent=1))


def aplicar(carpeta, operaciones: list) -> dict:
    """Aplica juntas `operaciones` ([{"op": nombre, ...parámetros}]) o ninguna.
    Devuelve {"ok", "cambios": [{op, antes, despues}], "tramos", "errores"}. `ok` False = no se tocó nada (`errores` dice por qué)."""
    carpeta = Path(carpeta)
    sb0, pal0 = _leer(carpeta, "storyboard.json"), _leer(carpeta, "palabras.json", [])
    if sb0 is None:
        return {"ok": False, "cambios": [], "tramos": None, "errores": ["el proyecto no tiene storyboard.json"]}
    if not operaciones:
        return {"ok": False, "cambios": [], "tramos": None, "errores": ["no hay operaciones"]}
    sb, pal, cambios = copy.deepcopy(sb0), copy.deepcopy(pal0), []
    for o in operaciones:
        nombre, params = o.get("op"), {k: v for k, v in o.items() if k != "op"}
        if nombre not in CATALOGO:
            return {"ok": False, "cambios": cambios, "tramos": None, "errores": [f"la operación {nombre!r} no existe"]}
        try:
            antes, despues = CATALOGO[nombre][0](sb, pal, **params)
        except OperacionInvalida as e:
            return {"ok": False, "cambios": cambios, "tramos": None, "errores": [f"{nombre}: {e}"]}
        except TypeError as e:           # parámetros que no son de esa operación
            return {"ok": False, "cambios": cambios, "tramos": None, "errores": [f"{nombre}: parámetros inválidos ({e})"]}
        cambios.append({"op": nombre, "antes": antes, "despues": despues})
    previos = {_norma_error(e) for e in _errores(sb0, carpeta)}
    nuevos = [e for e in _errores(sb, carpeta) if _norma_error(e) not in previos]
    if nuevos:
        return {"ok": False, "cambios": cambios, "tramos": None, "errores": nuevos}
    cambia_pal = pal != pal0
    (carpeta / DESHACER).write_text(json.dumps({"storyboard": sb0, "palabras": pal0 if cambia_pal else None}, ensure_ascii=False))
    _guardar(carpeta, sb, pal, cambia_pal)
    return {"ok": True, "cambios": cambios, "tramos": tramos_afectados(carpeta, sb0, pal0, sb, pal), "errores": []}


def deshacer(carpeta) -> dict:
    """Vuelve al estado anterior a la última corrección de capas (un paso). {"ok": False} si no hay nada que deshacer."""
    carpeta = Path(carpeta)
    f = carpeta / DESHACER
    if not f.exists():
        return {"ok": False, "error": "no hay nada que deshacer"}
    guardado = json.loads(f.read_text())
    sb0, pal0 = _leer(carpeta, "storyboard.json"), _leer(carpeta, "palabras.json", [])
    pal1 = guardado["palabras"] if guardado["palabras"] is not None else pal0
    _guardar(carpeta, guardado["storyboard"], pal1, guardado["palabras"] is not None)
    f.unlink()
    return {"ok": True, "tramos": tramos_afectados(carpeta, sb0, pal0, guardado["storyboard"], pal1)}
