"""Cámara que VIAJA: un solo recorrido continuo para todo el video, en tiempo de SALIDA (después de los cortes).

Corrección de Pablo (04-nov), para todos los estilos: «la flotabilidad de la cámara no se siente profesional, se siente cortada…
tiene brincos, no tiene keyframes perfectos… usa el mismo efecto de ir y venir… la cámara no viaja entre todo; el zoom in o
movimiento puede ser seguido y pegado entre una toma de apoyo y una toma de la persona… como si el motor estuviera en la necesidad
de usar un efecto por clip».

Por eso:
- La cámara NO se reinicia por escena ni por corte: es una curva por keyframes (Hermite tipo Catmull-Rom, velocidad continua),
  que arranca y termina con velocidad cero y no frena en cada keyframe.
- Desde el 11-nov la cámara es FIJA por regla de Pablo (`fija()`, perfil/reglas.json › camara_fija): este viaje queda apagado en
  todo el editor y solo corre si la regla se quita. La regla de la cámara es UNA y vive en `perfil/reglas.json` (nota «Cámara»); aquí solo se implementa: el viaje es UNO
  para todo el video, también a través de los cortes reales: un zoom in lento y profundo de principio a fin (más lento cuanto más largo
  el video), una deriva lateral en un solo sentido y la flotación.
- La flotación es ruido suave no periódico y lento (`estilo.flotar` × 0,5, nudos cada ~4 s).
"""
import json
import math
import zlib

FPS = 30
W, H = 1080, 1920
CLAVES = ("zoom", "x", "y", "rot")


def _azar(semilla: str, k: int) -> float:
    """Número fijo en [0, 1) para (semilla, k): el mismo video siempre tiene la misma cámara (la compuerta mide lo que se ve)."""
    return (zlib.crc32(f"{semilla}:{k}".encode()) % 100000) / 100000


def _hermite(ts: list, vs: list, t: float) -> float:
    """Curva por keyframes con velocidad continua (tangentes Catmull-Rom no uniformes; velocidad 0 en los extremos)."""
    if t <= ts[0]:
        return vs[0]
    if t >= ts[-1]:
        return vs[-1]
    i = max(j for j in range(len(ts) - 1) if ts[j] <= t)

    def tangente(j):
        if j == 0 or j == len(ts) - 1:
            return 0.0
        return (vs[j + 1] - vs[j - 1]) / (ts[j + 1] - ts[j - 1])

    h = ts[i + 1] - ts[i]
    u = (t - ts[i]) / h
    m0, m1 = tangente(i) * h, tangente(i + 1) * h
    return ((2 * u ** 3 - 3 * u ** 2 + 1) * vs[i] + (u ** 3 - 2 * u ** 2 + u) * m0
            + (-2 * u ** 3 + 3 * u ** 2) * vs[i + 1] + (u ** 3 - u ** 2) * m1)


def ruido(t: float, semilla: str, periodo: float = 2.9) -> float:
    """Ruido suave en [-1, 1] sin periodo visible: nudos al azar unidos con la misma curva continua."""
    k = math.floor(t / periodo)
    ts = [(k + j) * periodo for j in (-1, 0, 1, 2)]
    vs = [2 * _azar(semilla, k + j) - 1 for j in (-1, 0, 1, 2)]
    u = (t - ts[1]) / periodo
    p0, p1, p2, p3 = vs
    return .5 * (2 * p1 + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u ** 2 + (-p0 + 3 * p1 - 3 * p2 + p3) * u ** 3)


def salida(sb: dict, t_src: float) -> float:
    """Segundo de la fuente → segundo del video final (descontando lo que quitan los `cortes`)."""
    quitado = sum(max(0.0, min(b, t_src) - a) for a, b in sb.get("cortes", []))
    return max(0.0, t_src - quitado)


def tramos(sb: dict, dur_salida: float) -> list:
    """Tomas en tiempo de salida: [(inicio, fin)] entre cortes reales (lo que quitan los `cortes`)."""
    bordes, quitado = [], 0.0
    for a, b in sorted(sb.get("cortes", [])):
        if a - quitado > 0.05:
            bordes.append(a - quitado)
        quitado += b - a
    puntos = [0.0] + [x for x in bordes if 0 < x < dur_salida] + [dur_salida]
    puntos = sorted(set(round(x, 4) for x in puntos))
    return [(a, b) for a, b in zip(puntos, puntos[1:]) if b - a > .05]


ZOOM_POR_SEG, ZOOM_MAX = .010, .22


def _viaje(dur: float) -> dict:
    """El viaje de TODO el video: zoom in lento y profundo + deriva leve en un solo sentido."""
    return {"a": 0.0, "b": dur, "z0": 1.0, "dz": min(ZOOM_MAX, ZOOM_POR_SEG * dur + .03),
            "dx": min(24.0, 1.0 * dur), "dy": -min(18.0, .7 * dur), "drot": .3}


def _avance(u: float) -> float:
    """Arranca andando (sin frenar en el corte) y desacelera suave al final: f(0)=0, f(1)=1, f'(0)=1,3, f'(1)=0,4."""
    return 1.3 * u - .6 * u ** 2 + .3 * u ** 3


def _claves(sb: dict) -> list | None:
    propias = sb.get("camara")
    if not (isinstance(propias, list) and propias):
        return None
    base = {"zoom": 1.04, "x": 0.0, "y": 0.0, "rot": 0.0}
    out = []
    for c in sorted(propias, key=lambda c: c.get("t", 0)):
        base = {k: float(c.get(k, base[k])) for k in CLAVES}
        out.append((salida(sb, float(c.get("t", 0))), dict(base)))
    if out[0][0] > 0:
        out.insert(0, (0.0, dict(out[0][1])))
    return out


def fija() -> bool:
    """¿La cámara es fija? La regla es UNA (perfil/reglas.json › global.camara_fija; Pablo, 11-nov: «quita todo lo de los movimientos
    de cámara, deja todo estático») y este es el único lugar que la lee: motor, sonido, compuertas, director y Personalizar preguntan aquí."""
    from . import config
    f = config.RAIZ / "perfil" / "reglas.json"
    return bool(f.exists() and json.loads(f.read_text()).get("global", {}).get("camara_fija"))


class Ruta:
    """ruta(t_salida) → (zoom, dx, dy, rot) del cuadro. Se calcula una vez por video."""

    def __init__(s, sb: dict, dur_salida: float | None = None, flotar: bool = True):
        if dur_salida is None:
            fin = max([e.get("t1", 0) for e in sb.get("elementos", []) if isinstance(e, dict)]
                      + [e.get("t0", 0) for e in sb.get("escenas", []) if isinstance(e, dict)] + [1.0])
            dur_salida = salida(sb, fin) + 2
        s.claves = _claves(sb)
        if s.claves:
            s.ts = [c[0] for c in s.claves]
            s.vs = {k: [c[1][k] for c in s.claves] for k in CLAVES}
            s.cortes = []
        else:
            s.tomas = [_viaje(dur_salida)]
            s.cortes = []
        s.flotar = .5 * float((sb.get("estilo") or {}).get("flotar", 0) or 0) if flotar else 0.0

    def __call__(s, t: float) -> tuple:
        if s.claves:
            z, x, y, r = (_hermite(s.ts, s.vs[k], t) for k in CLAVES)
        else:
            tm = next((m for m in s.tomas if m["a"] <= t < m["b"]), s.tomas[-1])
            f = _avance(min(1.0, max(0.0, (t - tm["a"]) / max(.1, tm["b"] - tm["a"]))))
            z, x, y, r = tm["z0"] + tm["dz"] * f, tm["dx"] * (f - .5), tm["dy"] * (f - .5), tm["drot"] * (f - .5)
        fx, fy = s.deriva(t)
        return z, x + fx, y + fy, r

    def deriva(s, t: float) -> tuple:
        """La flotación (px): ruido suave y lento, sin ir y venir visible. Único lugar de su fórmula (la usan el supervisor y la compuerta)."""
        if not s.flotar:
            return 0.0, 0.0
        return s.flotar * ruido(t, "fx", 4.3), .6 * s.flotar * ruido(t, "fy", 5.1)


FLOTA_VENTANA_S = 4.0   # ventana en la que se mide cuánto se mueve la flotación
FLOTA_PISO_PX = 12.0    # recorrido (pico a pico) MEDIANO de la flotación por ventana, en px, que todo estilo que flota (todos menos Básico) debe tener para que se VEA
                        # (Glass a flotar 8 daba ~3 px: nadie lo notaba; a 40 da ~13,6 px)


def flotacion_px(sb: dict, dur_salida: float) -> float:
    """Recorrido pico a pico mediano de la flotación (px) en ventanas de FLOTA_VENTANA_S a lo largo del video; 0 si no flota."""
    import statistics
    r = Ruta(sb, dur_salida)
    if not r.flotar or dur_salida < FLOTA_VENTANA_S:
        return 0.0
    out = []
    for w0 in range(0, int(dur_salida - FLOTA_VENTANA_S) + 1):
        pts = [r.deriva(w0 + k / FPS) for k in range(int(FLOTA_VENTANA_S * FPS))]
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        out.append(math.hypot(max(xs) - min(xs), max(ys) - min(ys)))
    return statistics.median(out)


def saltos(sb: dict, dur_salida: float) -> dict:
    """Lo que mide la compuerta: el mayor cambio entre dos cuadros seguidos DENTRO de una toma (zoom y px) y cuántas veces el zoom
    cambia de sentido."""
    r = Ruta(sb, dur_salida)
    prev, dprev, peor_z, peor_p, vueltas = None, 0.0, 0.0, 0.0, 0
    cortes = {round(c * FPS) for c in r.cortes}
    for i in range(int(dur_salida * FPS)):
        z, x, y, _ = r(i / FPS)
        if i in cortes or i - 1 in cortes:   # en un corte real el encuadre cambia: es un corte, no un brinco
            prev, dprev = (z, x, y), 0.0
            continue
        if prev:
            dz = z - prev[0]
            peor_z = max(peor_z, abs(dz))
            peor_p = max(peor_p, math.hypot(x - prev[1], y - prev[2]))
            if abs(dz) > 2e-5:
                if dprev and (dz > 0) != (dprev > 0):
                    vueltas += 1
                dprev = dz
        prev = (z, x, y)
    return {"zoom_por_cuadro": peor_z, "px_por_cuadro": peor_p, "vueltas_zoom": vueltas}
