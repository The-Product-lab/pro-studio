"""Huella del estilo (librerias/estilos/huellas/<estilo>.json): lo aprendido de los referentes, medido sobre el storyboard.

La compuerta (validar.errores) la aplica cuando el storyboard dice de qué estilo es. Mide lo que falla de verdad, con
tolerancia (los rangos salen de pocos reels): ritmo no más lento que el estilo, cada recurso firma presente, colores dentro de
la paleta, imágenes dentro del máximo. El director recibe la huella resumida en su guía (`resumen`).
"""
import json
from pathlib import Path

from . import config

HUELLAS = config.RAIZ / "librerias" / "estilos" / "huellas"
TOLERANCIA_RITMO = 1.3        # el cambio visual medio puede ser hasta 30 % más lento que el máximo del estilo
FRACCION_FIRMA = .5           # cada recurso firma debe aparecer al menos la mitad de su mínimo por minuto (y 1 vez)
DIST_COLOR = 60               # distancia RGB para considerar que un #hex es «de la paleta»


def cargar(estilo: str | None) -> dict | None:
    f = HUELLAS / f"{estilo}.json"
    return json.loads(f.read_text()) if estilo and f.exists() else None


def _hex(c):
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def _coincide(obj: dict, patron: dict) -> bool:
    for k, v in patron.items():
        if k == "en":
            continue
        cur = obj
        for parte in k.split("."):
            cur = cur.get(parte) if isinstance(cur, dict) else None
        if cur != v and not (v is True and cur):
            return False
    return True


def _hexes(x, out):
    if isinstance(x, dict):
        for v in x.values():
            _hexes(v, out)
    elif isinstance(x, list):
        for v in x:
            _hexes(v, out)
    elif isinstance(x, str) and len(x) == 7 and x.startswith("#"):
        out.add(x.upper())
    return out


def duracion(sb: dict, carpeta: Path | None) -> float | None:
    if not carpeta or not (Path(carpeta) / "fuente.json").exists():
        return None
    n = json.loads((Path(carpeta) / "fuente.json").read_text())["cuadros"]
    quitar = sum(max(0, round(b * config.FPS) - round(a * config.FPS)) for a, b in sb.get("cortes", []))
    return max(.1, (n - quitar) / config.FPS)


def errores(sb: dict, carpeta: Path | None, estilo: str | None) -> list:
    h = cargar(estilo)
    if not h:
        return []
    err = []
    dur = duracion(sb, carpeta)
    nombre = f"huella de {estilo}"
    # ritmo: cambios visuales (escenas + entradas de elementos) que quedan en el video editado
    if dur and h.get("ritmo", {}).get("cambio_cada_s"):
        cortes = sb.get("cortes", [])
        vivos = sorted({round(t, 2) for t in [e["t0"] for e in sb.get("escenas", [])] + [e["t0"] for e in sb.get("elementos", [])]
                        if not any(a <= t < b for a, b in cortes)})
        maximo = h["ritmo"]["cambio_cada_s"][1] * TOLERANCIA_RITMO
        medio = dur / max(1, len(vivos))
        if medio > maximo:
            err.append(f"{nombre}: un cambio visual cada {medio:.1f} s y el estilo pide como mucho {h['ritmo']['cambio_cada_s'][1]} s "
                       f"(faltan ~{int(dur / maximo) - len(vivos) + 1} cambios: escenas, textos o apoyos amarrados a palabras)")
    # recursos firma
    if dur:
        for r in h.get("recursos_firma", []):
            patron = r.get("motor") or {}
            donde = patron.get("en", "elementos")
            lista = sb.get(donde, []) if donde in ("elementos", "escenas", "trazos", "cajas") else []
            n = sum(1 for o in lista if isinstance(o, dict) and _coincide(o, patron))
            minimo = max(1, int((r.get("por_min") or [1])[0] * dur / 60 * FRACCION_FIRMA))
            if n < minimo:
                err.append(f"{nombre}: el recurso firma «{r.get('nombre')}» aparece {n} veces y en {dur:.0f} s debe aparecer al menos "
                           f"{minimo} ({json.dumps({k: v for k, v in patron.items() if k != 'en'}, ensure_ascii=False)} en {donde})")
    # paleta: todo #hex usado debe parecerse a uno de la huella o de los permitidos
    permitidos = [_hex(p["hex"]) for p in h.get("paleta", []) if isinstance(p, dict) and p.get("hex")]
    permitidos += [_hex(c) for c in h.get("colores_extra_permitidos", []) if isinstance(c, str) and c.startswith("#")]
    permitidos += [_hex(v) for v in (sb.get("estilo") or {}).values() if isinstance(v, str) and v.startswith("#") and len(v) == 7]
    if permitidos:
        usados = _hexes({"e": sb.get("elementos", []), "s": sb.get("escenas", []), "c": sb.get("cajas", [])}, set())
        fuera = [c for c in sorted(usados) if min(sum((a - b) ** 2 for a, b in zip(_hex(c), p)) ** .5 for p in permitidos) > DIST_COLOR]
        if fuera:
            err.append(f"{nombre}: colores fuera de la paleta del estilo: {', '.join(fuera)} (usa los de la paleta o los nombres acento/acento2/blanco/negro)")
    # imágenes
    if h.get("imagenes_max") is not None:
        n_img = len({e.get("src") for e in sb.get("elementos", []) if e.get("tipo") in ("foto", "recorte") and e.get("src")})
        if n_img > int(h["imagenes_max"]):
            err.append(f"{nombre}: usa {n_img} imágenes y el estilo admite {h['imagenes_max']}")
    return err


def resumen(estilo: str) -> str:
    """La huella en palabras, para la guía del director."""
    h = cargar(estilo)
    if not h:
        return ""
    lin = [f"Identidad: {h.get('identidad', '')}",
           "Paleta: " + ", ".join(f"{p['hex']} ({p.get('rol', '')})" for p in h.get("paleta", []) if isinstance(p, dict)),
           "Piezas firma (inspiración: úsalas, mézclalas o inventa otras): " + "; ".join(
               f"{r.get('nombre')} = {json.dumps(r.get('motor'), ensure_ascii=False)}" for r in h.get("recursos_firma", [])),
           "SÍ: " + " · ".join(h.get("si", [])), "NO: " + " · ".join(h.get("no", []))]
    return "\n".join(f"- {x}" for x in lin)
