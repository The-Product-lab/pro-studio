"""`estudio doctor`: revisa cada pieza del motor y dice cómo arreglar lo que falte."""
import json
import platform
import subprocess
import sys
import time
from pathlib import Path

from . import config, disco, entorno

REINSTALAR = "corre otra vez «Instalar Pro Studio» (o instalar.sh en Linux) o `uv run estudio doctor --arreglar`"
LOGIN_CACHE = config.CACHE / "claude-login-ok"
LOGIN_VIGENCIA_S = 24 * 3600


def _item(nombre, ok, version="", arreglo=""):
    return {"nombre": nombre, "ok": ok, "version": version, "arreglo": "" if ok else arreglo}


def _correr(cmd: list[str], timeout=20) -> str:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=True).stdout.strip()


def revisar_python():
    ok = sys.version_info[:2] == (3, 11)
    return _item("python", ok, platform.python_version(), REINSTALAR)


def revisar_ffmpeg():
    try:
        ffmpeg, ffprobe = config.ffmpeg()
        linea = _correr([ffmpeg, "-version"]).splitlines()[0]
        _correr([ffprobe, "-version"])
        return _item("ffmpeg", True, linea.split()[2])
    except (OSError, subprocess.SubprocessError, ImportError, RuntimeError):
        return _item("ffmpeg", False, arreglo=REINSTALAR)


def revisar_modelos():
    falta = [n for n, p in (("whisper", config.WHISPER_DIR / "model.bin"), ("detector de caras", config.CARAS_ONNX), ("rvm", config.RVM_ONNX)) if not p.exists()]
    return _item("modelos", not falta, "whisper large-v3 + detector de caras + rvm", f"faltan {', '.join(falta)}: {REINSTALAR}")


def revisar_claude():
    cmd = config.claude_cmd()
    sin_claude = "instala Claude Code (https://claude.com/claude-code) y corre `claude` una vez para iniciar sesión"
    if not cmd:
        return _item("claude", False, arreglo=sin_claude)
    try:
        version = _correr(cmd + ["--version"]).split()[0]
    except (OSError, subprocess.SubprocessError):
        return _item("claude", False, arreglo=sin_claude)
    if LOGIN_CACHE.exists() and time.time() - LOGIN_CACHE.stat().st_mtime < LOGIN_VIGENCIA_S:
        return _item("claude", True, version)
    try:
        salida = _correr(cmd + ["-p", "Responde solo: ok", "--model", "opus", "--output-format", "json",
                                "--max-budget-usd", "0.5", "--no-session-persistence",
                                "--strict-mcp-config", "--mcp-config", "{\"mcpServers\":{}}"], timeout=120)
        ok = not json.loads(salida).get("is_error", False)
    except (OSError, subprocess.SubprocessError, ValueError):
        ok = False
    if ok:
        LOGIN_CACHE.parent.mkdir(parents=True, exist_ok=True)
        LOGIN_CACHE.touch()
    return _item("claude", ok, version, "abre una terminal, corre `claude` e inicia sesión con tu suscripción")


def revisar_discos():
    rotos = disco.revisar_enlaces(config.PROYECTOS)
    fuera = [e for e in rotos if e["unidad"] and disco.tipo_unidad(e["unidad"]) != disco.FIJO]
    return _item("discos", not rotos, f"{len(rotos)} enlaces rotos" if rotos else "enlaces sanos",
                 "; ".join(f"proyectos/{e['proyecto']} -> {e['destino']}" for e in rotos[:5])
                 + (f" (en unidades extraíbles o ausentes: {', '.join(sorted({e['unidad'] for e in fuera}))})" if fuera else ""))


def revisar_windows():
    if not entorno.en_wsl():   # solo aplica dentro de WSL (Mac, Linux y Windows nativo no los necesitan)
        return _item("windows", True, "no aplica fuera de WSL")
    falta = [n for n in ("powershell.exe", "attrib.exe") if not entorno.windows_exe(n)]
    return _item("windows", not falta, "powershell.exe + attrib.exe", f"no encuentro {', '.join(falta)} (¿fuera de WSL?)")


def revisar_bancos():
    """Lo que viaja dentro del paquete: sonido (orgánico + efectos), tipografías, estilos y perfil."""
    r = config.RAIZ
    falta = [n for n, ok in (
        ("sonido orgánico", any((r / "librerias/sonido/organico").glob("*/*.wav"))),
        ("efectos de sonido", any((r / "librerias/sonido/sfx").glob("*.wav"))),
        ("tipografías", any((r / "librerias/fuentes").rglob("*.[ot]tf"))),
        ("estilos", (r / "librerias/estilos/presets.json").is_file()),
        ("perfil", (r / "perfil/reglas.json").is_file())) if not ok]
    return _item("bancos", not falta, "sonido + tipografías + estilos + perfil",
                 f"faltan {', '.join(falta)}: vuelve a descomprimir el paquete" + (" (los efectos se bajan con `uv run estudio sfx traer`)" if "efectos de sonido" in falta else ""))


def revisar_textos() -> dict:
    """Los textos miden lo mismo que en cualquier otro equipo (13-nov: en otros Mac salían de otro tamaño)."""
    from PIL import features
    from . import fuentes
    version = f"Pillow {features.version('pil')}, FreeType {features.version('freetype2')}"
    try:
        distintas = fuentes.medidas_distintas()
    except Exception as e:  # noqa: BLE001 — una letra que falta o no abre también es «no mide igual»
        distintas = [f"{type(e).__name__}: {e}"]
    return _item("textos", not distintas, f"miden igual en todos los equipos ({version})",
                 "; ".join(distintas) + f" ({version}): {REINSTALAR} y avísale a Isis con este renglón")


def revisar_higgsfield(claude_ok: bool) -> dict:
    """Informativo (nunca falla): sin el conector los videos salen completos, pero sin arte a medida."""
    from . import imagenes
    if not claude_ok:
        return _item("higgsfield", True, "se revisa cuando Claude tenga sesión")
    return _item("higgsfield", True, "conectado (arte a medida)" if imagenes.conector()
                 else f"sin conectar: los videos salen sin arte a medida → {imagenes.CONECTAR}")


def revisar_opcionales() -> list[dict]:
    """Telegram es informativo (nunca falla). Estilos Pro: Lemo viaja en el paquete (12-nov), así que si está y no quedó instalado, falla."""
    from . import avisar, instalar
    pro = (config.lemo() / "core").is_dir()
    listo = pro and instalar.lemo_listo()
    return [_item("telegram", True, "avisos encendidos" if avisar.habilitado() else "apagado (opcional: sin token no avisa, no falla)"),
            _item("estilos-pro", listo or not pro,
                  "Lemo listo (Node, paquetes, navegador y Python)" if listo
                  else "Lemo sin terminar de instalar → repite el instalador con internet" if pro
                  else "sin Lemo en esta copia (los 13 estilos normales no lo necesitan)")]


def revisar() -> list[dict]:
    claude = revisar_claude()
    return [revisar_python(), revisar_ffmpeg(), revisar_modelos(), claude, revisar_higgsfield(claude["ok"]), revisar_bancos(), revisar_textos(), revisar_discos(),
            revisar_windows(), *revisar_opcionales()]


def main(como_json=False, arreglar=False) -> int:
    if arreglar:
        from . import instalar
        instalar.arreglar()
    items = revisar()
    if como_json:
        print(json.dumps({"ok": all(i["ok"] for i in items), "items": items}, ensure_ascii=False, indent=1))
    else:
        for i in items:
            print(f"{'✓' if i['ok'] else '✗'} {i['nombre']:<12} {i['version']}" + (f"  → {i['arreglo']}" if not i["ok"] else ""))
    return 0 if all(i["ok"] for i in items) else 1
