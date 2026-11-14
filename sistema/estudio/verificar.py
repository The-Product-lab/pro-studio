"""`estudio verificar`: capa 1 de la compuerta (< 60 s, sin video, sin IA, en cualquier máquina).

Sale 0 si todo pasa y 1 si algo falla. Es lo que corren el hook pre-push y GitHub Actions.
Revisa, en orden:
  1. Sin basura: el repo guarda SOLO lo necesario para producir (regla de Pablo, 07-nov).
  2. El código compila.
  3. Todas las pruebas pasan, y su número no baja respecto a tests/linea-base.json.
  4. Cada corrección de clase «sistema» de perfil/correcciones.jsonl tiene su prueba en tests/regresion/.
Las pruebas que dependen de un recurso de la máquina (un proyecto, un video) se saltan si falta; nunca fallan por eso.
"""
import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
MAX_BYTES = 5 * 1024 * 1024
VIDEO = {".mp4", ".mov", ".mxf", ".m4v", ".mkv", ".avi", ".webm"}
CARPETAS_BASURA = {".intentos", "intentos", "_antes", "tmp", "temp", "salidas", "backup", "backups"}
SUFIJOS_BASURA = (".bak", ".orig", ".rej", ".tmp", "~")
MIN_DUPLICADO = 200   # bytes: los archivos casi vacíos (__init__.py) no cuentan como copias
CONOCIDA = RAIZ / "tests" / "basura-conocida.txt"   # deuda que baja, nunca sube (la limpieza la va vaciando)
LINEA_BASE = RAIZ / "tests" / "linea-base.json"


# En el paquete instalado esta lista es lo que git rastreaba en el repo de origen. Manda aunque haya `.git`: el instalador crea uno
# propio (para el Agente Editor) con TODO lo instalado, también Lemo, y con ese `verificar` salía rojo en un equipo recién instalado.
MANIFIESTO = RAIZ / "MANIFIESTO.txt"


def _git(*args) -> list[str]:
    if args[:1] == ("ls-files",) and MANIFIESTO.exists():
        return [l for l in MANIFIESTO.read_text(encoding="utf-8").splitlines() if l.strip()]
    out = subprocess.run(["git", "-C", str(RAIZ), *args], capture_output=True, text=True, check=True).stdout
    return [x for x in out.split("\0") if x]


def _conocida() -> set[str]:
    if not CONOCIDA.exists():
        return set()
    return {l.strip() for l in CONOCIDA.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")}


def sin_basura(archivos: list[str] | None = None) -> list[str]:
    """Problemas de limpieza en lo que git rastrea. Lista vacía = limpio."""
    if archivos is None:
        archivos = _git("ls-files", "-z")
    conocida = _conocida()
    fallas, por_hash = [], {}
    for rel in archivos:
        if rel in conocida:
            continue
        ruta = RAIZ / rel
        if not ruta.is_file():
            continue   # borrado sin commit o enlace roto: git lo dirá, no esta puerta
        partes = Path(rel).parts
        if ruta.suffix.lower() in VIDEO:
            fallas.append(f"video versionado: {rel} (los videos no van a git)")
        elif ruta.stat().st_size > MAX_BYTES:
            fallas.append(f"archivo grande ({ruta.stat().st_size // 1024 // 1024} MB > 5 MB): {rel}")
        if CARPETAS_BASURA & set(p.lower() for p in partes[:-1]):
            fallas.append(f"carpeta de intentos o temporales versionada: {rel}")
        elif rel.endswith(SUFIJOS_BASURA):
            fallas.append(f"copia o temporal versionado: {rel}")
        if ruta.stat().st_size >= MIN_DUPLICADO:
            por_hash.setdefault(hashlib.sha1(ruta.read_bytes()).hexdigest(), []).append(rel)
    for rutas in por_hash.values():
        if len(rutas) > 1:
            fallas.append("copias idénticas: " + ", ".join(rutas))
    return fallas


def compila() -> list[str]:
    r = subprocess.run([sys.executable, "-m", "compileall", "-q", "estudio", "tests"], cwd=RAIZ, capture_output=True, text=True)
    return [] if r.returncode == 0 else [(r.stdout + r.stderr).strip()[-800:]]


def pruebas() -> tuple[list[str], str]:
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"], cwd=RAIZ, capture_output=True, text=True)
    resumen = (r.stdout.strip().splitlines() or [""])[-1]
    if r.returncode != 0:
        return [f"pytest falló: {resumen}\n" + "\n".join(r.stdout.strip().splitlines()[-25:])], resumen
    total = sum(int(n) for n, k in re.findall(r"(\d+) (passed|skipped)", resumen))
    if LINEA_BASE.exists():
        minimo = json.loads(LINEA_BASE.read_text(encoding="utf-8")).get("pruebas_min", 0)
        if total < minimo:
            return [f"hay {total} pruebas y la línea base exige {minimo}: no se arregla borrando pruebas"], resumen
    return [], resumen


def correcciones_con_prueba() -> list[str]:
    """Cada corrección de clase «sistema» (N3: compuerta en código) debe tener tests/regresion/test_<id>.py."""
    f = RAIZ / "perfil" / "correcciones.jsonl"
    if not f.exists():
        return []
    fallas = []
    for linea in f.read_text(encoding="utf-8").splitlines():
        try:
            c = json.loads(linea)
        except ValueError:
            continue
        cid = c.get("id")
        if cid and c.get("clase") == "sistema" and not (RAIZ / "tests" / "regresion" / f"test_{cid}.py").exists():
            fallas.append(f"la corrección {cid} es de sistema y no tiene tests/regresion/test_{cid}.py")
    return fallas


def verificar() -> int:
    t0 = time.time()
    fallas = []
    pasos = [("sin basura", sin_basura), ("compila", compila), ("correcciones con prueba", correcciones_con_prueba)]
    for nombre, paso in pasos:
        r = paso()
        print(f"{'OK ' if not r else 'FALLA'} {nombre}")
        fallas += r
    r, resumen = pruebas()
    print(f"{'OK ' if not r else 'FALLA'} pruebas ({resumen})")
    fallas += r
    for f in fallas:
        print(" -", f)
    print(f"verificar: {'verde' if not fallas else 'ROJO'} en {time.time() - t0:.0f} s")
    return 1 if fallas else 0


def main() -> int:
    return verificar()
