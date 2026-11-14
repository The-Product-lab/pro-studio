# Limpieza y pulido de estilos (10-nov)

Vigentes (13): basico, cine, glass, imprenta, julian-alborna, julian-alborna-3d, luminoso, maestro, maestro-calma, pop, prestiggio, swiss, vox.
Eliminados por orden de Pablo: collage-papel, hud (el ESTILO; el tipo de subtítulo `hud` se queda), archivo-rojo, cianotipo, kraft-verde, editorial-color, noche-neon.

## Ficha completa
Cada preset de `librerias/estilos/presets.json` declara TODAS las claves de `tests/test_estilos_fichas.py › FICHA`. El valor de una clave
que faltaba es el que el motor ya usaba (su defecto), así que elegir el estilo da lo mismo de siempre. El preset es la única fuente; el
ejemplo del director solo muestra nivel.

## Prueba de no daño
1. Liviana (corre en `estudio verificar`): `tests/test_estilos_fichas.py` compara el estilo efectivo que usa el motor con la foto
   `tests/estilos_nodano/efectivos.json` (tomada ANTES de completar fichas). Los cambios decididos por Pablo van en `INTENCIONALES`.
2. Con render real (a mano, pesada): ~9 s por estilo (subtítulo + apoyos + cámara), 1 de cada 4 cuadros, huella sha256 por cuadro.
   Usa solo el motor (sin director), sobre copias `proyectos/_estilos-<estilo>` que se borran solas.
   - Fijar la base:  `~/claude-code/captions/tools/pesado.sh uv run python tests/render_nodano.py guardar [estilo ...]`
   - Comparar:       `~/claude-code/captions/tools/pesado.sh uv run python tests/render_nodano.py comparar [estilo ...]`  (sale 1 si algo cambió)
   - 3 cuadros PNG:  `... tests/render_nodano.py png <estilo> <carpeta>`
   Los storyboards salen de `../the-product-studio-2/proyectos/c8866-<estilo>` (basico: c8872-basico); `TPS_BANCO_PROYECTOS` lo cambia.
   Las huellas de `tests/estilos_nodano/<estilo>.json` valen para la misma máquina y versiones de librerías.

## Construido (10-nov): subtítulo con caja de vidrio (Glass)
El motor tiene tres subtítulos (`tira` papel, `hud` palabra a palabra, `basico` con caja de color opcional) y el elemento `vidrio`
(panel esmerilado), pero NINGÚN subtítulo con caja de vidrio. Contrato corto:
- Entra: `estilo.subtitulo = "vidrio"`; bloques de palabras de siempre (`tramos_subtitulo`), palabra clave en acento.
- Sale: caja de vidrio esmerilado (desenfoque de lo que hay detrás + velo claro + borde de luz + sombra, como `Elemento._vidrio`) centrada en la zona
  segura (y de `subtitulos.y`), con las palabras dentro; las palabras aparecen cuando se dicen.
- Nunca: salir de la zona segura, tapar la cara, cambiar el color de la toma, ni verse sobre fondo claro sin legibilidad (usar `fondo_claro_o_rayado`).
- Verificación: caso nuevo en el banco de pruebas de Glass + `render_nodano.py` (cambio intencional: Glass cambia a propósito).
Hecho: `subtitulo: "vidrio"` (`motor.Subtitulos._vidrio`, vidrio común `motor.caja_vidrio`); Glass lo usa. Pruebas en `tests/test_recursos.py` (zona segura, acento, contraste ≥3 sobre negro/gris/blanco/rayas, entrada en fundido). OJO: el storyboard de la muestra de no daño (c8866-glass) oculta TODOS los subtítulos (`ocultar [[0,240]]`), así que `render_nodano.py` no los ve: IDÉNTICO no prueba nada del subtítulo.

## Decisiones de Pablo (10-nov) aplicadas
- Glass: sonido «digital» (cambio intencional del estilo efectivo, no de los cuadros).
- Cámara: regla ÚNICA en `perfil/reglas.json` («una cámara que viaja sin brincos; de vez en cuando golpes de zoom; Glass flota SIEMPRE»). Se quitaron
  las otras 4 notas de cámara, `camara_mov_cada_s` (y su chequeo en `validar._camara_viva`: exigía un keyframe cada ~4 s, contra «la cámara la mueve el motor»)
  y el override `camara_cambio_min_s: 2.5` (ahora manda el defecto del código, 6 s, igual que GRAMATICA.md: el ir y venir se mide igual para todos).
  `punch_por_min` (4/10/15 golpes por minuto) se deja: son los «golpes de zoom»; Pablo puede bajarlos.

## Unificado (mismo valor escrito en varios lugares)
Zona segura -> `config.ZONA_SEGURA`; volumen de efectos 0,28 -> `config.SFX_VOLUMEN`; silencio máx. 0,30 s (0,20 hasta el 13-nov) -> `montaje.SILENCIO_MAX_S` (lo importa `revisar_corte`).

## Contradicciones (estado al 10-nov)
1. «Un movimiento a la vez»: RESUELTA (Pablo): vale para los 13 con `flotar_elementos_max` global; luminoso, julian-alborna y julian-alborna-3d bajaron a 2.
2. Tope del reel: RESUELTA (main): `director/__init__.py` usa `machote.LIMITE_S` más `machote.TOLERANCIA_S`; el prompt recibe `{limite_s}`.
3. «Más imágenes» contra el ritmo: RESUELTA (Pablo): menos imágenes; la vida la dan los elementos tipográficos y las animaciones; el techo de ritmo se queda.
4. Ejemplo del director contra preset: el ejemplo ya no es la fuente; el test valida cada ejemplo con el estilo del PRESET. `color` es preferencia por video, no del preset.

## Garantía por estilo (en código: tests/test_estilos_fichas.py)
Contrato de los 13 (`CONTRATO`): subtítulo, paleta de sonido, tope de imágenes y si pide arte; la cámara se mide con `camara.saltos` (sin brincos y sin ir y venir
a 30, 60 y 110 s); los golpes de zoom salen de UNA tabla (`punch_por_min`, máx. 15/min); ningún preset trae `color`, `filtro` ni claves de cámara propias;
Glass flota siempre; Básico no toma ejemplo de otro estilo (`director._ejemplo` ya no hace respaldo). NO medible desde la ficha: que el motion/cortes/encuadres
«se vean perfectos» (eso lo miden la compuerta `validar.py` y el render de no daño por cuadro, y al final lo ve Pablo).
Render de no daño por cuadro hecho hasta ahora: basico, cine, glass, imprenta, julian-alborna, julian-alborna-3d = IDÉNTICO. Pendientes (cola de render, a la orden de Pablo):
luminoso, maestro, maestro-calma, pop, prestiggio, swiss, vox.

## Glass del 10-nov: cámara que no flotaba y cosas de más (Pablo: «hay momentos con muchos elementos al tiempo, no hay casi movimiento flotante de cámara»)
Diagnóstico (storyboard glass-nuevo-10nov, copia en tests/fixtures/glass-nuevo-10nov):
- Los «3 brincos de 0,23 de zoom / 86 px» NO eran golpes de zoom (en la base `pantalla` el punch ni entra a la cámara). Eran (1) el reencuadre: el primer cuadro caía 0,005 s
  antes del primer tramo y valía 1.0 en vez de 1.22 (`motor.encuadre_en`); (2) un tramo de reencuadre más corto de 1 s que movía 0,16 de zoom (`ENCUADRE_TRAMO_MIN_S`);
  (3) un escalón de ~86 px en la caja de la cara (`motor._suavizar_caras`). Con los tres arreglos el supervisor mide 0 brincos y 0 sacudidas SIN apagar el reencuadre.
- La flotación de Glass (flotar 8) se movía ~3 px por ventana de 4 s: invisible. Piso medible en `camara.FLOTA_PISO_PX` (recorrido mediano por ventana de `FLOTA_VENTANA_S`);
  Glass sube a flotar 48 (~16 px) y la compuerta `validar._flota_siempre` lo exige y rechaza que se apague. Ojo: más flotación acerca el texto al borde visible; se movieron 4 textos del ejemplo.
- NO se pidió un piso para los otros estilos con `flotar` (3 a 7 px): el mismo piso los rechazaría. Pablo decide si quiere que flote todo lo que declara flotar.
- Pregunta abierta: el reencuadre alterna zoom 1.06 y 1.22 cada ~3 s (ir y venir) y Glass debería «viajar lento sin ir y venir»; hoy Glass tiene ese reencuadre activo.
- «Una cosa a la vez»: `validar._una_cosa_a_la_vez` (clave `elementos_a_la_vez_max` en reglas.json) cuenta cosas visibles a la vez (tarjeta + su texto = un `grupo`; trazos cuentan). Solo vale en Glass:
  los 12 ejemplos del director la rompen (hasta 15 cosas a la vez; p. ej. swiss 15, julian-alborna 13, prestiggio 9), así que activarla global rechazaría todo lo aprobado.
- `validar._vidrio_vacio`: tarjeta de vidrio sin texto ni contenido más de `VIDRIO_VACIO_MAX_S` (en el caso real: v5, 0,7 s vacía). Global.
- Contador: `motor.texto_contador` dice «1 cita» / «2 citas» (plural regular sin su «s», o `singular` explícito).

## Cuestionario de Pablo (10-nov) aplicado
Decisiones: golpes de zoom = UN techo `punch_max_por_min` = 4 (los 13; Básico no); flotación visible para todos menos Básico (`flota_siempre` global, `flotar` 40 en los 12);
inicio = persona + texto/caja del gancho (`gancho: true`) desde el cuadro 0; Básico cámara quieta (excepción escrita) con efectos suaves en cortes; Cine y Luminoso con imágenes
(tope 4); Glass con foto en miniatura dentro de tarjeta de vidrio (`apoyo_integrado` falso); «una cosa a la vez» solo en Glass; 3D conserva 8 imágenes (excepción escrita);
Imprenta y Julián con sonido «papel-maquina» (papel grabado + click de máquina REAL: `librerias/sonido/organico/click-maquina/`, grabaciones del banco Epidemic de Pablo en
`the-product-lab-studio/biblioteca/sfx/tecleo`; el banco de audio no va a git, y `estudio sfx organicos` busca la categoría «click-maquina» en Openverse CC0 en otra máquina);
Prestiggio y Swiss con sonido digital; Maestro `flotar_elementos` 0; reencuadre de Glass como está.

Regla de Opus (Pablo 10-nov): las compuertas solo ponen TECHOS o prohíben DEFECTOS; el estilo y su ejemplo son REFERENTE, no receta. Compuertas con mínimo encontradas:
- `punch_por_min` (mínimo de golpes de zoom por densidad): convertida en techo `punch_max_por_min`. Ya no exige golpes.
- Mínimo de keyframes de cámara (`camara_mov_cada_s`): ya se había quitado.
- El ejemplo subía el tope de ritmo (`_ritmo_de_ejemplo`): quitado; el tope de ritmo es uno (reglas.json › ritmo).
- Pablo (10-nov): «Déjalas que Opus decida». `recurso_hueco_max_s`, `texto_siempre_max_s`, `variedad` y `ritmo` ya NO bloquean: salen de `validar.errores` y quedan como `validar.consejos`
  (el director los anota como avisos) más una frase de guía sin números en reglas.json. Sus pruebas de regresión (C-0007, C-0009, texto siempre) siguen midiendo las mismas funciones.
- `texto_min_px` de Swiss y `texto_linea_min_px` de Cine: reemplazados por UNA regla global de legibilidad (ver abajo).
Ejemplos aprobados: hoy son inspiración. Siguen teniendo más imágenes que el tope (vox 28, imprenta 19, pop 15…): no se regeneran; el prompt ya no les copia la cantidad.
Las fotos con `flotar` > 2 del ejemplo 3D y de Cine están exentas del tope (solo una imagen animada puede moverse además del texto).

## Legibilidad (Pablo 10-nov, muestra de Prestiggio: «palabras muy pequeñas en las tomas de b-roll… y en pantalla completa, fondo sólido»)
Dos pisos medibles en `perfil/reglas.json › global` para los 13 estilos:
- `texto_linea_min_px` = 48: ninguna línea de `texto`, `etiqueta` ni `contador` baja de ahí. Medida: a 1080 px de ancho en un celular de 6,1 pulgadas (~71,5 mm de ancho, ~15 px/mm) una mayúscula
  de 48 px (cap ≈ 0,73 em = 35 px) mide ~2,3 mm, unos 0,38° a 35 cm: el mínimo cómodo para leerla de un vistazo; a 30-34 px (las etiquetas de la muestra) quedan en ~1,5 mm.
- `pantalla_principal_ancho_min` = 0,40: en pantalla completa o fondo sólido (escena sin la persona) la línea principal (las palabras a la misma altura que están a la vez cuentan como una línea; sin las
  etiquetas mono) ocupa al menos el 40 % del ancho. Calibrado con los 12 ejemplos aprobados: 80 escenas, 6 por debajo de 40 % (3D x4, vox, cine) y el resto entre 40 % y 80 %.
Absorbe `texto_min_px` de Swiss (150) y `texto_linea_min_px` de Cine (40): ya no hay dos reglas para lo mismo. Swiss conserva «palabra principal grande» como identidad, en su guía.
Ojo para quien mezcle: este plano está en la raíz del repo y `pc/exportar` mueve los .md de la raíz a `docs/`.
Fuera de la regla de legibilidad, por decisión de Pablo (10-nov): los Estilos Pro («ahí no hay problema de tamaño, eso es diferente») y los subtítulos. Entran las franjas y las cajas HUD (mismo piso, `config.piso_texto_px()`).
