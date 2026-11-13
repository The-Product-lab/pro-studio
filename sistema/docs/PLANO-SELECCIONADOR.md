# Plano: seleccionador (efectos, colores, tipografías, estilos y todo lo seleccionable) — 2026-11-04

Pablo: «crear la app seleccionador de efectos, colores, tipografías, estilos y todo lo que sea seleccionable». Antes (03-nov):
«yo tengo opciones para decisión creativa: color, forma, estilo, fuente, efecto». Y la ley de hoy: no dañar lo que funciona, nada
de recetas que quiten libertad, nada de listas sueltas que después nadie mantiene.

## Contrato
- **Entra:** el catálogo VIVO del sistema, leído del código (nunca una lista copiada a mano): estilos (`presets.json` + muestras),
  fuentes (`librerias/fuentes/indice.json` + Google Fonts), color (`color.recetas()`, `color.looks()`), acentos, transiciones
  (`validar.ENTRADAS_ESCENA`), entradas de texto (`validar.ENTRADAS`), tratamientos de imagen (`tratamiento`, `fusion`, `fundir`,
  `cubrir`, `acercar`), fondos (`efectos.MUROS`), modos de subtítulo, efectos de estilo (grano, crt, aberración, bloom, flotar),
  paletas de sonido (`sonido.PALETAS`).
- **Sale:** una pantalla `/seleccionador` con tarjetas VISUALES (cada opción se ve: muestra animada corta o imagen) donde Pablo
  marca lo que quiere para un video. Se guarda en `proyectos/<p>/preferencias.json`:
  - `estilo`: valores únicos (acento, fuentes, color, grano, bloom, flotar, subtítulo, paleta…) — ya lo respeta `_fijar_estilo`.
  - `repertorio`: listas por categoría (transiciones, entradas de texto, tratamientos, fondos) que Pablo eligió.
- **Director:** si hay `repertorio`, la guía dice «Pablo eligió para este video: …» y la compuerta rechaza usar en ESA categoría
  algo que él no eligió. Categoría sin elegir = libertad total (como hoy).
- **Nunca:** duplicar listas del código; romper Personalizar (sigue igual y comparte el mismo `preferencias.json`); obligar a elegir;
  usar el repertorio como receta (elegir ≠ usar todo: el director usa lo que sirva de lo elegido).

## Fases (cada una con su prueba)
1. `estudio/catalogo.py`: arma el catálogo desde el código + `GET /api/catalogo`. Prueba: cada opción del catálogo existe en el
   motor/compuerta y viceversa (si alguien agrega una transición al motor, aparece sola).
2. Muestras: `uv run estudio muestras` renderiza por `pesado.sh` un clip de ~1,2 s por transición/entrada/efecto sobre el C8866 en
   `app/muestras/sel/` (fuera de git). Prueba: cada opción del catálogo tiene su muestra o un aviso claro.
3. `app/seleccionador.html` + `POST /api/seleccion` (proyecto, estilo, repertorio) → `preferencias.json` (mezcla, no pisa).
   Prueba: guardar y leer; Personalizar sigue funcionando.
4. Director y compuerta leen `repertorio` (guía + `_repertorio` en validar). Prueba: algo fuera de lo elegido se rechaza; sin
   repertorio no cambia nada (las 74 pruebas siguen verdes).
5. Enlace desde la app (paso Personalizar → «Abrir seleccionador») y desde la pantalla de revisión.

## Abogado del diablo
- «Las muestras pesan y tardan» → se hacen una vez, por la cola, fuera de git; se regeneran solo si cambia el motor.
- «El repertorio vuelve a ser una receta» → solo restringe lo que Pablo eligió explícitamente; vacío = libertad.
- «Dos pantallas editando lo mismo» → un solo archivo (`preferencias.json`), mezcla por clave.

## Fase 6 — rediseño (04-nov, Pablo: «el catálogo es muy lento… muy poco premium; que se vea más cosas»)
- **Lento = no cargaba**: `/api/proyectos` caía con «proyecto inválido» porque el lote deja proyectos como enlaces a C:
  (`--trabajo-en`) y `_proyecto()` rechazaba todo lo que apuntara fuera. Ahora revisa el NOMBRE (sin «/», «..»), no el destino.
  Además: catálogo en caché en el servidor (`catalogo_cacheado`, se rehace si cambia algo en disco), `/api/proyectos?ligero=1`,
  póster jpg por muestra (`<muestra>.poster.jpg`), video solo al pasar el mouse / al verse en táctil (máx. 6 a la vez),
  fuentes con `FontFace` al verse, URLs con `?v=<mtime>` y caché de un día. Medido: tarjetas en ~0,3 s (antes: nunca).
- **Más cosas, leídas del código**: estilos aprobados primero, tipos de hook (`catalogo.HOOKS` + `tipos_de_hook`, sale de cómo
  abren las copias aprobadas; muestra = sus primeros 2,8 s), paletas de los estilos, filtros (`efectos.FILTROS`), textura/luz,
  tipos de texto (`validar.ESTILOS_TEXTO`), cajas/etiquetas y contadores/barras (`validar.RECURSOS`; el destello queda fuera:
  prohibido), trazos (`validar.TIPOS_TRAZO`). Repertorios nuevos: filtros, trazos, recursos, textos (compuerta) y hooks (solo guía).
- **Personalizar**: secciones plegables (Estilo, Color, Tipografía, Textos y cajas, Hook, Efectos, Sonido) con las mismas muestras;
  mini módulo de color: entrada, receta y looks como miniaturas de la toma, fuerza y ajustes (`color.AJUSTES`: exposición,
  contraste, saturación, temperatura, tinte; en 0 la cadena es la de siempre, lo prueba `test_ajustes_de_color_en_cero…`).
- Pruebas: `tests/test_seleccionador.py`.
