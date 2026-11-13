"""Única puerta a la IA: el binario oficial `claude -p` con la suscripción. Opus dirige, Sonnet ejecuta. Nunca Haiku."""
import json
import os
import re
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from . import config, trabajo

MODELOS = {"opus", "sonnet"}
LIMITE_TOPE_H = 6.0           # horas máximas de espera acumulada por un límite de Claude (ESTUDIO_LIMITE_TOPE_H lo cambia)
LIMITE_TROZO_S = 300          # se duerme en trozos de 5 min y se deja constancia de que sigue esperando
LIMITE_MARGEN_S = 120         # segundos extra tras la hora de reinicio que da Claude
_LIMITE = re.compile(r"hit your[^.\n]*limit|usage limit", re.I)
_REANUDA = re.compile(r"resets?\s+(?:at\s+)?(\d{1,2})(?::(\d{2}))?\s*([ap]m)?\s*(?:\(([^)]+)\))?", re.I)
_ahora = datetime.now        # se reemplazan en las pruebas
_dormir = time.sleep


class LimiteAgotado(RuntimeError):
    """Claude dijo «hit your limit · resets HH:MM»: no es un fallo del video, es esperar. `reanuda_en` puede ser None."""

    def __init__(self, mensaje: str, reanuda_en: datetime | None = None):
        super().__init__(mensaje)
        self.reanuda_en = reanuda_en


def parsear_limite(texto: str, ahora: datetime | None = None) -> LimiteAgotado | None:
    """LimiteAgotado si el texto es el aviso de límite de Claude (con la hora de reinicio si la trae), si no None."""
    if not _LIMITE.search(texto or ""):
        return None
    ahora = ahora or _ahora().astimezone()
    m = _REANUDA.search(texto)
    if not m:
        return LimiteAgotado(texto.strip()[:300])
    h, minuto, ampm, zona = int(m.group(1)), int(m.group(2) or 0), (m.group(3) or "").lower(), m.group(4)
    if ampm:
        h = h % 12 + (12 if ampm == "pm" else 0)
    try:
        tz = ZoneInfo(zona.strip()) if zona else ahora.tzinfo
    except (KeyError, ValueError, OSError):
        tz = ahora.tzinfo
    if not 0 <= h < 24 or minuto > 59:
        return LimiteAgotado(texto.strip()[:300])
    hoy = ahora.astimezone(tz)
    cuando = hoy.replace(hour=h, minute=minuto, second=0, microsecond=0)
    if cuando <= hoy:
        cuando += timedelta(days=1)
    return LimiteAgotado(texto.strip()[:300], cuando)


def _estado_limite(datos: dict) -> None:
    """Deja constancia de la espera en el archivo que indica ESTUDIO_ESTADO_LIMITE (el lote lo lee); se sobrescribe, no se borra."""
    estado = os.environ.get("ESTUDIO_ESTADO_LIMITE")
    if estado:
        Path(estado).write_text(json.dumps(datos, ensure_ascii=False))


def _esperar_limite(lim: LimiteAgotado, esperado_s: float, paso: str) -> float:
    """Duerme hasta que Claude vuelva y devuelve lo esperado en total; LimiteAgotado si no se debe o no se puede esperar."""
    tope_s = float(os.environ.get("ESTUDIO_LIMITE_TOPE_H", LIMITE_TOPE_H)) * 3600
    if os.environ.get("ESTUDIO_NO_ESPERAR"):
        raise lim
    if lim.reanuda_en:
        falta = (lim.reanuda_en - _ahora().astimezone()).total_seconds() + LIMITE_MARGEN_S
    else:
        falta = min(60 * 60, 600 * 2 ** int(esperado_s // 1200))      # sin hora: 10 min, 20, 40… hasta 1 h
    falta = max(falta, 0)
    if esperado_s + falta > tope_s:
        raise lim
    hasta = (_ahora().astimezone() + timedelta(seconds=falta)).isoformat(timespec="minutes")
    restante = falta
    while restante > 0:
        _estado_limite({"esperando": True, "paso": paso, "hasta": hasta, "mensaje": str(lim)})
        trozo = min(LIMITE_TROZO_S, restante)
        _dormir(trozo)
        restante -= trozo
    _estado_limite({"esperando": False})
    return esperado_s + falta


def llamar(prompt: str, modelo: str, cwd: Path, herramientas: str = "Read,Write,Edit,Glob,Grep",
           tope_usd: float = 3.0, paso: str = "", mcp: bool = False, timeout: int = 1800, aislado: bool = True) -> dict:
    """Llama a Claude. Si responde «hit your limit», espera hasta la hora que indica y repite ESTE mismo paso (no es un fallo).
    `aislado` (por defecto): Claude corre sin lo personal de la máquina (su CLAUDE.md, memoria, skills, plugins y hooks), para que el
    estudio trabaje igual en cualquier equipo y no cargue ese contexto en cada llamada (10-nov: 56 mil tokens → 31 mil por llamada).
    Con `mcp=True` no aplica (los conectores de la cuenta son parte de lo personal); `aislado=False` es para quien necesita el
    CLAUDE.md de la carpeta donde trabaja (Agente Editor, Estilos Pro)."""
    esperado = 0.0
    while True:
        try:
            return _llamar(prompt, modelo, cwd, herramientas, tope_usd, paso, mcp, timeout, aislado)
        except LimiteAgotado as lim:
            esperado = _esperar_limite(lim, esperado, paso)


def _llamar(prompt: str, modelo: str, cwd: Path, herramientas: str, tope_usd: float, paso: str, mcp: bool, timeout: int,
            aislado: bool = True) -> dict:
    if modelo not in MODELOS:
        raise ValueError(f"modelo no permitido: {modelo} (solo {sorted(MODELOS)})")
    cmd = config.claude_cmd()
    if not cmd:
        raise RuntimeError("no encuentro `claude`: instálalo e inicia sesión (corre `claude` una vez)")
    if mcp and "ToolSearch" not in herramientas.split(","):
        # Claude Code entrega las herramientas de los conectores «diferidas»: sin permiso para ToolSearch no las puede ni cargar
        # (11-nov: las llamadas de imágenes volvían vacías en 5 s y ningún video recibía su arte)
        herramientas = "ToolSearch," + herramientas
    args = cmd + ["-p", prompt, "--model", modelo, "--output-format", "json", "--allowedTools", herramientas,
                  "--permission-mode", "acceptEdits", "--max-budget-usd", str(tope_usd), "--no-session-persistence"]
    if not mcp:
        args += ["--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}']
    t0 = time.time()
    # por variable y no por opción: un Claude Code anterior a este modo la ignora en vez de fallar por opción desconocida
    entorno = {**os.environ, "CLAUDE_CODE_SAFE_MODE": "1"} if aislado and not mcp else None
    r = trabajo.correr(args, cwd=cwd, capture_output=True, text=True, timeout=timeout, env=entorno)   # se puede detener desde la app
    try:
        out = json.loads(r.stdout)
    except ValueError:
        out = {"is_error": True, "result": (r.stdout + r.stderr)[-2000:]}
    with open(Path(cwd) / "costos.jsonl", "a") as f:
        u = out.get("usage") or {}   # tokens (Pablo 09-nov: «¿cuántos tokens gastaste?»): entrada, salida y caché, tal cual los da claude -p
        f.write(json.dumps({"paso": paso, "modelo": modelo, "usd_equivalente": out.get("total_cost_usd", 0),
                            "tokens": {k: u.get(k, 0) for k in ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")},
                            "segundos": round(time.time() - t0, 1), "ok": not out.get("is_error")}) + "\n")
    if out.get("is_error"):
        limite = parsear_limite(str(out.get("result")))
        if limite:
            raise limite
        raise RuntimeError(f"{paso}: claude falló: {str(out.get('result'))[:500]}")
    return out


def json_de(texto: str) -> dict:
    """Saca el primer objeto JSON de la respuesta de texto de Claude."""
    a, b = texto.find("{"), texto.rfind("}")
    return json.loads(texto[a:b + 1]) if a >= 0 < b else {}
