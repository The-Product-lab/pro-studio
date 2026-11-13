#!/usr/bin/env bash
# pesado.sh <comando…> — turno de trabajo pesado (render, transcripción, ffmpeg grande): uno a la vez, EN ORDEN DE LLEGADA.
# Es la cola propia del paquete. En el PC de la oficina `estudio.config.pesado()` usa antes la cola compartida de captions.
#   herramientas/pesado.sh --estado     quién corre y quién espera
# Dentro del turno (PESADO_TENGO=1) los pasos anidados corren directo, sin hacer cola otra vez.
Q="${TPS_COLA:-$(cd "$(dirname "$0")/.." && pwd)/.tps/cola}"
if [ "${1:-}" = "--estado" ]; then
  n=0
  for t in $(ls "$Q" 2>/dev/null | sort); do
    kill -0 "${t##*-}" 2>/dev/null || continue
    n=$((n+1)); printf '%-10s pid %-7s %s\n' "$([ $n -eq 1 ] && echo CORRIENDO || echo "espera #$((n-1))")" "${t##*-}" "$(cut -c1-110 "$Q/$t")"
  done
  [ $n -eq 0 ] && echo "pesado: nadie corriendo ni esperando."
  exit 0
fi
[ -z "${1:-}" ] && { echo "uso: pesado.sh <comando…> | --estado" >&2; exit 2; }
[ -n "${PESADO_TENGO:-}" ] && exec "$@"
mkdir -p "$Q"
T="$Q/$(date +%s)$$-$$"
printf '%s' "$*" > "$T"
hijo=
trap 'rm -f "$T"' EXIT
trap '[ -n "$hijo" ] && kill "$hijo" 2>/dev/null; exit 143' INT TERM
avisado=
while :; do   # mi turno = soy el ticket vivo más antiguo (los de procesos muertos se limpian solos)
  primero=
  for t in $(ls "$Q" | sort); do
    kill -0 "${t##*-}" 2>/dev/null || { rm -f "$Q/$t"; continue; }
    primero="$Q/$t"; break
  done
  [ "$primero" = "$T" ] && break
  [ -z "$avisado" ] && echo "pesado: esperando turno ($*)" | cut -c1-160 >&2; avisado=1
  sleep 2
done
export PESADO_TENGO=1
"$@" 0<&0 &
hijo=$!
wait "$hijo"
exit $?
