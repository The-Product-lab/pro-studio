"""Qué palabras del guion ya mostró Lemo en su película (Pablo, 09-nov, C-0014): «hay que dejar que Lemo haga y tú encima pones lo que haga falta».

Lemo hace la película COMPLETA con sus propios textos. Esto lo MIDE en código (N3), sin fiarse de lo que diga Opus:
1. recorre la película con el motor de Lemo (`estudio/textos_lemo.mjs` → `core/render/page.mjs`, sin GL) cada PASO_S y junta lo que
   devuelve `window.TEXTS(t)` (contrato de Lemo) con su tiempo en pantalla;
2. un texto cuya caja sale de la zona segura de Instagram (`config.ZONA_SEGURA`, con ZONA_TOL_PX de holgura) no cuenta: lo tapa la
   interfaz, así que esas palabras las pone el editor de textos dentro de la zona (PLANO-LEMO-APOYOS, abogado del diablo 6);
   una palabra del guion cuenta como «mostrada por Lemo» si su forma normalizada (sin tildes, minúsculas, sin signos) aparece como
   palabra de algún texto que esté en pantalla dentro de su ventana: de (inicio − ANTES_S) a (fin + DESPUES_S);
3. REGLA de las palabras vacías (de, la, que, y…; `VACIAS`): una vacía suelta no se pone sola. Cuenta como mostrada si ella misma está en
   pantalla en su ventana, O SI la palabra con contenido más cercana de su frase (a izquierda o derecha, sin cruzar una pausa de
   PAUSA_FRASE_S ni un signo de cierre) está mostrada. Una frase hecha solo de vacías no se hereda: se pone completa.
Salida `textos-lemo.json`: {palabras, mostradas_lemo, cobertura (0–1), indices_mostradas, por_palabra: [{w, s, e, mostrada, por}], textos}.
Uso: python -m estudio.textos_lemo <carpeta-del-encargo>  (con index.html de Lemo, palabras.json; escribe textos-lemo.json)"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

from . import config

LEMO = config.lemo()
# Lemo dibuja con el navegador que le baja Playwright; a un macOS viejo (13: la Mac de Pablo, 12-nov) ya no se lo baja. Si junto al
# motor hay uno propio (`laboratorio-estilos/navegador-lemo`), Lemo usa ese: lo heredan este lector y todo lo que corra el director Pro.
NAVEGADOR = config.navegador_lemo()
if NAVEGADOR.is_file():
    os.environ.setdefault("PLAYWRIGHT_CHROME", str(NAVEGADOR))
MJS = Path(__file__).resolve().parent / "textos_lemo.mjs"
PASO_S = .1                      # cada cuánto se mira qué texto hay en pantalla
PARECIDA, PARECIDA_MIN_LETRAS = .85, 5   # «worshop» en el audio y «WORKSHOP» en pantalla: misma palabra (errata de la transcripción)
ANTES_S, DESPUES_S = .6, 1.5     # ventana alrededor de cuando se dice la palabra: desde 0,6 s antes hasta 1,5 s después
PAUSA_FRASE_S = .35              # una pausa de voz de esto o más corta la frase (la vacía no hereda de la otra frase)
TIMEOUT_S = 900
ZONA_TOL_PX = 8                  # holgura de la caja de un texto de Lemo contra la zona segura
VACIAS = frozenset("""a al ante con contra de del desde e el en entre es ese esa esto esta este la las lo los le les me mi mis
 ni no o para pero por que se si sin sobre su sus te tu tus un una unos unas y ya""".split())


def norm(s: str) -> str:
    """Forma normalizada de una palabra: sin tildes, minúsculas, sin signos."""
    s = unicodedata.normalize("NFD", str(s).lower())
    return re.sub(r"[^a-z0-9ñ]", "", "".join(c for c in s if unicodedata.category(c) != "Mn"))


def _tokens(texto: str) -> set:
    return {n for n in (norm(w) for w in re.split(r"\s+", texto)) if n}


def leer_textos(carpeta: Path, lemo: Path | None = None, salida: Path | None = None) -> dict:
    """Corre el lector de Lemo sobre `carpeta/index.html` → {dur, paso, textos:[{id, text, t0, t1, x0, y0, x1, y1}]} (la caja, si Lemo la da)."""
    carpeta = Path(carpeta)
    lemo = Path(lemo or LEMO)
    node = shutil.which("node")
    if not node:
        raise RuntimeError("falta node para leer los textos de la película de Lemo")
    if not (carpeta / "index.html").exists():
        raise RuntimeError(f"{carpeta}: no hay index.html (la película de Lemo) para leer sus textos")
    out = salida or carpeta / "textos-lemo-crudo.json"
    r = subprocess.run([node, str(MJS), str(lemo), str(carpeta), str(out), "--step", str(PASO_S)], capture_output=True, text=True, timeout=TIMEOUT_S)
    if r.returncode:
        raise RuntimeError(f"no pude leer los textos de la película (código {r.returncode}): {(r.stderr or r.stdout).strip()[-400:]}")
    return json.loads(Path(out).read_text())


def en_zona(x: dict) -> bool:
    """¿El texto de Lemo se lee dentro de la zona segura? Sin caja medida (lector viejo), cuenta."""
    caja = [x.get(k) for k in ("x0", "y0", "x1", "y1")]
    if not all(isinstance(c, (int, float)) for c in caja):
        return True
    z0, w0, z1, w1 = config.ZONA_SEGURA
    return caja[0] >= z0 - ZONA_TOL_PX and caja[1] >= w0 - ZONA_TOL_PX and caja[2] <= z1 + ZONA_TOL_PX and caja[3] <= w1 + ZONA_TOL_PX


def _parecida(n: str, tokens: set) -> bool:
    """Una palabra larga cuenta como mostrada si en pantalla hay otra casi igual (la transcripción la oyó con una errata)."""
    return len(n) >= PARECIDA_MIN_LETRAS and any(len(t) >= PARECIDA_MIN_LETRAS and SequenceMatcher(None, n, t).ratio() >= PARECIDA for t in tokens)


def marcar(palabras: list, textos: list) -> list:
    """Por palabra: {w, s, e, mostrada, por} con por ∈ «lemo» (está en pantalla en su ventana), «frase» (vacía que hereda) o None."""
    ventanas = [(x["t0"], x["t1"], _tokens(x["text"])) for x in textos]
    out = []
    for p in palabras:
        n = norm(p["w"])
        a, b = p["s"] - ANTES_S, p["e"] + DESPUES_S
        propia = bool(n) and any(t0 <= b and t1 >= a and (n in tk or _parecida(n, tk)) for t0, t1, tk in ventanas)
        out.append({"w": p["w"], "s": p["s"], "e": p["e"], "mostrada": propia, "por": "lemo" if propia else None})
    for i, m in enumerate(out):                      # vacías: heredan de la palabra con contenido más cercana de su frase
        n = norm(m["w"])
        if m["mostrada"] or not n or n not in VACIAS:
            continue
        for paso in (-1, 1):
            k = i
            while 0 <= k + paso < len(out) and not m["mostrada"]:
                ant, sig = (out[k + paso], out[k]) if paso < 0 else (out[k], out[k + paso])
                if sig["s"] - ant["e"] >= PAUSA_FRASE_S or re.search(r"[.?!;:]$", ant["w"]):
                    break                            # otra frase: no hereda
                k += paso
                if norm(out[k]["w"]) not in VACIAS:
                    if out[k]["por"] == "lemo":
                        m["mostrada"], m["por"] = True, "frase"
                    break
    return out


def medir(carpeta: Path, lemo: Path | None = None) -> dict:
    """Lee la película, marca las palabras y escribe `textos-lemo.json`."""
    carpeta = Path(carpeta)
    crudo = leer_textos(carpeta, lemo)
    ps = [{"w": p["w"], "s": float(p.get("s", p.get("t0"))), "e": float(p.get("e", p.get("t1")))}
          for p in json.loads((carpeta / "palabras.json").read_text())]
    textos = [x for x in crudo["textos"] if en_zona(x)]
    pp = marcar(ps, textos)
    idx = [i for i, m in enumerate(pp) if m["mostrada"]]
    res = {"palabras": len(ps), "mostradas_lemo": len(idx), "cobertura": round(len(idx) / len(ps), 3) if ps else 0.0,
           "indices_mostradas": idx, "por_palabra": pp, "textos": textos,
           "fuera_de_zona": [x for x in crudo["textos"] if not en_zona(x)]}
    (carpeta / "textos-lemo.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))
    return res


def mostradas(carpeta: Path) -> set:
    """Índices de palabras que Lemo ya mostró, según `textos-lemo.json`."""
    return set(json.loads((Path(carpeta) / "textos-lemo.json").read_text())["indices_mostradas"])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("carpeta", type=Path)
    a = ap.parse_args(argv)
    r = medir(a.carpeta)
    print(f"Lemo mostró {r['mostradas_lemo']}/{r['palabras']} palabras ({r['cobertura'] * 100:.0f} %)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
