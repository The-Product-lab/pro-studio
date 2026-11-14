"""¿Claude Code está en este equipo y tiene la sesión iniciada? La app lo pregunta sola y lo dice ANTES de que la persona suba un video:
en un equipo recién instalado es lo único que el instalador no puede dejar hecho (hay que entrar con la cuenta de la suscripción), y
sin eso el guion y el editor fallan (13-nov, Mac nueva). `estado()` nunca bloquea a quien pregunta: mide en un hilo y contesta lo
último que supo. `entrar()` abre una terminal con el inicio de sesión oficial (`claude auth login`)."""
import json
import os
import subprocess
import sys
import threading
import time

from . import config

OK, SIN_SESION, FALTA = "ok", "sin_sesion", "falta"
VIGENCIA_S = {OK: 600, SIN_SESION: 10, FALTA: 30, None: 30}   # sin sesión se vuelve a mirar pronto: la persona está entrando
_visto = {"estado": None, "t": 0.0, "midiendo": False}
_candado = threading.Lock()


def medir() -> str | None:
    """"ok", "sin_sesion", "falta" (no hay Claude Code) o None si no se pudo saber (un Claude Code viejo sin `auth status`)."""
    cmd = config.claude_cmd()
    if not cmd:
        return FALTA
    try:
        r = subprocess.run(cmd + ["auth", "status"], capture_output=True, text=True, timeout=30, stdin=subprocess.DEVNULL)
    except (OSError, subprocess.SubprocessError):
        return None
    try:
        dentro = json.loads(r.stdout).get("loggedIn")
    except (ValueError, AttributeError):
        dentro = None
    if dentro is False:
        return SIN_SESION
    return OK if dentro or r.returncode == 0 else None


def estado(forzar: bool = False) -> str | None:
    """Lo último que se supo (None la primera vez, mientras se mide). No espera: la medición corre en un hilo aparte."""
    with _candado:
        vencido = time.time() - _visto["t"] > VIGENCIA_S[_visto["estado"]]
        if (forzar or vencido) and not _visto["midiendo"]:
            _visto["midiendo"] = True
            threading.Thread(target=_actualizar, daemon=True).start()
        return _visto["estado"]


def _actualizar() -> None:
    try:
        e = medir()
    finally:
        _visto["midiendo"] = False
    with _candado:
        _visto.update(estado=e, t=time.time())


def orden_entrar(sistema: str | None = None) -> list[str] | None:
    """La orden que abre una terminal con el inicio de sesión de Claude, o None si aquí no se sabe abrir una (se dice cómo hacerlo a mano)."""
    cmd = config.claude_cmd()
    if not cmd:
        return None
    sistema = sistema or sys.platform
    if sistema == "darwin":
        guion = config.TPS / "entrar-claude.command"   # un .command se abre en la Terminal con doble clic (o con `open`)
        guion.parent.mkdir(parents=True, exist_ok=True)
        guion.write_text('#!/bin/bash\nclear\necho "Pro Studio: entra a Claude con la cuenta de la suscripción (se abre el navegador)."\n'
                         + " ".join(f'"{c}"' for c in cmd) + ' auth login\necho\necho "Listo. Ya puedes cerrar esta ventana y volver a Pro Studio."\n',
                         encoding="utf-8")
        guion.chmod(0o755)
        return ["open", str(guion)]
    if sistema == "win32":   # en su propia consola (ver `entrar`); sin `start`, que toma el primer texto entre comillas como título
        return [*cmd, "auth", "login"]
    return None


def entrar() -> bool:
    """Abre la terminal con el inicio de sesión. True si se abrió."""
    orden = orden_entrar()
    if not orden:
        return False
    try:
        if sys.platform == "win32":
            subprocess.Popen(orden, creationflags=subprocess.CREATE_NEW_CONSOLE, env={**os.environ})
        else:
            subprocess.Popen(orden, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        return False
    with _candado:
        _visto["t"] = 0.0   # la próxima pregunta vuelve a medir
    return True
