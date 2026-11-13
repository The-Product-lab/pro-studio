"""Editar un LOTE de videos en varios estilos con la app (director + compuerta + render), sin vigilarlo.

Pablo (04-nov): «necesito editar todos los videos de la carpeta claude workshop… con los dos de Julián Alborna, prestiggio,
luminoso, imprenta, vox, cine, swiss».

- Cada video se prepara UNA vez (transcribir, ubicar a la persona, montaje limpio) y de ahí salen todos sus estilos (`--desde`).
- Orden: video por video (todos los estilos del primero, luego el segundo…), para ver resultados pronto.
- Cada paso pesado va por la cola `pesado.sh`; se retoma solo (lo que ya tiene su final no se rehace).
- Freno de disco: si C: (donde vive el disco de Linux) baja de `DISCO_MIN_GB`, se detiene y avisa.
- Arte: `--biblioteca estilo=carpeta` reusa imágenes ya hechas; sin generar (créditos) salvo que se pida.
- Los finales se copian a `--salida` como `<VIDEO>-<estilo>.mp4` y el avance queda en `<salida>/LOTE.json`.

    uv run estudio lote "<carpeta de videos>" --estilos julian-alborna,vox --salida "<carpeta>" --biblioteca vox=proyectos/c8866-vox/arte
"""
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

from . import config, disco, entorno

DISCO_MIN_GB = 6
HOLGURA_UBUNTU_MIN_GB = 2     # Pablo (04-nov): «ojo con usar Ubuntu y llenarlo; no quiero compactar»: el disco de Linux no crece
VHDX = os.environ.get("ESTUDIO_VHDX") or ""   # carpeta de los discos de WSL; vacío = la de este usuario de Windows (%LOCALAPPDATA%\wsl)
PESADO = config.pesado() or config.TPS / "sin-cola-pesado"
VIDEOS = (".mp4", ".mov", ".mxf")


def libre_gb(ruta="/mnt/c") -> float:
    return shutil.disk_usage(ruta).free / 1e9 if Path(ruta).exists() else 999.0


def holgura_ubuntu_gb() -> float | None:
    """Espacio ya reservado dentro del disco de Ubuntu (tamaño del .vhdx − lo usado): escribir ahí no lo hace crecer.
    None si no se pudo medir (sin powershell o fuera de WSL): la guarda lo dice, no finge que todo está bien."""
    carpeta = "'" + VHDX.replace("'", "''") + "'" if VHDX else "(Join-Path $env:LOCALAPPDATA 'wsl')"
    r = entorno.correr_windows("powershell.exe", ["-NoProfile", "-Command",
                               f"(Get-ChildItem -Path {carpeta} -Recurse -Filter ext4.vhdx | Measure-Object Length -Sum).Sum"])
    try:
        vhdx = float(r.stdout.strip()) if r else 0
    except ValueError:
        vhdx = 0
    if not vhdx:
        return None
    return (vhdx - shutil.disk_usage("/").used) / 1e9


def _windows(ruta: Path) -> str:
    r = subprocess.run(["wslpath", "-w", str(ruta)], capture_output=True, text=True)
    return r.stdout.strip()


def liberar_crudo(video: Path) -> str | None:
    """El crudo ya preparado queda «solo en la nube» de OneDrive (sigue en OneDrive; deja de ocupar C:).
    Mejor esfuerzo: si no se puede, devuelve el motivo (el lote lo anota) y sigue."""
    if "OneDrive" not in str(video):
        return None
    r = entorno.correr_windows("attrib.exe", ["-P", "+U", _windows(video)])
    if r is None:
        return f"no pude liberar {video.name} de C: (attrib.exe no disponible)"
    return None if r.returncode == 0 else f"attrib.exe salió con código {r.returncode} al liberar {video.name}"


def _correr(args: list, log: Path) -> int:
    cmd = ([str(PESADO)] if PESADO.exists() else []) + ["uv", "run", "--quiet"] + args
    with open(log, "a") as f:
        f.write(f"\n$ {' '.join(args)}\n")
        f.flush()
        return subprocess.run(cmd, cwd=config.RAIZ, stdout=f, stderr=subprocess.STDOUT).returncode


def lote(carpeta: Path, estilos: list, salida: Path, bibliotecas: dict | None = None, con_imagenes=False, rondas=1,
         preferencias_de: str | None = None, asignar: dict | None = None, telegram=False, trabajo_en: Path | None = None,
         avance=print) -> dict:
    """`preferencias_de`: proyecto cuyo `preferencias.json` (el color que Pablo eligió) se usa en los videos de la misma sesión.
    `asignar`: {VIDEO: estilo} — un estilo por video (Pablo, 04-nov: «es un estilo por cada video»); sin él, todos los estilos a cada uno."""
    carpeta, salida = Path(carpeta), Path(salida)
    if trabajo_en:
        disco.validar_trabajo_en(trabajo_en)     # DiscoError: no se arranca en una unidad extraíble ni sin espacio
    salida.mkdir(parents=True, exist_ok=True)
    estado_f = salida / "LOTE.json"
    estado = json.loads(estado_f.read_text()) if estado_f.exists() else {}
    log = salida / "LOTE.log"
    videos = sorted(f for f in carpeta.iterdir() if f.suffix.lower() in VIDEOS)

    def guardar(clave, valor):
        estado[clave] = valor
        estado_f.write_text(json.dumps(estado, ensure_ascii=False, indent=1))

    for r in disco.revisar_enlaces(config.PROYECTOS, reparar=False):
        avance(f"enlace roto: proyectos/{r['proyecto']} -> {r['destino']} ({r['accion']})")
    if asignar:
        videos = [v for v in videos if v.stem.upper() in {k.upper() for k in asignar}]
    for v in videos:
        base = v.stem.lower()
        propios = [e for k, e in asignar.items() if k.upper() == v.stem.upper()] if asignar else estilos
        for estilo in propios:
            clave = f"{v.stem}-{estilo}"
            if (salida / f"{clave}.mp4").exists():
                continue
            holgura = holgura_ubuntu_gb()
            if holgura is None:
                if entorno.en_wsl():   # Mac, Linux y Windows nativo no tienen un disco de Ubuntu que vigilar: ahí no hay nada que avisar
                    guardar("_guarda_ubuntu", "desactivada: no pude medir el disco de Ubuntu (¿falta powershell.exe?)")
            elif holgura < HOLGURA_UBUNTU_MIN_GB:
                guardar("_parado", f"{time.strftime('%H:%M')} el disco de Ubuntu tendría que crecer (holgura {holgura:.1f} GB): libera espacio adentro")
                avance(estado["_parado"])
                return estado
            if libre_gb() < DISCO_MIN_GB:
                guardar("_parado", f"{time.strftime('%H:%M')} disco C: con {libre_gb():.1f} GB libres (mín. {DISCO_MIN_GB}): libera espacio y vuelve a correr")
                avance(estado["_parado"])
                return estado
            destino_base = config.PROYECTOS / base
            if destino_base.is_symlink() and not destino_base.exists() and not trabajo_en:
                guardar(v.stem, f"falló: proyectos/{base} es un enlace roto (-> {os.readlink(destino_base)}); usa --trabajo-en o prepara de nuevo")
                avance(estado[v.stem])
                break
            if not (destino_base / "palabras.json").exists():
                if trabajo_en and (not destino_base.exists()):   # lo pesado (video normalizado) fuera de Ubuntu; rehace enlaces rotos
                    disco.enlazar(destino_base, Path(trabajo_en) / base)
                avance(f"{v.name}: preparando…")
                guardar(v.stem, "preparando")
                cod = _correr(["python", "-c", f"from estudio import ingesta; ingesta.preparar({str(v)!r}, {base!r}, print)"], log)
                if cod:
                    guardar(v.stem, f"falló la preparación (ver LOTE.log)")
                    break
            if (config.PROYECTOS / base / "palabras.json").exists():
                motivo = liberar_crudo(v)
                if motivo:
                    avance(motivo)
                    guardar("_aviso_liberar", motivo)
            pref = config.PROYECTOS / base / "preferencias.json"
            if preferencias_de and not pref.exists() and (config.PROYECTOS / preferencias_de / "preferencias.json").exists():
                shutil.copy2(config.PROYECTOS / preferencias_de / "preferencias.json", pref)
            avance(f"{clave}: editando…")
            guardar(clave, "editando")
            proyecto = f"lote-{base}-{estilo}"   # nombre propio: nunca pisa las copias aprobadas (c8866-<estilo>)
            args = ["estudio", "editar", "--desde", base, "--estilo", estilo, "--nombre", proyecto, "--rondas", str(rondas)]
            if not con_imagenes:
                args.append("--sin-imagenes")
            if (bibliotecas or {}).get(estilo):
                args += ["--biblioteca", str(bibliotecas[estilo])]
            final = config.PROYECTOS / proyecto / "final.mp4"
            cod = 0 if final.exists() else _correr(args, log)   # si ya quedó hecho (lote cortado), no se vuelve a dirigir
            if cod == 0 and final.exists():
                shutil.copy2(final, salida / f"{clave}.mp4")
                guardar(clave, f"listo {time.strftime('%H:%M')}")
                if telegram:   # Pablo: «mandar cada resultado completo por Telegram»
                    from . import avisar
                    try:
                        avisar.video(salida / f"{clave}.mp4", f"{v.stem} · {estilo} · editado por la app")
                    except Exception as x:  # noqa: BLE001 — sin Telegram el lote sigue
                        avance(f"Telegram: {x}")
            else:
                guardar(clave, f"falló (código {cod}; ver LOTE.log)")
    guardar("_parado", "")
    return estado
