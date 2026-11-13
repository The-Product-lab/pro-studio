"""Mapa de texto de los Estilos Pro: le dice al editor de textos (`texto_pelicula`) dónde cabe una palabra en cada tramo de la película.

Sale de `julian-animado/herramientas/mapa_texto.py` (la prueba que decidió, 09-nov), sin tramos escritos a mano. Se MIDE sobre
`limpio.mp4` (la película sin las palabras del guion): por tramo de voz, cuadros muestreados → máscara de tinta/forma (dilatada) →
unión → mayor rectángulo vacío dentro de la zona segura. Por tramo también: tinta según el fondo, acento, `fondo_luma`, tipo de
integración y el pliego de apoyo (`sobre_pliego`) cuando el mundo llena el cuadro.

Los tramos salen de `plano.json` si el editor 1 lo dejó ({"acento": "#rrggbb", "tramos": [{t0, t1, integracion}]}); si no, de las
pausas de la voz (`palabras.json`). La salida es la que lee `texto_pelicula.planear`: `mapa-texto.json`.
Uso: python -m estudio.mapa_texto <carpeta> [--video limpio.mp4]"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view as ventanas

from . import config

W, H = config.W, config.H
ZONA = config.ZONA_SEGURA
CELDA = 10                             # px por celda de la rejilla de libres
ANCHO_MIN = 36                         # celdas: un rectángulo útil para texto mide al menos 360 px de ancho
MUESTRAS = 4                           # cuadros medidos por tramo
BORDE_MUESTRA = .05                    # s que se alejan del borde del tramo los cuadros medidos
DILATAR = 7                            # iteraciones (a media resolución) que se agrandan tinta y bordes
BORDE_UMBRAL = 60                      # fuerza de borde (Sobel) que cuenta como ocupado
OSCURO_SOBRE_PAPEL = 28                # cuánto más oscuro que el papel cuenta como tinta
OSCURO_ABSOLUTO = 120                  # luma bajo el cual todo es ocupado (bloques negros)
AREA_MIN_PX = 60000                    # menos que esto de rectángulo libre: el texto va sobre un pliego
AREA_NULA_PX = 2000                    # menos que esto: no hay rectángulo libre
PLIEGO = {"x0": 120, "y0": 600, "x1": 960, "y1": 920}   # pliego de apoyo cuando no hay papel libre
LUMA_FONDO_CLARO = 110                 # fondo más claro que esto: tinta oscura
TINTA_OSCURA, TINTA_CLARA, ACENTO = "#1c1510", "#ede4cd", "#c2432a"
PAUSA_TRAMO_S = .28                    # pausa de voz que parte un tramo cuando no hay plano.json
TRAMO_MAX_S, TRAMO_MIN_S = 3.0, .8     # largo máximo de un tramo automático; los más cortos se pegan al anterior
INTEGRACION = "grabado"                # integración por defecto de un tramo automático
FUENTES = {"grabado": "EB Garamond 800 (capitales)", "rotulador": "Covered By Your Grace", "maquina": "Courier Prime Bold"}


def _cuadro(video: Path, t: float) -> np.ndarray:
    ffmpeg, _ = config.ffmpeg()
    raw = subprocess.run([ffmpeg, "-v", "error", "-ss", f"{t:.3f}", "-i", str(video), "-frames:v", "1", "-vf", f"scale={W}:{H}",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
    if len(raw) != W * H * 3:
        raise RuntimeError(f"{video.name}: no pude leer el cuadro de {t:.2f} s")
    return np.frombuffer(raw, np.uint8).reshape(H, W, 3).astype(np.float32)


def _filtro(g: np.ndarray, n: int, op) -> np.ndarray:
    """Filtro de ventana n×n (bordes repetidos) con `op` (np.max, np.min) sobre cada eje."""
    r = n // 2
    for eje in (0, 1):
        p = np.pad(g, [(r, r) if k == eje else (0, 0) for k in (0, 1)], mode="edge")
        g = op(ventanas(p, n, axis=eje), axis=-1)
    return g


def _media(g: np.ndarray, n: int) -> np.ndarray:
    """Media de ventana n×n con imagen integral (bordes repetidos)."""
    r = n // 2
    p = np.pad(g, r, mode="edge").astype(np.float64)
    ii = np.pad(p.cumsum(0).cumsum(1), ((1, 0), (1, 0)))
    return ((ii[n:, n:] - ii[:-n, n:] - ii[n:, :-n] + ii[:-n, :-n]) / (n * n))[:g.shape[0], :g.shape[1]]


def _bordes(g: np.ndarray) -> np.ndarray:
    """Módulo del gradiente de Sobel."""
    p = np.pad(g, 1, mode="edge")
    gx = (p[:-2, 2:] + 2 * p[1:-1, 2:] + p[2:, 2:]) - (p[:-2, :-2] + 2 * p[1:-1, :-2] + p[2:, :-2])
    gy = (p[2:, :-2] + 2 * p[2:, 1:-1] + p[2:, 2:]) - (p[:-2, :-2] + 2 * p[:-2, 1:-1] + p[:-2, 2:])
    return np.hypot(gx, gy)


def _dilatar(m: np.ndarray, veces: int) -> np.ndarray:
    for _ in range(veces):
        n = m.copy()
        n[1:] |= m[:-1]
        n[:-1] |= m[1:]
        n[:, 1:] |= m[:, :-1]
        n[:, :-1] |= m[:, 1:]
        m = n
    return m


def _ocupado(img: np.ndarray) -> np.ndarray:
    """Ocupado = tinta, bloque, tabla o bordes: todo lo que no es papel liso."""
    g = img.mean(2)[::2, ::2]                                   # a media resolución (rápido)
    papel = _media(_filtro(_filtro(g, 9, np.max), 9, np.min), 31)   # cierre (máx. y luego mín.) y media: el color del papel
    m = _dilatar((_bordes(g) > BORDE_UMBRAL) | (g < papel - OSCURO_SOBRE_PAPEL) | (g < OSCURO_ABSOLUTO), DILATAR)
    return np.repeat(np.repeat(m, 2, 0), 2, 1)


def mayor_rectangulo(libre: np.ndarray) -> tuple:
    """Mayor rectángulo de celdas libres de al menos ANCHO_MIN de ancho (método del histograma): (área, fila0, col0, fila1, col1)."""
    filas, cols = libre.shape
    h, mejor = np.zeros(cols, int), (0, 0, 0, 0, 0)
    for r in range(filas):
        h = np.where(libre[r], h + 1, 0)
        pila = []
        for c in range(cols + 1):
            cur = h[c] if c < cols else 0
            while pila and h[pila[-1]] >= cur:
                tope = pila.pop()
                alto = h[tope]
                izq = pila[-1] + 1 if pila else 0
                area = alto * (c - izq)
                if area > mejor[0] and c - izq >= ANCHO_MIN:
                    mejor = (area, r - alto + 1, izq, r, c - 1)
            pila.append(c)
    return mejor


def tramos_de(palabras: list, dur: float, plano: dict | None = None) -> list:
    """[(t0, t1, voz, integración)] contiguos de 0 a `dur`. Con `plano` (del editor 1) manda su lista; si no, las pausas de la voz."""
    def voz(a, b):
        return " ".join(p["w"] for p in palabras if a <= (p["s"] + p["e"]) / 2 < b)
    if plano and plano.get("tramos"):
        return [(float(x["t0"]), float(x["t1"]), voz(float(x["t0"]), float(x["t1"])), x.get("integracion") or INTEGRACION)
                for x in plano["tramos"]]
    cortes = [0.0]
    for p, q in zip(palabras, palabras[1:]):
        if q["s"] - p["e"] >= PAUSA_TRAMO_S or q["e"] - cortes[-1] > TRAMO_MAX_S:
            cortes.append(round((p["e"] + q["s"]) / 2, 3))
    cortes.append(dur)
    fusion = [cortes[0]]
    for c in cortes[1:-1]:
        if c - fusion[-1] >= TRAMO_MIN_S:
            fusion.append(c)
    fusion.append(cortes[-1])
    return [(a, b, voz(a, b), INTEGRACION) for a, b in zip(fusion, fusion[1:]) if b > a]


def medir(video: Path, tramos: list, acento: str = ACENTO) -> dict:
    """El mapa de texto de `video` para esos tramos."""
    zx0, zy0, zx1, zy1 = ZONA
    salida = []
    for t0, t1, voz, integ in tramos:
        a, b = t0 + BORDE_MUESTRA, max(t0 + BORDE_MUESTRA, t1 - BORDE_MUESTRA)
        imgs = [_cuadro(video, t) for t in np.linspace(a, b, MUESTRAS)]
        occ = np.zeros((H, W), bool)
        for im in imgs:
            occ |= _ocupado(im)
        z = occ[zy0:zy1, zx0:zx1]
        celdas = z[: (z.shape[0] // CELDA) * CELDA, : (z.shape[1] // CELDA) * CELDA].reshape(z.shape[0] // CELDA, CELDA, -1, CELDA).any((1, 3))
        area, r0, c0, r1, c1 = mayor_rectangulo(~celdas)
        x0, y0, x1, y1 = (int(v) for v in (zx0 + c0 * CELDA, zy0 + r0 * CELDA, zx0 + (c1 + 1) * CELDA, zy0 + (r1 + 1) * CELDA))
        bg = float(np.mean([im[y0:y1, x0:x1].mean() for im in imgs])) if area else 0.0
        tinta = TINTA_OSCURA if bg > LUMA_FONDO_CLARO else TINTA_CLARA
        pliego = None
        if area * CELDA * CELDA < AREA_MIN_PX:   # el mundo llena el cuadro: el texto va sobre un pliego con sombra
            pliego = {**PLIEGO, "como": "pliego encima de la película, con sombra (no hay papel libre)"}
            tinta = TINTA_OSCURA
            if area * CELDA * CELDA < AREA_NULA_PX:
                area = 0
        salida.append({"t0": round(t0, 3), "t1": round(t1, 3), "voz": voz,
                       "libre": {"x0": x0, "y0": y0, "x1": x1, "y1": y1} if area else None, "sobre_pliego": pliego,
                       "area_px": int(area * CELDA * CELDA), "fondo_luma": round(bg, 1), "tinta": tinta, "acento": acento,
                       "integracion": integ})
    return {"video": video.name, "tamano": [W, H], "zona": dict(zip(("x0", "y0", "x1", "y1"), ZONA)), "fuentes": FUENTES, "tramos": salida}


def escribir(carpeta: Path, video: str = "limpio.mp4") -> dict:
    """Mide `carpeta/<video>` con las palabras (`palabras.json`) y el plano del editor 1 (`plano.json`, si lo dejó) → `mapa-texto.json`."""
    carpeta = Path(carpeta)
    palabras = [{"w": p["w"], "s": float(p.get("s", p.get("t0"))), "e": float(p.get("e", p.get("t1")))}
                for p in json.loads((carpeta / "palabras.json").read_text())]
    _, ffprobe = config.ffmpeg()
    dur = float(subprocess.run([ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(carpeta / video)],
                               capture_output=True, text=True, check=True).stdout.strip())
    f = carpeta / "plano.json"
    plano = json.loads(f.read_text()) if f.exists() else None
    mapa = medir(carpeta / video, tramos_de(palabras, dur, plano), (plano or {}).get("acento") or ACENTO)
    (carpeta / "mapa-texto.json").write_text(json.dumps(mapa, ensure_ascii=False, indent=1))
    return mapa


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("carpeta", type=Path)
    ap.add_argument("--video", default="limpio.mp4")
    a = ap.parse_args(argv)
    for t in escribir(a.carpeta, a.video)["tramos"]:
        lb = t["libre"]
        print(f"{t['t0']:6.2f}-{t['t1']:6.2f}  libre {lb and (lb['x1'] - lb['x0'], lb['y1'] - lb['y0'])}  tinta {t['tinta']}  {t['integracion']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
