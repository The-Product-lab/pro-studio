"""Prueba de NO DAÑO de los estilos con render real (pesada, a mano; la liviana es tests/test_estilos_fichas.py).

Para cada estilo vigente toma un storyboard ya existente (proyectos/c8866-<estilo>; basico: c8872-basico), lo COPIA a
proyectos/_estilos-<estilo> con el bloque `estilo` recalculado desde el preset de hoy (como lo hace el director) y dibuja con el
motor (sin director, sin Opus) ~9 s con subtítulo y apoyos, 1 de cada 4 cuadros. Guarda o compara la huella (sha256) de cada cuadro.
  uv run python tests/render_nodano.py guardar [estilo ...]   → escribe tests/estilos_nodano/<estilo>.json
  uv run python tests/render_nodano.py comparar [estilo ...]  → sale 1 si algún cuadro cambió
Los cuadros se dibujan con la misma función que usa el render real (motor.Proyecto.cuadro). Las copias se borran al terminar.
Lo pesado va por pesado.sh:  ~/claude-code/captions/tools/pesado.sh uv run python tests/render_nodano.py comparar"""
import hashlib
import json
import shutil
import sys
from pathlib import Path

from PIL import Image

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from estudio import config, motor  # noqa: E402

BANCO = Path(__import__("os").environ.get("TPS_BANCO_PROYECTOS", RAIZ.parent / "the-product-studio-2" / "proyectos"))
GOLDEN = RAIZ / "tests" / "estilos_nodano"
PRESETS = RAIZ / "librerias" / "estilos" / "presets.json"
FUERA = {".tramos", ".cuadros", "final.mp4", "video_mudo.mp4", "sfx.wav", "copia.py", "lado.py"}
SEG, PASO = 9, 4
# cambios decididos por Pablo (10-nov) que SÍ mueven los cuadros: «un movimiento a la vez» baja flotar_elementos a 2. Hasta que Pablo los vea y se
# vuelva a hacer `guardar`, `comparar` los avisa pero no los cuenta como daño.
INTENCIONALES = {"luminoso", "julian-alborna", "julian-alborna-3d", "glass"}   # glass: flotar 48 (que la flotación se vea)


def origen(estilo):
    return BANCO / ("c8872-basico" if estilo == "basico" else f"c8866-{estilo}")


def enlazar_banco():
    """Los storyboards citan arte de otros proyectos con rutas relativas (../c8866-maestro/arte/...): se enlazan aquí, solo lectura."""
    config.PROYECTOS.mkdir(exist_ok=True)
    for d in BANCO.iterdir():
        if d.is_dir() and not d.name.startswith("_") and not (config.PROYECTOS / d.name).exists():
            (config.PROYECTOS / d.name).symlink_to(d)


def copiar(estilo):
    enlazar_banco()
    src, dst = origen(estilo), config.PROYECTOS / f"_estilos-{estilo}"
    shutil.rmtree(dst, ignore_errors=True)
    dst.mkdir(parents=True)
    for f in src.iterdir():
        if f.name in FUERA or f.name.startswith(("previa", ".audio", ".energia")):
            continue
        if f.is_symlink():
            dst.joinpath(f.name).symlink_to(f.resolve())
        elif f.is_dir():
            shutil.copytree(f, dst / f.name, symlinks=True)
        else:
            shutil.copy2(f, dst / f.name)
    sb = json.loads((dst / "storyboard.json").read_text())
    pre = json.loads(PRESETS.read_text())[estilo]
    sb["estilo"] = {"id": estilo, **{k: v for k, v in pre.items() if k != "nombre"}}
    prefs = dst / "preferencias.json"   # lo que Pablo eligió para el video (p. ej. el color) manda sobre el preset, como en el director
    if prefs.exists():
        sb["estilo"].update(json.loads(prefs.read_text()).get("estilo", {}))
    (dst / "storyboard.json").write_text(json.dumps(sb, ensure_ascii=False, indent=1))
    return dst


def ventana(p):
    """~9 s con más apoyos que ninguna otra (y con subtítulo): rango de cuadros de salida."""
    mejor, t_mejor = -1, 0.0
    fin = max(p.mapa) / motor.FPS
    for t in [x / 2 for x in range(0, int(max(fin - SEG, 0) * 2) + 1)]:
        n = sum(1 for e in p.sb.get("elementos", []) if e.get("t0", 0) < t + SEG and e.get("t1", 0) > t)
        n += sum(1 for w in p.palabras if t <= w.get("s", -1) < t + SEG) // 20
        if n > mejor:
            mejor, t_mejor = n, t
    a = next(i for i, m in enumerate(p.mapa) if m / motor.FPS >= t_mejor)
    return a, min(len(p.mapa), a + SEG * motor.FPS)


def huellas(estilo):
    dst = copiar(estilo)
    try:
        p = motor.Proyecto(dst)
        a, b = ventana(p)
        out = {}
        for of, rgb in motor.recorrer(p, solo=range(a, b, PASO)):
            out[str(of)] = hashlib.sha256(rgb.tobytes() if hasattr(rgb, "tobytes") else bytes(rgb)).hexdigest()[:20]
        return out
    finally:
        shutil.rmtree(dst, ignore_errors=True)


def pngs(estilo, carpeta):
    """3 cuadros del tramo (para que Pablo los vea): carpeta/<estilo>-<cuadro>.png"""
    dst = copiar(estilo)
    try:
        p = motor.Proyecto(dst)
        a, b = ventana(p)
        Path(carpeta).mkdir(parents=True, exist_ok=True)
        for of, im in motor.recorrer(p, solo=[a + (b - a) * k // 10 for k in (2, 5, 8)]):
            Image.fromarray(im).save(Path(carpeta) / f"{estilo}-{of}.png")
            print(Path(carpeta) / f"{estilo}-{of}.png")
    finally:
        shutil.rmtree(dst, ignore_errors=True)


def main():
    if sys.argv[1] == "png":   # png <estilo> <carpeta>
        return pngs(sys.argv[2], sys.argv[3])
    modo, estilos = sys.argv[1], sys.argv[2:] or sorted(json.loads(PRESETS.read_text()))
    malos = []
    for e in estilos:
        h = huellas(e)
        ruta = GOLDEN / f"{e}.json"
        if modo == "guardar":
            ruta.write_text(json.dumps(h, indent=0))
            print(f"{e}: {len(h)} cuadros guardados")
        else:
            ref = json.loads(ruta.read_text())
            dif = [k for k in ref if ref[k] != h.get(k)]
            print(f"{e}: {'IDÉNTICO' if not dif else 'CAMBIÓ en ' + str(len(dif)) + ' de ' + str(len(ref)) + ' cuadros'}")
            if dif and e in INTENCIONALES:
                print(f"  (cambio intencional de Pablo, 10-nov: flotar_elementos = 2; rehacer la base con `guardar {e}` tras verlo)")
            elif dif:
                malos.append(e)
    sys.exit(1 if malos else 0)


if __name__ == "__main__":
    main()
