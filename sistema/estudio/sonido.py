"""Sonido: voz cortada igual que la imagen (−14 LUFS) + efectos que salen solos del storyboard (plano: docs/PLANO-SONIDO.md).

Suenan solo los eventos que importan (corte, texto principal, apoyo, trazo, punch), con densidad tope, alineados por su pico al
evento, con la paleta del estilo (`estilo.sonido_paleta`: suave | papel | digital | cine) y el volumen `estilo.sfx` (0 = mudo).
Si el banco CC0 está vacío, se sintetizan."""
import subprocess
import wave
from bisect import bisect_left

import numpy as np

from . import camara, config

SR = 48000


def _lp(x, a):
    y, acc = np.empty_like(x), 0.0
    a = np.broadcast_to(a, x.shape)
    for i in range(len(x)):
        acc += a[i] * (x[i] - acc)
        y[i] = acc
    return y


def _whoosh(rng, d=.42):
    n = int(SR * d)
    t = np.linspace(0, 1, n)
    y = _lp(rng.normal(0, 1, n), .02 + .25 * np.sin(np.pi * t) ** 2) * np.sin(np.pi * t) ** 1.5
    return y / np.abs(y).max() * .5


def _pop(rng):
    n = int(SR * .18)
    t = np.arange(n) / SR
    click = rng.normal(0, 1, n) * np.exp(-t / .008)
    click -= _lp(click, .15)
    y = .5 * click + .8 * np.sin(2 * np.pi * (140 * t - 120 * t ** 2)) * np.exp(-t / .05)
    return y / np.abs(y).max() * .55


def _golpe(rng):
    n = int(SR * .7)
    t = np.arange(n) / SR
    ph = 2 * np.pi * np.cumsum(45 + 80 * np.exp(-t / .06)) / SR
    y = np.sin(ph) * np.exp(-t / .22) + .25 * _lp(rng.normal(0, 1, n), .05) * np.exp(-t / .05)
    return y / np.abs(y).max() * .7


def _marcador(rng, d=.5):
    n = int(SR * d)
    t = np.arange(n) / SR
    x = rng.normal(0, 1, n)
    y = (x - _lp(x, .35)) * (.55 + .45 * np.sin(2 * np.pi * 11 * t) ** 2) * np.minimum(t / .04, 1) * np.exp(-t / .25)
    return y / np.abs(y).max() * .22


# ---------- qué suena (reglas del curso de Julián, BASES-EDITOR §4: «sutil; si se notan, sobran») ----------
# categoría de evento → (importancia, ganancia). Lo chico (etiquetas, píxeles, textos secundarios) no suena.
CATEGORIAS = {"golpe": (4, 1.0), "corte": (3, .85), "corte-glitch": (3, .8), "texto": (2, .65), "apoyo": (1, .5), "trazo": (1, .7),
              "camara": (2, .55)}   # cada movimiento de cámara suena (referente de Pablo 07-nov: whoosh al moverse)
SEPARACION_MIN, MAX_POR_SEGUNDO = .18, 2     # nunca dos efectos pegados ni más de 2 en un segundo (Pablo: «satura»)
# paleta por estilo (Pablo, 25-oct: «el estilo de SFX depende del estilo de edición»): categoría → tipos del banco
PALETAS = {
    "suave": {"corte": ["whoosh", "swish"], "corte-glitch": ["glitch"], "texto": ["pop"], "apoyo": ["swish"], "trazo": ["slide"],
              "golpe": ["impact"]},
    "papel": {"corte": ["slide", "swish"], "corte-glitch": ["slide"], "texto": ["click"], "apoyo": ["slide"], "trazo": ["slide"],
              "golpe": ["impact", "metal"]},
    "digital": {"corte": ["zap", "swish"], "corte-glitch": ["glitch"], "texto": ["tick", "click"], "apoyo": ["click"], "trazo": ["slide"],
                "golpe": ["impact", "boom"]},
    "cine": {"corte": ["whoosh"], "corte-glitch": ["whoosh"], "texto": [], "apoyo": ["whoosh"], "trazo": [], "golpe": ["boom"]},
    # grabados y escuchados por el Taller (sfx.traer_organicos), Pablo 07-nov: «suenan sintéticos, falsos»
    "organico": {"corte": ["whoosh-corto", "swish"], "corte-glitch": ["whoosh-largo"], "texto": ["papel-mov", "tela"],
                 "apoyo": ["papel-apoya", "periodico-hoja"], "trazo": ["marcador", "lapiz-check"], "golpe": ["golpe-corto", "sub-drop"], "camara": ["swish", "whoosh-largo"]},
}
# paleta por defecto de cada estilo (propuesta; Pablo la cambia en Personalizar › Sonido o con `estilo.sonido_paleta`)
PALETAS["papel-maquina"] = {**PALETAS["organico"], "texto": ["papel-mov", "click-maquina"]}   # papel grabado + click de máquina de escribir REAL (Pablo 10-nov: Imprenta, Julián)
PALETA_DE_ESTILO = {"cine": "cine"}   # todo lo demás suena con el banco orgánico (Pablo 07-nov: «más vida, más orgánico»)


def paleta_de(estilo: dict) -> str:
    return estilo.get("sonido_paleta") or PALETA_DE_ESTILO.get(str(estilo.get("id", "")).split("-")[0], "organico")


SINTE = {"camara": "whoosh-corto", "corte": "whoosh", "corte-glitch": "pop", "texto": "pop", "apoyo": "whoosh-corto", "trazo": "marcador", "golpe": "golpe"}


def _principal(e) -> bool:
    l0 = (e.d.get("lineas") or [{}])[0]
    tam = l0.get("tam", 0) if isinstance(l0, dict) else (l0[1] if isinstance(l0, list) and len(l0) > 1 else 0)
    return tam >= 90


def eventos(p):
    """[(tiempo_fuente, categoría o tipo, ganancia, importancia)] del storyboard. Si trae `sonido` escrito a mano, se usa ese tal cual."""
    sb = p.sb
    if "sonido" in sb:
        return [(e["t"], e["tipo"], e.get("ganancia", 1.0), 9) for e in sb["sonido"]]
    ev = []
    for e in p.escenas[1:]:
        cat = "corte-glitch" if e.get("entrada") in ("rafaga", "pixel", "bloques", "invertir") else "corte"
        ev.append((e["t0"], cat))
    for e in p.elementos:
        tipo = e.d.get("tipo")
        if tipo in ("foto", "recorte", "clip", "vidrio", "panel"):
            ev.append((e.t0, "apoyo"))
        elif tipo in ("texto", "etiqueta") and _principal(e):
            ev.append((e.t0, "texto"))
    ev += [(tr.t0, "trazo") for tr in p.trazos]
    if not camara.fija():   # con la cámara fija no hay golpe de zoom ni movimiento que suene
        ev += [(t, "golpe") for t in sb.get("punch", [])]
        ev += [(c["t"], "camara") for c in (sb.get("camara") or [])[1:] if isinstance(c, dict) and "t" in c]  # cada movimiento suena
    return [(t, c, CATEGORIAS[c][1], CATEGORIAS[c][0]) for t, c in ev]


def depurar(ev_salida: list) -> list:
    """Densidad: [(t_salida, tipo, g, imp)] → los que quedan, priorizando lo importante. Lo escrito a mano (imp 9) no se toca."""
    quedan = []
    for ev in sorted(ev_salida, key=lambda e: (-e[3], e[0])):
        t = ev[0]
        if ev[3] < 9:
            if any(abs(t - q[0]) < SEPARACION_MIN for q in quedan):
                continue
            cerca = sorted([q[0] for q in quedan if abs(t - q[0]) < 1] + [t])   # ningún segundo con más de MAX_POR_SEGUNDO
            if any(sum(1 for y in cerca if x <= y < x + 1) > MAX_POR_SEGUNDO for x in cerca):
                continue
        quedan.append(ev)
    return sorted(quedan)


ORGANICO = config.RAIZ / "librerias" / "sonido" / "organico"   # grabados CC0 escuchados por el Taller (`estudio sfx organicos`)
BANCO = config.RAIZ / "librerias" / "sonido" / "sfx"   # efectos GRABADOS (CC0); `estudio sfx traer` lo llena
# tipo escrito a mano en el storyboard → tipos del banco (se rotan para que no suene siempre igual)
DEL_BANCO = {"whoosh": ["whoosh", "swish"], "whoosh-corto": ["swish"], "pop": ["pop"], "golpe": ["impact", "boom"],
             "marcador": ["slide"], "glitch": ["glitch", "zap"], "click": ["click", "tick"], "riser": ["riser"]}
def _leer_wav(ruta):
    """WAV del banco → mono float a 48 kHz (los del banco ya vienen a 48 kHz; si no, se re-muestrea simple)."""
    with wave.open(str(ruta)) as w:
        n, ch, sr, ancho = w.getnframes(), w.getnchannels(), w.getframerate(), w.getsampwidth()
        x = np.frombuffer(w.readframes(n), {2: np.int16, 4: np.int32}.get(ancho, np.int16)).astype(np.float32)
    x = x.reshape(-1, ch).mean(1) / (32768 if ancho == 2 else 2 ** 31)
    if sr != SR:
        x = np.interp(np.arange(int(len(x) * SR / sr)) * sr / SR, np.arange(len(x)), x)
    pico = np.abs(x).max() or 1
    return x / pico * .6


def banco() -> dict:
    """{tipo: [rutas]} de lo que hay en el banco (vacío si no hay banco: entonces se sintetiza). Suma el banco orgánico
    (`librerias/sonido/organico/<categoría>/`), cuyas categorías son los tipos de la paleta «organico»."""
    out = {}
    if BANCO.exists():
        for f in sorted(BANCO.glob("*.wav")):
            out.setdefault(f.stem.split("_")[0], []).append(f)
    if ORGANICO.exists():
        for d in sorted(x for x in ORGANICO.iterdir() if x.is_dir()):
            out.setdefault(d.name, []).extend(sorted(d.glob("*.wav")))
    return out


def _pico(x) -> int:
    """Muestra donde el efecto suena más fuerte: el efecto se coloca para que su pico caiga EN el evento (el sonido que causa
    algo va antes de la reacción, BASES-EDITOR §4.5; el whoosh culmina en el corte)."""
    env = np.convolve(np.abs(x), np.ones(240) / 240, "same")
    return int(env.argmax())


def efectos(p, dur_salida, informe=None):
    rng = np.random.default_rng(3)
    sinte = {"whoosh": lambda: _whoosh(rng), "whoosh-corto": lambda: _whoosh(rng, .3), "pop": lambda: _pop(rng),
             "golpe": lambda: _golpe(rng), "marcador": lambda: _marcador(rng), "glitch": lambda: _pop(rng),
             "click": lambda: _pop(rng), "riser": lambda: _whoosh(rng, .8)}
    paleta = PALETAS.get(paleta_de(p.sb.get("estilo", {})), PALETAS["suave"])
    grabados, cache, vuelta = banco(), {}, {}

    def del_banco(tipos, clave):
        rutas = [r for t in tipos for r in grabados.get(t, [])]
        if not rutas:
            return None
        k = vuelta.get(clave, 0)
        vuelta[clave] = k + 1
        r = rutas[k % len(rutas)]
        if r not in cache:
            cache[r] = _leer_wav(r)
        return cache[r]

    def sonido(tipo):
        if tipo in CATEGORIAS:
            tipos = paleta.get(tipo, [])
            if not tipos and tipo in paleta:      # la paleta calla esa categoría (ej. cine no suena en cada texto)
                return None
            x = del_banco(tipos, tipo)
            return x if x is not None else sinte[SINTE[tipo]]()
        x = del_banco(DEL_BANCO.get(tipo, []), tipo)
        return x if x is not None else sinte.get(tipo, sinte["pop"])()

    ev = []
    for t, tipo, g, imp in eventos(p):
        of = bisect_left(p.mapa, round(t * config.FPS))
        if of < len(p.mapa):
            ev.append((of / config.FPS, tipo, g, imp))
    ev = depurar(ev)
    out = np.zeros(int(SR * dur_salida) + SR)

    def poner(sig, ts, g):
        i = max(0, int(ts * SR) - _pico(sig))
        out[i:i + len(sig)] += sig[:len(out) - i] * g

    puestos = []
    for ts, tipo, g, _ in ev:
        sig = sonido(tipo)
        if sig is None:
            continue
        g *= 10 ** (rng.uniform(-1.5, 1.5) / 20)      # variación: que no suene a máquina
        poner(sig, ts, g)
        if tipo == "golpe":                            # capas en el impacto (§4.3): swish que lo anuncia + grave
            pre = del_banco(["swish"], "capa-swish")
            if pre is not None:
                poner(pre, ts - .06, .35 * g)
            grave = del_banco(["boom"], "capa-boom")
            if grave is not None:
                poner(grave, ts, .5 * g)
        puestos.append(round(ts, 3))
    if informe is not None:
        sep = min((b - a for a, b in zip(puestos, puestos[1:])), default=None)
        por_seg = max((sum(1 for y in puestos if x <= y < x + 1) for x in puestos), default=0)
        informe.update({"efectos": len(puestos), "por_minuto": round(len(puestos) / max(dur_salida, 1) * 60, 1),
                        "menor_separacion_s": None if sep is None else round(sep, 3), "max_en_un_segundo": por_seg,
                        "paleta": paleta_de(p.sb.get("estilo", {})), "tiempos": puestos})
    return out[:int(SR * dur_salida)]


def _tramos(p):
    """Tramos de la fuente que se conservan, en segundos."""
    tramos, ini = [], None
    for k, src in enumerate(p.mapa):
        if ini is None:
            ini = src
        if k + 1 == len(p.mapa) or p.mapa[k + 1] != src + 1:
            tramos.append((ini / config.FPS, (src + 1) / config.FPS))
            ini = None
    return tramos


def mezclar(p, mudo, salida, volumen_sfx=config.SFX_VOLUMEN):
    ffmpeg, _ = config.ffmpeg()
    dur = len(p.mapa) / config.FPS
    sfx = p.dir / "sfx.wav"
    informe = {"volumen": volumen_sfx}
    pcm = (np.clip(efectos(p, dur, informe), -1, 1) * 32767).astype(np.int16)
    (p.dir / "sfx-informe.json").write_text(__import__("json").dumps(informe, ensure_ascii=False, indent=1))
    with wave.open(str(sfx), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    tramos = _tramos(p)
    partes = "".join(f"[1:a]atrim={a:.4f}:{b:.4f},asetpts=PTS-STARTPTS[v{i}];" for i, (a, b) in enumerate(tramos))
    unir = "".join(f"[v{i}]" for i in range(len(tramos))) + f"concat=n={len(tramos)}:v=0:a=1[voz0];"
    filtro = (partes + unir +
              "[voz0]highpass=f=80,acompressor=threshold=-20dB:ratio=3:attack=5:release=80,"
              "loudnorm=I=-14:TP=-1.5:LRA=9,aresample=48000[voz];"
              f"[2:a]volume={volumen_sfx}[s];[voz][s]amix=inputs=2:normalize=0:duration=first,alimiter=limit=0.89[a]")
    try:
        subprocess.run([ffmpeg, "-v", "error", "-y", "-i", str(mudo), "-i", p.meta["video"], "-i", str(sfx),
                        "-filter_complex", filtro, "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "256k",
                        "-shortest", "-movflags", "+faststart", str(salida)], check=True)
    finally:
        sfx.unlink(missing_ok=True)          # el wav de efectos es un intermedio: ya está dentro del video, no se acumula en el proyecto
