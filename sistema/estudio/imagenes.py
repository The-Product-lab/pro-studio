"""Arte a medida: arte.json → arte/<id>.png con Higgsfield (vía `claude -p` y el conector de la cuenta), con tope por video."""
import json
import re
import shutil
import subprocess
import urllib.request
from pathlib import Path

from . import config, ia

HF = "mcp__claude_ai_higgsfield__"   # el nombre de siempre; `conector()` da el de ESTA cuenta
CONECTAR = "conéctalo en claude.ai → Ajustes → Conectores → Higgsfield"
PROMPT = """Genera estas imágenes con la herramienta {hf}generate_image_batch y espera con {hf}jobs_wait hasta que todas terminen.
Si esas herramientas aparecen como diferidas, cárgalas primero con ToolSearch (select:{hf}generate_image_batch,{hf}jobs_wait).
Para cada pedido usa model "seedream_v5_pro", resolution "2k", el aspect_ratio indicado y, si "recorte" es true,
remove_bg: true. Usa como index el número de orden del pedido. Si un pedido falla por límite de velocidad (429), reenvíalo una vez.
LLAMA a la herramienta: si funciona o no lo dice SU respuesta, nunca un aviso de la sesión sobre conectores por autorizar (puede
haber otro conector de nombre parecido sin autorizar; el de estas herramientas es el que está conectado).

Pedidos:
{pedidos}

Responde SOLO con un JSON: {{"urls": {{"<id>": "<result_url>", ...}}, "fallidos": ["<id>", ...]}}"""


def prefijo_en(listado: str) -> str | None:
    """De la salida de `claude mcp list`, el prefijo de las herramientas de Higgsfield. El nombre del conector lo pone cada cuenta
    («higgsfield», «Higgsfield AI»…) y las herramientas se llaman según ese nombre: escrito fijo solo sirve en la cuenta donde se
    programó (10-nov). None = hay conectores y ninguno de Higgsfield está conectado; si la lista no se pudo leer, el de siempre."""
    servidores = re.findall(r"^(.+?): \S+.* - (.+)$", listado, re.M)
    if not servidores:
        return HF
    for nombre, estado in servidores:
        if "higgsfield" in nombre.lower() and "connected" in estado.lower():
            return "mcp__" + re.sub(r"[^A-Za-z0-9_-]", "_", nombre.strip()) + "__"
    return None


def conector() -> str | None:
    """Prefijo de las herramientas de Higgsfield en la cuenta de Claude de esta máquina (None = sin conectar)."""
    cmd = config.claude_cmd()
    if not cmd:
        return None
    try:
        r = subprocess.run(cmd + ["mcp", "list"], capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.SubprocessError):
        return HF
    return prefijo_en(r.stdout)


SIN_IMAGENES = "Esta cuenta no tiene generación de imágenes (Higgsfield sin conectar): el video se diseña SIN imágenes, con textos y trazos"


def disponibles(pedidas: bool, avance=print) -> bool:
    """¿Se edita con imágenes? Se decide ANTES de dirigir: sin generador conectado el director diseña el video sin imágenes desde el
    principio (variante «sin imágenes» de cada estilo), en vez de diseñarlo con arte que después no llega y deja huecos
    (Pablo, 11-nov: «dos variantes a cada estilo, con o sin imágenes… y un aviso… para que él resuelva»)."""
    if pedidas and not conector():
        avance(f"{SIN_IMAGENES} ({CONECTAR})")
        return False
    return pedidas


def tope_de(carpeta: Path) -> int:
    """Imágenes máximas para este video: el tope del estilo (preset `tope_imagenes`) sin pasar el tope general."""
    sb = carpeta / "storyboard.json"
    est = json.loads(sb.read_text()).get("estilo", {}) if sb.exists() else {}
    return min(config.TOPE_IMAGENES_MAX, int(est.get("tope_imagenes", config.TOPE_IMAGENES)))


def generar(carpeta: Path, avance=print) -> dict:
    carpeta = Path(carpeta)
    arte_p = carpeta / "arte.json"
    if not arte_p.exists():
        return {}
    pedidos = json.loads(arte_p.read_text())
    faltan = [p for p in pedidos if not (carpeta / "arte" / f"{p['id']}.png").exists()]
    hechas = len(list((carpeta / "arte").glob("*.png"))) if (carpeta / "arte").exists() else 0
    tope = max(0, tope_de(carpeta) - hechas)
    if len(faltan) > tope:
        avance(f"tope del estilo: se generan {tope} de {len(faltan)} imágenes pedidas")
        faltan = faltan[:tope]
    if not faltan:
        return {}
    hf = conector()
    if not hf:
        avance(f"Higgsfield no está conectado en tu cuenta de Claude: el video sale sin arte a medida ({CONECTAR})")
        return {}
    avance(f"generando {len(faltan)} imágenes en Higgsfield…")
    (carpeta / "arte").mkdir(exist_ok=True)
    urls: dict = {}
    for intento in (1, 2):   # una imagen que falla (límite de velocidad, descarga cortada) se pide una vez más, sola
        urls.update(_pedir(carpeta, faltan, hf, avance))
        faltan = [p for p in faltan if not (carpeta / "arte" / f"{p['id']}.png").exists()]
        if not faltan:
            break
        if intento == 1:
            avance(f"{len(faltan)} imágenes no salieron: se piden otra vez…")
    with open(carpeta / "gasto-imagenes.jsonl", "a") as f:
        f.write(json.dumps({"imagenes": len(urls), "creditos_aprox": 2.5 * len(urls)}) + "\n")
    return urls


def _pedir(carpeta: Path, pedidos: list, hf: str, avance) -> dict:
    """Una llamada: genera `pedidos` y baja lo que salió. Un fallo de Higgsfield o de la descarga no tumba el video (la imagen
    queda sin hacer); quedarse sin cupo de Claude sí se propaga: eso es esperar, no seguir sin arte."""
    lista = "\n".join(json.dumps({"index": i, "id": p["id"], "prompt": p["prompt"], "aspect_ratio": p.get("aspecto", "1:1"),
                                  "recorte": p.get("recorte", False)}, ensure_ascii=False) for i, p in enumerate(pedidos))
    try:
        out = ia.llamar(PROMPT.format(hf=hf, pedidos=lista), "opus", carpeta, herramientas=f"{hf}generate_image_batch,{hf}jobs_wait",
                        tope_usd=1.0, paso="imagenes", mcp=True, timeout=900)
        urls = ia.json_de(out.get("result", "")).get("urls", {})
    except ia.LimiteAgotado:
        raise
    except (RuntimeError, ValueError, AttributeError, subprocess.SubprocessError) as e:
        avance(f"Higgsfield no respondió bien ({str(e)[:160]})")
        return {}
    hechas = {}
    pedidas = {p["id"] for p in pedidos}
    for id_, url in urls.items():
        if id_ not in pedidas:
            continue
        destino, parcial = carpeta / "arte" / f"{id_}.png", carpeta / "arte" / f"{id_}.png.part"
        try:
            with urllib.request.urlopen(url, timeout=120) as r, open(parcial, "wb") as f:
                shutil.copyfileobj(r, f)
            parcial.replace(destino)
            hechas[id_] = url
        except (OSError, ValueError) as e:
            parcial.unlink(missing_ok=True)
            avance(f"no pude bajar la imagen «{id_}» ({type(e).__name__})")
    return hechas


def arte_del_video(carpeta: Path, con_imagenes: bool = True, avance=print) -> list:
    """El paso de arte completo, igual para la app y la terminal: genera lo pedido (si se pidió) y deja el storyboard sin ningún
    dibujo cuya imagen no exista. Devuelve los `src` que se quitaron."""
    from . import lemo_apoyos
    sb = Path(carpeta) / "storyboard.json"
    lemo = (json.loads(sb.read_text()).get("estilo") or {}).get("lemo") if sb.exists() else None
    if lemo:                       # reel con apoyos de Lemo (docs/PLANO-LEMO-APOYOS.md): el arte no es de Higgsfield
        lemo_apoyos.hacer(carpeta, lemo, avance=avance)
    elif con_imagenes:
        generar(carpeta, avance)
    return quitar_sin_arte(carpeta, avance)


def quitar_sin_arte(carpeta: Path, avance=print) -> list:
    """Después de generar: lo que el storyboard dibuja con una imagen que no existe se quita (y los trazos que lo señalan), para que
    el render nunca reviente al final por un archivo que falta (10-nov: Higgsfield sin conectar o una imagen fallida tumbaba el
    video ya dirigido). Devuelve los `src` quitados; el aviso dice cuántos y por qué."""
    carpeta = Path(carpeta)
    sb_p = carpeta / "storyboard.json"
    if not sb_p.exists():
        return []
    sb = json.loads(sb_p.read_text())
    sin = [e for e in sb.get("elementos", []) if isinstance(e, dict) and e.get("src") and not (carpeta / e["src"]).exists()]
    if not sin:
        return []
    ids = {e["id"] for e in sin if e.get("id")}
    sb["elementos"] = [e for e in sb["elementos"] if not any(e is x for x in sin)]
    if isinstance(sb.get("trazos"), list):
        sb["trazos"] = [t for t in sb["trazos"] if not (isinstance(t, dict) and isinstance(t.get("sobre"), str) and t["sobre"] in ids)]
    sb_p.write_text(json.dumps(sb, ensure_ascii=False, indent=1))
    avance(f"{len(sin)} imágenes no se pudieron generar ({', '.join(sorted({Path(e['src']).stem for e in sin}))}): esas piezas se quitaron y el ojo revisa que no quede hueco")
    return [e["src"] for e in sin]
