"""Render por tramos con memoria: una corrección vuelve a exportar SOLO los tramos que cambiaron (Pablo 06-nov: «necesito un
corrector más ágil»).

El video de salida se parte en tramos fijos de TRAMO cuadros. Cada tramo tiene una CLAVE = todo lo que decide sus cuadros:
  · lo global: el código del motor, el estilo y cualquier otra parte del storyboard que no tenga tiempo propio, las palabras,
    la fuente, la LUT de color, los archivos de arte y la posición de la persona;
  · lo suyo: qué cuadros fuente muestra (después de los cortes), la cámara en cada uno de sus cuadros, y las piezas con tiempo
    (elementos, trazos, cajas, escenas, golpes) que caen en su ventana con un margen.
Si la clave ya está en <proyecto>/.tramos/, ese tramo no se vuelve a dibujar. Un corte de guion corre la fuente de todos los
tramos que vienen después: esos cambian de clave solos; los de antes se reusan.
Nada se reusa a ciegas: de cada tramo reusado se dibuja de nuevo su cuadro del medio y se compara con el guardado; si no
calza, ese tramo se vuelve a exportar. Los tramos que ya no sirven se borran al terminar (nada se acumula).
"""
import hashlib
import json
import subprocess
from pathlib import Path

import numpy as np

from . import config, persona

TRAMO = 90            # cuadros de salida por tramo (3 s a 30 cps): chico = una corrección exporta poco
MARGEN_S = 1.0        # las piezas entran y salen con animación: se cuentan desde un segundo antes hasta uno después
GOLPE_S = 2.0         # un golpe de cámara dura menos que esto
DIF_MAX = 3.0         # diferencia media (0-255) que se acepta entre el cuadro guardado y el redibujado (códec)
LOCALES = {"elementos", "trazos", "cajas", "escenas", "punch", "cortes", "camara", "sonido"}
CODIGO = Path(__file__).parent


def _h(*partes) -> str:
    h = hashlib.sha256()
    for p in partes:
        h.update(p if isinstance(p, bytes) else json.dumps(p, sort_keys=True, ensure_ascii=False, default=str).encode())
    return h.hexdigest()


def _archivos(carpeta: Path):
    return [(str(f.relative_to(carpeta)), f.stat().st_size, f.stat().st_mtime_ns) for f in sorted(carpeta.rglob("*")) if f.is_file()] \
        if carpeta.is_dir() else []


def _global(p) -> str:
    codigo = [(f.name, f.read_bytes()) for f in sorted(CODIGO.rglob("*.py"))]
    video = Path(p.dir, p.meta["video"]) if not Path(p.meta["video"]).is_absolute() else Path(p.meta["video"])
    return _h([(n, hashlib.sha256(b).hexdigest()) for n, b in codigo],
              {k: v for k, v in p.sb.items() if k not in LOCALES},
              p.palabras, p.meta, [video.stat().st_size, video.stat().st_mtime_ns] if video.exists() else None,
              Path(p.cubo).read_bytes() if getattr(p, "cubo", None) else b"",
              _archivos(p.dir / "arte"), (p.dir / persona.ARCHIVO).read_bytes() if (p.dir / persona.ARCHIVO).exists() else b"")


def _tramo_de(x):
    if not isinstance(x, dict) or not isinstance(x.get("t0"), (int, float)):
        return None
    t1 = x.get("t1") if isinstance(x.get("t1"), (int, float)) else x["t0"] + float(x.get("dur") or 0)
    return float(x["t0"]), float(t1)


def claves(p) -> list:
    """[(a, b, clave)] tramos de salida [a, b) y su clave."""
    fps, n, g = config.FPS, len(p.mapa), _global(p)
    escenas = sorted((e for e in p.sb.get("escenas", []) if isinstance(e, dict)), key=lambda e: e.get("t0", 0))
    piezas = [x for k in ("elementos", "trazos", "cajas") for x in p.sb.get(k, []) or []]
    golpes = [x[0] if isinstance(x, list) else x for x in p.sb.get("punch", []) or []]
    out = []
    for a in range(0, n, TRAMO):
        b = min(n, a + TRAMO)
        s0, s1 = p.mapa[a] / fps - MARGEN_S, p.mapa[b - 1] / fps + MARGEN_S
        o0, o1 = a / fps - MARGEN_S, b / fps + MARGEN_S
        suyas = [x for x in piezas if (lambda r: r is None or (r[0] <= s1 and r[1] >= s0))(_tramo_de(x))]
        esc = [e for i, e in enumerate(escenas)
               if e.get("t0", 0) <= s1 and (i + 1 == len(escenas) or escenas[i + 1].get("t0", 0) >= s0)]
        gol = [t for t in golpes if isinstance(t, (int, float)) and (s0 - GOLPE_S <= t <= s1 or o0 - GOLPE_S <= t <= o1)]
        cam = [[round(v, 4) for v in p.ruta(of / fps)] for of in range(a, b)]
        out.append((a, b, _h(g, p.mapa[a:b], cam, suyas, esc, gol)[:24]))
    return out


def _cuadro_guardado(video: Path, k: int):
    ffmpeg, _ = config.ffmpeg()
    b = subprocess.run([ffmpeg, "-v", "error", "-ss", f"{max(0.0, (k - .25) / config.FPS):.4f}", "-i", str(video), "-frames:v", "1",
                        "-vf", "scale=270:480,format=gray", "-f", "rawvideo", "-"], capture_output=True).stdout
    if len(b) < 270 * 480:
        raise ValueError(f"{video.name}: no pude leer su cuadro {k}")   # tramo guardado roto o corto: no se reusa
    return np.frombuffer(b[:270 * 480], np.uint8).reshape(480, 270).astype(np.int16)   # misma forma que _cuadro_nuevo


def _cuadro_nuevo(p, of: int, filtro: str):
    from PIL import Image
    ffmpeg, _ = config.ffmpeg()
    i = p.mapa[of]
    b = subprocess.run([ffmpeg, "-v", "error", "-ss", f"{i / config.FPS:.4f}", "-i", p.meta["video"], "-frames:v", "1",
                        "-vf", filtro, "-f", "rawvideo", "-"], capture_output=True, check=True, cwd=p.dir).stdout
    rgb = np.frombuffer(b[:config.W * config.H * 3], np.uint8).reshape(config.H, config.W, 3)
    im = Image.fromarray(np.asarray(p.cuadro(of, rgb))[..., :3].astype(np.uint8)).convert("L").resize((270, 480), Image.BILINEAR)
    return np.asarray(im).astype(np.int16)


def reusables(p, plan, filtro, avance=print) -> set:
    """Claves de tramos ya guardados que siguen sirviendo (su cuadro del medio redibujado calza con el guardado)."""
    d = p.dir / ".tramos"
    ok = set()
    for a, b, k in plan:
        f = d / f"{k}.mp4"
        if not f.exists():
            continue
        m = (b - a) // 2
        try:
            dif = np.abs(_cuadro_nuevo(p, a + m, filtro) - _cuadro_guardado(f, m)).mean()
        except Exception:
            continue
        if dif <= DIF_MAX:
            ok.add(k)
        else:
            avance(f"tramo {a / config.FPS:.0f} s: el guardado no calza ({dif:.1f}), se vuelve a exportar")
    return ok


def limpiar(p, plan):
    d = p.dir / ".tramos"
    vivas = {f"{k}.mp4" for _, _, k in plan}
    for f in d.glob("*.mp4") if d.is_dir() else []:
        if f.name not in vivas:
            f.unlink()
