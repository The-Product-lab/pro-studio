"""Repartir una grabación en videos (docs/PLANO-LOTE.md). Pablo, 13-nov: «yo te puedo entregar 30 archivos de video y tú miras cuántos
videos finales salen… tienes que revisar a través de las transcripciones qué idea se cierra, qué guion se cierra».

Una TANDA es lo que se subió junto: `proyectos/_tandas/<id>/tanda.json` (archivos, propuesta, avisos, estado) y la transcripción de
cada archivo al lado (`<archivo>.palabras.json`). El camino:
  1. `crear`: anota los archivos.  2. `transcribir`: uno a la vez; lo ya hecho no se repite; sin voz se marca.
  3. `agrupar`: Opus lee las transcripciones y propone los videos (qué archivos, en qué orden, qué tomas sobran: de una idea repetida
     queda la ÚLTIMA). Sin IA, reparto por código.  4. `revisar`: la compuerta, en código: ningún archivo ni palabra se pierde sin
     decirlo, ningún tramo queda en dos videos, un archivo solo se parte en una pausa. Por ella pasa también lo que mueve la persona.
  5. `armar`: corta y une los tramos de un video aprobado y deja sus palabras ya puestas en el tiempo nuevo (no se transcribe otra vez).
Lo que NO decide el código: si dos ideas quedaron mezcladas. Eso lo propone Opus y lo aprueba la persona; nada se prepara sin su sí."""
import json
import os
import re
import subprocess
import threading
import time
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

from . import config, errores, ia, ingesta, unir

PAUSA_FRASE_S = .6            # una pausa así (o un punto) cierra una frase en lo que lee el agrupador
PARECIDA = .75                # dos textos así de parecidos son la misma toma repetida
PARECIDA_MIN_PALABRAS = 4     # …si tienen al menos estas palabras (un «listo» suelto no es una toma repetida)
TRAMO_MIN_S = .3              # un tramo más corto no es nada
SIN_VOZ, REPETIDA, SIN_UBICAR = "sin voz", "toma repetida: queda la última", "sin ubicar: el agrupador no dijo dónde va"
SIN_IA = ("Sin IA no se puede saber qué archivos forman una misma idea: cada archivo quedó como un video (las tomas repetidas ya "
          "están en «Sobran»). Júntalos tú antes de aprobar.")
_CANDADO = threading.Lock()   # una tanda a la vez escribe su archivo


def raiz() -> Path:
    return config.PROYECTOS / "_tandas"


def carpeta(tid: str) -> Path:
    if not re.fullmatch(r"[a-z0-9-]{3,60}", str(tid)):
        raise ValueError("tanda inválida")
    return raiz() / tid


def leer(tid: str) -> dict:
    f = carpeta(tid) / "tanda.json"
    if not f.is_file():
        raise errores.Aviso("Ya no encuentro esa tanda de archivos. Súbelos otra vez.")
    return json.loads(f.read_text(encoding="utf-8"))


def guardar(t: dict) -> dict:
    """Entero o nada (temporal + reemplazo): la pantalla, que pregunta a cada rato, nunca lee medio archivo."""
    d = carpeta(t["id"])
    d.mkdir(parents=True, exist_ok=True)
    with _CANDADO:
        tmp = d / f"tanda.json.{threading.get_ident()}.part"
        tmp.write_text(json.dumps(t, ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(tmp, d / "tanda.json")
    return t


def _natural(nombre: str) -> list:
    return [int(x) if x.isdigit() else x.lower() for x in re.split(r"(\d+)", nombre)]


def crear(videos: list) -> dict:
    """Tanda nueva con esos archivos (ya subidos), en orden de nombre («toma 2» antes que «toma 10»). El orden es solo una pista."""
    rutas = sorted((Path(v) for v in videos), key=lambda r: _natural(r.name))
    if not rutas:
        raise errores.Aviso("No hay archivos para repartir.")
    falta = next((r for r in rutas if not r.is_file()), None)
    if falta:
        raise errores.Aviso(f"Ya no encuentro «{falta.name}». Sube los archivos otra vez.")
    base = time.strftime("t-%Y%m%d-%H%M%S")
    tid = next(x for n in range(1, 1000) if not (raiz() / (x := base if n == 1 else f"{base}-{n}")).exists())
    archivos = [{"id": f"a{i + 1}", "nombre": r.name, "video": str(r), "fecha": r.stat().st_mtime, "estado": "pendiente"}
                for i, r in enumerate(rutas)]
    return guardar({"id": tid, "creada": time.time(), "estado": "transcribiendo", "archivos": archivos, "propuesta": None, "avisos": []})


def palabras_de(t: dict, aid: str) -> list:
    f = carpeta(t["id"]) / f"{aid}.palabras.json"
    return sorted(json.loads(f.read_text(encoding="utf-8")), key=lambda p: p["s"]) if f.is_file() else []


def transcribir(tid: str, avance=print) -> dict:
    """Un archivo a la vez (Whisper además tiene su propio candado: nunca dos a la vez en el equipo). Lo ya transcrito se salta."""
    t = leer(tid)
    n = len(t["archivos"])
    for i, a in enumerate(t["archivos"], 1):
        if a["estado"] in ("transcrito", "sin_voz"):
            continue
        avance(f"transcribiendo {i} de {n}: {a['nombre']}")
        try:
            sonda = unir._sonda(Path(a["video"]))
            a["duracion"] = round(sonda["duracion"], 3)
            palabras = ingesta.transcribir(Path(a["video"]), carpeta(tid) / f"{a['id']}.palabras.json") if sonda["audio"] else []
            if not sonda["audio"]:
                (carpeta(tid) / f"{a['id']}.palabras.json").write_text("[]", encoding="utf-8")
            a["palabras"] = len(palabras)
            a["texto"] = " ".join(p["w"] for p in palabras)[:400]
            a["estado"] = "transcrito" if palabras else "sin_voz"
        except (errores.Aviso, subprocess.CalledProcessError) as e:   # un archivo que no se puede leer no tumba la tanda: queda dicho y va a «Sobran»
            errores.registrar(f"tanda {tid} {a['id']}", e)
            (carpeta(tid) / f"{a['id']}.palabras.json").write_text("[]", encoding="utf-8")
            a.update(estado="error", motivo="no se pudo leer: " + errores.frase(e), duracion=a.get("duracion", 0), palabras=0, texto="")
        guardar(t)
    return t


# ---------- lo que lee el agrupador ----------
def frases(palabras: list) -> list:
    """[(t0, t1, texto)]: las palabras juntas hasta una pausa larga o un punto. Son los únicos lugares donde un archivo se puede partir."""
    out, actual = [], []
    for k, p in enumerate(palabras):
        actual.append(p)
        sig = palabras[k + 1] if k + 1 < len(palabras) else None
        if sig is None or sig["s"] - p["e"] >= PAUSA_FRASE_S or p["w"].rstrip().endswith((".", "?", "!")):
            out.append((actual[0]["s"], actual[-1]["e"], " ".join(x["w"] for x in actual)))
            actual = []
    return out


def _hoja(t: dict) -> str:
    """Las transcripciones de la tanda, archivo por archivo, con el tiempo de cada frase: lo ÚNICO que ve el agrupador."""
    partes = []
    for a in t["archivos"]:
        if a["estado"] != "transcrito":
            continue
        cab = (f"## {a['id']} · {a['nombre']} · dura {a['duracion']:.1f} s · grabado "
               f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(a.get('fecha', 0)))}")
        partes.append(cab + "\n" + "\n".join(f"[{a0:.2f}–{b0:.2f}] {tx}" for a0, b0, tx in frases(palabras_de(t, a["id"]))))
    return "\n\n".join(partes) + "\n"


PROMPT = """Eres el montajista de una grabación. La persona grabó varios archivos seguidos y de ahí salen uno o varios videos cortos
(reels). Lee `transcripciones.md` (está en esta carpeta): trae cada archivo con su id, nombre, duración, hora de grabación y lo que se
dijo, frase por frase, con sus segundos.

Decide cuántos videos salen y qué va en cada uno. Un video = UNA idea o un guion que abre y CIERRA (gancho, desarrollo, cierre o
llamado). Reglas:
1. Nunca mezcles dos ideas en un video. Si dudas entre juntar o separar, separa.
2. Un video puede venir en varios archivos (lo grabó por partes): júntalos en el orden en que tiene sentido decirlos. El nombre y la
   hora son una pista, no una orden.
3. Si la misma idea o frase está dicha más de una vez (repitió la toma), queda SOLO la última vez; las anteriores van a `sobran` con
   motivo "toma repetida". Una toma que se corta, se equivoca o es charla con el equipo va a `sobran` con motivo "toma fallada".
4. Si un archivo trae dos ideas, pártelo: usa `desde` y `hasta` (segundos de ESE archivo), cortando siempre entre dos frases.
5. Todo lo dicho en todos los archivos tiene que quedar en un video o en `sobran`. No dejes nada sin ubicar.

Responde SOLO este JSON, sin texto alrededor:
{"videos": [{"titulo": "3 a 6 palabras", "idea": "la idea que cierra, en una frase",
             "tramos": [{"archivo": "a1", "desde": 0, "hasta": 12.5}]}],
 "sobran": [{"archivo": "a2", "desde": 0, "hasta": 8.0, "motivo": "toma repetida"}]}
`desde` y `hasta` se pueden omitir para tomar el archivo entero."""


def _con_opus(t: dict, avance=print) -> dict | None:
    d = carpeta(t["id"])
    (d / "transcripciones.md").write_text(_hoja(t), encoding="utf-8")   # en un archivo: la orden tiene tope de largo (Windows)
    for intento in range(2):
        avance("el agrupador (Opus) lee las transcripciones…" if not intento else "el agrupador no respondió claro; se le pide otra vez…")
        prompt = PROMPT + ("\n\nIMPORTANTE: tu respuesta anterior no era JSON. Responde SOLO el objeto JSON." if intento else "")
        out = ia.llamar(prompt, "opus", d, herramientas="Read", tope_usd=1.5, paso="tanda-agrupar")
        try:
            resp = ia.json_de(out.get("result", ""))
        except ValueError:
            resp = None
        if isinstance(resp, dict) and isinstance(resp.get("videos"), list) and resp["videos"]:
            return {"origen": "opus", "videos": resp["videos"], "sobran": resp.get("sobran") or []}
    return None


def _normal(texto: str) -> list:
    sin = unicodedata.normalize("NFD", texto.lower())
    return re.findall(r"[a-z0-9]+", "".join(c for c in sin if unicodedata.category(c) != "Mn"))


def _parecidas(a: str, b: str) -> bool:
    x, y = _normal(a), _normal(b)
    return min(len(x), len(y)) >= PARECIDA_MIN_PALABRAS and SequenceMatcher(None, x, y).ratio() >= PARECIDA


def por_codigo(t: dict) -> dict:
    """Sin IA: cada archivo con voz es un video, salvo las tomas repetidas (queda la última). Juntar ideas lo hace la persona."""
    con_voz = [a for a in t["archivos"] if a["estado"] == "transcrito"]
    textos = {a["id"]: " ".join(p["w"] for p in palabras_de(t, a["id"])) for a in con_voz}
    videos, sobran = [], []
    for k, a in enumerate(con_voz):
        despues = next((b for b in reversed(con_voz[k + 1:]) if _parecidas(textos[a["id"]], textos[b["id"]])), None)   # la ÚLTIMA que la repite
        if despues:
            sobran.append({"archivo": a["id"], "motivo": f"{REPETIDA} ({despues['nombre']})"})
        else:
            videos.append({"titulo": Path(a["nombre"]).stem, "idea": "", "tramos": [{"archivo": a["id"]}]})
    return {"origen": "codigo", "videos": videos, "sobran": sobran}


# ---------- la compuerta ----------
def _borde_en_pausa(palabras: list, x: float) -> float:
    """Si `x` cae dentro de una palabra, se corre al borde de palabra más cercano (el corte nunca parte una palabra)."""
    for k, p in enumerate(palabras):
        if p["s"] < x < p["e"]:
            antes = (palabras[k - 1]["e"] + p["s"]) / 2 if k else max(0.0, p["s"] - .05)
            despues = (p["e"] + palabras[k + 1]["s"]) / 2 if k + 1 < len(palabras) else p["e"] + .05
            return antes if x - p["s"] <= p["e"] - x else despues
    return x


def _restar(a: float, b: float, tomados: list) -> list:
    """[a, b] menos los intervalos ya tomados → los pedazos libres."""
    libres = [(a, b)]
    for x, y in tomados:
        libres = [(u, v) for l0, l1 in libres for u, v in ((l0, min(l1, x)), (max(l0, y), l1)) if v - u >= TRAMO_MIN_S]
    return libres


def revisar(t: dict, propuesta: dict) -> tuple[dict, list]:
    """La compuerta de TODA propuesta (del agrupador o de la persona) → (propuesta limpia, avisos para la pantalla).
    Garantiza: cada archivo y cada palabra dicha queda en un video o en «sobran» con su motivo; ningún tramo está en dos videos; nada
    se sale de su archivo; un archivo solo se parte en una pausa; no hay videos vacíos."""
    arch = {a["id"]: a for a in t["archivos"]}
    palabras = {aid: palabras_de(t, aid) for aid in arch}
    avisos, tomados = [], {aid: [] for aid in arch}

    def tramo(x: dict, donde: str) -> tuple | None:
        aid = str(x.get("archivo", "")) if isinstance(x, dict) else ""
        if aid not in arch:
            avisos.append(f"{donde}: se quitó un archivo que no existe en esta tanda («{aid}»).")
            return None
        dur = float(arch[aid].get("duracion") or 0)
        try:
            a = 0.0 if x.get("desde") is None else float(x["desde"])
            b = dur if x.get("hasta") is None else float(x["hasta"])
        except (TypeError, ValueError):
            a, b = 0.0, dur
        a, b = max(0.0, min(a, dur)), max(0.0, min(b, dur))
        a = 0.0 if a < .15 else _borde_en_pausa(palabras[aid], a)          # casi el inicio o casi el final = el archivo entero
        b = dur if dur - b < .15 else _borde_en_pausa(palabras[aid], b)
        return (aid, a, b) if b - a >= TRAMO_MIN_S else None

    videos = []
    for n, v in enumerate(propuesta.get("videos") or [], 1):
        if not isinstance(v, dict):
            continue
        tramos = []
        for x in v.get("tramos") or []:
            r = tramo(x, f"Video {n}")
            if not r:
                continue
            aid, a, b = r
            libres = _restar(a, b, tomados[aid])
            if libres != [(a, b)]:
                avisos.append(f"Video {n}: parte de «{arch[aid]['nombre']}» ya estaba en otro video; aquí quedó solo lo que no se repite.")
            for u, w in libres:
                tomados[aid].append((u, w))
                tramos.append({"archivo": aid, "desde": round(u, 3), "hasta": round(w, 3)})
        if tramos:
            videos.append({"titulo": str(v.get("titulo") or "").strip()[:80], "idea": str(v.get("idea") or "").strip()[:300], "tramos": tramos})
    sobran = []
    for x in propuesta.get("sobran") or []:
        r = tramo(x, "Sobran")
        if not r:
            continue
        aid, a, b = r
        for u, w in _restar(a, b, tomados[aid]):   # lo que ya está en un video no sobra
            tomados[aid].append((u, w))
            sobran.append({"archivo": aid, "desde": round(u, 3), "hasta": round(w, 3), "motivo": str(x.get("motivo") or "sobra").strip()[:120]})
    # nada se pierde: toda palabra que nadie reclamó, y todo archivo sin palabras que nadie nombró, va a «sobran» y se dice
    for aid, a in arch.items():
        dur = float(a.get("duracion") or 0)
        if not palabras[aid]:
            if not tomados[aid]:
                motivo = a.get("motivo") or SIN_VOZ
                sobran.append({"archivo": aid, "desde": 0.0, "hasta": round(dur, 3), "motivo": motivo if a["estado"] == "error" else SIN_VOZ})
            continue
        sueltas = [p for p in palabras[aid] if not any(u <= (p["s"] + p["e"]) / 2 <= w for u, w in tomados[aid])]
        if not sueltas:
            continue
        grupos, actual = [], [sueltas[0]]
        for p in sueltas[1:]:
            if palabras[aid].index(p) == palabras[aid].index(actual[-1]) + 1:
                actual.append(p)
            else:
                grupos.append(actual)
                actual = [p]
        grupos.append(actual)
        for g in grupos:
            u = 0.0 if g[0] is palabras[aid][0] else _borde_en_pausa(palabras[aid], g[0]["s"] - .01)
            w = dur if g[-1] is palabras[aid][-1] else _borde_en_pausa(palabras[aid], g[-1]["e"] + .01)
            for l0, l1 in _restar(max(0.0, u), min(dur, w), tomados[aid]) or [(max(0.0, g[0]["s"]), min(dur, g[-1]["e"]))]:
                tomados[aid].append((l0, l1))
                sobran.append({"archivo": aid, "desde": round(l0, 3), "hasta": round(l1, 3), "motivo": SIN_UBICAR})
        avisos.append(f"«{a['nombre']}»: {len(sueltas)} palabras no quedaron en ningún video; están en «Sobran» para que decidas.")
    for n, v in enumerate(videos, 1):
        v["id"] = f"v{n}"
        v["titulo"] = v["titulo"] or f"Video {n}"
    # la misma toma dos veces en lo que quedó (regla «última toma siempre»): se avisa, no se decide por la persona
    dicho = [(n, x, " ".join(p["w"] for p in palabras[x["archivo"]] if x["desde"] <= (p["s"] + p["e"]) / 2 <= x["hasta"]))
             for n, v in enumerate(videos, 1) for x in v["tramos"]]
    for i, (n1, x1, t1) in enumerate(dicho):
        for n2, x2, t2 in dicho[i + 1:]:
            if (x1["archivo"], x1["desde"]) != (x2["archivo"], x2["desde"]) and _parecidas(t1, t2):
                avisos.append(f"«{arch[x1['archivo']]['nombre']}» (Video {n1}) y «{arch[x2['archivo']]['nombre']}» (Video {n2}) dicen casi lo "
                              "mismo: si es la misma toma repetida, deja solo la última.")
    return {"origen": propuesta.get("origen", "persona"), "videos": videos, "sobran": sobran}, avisos


def agrupar(tid: str, avance=print) -> dict:
    """Propuesta de la tanda: Opus si se puede; si no (sin IA, sin sesión, sin respuesta), reparto por código. Siempre pasa por `revisar`."""
    t = leer(tid)
    cruda, avisos = None, []
    con_voz = [a for a in t["archivos"] if a["estado"] == "transcrito"]
    if len(con_voz) > 1 and not os.environ.get("ESTUDIO_SIN_IA"):
        try:
            cruda = _con_opus(t, avance)
            if cruda is None:
                avisos.append("El agrupador no respondió claro. " + SIN_IA)
        except ia.LimiteAgotado as e:
            avisos.append(errores.frase(e) + " " + SIN_IA)
        except RuntimeError as e:   # sin sesión, sin Claude o falló la llamada: no se pierde lo transcrito
            errores.registrar("tanda-agrupar", e)
            avisos.append((str(e) if isinstance(e, errores.Aviso) else "El agrupador falló.") + " " + SIN_IA)
    elif len(con_voz) > 1:
        avisos.append(SIN_IA)
    if cruda is None:
        cruda = por_codigo(t)
    t["propuesta"], extra = revisar(t, cruda)
    t["avisos"] = avisos + extra
    t["estado"] = "propuesta"
    avance(f"propuesta: {len(t['propuesta']['videos'])} videos de {len(t['archivos'])} archivos")
    return guardar(t)


def analizar(tid: str, avance=print) -> dict:
    """Lo que corre al subir la tanda: transcribir (en serie) y proponer."""
    transcribir(tid, avance)
    return agrupar(tid, avance)


def proponer(tid: str, propuesta: dict) -> dict:
    """Lo que la persona movió en la pantalla: se guarda lo que deja la compuerta, con sus avisos."""
    t = leer(tid)
    if t.get("estado") not in ("propuesta",):
        raise errores.Aviso("Esta tanda ya se está preparando: no se puede mover ahora.")
    limpia, avisos = revisar(t, {**propuesta, "origen": "persona"})
    if not limpia["videos"]:
        raise errores.Aviso("No quedó ningún video. Deja al menos un archivo en un video.")
    t["propuesta"], t["avisos"] = limpia, avisos
    return guardar(t)


def vista(t: dict) -> dict:
    """La tanda como la pinta la pantalla: a cada tramo (y a cada sobrante) se le suma el nombre de su archivo, si va entero y lo que
    se dice ahí. No se guarda: se calcula al pedirla."""
    import copy
    t = copy.deepcopy(t)
    arch = {a["id"]: a for a in t["archivos"]}
    palabras = {aid: palabras_de(t, aid) for aid in arch}
    p = t.get("propuesta") or {}
    for x in [x for v in p.get("videos", []) for x in v["tramos"]] + p.get("sobran", []):
        a = arch[x["archivo"]]
        dicho = " ".join(w["w"] for w in palabras[x["archivo"]] if x["desde"] <= (w["s"] + w["e"]) / 2 <= x["hasta"])
        x.update(nombre=a["nombre"], entero=x["desde"] < .05 and float(a.get("duracion") or 0) - x["hasta"] < .05,
                 texto=dicho if len(dicho) <= 160 else dicho[:90] + " … " + dicho[-60:])
    return t


# ---------- armar un video aprobado ----------
def _slug(texto: str) -> str:
    sin = "".join(c for c in unicodedata.normalize("NFD", texto.lower()) if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", "-", sin).strip("-")[:40]


def armar(t: dict, v: dict, avance=print) -> tuple[Path, list]:
    """Un video de la propuesta → (su archivo, sus palabras ya en el tiempo del video armado). Un solo archivo entero se usa tal cual
    (sin volver a codificar); lo demás se corta y se une con `unir`."""
    arch = {a["id"]: a for a in t["archivos"]}
    palabras, corrido = [], 0.0
    for x in v["tramos"]:
        for p in palabras_de(t, x["archivo"]):
            if x["desde"] <= (p["s"] + p["e"]) / 2 <= x["hasta"]:
                palabras.append({**p, "s": round(max(0.0, p["s"] - x["desde"]) + corrido, 2), "e": round(max(0.0, p["e"] - x["desde"]) + corrido, 2)})
        corrido += x["hasta"] - x["desde"]
    enteros = all(x["desde"] < .05 and float(arch[x["archivo"]].get("duracion") or 0) - x["hasta"] < .05 for x in v["tramos"])
    if len(v["tramos"]) == 1 and enteros:
        return Path(arch[v["tramos"][0]["archivo"]]["video"]), palabras
    destino = config.PROYECTOS / "_subidas" / f"{t['id']}-{v['id']}-{_slug(v['titulo']) or 'video'}.mp4"
    unir.unir([arch[x["archivo"]]["video"] for x in v["tramos"]], destino, avance,
              tramos=[None if enteros else (x["desde"], x["hasta"]) for x in v["tramos"]])
    return destino, palabras


def preparar_videos(tid: str, preparar, avance=print) -> dict:
    """Aprobada la propuesta: cada video se arma y entra al flujo de siempre con `preparar(video, nombre, avance)` (el del servidor),
    UNO TRAS OTRO. El que falle queda anotado con su frase y se sigue con el siguiente. Lo ya preparado no se repite (se puede retomar)."""
    t = leer(tid)
    if not (t.get("propuesta") or {}).get("videos"):
        raise errores.Aviso("Esta tanda todavía no tiene una propuesta de videos.")
    t["estado"] = "preparando"
    guardar(t)
    total = len(t["propuesta"]["videos"])
    for n, v in enumerate(t["propuesta"]["videos"], 1):
        if v.get("proyecto") and v.get("estado") == "listo":
            continue
        avance(f"video {n} de {total}: «{v['titulo']}»")
        try:
            video, palabras = armar(t, v, avance)
            nombre, _ = ingesta.proyecto_para(video, _slug(v["titulo"]) or f"{tid}-{v['id']}")
            destino = config.PROYECTOS / nombre / "palabras.json"
            if palabras and not destino.exists():   # ya están transcritas: se ponen en el tiempo del video armado y no se repite Whisper
                destino.write_text(json.dumps(palabras, ensure_ascii=False), encoding="utf-8")
            v.update(proyecto=nombre, estado="preparando")
            guardar(t)
            preparar(str(video), nombre, lambda m: avance(f"video {n} de {total}: {m}"))
            v["estado"] = "listo"
        except Exception as e:  # noqa: BLE001 — un video que falla no tumba a los demás; queda dicho en su tarjeta
            from . import trabajo
            if isinstance(e, trabajo.Detenido):
                t["estado"] = "propuesta"
                guardar(t)
                raise
            v.update(estado="error", error=errores.amable(f"tanda {tid} {v['id']}", e))
        guardar(t)
    t["estado"] = "lista"
    return guardar(t)
