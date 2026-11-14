#!/bin/bash
# Instalador de un paso (Mac, Linux y WSL). Se puede correr las veces que quieras.
# 1) Copia la app a su lugar fijo (Mac ~/Applications/Pro Studio · Linux ~/.local/share/pro-studio) y sigue desde ahí, así la carpeta
#    descargada se puede borrar. Los proyectos, modelos y el entorno que ya existan allá no se tocan.
# 2) Solo consigue `uv`; TODO lo demás (Claude Code, ffmpeg, modelos, bancos, icono del Escritorio) lo hace `uv run estudio instalar`.
# TPS_EN_SITIO=1 instala donde está (desarrollo); TPS_DESTINO cambia el lugar.
set -e
AQUI="$(cd "$(dirname "$0")" && pwd)"
# El motor no existe para macOS más viejos (sus piezas piden macOS 14 en Mac con chip Apple y macOS 13 en Mac Intel): se dice aquí,
# claro, en vez de fallar a la mitad con «No se pudo instalar el motor».
if [ "$(uname)" = "Darwin" ]; then
  MACOS="$(sw_vers -productVersion 2>/dev/null | cut -d. -f1)"
  if [ "$(uname -m)" = "arm64" ]; then MINIMO=14; else MINIMO=13; fi
  if [ -n "$MACOS" ] && [ "$MACOS" -lt "$MINIMO" ] 2>/dev/null; then
    AVISO="Pro Studio necesita macOS $MINIMO o más nuevo en esta Mac (tiene macOS $MACOS). Actualiza macOS en Ajustes del Sistema y abre el instalador otra vez."
    echo "$AVISO"
    osascript -e "display dialog \"$AVISO\" buttons {\"OK\"} default button \"OK\" with title \"Pro Studio\"" >/dev/null 2>&1 || true
    exit 1
  fi
fi
if [ "$(uname)" = "Darwin" ]; then DESTINO_POR_DEFECTO="$HOME/Applications/Pro Studio"; else DESTINO_POR_DEFECTO="$HOME/.local/share/pro-studio"; fi
DESTINO="${TPS_DESTINO:-$DESTINO_POR_DEFECTO}"
if [ -z "$TPS_EN_SITIO" ] && [ "$AQUI" != "$DESTINO" ]; then
  echo "Pro Studio: copiando la app a $DESTINO"
  mkdir -p "$DESTINO"
  # Reinstalar NO pisa lo aprendido: si el destino ya tiene perfil/ o librerias/estilos/, de esas carpetas solo entran los archivos NUEVOS
  # del paquete. El presets.json del paquete se deja aparte y `estudio instalar` lo fusiona (los estilos del usuario se conservan).
  PROTEGIDOS=()
  for p in perfil librerias/estilos; do
    if [ -d "$DESTINO/$p" ]; then PROTEGIDOS+=("$p"); fi
  done
  if [ -d "$DESTINO/librerias/estilos" ] && [ -f "$AQUI/librerias/estilos/presets.json" ]; then
    mkdir -p "$DESTINO/.tps"; cp "$AQUI/librerias/estilos/presets.json" "$DESTINO/.tps/presets-paquete.json"
  fi
  if command -v rsync >/dev/null; then
    EXCL=(); for p in ${PROTEGIDOS[@]+"${PROTEGIDOS[@]}"}; do EXCL+=(--exclude "/$p"); done
    rsync -a --exclude /proyectos --exclude /.tps --exclude /.venv ${EXCL[@]+"${EXCL[@]}"} "$AQUI/" "$DESTINO/"
    for p in ${PROTEGIDOS[@]+"${PROTEGIDOS[@]}"}; do rsync -a --ignore-existing "$AQUI/$p/" "$DESTINO/$p/"; done
  else
    EXCL=(); for p in ${PROTEGIDOS[@]+"${PROTEGIDOS[@]}"}; do EXCL+=("--exclude=./$p"); done
    (cd "$AQUI" && tar cf - --exclude=./proyectos --exclude=./.tps --exclude=./.venv ${EXCL[@]+"${EXCL[@]}"} .) | (cd "$DESTINO" && tar xf -)
    for p in ${PROTEGIDOS[@]+"${PROTEGIDOS[@]}"}; do (cd "$AQUI/$p" && tar cf - .) | (cd "$DESTINO/$p" && tar xkf - 2>/dev/null) || true; done
  fi
  [ "$(uname)" = "Darwin" ] && xattr -dr com.apple.quarantine "$DESTINO" 2>/dev/null || true
  exec bash "$DESTINO/instalar.sh"
fi
cd "$AQUI"
export PATH="$HOME/.local/bin:/usr/local/bin:/opt/homebrew/bin:$PATH"
mkdir -p .tps
LOG="$AQUI/.tps/instalacion.log"
if ! command -v uv >/dev/null; then
  echo "Pro Studio: instalando el gestor de Python (1 de 3)"
  curl -LsSf https://astral.sh/uv/install.sh 2>>"$LOG" | sh >>"$LOG" 2>&1
  export PATH="$HOME/.local/bin:$PATH"
fi
echo "Pro Studio: instalando el motor (2 de 3)"
# señal de vida cada 30 s: con internet lento este paso tarda minutos y una pantalla quieta parece colgada
( n=0; while sleep 30; do n=$((n + 30)); echo "   …sigue instalando ($((n / 60)) min $((n % 60)) s; es normal)"; done ) &
LATIDO=$!
trap 'kill "$LATIDO" 2>/dev/null' EXIT
MOTOR=0
uv sync --quiet >>"$LOG" 2>&1 || MOTOR=$?
# con `set -e`, el `wait` del latido recién matado (sale 143) cerraba el instalador justo después de instalar el motor (12-nov)
kill "$LATIDO" 2>/dev/null || true; wait "$LATIDO" 2>/dev/null || true; trap - EXIT
[ "$MOTOR" -eq 0 ] || { echo "No se pudo instalar el motor. Detalle en $LOG"; exit 1; }
echo "Pro Studio: bajando herramientas y modelos; la primera vez tarda (3 de 3)"
uv run --quiet estudio instalar 2>>"$LOG" || echo "Algo quedó pendiente (detalle en $LOG). Repite el instalador o pídele ayuda a Claude."
if [ -z "$TPS_SIN_ABRIR" ]; then
  echo "Pro Studio: abriendo la app"
  exec ./abrir.sh
fi
