"""Pantalla de revisión: los finales de cada estilo (video + storyboard + lado a lado + ficha) con un cuadro para el feedback de Pablo.

Las notas se guardan en `proyectos/FEEDBACK.json` (una por envío: estilo, segundo del video, texto, aprueba) y son lo que se lee
para corregir. Ruta en la app: /revision.
"""
import json
import time
from pathlib import Path

from . import config

CARPETA = config.REVISION
NOTAS = config.PROYECTOS / "FEEDBACK.json"
ESTILOS = [("luminoso", "luminoso4", "Dbq9awKotYY"), ("maestro", "maestro", "DRUpn + DexAo + DfAE"), ("swiss", "swiss", "De9SYDwhTG0"),
           ("vox", "vox", "DbGP21gqRnm"), ("pop", "pop", "Db70QWsA9wd"), ("cine", "cine", "DfM5 + DbqvQ"),
           ("glass", "glass", "DfMi_f0jseK"), ("imprenta", "imprenta", "DeMdv7NqeL-"), ("prestiggio", "prestiggio", "estilo de la app Prestiggio"), ("julian-alborna", "julian-alborna", "Estilo papel (vidIQ + tutoriales)"), ("julian-alborna-3d", "julian-alborna-3d", "3D sobre negro (Higgsfield)")]


def _src(nombre: str) -> str:
    return f"/revision-archivo/{nombre}" if (CARPETA / nombre).exists() else ""


def notas() -> list:
    return json.loads(NOTAS.read_text()) if NOTAS.exists() else []


def lista() -> list:
    todas = notas()
    return [{"estilo": e, "referente": ref, "video": _src(f"COPIA-{a}.mp4"), "storyboard": _src(f"STORYBOARD-{a}.jpg"),
             "lado": _src(f"COPIA-{a}-lado-a-lado.jpg"), "ficha": _src(f"FICHA-{e}.jpg") or _src(f"FICHA-{e.split('-')[0]}.jpg"),
             "notas": [n for n in todas if n["estilo"] == e]} for e, a, ref in ESTILOS]


def anotar(estilo: str, texto: str, segundo=None, aprueba: bool = False) -> list:
    if estilo not in {e for e, _, _ in ESTILOS} or not (texto.strip() or aprueba):
        raise ValueError("falta el estilo o el texto")
    todas = notas()
    todas.append({"estilo": estilo, "texto": texto.strip(), "segundo": segundo, "aprueba": bool(aprueba),
                  "fecha": time.strftime("%Y-%m-%d %H:%M"), "hecho": False})
    NOTAS.write_text(json.dumps(todas, ensure_ascii=False, indent=1))
    return [n for n in todas if n["estilo"] == estilo]


_COLA = __import__("threading").Lock()   # una corrección a la vez: cada una lleva un agente Opus y un render


def corregir(estilo: str, texto: str, segundo=None, avance=print) -> dict:
    """«Corregir»: guarda la nota, el Agente Editor la aplica al storyboard de la copia, se vuelve a renderizar y el video
    nuevo reemplaza al de REVISION (el anterior queda como COPIA-<estilo>-antes.mp4)."""
    import shutil
    from . import agente, motor
    anotar(estilo, texto, segundo)
    a = dict((e, a) for e, a, _ in ESTILOS)[estilo]
    proyecto = f"c8866-{a}"
    if not (config.PROYECTOS / proyecto).is_dir():   # las copias aprobadas son del taller (el video C8866): fuera de esa máquina no hay qué corregir
        raise FileNotFoundError("Esta pantalla corrige las copias aprobadas del taller y esta máquina no las tiene. Tu nota quedó guardada.")
    avance("En cola…" if _COLA.locked() else "Empezando…")
    with _COLA:
        pedido = (f"{texto}\n\n(Desde la pantalla de revisión, estilo «{estilo}»"
                  + (f", segundo {segundo:.1f} del video final" if segundo is not None else "")
                  + f". Aplícalo al storyboard de proyectos/{proyecto}; NO lo renderices tú: el render lo hace la app al terminar."
                  " Si es un gusto general, además anótalo como gusto.)")
        reg = agente.corregir(pedido, proyecto, avance)
        avance(f"Corrección aplicada: {reg.get('resumen') or ''}. Renderizando el video nuevo…")
        final = motor.render(config.PROYECTOS / proyecto, avance=avance)
        destino = CARPETA / f"COPIA-{a}.mp4"
        if destino.exists():
            shutil.copy2(destino, CARPETA / f"COPIA-{a}-antes.mp4")
        shutil.copy2(final, destino)
    todas = notas()
    for n in reversed(todas):
        if n["estilo"] == estilo and n["texto"] == texto.strip():
            n.update(hecho=True, resumen=reg.get("resumen"), id=reg.get("id"))
            break
    NOTAS.write_text(json.dumps(todas, ensure_ascii=False, indent=1))
    avance("Listo: el video nuevo ya está en la pantalla.")
    return {"resumen": reg.get("resumen"), "id": reg.get("id")}
