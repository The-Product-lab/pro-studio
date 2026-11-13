# Pro Studio — guía para Claude (paquete instalable)

Editor de reels (9:16) para The Product Lab. Una persona sube un video hablado; el estudio lo transcribe, corta lo sobrante, propone el guion,
y tras la aprobación un **director** (Opus, por el CLI `claude` y la suscripción; nunca API) diseña el video en un storyboard JSON, un **ojo** lo
revisa con cuadros reales y el **motor** lo renderiza con subtítulos, cámara, color y sonido. Todo corre en esta carpeta; la app web es `http://127.0.0.1:8792`.
Si estás desarrollando el sistema (no solo usándolo), lee `docs/DESARROLLO.md`.

## Instalar y abrir (una sola vez, un solo paso)
- El ZIP trae la carpeta `Pro Studio/` con solo tres cosas a la vista: «Instalar Pro Studio (Windows).bat», «Instalar Pro Studio (Mac).command» y `LEEME.txt`;
  todo lo demás (esta guía, el código) está en `sistema/`. En Linux/WSL: `sistema/instalar.sh`.
- El instalador copia la app a su lugar fijo (Windows `%LOCALAPPDATA%\Pro Studio` · Mac `~/Applications/Pro Studio` · Linux `~/.local/share/pro-studio`), así la carpeta descargada
  se puede borrar; instala `uv`, Python 3.11, dependencias, Claude Code (si falta), ffmpeg y los modelos (Whisper large-v3 y recorte: ~3 GB), deja el icono «Pro Studio» en el Escritorio y abre la app.
  Es idempotente; no toca los `proyectos/` ya existentes. El detalle técnico queda en `.tps/instalacion.log`. `TPS_EN_SITIO=1` instala donde está (desarrollo).
- Falta iniciar sesión en Claude con la suscripción: si el instalador no lo pudo hacer (sin terminal), corre `claude auth login` una vez.
- Abrir: icono del Escritorio, o `abrir.bat` / `abrir.command` / `./abrir.sh` en la carpeta instalada. Si algo falla: `uv run estudio doctor` dice qué falta; `uv run estudio doctor --arreglar` lo instala.

## El flujo completo (lo mismo en la app y por terminal; `uv run estudio <comando>`)
1. **Material / ingesta:** subir el video en la app, o `estudio machote <video>` (crea `proyectos/<id>/`, transcribe, ubica a la persona (no la recorta), decide cortes).
   `--sin-ia` evita la llamada corta de Opus para los cortes.
2. **Guion:** la app muestra el guion cortado (machote); se **aprueba** antes de seguir (el director no corre sin guion aprobado).
3. **Estilo:** uno de los 13 estilos (`librerias/estilos/presets.json`), con sus colores, papel, tipografías y altura de subtítulos; vistas previas rápidas (`estudio previa`).
4. **Director + ojo:** `estudio editar <video> --estilo <id>` (o desde la app); `--desde <proyecto>` reutiliza lo ya hecho con otro estilo. Genera el arte con el conector de Higgsfield de tu cuenta de Claude (tope por estilo).
5. **Render:** `estudio render proyectos/<id>` → `final.mp4` (subtítulos, cámara, color, sonido con efectos y música por estilo, −14 LUFS).
6. **Corregir:** en la app, escribir la corrección: el Agente Editor la clasifica (video / gusto / sistema) y la aplica; el aprendizaje queda en `perfil/`.
Lotes: `estudio lote`. Estilos nuevos: `estudio crear-estilo`. Estilos Pro (Lemo): viaja en el zip (`lemo/lemo-opuscar`); el instalador le deja Node 20+, sus paquetes, su navegador (Playwright o Chrome for Testing) y su Python; en Windows también Git for Windows (su `sh`). `ESTUDIO_LEMO` apunta a otra carpeta.

## Dónde está cada cosa
- `estudio/` motor y CLI (`cli.py` es la puerta única) · `estudio/director/` prompts y gramática del director (`GRAMATICA.md`) · `app/` interfaz web.
- `librerias/` estilos, tipografías, color, sonido (`sonido/organico` grabado, `sonido/sfx`) · `perfil/` gusto y reglas del editor (el cerebro: no se borra).
- `proyectos/` los videos del usuario (nunca viajan en el paquete ni van a git) · `.tps/` lo instalado (modelos, caché).
- `tests/` pruebas · `docs/` planos y métodos · `herramientas/` cola de trabajo pesado (`pesado.sh`) y lanzador de Windows.

## Reglas que no se rompen
- IA solo por `claude -p` (Opus decide y revisa, Sonnet ejecuta; nunca Haiku ni API). Nada de claves en el repo: los avisos por Telegram quedan apagados sin token.
- Trabajo pesado (render, ffmpeg grande, transcripción) corre de a uno: `herramientas/pesado.sh <comando>`.
- Antes de entregar un cambio: `uv run estudio verificar` (sale 0). No toques `perfil/reglas.json`, `estudio/validar.py` ni las pruebas para que algo pase: se arregla la causa.
- Para sacar un paquete nuevo: `uv run estudio exportar` (lista blanca; nunca proyectos, privadas ni secretos).
- Habla con la persona en español, directo y sin relleno; no es programadora.
