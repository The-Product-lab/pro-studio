"""Compuerta del MONTAJE (reglas de Pablo, medidas en el audio y la transcripción, no a ojo):

1. Queda la ÚLTIMA versión de cada frase repetida (aunque las tomas estén a minutos de distancia) — `repeticiones`.
2. Nada de claqueta ni voces fuera de cámara (conteos «1, 2, 3, va», «otra», «corte», y el APUNTADOR que dicta en voz baja) — `voz`.
3. Se corta solo en silencio REAL (mapa de voz adaptativo de `voz`, no los tiempos de Whisper): ningún borde con voz sonando.
4. Ningún silencio de más de SILENCIO_MAX_S en el video final (en una unión suma el aire de las dos tomas).

`reparar` hace en código todo lo medible; `errores` es la compuerta.

`voces_fuera` completa la transcripción: Whisper con VAD se come las voces bajas de fuera de cámara (04-nov: un «acción»
se coló en un reel). Se re-escucha cada pausa sin filtro y lo que aparezca se agrega marcado `fuera: true`.
"""
import json
import re
import subprocess
import unicodedata
from pathlib import Path

import numpy as np

from . import config, repeticiones, trabajo, voz

SR = 16000
AIRE_FIN = .08          # s de aire mínimo entre la última palabra de un tramo y el corte (que la palabra termine de sonar)
SILENCIO_DB = -38       # bajo esto (dBFS, ventana de 50 ms) es silencio
# s: ningún silencio del video final (ni la suma de los dos lados de una unión) pasa de esto. Era 0,20 (Pablo, 07-nov); el 13-nov pidió
# 0,1 s más de aire en cada corte: «corta muy encima de la palabra y no la deja respirar cuando pega un corte con otro». Es el ÚNICO
# número del margen: de él salen la meta de `reparar` (SILENCIO_META_S), el aire del inicio y del final (machote) y la revisión del oído.
# El aire que queda es SIEMPRE silencio de las mismas tomas (el corte se corre dentro de la pausa): nunca entra voz cortada.
SILENCIO_MAX_S = .30
SILENCIO_META_S = SILENCIO_MAX_S - 3 * voz.HOP    # a lo que apunta `reparar`: un cuadro de energía menos, para que la medición no pase del tope
VOZ_PALABRA_MIN = .5    # una palabra con menos voz medida que esto es una palabra mal puesta en el tiempo por Whisper
ARRANQUE_MIN_S = .04    # s de aire mínimo antes de la primera palabra de un tramo (el corte no la toca)


def _norma(t: str) -> str:
    t = unicodedata.normalize("NFKD", t.lower())
    return re.sub(r"[^a-z0-9ñ]", "", "".join(c for c in t if not unicodedata.combining(c)))


def audio(carpeta: Path) -> np.ndarray:
    """Audio del video fuente a 16 kHz mono (en caché en el proyecto)."""
    cache = Path(carpeta) / ".audio16k.npy"
    if cache.exists():
        return np.load(cache)
    meta = json.loads((Path(carpeta) / "fuente.json").read_text())
    ffmpeg, _ = config.ffmpeg()
    raw = subprocess.run([ffmpeg, "-v", "error", "-i", meta["video"], "-vn", "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"],
                         capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
    np.save(cache, x)
    return x


def _db(x: np.ndarray) -> float:
    return 20 * np.log10(max(1e-6, float(np.sqrt((x ** 2).mean())) if len(x) else 1e-6))


PAUSA_DENTRO_S = .3     # una palabra no trae una pausa así por dentro: si la trae, Whisper la estiró sobre una pausa


def cenir_estiradas(palabras: list, hay_voz: np.ndarray) -> list:
    """Una palabra larga (≥ 0,9 s) con una pausa real por dentro está estirada: Whisper la arrancó antes (o la soltó después) de
    donde suena. Se ciñe al trozo de voz pegado a su vecina (la siguiente si vienen pegadas; si no, la anterior; si no, el trozo más
    largo). Lo que queda libre vuelve a ser pausa y se re-escucha como cualquier otra (IMG_4965, 11-nov: «vas» ocupaba 72,4–80,6 s;
    adentro había 4 s de apuntador sin transcribir y el «vas» de verdad sonaba en 80,3–80,6: el guion quedó empatado de dos tomas)."""
    out = [dict(p) for p in palabras]
    for k, p in enumerate(out):
        if p["e"] - p["s"] < .9 or p.get("fuera"):
            continue
        a, b = int(p["s"] / voz.HOP), min(len(hay_voz), int(p["e"] / voz.HOP) + 1)
        trozos = []
        for i, j, suena in voz._tandas(hay_voz[a:b]):
            if not suena:
                continue
            if trozos and (a + i) * voz.HOP - trozos[-1][1] < PAUSA_DENTRO_S:
                trozos[-1][1] = (a + j) * voz.HOP
            else:
                trozos.append([(a + i) * voz.HOP, (a + j) * voz.HOP])
        if len(trozos) < 2:
            continue
        pegada_despues = k + 1 < len(out) and out[k + 1]["s"] - p["e"] < .15
        pegada_antes = k > 0 and p["s"] - out[k - 1]["e"] < .15
        s, e = trozos[-1] if pegada_despues else trozos[0] if pegada_antes else max(trozos, key=lambda t: t[1] - t[0])
        p["s"], p["e"] = round(max(p["s"], s), 2), round(min(p["e"], max(e, s + .1)), 2)
    return out


def reescuchar(x: np.ndarray, trozos: list, avance=None) -> list:
    """Vuelve a oír cada trozo [(t0, t1)] del audio, sin filtro de voz. Devuelve, por trozo, sus palabras con el tiempo del VIDEO:
    [(texto, inicio, fin, probabilidad)]. Es UNA llamada a Whisper por trozo y avisa por cuál va: es el paso más largo del guion
    en una máquina sin GPU (cada llamada cuesta lo mismo que oír 30 s) y sin aviso parecía colgado (Pablo, 11-nov: «lleva casi 15 min
    en los guiones»).
    Juntar los trozos en una sola pasada se probó el 11-nov y NO sirve: 10 veces más rápido, pero Whisper oye otra cosa (se salta
    trozos o repite frases en las pausas cortas) y este paso decide qué palabras existen en el guion. Medición: docs/PLANO-REESCUCHA.md."""
    from . import asr
    out = []
    for n, (t0, t1) in enumerate(trozos, 1):
        trabajo.revisar()   # entre una re-escucha y la siguiente se puede detener
        if avance:
            avance(f"re-escuchando las pausas: {n} de {len(trozos)}…")
        segs = asr.transcribir(x[int(t0 * SR):int(t1 * SR)], word_timestamps=True, vad_filter=False, condition_on_previous_text=False, beam_size=5)
        out.append([(w.word, float(t0 + w.start), float(t0 + w.end), float(w.probability)) for s_ in segs for w in s_.words])
    return out


def voces_fuera(carpeta: Path, palabras: list, avance=None) -> list:
    """Re-escucha cada pausa ≥ 0,3 s sin filtro de voz y agrega lo que encuentre (marcado `fuera`)."""
    x = audio(carpeta)
    # 1) palabras sospechosamente largas (≥ 0,9 s): Whisper suele meter ahí una toma entera; se re-escuchan y se reemplazan
    largas = [k for k, p in enumerate(palabras) if p["e"] - p["s"] >= .9 and not p.get("fuera")]
    if largas:
        oido = reescuchar(x, [(max(0, palabras[k]["s"] - .05), palabras[k]["e"] + .05) for k in largas], avance)
        reemplazo = {}
        for k, vistas in zip(largas, oido):
            ws = [{"w": w.strip(), "s": round(s_, 2), "e": round(e_, 2), "p": round(pr, 2), "releida": True} for w, s_, e_, pr in vistas if _norma(w)]
            if len(ws) > 1:
                reemplazo[k] = ws
        palabras = [w for k, p in enumerate(palabras) for w in (reemplazo.get(k) or [p])]
    palabras = cenir_estiradas(palabras, voz.mapa_voz(voz.energia(x)))
    # 2) voces en las pausas (fuera de cámara)
    huecos = [(0.0, palabras[0]["s"])] if palabras else []
    huecos += [(a["e"], b["s"]) for a, b in zip(palabras, palabras[1:]) if b["s"] - a["e"] >= .3]
    con_sonido = []
    for a, b in huecos:
        t0, t1 = max(0, a - .15), b + .6
        trozo = x[int(t0 * SR):int(t1 * SR)]
        if len(trozo) >= SR * .3 and _db(trozo) >= SILENCIO_DB - 6:
            con_sonido.append((a, b, t0, t1))
    nuevas = []
    for (a, b, _, _), vistas in zip(con_sonido, reescuchar(x, [(t0, t1) for _, _, t0, t1 in con_sonido], avance)):
        for w, ws, we, prob in vistas:
            ws, we = round(ws, 2), round(we, 2)
            medio = (ws + we) / 2
            # la misma palabra pisando a la que ya estaba ES esa palabra: Whisper le estira el inicio hacia la pausa (10-nov,
            # IMG_0653: el «Y» del talento en 5,40–5,72 salió otra vez como «y» en 4,63–5,73 con p 0,35, quedó `fuera` y frenó el guion)
            ya_estaba = any(q["s"] - .05 <= medio <= q["e"] + .05
                            or (_norma(q["w"]) == _norma(w) and (abs(q["s"] - ws) < .6 or min(q["e"], we) > max(q["s"], ws)))
                            for q in palabras if abs(q["s"] - ws) < 2.5)
            estirada = we - ws > 1.2                                       # Whisper estiró la palabra: no es real
            if a - .05 <= medio <= b + .05 and prob > .35 and _norma(w) and not ya_estaba and not estirada:
                nuevas.append({"w": w.strip(), "s": ws, "e": we, "p": round(prob, 2), "fuera": True})
    todas = sorted(palabras + nuevas, key=lambda p: p["s"])
    for k in range(1, len(todas)):           # una palabra «fuera» que pisa el inicio de la siguiente la corre (el «Si» tras «acción»)
        if todas[k - 1].get("fuera") and todas[k]["s"] < todas[k - 1]["e"] and todas[k - 1]["e"] - todas[k]["s"] < .4:
            todas[k]["s"] = round(todas[k - 1]["e"], 2)
            todas[k]["e"] = max(todas[k]["e"], round(todas[k]["s"] + .1, 2))
    return todas


def tramos(sb: dict, fin: float) -> list:
    """Lo que QUEDA del video fuente: el complemento de `cortes`."""
    out, t = [], 0.0
    for a, b in sorted(sb.get("cortes", [])):
        if a > t:
            out.append((t, a))
        t = max(t, b)
    if t < fin:
        out.append((t, fin))
    return [(a, b) for a, b in out if b - a > .05]


def arranques_en_falso(palabras: list, quedan: list, max_palabras=3, max_s=2.0) -> list:
    """Pablo (04-nov, C8868): «deja pasar un error del hablante… corta lo que va atrás y deja solo y todo completamente».
    Un tramo que arranca con un pedazo suelto (≤ max_palabras que cierran una frase cuyo comienzo quedó cortado) justo antes
    de la toma que QUEDA de una repetición es la cola de otra toma («…grabas. lo montas en una carpeta…»): no pasa."""
    err = []
    fs = repeticiones.frases(palabras)
    dentro = lambda p: any(x - 1e-3 <= (p["s"] + p["e"]) / 2 <= y + 1e-3 for x, y in quedan)  # noqa: E731
    for g in repeticiones.grupos(palabras):
        s_u = g[-1]["t0"]
        for a, b in quedan:
            if not a < s_u - .05 <= b:
                continue
            antes = [p for p in palabras if a - 1e-3 <= (p["s"] + p["e"]) / 2 < s_u]
            if not antes or len(antes) > max_palabras or s_u - antes[0]["s"] > max_s:
                continue
            k, k0 = palabras.index(antes[-1]), palabras.index(antes[0])
            i0 = next(i0 for i0, i1 in fs if i0 <= k0 < i1)    # frase a la que pertenece el pedazo
            previas = palabras[i0:k0]
            if any(i1 == k + 1 for _, i1 in fs) and previas and not any(dentro(p) for p in previas):
                err.append(f"montaje: el tramo {a:.2f}–{b:.2f} s arranca con «{' '.join(p['w'] for p in antes)}», la cola de otra "
                           f"toma pegada a la que queda («{g[-1]['texto'][:40]}…», {s_u:.2f} s): empieza el tramo en la toma buena")
    return err


FUERA_OIDO_MAX = .03    # s de voz de fuera (apuntador, claqueta) que pueden quedar en el final: nada que se oiga
TRAMO_MIN = .5          # s: un tramo que queda más corto entre dos cortes es un fragmento, no una frase
ISLA_MAX_S = 2.5        # «isla»: un tramo corto (menos de esto), de pocas palabras (ISLA_MAX_PALABRAS), con un corte grande (≥ ISLA_CORTE_S)
ISLA_MAX_PALABRAS = 3   # a cada lado. Es un resto de otra toma, no una frase del guion (C8867 07-nov: «te», «en», «este con cloud»,
ISLA_CORTE_S = .3       # «listo», «tres» sueltos entre cortes de 5–40 s; Pablo: «no sirve»). Se quita entera. Solo cuentan los
                        # cortes que quitan palabras: los que solo cierran una pausa no aíslan.
COBERTURA = .6          # una palabra con al menos esta fracción dentro de un corte se considera quitada
MAX_PASADAS = 4        # `reparar` repite hasta que una pasada ya no cambie nada
MAX_TRAGADAS = 6        # al ampliar un corte hasta un silencio real no se traga más de tantas palabras del talento


PERSONA = "guion-persona.json"   # las decisiones del guion (la persona en la pantalla; la IA al devolver lo que el detector quitó): {"firma", "dejar": [k], "quitar": [k]}


def firma_palabras(carpeta: Path) -> str:
    """Huella de la transcripción: los índices de palabra de una decisión solo valen para ESTA transcripción. Es la huella de los
    TIEMPOS (cuántas palabras y dónde suena cada una), no de cómo se escriben: corregir la ortografía de una palabra en el mini editor
    (`capas › subtitulo.palabra`, «Cádiz» → «detalles», 12-nov) no es otra transcripción y no borra las decisiones ni la aprobación
    del guion. Antes la huella era de los bytes del archivo: esa corrección soltaba las palabras que la persona dejó («te», 101,4 s)
    y el guion pedía aprobarse otra vez en bucle."""
    import hashlib
    pal = json.loads((Path(carpeta) / "palabras.json").read_text())
    tiempos = [[round(float(p.get("s", p.get("t0", 0))), 3), round(float(p.get("e", p.get("t1", 0))), 3)] for p in pal]
    return hashlib.sha1(json.dumps(tiempos).encode()).hexdigest()[:12]


def firma_vale(carpeta: Path, firma) -> bool:
    """¿Esa huella guardada es de esta transcripción? Acepta también la de antes (bytes del archivo) de lo guardado hasta el 12-nov."""
    import hashlib
    return bool(firma) and firma in (firma_palabras(carpeta), hashlib.sha1((Path(carpeta) / "palabras.json").read_bytes()).hexdigest()[:12])


def decisiones(carpeta: Path) -> dict:
    """Las palabras (por índice, en orden de tiempo) que la persona mandó dejar o quitar en el guion. Mandan sobre el detector: una
    palabra que la persona dejó nunca es «voz de fuera» (11-nov, IMG_4965: el llamado a la acción dicho 15 dB más bajo se tomó por
    apuntador y se perdió sin que nadie pudiera devolverlo). Si la transcripción cambió, ya no valen."""
    f = Path(carpeta) / PERSONA
    try:
        d = json.loads(f.read_text()) if f.exists() else {}
    except ValueError:
        d = {}
    if not d or not firma_vale(carpeta, d.get("firma")):
        return {"dejar": set(), "quitar": set()}
    return {"dejar": set(d.get("dejar", [])), "quitar": set(d.get("quitar", []))}


class Contexto:
    """Lo medido de un proyecto: palabras (con apuntador y claqueta marcados `fuera`), energía, mapa de voz y pausas reales."""

    def __init__(self, carpeta: Path):
        carpeta = Path(carpeta)
        self.fin = json.loads((carpeta / "fuente.json").read_text())["cuadros"] / config.FPS
        cache = carpeta / ".energia.npy"
        if cache.exists():
            self.db = np.load(cache).astype(np.float32)
        else:
            self.db = voz.energia(audio(carpeta))
            np.save(cache, self.db.astype(np.float16))
        vad = voz.mapa_voz(self.db)
        crudas = sorted(json.loads((carpeta / "palabras.json").read_text()), key=lambda p: p["s"])
        self.palabras = voz.marcar_fuera(crudas, self.db, vad)
        persona = decisiones(carpeta)
        for marca in ("dejar", "quitar"):          # `persona` en la palabra: lo que no se puede medir lo decide quien lo dijo
            for k in persona[marca]:
                if k < len(self.palabras):
                    self.palabras[k]["persona"] = marca
        for p in self.palabras:                    # lo que la persona dejó es del talento, diga lo que diga el detector
            if p.get("persona") == "dejar" and p.get("fuera"):
                p.update(fuera=False, motivo="talento: decidido en el guion")
        # silencio = lo que se OYE como silencio: bajo el nivel del talento (no bajo el ruido de la sala). Con el umbral solo
        # relativo al ruido, un soplido a -47 dB contaba como voz y partía la pausa en pedazos cortos que nadie cerraba
        # (Cine C8867, 07-nov: con solo el tope de 0,2 s quedaban 0,50 / 0,45 / 0,38 s mudos en el final).
        suena = voz.sumar_palabras(vad, self.db, self.palabras)
        self.voz = suena & voz.audible(self.db, vad)
        # lo que se decidió dejar en el guion es voz aunque suene muy por debajo del talento: si no, esa frase bajita contaba como
        # «silencio» y el cierre de pausas se la comía después de devolverla (11-nov, llamado a la acción de IMG_4965). Ahí vale el
        # mapa de voz contra el ruido de la sala, sin el filtro «se oye junto al talento».
        self.dejado = np.zeros(len(self.db), bool)
        for p in self.palabras:
            if p.get("persona") == "dejar":
                self.dejado[max(0, int(p["s"] / voz.HOP)):min(len(self.db), int(p["e"] / voz.HOP) + 1)] = True
        self.dejado &= suena
        self.voz |= self.dejado
        self.sil = voz.silencios(self.voz)
        # lo que el oído toma por silencio (C8867 07-nov: 0,16 s de respiración a -44 dB antes de «Es como tener» sumaban 0,3 s
        # mudos en la unión): con esto se miden y se cierran los silencios; los bordes y la voz de fuera siguen con `voz`
        self.talento = voz.talento(self.db, vad)
        self.oye = (self.voz & voz.oido(self.db, self.talento)) | self.dejado   # la misma regla que usa revisar_corte sobre el video terminado
        self.sil_oido = voz.silencios(self.oye)
        self.centros = np.array([(p["s"] + p["e"]) / 2 for p in self.palabras])


_CACHE: dict = {}


def contexto(carpeta: Path) -> Contexto:
    """El contexto de un proyecto, en caché mientras no cambien sus archivos (la compuerta lo pide varias veces por ronda)."""
    carpeta = Path(carpeta)
    firma = tuple(((carpeta / f).stat().st_mtime_ns, (carpeta / f).stat().st_size) if (carpeta / f).exists() else 0
                  for f in ("palabras.json", "fuente.json", ".energia.npy", ".audio16k.npy", PERSONA))
    clave = str(carpeta.resolve())
    if _CACHE.get(clave, (None,))[0] != firma:
        _CACHE.clear()
        _CACHE[clave] = (firma, Contexto(carpeta))
    return _CACHE[clave][1]


def _hay_datos(carpeta: Path) -> bool:
    carpeta = Path(carpeta)
    return (carpeta / "palabras.json").exists() and (carpeta / "fuente.json").exists()


def _corridas_fuera(palabras: list, dentro) -> list:
    """Tandas de palabras `fuera` que quedan en el video: [(primera, ultima)] (una por voz o claqueta seguida)."""
    out, actual = [], []
    for p in palabras:
        if p.get("fuera") and dentro(p):
            if actual and p["s"] - actual[-1]["e"] > .6:
                out.append(actual)
                actual = []
            actual.append(p)
    return out + ([actual] if actual else [])


def repetidas_sin_cortar(c: Contexto, cortes: list) -> list:
    """Versiones anteriores de una frase repetida que siguen en el video (regla: queda la ÚLTIMA), salvo la toma que la persona dejó
    a mano en el guion: ella escogió cuál queda. Un solo lugar para la compuerta del montaje y la del director."""
    libres = [p for p in c.palabras if not p.get("fuera")]
    return repeticiones.faltas(libres, cortes, elegidas=lambda ps: any(p.get("persona") == "dejar" for p in ps))


def _contenido(sb: dict, c: Contexto) -> list:
    """Reglas de contenido (las decide el director): última toma y arranques en falso."""
    libres = [p for p in c.palabras if not p.get("fuera")]
    quedan = tramos(sb, c.fin)
    faltan = repetidas_sin_cortar(c, sb.get("cortes", []))
    err = []
    if faltan:
        err.append("montaje: quedan versiones repetidas (queda solo la ÚLTIMA): " + " | ".join(faltan)[:600])
    return err + arranques_en_falso(libres, quedan)


def _inicio_de_voz(c: Contexto, p: dict) -> float:
    """Donde la energía dice que EMPIEZA a sonar la palabra (Whisper suele adelantarla sobre la pausa previa)."""
    a, b = max(0, int(p["s"] / voz.HOP)), min(len(c.oye), int(p["e"] / voz.HOP) + 1)
    sonando = np.flatnonzero(c.oye[a:b])
    return p["s"] if not len(sonando) else max(p["s"], (a + int(sonando[0])) * voz.HOP)


def _fin_de_voz(c: Contexto, p: dict) -> float:
    """Donde la energía dice que termina de sonar la palabra (Whisper la estira sobre la pausa que le sigue)."""
    a, b = max(0, int(p["s"] / voz.HOP)), min(len(c.oye), int(p["e"] / voz.HOP) + 1)
    sonando = np.flatnonzero(c.oye[a:min(len(c.oye), b + int(.3 / voz.HOP))])   # la cola puede pasar del fin que da Whisper
    if not len(sonando):
        return p["e"]
    k = a + int(sonando[0])                         # la voz que sigue PEGADA a la palabra (sin pausa) es su cola
    while k + 1 < len(c.oye) and c.oye[k + 1] and k + 1 < b + int(.3 / voz.HOP):
        k += 1
    return (k + 1) * voz.HOP


def silencio_mayor(c: Contexto, quedan: list) -> tuple:
    """(duración, segundo del video editado, segundo del original) del silencio más largo del video final, medido sobre el mapa
    de voz adaptativo de `voz` (no un umbral fijo) con los tramos ya unidos: en una unión suma el aire de las dos tomas."""
    if not quedan:
        return 0.0, 0.0, 0.0
    tr = [(int(a / voz.HOP), int(b / voz.HOP)) for a, b in quedan]
    y = np.concatenate([c.oye[a:b] for a, b in tr])
    mapa = np.concatenate([np.arange(a, b) for a, b in tr])       # cuadro editado -> cuadro del original
    largo, peor = 0, (0.0, 0.0, 0.0)
    for i, v in enumerate(y):
        largo = 0 if v else largo + 1
        if largo * voz.HOP > peor[0]:
            ini = i - largo + 1
            peor = (largo * voz.HOP, ini * voz.HOP, float(mapa[ini]) * voz.HOP)
    return peor


def _medibles(sb: dict, c: Contexto) -> list:
    """Lo que se mide en el audio y se repara en código: claqueta/apuntador, cortes en silencio real, aire, pedacitos, silencios."""
    quedan = tramos(sb, c.fin)
    # la voz de fuera no puede SONAR ni un poco en el final: cuenta la voz audible de la palabra que queda dentro de un tramo, no
    # su centro (el final del «tres» de un conteo se colaba al arrancar un tramo, Cine C8867 07-nov)
    def oido(p):
        fuera = c.voz & ~c.dejado      # la voz que cae dentro de una palabra que se decidió dejar es de esa palabra
        n = sum(int(fuera[int(max(a, p["s"]) / voz.HOP):int(min(b, p["e"]) / voz.HOP)].sum()) for a, b in quedan if min(b, p["e"]) > max(a, p["s"]))
        return n * voz.HOP > FUERA_OIDO_MAX
    err = []
    for tanda in _corridas_fuera(c.palabras, oido):
        texto, motivo = " ".join(p["w"] for p in tanda), tanda[0].get("motivo")
        if motivo == "claqueta":
            err.append(f"montaje: claqueta «{texto}» en {tanda[0]['s']:.2f} s quedó en el video: córtala")
        else:
            err.append(f"montaje: voz fuera de cámara «{texto[:60]}» en {tanda[0]['s']:.2f} s quedó en el video: córtala")
    for a, b in quedan:
        for borde, nombre in ((a, "inicio"), (b, "fin")):
            if 0 < borde < c.fin - .01 and voz.hay_voz(c.oye, borde):
                err.append(f"montaje: el {nombre} del tramo {a:.2f}–{b:.2f} s corta con voz sonando: mueve el corte a un silencio")
        ultimas = [p for p in c.palabras if a <= (p["s"] + p["e"]) / 2 <= b and not p.get("fuera")]
        if ultimas and b < c.fin - .01:
            fin_voz = _fin_de_voz(c, ultimas[-1])
            if b - fin_voz < AIRE_FIN - 1e-6:
                sig = next((p for p in c.palabras if p["s"] > fin_voz + 1e-3), None)
                if sig is None or sig["s"] - fin_voz >= AIRE_FIN + .06:     # si las palabras vienen pegadas, es inalcanzable
                    err.append(f"montaje: el tramo {a:.2f}–{b:.2f} s termina {max(0, b - fin_voz):.2f} s después de "
                               f"«{ultimas[-1]['w']}»: deja al menos {AIRE_FIN} s para que la palabra termine")
        if b - a < TRAMO_MIN and 0 < a and b < c.fin - .01:
            err.append(f"montaje: el tramo {a:.2f}–{b:.2f} s dura {b - a:.2f} s: es un pedacito suelto que suena rebobinado; quítalo")
    peor = silencio_mayor(c, quedan)
    if peor[0] > SILENCIO_MAX_S + voz.HOP / 2:
        err.append(f"montaje: hay {peor[0]:.2f} s de silencio en el video final (en {peor[1]:.1f} s del editado, {peor[2]:.1f} s del "
                   f"original): máx. {SILENCIO_MAX_S} s")
    return err


def medibles(sb: dict, carpeta: Path) -> list:
    """Errores de montaje que el código sabe reparar (`reparar`); los que queden son avisos, nunca motivo para tirar el video."""
    return _medibles(sb, contexto(carpeta)) if _hay_datos(carpeta) else []


def errores(sb: dict, carpeta: Path) -> list:
    if not _hay_datos(carpeta):
        return []
    c = contexto(carpeta)
    return _contenido(sb, c) + _medibles(sb, c)


# ---------------------------------------------------------------------------------------------------------------------
# Reparación: el código pone cada corte en un silencio real. Idea de los comandos «roll» y «ripple delete» de FilmCraft
# (MIT/Apache-2.0): un corte se mueve entre las dos palabras que separa, nunca dentro de una.
# ---------------------------------------------------------------------------------------------------------------------

def _descartables(c: Contexto, cortes: list) -> set:
    """Índices de palabras que se pueden tragar al ampliar un corte: voces fuera, lo que el director ya quitó y las versiones
    anteriores de una frase repetida cuya versión limpia (la última) existe después."""
    libres = [p for p in c.palabras if not p.get("fuera")]
    pos = {id(p): k for k, p in enumerate(c.palabras)}
    out = {k for k, p in enumerate(c.palabras) if p.get("fuera") or _cobertura(p, cortes) >= COBERTURA}
    for g in repeticiones.grupos(libres):
        for v in g[:-1]:
            out.update(pos[id(p)] for p in libres[v["i0"]:v["i1"]])
    # tartamudeo de UNA palabra («editar como, como si…», Julián C8866 07-nov): la primera de dos iguales seguidas se puede tragar
    for x, y in zip(libres, libres[1:]):
        if _norma(x["w"]) and _norma(x["w"]) == _norma(y["w"]) and y["s"] - x["e"] < 1.0:
            out.add(pos[id(x)])
    return {k for k in out if c.palabras[k].get("persona") != "dejar"}   # lo que la persona dejó a mano no se traga nunca


def _cobertura(p: dict, cortes: list) -> float:
    """Fracción de la palabra dentro de los cortes (las de duración ~0 que Whisper deja al apilar palabras: dentro o fuera)."""
    if p["e"] - p["s"] < .02:
        return 1.0 if any(a - 1e-3 <= p["s"] <= b + 1e-3 for a, b in cortes) else 0.0
    dur = p["e"] - p["s"]
    return sum(max(0.0, min(b, p["e"]) - max(a, p["s"])) for a, b in cortes) / dur


def _fusionar(cortes: list, holgura=.02) -> list:
    out = []
    for a, b in sorted((float(a), float(b)) for a, b in cortes if b > a):
        if out and a <= out[-1][1] + holgura:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out


def _mejor_punto(c: Contexto, t0: float, lo: float, hi: float, ocupadas: set, previa_e: float | None = None) -> float | None:
    """El punto de corte válido (en una pausa real, con margen a la voz) más cercano a t0 dentro de [lo, hi]. None si no hay."""
    mejor = None
    for sa, sb in c.sil_oido:   # la misma regla del oído para poner bordes
        a, b = max(sa, lo), min(sb, hi)
        if b - a < voz.MIN_SILENCIO_S - 1e-6 and not (a <= t0 <= b):
            continue
        if sb - sa < voz.MIN_SILENCIO_S - 1e-6:
            continue
        m = min(.08, (sb - sa) / 2)
        a, b = max(a, sa + m), min(b, sb - m)
        if a > b + 1e-9:
            continue
        if previa_e is not None and previa_e + AIRE_FIN <= b:      # con aire para que la palabra anterior termine, si cabe en esta pausa
            a = max(a, previa_e + AIRE_FIN)
        p = min(max(t0, a), b)
        costo = abs(p - t0)
        k = int(np.searchsorted(c.centros, p))
        for j in (k - 1, k):             # no partir una palabra conservada
            if 0 <= j < len(c.palabras) and j not in ocupadas and c.palabras[j]["s"] + .04 < p < c.palabras[j]["e"] - .04:
                costo += .5
        if previa_e is not None and p - previa_e < AIRE_FIN:
            costo += .3
        if mejor is None or costo < mejor[0]:
            mejor = (costo, p)
    return None if mejor is None else round(mejor[1], 3)


def _punto_de_menor_energia(c: Contexto, lo: float, hi: float) -> float:
    """El cuadro de menor energía (a 1 dB; a igual energía, el más cerca del centro) entre las dos palabras que separa el corte."""
    a = max(0, int(lo / voz.HOP))
    b = max(int(hi / voz.HOP), a + 1)
    seg = np.round(c.db[a:b])
    if not len(seg):
        return round((lo + hi) / 2, 3)
    t = (a + np.arange(len(seg)) + .5) * voz.HOP
    k = int(np.lexsort((np.abs(t - (lo + hi) / 2), seg))[0])
    return round(float(t[k]), 3)


def _resolver(c: Contexto, a: float, b: float, forzadas: set, tragables: set, avisos: list, forzar: bool = False) -> tuple | None:
    """Pone los dos bordes del corte [a, b] en pausas reales SIN cambiar qué palabras quita, salvo las que se pueden tragar.
    `forzar` = es un corte de voz fuera de cámara que pone el código (no el director): si no se puede sin llevarse talento sin
    repetición limpia, no se borra. Un corte del director nunca se descarta por esto: se pone en el mínimo de energía (aviso).
    Devuelve el corte nuevo, o None si no se puede (el motivo queda en `avisos`)."""
    P, cen, n = c.palabras, c.centros, len(c.palabras)
    quitadas = {k for k in range(n) if _cobertura(P[k], [(a, b)]) >= COBERTURA or (k in forzadas and _cobertura(P[k], [(a, b)]) > .1)}
    if quitadas:
        i0, i1 = min(quitadas), max(quitadas) + 1
    else:
        i0 = i1 = int(np.searchsorted(cen, (a + b) / 2))      # corte de pura pausa: vive entre dos palabras
    quitadas = set(range(i0, i1))
    tragadas = 0
    bordes = {}
    for lado in ("a", "b"):
        t0 = a if lado == "a" else b
        if (lado == "a" and a <= 1e-3) or (lado == "b" and b >= c.fin - 1e-3):
            bordes[lado] = t0
            continue
        while True:
            # la búsqueda va de palabra a palabra, pero medida donde SUENAN (no donde Whisper las pone): Whisper cerró «paso» en
            # 64,78 s y sonaba hasta 64,95, y el corte quedaba encima de la palabra (C8869 07-nov: «mocha paso a paso»)
            if lado == "a":
                lo, hi = (cen[i0 - 1] if i0 > 0 else 0.0), (cen[i0] if i0 < n else c.fin)
                if i0 < n:                                     # hasta donde de verdad empieza la primera palabra que se quita:
                    cola = _fin_de_voz(c, P[i0 - 1]) if i0 > 0 else 0.0     # pasada la cola de la anterior y su pausa
                    pausa = next((sb for sa, sb in c.sil_oido if sa - .02 <= cola <= sb + 1e-6 or cola <= sa <= P[i0]["e"]), None)
                    hi = max(hi, min(pausa, P[i0]["e"]) if pausa else _inicio_de_voz(c, P[i0]))
                previa = max(P[i0 - 1]["e"], _fin_de_voz(c, P[i0 - 1])) if i0 > 0 and (i0 - 1) not in quitadas else None
            else:
                lo, hi = (cen[i1 - 1] if i1 > 0 else 0.0), (cen[i1] if i1 < n else c.fin)
                if i1 > 0:
                    lo = min(lo, _fin_de_voz(c, P[i1 - 1]))
                previa = None
            ya_vale = not voz.hay_voz(c.voz, t0) and lo < t0 <= hi + 1e-9
            if ya_vale and (lado == "b" or previa is None or t0 - previa >= AIRE_FIN or hi - t0 < .06):
                bordes[lado] = t0     # el borde del director ya cumple: no se toca (idempotente y no pisa lo aprobado)
                break
            p = _mejor_punto(c, t0, lo, hi, quitadas, previa)
            if p is not None:
                bordes[lado] = p
                break
            vecina = (i0 - 1) if lado == "a" else i1
            if 0 <= vecina < n and vecina in tragables and tragadas < MAX_TRAGADAS:
                quitadas.add(vecina)             # voz pegada al talento: se amplía el corte hasta el silencio real
                tragadas += 1
                if lado == "a":
                    i0 = vecina
                else:
                    i1 = vecina + 1
                continue
            if forzar and forzadas & quitadas:
                avisos.append({"t": round(t0, 2), "tipo": "no_borrar",
                               "motivo": "voz fuera de cámara pegada a palabras del talento SIN una repetición limpia posterior: no se borra "
                                         f"(palabra «{P[vecina]['w'] if 0 <= vecina < n else '?'}» en {P[vecina]['s'] if 0 <= vecina < n else t0:.2f} s)"})
                return None
            if not quitadas:
                avisos.append({"t": round(t0, 2), "tipo": "deshecho", "motivo": "corte de pausa sin un silencio real donde ponerlo: se deshace"})
                return None
            if lado == "a":     # entre el final de la palabra que queda y el inicio de la primera quitada (Whisper las pega)
                x, y = (P[i0 - 1]["e"] if i0 > 0 else 0.0), (P[i0]["s"] if i0 < n else c.fin)
            else:
                x, y = (P[i1 - 1]["e"] if i1 > 0 else 0.0), (P[i1]["s"] if i1 < n else c.fin)
            x, y = min(x, y) - .03, max(x, y) + .03
            bordes[lado] = _punto_de_menor_energia(c, max(lo, x), min(hi, y) if min(hi, y) > max(lo, x) else hi)
            avisos.append({"t": bordes[lado], "tipo": "degradado",
                           "motivo": "no hay silencio entre estas palabras (vienen pegadas): corte en el punto de menor energía"})
            break
    a2, b2 = bordes["a"], bordes["b"]
    return (a2, b2) if b2 - a2 > .01 else None


def _acortar_silencios(c: Contexto, cortes: list) -> list:
    """Ningún silencio pasa de SILENCIO_MAX_S en el final, medido sobre la energía (el mapa de voz de `voz`, que ya cuenta como
    voz las palabras suaves): no se mira el tiempo de Whisper, que estira palabras sobre las pausas.
    · En cada unión el aire total (el de la toma A + el de la B) se recorta a SILENCIO_META_S, repartido por igual; el lado de la
      toma A nunca baja de AIRE_FIN después de su voz ni el de la B de ARRANQUE_MIN_S antes de la suya: no se corta ninguna sílaba.
    · Las pausas largas dentro de un tramo se cierran igual (queda SILENCIO_META_S de pausa), salvo que el corte deje un
      pedacito suelto de menos de TRAMO_MIN: entonces se deja y la compuerta lo avisa.
    · En el borde del video queda a lo más medio SILENCIO_META_S."""
    cortes = [list(x) for x in cortes]
    mitad = SILENCIO_META_S / 2
    pausa = lambda t: next(((sa, sb) for sa, sb in c.sil_oido if sa - 1e-6 <= t <= sb + 1e-6), None)  # noqa: E731
    quedan = tramos({"cortes": cortes}, c.fin)
    for k, (ca, cb) in enumerate(cortes):
        izq, der = (pausa(ca) if ca > 1e-3 else None), (pausa(cb) if cb < c.fin - 1e-3 else None)
        ka = max((x for x, y in quedan if y <= ca + 1e-3), default=0.0)
        kb = min((y for x, y in quedan if x >= cb - 1e-3), default=c.fin)
        if not (izq or der):
            continue
        vl = max(izq[0], ka) if izq else ca              # donde termina la voz de la toma A (o el borde del video)
        vr = min(der[1], kb) if der else cb              # donde empieza la voz de la toma B
        l, r = ca - vl, vr - cb
        if l + r <= SILENCIO_META_S + 1e-6:
            continue
        if not izq:                                      # inicio del video: solo hay aire del lado de la toma B
            nl, nr = 0.0, min(r, mitad)
        elif not der:                                    # fin del video: solo hay aire del lado de la toma A
            nl, nr = min(l, mitad), 0.0
        else:
            nl = min(l, max(SILENCIO_META_S - min(r, mitad), mitad))
            nr = min(r, max(SILENCIO_META_S - nl, ARRANQUE_MIN_S))
        nca = min(ca, vl + max(nl, AIRE_FIN)) if izq else ca
        ncb = max(cb, vr - max(nr, ARRANQUE_MIN_S)) if der else cb
        for cand in ([nca, ncb], [nca, cb], [ca, ncb]):          # primero el recorte completo; si se lleva una palabra, un solo lado
            if not _quita_palabra_nueva(c, [(ca, cb)], [tuple(cand)]):
                cortes[k] = cand
                break
    extra = []
    quedan = tramos({"cortes": cortes}, c.fin)
    for ka, kb in quedan:
        inicio = ka                                       # donde empieza el pedazo que queda tras los cortes internos ya puestos
        for sa, sb in c.sil_oido:
            x, y = max(sa, ka), min(sb, kb)
            if y - x <= SILENCIO_META_S + 1e-6 or (x <= ka + 1e-3 and ka > 1e-3) or (y >= kb - 1e-3 and kb < c.fin - 1e-3):
                continue
            x2 = x + mitad if x > ka + 1e-3 else x         # en el borde del video no hay «otro lado»
            y2 = y - mitad if y < kb - 1e-3 else y
            # el pedacito que quedaría suelto al borde del tramo («colores. [2 s] Ya» en C8869 07-nov: el «Ya» de «ya hice» protegía
            # el silencio): si son a lo más ISLA_MAX_PALABRAS - 2 palabras, se va con el silencio en vez de dejar las dos cosas
            palabras_en = lambda a, b: sum(1 for p in c.palabras if not p.get("fuera") and a <= (p["s"] + p["e"]) / 2 <= b)  # noqa: E731
            huerfano = False
            if kb < c.fin - 1e-3 and kb - y2 < TRAMO_MIN and palabras_en(y2, kb) <= ISLA_MAX_PALABRAS - 2:
                y2, huerfano = kb, True
            elif inicio > 1e-3 and x2 - inicio < TRAMO_MIN and palabras_en(inicio, x2) <= ISLA_MAX_PALABRAS - 2:
                x2, huerfano = inicio, True
            if y2 - x2 <= .02 or (inicio > 1e-3 and x2 - inicio < TRAMO_MIN and x2 > inicio) or (kb < c.fin - 1e-3 and kb - y2 < TRAMO_MIN and y2 < kb):
                continue
            if not huerfano and _quita_palabra_nueva(c, [], [(x2, y2)]):     # el huérfano se quita a propósito
                continue
            extra.append([x2, y2])
            inicio = y2
    return _fusionar(cortes + extra)


def _voz_de(c: Contexto, p: dict) -> float:
    """Fracción de la palabra donde la ENERGÍA dice que suena voz (Whisper estira palabras sobre las pausas: una palabra con poca
    voz medida está mal puesta en el tiempo; cortar su parte en silencio no le quita nada al audio)."""
    a, b = max(0, int(p["s"] / voz.HOP)), max(int(p["e"] / voz.HOP), int(p["s"] / voz.HOP) + 1)
    return float(c.oye[a:b].mean()) if b > a and a < len(c.oye) else 0.0


def _cobertura_voz(c: Contexto, p: dict, cortes: list) -> float:
    """Como `_cobertura`, pero medida sobre la VOZ de la palabra y no sobre su tiempo: Whisper estira una palabra sobre la pausa que la
    precede (glass-nuevo-10nov: «entendí» empezaba 0,6 s antes de sonar), y cortar esa parte en silencio no le quita nada al audio."""
    a, b = max(0, int(p["s"] / voz.HOP)), min(len(c.oye), int(p["e"] / voz.HOP) + 1)
    sonando = np.flatnonzero(c.oye[a:b]) + a
    if not len(sonando):
        return _cobertura(p, cortes)
    t = (sonando + .5) * voz.HOP
    return float(np.mean([any(x <= ti <= y for x, y in cortes) for ti in t]))


def palabras_que_quedan(c: Contexto, cortes: list) -> list:
    """ÚNICA regla de «qué palabras quedan» para decidir si dos juegos de cortes son el mismo guion: los índices de las palabras que NO
    quedan quitadas. Mover un borde dentro de un silencio no cambia esta lista.
    · Palabra con voz medida (`_voz_de` ≥ VOZ_PALABRA_MIN): queda si el corte cubre menos de COBERTURA de su VOZ (un resto audible cuenta).
    · Palabra con menos voz que eso: Whisper la puso mal en el tiempo (un «Y» de 0,01 s a -57 dB) y el audio no puede decidir. Vale lo
      que se marcó en el guion (IMG_4965, 11-nov: «dos» y «sí» caían sobre una pausa cerrada y salían del texto aunque se oían: la
      persona las devuelve con un toque y quedan); sin marca, su punto medio, como siempre."""
    return [k for k, p in enumerate(c.palabras) if _queda(c, p, cortes)]


def _queda(c: Contexto, p: dict, cortes: list) -> bool:
    if _voz_de(c, p) < VOZ_PALABRA_MIN:
        if p.get("persona"):
            return p["persona"] == "dejar"
        m = (p["s"] + p["e"]) / 2
        return not any(a <= m <= b for a, b in cortes)
    return _cobertura_voz(c, p, cortes) < COBERTURA


def quedan(c: Contexto, cortes: list) -> list:
    """Las palabras (dicts de `c.palabras`, en orden) que quedan con esos cortes: el guion. Lo usan la app (`servidor._guion`), la revisión
    final y Estilos Pro (`machote.palabras_cortadas`) y la decisión de «mismo guion»: una sola regla, por voz."""
    return [c.palabras[k] for k in palabras_que_quedan(c, cortes)]


def _quita_palabra_nueva(c: Contexto, antes: list, despues: list) -> bool:
    """¿El corte ampliado se lleva una palabra con voz que el director conservó? Si es así ese cambio no se hace (la compuerta avisa
    el silencio que queda): acortar un silencio nunca se come una palabra."""
    return any(not p.get("fuera") and _voz_de(c, p) >= VOZ_PALABRA_MIN and _cobertura_voz(c, p, antes) < COBERTURA
               and _cobertura_voz(c, p, despues) >= COBERTURA - .05 for p in c.palabras)


def reparar(sb: dict, carpeta: Path, avisos: list | None = None) -> dict:
    """Deja los `cortes` medibles bien hechos SIN tocar qué frases eligió el director, y en código (0 llamadas a la IA):
    · lo `fuera` (apuntador, claqueta, voces fuera de cámara) se corta ENTERO, ampliando el corte hasta un silencio real aunque
      se lleve palabras pegadas del talento, pero SOLO si esas palabras tienen una repetición limpia posterior; si no, no se borra
      y queda un aviso con el segundo y el motivo;
    · cada borde cae en una pausa real (mapa de voz adaptativo), nunca dentro de una palabra conservada ni con voz sonando;
    · un corte de pura pausa sin dónde ponerlo se deshace; uno de contenido sin silencio se pone en el mínimo de energía (aviso);
    · se cierran los silencios largos y se juntan los pedacitos sueltos.
    Idempotente: reparar(reparar(x)) == reparar(x). Lo que no se pueda queda en `avisos` [{t, tipo, motivo}]; nunca lanza por eso."""
    avisos = [] if avisos is None else avisos
    carpeta = Path(carpeta)
    if not _hay_datos(carpeta):
        return sb
    c = contexto(carpeta)
    cortes = [(max(0.0, float(a)), min(c.fin, float(b))) for a, b in sb.get("cortes", [])
              if np.isfinite(a) and np.isfinite(b)]
    previos = []
    for _ in range(MAX_PASADAS):     # punto fijo: lo que una pasada agranda (un pedacito suelto) cambia qué es «tragable» en la siguiente
        parciales = []
        nuevo = [(round(a, 3), round(b, 3)) for a, b in _pasada(c, cortes, parciales)]
        previos += [x for x in parciales if x["tipo"] in ("pedacito", "deshecho")]   # lo que una pasada hizo y la siguiente ya no repite
        estable = nuevo == [(round(a, 3), round(b, 3)) for a, b in _fusionar(cortes)]
        cortes = nuevo
        if estable:
            break
    avisos += [x for x in previos if x not in parciales] + parciales
    return {**sb, "cortes": [[round(a, 3), round(b, 3)] for a, b in cortes]}




def _isla(c: Contexto, quedan: list):
    """La primera «isla» (ver ISLA_*) como (inicio, fin) o None. Una isla puede ser un grupo de tramos cortos separados por cortes
    chicos («este con cloud» + «listo»): cuenta el grupo entero. El primer y el último tramo también pueden serlo si del otro lado
    hay un corte de contenido (C8867 07-nov: el video arrancaba con 0,6 s de «acción» y «¡hasta la próxima!» de fondo)."""
    # solo cuenta un corte que quita CONTENIDO (alguna palabra): uno que solo cierra una pausa no aísla nada
    grande = lambda a, b: b - a >= ISLA_CORTE_S and any(a < (p["s"] + p["e"]) / 2 < b for p in c.palabras)  # noqa: E731
    if len(quedan) < 2:
        return None
    k = 0
    while k < len(quedan):
        j = k
        while j + 1 < len(quedan) and not grande(quedan[j][1], quedan[j + 1][0]):
            j += 1
        if k == 0 and j == len(quedan) - 1:
            return None                                           # un solo bloque: no hay nada de qué aislarse
        x, y = quedan[k][0], quedan[j][1]
        dur = sum(b - a for a, b in quedan[k:j + 1])
        antes = k == 0 or grande(quedan[k - 1][1], x)
        despues = j == len(quedan) - 1 or grande(y, quedan[j + 1][0])
        if dur < ISLA_MAX_S and antes and despues:
            ws = [_norma(p["w"]) for p in c.palabras if not p.get("fuera") and p["e"] - p["s"] > .02 and x <= (p["s"] + p["e"]) / 2 <= y]
            ws = [w for w in ws if w]
            # solo es resto de OTRA toma si esas palabras se vuelven a decir después (la última toma manda); un pedazo único del
            # guion entre dos cortes («es de centavos», Prestiggio C8873) no se toca
            despues_ws = [_norma(p["w"]) for p in c.palabras if not p.get("fuera") and p["s"] > y]
            se_repite = not ws or any(despues_ws[i:i + len(ws)] == ws for i in range(len(despues_ws) - len(ws) + 1))
            if len(ws) <= ISLA_MAX_PALABRAS and se_repite:
                return x, y
        # arranque en falso dentro del grupo: un tramo corto con un corte de contenido a un lado y una pausa cortada al otro,
        # cuyas palabras se vuelven a decir justo después («te … te cuatro», C-0010): también es resto de otra toma
        for m in range(k, j + 1):
            a_, b_ = quedan[m]
            if b_ - a_ >= ISLA_MAX_S:
                continue
            lados = [(quedan[m - 1][1], a_) if m > 0 else None, (b_, quedan[m + 1][0]) if m + 1 < len(quedan) else None]
            if not any(l and grande(*l) for l in lados) or not all(l is None or l[1] - l[0] >= ISLA_CORTE_S for l in lados):
                continue
            ws = [w for w in (_norma(p["w"]) for p in c.palabras if not p.get("fuera") and p["e"] - p["s"] > .02
                              and a_ <= (p["s"] + p["e"]) / 2 <= b_) if w]
            sig = [_norma(p["w"]) for p in c.palabras if not p.get("fuera") and p["s"] > b_][:len(ws)]
            if ws and len(ws) <= ISLA_MAX_PALABRAS and sig == ws:
                return a_, b_
        k = j + 1
    return None


def _pasada(c: Contexto, validos: list, avisos: list) -> list:
    """Una pasada de `reparar`: devuelve los cortes ya puestos en silencios reales (y deja los avisos en `avisos`)."""
    originales = _fusionar(validos)
    tragables = _descartables(c, originales)
    fuera = {k for k, p in enumerate(c.palabras) if p.get("fuera")}
    resueltos = []
    for a, b in originales:
        r = _resolver(c, a, b, fuera, tragables, avisos)
        if r:
            resueltos.append(r)
    k = 0
    while k < len(c.palabras):                       # cada tanda de voz fuera de cámara, entera
        if k in fuera:
            j = k
            while j + 1 < len(c.palabras) and (j + 1) in fuera:
                j += 1
            a, b = c.palabras[k]["s"], max(c.palabras[j]["e"], c.palabras[j]["s"] + .05)
            if any(_cobertura(c.palabras[m], resueltos) < COBERTURA for m in range(k, j + 1)):     # ya la quitó otro corte
                r = _resolver(c, a, b, fuera, tragables, avisos, forzar=True)
                if r:
                    resueltos.append(r)
            k = j + 1
        else:
            k += 1
    avisos[:] = [dict(t) for t in {tuple(sorted(x.items())) for x in avisos}]
    avisos.sort(key=lambda x: x["t"])
    cortes = _fusionar(resueltos)
    for _ in range(4):                               # cada paso solo AGRANDA cortes: termina
        previo = cortes
        while True:                                  # pedacitos sueltos entre dos cortes: suenan a palabra rebobinada
            quedan = tramos({"cortes": cortes}, c.fin)
            suelto = next(((x, y) for x, y in quedan if y - x < TRAMO_MIN and x > 1e-3 and y < c.fin - .01), None) \
                or _isla(c, quedan)
            if suelto is None:
                break
            perdidas = [p["w"] for p in c.palabras if not p.get("fuera") and suelto[0] <= (p["s"] + p["e"]) / 2 <= suelto[1]]
            if perdidas:
                avisos.append({"t": round(suelto[0], 2), "tipo": "pedacito",
                               "motivo": f"un tramo suelto de {suelto[1] - suelto[0]:.2f} s se quitó y se llevó «{' '.join(perdidas)[:40]}»"})
            cortes = _fusionar(cortes + [[max(0.0, suelto[0] - .001), min(c.fin, suelto[1] + .001)]], holgura=.003)
        cortes = _acortar_silencios(c, cortes)
        if cortes == previo:
            break
    # un aviso de un borde que otro corte más grande se tragó ya no existe
    cortados = [(c.palabras[k]["s"], c.palabras[k]["e"], c.palabras[k].get("motivo")) for k in fuera if c.palabras[k].get("motivo") == "apuntador"]
    if cortados:          # que un apuntador borrado nunca pase en silencio (si fuera un talento que susurra, se ve)
        avisos.append({"t": round(cortados[0][0], 2), "tipo": "apuntador",
                       "motivo": f"{len(cortados)} palabras tratadas como apuntador (voz ~{voz.APUNTADOR_BAJO_DB} dB bajo el talento) entre "
                                 f"{cortados[0][0]:.1f} y {cortados[-1][1]:.1f} s: revisa que no sea el talento hablando bajo"})
    avisos[:] = [x for x in avisos if x["tipo"] in ("no_borrar", "apuntador", "pedacito") or not any(a + .05 < x["t"] < b - .05 for a, b in cortes)]
    return cortes
