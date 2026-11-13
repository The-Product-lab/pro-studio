"""`estudio doctor --arreglar` / `estudio instalar`: la ÚNICA lógica de instalación (los instaladores de cada sistema solo
consiguen `uv` y llaman a esto). Idempotente: lo que ya está no se vuelve a hacer; un paso que falla no frena los demás
(el doctor del final dice qué quedó pendiente y cómo arreglarlo). Nada de API: Claude Code entra con la suscripción."""
import os
import shutil
import subprocess
import sys
from pathlib import Path

from . import config, recursos

CLAUDE_SH = "curl -fsSL https://claude.ai/install.sh | bash"
CLAUDE_PS1 = "irm https://claude.ai/install.ps1 | iex"


def _claude_code(avance) -> None:
    if config.claude_cmd():
        return
    avance("· instalando Claude Code (instalador oficial)…")
    try:
        if os.name == "nt":
            subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "ByPass", "-Command", CLAUDE_PS1], check=True)
        else:
            subprocess.run(["bash", "-c", CLAUDE_SH], check=True)
    except (OSError, subprocess.SubprocessError) as e:
        avance(f"  no pude instalar Claude Code ({type(e).__name__}); instálalo desde https://claude.com/claude-code")


def _sesion(avance) -> None:
    """Si Claude Code está pero sin sesión, abre el inicio de sesión (necesita a la persona: solo con terminal interactiva)."""
    cmd = config.claude_cmd()
    if not cmd or not sys.stdin.isatty():
        return
    estado = subprocess.run(cmd + ["auth", "status"], capture_output=True, text=True)
    if estado.returncode == 0:
        return
    avance("· inicia sesión en Claude con tu suscripción (se abre el navegador)…")
    subprocess.run(cmd + ["auth", "login"])


NODE_VERSION = "22.12.0"   # LTS oficial; Lemo pide Node 20+


def _node_ok(node: str | None) -> bool:
    if not node:
        return False
    try:
        v = subprocess.run([node, "-p", "process.versions.node.split('.')[0]"], capture_output=True, text=True, timeout=30).stdout
        return int(v.strip() or 0) >= 20
    except (OSError, ValueError, subprocess.SubprocessError):
        return False


def _node(avance) -> str | None:
    """El Node 20+ del equipo o, si no hay, el oficial de nodejs.org dentro de la app (.tps/node), sin permisos de administrador."""
    import platform
    import tarfile
    import urllib.request
    import zipfile
    config.herramientas_en_path()
    if _node_ok(shutil.which("node")):
        return shutil.which("node")
    sistema = {"darwin": "darwin", "linux": "linux", "win32": "win"}.get(sys.platform)
    arq = {"arm64": "arm64", "aarch64": "arm64", "x86_64": "x64", "amd64": "x64"}.get(platform.machine().lower())
    if not sistema or not arq:
        avance(f"  Node: sistema no soportado ({sys.platform}/{platform.machine()})")
        return None
    nombre = f"node-v{NODE_VERSION}-{sistema}-{arq}"
    ext = "zip" if sistema == "win" else "tar.gz"
    avance("· bajando Node (para los Estilos Pro)…")
    config.TPS.mkdir(parents=True, exist_ok=True)
    tmp = config.TPS / f"{nombre}.{ext}.part"
    with urllib.request.urlopen(f"https://nodejs.org/dist/v{NODE_VERSION}/{nombre}.{ext}", timeout=300) as r, open(tmp, "wb") as f:
        shutil.copyfileobj(r, f)
    shutil.rmtree(config.TPS / nombre, ignore_errors=True)
    if ext == "zip":
        with zipfile.ZipFile(tmp) as z:
            z.extractall(config.TPS)
    else:
        with tarfile.open(tmp) as t:
            t.extractall(config.TPS)   # trae enlaces relativos (npm → ../lib/…) y permisos de ejecución
    tmp.unlink()
    shutil.rmtree(config.NODE, ignore_errors=True)
    (config.TPS / nombre).rename(config.NODE)
    config.herramientas_en_path()
    return shutil.which("node")


def _ffmpeg_a_la_vista() -> None:
    """Lemo llama `ffmpeg`/`ffprobe` por su nombre: se dejan los del motor en .tps/bin (enlace; copia en Windows)."""
    config.BIN.mkdir(parents=True, exist_ok=True)
    for origen in recursos.ffmpeg():
        destino = config.BIN / Path(origen).name
        if destino.exists() or destino.is_symlink():
            continue
        if os.name == "nt":
            shutil.copy2(origen, destino)
        else:
            destino.symlink_to(origen)
    config.herramientas_en_path()


NAVEGADOR_OK = ".navegador-ok"   # marca en la carpeta de Lemo: su navegador quedó (el de Playwright o el propio de Chrome for Testing)


def _navegador_propio(lib: Path, avance) -> None:
    """Chrome for Testing (headless shell) oficial de Google, en la versión que pide el Playwright de Lemo, en `navegador-lemo/`.
    Se usa cuando Playwright no da navegador para este sistema; Lemo lo toma por PLAYWRIGHT_CHROME (textos_lemo)."""
    import json
    import platform
    import urllib.request
    import zipfile
    browsers = json.loads((lib / "node_modules" / "playwright-core" / "browsers.json").read_text())["browsers"]
    version = next(b["browserVersion"] for b in browsers if b["name"] == "chromium-headless-shell")
    arm = platform.machine().lower() in ("arm64", "aarch64")
    plat = {"darwin": "mac-arm64" if arm else "mac-x64", "win32": "win64", "linux": "linux64"}[sys.platform]
    avance(f"· bajando el navegador de Lemo (Chrome for Testing {version})…")
    destino = config.navegador_lemo().parent
    tmp = destino.with_name("navegador-lemo.zip.part")
    url = f"https://storage.googleapis.com/chrome-for-testing-public/{version}/{plat}/chrome-headless-shell-{plat}.zip"
    with urllib.request.urlopen(url, timeout=600) as r, open(tmp, "wb") as f:
        shutil.copyfileobj(r, f)
    shutil.rmtree(destino, ignore_errors=True)
    with zipfile.ZipFile(tmp) as z:
        for info in z.infolist():   # zipfile no guarda permisos: se reponen (el ejecutable y sus ayudantes)
            dentro = Path(*Path(info.filename).parts[1:])   # sin la carpeta chrome-headless-shell-<plat>/
            if not dentro.parts:
                continue
            final = destino / dentro
            if info.is_dir():
                final.mkdir(parents=True, exist_ok=True)
                continue
            final.parent.mkdir(parents=True, exist_ok=True)
            final.write_bytes(z.read(info))
            modo = info.external_attr >> 16
            if modo:
                final.chmod(modo & 0o777)
    tmp.unlink()
    if sys.platform == "darwin":
        subprocess.run(["xattr", "-dr", "com.apple.quarantine", str(destino)], capture_output=True)
    if not config.navegador_lemo().is_file():
        raise RuntimeError(f"el navegador de Lemo no quedó en {destino}")
    os.environ["PLAYWRIGHT_CHROME"] = str(config.navegador_lemo())


def lemo_listo() -> bool:
    """Lemo puede renderizar: su carpeta, sus paquetes de Node, su navegador, su Python propio y un Node 20+ a la vista."""
    lib = config.lemo()
    py = lib / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    navegador = (lib / NAVEGADOR_OK).exists() or config.navegador_lemo().is_file()
    return ((lib / "core").is_dir() and (lib / "node_modules" / "playwright-core").is_dir() and navegador and py.exists()
            and _node_ok(shutil.which("node")) and (os.name != "nt" or bool(shutil.which("sh"))))   # sus .sh piden `sh`: en Windows lo trae Git


GIT_WINDOWS_URL = "https://git-scm.com/download/win"
GIT_WINDOWS_WINGET = ["winget", "install", "--id", "Git.Git", "-e", "--silent",
                      "--accept-package-agreements", "--accept-source-agreements"]


def _git_windows(avance) -> bool:
    """Windows no trae `sh` y Lemo (mux.sh, build.sh) y el Agente Editor (git) lo necesitan: Git for Windows lo trae todo. Si no está,
    se instala con winget; si winget no puede, se dice claro dónde bajarlo. True si al terminar hay `sh`. Fuera de Windows no hace nada."""
    if os.name != "nt":
        return True
    config.herramientas_en_path()
    if shutil.which("sh"):
        return True
    avance("· instalando Git for Windows (lo necesitan los Estilos Pro y el Agente Editor)…")
    try:
        subprocess.run(GIT_WINDOWS_WINGET, check=True)
    except (OSError, subprocess.SubprocessError) as e:
        avance(f"  no pude instalar Git con winget ({type(e).__name__}); instálalo tú desde {GIT_WINDOWS_URL} y repite el instalador")
        return False
    config.herramientas_en_path()
    if not (shutil.which("sh") or config.git_usr_bin()):
        avance(f"  Git quedó instalado pero no lo encuentro; cierra y abre el instalador otra vez (o bájalo de {GIT_WINDOWS_URL})")
        return False
    return True


def _lemo(avance) -> None:
    """Estilos Pro: Lemo viaja dentro del paquete; aquí se le instala lo que su propio `setup.sh deps` instala (Node, sus paquetes, el
    navegador sin ventana y su Python), en Python para que corra igual en Windows sin bash."""
    lib = config.lemo()
    if not (lib / "core").is_dir():
        return
    try:
        _ffmpeg_a_la_vista()
        node = _node(avance)
        if not node:
            avance("  Estilos Pro: sin Node; repite el instalador con internet")
            return
        env = config.herramientas_en_path(dict(os.environ))
        npm = shutil.which("npm", path=env["PATH"])
        avance("· preparando los Estilos Pro (Lemo)…")
        if not (lib / "node_modules" / "playwright-core").is_dir():
            subprocess.run([npm, "install", "--no-audit", "--no-fund", "--loglevel=error"], cwd=lib, env=env, check=True)
        if not config.navegador_lemo().is_file():
            pw = subprocess.run([node, "node_modules/playwright-core/cli.js", "install", "chromium-headless-shell"], cwd=lib, env=env,
                                capture_output=True, text=True)
            if pw.returncode != 0:   # Playwright no da navegador para este sistema (macOS 13): el oficial de Google, directo
                _navegador_propio(lib, avance)
        (lib / NAVEGADOR_OK).write_text("ok\n")
        uv = os.environ.get("UV") or shutil.which("uv") or shutil.which("uv", path=str(Path.home() / ".local" / "bin"))
        py = lib / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        if not py.exists():
            subprocess.run([uv, "venv", "--quiet", "--python", "3.12", ".venv"], cwd=lib, env=env, check=True)
        subprocess.run([uv, "pip", "install", "--quiet", "--python", str(py), "-r", "requirements.txt"], cwd=lib, env=env, check=True)
        if os.name == "nt" and not (lib / ".venv" / "bin" / "python").exists():   # las herramientas de Lemo llaman .venv/bin/python
            (lib / ".venv" / "bin").mkdir(exist_ok=True)
            (lib / ".venv" / "bin" / "python").write_text(   # saltos LF a secas: con CRLF `sh` no encuentra el intérprete
                '#!/bin/sh\nPYTHONUTF8=1 PYTHONIOENCODING=utf-8 exec "$(dirname "$0")/../Scripts/python.exe" "$@"\n',
                encoding="utf-8", newline="\n")
    except Exception as e:  # noqa: BLE001 — sin red: el doctor lo dice y el instalador se puede repetir
        avance(f"  Estilos Pro incompletos ({type(e).__name__}: {e}); repite el instalador")


def git_usable() -> bool:
    """¿Hay un `git` que funciona sin sorpresas? En Mac, `/usr/bin/git` sin las herramientas de Xcode abre un diálogo de instalación:
    ahí solo cuenta si `xcode-select -p` dice que están."""
    git = shutil.which("git")
    if not git:
        return False
    if sys.platform == "darwin" and git == "/usr/bin/git":
        try:
            return subprocess.run(["xcode-select", "-p"], capture_output=True, timeout=30).returncode == 0
        except (OSError, subprocess.SubprocessError):
            return False
    return True


def _repositorio(avance) -> None:
    """El paquete no trae `.git` y el Agente Editor guarda y deshace sus cambios con git: se crea el repo de la app instalada con un
    commit inicial (lo que ignora .gitignore —proyectos, modelos, entorno— no entra). Sin git no se hace nada: el agente lo dirá."""
    if (config.RAIZ / ".git").exists() or not git_usable():
        return
    ident = ["-c", "user.name=Pro Studio", "-c", "user.email=prostudio@localhost"]
    try:
        for orden in (["init", "-q", "-b", "main"], ["add", "-A"], [*ident, "commit", "-q", "-m", "Pro Studio: versión instalada"]):
            subprocess.run(["git", "-C", str(config.RAIZ), *orden], check=True, capture_output=True)
    except (OSError, subprocess.SubprocessError) as e:
        shutil.rmtree(config.RAIZ / ".git", ignore_errors=True)   # un repo a medias engaña al agente: mejor ninguno
        avance(f"  no pude preparar el control de cambios del Agente Editor ({type(e).__name__})")


PRESETS = config.RAIZ / "librerias" / "estilos" / "presets.json"
PRESETS_PAQUETE = config.TPS / "presets-paquete.json"   # lo deja el instalador (.sh / .bat) al reinstalar sobre una app que ya tenía lo suyo


def _completar(usuario, paquete):
    """Lo del usuario manda; del paquete entra solo lo que al usuario le falta (a cualquier profundidad)."""
    if isinstance(usuario, dict) and isinstance(paquete, dict):
        return {**{k: _completar(usuario[k], v) if k in usuario else v for k, v in paquete.items()},
                **{k: v for k, v in usuario.items() if k not in paquete}}
    return usuario


def fusionar_presets(usuario: Path = PRESETS, paquete: Path = PRESETS_PAQUETE) -> list[str]:
    """Reinstalar no pisa los estilos del usuario: los instaladores conservan `librerias/estilos` y `perfil` y dejan el presets.json del
    paquete aparte; aquí entran sus estilos y claves nuevos y se conserva todo lo que el usuario ya tenía. Devuelve los estilos nuevos."""
    import json
    if not paquete.is_file():
        return []
    try:
        nuevo = json.loads(paquete.read_text(encoding="utf-8"))
        actual = json.loads(usuario.read_text(encoding="utf-8")) if usuario.is_file() else {}
    except (OSError, ValueError):
        return []   # archivo ilegible: no se toca nada y la semilla queda para el próximo intento
    fusion = _completar(actual, nuevo)
    if fusion != actual:
        parcial = usuario.with_name(usuario.name + ".part")
        parcial.write_text(json.dumps(fusion, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        parcial.replace(usuario)
    paquete.unlink()
    return [k for k in fusion if k not in actual]


def _presets(avance) -> None:
    try:
        nuevos = fusionar_presets()
        if nuevos:
            avance(f"· estilos nuevos del paquete: {', '.join(nuevos)}")
    except OSError as e:
        avance(f"  no pude fusionar los estilos del paquete ({type(e).__name__})")


def _hooks(avance) -> None:
    if (config.RAIZ / ".git").exists() and shutil.which("git"):
        subprocess.run(["git", "-C", str(config.RAIZ), "config", "core.hooksPath", ".githooks"])


def arreglar(avance=print) -> None:
    """Todo lo que el paquete necesita y no viene dentro: carpetas, Claude Code, ffmpeg, modelos, efectos de sonido, compuerta de git."""
    for d in (config.PROYECTOS, config.TPS, config.CACHE):
        d.mkdir(parents=True, exist_ok=True)
    _claude_code(avance)
    avance("· bajando ffmpeg y modelos (la primera vez tarda: ~3 GB)…")
    try:
        recursos.instalar()
    except Exception as e:  # noqa: BLE001 — sin red o sin disco: el doctor lo dice y se puede repetir
        avance(f"  recursos incompletos ({type(e).__name__}: {e}); repite `uv run estudio doctor --arreglar`")
    try:
        from . import sfx, sonido
        if not any(sonido.BANCO.glob("*.wav")):
            avance("· bajando el banco de efectos de sonido (CC0)…")
            sfx.traer()
    except Exception as e:  # noqa: BLE001 — opcional: el banco orgánico ya viaja en el paquete
        avance(f"  efectos de sonido: {type(e).__name__}")
    _presets(avance)
    _git_windows(avance)   # antes de Lemo (su `sh`) y del repositorio (el Agente Editor)
    _lemo(avance)
    from . import escritorio
    escritorio.crear(avance)
    _repositorio(avance)
    _hooks(avance)
    _sesion(avance)
