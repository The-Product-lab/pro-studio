# Pro Studio

Editor de reels que **diseña cada video a medida** y **aprende de tus correcciones**.

## Instalar (una vez, en cualquier PC)
- **Windows:** doble clic en `instalar.bat` · **Mac:** `instalar.command` · **Linux/WSL:** `./instalar.sh`

Hace todo solo (uv, Python, dependencias, Claude Code si falta, ffmpeg y modelos: ~3 GB la primera vez), deja el icono **Pro Studio** en el Escritorio
y abre la app. Necesita una cuenta de Claude con suscripción (nada de API). Si algo falla: `uv run estudio doctor --arreglar`.

## Usar
- Doble clic en el icono **Pro Studio** del Escritorio (o `abrir.bat` / `abrir.command` / `./abrir.sh`) → se abre la app en `http://127.0.0.1:8792`.
- **Nuevo video** → el estudio transcribe, ubica a la persona (sin recortarla), el **director** (Opus) diseña las escenas, genera el arte
  a medida (Higgsfield, máximo 8 imágenes), el **ojo** (Opus) revisa cuadros reales y corrige, y renderiza.
- A la derecha: estilos, colores, papel, tipografías, persona B/N o color, altura de subtítulos → vista previa al instante.
- **Corregir:** escríbele al Agente Editor. Clasifica tu corrección:
  - **video** → arregla ese video;
  - **gusto** → lo anota en `perfil/gusto.md` y el director lo aplica en todos los videos siguientes;
  - **sistema** → cambia el código del motor con una prueba en `tests/regresion/` que demuestra que aprendió.

## Por terminal (lo mismo que usa la app y el agente)
```
uv run estudio doctor                 # revisa que todo esté instalado
uv run estudio editar video.mov       # edición completa
uv run estudio machote c8866          # PRIMERO: crudo con el color aprobado + solo los cortes, MP4 liviano (machote.mp4)
uv run estudio previa proyectos/x 1.0 5.0 9.5
uv run estudio render proyectos/x
uv run estudio verificar              # compuerta antes de entregar: sin basura, compila, pruebas
uv run estudio exportar               # arma el ZIP del paquete (ProStudio-AAAA-MM-DD.zip); --publicar lo sube a un repo privado
```

## El machote (etapa fija, antes de cualquier estilo)
`estudio machote <proyecto|video>` deja en el proyecto `machote.json` (cortes + color + qué se quitó) y `machote.mp4`: el crudo con el
color aprobado (`preferencias.json`) y SOLO los cortes, con su audio; sin textos, apoyos, SFX ni subtítulos. 720×1280, H.264 CRF 26, AAC 128k
(≈65–110 KB por segundo: los 5 del 07-nov, 30–37 s, pesan 2,2–3,8 MB). Un solo ffmpeg con `select` (una pasada, sin intermedios ni cuadros
en memoria): los 5 a la vez tardan 1 min y usan < 6 GB de RAM (`ESTUDIO_PROCESOS=3` hilos cada uno). Los cortes salen casi todos de código
(última toma de cada frase repetida, claqueta y apuntador fuera, bordes en pausas reales, ningún tramo sin palabras, inicio y final limpios con
≤ 0,1 s de aire) más UNA llamada corta de Opus solo de cortes (`--sin-ia` la omite; reintenta una vez si no responde JSON): quita charla con el
equipo, conteos, tomas abandonadas, versiones sobrantes y lo que pase de 110 s, y puede `restaurar` frases que el detector de apuntador
cortó pero son del talento hablando suave. Solo rehace lo que cambió (otras palabras → cortes nuevos; otro color → solo el video).
`estudio editar --desde <proyecto>` copia `machote.json` al proyecto del estilo, el director lo recibe en su prompt y `machote.imponer` garantiza en código
que sus cortes entran al storyboard; `editar` sobre un video nuevo decide los cortes antes del director. Siguiente paso: que el motor de estilos
lea `machote.mp4` como fuente liviana para las vistas previas.

## Cómo está hecho
- `estudio/motor.py`: storyboard JSON → video (la toma completa, textos, apoyos, trazos, subtítulos, grano). Gramática: `estudio/director/GRAMATICA.md`.
- `estudio/director/`: prompts del director y del ojo + un ejemplo aprobado (IMG_0653).
- `estudio/agente/`: el Agente Editor, su constitución y el candado (no puede tocar pruebas existentes, su constitución ni los instaladores).
- `librerias/`: estilos, tipografías (solo OFL) y guías de estilo. Para sumar estilos: deja referencias en `referencias-estilos/`.
- IA solo por `claude -p`: Opus dirige, mira y corrige; Sonnet ejecuta. Nunca Haiku.
