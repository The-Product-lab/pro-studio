"""Motor de color de cine (ACES por OpenColorIO), portado de ESTUDIO BETA/tools/color.

Todo se hornea en UN .cube por proyecto que ffmpeg aplica al decodificar (lut3d): vista previa y render cuestan lo mismo.
El video se usa TAL CUAL viene (sin detectar cámara ni convertir LOG). Cadena: receta (p. ej. «Pablo, cine suave»)
→ look de película con su fuerza → ajustes básicos de Pablo (exposición, contraste, saturación, temperatura, tinte).
Nada se colorea solo: sin `color` en el estilo, el video queda como vino; con los ajustes en 0, la cadena es la de siempre.
"""
import hashlib
import os
import threading
import json
import math
from pathlib import Path

import numpy as np

from . import config

LIB = config.RAIZ / "librerias" / "color"
PRIVADAS = config.RAIZ / "privadas" / "color"
PIVOT, BLACK = 0.4135, 0.0729
LUMA = np.array([0.2722, 0.6741, 0.0537])
N = 33
_proc = {}


HDR = ("arib-std-b67", "smpte2084")   # HLG (iPhone, Dolby Vision) y PQ


# (blanco difuso, rodilla) por curva. HLG: calibrado contra cómo macOS muestra el mismo cuadro de un iPhone (IMG_4965, 11-nov; error
# medio 0,03 de 1). Con los números de la cadena original (0,9 / 0,6) un iPhone en interiores salía quemado, 1,4 pasos más claro que
# en el teléfono (Pablo: «se ve mal otra vez la preview de un iPhone»). PQ: sin material para calibrar, sigue con los originales.
HDR_PUNTOS = {"arib-std-b67": (.35, .4), "smpte2084": (.9, .6)}


def hdr_a_sdr(trc: str, blanco_difuso: float | None = None, rodilla: float | None = None) -> str:
    """Cadena ffmpeg HDR → Rec.709 (RGB de 16 bits ya con su curva), portada de `captions/tools/factory/sdr.py › tonemap_lut`.
    Es la conversión de rango dinámico, no un etalonaje: el color de la toma no se toca. Solo usa filtros
    que TODO ffmpeg trae (`lutrgb` + `colorchannelmixer`, sin zscale), para que cualquier máquina dé el mismo color.
    1) YUV BT.2020 → RGB 16 bits · 2) curva de la señal → luz lineal (HLG o PQ), con el blanco difuso llevado a `blanco_difuso` ·
    3) rodilla suave: lo que pasa de `rodilla` se comprime sin recortar · 4) primarios BT.2020 → BT.709 · 5) curva Rec.709.
    (11-nov: solo se cambiaba la matriz y un iPhone en HDR salía lavado, con la piel pálida.)"""
    base = HDR_PUNTOS.get(trc, HDR_PUNTOS["arib-std-b67"])
    blanco_difuso, rodilla = base[0] if blanco_difuso is None else blanco_difuso, base[1] if rodilla is None else rodilla
    if trc == "smpte2084":   # PQ (ST 2084): nits = 10000 · (max(p^(1/m2) − c1, 0) / (c2 − c3·p^(1/m2)))^(1/m1)
        p = "pow(val/maxval,1/78.84375)"
        x = f"({blanco_difuso}/203*10000*pow(max({p}-0.8359375,0)/(18.8515625-18.6875*{p}),1/0.1593017578125))"
    else:                    # HLG (ARIB STD-B67): escena lineal E; el blanco de referencia (señal 0,75) es E = 0,2646
        e = "if(lte(val/maxval,0.5),pow(val/maxval,2)/3,(exp((val/maxval-0.55991073)/0.17883277)+0.28466892)/12)"
        x = f"({blanco_difuso}/0.2646*({e}))"
    u = f"(({x}-{rodilla})/(1-{rodilla}))"
    lin = f"clip(maxval*if(lte({x},{rodilla}),{x},{rodilla}+(1-{rodilla})*{u}/(1+{u})),0,maxval)"
    oetf = "maxval*if(lte(val/maxval,0.018),4.5*val/maxval,1.099*pow(val/maxval,0.45)-0.099)"
    return ("scale=in_color_matrix=bt2020:in_range=tv,format=gbrp16le,lutrgb=" + ":".join(f"{k}='{lin}'" for k in "rgb")
            + ",colorchannelmixer=rr=1.6605:rg=-0.5876:rb=-0.0728:gr=-0.1246:gg=1.1329:gb=-0.0083:br=-0.0182:bg=-0.1006:bb=1.1187,"
            + "lutrgb=" + ":".join(f"{k}='{oetf}'" for k in "rgb"))


def _ocio():
    import PyOpenColorIO as OCIO
    return OCIO


def _cfg():
    if "cfg" not in _proc:
        _proc["cfg"] = _ocio().Config.CreateFromBuiltinConfig("studio-config-v2.1.0_aces-v1.3_ocio-v2.3")
    return _proc["cfg"]


def _cpu(src, dst):
    if (src, dst) not in _proc:
        _proc[(src, dst)] = _cfg().getProcessor(src, dst).getDefaultCPUProcessor()
    return _proc[(src, dst)]


def _apply(proc, x):
    a = np.ascontiguousarray(x, dtype=np.float32)
    proc.applyRGB(a)
    return a.astype(np.float64)


def _a_pantalla(x):
    """ACEScct → señal Rec.709."""
    return _apply(_cpu("ACEScct", "Camera Rec.709"), x)


def _suave(t):
    t = np.clip(t, 0, 1)
    return t * t * (3 - 2 * t)


def graduar(rgb, p):
    """rgb (N,3) 0..1 Rec.709 → (N,3) Rec.709. Misma matemática que el panel de color de ESTUDIO BETA."""
    lin = _apply(_cpu("Camera Rec.709", "ACEScg"), rgb)
    t, ti = p.get("temp", 0), p.get("tint", 0)
    lin = lin * 2 ** p.get("exposure", 0) * np.array([1 + .3 * t, 1 - .3 * ti, 1 - .3 * t])
    x = _apply(_cpu("ACEScg", "ACEScct"), lin)
    lift, gamma = np.array(p.get("lift", [0, 0, 0])) * .25, np.array(p.get("gamma", [0, 0, 0]))
    x = x + lift * (1 - _suave((x - BLACK) / (PIVOT - BLACK)))
    x = BLACK + (x - BLACK) * (1 + np.array(p.get("gain", [0, 0, 0])))
    x = PIVOT * (np.maximum(x, 1e-6) / PIVOT) ** (2.0 ** -gamma)
    x = (x - PIVOT) * p.get("contrast", 1) + PIVOT
    y = (_apply(_cpu("ACEScct", "ACEScg"), x) @ LUMA)[:, None]
    yl = _apply(_cpu("ACEScg", "ACEScct"), np.repeat(y, 3, 1))[:, :1]
    c = x - yl
    croma = np.linalg.norm(c, axis=1, keepdims=True)
    tono = np.arctan2(3 ** .5 * (x[:, 1:2] - x[:, 2:3]), 2 * x[:, 0:1] - x[:, 1:2] - x[:, 2:3])
    piel = np.exp(-(((tono - .3) / .3) ** 2))
    sat = p.get("saturation", 1) * (1 + p.get("vibrance", 0) * (1 - np.clip(croma / .25, 0, 1)) * (1 - .7 * piel))
    out = _a_pantalla(yl + c * sat)
    k = .92
    out = np.where(out > k, k + (1 - k) * np.tanh((out - k) / (1 - k)), out)
    return np.clip(out, 0, 1)


def _rueda(k, C):
    """Rueda + deslizador maestro de la receta → [r, g, b] (port de colorVec del panel)."""
    w, m = C["wheel"][k], C["master"][k]
    a = min(1.0, math.hypot(w["x"], w["y"]))
    h = (math.atan2(w["y"], w["x"]) / (2 * math.pi) + 1) % 1
    kk = lambda n: (n + h * 6) % 6
    c = [1 - max(0, min(kk(n), 4 - kk(n), 1)) for n in (5, 3, 1)]
    mu = sum(c) / 3
    return [m + (v - mu) * a * 1.5 for v in c]


def recetas() -> dict:
    out = {}
    for f in sorted((LIB / "recetas").glob("*.json")):
        C = json.loads(f.read_text())
        out[f.stem] = {**C["P"], "lift": _rueda("lift", C), "gamma": _rueda("gamma", C), "gain": _rueda("gain", C)}
    return out


MIS_LUTS = PRIVADAS / "mis-luts"   # LUTs de Pablo (.cube de DaVinci): se copian aquí a mano


def looks() -> list:
    """Looks disponibles en esta máquina: los LUTs de Pablo primero, luego los de película (los sin redistribución, de privadas/)."""
    fichas = json.loads((LIB / "looks.json").read_text())["looks"]
    out = [{"id": f"mio:{c.stem}", "nombre": c.stem, "familia": "mis LUTs", "favorito": True, "fuerza": 1.0, "ruta": str(c)}
           for c in sorted(MIS_LUTS.glob("**/*.cube"))]
    for l in fichas:
        ruta = LIB / f"{l['id']}.cube"
        ruta = ruta if ruta.exists() else PRIVADAS / f"{l['id']}.cube"
        if ruta.exists():
            out.append({"id": l["id"], "nombre": l["nombre"], "familia": l["familia"], "favorito": l.get("favorito", False),
                        "fuerza": l.get("intensidad", 100) / 100, "ruta": str(ruta)})
    return sorted(out, key=lambda l: (l["familia"] != "mis LUTs", not l["favorito"], l["familia"], l["nombre"]))


# Ajustes básicos del mini módulo de color (Personalizar): cada uno va de -1 a 1 en la pantalla; 0 = no toca nada.
# {clave en cfg.ajustes: (parámetro de `graduar`, valor neutro, cuánto mueve un 1)}
AJUSTES = {"exposicion": ("exposure", 0, 1.5), "contraste": ("contrast", 1, .45), "saturacion": ("saturation", 1, 1.0),
           "temperatura": ("temp", 0, .5), "tinte": ("tint", 0, .5)}


def ajustes_de(cfg: dict) -> dict:
    """Los ajustes que de verdad mueven algo, ya como parámetros de `graduar` ({} si todos están en 0)."""
    a = (cfg or {}).get("ajustes") or {}
    return {AJUSTES[k][0]: AJUSTES[k][1] + max(-1., min(1., float(v))) * AJUSTES[k][2]
            for k, v in a.items() if k in AJUSTES and isinstance(v, (int, float)) and not isinstance(v, bool) and v}


def _leer_cubo(ruta):
    n, filas = None, []
    for linea in open(ruta, encoding="utf-8", errors="replace"):
        t = linea.split("#")[0].split()
        if not t:
            continue
        if t[0] == "LUT_3D_SIZE":
            n = int(t[1])
        elif t[0][0] in "-+.0123456789" and len(t) == 3:
            filas.append([float(v) for v in t])
    return n, np.array(filas).reshape(n, n, n, 3)  # [b][g][r]


def _aplicar_cubo(n, tabla, rgb):
    x = np.clip(rgb, 0, 1) * (n - 1)
    i = np.minimum(x.astype(int), n - 2)
    f = x - i
    out = 0
    for db in (0, 1):
        for dg in (0, 1):
            for dr in (0, 1):
                w = (f[:, 2] if db else 1 - f[:, 2]) * (f[:, 1] if dg else 1 - f[:, 1]) * (f[:, 0] if dr else 1 - f[:, 0])
                out = out + w[:, None] * tabla[i[:, 2] + db, i[:, 1] + dg, i[:, 0] + dr]
    return out


def filtro(cubo: Path | None) -> str:
    """Trozo de filtro de ffmpeg que aplica el cubo en 16 bits ('' si no hay). ffmpeg corre con cwd = carpeta del proyecto."""
    return f"format=rgb48le,lut3d=file={cubo.name}:interp=tetrahedral" if cubo else ""


def cubo(carpeta: Path, cfg: dict | None) -> Path | None:
    """ÚNICO lugar que arma el color: hornea receta + look (LUT) + ajustes en `carpeta/color-<hash>.cube`. cfg = {"receta", "look", "fuerza", "ajustes"}.
    Sin color elegido devuelve None y el video queda como vino. Todo el que necesite color (normalizado, render, machote, hoja del director,
    vista rápida, previas) llama a esta función y a `filtro`."""
    cfg = {k: v for k, v in (cfg or {}).items() if k != "entrada"}   # `entrada` (LOG) ya no existe: se ignora en proyectos viejos
    if not (cfg.get("receta") or cfg.get("look") or ajustes_de(cfg)):
        return None
    clave = hashlib.sha1(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:10]
    destino = Path(carpeta) / f"color-{clave}.cube"
    if destino.exists():
        return destino
    g = np.linspace(0, 1, N)
    b, gg, r = np.meshgrid(g, g, g, indexing="ij")
    rgb = np.stack([r, gg, b], -1).reshape(-1, 3)
    receta = recetas().get(cfg.get("receta"))
    look = next((l for l in looks() if l["id"] == cfg.get("look")), None)
    if receta:
        rgb = graduar(rgb, receta)
    if look:
        n, tabla = _leer_cubo(look["ruta"])
        rgb = rgb + (_aplicar_cubo(n, tabla, rgb) - rgb) * float(cfg.get("fuerza", look["fuerza"]))
    aj = ajustes_de(cfg)
    if aj:                              # lo último: el ajuste fino de Pablo sobre todo lo anterior
        rgb = graduar(np.clip(rgb, 0, 1), aj)
    rgb = np.clip(rgb, 0, 1)
    # nombre propio por hilo: dos vistas previas pedidas a la vez horneaban el mismo color en el mismo temporal y la segunda
    # fallaba al moverlo (11-nov: «No such file… color-….tmp» y la vista quedaba sin pintar)
    tmp = destino.with_suffix(f".{os.getpid()}-{threading.get_ident()}.tmp")
    with open(tmp, "w") as f:
        f.write(f'TITLE "estudio color"\nLUT_3D_SIZE {N}\nDOMAIN_MIN 0 0 0\nDOMAIN_MAX 1 1 1\n')
        f.writelines(f"{x:.6f} {y:.6f} {z:.6f}\n" for x, y, z in rgb)
    tmp.replace(destino)
    return destino
