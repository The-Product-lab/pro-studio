#!/bin/bash
# Abre Pro Studio (Linux, WSL y, vía abrir.command, Mac).
cd "$(dirname "$0")"
export PATH="$HOME/.local/bin:/usr/local/bin:/opt/homebrew/bin:$PATH"
PUERTO="${ESTUDIO_PUERTO:-8792}"
if curl -s -o /dev/null --max-time 1 "http://127.0.0.1:$PUERTO/api/proyectos"; then
  (open "http://127.0.0.1:$PUERTO" || xdg-open "http://127.0.0.1:$PUERTO" || explorer.exe "http://127.0.0.1:$PUERTO") >/dev/null 2>&1
  exit 0
fi
uv run --quiet estudio servir
