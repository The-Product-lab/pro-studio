"""Integrar un estilo APROBADO por Pablo al director de la app, sin dañar nada (Pablo, 04-nov: «para que integre bien el nuevo
conocimiento sin dañar nada»).

La copia aprobada (`proyectos/<proyecto>`) pasa a ser lo que el director usa para ese estilo:
- su storyboard → `estudio/director/ejemplo/<id>.json` (el modelo «así se ve el nivel esperado») + sus palabras
  → `ejemplo/<id>.palabras.json`; sale de OBSOLETOS si estaba;
- su bloque `estilo` → `librerias/estilos/presets.json[<id>]` (lo que fija el código, no el director).
La guía `<id>.md` la escribe una persona/Opus (es criterio, no se genera); aquí solo se exige que exista.

Candados (si uno falla, no se toca NADA):
1. Pablo la aprobó en la pantalla de revisión (`proyectos/FEEDBACK.json`, «Apruebo»).
2. Pasa la compuerta vigente (`validar.errores` vacío salvo «huella …»).
3. Solo escribe lo de ESE estilo; deja copia de lo anterior en `estudio/director/ejemplo/_antes/`.

    uv run estudio integrar luminoso c8866-luminoso4
"""
import json
import shutil
import time
from pathlib import Path

from . import config, validar
from .director import AQUI as DIRECTOR

EJEMPLOS = DIRECTOR / "ejemplo"
PRESETS = config.RAIZ / "librerias" / "estilos" / "presets.json"
FEEDBACK = config.PROYECTOS / "FEEDBACK.json"
NO_VAN_AL_PRESET = {"id", "color"}          # el color es de ESE video (preferencias.json), no del estilo
SE_CONSERVAN = ("imagenes", "tope_imagenes", "sonido_paleta")   # ajustes del preset que no son del look: no se pisan


def aprobado(estilo: str, feedback: Path = FEEDBACK) -> bool:
    notas = json.loads(feedback.read_text()) if feedback.exists() else []
    return any(n.get("estilo") == estilo and n.get("aprueba") for n in notas)


def integrar(estilo: str, proyecto: str, nombre: str | None = None, *, feedback: Path = FEEDBACK,
             ejemplos: Path = EJEMPLOS, presets: Path = PRESETS, avance=print) -> dict:
    carpeta = config.PROYECTOS / proyecto if not Path(proyecto).is_absolute() else Path(proyecto)
    if not aprobado(estilo, feedback):
        raise ValueError(f"«{estilo}» no está aprobado por Pablo en la pantalla de revisión: no se integra")
    sb = json.loads((carpeta / "storyboard.json").read_text())
    sb["estilo"] = {**sb.get("estilo", {}), "id": estilo}
    malos = [e for e in validar.errores(sb) if not e.startswith("huella")]
    if malos:
        raise ValueError(f"«{estilo}» no pasa la compuerta vigente ({len(malos)}): " + " | ".join(malos[:3]))
    guia = config.RAIZ / "librerias" / "estilos" / f"{estilo}.md"
    if not guia.exists():
        raise ValueError(f"falta la guía {guia.name}: escríbela antes de integrar (es criterio, no se genera)")

    antes = ejemplos / "_antes" / time.strftime("%Y%m%d-%H%M")
    ej, pal = ejemplos / f"{estilo}.json", ejemplos / f"{estilo}.palabras.json"
    for f in (ej, pal):
        if f.exists():
            antes.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, antes / f.name)
    ej.write_text(json.dumps(sb, ensure_ascii=False, indent=1))
    shutil.copy2(carpeta / "palabras.json", pal)
    obs = ejemplos / "OBSOLETOS.txt"
    if obs.exists():
        lineas = obs.read_text().splitlines()
        obs.write_text("\n".join(l for l in lineas if l.strip() != ej.name) + "\n")

    todos = json.loads(presets.read_text())
    if estilo in todos:
        antes.mkdir(parents=True, exist_ok=True)
        (antes / f"preset-{estilo}.json").write_text(json.dumps(todos[estilo], ensure_ascii=False, indent=1))
    viejo = todos.get(estilo, {})
    todos[estilo] = {"nombre": nombre or viejo.get("nombre") or estilo,
                     **{k: v for k, v in sb["estilo"].items() if k not in NO_VAN_AL_PRESET},
                     **{k: viejo[k] for k in SE_CONSERVAN if k in viejo}}
    presets.write_text(json.dumps(todos, ensure_ascii=False, indent=1))
    avance(f"{estilo}: ejemplo, palabras y preset integrados desde {carpeta.name}")
    if (carpeta / "final.mp4").exists() and ejemplos == EJEMPLOS:   # la portada del carrusel sale de su video aprobado
        try:
            from . import portadas
            portadas.portada(estilo, carpeta)
        except Exception as e:  # noqa: BLE001 — sin portada el estilo igual queda integrado
            avance(f"{estilo}: sin portada ({e})")
    return {"ejemplo": str(ej), "palabras": str(pal), "preset": estilo, "respaldo": str(antes) if antes.exists() else ""}
