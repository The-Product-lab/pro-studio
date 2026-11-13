"""Estudio VISUAL de cada referente: lo que se mide con código (exacto) + lo que Opus ve cuadro a cuadro (el sistema de diseño).

    medir(video)              → cortes reales (cambio de plano cuadro a cuadro), ritmo, paleta real por píxeles, luz/contraste
    estudiar(estilo, codigo)  → db/<estilo>/visual/<codigo>.md: Opus mira la hoja de cuadros y los cuadros clave con esas medidas

Reemplaza a «leer la descripción de vidIQ»: el aprendizaje sale de las imágenes del reel.
"""
import json
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image

from . import config, ia, referentes

DB = referentes.DB


def _cortes(video: Path) -> tuple[list, float]:
    """Tiempos de cambio de plano: diferencia media entre cuadros seguidos (a 90×160 en gris) muy por encima de la local."""
    ffmpeg, ffprobe = config.ffmpeg()
    fps = 30
    raw = subprocess.run([ffmpeg, "-v", "error", "-i", str(video), "-vf", f"fps={fps},scale=90:160,format=gray", "-f", "rawvideo", "-"],
                         capture_output=True, check=True).stdout
    f = np.frombuffer(raw, np.uint8).reshape(-1, 160, 90).astype(np.float32)
    if len(f) < 2:
        return [], len(f) / fps
    d = np.abs(np.diff(f, axis=0)).mean((1, 2))
    med = np.array([np.median(d[max(0, i - 15):i + 15]) for i in range(len(d))])
    cortes, ultimo = [], -99
    for i, v in enumerate(d):
        if v > max(18, 3.5 * med[i]) and i - ultimo > 4:
            cortes.append(round((i + 1) / fps, 2))
            ultimo = i
    return cortes, len(f) / fps


def _paleta(fotos: list, k=8) -> list:
    """Colores dominantes de todos los cuadros (k-means simple y determinista) con su porcentaje."""
    px = np.concatenate([np.asarray(Image.open(f).convert("RGB").resize((48, 85)), np.float32).reshape(-1, 3) for f in fotos])
    rng = np.random.default_rng(0)
    c = px[rng.choice(len(px), k, replace=False)]
    for _ in range(12):
        lab = ((px[:, None] - c[None]) ** 2).sum(-1).argmin(1)
        c = np.array([px[lab == j].mean(0) if (lab == j).any() else c[j] for j in range(k)])
    cuanto = np.bincount(lab, minlength=k) / len(lab)
    orden = np.argsort(-cuanto)
    return [{"hex": "#%02X%02X%02X" % tuple(int(v) for v in c[j]), "pct": round(float(cuanto[j]) * 100, 1)} for j in orden]


def medir(estilo: str, codigo: str) -> dict:
    video = referentes.RAIZ / estilo / f"{codigo}.mp4"
    fotos = sorted((referentes.RAIZ / estilo / codigo).glob("t_*.jpg"))
    cortes, dur = _cortes(video)
    planos = np.diff([0] + cortes + [dur]) if dur else np.array([])
    arr = np.stack([np.asarray(Image.open(f).convert("RGB").resize((48, 85)), np.float32) / 255 for f in fotos]) if fotos else np.zeros((1, 1, 1, 3))
    luma = arr @ np.array([.299, .587, .114])
    sat = arr.max(-1) - arr.min(-1)
    m = {"duracion_s": round(dur, 2), "cortes_s": cortes, "cortes_por_min": round(len(cortes) / dur * 60, 1) if dur else 0,
         "plano_medio_s": round(float(planos.mean()), 2) if len(planos) else None,
         "plano_min_max_s": [round(float(planos.min()), 2), round(float(planos.max()), 2)] if len(planos) else None,
         "luz_media": round(float(luma.mean()), 2), "contraste": round(float(luma.std()), 2), "saturacion": round(float(sat.mean()), 2),
         "paleta": _paleta(fotos) if fotos else []}
    destino = DB / estilo / "visual"
    destino.mkdir(parents=True, exist_ok=True)
    (destino / f"{codigo}.medidas.json").write_text(json.dumps(m, ensure_ascii=False, indent=1))
    return m


PROMPT = """Eres director de arte y motion designer. Estudia este reel de referencia del estilo «{estilo}» MIRANDO SUS CUADROS (no hay texto que leer:
lo que sepas sale de las imágenes). {duenno}
NO juzgues si el reel «encaja» con el estilo ni recomiendes descartarlo: Pablo lo eligió por su EDICIÓN (aunque sea de otro tema,
idioma o una grabación de pantalla del programa de edición: entonces estudia también cómo está armado, capas y tiempos de la línea
de tiempo). Tu trabajo es extraer TODO lo que tiene, con el máximo detalle.

Abre con Read, TODO:
- la hoja de contacto `{hoja}` (todo el reel, un cuadro cada 0,5 s, con su segundo);
- las hojas CUADRO A CUADRO: {finas} (el gancho a 10 cps y cada corte de 0,25 s antes a 0,3 s después a 20 cps): ahí se ve cómo
  entra y sale cada cosa, la curva del movimiento, qué hace la cámara y cómo es cada transición;
- los cuadros sueltos de `{carpeta}` (t_<segundo>.jpg) que necesites ver grandes para leer bordes, texturas y letras.
Medidas exactas sacadas con código (úsalas, no las contradigas): {medidas}

Estudia como un motion designer senior. Para CADA elemento que aparezca recorre esta lista y di lo que ves (o «no»):
- luz y textura: halation (halo rojizo en altas luces), bloom, glow, grano (fino/grueso, constante/animado), ruido, viñeta,
  aberración cromática, desenfoque/profundidad, scanlines/CRT, polvo y rayones, papel, semitono, light leak;
- modo de fusión aparente: normal, screen/add (las luces se suman y el negro desaparece), multiply (oscurece), overlay, luz suave;
- borde: limpio, áspero/impreso, con trazo (grosor y color), hueco, extruido/3D, sombra dura o suave (dirección, distancia, blur);
- color: armonía (análoga, complementaria, monocroma, triádica, un solo acento), temperatura, saturación, negros levantados, grade;
- tipografía: familia probable y equivalente libre en Google Fonts, peso, ancho (condensada/normal), mayúsculas, tracking, interlineado,
  tamaño como % del ancho del cuadro, alineación, cómo se apila;
- animación: estilo (retro/vintage, stop-motion 12 cps, elástica con rebote, seca, suave), curva (ease-out, overshoot, lineal),
  cuántos cuadros dura la entrada, de dónde entra, cómo sale, si es en cascada (y el desfase);
- cámara: estática, flotante (deriva suave continua), push-in, punch-in en palabra, whip zoom/pan, temblor; ¿se mueve la cámara mientras
  entra un apoyo?;
- relación toma ↔ apoyo: qué pasa entre una toma y la siguiente y cómo encaja el apoyo con lo que se dice.

Escribe `{salida}` con TODO lo estético, concreto y medible (porcentajes del cuadro, posiciones, segundos, HEX de las medidas):
1. **Sistema en una frase** y qué lo hace reconocible en 1 segundo.
2. **Color**: la paleta medida con el ROL de cada color (fondo, texto, acento, sombra) y dónde aparece; tratamiento de la imagen (grade, contraste, saturación, grano, viñeta).
3. **Tipografía**: cada estilo de letra que aparece (rol, mayúsculas, peso, ancho, serif o no, tracking, tamaño como % del ancho del cuadro, color, borde/sombra/brillo) y la familia de Google Fonts más cercana.
4. **Composición**: retícula, dónde va la persona (y cuánto ocupa), dónde va el texto, márgenes, qué queda delante/detrás de la persona.
5. **Elementos gráficos**: CADA uno (forma, tamaño, borde, radio, sombra, textura, color) y cómo entra y sale (mirando cuadros seguidos).
6. **Apoyos**: qué apoya cada idea (imagen, objeto, ícono, mapa, cifra) y cada cuánto aparece uno.
7. **Persona**: encuadre, recorte, tratamiento (color/B-N/silueta), fondo detrás de ella, luz.
8. **Movimiento y transiciones**: cámara (zooms, punch, temblor), cómo se pasa de un plano a otro, en qué segundos (usa los cortes medidos).
9. **Subtítulos**: si hay, posición, tamaño, cuántas palabras, cómo se marca la palabra clave.
10. **Reglas del sistema**: 8–12 reglas que se cumplen siempre en este reel (lo que un editor debe hacer para que se vea igual).
11. **Qué NO hace** este reel.
12. **Tabla de momentos**: segundo · qué se ve · recurso (un renglón por plano, con los cortes medidos).
Responde en una línea «listo»."""


def _hoja_fina(video: Path, t0: float, t1: float, fps: float, salida: Path, cols=6):
    """Cuadro a cuadro de un tramo (para ver cómo entra cada cosa y cómo es cada transición), con el segundo en cada cuadro."""
    from PIL import ImageDraw
    ffmpeg, _ = config.ffmpeg()
    raw = subprocess.run([ffmpeg, "-v", "error", "-ss", f"{max(0, t0):.3f}", "-t", f"{t1 - max(0, t0):.3f}", "-i", str(video),
                          "-vf", f"fps={fps},scale=240:-2", "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True).stdout
    import io
    fotos, i = [], 0
    while True:
        j = raw.find(b"\x89PNG", i + 1)
        trozo = raw[i:j] if j > 0 else raw[i:]
        if trozo.startswith(b"\x89PNG"):
            fotos.append(Image.open(io.BytesIO(trozo)).convert("RGB"))
        if j < 0:
            break
        i = j
    if not fotos:
        return None
    w, h = fotos[0].size
    hoja = Image.new("RGB", (cols * w, -(-len(fotos) // cols) * h), "black")
    for k, f in enumerate(fotos):
        ImageDraw.Draw(f).text((4, 4), f"{max(0, t0) + k / fps:.2f}s", fill="yellow")
        hoja.paste(f, ((k % cols) * w, (k // cols) * h))
    hoja.save(salida, quality=85)
    return salida


def hojas_finas(estilo: str, codigo: str, m: dict) -> list:
    video = referentes.RAIZ / estilo / f"{codigo}.mp4"
    dest = referentes.RAIZ / estilo / codigo / "fino"
    dest.mkdir(exist_ok=True)
    out = [_hoja_fina(video, 0, min(3, m["duracion_s"]), 10, dest / "gancho_0-3s.jpg")]
    for t in m["cortes_s"][:14]:
        out.append(_hoja_fina(video, t - .25, t + .3, 20, dest / f"corte_{t:06.2f}.jpg"))
    return [str(x) for x in out if x]


def estudiar(estilo: str, codigo: str, avance=print) -> Path:
    carpeta = referentes.RAIZ / estilo / codigo
    if not (carpeta / "hoja.jpg").exists():
        raise FileNotFoundError(f"faltan los cuadros de {estilo}/{codigo}")
    m = medir(estilo, codigo)
    finas = hojas_finas(estilo, codigo, m)
    d = json.loads((DB / "referencias.json").read_text()).get(estilo, {})
    duenno = codigo in d.get("del_duenno", []) or any(r[0] == codigo and ("tu referencia" in str(r) or "dueño" in str(r)) for r in d.get("refs", []))
    salida = DB / estilo / "visual" / f"{codigo}.md"
    prompt = PROMPT.format(estilo=estilo, idea=d.get("idea", ""), hoja=carpeta / "hoja.jpg", carpeta=carpeta, salida=salida,
                           finas=", ".join(f"`{x}`" for x in finas),
                           medidas=json.dumps(m, ensure_ascii=False),
                           duenno="ES UNA REFERENCIA DE PABLO (el dueño): manda sobre las demás." if duenno else "Es un reel de un creador encontrado en la búsqueda.")
    avance(f"estudio visual {estilo}/{codigo}…")
    ia.llamar(prompt, "opus", config.RAIZ, herramientas="Read,Write", tope_usd=4.0, paso=f"visual-{codigo}", timeout=2400)
    return salida


SINTESIS = """Eres director de arte. Sintetiza el estilo «{estilo}» a partir de lo que se VIO en sus referentes, para que Pablo lo apruebe.
Lee TODO: los estudios cuadro a cuadro `librerias/estilos/db/{estilo}/visual/*.md` y sus medidas `*.medidas.json`; lo que Pablo marcó
en el taller (manda sobre todo): `librerias/estilos/db/{estilo}/gustos.json` y `gustos-reel.json` (si existen); la huella actual
`librerias/estilos/huellas/{estilo}.json` y el formato en `librerias/estilos/HUELLA.md`. Los reels marcados «tu referencia»/«dueño» mandan.
Nunca descartes un referente por tema o idioma. Las reglas de Pablo: `perfil/reglas.json` (el color de su toma no se cambia salvo
golpes ≤ 1,5 s; las imágenes generadas deben ser SUTILES: chicas, fundidas con el fondo, nunca un muñeco que llene la pantalla).

Escribe dos archivos:
1. `librerias/estilos/huellas/{estilo}.json` reescrita con el mismo esquema, con rangos que cubran lo visto, `tipografia` con familias
   reales de Google Fonts, `recursos_firma` solo con patrones que el motor entiende (`estudio/director/GRAMATICA.md`) y `falta_en_motor`.
2. `librerias/estilos/db/{estilo}/resumen.md` para Pablo (español simple, sin tecnicismos de programación, máx. 30 líneas):
   - **Qué es** (2 líneas) · **De qué referentes sale** (código y una línea de qué aporta cada uno; los de Pablo primero)
   - **Color** · **Letras** · **Composición** · **Apoyos e imágenes** · **Movimiento, cámara y transiciones** · **Ritmo**
   - **Lo que SÍ hace** (6 viñetas concretas) · **Lo que NO hace** (4 viñetas)
   - **Lo que no sé todavía / necesito que me digas** (2–3 preguntas cortas para Pablo)
Responde en una línea «listo»."""


def sintetizar(estilo: str, avance=print) -> Path:
    avance(f"síntesis de {estilo}…")
    ia.llamar(SINTESIS.format(estilo=estilo), "opus", config.RAIZ, herramientas="Read,Write,Glob", tope_usd=4.0,
              paso=f"sintesis-{estilo}", timeout=2400)
    return DB / estilo / "resumen.md"
