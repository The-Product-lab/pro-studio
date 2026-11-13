"""Machote: etapa fija del editor (Pablo, 07-nov). El crudo ya colorizado y con SOLO los cortes perfectos, en un MP4 liviano.
Sin textos, apoyos, SFX ni subtítulos: con esa versión se pule cada estilo, y los estilos parten de sus cortes.

  decidir()  → `machote.json` (cortes + color + qué se quitó). Casi todo en código (0 IA): última toma de cada frase repetida
               (repeticiones.py), claqueta y apuntador fuera (voz.py), cada borde en una pausa real y silencios recortados
               (montaje.reparar), inicio y final limpios. Una llamada corta de Opus, SOLO de cortes (sin escenas ni elementos),
               quita lo que el código no ve: charla con el equipo, tomas abandonadas, y lo que pase del tope de 110 s.
  render()   → `machote.mp4`: el color aprobado del proyecto (preferencias.json) y solo esos cortes, con su audio, 720×1280.
  imponer()  → los cortes del storyboard son EXACTAMENTE los del machote (aprobados); el director no los toca.
"""
import hashlib
import json
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path

import numpy as np

from . import color, config, ia, montaje, repeticiones, voz

VERSION = 1
LIMITE_S = 110                  # tope del reel: un guion más largo no se puede aprobar ni dirigir
MENSAJE_GUION_NUEVO = "El sistema ajustó el guion"   # la app lo reconoce (guion_nuevo) para volver a mostrar el texto antes de aprobar
TOLERANCIA_S = 2                # holgura al medir el reel ya montado contra LIMITE_S: dura 2 s más que el machote porque el hook y el cierre
                                # (escena final) se montan encima; 2 s es el redondeo observado en los 20 proyectos reales, no un criterio creativo

OBJETIVO_S = 105                # si se pasa del tope, la IA recorta hasta aquí
FRASE_MAX_S = 6.0               # una «frase» más larga (Whisper sin puntos) se parte en su pausa más larga: la IA quita frases enteras
MAX_QUITA_IA = .9               # si la IA pide quitar más de esta fracción del TIEMPO hablado que queda, la respuesta se descarta
                                # (por tiempo, no por frases: Cine C8867 tiene 81 frases cortas y quitar 75 era lo correcto)
AIRE_INICIO = montaje.SILENCIO_META_S / 2   # s de aire antes de la primera palabra (la misma regla del borde que usa montaje:
AIRE_FINAL = montaje.SILENCIO_META_S / 2    # ningún silencio pasa de SILENCIO_MAX_S, y en el borde no hay «otro lado»)
ANCHO, CRF = 720, 26            # liviano: 720×1280 H.264 CRF 26, AAC 128k
ARCHIVO, VIDEO = "machote.json", "machote.mp4"
# órdenes y charla de grabación que el arquitecto SÍ puede quitar aunque no se repitan (normalizadas, sin tildes ni signos)
ORDENES_Y_CHARLA = set(voz.CLAQUETA) | {"aver", "ver", "ya", "eh", "em", "mm", "bueno", "ok", "okay", "vale", "sale", "listo",
                                        "siguiente", "perdon", "espera", "corta", "denuevo"}   # sin palabras de guion («de», «que»…)
CANDADO_MAX_PALABRAS = 3       # el candado del arquitecto mira pedazos cortos: ahí es donde borraba guion («una sola persona»)
VUELTAS_REVISION = 2            # vueltas del bucle revisión final → arquitecto → corte → revisión


def estabilizar(carpeta: Path, avance=lambda m: None) -> str | None:
    """Pasa `reparar` por el machote ANTES de gastar nada. Mismas palabras: el machote se actualiza solo (con registro) y la aprobación sigue.
    Si la reparación cambia palabras, los cortes reparados SE APLICAN, se borra la aprobación y se devuelve el mensaje con lo que el sistema
    quitó/agregó: la persona aprueba el guion nuevo UNA vez (al aprobarlo ya es estable: no hay ciclo). None = nada que decir."""
    r = reparar_machote(carpeta, avance)
    if r["estado"] in ("ajustado", "guion_nuevo") and (Path(carpeta) / "storyboard.json").exists():
        imponer(carpeta)
    return r["mensaje"] if r["estado"] == "guion_nuevo" else None


def _firma_guion(carpeta: Path, mj: dict, transcripcion: str | None = None) -> str:
    """Huella de las PALABRAS que quedan (no de los bordes: moverlos dentro de un silencio no cambia el guion)."""
    quedan = montaje.palabras_que_quedan(montaje.contexto(carpeta), mj["cortes"])
    return hashlib.sha1(json.dumps([transcripcion or montaje.firma_palabras(carpeta), quedan]).encode()).hexdigest()[:12]


def _acepta(carpeta: Path, mj: dict) -> bool:
    """¿`aceptado` es de este guion? También con la huella vieja de la transcripción (bytes del archivo, hasta el 12-nov)."""
    vieja = hashlib.sha1((Path(carpeta) / "palabras.json").read_bytes()).hexdigest()[:12]
    return bool(mj.get("aceptado")) and mj["aceptado"] in (_firma_guion(Path(carpeta), mj), _firma_guion(Path(carpeta), mj, vieja))


def aceptar_detalles(carpeta: Path) -> None:
    """La persona vio el guion con sus detalles de montaje señalados y lo aprueba así (Pablo, 11-nov: «ya con ese paso humano es
    suficiente»). Vale para ESTE guion: si cambian las palabras que quedan, deja de valer. Dos frases dichas de corrido no tienen
    silencio donde cortar; sin esto, quitar una dejaba el guion sin poder aprobarse nunca (IMG_4955)."""
    mj = cargar(carpeta)
    if mj:
        _guardar(Path(carpeta) / ARCHIVO, {**mj, "aceptado": _firma_guion(Path(carpeta), mj)})


def tolera_montaje(carpeta: Path) -> bool:
    """¿Los detalles medibles del montaje de este guion ya no bloquean? Sí si pasó la revisión final (`apto`) o si la persona lo
    aprobó viéndolos (`aceptar_detalles`). Lo usan `impedimento` y la compuerta del render: una sola respuesta."""
    mj = cargar(carpeta)
    return bool(mj) and (apto(carpeta) or _acepta(Path(carpeta), mj))


def impedimento(carpeta: Path) -> str | None:
    """Por qué ESTE guion no se puede aprobar ni dirigir (se sabe ANTES de gastar director e imágenes), o None. Tres causas: pasa del
    tope de duración, la reparación técnica cambiaría palabras (si solo mueve bordes dentro de un silencio, el machote se actualiza
    solo), o los cortes dejan un error de montaje que la compuerta del render rechazaría (la misma `montaje.errores`). Esos errores
    se toleran si el machote pasó la revisión final o la persona lo aprobó viéndolos (`tolera_montaje`), pero NO se salta ni el
    tope ni la estabilidad."""
    largo = exceso(carpeta)
    if largo or not cargar(carpeta):
        return largo
    if (cambian := estabilizar(carpeta)):
        return cambian
    if tolera_montaje(carpeta):
        return None
    malos = montaje.errores({"cortes": cargar(carpeta)["cortes"]}, Path(carpeta))
    if malos:
        return "Este guion deja un problema de montaje que no se arregla solo: " + "; ".join(m.removeprefix("montaje: ") for m in malos[:3]) + "."
    return None


def exceso(carpeta: Path) -> str | None:
    """Mensaje para la persona si el guion del machote pasa del tope (no se puede aprobar ni dirigir); None si cabe."""
    mj = cargar(carpeta)
    if mj and mj.get("duracion_s", 0) > LIMITE_S:
        return f"El guion dura {mj['duracion_s']:.1f} s y el máximo es {LIMITE_S} s: quita frases y vuelve a aprobarlo."
    return None


def cargar(carpeta: Path) -> dict | None:
    f = Path(carpeta) / ARCHIVO
    return json.loads(f.read_text()) if f.exists() else None


def color_de(carpeta: Path) -> dict | None:
    """El color aprobado del proyecto (el mismo bloque que usa el motor)."""
    f = Path(carpeta) / "preferencias.json"
    return (json.loads(f.read_text()).get("estilo", {}).get("color") or None) if f.exists() else None


def firma(carpeta: Path) -> str:
    """Qué entra a la decisión de cortes: la transcripción y la versión de las reglas."""
    h = hashlib.sha1(f"v{VERSION}".encode())
    h.update((Path(carpeta) / "palabras.json").read_bytes())
    return h.hexdigest()[:12]


def _firma_render(mj: dict, ancho: int, crf: int) -> str:
    return hashlib.sha1(json.dumps([mj["cortes"], mj.get("color"), ancho, crf], sort_keys=True).encode()).hexdigest()[:12]


# ---------------------------------------------------------------------------------------------------------------------
# Decidir los cortes
# ---------------------------------------------------------------------------------------------------------------------

def _cortes_repetidas(libres: list) -> list:
    """Todas las versiones anteriores de una idea repetida; queda la ÚLTIMA (regla de Pablo)."""
    return [[v["t0"], v["t1"]] for g in repeticiones.grupos(libres) for v in g[:-1]]


def _frases_para_ia(c, repetidas: list, cortes: list) -> list:
    """Todas las frases que no son una toma repetida, con `cortada` = el código ya la quitó (casi siempre por sonar baja: apuntador
    o claqueta). Entran también las de voz de fuera que siguen en el video (charla pegada al talento que reparar no puede borrar
    sola). Van sin marca de «voz baja»: el detector de apuntador también marca al talento hablando suave y con esa marca la IA
    borraba guion (Julián 3D C8869: los tres pasos); por eso también ve lo que el código quitó y puede pedir devolverlo."""
    en = lambda p, spans: any(a - 1e-3 <= (p["s"] + p["e"]) / 2 <= b + 1e-3 for a, b in spans)  # noqa: E731
    quedan = montaje.tramos({"cortes": cortes}, c.fin)
    ps = [p for p in c.palabras if not en(p, repetidas)]
    out = []
    for f in (ps[a:b] for i0, i1 in repeticiones.frases(ps) for a, b in _partir(ps, i0, i1)):
        out.append({"id": len(out), "t0": f[0]["s"], "t1": f[-1]["e"], "texto": " ".join(p["w"] for p in f),
                    "cortada": 2 * sum(1 for p in f if not en(p, quedan)) > len(f)})
    return out


def _partir(ps: list, i0: int, i1: int) -> list:
    """[(a, b)] de una frase partida en su pausa más larga hasta que cada pedazo dure ≤ FRASE_MAX_S (Julián 3D C8869: Whisper sin
    puntos dejó tres versiones del llamado a la acción en una sola «frase» de 21 s y la IA no podía quitar las dos primeras)."""
    if i1 - i0 < 2 or ps[i1 - 1]["e"] - ps[i0]["s"] <= FRASE_MAX_S:
        return [(i0, i1)]
    k = max(range(i0 + 1, i1), key=lambda j: ps[j]["s"] - ps[j - 1]["e"])
    return _partir(ps, i0, k) + _partir(ps, k, i1)


def _prompt_ia(frases: list, dur: float) -> str:
    linea = lambda f: f"{f['id']} · {f['t0']:.1f}-{f['t1']:.1f} s · {f['texto']}"  # noqa: E731
    en_video = "\n".join(linea(f) for f in frases if not f.get("cortada"))
    fuera = "\n".join(linea(f) for f in frases if f.get("cortada"))
    tope = (f"\nEl video dura {dur:.0f} s y el máximo es {LIMITE_S} s: además de lo anterior, quita las frases MENOS importantes "
            f"(enteras, nunca a media idea) hasta que queden como mucho {OBJETIVO_S} s, conservando la historia más fuerte.") if dur > LIMITE_S else ""
    return ("Eres el montajista de un reel. Abajo está la transcripción de lo que quedó después de quitar, en código, las tomas "
            "repetidas, la claqueta y la voz del apuntador. Una línea por frase: id · inicio-fin · texto.\n\n"
            "## EN EL VIDEO\n" + en_video + "\n\n"
            "Pon en \"quitar\" las frases de EN EL VIDEO que NO deben estar: charla con el equipo o con el director, conteos, el "
            "apuntador dictando una línea que el talento dice después, comentarios fuera de guion, tomas abandonadas o frases truncadas "
            "que no cierran, y versiones de una misma idea que sobraron (queda la ÚLTIMA versión completa). No reordenes ni reescribas; "
            "con la duda, déjala." + tope +
            (("\n\n## QUITADAS POR EL CÓDIGO (sonaban más bajo que el talento)\n" + fuera + "\n\n"
              "El detector a veces confunde al talento hablando suave con el apuntador. Pon en \"restaurar\" solo las de esta lista "
              "que son parte del mensaje del talento y que NO se dicen completas en EN EL VIDEO (sin ellas el guion queda cojo). "
              "Nunca un dictado, un conteo ni charla.") if fuera else "") +
            "\n\nResponde SOLO un JSON {\"quitar\": [{\"id\": N, \"motivo\": \"…\"}], \"restaurar\": [{\"id\": N, \"motivo\": \"…\"}]}.")


def _preguntar_ia(carpeta: Path, frases: list, dur: float) -> tuple[list, list, list]:
    """([quitar], [restaurar], [avisos]), cada pedido {id, motivo}. La IA solo señala frases enteras; el código pone los bordes. Si
    no responde un JSON, un reintento (Cine C8867, 07-nov: la primera respuesta no traía JSON y quedaba la charla)."""
    resp = None
    for intento in range(2):
        prompt = _prompt_ia(frases, dur) + ("\n\nIMPORTANTE: tu respuesta anterior no era JSON. Responde SOLO el objeto JSON." if intento else "")
        out = ia.llamar(prompt, "opus", carpeta, herramientas="Read", tope_usd=.75, paso="machote-cortes")
        try:
            resp = ia.json_de(out.get("result", ""))
            if isinstance(resp, dict):
                break
        except ValueError:
            pass
        resp = None
    if resp is None:
        return [], [], [{"t": 0, "tipo": "ia", "motivo": "la IA no respondió un JSON (2 intentos): se dejaron los cortes de código"}]

    def ids(clave, cortada):
        out = {}
        for x in resp.get(clave) or []:
            if isinstance(x, dict) and isinstance(x.get("id"), int) and 0 <= x["id"] < len(frases) and bool(frases[x["id"]].get("cortada")) == cortada:
                out[x["id"]] = str(x.get("motivo", ""))[:120]
        return [{"id": k, "motivo": m} for k, m in sorted(out.items())]
    quitar, restaurar = ids("quitar", False), ids("restaurar", True)
    hablado = sum(f["t1"] - f["t0"] for f in frases if not f.get("cortada"))
    pide = sum(frases[x["id"]]["t1"] - frases[x["id"]]["t0"] for x in quitar)
    if pide > MAX_QUITA_IA * hablado:
        return [], [], [{"t": 0, "tipo": "ia", "motivo": f"la IA pidió quitar {pide:.0f} s de {hablado:.0f} s hablados: respuesta descartada"}]
    return quitar, restaurar, []


def es_resto(palabras: list, despues: list, frase_entera: bool = True, sigue_la_frase: bool = False) -> bool:
    """El arquitecto NO borra guion (C8871 07-nov: quitó «de forma automática» y «una sola persona»). Quitar vale solo si es
    (1) una versión que se vuelve a decir después (queda la última), (2) puras órdenes o charla de grabación, o (3) un arranque
    cortado cuyas palabras reaparecen enseguida (mismo comienzo de palabra: «trabajen» → «trabaja»). Palabras ya normalizadas."""
    ws = [w for w in palabras if w]
    if not ws or all(w in ORDENES_Y_CHARLA for w in ws):
        return True
    if frase_entera and not sigue_la_frase:   # una frase entera suelta (charla: «tranqui, tranqui», «¿así? sí») se puede quitar;
        return True                           # si lo que viene después la CONTINÚA («una sola persona | con Claude puede…»), no
    if frase_entera and len(ws) > CANDADO_MAX_PALABRAS:   # una frase completa de charla («perdón, pensé que estaba María acá»)
        return True                                       # sí se puede quitar; palabras DENTRO de una frase, nunca sin prueba
    if any(despues[i:i + len(ws)] == ws for i in range(len(despues) - len(ws) + 1)):
        return True
    cerca = {w[:5] for w in despues[:40]}
    if all(w in ORDENES_Y_CHARLA or w[:5] in cerca for w in ws):
        return True
    # arranque abandonado: la frase se vuelve a empezar enseguida con la misma palabra («antes grababa una…» → «Antes me
    # demoraba…», C8872 07-nov). Solo para pedazos cortos de frase entera, nunca para palabras dentro de una frase
    return frase_entera and ws[0] not in ORDENES_Y_CHARLA and ws[0] in despues[:15]


def _leer_guion_final(carpeta: Path, c, cortes: list, pistas: list = ()) -> tuple[list, list]:
    """Pablo (07-nov): «el arquitecto ve la transcripción y ve "y todo… y todo" dos veces y lo deja pasar». Última lectura del
    GUION QUE QUEDÓ, tramo por tramo (lo que de verdad va a sonar, en orden), por Opus: marca los tramos que sobran (resto de otra
    toma, orden de grabación, palabra suelta, la versión vieja de algo que se repite enseguida, el CTA dicho dos veces). Solo
    tramos enteros: el código pone los bordes y la revisión final mide el resultado. → ([(t0, t1, texto, motivo)], [avisos])."""
    quedan = montaje.tramos({"cortes": cortes}, c.fin)
    filas, t = [], 0.0
    for k, (a, b) in enumerate(quedan):
        ws = [p for p in c.palabras if not p.get("fuera") and min(b, p["e"]) - max(a, p["s"]) > .5 * max(.01, p["e"] - p["s"])]
        filas.append((k, a, b, ws))
        t += b - a
    if len(filas) < 2:
        return [], []
    prompt = ("Eres el montajista final de un video hablado a cámara. Este es el video YA CORTADO, en orden, un tramo por línea "
              "(id · segundo en el video · texto que se oye):\n\n" +
              "\n".join(f"{k} · {sum(bb - aa for aa, bb in quedan[:k]):.1f}s · " + " ".join(f"{i}:{p['w']}" for i, p in enumerate(ws))
                        for k, a, b, ws in filas) +
              "\n\n(cada palabra lleva su número dentro del tramo: «3:hola»)" +
              "\n\nLéelo como lo oiría el público. Marca en \"quitar\" los tramos que SOBRAN: restos de otra toma o palabras sueltas "
              "que no forman parte de la frase («ver, ya», «trabajen.», «como… como si»), órdenes o charla de grabación («a ver», «ya, "
              "listo», «acción», «siguiente»), la versión vieja de algo que se dice dos veces seguidas (queda la ÚLTIMA completa: "
              "«todo directamente desde tu… | todo directamente desde tu computador»), y el llamado a la acción repetido (queda uno, "
              "el último y completo). Si lo que sobra es solo PARTE de un tramo («aprender a editar como, como si quieres aprender…»: "
              "sobra el primer arranque), indica las palabras con \"palabras\": [desde, hasta] (números del tramo, inclusive). NO quites "
              "guion: con la duda, déjalo. Responde SOLO el JSON "
              "{\"quitar\": [{\"id\": N, \"palabras\": [i, j] (opcional), \"motivo\": \"…\"}]}.")
    if pistas:                              # lo que la revisión final midió en el video terminado vuelve al arquitecto
        inicio = [sum(bb - aa for aa, bb in quedan[:k]) for k in range(len(quedan))]
        tramo = lambda t: max((k for k, x in enumerate(inicio) if x <= t + .05), default=0)  # noqa: E731
        prompt += ("\n\nLA REVISIÓN FINAL DEL VIDEO TERMINADO ENCONTRÓ ESTO (corrígelo quitando tramos):\n" +
                   "\n".join(f"- {p['tipo'].replace('_', ' ')} en el segundo {p['segundo']:.1f} (tramo {tramo(p['segundo'])}): {p['detalle']}"
                              for p in pistas))
    out = ia.llamar(prompt, "opus", carpeta, herramientas="Read", tope_usd=.5, paso="machote-lectura")
    try:
        resp = ia.json_de(out.get("result", ""))
    except ValueError:
        resp = None
    if not isinstance(resp, dict):
        return [], [{"t": 0, "tipo": "ia", "motivo": "la lectura final del guion no respondió JSON: queda sin ella (la revisión final igual mide)"}]
    sobran, avisos = [], []
    despues = lambda k: [voz._norma(p["w"]) for _, _, _, ws2 in filas[k + 1:] for p in ws2]  # noqa: E731

    for x in resp.get("quitar") or []:
        if isinstance(x, dict) and isinstance(x.get("id"), int) and 0 <= x["id"] < len(filas):
            k, a, b, ws = filas[x["id"]]
            rango = x.get("palabras")
            if isinstance(rango, list) and len(rango) == 2 and all(isinstance(v, int) for v in rango) and ws \
                    and 0 <= rango[0] <= rango[1] < len(ws):
                sel = ws[rango[0]:rango[1] + 1]
                a2 = a if rango[0] == 0 else max(a, sel[0]["s"])        # el borde exacto lo pone reparar en el silencio
                b2 = b if rango[1] == len(ws) - 1 else min(b, sel[-1]["e"])
            else:
                sel, a2, b2 = ws, a, b
            texto = " ".join(p["w"] for p in sel)
            sig = next((ws2[0]["w"] for _, _, _, ws2 in filas[k + 1:] if ws2), "")
            sigue = bool(sig) and sig[:1].islower() and not (ws and ws[-1]["w"][-1:] in ".?!")
            if es_resto([voz._norma(p["w"]) for p in sel], despues(k), frase_entera=sel is ws, sigue_la_frase=sigue):
                sobran.append((a2, b2, texto, str(x.get("motivo", ""))[:120]))
            else:
                avisos.append({"t": round(a2, 2), "tipo": "ia", "motivo": f"el arquitecto quería quitar «{texto[:60]}», que es guion único: "
                               f"se dejó (revísalo en el guion)"})
    hablado = sum(b - a for _, a, b, _ in filas)
    if sum(b - a for a, b, _, _ in sobran) > .5 * hablado:      # quitar más de la mitad del video ya cortado no es pulir
        return [], [{"t": 0, "tipo": "ia", "motivo": "la lectura final pidió quitar más de la mitad del video: se descarta"}]
    return sobran, avisos


MOTIVO_IA_DEJO = "talento: la IA lo dejó"


def _la_ia_lo_dejo(c, frases: list, quitar: set, restaurar: set) -> int:
    """Las palabras que el detector marcó como APUNTADOR dentro de una frase que la IA leyó y dejó (o pidió restaurar) pasan a ser
    del talento para el resto de la decisión; si no, `reparar` las vuelve a borrar (Julián 3D C8869: los tres pasos del guion;
    Prestiggio C8873: «15 videos a la semana…»). La claqueta no se toca, y lo que la IA quitó o no restauró sigue fuera.
    Cambia el contexto en caché de montaje, que es el que lee `reparar`; al terminar, `decidir` lo suelta y deja esas palabras
    escritas en `guion-persona.json` (las decisiones del guion, que montaje sí lee)."""
    n = 0
    for f in frases:
        if f["id"] in quitar or (f.get("cortada") and f["id"] not in restaurar):
            continue
        for p in c.palabras:
            if p.get("motivo") == "apuntador" and f["t0"] - 1e-3 <= (p["s"] + p["e"]) / 2 <= f["t1"] + 1e-3:
                p.update(fuera=False, motivo=MOTIVO_IA_DEJO)
                n += 1
    return n


def _limite_de_voz(c, t: float, paso: int) -> float:
    """Donde de verdad empieza (paso=-1) o termina (paso=+1) la voz de una palabra: Whisper marca la palabra hasta 0,25 s tarde o
    corta, así que se sigue la voz sonando alrededor de su marca (máximo 0,5 s)."""
    n, i = len(c.voz), int(t / voz.HOP)
    cerca = [j for j in range(i - 10, i + 11) if 0 <= j < n and c.voz[j]]
    if not cerca:
        return t
    i = min(cerca) if paso < 0 else max(cerca)
    for _ in range(int(.5 / voz.HOP)):
        if not 0 <= i + paso < n or not c.voz[i + paso]:
            break
        i += paso
    return i * voz.HOP


def _ajustar_bordes(c, cortes: list, ia_spans: list = ()) -> list:
    """El video empieza AIRE_INICIO antes de que suene la primera palabra y termina AIRE_FINAL después de la última: lo de afuera
    se quita aunque suene algo (un pedazo de claqueta o de otra toma que el corte dejó pegado no es parte del video). Las palabras
    de una frase que la IA mandó quitar no cuentan como «primera palabra» aunque reparar no haya podido cortarlas (Cine C8867: un
    «¡Hasta la próxima!» que Whisper inventó sobre un «Ya» quedaba al arranque)."""
    quedan = montaje.tramos({"cortes": cortes}, c.fin)
    en = lambda p, spans: any(a - 1e-3 <= (p["s"] + p["e"]) / 2 <= b + 1e-3 for a, b in spans)  # noqa: E731
    dentro = [p for p in c.palabras if not p.get("fuera") and en(p, quedan) and not en(p, ia_spans)]
    if not quedan or not dentro:
        return cortes
    nuevos = [list(x) for x in cortes]
    ini = _limite_de_voz(c, dentro[0]["s"], -1) - AIRE_INICIO
    if ini > quedan[0][0] + .02 and not voz.hay_voz(c.voz, ini):
        nuevos.append([0.0, ini])
    fin = _limite_de_voz(c, dentro[-1]["e"], +1) + AIRE_FINAL
    if fin < quedan[-1][1] - .02 and not voz.hay_voz(c.voz, fin):
        nuevos.append([fin, c.fin])
    return [[round(a, 3), round(b, 3)] for a, b in montaje._fusionar(nuevos)]


def _sin_palabras(c, cortes: list) -> list:
    """Tramos del medio que quedaron sin NINGUNA palabra (solo aire o un ruido entre dos cortes): se cortan enteros. Reparar no
    los cierra cuando partirlos dejaría un pedacito suelto, y en el final sonaban como un silencio largo (Swiss C8872: 2,1 s).
    Un tramo con voz baja no entra aquí: el detector de apuntador también marca al talento hablando suave; eso lo decide la IA."""
    quedan = montaje.tramos({"cortes": cortes}, c.fin)
    return [[a, b] for a, b in quedan[1:-1] if not any(a - 1e-3 <= (p["s"] + p["e"]) / 2 <= b + 1e-3 for p in c.palabras)]


def _cerrar(carpeta: Path, c, cortes: list, avisos: list, quitados: list = ()) -> tuple[list, list]:
    """Lo que falta después de `reparar`: los tramos que quedaron sin ninguna palabra se cortan y el video arranca y termina en la
    voz. → (cortes, avisos de la última pasada de reparar). Lo usan `decidir` y `editar_guion`: un solo camino para cerrar cortes."""
    vacios = _sin_palabras(c, cortes)
    if vacios:                          # reparar cierra la unión nueva (aire de los dos lados ≤ SILENCIO_MAX_S)
        avisos = []
        cortes = montaje.reparar({"cortes": cortes + vacios}, carpeta, avisos)["cortes"]
        resto = _sin_palabras(c, cortes)    # si reparar deshizo alguno (un corte de pura pausa sin dónde ponerlo), se une directo:
        if resto:                           # sus dos bordes son bordes de cortes que reparar ya puso en silencio
            cortes = [[round(a, 3), round(b, 3)] for a, b in montaje._fusionar([list(x) for x in cortes] + resto)]
    return _ajustar_bordes(c, cortes, quitados), avisos


def _cuanto_quito(c, cortes: list, repetidas: list, ia_spans: list) -> dict:
    """Segundos quitados por motivo (cada instante se cuenta una vez: claqueta > apuntador > repetidas > IA > pausas)."""
    n = int(c.fin / voz.HOP) + 1

    def marca(spans):
        m = np.zeros(n, bool)
        for a, b in spans:
            m[int(a / voz.HOP):int(b / voz.HOP)] = True
        return m
    libre = marca(cortes)
    capas = [("claqueta", [(p["s"], p["e"]) for p in c.palabras if p.get("motivo") == "claqueta"]),
             ("apuntador", [(p["s"], p["e"]) for p in c.palabras if p.get("motivo") == "apuntador"]),
             ("tomas_repetidas", repetidas), ("ia_fuera_de_guion", ia_spans)]
    out = {}
    for nombre, spans in capas:
        sel = libre & marca(spans)
        out[nombre] = round(float(sel.sum()) * voz.HOP, 1)
        libre &= ~sel
    out["pausas_y_aire"] = round(float(libre.sum()) * voz.HOP, 1)
    return out


# Lo grave que el código solo no siempre resuelve (Pablo 08-nov: «cuando pase eso, metés IA full y ya»): una orden de grabación pegada
# sin pausa a una toma mala no tiene un borde seguro por código. Con IA, esos tramos vuelven a Opus señalados; sin IA, quedan en
# `necesita_ia` (nunca pasan callados).
GRAVES = ("versiones repetidas", "corta con voz sonando", "pedacito suelto")
IA_GRAVES_RONDAS = 2


def _pistas_graves(c, cortes: list, errores: list) -> list:
    """Errores graves del montaje → pistas para `_leer_guion_final` (segundo en el video CORTADO, como las de la revisión final)."""
    import re
    quedan = montaje.tramos({"cortes": cortes}, c.fin)
    out = []
    for e in errores:
        if not any(g in e for g in GRAVES):
            continue
        m = re.search(r"(\d+\.\d+)\s*[–-]\s*(\d+\.\d+)", e)
        t_src = float(m.group(1)) if m else 0.0
        seg = sum(max(0.0, min(b, t_src) - a) for a, b in quedan)
        out.append({"tipo": "montaje", "segundo": seg,
                    "detalle": e.replace("montaje: ", "") + ". El código no encuentra un borde seguro: decide qué palabras de ese tramo sobran"})
    return out


def decidir(carpeta: Path, con_ia: bool = True, avance=print) -> dict:
    """Decide los cortes del machote y los guarda en `machote.json`. Idempotente: mismas palabras → mismos cortes (la IA, una vez)."""
    carpeta = Path(carpeta)
    if not montaje._hay_datos(carpeta):
        raise FileNotFoundError(f"{carpeta.name}: falta fuente.json o palabras.json (prepara el proyecto primero)")
    n_costos = _lineas(carpeta / "costos.jsonl")
    desaprobar(carpeta)   # cortes nuevos = guion nuevo: la aprobación anterior ya no vale
    (carpeta / montaje.PERSONA).unlink(missing_ok=True)   # y lo que la persona marcó era sobre el guion anterior
    c = montaje.contexto(carpeta)
    libres = [p for p in c.palabras if not p.get("fuera")]
    avisos: list = []          # lo que reparar() no pudo dejar perfecto, en su última pasada
    avisos_ia: list = []
    repetidas = _cortes_repetidas(libres)
    avance(f"machote: {len(repetidas)} tomas repetidas, {sum(1 for p in c.palabras if p.get('fuera'))} palabras fuera de cámara")
    cortes = montaje.reparar({"cortes": repetidas}, carpeta, avisos)["cortes"]
    ia_quito: list = []
    ia_restauro: list = []
    ia_spans: list = []
    try:
        if con_ia:
            frases = _frases_para_ia(c, repetidas, cortes)
            dur = sum(b - a for a, b in montaje.tramos({"cortes": cortes}, c.fin))
            if frases:
                avance(f"machote: Opus revisa {len(frases)} frases (solo cortes)…")
                quitar, restaurar, av = _preguntar_ia(carpeta, frases, dur)
                avisos_ia += av
                ok = []
                for x in quitar:
                    f = frases[x["id"]]
                    despues_f = [voz._norma(p["w"]) for p in c.palabras if not p.get("fuera") and p["s"] > f["t1"]]
                    sig = next((p["w"] for p in c.palabras if not p.get("fuera") and p["s"] > f["t1"]), "")
                    sigue = bool(sig) and sig[:1].islower() and f["texto"].rstrip()[-1:] not in ".?!"
                    if not es_resto([voz._norma(w) for w in f["texto"].split()], despues_f, sigue_la_frase=sigue):
                        avisos_ia.append({"t": round(f["t0"], 2), "tipo": "ia", "motivo": f"el arquitecto quería quitar «{f['texto'][:60]}», "
                                          "que es guion único: se dejó (revísalo en el guion)"})
                        continue
                    ok.append(x)
                    ia_spans.append([f["t0"], f["t1"]])
                    ia_quito.append({"t0": f["t0"], "t1": f["t1"], "texto": f["texto"][:90], "motivo": x["motivo"]})
                quitar = ok
                ia_restauro = [{"t0": frases[x["id"]]["t0"], "t1": frases[x["id"]]["t1"], "texto": frases[x["id"]]["texto"][:90],
                                "motivo": x["motivo"]} for x in restaurar]
                devueltas = _la_ia_lo_dejo(c, frases, {x["id"] for x in quitar}, {x["id"] for x in restaurar}) if (quitar or restaurar) else 0
                if devueltas:
                    avisos_ia.append({"t": 0, "tipo": "ia", "motivo": f"{devueltas} palabras marcadas como apuntador quedan como talento: la IA las leyó y las dejó"})
                if quitar or devueltas:   # de nuevo desde las tomas repetidas: lo que el código quitó por «apuntador» y la IA devolvió vuelve
                    avisos = []
                    cortes = montaje.reparar({"cortes": repetidas + ia_spans}, carpeta, avisos)["cortes"]
        cortes, avisos = _cerrar(carpeta, c, cortes, avisos, ia_spans)
        if con_ia:                          # el montajista LEE el guion que quedó, tramo por tramo, y marca lo que sobra
            sobran, av = _leer_guion_final(carpeta, c, cortes)
            avisos_ia += av
            if sobran:
                cortes, av2 = _aplicar_sin_mochar(carpeta, c, cortes, sobran)
                avisos_ia += av2
                ia_quito += [{"t0": a, "t1": b, "texto": t[:90], "motivo": m} for a, b, t, m in sobran]
                ia_spans += [[a, b] for a, b, _, _ in sobran]
                cortes = _ajustar_bordes(c, cortes, ia_spans)
        if con_ia:                          # lo que el código no pudo dejar limpio lo decide la IA, con el problema señalado
            for _ in range(IA_GRAVES_RONDAS):
                pistas = _pistas_graves(c, cortes, montaje.errores({"cortes": cortes}, carpeta))
                if not pistas:
                    break
                avance(f"machote: {len(pistas)} problemas que el código no resuelve solo: decide Opus")
                sobran, av = _leer_guion_final(carpeta, c, cortes, pistas)
                avisos_ia += av
                if not sobran:
                    break
                cortes, av2 = _aplicar_sin_mochar(carpeta, c, cortes, sobran)
                avisos_ia += av2
                ia_quito += [{"t0": a, "t1": b, "texto": t[:90], "motivo": m} for a, b, t, m in sobran]
                ia_spans += [[a, b] for a, b, _, _ in sobran]
                cortes = _ajustar_bordes(c, cortes, ia_spans)
        duracion = sum(b - a for a, b in montaje.tramos({"cortes": cortes}, c.fin))
        ia_dejo = [k for k, p in enumerate(c.palabras) if p.get("motivo") == MOTIVO_IA_DEJO]
    finally:
        montaje._CACHE.clear()         # suelta lo que cambió _la_ia_lo_dejo
    if ia_dejo:   # lo que la IA leyó y dejó queda escrito como decisión del guion: si no, la compuerta lo volvía a llamar «voz de
        # fuera» y el guion no se podía aprobar (IMG_4965, 11-nov: el llamado a la acción devuelto por Opus bloqueaba «Aprobar»)
        _guardar(carpeta / montaje.PERSONA, {"firma": montaje.firma_palabras(carpeta), "dejar": ia_dejo, "quitar": []})
        c = montaje.contexto(carpeta)   # y los cortes se cierran con lo mismo que medirá la compuerta: esa voz baja ya cuenta como voz
        cortes, avisos = _cerrar(carpeta, c, montaje.reparar({"cortes": cortes}, carpeta)["cortes"], avisos, ia_spans)
        duracion = sum(b - a for a, b in montaje.tramos({"cortes": cortes}, c.fin))
    residuales = montaje.errores({"cortes": cortes}, carpeta)
    necesita_ia = [e for e in residuales if any(g in e for g in GRAVES)] if not con_ia else []
    if duracion > LIMITE_S:
        residuales.append(f"machote: dura {duracion:.0f} s y el máximo del reel es {LIMITE_S} s (quita frases del guion y apruébalo de nuevo: el director no corta)")
    mj = {"version": VERSION, "proyecto": carpeta.name, "firma": firma(carpeta), "fuente_s": round(c.fin, 2),
          "duracion_s": round(duracion, 2), "cortes": cortes, "color": color_de(carpeta),
          "quitado_s": _cuanto_quito(c, cortes, repetidas, ia_spans),
          "ia": {"usada": bool(con_ia), "quito": ia_quito, "restauro": ia_restauro, "llamadas": _lineas(carpeta / "costos.jsonl") - n_costos,
                 "usd_eq": _usd(carpeta / "costos.jsonl", n_costos)},
          "avisos": avisos_ia + [dict(t) for t in {tuple(sorted(x.items())) for x in avisos}], "residuales": residuales,
          "necesita_ia": necesita_ia}
    (carpeta / ARCHIVO).write_text(json.dumps(mj, ensure_ascii=False, indent=1))
    avance(f"machote: {len(cortes)} cortes · {duracion:.1f} s de {c.fin:.1f} s · quitado {mj['quitado_s']}")
    return mj


def _lineas(f: Path) -> int:
    return len(f.read_text().splitlines()) if f.exists() else 0


def _usd(f: Path, desde: int) -> float:
    if not f.exists():
        return 0.0
    return round(sum(json.loads(l).get("usd_equivalente") or 0 for l in f.read_text().splitlines()[desde:]), 3)


# ---------------------------------------------------------------------------------------------------------------------
# Render liviano
# ---------------------------------------------------------------------------------------------------------------------

def _corridas(cuadros: int, cortes: list) -> list:
    """[(primer cuadro, último cuadro exclusivo)] de lo que queda, en la misma cuadrícula que usa el motor (round(t·FPS))."""
    fps = config.FPS
    queda = np.ones(cuadros, bool)
    for a, b in cortes:
        queda[max(0, round(a * fps)):max(0, round(b * fps))] = False
    d = np.diff(np.concatenate([[0], queda.astype(int), [0]]))
    return list(zip(np.where(d == 1)[0].tolist(), np.where(d == -1)[0].tolist()))


def _grafo(corridas: list, ancho: int, alto: int, cubo: Path | None, hdr: bool) -> str:
    """Un solo ffmpeg y una sola pasada: `select` deja pasar solo los cuadros de lo que queda, escala, colorea (LUT en 16 bits, como
    el motor) y comprime. Sin intermedios y sin `trim`+`concat` de VIDEO, que guarda en memoria los cuadros de cada tramo hasta que
    le toca (un clip de 1080p podía pedir varios GB; así se pueden correr varios a la vez). El AUDIO sí va con `atrim`+`concat`
    (pesa poco y corta a la muestra): `aselect` no filtra nada en el ffmpeg 8.0.1 que baja el paquete en Mac (10-nov: el machote
    salía con el audio entero y el render abortaba por duración)."""
    fps = config.FPS
    v = "+".join(f"between(n\\,{c0}\\,{c1 - 1})" for c0, c1 in corridas)
    escala = f"scale={ancho}:{alto}:flags=lanczos" + (":in_color_matrix=bt2020:out_color_matrix=bt709" if hdr else "")
    cadena = escala + (f",{color.filtro(cubo)}" if cubo else "") + ",format=yuv420p"
    n = len(corridas)
    ramas = "".join(f"[s{i}]" for i in range(n))
    tramos = "".join(f"[s{i}]atrim=start={c0 / fps:.5f}:end={c1 / fps:.5f},asetpts=PTS-STARTPTS[a{i}];" for i, (c0, c1) in enumerate(corridas))
    a = f"[0:a:0]asplit={n}{ramas};{tramos}" + "".join(f"[a{i}]" for i in range(n)) + f"concat=n={n}:v=0:a=1[a]"
    return f"[0:v:0]select={v},setpts=N/({fps}*TB),{cadena}[v];{a}"


def render(carpeta: Path, ancho: int = ANCHO, crf: int = CRF, avance=print) -> Path:
    """Escribe `machote.mp4` desde `machote.json`. Atómico: si ffmpeg falla no queda un archivo a medias."""
    carpeta = Path(carpeta).resolve()           # ffmpeg corre con cwd=carpeta: las rutas tienen que ser absolutas
    mj = cargar(carpeta)
    if not mj:
        raise FileNotFoundError(f"{carpeta.name}: no hay machote.json (corre `estudio machote`)")
    meta = json.loads((carpeta / "fuente.json").read_text())
    corridas = _corridas(meta["cuadros"], mj["cortes"])
    if not corridas:
        raise ValueError("los cortes quitan todo el video")
    alto = round(ancho * config.H / config.W / 2) * 2
    cubo = color.cubo(carpeta, mj.get("color"))   # sin color elegido: None (el video tal cual)
    ffmpeg, ffprobe = config.ffmpeg()
    from .motor import procesos
    destino, parcial = carpeta / VIDEO, carpeta / "machote.tmp.mp4"
    cmd = [ffmpeg, "-v", "error", "-y", "-i", meta["video"], "-filter_complex", _grafo(corridas, ancho, alto, cubo, bool(meta.get("hdr"))),
           "-map", "[v]", "-map", "[a]", "-r", str(config.FPS), "-c:v", "libx264", "-preset", "medium", "-crf", str(crf),
           "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-c:a", "aac", "-b:a", "128k",
           "-threads", str(procesos()), "-movflags", "+faststart", str(parcial)]
    esperado = sum(c1 - c0 for c0, c1 in corridas) / config.FPS
    avance(f"machote: renderizando {len(corridas)} tramos, {esperado:.1f} s, {ancho}x{alto} CRF {crf}"
           + (f", color {cubo.name}" if cubo else ", sin color"))
    try:
        r = subprocess.run(cmd, cwd=carpeta, capture_output=True, text=True)
        if r.returncode:
            raise RuntimeError(f"ffmpeg falló al hacer el machote: {r.stderr.strip()[-600:]}")
        real = float(subprocess.run([ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(parcial)],
                                    capture_output=True, text=True, check=True).stdout.strip())
        if abs(real - esperado) > .25:
            raise RuntimeError(f"el machote dura {real:.2f} s y debía durar {esperado:.2f} s")
        parcial.replace(destino)
    finally:
        parcial.unlink(missing_ok=True)
    mj["render"] = {"firma": _firma_render(mj, ancho, crf), "ancho": ancho, "alto": alto, "crf": crf, "duracion_s": round(real, 2),
                    "bytes": destino.stat().st_size}
    (carpeta / ARCHIVO).write_text(json.dumps(mj, ensure_ascii=False, indent=1))
    avance(f"machote: {destino} · {real:.1f} s · {destino.stat().st_size / 1e6:.1f} MB")
    return destino


# ---------------------------------------------------------------------------------------------------------------------
# Etapa fija
# ---------------------------------------------------------------------------------------------------------------------

def preparar(carpeta: Path, con_video: bool = True, con_ia: bool = True, rehacer: bool = False,
             ancho: int = ANCHO, crf: int = CRF, avance=print) -> dict:
    """Deja `machote.json` (y `machote.mp4` si `con_video`) al día. Solo rehace lo que cambió: otras palabras → cortes nuevos;
    otro color o calidad → solo el video."""
    carpeta = Path(carpeta)
    mj = cargar(carpeta)
    if rehacer or not mj or mj.get("firma") != firma(carpeta):
        mj = decidir(carpeta, con_ia, avance)
    elif mj.get("color") != color_de(carpeta):
        mj["color"] = color_de(carpeta)
        (carpeta / ARCHIVO).write_text(json.dumps(mj, ensure_ascii=False, indent=1))
    if con_video and (not (carpeta / VIDEO).exists() or mj.get("render", {}).get("firma") != _firma_render(mj, ancho, crf)):
        render(carpeta, ancho, crf, avance)
        mj = cargar(carpeta)
    if con_video and (carpeta / VIDEO).exists() and mj.get("revision", {}).get("firma") != mj.get("render", {}).get("firma"):
        mj = _revisar(carpeta, mj, avance)
        # bucle cerrado (Pablo 07-nov: «no se trata de arreglar el video, se trata de arreglar el sistema»): lo que la revisión
        # encuentra en el video terminado vuelve al arquitecto, que quita tramos; el código corta y se vuelve a medir
        for vuelta in range(VUELTAS_REVISION if con_ia and not guion_aprobado(carpeta) else 0):   # con guion aprobado los cortes no se tocan
            pistas = [x for x in mj["revision"]["fallas"] if x["tipo"] in ("repeticion", "fuera_de_guion", "voz_de_fondo")]
            if mj["revision"]["ok"] or not pistas:
                break
            avance(f"machote: vuelta {vuelta + 1}: el arquitecto corrige lo que encontró la revisión")
            c = montaje.contexto(carpeta)
            sobran, _ = _leer_guion_final(carpeta, c, mj["cortes"], pistas)
            if not sobran:
                break
            cortes, av2 = _aplicar_sin_mochar(carpeta, c, mj["cortes"], sobran)
            mj.setdefault("avisos", []).extend(av2)
            mj["cortes"] = _ajustar_bordes(c, cortes, [[a, b] for a, b, _, _ in sobran])
            mj["ia"]["quito"] += [{"t0": a, "t1": b, "texto": t[:90], "motivo": m} for a, b, t, m in sobran]
            mj["duracion_s"] = round(sum(b - a for a, b in montaje.tramos({"cortes": mj["cortes"]}, c.fin)), 2)
            (carpeta / ARCHIVO).write_text(json.dumps(mj, ensure_ascii=False, indent=1))
            render(carpeta, ancho, crf, avance)
            mj = _revisar(carpeta, cargar(carpeta), avance)
    return mj


def _aplicar_sin_mochar(carpeta: Path, c, cortes: list, sobran: list) -> tuple[list, list]:
    """Aplica las propuestas del arquitecto UNA por una y descarta la que obliga a cortar con voz sonando (C8872 07-nov: quitar un
    «Y» pegado entre dos frases mochó «importantes» y el «si» siguiente). → (cortes, avisos de lo que no se quitó)."""
    mochan = lambda cs: sum("corta con voz sonando" in e for e in montaje.errores({"cortes": cs}, carpeta))  # noqa: E731
    base, avisos = mochan(cortes), []
    for a, b, texto, motivo in sobran:
        nuevos = montaje.reparar({"cortes": cortes + [[a, b]]}, carpeta)["cortes"]
        if mochan(nuevos) > base:
            avisos.append({"t": round(a, 2), "tipo": "ia", "motivo": f"no se quitó «{texto[:50]}»: no hay silencio donde cortar sin mochar una palabra"})
            continue
        cortes = nuevos
    return cortes, avisos


def palabras_cortadas(carpeta: Path, mj: dict) -> list:
    """Las palabras del talento (sin claqueta ni apuntador) en el tiempo del video cortado: [{w, s, e}]. Es el `palabras.json`
    de lo que el público oye; lo usan la revisión final y los Estilos Pro (la voz cortada llega con estos mismos tiempos).
    Qué palabras quedan lo decide `montaje.quedan` (la misma regla que el guion de la app)."""
    ctx = montaje.contexto(carpeta)
    tr = montaje.tramos({"cortes": mj["cortes"]}, ctx.fin)
    inicio = [0.0]
    for a, b in tr:
        inicio.append(inicio[-1] + b - a)
    sal = []
    for p in montaje.quedan(ctx, mj["cortes"]):
        if p.get("fuera") or not tr:
            continue
        k = max(range(len(tr)), key=lambda i: min(tr[i][1], p["e"]) - max(tr[i][0], p["s"]))   # el tramo donde más suena
        sal.append({"w": p["w"], "s": inicio[k] + p["s"] - tr[k][0], "e": inicio[k] + p["e"] - tr[k][0]})
    return sal


def _revisar(carpeta: Path, mj: dict, avance=print) -> dict:
    """Revisión final OBLIGATORIA sobre el video terminado (Pablo 07-nov). Mide con el mismo talento que usó el corte, y las
    repeticiones también sobre las palabras originales que quedaron (Whisper limpia los tartamudeos al volver a transcribir)."""
    from . import revisar_corte
    ctx = montaje.contexto(carpeta)
    informe = revisar_corte.revisar(carpeta / VIDEO, nivel_talento=ctx.talento)
    sal = palabras_cortadas(carpeta, mj)
    # una palabra mochada (el corte cae con voz sonando) bloquea: es un error que se oye, aunque el audio no tenga silencio
    inicio = [0.0]
    tr = montaje.tramos({"cortes": mj["cortes"]}, ctx.fin)
    for a, b in tr:
        inicio.append(inicio[-1] + b - a)
    for k, (a, b) in enumerate(tr):
        for borde, t_sal in ((a, inicio[k]), (b, inicio[k + 1])):
            if 0 < borde < ctx.fin - .01 and voz.hay_voz(ctx.oye, borde):
                informe["fallas"].append({"tipo": "palabra_mochada", "segundo": round(t_sal, 2), "detalle": "el corte cae con voz sonando"})
                informe["ok"] = False
    ya = {f["segundo"] for f in informe["fallas"] if f["tipo"] == "repeticion"}
    extra = [{"tipo": "repeticion", "segundo": t, "detalle": f"«{g}» dos veces (guion)"} for t, g in revisar_corte.repeticiones(sal)
             if not any(abs(t - u) < 1.5 for u in ya)]
    if extra:
        informe["fallas"] = sorted(informe["fallas"] + extra, key=lambda f: f["segundo"])
        informe["ok"] = False
    revisar_corte.guardar(carpeta / VIDEO, informe)
    mj["revision"] = {"firma": mj.get("render", {}).get("firma"), "ok": informe["ok"], "fallas": informe["fallas"]}
    (carpeta / ARCHIVO).write_text(json.dumps(mj, ensure_ascii=False, indent=1))
    avance("revisión final: " + ("pasa" if informe["ok"] else "NO pasa: " + "; ".join(
        f"{x['tipo']} {x['segundo']} s ({x['detalle']})" for x in informe["fallas"])))
    return mj


def apto(carpeta: Path) -> bool:
    """¿El machote pasó la revisión final? Solo un machote apto se entrega o sirve de base para un estilo."""
    return bool((cargar(carpeta) or {}).get("revision", {}).get("ok"))


# ---------------------------------------------------------------------------------------------------------------------
# Los estilos parten del machote
# ---------------------------------------------------------------------------------------------------------------------

def nota_para_director(carpeta: Path) -> str:
    """Párrafo para el prompt del director cuando el proyecto ya tiene machote."""
    mj = cargar(carpeta)
    if not mj:
        return ""
    return ("\n\n## YA HAY MACHOTE (cortes hechos)\n"
            f"`machote.json` trae los `cortes` ya decididos y reparados (video de {mj['fuente_s']:.0f} s → {mj['duracion_s']:.0f} s: "
            "última toma de cada frase repetida, sin claqueta ni apuntador, pausas recortadas). Copia esos `cortes` TAL CUAL a "
            "`storyboard.json` y diseña encima: no los rehagas ni los muevas. Solo agrega un corte si el estilo de verdad lo necesita "
            "(una frase entera que no cabe en el ritmo del estilo); nunca devuelvas algo que el machote quitó.")


def _guardar(f: Path, datos: dict) -> None:
    """Escritura atómica: archivo temporal + os.replace (un corte de luz o dos procesos nunca dejan el JSON a medias)."""
    with tempfile.NamedTemporaryFile("w", dir=f.parent, prefix=f.name + ".", suffix=".part", delete=False, encoding="utf-8") as t:   # nombre único: hilos y procesos no se pisan
        t.write(json.dumps(datos, ensure_ascii=False, indent=1))
    os.replace(t.name, f)


def _punto_fijo(carpeta: Path, cortes: list) -> list:
    """`reparar` repetido hasta que no cambie nada (máximo 4 pasadas): los cortes en los que ya se puede confiar."""
    cortes = [[round(a, 3), round(b, 3)] for a, b in cortes]
    for _ in range(4):
        nuevos = [[round(a, 3), round(b, 3)] for a, b in montaje.reparar({"cortes": cortes}, carpeta)["cortes"]]
        if nuevos == cortes:
            break
        cortes = nuevos
    return cortes


def _errores_nuevos(carpeta: Path, viejos: list, nuevos: list) -> list:
    """Errores de montaje que los cortes nuevos tienen de MÁS que los viejos (se comparan sin cifras: los segundos se corren)."""
    from collections import Counter
    norma = lambda e: re.sub(r"\d+(?:\.\d+)?", "#", e)  # noqa: E731
    antes = Counter(norma(e) for e in montaje.errores({"cortes": viejos}, carpeta))
    return [e for e, n in (Counter(norma(e) for e in montaje.errores({"cortes": nuevos}, carpeta)) - antes).items() for _ in range(n)]


def _escribir_cortes(carpeta: Path, mj: dict, nuevos: list, mismas: bool, quitadas=(), agregadas=()) -> None:
    c = montaje.contexto(carpeta)
    viejos = mj["cortes"]
    quitados, puestos = [x for x in viejos if x not in nuevos], [x for x in nuevos if x not in viejos]
    movimientos = []
    for q in quitados:
        a = min(puestos, key=lambda n: abs(n[0] - q[0]) + abs(n[1] - q[1])) if puestos else None
        movimientos.append({"de": q, "a": a, "mueve_s": round(max(abs(q[0] - a[0]), abs(q[1] - a[1])), 3) if a else None})
    mj = {**mj, "cortes": nuevos, "duracion_s": round(sum(b - a for a, b in montaje.tramos({"cortes": nuevos}, c.fin)), 2)}
    reg = {"fecha": time.strftime("%Y-%m-%d %H:%M"), "cambios": movimientos, "mismas_palabras": mismas}
    if not mismas:
        reg.update(quitadas=[f"{p['w']} ({p['s']:.1f} s)" for p in quitadas], agregadas=[f"{p['w']} ({p['s']:.1f} s)" for p in agregadas])
    mj.setdefault("ajustes_tecnicos", []).append(reg)
    _guardar(carpeta / ARCHIVO, mj)


def reparar_machote(carpeta: Path, avance=print) -> dict:
    """La reparación técnica del machote en UN solo lugar (0 IA). → {"estado", "mensaje", "quitadas", "agregadas"}:
    · "estable": nada que mover;
    · "ajustado": solo bordes dentro de un silencio, mismas palabras (`montaje.quedan`): machote actualizado con registro, aprobación vigente;
    · "empeora": mismas palabras pero los cortes nuevos traerían errores de montaje que los viejos no tenían: no se aplica;
    · "guion_nuevo": la reparación cambia palabras (p. ej. se traga una repetida): se aplica, se borra la aprobación y el mensaje dice qué."""
    carpeta = Path(carpeta)
    mj = cargar(carpeta)
    if not mj:
        return {"estado": "estable", "mensaje": None, "quitadas": [], "agregadas": []}
    viejos = [[round(a, 3), round(b, 3)] for a, b in mj["cortes"]]
    nuevos = _punto_fijo(carpeta, viejos)
    if nuevos == viejos:
        return {"estado": "estable", "mensaje": None, "quitadas": [], "agregadas": []}
    c = montaje.contexto(carpeta)
    antes, despues = montaje.quedan(c, viejos), montaje.quedan(c, nuevos)
    ids = lambda ps: {id(p) for p in ps}  # noqa: E731
    quitadas, agregadas = [p for p in antes if id(p) not in ids(despues)], [p for p in despues if id(p) not in ids(antes)]
    if not quitadas and not agregadas:
        if _errores_nuevos(carpeta, viejos, nuevos):
            return {"estado": "empeora", "mensaje": None, "quitadas": [], "agregadas": []}
        _escribir_cortes(carpeta, mj, nuevos, True)
        avance("machote: bordes movidos dentro de un silencio; mismas palabras, el guion aprobado sigue valiendo")
        return {"estado": "ajustado", "mensaje": None, "quitadas": [], "agregadas": []}
    if _errores_nuevos(carpeta, viejos, nuevos):   # igual que en «ajustado»: no se aplica una reparación que empeora el montaje
        return {"estado": "empeora", "mensaje": None, "quitadas": [], "agregadas": []}
    _escribir_cortes(carpeta, mj, nuevos, False, quitadas, agregadas)
    desaprobar(carpeta)
    lista = lambda ps: ", ".join(f"«{p['w']}» ({p['s']:.1f} s)" for p in ps[:6]) or "nada"  # noqa: E731
    msg = f"{MENSAJE_GUION_NUEVO}. Quitó: {lista(quitadas)}. Agregó: {lista(agregadas)}. Aprueba el guion nuevo."
    avance("machote: " + msg)
    return {"estado": "guion_nuevo", "mensaje": msg, "quitadas": quitadas, "agregadas": agregadas}


def actualizar_cortes(carpeta: Path, nuevos: list, avance=print) -> bool:
    """Acepta unos cortes reparados (los del montaje del director) SOLO si son el mismo guion (mismas palabras) y no traen errores de
    montaje nuevos; entonces `machote.json` se actualiza con registro. Si no, False y no toca nada."""
    carpeta = Path(carpeta)
    mj = cargar(carpeta)
    if not mj:
        return False
    viejos, nuevos = [[round(a, 3), round(b, 3)] for a, b in mj["cortes"]], [[round(a, 3), round(b, 3)] for a, b in nuevos]
    if nuevos == viejos:
        return True
    if cambia_palabras(carpeta, nuevos) or _errores_nuevos(carpeta, viejos, nuevos):
        return False
    _escribir_cortes(carpeta, mj, nuevos, True)
    avance("machote: bordes movidos dentro de un silencio; mismas palabras")
    return True


def cambia_palabras(carpeta: Path, nuevos: list) -> bool:
    """¿Esos cortes dejan un conjunto de palabras distinto al del machote? (misma regla: `montaje.quedan`)"""
    mj = cargar(carpeta)
    c = montaje.contexto(carpeta)
    return montaje.palabras_que_quedan(c, mj["cortes"]) != montaje.palabras_que_quedan(c, nuevos)


def reparar_cortes(carpeta: Path, avance=print) -> dict:
    """Una sola capa para un proyecto ya dirigido (CLI `reparar-cortes`): repara los cortes del machote, los registra y los impone al
    storyboard. Sin director ni ojo (0 IA). Si la reparación cambia palabras, el guion nuevo queda PENDIENTE de aprobación."""
    carpeta = Path(carpeta)
    if not cargar(carpeta):
        raise FileNotFoundError(f"{carpeta.name}: no hay machote.json")
    r = reparar_machote(carpeta, avance)
    if r["estado"] in ("ajustado", "guion_nuevo"):
        imponer(carpeta)
    return r


# ---------------------------------------------------------------------------------------------------------------------
# El guion lo corrige la persona (Pablo, 11-nov: «un mini editor de texto que me permita revisar qué deja y qué no, y decidir qué
# dejar también… el problema de esos editores es que no mandan la orden al código: crea algo que sí sirva»)
# ---------------------------------------------------------------------------------------------------------------------

BAJA_DB = voz.APUNTADOR_EXTIENDE_DB   # una palabra que suena así de baja frente al talento se señala en el guion


def _motivos(carpeta: Path, c, mj: dict) -> dict:
    """{índice de palabra: por qué no está en el guion}, en palabras de persona. Solo para mostrar; no decide nada."""
    persona = montaje.decisiones(carpeta)
    libres = [p for p in c.palabras if not p.get("fuera")]
    repetidas = _cortes_repetidas(libres)
    ia = [(x["t0"], x["t1"], x.get("motivo", "")) for x in (mj.get("ia") or {}).get("quito", [])]
    en = lambda p, a, b: a - 1e-3 <= (p["s"] + p["e"]) / 2 <= b + 1e-3  # noqa: E731
    out = {}
    for k, p in enumerate(c.palabras):
        if k in persona["quitar"]:
            out[k] = "la quitaste tú"
        elif p.get("motivo") == "apuntador":
            out[k] = "sonaba muy baja: la app creyó que era otra persona"
        elif p.get("motivo") == "claqueta":
            out[k] = "claqueta o conteo"
        elif p.get("fuera"):
            out[k] = "voz de fuera de cámara"
        elif any(en(p, a, b) for a, b in repetidas):
            out[k] = "toma repetida: queda la última"
        else:
            out[k] = next((m for a, b, m in ia if en(p, a, b)), "")
    return out


# Cada error de la compuerta del montaje, dicho para quien NO es técnico y puesto en la palabra donde pasa. (patrón, de qué grupo
# del patrón sale el segundo, frase). El patrón de las repetidas no trae segundo propio: sale de cada versión listada.
_EN_CRISTIANO = (
    (r"voz fuera de cámara «(?P<x>.+?)» en (?P<t>[\d.]+) s", "Aquí se cuela una voz que la app tomó por otra persona («{x}»). Si eres tú, tócala para dejarla; si no, quita lo que tenga pegado."),
    (r"claqueta «(?P<x>.+?)» en (?P<t>[\d.]+) s", "Aquí se cuela la claqueta («{x}»): quita lo que tenga pegado."),
    (r"el inicio del tramo (?P<t>[\d.]+)–[\d.]+ s corta con voz", "El corte cae en medio de una palabra y puede oírse mochada: quita esta palabra o deja también la anterior."),
    (r"el fin del tramo [\d.]+–(?P<t>[\d.]+) s corta con voz", "El corte cae en medio de una palabra y puede oírse mochada: quita esta palabra o deja también la que sigue."),
    (r"el tramo [\d.]+–(?P<t>[\d.]+) s termina .*? después de «(?P<x>.+?)»", "«{x}» queda sin aire al final y puede sonar cortada: quítala o deja también la que sigue."),
    (r"el tramo (?P<t>[\d.]+)–[\d.]+ s dura", "Aquí queda un pedacito suelto de menos de medio segundo: quítalo o deja también lo de al lado."),
    (r"el tramo (?P<t>[\d.]+)–[\d.]+ s arranca con «(?P<x>.+?)»", "Este pedazo arranca con la cola de otra toma («{x}»): quítala."),
    (r"hay (?P<x>[\d.]+) s de silencio .*?(?P<t>[\d.]+) s del\s+original", "Aquí queda una pausa de {x} s que no se pudo cerrar: quita la palabra de al lado o deja la frase completa."),
)


def _problemas(c, errores: list) -> list:
    """Los errores del montaje → [{"k": palabra donde pasa (o None si es del guion entero), "texto"}], sin repetir palabra."""
    def palabra_en(t):
        return min(range(len(c.palabras)), key=lambda k: abs((c.palabras[k]["s"] + c.palabras[k]["e"]) / 2 - t)) if c.palabras else None
    out, vistas = [], set()

    def agrega(k, texto):
        if k is None or k not in vistas:
            vistas.add(k)
            out.append({"k": k, "texto": texto})
    for e in errores:
        if "versiones repetidas" in e:
            for t in re.findall(r"([\d.]+)–[\d.]+ s «", e):
                agrega(next((k for k, p in enumerate(c.palabras) if p["s"] >= float(t) - .01), None), "Esto lo repites más adelante y queda la última vez: quita esta o la otra.")
            continue
        for patron, frase in _EN_CRISTIANO:
            if (m := re.search(patron, e)):
                agrega(palabra_en(float(m["t"])), frase.format(**m.groupdict()))
                break
        else:
            agrega(None, e.removeprefix("montaje: ").removeprefix("machote: "))
    return out


def guion_editable(carpeta: Path) -> dict:
    """Todo lo que se dijo, palabra por palabra, con lo que queda y lo que no (y por qué): lo que pinta el editor del guion.
    `firma` ata los índices a esta transcripción; `frases` = [[primera, última+1]] para leerlo por renglones; `problemas` = lo que
    hoy impide aprobar, cada uno en su palabra (se mide ahora, no se lee de un archivo viejo). No escribe nada."""
    carpeta = Path(carpeta)
    mj = cargar(carpeta)
    if not mj:
        return {}
    c = montaje.contexto(carpeta)
    queda = set(montaje.palabras_que_quedan(c, mj["cortes"]))
    motivos = _motivos(carpeta, c, mj)
    talento = float(np.percentile([voz._nivel_palabra(c.db, p) for p in c.palabras], 90)) if c.palabras else 0.0
    palabras = []
    for k, p in enumerate(c.palabras):
        baja = voz._nivel_palabra(c.db, p) < talento - BAJA_DB
        palabras.append({"k": k, "w": p["w"], "s": p["s"], "e": p["e"], "queda": k in queda,
                         **({"motivo": motivos[k]} if k not in queda and motivos[k] else {}), **({"baja": True} if baja else {})})
    frases = [[a, b] for i0, i1 in repeticiones.frases(c.palabras) for a, b in _partir(c.palabras, i0, i1)]
    errores = montaje.errores({"cortes": mj["cortes"]}, carpeta) + ([largo] if (largo := exceso(carpeta)) else [])
    return {"firma": montaje.firma_palabras(carpeta), "palabras": palabras, "frases": frases, "duracion_s": mj.get("duracion_s"),
            "problemas": _problemas(c, errores)}


def editar_guion(carpeta: Path, quedan, avance=print) -> dict:
    """La persona dice QUÉ PALABRAS quedan (índices de `guion_editable`) y eso se vuelve cortes de verdad, por el mismo camino que
    usa la decisión automática (`reparar` + `_cerrar`): bordes en silencios reales, pausas cerradas, arranque y final en la voz.
    Lo que decidió queda en `guion-persona.json` y manda sobre el detector (lo que dejó deja de ser «voz de fuera» y no cuenta como
    toma repetida) y sobre las reparaciones posteriores. El guion cambia: hay que aprobarlo de nuevo. Devuelve el guion editable ya
    actualizado y, si algo no se pudo cumplir tal cual (dos palabras pegadas sin silencio entre ellas), lo dice en `no_se_pudo`:
    nunca se ignora en silencio."""
    carpeta = Path(carpeta)
    mj = cargar(carpeta)
    if not mj:
        raise FileNotFoundError(f"{carpeta.name}: todavía no hay guion")
    c = montaje.contexto(carpeta)
    n = len(c.palabras)
    quiere = {int(k) for k in quedan if 0 <= int(k) < n}
    if not quiere:
        raise ValueError("El guion no puede quedar vacío: deja al menos una frase.")
    antes = set(montaje.palabras_que_quedan(c, mj["cortes"]))
    previas = montaje.decisiones(carpeta)
    dejar = (previas["dejar"] | (quiere - antes) | {k for k in quiere if c.palabras[k].get("fuera")}) & quiere
    quitar = (previas["quitar"] | (antes - quiere)) - quiere
    _guardar(carpeta / montaje.PERSONA, {"firma": montaje.firma_palabras(carpeta), "dejar": sorted(dejar), "quitar": sorted(quitar)})
    c = montaje.contexto(carpeta)   # otra vez: lo que la persona dejó ya no es «fuera»
    fuera = sorted(set(range(n)) - quiere)
    spans, k = [], 0
    while k < len(fuera):               # cada tanda seguida de palabras que no quedan = un corte de contenido
        j = k
        while j + 1 < len(fuera) and fuera[j + 1] == fuera[j] + 1:
            j += 1
        spans.append([c.palabras[fuera[k]]["s"], c.palabras[fuera[j]]["e"]])
        k = j + 1
    avisos: list = []
    cortes = montaje.reparar({"cortes": spans}, carpeta, avisos)["cortes"]
    cortes, avisos = _cerrar(carpeta, c, cortes, avisos, spans)
    logrado = set(montaje.palabras_que_quedan(c, cortes))
    residuales = montaje.errores({"cortes": cortes}, carpeta)
    duracion = round(sum(b - a for a, b in montaje.tramos({"cortes": cortes}, c.fin)), 2)
    mj = {**mj, "cortes": cortes, "duracion_s": duracion, "residuales": residuales, "necesita_ia": [],
          "avisos": [dict(t) for t in {tuple(sorted(x.items())) for x in avisos}],
          "persona": {"fecha": time.strftime("%Y-%m-%d %H:%M"), "dejo": len(dejar), "quito": len(quitar)}}
    mj.pop("revision", None)            # la revisión era del guion anterior
    _guardar(carpeta / ARCHIVO, mj)
    desaprobar(carpeta)
    if (carpeta / "storyboard.json").exists():
        imponer(carpeta)
    avance(f"guion: la persona dejó {len(dejar)} palabras y quitó {len(quitar)} · {duracion:.1f} s")
    texto = lambda ks: " ".join(c.palabras[k]["w"] for k in sorted(ks))  # noqa: E731
    no_se_pudo = [m for m in (
        f"«{texto(logrado - quiere)}» se sigue oyendo: viene pegada a la palabra de al lado, sin una pausa donde cortar. Para quitarla, quita también esa palabra."
        if logrado - quiere else "",
        f"«{texto(quiere - logrado)}» no se pudo dejar: viene pegada a algo que quitaste, sin una pausa donde cortar. Para dejarla, deja también esa palabra."
        if quiere - logrado else "") if m]
    return {**guion_editable(carpeta), "no_se_pudo": no_se_pudo}


def guion_aprobado(carpeta: Path) -> bool:
    f = Path(carpeta) / "preferencias.json"
    try:
        return bool(json.loads(f.read_text()).get("guion_aprobado")) if f.exists() else False
    except ValueError:
        return False


def desaprobar(carpeta: Path) -> None:
    """Rehacer los cortes cambia el texto que la persona aprobó: la aprobación se borra y hay que aprobar el guion nuevo."""
    f = Path(carpeta) / "preferencias.json"
    try:
        prefs = json.loads(f.read_text()) if f.exists() else {}
    except ValueError:
        return
    if prefs.get("guion_aprobado"):
        prefs.pop("guion_aprobado")
        _guardar(f, prefs)


def imponer(carpeta: Path) -> bool:
    """Garantía en código: los cortes del storyboard SON los del machote (los aprobados): el director no suma, quita ni mueve ninguno.
    Devuelve True si cambió el storyboard."""
    carpeta = Path(carpeta)
    mj = cargar(carpeta)
    f = carpeta / "storyboard.json"
    if not mj or not f.exists():
        return False
    sb = json.loads(f.read_text())
    fijos = [[round(a, 3), round(b, 3)] for a, b in mj["cortes"]]
    if fijos == [list(x) for x in sb.get("cortes", [])]:
        return False
    _guardar(f, {**sb, "cortes": fijos})
    return True
