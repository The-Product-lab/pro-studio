"""`estudio autoprueba`: recorre en ESTA instalación el camino entero de la app, por su API real y con el mismo servidor que usa la
ventana (subir en dos partes → unirlas → preparar → guion → exportar sin editar → aprobar → editar → exportar → descargar), y
comprueba el video final. Después, una grabación en 4 archivos (docs/PLANO-LOTE.md): se revisan, se propone cuántos videos salen (sin
IA: reparto por código), se junta un video como lo haría la persona, se aprueba y queda preparado con su guion.

Nació el 13-nov: en una Mac recién instalada «Exportar» decía «Algo falló» y la prueba de instalación limpia de entonces no llegaba
hasta ahí. Sin argumentos no gasta IA ni necesita la sesión de Claude: fabrica un video corto en DOS partes distintas (otro tamaño,
otros cuadros por segundo, otro sonido) que la app une como las de un video grabado por pedazos, trae sus palabras ya escritas (no
transcribe), corta solo con código y edita con el estilo Básico (sin director); lo demás (normalizar, ubicar a la persona, guion,
compuerta, render por tramos, sonido) es el motor de verdad. Con `--video` usa un video tuyo y transcribe; con `--estilo` y `--con-ia`
corre también el director. Sale 0 si todo pasó; si no, dice el paso, la frase que vería la persona y el detalle del registro.
La corre `tests/test_autoprueba.py` (compuerta) y se puede correr a mano en cualquier equipo recién instalado."""
import json
import os
import shutil
import subprocess
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from . import config

BASE = "autoprueba"
SEGUNDOS = 6
PALABRAS = "esta es la prueba de exportar de pro studio y tiene que salir completa".split()


class Fallo(Exception):
    """Un paso de la autoprueba no salió como debía."""


def _partes_de_prueba(carpeta: Path) -> list[Path]:
    """Un video corto grabado «en dos partes» que NO vienen listas ni iguales: la 1 horizontal a 25 cuadros con sonido mono a 48 kHz;
    la 2 vertical, más chica, a 30 cuadros y con sonido estéreo a 44,1 kHz. Unirlas obliga a igualar tamaño, cuadros y sonido; después
    hay que normalizar. (La parte SIN sonido la cubre tests/test_unir.py: aquí las dos suenan para que el guion conserve todo el video.)"""
    ffmpeg, _ = config.ffmpeg()
    mitad = SEGUNDOS / 2
    uno, dos = carpeta / f".{BASE}-parte-1.mp4", carpeta / f".{BASE}-parte-2.mp4"
    subprocess.run([ffmpeg, "-v", "error", "-y", "-f", "lavfi", "-i", f"testsrc2=size=1280x720:rate=25:d={mitad}",
                    "-f", "lavfi", "-i", f"sine=frequency=220:duration={mitad}", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-ac", "1", "-ar", "48000", "-shortest", str(uno)], check=True)
    subprocess.run([ffmpeg, "-v", "error", "-y", "-f", "lavfi", "-i", f"testsrc=size=540x960:rate=30:d={mitad}",
                    "-f", "lavfi", "-i", f"sine=frequency=330:duration={mitad}", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-ac", "2", "-ar", "44100", "-shortest", str(dos)], check=True)
    return [uno, dos]


def _palabras() -> list:
    paso = (SEGUNDOS - .6) / len(PALABRAS)
    return [{"w": w, "s": round(.3 + i * paso, 2), "e": round(.3 + (i + .8) * paso, 2), "p": .99} for i, w in enumerate(PALABRAS)]


def _limpiar() -> None:
    for d in config.PROYECTOS.glob(f"{BASE}*"):
        if d.is_dir() and not d.is_symlink():
            shutil.rmtree(d, ignore_errors=True)
    for f in [*(config.PROYECTOS / "_subidas").glob(f"{BASE}*"), *config.PROYECTOS.glob(f".{BASE}-parte-*.mp4")]:
        f.unlink(missing_ok=True)
    for ficha in (config.PROYECTOS / "_tandas").glob("*/tanda.json"):   # las tandas de la autoprueba (sus archivos se llaman autoprueba-…)
        try:
            propia = all(a["nombre"].startswith(BASE) for a in json.loads(ficha.read_text(encoding="utf-8"))["archivos"])
        except (OSError, ValueError, KeyError):
            continue
        if propia:
            for f in (config.PROYECTOS / "_subidas").glob(f"{ficha.parent.name}-*"):
                f.unlink(missing_ok=True)
            shutil.rmtree(ficha.parent, ignore_errors=True)


LOTE = [("lote-1", "hoy te cuento como grabar mejor tus videos"),          # una idea…
        ("lote-2", "el primer truco es mirar siempre al lente"),           # …su continuación, primera toma
        ("lote-3", "el primer truco es mirar siempre al lente"),           # la misma toma repetida: queda esta, la última
        ("lote-4", "")]                                                    # un archivo sin voz


def _recorrer_lote(api, esperar, debe) -> None:
    """Una grabación en 4 archivos (docs/PLANO-LOTE.md) por la API de la app: se suben, se «transcriben» en serie (las palabras vienen
    escritas: sin Whisper), el reparto por código propone (sin IA), la persona junta dos videos, aprueba, y el video queda preparado
    con su guion. Comprueba lo que nunca debe pasar: que un archivo se pierda sin decirlo."""
    from . import ingesta, reparto
    ffmpeg, _ = config.ffmpeg()
    dichos, subidos = {}, []
    for nombre, texto in LOTE:
        tmp = config.PROYECTOS / f".{BASE}-parte-{nombre}.mp4"
        subprocess.run([ffmpeg, "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=640x360:rate=30:d=4", "-f", "lavfi", "-i",
                        "sine=frequency=260:duration=4", "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "aac",
                        "-shortest", str(tmp)], check=True)
        r = api(f"/api/subir?nombre={urllib.parse.quote(f'{BASE}-{nombre}.mp4')}", crudo=tmp.read_bytes())
        tmp.unlink(missing_ok=True)
        debe(r.get("ok"), f"lote: subir {nombre}", r)
        subidos.append(r["video"])
        ws = texto.split()
        dichos[Path(r["video"]).name] = [{"w": w, "s": round(.3 + i * .4, 2), "e": round(.6 + i * .4, 2), "p": .99} for i, w in enumerate(ws)]
    whisper = ingesta.transcribir

    def escrito(video, destino):   # las palabras de cada archivo del lote; lo demás, el Whisper de verdad
        if Path(video).name not in dichos:
            return whisper(video, destino)
        Path(destino).write_text(json.dumps(dichos[Path(video).name], ensure_ascii=False), encoding="utf-8")
        return dichos[Path(video).name]
    ingesta.transcribir = escrito
    try:
        r = api("/api/tanda", {"videos": subidos})
        debe(r.get("ok") and r.get("tanda"), "lote: empezar a revisar los 4 archivos", r)
        tid = r["tanda"]
        esperar(r["trabajo"], "lote: transcribir y proponer")
    finally:
        ingesta.transcribir = whisper
    t = api(f"/api/tanda/{tid}")["tanda"]
    p = t["propuesta"]
    ids = {a["nombre"].removeprefix(f"{BASE}-").removesuffix(".mp4"): a["id"] for a in t["archivos"]}
    motivos = {x["archivo"]: x["motivo"] for x in p["sobran"]}
    debe(t["estado"] == "propuesta" and [[x["archivo"] for x in v["tramos"]] for v in p["videos"]] == [[ids["lote-1"]], [ids["lote-3"]]],
         "lote: de 4 archivos se proponen 2 videos", p["videos"])
    debe(reparto.REPETIDA in motivos.get(ids["lote-2"], "") and motivos.get(ids["lote-4"]) == reparto.SIN_VOZ,
         "lote: la toma repetida (queda la última) y el archivo sin voz están en «Sobran», dichos", motivos)
    debe(any("Júntalos tú" in a for a in t["avisos"]), "lote: sin IA se avisa que juntar ideas le toca a la persona", t["avisos"])
    r = api("/api/tanda-propuesta", {"tanda": tid, "videos": [{"titulo": f"{BASE} lote", "tramos": p["videos"][0]["tramos"] + p["videos"][1]["tramos"]}]})
    p = (r.get("tanda") or {}).get("propuesta") or {}
    debe(r.get("ok") and len(p.get("videos", [])) == 1 and len(p["videos"][0]["tramos"]) == 2
         and {x["archivo"] for x in p["sobran"]} == {ids["lote-2"], ids["lote-4"]},
         "lote: la persona junta los dos videos en uno y lo que sobraba sigue a la vista (nada se pierde)", r.get("error") or p)
    from . import montaje
    reescucha = montaje.voces_fuera
    montaje.voces_fuera = lambda carpeta, palabras, avance=print: palabras   # la re-escucha de pausas es de Whisper: aquí no se prueba
    try:
        r = api("/api/tanda-aprobar", {"tanda": tid})
        debe(r.get("ok") and r.get("trabajo"), "lote: aprobar el reparto", r)
        esperar(r["trabajo"], "lote: armar y preparar el video")
    finally:
        montaje.voces_fuera = reescucha
    t = api(f"/api/tanda/{tid}")["tanda"]
    v = t["propuesta"]["videos"][0]
    debe(t["estado"] == "lista" and v.get("estado") == "listo" and v.get("proyecto"), "lote: el video queda preparado como proyecto", v)
    g = api(f"/api/guion/{urllib.parse.quote(v['proyecto'])}")
    esperado = f"{LOTE[0][1]} {LOTE[2][1]}"
    dicho = " ".join(w["w"] for w in json.loads((config.PROYECTOS / v["proyecto"] / "palabras.json").read_text(encoding="utf-8")))
    debe(g.get("listo") and dicho == esperado, "lote: su guion trae lo dicho en los dos archivos, en orden y sin la toma repetida", dicho)
    m = _medir(Path(json.loads((config.PROYECTOS / v["proyecto"] / "fuente.json").read_text())["original"]))
    debe(abs(m["duracion"] - 8) < .4 and m["audio"], f"lote: el video armado dura lo de sus dos archivos ({m['duracion']:.1f} s)", m)


def _medir(video: Path) -> dict:
    _, ffprobe = config.ffmpeg()
    info = json.loads(subprocess.run([ffprobe, "-v", "error", "-show_entries", "stream=codec_type,width,height:format=duration",
                                      "-of", "json", str(video)], capture_output=True, text=True, check=True).stdout)
    v = next((s for s in info["streams"] if s["codec_type"] == "video"), {})
    return {"ancho": v.get("width"), "alto": v.get("height"), "duracion": float(info["format"]["duration"]),
            "audio": any(s["codec_type"] == "audio" for s in info["streams"])}


def recorrer(video: Path | None = None, estilo: str = "basico", con_ia: bool = False, conservar: bool = False, avance=print) -> Path:
    """Hace el recorrido y devuelve el `final.mp4`; lanza `Fallo` (con el paso y lo que vio la persona) si algo no sale."""
    from . import ingesta, servidor
    srv = servidor.Servidor(("127.0.0.1", 0), servidor.Manejador)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{srv.server_address[1]}"
    registro = config.PROYECTOS / "_errores.log"
    desde = registro.stat().st_size if registro.exists() else 0
    sin_ia_antes = os.environ.get("ESTUDIO_SIN_IA")

    def pedir(ruta, cuerpo=None, crudo: bytes | None = None):
        datos = crudo if crudo is not None else json.dumps(cuerpo).encode() if cuerpo is not None else None
        req = urllib.request.Request(url + ruta, datos, {"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=600) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read()

    def api(ruta, cuerpo=None, crudo=None) -> dict:
        codigo, b = pedir(ruta, cuerpo, crudo)
        return {"_codigo": codigo, **json.loads(b)}

    def esperar(tid: str, paso: str) -> dict:
        while True:
            t = api(f"/api/trabajo/{tid}")
            if t.get("estado") != "corriendo":
                break
            time.sleep(.5)
        if t.get("estado") != "listo":
            raise Fallo(f"{paso}: la persona vería «{(t.get('log') or ['(nada)'])[-1]}»")
        return t

    def debe(condicion, paso: str, visto=None) -> None:
        if not condicion:
            raise Fallo(f"{paso}" + (f": {visto}" if visto is not None else ""))
        avance(f"✓ {paso}")

    try:
        if not con_ia:
            os.environ["ESTUDIO_SIN_IA"] = "1"
        _limpiar()
        config.PROYECTOS.mkdir(parents=True, exist_ok=True)
        propio = video is None
        if propio:   # dos partes distintas, subidas una por una y unidas por la app (como «Unir y preparar» en Material)
            subidas = []
            for n, parte in enumerate(_partes_de_prueba(config.PROYECTOS), 1):
                r = api(f"/api/subir?nombre={urllib.parse.quote(f'{BASE}-parte-{n}.mp4')}", crudo=parte.read_bytes())
                parte.unlink(missing_ok=True)
                debe(r.get("ok") and Path(r.get("video", "")).is_file(), f"subir la parte {n}", r)
                subidas.append(r["video"])
            r = api("/api/unir", {"videos": [subidas[0]]})
            debe(r["_codigo"] == 400 and "dos partes" in r.get("error", ""), "unir con una sola parte se niega con su motivo", r)
            r = api("/api/unir", {"videos": subidas})
            debe(r.get("ok") and r.get("trabajo"), "empezar a unir las dos partes", r)
            subido = esperar(r["trabajo"], "unir las partes")["resultado"]
            m = _medir(Path(subido))
            debe((m["ancho"], m["alto"]) == (1280, 720) and m["audio"] and abs(m["duracion"] - SEGUNDOS) < .3
                 and not any(Path(s).exists() for s in subidas),
                 f"las dos partes quedan en un solo video, con el tamaño de la primera y sonido ({m['duracion']:.1f} s)", m)
        else:
            origen = Path(video)
            r = api(f"/api/subir?nombre={urllib.parse.quote(f'{BASE}-{origen.name}')}", crudo=origen.read_bytes())
            debe(r.get("ok") and Path(r.get("video", "")).is_file(), "subir el video", r)
            subido = r["video"]
        if propio:   # mismas palabras siempre y sin transcribir: el proyecto se reconoce por el contenido del video y se retoma
            pid, _ = ingesta.proyecto_para(Path(subido), BASE)
            (config.PROYECTOS / pid / "palabras.json").write_text(json.dumps(_palabras(), ensure_ascii=False))
            (config.PROYECTOS / pid / ".voces_fuera").write_text("ok")
        r = api("/api/preparar", {"video": subido, "nombre": BASE})
        debe(r.get("ok") and r.get("trabajo"), "empezar a preparar el material", r)
        pid = r["proyecto"]
        esperar(r["trabajo"], "preparar el material (guion, video normalizado, persona)")
        debe(api(f"/api/guion/{pid}").get("listo"), "el guion queda a la vista")
        # lo que falló el 13-nov: el video aún no está editado y la pantalla dejaba exportar. Ahora se niega y dice por qué.
        p = api(f"/api/proyecto/{pid}")
        debe(p.get("listo") is False and p.get("no_exporta") == servidor.SIN_EDITAR, "sin editar, la app sabe que no se puede exportar", p.get("no_exporta"))
        r = api("/api/render", {"proyecto": pid, "estilo": {}})
        debe(r["_codigo"] == 409 and r.get("error") == servidor.SIN_EDITAR, "exportar sin editar se niega con su motivo (no «Algo falló»)", r)
        r = api("/api/seleccion", {"proyecto": pid, "guion_aprobado": True, "con_detalles": True})
        debe(r.get("ok"), "aprobar el guion", r.get("error"))
        r = api("/api/dirigir", {"proyecto": pid, "estilo": estilo, "imagenes": con_ia, "confirmado": True})
        debe(r.get("ok") and r.get("trabajo"), f"empezar a editar con el estilo «{estilo}»", r.get("error"))
        esperar(r["trabajo"], f"editar con el estilo «{estilo}»")
        p = api(f"/api/proyecto/{pid}")
        debe(p.get("listo") is True and p.get("no_exporta") is None, "editado: ya se puede exportar", p.get("no_exporta"))
        r = api("/api/render", {"proyecto": pid, "estilo": {}})
        debe(r.get("ok") and r.get("trabajo"), "empezar a exportar", r.get("error"))
        esperar(r["trabajo"], "exportar")
        final = config.PROYECTOS / pid / "final.mp4"
        debe(final.is_file(), "el video final existe")
        m = _medir(final)
        cortes = json.loads((config.PROYECTOS / pid / "storyboard.json").read_text()).get("cortes") or []
        fuente = json.loads((config.PROYECTOS / pid / "fuente.json").read_text())["cuadros"] / config.FPS
        esperado = fuente - sum(b - a for a, b in cortes)
        debe((m["ancho"], m["alto"]) == (config.W, config.H) and m["audio"] and abs(m["duracion"] - esperado) < .5,
             f"el final es vertical {config.W}×{config.H}, con sonido y completo ({m['duracion']:.1f} s)", {**m, "esperado": round(esperado, 2)})
        codigo, cuerpo = pedir(f"/archivo/{urllib.parse.quote(pid)}/final.mp4")
        debe(codigo == 200 and len(cuerpo) == final.stat().st_size, "«Descargar» entrega el video entero")
        debe(api(f"/api/proyecto/{pid}").get("final") is True, "la pantalla Exportar lo muestra")
        if propio and not con_ia:
            _recorrer_lote(api, esperar, debe)
        return final
    except Fallo as e:
        detalle = ""
        if registro.exists() and registro.stat().st_size > desde:
            with open(registro, encoding="utf-8", errors="replace") as f:
                f.seek(desde)
                detalle = "\n--- del registro (proyectos/_errores.log) ---\n" + f.read()[-3000:]
        raise Fallo(f"{e}{detalle}") from None
    finally:
        srv.shutdown()
        srv.server_close()
        if sin_ia_antes is None:
            os.environ.pop("ESTUDIO_SIN_IA", None)
        else:
            os.environ["ESTUDIO_SIN_IA"] = sin_ia_antes
        if not conservar:
            _limpiar()


def main(video: str | None = None, estilo: str = "basico", con_ia: bool = False, conservar: bool = False) -> int:
    t0 = time.time()
    try:
        final = recorrer(Path(video) if video else None, estilo, con_ia, conservar)
    except Fallo as e:
        print(f"✗ autoprueba: {e}")
        return 1
    print(f"autoprueba: VERDE en {time.time() - t0:.0f} s" + (f" · {final}" if conservar else ""))
    return 0
