# Plano: paquete exportable de Pro Studio (ZIP que corre en otro computador)

Orden de Pablo: un ZIP que se descomprime en otra máquina (Windows, Mac o Linux/WSL), se abre con un Claude Code nuevo sin skills ni MCP nuestros,
y con UN paso queda funcionando y haciendo todo. Sin datos de Pablo.

## Contrato
- **Entra:** código, app, librerías (estilos, tipografías, color, sonido orgánico y efectos, carátulas y muestras de la app), perfil (el gusto del editor),
  pruebas, docs, instaladores, `MANIFIESTO.txt`.
- **Sale:** un `.zip` con lista blanca (`estudio/exportar.py`). Nunca: `proyectos/`, `privadas/`, `.tps/`, `.venv`, `.git`, `costos.jsonl`, videos, `.env`,
  tokens, rutas del PC de la oficina, el chat de Telegram. Lo comprueba `tests/test_exportar.py` abriendo el zip.
- **Nunca debe pasar:** que el paquete dependa de una carpeta fuera de sí mismo; que un aviso sin token falle.

## Inventario: qué vivía fuera del repo o en .gitignore, y qué se hizo
| Pieza | Antes | Ahora |
|---|---|---|
| `librerias/sonido/organico` (22 categorías CC0, con `click-maquina` de Epidemic) | ignorada por git | viaja en el zip (4 MB) |
| `librerias/sonido/sfx` | enlace a `captions/assets-lib/sfx` | el zip lleva los archivos reales (8 MB); si faltan, el instalador corre `sfx traer` |
| `app/muestras/*` y `app/muestras/sel` (carátulas y muestras de efectos/color/estilos) | `sel` ignorada, 19 MB | viaja el contenido real (jpg y mp4 de muestra) |
| `referencias-estilos` (6 800 cuadros, 334 MB) | ignorada | solo viajan las hojas de contacto `hoja.jpg`; los cuadros se regeneran con `estudio crear-estilo` |
| `perfil/` | en git | viaja (gusto, reglas, diccionario, correcciones) |
| `banco/` (6 GB de video del taller) | ignorada | solo `banco/LEEME.md`; las pruebas con video se saltan si falta |
| `privadas/` (LUTs de Pablo) | ignorada | NO viaja; `looks()` usa los de `librerias/color` |
| Modelos Whisper large-v3, detector de caras (YuNet) y personas en fotos (RVM) | `.tps/modelos` | se bajan al instalar (`estudio doctor --arreglar`) |
| ffmpeg | `static-ffmpeg` | igual, lo baja el instalador |
| Claude Code (`claude`) | instalado a mano | el instalador lo instala con el instalador oficial; `config.claude_cmd()` también mira `~/.local/bin` |
| Rutas `/home/…`, `/mnt/c/Users/…` en código | `revision.py`, `pro.py`, `textos_lemo.py`, `texto_pelicula.py` | `config.REVISION`, `config.lemo()`, `config.pesado()`; en notas y fixtures el exportador las reescribe |
| Cola `captions/tools/pesado.sh` | rutas absolutas | `config.pesado()`: `ESTUDIO_PESADO` o la propia `herramientas/pesado.sh`; en Windows nativo, directo |
| Aviso Telegram (`avisar.py`) | token y chat fijos | token por variable o canal del bot; sin token queda apagado y devuelve `apagado`, no falla |
| Estilos Pro (Lemo, node) | carpeta hermana | viaja en el zip (`lemo/lemo-opuscar`, sin `node_modules`); `estudio instalar` le deja Node 20+, paquetes, navegador (Playwright o Chrome for Testing) y Python; en Windows, Git for Windows (winget) por su `sh` |
| Agente Editor (git, guarda) | git del repo y `.claude` fuera del zip | `.claude/settings.json` (solo ese) viaja; el instalador hace `git init` + commit inicial; sin git el agente avisa claro |
| Reinstalar | pisaba `perfil/` y los estilos | `perfil/` y `librerias/estilos/` del destino se conservan (solo entran archivos nuevos); `presets.json` se fusiona en Python (`instalar.fusionar_presets`) |
| Windows | cp1252, `os.kill`, `fcntl`, SO_REUSEADDR | `PYTHONUTF8=1` en los `.bat`/`.vbs` y relanzado `-X utf8` en `cli`; `estudio/portable.py` (proceso vivo, candado); puerto en exclusiva |
| `verificar` usaba `git ls-files` | fallaba sin `.git` | usa `MANIFIESTO.txt` (lo que git rastreaba) |
| Node, Chromium, Playwright | — | el render no los usa (solo Estilos Pro necesita node) |
| 15 planos sueltos en la raíz | raíz | `docs/` (con `git mv`) |

## Fases y su prueba
1. Rutas portables: `grep -rn "/home/\|/mnt/c" estudio app` sin resultados de datos personales. 
2. Instalador único: los tres `instalar.*` solo consiguen `uv` y llaman `uv run estudio instalar`. CUANDO se corre en carpeta limpia, EL SISTEMA DEBE dejar `estudio doctor` en verde.
3. Exportar: `uv run estudio exportar` → `pytest tests/test_exportar.py` sale 0.
4. Acceso directo: `estudio instalar` crea el icono del Escritorio (`estudio/escritorio.py`).
5. Publicar: `uv run estudio exportar --publicar [--en-seco]` crea repo PRIVADO con `gh` y adjunta el zip como Release (límite 2 GB por archivo).
6. Prueba de verdad: zip → carpeta limpia con HOME propio → `instalar.sh` → `doctor` → `verificar` → `servir` en 8799 → `curl`.

## Estructura del zip (10-nov, Pablo: «se abren un montón de carpetas»)
`Pro Studio/` con solo «Instalar Pro Studio (Windows).bat», «Instalar Pro Studio (Mac).command» y `LEEME.txt` (fuentes en `herramientas/paquete/`); todo lo demás en `sistema/`
(en Windows queda oculta). El instalador copia `sistema/` al lugar fijo (`%LOCALAPPDATA%\Pro Studio`, `~/Applications/Pro Studio`, `~/.local/share/pro-studio`) y sigue desde ahí.
Si el `.bat` se abre desde dentro del ZIP sin extraer, no ve `sistema\` y muestra un cuadro «Primero extrae el ZIP». La lógica vive en `instalar.bat` / `instalar.sh` (dentro de `sistema/`); los de la raíz solo revisan y llaman.
