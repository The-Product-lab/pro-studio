"""Las dos vistas previas de Personalizar (el ÚNICO camino que las genera): «con la persona» y «apoyo a pantalla completa».

Pablo (10-nov): «la app es muy lenta en mostrar las previas… la de B-roll es muy lenta, aún no muestra nada para escoger».
Causas medidas (ver docs/PLANO-PREVIAS.md): se reconstruía el proyecto entero (158 elementos, ~0,7 s) en cada cambio; un arte que aún
no existe tumbaba las DOS vistas sin decir nada; mientras el director trabaja, la vista rápida nunca dibujaba la segunda vista.

Dos entradas, un mismo dibujo (`pintar`):
- `con_director`: el video ya dirigido (storyboard del director) con el estilo elegido encima.
- `con_toma`: mientras el director aún no termina, un trozo del crudo con el estilo; la segunda vista es una muestra del estilo.
Cada una devuelve {"a", "b", "nota_a", "nota_b", "ms"}; `a` y `b` son nombres de archivo dentro de la carpeta de la vista.
"""
import hashlib
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image

from . import catalogo, config, contraste, motor, portadas, rapida

A, B = "previa-a.jpg", "previa-b.jpg"
_CANDADOS: dict = {}
_MEMO: dict = {}
NOTA_MUESTRA = "Muestra del estilo: tu apoyo real aparece cuando el editor termine de dirigir el video."
NOTA_SIN_APOYO = "Este video aún no tiene apoyo a pantalla completa: se ve una toma con la persona."


def _candado(carpeta: Path) -> threading.Lock:
    return _CANDADOS.setdefault(str(carpeta), threading.Lock())


def _clave(*partes) -> str:
    return hashlib.sha1(json.dumps(partes, sort_keys=True, default=str).encode()).hexdigest()


def pintar(carpeta: Path, sb: dict, pedidos: dict, avance=print, vigente=lambda: True):
    """Dibuja los cuadros de salida {cuadro: archivo}, cada uno en su hilo con su propio proyecto (solo con los elementos que
    se ven en él): decodificar y dibujar casi no usan el GIL, así las dos vistas salen a la vez. Cada una se guarda y se avisa
    apenas está, y la pantalla pinta la primera sin esperar la segunda. Devuelve {archivo: [elementos sin su arte]} o None si otra
    petición más nueva la reemplazó."""
    def una(par):
        of, archivo = par
        if not vigente():
            return archivo, None
        p = motor.Proyecto(carpeta, sb, solo_en={of})
        motor.precargar(p, {of})
        for _, rgb in motor.recorrer(p, {of}):
            if not vigente():
                return archivo, None
            Image.fromarray(rgb).resize((540, 960)).save(carpeta / archivo, quality=88)
            avance(archivo)
        return archivo, p.omitidos
    with ThreadPoolExecutor(len(pedidos)) as pool:
        hechas = dict(pool.map(una, pedidos.items()))
    return None if any(v is None for v in hechas.values()) else hechas


def _nota_arte(omitidos: list) -> str:
    n = len(omitidos)
    return f"Faltan {n} imagen{'es' if n > 1 else ''} por generar: aparece{'n' if n > 1 else ''} cuando el editor termine." if n else ""


def con_director(carpeta: Path, estilo: dict, guardar=None, avance=print, vigente=lambda: True) -> dict:
    """`guardar(carpeta, estilo)`: si se da, deja el estilo elegido en el storyboard (solo la petición vigente escribe)."""
    t0 = time.time()
    carpeta = Path(carpeta)
    with _candado(carpeta):
        if not vigente():
            return {"cancelada": True}
        if guardar:
            guardar(carpeta, estilo)
        sb = json.loads((carpeta / "storyboard.json").read_text())
        sb["estilo"] = catalogo.aplicar_estilo(sb.get("estilo", {}), estilo)   # null = «Del estilo»: vuelve al valor del preset
        meta = json.loads((carpeta / "fuente.json").read_text())
        pal = carpeta / "palabras.json"
        palabras = json.loads(pal.read_text()) if pal.exists() else None
        n = len(motor.mapa_de(sb, meta["cuadros"]))
        persona, apoyo = portadas.previa(sb, n / config.FPS, palabras)
        pedidos = {min(n - 1, int(t * config.FPS)): nombre for t, nombre in ((persona, A), (apoyo, B))}
        arte = carpeta / "arte"
        clave = _clave(sb, [persona, apoyo], sorted(x.name for x in arte.iterdir()) if arte.exists() else [])
        if _MEMO.get(str(carpeta)) == clave and all((carpeta / f).exists() for f in (A, B)):   # nada cambió: las mismas vistas
            return _MEMO[str(carpeta) + "r"]
        omitidos = pintar(carpeta, sb, pedidos, avance, vigente)
        if omitidos is None:
            return {"cancelada": True}
        nota_b = NOTA_SIN_APOYO if not portadas.es_apoyo(sb, apoyo) else ""
        res = {"a": A, "b": B, "nota_a": _nota_arte(omitidos[A]), "nota_b": _nota_arte(omitidos[B]) or nota_b, "ms": int((time.time() - t0) * 1000)}
        _MEMO[str(carpeta)], _MEMO[str(carpeta) + "r"] = clave, res
        return res




def muestra(estilo: dict) -> dict:
    """El storyboard de la muestra: el título de ejemplo sobre la persona (0–1 s) y sobre el papel del estilo (1–2 s).
    Sobre el papel va como los apoyos de verdad: sin sombra (la sombra es para leerse encima del video; sobre un papel claro es un
    halo sucio) y con colores que SÍ contrastan con ese papel (11-nov, Swiss: «tu estilo» en gris claro sobre papel casi blanco)."""
    fondo = estilo.get("papel") if str(estilo.get("papel", "")).startswith("#") and len(estilo["papel"]) == 7 else "#FFFFFF"
    est = motor.Estilo({**estilo, "papel": fondo})

    def legible(*candidatos):   # el primero que se lee sobre el papel; si ninguno, negro o blanco
        papel = motor._hex(fondo)
        return next((c for c in candidatos if contraste.razon(est.color(c), papel) >= contraste.MINIMO),
                    "negro" if contraste.luz(papel) > .4 else "blanco")

    def titulo(tid, t0, t1, conector, palabra, **extra):
        return {"id": tid, "tipo": "texto", "x": 540, "y": 520, "t0": t0, "t1": t1, "entra": "fundido", "interlineado": 14,
                "lineas": [{"texto": "tu estilo", "rol": "script", "tam": 84, "color": conector},
                           {"texto": "EDITARLO", "rol": "display", "tam": 130, "color": palabra, "mayus": True}], **extra}
    # base «pantalla» SIEMPRE: la vista de la izquierda es la persona en su toma completa con los textos encima, nunca recortada
    # sobre papel, llegue el estilo que llegue (Pablo, 11-nov: «la de la izquierda siempre tiene que ser la persona completa, y ya»)
    return {"estilo": {**estilo, "grano": estilo.get("grano", 0), "base": "pantalla"}, "cortes": [],
            "escenas": [{"t0": 0.0, "persona": {"modo": "completa"}}, {"t0": 1.0, "persona": {"modo": "oculta", "fondo": fondo}}],
            "elementos": [titulo("t", 0, 1.0, "blanco", "acento"),   # como los escribe el director: la línea pequeña en blanco (la cambia `texto`)
                          titulo("tp", 1.0, 5, legible("acento2", "tinta"), legible("acento", "tinta"), sombra=False)],
            "subtitulos": {"y": 1400}}


def con_toma(carpeta: Path, estilo: dict, avance=print, vigente=lambda: True) -> dict:
    """Vista de la toma de Pablo con el estilo, antes de que exista el storyboard del director. La carpeta la deja lista
    `rapida.preparar`."""
    t0 = time.time()
    carpeta = Path(carpeta)
    with _candado(carpeta):
        if not vigente():
            return {"cancelada": True}
        # El estilo se COMPLETA aquí con su preset (por su id) y encima va lo que la persona cambió; null = «Del estilo» = el valor
        # del preset. El motor no completa nada: con solo el id y dos cambios dibujaba con sus valores de relleno (persona enmarcada
        # en papel, letra y amarillo de otro estilo) y eso era el «montaje» que salía a la izquierda (Pablo, 11-nov).
        elegido = {k: v for k, v in estilo.items() if v is not None}
        preset = {k: v for k, v in (catalogo.presets().get(elegido.get("id")) or {}).items() if k != "nombre"}
        estilo = {**preset, **elegido}
        clave = _clave(estilo)
        if _MEMO.get(str(carpeta)) == clave and all((carpeta / f).exists() for f in (A, B)):
            return _MEMO[str(carpeta) + "r"]
        sb = muestra(estilo)
        if not preset:   # todavía no hay estilo elegido: la toma tal cual, sin textos de ningún estilo
            sb = {**sb, "elementos": []}
        meta = json.loads((carpeta / "fuente.json").read_text())
        a, b = (min(k, meta["cuadros"] - 1) for k in rapida.CUADROS)   # con la persona (0-1 s) y luego apoyo a pantalla completa (1-2 s)
        if pintar(carpeta, sb, {a: A, b: B}, avance, vigente) is None:
            return {"cancelada": True}
        res = {"a": A, "b": B, "nota_a": "", "nota_b": NOTA_MUESTRA, "ms": int((time.time() - t0) * 1000)}
        _MEMO[str(carpeta)], _MEMO[str(carpeta) + "r"] = clave, res
        return res
