"""Discos del trabajo pesado: nada de escribir en una SD/USB (se desmonta y deja enlaces rotos) ni por un enlace roto.

Casos reales: c8868/c8870/c8871 apuntan a /mnt/g (una unidad extraíble que ya no está) y `symlink_to` sobre un enlace roto
daba `FileExistsError`.
"""
import os
import re
import shutil
from pathlib import Path

from . import entorno

FIJO, EXTRAIBLE, RED, OPTICO = 3, 2, 4, 5
HOLGURA_MIN_GB = 20            # espacio libre mínimo en el disco de trabajo
BLOQUEADAS_ENV = "ESTUDIO_UNIDADES_BLOQUEADAS"   # letras (p. ej. "G,H") de discos USB que Windows marca como fijos


class DiscoError(RuntimeError):
    """El disco o el enlace no sirve para trabajar; el mensaje dice cuál unidad y qué hacer."""


def letra(ruta) -> str | None:
    """Letra de unidad de una ruta /mnt/<letra>/… (None si es disco de Linux)."""
    m = re.match(r"^/mnt/([a-z])(?:/|$)", str(ruta))
    return m.group(1).upper() if m else None


def tipo_unidad(l: str) -> int | None:
    """DriveType de Windows (3 fijo, 2 extraíble…) o None si no se pudo medir."""
    r = entorno.correr_windows("powershell.exe", ["-NoProfile", "-Command",
                               f"(Get-CimInstance Win32_LogicalDisk -Filter \"DeviceID='{l}:'\").DriveType"])
    if r is None or not r.stdout.strip().isdigit():
        return None
    return int(r.stdout.strip())


def validar_trabajo_en(ruta, minimo_gb=HOLGURA_MIN_GB) -> None:
    """Rechaza (DiscoError) un disco de trabajo extraíble, bloqueado, que no se pueda comprobar o sin espacio."""
    ruta = Path(ruta)
    l = letra(ruta)
    if l:
        if l in {x.strip().upper() for x in os.environ.get(BLOQUEADAS_ENV, "").split(",") if x.strip()}:
            raise DiscoError(f"--trabajo-en {ruta}: la unidad {l}: está en la lista de bloqueadas ({BLOQUEADAS_ENV})")
        tipo = tipo_unidad(l)
        if tipo is None:
            raise DiscoError(f"--trabajo-en {ruta}: no pude comprobar si la unidad {l}: es fija (¿falta powershell.exe?)")
        if tipo != FIJO:
            raise DiscoError(f"--trabajo-en {ruta}: la unidad {l}: es extraíble o de red (tipo {tipo}); usa un disco fijo")
    base = ruta
    while not base.exists() and base != base.parent:
        base = base.parent
    if not base.exists() or shutil.disk_usage(base).free / 1e9 < minimo_gb:
        raise DiscoError(f"--trabajo-en {ruta}: menos de {minimo_gb} GB libres (o la unidad no está montada)")


def rotos(proyectos: Path) -> list:
    """[(enlace, destino)] enlaces de la carpeta de proyectos cuyo destino ya no existe."""
    proyectos = Path(proyectos)
    if not proyectos.exists():
        return []
    return [(p, Path(os.readlink(p))) for p in sorted(proyectos.iterdir()) if p.is_symlink() and not p.exists()]


def revisar_enlaces(proyectos: Path, reparar=False) -> list:
    """Informe de enlaces rotos: [{proyecto, destino, unidad, accion}]. Con `reparar`, si el destino está en un disco fijo
    montado se recrea la carpeta (queda «sin datos»: el lote lo vuelve a preparar); si no, solo se informa."""
    informe = []
    for enlace, destino in rotos(proyectos):
        l = letra(destino)
        fijo = (l is None and destino.parent.exists()) or (l is not None and destino.parent.exists() and tipo_unidad(l) == FIJO)
        accion = "recreada (sin datos: se vuelve a preparar)" if fijo and reparar else \
            ("recreable" if fijo else f"unidad {l or '?'}: no está o es extraíble: reconecta el disco o prepara el video de nuevo")
        if fijo and reparar:
            destino.mkdir(parents=True, exist_ok=True)
        informe.append({"proyecto": enlace.name, "destino": str(destino), "unidad": l, "accion": accion})
    return informe


def enlazar(enlace: Path, destino: Path) -> None:
    """Deja `enlace` apuntando a `destino`, aunque ya exista un enlace roto o viejo con ese nombre."""
    if enlace.is_symlink():
        if enlace.exists() and enlace.resolve() == Path(destino).resolve():
            return
        enlace.unlink()
    elif enlace.exists():
        raise DiscoError(f"{enlace} existe y no es un enlace: no lo piso")
    Path(destino).mkdir(parents=True, exist_ok=True)
    enlace.symlink_to(destino, target_is_directory=True)
