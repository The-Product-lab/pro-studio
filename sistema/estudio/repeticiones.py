"""Regla de Pablo: cuando el talento repite la misma idea 2–3 veces, SIEMPRE queda la ÚLTIMA versión.

Detecta en la transcripción las frases repetidas (falsos arranques, reformulaciones) y comprueba que el storyboard
corte todas las versiones menos la última. Es determinista: no depende de que el director se acuerde.
"""
import re
import unicodedata
from difflib import SequenceMatcher

PAUSA = .45          # silencio que separa frases (s)
VENTANA = 900.0      # en un crudo las tomas de una frase pueden estar a minutos (04-nov: 100 s): se compara todo el video
COLA_MIN = 4             # palabras mínimas de un falso arranque pegado al final de la frase anterior
PAUSA_FALSO_ARRANQUE = 3.0  # s máx. entre ese falso arranque y su versión buena
PARECIDO = .55       # similitud mínima entre frases para tratarlas como la misma idea


def _norma(w: str) -> str:
    w = unicodedata.normalize("NFKD", w.lower())
    return re.sub(r"[^a-z0-9ñ]", "", "".join(c for c in w if not unicodedata.combining(c)))


def frases(palabras: list) -> list:
    """[(i0, i1)] índices de palabras (i1 exclusivo), cortando en pausas y en puntuación de cierre."""
    out, i0 = [], 0
    for j, p in enumerate(palabras):
        fin = j + 1 == len(palabras) or p["w"][-1:] in ".?!" or palabras[j + 1]["s"] - p["e"] > PAUSA
        if fin:
            out.append((i0, j + 1))
            i0 = j + 1
    return out


def _misma_idea(a: list, b: list) -> bool:
    if len(a) < 3 or len(b) < 3:
        return False
    if SequenceMatcher(None, a, b).ratio() >= PARECIDO:
        return True
    n = min(len(a), len(b), 4)          # falso arranque: la primera versión arranca igual y se corta
    if len(a) <= len(b) and a[:n] == b[:n]:
        return True
    # falso arranque que Whisper partió distinto («mejor de todo es que» | «lo mejor de todo es que Cloud…», C8873 07-nov):
    # la versión corta aparece entera al comienzo de la larga (a lo más 2 palabras corrida)
    return 4 <= len(a) < len(b) and any(b[j:j + len(a)] == a for j in range(3))


def grupos(palabras: list) -> list:
    """Cadenas de versiones de la misma idea, en orden; la última de cada cadena es la que queda."""
    fs = frases(palabras)
    toks = [[_norma(palabras[k]["w"]) for k in range(i0, i1)] for i0, i1 in fs]
    siguiente = {}
    for a in range(len(fs)):
        for b in range(a + 1, len(fs)):
            if palabras[fs[b][0]]["s"] - palabras[fs[a][1] - 1]["e"] > VENTANA:
                break
            if _misma_idea(toks[a], toks[b]):
                siguiente[a] = b
                break
    vistos, out = set(), []
    for a in sorted(siguiente):
        if a in vistos:
            continue
        cadena = [a]
        while cadena[-1] in siguiente:
            cadena.append(siguiente[cadena[-1]])
        vistos.update(cadena)
        out.append([{"i0": fs[k][0], "i1": fs[k][1], "t0": palabras[fs[k][0]]["s"], "t1": palabras[fs[k][1] - 1]["e"],
                     "texto": " ".join(palabras[i]["w"] for i in range(*fs[k]))} for k in cadena])
    # falso arranque PEGADO al final de otra frase («…de forma automática y lo mejor de todo es que | y lo mejor de todo es que Cloud
    # se sigue…», C8873 07-nov): Whisper no pone punto, la primera versión queda dentro de la frase anterior y la regla de arriba
    # no la ve. Si la cola de una frase (≥ COLA_MIN palabras) es el arranque de la siguiente, esa cola es la versión vieja.
    for a in range(len(fs) - 1):
        if a in siguiente:
            continue
        b = a + 1
        if palabras[fs[b][0]]["s"] - palabras[fs[a][1] - 1]["e"] > PAUSA_FALSO_ARRANQUE:
            continue
        ta, tb = toks[a], toks[b]
        # la cola puede traer pegada la primera palabra de la toma siguiente («…desde tu Y | todo directamente desde tu
        # computador», C8868 07-nov): se prueba también ignorando esa última palabra
        mejor = (0, 0)
        for extra in (0, 1):
            cola = ta[:len(ta) - extra] if extra else ta
            k = max((k for k in range(COLA_MIN, min(len(cola) - 1, len(tb)) + 1) if cola[-k:] == tb[:k]), default=0)
            if k > mejor[0]:
                mejor = (k, extra)
        k, extra = mejor
        if k:
            i0 = fs[a][1] - k - extra
            out.append([{"i0": i0, "i1": fs[a][1], "t0": palabras[i0]["s"], "t1": palabras[fs[a][1] - 1]["e"],
                         "texto": " ".join(palabras[i]["w"] for i in range(i0, fs[a][1]))},
                        {"i0": fs[b][0], "i1": fs[b][1], "t0": palabras[fs[b][0]]["s"], "t1": palabras[fs[b][1] - 1]["e"],
                         "texto": " ".join(palabras[i]["w"] for i in range(*fs[b]))}])
    return out


def texto_para_director(palabras: list) -> str:
    gs = grupos(palabras)
    if not gs:
        return "No se detectaron frases repetidas."
    lineas = []
    for n, g in enumerate(gs, 1):
        lineas.append(f"Repetición {n}:")
        for k, v in enumerate(g):
            marca = "QUEDA (última)" if k == len(g) - 1 else "CORTAR"
            lineas.append(f"  [{marca}] {v['t0']:.2f}–{v['t1']:.2f} s · «{v['texto']}»")
    return "\n".join(lineas)


def faltas(palabras: list, cortes: list, minimo=.8, elegidas=lambda ps: False) -> list:
    """Versiones anteriores que el storyboard NO cortó (menos del 80 % de su duración dentro de `cortes`). `elegidas(palabras de la
    versión)` exime la toma que la persona dejó a mano en el guion: ella escogió cuál queda."""
    out = []
    for g in grupos(palabras):
        for v in g[:-1]:
            if elegidas(palabras[v["i0"]:v["i1"]]):
                continue
            dur = max(.01, v["t1"] - v["t0"])
            dentro = sum(max(0, min(b, v["t1"]) - max(a, v["t0"])) for a, b in cortes)
            if dentro / dur < minimo:
                out.append(f"{v['t0']:.2f}–{v['t1']:.2f} s «{v['texto']}» (repite una idea que se dice después: córtala, queda la última)")
    return out
