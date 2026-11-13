# Plano: guion rápido y orden del flujo (Pablo, 07-nov y 10-nov)

## Regla principal (una sola)
**Antes de cada orden de la persona, la app solo hace trabajo neutro de preparación**: normalizar, transcribir, recortar a la persona y
proponer los cortes del guion. Ninguna decisión creativa ni de estilo (director, imágenes, ojo, presets, hook, sonido) corre sin la orden
que le toca: **guion aprobado → estilo elegido → recién ahí el director, con ESE estilo.**
(Pablo: «la app empieza a trabajar y a tomar decisiones antes de yo darle la orden; por eso se enreda».)
Se hace cumplir en código: `/api/dirigir` y `servidor._dirigir` se niegan sin `guion_aprobado`; `tests/test_guion_rapido.py::test_regla_principal_preparar_no_decide_nada`.

## Contrato
- **Entra:** cualquier video (4K, S-Log, HDR, 60 fps, vertical ya listo) subido en la app.
- **Sale, en este orden:** 1) `palabras.json` + `machote.json` (el guion) sin esperar normalización ni alfa; 2) `fuente.mp4` + alfa
  (en paralelo); 3) con guion aprobado y estilo elegido: storyboard, arte, ojo.
- **Nunca:** `storyboard.json`/`arte.json`/llamadas `director` antes de la orden · un `fuente.json` provisional leído como master ·
  dos lugares que eligen el dispositivo de Whisper · el estilo nuevo mezclado con restos del anterior.

## Fases (CUANDO… EL SISTEMA DEBE… · verifica)
Todo: `uv run pytest tests/test_guion_rapido.py` sale 0.
1. **Motores.** CUANDO se transcribe EL SISTEMA DEBE usar un solo modelo Whisper (`estudio/asr.py`), en GPU (cuda int8) si arranca; si no, en
   CPU con aviso; si la GPU falla a mitad, rehacer esa transcripción en CPU y no volver a probarla. `transcribir`, `voces_fuera` y
   `revisar_corte` pasan por `asr` (ninguno crea `WhisperModel`). Dependencias `nvidia-cublas-cu12` y `nvidia-cudnn-cu12` (no Mac).
2. **Guion primero.** CUANDO se sube un video EL SISTEMA DEBE correr `ingesta.preparar_guion` (audio del original, `fuente.json`
   provisional, machote) en paralelo, en otro hilo, a `ingesta.preparar_media` (normalizar + alfa), que al terminar escribe el
   `fuente.json` definitivo. `derivar` se niega sobre un proyecto provisional.
3. **Director después de la orden.** CUANDO la persona elige estilo con el guion aprobado EL SISTEMA DEBE lanzar `/api/dirigir`:
   espera la preparación, borra el intento previo (`limpiar_intento`), y corre densidad + director + imágenes + ojo con ese estilo.
   Un pedido nuevo deja sin efecto al anterior que aún esperaba; cambiar de estilo re-dirige partiendo de los cortes del machote.
4. **Estilo completo.** CUANDO se elige un estilo EL SISTEMA DEBE partir del preset completo de ese estilo (`app.js › elegir`, y
   `director._fijar_estilo` en el servidor), no del estilo anterior.

## Anotado, no cambiado
- **NVENC en `normalizar`:** no se cambió. El master es x264 `crf 15 preset medium` (máxima calidad) y NVENC de la GTX 1050 (Pascal) a
  igual tamaño pierde detalle y no admite el mismo control de calidad; tampoco acelera el filtro (lut3d en 16 bits y lanczos corren en CPU).
  Ahora la normalización corre en paralelo al guion, así que ya no está en el camino crítico del guion.
- **Alfa (RVM):** sigue en CPU (onnxruntime sin CUDA); también va en paralelo.
