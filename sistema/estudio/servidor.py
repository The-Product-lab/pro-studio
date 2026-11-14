"""Servidor local de la app (127.0.0.1:8792): sirve la UI y expone el motor como API JSON. Los trabajos largos van en hilos."""
import itertools
import json
import mimetypes
import shutil
import socket
import subprocess
import sys
import threading
import os
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import agente, catalogo, config, errores, machote, montaje, motor, previas, rapida, sesion, trabajo

PUERTO = int(os.environ.get("ESTUDIO_PUERTO", 8792))   # otro puerto = otra copia de la app al lado (pruebas)
APP = config.RAIZ / "app"
LIB = config.RAIZ / "librerias"
TRABAJOS: dict = {}
_CUENTA = itertools.count()   # numera trabajos y pedidos de vistas: dos en el mismo milisegundo no se pisan


def _trabajo(nombre, fn, *args, proyecto=None):
    tid = f"{nombre}-{int(time.time() * 1000)}-{next(_CUENTA)}"
    t = TRABAJOS[tid] = {"id": tid, "tipo": nombre, "proyecto": proyecto, "estado": "corriendo", "log": [], "resultado": None,
                         "inicio": time.time()}

    def avance(msg):
        trabajo.revisar()   # cada aviso de avance es un punto donde «Detener» corta
        t["log"].append(str(msg))

    def correr():
        trabajo.entrar(tid)
        try:
            t["resultado"] = fn(*args, avance=avance)
            t["estado"] = "listo"
        except Exception as e:  # noqa: BLE001 — a la pantalla solo la frase clara; el detalle va al registro
            if tid in trabajo._DETENIDOS:   # lo paró la persona (el proceso cortado o el siguiente aviso): no es un error
                t["log"].append("Detenido: lo paraste tú.")
                t["estado"] = "detenido"
            else:
                t["log"].append(errores.amable(nombre, e))
                t["estado"] = "error"
        finally:
            trabajo.soltar(tid)
    threading.Thread(target=correr, daemon=True).start()
    return tid


# Lo que la app está haciendo, dicho para la persona: (tipo de trabajo) → cómo se nombra en la barra de estado.
NOMBRES_TRABAJO = {"preparar": "Preparando tu video", "dirigir": "Editando con el estilo", "render": "Sacando el video final", "unir": "Uniendo las partes del video",
                   "tanda": "Mirando cuántos videos salen", "tanda-preparar": "Preparando los videos de la grabación",
                   "corregir": "Aplicando tu corrección", "crear-estilo": "Creando el estilo", "pro": "Editando con el estilo Pro"}


def _actividad() -> list:
    """Todo lo que corre ahora (sin las vistas previas, que duran segundos): qué es, de qué video, el último paso que avisó y cuánto
    lleva. Es lo que pinta la barra de estado de la app, con su botón «Detener»."""
    ahora = time.time()
    return [{"id": t["id"], "tipo": t["tipo"], "proyecto": t["proyecto"], "que": NOMBRES_TRABAJO.get(t["tipo"], t["tipo"]),
             "paso": next((l for l in reversed(t["log"]) if not l.startswith("/")), ""), "segundos": int(ahora - t.get("inicio", ahora)),
             "deteniendo": t["id"] in trabajo._DETENIDOS}
            for t in list(TRABAJOS.values()) if t["estado"] == "corriendo" and t["tipo"] != "previa"]


def capas_activas() -> bool:
    """Bandera del editor por capas (docs/PLANO-EDITOR-CAPAS.md): ESTUDIO_CAPAS=0 la apaga y /api/corregir vuelve a ser solo el Agente Editor."""
    return os.environ.get("ESTUDIO_CAPAS", "1") != "0"


def _corregir_capas(texto, proyecto, segundo=None, avance=print):
    from . import corrector_capas
    r = corrector_capas.intentar(_proyecto(proyecto), texto, segundo, avance)
    return r if r is not None else agente.corregir(texto, proyecto, avance)


def _proyecto(pid: str) -> Path:
    """La carpeta de un proyecto por su NOMBRE. Puede ser un enlace a otro disco (el lote deja lo pesado en C:, `--trabajo-en`):
    lo que se revisa es el nombre (nada de rutas ni «..»), no a dónde apunta."""
    pid = str(pid)
    if not pid or pid in (".", "..") or "/" in pid or "\\" in pid or Path(pid).name != pid:
        raise ValueError("proyecto inválido")
    return config.PROYECTOS / pid


def _unir(videos: list, avance) -> str:
    """Varias partes ya subidas (en `_subidas/`), en el orden que dejó la persona → un solo video en `_subidas/`. Las partes se
    borran al terminar bien: lo que sigue (preparar, guion, editar) trabaja sobre el video unido."""
    from . import unir
    subidas = (config.PROYECTOS / "_subidas").resolve()
    rutas = [Path(v).resolve() for v in videos]
    if any(r.parent != subidas for r in rutas):   # solo lo que subió la app: nunca una ruta cualquiera del disco
        raise errores.Aviso("Solo se unen videos subidos desde esta pantalla. Súbelos otra vez.")
    base = f"{rutas[0].stem}-unido" if rutas else "unido"
    destino = next(d for n in itertools.count(1) if not (d := subidas / (f"{base}.mp4" if n == 1 else f"{base}-{n}.mp4")).exists())
    unir.unir(rutas, destino, avance)
    for r in set(rutas):
        r.unlink(missing_ok=True)
    return str(destino)


def _en_subidas(videos: list) -> list:
    """Solo lo que subió la app (carpeta `_subidas`): nunca una ruta cualquiera del disco."""
    subidas = (config.PROYECTOS / "_subidas").resolve()
    rutas = [Path(v).resolve() for v in videos]
    if any(r.parent != subidas for r in rutas):
        raise errores.Aviso("Solo se reparten videos subidos desde esta pantalla. Súbelos otra vez.")
    return rutas


def _tanda_analizar(tid: str, avance) -> str:
    from . import reparto
    reparto.analizar(tid, avance)
    return tid


def _tanda_preparar(tid: str, avance) -> str:
    """Los videos aprobados, uno tras otro, por el mismo camino que un video subido solo (`_preparar`)."""
    from . import reparto
    reparto.preparar_videos(tid, _preparar, avance)
    return tid


def _tanda_en_curso(tid: str) -> dict | None:
    return next((t for t in list(TRABAJOS.values()) if t["estado"] == "corriendo" and t["tipo"] in ("tanda", "tanda-preparar")
                 and t.get("tanda") == tid), None)


def _preparar(video, nombre, avance):
    """Lo que NO depende del estilo, en dos carriles: el guion (transcribir + cortes del machote, sale en minutos) y, en un hilo
    aparte, el video normalizado y el alfa de la persona. Con GPU van a la vez (Whisper no toca el procesador). Sin GPU el guion va
    PRIMERO y el video arranca cuando el guion ya está a la vista: a la vez se peleaban el procesador y el guion de un 4K de 68 s
    tardaba más de 7 min en una Mac (Pablo, 11-nov: «debería mostrar el guion rápido para hacerle las correcciones rápido»).
    El director NO corre aquí: lo lanza `_dirigir` con el estilo elegido."""
    from . import asr, ingesta
    fallo: list = []
    guion_a_la_vista = threading.Event()
    if not asr.en_cpu():
        guion_a_la_vista.set()

    def pesado():
        guion_a_la_vista.wait()
        try:
            ingesta.preparar_media(video, nombre, lambda m: avance(f"[video] {m}"))
        except Exception as e:  # noqa: BLE001 — se re-lanza abajo, ya con el guion a salvo
            fallo.append(e)
    hilo = threading.Thread(target=trabajo.heredar(pesado), daemon=True)   # el carril del video es del mismo trabajo: «Detener» lo para también
    hilo.start()
    try:
        ingesta.preparar_guion(video, nombre, avance)
    finally:
        guion_a_la_vista.set()
        hilo.join()
    if fallo:
        raise fallo[0]
    avance("material listo: elige el estilo")
    return nombre


MOTIVO_SIN_CONFIRMAR = "Falta confirmar: «Editar con este estilo» es una edición completa (usa IA e imágenes)."
MOTIVO_SIN_APROBAR = "Primero aprueba el guion."   # PLANO-FLUJO: el director no corre hasta que el guion esté aprobado


_PEDIDO: dict = {}      # proyecto → token del último pedido de dirigir (un pedido nuevo deja sin efecto al anterior si aún espera)
_DIRIGIENDO: dict = {}  # proyecto → candado: un solo director a la vez por proyecto


def _impedimento(carpeta: Path) -> str | None:
    """`machote.impedimento` con el candado: si el director está corriendo en ese proyecto no se escribe nada (responde 409)."""
    lock = _DIRIGIENDO.setdefault(Path(carpeta).name, threading.Lock())
    if not lock.acquire(blocking=False):   # el mismo candado de `_dirigir`: o corre el director o se revisa el machote, nunca los dos
        return "Ya se está dirigiendo o revisando este video: espera a que termine."
    try:
        return machote.impedimento(carpeta)
    finally:
        lock.release()


def _dirigir(pid, estilo, imagenes, densidad, token, avance):
    """Desde el guion aprobado y el estilo elegido: densidad, director con ESE estilo, imágenes y ojo. Si ya había un intento (otro estilo)
    se borra primero (`limpiar_intento`); los cortes salen siempre del machote."""
    from . import director, imagenes as img, ingesta, lemo_apoyos, validar
    carpeta = _proyecto(pid)
    if not machote.guion_aprobado(carpeta):
        raise ValueError(MOTIVO_SIN_APROBAR)
    with _DIRIGIENDO.setdefault(pid, threading.Lock()):
        if _PEDIDO.get(pid) != token:
            return "reemplazado por un pedido más nuevo"
        while any(t["proyecto"] == pid and t["tipo"] == "preparar" and t["estado"] == "corriendo" for t in list(TRABAJOS.values())):
            avance("esperando el video normalizado…")
            time.sleep(2)
        meta = json.loads((carpeta / "fuente.json").read_text())
        ingesta.preparar_media(meta["original"], pid, avance)   # no hace nada si ya está; termina lo que falte (reinicio a medias)
        ingesta.limpiar_intento(carpeta)
        validar.fijar_densidad(carpeta, densidad if densidad in validar.DENSIDADES else "normal")
        estilo = lemo_apoyos.elegir(carpeta, estilo)   # «lemo:<slug>» → estilo «lemo» con ese estilo de Lemo anotado en el video
        if estilo != lemo_apoyos.ESTILO:               # con Lemo el arte no es de Higgsfield: no depende de ese conector
            imagenes = img.disponibles(imagenes and not director.sin_director(estilo), avance)
        director.dirigir(carpeta, estilo, imagenes, avance)
        img.arte_del_video(carpeta, imagenes, avance)
        # un estilo sin director (Básico) no usa IA: tampoco el ojo (la pantalla lo promete así; antes aquí sí lo llamaba, dos veces)
        for ronda in (() if director.sin_director(estilo) else (1, 2)):
            v = director.mirar(carpeta, ronda, avance)
            avance(f"ojo: {v.get('veredicto')}")
            if v.get("veredicto") == "aprobar":
                break
        avance("listo para personalizar")
    return pid


def _guardar_estilo(carpeta: Path, estilo: dict) -> dict:
    """Suma al storyboard SOLO las claves que llegan (lo que la persona cambió): lo demás (p. ej. una corrección) queda intacto."""
    sb = json.loads((carpeta / "storyboard.json").read_text())
    sb["estilo"] = catalogo.aplicar_estilo(sb.get("estilo", {}), estilo)
    machote._guardar(carpeta / "storyboard.json", sb)   # entero o nada, con temporal único: el render o una vista que lee a la vez nunca ve medio archivo
    return sb


_VIGENTE: dict = {}   # carpeta de vistas → id del último pedido: los anteriores se descartan sin dibujar


def _previa(clave, nombre_trabajo, base_url, generar, avance=print):
    """Una petición de vistas: solo la más nueva por carpeta se dibuja. Devuelve las URL de las dos vistas y sus notas."""
    def vigente():
        return _VIGENTE.get(clave) == nombre_trabajo
    v = f"?v={int(time.time() * 1000)}"
    r = generar(lambda archivo: avance(f"{base_url}{archivo}{v}"), vigente)   # cada vista se anuncia (su URL) apenas está dibujada
    if r.get("cancelada"):
        return r
    return {**r, "a": f"{base_url}{r['a']}{v}", "b": f"{base_url}{r['b']}{v}"}


def _pedir_previa(clave, base_url, generar, **kw):
    """Lanza el trabajo de vistas; la petición nueva deja vieja a la anterior de la misma carpeta."""
    nombre = f"{clave}#{next(_CUENTA)}"
    _VIGENTE[clave] = nombre
    tid = _trabajo("previa", _previa, clave, nombre, base_url, generar, **kw)
    return tid


def _guion(carpeta: Path) -> dict:
    """El texto exacto que queda en el video: las palabras de `palabras.json` que no caen dentro de un corte. Los cortes salen del
    storyboard (lo que decidió el director) o, si aún no hay, del machote (lo que decidió la ingesta). Sin ninguno de los dos
    todavía no hay guion: {"listo": False}, nunca un texto inventado."""
    def leer(nombre):
        f = carpeta / nombre
        try:
            return json.loads(f.read_text()) if f.exists() else None
        except ValueError:
            return None
    palabras, sb, mj = leer("palabras.json"), leer("storyboard.json") or {}, leer("machote.json") or {}
    fuente, cortes = next(((n, d["cortes"]) for n, d in (("storyboard", sb), ("machote", mj)) if isinstance(d.get("cortes"), list)), (None, None))
    if not palabras or cortes is None:
        return {"listo": False}
    if (carpeta / ".energia.npy").exists():
        quedan = montaje.quedan(montaje.contexto(carpeta), cortes)   # la regla única de qué palabras quedan
    else:   # un GET no mide audio ni escribe: sin energía medida aún, el punto medio de cada palabra (solo mientras se prepara)
        quedan = [p for p in sorted(palabras, key=lambda p: p["s"]) if not any(a <= (p["s"] + p["e"]) / 2 <= b for a, b in cortes)]
    edicion = machote.guion_editable(carpeta) if mj and (carpeta / ".energia.npy").exists() else None   # todo lo dicho, para corregirlo
    return {"listo": True, "fuente": fuente, "texto": " ".join(p["w"] for p in quedan).strip(),
            "palabras": [{"w": p["w"], "s": p["s"], "e": p["e"], **({"fuera": True} if p.get("fuera") else {})} for p in quedan],
            "aprobado": bool((leer("preferencias.json") or {}).get("guion_aprobado")), **({"edicion": edicion} if edicion else {})}


GUION_PARADO = "El guion de este video no se terminó de preparar."
SIN_ORIGINAL = "Ya no encuentro el video original de este proyecto. Súbelo otra vez desde Material."


def _guion_parado(pid: str) -> str | None:
    """Sin guion y sin nadie preparándolo: el motivo del último intento (si falló en esta sesión) o que quedó a medias. None si se
    está preparando ahora. En un equipo nuevo sin sesión de Claude la pantalla se quedaba en «Preparando tu guion…» para siempre."""
    if any(t["tipo"] == "preparar" for t in _corriendo(pid)):
        return None
    ultimo = next((t for t in reversed(list(TRABAJOS.values())) if t["proyecto"] == pid and t["tipo"] == "preparar"), None)
    if ultimo and ultimo["estado"] == "error" and ultimo["log"]:
        return ultimo["log"][-1]
    return GUION_PARADO


MOTIVO_GUION_VIEJO = "El guion cambió mientras lo corregías: te muestro el de ahora."


def _editar_guion(d: dict) -> tuple[dict, int]:
    """POST /api/guion-editar {proyecto, firma, quedan: [índices]} → la corrección de la persona hecha cortes (`machote.editar_guion`).
    Con el candado del director (nunca los dos a la vez) y la firma de la transcripción que la persona estaba viendo: unos índices
    de otra transcripción no se aplican."""
    carpeta = _proyecto(d.get("proyecto", ""))
    if not (carpeta / machote.ARCHIVO).exists():
        return {"ok": False, "error": "Ese video todavía no tiene guion."}, 404
    lock = _DIRIGIENDO.setdefault(carpeta.name, threading.Lock())
    if not lock.acquire(blocking=False):
        return {"ok": False, "error": "Ya se está dirigiendo o revisando este video: espera a que termine."}, 409
    try:
        if not montaje.firma_vale(carpeta, d.get("firma")):
            return {"ok": False, "error": MOTIVO_GUION_VIEJO, "guion_nuevo": True}, 409
        try:
            return {"ok": True, "edicion": machote.editar_guion(carpeta, d.get("quedan") or [], avance=lambda m: None)}, 200
        except ValueError as e:
            return {"ok": False, "error": str(e)}, 400
    finally:
        lock.release()


def _biblioteca() -> list:
    """Lo ya editado (exportado): [{id, fecha, estilo, previa}] del más nuevo al más viejo. Lectura simple de `proyectos/`."""
    try:
        nombres = {k: v.get("nombre", k) for k, v in json.loads((LIB / "estilos" / "presets.json").read_text()).items()}
    except (OSError, ValueError):
        nombres = {}
    out = []
    for d in config.PROYECTOS.glob("*"):
        final = d / "final.mp4"
        if d.name.startswith("_") or not final.exists():
            continue
        try:
            eid = (json.loads((d / "storyboard.json").read_text()).get("estilo") or {}).get("id")
        except (OSError, ValueError):
            eid = None
        previa = next((f.name for f in sorted(d.glob("previa-a.jpg"))), None)
        out.append({"id": d.name, "fecha": time.strftime("%Y-%m-%d", time.localtime(final.stat().st_mtime)), "t": final.stat().st_mtime,
                    "estilo": nombres.get(eid, eid or ""), "previa": previa})
    out.sort(key=lambda x: x["t"], reverse=True)
    return [{k: v for k, v in x.items() if k != "t"} for x in out]


def _biblioteca_proyectos() -> list:
    """Todo lo hecho, liviano, para la barra Biblioteca de Material: un renglón por proyecto (solo exists/stat; sin storyboards ni videos).
    {id, nombre, t, fecha, duracion, estado, estilo, miniatura, videos: [{nombre, url, ruta}]}, del más nuevo al más viejo."""
    try:
        nombres = {k: v.get("nombre", k) for k, v in json.loads((LIB / "estilos" / "presets.json").read_text()).items()}
    except (OSError, ValueError):
        nombres = {}

    def leer(f: Path, tope: int = 4_000_000):
        try:
            return json.loads(f.read_text()) if f.stat().st_size <= tope else {}
        except (OSError, ValueError):
            return {}
    corriendo = {t["proyecto"] for t in TRABAJOS.values() if t["estado"] == "corriendo"}
    pro = _pro_modulo()
    out = []
    for d in config.PROYECTOS.glob("*"):
        fuente = d / "fuente.json"
        if d.name.startswith("_") or not fuente.is_file():
            continue
        meta = leer(fuente)
        orig = Path(str(meta.get("original") or "")).stem
        videos = []
        if (d / "final.mp4").is_file():
            videos.append(("Final", "final.mp4"))
        for e in sorted(d.glob("pro-*/final.mp4")) + sorted(x for x in d.glob("pro-*/pelicula.mp4") if not (x.parent / "final.mp4").exists()):
            if e.is_file():
                videos.append((f"Pro · {nombres.get(e.parent.name[4:], e.parent.name[4:])}", f"{e.parent.name}/{e.name}"))
        eid = _estilo_de(d)
        pro_activo = bool(pro and list(d.glob("pro-*/estado.json")) and pro.activo(d))   # `activo` ya descarta procesos muertos
        prefs = leer(d / "preferencias.json")
        estado = ("final" if videos else "en proceso" if d.name in corriendo or pro_activo
                  else "guion aprobado" if prefs.get("guion_aprobado") else "subido")
        previa = next((f.name for f in sorted(d.glob("previa-[ab].jpg"))), None) or next((f"arte/{f.name}" for f in sorted((d / "arte").glob("*.png"))[:1]), None)
        mach = leer(d / "machote.json")
        t = max([fuente.stat().st_mtime] + [(d / r).stat().st_mtime for _, r in videos])
        out.append({"id": d.name, "nombre": orig or d.name, "t": t, "fecha": time.strftime("%Y-%m-%d", time.localtime(t)),
                    "duracion": mach.get("duracion_s"), "estado": estado, "estilo": nombres.get(eid, eid or ""),
                    "miniatura": f"/archivo/{d.name}/{previa}" if previa else None,
                    "videos": [{"nombre": n, "url": f"/archivo/{d.name}/{r}", "ruta": r} for n, r in videos]})
    out.sort(key=lambda x: x["t"], reverse=True)
    return out


SIN_EDITAR = ("Este video todavía no está editado. Ve a «Estilo», elige uno y pulsa «Editar con este estilo»; cuando el editor "
              "termine, vuelve a Exportar.")
EDITANDO = "El editor todavía está trabajando en este video. Espera a que termine (abajo se ve el avance) y vuelve a Exportar."
EXPORTANDO = "Este video ya se está exportando. Espera a que termine."
COMPUERTA = ("La revisión de calidad no dejó exportar este diseño. Vuelve a «Estilo» y edítalo otra vez, o escribe una corrección; "
             "el detalle quedó anotado.")


def _corriendo(pid: str, salvo: str | None = None) -> list:
    """Los trabajos de ese video que siguen corriendo (sin las vistas previas, que duran segundos y no cambian el diseño)."""
    return [t for t in list(TRABAJOS.values())
            if t["proyecto"] == pid and t["estado"] == "corriendo" and t["tipo"] != "previa" and t["id"] != salvo]


def _impide_exportar(carpeta: Path, salvo: str | None = None) -> str | None:
    """Por qué este video NO se puede exportar ahora, dicho para la persona; None si se puede. Es la ÚNICA regla: la usan la pantalla
    (para apagar el botón y decir el motivo), `/api/render` (antes de lanzar nada) y el propio render. El 13-nov, en una Mac nueva, la
    pantalla dejó exportar un video que el editor aún no había diseñado (sin `storyboard.json`) y el render reventó con «Algo falló»."""
    corriendo = _corriendo(carpeta.name, salvo)
    if any(t["tipo"] == "render" for t in corriendo):
        return EXPORTANDO
    if corriendo:
        return EDITANDO
    if not (carpeta / "storyboard.json").exists():
        return SIN_EDITAR
    return None


def _render(pid, avance):
    carpeta = _proyecto(pid)
    if (motivo := _impide_exportar(carpeta, salvo=trabajo.actual())):
        raise errores.Aviso(motivo)
    try:
        return str(motor.render(carpeta, avance=lambda m: avance(m)))
    except ValueError as e:
        if not str(e).startswith(motor.COMPUERTA_NO_DEJA):
            raise
        errores.registrar("render (compuerta)", e)   # la lista completa de lo que no pasó queda en el registro
        raise errores.Aviso(COMPUERTA) from e


def _muestras_personalizar() -> dict:
    """Miniaturas de Personalizar ({"look:<id>": url, "color:sin": url}): las mismas
    muestras del seleccionador (su toma del C8866 con ese color, precalculada por `estudio muestras`). Lo que falta, no va."""
    from . import catalogo, color
    pares = [("look", l["id"]) for l in color.looks()] + [("color", "sin")]
    return {f"{c}:{o}": m for c, o in pares if (m := catalogo.muestra(c, o)) and ".jpg" in m}


def _estilo_de(carpeta: Path) -> str | None:
    """El estilo del video: el del storyboard si el director ya terminó; si no, el que se mandó a editar."""
    def leer(nombre):
        try:
            return json.loads((carpeta / nombre).read_text()) if (carpeta / nombre).exists() else {}
        except ValueError:
            return {}
    return (leer("storyboard.json").get("estilo") or {}).get("id") or leer("preferencias.json").get("estilo_elegido")


def _info(pid: str) -> dict:
    p = _proyecto(pid)
    sb = json.loads((p / "storyboard.json").read_text()) if (p / "storyboard.json").exists() else {}
    costos = [json.loads(l) for l in (p / "costos.jsonl").read_text().splitlines()] if (p / "costos.jsonl").exists() else []
    corriendo = _corriendo(pid)
    previas = sorted(x.name for x in p.glob("previa-[ab].jpg")) or sorted(f"arte/{x.name}" for x in p.glob("arte/*.png"))[:1]
    meta = json.loads((p / "fuente.json").read_text()) if (p / "fuente.json").exists() else {}
    return {"id": pid, "storyboard": sb, "listo": bool(sb) and not corriendo,
            "no_exporta": _impide_exportar(p),   # None = se puede exportar; si no, el motivo que la pantalla muestra junto al botón
            "guion_aprobado": machote.guion_aprobado(p),   # lo que habilita Estilos Pro (no usa el director normal: parte del machote)
            "final": (p / "final.mp4").exists(), "previas": previas, "estilo_elegido": _estilo_de(p),
            "usd": round(sum(c.get("usd_equivalente") or 0 for c in costos), 2),
            "arte": len(list((p / "arte").glob("*.png"))) if (p / "arte").exists() else 0,
            "trabajo": corriendo[-1]["id"] if corriendo else None}


def _pro_modulo():
    """El motor Pro (estudio/pro.py) se importa al usarlo: la app arranca aunque esta rama aún no lo traiga."""
    import importlib
    try:
        return importlib.import_module(f"{__package__}.pro")
    except ModuleNotFoundError as e:
        if e.name != f"{__package__}.pro":
            raise
        return None


def _pro_catalogo() -> dict:
    """El catálogo Pro para la app: las rutas de archivo se cambian por las URLs de /pro-media y se suma el aviso de tiempo y consumo."""
    from . import pro_catalogo
    estilos = [{**{k: v for k, v in e.items() if k not in ("poster", "muestra")}, "poster": f"/pro-media/{e['slug']}/poster",
                "muestra": f"/pro-media/{e['slug']}/muestra" if e["muestra"] else None} for e in pro_catalogo.catalogo()]
    pro = _pro_modulo()   # `motor`: si aquí se puede editar con ellos o solo verlos (la pantalla lo dice antes de dejar elegir)
    return {"ok": True, "estilos": estilos, "aviso": pro_catalogo.aviso(), "motor": bool(pro and pro.motor_instalado())}


class Manejador(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, obj, codigo=200):
        b = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def _archivo(self, ruta: Path, cache: int = 0):
        """`cache` (segundos): solo para lo que se pide con su versión en la URL (muestras ?v=, fuentes); lo demás, no-store."""
        if not ruta.is_file():
            return self._json({"ok": False, "error": "no existe"}, 404)
        total = ruta.stat().st_size
        rango = self.headers.get("Range", "")
        ini, fin = 0, total - 1
        if rango.startswith("bytes="):   # el navegador pide trozos para poder adelantar/retroceder un video
            a, _, b = rango[6:].split(",")[0].partition("-")
            ini, fin = (int(a), int(b) if b else total - 1) if a else (max(0, total - int(b)), total - 1)
            fin = min(fin, total - 1)
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {ini}-{fin}/{total}")
        else:
            self.send_response(200)
        self.send_header("Content-Type", mimetypes.guess_type(ruta.name)[0] or "application/octet-stream")
        self.send_header("Content-Length", str(fin - ini + 1))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Cache-Control", f"public, max-age={cache}" if cache else "no-store")
        self.end_headers()
        with open(ruta, "rb") as f:
            f.seek(ini)
            restante = fin - ini + 1
            try:
                while restante:
                    b = f.read(min(1 << 20, restante))
                    if not b:
                        break
                    self.wfile.write(b)
                    restante -= len(b)
            except (BrokenPipeError, ConnectionResetError):
                pass

    def _cuerpo(self):
        n = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(n) or b"{}")

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        partes = [urllib.parse.unquote(x) for x in u.path.strip("/").split("/") if x]
        if any(x in ("..", ".") or "/" in x or "\\" in x for x in partes):
            return self._json({"ok": False, "error": "ruta inválida"}, 404)
        try:
            if not partes:
                return self._archivo(APP / "index.html")
            if partes[0] == "app":
                return self._archivo(APP.joinpath(*partes[1:]), cache=86400 if partes[1:2] == ["muestras"] and u.query else 0)
            if partes[0] == "taller":
                return self._archivo(APP / "taller.html")
            if partes[0] == "revision":
                return self._archivo(APP / "revision.html")
            if partes[0] == "seleccionador":
                return self._archivo(APP / "seleccionador.html")
            if partes[:2] == ["api", "catalogo"]:
                return self._json({"ok": True, **catalogo.catalogo_cacheado()})
            if partes[:3] == ["api", "pro", "catalogo"]:
                return self._json(_pro_catalogo())
            if partes[:3] == ["api", "pro", "estado"]:
                pro = _pro_modulo()
                if pro is None:
                    return self._json({"ok": False, "error": "Estilos Pro todavía no está instalado en esta copia del estudio."}, 503)
                q = urllib.parse.parse_qs(u.query)
                from . import pro_catalogo
                slug = (q.get("estilo") or [""])[0]
                if not pro_catalogo.por_slug(slug):
                    return self._json({"ok": False, "error": "Ese estilo Pro no existe."}, 404)
                return self._json({"ok": True, **pro.estado(_proyecto((q.get("proyecto") or [""])[0]), slug)})
            if partes[0] == "pro-media" and len(partes) == 3 and partes[2] in ("poster", "muestra"):
                from . import pro_catalogo
                e = pro_catalogo.por_slug(partes[1])
                return self._archivo(Path(e[partes[2]])) if e and e[partes[2]] else self._json({"ok": False, "error": "no existe"}, 404)
            if partes[:3] == ["api", "biblioteca", "proyectos"]:
                return self._json({"ok": True, "proyectos": _biblioteca_proyectos()})
            if partes[:2] == ["api", "biblioteca"]:
                return self._json({"ok": True, "videos": _biblioteca()})
            if partes[:2] == ["api", "guion"]:
                g = _guion(_proyecto(partes[2]))
                if not g["listo"] and (parado := _guion_parado(partes[2])):
                    g["parado"] = parado   # nadie lo está preparando: la pantalla lo dice y ofrece reintentar (no un «Preparando…» eterno)
                return self._json({"ok": True, **g})
            if partes[:2] == ["api", "seleccion"]:
                p = _proyecto(partes[2])
                return self._json({"ok": True, "preferencias": catalogo.leer(p),
                                   "storyboard": (p / "storyboard.json").exists()})
            if partes[0] == "revision-archivo":
                from . import revision
                return self._archivo(revision.CARPETA / Path(partes[1]).name)
            if partes[:2] == ["api", "revision"]:
                from . import revision
                return self._json({"ok": True, "estilos": revision.lista()})
            if partes[0] == "ref":   # videos y cuadros de los referentes bajados (no van a git)
                from . import referentes
                return self._archivo(referentes.RAIZ.joinpath(*partes[1:]))
            if partes[:2] == ["api", "taller"]:
                from . import referentes
                e = partes[2]
                info = {r[0]: r for r in json.loads((referentes.DB / "referencias.json").read_text()).get(e, {}).get("refs", [])}
                duennos = set(json.loads((referentes.DB / "referencias.json").read_text()).get(e, {}).get("del_duenno", []))
                refs = []
                for c in referentes.codigos(e):
                    d = referentes.RAIZ / e / c
                    fotos = sorted(d.glob("t_*.jpg")) if d.exists() else []
                    if not fotos:
                        continue
                    r = info.get(c, [c])
                    refs.append({"codigo": c, "cuenta": r[2] if len(r) > 2 and r[2] != "dueño" else "",
                                 "que": r[3] if len(r) > 3 else "", "duenno": c in duennos or "dueño" in str(r) or "tu referencia" in str(r),
                                 "video": f"/ref/{e}/{c}.mp4" if (referentes.RAIZ / e / f"{c}.mp4").exists() else "",
                                 "cuadros": [{"t": float(f.stem[2:]), "src": f"/ref/{e}/{c}/{f.name}"} for f in fotos]})
                refs.sort(key=lambda r: not r["duenno"])
                return self._json({"ok": True, "refs": refs, "total": len(referentes.codigos(e)), "gustos": referentes.gustos(e), "notas": referentes.notas_reel(e),
                                   "aspectos": referentes.ASPECTOS, "vocabulario": referentes.VOCABULARIO})
            if partes[0] == "rapida":
                return self._archivo(rapida.carpeta_de(Path(partes[1]).name) / Path(partes[2]).name)
            if partes[0] == "archivo":
                return self._archivo(_proyecto(partes[1]).joinpath(*partes[2:]))
            if partes[:2] == ["api", "proyectos"]:
                ps = sorted((d for d in config.PROYECTOS.glob("*") if (d / "fuente.json").exists()),
                            key=lambda d: d.stat().st_mtime, reverse=True)
                if "ligero" in urllib.parse.parse_qs(u.query):   # solo los nombres (el seleccionador no necesita los storyboards)
                    return self._json({"ok": True, "proyectos": [{"id": d.name} for d in ps]})
                return self._json({"ok": True, "proyectos": [_info(d.name) for d in ps]})
            if partes[:2] == ["api", "proyecto"]:
                return self._json({"ok": True, **_info(partes[2])})
            if partes[:2] == ["api", "tanda"]:
                from . import reparto
                t = reparto.leer(partes[2])
                en_curso = _tanda_en_curso(t["id"])
                return self._json({"ok": True, "tanda": reparto.vista(t), "trabajo": en_curso["id"] if en_curso else None,
                                   "paso": next((l for l in reversed(en_curso["log"])), "") if en_curso else ""})
            if partes[:2] == ["api", "actividad"]:
                # `raiz`: qué copia contesta · `claude`: "ok", "sin_sesion" o "falta" (la barra lo avisa antes de que algo falle)
                return self._json({"ok": True, "trabajos": _actividad(), "raiz": str(config.RAIZ), "claude": sesion.estado()})
            if partes[:2] == ["api", "trabajo"]:
                return self._json({"ok": True, **TRABAJOS.get(partes[2], {"estado": "desconocido", "log": []})})
            if partes[:2] == ["api", "librerias"]:
                fuentes = json.loads((LIB / "fuentes" / "indice.json").read_text())
                return self._json({"ok": True, "estilos": json.loads((LIB / "estilos" / "presets.json").read_text()),
                                   "aprobados": catalogo.en_pantalla(),   # lo que se ve en Estilos, en su orden (una sola lista)
                                   "tope_imagenes": {"defecto": config.TOPE_IMAGENES, "paso": config.TOPE_IMAGENES_PASO},
                                   "fuentes": {k: v["nota"] for k, v in fuentes.items()},
                                   "muestras": _muestras_personalizar()})
            if partes[:2] == ["api", "fuente"]:   # el archivo de una tipografía, para pintar «Aa» con ella en la UI
                fuentes = json.loads((LIB / "fuentes" / "indice.json").read_text())
                return self._archivo(LIB / "fuentes" / fuentes[partes[2]]["regular" if partes[3:] == ["regular"] else "italica"], cache=86400)
            if partes[:2] == ["api", "aprendizajes"]:
                return self._json({"ok": True, "aprendizajes": agente.aprendizajes()})
            return self._json({"ok": False, "error": "ruta desconocida"}, 404)
        except Exception as e:  # noqa: BLE001
            return self._json({"ok": False, "error": errores.amable(self.path, e)}, 500)

    def do_POST(self):
        u = urllib.parse.urlparse(self.path)
        partes = [urllib.parse.unquote(x) for x in u.path.strip("/").split("/") if x]
        try:
            if partes[:2] == ["api", "subir"]:
                nombre = Path(urllib.parse.parse_qs(u.query)["nombre"][0]).name
                destino = config.PROYECTOS / "_subidas" / nombre
                destino.parent.mkdir(parents=True, exist_ok=True)
                parte = destino.with_name(f".{nombre}.subiendo")   # a un lado: otro video con el mismo nombre no pisa el original de un proyecto
                restante = int(self.headers["Content-Length"])
                with open(parte, "wb") as f:
                    while restante:
                        b = self.rfile.read(min(1 << 20, restante))
                        if not b:
                            break
                        f.write(b)
                        restante -= len(b)
                if restante:
                    parte.unlink(missing_ok=True)
                    return self._json({"ok": False, "error": "La subida se cortó. Súbelo otra vez."}, 400)
                from . import ingesta
                h = ingesta.huella(parte)
                if destino.exists() and ingesta.huella(destino) != h:
                    destino = destino.with_name(f"{destino.stem}-{h[:6]}{destino.suffix}")
                parte.replace(destino)
                return self._json({"ok": True, "video": str(destino)})
            d = self._cuerpo()
            if partes[:2] == ["api", "preparar"]:
                from . import ingesta
                if d.get("reintentar"):   # el mismo proyecto, desde donde quedó (lo ya hecho se reusa: transcripción, video normalizado)
                    carpeta = _proyecto(d.get("proyecto", ""))
                    en_curso = next((t for t in _corriendo(carpeta.name) if t["tipo"] == "preparar"), None)
                    if en_curso:
                        return self._json({"ok": True, "trabajo": en_curso["id"], "proyecto": carpeta.name, "ya_estaba": True})
                    try:
                        original = json.loads((carpeta / "fuente.json").read_text()).get("original")
                    except (OSError, ValueError):
                        original = None
                    if not original or not Path(original).is_file():
                        return self._json({"ok": False, "error": SIN_ORIGINAL}, 409)
                    tid = _trabajo("preparar", _preparar, original, carpeta.name, proyecto=carpeta.name)
                    return self._json({"ok": True, "trabajo": tid, "proyecto": carpeta.name, "ya_estaba": True})
                base = Path(d.get("nombre") or Path(d["video"]).stem.lower().replace(" ", "-")).name
                nombre, ya_estaba = ingesta.proyecto_para(Path(d["video"]), base, de_cero=bool(d.get("de_cero")))
                tid = _trabajo("preparar", _preparar, d["video"], nombre, proyecto=nombre)
                return self._json({"ok": True, "trabajo": tid, "proyecto": nombre, "ya_estaba": ya_estaba})
            if partes[:2] == ["api", "tanda"]:   # una grabación en muchos archivos: transcribir y proponer cuántos videos salen
                from . import reparto
                videos = d.get("videos")
                if not isinstance(videos, list) or not videos or not all(isinstance(v, str) and v for v in videos):
                    return self._json({"ok": False, "error": "No hay archivos para repartir."}, 400)
                t = reparto.crear(_en_subidas(videos))
                tid = _trabajo("tanda", _tanda_analizar, t["id"])
                TRABAJOS[tid]["tanda"] = t["id"]
                return self._json({"ok": True, "tanda": t["id"], "trabajo": tid})
            if partes[:2] == ["api", "tanda-seguir"]:   # la app se cerró o algo falló a la mitad: sigue donde iba (lo transcrito no se repite)
                from . import reparto
                t = reparto.leer(d.get("tanda", ""))
                en_curso = _tanda_en_curso(t["id"])
                if not en_curso:
                    tipo, fn = ("tanda-preparar", _tanda_preparar) if t["estado"] in ("preparando", "lista") else ("tanda", _tanda_analizar)
                    tid = _trabajo(tipo, fn, t["id"])
                    TRABAJOS[tid]["tanda"] = t["id"]
                return self._json({"ok": True, "trabajo": en_curso["id"] if en_curso else tid})
            if partes[:2] == ["api", "tanda-propuesta"]:   # lo que la persona movió: se guarda lo que deja la compuerta
                from . import reparto
                t = reparto.proponer(d.get("tanda", ""), {"videos": d.get("videos"), "sobran": d.get("sobran")})
                return self._json({"ok": True, "tanda": reparto.vista(t)})
            if partes[:2] == ["api", "tanda-aprobar"]:
                from . import reparto
                t = reparto.leer(d.get("tanda", ""))
                en_curso = _tanda_en_curso(t["id"])
                if en_curso:
                    return self._json({"ok": True, "trabajo": en_curso["id"]})
                if not (t.get("propuesta") or {}).get("videos"):
                    return self._json({"ok": False, "error": "Esta tanda todavía no tiene una propuesta de videos."}, 409)
                tid = _trabajo("tanda-preparar", _tanda_preparar, t["id"])
                TRABAJOS[tid]["tanda"] = t["id"]
                return self._json({"ok": True, "trabajo": tid})
            if partes[:2] == ["api", "unir"]:   # un video grabado en varias partes: se unen en uno antes de preparar
                videos = d.get("videos")
                if not isinstance(videos, list) or len(videos) < 2 or not all(isinstance(v, str) and v for v in videos):
                    return self._json({"ok": False, "error": "Para unir hacen falta al menos dos partes."}, 400)
                return self._json({"ok": True, "trabajo": _trabajo("unir", _unir, videos)})
            if partes[:2] == ["api", "detener"]:
                t = TRABAJOS.get(d.get("trabajo"))
                if not t or t["estado"] != "corriendo":
                    return self._json({"ok": False, "error": "Eso ya no está corriendo."}, 404)
                trabajo.detener(t["id"])
                return self._json({"ok": True})
            if partes[:2] == ["api", "guion-editar"]:
                return self._json(*_editar_guion(d))
            if partes[:2] == ["api", "dirigir"]:
                pid = _proyecto(d.get("proyecto", "")).name
                from . import lemo_apoyos
                pedido = str(d.get("estilo") or "")
                if pedido.startswith(lemo_apoyos.ESTILO + ":"):   # un Estilo Pro: el reel de siempre con los apoyos de Lemo
                    from . import pro_catalogo
                    pro = _pro_modulo()
                    if not (pro and pro.motor_instalado()):
                        return self._json({"ok": False, "error": "Los Estilos Pro necesitan el motor de Lemo y esta máquina no lo tiene."}, 409)
                    if not pro_catalogo.por_slug(pedido.split(":", 1)[1]):
                        return self._json({"ok": False, "error": "Ese estilo Pro no existe."}, 404)
                elif pedido == lemo_apoyos.ESTILO or pedido not in json.loads((LIB / "estilos" / "presets.json").read_text()):
                    return self._json({"ok": False, "error": "Ese estilo no existe."}, 404)
                if not machote.guion_aprobado(_proyecto(pid)):
                    return self._json({"ok": False, "error": MOTIVO_SIN_APROBAR}, 409)
                if (largo := _impedimento(_proyecto(pid))):
                    return self._json({"ok": False, "error": largo, "guion_nuevo": largo.startswith(machote.MENSAJE_GUION_NUEVO)}, 409)
                if d.get("confirmado") is not True:   # elegir una tarjeta no gasta: el director (Opus + imágenes) solo corre con la orden explícita
                    return self._json({"ok": False, "error": MOTIVO_SIN_CONFIRMAR}, 409)
                token = _PEDIDO[pid] = time.time_ns()
                return self._json({"ok": True, "proyecto": pid, "trabajo": _trabajo(
                    "dirigir", _dirigir, pid, d["estilo"], d.get("imagenes", True), d.get("densidad", "normal"), token, proyecto=pid)})
            if partes[:3] == ["api", "pro", "lanzar"]:
                pro = _pro_modulo()
                if pro is None:
                    return self._json({"ok": False, "error": "Estilos Pro todavía no está instalado en esta copia del estudio."}, 503)
                from . import pro_catalogo
                carpeta = _proyecto(d.get("proyecto", ""))
                if not carpeta.exists():
                    return self._json({"ok": False, "error": "Primero sube un video."}, 404)
                if not pro_catalogo.por_slug(d.get("estilo", "")):
                    return self._json({"ok": False, "error": "Ese estilo Pro no existe."}, 404)
                if not machote.guion_aprobado(carpeta):   # misma regla que /api/dirigir: nada se dirige sin guion aprobado
                    return self._json({"ok": False, "error": MOTIVO_SIN_APROBAR}, 409)
                if (largo := _impedimento(carpeta)):   # mismo tope que /api/dirigir, antes de gastar nada
                    return self._json({"ok": False, "error": largo, "guion_nuevo": largo.startswith(machote.MENSAJE_GUION_NUEVO)}, 409)
                return self._json({"ok": True, "carpeta": str(pro.lanzar(carpeta, d["estilo"]))})
            if partes[:2] == ["api", "previa-rapida"]:
                nombre = Path(d.get("nombre") or "").name
                video = d.get("video")
                f = config.PROYECTOS / Path(d.get("proyecto") or nombre).name / "fuente.json"
                if f.exists():
                    meta = json.loads(f.read_text())
                    if not video and d.get("proyecto"):
                        video = meta.get("video")   # ya normalizada por la ingesta: se corta al instante
                if not video and nombre and f.exists():   # aún se está preparando: la toma sale del archivo que se subió
                    video = meta.get("original")
                if not nombre or not video:
                    return self._json({"ok": False, "error": "primero sube un video"})

                estilo = dict(d.get("estilo") or {})
                if not estilo.get("id") and d.get("proyecto"):   # la pantalla no sabe el estilo (se recargó): el proyecto sí
                    estilo["id"] = _estilo_de(_proyecto(d["proyecto"]))

                def generar(avance, vigente):
                    rapida.preparar(Path(video), nombre)
                    return previas.con_toma(rapida.carpeta_de(nombre), estilo, avance, vigente)
                return self._json({"ok": True, "trabajo": _pedir_previa(f"rapida/{nombre}", f"/rapida/{nombre}/", generar)})
            if partes[:2] == ["api", "estilo-guardar"]:   # lo que la persona tocó en Personalizar, al storyboard (solo esas claves)
                carpeta = _proyecto(d["proyecto"])
                if not (carpeta / "storyboard.json").exists():
                    return self._json({"ok": False, "error": "ese video todavía no está editado"}, 404)
                with previas._candado(carpeta):
                    _guardar_estilo(carpeta, d.get("estilo") or {})
                return self._json({"ok": True})
            if partes[:2] == ["api", "previa"]:
                carpeta = _proyecto(d["proyecto"])
                guardar = d.get("guardar", True) is not False   # Edición avanzada ve sin comprometer: guardar=false
                return self._json({"ok": True, "trabajo": _pedir_previa(
                    f"proyecto/{carpeta.name}", f"/archivo/{carpeta.name}/",
                    lambda avance, vigente: previas.con_director(carpeta, d["estilo"], _guardar_estilo if guardar else None, avance, vigente), proyecto=d["proyecto"])})
            if partes[:2] == ["api", "render"]:
                carpeta = _proyecto(d["proyecto"])
                if (motivo := _impide_exportar(carpeta)):   # sin diseño, o con el editor a medias: se dice el motivo y no se lanza nada
                    return self._json({"ok": False, "error": motivo}, 409)
                if d.get("estilo") and (carpeta / "storyboard.json").exists():   # lo que la persona cambió y aún no se guardó, antes de render
                    with previas._candado(carpeta):   # el mismo candado con que una vista guarda
                        _guardar_estilo(carpeta, d["estilo"])
                return self._json({"ok": True, "trabajo": _trabajo("render", _render, carpeta.name, proyecto=carpeta.name)})
            if partes[:2] == ["api", "corregir"]:
                if capas_activas() and d.get("proyecto"):   # editor por capas: primero la corrección exacta; si no es de capa, el agente de siempre
                    return self._json({"ok": True, "trabajo": _trabajo("corregir", _corregir_capas, d["texto"], d["proyecto"], d.get("segundo"),
                                                                        proyecto=d["proyecto"])})
                return self._json({"ok": True, "trabajo": _trabajo("corregir", agente.corregir, d["texto"], d.get("proyecto"),
                                                                    proyecto=d.get("proyecto"))})
            if partes[:2] == ["api", "crear-estilo"]:
                from . import estilista
                return self._json({"ok": True, "trabajo": _trabajo("crear-estilo", estilista.crear, d["estilo"], d.get("links", []),
                                                                    d.get("idea", ""), d.get("buscar", True), d.get("clip"))})
            if partes[:2] == ["api", "gusto"]:
                from . import referentes
                return self._json({"ok": True, "gustos": referentes.marcar(d["estilo"], d["ref"], float(d["t"]), d.get("nota", ""), d.get("me_gusta"),
                                                                            d.get("aspectos", []), d.get("caja"), d.get("cuanto", "me gusta"),
                                                                            d.get("terminos", []))})
            if partes[:2] == ["api", "revision-corregir"]:
                from . import revision
                if not d.get("texto", "").strip():
                    return self._json({"ok": False, "error": "escribe qué corregir"})
                return self._json({"ok": True, "trabajo": _trabajo("corregir-revision", revision.corregir, d["estilo"], d["texto"], d.get("segundo"),
                                                                    proyecto=d["estilo"])})
            if partes[:2] == ["api", "revision"]:
                from . import revision
                return self._json({"ok": True, "notas": revision.anotar(d["estilo"], d.get("texto", ""), d.get("segundo"), d.get("aprueba", False))})
            if partes[:2] == ["api", "nota-reel"]:
                from . import referentes
                return self._json({"ok": True, "notas": referentes.nota_reel(d["estilo"], d["ref"], d.get("nota", ""))})
            if partes[:2] == ["api", "fuentes-buscar"]:
                from . import fuentes as gf
                return self._json({"ok": True, "fuentes": gf.buscar(d.get("texto", ""), d.get("categoria", ""), 24)})
            if partes[:2] == ["api", "fuente-instalar"]:
                from . import fuentes as gf
                return self._json({"ok": True, "ficha": gf.instalar(d["familia"])})
            if partes[:2] == ["api", "seleccion"]:
                p = _proyecto(d["proyecto"])
                if not (p / "fuente.json").exists():
                    return self._json({"ok": False, "error": "ese proyecto no existe"}, 404)
                if d.get("guion_aprobado") is True and d.get("con_detalles") is True:   # la persona vio los detalles señalados y aprueba así
                    machote.aceptar_detalles(p)
                if d.get("guion_aprobado") is True and (largo := _impedimento(p)):
                    return self._json({"ok": False, "error": largo, "guion_nuevo": largo.startswith(machote.MENSAJE_GUION_NUEVO)}, 409)
                try:
                    return self._json({"ok": True, **catalogo.guardar(p, d)})
                except ValueError as e:
                    return self._json({"ok": False, "error": str(e)}, 400)
            if partes[:2] == ["api", "deshacer"]:
                return self._json(agente.deshacer(d["id"]))
            if partes[:2] == ["api", "claude-entrar"]:   # abre la terminal con el inicio de sesión de Claude (equipo nuevo)
                if sesion.entrar():
                    return self._json({"ok": True})
                return self._json({"ok": False, "error": errores.SIN_CLAUDE if not config.claude_cmd() else errores.SIN_SESION}, 409)
            if partes[:2] == ["api", "finder"]:
                final = _proyecto(d["proyecto"]) / "final.mp4"
                if d.get("archivo"):   # un video de la Biblioteca (p. ej. pro-<estilo>/final.mp4): dentro del proyecto, nunca fuera
                    raiz = _proyecto(d["proyecto"]).resolve()
                    final = (raiz / d["archivo"]).resolve()
                    if raiz not in final.parents:
                        return self._json({"ok": False, "error": "ruta inválida"}, 404)
                if sys.platform == "darwin":
                    subprocess.run(["open", "-R", str(final)])
                elif sys.platform == "win32":
                    subprocess.run(["explorer", "/select,", str(final)])
                return self._json({"ok": True})
            return self._json({"ok": False, "error": "ruta desconocida"}, 404)
        except Exception as e:  # noqa: BLE001
            return self._json({"ok": False, "error": errores.amable(self.path, e)}, 500)


NAVEGADORES_MAC = ("Google Chrome", "Microsoft Edge", "Brave Browser", "Chromium")   # los que saben abrir una página como app (--app)


def _hay_app_mac(nombre: str) -> bool:
    return any((raiz / f"{nombre}.app").exists() for raiz in (Path("/Applications"), Path.home() / "Applications"))


def orden_ventana(url: str, plataforma: str = sys.platform, hay=_hay_app_mac) -> list | None:
    """La orden que abre Pro Studio como app de escritorio (ventana propia, sin pestañas ni barra de direcciones), o None si en esta
    máquina no hay con qué (entonces se abre en el navegador normal). En Mac no existía (Pablo, 11-nov: «¿por qué no abre como una
    app de escritorio sino como una página web toda rara?»): se intentaba la orden de Windows y caía siempre al navegador."""
    if plataforma == "darwin":
        app = next((n for n in NAVEGADORES_MAC if hay(n)), None)
        return ["open", "-na", app, "--args", f"--app={url}", "--window-size=1600,1000"] if app else None
    return ["cmd.exe", "/c", "start", "chrome", f"--app={url}", "--window-size=1600,1000"]


def _quien_sirve(url: str) -> str | None:
    """Quién tiene el puerto: "esta" (este mismo Pro Studio, ya abierto), "otra" (otra copia u otro programa) o None (nadie contesta).
    Se reconoce por la carpeta que el servidor dice ser. Antes bastaba con que algo contestara: el 11-nov una copia vieja del estudio
    (otro icono, misma dirección) estaba abierta y la ventana nueva se pegó a ella sin avisar: Pablo usó la versión vieja toda la noche
    («en edición Pro no muestra las miniaturas»: ya estaba arreglado, pero no en la copia que tenía delante)."""
    try:
        with urllib.request.urlopen(f"{url}/api/actividad", timeout=2) as r:
            return "esta" if json.loads(r.read()).get("raiz") == str(config.RAIZ) else "otra"
    except urllib.error.HTTPError:
        return "otra"      # contesta, pero no es esta versión
    except (OSError, ValueError):
        return None


OTRA_ABIERTA = ("Hay otra versión de Pro Studio abierta en esta máquina y ocupa su lugar. Ciérrala (o reinicia el equipo) y vuelve a abrir "
                "Pro Studio.")


def _trabajando() -> list[str]:
    return [f"{t['que']} ({t['proyecto']})" if t["proyecto"] else t["que"] for t in _actividad()]


class Servidor(ThreadingHTTPServer):
    """En Windows SO_REUSEADDR deja enlazar el mismo puerto dos veces (dos Pro Studio a la vez, cada uno con la mitad de las
    peticiones): ahí el puerto se toma en exclusiva. En Mac y Linux se deja como estaba."""
    allow_reuse_address = os.name != "nt"

    def server_bind(self):
        if os.name == "nt":
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


def _abrir_ventana(url: str) -> None:
    """Ventana tipo app con Chrome; en Windows, sin Chrome se prueba Edge (viene con el sistema); si no, el navegador por defecto."""
    orden = orden_ventana(url)
    candidatas = [orden] if orden else []
    if orden and sys.platform == "win32":
        candidatas.append([*orden[:3], "msedge", *orden[4:]])
    for c in candidatas:
        try:
            if subprocess.run(c, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
                return
        except OSError:
            pass
    webbrowser.open(url)


def servir(abrir=True):
    from . import ventana
    url = f"http://127.0.0.1:{PUERTO}"
    srv = None
    quien = _quien_sirve(url)   # primero se pregunta quién tiene el puerto: enlazar a ciegas no basta en Windows
    if quien is None:
        try:
            srv = Servidor(("127.0.0.1", PUERTO), Manejador)
        except OSError:
            quien = _quien_sirve(url)   # alguien lo tomó justo ahora
            if quien is None:
                raise
    if quien == "otra":   # nunca pegarse en silencio a otra copia: se dice y no se abre
        if abrir and ventana.disponible():
            ventana.avisar(OTRA_ABIERTA)
        raise SystemExit(OTRA_ABIERTA)
    # quien == "esta": este mismo Pro Studio ya está sirviendo (otra ventana, o arrancado sin ventana): solo se abre la ventana sobre él
    print(f"Pro Studio en {url}")
    if abrir and ventana.disponible():   # Mac: ventana propia; al cerrarla se cierra la app y se detiene lo que corría
        if srv:
            threading.Thread(target=srv.serve_forever, daemon=True).start()
        ventana.abrir(url, _trabajando if srv else lambda: [])
        for t in (_actividad() if srv else []):
            trabajo.detener(t["id"])
        return
    if abrir:
        _abrir_ventana(url)
    if srv:
        srv.serve_forever()
