"""Editor 2 de la cadena «Estilos Pro» (Pablo, 08-nov y 09-nov): pone el TEXTO del guion sobre una película ya hecha (p. ej. una de Lemo).

Pablo 09-nov sobre «Julián todo animado»: «está muy bien, pero no muestra todas las palabras». Regla de siempre (07-nov): toda palabra
que se dice se ve, una sola vez. El editor 1 (Lemo) entrega la película SIN las palabras del guion (`limpio.mp4`) y el mapa de dónde
cabe texto (`mapa-texto.json`: por tramo, rectángulo libre, tinta, acento y tipo de integración). Este módulo:
1. parte la voz en bloques de 1–3 palabras (los mismos bloques que el estilo básico) y marca la palabra clave de cada bloque;
2. a cada bloque le da su lugar: el hueco libre del tramo si la letra entra con tamaño legible; si no, un pliego de papel con sombra;
3. dibuja cada palabra cuando se dice (entrada seca), con la letra del tipo de integración (grabado, rotulador, máquina, tallado);
4. compuertas (salen en `informe`): 100 % de las palabras dibujadas, todo dentro de la zona segura, letra ≥ TAM_MIN, contraste;
5. pega la capa sobre la película con ffmpeg (un solo flujo de capas por concat, sin recodificar el audio).

Uso: python -m estudio.texto_pelicula <carpeta> [--salida final.mp4] [--solo-informe] [--faltantes]
La carpeta trae la película (`pelicula.mp4`, o `limpio.mp4` en encargos viejos; la dice el `video` del mapa), `palabras.json`
([{w, s|t0, e|t1}]) y `mapa-texto.json`.

C-0014 (Pablo, 09-nov): «Lemo va a ser lo mejor que el otro editor… dejá que Lemo haga y vos encima ponés lo que haga falta». Con
`--faltantes` (modo nuevo de los Estilos Pro) Lemo ya puso sus textos; acá solo se agregan, chicas y discretas, las palabras que la
medición de `textos_lemo` no encontró en pantalla. La compuerta de cobertura es Lemo + las nuestras = 100 %.
Lo pesado (el ffmpeg final) se corre por la cola del PC cuando existe (`captions/tools/pesado.sh`). Los números viven aquí."""
import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from . import config, fuentes
from .contraste import MINIMO as CONTRASTE_MIN, razon as contraste
from .subtitulo_basico import bloques, claves

W, H = 1080, 1920
ZONA = config.ZONA_SEGURA
TAM_MAX, TAM_MIN = 104, 58             # cuerpo de la letra: lo más grande que quepa, nunca menos de TAM_MIN
TAM_MAX_FALTA, TAM_MIN_FALTA = 64, 40  # modo «solo faltantes» (C-0014): chicas y discretas, Lemo ya puso lo grande
COLA_FALTA = .6                        # en ese modo el bloque se va esta cola después de su última palabra (no espera al siguiente)
INTERLINEA = 1.08
MARGEN = 18                            # aire dentro del hueco libre
PLIEGO = (110, 1130, 970, 1470)        # pliego por defecto cuando el tramo no trae uno (abajo, dentro de la zona)
PLIEGO_PAD = (44, 30)
PLIEGO_COLOR, PLIEGO_FILETE = (239, 230, 210), (60, 48, 38)
SOMBRA = (14, 10, 120)                 # blur, desplazamiento y, opacidad de la sombra del pliego
TALLADO_FONDO, TALLADO_TINTA = (24, 20, 17), (243, 234, 216)
ADELANTO = .03                         # la palabra aparece apenas antes de decirse
COLA = .25                             # el bloque se queda hasta que entra el siguiente, como mucho esta cola tras su última palabra
PESADO = config.pesado() or config.TPS / "sin-cola-pesado"

FUENTES = Path(__file__).resolve().parent.parent / "librerias" / "fuentes"
LETRA = {"grabado": ("EBGaramond[wght].ttf", 800, True), "rotulador": ("CoveredByYourGrace.ttf", None, False),
         "maquina": ("CourierPrime-Bold.ttf", None, False), "tallado": ("EBGaramond[wght].ttf", 800, True)}


def _tipo(integracion: str) -> str:
    s = (integracion or "").lower()
    if "tallado" in s:
        return "tallado"
    if "máquina" in s or "maquina" in s or "tipos" in s or "sello" in s:
        return "maquina"
    if s.startswith("rotulador"):
        return "rotulador"
    return "grabado"


def _fuente(tipo: str, tam: int):
    archivo, peso, _ = LETRA[tipo]
    f = fuentes.abrir(FUENTES / archivo, tam)
    if peso:
        try:
            f.set_variation_by_axes([peso])
        except (OSError, AttributeError):
            pass
    return f


def _rgb(c, defecto=(28, 21, 16)):
    if not c:
        return defecto
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def _palabras(carpeta: Path) -> list:
    ps = json.loads((carpeta / "palabras.json").read_text())
    return [{"w": p["w"], "s": float(p.get("s", p.get("t0"))), "e": float(p.get("e", p.get("t1")))} for p in ps]


def _tramo(mapa: dict, t: float) -> dict:
    tr = mapa["tramos"]
    dentro = [x for x in tr if x["t0"] - .05 <= t <= x["t1"] + .05]
    return dentro[0] if dentro else min(tr, key=lambda x: min(abs(x["t0"] - t), abs(x["t1"] - t)))


def _medir(toks: list, f, ancho: float) -> list:
    """Líneas [[(k, ancho_palabra)]] que caben en `ancho`; None si una palabra sola no entra."""
    esp, out, cur, a_cur = f.getlength(" "), [], [], 0.0
    for k, w in enumerate(toks):
        a = f.getlength(w)
        if a > ancho:
            return None
        if cur and a_cur + esp + a > ancho:
            out.append(cur)
            cur, a_cur = [], 0.0
        a_cur += (esp if cur else 0) + a
        cur.append((k, a))
    return out + [cur] if cur else out


def _encajar(toks: list, tipo: str, caja, tam_max: int = TAM_MAX, tam_min: int = TAM_MIN) -> tuple:
    """Mayor tamaño (≤ tam_max, ≥ tam_min) con el que el bloque entra en la caja; (None, None, None) si no entra."""
    ancho, alto = caja[2] - caja[0] - 2 * MARGEN, caja[3] - caja[1] - 2 * MARGEN
    for tam in range(tam_max, tam_min - 1, -2):
        f = _fuente(tipo, tam)
        ls = _medir(toks, f, ancho)
        if ls and len(ls) * tam * INTERLINEA <= alto:
            return tam, f, ls
    return None, None, None


def _recorte(c) -> tuple:
    return (max(c[0], ZONA[0]), max(c[1], ZONA[1]), min(c[2], ZONA[2]), min(c[3], ZONA[3]))


def _bloques_faltantes(ps: list, lemo: set) -> list:
    """Bloques [i0, i1) SOLO con las palabras que Lemo no mostró: cada racha de palabras seguidas se parte con las reglas de siempre."""
    out, run = [], []
    for j in range(len(ps) + 1):
        if j < len(ps) and j not in lemo:
            run.append(j)
            continue
        if run:
            out += [[run[0] + a, run[0] + b] for a, b in bloques(ps[run[0]:run[-1] + 1])]
            run = []
    return out


def planear(carpeta: Path, lemo: set | None = None) -> dict:
    """Plan del texto: por bloque, dónde va, con qué letra, tinta y tamaño. Puro (no dibuja).
    `lemo` = índices de palabras que Lemo ya mostró en su película (`textos_lemo`): modo «solo faltantes» (C-0014), bloques chicos solo
    con las que faltan, en el mismo orden y tiempo. Sin `lemo`: todas las palabras (encargos viejos con `limpio.mp4`)."""
    mapa = json.loads((carpeta / "mapa-texto.json").read_text())
    ps = _palabras(carpeta)
    falta = lemo is not None
    tam_max, tam_min = (TAM_MAX_FALTA, TAM_MIN_FALTA) if falta else (TAM_MAX, TAM_MIN)
    bl = _bloques_faltantes(ps, lemo) if falta else bloques(ps)
    resaltar = set(claves(ps, bl))
    plan = []
    for n, (i0, i1) in enumerate(bl):
        tr = _tramo(mapa, (ps[i0]["s"] + ps[i1 - 1]["e"]) / 2)
        tipo = _tipo(tr.get("integracion"))
        tinta, acento = _rgb(tr.get("tinta")), _rgb(tr.get("acento"), (194, 67, 42))
        mayus = LETRA[tipo][2]
        toks = [(ps[j]["w"].upper() if mayus else ps[j]["w"]) for j in range(i0, i1)]
        lugar, fondo = "libre", (int(tr.get("fondo_luma") or 0),) * 3
        tam = f = ls = None
        if tr.get("libre"):
            caja = _recorte(tuple(tr["libre"][k] for k in ("x0", "y0", "x1", "y1")))
            tam, f, ls = _encajar(toks, tipo, caja, tam_max, tam_min)
        if tipo == "tallado" and tam:
            lugar, fondo, tinta = "tallado", TALLADO_FONDO, TALLADO_TINTA
        if not tam or contraste(tinta, fondo) < CONTRASTE_MIN:
            sp = tr.get("sobre_pliego") or {}
            caja = _recorte(tuple(sp[k] for k in ("x0", "y0", "x1", "y1"))) if sp else PLIEGO
            if tipo == "tallado":
                tipo = "grabado"
            tam, f, ls = _encajar(toks, tipo, caja, tam_max, tam_min)
            lugar, fondo, tinta = "pliego", PLIEGO_COLOR, _rgb(tr.get("tinta"))
        fin = ps[bl[n + 1][0]]["s"] - ADELANTO if n + 1 < len(bl) else ps[i1 - 1]["e"] + COLA
        if falta:
            fin = min(fin, ps[i1 - 1]["e"] + COLA_FALTA)
        plan.append({"i0": i0, "i1": i1, "t0": ps[i0]["s"] - ADELANTO, "t1": fin, "lugar": lugar, "tipo": tipo,
                     "caja": list(caja), "tam": tam, "lineas": [[k for k, _ in l] for l in ls] if ls else None,
                     "tinta": list(tinta), "acento": list(acento), "fondo": list(fondo),
                     "claves": [j - i0 for j in range(i0, i1) if j in resaltar], "toks": toks, "tam_min": tam_min,
                     "ts": [ps[j]["s"] for j in range(i0, i1)]})
    return {"palabras": ps, "plan": plan, "video": mapa.get("video", "limpio.mp4"), "lemo": sorted(lemo or ())}


def informe(pl: dict) -> dict:
    """Compuertas del texto. ok=False si alguna falla; cada falla dice el bloque y el dato. Cobertura: lo de Lemo + lo nuestro = 100 %."""
    ps, plan, fallas = pl["palabras"], pl["plan"], []
    lemo = set(pl.get("lemo", ()))
    vistas = set()
    for b in plan:
        if not b["tam"] or not b["lineas"]:
            fallas.append(f"bloque «{' '.join(b['toks'])}» no entra ni en el pliego")
            continue
        vistas.update(range(b["i0"], b["i1"]))
        x0, y0, x1, y1 = b["caja"]
        if x0 < ZONA[0] or y0 < ZONA[1] or x1 > ZONA[2] or y1 > ZONA[3]:
            fallas.append(f"bloque «{' '.join(b['toks'])}» fuera de la zona segura {b['caja']}")
        if b["tam"] < b.get("tam_min", TAM_MIN):
            fallas.append(f"bloque «{' '.join(b['toks'])}» con letra {b['tam']} < {b.get('tam_min', TAM_MIN)}")
        c = contraste(b["tinta"], b["fondo"])
        if c < CONTRASTE_MIN:
            fallas.append(f"bloque «{' '.join(b['toks'])}» contraste {c:.1f} < {CONTRASTE_MIN}")
    faltan = [ps[j]["w"] for j in range(len(ps)) if j not in vistas and j not in lemo]
    if faltan:
        fallas.append(f"{len(faltan)} palabras sin mostrar: {' '.join(faltan[:12])}")
    return {"ok": not fallas, "palabras": len(ps), "mostradas": len(vistas | lemo), "lemo": len(lemo), "agregadas": len(vistas - lemo),
            "bloques": len(plan),
            "en_pliego": sum(b["lugar"] == "pliego" for b in plan), "fallas": fallas}


def _capa(b: dict, hasta: int) -> Image.Image:
    """La capa de un bloque con sus primeras `hasta` palabras dichas (el bloque ya está medido: nada se corre)."""
    img = Image.new("RGBA", (W, H))
    x0, y0, x1, y1 = b["caja"]
    f = _fuente(b["tipo"], b["tam"])
    esp, alto_l = f.getlength(" "), b["tam"] * INTERLINEA
    anchos = {k: f.getlength(b["toks"][k]) for l in b["lineas"] for k in l}
    alto_t = alto_l * len(b["lineas"])
    ancho_t = max(sum(anchos[k] for k in l) + esp * (len(l) - 1) for l in b["lineas"])
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    if b["lugar"] in ("pliego", "tallado"):
        px, py = PLIEGO_PAD
        r = _recorte((int(cx - ancho_t / 2 - px), int(cy - alto_t / 2 - py), int(cx + ancho_t / 2 + px), int(cy + alto_t / 2 + py)))
        if b["lugar"] == "pliego":
            blur, off, op = SOMBRA
            sh = Image.new("L", (W, H))
            ImageDraw.Draw(sh).rectangle((r[0], r[1] + off, r[2], r[3] + off), fill=op)
            sombra = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            sombra.putalpha(sh.filter(ImageFilter.GaussianBlur(blur)))
            img.alpha_composite(sombra)
        d = ImageDraw.Draw(img)
        fondo = tuple(b["fondo"]) + (255,)
        d.rectangle(r, fill=fondo)
        if b["lugar"] == "pliego":
            d.rectangle((r[0] + 8, r[1] + 8, r[2] - 8, r[3] - 8), outline=PLIEGO_FILETE + (200,), width=2)
            d.rectangle((r[0] + 13, r[1] + 13, r[2] - 13, r[3] - 13), outline=PLIEGO_FILETE + (120,), width=1)
    d = ImageDraw.Draw(img)
    for n, l in enumerate(b["lineas"]):
        ancho_l = sum(anchos[k] for k in l) + esp * (len(l) - 1)
        x, y = cx - ancho_l / 2, cy - alto_t / 2 + alto_l * n + alto_l / 2
        for k in l:
            if k < hasta:
                color = tuple(b["acento"] if k in b["claves"] else b["tinta"]) + (255,)
                d.text((x, y), b["toks"][k], font=f, fill=color, anchor="lm")
            x += anchos[k] + esp
    return img


def capas(pl: dict, dur: float, carpeta: Path) -> Path:
    """Escribe las capas (una por cambio: cada palabra que entra) y su lista de concat con duraciones exactas."""
    cambios = []
    for b in pl["plan"]:
        for k, ts in enumerate(b["ts"]):
            cambios.append((max(0.0, ts - ADELANTO) if k else max(0.0, b["t0"]), b, k + 1))
        cambios.append((b["t1"], None, 0))
    cambios.sort(key=lambda c: c[0])
    vacia = carpeta / "c_vacia.png"
    Image.new("RGBA", (W, H)).save(vacia)
    lista, t_prev, img_prev = [], 0.0, vacia
    for n, (t, b, hasta) in enumerate(cambios):
        t = min(max(t, t_prev), dur)
        if t > t_prev:
            lista.append(f"file '{img_prev}'\nduration {t - t_prev:.4f}")
        if b is None:
            img_prev = vacia
        else:
            p = carpeta / f"c_{n:04d}.png"
            _capa(b, hasta).save(p)
            img_prev = p
        t_prev = t
    if dur > t_prev:
        lista.append(f"file '{img_prev}'\nduration {dur - t_prev:.4f}")
    lista.append(f"file '{img_prev}'")
    (carpeta / "capas.txt").write_text("\n".join(lista) + "\n")
    return carpeta / "capas.txt"


def _dur(video: Path) -> float:
    return float(subprocess.run([config.ffmpeg()[1], "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(video)],
                                capture_output=True, text=True, check=True).stdout.strip())


def componer(carpeta: Path, salida: Path, lemo: set | None = None) -> dict:
    pl = planear(carpeta, lemo)
    inf = informe(pl)
    (carpeta / "texto-informe.json").write_text(json.dumps({**inf, "plan": [{k: v for k, v in b.items() if k != "ts"} for b in pl["plan"]]},
                                                           ensure_ascii=False, indent=1))
    if not inf["ok"]:
        return inf
    video = carpeta / pl["video"]
    tmp = Path(tempfile.mkdtemp(prefix="texto-pelicula-"))
    try:
        lista = capas(pl, _dur(video), tmp)
        cmd = [config.ffmpeg()[0], "-v", "error", "-y", "-i", str(video), "-f", "concat", "-safe", "0", "-i", str(lista),
               "-filter_complex", "[1:v]format=rgba,fps=30[t];[0:v][t]overlay=0:0:format=auto:shortest=1[v]",
               "-map", "[v]", "-map", "0:a?", "-c:v", "libx264", "-crf", "16", "-preset", "medium", "-pix_fmt", "yuv420p",
               "-c:a", "copy", "-movflags", "+faststart", str(salida)]
        if PESADO.exists():
            cmd = [str(PESADO)] + cmd
        subprocess.run(cmd, check=True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return inf


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("carpeta", type=Path)
    ap.add_argument("--salida", type=Path)
    ap.add_argument("--solo-informe", action="store_true")
    ap.add_argument("--faltantes", action="store_true", help="solo las palabras que Lemo no mostró (lee textos-lemo.json de la carpeta)")
    a = ap.parse_args(argv)
    lemo = None
    if a.faltantes:
        from .textos_lemo import mostradas
        lemo = mostradas(a.carpeta)
    if a.solo_informe:
        inf = informe(planear(a.carpeta, lemo))
    else:
        inf = componer(a.carpeta, a.salida or a.carpeta / "con-texto.mp4", lemo)
    print(json.dumps({k: v for k, v in inf.items()}, ensure_ascii=False, indent=1))
    return 0 if inf["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
