"""Revisión final OBLIGATORIA de un corte ya renderizado (Pablo, 07-nov: «garantízame algo bueno»; aprobó «revisión final»).

Se mide el VIDEO TERMINADO (machote.mp4 o final.mp4), no el plan: lo que se oye es lo que cuenta.

Contrato
- Entra: la ruta del video renderizado y, si hay, el guion esperado (las palabras que el corte debía conservar).
- Sale: `{"ok": bool, "fallas": [{"tipo", "segundo", "detalle"}], "medidas": {...}}`. `ok` es False si hay al menos una falla.
- Fallas que bloquean (los números viven en este archivo, arriba, con su porqué):
  · silencio: un tramo que se oye mudo (más de OIDO_BAJO_DB bajo el nivel del talento) de más de SILENCIO_MAX_S.
  · (aviso, no bloquea) voz_de_fondo: sonido sostenido entre FONDO_MIN_DB y FONDO_MAX_DB bajo el talento durante FONDO_MIN_S.
    Medido el 07-nov: casi siempre es la respiración del talento; la voz ajena se resuelve separando voces, no por volumen.
  · repeticion: el mismo pedazo de FRASE_REPETIDA_MIN o más palabras dicho dos veces a menos de REPETIDA_VENTANA_S
    («y lo mejor de todo es que… y lo mejor de todo es que», C8873; «y todo… y todo», C8868).
  · fuera_de_guion: con guion esperado, una palabra con contenido que suena y no está en el guion (orden de grabación, charla).
- Nunca: aprobar sin medir; inventar una repetición en el silencio final (la transcripción usa VAD para que Whisper no alucine).
"""
import json
import re
import subprocess
import unicodedata
from pathlib import Path

import numpy as np

from . import config
from .montaje import SILENCIO_MAX_S   # un solo lugar: montaje.py

SR = 16000
VENTANA_S = .05            # ventanas de 50 ms (como se mide el oído en el resto del editor)
FONDO_MIN_DB, FONDO_MAX_DB = 13, 30  # «otra persona lejos»: entre 13 y 30 dB bajo el talento (el apuntador mide ~15–17). Más cerca
                                     # del talento (9–12 dB) el nivel no la distingue de una frase dicha suave: eso lo resuelve la
                                     # separación de voces (fase 3), no el volumen
FONDO_MIN_S = .30          # sostenida: una cola de palabra o una respiración duran menos
FRASE_REPETIDA_MIN = 3     # palabras seguidas iguales que cuentan como repetición si la segunda vez llega enseguida (falso arranque)
REPETIDA_HUECO_PALABRAS = 4  # «enseguida» = a lo más estas palabras entre las dos versiones («y todo… y todo»)
FRASE_LARGA_MIN = 6        # un pedazo de 6+ palabras dicho dos veces en la ventana es repetición aunque haya algo en medio (dos CTA)
REPETIDA_VENTANA_S = 12.0  # dos menciones más lejanas pueden ser del guion («cómo editar videos con Claude… aprender a editar videos…»)
VACIAS = {"que", "de", "la", "el", "y", "a", "en", "los", "las", "con", "por", "un", "una", "lo", "es", "se", "tu", "te", "mi"}


def _norma(t: str) -> str:
    t = unicodedata.normalize("NFKD", t.lower())
    return re.sub(r"[^a-z0-9ñ]", "", "".join(c for c in t if not unicodedata.combining(c)))


def _audio(video: Path) -> np.ndarray:
    ffmpeg, _ = config.ffmpeg()
    r = subprocess.run([ffmpeg, "-v", "error", "-i", str(video), "-vn", "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"],
                       capture_output=True, check=True)
    return np.frombuffer(r.stdout, np.int16).astype(np.float32) / 32768


def _niveles(x: np.ndarray) -> np.ndarray:
    n = int(VENTANA_S * SR)
    k = len(x) // n
    if not k:
        return np.full(1, -120.0)
    v = x[:k * n].reshape(k, n)
    return 10 * np.log10((v ** 2).mean(1) + 1e-12)


def _corridas(m: np.ndarray) -> list:
    out, i = [], 0
    while i < len(m):
        if m[i]:
            j = i
            while j < len(m) and m[j]:
                j += 1
            out.append((i, j))
            i = j
        else:
            i += 1
    return out


def silencios(x: np.ndarray, nivel_talento: float | None = None) -> list:
    """Con la MISMA regla que usa montaje para cortar (voz.oido sobre cuadros de voz.HOP): un solo metro para cortar y revisar."""
    from . import voz
    db = voz.energia(x)
    # el MISMO número de talento que usó el corte (si se conoce) y el mismo oído: una sola regla para cortar y para revisar
    mudo = ~voz.oido(db, voz.talento(db, voz.mapa_voz(db)) if nivel_talento is None else nivel_talento)
    return [(a * voz.HOP, (b - a) * voz.HOP) for a, b in _corridas(mudo) if (b - a) * voz.HOP > SILENCIO_MAX_S + voz.HOP / 2]


def voz_de_fondo(db: np.ndarray, talento: float) -> list:
    banda = (db < talento - FONDO_MIN_DB) & (db > talento - FONDO_MAX_DB)
    return [(a * VENTANA_S, (b - a) * VENTANA_S, float(db[a:b].max() - talento)) for a, b in _corridas(banda)
            if (b - a) * VENTANA_S >= FONDO_MIN_S - 1e-6]


def repeticiones(palabras: list) -> list:
    """[(segundo, texto)] de cada pedazo de ≥ FRASE_REPETIDA_MIN palabras (no todas vacías) dicho dos veces seguidas en la ventana."""
    toks = [(_norma(p["w"]), p["s"]) for p in palabras if _norma(p["w"])]
    out = []
    for n in (2, FRASE_REPETIDA_MIN, FRASE_LARGA_MIN):          # 2: «y todo… y todo» (C8868), solo si se repite pegado
        for i in range(len(toks) - n + 1):
            g = [t for t, _ in toks[i:i + n]]
            if all(t in VACIAS for t in g):
                continue
            hueco_max = 0 if n == 2 else REPETIDA_HUECO_PALABRAS if n < FRASE_LARGA_MIN else 10 ** 6
            for j in range(i + n, min(len(toks) - n + 1, i + n + hueco_max + 1)):
                if toks[j][1] - toks[i][1] > REPETIDA_VENTANA_S:
                    break
                if [t for t, _ in toks[j:j + n]] == g:
                    out.append((round(float(toks[j][1]), 2), " ".join(g)))
                    break
    out.sort()
    vistos, limpio = set(), []
    for t, g in out:                       # una repetición larga aparece como varias ventanas seguidas: se informa una vez
        if not any(abs(t - u) < 1.5 for u in vistos):
            limpio.append((t, g))
            vistos.add(t)
    return limpio


def transcribir(x: np.ndarray) -> list:
    from . import asr
    segs = asr.transcribir(x, word_timestamps=True, beam_size=5, condition_on_previous_text=False,
                           vad_filter=True)                      # VAD: sin él Whisper inventa frases en el silencio final
    return [{"w": w.word.strip(), "s": round(w.start, 2), "e": round(w.end, 2)} for s in segs for w in s.words]


def fuera_de_guion(dichas: list, guion: list) -> list:
    esperado = {_norma(w) for w in guion}
    return [(p["s"], p["w"]) for p in dichas if (t := _norma(p["w"])) and t not in esperado and t not in VACIAS and len(t) >= 2]


def revisar(video: Path, guion: list | None = None, palabras: list | None = None, nivel_talento: float | None = None) -> dict:
    """Mide `video`. `guion`: palabras que el corte debía decir (lista de str). `palabras`: transcripción ya hecha (pruebas)."""
    x = _audio(Path(video))
    db = _niveles(x)
    talento = float(np.percentile(db, 90)) if nivel_talento is None else nivel_talento
    dichas = palabras if palabras is not None else transcribir(x)
    fallas = [{"tipo": "silencio", "segundo": round(t, 2), "detalle": f"{d:.2f} s mudos (máx. {SILENCIO_MAX_S})"}
              for t, d in silencios(x, nivel_talento)]
    fallas += [{"tipo": "voz_de_fondo", "segundo": round(t, 2), "detalle": f"{d:.2f} s de voz {abs(n):.0f} dB bajo la persona"}
               for t, d, n in voz_de_fondo(db, talento)]
    fallas += [{"tipo": "repeticion", "segundo": t, "detalle": f"«{g}» dos veces"} for t, g in repeticiones(dichas)]
    if guion:
        fallas += [{"tipo": "fuera_de_guion", "segundo": t, "detalle": f"«{w}» no está en el guion"} for t, w in fuera_de_guion(dichas, guion)]
    fallas.sort(key=lambda f: f["segundo"])
    # «voz de fondo» por VOLUMEN no bloquea: medido el 07-nov, lo que marca (13–30 dB bajo la persona, 0,3 s) es su respiración o un
    # «y» suave entre frases (C8867 7,4 s, C8871 12,1 s, C8872 28,8 s), y el «acción» real de fondo suena a solo ~10 dB (no lo ve).
    # Queda como aviso; la voz ajena la resuelve la separación de voces y la lectura del arquitecto
    bloquean = [f for f in fallas if f["tipo"] != "voz_de_fondo"]
    return {"ok": not bloquean, "fallas": bloquean, "avisos": [f for f in fallas if f["tipo"] == "voz_de_fondo"],
            "medidas": {"duracion_s": round(len(x) / SR, 2), "talento_db": round(talento, 1), "palabras": len(dichas),
                        "texto": " ".join(p["w"] for p in dichas)}}


def guardar(video: Path, informe: dict) -> Path:
    destino = Path(video).with_name(Path(video).stem + ".revision.json")
    destino.write_text(json.dumps(informe, ensure_ascii=False, indent=1))
    return destino
