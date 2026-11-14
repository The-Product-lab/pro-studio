"""Mapa de energía y de voz de un video (base del montaje que se repara solo).

La energía se mide en cuadros de 10 ms (ventana de 20 ms) en dBFS y se guarda como `.energia.npy` (float16, ~40 KB por
cada 3 min), así el montaje y el banco de pruebas trabajan sin el audio crudo.

Detector de voz ADAPTATIVO (idea tomada de FilmCraft, MIT/Apache-2.0, `crates/speech/src/vad.rs`): el umbral sale del ruido
de CADA video (piso = percentil 10, techo = percentil 95), no de un número fijo, con histéresis. Whisper pega las palabras y
corre sus límites; la energía dice dónde hay silencio de verdad.

APUNTADOR: alguien fuera de cámara dicta el guion en voz baja y el talento lo repite (Cine, 7-nov: 8,54–17,1 s mide ~17 dB bajo
el talento). Es voz SOSTENIDA mucho más baja que el nivel del propio talento del video: se marca `fuera` para que se corte.
"""
import re
import shutil
import unicodedata
from pathlib import Path

import numpy as np

SR = 16000
HOP = .01                  # s por cuadro de energía
VENTANA = .02              # s de audio por cuadro
HISTERESIS_DB = 3.0        # la voz se apaga 3 dB más abajo de donde se enciende
MIN_VOZ_S = .05            # un chasquido de voz más corto que esto es ruido
MIN_SILENCIO_S = .06       # una pausa más corta que esto no se puede cortar
APUNTADOR_BAJO_DB = 15     # núcleo: voz sostenida ~15 dB bajo el talento (regla aprobada por Pablo, 7-nov)
APUNTADOR_EXTIENDE_DB = 10 # histéresis de nivel: el apuntador se extiende a las palabras vecinas hasta 10 dB bajo el talento
APUNTADOR_MIN_S = 1.0      # y debe durar al menos esto (una palabra suave suelta no es apuntador)
APUNTADOR_MAX_FRACCION = .6  # más que esto de las palabras no puede ser apuntador
VENTANA_NIVEL_S = 1.2      # el nivel local es el percentil 90 de la voz en ±0,6 s


def energia(x: np.ndarray) -> np.ndarray:
    """dBFS por cuadro de 10 ms (ventana 20 ms) de un audio mono a 16 kHz."""
    h, w = int(HOP * SR), int(VENTANA * SR)
    if len(x) < w:
        return np.full(1, -120.0, np.float32)
    cuadros = np.lib.stride_tricks.sliding_window_view(x.astype(np.float32), w)[::h]
    return (10 * np.log10((cuadros ** 2).mean(1) + 1e-12)).astype(np.float32)


def piso(db: np.ndarray) -> float:
    """Ruido de fondo del video: percentil 10 de los cuadros con algo de señal."""
    v = db[db > -100]
    return float(np.percentile(v, 10)) if len(v) >= 50 else -60.0


def umbral(db: np.ndarray) -> float:
    """Umbral de voz relativo al ruido del video: 30 % del camino del piso al techo y al menos 6 dB sobre el piso."""
    v = db[db > -100]
    if len(v) < 50:
        return -45.0
    piso, techo = float(np.percentile(v, 10)), float(np.percentile(v, 95))
    if techo - piso < 15:                      # la voz es muy poca del video (<5 % de los cuadros): el techo real está más arriba
        techo = max(techo, float(np.percentile(v, 99.5)))
    thr = max(piso + 6, piso + .3 * (techo - piso))
    return min(thr, techo - 15) if techo - piso < 15 else thr      # sin silencio medible (solo voz): no apagar toda la voz


def _tandas(m: np.ndarray) -> list:
    """[(inicio, fin, valor)] de las tandas seguidas iguales de un arreglo booleano (fin exclusivo)."""
    if not len(m):
        return []
    cortes = np.flatnonzero(np.diff(m.astype(np.int8))) + 1
    ini = np.concatenate(([0], cortes))
    fin = np.concatenate((cortes, [len(m)]))
    return [(int(a), int(b), bool(m[a])) for a, b in zip(ini, fin)]


def mapa_voz(db: np.ndarray, thr: float | None = None) -> np.ndarray:
    """True donde hay voz: se enciende sobre `thr`, se apaga 3 dB abajo, y se descartan chasquidos de voz muy cortos."""
    thr = umbral(db) if thr is None else thr
    voz = np.zeros(len(db), bool)
    encendida, apaga = False, thr - HISTERESIS_DB
    for i, v in enumerate(db):
        encendida = v > (apaga if encendida else thr)
        voz[i] = encendida
    for a, b, val in _tandas(voz):
        if val and (b - a) * HOP < MIN_VOZ_S:
            voz[a:b] = False
    return voz


BAJO_TALENTO_DB = 25       # lo que suena más de esto bajo el nivel del talento se OYE como silencio (Pablo, 07-nov: silencios ≤ 0,2 s)


OIDO_BAJO_TALENTO_DB = 20  # para MEDIR y CERRAR silencios: más de esto bajo el talento ya se oye como silencio (respiración, soplido)


def audible(db: np.ndarray, vad: np.ndarray, bajo: float = BAJO_TALENTO_DB) -> np.ndarray:
    """True donde suena algo que se oye junto al talento: a menos de BAJO_TALENTO_DB de su nivel (percentil 90 de la voz).
    El umbral de `mapa_voz` sale del RUIDO de la sala; en una toma muy limpia deja como «voz» soplidos a -47 dB con el talento a
    -17 dB, y la pausa medida se parte en pedazos cortos que nadie cierra (Cine C8867, 07-nov)."""
    if not vad.any():
        return np.ones(len(db), bool)
    return db > float(np.percentile(db[vad], 90)) - bajo


OIDO_VENTANA_S = .05       # el oído integra ~50 ms: una sola regla para cortar (montaje) y para revisar el final (revisar_corte)


def nivel_oido(db: np.ndarray) -> np.ndarray:
    """dB por cuadro de HOP, promediando la POTENCIA en una ventana de OIDO_VENTANA_S centrada: lo que el oído percibe. Un
    soplido de 10 ms sobre el umbral no parte un silencio que el oído oye entero (C8867 07-nov: el corte decía 0,19 s y la
    revisión del video terminado 0,35 s, porque uno medía en 10 ms y la otra en 50 ms)."""
    n = max(1, int(round(OIDO_VENTANA_S / HOP)))
    p = 10 ** (np.asarray(db, np.float64) / 10)
    k = np.ones(n) / n
    return (10 * np.log10(np.convolve(p, k, mode="same") + 1e-12)).astype(np.float32)


def talento(db: np.ndarray, vad: np.ndarray | None = None) -> float:
    """Nivel del talento: percentil 90 de los cuadros con voz (o de todos, si no hay mapa)."""
    v = db[vad] if vad is not None and vad.any() else db
    return float(np.percentile(v, 90)) if len(v) else -20.0


def oido(db: np.ndarray, nivel_talento: float) -> np.ndarray:
    """True donde se OYE voz: nivel de oído a menos de OIDO_BAJO_TALENTO_DB del talento. La ÚNICA definición de silencio del
    editor: la usan montaje (para cortar) y revisar_corte (para aprobar el video terminado)."""
    return nivel_oido(db) > nivel_talento - OIDO_BAJO_TALENTO_DB


def sumar_palabras(voz: np.ndarray, db: np.ndarray, palabras: list) -> np.ndarray:
    """Una palabra suave (Whisper la ve; el umbral de voz casi no) no puede quedar como «silencio»: dentro de cada palabra SUAVE,
    los cuadros que superan el ruido de fondo en 6 dB cuentan como voz. Así un corte o un silencio medido nunca se come una sílaba
    baja. Una palabra que ya suena sobre el umbral no se suma: Whisper estira palabras sobre una pausa (Swiss C8872, la «Y» de
    0,7 s a las 89,37 s) y sumarlas taparía el silencio real que hay dentro."""
    out, minimo, thr = voz.copy(), piso(db) + 6, umbral(db)
    for p in palabras:
        a, b = max(0, int(p["s"] / HOP)), min(len(db), int(p["e"] / HOP) + 1)
        if b > a and float(np.percentile(db[a:b], 90)) >= thr:
            continue
        out[a:b] |= db[a:b] > minimo
    return out


def silencios(voz: np.ndarray, minimo: float = MIN_SILENCIO_S) -> list:
    """[(a, b)] en segundos de las pausas sin voz de al menos `minimo`."""
    return [(a * HOP, b * HOP) for a, b, val in _tandas(voz) if not val and (b - a) * HOP >= minimo]


def hay_voz(voz: np.ndarray, t: float, radio: float = .02) -> bool:
    """¿Suena voz en t ± radio? (un corte ahí se oiría)."""
    a, b = int(round((t - radio) / HOP)), int(round((t + radio) / HOP)) + 1
    return bool(voz[max(0, a):max(0, b)].any())


def _norma(t: str) -> str:
    t = unicodedata.normalize("NFKD", t.lower())
    return re.sub(r"[^a-z0-9ñ]", "", "".join(c for c in t if not unicodedata.combining(c)))


_CUENTA = r"(?:uno|dos|tres|cuatro|cinco|\d{1,2})"
_CIERRE = r"(?:va|ya|accion|listo|grabando|corte|otra)"
_CONTEO = re.compile(rf"^(?:{_CUENTA}{{2,5}}{_CIERRE}?|{_CUENTA}{{1,5}}{_CIERRE})$")
CLAQUETA = {"accion", "corte", "otra", "otravez", "siguiente", "siguienteparte", "medices", "yamedices", "aver", "listo", "va",
            "ya", "denuevo", "otramas", "sobreexagerado", "yasiguiente", "yalisto"}


def es_claqueta(palabras: list) -> bool:
    """Una frase entera de claqueta: conteo («1, 2, 3, va», «123va», «dos, tres, acción») o una orden suelta («corte», «siguiente»).
    Se reconoce por PATRÓN (números + cierre), no por una lista cerrada de frases."""
    t = _norma("".join(p["w"] for p in palabras))
    return bool(t) and (t in CLAQUETA or bool(_CONTEO.match(t)))


def _nivel_palabra(db: np.ndarray, p: dict) -> float:
    a = min(len(db) - 1, int(p["s"] / HOP))
    return float(np.percentile(db[a:max(int(p["e"] / HOP), a + 1)], 90))


def apuntador(palabras: list, db: np.ndarray, voz: np.ndarray | None = None) -> set:
    """Índices de las palabras que son voz sostenida mucho más baja que el talento DE ESTE video (no un nivel fijo)."""
    if len(palabras) < 5:
        return set()
    voz = mapa_voz(db) if voz is None else voz
    talento = float(np.percentile([_nivel_palabra(db, p) for p in palabras], 90))
    n, mitad = len(db), int(VENTANA_NIVEL_S / HOP / 2)
    local = np.zeros(n, np.float32)            # 0 dB = «sin voz medible alrededor»: nunca cuenta como bajo
    for t in range(0, n, 5):
        tramo = db[max(0, t - mitad):t + mitad][voz[max(0, t - mitad):t + mitad]]
        if len(tramo) > 10:
            local[t:t + 5] = np.percentile(tramo, 90)
    nivel = np.array([local[min(n - 1, int((p["s"] + p["e"]) / 2 / HOP))] for p in palabras])
    fuerte, debil = nivel < talento - APUNTADOR_BAJO_DB, nivel < talento - APUNTADOR_EXTIENDE_DB
    if len(palabras) < 5:
        return set()
    marcadas, i = set(), 0
    while i < len(palabras):
        if not debil[i]:
            i += 1
            continue
        j = i
        while j + 1 < len(palabras) and debil[j + 1]:
            j += 1
        nucleo = [k for k in range(i, j + 1) if fuerte[k]]
        # el núcleo (bien bajo) debe ser una tanda seguida de al menos APUNTADOR_MIN_S
        seguidas = [list(g) for g in np.split(nucleo, np.flatnonzero(np.diff(nucleo) > 1) + 1)] if nucleo else []
        if any(palabras[g[-1]]["e"] - palabras[g[0]]["s"] >= APUNTADOR_MIN_S for g in seguidas if len(g)):
            marcadas.update(range(i, j + 1))
        i = j + 1
    for k in sorted(marcadas):          # el primer/último sonido del apuntador es tan bajo que su nivel local se mezcla con el vecino
        for v in (k - 1, k + 1):
            if 0 <= v < len(palabras) and v not in marcadas and abs(palabras[v]["s"] - palabras[k]["s"]) < 1.0 \
                    and _nivel_palabra(db, palabras[v]) < talento - APUNTADOR_BAJO_DB:
                marcadas.add(v)
    if len(marcadas) > APUNTADOR_MAX_FRACCION * len(palabras):
        return set()       # si «el apuntador» fuera casi todo el video, no hay apuntador: hay un talento que habla bajo
    return marcadas


def _soltar_marcas_viejas(out: list, db: np.ndarray) -> None:
    """Las marcas `fuera` SIN `motivo` las puso el `voces_fuera` viejo (Whisper sin filtro, a ciegas): sobre voz fuerte del talento
    son falsas (Swiss C8872, 7-nov: «Dejé de ser el editor y» a su nivel, marcado fuera → 4 cortes en voz). Solo se conservan las
    que de verdad suenan más bajas que el talento (≥ APUNTADOR_EXTIENDE_DB bajo), más la palabra fuerte aislada entre dos que se
    conservan (un corte no puede dejar un agujero dentro de la voz de fuera). Las claquetas se vuelven a marcar por patrón."""
    viejas = [k for k, p in enumerate(out) if p.get("fuera") and not p.get("motivo")]
    if not viejas or len(out) < 5:
        return
    talento = float(np.percentile([_nivel_palabra(db, p) for p in out], 90))
    quedan = {k for k in viejas if _nivel_palabra(db, out[k]) < talento - APUNTADOR_EXTIENDE_DB}
    quedan |= {k for k in viejas if k not in quedan and k - 1 in quedan and k + 1 in quedan}
    for k in viejas:
        if k not in quedan:
            out[k].pop("fuera", None)


def marcar_fuera(palabras: list, db: np.ndarray, voz: np.ndarray | None = None) -> list:
    """Copia de `palabras` con `fuera: true` (y `motivo`) en el apuntador y en la claqueta. Las marcas viejas sin `motivo` solo
    sobreviven si suenan bajas de verdad (`_soltar_marcas_viejas`): el detector nuevo manda."""
    from . import repeticiones
    out = [dict(p) for p in palabras]
    _soltar_marcas_viejas(out, db)
    for k in apuntador(out, db, voz):
        if not out[k].get("fuera"):
            out[k].update(fuera=True, motivo="apuntador")
    libres = [p for p in out if not p.get("fuera")]
    for i0, i1 in repeticiones.frases(libres):
        if es_claqueta(libres[i0:i1]):
            for p in libres[i0:i1]:
                p.update(fuera=True, motivo="claqueta")
    _ordenes_pegadas(out)
    _estirar_fuera(out, db, mapa_voz(db) if voz is None else voz)
    return out


ORDENES_PEGADAS = {("ya", "listo"), ("ya", "siguiente"), ("listo", "siguiente"), ("ya", "va")}


def _ordenes_pegadas(out: list) -> None:
    """Una orden de grabación de dos palabras pegada a una frase del talento («…este con cloud. Ya, listo», C8867 07-nov): Whisper
    la junta con la frase y `es_claqueta` (que mira la frase entera) no la ve. Se marca el par, venga donde venga."""
    libres = [p for p in out if not p.get("fuera")]
    for a, b in zip(libres, libres[1:]):
        if (_norma(a["w"]), _norma(b["w"])) in ORDENES_PEGADAS and b["s"] - a["e"] < 1.0:
            for p in (a, b):
                p.update(fuera=True, motivo="claqueta")


def _estirar_fuera(out: list, db: np.ndarray, voz: np.ndarray) -> None:
    """La voz de fuera dura lo que SUENA, no lo que Whisper le da: cada palabra `fuera` se estira sobre la voz baja pegada a ella
    (≥ APUNTADOR_EXTIENDE_DB bajo el talento, sin pausa en medio). Si Whisper puso el arranque de la palabra siguiente del
    talento dentro de esa voz baja, ese arranque se corre al final de ella. Cine C8867 (Pablo, 07-nov: «se escucha una persona
    de atrás decir uno, dos, tres, va»): Whisper cerraba el «tres» en 185,07 s, la voz de fuera seguía hasta 185,35 y el «Si»
    del talento figuraba desde 185,07 aunque suena desde 185,75: el corte quedaba en 184,98 y el conteo se oía."""
    if len(out) < 5 or not any(p.get("fuera") for p in out):
        return
    talento = float(np.percentile([_nivel_palabra(db, p) for p in out], 90))
    bajo, n, hueco = talento - APUNTADOR_EXTIENDE_DB, len(db), int(MIN_SILENCIO_S / HOP)
    def corre(i, paso):          # avanza mientras haya voz baja (o una pausa más corta que MIN_SILENCIO_S dentro de ella)
        ult, k, mudos = i, i, 0
        while 0 <= k + paso < n:
            k += paso
            if voz[k] and db[k] < bajo:
                ult, mudos = k, 0
            elif not voz[k] and mudos < hueco:
                mudos += 1
            else:
                break
        return ult
    for k, p in enumerate(out):
        if not p.get("fuera"):
            continue
        a, b = max(0, int(p["s"] / HOP)), min(n - 1, int(p["e"] / HOP))
        p["s"], p["e"] = round(corre(a, -1) * HOP, 3), round((corre(b, 1) + 1) * HOP, 3)
        sig = out[k + 1] if k + 1 < len(out) else None
        if sig and not sig.get("fuera") and p["s"] < sig["s"] < p["e"]:
            sig["s"] = min(p["e"], sig["e"])
        ant = out[k - 1] if k else None
        if ant and not ant.get("fuera") and p["s"] < ant["e"] < p["e"]:
            ant["e"] = max(p["s"], ant["s"])


def guardar_banco(carpeta: Path, destino: Path) -> Path:
    """Copia al banco de pruebas lo mínimo de un proyecto (JSON + energía), nunca video ni el audio de 12 MB.
    Uso: `python -m estudio.voz <proyecto> <destino>`."""
    carpeta, destino = Path(carpeta), Path(destino)
    destino.mkdir(parents=True, exist_ok=True)
    for f in ("palabras.json", "storyboard.json", "fuente.json"):
        if (carpeta / f).exists():
            shutil.copy2(carpeta / f, destino / f)
    cache = carpeta / ".energia.npy"
    db = np.load(cache) if cache.exists() else energia(np.load(carpeta / ".audio16k.npy"))
    np.save(destino / ".energia.npy", db.astype(np.float16))
    return destino


if __name__ == "__main__":
    import sys
    print(guardar_banco(Path(sys.argv[1]), Path(sys.argv[2])))
