"""Opciones del subtítulo para TODOS los tipos (tira, hud, vidrio, basico): una sola definición y una sola validación.

Claves de `estilo` (se cambian en Personalizar → Subtítulos o por `preferencias.json`):
  sub_caja (sí/no) · sub_color (texto) · sub_clave (palabra clave) · sub_caja_color · sub_efecto (corte | pop | sube) · sub_fuente (tipografía)
Sin elegir nada (`None`) cada tipo se dibuja como siempre; lo que cada tipo hace con cada clave está en `SOPORTE`, y lo que no admite
lleva su motivo (la pantalla lo muestra apagado con esa línea)."""
import json
import math
import re

from . import config

CLAVES = ("sub_caja", "sub_color", "sub_clave", "sub_caja_color", "sub_efecto", "sub_fuente")
EFECTOS = ("corte", "pop", "sube")
SIN_VALOR_DE_SERIE = ("sub_fuente",)   # sin elegir usa la tipografía de títulos del estilo: el preset no tiene que declararla
EFECTO_NOMBRE = {"corte": "Corte", "pop": "Pop", "sube": "Sube"}
_HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")

# tipo → clave → None (la admite) | motivo (no la admite)
SOPORTE = {
    "tira": {k: None for k in CLAVES},
    "vidrio": {k: None for k in CLAVES},
    "basico": {k: None for k in CLAVES},
    "hud": {**{k: None for k in CLAVES},
            "sub_caja": "El HUD es palabra a palabra sin caja: para una caja elige Tira o Vidrio.",
            "sub_caja_color": "El HUD no tiene caja: no hay color de caja."},
}
NOMBRE = {"tira": "Tira", "vidrio": "Vidrio", "hud": "HUD", "basico": "Básico"}
FORMAS = ("tira", "vidrio", "hud")   # las que se eligen en Personalizar (Básico es un estilo entero, no una forma)
CAJA_DEFECTO = {"tira": True, "vidrio": True, "hud": False, "basico": False}   # con `sub_caja` sin elegir
# lo que significa cada clave en cada tipo, cuando no es lo obvio
NOTAS = {("tira", "sub_clave"): "En la Tira pinta el bloque que resalta la palabra clave.",
         ("vidrio", "sub_caja_color"): "En el Vidrio es el tinte del cristal."}


def error(k: str, v):
    """Mensaje si `v` no vale para la clave `k` (None si vale). La única validación de las claves sub_*."""
    if k in ("sub_color", "sub_clave", "sub_caja_color"):
        from .validar import es_rosa
        if not (isinstance(v, str) and _HEX.match(v)) or es_rosa(v):
            return f"{k}: {v!r} no es un color válido (#RRGGBB, sin rosa)"
    elif k == "sub_caja":
        if not isinstance(v, bool):
            return "sub_caja: sí o no"
    elif k == "sub_efecto":
        if v not in EFECTOS:
            return f"sub_efecto: {v!r} no existe (hay: {', '.join(EFECTOS)})"
    elif k == "sub_fuente":
        if v not in json.loads((config.FUENTES / "indice.json").read_text()):
            return f"sub_fuente: la fuente {v!r} no está instalada"
    else:
        return f"{k}: no es una opción del subtítulo"
    return None


def errores(est: dict) -> list:
    return [m for k in CLAVES if k in est and (m := error(k, est[k]))]


def soporte(tipo: str) -> dict:
    """{clave: motivo o None} para la pantalla: lo que el tipo no admite sale apagado con su motivo."""
    return {k: m for k, m in SOPORTE.get(tipo, SOPORTE["tira"]).items()}


def para_pantalla() -> dict:
    """Lo que Personalizar necesita para armar la sección Subtítulos: por tipo, qué admite (clave → None | motivo), la caja de siempre y las notas."""
    return {"efectos": [{"id": e, "nombre": EFECTO_NOMBRE[e]} for e in EFECTOS],
            "tipos": {t: {"nombre": NOMBRE[t], "forma": t in FORMAS, "soporte": soporte(t), "caja": CAJA_DEFECTO[t], "notas": {k: n for (tt, k), n in NOTAS.items() if tt == t}} for t in SOPORTE}}


def _rgb(c):
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def de_estilo(d: dict) -> dict:
    """Lo elegido en el bloque `estilo`, ya en forma de dibujo; None = «el de siempre» de cada tipo. Valores inválidos se ignoran."""
    def col(k):
        return _rgb(d[k]) if k in d and error(k, d[k]) is None else None
    efecto = d.get("sub_efecto")
    return {"caja": d["sub_caja"] if isinstance(d.get("sub_caja"), bool) else None,
            "color": col("sub_color"), "clave": col("sub_clave"), "caja_color": col("sub_caja_color"),
            "efecto": efecto if efecto in EFECTOS else None,
            "fuente": d["sub_fuente"] if error("sub_fuente", d.get("sub_fuente")) is None else None}


def entrada(efecto: str, p: float, subida: float):
    """(opacidad, desplazamiento y en px, escala) de un bloque en su entrada, `p` de 0 a 1."""
    if efecto == "corte":
        return 1.0, 0, 1.0
    if efecto == "pop":
        return min(1.0, p * 2.5), 0, .86 + .14 * p + .05 * math.sin(p * math.pi)
    return p, subida * (1 - p), 1.0
