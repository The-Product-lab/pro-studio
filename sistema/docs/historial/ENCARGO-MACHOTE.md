# Encargo (Isis, orden de Pablo 07-nov): terminar el MACHOTE y sacarlo para 5 clips

Repo: este worktree ~/claude-code/tps2-machote (rama pc/machote = mejora/machote + main b51910c). Lee CLAUDE.md del repo (carriles, puerta única, regla de limpieza: nada de intermedios acumulados) y estudio/machote.py + tests/test_machote.py (avance a medias de la Mac, commits 0cd0a5d y f6b62b4).

Pedido de Pablo: «preparar el clip crudo, pero colorizado y que pese poquito… coloriza, haz cortes perfectos y genera el machote. Nada de apoyos ni textos ni nada, solo coloriza y cortes, MP4 liviano; con esa versión empezamos a pulir cada uno de los estilos». Y «usa las 48 GB, que trabajemos todos al tiempo».

1. Termina `estudio machote <proyecto>`: cortes = última toma de cada frase (repeticiones.py), fuera apuntador y claquetas (voz.py/montaje.reparar), silencios ≤0,2 s (SILENCIO_MAX_S ya está en main), inicio limpio; si hace falta Claude para escoger tomas, una llamada corta de SOLO cortes. Guarda machote.json (cortes + color) y renderiza machote.mp4 con el color aprobado del proyecto (preferencias.json), solo cortes y audio, MP4 liviano (documenta resolución/CRF/peso). Que `editar --desde` use los cortes del machote si existe. Pruebas rápidas (sin render pesado en pytest).
2. `PATH=$HOME/.local/bin:$PATH uv run estudio verificar` en verde. Commit local (git add por nombre) con `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Sin push.
3. Córrelo de verdad en el PC para: c8866, c8867, c8869, c8872, c8873 (proyectos preparados; los c886x/c887x son enlaces a /mnt/e/StudioProyectos). Aprovecha RAM y CPU: los que se puedan en paralelo (ESTUDIO_PROCESOS), sin pasar la GPU (GTX 1050 3 GB) y por pesado.sh si aplica. Copia cada machote.mp4 a "<Escritorio>/claude workshop/MACHOTES/<CLIP>-machote.mp4".
4. NO toques: ~/claude-code/the-product-studio-2 (árbol principal), ni el worktree ../tps2-correcciones-07nov (otra sesión con las correcciones de Pablo), ni ../tps2-t0193.
Al terminar escribe RESULTADO-MACHOTE.md: archivos, commit, verificar, y por clip: duración, peso, # cortes, qué quitó; 6 líneas en simple para Pablo.
