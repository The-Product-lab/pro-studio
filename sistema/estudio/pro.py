"""Estilos Pro (Pablo, 09-nov): el reel aprobado rehecho como película animada con el motor de Lemo, más todas las palabras del guion.
Plano: docs/PLANO-ESTILOS-PRO.md. Dos editores en cadena:
  1. voz cortada + palabras en el tiempo del corte (lo que ya usa el motor: machote.mp4 y machote.palabras_cortadas);
  2. editor 1 · Opus dirige la película COMPLETA de Lemo sobre esa voz, con sus propios textos del guion (`director/pro.md`) →
     `pelicula.mp4` + su `index.html` de contrato Lemo (`TEXTS`). C-0014 (Pablo, 09-nov): Lemo es mejor editor que nuestro texto, se lo deja hacer;
  3. compuertas de la película (formato, duración = voz, sin negros, `TEXTS`); si fallan, UN reintento con el informe;
  4. `textos_lemo` MIDE en código qué palabras mostró Lemo → mapa de texto sobre `pelicula.mp4` → editor 2 (`texto_pelicula.componer`,
     solo las que faltan, chicas) → `final.mp4`; compuertas (Lemo + nuestras = 100 % de palabras, −14 LUFS ±1).
Encargos viejos (hay `limpio.mp4` y no `pelicula.mp4`): siguen como antes (el editor de textos pone todas).
Todo vive en `proyectos/<p>/pro-<slug>/` con su `estado.json` (fase, pct, linea, error, final). Un encargo a la vez por proyecto.
La IA es `ia.llamar` (suscripción, nunca API); se inyecta con `ia=` para probar sin gastar.
Uso: python -m estudio.cli pro <proyecto> <estilo>"""
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

from . import config, ia as _ia, machote, mapa_texto, motor, portable, texto_pelicula, textos_lemo

LEMO = config.lemo()
PESADO = texto_pelicula.PESADO
PROMPT = Path(__file__).resolve().parent / "director" / "pro.md"
TOPE_USD, TOPE_REINTENTO_USD = 40.0, 20.0     # tope de Claude (equivalente en USD de la suscripción) por llamada
TIMEOUT_S, TIMEOUT_REINTENTO_S = 4 * 3600, 2 * 3600
HERRAMIENTAS = "Read,Write,Edit,Glob,Grep,Bash"
FPS, TAMANO = config.FPS, (config.W, config.H)
DUR_TOL_S = .5                       # la película dura lo que la voz, con esta tolerancia
NEGRO_MIN_S = .15                    # un tramo negro de esto o más es un cuadro negro (falla)
NEGRO_PIX = .10                      # luma bajo la cual un cuadro cuenta como negro (0–1)
LUFS_META, LUFS_TOL = -14.0, 1.0
PELICULA, LEGADO = "pelicula.mp4", "limpio.mp4"   # la película de Lemo con sus textos / la de los encargos viejos (sin las palabras del guion)
FASES = {"cola": 0, "voz": 5, "pelicula": 10, "compuertas": 80, "reintento": 82, "textos": 85, "mapa": 88, "texto": 92, "final": 97, "listo": 100}
TERMINALES = ("listo", "error")


class EncargoOcupado(RuntimeError):
    """Ya hay un encargo Pro corriendo en este proyecto (solo uno a la vez)."""


# ---------------------------------------------------------------------------------------------------------------------
# Estado
# ---------------------------------------------------------------------------------------------------------------------

def nombre(w: str) -> str:
    """Las palabras mal oídas se escriben bien («Cloud» → «Claude») con el mismo diccionario del motor (perfil/diccionario.json):
    así Opus recibe el guion correcto y lo que agregamos no sale con la errata de la transcripción."""
    nucleo = w.strip("¿?¡!.,;:")
    return w.replace(nucleo, motor.diccionario().get(nucleo, nucleo)) if nucleo else w


def encargo(carpeta: Path, slug: str) -> Path:
    return Path(carpeta) / f"pro-{slug}"


def _vivo(pid) -> bool:
    return portable.proceso_vivo(pid)


def _guardar(enc: Path, **cambios) -> dict:
    f = enc / "estado.json"
    est = json.loads(f.read_text()) if f.exists() else {}
    est.update(cambios)
    parcial = enc / "estado.tmp"
    parcial.write_text(json.dumps(est, ensure_ascii=False, indent=1))
    parcial.replace(f)
    return est


def estado(carpeta: Path, slug: str) -> dict:
    """{fase, pct, linea, error, final, ...} del encargo. Si el proceso murió a medias, lo dice como error."""
    f = encargo(carpeta, slug) / "estado.json"
    if not f.exists():
        return {"fase": "nuevo", "pct": 0, "linea": "", "error": None, "final": None}
    est = json.loads(f.read_text())
    if est["fase"] not in TERMINALES and not _vivo(est.get("pid")):
        est.update(fase="error", error=est.get("error") or "el proceso terminó sin avisar (mirá pro.log)", linea="se cortó")
    return est


def activo(carpeta: Path, excepto: str | None = None) -> str | None:
    """El estilo con un encargo corriendo en este proyecto (None si no hay)."""
    for f in sorted(Path(carpeta).glob("pro-*/estado.json")):
        slug = f.parent.name[4:]
        if slug != excepto and estado(carpeta, slug)["fase"] not in TERMINALES + ("nuevo",):
            return slug
    return None


def _fase(enc: Path, fase: str, linea: str, avance=print) -> None:
    _guardar(enc, fase=fase, pct=FASES[fase], linea=linea)
    avance(f"pro: {fase} · {linea}")


# ---------------------------------------------------------------------------------------------------------------------
# Medidas
# ---------------------------------------------------------------------------------------------------------------------

def _sonda(video: Path) -> dict:
    _, ffprobe = config.ffmpeg()
    return json.loads(subprocess.run([ffprobe, "-v", "error", "-show_entries", "format=duration:stream=codec_type,width,height,r_frame_rate",
                                      "-of", "json", str(video)], capture_output=True, text=True, check=True).stdout)


def _negros(video: Path) -> list:
    """[(inicio, duración)] de los tramos negros del video."""
    ffmpeg, _ = config.ffmpeg()
    r = subprocess.run([ffmpeg, "-v", "info", "-i", str(video), "-vf", f"blackdetect=d={NEGRO_MIN_S}:pix_th={NEGRO_PIX}", "-an", "-f", "null", "-"],
                       capture_output=True, text=True)
    return [(float(a), float(d)) for a, d in re.findall(r"black_start:([\d.]+).*?black_duration:([\d.]+)", r.stderr)]


def lufs(video: Path) -> float:
    """Sonoridad integrada (EBU R128) del audio, en LUFS."""
    ffmpeg, _ = config.ffmpeg()
    r = subprocess.run([ffmpeg, "-v", "info", "-nostats", "-i", str(video), "-vn", "-af", "ebur128", "-f", "null", "-"],
                       capture_output=True, text=True)
    m = re.findall(r"^\s+I:\s+(-?[\d.]+) LUFS", r.stderr, re.M)
    if not m:
        raise RuntimeError(f"{Path(video).name}: no pude medir la sonoridad")
    return float(m[-1])


def video_de(enc: Path) -> Path:
    """La película del encargo: `pelicula.mp4`; si solo hay `limpio.mp4` (encargo viejo) esa; si no hay ninguna, `pelicula.mp4` (la que falta)."""
    nueva, vieja = enc / PELICULA, enc / LEGADO
    return vieja if vieja.exists() and not nueva.exists() else nueva


def revisar_pelicula(enc: Path, dur_voz: float) -> list:
    """Compuertas de la película del editor 1 → lista de fallas (vacía = pasa)."""
    f = video_de(enc)
    if not f.exists():
        return [f"no entregó {f.name}"]
    try:
        s = _sonda(f)
    except subprocess.CalledProcessError:
        return [f"{f.name} no se puede leer (archivo roto)"]
    fallas, v = [], next((x for x in s["streams"] if x["codec_type"] == "video"), None)
    if not v:
        return [f"{f.name} no tiene video"]
    if (v["width"], v["height"]) != TAMANO:
        fallas.append(f"tamaño {v['width']}x{v['height']}, debe ser {TAMANO[0]}x{TAMANO[1]}")
    n, d = (int(x) for x in v["r_frame_rate"].split("/"))
    if abs(n / d - FPS) > .01:
        fallas.append(f"{n / d:.2f} cuadros por segundo, deben ser {FPS}")
    if not any(x["codec_type"] == "audio" for x in s["streams"]):
        fallas.append("no tiene audio (falta la voz, la música y el foley)")
    dur = float(s["format"]["duration"])
    if abs(dur - dur_voz) > DUR_TOL_S:
        fallas.append(f"dura {dur:.2f} s y la voz dura {dur_voz:.2f} s (tolerancia {DUR_TOL_S} s)")
    fallas += [f"cuadros negros de {d:.2f} s desde el segundo {a:.2f}" for a, d in _negros(f)]
    if not (enc / "plano.json").exists():
        fallas.append("falta plano.json (tramos con su integración para el editor de textos)")
    if f.name == PELICULA:                        # contrato Lemo: sin index.html con TEXTS no se puede medir qué texto mostró Lemo
        idx = enc / "index.html"
        if not idx.exists() or "TEXTS" not in idx.read_text(errors="ignore"):
            fallas.append("falta index.html con window.TEXTS (todo texto en pantalla registrado, contrato de Lemo)")
    return fallas


def _nivelar(video: Path, avance=print) -> float:
    """Deja el audio de `video` en LUFS_META ±LUFS_TOL con una ganancia fija (sin recodificar el video). Devuelve la sonoridad final."""
    actual = lufs(video)
    if abs(actual - LUFS_META) <= LUFS_TOL:
        return actual
    ffmpeg, _ = config.ffmpeg()
    ganancia = LUFS_META - actual
    avance(f"pro: audio a {actual:.1f} LUFS, se sube {ganancia:+.1f} dB a {LUFS_META:.0f}")
    parcial = video.with_name("nivelado.tmp.mp4")
    subprocess.run([ffmpeg, "-v", "error", "-y", "-i", str(video), "-c:v", "copy", "-af", f"volume={ganancia:.2f}dB,alimiter=limit=0.95",
                    "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(parcial)], check=True)
    parcial.replace(video)
    return lufs(video)


# ---------------------------------------------------------------------------------------------------------------------
# Pasos
# ---------------------------------------------------------------------------------------------------------------------

VOZ_EN_OFF = "voz-en-off.wav"   # proyecto de solo narración (un comercial): la voz tal cual, sin cortes, con su palabras.json


def _voz_en_off(carpeta: Path, enc: Path) -> float:
    """Proyecto «voz en off» (Pablo 09-nov: el guion del comercial de PRO STUDIO en Tinta china): no hay video ni machote; la narración
    ya está aprobada y se usa tal cual, con sus palabras (los nombres pasan por el diccionario)."""
    ffmpeg, ffprobe = config.ffmpeg()
    subprocess.run([ffmpeg, "-v", "error", "-y", "-i", str(carpeta / VOZ_EN_OFF), "-ac", "1", "-ar", "48000", "-c:a", "pcm_s16le",
                    str(enc / "voz.wav")], check=True)
    ps = json.loads((carpeta / "palabras.json").read_text())
    (enc / "palabras.json").write_text(json.dumps([{"w": nombre(p["w"]), "s": round(float(p.get("s", p.get("t0"))), 3),
                                                     "e": round(float(p.get("e", p.get("t1"))), 3)} for p in ps], ensure_ascii=False))
    return float(subprocess.run([ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(enc / "voz.wav")],
                                capture_output=True, text=True, check=True).stdout.strip())


def _voz(carpeta: Path, enc: Path, avance=print) -> float:
    """`voz.wav` (48 kHz mono) y `palabras.json` del reel cortado, en el tiempo del corte. Lo hace el motor: los cortes del machote y su
    audio (`machote.mp4`), y las palabras con `machote.palabras_cortadas`. Si el proyecto no tiene machote, se prepara (etapa fija)."""
    if (carpeta / VOZ_EN_OFF).exists() and (carpeta / "palabras.json").exists() and not machote.cargar(carpeta):
        return _voz_en_off(carpeta, enc)
    mj = machote.cargar(carpeta)
    if not mj or not (carpeta / machote.VIDEO).exists():
        from . import ingesta
        hasta = time.time() + 3600
        while ingesta.es_provisional(carpeta):   # machote.mp4 se corta por cuadros de fuente.mp4: esperar al normalizado definitivo
            if time.time() > hasta:
                raise RuntimeError("el video normalizado no terminó en una hora: vuelve a preparar el video")
            avance("esperando el video normalizado…")
            time.sleep(5)
        mj = machote.preparar(carpeta, avance=avance)
    ffmpeg, _ = config.ffmpeg()
    subprocess.run([ffmpeg, "-v", "error", "-y", "-i", str(carpeta / machote.VIDEO), "-vn", "-ac", "1", "-ar", "48000", "-c:a", "pcm_s16le",
                    str(enc / "voz.wav")], check=True)
    ps = machote.palabras_cortadas(carpeta, mj)
    if not ps:
        raise RuntimeError("el reel cortado no trae palabras: no hay nada que animar")
    (enc / "palabras.json").write_text(json.dumps([{"w": nombre(p["w"]), "s": round(p["s"], 3), "e": round(p["e"], 3)} for p in ps], ensure_ascii=False))
    return float(subprocess.run([config.ffmpeg()[1], "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(enc / "voz.wav")],
                                capture_output=True, text=True, check=True).stdout.strip())


def _prompt(enc: Path, slug: str, dur: float) -> str:
    guion = " ".join(p["w"] for p in json.loads((enc / "palabras.json").read_text()))
    p = PROMPT.read_text()
    for clave, valor in (("slug", slug), ("encargo", str(enc)), ("lemo", str(LEMO)), ("laboratorio", str(LEMO.parent)), ("pesado", str(PESADO) if PESADO.exists() else ""), ("dur", f"{dur:.2f}"), ("guion", guion)):
        p = p.replace(f"[[{clave}]]", valor)
    return p


def _pelicula(enc: Path, slug: str, dur: float, ia, avance=print) -> list:
    """Editor 1. Si ya hay una película que pasa las compuertas (encargo retomado), no se vuelve a pedir. → fallas (vacío = pasa)."""
    fallas = revisar_pelicula(enc, dur) if video_de(enc).exists() else ["todavía no hay película"]
    if not fallas:
        return []
    prompt = _prompt(enc, slug, dur)
    _fase(enc, "pelicula", f"Opus dirige la película «{slug}» ({dur:.0f} s de voz)", avance)
    ia(prompt, "opus", cwd=enc, herramientas=HERRAMIENTAS, tope_usd=TOPE_USD, paso=f"pro-{slug}", timeout=TIMEOUT_S, aislado=False)
    _fase(enc, "compuertas", "revisando la película", avance)
    fallas = revisar_pelicula(enc, dur)
    if not fallas:
        return []
    _fase(enc, "reintento", f"la película no pasó ({len(fallas)} fallas): Opus la corrige una vez", avance)
    informe = "\n".join(f"- {x}" for x in fallas)
    (enc / "informe-compuertas.txt").write_text(informe + "\n")
    ia(prompt + "\n\n# REINTENTO: la película que entregaste NO pasó las compuertas\nCorregí SOLO esto (tu carpeta ya tiene todo lo hecho: "
       "no rehagas la película, arreglá y volvé a renderizar lo mínimo por la cola) y entregá de nuevo `" + video_de(enc).name + "` (con su "
       "`index.html`) y `plano.json`:\n"
       + informe + "\n", "opus", cwd=enc, herramientas=HERRAMIENTAS, tope_usd=TOPE_REINTENTO_USD, paso=f"pro-{slug}-reintento",
       timeout=TIMEOUT_REINTENTO_S, aislado=False)
    return revisar_pelicula(enc, dur)


def correr(carpeta: Path, slug: str, ia=None, avance=print) -> dict:
    """El encargo entero. → {"ok", "fase", "final", "informe"/"error"}. `ia` reemplaza a `ia.llamar` (las pruebas nunca llaman a Claude)."""
    carpeta = Path(carpeta)
    ia = ia or _ia.llamar
    if not (LEMO / "styles" / slug / "STYLE.md").exists():
        raise ValueError(f"estilo Pro desconocido: «{slug}» (no está en {LEMO / 'styles'})")
    otro = activo(carpeta, excepto=slug)
    if otro:
        raise EncargoOcupado(f"{carpeta.name} ya tiene un encargo corriendo ({otro}): un reel Pro a la vez")
    enc = encargo(carpeta, slug)
    enc.mkdir(exist_ok=True)
    _guardar(enc, slug=slug, pid=os.getpid(), error=None, final=None, inicio=time.strftime("%Y-%m-%dT%H:%M:%S"))
    try:
        _fase(enc, "voz", "sacando la voz y las palabras del reel cortado", avance)
        dur = _voz(carpeta, enc, avance)
        fallas = _pelicula(enc, slug, dur, ia, avance)
        if fallas:
            return _fallo(enc, "la película no pasó las compuertas tras el reintento: " + "; ".join(fallas), fallas)
        sonoridad = _nivelar(video_de(enc), avance)
        return _textos_y_final(enc, dur, sonoridad, avance)
    except BaseException as e:           # también el límite de Claude y Ctrl-C: el estado nunca queda «corriendo» sin proceso
        _guardar(enc, fase="error", linea="se cortó", error=f"{type(e).__name__}: {e}"[:600])
        raise


def _textos_y_final(enc: Path, dur: float, sonoridad: float, avance=print, video: Path | None = None) -> dict:
    """Pasos 2–4 de la cadena sobre una película ya hecha (los usa `correr` y `pro_textos`): mide qué textos mostró Lemo, mapa de texto
    sobre la película, editor 2 con SOLO las palabras que faltan y compuertas finales. Encargo viejo (`limpio.mp4`): el editor 2 pone todas."""
    video = video or video_de(enc)
    legado = video.name == LEGADO
    lemo = None
    if not legado:
        _fase(enc, "textos", "midiendo qué palabras mostró Lemo", avance)
        lemo = textos_lemo.medir(enc, LEMO)
        avance(f"pro: Lemo mostró {lemo['mostradas_lemo']}/{lemo['palabras']} palabras ({lemo['cobertura'] * 100:.0f} %)")
        lemo = set(lemo["indices_mostradas"])
    _fase(enc, "mapa", "midiendo dónde cabe el texto", avance)
    mapa_texto.escribir(enc, video.name)
    _fase(enc, "texto", "poniendo las palabras que faltan" if lemo is not None else "poniendo todas las palabras del guion", avance)
    inf = texto_pelicula.componer(enc, enc / "final.mp4", lemo)
    if not inf["ok"]:
        return _fallo(enc, "el editor de textos no pasó sus compuertas: " + "; ".join(inf["fallas"]), inf["fallas"])
    _fase(enc, "final", "compuertas finales", avance)
    fallas = _compuertas_finales(enc, dur, inf)
    if fallas:
        return _fallo(enc, "el final no pasó las compuertas: " + "; ".join(fallas), fallas)
    detalle = (f"Lemo puso {inf['lemo']} de {inf['palabras']} palabras, agregamos {inf['agregadas']}" if lemo is not None
               else f"{inf['mostradas']}/{inf['palabras']} palabras")
    _guardar(enc, fase="listo", pct=100, final=str(enc / "final.mp4"), lemo=inf["lemo"], agregadas=inf["agregadas"],
             linea=f"listo · {detalle} · {lufs(enc / 'final.mp4'):.1f} LUFS")
    return {"ok": True, "fase": "listo", "final": str(enc / "final.mp4"), "palabras": f"{inf['mostradas']}/{inf['palabras']}",
            "lemo": inf["lemo"], "agregadas": inf["agregadas"], "lufs": round(sonoridad, 1)}


def pro_textos(enc: Path, video: str | None = None, avance=print) -> dict:
    """Solo los pasos 2–4 sobre un encargo ya rendido (con `index.html` de contrato Lemo, la película completa, `palabras.json` y, si
    quedó, `plano.json`): reaprovecha una película hecha sin volver a llamar a Opus. → como `correr`."""
    enc = Path(enc)
    f = enc / video if video else video_de(enc)
    for req in (f, enc / "palabras.json"):
        if not req.exists():
            raise FileNotFoundError(f"{enc.name}: falta {req.name}")
    if f.name != LEGADO and not (enc / "index.html").exists():
        raise FileNotFoundError(f"{enc.name}: falta index.html (la película de Lemo, para leer sus textos)")
    dur = float(_sonda(f)["format"]["duration"])
    _guardar(enc, pid=os.getpid(), error=None, final=None)
    try:
        return _textos_y_final(enc, dur, _nivelar(f, avance), avance, f)
    except BaseException as e:
        _guardar(enc, fase="error", linea="se cortó", error=f"{type(e).__name__}: {e}"[:600])
        raise


def _fallo(enc: Path, error: str, fallas: list) -> dict:
    _guardar(enc, fase="error", linea="no pasó las compuertas", error=error[:900])
    return {"ok": False, "fase": "error", "error": error, "fallas": fallas}


def _compuertas_finales(enc: Path, dur_voz: float, inf: dict) -> list:
    f = enc / "final.mp4"
    if not f.exists():
        return ["no se generó final.mp4"]
    fallas = []
    if inf["mostradas"] != inf["palabras"]:
        fallas.append(f"{inf['mostradas']} de {inf['palabras']} palabras mostradas")
    dur = float(_sonda(f)["format"]["duration"])
    if abs(dur - dur_voz) > DUR_TOL_S:
        fallas.append(f"dura {dur:.2f} s y la voz {dur_voz:.2f} s")
    fallas += [f"cuadros negros de {d:.2f} s desde el segundo {a:.2f}" for a, d in _negros(f)]
    sonoridad = lufs(f)
    if abs(sonoridad - LUFS_META) > LUFS_TOL:
        fallas.append(f"{sonoridad:.1f} LUFS, debe estar en {LUFS_META:.0f} ±{LUFS_TOL:.0f}")
    return fallas


def motor_instalado() -> bool:
    """¿Esta máquina puede EDITAR con Estilos Pro? El catálogo se ve con la copia de referencia; editar pide el motor de Lemo."""
    return LEMO.is_dir()


def lanzar(carpeta: Path, slug: str) -> Path:
    """Arranca el encargo en un proceso aparte (no bloquea) y devuelve su carpeta. Un encargo a la vez por proyecto."""
    carpeta = Path(carpeta).resolve()
    if not motor_instalado():   # se ve el catálogo (copia de referencia) pero el motor para editar no está en esta máquina
        raise ValueError("Para editar con un estilo Pro falta el motor de Lemo instalado en esta máquina (viaja en el paquete; repite el instalador o corre `estudio doctor --arreglar`).")
    if not (LEMO / "styles" / slug / "STYLE.md").exists():
        raise ValueError(f"estilo Pro desconocido: «{slug}»")
    otro = activo(carpeta)
    if otro:
        raise EncargoOcupado(f"{carpeta.name} ya tiene un encargo corriendo ({otro}): un reel Pro a la vez")
    enc = encargo(carpeta, slug)
    enc.mkdir(exist_ok=True)
    _guardar(enc, slug=slug, pid=os.getpid(), fase="cola", pct=0, linea="arrancando", error=None, final=None)   # vivo mientras el hijo toma el relevo
    with open(enc / "pro.log", "ab") as log:
        subprocess.Popen([sys.executable, "-m", "estudio.cli", "pro", str(carpeta), slug], cwd=config.RAIZ, stdout=log, stderr=log,
                         stdin=subprocess.DEVNULL, start_new_session=True)
    return enc
