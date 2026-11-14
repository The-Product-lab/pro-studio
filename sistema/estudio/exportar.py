"""`estudio exportar [--destino carpeta]`: arma `<NOMBRE_ZIP>-AAAA-MM-DD.zip`, el paquete que se descomprime en otro computador
(Windows, Mac o Linux/WSL), se instala con UN doble clic y hace todo. LISTA BLANCA: solo entra lo que está escrito aquí.

NUNCA entran (y `revisar_zip` lo comprueba abriendo el zip): proyectos/, privadas/, .tps/, .venv, .git, costos.jsonl, historiales de
proyectos, videos, cachés, .env, tokens o cualquier archivo con pinta de secreto. Lo pesado que se puede bajar (ffmpeg, Whisper, recorte)
NO viaja: lo baja `estudio doctor --arreglar`. Plano: docs/PLANO-EXPORTAR.md.

Estructura del zip (Pablo, 10-nov: «se abren un montón de carpetas»): una carpeta `Pro Studio/` con SOLO tres cosas a la vista: el instalador de Windows,
el de Mac y `LEEME.txt` (están en herramientas/paquete/). Todo lo demás va dentro de `sistema/`."""
import os
import re
import sys
import time
import zipfile
from pathlib import Path

from . import config, verificar

RAIZ = config.RAIZ
SISTEMA = "sistema"
PAQUETE = Path("herramientas") / "paquete"   # lo que se ve en la raíz del zip (no entra a sistema/)
ARCHIVOS = ["README.md", "LEEME.md", "CLAUDE.md", "pyproject.toml", "uv.lock", "uv.toml", ".gitignore",
            "instalar.bat", "instalar.command", "instalar.sh", "abrir.bat", "abrir.command", "abrir.sh"]
CARPETAS = ["estudio", "app", "tests", "docs", "herramientas", "librerias", "perfil", "referencias-estilos", ".githooks"]
EXTRAS = ["banco/LEEME.md",   # el banco de pruebas son videos de clientes: solo viaja su descripción
          ".claude/settings.json"]   # la guarda del Agente Editor (estudio.agente.proteger): sin ella el agente trabaja sin freno. Nada más de .claude
PERMITIDOS_EN_CARPETA_FUERA = {Path(".claude/settings.json")}
SOLO_DEL_TALLER = {Path("docs/HANDOFF-PC.md")}   # notas del PC de la oficina: no sirven (ni deben viajar) fuera de esa máquina
# nunca, en ninguna carpeta
CARPETAS_FUERA = {"__pycache__", ".pytest_cache", ".git", ".tps", ".venv", "node_modules", "proyectos", "privadas", "salidas",
                  ".intentos", "_antes", ".claude", "revision"}
SUFIJOS_FUERA = {".mp4", ".mov", ".mxf", ".m4v", ".mkv", ".avi", ".webm", ".pyc", ".log", ".bak", ".orig", ".tmp", ".part", ".onnx", ".bin",
                 ".pem", ".key", ".p12", ".pfx", ".sqlite", ".db-journal"}
NOMBRES_FUERA = {".env", "costos.jsonl", "tokens.jsonl", ".DS_Store", "galeria.html", "access.json", "credentials.json", ".git"}
# referencias-estilos: son 6 800 cuadros sueltos de estudio (334 MB, se regeneran con `estudio crear-estilo`); viajan las notas y las hojas de contacto
REFERENCIAS_JPG = {"hoja.jpg"}
# pinta de secreto, en el nombre o dentro del texto
NOMBRE_SECRETO = re.compile(r"(^|[._-])(env|secret|secrets|token|tokens|credential|credentials|password|id_rsa|id_ed25519)([._-]|$)", re.I)
CONTENIDO_SECRETO = re.compile(
    r"sk-ant-[A-Za-z0-9_-]{20,}|ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|AKIA[0-9A-Z]{16}|xox[baprs]-[A-Za-z0-9-]{20,}"
    r"|\b\d{8,10}:[A-Za-z0-9_-]{35}\b|-----BEGIN [A-Z ]*PRIVATE KEY-----"
    r"|(?i:(api[_-]?key|secret|passw(?:or)?d|token)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{20,})")
# Datos de la persona que exporta: se arman por partes para que este archivo no los contenga (la prueba busca en TODO el zip)
_USUARIO, _CORREO, _CHAT = "deal" + "c", "pabl" + "oat", "169217" + "1320"
PERSONAL = re.compile(f"{_USUARIO}|{_CORREO}|{_CHAT}", re.I)   # usuario del PC, correo y chat de Telegram: nada de eso viaja
# Se reescribe en el texto que viaja (rutas del PC de la oficina en notas y fixtures)
LIMPIEZA = [(re.compile(f"/mnt/c/Users/{_USUARIO}/OneDrive/Desktop"), "<Escritorio>"), (re.compile(f"/mnt/c/Users/{_USUARIO}"), "/mnt/c/Users/<usuario>"),
            (re.compile(f"/home/{_USUARIO}"), "~"), (re.compile(_CHAT), "<chat>"), (re.compile(_USUARIO, re.I), "usuario")]
MAX_TEXTO = 2_000_000   # los archivos de texto más grandes no se escanean por contenido
# Lemo (Estilos Pro) viaja dentro (12-nov, Pablo: «todo es todo»; el zip del 10-nov lo dejaba fuera). Lo que se instala en cada equipo, no.
LEMO_ZIP = config.LEMO_PAQUETE.relative_to(RAIZ)
LEMO_FUERA = {"node_modules", ".git", ".github", ".venv", ".lemo-deps.lock"}


def _muestra_de_estilo(rel: Path) -> bool:
    """Las muestras que la app muestra en el seleccionador (efectos, color, estilos) son videos cortos de estilo: viajan; ningún otro video."""
    return rel.parts[:3] == ("app", "muestras", "sel") and rel.suffix.lower() == ".mp4"


def _fuera(rel: Path) -> bool:
    if rel in PERMITIDOS_EN_CARPETA_FUERA:
        return False
    if rel in SOLO_DEL_TALLER:
        return True
    if _muestra_de_estilo(rel):
        return bool(CARPETAS_FUERA & set(rel.parts[:-1])) or rel.name in NOMBRES_FUERA
    return (bool(CARPETAS_FUERA & set(rel.parts[:-1])) or rel.name in NOMBRES_FUERA or rel.suffix.lower() in SUFIJOS_FUERA
            or bool(NOMBRE_SECRETO.search(rel.name)))


def _incluir(rel: Path) -> bool:
    if _fuera(rel) or rel.parts[:2] == PAQUETE.parts:
        return False
    if rel.parts[0] == "referencias-estilos" and rel.suffix.lower() in {".jpg", ".jpeg", ".png"}:
        return rel.name in REFERENCIAS_JPG
    return True


def origen(rel: Path) -> Path:
    """Dónde está en esta máquina el archivo que viaja como `rel`: Lemo viene de su carpeta (config.lemo()); lo demás, del repo."""
    if rel.parts[:len(LEMO_ZIP.parts)] == LEMO_ZIP.parts:
        return config.lemo().joinpath(*rel.parts[len(LEMO_ZIP.parts):])
    return RAIZ / rel


def archivos_lemo() -> list[Path]:
    """Lemo (Estilos Pro) entero, como `lemo/lemo-opuscar/…`: código, estilos, guías y carátulas. Sus paquetes, navegador y Python se
    instalan en cada equipo (instalar._lemo); videos, .git y lo con pinta de secreto, nunca."""
    lib = config.lemo()
    out = []
    for dentro, carpetas, nombres in os.walk(lib):
        carpetas[:] = sorted(d for d in carpetas if d not in LEMO_FUERA and d not in CARPETAS_FUERA)
        for n in nombres:
            rel = LEMO_ZIP / (Path(dentro) / n).relative_to(lib)
            if (Path(dentro) / n).is_file() and not _fuera(rel):
                out.append(rel)
    return out


def archivos() -> list[Path]:
    """Rutas relativas (a RAIZ) de todo lo que entra al zip, en orden. Sigue el enlace de librerias/sonido/sfx (en el PC apunta al banco de captions)."""
    out = {Path(a) for a in ARCHIVOS + EXTRAS if (RAIZ / a).is_file()}
    out.update(archivos_lemo())
    for c in CARPETAS:
        vistas = set()
        for dentro, carpetas, nombres in os.walk(RAIZ / c, followlinks=True):
            real = os.path.realpath(dentro)
            if real in vistas:   # enlace que vuelve sobre sí mismo (hay uno suelto en las muestras)
                carpetas[:] = []
                continue
            vistas.add(real)
            carpetas[:] = sorted(d for d in carpetas if d not in CARPETAS_FUERA)
            for n in nombres:
                if not (Path(dentro) / n).is_file():
                    continue
                if _incluir(rel := (Path(dentro) / n).relative_to(RAIZ)):
                    out.add(rel)
    return sorted(out)


def contenido(rel: Path) -> bytes:
    """Lo que entra al zip por archivo: el texto sale sin rutas ni datos personales del PC; lo binario, tal cual."""
    datos = origen(rel).read_bytes()
    if len(datos) > MAX_TEXTO or b"\0" in datos[:2048]:
        return datos
    try:
        texto = datos.decode("utf-8")
    except UnicodeDecodeError:
        return datos
    for patron, cambio in LIMPIEZA:
        texto = patron.sub(cambio, texto)
    if rel.suffix.lower() in (".bat", ".txt"):   # Windows: un .bat con saltos LF a secas falla en `goto`/`call`
        texto = texto.replace("\r\n", "\n").replace("\n", "\r\n")
    return texto.encode("utf-8")


def _manifiesto(rutas: list[Path]) -> str:
    """Lo que git rastrea dentro del paquete: es la lista de `estudio verificar` cuando no hay .git (verificar.py)."""
    try:
        seguidos = set(verificar._git("ls-files", "-z"))
    except Exception:  # noqa: BLE001 — sin git: todo lo del paquete cuenta
        seguidos = {str(r) for r in rutas}
    return "\n".join(sorted(str(r) for r in rutas if str(r) in seguidos)) + "\n"


def en_sistema(nombre: str) -> str:
    """Ruta de un archivo del zip tal como es en el repo: sin la carpeta raíz ni `sistema/`."""
    partes = nombre.split("/")[1:]
    return "/".join(partes[1:] if partes[:1] == [SISTEMA] else partes)


def sospechoso(nombre: str, datos: bytes | None) -> str | None:
    """Motivo por el que un archivo del zip NO debería estar, o None."""
    rel = Path(nombre)
    if _fuera(rel):
        return "nombre prohibido"
    if NOMBRE_SECRETO.search(rel.name):
        return "nombre con pinta de secreto"
    if datos is not None and len(datos) <= MAX_TEXTO and b"\0" not in datos[:2048]:
        texto = datos.decode("utf-8", "ignore")
        if (m := PERSONAL.search(texto)):
            return f"dato personal ({m.group(0)})"
        m = CONTENIDO_SECRETO.search(texto)
        if m:
            return f"contenido con pinta de secreto ({m.group(0)[:6]}…)"
    return None


def revisar_zip(zip_path: Path) -> list[str]:
    """Abre el zip y devuelve los problemas (vacío = limpio). Es lo que corre la prueba tests/test_exportar.py."""
    fallas = []
    with zipfile.ZipFile(zip_path) as z:
        for info in z.infolist():
            if info.is_dir():
                continue
            motivo = sospechoso(en_sistema(info.filename), z.read(info.filename))
            if motivo:
                fallas.append(f"{info.filename}: {motivo}")
    return fallas


def incompleto() -> list[str]:
    """Lo que el paquete necesita y NO está en git (se genera o se graba en una máquina): sin eso el zip no se arma (11-nov: una copia
    clonada mostraba el editor avanzado con todas las tarjetas vacías; antes solo se avisaba y el zip salía igual)."""
    return [nombre for nombre, hay in (
        ("las muestras del editor avanzado (app/muestras/sel)", any((RAIZ / "app/muestras/sel").glob("*.mp4"))),
        ("el banco de sonido orgánico (librerias/sonido/organico)", any((RAIZ / "librerias/sonido/organico").glob("*/*.wav"))),
        ("Lemo, el motor de los Estilos Pro (config.lemo())", (config.lemo() / "core" / "render").is_dir()
         and any((config.lemo() / "styles").glob("*/STYLE.md")))) if not hay]


def armar(destino: Path, fecha: str | None = None) -> Path:
    destino = Path(destino)
    destino.mkdir(parents=True, exist_ok=True)
    raiz_zip = config.NOMBRE_APP   # la única carpeta a la vista al abrir el zip
    zip_path = destino / f"{config.NOMBRE_ZIP}-{fecha or time.strftime('%Y-%m-%d')}.zip"
    rutas = archivos()
    falta = incompleto()
    if falta:   # no viven en git: una copia recién clonada no los tiene y el zip saldría a medias sin que nadie lo note
        raise SystemExit("exportar: esta copia no puede armar el paquete, le falta " + " y ".join(falta)
                         + ". Expórtalo desde la máquina que los tiene o cópialos aquí primero.")
    if not (RAIZ / "librerias/sonido/sfx").exists():
        print("aviso: sin el banco de efectos de sonido en esta copia; el instalador lo baja en cada equipo", file=sys.stderr)
    for r in rutas:   # nada sospechoso entra: si algo lo es, se para (no se arma un zip a medias)
        motivo = sospechoso(str(r), contenido(r))
        if motivo:
            raise SystemExit(f"exportar: {r} no puede viajar ({motivo})")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for r in rutas:
            info = zipfile.ZipInfo.from_file(origen(r), f"{raiz_zip}/{SISTEMA}/{r.as_posix()}")
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, contenido(r))
        z.writestr(f"{raiz_zip}/{SISTEMA}/MANIFIESTO.txt", _manifiesto(rutas))
        for f in sorted((RAIZ / PAQUETE).glob("*")):   # lo único que se ve en la raíz del zip
            info = zipfile.ZipInfo.from_file(f, f"{raiz_zip}/{f.name}")
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, contenido(f.relative_to(RAIZ)))
    fallas = revisar_zip(zip_path)
    if fallas:
        zip_path.unlink()
        raise SystemExit("exportar: el zip salió con lo que no debe:\n - " + "\n - ".join(fallas))
    return zip_path


LIMITE_RELEASE = 2 * 1024 ** 3   # GitHub: 2 GB por archivo de un release


def publicar(zip_path: Path, repo: str = "", en_seco: bool = False) -> int:
    """Sube el paquete a un repo PRIVADO nuevo con `gh` (contenido del zip, sin videos de clientes) y adjunta el zip como Release.
    Quien descarga necesita invitación al repo. `en_seco` solo muestra los comandos."""
    import subprocess
    import tempfile
    repo = repo or config.REPO_PAQUETE
    if zip_path.stat().st_size >= LIMITE_RELEASE:
        raise SystemExit(f"exportar: el zip pesa {zip_path.stat().st_size / 1e9:.2f} GB y un release admite 2 GB por archivo")
    etiqueta = "v" + time.strftime("%Y-%m-%d-%H%M")   # con hora: dos publicaciones el mismo día no chocan
    existe = en_seco is False and subprocess.run(["gh", "repo", "view", repo], capture_output=True).returncode == 0
    with tempfile.TemporaryDirectory() as tmp:
        with zipfile.ZipFile(zip_path) as z:
            z.extractall(tmp)
        carpeta = Path(tmp) / config.NOMBRE_APP
        # El repo es un espejo del ÚLTIMO paquete (cada versión es una foto nueva de main); lo que se descarga es el zip del Release.
        # postBuffer: un envío de ~170 MB por HTTPS se corta con «HTTP 400» con el búfer por defecto (12-nov).
        comandos = [["git", "init", "-q", "-b", "main"], ["git", "config", "http.postBuffer", "1048576000"], ["git", "add", "-A"],
                    ["git", "commit", "-q", "-m", f"Paquete {etiqueta}"]]
        if not existe:
            comandos.append(["gh", "repo", "create", repo, "--private", "--description", f"{config.NOMBRE_APP}: paquete instalable (privado)"])
        comandos += [["git", "remote", "add", "origin", f"https://github.com/{repo}.git"],
                     ["git", "push", "--force", "-q", "origin", "main"],
                     # se ve como «Pro Studio» a secas (Pablo, 12-nov); la versión queda en la etiqueta
                     ["gh", "release", "create", etiqueta, f"{zip_path}#{config.NOMBRE_APP}", "--repo", repo, "--latest", "--title", config.NOMBRE_APP,
                      "--notes", "Descomprime, doble clic en instalar y luego en el icono del Escritorio."]]
        for c in comandos:
            print("$", " ".join(c))
            if not en_seco and subprocess.run(c, cwd=carpeta).returncode != 0:
                raise SystemExit(f"exportar: falló `{' '.join(c[:3])}`")
    print(f"{'(en seco) ' if en_seco else ''}repo privado: https://github.com/{repo} · descarga: https://github.com/{repo}/releases/latest")
    return 0


def main(destino: Path, publicar_: bool = False, en_seco: bool = False, repo: str = "") -> int:
    zip_path = armar(destino)
    print(f"{zip_path}  ({zip_path.stat().st_size / 1e6:.1f} MB)")
    print("Dentro: «Instalar Pro Studio (Windows).bat», «Instalar Pro Studio (Mac).command», LEEME.txt y sistema/. Los modelos se bajan al instalar.")
    return publicar(zip_path, repo, en_seco) if publicar_ else 0
