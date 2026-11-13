# Resultado: MACHOTE (encargo Isis, orden de Pablo 07-nov). PC, rama `pc/machote`

## Para Pablo (en simple)
1. Los 5 machotes están listos en `<Escritorio>/claude workshop/MACHOTES/` (C8866, C8867, C8869, C8872, C8873): crudo con tu color, solo cortes, sin textos ni apoyos.
2. Pesan entre 2,2 y 3,8 MB y duran entre 30 y 37 s (720×1280).
3. Quedan la última toma de cada frase, sin conteos ni charla con el equipo, y los silencios bien recortados.
4. Los 5 se hicieron a la vez en 1 minuto, sin trabar el PC.
5. Hay restos chicos que conviene oír: C8866 («Lo corta, lo… a ver, ya», «3,» y el CTA repetido «si quieres aprender a editar como…»), C8872 («Ya.» y un «Y Y si»), C8867 («te… listo» antes del CTA).
6. Con estos machotes ya se puede pulir cada estilo: `editar --desde` parte de estos cortes.

## Archivos
- Código: `estudio/machote.py`, `tests/test_machote.py` (25 pruebas, sin IA real ni render pesado), `README.md` (sección «El machote»).
- Por proyecto: `machote.json` (cortes, color, qué se quitó, qué hizo la IA, avisos) y `machote.mp4`.
  C8866 está en `~/claude-code/the-product-studio-2/proyectos/c8866/` (solo datos, carpeta ignorada por git; no se tocó código del árbol principal). Los demás están en `/mnt/e/StudioProyectos/c88xx/`.
- Copias: `<Escritorio>/claude workshop/MACHOTES/<CLIP>-machote.mp4`.

## Commits (locales, sin push)
- `2f41852`: bordes con la regla de 0,2 s (aire de inicio y final ≤ 0,09 s), tramos sin palabras se cortan enteros, la IA ve la charla pegada.
- `bacc44f`: la IA puede **restaurar** guion que el detector tomó por apuntador; las frases de más de 6 s (Whisper sin puntos) se parten en su pausa más larga; un reintento si la IA no responde JSON; el descarte por exceso se mide en tiempo y no en número de frases; el inicio limpio ignora lo que quitó la IA; el render se hace con `select` en una pasada.
- `uv run estudio verificar`: **verde** (259 passed, 2 skipped, 21 s).

## Formato del MP4
720×1280, H.264 `-preset medium -crf 26`, AAC 128k, faststart, BT.709. La LUT del color aprobado (`preferencias.json`: receta pablo + calido-EliteColor200 0,7) se aplica en 16 bits. Peso de 65 a 110 KB por segundo. Un ffmpeg por clip, sin intermedios. Los 5 en paralelo dentro de un solo turno de `pesado.sh` (`ESTUDIO_PROCESOS=3`): 60 s en total, pico de 5,8 GB de RAM y sin GPU.

## Por clip
Columna «quitado»: tomas repetidas / claqueta / apuntador / IA fuera de guion / pausas y aire, en segundos.

| Clip | Duración | Peso | # cortes | Quitado (s) | IA (1 llamada Opus) | Residuales |
|---|---|---|---|---|---|---|
| C8866 | 238 s → 33,7 s | 3,8 MB | 12 | 69,6 / 10,3 / 10,5 / 46,5 / 67,8 | quitó 42 frases, restauró «pone» | 3 |
| C8867 | 195 s → 30,3 s | 2,5 MB | 10 | 4,8 / 1,4 / 32,3 / 65,0 / 61,3 | quitó 75 frases, restauró «Además,» | 1 |
| C8869 | 85 s → 37,3 s | 2,2 MB | 16 | 0 / 0 / 14,1 / 14,2 / 19,5 | quitó 36 frases, restauró «todos», «si» | 8 |
| C8872 | 99 s → 34,5 s | 3,5 MB | 7 | 2,0 / 0,1 / 19,3 / 10,4 / 32,2 | quitó 16 frases | 2 |
| C8873 | 109 s → 33,7 s | 3,4 MB | 7 | 1,2 / 0,8 / 27,2 / 17,1 / 29,0 | quitó 21 frases | 2 |

Qué quitó la IA, por ejemplo: «Perdón, pensé que estaba María acá / Tranqui, tranqui» (C8872), «¿Qué era? Ya me olvidé» y la discusión «taller o workshop» (C8867), «Otra, más potencia / Sobre exagerado / Ahí es» (C8866), «¿Y qué más era? / 7A / de ahí sí ya el call to action» (C8873), y las dos primeras versiones del CTA (C8869). El detalle completo está en `machote.json` → `ia.quito`.
Como referencia, el texto final de cada clip coincide con lo que dejó el director en el lote anterior: 26–38 s, el mismo guion.

## Lo que queda abierto (con el dato)
- **El detector de apuntador (`voz.py`) marca al talento.** En C8869 marcó 101 palabras, entre ellas los tres pasos del guion. Mientras tanto, el machote le muestra a Opus lo que el código quitó y Opus puede devolverlo (`_la_ia_lo_dejo`, marcado **provisional** en el código porque cambia el contexto en caché de montaje). El arreglo real va en `voz.py`/`montaje.py`, que están en obra en `../tps2-correcciones-07nov`: no los toqué.
- **Avisos de `montaje.errores` que siguen saliendo:**
  - «termina 0,00 s después de…»: falso positivo cuando Whisper estira una palabra sobre la pausa que `reparar` mismo cerró. El corte cae en silencio medido.
  - «silencio de 0,4–1,6 s»: pausas que `reparar` no parte para no dejar un pedacito de menos de 0,5 s.
  - «voz fuera de cámara quedó»: en estos casos es el talento hablando suave.

  Los tres son de montaje, así que en la prueba del banco quedaron fuera de los «graves», con un comentario que explica por qué. Lo grave sí se exige: versiones repetidas, cortes con voz sonando y pedacitos.
- **La IA no da siempre la misma respuesta.** Una llamada por clip; si se rehace (`--rehacer`), el corte puede variar un poco.
- **`obras.md`:** no existe en este PC (`~/Desktop/CLAUDE CODE/claudio/cerebro/registro/obras.md`), así que no pude anotar la obra.
- **Costo:** 1 llamada Opus por clip y por corrida, ~0,25–0,29 USD equivalente cada una, dentro de la suscripción. Mientras ajustaba el prompt hice unas 26 llamadas en total.
