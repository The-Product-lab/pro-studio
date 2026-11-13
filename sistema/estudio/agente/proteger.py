"""Hook PreToolUse: con ESTUDIO_AGENTE=1, el agente no puede tocar pruebas existentes, su constitución, .claude/ ni los instaladores."""
import json
import os
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
PROTEGIDOS = ("estudio/agente/CONSTITUCION.md", ".claude/", "instalar.command", "instalar.bat", "instalar.sh", "estudio/agente/proteger.py")


def _versionado(rel: str) -> bool:
    manifiesto = RAIZ / "MANIFIESTO.txt"   # en el paquete exportado no hay .git: esta lista es lo que git rastreaba
    if not (RAIZ / ".git").exists() and manifiesto.exists():
        return rel in manifiesto.read_text(encoding="utf-8").splitlines()
    return bool(subprocess.run(["git", "ls-files", rel], cwd=RAIZ, capture_output=True, text=True).stdout.strip())


def main() -> int:
    if os.environ.get("ESTUDIO_AGENTE") != "1":
        return 0
    ev = json.load(sys.stdin)
    entrada = ev.get("tool_input", {})
    ruta = entrada.get("file_path") or ""
    if ev.get("tool_name") == "Bash":
        cmd = entrada.get("command", "")
        if any(p in cmd for p in ("rm ", "git checkout", "git reset", "git push")):
            print(f"Bloqueado: el agente no puede correr «{cmd[:80]}».", file=sys.stderr)
            return 2
        return 0
    if not ruta:
        return 0
    rel = os.path.relpath(Path(ruta).resolve(), RAIZ).replace("\\", "/")
    if rel.startswith(PROTEGIDOS) or (rel.startswith("tests/") and _versionado(rel)):
        print(f"Bloqueado: «{rel}» está protegido (constitución del Agente Editor).", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
