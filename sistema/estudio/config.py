"""Rutas y constantes del motor. Todo lo instalado vive dentro de la carpeta de la app (.tps/)."""
import json
import os
import shutil
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
TPS = RAIZ / ".tps"
MODELOS = TPS / "modelos"
CACHE = TPS / "cache"
PROYECTOS = RAIZ / "proyectos"
FUENTES = RAIZ / "librerias" / "fuentes"

WHISPER_MODELO = "large-v3"
WHISPER_DIR = MODELOS / "whisper-large-v3"
RVM_ONNX = MODELOS / "rvm_mobilenetv3_fp32.onnx"
RVM_URL = "https://github.com/PeterL1n/RobustVideoMatting/releases/download/v1.0.0/rvm_mobilenetv3_fp32.onnx"
CARAS_ONNX = MODELOS / "face_detection_yunet_2023mar.onnx"   # detector de caras (YuNet, OpenCV Zoo): ubica a la persona sin recortarla
CARAS_URL = "https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"
CARAS_SHA256 = "8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4"

NOMBRE_APP = "Pro Studio"   # lo que se ve: ventana, icono, acceso directo
NOMBRE_ZIP = "ProStudio"       # prefijo del paquete: <NOMBRE_ZIP>-AAAA-MM-DD.zip
REPO_PAQUETE = "academiaprestiggio/pro-studio"   # repo PRIVADO donde `estudio exportar --publicar` sube el paquete

W, H, FPS = 1080, 1920, 30
TEXTO_MARGEN_LATERAL_PX = 48   # el texto visible nunca queda a menos de esto del borde izquierdo/derecho (Pop: «aprender a editar» pegado al borde a 25 px)


def piso_texto_px() -> int:
    """El piso de legibilidad de TODA línea de texto (perfil/reglas.json › global › texto_linea_min_px): único lugar del número; lo leen la compuerta,
    los estilos Pro, las franjas y las cajas HUD."""
    try:
        return int(json.loads((RAIZ / "perfil" / "reglas.json").read_text())["global"]["texto_linea_min_px"])
    except (OSError, KeyError, ValueError):
        return 0


TOPE_IMAGENES = 4        # tope de imágenes por defecto (Pablo: menos imágenes); cada preset puede declarar el suyo (3D: 8, excepción escrita)
TOPE_IMAGENES_PASO = 2   # de Sencilla a Media a Pro la app sube/baja el tope del estilo en esto (la app lo lee de /api/librerias)
TOPE_IMAGENES_MAX = 10   # techo absoluto de lo que se puede pedir (Pro de un estilo con tope 8)
ZONA_SEGURA = (60, 230, 1020, 1500)   # zona segura de Instagram (x0, y0, x1, y1): único lugar del valor
SUAVE_PX = 100   # lo suave (sombra del cristal, velo de bordes difusos) puede asomar así de la zona segura; lo que se lee (caja y letras), nada
SFX_VOLUMEN = .28   # volumen de los efectos de sonido por defecto (el preset puede declarar `sfx`); único lugar del valor


def pesado() -> Path | None:
    """La cola de trabajo pesado, de uno en uno y en orden de llegada: la propia del paquete (`herramientas/pesado.sh`). None en Windows
    nativo: ahí todo corre directo. ESTUDIO_PESADO la apunta a otra (p. ej. una cola compartida entre equipos); ESTUDIO_PESADO=0 la apaga."""
    propia = os.environ.get("ESTUDIO_PESADO")
    if propia == "0" or os.name == "nt":
        return None
    candidatas = [Path(propia)] if propia else [RAIZ / "herramientas" / "pesado.sh"]
    return next((c for c in candidatas if c.is_file()), None)


def laboratorio() -> Path | None:
    """La carpeta que trae a Lemo (`lemo-opuscar/styles`), o None si esta máquina no la tiene. ÚNICO lugar que la busca:
    ESTUDIO_LABORATORIO, la hermana del repo, la del escritorio de la Mac o la copia de referencia del Estudio beta (11-nov, Pablo:
    «no veo las miniaturas de Lemo»: en su Mac los estilos estaban en `ESTUDIO BETA/referencias` y la app solo miraba `laboratorio-estilos`)."""
    casa = Path.home() / "Desktop" / "CLAUDE CODE"
    candidatas = [os.environ.get("ESTUDIO_LABORATORIO"), LEMO_PAQUETE.parent, RAIZ.parent / "laboratorio-estilos", casa / "laboratorio-estilos",
                  casa / "ESTUDIO BETA" / "referencias"]
    return next((Path(c) for c in candidatas if c and (Path(c) / "lemo-opuscar" / "styles").is_dir()), None)


LEMO_PAQUETE = RAIZ / "lemo" / "lemo-opuscar"   # Lemo dentro de la app instalada (12-nov, Pablo: el zip lleva «todo es todo»)


def lemo() -> Path:
    """La carpeta del MOTOR de Lemo (Estilos Pro): ESTUDIO_LEMO; la que viaja dentro del paquete (`lemo/lemo-opuscar`); o, en la máquina
    que desarrolla, `laboratorio-estilos/lemo-opuscar` junto al repo. La copia de referencia del Estudio beta sirve para VER el catálogo
    (`laboratorio`), no para editar: no trae el motor instalado."""
    if os.environ.get("ESTUDIO_LEMO"):
        return Path(os.environ["ESTUDIO_LEMO"])
    return LEMO_PAQUETE if LEMO_PAQUETE.is_dir() else RAIZ.parent / "laboratorio-estilos" / "lemo-opuscar"


def navegador_lemo() -> Path:
    """El navegador sin ventana propio de Lemo (`navegador-lemo/` junto a su motor): el instalador lo baja de Chrome for Testing cuando
    Playwright no da uno para este sistema (macOS 13: «does not support chromium-headless-shell on mac13», 12-nov)."""
    return lemo().parent / "navegador-lemo" / ("chrome-headless-shell.exe" if os.name == "nt" else "chrome-headless-shell")


NODE = TPS / "node"      # Node propio (lo baja el instalador si el equipo no tiene Node 20+): lo necesita Lemo
BIN = TPS / "bin"        # ffmpeg/ffprobe del motor a la vista de Lemo y de Claude (Lemo los llama por su nombre)


def git_usr_bin(windows: bool | None = None) -> Path | None:
    """`usr\\bin` de Git for Windows (trae `sh`, que necesitan los `.sh` de Lemo), o None si no está en sus rutas típicas o no es Windows."""
    if not ((os.name == "nt") if windows is None else windows):
        return None
    bases = [os.environ.get(v) for v in ("ProgramFiles", "ProgramW6432", "ProgramFiles(x86)")]
    if os.environ.get("LOCALAPPDATA"):
        bases.append(str(Path(os.environ["LOCALAPPDATA"]) / "Programs"))
    for b in bases:
        if b and (Path(b) / "Git" / "usr" / "bin" / "sh.exe").is_file():
            return Path(b) / "Git" / "usr" / "bin"
    return None


def herramientas_en_path(env: dict | None = None, windows: bool | None = None) -> dict:
    """Pone el Node propio y el ffmpeg del motor delante en el PATH (de este proceso o de `env`): así Lemo, y el Claude que lo dirige,
    los encuentran por su nombre en un equipo que no tiene nada instalado. En Windows suma al final el `usr\\bin` de Git (el `sh` de Lemo;
    al final para no tapar `find` ni `sort` de Windows). Lo que no existe no se agrega."""
    env = os.environ if env is None else env
    nt = (os.name == "nt") if windows is None else windows
    propias = [str(d) for d in (NODE if nt else NODE / "bin", BIN) if d.is_dir()]
    actual = env.get("PATH", "")
    en_path = actual.split(os.pathsep)
    faltan = [d for d in propias if d not in en_path]
    if faltan:
        env["PATH"] = os.pathsep.join(faltan + ([actual] if actual else []))
    git = git_usr_bin(nt)
    if git and str(git) not in env.get("PATH", "").split(os.pathsep):
        env["PATH"] = os.pathsep.join([p for p in (env.get("PATH", ""), str(git)) if p])
    return env


herramientas_en_path()


REVISION = Path(os.environ.get("ESTUDIO_REVISION") or RAIZ / "revision")   # finales de cada estilo para la pantalla /revision


def claude_cmd() -> list[str] | None:
    """Cómo invocar el binario oficial `claude`. ESTUDIO_CLAUDE_BIN lo reemplaza (un .py se corre con este Python)."""
    propio = os.environ.get("ESTUDIO_CLAUDE_BIN")
    if propio:
        if not Path(propio).exists():
            return None
        return [sys.executable, propio] if propio.endswith(".py") else [propio]
    encontrado = shutil.which("claude")
    if encontrado:
        return [encontrado]
    for nativo in (Path.home() / ".local" / "bin" / "claude", Path.home() / ".local" / "bin" / "claude.exe"):   # donde lo deja su instalador oficial
        if nativo.is_file():
            return [str(nativo)]
    for vscode in sorted(Path.home().glob(".vscode/extensions/anthropic.claude-code-*/resources/native-binary/claude*")):
        return [str(vscode)]
    return None


def ffmpeg() -> tuple[str, str]:
    """(ffmpeg, ffprobe) de static-ffmpeg; los baja la primera vez."""
    from static_ffmpeg import run
    return run.get_or_fetch_platform_executables_else_raise()
