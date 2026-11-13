"""Estilista: crea un estilo SOLO, de punta a punta (método de docs/METODO-ESTILOS.md).

    buscar      Opus + vidIQ: creadores que editan con ese FORMATO (no por tema) → refs en db/referencias.json
    estudiar    Sonnet + vidIQ: cada reel no estudiado → db/<estilo>/analisis/<código>.md (11 bloques, siempre de cero)
    implementar Opus: cruza los análisis → librerias/estilos/<estilo>.md + preset + ejemplo del director
    validar     pytest; si falla, el error vuelve a Opus (máx. 2 vueltas)
    probar      edita un clip corto con el estilo nuevo → carpeta de revisión

Las referencias del dueño pesan más que las encontradas. Nada se publica; Pablo aprueba mirando el clip.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

from . import config, ia, portable

DB = config.RAIZ / "librerias/estilos/db"


def prefijo_vidiq(claude_json: Path = Path.home() / ".claude.json") -> str:
    """vidIQ como MCP local «viqiq» (Mac) o, si no está, el conector de la cuenta claude.ai (ya con sesión en cualquier PC)."""
    try:
        d = json.loads(claude_json.read_text())
    except (OSError, ValueError):
        d = {}
    locales = set(d.get("mcpServers", {}))
    for p in d.get("projects", {}).values():
        locales |= set(p.get("mcpServers", {}))
    return "mcp__viqiq__vidiq_" if "viqiq" in locales else "mcp__claude_ai_vidiq__vidiq_"


VQ = prefijo_vidiq()
CODIGO = re.compile(r"instagram\.com/(?:reel|p)/([\w-]+)")

BUSCAR = """Busca en Instagram, con vidIQ, creadores que editan reels con este FORMATO DE EDICIÓN: «{idea}» (estilo «{estilo}»).
Regla del dueño: se busca por formato visual de edición, NUNCA por tema. Prefiere creadores (cuentas que editan siempre así).
1. {vq}instagram_tiktok_outlier_search y {vq}ig_accounts_from_outliers para hallar 3–5 cuentas de ese formato.
2. {vq}ig_profile_reels de cada una; elige los {n} reels que MEJOR muestran el formato (y con buenas vistas).
Responde SOLO JSON: {{"refs": [["<código del reel>", "<cuenta>", "<qué se ve en una línea>", "<vistas>"], ...]}}"""

ESTUDIAR = """Estudia este reel con {vq}watch_shortform_content (espera el resultado con {vq}job_poll): {url}
Pide y escribe el análisis COMPLETO de la edición (no del tema) en el archivo `{archivo}`, con este encabezado:
# {estilo_mayus} · @{cuenta} · {url}
Estudiado con vidIQ el {hoy} · fuente: {fuente}

Y estos 11 bloques numerados, concretos y medibles (HEX, segundos, tamaños, nombres de fuente):
1) Lenguaje visual en una frase · 2) Paleta (HEX y uso) · 3) Tipografías · 4) Subtítulos / texto en pantalla ·
5) Fondos y texturas · 6) La persona (encuadre, recorte, filtros) · 7) Elementos gráficos · 8) Movimiento y animación ·
9) Transiciones · 10) Ritmo (cambios por segundo, duración de escenas) · 11) Sonido y SFX.
Responde en una línea «listo» o el error."""

IMPLEMENTAR = """Eres el director de arte del estudio. Vas a IMPLEMENTAR el estilo «{estilo}» en el motor, solo con lo que el motor sabe hacer.
Lee:
- Todos los análisis: `librerias/estilos/db/{estilo}/analisis/*.md` (los marcados «referencia del dueño» mandan).
- La gramática del motor: `estudio/director/GRAMATICA.md`, y un estilo ya hecho como modelo: `librerias/estilos/maestro.md`,
  `estudio/director/ejemplo/maestro.json`, el preset "maestro" en `librerias/estilos/presets.json`.
- Tipografías instaladas: {fuentes}. Si las referencias piden otra, búscala e instálala del catálogo completo de Google Fonts
  (licencia libre) con `uv run estudio fuentes buscar <palabra>` y `uv run estudio fuentes instalar "<Familia>"`. Guion de ejemplo: `estudio/director/ejemplo/palabras.json`.

Escribe:
1. `librerias/estilos/{estilo}.md`: guía para el director (identidad en una frase, paleta, roles de tipografía, base
   pantalla (la persona en su toma completa), recursos y CUÁNDO usar cada uno, ritmo, subtítulos, transiciones, sonido, qué NO hacer) y al final
   una sección «Falta en motor» con lo que las referencias hacen y el motor aún no.
2. Agrega la clave "{estilo}" a `librerias/estilos/presets.json` (mismas claves que "maestro", TODAS las de la ficha; no toques los otros presets).
3. `estudio/director/ejemplo/{estilo}.json`: un storyboard ejemplar sobre palabras.json, válido según la gramática.
{error}
Responde en una línea qué identidad le diste."""


def _refs() -> dict:
    p = DB / "referencias.json"
    return json.loads(p.read_text()) if p.exists() else {}


def _guardar_refs(d: dict) -> None:
    """Guarda COMBINANDO con lo que haya ahora en disco (otro proceso pudo sumar referentes mientras tanto): nunca se pierde uno."""
    ruta = DB / "referencias.json"
    with open(ruta, "r+", encoding="utf-8") as f, portable.candado(f):
        actual = json.loads(f.read() or "{}")
        for estilo, e in d.items():
            a = actual.setdefault(estilo, {})
            for k, v in e.items():
                if k == "refs":
                    vistos = {r[0] for r in v}
                    a["refs"] = v + [r for r in a.get("refs", []) if r[0] not in vistos]
                elif k == "estado":
                    a["estado"] = {**a.get("estado", {}), **v}
                elif k == "del_duenno":
                    a["del_duenno"] = sorted(set(a.get("del_duenno", [])) | set(v))
                else:
                    a[k] = v
        f.seek(0)
        f.truncate()
        f.write(json.dumps(actual, ensure_ascii=False, indent=1))


def agregar_links(estilo: str, links: list, idea: str = "") -> list:
    """Links del dueño → refs del estilo (pesan más). Devuelve los códigos."""
    d = _refs()
    e = d.setdefault(estilo, {"nombre": estilo.title(), "idea": idea, "refs": [], "estado": {}})
    if idea and not e.get("idea"):
        e["idea"] = idea
    codigos = []
    for url in links:
        m = CODIGO.search(url)
        if not m:
            continue
        c = m.group(1)
        codigos.append(c)
        if c not in [r[0] for r in e["refs"]]:
            e["refs"].insert(0, [c, "", "dueño", "referencia del dueño", ""])
        e["estado"].setdefault(c, "pendiente")
        e.setdefault("del_duenno", [])
        if c not in e["del_duenno"]:
            e["del_duenno"].append(c)
    _guardar_refs(d)
    return codigos


def buscar(estilo: str, idea: str, n=4, avance=print) -> list:
    avance(f"buscando creadores con formato «{idea}»…")
    out = ia.llamar(BUSCAR.format(idea=idea, estilo=estilo, vq=VQ, n=n), "opus", config.RAIZ,
                    herramientas=f"{VQ}instagram_tiktok_outlier_search,{VQ}ig_accounts_from_outliers,{VQ}ig_profile_reels",
                    tope_usd=3.0, paso=f"estilista-buscar-{estilo}", mcp=True, timeout=1200)
    nuevas = ia.json_de(out.get("result", "")).get("refs", [])
    d = _refs()
    e = d.setdefault(estilo, {"nombre": estilo.title(), "idea": idea, "refs": [], "estado": {}})
    for r in nuevas:
        if r and r[0] not in [x[0] for x in e["refs"]]:
            e["refs"].append([r[0], "", *r[1:4]])
            e["estado"].setdefault(r[0], "pendiente")
    _guardar_refs(d)
    avance(f"{len(nuevas)} reels de creadores agregados")
    return [r[0] for r in nuevas]


def estudiar(estilo: str, avance=print) -> int:
    """Estudia de cero cada ref pendiente (de a una: vidIQ admite 2 trabajos a la vez y así nunca se pasa)."""
    import datetime
    d = _refs()
    e = d[estilo]
    carpeta = DB / estilo / "analisis"
    carpeta.mkdir(parents=True, exist_ok=True)
    hechos = 0
    for r in e["refs"]:
        c = r[0]
        archivo = carpeta / f"{c}.md"
        if e["estado"].get(c) == "estudiado" and archivo.exists():
            continue
        cuenta = r[2] if len(r) > 2 else ""
        duenno = c in e.get("del_duenno", [])
        avance(f"estudiando {c} ({'del dueño' if duenno else '@' + cuenta})…")
        url = f"https://www.instagram.com/reel/{c}/"
        try:
            ia.llamar(ESTUDIAR.format(vq=VQ, url=url, archivo=archivo.relative_to(config.RAIZ), estilo_mayus=estilo.upper(),
                                      cuenta=cuenta or "?", hoy=datetime.date.today().isoformat(),
                                      fuente="referencia del dueño" if duenno else "búsqueda de creadores (no es referencia del dueño)"),
                      "opus", config.RAIZ, herramientas=f"{VQ}watch_shortform_content,{VQ}job_poll,Write",
                      tope_usd=1.5, paso=f"estilista-estudiar-{c}", mcp=True, timeout=1200)
        except RuntimeError as err:
            avance(f"  no se pudo estudiar {c}: {err}")
            continue
        if archivo.exists() and archivo.stat().st_size > 800:
            e["estado"][c] = "estudiado"
            hechos += 1
            _guardar_refs(d)
    return hechos


def _pytest() -> str:
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-x", "tests"], cwd=config.RAIZ, capture_output=True, text=True)
    return "" if r.returncode == 0 else (r.stdout + r.stderr)[-1500:]


def implementar(estilo: str, avance=print) -> str:
    if not list((DB / estilo / "analisis").glob("*.md")):
        raise RuntimeError(f"«{estilo}» no tiene análisis: estúdialo primero")
    fuentes = ", ".join(json.loads((config.RAIZ / "librerias/fuentes/indice.json").read_text()))
    error = ""
    for vuelta in (1, 2, 3):
        avance(f"implementando «{estilo}» (vuelta {vuelta})…")
        out = ia.llamar(IMPLEMENTAR.format(estilo=estilo, fuentes=fuentes,
                                           error=f"\nLA VUELTA ANTERIOR FALLÓ LAS PRUEBAS. Arregla esto:\n{error}" if error else ""),
                        "opus", config.RAIZ, herramientas="Read,Write,Edit,Glob,Grep,Bash(uv run estudio fuentes:*)", tope_usd=4.0,
                        paso=f"estilista-implementar-{estilo}", timeout=1800)
        error = _pytest()
        if not error:
            avance(f"«{estilo}» implementado: {out.get('result', '').strip()[:300]}")
            return out.get("result", "")
    raise RuntimeError(f"«{estilo}» no pasa las pruebas tras 3 vueltas:\n{error}")


def probar(estilo: str, clip: str, avance=print) -> Path:
    from . import cli
    return cli.editar(clip, estilo, False, 1, f"prueba-{estilo}")


def crear(estilo: str, links=(), idea="", buscar_mas=True, clip=None, avance=print) -> dict:
    """Todo el ciclo. Con links del dueño, igual busca creadores para completar (salvo buscar_mas=False)."""
    if links:
        agregar_links(estilo, list(links), idea)
    e = _refs().get(estilo, {})
    if buscar_mas and len(e.get("refs", [])) < 4:
        buscar(estilo, idea or e.get("idea", estilo), avance=avance)
    n = estudiar(estilo, avance)
    avance(f"{n} reels estudiados de cero")
    implementar(estilo, avance)
    final = str(probar(estilo, clip, avance)) if clip else None
    return {"estilo": estilo, "estudiados": n, "prueba": final}
