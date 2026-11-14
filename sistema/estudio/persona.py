"""Dónde está la persona en la toma: caja de la cara y del cuerpo, en UNOS POCOS cuadros. Nada de recortarla del fondo.

Pablo (11-nov): «el recorte frame por frame únicamente sirve para poner cosas detrás de la persona. Pero yo no necesito recortar
para saber dónde está la cara y cómo no taparla… elimina el tema de recortes de todo, no le veo uso». Antes el sistema separaba a la
persona del fondo en TODOS los cuadros (21 min en una Mac para un video de 2,5 min), aunque su propia regla
(`sujeto_recortado_prohibido`) prohíbe mostrarla recortada: lo único que se usaba de esas máscaras era la posición de la cara.

Ahora un detector de caras (YuNet, de OpenCV: 230 KB) mira un cuadro cada PASO (2 por segundo) y se guarda SOLO la posición
(`persona.json`); entre dos muestras se interpola. La silueta del recorte viejo además tomaba por persona los maniquíes del fondo
(IMG_4965: «cara» de 688 px de ancho); un detector de caras no.
Es el único lugar que ubica a la persona: lo usan el encuadre vertical (`centro`), el motor (cajas junto a la persona), el
director (`cara.json`, para no taparla) y las compuertas.
"""
import json
import subprocess
from pathlib import Path

import numpy as np

from . import config, trabajo

PASO = 15                 # cuadros entre muestras (30 fps → 2 por segundo)
ARCHIVO = "persona.json"
VERSION = 2
LADO = 640                # el detector (YuNet, OpenCV) mira un cuadrado de este lado; el cuadro entra completo, con franjas
CONFIANZA = .6            # por debajo no es una cara
AIRE = .25                # la caja de la cara se abre esto por lado: pelo y mentón también se respetan
CUERPO_ANCHOS = 3.2       # el cuerpo se estima desde la cara: este ancho (en caras) y hasta el borde de abajo


def _sesion():
    if not config.CARAS_ONNX.exists():
        raise FileNotFoundError("falta el detector de caras: corre el instalador")
    import onnxruntime as ort
    return ort.InferenceSession(str(config.CARAS_ONNX), providers=["CPUExecutionProvider"])


def _caras(sesion, rgb: np.ndarray) -> list:
    """[(confianza, x0, y0, x1, y1)] en px del cuadrado LADO×LADO que se le pasa (RGB). Decodifica las tres escalas de YuNet."""
    x = rgb[..., ::-1].astype(np.float32).transpose(2, 0, 1)[None]   # YuNet espera BGR 0–255
    sal = dict(zip((o.name for o in sesion.get_outputs()), sesion.run(None, {sesion.get_inputs()[0].name: x})))
    out = []
    for paso in (8, 16, 32):
        n = LADO // paso
        nota = np.sqrt(np.clip(sal[f"cls_{paso}"][0, :, 0], 0, 1) * np.clip(sal[f"obj_{paso}"][0, :, 0], 0, 1))
        for k in np.where(nota >= CONFIANZA)[0]:
            bx = sal[f"bbox_{paso}"][0, k]
            cx, cy = (k % n + bx[0]) * paso, (k // n + bx[1]) * paso
            w, h = float(np.exp(bx[2])) * paso, float(np.exp(bx[3])) * paso
            out.append((float(nota[k]), cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2))
    return out


def _la_persona(caras: list):
    """De las caras vistas, la de quien habla a cámara: la más grande (el resto es público, fotos o fondo)."""
    return max(caras, key=lambda c: (c[3] - c[1]) * (c[4] - c[2]))[1:] if caras else None


def cajas_de(cara, ancho: int = config.W, alto: int = config.H):
    """(cara, cuerpo) en px del cuadro a partir de la cara detectada (x0, y0, x1, y1); (None, None) sin cara. La cara se abre AIRE
    por lado; el cuerpo se ESTIMA (no se mide): centrado bajo la cara, CUERPO_ANCHOS caras de ancho y hasta el borde de abajo."""
    if cara is None:
        return None, None
    x0, y0, x1, y1 = cara
    w, h = x1 - x0, y1 - y0
    cx = (x0 + x1) / 2
    lim = lambda v, tope: float(min(max(v, 0), tope))   # noqa: E731
    con_aire = (lim(x0 - AIRE * w, ancho), lim(y0 - AIRE * h, alto), lim(x1 + AIRE * w, ancho), lim(y1 + AIRE * h, alto))
    cuerpo = (lim(cx - CUERPO_ANCHOS * w / 2, ancho), con_aire[1], lim(cx + CUERPO_ANCHOS * w / 2, ancho), float(alto))
    return con_aire, cuerpo


def ubicar(carpeta: Path, avance=print) -> Path:
    """Escribe `persona.json` del proyecto: la posición de la persona cada PASO cuadros de `fuente.json › video`. Idempotente."""
    carpeta = Path(carpeta)
    meta = json.loads((carpeta / "fuente.json").read_text())
    destino = carpeta / ARCHIVO
    if _vigente(destino, meta):
        return destino
    avance("ubicando a la persona…")
    sesion = _sesion()
    ffmpeg, _ = config.ffmpeg()
    w = LADO * config.W // config.H // 2 * 2          # el cuadro vertical entra a lo alto del cuadrado; a los lados, franjas
    margen, k = (LADO - w) // 2, config.H / LADO
    dec = subprocess.Popen([ffmpeg, "-v", "error", "-i", str(meta["video"]), "-vf",
                            f"select='not(mod(n\\,{PASO}))',scale={w}:{LADO},pad={LADO}:{LADO}:{margen}:0,format=rgb24", "-vsync", "0",
                            "-f", "rawvideo", "-"], stdout=subprocess.PIPE, cwd=carpeta)
    cajas = []
    try:
        while True:
            b = dec.stdout.read(LADO * LADO * 3)
            if len(b) < LADO * LADO * 3:
                break
            trabajo.revisar()
            cara = _la_persona(_caras(sesion, np.frombuffer(b, np.uint8).reshape(LADO, LADO, 3)))
            en_cuadro = ((cara[0] - margen) * k, cara[1] * k, (cara[2] - margen) * k, cara[3] * k) if cara else None
            cajas.append(list(cajas_de(en_cuadro)) if cara else None)
    finally:
        dec.kill()
        dec.wait()
    tmp = destino.with_name(ARCHIVO + ".part")
    tmp.write_text(json.dumps({"version": VERSION, "paso": PASO, "cuadros": meta["cuadros"], "cajas": cajas}))
    tmp.replace(destino)
    return destino


def _vigente(destino: Path, meta: dict) -> bool:
    try:
        d = json.loads(destino.read_text())
    except (OSError, ValueError):
        return False
    return d.get("version") == VERSION and d.get("cuadros") == meta.get("cuadros")


class Tabla:
    """Posición de la persona por cuadro fuente. Sin `persona.json` (proyecto de prueba, video sin persona) no hay cajas."""

    def __init__(self, carpeta):
        f = Path(carpeta) / ARCHIVO if carpeta is not None else None
        d = json.loads(f.read_text()) if f and f.exists() else {}
        self.paso = d.get("paso", PASO)
        self.muestras = d.get("cajas", [])

    def cajas(self, i: int):
        """(cara, cuerpo) en el cuadro fuente i, interpolando entre las dos muestras vecinas; (None, None) si no hay persona."""
        if not self.muestras:
            return None, None
        f = min(max(i / self.paso, 0), len(self.muestras) - 1)
        a, b = self.muestras[int(f)], self.muestras[min(int(f) + 1, len(self.muestras) - 1)]
        if a is None or b is None:
            cerca = a if (f - int(f) < .5 or b is None) else b
            return (tuple(cerca[0]), tuple(cerca[1])) if cerca else (None, None)
        r = f - int(f)
        return tuple(tuple(u + (v - u) * r for u, v in zip(a[n], b[n])) for n in (0, 1))

    def cara(self, i: int):
        return self.cajas(i)[0]


def ajuste_cuadrado(ancho: int, alto: int) -> tuple[str, float, int]:
    """Filtro que mete el cuadro COMPLETO en el cuadrado del detector, con franjas en el lado que sobre (horizontal, vertical o 3:4).
    → (filtro, escala original→cuadrado, franja izquierda en px del cuadrado) para volver la x de la cara al video original."""
    escala = LADO / max(ancho, alto)
    w = max(2, int(ancho * escala) // 2 * 2)
    h = max(2, int(alto * escala) // 2 * 2)
    x0, y0 = (LADO - w) // 2, (LADO - h) // 2
    return f"scale={w}:{h},pad={LADO}:{LADO}:{x0}:{y0},format=rgb24", w / ancho, x0


def centro(video: Path, p: dict, carpeta: Path, avance=print) -> float:
    """Centro horizontal de la CARA (px del video original): mediana de 12 cuadros repartidos. Sirve para el encuadre vertical de
    un video horizontal."""
    ffmpeg, _ = config.ffmpeg()
    sesion = _sesion()
    vf, escala, x0 = ajuste_cuadrado(p["ancho"], p["alto"])
    centros = []
    for k in range(12):
        t = p["duracion"] * (k + .5) / 12
        b = subprocess.run([ffmpeg, "-v", "error", "-ss", f"{t:.2f}", "-i", str(video), "-frames:v", "1", "-vf", vf,
                            "-f", "rawvideo", "-"],
                           capture_output=True, check=True, cwd=carpeta).stdout
        if len(b) < LADO * LADO * 3:
            continue
        cara = _la_persona(_caras(sesion, np.frombuffer(b[:LADO * LADO * 3], np.uint8).reshape(LADO, LADO, 3)))
        if cara:
            centros.append(((cara[0] + cara[2]) / 2 - x0) / escala)
    avance(f"persona ubicada en x≈{np.median(centros):.0f} de {p['ancho']}" if centros else "no encontré a la persona: recorto al centro")
    return float(np.median(centros)) if centros else p["ancho"] / 2
