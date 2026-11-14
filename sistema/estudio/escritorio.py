"""Acceso directo con icono en el Escritorio (lo crea `estudio instalar`). Doble clic = arranca el servidor si no corre y abre el navegador
en el puerto 8792, sin terminal. Windows: .lnk · Mac: .app · Linux/WSL: .desktop (y en WSL además el .lnk del Escritorio de Windows).
El icono se dibuja al instalar (Pillow), no viaja como binario."""
import os
import platform
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from . import config, entorno, fuentes

ICONOS = config.TPS / "icono"


ICONO_TEXTO = "ProStudio"   # lo que dice el icono (Pablo, 12-nov: «muy minimalista, negro y blanco»; eligió la opción 4 de 6)
ICONO_NEGRO = False         # fondo blanco con letra negra; True = al revés


def dibujar_icono(lado: int = 512, texto: str | None = None, negro: bool | None = None) -> Image.Image:
    """Icono minimalista en blanco y negro: un cuadro redondeado liso y la palabra, sin adornos. Con la proporción de los iconos de
    macOS (el cuadro ocupa el 80 % del lienzo, con aire alrededor) para que no se vea más grande que los demás en el Dock."""
    texto = ICONO_TEXTO if texto is None else texto
    negro = ICONO_NEGRO if negro is None else negro
    fondo, tinta = ((12, 12, 13, 255), (255, 255, 255, 255)) if negro else ((255, 255, 255, 255), (12, 12, 13, 255))
    k = 4   # se dibuja 4 veces más grande y se reduce: bordes y letra lisos
    L = lado * k
    im = Image.new("RGBA", (L, L), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    m = round(L * .1)
    d.rounded_rectangle((m, m, L - m, L - m), radius=round((L - 2 * m) * .225), fill=fondo,
                        outline=None if negro else (0, 0, 0, 40), width=0 if negro else max(1, L // 400))
    ruta = next((f for f in sorted(config.FUENTES.glob("InterTight[[]wght[]].ttf"))), None) or next(iter(sorted(config.FUENTES.rglob("Inter*.ttf"))), None)
    ancho_max, tam = (L - 2 * m) * .74, round(L * .46)
    while True:
        fuente = fuentes.abrir(ruta, tam) if ruta else ImageFont.load_default(tam)
        if ruta:
            try:
                fuente.set_variation_by_axes([700])
            except (OSError, AttributeError):
                pass
        x0, y0, x1, y1 = d.textbbox((0, 0), texto, font=fuente, anchor="ls")
        if x1 - x0 <= ancho_max or tam <= 20:
            break
        tam = round(tam * .94)
    d.text((L / 2 - (x0 + x1) / 2, L / 2 - (y0 + y1) / 2), texto, font=fuente, fill=tinta, anchor="ls")
    return im.resize((lado, lado), Image.LANCZOS)


def icono(formato: str) -> Path:
    ICONOS.mkdir(parents=True, exist_ok=True)
    base = dibujar_icono()
    if formato == "ico":
        ruta = ICONOS / "app.ico"
        base.save(ruta, sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
    else:
        ruta = ICONOS / "app.png"
        base.save(ruta)
    return ruta


def _escritorio() -> Path | None:
    for c in (Path.home() / "Desktop", Path.home() / "Escritorio"):
        if c.is_dir():
            return c
    return None


def _linux(avance) -> None:
    dest = _escritorio()
    if not dest:
        return
    png = icono("png")
    contenido = (f"[Desktop Entry]\nType=Application\nName={config.NOMBRE_APP}\nComment=Editor de reels\nIcon={png}\nTerminal=false\n"
                 f"Path={config.RAIZ}\nExec=bash \"{config.RAIZ / 'abrir.sh'}\"\nCategories=AudioVideo;\n")
    for carpeta in (dest, Path.home() / ".local" / "share" / "applications"):
        carpeta.mkdir(parents=True, exist_ok=True)
        f = carpeta / f"{config.NOMBRE_APP}.desktop"
        f.write_text(contenido, encoding="utf-8")
        f.chmod(0o755)
    avance(f"· acceso directo en {dest}")


def _mac(avance, dest: Path | None = None) -> None:
    """`Pro Studio.app`: su proceso ES la app (servidor + ventana propia, `estudio/ventana.py`), así el Dock muestra su nombre y su
    icono mientras está abierta y se puede dejar fija ahí. El lanzador hace `exec` del Python del entorno: mismo proceso que lanzó
    el Dock, que por eso lo reconoce como esta app y no como «Python»."""
    dest = dest or _escritorio()
    if not dest:
        return
    app = dest / f"{config.NOMBRE_APP}.app"
    shutil.rmtree(app, ignore_errors=True)
    (app / "Contents" / "MacOS").mkdir(parents=True)
    (app / "Contents" / "Resources").mkdir()
    lanzador = app / "Contents" / "MacOS" / "abrir"
    lanzador.write_text(f'#!/bin/bash\ncd "{config.RAIZ}" || exit 1\nexport PATH="$HOME/.local/bin:/usr/local/bin:/opt/homebrew/bin:$PATH"\n'
                        'mkdir -p .tps\n[ -x .venv/bin/python ] || uv sync --quiet >> .tps/app.log 2>&1\n'
                        'exec .venv/bin/python -c "from estudio.cli import main; main()" servir >> .tps/app.log 2>&1\n')
    lanzador.chmod(0o755)
    (app / "Contents" / "Info.plist").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<plist version="1.0"><dict><key>CFBundleName</key><string>' + config.NOMBRE_APP +
        '</string><key>CFBundleExecutable</key><string>abrir</string><key>CFBundleIconFile</key><string>app</string>'
        '<key>CFBundleIdentifier</key><string>studio.productlab.prostudio</string><key>CFBundlePackageType</key><string>APPL</string>'
        '<key>CFBundleDisplayName</key><string>' + config.NOMBRE_APP + '</string><key>NSHighResolutionCapable</key><true/></dict></plist>\n')
    if shutil.which("iconutil"):   # .icns desde un iconset de Pillow
        iconset = ICONOS / "app.iconset"
        iconset.mkdir(parents=True, exist_ok=True)
        base = dibujar_icono(1024)
        for n in (16, 32, 64, 128, 256, 512):
            base.resize((n, n), Image.LANCZOS).save(iconset / f"icon_{n}x{n}.png")
            base.resize((n * 2, n * 2), Image.LANCZOS).save(iconset / f"icon_{n}x{n}@2x.png")
        subprocess.run(["iconutil", "-c", "icns", str(iconset), "-o", str(app / "Contents" / "Resources" / "app.icns")], check=False)
    avance(f"· {app}")


def _ps(texto: str) -> str:
    """Texto dentro de comillas simples de PowerShell: el apóstrofo se duplica (rutas como C:\\Users\\O'Brien)."""
    return str(texto).replace("'", "''")


def guion_lnk(destino: str, argumentos: str, icono_win: str, trabajo: str) -> str:
    """El script de PowerShell que crea el .lnk. La carpeta del Escritorio la resuelve el MISMO script (nada pasa por stdout, que en
    Windows llega en la página de códigos del sistema y rompe rutas con acentos o la ñ) y todo texto va con el apóstrofo escapado."""
    return ("$d=[Environment]::GetFolderPath('Desktop');if(-not $d){{exit 3}};"
            "$s=(New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path $d '{nombre}.lnk'));$s.TargetPath='{t}';$s.Arguments='{a}';"
            "$s.IconLocation='{i}';$s.WorkingDirectory='{w}';$s.WindowStyle=7;$s.Description='{nombre}';$s.Save()").format(
        nombre=_ps(config.NOMBRE_APP), t=_ps(destino), a=_ps(argumentos), i=_ps(icono_win), w=_ps(trabajo))


def _lnk(destino: str, argumentos: str, icono_win: str, trabajo: str, avance) -> None:
    ps = guion_lnk(destino, argumentos, icono_win, trabajo)
    r = entorno.correr_windows("powershell.exe", ["-NoProfile", "-Command", ps]) if platform.system() != "Windows" else \
        subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True)
    if r is None or r.returncode != 0:
        avance("  no pude crear el acceso directo de Windows (se abre con abrir.bat)")
    else:
        avance(f"· acceso directo «{config.NOMBRE_APP}» en el Escritorio de Windows")


def _windows(avance) -> None:
    _lnk("wscript.exe", f'"{config.RAIZ / "herramientas" / "abrir.vbs"}"', str(icono("ico")), str(config.RAIZ), avance)


def _wsl(avance) -> None:
    """Dentro de WSL: .desktop de Linux + el .lnk del Escritorio de Windows, que arranca la app dentro de esta distro sin terminal."""
    _linux(avance)
    exe = entorno.windows_exe("powershell.exe")
    wslpath = shutil.which("wslpath")
    if not exe or not wslpath:
        return
    ico = subprocess.run([wslpath, "-w", str(icono("ico"))], capture_output=True, text=True).stdout.strip()
    distro = os.environ.get("WSL_DISTRO_NAME", "")
    args = (f"-d {distro} " if distro else "") + f"--cd \"{config.RAIZ}\" -- bash ./abrir.sh"
    _lnk("wsl.exe", args, ico, "", avance)


def crear(avance=print) -> None:
    """Crea el acceso directo de esta máquina. Nunca falla la instalación: un error se avisa y ya."""
    try:
        if os.name == "nt":
            _windows(avance)
        elif platform.system() == "Darwin":
            _mac(avance)
        elif entorno.en_wsl():
            _wsl(avance)
        else:
            _linux(avance)
    except Exception as e:  # noqa: BLE001 — el acceso directo es comodidad; la app abre igual con abrir.*
        avance(f"  acceso directo no creado ({type(e).__name__}: {e})")
