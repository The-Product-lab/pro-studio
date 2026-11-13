# DfM7ZyruNRU — estudio visual (luminoso)

Reel promocional de una competencia de edición («Frame War by EarnEdits»), 23,6 s, 28 cortes (71,2/min), plano medio 0,81 s. Aquí no habla nadie a cámara: es **motion puro**, con siluetas, renders 3D, imágenes de IA y tipografía cinética. Los cuadros muestreados son 4:3 (360×270), así que las medidas en % salen de ese cuadro.

## 1. Sistema en una frase
Siluetas y objetos **iluminados desde adentro** (mapa de calor, verde neón, oro) sobre fondos casi negros, cada escena con **una palabra gigante** que se queda detrás del sujeto, y por encima una línea pequeña en sans blanca que escribe la frase palabra por palabra.
**Se reconoce en 1 s por** la silueta humana en degradado térmico rojo→naranja→crema con borde de luz, la palabra serif roja enorme detrás de la cabeza y el fondo negro con viñeta.

## 2. Color
Tiene grade de cine oscuro y desaturado (luz media 0,24, contraste 0,24, saturación media 0,12). Todo el color vive en el sujeto. Cada bloque tiene **un solo acento**, que cambia de bloque a bloque (rojo → verde → oro → carmesí → verde).

| HEX | % | Rol | Dónde |
|---|---|---|---|
| #041005 | 27,9 | Fondo base, negro verdoso | Bloque «$250/FREE» (4–12 s) y cierre CTA (20–23,6 s) |
| #052B18 | 19,8 | Fondo verde botella con degradado (más claro arriba) | Arriba del cuadro en 4–12 s y 20–23 s |
| #1E1916 | 11,4 | Negro cálido / carbón | Fondo del gancho (0–2,2 s) y bloque «NOT» |
| #4C564B | 10,8 | Gris verdoso de transición | Barrido 3,8–4,3 s (crema → gris → verde) y nubes de «LIVE» |
| #DAD0B9 | 9,4 | Crema / hueso: fondo claro y texto claro | Fondo del bloque «Frame War» (2,3–3,9 s), palabra «MONTHS», «FREE» |
| #402C28 | 9,4 | Sombra café rojiza | Penumbra del bloque «NOT» y «TALENT» |
| #888F7F | 7,9 | Gris medio | Nubes y cielo de «LIVE» (15,3–20 s) |
| #C9572C | 3,4 | Acento naranja-rojo térmico | Silueta del gancho, salpicaduras de oro en «TALENT» |

Acentos que no salen en la paleta medida porque ocupan poco: rojo serif ~#B3202A («THREE», «NOT»), granate ~#9A0F14 («Frame War»), verde neón ~#7CF08A (puño, «true?», «EarnEdits»), carmesí rosado ~#A8325A («LIVE»).

**Tratamiento de la imagen**
- **Viñeta** fuerte y constante en todo el reel; en los bloques verdes es un degradado vertical (verde arriba, negro abajo).
- **Glow/bloom**: sí. La silueta térmica tiene un borde crema de 3–5 px que brilla, el puño verde tiene resplandor propio, «EarnEdits» del CTA tiene halo verde y el trofeo de «TALENT» tiene bloom dorado.
- **Halation**: leve, solo en las altas luces doradas de «TALENT».
- **Grano**: fino y constante, casi invisible, más notorio en «NOT» y «LIVE» (fotos de IA).
- **Aberración cromática**: sí, en dos sitios. A 0,00 s la silueta blanca tiene un halo cian/rojo en el borde, y a 2,22 s hay un glitch RGB.
- **Scanlines/CRT**: sí, solo como transición. A 0,00 s y 2,22 s hay líneas horizontales rojo/azul en el tercio superior, cada una durante 1 cuadro.
- **Desenfoque de profundidad**: muy usado. Las palabras de fondo se desenfocan («FREE» a 10,5–11,5 s, «Frame War» al salir), y se ve confeti desenfocado al frente y atrás.
- **No tiene** papel, semitono, polvo/rayones ni light leak.

## 3. Tipografía
| Rol | Aspecto | Tamaño (% ancho) | Color / efecto | Google Fonts |
|---|---|---|---|---|
| Palabra gigante de fondo (THREE, NOT, LIVE) | Serif de alto contraste, didona/transicional, MAYÚSCULAS, peso bold, normal, tracking 0 | THREE ~85 %, NOT ~80 %, LIVE ~65 % | Rojo o carmesí plano, sin borde ni sombra; queda **detrás** del sujeto | **Bodoni Moda** Bold / Playfair Display Black |
| Palabra gigante clara (MONTHS, FREE) | Serif ancha con remates finos, MAYÚSCULAS, semibold | MONTHS ~85 %, FREE ~55 % | Crema #DAD0B9, con sombra suave negra y difusa en FREE | **Cormorant SC** Bold / Gloock |
| Palabra metálica (TALENT, $250) | Serif bold MAYÚSCULAS con textura | TALENT ~90 %, $250 ~55 % | Oro metálico con bloom (TALENT); «$250» gris verdoso semitransparente detrás del puño | Bodoni Moda Black + relleno degradado oro |
| Logotipo «Frame War» | Sans geométrica bold, minúsculas con capital, tracking apretado (−2 %) | ~45 % al entrar, ~110 % en el empuje final (se sale del cuadro) | Granate #9A0F14 sobre crema, con trazo a mano encima | **Poppins** Bold / Outfit Bold |
| Línea de narración pequeña («where Editors compete to win», «for the past», «we're looking for») | Sans geométrica regular, minúsculas, la palabra clave en semibold | Altura de letra ~3 % del ancho; la línea ocupa 30–40 % | Blanco 85 %; la palabra que entra empieza en gris 40 % y sube a blanco | **Poppins** Regular/Medium |
| Pregunta («sounds too good to be true?») | Poppins Regular, centrada, ~4,5 % de altura | Línea ~80 % del ancho | Blanco, con la última palabra «true?» en verde neón y un subrayado a mano blanco bajo «too good» | Poppins |
| Firma «by EarnEdits» | Poppins Medium, pequeña | ~15 % del ancho | Gris carbón | Poppins |
| CTA de cierre («Comment "EarnEdits"», «we'll send you the participation link.») | Serif bold pequeña con terminaciones marcadas, 2 líneas centradas, interlineado 1,1 | ~20–25 % del ancho | Blanco; «EarnEdits» en verde neón con glow | **Young Serif** / DM Serif Display |

La regla es una pareja fija: **serif gigante como textura de fondo + Poppins pequeña para leer**. Nunca hay dos palabras gigantes a la vez.

## 4. Composición
- **Retícula**: sujeto centrado en el eje vertical. La palabra gigante va en el tercio superior (y 10–45 % del alto). La línea pequeña va arriba a la izquierda (x ≈ 15 %, y ≈ 23 %) o encima de la palabra gigante (y ≈ 12 %, centrada).
- **Sujeto**: ocupa el 50–65 % del ancho y entra desde el borde inferior. Nunca tiene pies ni base: siempre está cortado por abajo, de cintura o pecho hacia arriba.
- **Capas, de atrás hacia adelante**: fondo oscuro con viñeta → palabra gigante → sujeto (recortado; tapa entre el 30 y el 50 % de la palabra) → partículas/confeti → línea pequeña de narración (siempre libre, nunca tapada).
- **Márgenes**: la palabra gigante puede sangrar por los dos lados (THREE, TALENT, Frame War al final). La línea pequeña respeta un margen de ~12–15 %.
- La HUD de cámara en «LIVE» ocupa el cuadro completo con un margen de ~3 %.

## 5. Elementos gráficos
1. **Trazo a mano blanco** (0,1–1,4 s): línea de unos 3 px, sin relleno, con terminación redondeada. Entra como write-on (se dibuja), da la vuelta a la cabeza a la altura de la frente (0,5–0,6 s), cruza el cuadro y sale por abajo a la izquierda (0,7–1,4 s). Marca el «loop» de «for the past».
2. **Garabatos granate** (2,3–3,5 s): curvas a mano de 1–2 px que crecen desde las esquinas. Además hay un **swoosh grueso granate** (~6 px) que se escribe sobre «Frame» en 4–5 cuadros (2,47–2,57 s), primero como punto, luego tilde, luego arco, y se vuelve a dibujar sobre «War».
3. **Subrayado a mano blanco** bajo «too good» (10,5–11,5 s): trazo de unos 2 px, ligeramente curvo.
4. **Confeti 3D** multicolor (azul, naranja, rosa, crema): entra en ráfaga en 1 cuadro (4,72 s), cae con desenfoque de movimiento y profundidad de campo (piezas al frente desenfocadas y grandes, al fondo nítidas y pequeñas). Se repite en «TALENT».
5. **Billetes de dólar** volando con desenfoque fuerte al frente, en «NOT» (12–13,9 s).
6. **HUD de cámara de video** (15,3–20 s): «● REC» arriba a la izquierda, esquinas en L blancas, retícula de enfoque central (cuadrado de esquinas), timecode «00:00:20:05» abajo al centro, batería verde y «25FPS» arriba a la derecha, «MENU» abajo a la derecha. Todo blanco, delgado, de 1–2 px. Debajo, texto legal de 3 líneas a ~1,5 % de altura.
7. **Barras de scanline RGB** (0,00 y 2,22 s): banda horizontal de líneas rojo/azul en el 30 % superior, durante 1 cuadro.
No hay cajas, tarjetas, píldoras ni íconos planos.

## 6. Apoyos
Cada idea tiene un **objeto-símbolo** propio, y aparece uno nuevo cada ~2–4 s:
- «for the past three months» → silueta térmica que gira la cabeza y baja la mirada: tiempo y desgaste.
- «Frame War by EarnEdits» → logotipo con trazo a mano.
- «where Editors compete to win $250» → puño 3D verde (estilo clay/glossy) que sube con confeti, y una medalla que cuelga.
- «entry is completely FREE» → trofeo 3D de cristal verde con base de metal, girando sobre su eje.
- «sounds too good to be true?» → el trofeo desenfocado de fondo, con la pregunta encima.
- «we're NOT here for money» → personaje de IA con gafas de esquí naranjas y chaqueta negra con logo «E», con billetes volando.
- «we're looking for TALENT» → trofeo dorado sostenido en alto, manos alrededor que lo buscan, confeti.
- «Frame War November LIVE» → caballero oscuro de IA que levanta una corona frente a una catedral gótica, con HUD de cámara.
- CTA → texto solo sobre verde oscuro.

## 7. Persona
- No sale una persona real a cámara. El «protagonista» es una **silueta recortada** (de busto, un tercio de espaldas) convertida en **mapa de calor**: rojo #C9572C en el centro, naranja, amarillo y crema en los bordes, con contorno luminoso.
- La silueta evoluciona: blanca plana con aberración (0,0 s) → térmica roja (0,2–1,0 s) → térmica más clara y crema conforme gira (1,5–2,0 s) → rosada y desaturada (2,1 s) → desenfocada y anaranjada como fondo del logo (2,3–3,5 s).
- Fondo detrás: carbón #1E1916 con viñeta. Luz: la emite la propia silueta, no hay luz de escena.
- Los personajes de IA de «NOT» y «LIVE» van en B/N casi completo. El único color en «NOT» es el naranja de las gafas; en «LIVE», la capa roja del caballero.

## 8. Movimiento y transiciones
- **Cámara**: hay deriva y push-in suaves y continuos en casi todos los planos. El empuje más largo es el de «Frame War», que crece de ~45 % a ~110 % del ancho entre 2,5 y 3,9 s con ease-in y termina saliendo del cuadro por abajo. En «LIVE» hay un leve zoom lento; en «NOT», una deriva lateral. No hay temblor.
- **Entradas de texto**:
  - Palabra gigante: **aparece por palabra en 1–2 cuadros** (THREE a 0,7 s; MONTHS a 0,9 s), sin rebote. Sale **deslizándose hacia abajo** detrás del sujeto (1,5–1,6 s: «THREE MONTHS» baja ~35 % del alto en 3 cuadros, con ease-in).
  - Línea pequeña: **write-on palabra por palabra**. Cada palabra nueva entra en 2–3 cuadros con opacidad 40 %→100 % y un leve desenfoque que se va. Ejemplo: «where» 3,72 → «Editors» 4,07 → «compete» 4,42 → «to» 4,82 → «win» 5,12, con un desfase de ~0,3–0,35 s por palabra.
  - «FREE»: entra desenfocada y se enfoca (9,0–9,5 s). Luego sale con un desenfoque lateral de movimiento hacia la izquierda mientras entra «sounds…» (10,0 s).
  - CTA: fade + desenfoque → nítido, en 0,3 s.
- **Sujeto 3D**: el puño **sube desde abajo** con ease-out (de y 95 % a y 55 % entre 3,9 y 4,7 s, unos 20 cuadros) y la ráfaga de confeti lo acompaña. El trofeo gira en Y (7,5–8,5 s).
- **Transiciones**:
  - 0,07 y 0,27 s: **flash/glitch** (silueta blanca con aberración y scanlines → térmica).
  - 2,07–2,27 s: cambio de color de la silueta + **glitch RGB de 1 cuadro** + cuadro de silueta desenfocada naranja → **flash a crema**.
  - 3,47–4,27 s: el logo hace push y cae, el fondo se **funde de crema a gris verdoso y a verde oscuro** (cross-dissolve de ~0,5 s) y el puño ya asoma.
  - 7,47 s: corte seco a trofeo.
  - 9,0 / 9,2 s: dos cortes de enfoque en «FREE».
  - 12,0–13,93 s: **ráfaga de cortes cada ~0,2–0,27 s** (siete cortes) entre variantes de «NOT» con billetes que barren el cuadro (los billetes hacen de wipe). Luego, corte a «TALENT».
  - 15,33 s: corte con flash a «LIVE» con HUD.
  - 20,0 s: corte a verde oscuro del CTA.

## 9. Subtítulos
No hay subtítulos de voz al estilo karaoke. La **línea pequeña de narración** cumple ese papel:
- arriba a la izquierda o centrada en el tercio superior (y 12–25 %);
- Poppins, ~3 % de altura;
- se construye palabra por palabra, hasta 5 palabras en la línea;
- la palabra clave se marca de tres maneras: con peso semibold («Editors»), cambiando de color a verde neón («true?») o pasando a palabra gigante serif («THREE», «FREE», «NOT», «TALENT», «LIVE»).

## 10. Reglas del sistema
1. **Una palabra gigante por escena**, serif MAYÚSCULAS, de 55–90 % del ancho, siempre **detrás** del sujeto, que tapa entre el 30 y el 50 %.
2. La frase se lee en **Poppins pequeña**, que se escribe palabra por palabra (~0,3 s por palabra, cada una de gris a blanco).
3. **Fondo casi negro con viñeta**, de carbón o verde botella; luz media ≈0,24.
4. **Un solo acento por bloque**; el color está en el sujeto, nunca en el fondo.
5. El sujeto **brilla desde adentro** (térmico, neón, oro) con un borde de luz de 3–5 px.
6. El sujeto entra o se ancla **desde el borde inferior** y siempre va cortado por abajo.
7. Hay **partículas con profundidad de campo** (confeti, billetes) al frente y atrás en los momentos de recompensa.
8. Los **trazos a mano** (blancos o granate, 1–6 px) se escriben sobre el sujeto o el logo para subrayar o hacer un loop.
9. Las transiciones son de **glitch RGB/scanline de 1 cuadro, flash, fundido de color o desenfoque**; sin cortinas ni deslizamientos de plano.
10. La **cámara siempre respira** (push-in o deriva lenta) y nunca hay un cuadro congelado.
11. En la frase de tensión («NOT for money») hay una **ráfaga de cortes de ~0,2 s**; el resto de planos dura 1,5–4,7 s.
12. **El cierre va solo en texto**, serif pequeña sobre verde oscuro, con la palabra de acción en verde neón con glow.

## 11. Qué NO hace
- No hay persona real hablando a cámara ni subtítulos de voz.
- No hay cajas, tarjetas, píldoras, íconos planos, emojis ni flechas.
- No usa fondos blancos salvo el bloque crema del logo.
- No hay rebote elástico ni overshoot: todo es ease-out o ease-in seco.
- No pone dos palabras gigantes a la vez ni mezcla tres colores de acento en un bloque.
- No hay temblor de cámara ni whip pan.
- No usa texturas de papel, semitono, polvo ni light leaks.
- No pone texto delante de la cara del sujeto, salvo la palabra gigante, que va detrás.

## 12. Tabla de momentos
| Segundo | Qué se ve | Recurso |
|---|---|---|
| 0,00–0,07 | Silueta blanca plana, fondo azul con scanlines | Flash/glitch de entrada, aberración cian-rojo |
| 0,07–0,27 | Silueta blanca sobre gris, primer trazo a mano | Write-on del trazo blanco |
| 0,27–0,87 | Silueta térmica roja, el trazo rodea la cabeza, «for the past» | Mapa de calor + glow de borde, línea Poppins palabra por palabra |
| 0,87–1,07 | Aparece «THREE» rojo detrás, «MONTHS» crema | Palabra gigante en 1–2 cuadros, detrás del sujeto |
| 1,07–1,27 | La silueta gira la cabeza y baja la mirada | Animación del recorte; tapa ~40 % de la palabra |
| 1,27–1,53 | Silueta de perfil, más clara | Cambio de gradiente térmico a crema |
| 1,53–2,07 | «THREE MONTHS» se desliza hacia abajo y sale | Salida con ease-in detrás del sujeto |
| 2,07–2,27 | Silueta rosada de espaldas → glitch RGB → silueta naranja desenfocada | Glitch de 1 cuadro + desenfoque |
| 2,27–3,47 | Fondo crema, «Frame War» granate se escribe con swoosh, «by EarnEdits» | Trazos a mano granate, push-in del logo |
| 3,47–3,67 | El logo crece y se sale de cuadro | Push-in con ease-in, desenfoque |
| 3,67–3,87 | El logo cae, entra «where» | Fundido de fondo crema → gris |
| 3,87–4,07 | Fondo gris verdoso, asoma el puño verde | Cross-dissolve de color |
| 4,07–4,27 | «where Editors», fondo se oscurece a verde | Write-on palabra por palabra |
| 4,27–4,87 | El puño sube desde abajo, «compete», ráfaga de confeti | Ease-out de subida, confeti con profundidad de campo |
| 4,87–7,47 | «to win», «$250» gris detrás del puño, medalla, «guess who?» | Palabra gigante detrás, confeti, deriva |
| 7,47–9,00 | Trofeo 3D de cristal verde gira, «entry is FREE completely» | Giro en Y, palabra gigante desenfocada |
| 9,00–9,20 | «FREE» desenfocada | Cambio de enfoque |
| 9,20–12,00 | «FREE» nítida → se barre a la izquierda; «sounds too good to be true?» sobre el trofeo desenfocado | Desenfoque de movimiento lateral, «true?» en verde, subrayado a mano |
| 12,00–12,27 | Personaje con gafas naranjas, «NOT» rojo, billetes | Corte rápido, billetes como wipe |
| 12,27–12,47 | Variante de «NOT» | Ráfaga de cortes |
| 12,47–12,73 | Variante de «NOT», billetes al frente | Ráfaga |
| 12,73–12,93 | «we're NOT … for money» | Ráfaga |
| 12,93–13,13 | Variante de «NOT» | Ráfaga |
| 13,13–13,47 | Billetes barren el cuadro | Ráfaga |
| 13,47–13,73 | Personaje, billetes | Ráfaga |
| 13,73–13,93 | Salida del bloque «NOT» | Ráfaga |
| 13,93–15,33 | Trofeo dorado en alto, manos, «we're looking for TALENT» | Oro con bloom/halation, confeti |
| 15,33–20,00 | Caballero levanta corona frente a catedral, «LIVE» carmesí, HUD REC | HUD de cámara, B/N con capa roja, zoom lento |
| 20,00–23,60 | Verde oscuro: «Comment "EarnEdits"» → «we'll send you the participation link.» | Serif pequeña, palabra de acción en verde neón con glow, fade + desenfoque |
