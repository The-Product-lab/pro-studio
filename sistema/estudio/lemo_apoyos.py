"""Lemo dentro del reel hablado (docs/PLANO-LEMO-APOYOS.md): el director nuestro marca los tramos del reel (`arte.json` con
`clip: true`) y Lemo hace en ellos lo que quiera, en su estilo: apoyos de pantalla completa (fondos, figuras, personas), textos,
un universo que atraviese varios tramos, o nada. El código solo le da el contrato técnico, mide lo que entrega, deja las escenas como él las entregó
y completa en TODO el reel las palabras que no mostró, en su estilo (cadena de Estilos Pro: `textos_lemo` → `mapa_texto` →
`texto_pelicula`, y el gancho y el subtítulo nuestros con su acento y su letra). No es otro motor: entra por donde entra Higgsfield
(`arte/<id>`), y el render, el sonido y la cola son los de siempre.

Pablo (12-nov): «Lemus puede hacer de todo, pero pues no es una camisa de fuerza, o sea, tú tienes que ver dónde puso los textos y
tú revisas qué faltaron y las pones tú en el estilo mismo de Lemus.»
Pablo (12-nov, tras ver la prueba): los tramos que Lemo dibujó sobre la persona (texto sobre negro) no van; «las quiero con diseño
de Lemo como lo otro, fondos bacanos, figuras de personas»: todo tramo de Lemo es de pantalla completa (la compuerta de cuadros
negros lo mide). Cada tramo es un encargo aparte y corto, para que Lemo no relea en cada paso lo de los demás («mira cómo puedes
hacer para que él no tenga que releer todo»)."""
import copy
import json
import shutil
import subprocess
from pathlib import Path

import numpy as np

from . import config, ia as _ia, machote, mapa_texto, persona, pro, texto_pelicula, textos_lemo

PROMPT = Path(__file__).resolve().parent / "director" / "lemo_apoyos.md"
ESTILO = "lemo"                      # el id del estilo del director (preset, guía y ejemplo) cuando el arte lo hace Lemo
TRABAJO = "lemo"                     # proyectos/<p>/lemo/<id>/: lo que entrega Lemo por tramo
CLASES = ("completo",)               # lo que Lemo puede entregar en un tramo; «nada» = decidió no hacerlo
NADA = "nada"
DUR_TOL_S = .1
EPS = 1e-3
TOPE_USD_APOYO, TIMEOUT_APOYO_S = 8.0, 40 * 60    # por tramo ofrecido; el reintento usa la mitad
TOPE_USD_REEL = 48.0                 # techo del encargo entero: el director ya no tiene tope de tramos
VACIO_LUMA, VACIO_FRAC, VACIO_MAX_S = 20, .85, .5   # cuadro «vacío»: ≥85 % de píxeles con luma <20; más de 0,5 s así = texto sobre negro
MUESTRAS_POR_S = 4
# La letra de nuestros textos (gancho, subtítulo) según la integración que más dura en los `plano.json` de Lemo: las mismas
# familias con las que `texto_pelicula` completa dentro de su película (LETRA), por su nombre en librerias/fuentes/indice.json.
FUENTE_DE = {"grabado": "EB Garamond", "tallado": "EB Garamond", "rotulador": "Covered By Your Grace", "maquina": "Courier Prime"}


def elegir(carpeta: Path, estilo: str) -> str:
    """Lo que llega de la pantalla → el id de estilo del director. «lemo:<slug>» deja anotado el estilo de Lemo de ESTE video
    (`preferencias.json › estilo.lemo`, que `director._fijar_estilo` pasa al storyboard) y devuelve «lemo»; cualquier otro estilo
    borra esa nota, para que un video que deja a Lemo no le siga pidiendo el arte."""
    slug = estilo[len(ESTILO) + 1:] if estilo.startswith(ESTILO + ":") else None
    if slug is not None and not (pro.LEMO / "styles" / slug / "STYLE.md").exists():
        raise ValueError(f"estilo de Lemo desconocido: «{slug}»")
    f = Path(carpeta) / "preferencias.json"
    prefs = json.loads(f.read_text()) if f.exists() else {}
    antes = (prefs.get("estilo") or {}).get("lemo")
    if slug != antes:
        est = {k: v for k, v in (prefs.get("estilo") or {}).items() if k != "lemo"}
        prefs["estilo"] = {**est, **({"lemo": slug} if slug else {})}
        machote._guardar(f, prefs)
    return ESTILO if slug else estilo


def slug_de(carpeta: Path):
    """El estilo de Lemo elegido para este video, o None."""
    f = Path(carpeta) / "preferencias.json"
    try:
        return (json.loads(f.read_text()).get("estilo") or {}).get("lemo") or None
    except (OSError, ValueError):
        return None


def nota_del_estilo(slug: str) -> str:
    """Para el director nuestro: cuál es el estilo de Lemo de este video (su ficha), para que sus textos sean de esa familia."""
    try:
        d = json.loads((pro.LEMO / "styles" / slug / "style.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ""
    return (f"\n\n## El estilo de Lemo de este video: «{d.get('en', slug)}» ({d.get('category_en', '')})\n{d.get('line', '')}\n"
            f"Se usa para: {', '.join(d.get('uses', []))}. Sus colores y su letra los trae Lemo con lo que entrega; el acento y la "
            "letra de tus textos se cambian solos por los suyos.")


def _cortada(p: dict, cortes: list) -> bool:
    return any(a <= (p["s"] + p["e"]) / 2 < b for a, b in cortes)


def _palabras(carpeta: Path) -> list:
    return [{**p, "s": float(p.get("s", p.get("t0"))), "e": float(p.get("e", p.get("t1")))}
            for p in json.loads((Path(carpeta) / "palabras.json").read_text())]


def pedidos(carpeta: Path) -> list:
    """Los tramos que el director le ofrece a Lemo: [{id, clase, t0, t1, dur, idea, palabras, indices, cara}]. Todos «completo»
    (pantalla llena; Lemo puede dejar uno en «nada»). Las palabras van en segundos
    desde t0, sin las que el machote cortó; `indices` son sus posiciones en `palabras.json`. La caja de la cara va siempre."""
    carpeta = Path(carpeta)
    arte, sb_p = carpeta / "arte.json", carpeta / "storyboard.json"
    if not arte.exists() or not sb_p.exists():
        return []
    sb = json.loads(sb_p.read_text())
    cortes = sb.get("cortes", [])
    ps = [(i, p) for i, p in enumerate(_palabras(carpeta)) if not _cortada(p, cortes)]
    tabla, out = persona.Tabla(carpeta), []
    for p in json.loads(arte.read_text()):
        if not p.get("clip"):
            continue
        el = next((e for e in sb.get("elementos", []) if isinstance(e, dict) and e.get("src") == f"arte/{p['id']}.mp4"), None)
        if el is None:
            continue
        t0, t1 = float(el["t0"]), float(el["t1"])
        dentro = [(i, w) for i, w in ps if t0 <= w["s"] < t1]
        out.append({"id": p["id"], "clase": "completo",
                    "t0": t0, "t1": t1, "dur": round(t1 - t0, 2), "idea": p.get("idea", ""),
                    "palabras": [{"w": pro.nombre(w["w"]), "s": round(w["s"] - t0, 3), "e": round(w["e"] - t0, 3)} for _, w in dentro],
                    "indices": [i for i, _ in dentro], "cara": _cara(tabla, t0, t1)})
    return out


def _cara(tabla, t0: float, t1: float):
    """La caja que cubre la cara durante todo el tramo (px del cuadro), o None si no se ve."""
    cajas = [c for c in (tabla.cara(i) for i in range(int(t0 * config.FPS), int(t1 * config.FPS) + 1, 5)) if c]
    if not cajas:
        return None
    return [round(min(c[0] for c in cajas)), round(min(c[1] for c in cajas)), round(max(c[2] for c in cajas)), round(max(c[3] for c in cajas))]


def _prompt(carpeta: Path, slug: str, ped: list) -> str:
    tramos = "\n".join(json.dumps({k: p[k] for k in ("id", "clase", "dur", "idea", "palabras", "cara") if p[k] is not None},
                                  ensure_ascii=False) for p in ped)
    t = PROMPT.read_text()
    for clave, valor in (("n", str(len(ped))), ("slug", slug), ("lemo", str(pro.LEMO)), ("trabajo", str(carpeta / TRABAJO)),
                         ("apoyos", tramos), ("pesado", str(pro.PESADO) if pro.PESADO.exists() else "")):
        t = t.replace(f"[[{clave}]]", valor)
    return t


def _leer(f: Path):
    try:
        return json.loads(Path(f).read_text())
    except (OSError, ValueError):
        return None


def _clase(carpeta: Path, p: dict) -> str:
    """La clase que Lemo eligió para el tramo (`plano.json › clase`), o la propuesta si no dijo nada."""
    c = (_leer(Path(carpeta) / TRABAJO / p["id"] / "plano.json") or {})
    c = c.get("clase") if isinstance(c, dict) else None
    return c if c in (*CLASES, NADA) else p["clase"]


def _entregado(carpeta: Path, p: dict) -> bool:
    return (Path(carpeta) / TRABAJO / p["id"] / pro.PELICULA).exists()


def _preparar(carpeta: Path, slug: str, ped: list) -> None:
    """Cada `lemo/<id>/` lleva la firma de su pedido (estilo, t0, t1): una entrega hecha para otro pedido se borra, y el
    `arte/<id>.mp4` de cada tramo se rehace siempre desde lo de Lemo (nunca entra uno viejo con el mismo id)."""
    for p in ped:
        d = carpeta / TRABAJO / p["id"]
        firma = {"estilo": slug, "t0": p["t0"], "t1": p["t1"]}
        if d.exists() and _leer(d / "pedido.json") != firma:
            shutil.rmtree(d)
        d.mkdir(parents=True, exist_ok=True)
        (d / "pedido.json").write_text(json.dumps(firma))
        (carpeta / "arte" / f"{p['id']}.mp4").unlink(missing_ok=True)


def _segundos_vacios(video: Path, dur: float) -> float:
    """Cuántos segundos del video son casi todo negro (texto o un dibujo chico sobre fondo vacío). blackdetect no los ve: hay algo."""
    ffmpeg, _ = config.ffmpeg()
    b = subprocess.run([ffmpeg, "-v", "error", "-i", str(video), "-vf", f"fps={MUESTRAS_POR_S},scale=108:192,format=gray", "-f", "rawvideo", "-"],
                       capture_output=True, check=True).stdout
    g = np.frombuffer(b[:len(b) // (108 * 192) * 108 * 192], np.uint8).reshape(-1, 108 * 192)
    return float(((g < VACIO_LUMA).mean(axis=1) >= VACIO_FRAC).sum()) / MUESTRAS_POR_S if g.size else 0.0


def revisar(carpeta: Path, p: dict) -> list:
    """Compuertas de UNA entrega (`lemo/<id>/`), según su clase. → fallas (vacío = entra al reel)."""
    enc = Path(carpeta) / TRABAJO / p["id"]
    f = enc / pro.PELICULA
    if not f.exists():
        return [f"no entregó {p['id']}/{pro.PELICULA}"]
    try:
        s = pro._sonda(f)
    except subprocess.CalledProcessError:
        return [f"{p['id']}/{f.name} no se puede leer (archivo roto)"]
    v = next((x for x in s["streams"] if x["codec_type"] == "video"), None)
    if not v:
        return [f"{p['id']}/{f.name} no tiene video"]
    fallas = []
    if (v["width"], v["height"]) != pro.TAMANO:
        fallas.append(f"tamaño {v['width']}x{v['height']}, debe ser {pro.TAMANO[0]}x{pro.TAMANO[1]}")
    n, d = (int(x) for x in v["r_frame_rate"].split("/"))
    if abs(n / d - pro.FPS) > .01:
        fallas.append(f"{n / d:.2f} cuadros por segundo, deben ser {pro.FPS}")
    dur = float(s["format"]["duration"])
    if abs(dur - p["dur"]) > DUR_TOL_S + 1 / pro.FPS:
        fallas.append(f"dura {dur:.2f} s y el tramo dura {p['dur']:.2f} s (tolerancia {DUR_TOL_S} s)")
    idx = enc / "index.html"
    if not idx.exists() or "TEXTS" not in idx.read_text(errors="ignore"):
        fallas.append("falta index.html con window.TEXTS (contrato de Lemo)")
    if not (enc / "plano.json").exists():
        fallas.append("falta plano.json")
    fallas += [f"cuadros negros de {d:.2f} s desde el segundo {a:.2f}: el tramo es de pantalla completa, con fondo y figuras"
               for a, d in pro._negros(f)]
    if (vacio := _segundos_vacios(f, dur)) > VACIO_MAX_S:
        fallas.append(f"{vacio:.1f} s con el fondo vacío (casi todo negro, solo texto encima): va un diseño entero, con fondo pintado y figuras")
    return [f"{p['id']}: {x}" if not x.startswith(p["id"]) else x for x in fallas]


def _completar(carpeta: Path, p: dict, avance=print) -> set:
    """Deja `arte/<id>.mp4` y devuelve los índices (de `palabras.json`) que ya quedan en pantalla en ese tramo: los que Lemo mostró
    y los que el editor de textos agregó dentro de su película (entonces son todos)."""
    enc, destino = carpeta / TRABAJO / p["id"], carpeta / "arte" / f"{p['id']}.mp4"
    destino.parent.mkdir(exist_ok=True)
    shutil.copyfile(enc / pro.PELICULA, destino)       # lo de Lemo entra siempre; si se completa, se reemplaza abajo
    if not p["palabras"]:
        return set()
    (enc / "palabras.json").write_text(json.dumps(p["palabras"], ensure_ascii=False))
    try:
        m = textos_lemo.medir(enc, pro.LEMO)
    except (RuntimeError, OSError, ValueError, KeyError, subprocess.SubprocessError) as e:
        avance(f"lemo · {p['id']}: no pude leer sus textos ({str(e)[:160]}); las palabras van en el subtítulo")
        return set()
    suyas = {p["indices"][i] for i in m["indices_mostradas"]}
    try:
        mapa_texto.escribir(enc, pro.PELICULA)
        inf = texto_pelicula.componer(enc, enc / "final.mp4", set(m["indices_mostradas"]))
    except (RuntimeError, OSError, ValueError, KeyError, subprocess.SubprocessError) as e:
        avance(f"lemo · {p['id']}: no pude completar sus textos ({str(e)[:160]}); queda como lo entregó Lemo, con el subtítulo")
        return suyas
    if not inf["ok"]:
        avance(f"lemo · {p['id']}: el editor de textos no pasó ({'; '.join(inf['fallas'])[:200]}); queda con el subtítulo")
        return suyas
    shutil.copyfile(enc / "final.mp4", destino)
    avance(f"lemo · {p['id']}: Lemo puso {inf['lemo']} de {inf['palabras']} palabras, agregamos {inf['agregadas']}")
    return set(p["indices"])


def _persona_en(sb: dict, t0: float, t1: float, modo: str, fin: float) -> None:
    """Deja `persona.modo = modo` en todo [t0, t1) y lo de después de t1 como estaba: parte escenas si hace falta (copia la que
    regía) y no toca nada si el tramo ya está así."""
    esc = sorted((e for e in sb.get("escenas", []) if isinstance(e, dict)), key=lambda e: e.get("t0", 0))

    def rige(t):
        return next((e for e in reversed(esc) if e.get("t0", 0) <= t + EPS), None)

    def modo_de(e):
        return ((e or {}).get("persona") or {}).get("modo", "completa")   # sin escena, la persona se ve

    dentro = [e for e in esc if t0 - EPS <= e.get("t0", 0) < t1 - EPS]
    al_inicio = rige(t0)
    if all(modo_de(e) == modo for e in [*dentro, al_inicio]):
        return
    nuevas = list(esc)
    tras = rige(t1)
    if t1 < fin - EPS and not any(abs(e.get("t0", 0) - t1) < EPS for e in esc):   # después del tramo, como estaba
        nuevas.append({**(copy.deepcopy(tras) if tras else {"persona": {"modo": "completa"}}), "t0": round(t1, 3)})
    if not any(abs(e.get("t0", 0) - t0) < EPS for e in esc):
        nueva = {**copy.deepcopy(al_inicio or {}), "t0": round(t0, 3)}
        nuevas.append(nueva)
        dentro.append(nueva)
    for e in dentro:
        e["persona"] = {**(e.get("persona") or {}), "modo": modo}
    sb["escenas"] = sorted(nuevas, key=lambda e: e.get("t0", 0))


def _menos(intervalos: list, quitar: list) -> list:
    """[[a, b], …] sin los trozos que caen dentro de `quitar`."""
    out = []
    for a, b in intervalos:
        partes = [(float(a), float(b))]
        for x, y in quitar:
            partes = [q for c, d in partes for q in ((c, min(d, x)), (max(c, y), d)) if q[1] - q[0] > EPS]
        out += [[round(c, 3), round(d, 3)] for c, d in partes]
    return out


def _bloques(sub: dict, palabras: list) -> list:
    """Los bloques del subtítulo como los arma el motor, sin ocultar ninguno: [(t0, t1, i0, i1)]."""
    from . import motor
    return motor.tramos_subtitulo({**sub, "ocultar": []}, palabras)


def cobertura(palabras: list, cortes: list, sub: dict, mostradas: set, de_director: list) -> dict:
    """La medida final del reel: cada palabra que queda (no cortada) se ve por Lemo o lo nuestro en su película (`mostradas`), por
    el subtítulo, o por un texto del director donde él ocultó el subtítulo fuera de los tramos de Lemo (`de_director`). Lo que no
    está en ninguno va en `sin_mostrar` (debe quedar vacío)."""
    ocultar = sub.get("ocultar", [])
    sub_vis, por_director = set(), set()
    for t0, _, i0, i1 in _bloques(sub, palabras):
        if not any(a <= t0 < b for a, b in ocultar):
            sub_vis.update(range(i0, i1))
        elif any(a <= t0 < b for a, b in de_director):
            por_director.update(range(i0, i1))
    vivas = [i for i, p in enumerate(palabras) if not _cortada(p, cortes)]
    sin = [i for i in vivas if i not in mostradas and i not in sub_vis and i not in por_director]
    return {"palabras": len(vivas), "en_pelicula_de_lemo": len([i for i in vivas if i in mostradas]),
            "en_subtitulo": len([i for i in vivas if i in sub_vis and i not in mostradas]),
            "sin_mostrar": [{"i": i, "w": palabras[i]["w"], "s": palabras[i]["s"]} for i in sin]}


def _estilo_de_lemo(carpeta: Path, buenos: list) -> dict:
    """{acento, fuente} de lo que entregó Lemo: el primer acento bien escrito y la letra de la integración que más dura."""
    acento, dur = None, {}
    for p in buenos:
        plano = _leer(carpeta / TRABAJO / p["id"] / "plano.json")
        if not isinstance(plano, dict):
            continue
        c = plano.get("acento")
        if acento is None and isinstance(c, str) and len(c) == 7 and c[0] == "#" and all(x in "0123456789abcdefABCDEF" for x in c[1:]):
            acento = c
        for t in plano.get("tramos") or []:
            try:
                d = float(t["t1"]) - float(t["t0"])
            except (KeyError, TypeError, ValueError):
                continue
            k = texto_pelicula._tipo(str(t.get("integracion", "")))
            dur[k] = dur.get(k, 0.0) + max(0.0, d)
    return {**({"acento": acento} if acento else {}), **({"fuente": FUENTE_DE[max(dur, key=dur.get)]} if dur else {})}


def _al_storyboard(carpeta: Path, ped: list, buenos: list, mostradas: set) -> dict:
    """Lleva al storyboard lo que Lemo entregó: escenas según su clase (persona a la vista donde no hizo nada), fusión del clip,
    subtítulo oculto solo en los bloques que ya están todos en pantalla, y su acento y su letra en el estilo (salvo lo que la
    persona eligió para este video). → la medida de cobertura."""
    sb_p = carpeta / "storyboard.json"
    sb = json.loads(sb_p.read_text())
    palabras = _palabras(carpeta)
    fin = max((p["e"] for p in palabras), default=0.0)
    ok = {p["id"]: p for p in buenos}
    for p in ped:
        q = ok.get(p["id"])
        _persona_en(sb, p["t0"], p["t1"], "oculta" if q else "completa", fin)
        el = next((e for e in sb.get("elementos", []) if isinstance(e, dict) and e.get("src") == f"arte/{p['id']}.mp4"), None)
        if el is not None and q:
            el.pop("fusion", None)
    sub = sb.setdefault("subtitulos", {})
    # dentro de los tramos de Lemo el subtítulo lo decide la medida, no un texto del director; fuera, lo del director queda
    de_director = _menos(sub.get("ocultar", []), [(p["t0"], p["t1"]) for p in ped])
    cortes = sb.get("cortes", [])
    nuevos = []
    for t0, t1, i0, i1 in _bloques(sub, palabras):
        vivas = [i for i in range(i0, i1) if not _cortada(palabras[i], cortes)]
        if vivas and all(i in mostradas for i in vivas) and not any(a <= t0 < b for a, b in de_director):
            nuevos.append([round(t0, 3), round(t1, 3)])
    if nuevos or de_director != sub.get("ocultar", []):
        sub["ocultar"] = sorted(de_director + nuevos)
    if not sub.get("ocultar"):
        sub.pop("ocultar", None)
    elegidos = set((((_leer(carpeta / "preferencias.json") or {}).get("estilo")) or {}))
    sb.setdefault("estilo", {}).update({k: v for k, v in _estilo_de_lemo(carpeta, buenos).items() if k not in elegidos})
    machote._guardar(sb_p, sb)
    return cobertura(palabras, cortes, sub, mostradas, de_director)


def hacer(carpeta: Path, slug: str, ia=None, avance=print) -> dict:
    """El paso de arte con Lemo: le ofrece los tramos, revisa lo que entregó (una vuelta de corrección para lo entregado que falla),
    deja en `arte/` lo que pasa, ajusta el storyboard y mide que todas las palabras queden en pantalla (`lemo/cobertura.json`).
    → {"pedidos", "hechos": [ids], "fallas": {id: [..]}}. Lo que no llegó lo quita después `imagenes.quitar_sin_arte`."""
    carpeta, ia = Path(carpeta), ia or _ia.llamar
    ped = pedidos(carpeta)
    if not ped:
        return {"pedidos": 0, "hechos": [], "fallas": {}}
    if not (pro.LEMO / "styles" / slug / "STYLE.md").exists():
        raise ValueError(f"estilo de Lemo desconocido: «{slug}» (no está en {pro.LEMO / 'styles'})")
    trabajo = carpeta / TRABAJO
    _preparar(carpeta, slug, ped)
    faltan = [p for p in ped if not _entregado(carpeta, p) and _clase(carpeta, p) != NADA]   # un pedido retomado no rehace lo hecho
    if faltan:
        avance(f"Lemo tiene {len(faltan)} tramos para hacer lo que quiera con el estilo «{slug}», uno por encargo…")
    tope = TOPE_USD_REEL
    for i, p in enumerate(faltan, 1):     # un encargo corto por tramo: Lemo no relee en cada paso lo de los otros tramos
        if _entregado(carpeta, p) or _clase(carpeta, p) == NADA:   # ya lo dejó hecho otro encargo (un universo de varios tramos)
            continue
        if tope <= 0:
            avance(f"lemo: se llegó al techo del reel; {p['id']} y los que siguen quedan sin hacer")
            break
        avance(f"lemo · {p['id']} ({i}/{len(faltan)})…")
        r = ia(_prompt(carpeta, slug, [p]), "opus", cwd=trabajo, herramientas=pro.HERRAMIENTAS, tope_usd=min(TOPE_USD_APOYO, tope),
               paso=f"lemo-{slug}-{p['id']}", timeout=TIMEOUT_APOYO_S, aislado=False)
        tope -= float((r or {}).get("total_cost_usd", 0) or 0) if isinstance(r, dict) else 0
    ped = [{**p, "clase": _clase(carpeta, p)} for p in ped]
    fallas = {p["id"]: revisar(carpeta, p) for p in ped if p["clase"] != NADA and _entregado(carpeta, p)}
    malos = [p for p in ped if fallas.get(p["id"])]
    if malos:
        avance(f"{len(malos)} entregas de Lemo no pasaron las medidas: las corrige una vez, cada una aparte")
        for p in malos:
            informe = "\n".join(f"- {x}" for x in fallas[p["id"]])
            ia(_prompt(carpeta, slug, [p]) + "\n\n# REINTENTO: esta entrega NO pasó las medidas\nTu carpeta ya tiene lo hecho: corregí "
               "SOLO esto y volvé a rendir lo mínimo (o dejá el tramo en «nada»).\n" + informe + "\n", "opus", cwd=trabajo,
               herramientas=pro.HERRAMIENTAS, tope_usd=TOPE_USD_APOYO / 2, paso=f"lemo-{slug}-{p['id']}-reintento",
               timeout=TIMEOUT_APOYO_S // 2, aislado=False)
        ids = {p["id"] for p in malos}
        ped = [{**p, "clase": _clase(carpeta, p)} if p["id"] in ids else p for p in ped]
        for p in ped:
            if p["id"] in ids:
                fallas.pop(p["id"])
                if p["clase"] != NADA:          # si en el reintento Lemo prefirió no hacerlo, no es una falla
                    fallas[p["id"]] = revisar(carpeta, p)
    buenos = [p for p in ped if p["id"] in fallas and not fallas[p["id"]]]
    mostradas = set()
    for p in buenos:
        mostradas |= _completar(carpeta, p, avance)
    nada = [p["id"] for p in ped if p["id"] not in fallas]
    if nada:
        avance(f"Lemo no hizo {len(nada)} tramos ({', '.join(nada)}): ahí sigue la persona con su subtítulo")
    cob = _al_storyboard(carpeta, ped, buenos, mostradas)
    (trabajo / "cobertura.json").write_text(json.dumps(cob, ensure_ascii=False, indent=1))
    avance("todas las palabras quedan en pantalla" if not cob["sin_mostrar"] else
           f"OJO: {len(cob['sin_mostrar'])} palabras sin mostrar ({', '.join(x['w'] for x in cob['sin_mostrar'][:8])})")
    malos = {k: v for k, v in fallas.items() if v}
    if malos:
        (trabajo / "informe-compuertas.txt").write_text("\n".join(x for v in malos.values() for x in v) + "\n")
        avance(f"{len(malos)} entregas de Lemo no entran al reel ({', '.join(sorted(malos))})")
    return {"pedidos": len(ped), "hechos": [p["id"] for p in buenos], "fallas": malos}
