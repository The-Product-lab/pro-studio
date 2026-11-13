# Handoff · pulir estilos de The Product Studio 2 (sesión Trabajo/Telegram, 08-nov)

Forma de trabajar (orden de Pablo 08-nov): memoria `feedback_opus_orquesta_sonnet_ejecuta.md`. Contestar cada Telegram en <1 min en una línea; Opus orquesta; todo el hacer a subagentes Sonnet en segundo plano; no tocar app/.

## Dónde
- Rama local `pc/silencio-oido` en el worktree `~/claude-code/tps2-machote` (NO subida a main). 3 pruebas rojas que frenan el merge: test_C-0010::test_isla_entre_cortes_de_contenido_se_quita, test_machote::test_banco_de_casos_reales[julian3d-c8869], test_validar::test_montaje_ajusta_lo_medible_y_no_toca_lo_aprobado (esta también falla en main, depende de la máquina).
- Symlinks del worktree sin commitear (no subir): proyectos, .tps/modelos, librerias/sonido/sfx.
- **app/index.html + app/app.js**: el 07-nov agregué el selector Poco/Normal/Mucho (#densidad). Desde el 08-nov app/ es de la Mac: avisarle para que lo revise o lo rehaga.

## Estilos (cada uno con un video distinto del workshop C8866–C8873)
Aprobados: maestro, luminoso, prestiggio, julian-alborna, maestro-calma.
Enviados, sin respuesta: swiss (c8867-swiss), vox (c8870-vox, el primero con todo lo nuevo de cámara).
Faltan: pop, glass, imprenta, julian-alborna-3d, cine. Revisar antes que el base tenga alpha (c8871 puede faltar; los base c8868/c8870/c8871 apuntan a /mnt/g desconectado → usar lote-c88xx-* o regenerar en /mnt/c/Users/<usuario>/StudioProyectos).
Comando: `cd tps2-machote && ~/claude-code/captions/tools/pesado.sh uv run estudio editar --desde <base> --estilo <x> --nombre <nombre> --biblioteca proyectos/c8866-<estilo>/arte`.
Antes de mandar: `revisar_corte.revisar(final, nivel_talento=montaje.contexto(proj).talento)` + hoja de contacto.

## Cámara (lo nuevo del 07-nov, en estudio/motor.py)
- Reencuadre de la persona: ENCUADRES 1,0–1,26, cambia seco en una palabra cada 2,8–4,6 s al azar, nunca repite.
- Lienzo en pantallas completas (persona oculta): se acerca y viaja a lo que entra (LIENZO_ZOOM .07, LIENZO_SIGUE .14, LIENZO_MAX_PX 40) + flotación por ruido.
- Quitado el golpe fijo al entrar a cada pantalla (Pablo: «elimina eso»).
- Director: cámara siempre activa, sin patrón.
- PENDIENTE de Pablo: eligió entre 3 clips (sutil .04/.08/25 · medio = actual · agresivo .20/.40/140 con textos al 72 %). Clips en el scratchpad: lienzo-sutil/medio/agresivo.mp4. Propuse: una por estilo o según densidad (poco/normal/mucho). Pablo pidió coordinar zoom agresivo con textos más chicos.

## En curso
- Agente (general-purpose) estudiando los reels DfcLoDvEgMg y DfLmQwWp5E8 → prototipo de estilo en `~/claude-code/laboratorio-estilos/` (fuera del editor). Reportar a Pablo cuando termine.
- Reel DfcM2kcFkAA (analizado con vidIQ): estilo técnico/isométrico, acento rojo, micro-interacciones UI, estímulo cada 0,8–1,5 s, SFX de clics/checks. Pablo dijo «podría funcionar para varios estilos»: sin acción aún.

## Otros pendientes
- Luminoso: excepción gris hasta «colores» (sin respuesta de Pablo).
- Bloqueado por Pablo: DJI, Valentina, conversación aburrida, Paulina, Notion. No borrar nada sin su OK.

## Estado 08-nov 23:20 (leer esto primero)
- Aprobados por Pablo: maestro, luminoso, prestiggio, julian-alborna, maestro-calma, swiss, vox, glass. Cámara aprobada: pantallas completas = UN movimiento A→B (suave ease_io / continuo lineal, mismo recorrido); persona = movimiento fluido entre planos (commit 15bae23). El texto se achica para caber, nunca se acorta el movimiento.
- Imprenta v2 enviada (c8868-imprenta), falta quitar foto de mujer.
- En curso (subagente): banco de archivo SIN fotos de personas + reemplazo en imprenta y glass; fila con motor nuevo: julian-alborna-3d (C8869), cine (C8867), glass re-render, pop sobre C8869 (falló en C8872 por escena de 0,3 s del director).
- Revisar cada final: `revisar_corte.revisar(final, nivel_talento=montaje.contexto(P).talento)` + hoja de contacto mirada (bordes, cámara, nada de personas en fotos de archivo, ningún texto diminuto) ANTES de mandarlo a Pablo.
- Plan de laboratorio (aparte del editor): ~/claude-code/laboratorio-estilos/PLAN-NOCHE-08nov.md.
