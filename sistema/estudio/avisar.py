"""Mandar muestras a Pablo por Telegram (bot operador del PC) bien formadas.

Un video sin ancho/alto ni miniatura se ve CUADRADO/achatado en la vista previa de Telegram (Pablo, 04-nov: «están achatados»).
`video()` manda siempre width/height reales, duración y una miniatura vertical; `foto()` y `texto()` para el resto.

    uv run python -c "from estudio import avisar; avisar.video('ruta.mp4', 'caption')"
"""
import json
import os
import subprocess
import tempfile
from pathlib import Path

from . import config

CANAL = Path.home() / ".claude/channels/telegram-operador"
ENV = CANAL / ".env"
APAGADO = {"ok": False, "apagado": True, "error": "avisos por Telegram apagados en esta máquina (sin token)"}


def _env() -> dict:
    """Token y chat: variables TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID, o el canal del bot operador de esta máquina (.env + access.json)."""
    v = {k: os.environ[k] for k in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID") if os.environ.get(k)}
    if "TELEGRAM_BOT_TOKEN" not in v and ENV.exists():
        for linea in ENV.read_text().splitlines():
            if linea.startswith("TELEGRAM_BOT_TOKEN="):
                v["TELEGRAM_BOT_TOKEN"] = linea.split("=", 1)[1].strip()
    if "TELEGRAM_CHAT_ID" not in v and (CANAL / "access.json").exists():
        try:
            v["TELEGRAM_CHAT_ID"] = str(json.loads((CANAL / "access.json").read_text())["allowFrom"][0])
        except (ValueError, KeyError, IndexError):
            pass
    return v


def habilitado() -> bool:
    """Hay token y chat. Sin ellos (cualquier otra máquina) los avisos quedan apagados y NUNCA fallan."""
    v = _env()
    return bool(v.get("TELEGRAM_BOT_TOKEN") and v.get("TELEGRAM_CHAT_ID"))


def _token() -> str:
    return _env()["TELEGRAM_BOT_TOKEN"]


def _chat() -> str:
    return _env()["TELEGRAM_CHAT_ID"]


def _curl(metodo: str, campos: list) -> dict:
    args = ["curl", "-s", f"https://api.telegram.org/bot{_token()}/{metodo}"]
    for k, v in campos:
        args += ["-F", f"{k}={v}"]
    r = subprocess.run(args, capture_output=True, text=True, timeout=300)
    try:
        return json.loads(r.stdout)
    except ValueError:
        return {"ok": False, "error": r.stdout[-300:]}


def video(ruta, caption: str = "") -> dict:
    if not habilitado():
        return APAGADO
    ruta = Path(ruta)
    ffmpeg, ffprobe = config.ffmpeg()
    info = json.loads(subprocess.run([ffprobe, "-v", "error", "-select_streams", "v:0", "-show_entries",
                                      "stream=width,height:format=duration", "-of", "json", str(ruta)],
                                     capture_output=True, text=True, check=True).stdout)
    w, h = info["streams"][0]["width"], info["streams"][0]["height"]
    dur = int(float(info["format"]["duration"]) + .5)
    with tempfile.TemporaryDirectory() as tmp:
        mini = Path(tmp) / "mini.jpg"   # miniatura vertical ≤ 320 px (lo que pide Telegram)
        subprocess.run([ffmpeg, "-v", "error", "-y", "-ss", "1", "-i", str(ruta), "-frames:v", "1",
                        "-vf", "scale=-2:320", str(mini)], check=True)
        return _curl("sendVideo", [("chat_id", _chat()), ("video", f"@{ruta}"), ("thumbnail", f"@{mini}"), ("width", w),
                                   ("height", h), ("duration", dur), ("supports_streaming", "true"), ("caption", caption[:1000])])


def foto(ruta, caption: str = "") -> dict:
    if not habilitado():
        return APAGADO
    return _curl("sendPhoto", [("chat_id", _chat()), ("photo", f"@{Path(ruta)}"), ("caption", caption[:1000])])


def texto(t: str) -> dict:
    if not habilitado():
        return APAGADO
    args = ["curl", "-s", f"https://api.telegram.org/bot{_token()}/sendMessage", "--data-urlencode", f"chat_id={_chat()}",
            "--data-urlencode", f"text={t[:4000]}"]
    r = subprocess.run(args, capture_output=True, text=True, timeout=60)
    return json.loads(r.stdout or "{}")
