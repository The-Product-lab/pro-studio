"""Agente Editor: recibe correcciones de Pablo, las aplica (video, gusto o código del sistema) y deja la prueba de que aprendió."""
import datetime
import json
import os
import subprocess
from pathlib import Path

from .. import config, ia

AQUI = Path(__file__).resolve().parent
REGISTRO = config.RAIZ / "perfil" / "correcciones.jsonl"
HERRAMIENTAS = ("Read,Write,Edit,Glob,Grep,Bash(uv run estudio:*),Bash(uv run pytest:*),"
                "Bash(git add:*),Bash(git commit:*),Bash(git status:*),Bash(git diff:*)")


SIN_GIT = "El Agente Editor necesita Git para guardar y deshacer sus cambios y no está listo. Repite el instalador de Pro Studio o instala Git (git-scm.com)."


def _git(*args) -> subprocess.CompletedProcess:
    """git sobre la app. Sin git (o sin repositorio) levanta FileNotFoundError con una frase clara, no el error crudo del sistema."""
    try:
        r = subprocess.run(["git", *args], cwd=config.RAIZ, capture_output=True, text=True, encoding="utf-8")
    except OSError:
        raise FileNotFoundError(SIN_GIT) from None
    if r.returncode and "not a git repository" in r.stderr:
        raise FileNotFoundError(SIN_GIT)
    return r


def _registros() -> list:
    return [json.loads(l) for l in REGISTRO.read_text().splitlines() if l.strip()] if REGISTRO.exists() else []


def _nuevo_id() -> str:
    return f"C-{len(_registros()) + 1:04d}"


def corregir(texto: str, proyecto: str | None = None, avance=print) -> dict:
    REGISTRO.parent.mkdir(exist_ok=True)
    cid = _nuevo_id()
    antes = _git("rev-parse", "HEAD").stdout.strip()
    contexto = f"Proyecto actual: proyectos/{proyecto}\n" if proyecto else "Sin proyecto abierto.\n"
    prompt = (f"{(AQUI / 'CONSTITUCION.md').read_text()}\n\n---\nCorrección {cid} de Pablo:\n«{texto}»\n{contexto}"
              f"Usa el id {cid} en el commit y en el registro.")
    avance(f"{cid}: el Agente Editor (Opus) está trabajando…")
    os.environ["ESTUDIO_AGENTE"] = "1"
    try:
        out = ia.llamar(prompt, "opus", config.RAIZ, herramientas=HERRAMIENTAS, tope_usd=4.0, paso=f"agente-{cid}", timeout=3600,
                        aislado=False)   # trabaja sobre el sistema: necesita el CLAUDE.md del paquete
    finally:
        os.environ.pop("ESTUDIO_AGENTE", None)
    res = ia.json_de(out.get("result", "")) or {"clase": "?", "resumen": out.get("result", "")[:300]}
    despues = _git("rev-parse", "HEAD").stdout.strip()
    reg = {"id": cid, "fecha": datetime.datetime.now().isoformat(timespec="minutes"), "proyecto": proyecto, "texto": texto,
           "clase": res.get("clase"), "resumen": res.get("resumen"), "prueba": res.get("prueba", ""),
           "commit": despues if despues != antes else ""}
    with open(REGISTRO, "a") as f:
        f.write(json.dumps(reg, ensure_ascii=False) + "\n")
    return reg


def aprendizajes() -> list:
    return list(reversed(_registros()))


def deshacer(cid: str) -> dict:
    reg = next((r for r in _registros() if r["id"] == cid), None)
    if not reg or not reg.get("commit"):
        return {"ok": False, "error": f"{cid} no dejó un cambio que se pueda deshacer"}
    try:
        r = _git("revert", "--no-edit", reg["commit"])
    except FileNotFoundError as e:
        return {"ok": False, "error": str(e)}
    if r.returncode:
        _git("revert", "--abort")
        return {"ok": False, "error": r.stderr[-400:]}
    with open(REGISTRO, "a") as f:
        f.write(json.dumps({"id": f"{cid}-deshecho", "fecha": datetime.datetime.now().isoformat(timespec="minutes"),
                            "texto": f"deshacer {cid}", "clase": "deshacer", "resumen": f"Se deshizo {cid}", "commit": ""},
                           ensure_ascii=False) + "\n")
    return {"ok": True}
