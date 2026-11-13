"""Muestras del seleccionador: cada opción del catálogo se VE, renderizada con el motor REAL sobre el C8866 (docs/PLANO-SELECCIONADOR.md).

`uv run estudio muestras` hace un clip de ~1,2 s (540×960) por transición, subtítulo, efecto y caja; una imagen fija por look y filtro; un trozo del video
final de cada estilo y los primeros segundos de la copia aprobada que mejor muestra cada tipo de hook. Cada video lleva su
póster (`<muestra>.poster.jpg`): la pantalla lo muestra al instante y el video carga solo cuando se ve. Todo en
`app/muestras/sel/` (fuera de git). Va siempre por la cola del PC (`pesado.sh`): la CLI se pone en la cola sola.
Solo se rehace lo que cambió: cada muestra guarda la huella del motor y de su storyboard.
"""
import copy
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

from . import catalogo, config, motor, persona

BASE = config.PROYECTOS / "c8866"                 # el video de trabajo del banco (persona y voz reales)
TRABAJO = config.TPS / "muestras-sel"             # proyecto de trabajo, fuera de git y fuera de la lista de proyectos
SEL = catalogo.SEL
HUELLAS = SEL / "huellas.json"
PESADO = config.pesado() or config.TPS / "sin-cola-pesado"   # inexistente = esta máquina corre directo
UNA = (21.0, 22.2)                                # «celular está lleno de videos»
DOS = ((21.3, 21.9), (31.6, 32.2))                # dos tomas distintas: para ver un corte
QUIETO = 21.6
MOTOR = ("motor.py", "efectos.py", "camara.py", "color.py", "sonido.py", "muestras.py")
ESTILO = {"id": "muestra", "base": "pantalla", "acento": "#FFE800", "acento2": "#00E5FF", "tinta": "#0B0C10", "papel": "#0B0C10",
          "persona": "color", "fuente": "Montserrat", "fuente_script": "Alex Brush", "fuente_mono": "JetBrains Mono",
          "subtitulo": "hud", "grano": 0}


def _texto(t0, t1, entra="llega", palabra="CELULAR", **extra):
    return {"id": "t", "tipo": "texto", "x": 540, "y": 330, "t0": t0, "t1": t1, "entra": entra,
            "lineas": [{"texto": palabra, "rol": "display", "tam": 190, "color": "acento", "mayus": True}], **extra}


def _sb(tramos=(UNA,), estilo=None, escenas=None, elementos=(), subtitulos=False, **extra):
    """Storyboard mínimo que deja solo esos tramos de la fuente (el resto va en `cortes`)."""
    fin = json.loads((BASE / "fuente.json").read_text())["cuadros"] / config.FPS
    cortes, desde = [], 0.0
    for a, b in tramos:
        if a > desde:
            cortes.append([round(desde, 3), a])
        desde = b
    cortes.append([desde, round(fin, 3)])
    return {"estilo": {**ESTILO, **(estilo or {})}, "cortes": cortes,
            "escenas": escenas or [{"t0": 0.0, "persona": {"modo": "completa"}}], "elementos": list(elementos),
            "subtitulos": {"y": 1400} if subtitulos else {"y": 1400, "ocultar": [[0, fin]]}, **extra}


def _corte(entrada="corte", **estilo):
    return _sb(DOS, estilo, [{"t0": 0.0, "persona": {"modo": "completa"}},
                             {"t0": DOS[1][0], "persona": {"modo": "completa"}, **({"entrada": entrada} if entrada != "corte" else {})}])


def _efecto(k, valor):
    if k in ("aberracion_corte", "transicion"):
        return _corte(**{k: valor})
    elems = [_texto(UNA[0] + .1, UNA[1], profundidad=1)] if k == "flotar_elementos" else []
    return _sb(estilo={k: valor}, elementos=elems)


LINEA = {"texto": "CELULAR", "rol": "display", "tam": 190, "color": "acento", "mayus": True}


def _recurso(rid):
    t0, t1 = UNA[0] + .1, UNA[1]
    base = {"t0": t0, "t1": t1}
    els, extra = [], {}
    if rid == "etiqueta":
        els = [{"id": "e", "tipo": "etiqueta", "lineas": [["Celular lleno", 92, False, 800]], "fondo": "acento", "x": 540, "y": 420,
                "entra": "barrido", **base}]
    elif rid == "etiqueta-redondeada":
        els = [{"id": "e", "tipo": "etiqueta", "lineas": [["celular lleno", 60, False, 700]], "fondo": "blanco", "radio": 30, "rol": "mono",
                "x": 540, "y": 420, "entra": "pop", **base}]
    elif rid == "vidrio":
        els = [{"id": "v", "tipo": "vidrio", "x": 540, "y": 400, "ancho": 860, "alto": 300, "radio": 32, "desenfoque": 22, "velo": .28,
                "grupo": "g", **base},
               {**_texto(t0, t1, "fundido", z="frente", grupo="g"), "y": 400,
                "lineas": [{**LINEA, "tam": 150, "color": "blanco"}]}]
    elif rid == "panel":
        els = [{"id": "p", "tipo": "panel", "src": "arte/apoyo.jpg", "x": 540, "y": 640, "ancho": 440, "alto": 580, **base}]
    elif rid == "caja-hud":
        extra = {"cajas": [{"sobre": "cara", "etiqueta": "Sujeto 01", "datos": ["celular · 100 %", "videos · 2431"], **base}]}
    elif rid == "contador":
        els = [{"id": "c", "tipo": "contador", "x": 540, "y": 460, "desde": 0, "hasta": 100, "sufijo": " %", "cuenta_s": 1.0,
                "tam": 230, "color": "acento", **base}]
    elif rid == "barra":
        els = [{"id": f"b{i}", "tipo": "barra", "x": 330 + i * 210, "y": 1050, "ancho": 150, "alto": 260 + i * 170, "color": "acento",
                "crece_s": .6, "t0": t0 + i * .12, "t1": t1} for i in range(3)]
    elif rid == "barra-horizontal":
        els = [{"id": f"b{i}", "tipo": "barra", "direccion": "horizontal", "x": 540, "y": 420 + i * 110, "ancho": 820 - i * 220,
                "alto": 64, "color": "acento", "crece_s": .6, "t0": t0 + i * .12, "t1": t1} for i in range(3)]
    elif rid == "pixeles":
        els = [{"id": f"x{i}", "tipo": "pixeles", "x": x, "y": y, "ancho": 150, "alto": 150, "celda": 25, "colores": ["acento", "blanco"],
                **base} for i, (x, y) in enumerate(((300, 420), (780, 560)))]
    else:
        raise ValueError(f"recurso sin muestra: {rid}")
    return _sb(elementos=els, **extra)


def _final_de(estilo: str) -> Path | None:
    """El video final más reciente de ese estilo (un proyecto cuyo storyboard es de ese estilo o que se llama c8866-<estilo>)."""
    mejores = []
    for d in config.PROYECTOS.glob("*"):
        f, s = d / "final.mp4", d / "storyboard.json"
        if not f.exists():
            continue
        try:
            sid = json.loads(s.read_text()).get("estilo", {}).get("id") if s.exists() else None
        except ValueError:
            sid = None
        if d.name.endswith("-" + estilo) or (sid == estilo and not any(d.name.endswith("-" + o) for o in catalogo.presets() if o != estilo)):
            mejores.append(f)
    return max(mejores, key=lambda f: (f.parent.name.endswith("-" + estilo), f.stat().st_mtime)) if mejores else None


def pedidos() -> list:
    """[(categoría, opción, clase, dato)] — una muestra por opción del catálogo que se puede mostrar.
    clase: video (storyboard), foto (storyboard, un cuadro), estilo (trozo de un final)."""
    out = []
    for c in catalogo.catalogo(todas=True)["categorias"]:
        for o in c["opciones"]:
            oid = o["id"]
            if c["id"] == "preset":   # un trozo de su video final; si no tiene, un cuadro del C8866 con ese estilo
                final = _final_de(oid)
                if final:
                    out.append(("estilo", oid, "estilo", str(final)))
                elif not (catalogo.MUESTRAS / f"{oid}.jpg").exists():
                    est = {k: v for k, v in catalogo.presets()[oid].items() if k != "nombre"}
                    out.append(("estilo", oid, "foto", _sb(estilo={**est, "id": oid}, escenas=[{"t0": 0.0}],
                                                           elementos=[_texto(QUIETO - .5, QUIETO + .5)])))
            elif c["id"] == "transiciones":
                out.append(("transicion", oid, "video", _corte(oid)))
            elif c["id"] == "subtitulo":
                out.append(("subtitulo", oid, "video", _sb(estilo={"subtitulo": oid}, subtitulos=True)))
            elif c["id"] == "hooks":   # los primeros segundos de la copia aprobada que más claro abre así
                final = _final_hook(o.get("ejemplos_id") or [])
                if final:
                    out.append(("hook", oid, "hook", str(final)))
            elif c["id"] == "filtros":
                out.append(("filtro", oid, "foto", _sb(escenas=[{"t0": 0.0, "filtro": oid, "persona": {"modo": "completa"}}])))
            elif c["id"] == "cajas":
                out.append(("recurso", oid, "video", _recurso(oid)))
            elif c["id"].startswith("efectos"):
                out.append(("efecto", oid, "video", _efecto(oid, o.get("encendido", o.get("valor")))))
            elif c["id"] == "look":
                cfg = {"look": oid, **({"fuerza": o["fuerza"]} if "fuerza" in o else {})}
                out.append(("look", oid, "foto", _sb(estilo={"color": cfg})))
    out.append(("color", "sin", "foto", _sb()))   # la toma sin receta ni look: la miniatura de «Sin color» en Personalizar
    return out


def _final_hook(estilos) -> Path | None:
    """El final de la primera copia aprobada (de las que abren con ese hook) que exista."""
    from .portadas import aprobados
    ap = aprobados()
    return next((ap[e] / "final.mp4" for e in estilos if e in ap), None)


def _huella(clase, dato) -> str:
    h = hashlib.sha1(json.dumps([clase, dato], sort_keys=True, default=str).encode())
    for f in MOTOR:
        h.update((config.RAIZ / "estudio" / f).read_bytes())
    return h.hexdigest()[:16]


def _preparar_trabajo() -> None:
    TRABAJO.mkdir(parents=True, exist_ok=True)
    for f in ("fuente.json", "palabras.json", persona.ARCHIVO):
        if (BASE / f).exists():
            shutil.copy(BASE / f, TRABAJO / f)
    (TRABAJO / "arte").mkdir(exist_ok=True)
    if not (TRABAJO / "arte" / "apoyo.jpg").exists():   # un apoyo de verdad: el primero que haya en el arte de los proyectos
        fotos = sorted(f for f in config.PROYECTOS.glob("*/arte/*") if f.suffix.lower() in (".png", ".jpg") and "neon" not in f.name)
        from PIL import Image
        im = Image.open(fotos[0]).convert("RGB") if fotos else Image.new("RGB", (900, 900), (210, 200, 180))
        im.thumbnail((1000, 1000))
        im.save(TRABAJO / "arte" / "apoyo.jpg", quality=90)


def _codificar(destino: Path, cuadros) -> None:
    ffmpeg, _ = config.ffmpeg()
    enc = subprocess.Popen([ffmpeg, "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{config.W}x{config.H}",
                            "-r", str(config.FPS), "-i", "-", "-vf", "scale=540:960", "-c:v", "libx264", "-preset", "veryfast",
                            "-crf", "23", "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-an", str(destino)], stdin=subprocess.PIPE)
    try:
        for rgb in cuadros:
            enc.stdin.write(rgb.tobytes())
    finally:
        enc.stdin.close()
        enc.wait()
    if enc.returncode:
        raise RuntimeError(f"ffmpeg no pudo codificar {destino.name}")


def _hacer(pedido) -> str:
    """Una muestra. Corre en otro proceso; devuelve el archivo hecho."""
    cat, oid, clase, dato = pedido
    base = SEL / catalogo.archivo_muestra(cat, oid)
    if clase in ("estilo", "hook"):   # estilo: un trozo del medio de su final; hook: sus primeros segundos
        destino = base.with_suffix(".mp4")
        if not dato:
            raise FileNotFoundError(f"el estilo {oid} no tiene video final todavía")
        ffmpeg, ffprobe = config.ffmpeg()
        dur = float(subprocess.run([ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", dato],
                                   capture_output=True, text=True, check=True).stdout.strip() or 4)
        ini, largo = (0.0, 2.8) if clase == "hook" else (max(0, dur * .35), 2.4)
        subprocess.run([ffmpeg, "-v", "error", "-y", "-ss", f"{ini:.2f}", "-t", str(largo), "-i", dato, "-vf", "scale=540:960",
                        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-an",
                        str(destino)], check=True)
        return destino.name
    sb = copy.deepcopy(dato)
    p = motor.Proyecto(TRABAJO, sb)
    if clase == "foto":
        from bisect import bisect_left
        from PIL import Image
        of = min(len(p.mapa) - 1, bisect_left(p.mapa, round(QUIETO * config.FPS)))
        destino = base.with_suffix(".jpg")
        for _, rgb in motor.recorrer(p, {of}):
            Image.fromarray(rgb).resize((540, 960)).save(destino, quality=86)
        return destino.name
    destino = base.with_suffix(".mp4")
    _codificar(destino, (rgb for _, rgb in motor.recorrer(p, set(range(len(p.mapa))))))
    return destino.name


def generar(forzar=False, solo=None, avance=print) -> dict:
    """Hace las muestras que faltan o cambiaron. `solo`: categoría (transicion, entrada, tratamiento…). Devuelve el informe."""
    import multiprocessing as mp
    if not (BASE / "fuente.json").exists():
        raise FileNotFoundError("Las muestras se hacen con un video de trabajo del taller (C8866) que esta máquina no tiene; las ya hechas viajan en el paquete.")
    SEL.mkdir(parents=True, exist_ok=True)
    _preparar_trabajo()
    huellas = json.loads(HUELLAS.read_text()) if HUELLAS.exists() else {}
    solos = set(str(solo).split(",")) if solo else None
    todos = [p for p in pedidos() if not solos or p[0] in solos]
    faltan = []
    for p in todos:
        nombre = catalogo.archivo_muestra(p[0], p[1])
        hecho = any((SEL / (nombre + e)).exists() for e in (".mp4", ".jpg"))
        if forzar or not hecho or huellas.get(nombre) != _huella(p[2], p[3]):
            faltan.append(p)
    avance(f"muestras: {len(todos)} en el catálogo, {len(faltan)} por hacer")
    # los cuadros fuente se decodifican una sola vez (y en serie: así los procesos no se pisan la caché)
    p0 = motor.Proyecto(TRABAJO, _sb())
    for i in sorted({i for a, b in (UNA, *DOS) for i in range(round(a * config.FPS), round(b * config.FPS) + 1)}):
        motor._un_cuadro(p0, i)
    informe, hechos = {"hechas": [], "fallas": {}}, 0
    with mp.get_context("spawn").Pool(max(1, min(motor.procesos(), len(faltan) or 1))) as pool:
        for p, r in zip(faltan, pool.imap(_seguro, faltan)):
            hechos += 1
            nombre = catalogo.archivo_muestra(p[0], p[1])
            if r.startswith("ERROR"):
                informe["fallas"][nombre] = r
                avance(f"[{hechos}/{len(faltan)}] {nombre}: {r}")
                continue
            huellas[nombre] = _huella(p[2], p[3])
            HUELLAS.write_text(json.dumps(huellas, indent=1))
            informe["hechas"].append(r)
            avance(f"[{hechos}/{len(faltan)}] {r}")
    shutil.rmtree(TRABAJO / ".cuadros", ignore_errors=True)   # ~6 MB por cuadro: no se guarda
    informe["posters"] = posters(avance)
    return informe


def posters(avance=print) -> int:
    """Un póster jpg (un cuadro del medio) por cada muestra en video que no lo tenga o sea más vieja que su video."""
    ffmpeg, _ = config.ffmpeg()
    hechos = 0
    for v in sorted(SEL.glob("*.mp4")):
        p = v.with_suffix(".poster.jpg")
        if p.exists() and p.stat().st_mtime >= v.stat().st_mtime:
            continue
        r = subprocess.run([ffmpeg, "-v", "error", "-y", "-ss", "0.9", "-i", str(v), "-frames:v", "1", "-q:v", "4", str(p)])
        if r.returncode or not p.exists():   # clip más corto que el punto pedido: el primer cuadro
            subprocess.run([ffmpeg, "-v", "error", "-y", "-i", str(v), "-frames:v", "1", "-q:v", "4", str(p)])
        hechos += p.exists()
    avance(f"pósters: {hechos} nuevos")
    return hechos


def _seguro(p) -> str:
    try:
        return _hacer(p)
    except Exception as e:  # noqa: BLE001 — una muestra que falla no frena las demás; queda en el informe
        return f"ERROR {type(e).__name__}: {e}"


def en_cola(argv: list) -> int | None:
    """Si no estamos ya dentro del turno de `pesado.sh`, se vuelve a lanzar por la cola y devuelve su código de salida.
    None = ya estamos en el turno (o esta máquina no tiene la cola): se corre aquí mismo."""
    if os.environ.get("PESADO_TENGO") or not PESADO.exists():
        return None
    import sys
    return subprocess.run([str(PESADO), sys.executable, "-m", "estudio.cli", *argv], cwd=config.RAIZ).returncode
