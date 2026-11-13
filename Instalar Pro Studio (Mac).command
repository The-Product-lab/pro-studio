#!/bin/bash
# Pro Studio: instalador para Mac (doble clic). Solo revisa que el ZIP este extraido; TODO lo demas lo hace sistema/instalar.sh.
cd "$(dirname "$0")"
if [ ! -f sistema/instalar.sh ]; then
  osascript -e 'display dialog "Primero extrae el ZIP (doble clic en el ZIP) y abre este archivo otra vez." buttons {"OK"} default button "OK" with title "Pro Studio"' >/dev/null 2>&1
  exit 1
fi
bash sistema/instalar.sh
