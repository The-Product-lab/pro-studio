# VOX · @johnny.harris · https://www.instagram.com/reel/DbvdFAgBHKy/
Estudiado con vidIQ el 2026-11-04 · fuente: búsqueda de creadores (no es referencia del dueño)

Duración: 59,5 s · formato vertical 9:16 · «Japanese baseball looks a lot different than American baseball. Here's why.»

Nota de método: vidIQ entrega la descripción por escenas, los tiempos de corte, el texto en pantalla y un cuadro. Los HEX y tamaños marcados «≈» son estimados a partir de ese cuadro y de la descripción, no medidos por código. Los tiempos de corte y los textos sí vienen literales de vidIQ.

## 1) Lenguaje visual en una frase
Explicativo de archivo estilo Vox/Johnny Harris: metraje de época (blanco y negro, transmisiones viejas, cromos de béisbol) cortado cada ~2,6 s, con mapas 2D animados y tarjetas de comparación lado a lado, subtítulos pequeños pegados a la voz y cierre de marca con cursor animado.

## 2) Paleta (HEX y uso)
≈ valores del cuadro visible y de la descripción; verificar con medición por píxeles antes de implementar.
- Azul cromo vintage ≈ #2F6F9F: fondo de los cromos de béisbol de archivo.
- Rojo de imprenta ≈ #C8202A: caracteres japoneses del cromo, acento de archivo.
- Gris flanela ≈ #B9B7B0: uniforme del jugador, tonos medios del archivo.
- Blanco subtítulo ≈ #FFFFFF: texto de subtítulos y etiquetas.
- Negro translúcido ≈ #000000 al 55–65 %: caja detrás del subtítulo.
- Negro/gris muy oscuro ≈ #111111: pantalla final de marca y fondo de mapas oscuros.
- Blanco y negro del archivo (escala de grises): todo el metraje histórico de las escenas 1–2 y 5.
- Etiquetas con bandera 🇺🇸 / 🇯🇵: color por emoji, sin color de marca propio.

## 3) Tipografías
- Subtítulos: sans-serif neutra tipo Helvetica/Arial regular (≈, no confirmado por vidIQ), ~16 px sobre un cuadro de 180 px de ancho (≈ 9 % del ancho; ≈ 3,5 % de la altura de 1920 equivale a ~38 px en 1080×1920).
- Etiquetas de comparación («POWER», «CONSISTENCY», «VELOCITY», «CRAFTINESS»): mayúsculas sans-serif en negrita (≈), con emoji de bandera delante.
- Mapas: «JAPAN», «NPB», «UNITED STATES» en mayúsculas sans-serif, más el logo MLB.
- Tarjetas de jugadores: «BLUE WAVE / ICHIRO», «LIONS / MATSUZAKA», «GIANTS / MATSUI» (equipo / jugador, mayúsculas).
- Cierre: «For more sports and geopolitics, decoded», «S/P», botones «Subscribe», «Subscribed», «Join».
- Una sola familia sans en todo el reel (≈); sin serif ni script.

## 4) Subtítulos / texto en pantalla
- Subtítulos que reproducen la voz literal durante todo el reel, desde los 0–1 s.
- Posición: centrado horizontal, tercio inferior (en el cuadro ≈ y 238–246 de 320, es decir ≈ 75 % de la altura), fuera de la zona de iconos de IG solo parcialmente.
- Estilo del cuadro: texto blanco pequeño sobre caja negra translúcida de esquinas casi rectas; una línea corta (3–5 palabras visibles, p. ej. «Japanese baseball»).
- No resalta palabras clave ni cambia de color en el subtítulo (sin karaoke visible en el cuadro).
- Texto gráfico aparte de los subtítulos: etiquetas de mapa (JAPAN, NPB, UNITED STATES), etiquetas de comparación con bandera (00:25–00:44) y tarjetas de jugadores (00:44–00:55).
- Cierre 00:56–00:58: «For more sports and geopolitics, decoded» + «S/P».

## 5) Fondos y texturas
- Metraje de archivo en blanco y negro con grano y desgaste propios de la película.
- Cromos de béisbol impresos (azul y rojo, textura de papel/impresión) a pantalla completa.
- Mapas 2D animados de Japón y Estados Unidos con las ligas NPB y MLB (fondo plano, estilo infográfico).
- Pantalla final minimalista oscura con branding.
- Sin texturas añadidas por el editor (no se describen grano, ruido ni vidrio superpuestos).

## 6) La persona
- No aparece ninguna persona hablando a cámara: es una voz en off sobre archivo.
- Los jugadores que se ven son de archivo (metraje y cromos); en el cuadro visible, jugador de cromo recortado en encuadre medio de cintura hacia arriba, a pantalla completa.
- Sin recorte de silueta, sin filtros ni corrección de color aplicada sobre las personas; el aspecto viene del propio archivo.
- Para TPL: este estilo no sirve para hablante a cámara; el equivalente es sustituir al presentador por archivo + voz.

## 7) Elementos gráficos
- Mapas 2D animados Japón ↔ EE. UU. con las etiquetas de liga (00:03–00:24).
- Interfaz de tarjetas de comparación: dos cajas de video lado a lado que se desplazan, con clips que cambian dentro de la caja a 00:27, 00:28, 00:30, 00:32 (batting) y 00:36, 00:38, 00:40, 00:42 (pitching).
- Etiquetas con bandera: «🇺🇸 POWER» vs «🇯🇵 CONSISTENCY» (00:25–00:33); «🇺🇸 VELOCITY» vs «🇯🇵 CRAFTINESS» (00:34–00:44).
- Tarjetas de jugadores (Ichiro, Matsuzaka, Matsui, Nomo) que viajan de Japón a las ciudades de MLB sobre un mapamundi (00:44–00:55).
- Pantalla final con cursor animado que hace clic en «Subscribe», campana de notificación (00:56–00:58).
- Solo un elemento gráfico principal a la vez; no se describen elementos apilados.

## 8) Movimiento y animación
- Mapas animados: las rutas y tarjetas se desplazan sobre el mapa (viajes de jugadores Japón → MLB).
- Tarjetas de comparación con desplazamiento lateral (side-scroll) de las cajas de video.
- Cursor animado del cierre: clic en Subscribe → cambia a «Subscribed».
- El metraje de archivo no lleva zoom ni cámara lenta añadidos que vidIQ describa; el movimiento viene del propio material.
- Sin datos de curvas de easing ni duraciones de animación; no inventar: medir con cuadros si se quiere replicar.

## 9) Transiciones
- Casi todo corte directo (hard cut) entre clips de archivo.
- Entrada de mapas y tarjetas con animación propia (desplazamiento), no con efecto de transición genérico.
- Cierre en una sola toma continua, sin corte (00:56–00:58).
- Sin fundidos, glitch ni whip descritos.

## 10) Ritmo (cambios por segundo, duración de escenas)
Cortes listados por vidIQ:
- 00:00–00:03: 00:01, 00:02 → 2 cortes.
- 00:03–00:24: 00:05, 00:07, 00:12, 00:13, 00:16, 00:20, 00:22 → 7 cortes.
- 00:25–00:33: 00:27, 00:28, 00:30, 00:32 → 4 cortes.
- 00:34–00:44: 00:36, 00:38, 00:40, 00:42 → 4 cortes.
- 00:44–00:55: 00:46, 00:47, 00:49, 00:52 → 4 cortes.
- 00:56–00:58: 0 cortes (una toma).
- Total: 21 cortes en 59,5 s → ≈ 0,35 cortes/s, es decir un cambio cada ≈ 2,8 s de media; en el cuerpo (00:00–00:55) ≈ 0,38/s.
- Duración de toma típica 1–2 s en los tramos de comparación y hasta 5 s (00:07–00:12) en los de historia.
- Estructura: gancho 0–3 s con el titular hablado, historia 3–24 s, batting 25–33 s, pitching 34–44 s, entrenamiento + impacto 44–55 s, cierre 56–58 s.
- La voz empieza en el segundo 0, sin silencio previo.

## 11) Sonido y SFX
- Voz en off clara, informativa y a ritmo constante, desde el segundo 0.
- Ambiente de estadio/béisbol de época durante los primeros 1–2 s.
- Cama musical: beat instrumental hip-hop/synth de tempo medio, por debajo de la voz durante todo el reel.
- SFX descritos por vidIQ: solo el ambiente inicial; no se describen whooshes ni clics en las tarjetas (no confirmado).
- Cierre: voz «For more sports and geopolitics, subscribe to S/P.» con tono más animado.
