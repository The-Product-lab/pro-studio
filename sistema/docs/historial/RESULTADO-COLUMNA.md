# Resultado: columna vertebral, registro único de reglas y mapa vivo (07-nov)

Rama `pc/columna` · commit **5892c2d** (local, sin push) · `uv run estudio verificar` **verde** (253 pruebas pasan, 2 saltadas, 33 s; 19 pruebas nuevas en `tests/test_columna.py`).

## Para Pablo (en simple)
1. El editor ya tiene una columna fija: Preparar → Machote → Guion → Estilo → Render → Entrega; cada paso dice qué recibe, qué entrega y quién lo revisa.
2. Todas las reglas viven ahora en un solo archivo (28 reglas), cada una con tu frase y su fecha. No se guardan reglas viejas: si cambias una, la anterior se borra.
3. Si dos reglas chocan, o si el código, un prompt o una guía dicen otro número, el editor no deja guardar el cambio.
4. Ya encontró y corrigió 4 contradicciones: el director decía «los primeros 2 s con un elemento fuerte» y tu regla dice «los primeros 3 s solo la persona».
5. Hay un mapa (MAPA.md) que dice para qué sirve cada pieza y a qué paso pertenece; si aparece una pieza sin dueño, el editor la frena.
6. Decisión tuya: en Prestiggio, ¿la caja del hook sale desde el cuadro 0 o espera los 3 s limpios? Hoy gana el inicio limpio, que es lo que el código ya hacía.

## Archivos
- Nuevos: `estudio/columna.py` (pasos, contratos, `estado()`, índice de piezas, generador del mapa), `estudio/reglas.py` (leer, `reemplazar`, `contradicciones`), `librerias/reglas.json` (registro), `MAPA.md` (generado), `tests/test_columna.py`.
- Modificados: `estudio/cli.py` (`estudio mapa`, `estudio reglas`, `estudio regla <id> <valor> --frase "…"`, `estudio paso <proyecto>`), `estudio/verificar.py` (pasos 5 y 6).
- Limpieza de menciones viejas: `estudio/director/director.md`, `librerias/estilos/hud.md`, `librerias/estilos/prestiggio.md`, `perfil/reglas.json` (nota de Prestiggio), `estudio/director/GRAMATICA.md`, `tests/test_montaje.py`; se quitó `ingesta.silencios` (regla vieja de 0,45 s, ya no la usaba nadie).

## Reglas registradas (28, todas vivas)
| Paso | Regla | Valor | Dónde se vigila |
|---|---|---|---|
| machote | silencio_max_s | 0,2 s | `montaje.SILENCIO_MAX_S` |
| machote | ultima_toma | sí | repeticiones + director (sin compuerta numérica) |
| machote | inicio_sin_basura | sí | voz + montaje.reparar |
| machote | apuntador_bajo_db | 15 dB | `voz.APUNTADOR_BAJO_DB` |
| guion | reel_max_s | 110 s | **solo en el prompt** (no hay compuerta en código) |
| estilo | zona_texto_y | 230–1500 px | `validar.ZONA_TEXTO` + gramática + director |
| estilo | inicio_limpio_s | 3 s | perfil + textos |
| estilo | escena_min_s · ritmo_entradas_max · ritmo_ventana_s | 2,5 s · 3 · 5 s | perfil + textos |
| estilo | texto_siempre_max_s · filtro_max_s | 1,5 s · 1,5 s | perfil |
| estilo | color_toma_intocable · sujeto_recortado_prohibido | sí · sí | perfil |
| estilo | variedad_max_mismo_seguido · variedad_max_proporcion · variedad_min_tipos | 2 · 0,45 · 3 | perfil |
| estilo | apoyo_literal_ventana_s | −1…1,5 s | perfil |
| estilo | apoyo_integrado | sí (pop, imprenta, vox: no) | perfil |
| estilo | texto_salto_max_px | 380 px | perfil |
| estilo | texto_min_px | swiss 150 px | perfil |
| estilo | flotar_elementos_max | maestro 2 | perfil |
| estilo | colores_prohibidos | prestiggio: rosa | perfil |
| estilo | tapado_max_area · tapado_max_ancho | 0,35 · 0,22 | `validar.MAX_TAPADO*` |
| render | acercar_max | 0,15 | `efectos.ACERCAR_MAX` |
| render | zoom_entrada_dur_s · zoom_entrada_amp | 0,7 s · 0,04 | `efectos.ZOOM_ENTRADA_*` + gramática |

Las constantes técnicas que no son reglas tuyas (AIRE_FIN, ARRANQUE_MIN_S, TRAMO_MIN, HOP, umbrales de voz, etc.) quedan en su módulo y no van al registro.

## Huérfanos y contradicciones encontrados
- Piezas sin paso: **ninguna** (las 44 de `estudio/` y las 7 de `app/` quedan en el índice). `estudio/machote.py` se declaró de antemano en el paso Machote como pendiente.
- Contradicciones corregidas: director.md «primeros 2 s… elemento fuerte desde el cuadro 0», hud.md «primeros 2 s los más rápidos» y «cambio cada 0,5–2 s» (chocaban con el inicio limpio de 3 s, la escena mínima de 2,5 s y el máximo de 3 cosas en 5 s), GRAMATICA «rosa prohibido» para todos (en el código solo aplica a Prestiggio), docstring de prueba con el 0,7 s viejo, `ingesta.silencios` (0,45 s).
- Pendiente de Pablo: la caja del hook de Prestiggio desde el cuadro 0 contra el inicio limpio. Alineé los textos a lo que el código ya hacía (gana el inicio limpio). Si quiere el hook desde el cuadro 0: `"inicio_limpio_s": 0` en `estilos.prestiggio` de perfil/reglas.json y `"por_estilo": {"prestiggio": 0}` en el registro.

## Al integrar (avisos para quien junte ramas)
- `pc/silencio-audible`, `pc/correcciones-07nov` y `pc/plano-flujo` agregan `global.recurso_hueco_max_s` (C-0009) a perfil/reglas.json. Al juntarlas, `verificar` la marcará como huérfana: agregar al registro `{"id": "recurso_hueco_max_s", "que": "Después del inicio limpio, nunca más de esto sin un recurso visible.", "valor": 2.5, "unidad": "s", "paso": "estilo", "estado": "viva", "origen": {"frase": "no le está poniendo casi recurso", "fecha": "2026-11-07", "literal": true}, "compuerta": "estudio.validar:errores", "perfil": "recurso_hueco_max_s"}`.
- `pc/machote`: al entrar, poner `"existe": True` en el paso Machote de `estudio/columna.py` y correr `estudio mapa`.
- Cualquier cambio de docstring de un módulo pide `estudio mapa` (el mensaje de verificar lo dice).
- TODO migración (en `estudio/reglas.py`): que montaje/validar/voz/efectos lean `reglas.valor(id)` y desaparezcan las constantes. Hoy la prueba solo exige que tengan el mismo valor.
- Sin tocar (sección 10, es sensible): una línea en el `CLAUDE.md` del repo que apunte a `MAPA.md` y `librerias/reglas.json`. Queda como recomendación.
- No encontré `obras.md` en este PC (`~/Desktop/CLAUDE CODE/claudio/cerebro/registro/` no existe aquí); la obra quedó registrada solo en este encargo.
