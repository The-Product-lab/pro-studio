# DdKZ5oBpPCW — «If your Photos feel flat» (tutorial Adobe Stock + Premiere, #adobepartner)

Ficha visual sacada de los cuadros (hoja 0,5 s, gancho a 10 cps, cortes a 20 cps). 46,0 s · 42 cortes medidos · 54,8 cortes/min · plano medio 1,07 s (mín 0,07 – máx 6,7 s).

Nota de lectura: los «cortes» medidos en 0,07 · 0,23 · 0,40 · 0,83 · 2,23 · 3,07 · 3,50 no son cambios de toma. Son **barridos de luz/sombra** (overlays de sombra y luz en modo multiply/screen) que pasan por encima de la misma foto, más entradas de texto. El detector los cuenta como cortes porque cambia la luz de golpe. Al reel le basta una sola foto para parecer muy cortado.

## 1. Sistema en una frase
Una foto de archivo en blanco y negro (campesinos en un trigal, años 30–40) que **respira con luz**: sombras de ventana y franjas de sol cruzan el cuadro, la foto se acerca o se aleja y cambia de recorte, y encima va un **titular editorial de revista** (serif de cuerpo grande, color oliva, con una flecha roja de pincel). Esa foto se intercala con cara a cámara, iconos de Adobe y pantallazos de Premiere/Stock.
**Se reconoce en 1 s por** tres cosas: la foto sepia sin color, la palabra gigante en serif oliva «Photos» y la flecha roja a mano que apunta al niño.

## 2. Color
| HEX | % | Rol | Dónde |
|---|---|---|---|
| #1D201D | 22,7 | negro verdoso de sombras | ropa, sombras de la foto, fondo de las cintas de texto y de la interfaz de Premiere |
| #625E52 | 15,7 | medio tono cálido (sepia gris) | trigal, cuerpo de la foto |
| #3C3E38 | 14,5 | sombra media / overlay de sombra multiply | franjas diagonales de sombra que cruzan el cielo |
| #817E74 | 14,3 | gris pardo | cielo en la zona sombreada, paja |
| #ACA397 | 11,5 | crema medio | cielo iluminado |
| #020404 | 9,6 | negro puro | UI de Premiere/Stock, fondo del icono St |
| #DAD8CC | 9,3 | **papel crema** (altas luces) | cielo cuando pasa la franja de luz; fondo del titular |
| #395391 | 2,3 | **único color vivo**: azul | camisa del presentador, icono Pr (#2B2A8C aprox. con letras lila #9999FF), botón Download azul |
Acentos que no salen en la paleta porque ocupan poco: **rojo sangre seco ~#8E1B1B** (flecha de pincel), **oliva oscuro ~#3B3A12** (palabra «Photos»).

- Armonía: **monocroma cálida (sepia-gris) + un solo acento rojo**. El azul solo vive en la toma del presentador y en la UI, nunca sobre la foto.
- Tratamiento de la foto: blanco y negro con un poco de calor (saturación medida 0,07), contraste bajo (0,25) y luz media 0,35. Negros levantados a verde-negro (#1D201D, nunca 000). Viñeta suave en las esquinas y abajo. Grano fino de papel/película, constante, con polvo y rayitas sueltas (se ven en el cielo a 14 s y 27 s). Sin halation, sin bloom, sin aberración cromática, sin scanlines.
- Luz: overlays de **sombra de ventana/persiana** (diagonales anchas, 25–40 % del ancho del cuadro, a ~30–40°) en **multiply**, y **light leaks blancos verticales** (franjas crema que suben la luz del cielo) en **screen/luz suave**. Ambos se deslizan despacio de lado a lado y son el «movimiento» principal del reel.
- Presentador: color normal, luz cálida de cuarto (lámparas ámbar al fondo, LED azul), sin grade especial. Es el contraste de temperatura frente a la foto fría y gris.

## 3. Tipografía
| Rol | Ejemplo | Familia vista | Google Fonts | Peso / ancho | Caja | Tamaño (% ancho cuadro) | Color / tratamiento |
|---|---|---|---|---|---|---|---|
| Titular héroe | «Photos» | serif de transición de revista, contraste medio, «h» y «t» con remates cortos (tipo GT Super / Canela Text) | **Fraunces 600** (o Playfair Display 600) | semibold, ancho normal | Título (1.ª mayúscula) | palabra ~75 % del ancho; altura de caja ~9 % del alto | oliva oscuro ~#3B3A12, plano, sin trazo ni sombra |
| Titular de apoyo | «If your» / «feel flat» | grotesca condensada-normal bold | **Inter Tight 700** / Archivo 700 | bold, un poco condensada | minúscula | ~7 % de alto de x-height; línea ~40 % del ancho | negro #1D201D, plano |
| Etiqueta de concepto (cinta) | «feel cinematic.» · «integrating assets» · «that add depth» | grotesca bold redondeada | **Inter Tight 700** | bold | minúscula, con punto final | 45–60 % del ancho | blanco #F2F0EA sobre cinta negra |
| Etiqueta de concepto serif | «dust» · «dust overlay.» · «shadow overlay» | serif de libro (tipo Iowan/Georgia) | **Source Serif 4 600** (o Libre Caslon Text) | semibold | minúscula | 50–80 % del ancho | blanco crema sobre cinta negra |
| Subtítulo | «THIS TRICK» · «CAN INSTANTLY» | grotesca condensada bold | **Archivo Narrow 700** / Inter Tight 800 | bold, condensada | MAYÚSCULAS, tracking +2 % | ~2,6 % del alto; línea de 1–3 palabras = 20–30 % del ancho | blanco con caja negra translúcida (~60 %), radio 4 px |
| Marca de patrocinio | «#adobepartner» | grotesca regular | Inter 400 | regular | minúscula | ~2 % del alto | blanco al ~60 %, fijo en y ≈ 71 % del alto, centrado |

Apilado del titular (0,6–2,2 s): 3 renglones con interlineado apretado (≈0,9): «If your» alineado a la izquierda en x≈13 %, «Photos» desde x≈13 % hasta x≈88 %, «feel flat» **alineado a la derecha** en x≈88 %. Es una diagonal tipográfica: entra arriba a la izquierda y sale abajo a la derecha, apuntando a la flecha.

## 4. Composición
- Vertical 9:16. La foto llena el cuadro (sangrado completo), recortada cada vez distinto (plano general → medio → primer plano del niño).
- **Tercio superior (y 10–35 %)**: cielo vacío de la foto = el lugar del texto. Todo titular y toda cinta van ahí, nunca sobre caras.
- **Tercio medio (y 35–70 %)**: los personajes (el niño con gorra en x≈45 % y el bebé a su izquierda). La flecha roja une el texto con la cabeza del niño.
- **y ≈ 71 %**: «#adobepartner» fijo. **y ≈ 80 %**: subtítulo.
- Márgenes laterales ~10–12 %. La cinta de concepto arranca en x≈10 % (alineada a la izquierda) o se centra en las tomas cerradas.
- Delante/detrás: todo el texto va **delante** de la foto. Los overlays de sombra van por encima de foto y texto (la franja oscura también tapa el titular, ver 2,0–2,3 s); así la luz parece real, sobre el papel. Nada va detrás de la persona.
- Presentador: plano medio corto centrado, ojos en y≈20 %, sin aire arriba. El icono St (cuadro ~30 % del ancho) va arriba a la izquierda, **detrás de la cabeza**: el presentador lo tapa en parte, con integración de profundidad.

## 5. Elementos gráficos
1. **Flecha roja de pincel** (0,2–2,2 s; vuelve 12–13,9 s): trazo con textura de brocha seca, grosor ~1,8 % del ancho, curva en S de (x 18 %, y 32 %) a (x 48 %, y 52 %), punta abierta. **Se dibuja con write-on**: 0,2 s es un punto, 0,3 s un trazo corto, 0,5 s llega a la punta (≈4–5 cuadros a 10 cps, ease-out). Sale con corte seco.
2. **Palabra «Photos»**: entra con **desenfoque + barrido de izquierda a derecha** letra a letra (0,3 s «P» borrosa → 0,5 s «Phot» → 0,68 s «Photos» nítida). Duración ~0,4 s, desfase ~0,07 s por letra, blur de ~12 px a 0. Sin escala ni rebote.
3. **«If your» / «feel» / «flat»**: aparición palabra a palabra al ritmo de la voz, por corte (0 cuadros de animación). «If» 0,1 s → «your» 0,3 s → «feel» 0,73 s → «flat» 0,9 s.
4. **Cinta negra de etiqueta** (desde 2,4 s): rectángulo #1D201D casi opaco, con bordes **ásperos, como impresos o de cinta de máquina Dymo** (los bordes tienen grano y no son rectos del todo), alto ~6 % del cuadro, ancho fijo desde el inicio (la caja aparece **vacía y completa** primero, 2,4–2,5 s; ver 13,93–14,03 s). Luego el texto se escribe **palabra a palabra dentro de la caja ya puesta** («feel» 2,6 s → «feel cinematic.» 2,9 s). Sale por corte junto con el plano. Entra en un cuadro, sin easing.
5. **Icono Adobe Stock «St»** (3,9–7,2 s): cuadrado de esquinas redondeadas (radio ~18 %) negro-azul #0B1220 con «St» blanco. Entra **de izquierda/arriba con escala y overshoot**: 4,0 s asoma recortado por el borde/cabeza → 4,05 s 80 % → 4,15 s 105 % → 4,2 s 100 %. Son ~5 cuadros con rebote suave. Leve rotación de entrada (~-5°). Queda detrás de la cabeza.
6. **Icono Premiere «Pr»** (16,8–17,1 s): mismo sistema, azul-morado #1E1A5E con «Pr» lila. Entra con **pop de escala** en el centro de la pantalla de UI y luego deriva hacia la derecha/arriba (~6 % del ancho en 0,3 s). Entra en ~2–3 cuadros.
7. **Overlays de sombra** (multiply) y **light leaks** (screen): diagonales y franjas verticales que se desplazan lento (≈10–15 % del ancho por segundo). No tienen borde: son degradados suaves de 30–60 px.
8. **Marca de agua «Adobe Stock»** (26–29 s): texto gris claro transparente en diagonal sobre la foto. Es la muestra «sin licenciar» y forma parte del relato del tutorial.
9. Subtítulos con caja (ver 9).

## 6. Apoyos
- Cada idea abstracta lleva su **demostración literal en la misma foto**: «feel flat» = foto plana; «feel cinematic» = la misma foto con sombra; «dust overlay» = polvo y rayas encima; «shadow overlay» = franja de sombra; «before/after» = foto sin y con efecto.
- La marca (Adobe Stock / Premiere) = icono de app de cuerpo grande, cada vez que se nombra.
- El proceso («busqué», «licencié», «añadí») = pantallazo real de la UI con cursor y caja de búsqueda escribiéndose («Dust Overl…», «Shadow Overla…»), parámetros de Motion/Opacity y el modo de fusión **Multiply** visible a 36 s.
- Ritmo: un apoyo nuevo (cinta, icono, UI o cambio de overlay) cada **~1,1 s**. Nunca hay más de 2 s sin que algo cambie.

## 7. Persona
- Presentador (hombre, gafas de carey, polo azul #395391) en plano medio corto, centrado, a la altura de los ojos, con fondo de cuarto/estudio desenfocado (estantes, lámparas cálidas, LED azul). Color natural, sin grade de época: es el «presente» frente al «archivo».
- Aparece en 3,9–7,2 s, 22,0–23,3 s y 40,9–43,6 s (≈20 % del reel). Hace mucha mano: los gestos van hacia el icono.
- La «persona» de la foto (el niño) hace de sujeto del gancho: la flecha lo señala y los recortes siempre lo dejan dentro (de plano general a primer plano).

## 8. Movimiento y transiciones
- **Cámara sobre la foto**: deriva continua (Ken Burns) con push-in y pequeñas subidas. Entre 0 y 0,4 s la foto cambia tres veces de recorte (0,07 / 0,23 / 0,40) mientras el texto empieza: **3 jump-zooms seguidos** de primer plano a plano general (el gancho se arma «abriendo» la foto). Ahí el detector marca cortes.
- Ese push-in sobre la foto sigue **mientras entran los apoyos** (texto y flecha viajan con la foto en 1,4–2,2 s).
- **Transiciones**: todas por **corte seco**. No hay disolvencias, whips ni glitches. El cambio de «luz» lo hace el overlay que barre, no la transición. Un corte pasa de la foto (3,85 s) al presentador (3,90 s) en un cuadro, y el subtítulo sigue igual en el mismo sitio: el subtítulo hace de puente.
- Corte a la misma foto con otro recorte = jump-cut de archivo (7,23 s: del presentador a la foto general; 13,93 s: de plano general con flecha a primer plano del niño).
- UI de Premiere (15,2–21 s y 29,6–36,4 s): grabación de pantalla con **punch-in a la zona del cursor** (a 18,6 s y 34–36 s el cuadro se acerca a la caja de búsqueda y al panel de Motion) y cortes cada 0,5–1 s.
- Ráfaga de cortes 37,9–38,6 s (cada 0,17 s): antes/después alternando foto plana ⇄ foto con sombra. Es el **parpadeo comparativo**.
- Ningún temblor de cámara ni shake.

## 9. Subtítulos
- Siempre presentes (también sobre la UI), **1–3 palabras**, MAYÚSCULAS, grotesca condensada bold blanca, caja negra translúcida con radio pequeño, centrado en x 50 % y y ≈ 80 %.
- Tamaño pequeño (~2,6 % del alto): es lectura de apoyo, no decoración. Cambian a ritmo de sílaba o palabra y **cruzan los cortes sin moverse**.
- La palabra clave **no va en el subtítulo**: sube al tercio superior como **cinta de concepto** (blanca sobre negro, más grande, a veces en serif). Esa es la marca de la palabra clave.

## 10. Reglas del sistema
1. Una sola foto de archivo B/N carga el reel: se vuelve a ella con otro recorte, otra luz u otro overlay, no con fotos nuevas.
2. El cielo vacío (tercio superior) es la zona del texto; caras y cuerpos van del 35 % hacia abajo.
3. El gancho es un **titular de revista en 3 renglones en diagonal**: chico/sans → GIGANTE/serif oliva → chico/sans alineado a la derecha, con una flecha roja de pincel dibujada (write-on de 0,3 s) hacia el sujeto.
4. La palabra héroe entra con desenfoque y barrido letra a letra (~0,4 s); el resto, palabra a palabra por corte, al ritmo de la voz.
5. La palabra clave se escribe en una **cinta negra de borde áspero** que aparece vacía y luego se llena palabra a palabra.
6. La luz se mueve, la toma no se corta: sombras de ventana en multiply y franjas de luz en screen barren despacio por encima de foto y texto.
7. Paleta sepia-gris con negros verdosos levantados (#1D201D) y **un solo acento rojo**; el azul solo en el presentador y la UI.
8. Grano fino, polvo y viñeta suave, siempre; nada de efectos digitales (glow, chroma, glitch).
9. Cada marca o app que se nombra = icono de app grande con pop de escala y overshoot (~5 cuadros), detrás de la cabeza si hay persona.
10. Todo cambio de plano por corte seco; el subtítulo fijo abajo cose los cortes.
11. Un apoyo nuevo cada ~1 s; antes/después = parpadeo rápido de 0,17 s.
12. El proceso se demuestra con UI real + punch-in al cursor, nunca con un esquema dibujado.

## 11. Qué NO hace
- No usa color sobre la foto de archivo, ni duotonos, ni semitono, ni halftone.
- No usa halation, bloom, glow, aberración cromática, scanlines ni glitch.
- No usa transiciones animadas (ni whip, ni zoom-transition, ni disolvencia).
- No usa shake ni temblor de cámara.
- No pone texto sobre las caras ni texto detrás de la persona (solo el icono St detrás de la cabeza).
- No hace subtítulos grandes ni karaoke de colores; la palabra clave no se colorea dentro del subtítulo.
- No pone más de un titular a la vez ni mezcla la cinta de concepto con el titular héroe en el mismo plano.
- No usa trazos ni sombras paralelas en las letras: todo es plano.

## 12. Tabla de momentos
| Segundo | Qué se ve | Recurso |
|---|---|---|
| 0,00–0,07 | Foto B/N, primer plano del niño, sombra diagonal arriba | arranque sin texto, foto con overlay de sombra |
| 0,07–0,23 | «If» aparece; la foto se abre | jump-zoom (salto de recorte) + palabra por corte |
| 0,23–0,40 | «If your», flecha empieza (punto rojo) | jump-zoom + write-on de la flecha |
| 0,40–0,83 | «Photos» entra borrosa letra a letra; flecha completa | blur-reveal en barrido; plano general |
| 0,83–2,23 | «feel» → «flat», «THIS TRICK», «CAN INSTANTLY»; franja de luz crema entra por la izquierda y cubre el cielo, luego la sombra vuelve por la derecha | light leak en screen que barre, push-in lento, titular completo |
| 2,23–2,40 | Sale el titular; primer plano del niño + bebé | corte; cinta negra vacía aparece |
| 2,40–3,07 | «feel» → «feel cinematic.» en la cinta | cinta impresa que se llena palabra a palabra |
| 3,07–3,50 | Mismo plano, cambio de luz | barrido de sombra (multiply) |
| 3,50–3,90 | Cinta sigue; subtítulo «I'M PARTNERING» | deriva de la foto |
| 3,90–7,23 | Presentador; icono St entra a 4,0 s con pop y se queda detrás de la cabeza | corte seco con subtítulo puente; icono con overshoot |
| 7,23–13,93 | Foto plano general, nubes en el cielo; cintas «integrating» → «integrating assets» → «that add» → «that add depth» + flecha roja de nuevo (12 s) | plano largo (6,7 s), push-in lento, cintas en el cielo, flecha vuelve |
| 13,93–15,23 | Primer plano niño + bebé; cinta vacía → «dust» → «dust overlay.» (serif) | jump-cut de recorte; cinta serif; polvo y rayas visibles |
| 15,23–16,40 | UI negra de Premiere, ventana vacía, cursor | grabación de pantalla, corte seco |
| 16,40–16,80 | Panel de Adobe Stock (miniaturas) | punch-in a la UI |
| 16,80–17,67 | Icono Pr con pop en el centro sobre la UI, deriva arriba-derecha | icono de app con escala |
| 17,67–18,63 | Caja de búsqueda «Dust Overl…» escribiéndose | punch-in al cursor |
| 18,63–19,60 | Resultados: Titles / Video overlays (bokeh) | UI con zoom |
| 19,60–20,13 | Foto con polvo, «OPTIONS OVER» | vuelta a la foto, overlay de polvo |
| 20,13–22,07 | Foto con marca de agua «Adobe Stock» en diagonal | demostración literal (muestra sin licencia) |
| 22,07–23,30 | Presentador gesticulando | corte a cámara |
| 23,30–25,10 | Primer plano niño, cinta serif «shadow overlay» | jump-cut + cinta |
| 25,10–25,63 | UI: búsqueda «Shadow Overla…» | grabación de pantalla |
| 25,63–25,90 | Resultados de sombras | corte rápido |
| 25,90–27,13 | Foto con sombra de ventana + marca de agua Stock | overlay multiply |
| 27,13–28,67 | Misma foto, sombra se desplaza | barrido de luz |
| 28,67–29,57 | Foto, «TO EXPERIMENT» | deriva |
| 29,57–29,77 | UI grilla de sombras | corte de 0,2 s |
| 29,77–30,93 | Ficha del asset en Stock | punch-in a la tarjeta |
| 30,93–31,13 | Ficha cerrada | corte de 0,2 s |
| 31,13–31,50 | Sombra de ventana sobre negro / «I LICENSED IT» | corte |
| 31,50–33,07 | License type + botón Download azul + cursor | punch-in al botón |
| 33,07–34,17 | Download clic, «TO LEAVE» / «PREMIERE» | cursor, zoom |
| 34,17–36,43 | Panel Motion/Opacity de Premiere; Blend Mode = Multiply | punch-in progresivo a los parámetros |
| 36,43–37,93 | Foto con sombra que se desliza lenta, «GENTLY SHIFT ACROSS THE FRAME» | keyframe de posición del overlay visible |
| 37,93–38,10 | Foto plana | parpadeo antes/después |
| 38,10–38,27 | Foto con sombra | parpadeo |
| 38,27–38,43 | Foto plana | parpadeo |
| 38,43–38,60 | Foto con sombra | parpadeo |
| 38,60–39,70 | Foto plana limpia, «AND HERE'S» | antes |
| 39,70–39,87 | Foto con sombra | corte de 0,17 s |
| 39,87–40,97 | Foto con sombra, «CHECK OUT THE ADOBE STOCK» | después |
| 40,97–43,57 | Presentador, «PANEL IN PREMIERE… SUBTLE OVERLAYS» | cierre a cámara |
| 43,57–46,00 | Foto con sombra, «CAN COMPLETELY CHANGE THE FEEL OF YOUR PHOTOS» | cierre en la foto, sin titular |
