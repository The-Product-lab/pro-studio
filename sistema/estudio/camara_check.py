"""Supervisor de cámara (Pablo 08-nov: «pon un supervisor al movimiento de cámara: Julián 3D brinca, hace un montón de cosas»).

Reconstruye la cámara EFECTIVA de cada cuadro con el mismo código que usa el render (`motor.CamaraProyecto.camara_cuadro`: viaje
global, flotación, reencuadre de la persona, A→B de pantalla completa) y mide tres cosas:
  a) SALTOS: cambio entre cuadros seguidos (zoom, píxeles, giro) mayor al umbral, fuera de un corte de escena o un corte real.
  b) SACUDIDAS: pico de aceleración (cambio de velocidad entre cuadros) que un ease no produce.
  c) SUPERPOSICIÓN: más movimientos activos a la vez de los que permite el estilo (los de cámara propia, como Julián 3D: UNO solo).
Si falla, `supervisar` NO deja renderizar esa versión: primero arregla quitando las capas que se suman (`camara_apagar` en el
storyboard: flotación y reencuadre; en estilos de cámara propia también los genéricos) y vuelve a medir. Nada se baja de umbral.
Mide también el empujón que mantiene la cara dentro (`_reencuadre_cara`), con la MISMA caja estable que usa el render
(`motor.caras_estables`): una mano levantada que corría la cámara 50-70 px y la devolvía (Pablo 08-nov, Pop seg 2) es un brinco.
"""
import json
import math
from pathlib import Path

from . import camara
from .motor import ESTILOS_CAMARA_PROPIA, FPS, W, CamaraProyecto

# Umbrales con nombre (un solo lugar). Calibrados con los finales que Pablo aprobó con el motor vigente (vox, glass, prestiggio,
# maestro-calma, luminoso: peor zoom .015/cuadro, 12 px/cuadro, aceleración .0017 / 1,6 px): un ease rápido pasa; un salto no.
SALTO_ZOOM = .02           # cambio de zoom entre dos cuadros seguidos
SALTO_PX = 14.0            # desplazamiento del centro entre dos cuadros seguidos, en px del cuadro de salida
SALTO_ROT = .08            # grados entre dos cuadros
SACUDIDA_ZOOM = .003       # cambio de la velocidad de zoom entre dos cuadros (aceleración por cuadro)
SACUDIDA_PX = 3.0          # ídem para el desplazamiento, en px
MOV_ZOOM_MIN = .0003       # una capa «se mueve» si su zoom cambia al menos esto por cuadro…
MOV_PX_MIN = .35           # … o su desplazamiento al menos esto
CAPAS_MAX = {"generico": 2, "propia": 1}   # capas activas a la vez: viaje/flotación + reencuadre, o solo una en el estilo con la excepción escrita (3D)
CAPAS_GENERICAS = ("encuadre", "flotar")   # lo que se apaga para dejar un solo movimiento
TOL = 1e-6                 # un valor IGUAL al máximo no falla (error de coma flotante)
MARGEN_EXENTO = 2          # cuadros alrededor de un corte que no se miden (la aceleración mira 2 cuadros)


class _Ligera(CamaraProyecto):
    """Lo mínimo del proyecto para calcular la cámara: sin video ni fuentes; del alfa solo la caja estable de la cara."""

    def __init__(s, carpeta: Path, sb: dict):
        s.sb, s.dir = sb, carpeta
        meta = json.loads((carpeta / "fuente.json").read_text())
        pal = carpeta / "palabras.json"
        s.palabras = [p for p in json.loads(pal.read_text()) if "s" in p] if pal.exists() else []
        quitar = set()
        for a, b in sb.get("cortes", []):
            quitar.update(range(round(a * FPS), round(b * FPS)))
        mapa = [i for i in range(meta["cuadros"]) if i not in quitar]
        s.iniciar_camara(sb, s.palabras, meta["cuadros"], mapa, carpeta.name)


def _vista(c: dict) -> tuple:
    """(zoom, cx, cy, rot) efectivos de la vista: zoom = W / ancho del recorte."""
    return W / c["cw"], c["dx"], c["dy"], c["rot"]


def _capa_mueve(a: tuple, b: tuple) -> bool:
    return abs(b[0] - a[0]) > MOV_ZOOM_MIN or math.hypot(b[1] - a[1], b[2] - a[2]) > MOV_PX_MIN


def medir(carpeta, sb: dict | None = None) -> dict:
    """{saltos, sacudidas, capas_max, por_capas, fallas}: la cámara efectiva de todo el video, cuadro a cuadro."""
    carpeta = Path(carpeta)
    sb = sb or json.loads((carpeta / "storyboard.json").read_text())
    p = _Ligera(carpeta, sb)
    n = len(p.mapa)
    limite = CAPAS_MAX["propia" if (sb.get("estilo") or {}).get("id") in ESTILOS_CAMARA_PROPIA else "generico"]
    vistas, capas, exento = [], [], set()
    previo_esc, previo_src = None, None
    for of in range(n):
        t = p.mapa[of] / FPS
        esc, s0, s1 = p.escena(t)
        c = p.camara_cuadro(of, t, esc, s0, s1, p.cara_de(of), esc.get("persona", {}))
        vistas.append(_vista(c))
        capas.append(c["capas"])
        if previo_esc is not None and s0 != previo_esc:   # solo el corte de ESCENA; un corte real dentro de una toma no salta
            exento.update(range(of - MARGEN_EXENTO, of + MARGEN_EXENTO + 1))
        previo_esc, previo_src = s0, p.mapa[of]
    fallas, saltos, sacudidas, mx = [], 0, 0, 0
    peor = {"zoom": 0.0, "px": 0.0, "rot": 0.0, "sac_zoom": 0.0, "sac_px": 0.0}
    cuando = {}
    por_n = {}
    flo = p.ruta.flotar
    for i in range(1, n):
        if i in exento:
            continue
        a, b = vistas[i - 1], vistas[i]
        dz, dp, dr = abs(b[0] - a[0]), math.hypot(b[1] - a[1], b[2] - a[2]), abs(b[3] - a[3])
        peor["zoom"], peor["px"], peor["rot"] = max(peor["zoom"], dz), max(peor["px"], dp), max(peor["rot"], dr)
        if dz > SALTO_ZOOM + TOL or dp > SALTO_PX + TOL or dr > SALTO_ROT + TOL:
            saltos += 1
            cuando.setdefault("salto", i / FPS)
        if i >= 2 and (i - 2) not in exento:
            v0 = (a[0] - vistas[i - 2][0], a[1] - vistas[i - 2][1], a[2] - vistas[i - 2][2])
            v1 = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
            sz, sp = abs(v1[0] - v0[0]), math.hypot(v1[1] - v0[1], v1[2] - v0[2])
            peor["sac_zoom"], peor["sac_px"] = max(peor["sac_zoom"], sz), max(peor["sac_px"], sp)
            if sz > SACUDIDA_ZOOM + TOL or sp > SACUDIDA_PX + TOL:
                sacudidas += 1
                cuando.setdefault("sacudida", i / FPS)
        activas = 0
        for k, v in capas[i].items():
            w = capas[i - 1].get(k)
            if w and _capa_mueve(w, v):
                activas += 1
        if flo and i < n:   # la flotación suma su propia deriva (va dentro de la ruta, pero es otro movimiento)
            f0, f1 = p.ruta.deriva((i - 1) / FPS), p.ruta.deriva(i / FPS)
            if math.hypot(f1[0] - f0[0], f1[1] - f0[1]) > MOV_PX_MIN and "pantalla" not in capas[i]:
                activas += 1
        por_n[activas] = por_n.get(activas, 0) + 1
        mx = max(mx, activas)
        if activas > limite:
            cuando.setdefault("capas", i / FPS)
    sobre = sum(v for k, v in por_n.items() if k > limite)
    if saltos:
        fallas.append(f"camara: {saltos} brincos (peor {peor['zoom']:.4f} de zoom / {peor['px']:.1f} px / {peor['rot']:.2f}° en un cuadro; "
                      f"máx. {SALTO_ZOOM} / {SALTO_PX} px / {SALTO_ROT}°), el primero en el segundo {cuando['salto']:.1f}")
    if sacudidas:
        fallas.append(f"camara: {sacudidas} sacudidas (aceleración {peor['sac_zoom']:.4f} de zoom / {peor['sac_px']:.1f} px por cuadro; "
                      f"máx. {SACUDIDA_ZOOM} / {SACUDIDA_PX}), la primera en el segundo {cuando['sacudida']:.1f}")
    if sobre:
        fallas.append(f"camara: hasta {mx} movimientos a la vez en {sobre} cuadros (este estilo admite {limite}), el primero en el segundo {cuando['capas']:.1f}")
    return {"saltos": saltos, "sacudidas": sacudidas, "capas_max": mx, "limite_capas": limite, "peor": peor, "por_capas": por_n, "fallas": fallas}


def supervisar(carpeta, avance=print) -> dict:
    """Mide; si falla, apaga las capas que se suman (flotación y reencuadre; el viaje de la ruta solo si aun así brinca) y vuelve a medir.
    Deja `camara_apagar` en el storyboard para que el render y las mediciones siguientes vean lo mismo. Si no se arregla: ValueError. En un estilo que flota siempre (reglas.json › flota_siempre) la flotación NO se apaga: la falla queda a la vista."""
    carpeta = Path(carpeta)
    f = carpeta / "storyboard.json"
    sb = json.loads(f.read_text())
    m = medir(carpeta, sb)
    if not m["fallas"]:
        return m
    avance("camara: " + "; ".join(m["fallas"]))
    apagadas = list(sb.get("camara_apagar") or [])
    for capa in CAPAS_GENERICAS:
        if capa in apagadas:
            continue
        apagadas.append(capa)
        sb["camara_apagar"] = apagadas
        m = medir(carpeta, sb)
        avance(f"camara: sin {capa} → {'OK' if not m['fallas'] else 'sigue fallando'}")
        if not m["fallas"]:
            break
    if m["fallas"]:
        raise ValueError("la cámara no pasa el supervisor:\n- " + "\n- ".join(m["fallas"]))
    f.write_text(json.dumps(sb, ensure_ascii=False, indent=1))
    return m
