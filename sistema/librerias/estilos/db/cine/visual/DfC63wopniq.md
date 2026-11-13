# DfC63wopniq — «Netflix title sequence / light leak» (cine)

Tutorial de After Effects (en inglés) de un creador a cámara. Dura 47,17 s, con 21 cortes medidos (26,7 por minuto). El plano medio dura 2,14 s (mínimo 0,16 s, máximo 6,0 s). Luz media 0,22, contraste 0,20, saturación 0,04: casi monocromo oscuro.
Estructura: **gancho con título de cine (0–11,27 s)**, **cara (11,27–14,1 s)**, **ejemplos en pantalla completa (14,1–22,2 s)**, **cara (22,2–23,6 s)**, **captura de After Effects paso a paso (23,6–43,7 s)** y **cierre: vuelve el mismo título (43,7–47,17 s)**.

## 1. Sistema en una frase
Se abre con un título de cine (letra condensada crema con una palabra en dorado) sobre negro con textura de película. Después se «estropea» ese título para mostrar el problema y se enseña la receta con capturas reales del programa, todo amarrado por un subtítulo blanco en una píldora oscura, siempre en el mismo sitio.
**Se reconoce en 1 s por:** el negro con polvo y rayitas de película, el título condensado gigante que se sale por los bordes y deriva lento, la palabra «NETFLIX» en dorado apagado y el subtítulo pequeño centrado al 80 % de la altura.

## 2. Color
| HEX | % | Rol |
|---|---|---|
| #1A1B19 | 23,1 | Fondo base: el negro verdoso de la textura de película y del interfaz de After Effects |
| #77736F | 17,1 | Gris medio: el ruido fractal (14–20 s) y las vetas de luz (31–43 s) |
| #4B463F | 12,7 | Marrón grisáceo: la sombra del dorado, la caja de «BORING» y «RANDOM NOISE» y la textura del gancho |
| #282824 | 11,0 | Paneles de After Effects y zonas medias de la película |
| #12100E | 10,7 | Negro cálido del gancho y del cierre |
| #0A0A07 | 9,7 | Negro profundo (8,9–11,3 s y los bordes) |
| #AEA8A2 | 8,2 | Crema/gris claro: altas luces del ruido y de las vetas; cerca del crema del título (#EDE6DA aprox.) |
| #000100 | 7,5 | Negro puro (cortes a negro, fondo de los rayones blancos) |

- **Acento único:** dorado apagado, de bronce a ocre (≈ #8A6A3E a #A07B45), en «NETFLIX» y en las cajas de palabra clave. No hay otro acento de marca.
- **Excepciones de color**, solo como muestras de 0,5–0,8 s cada una: abanico de luz amarillo verdoso (#C8C27A en las puntas, 20,1–20,77 s), remolinos verde menta (#5FBF85 sobre negro, 20,77–21,43 s) y degradado naranja (#E8752A a negro, con estrellitas, 21,43–22,23 s). Son el «miren lo que se puede hacer» y se van enseguida.
- **Tratamiento de la imagen** en el gancho y el cierre: grade cálido, casi sepia, desaturado. Negros apenas levantados (no llegan a #000 en la textura). Grano fino animado, más polvo y pelusas blancas (rayitas curvas de 3–8 px) que cambian cada cuadro y rayas verticales de película (bandas oscuras de 10–20 % del ancho). Viñeta suave arriba y abajo.
- La toma de la persona tiene color natural de casa (luz cálida de techo, camiseta azul #3D4B63, gorra blanca). No lleva grade de cine: el «cine» lo ponen solo los gráficos.
- No hay halation, bloom fuerte, aberración cromática, scanlines, semitono ni light leak de color sobre la persona. El tutorial justamente enseña a hacer light leak, y el resultado se ve como vetas grises verticales (31–43 s).

## 3. Tipografía
1. **Título principal «TITLE SEQUENCE»**: mayúsculas, sans de palo seco **muy condensada**, alta, peso bold. Crema #EDE6DA. Tracking ~0 a ligeramente negativo, interlineado ~0,9. Ocupa **105–125 % del ancho** del cuadro, así que se sale por los dos lados (se lee «ITLE SEQUENC» o «LE SEQUEN»). En el primer armado (0,6–1,5 s) está al 85 %. Altura de letra ≈ 9–11 % del alto. Tiene una sombra suave oscura de 4–8 px de blur, sin trazo. Equivalente en Google Fonts: **League Gothic** (o **Antonio Bold** / **Oswald SemiBold** más condensada).
2. **Antetítulo «LOOK AT THIS»**: la misma familia condensada, crema, al ~35 % de la altura del título. Va alineado a la izquierda del bloque, encima de «TITLE».
3. **Palabra de marca «NETFLIX»**: la misma familia, algo más ancha y con tracking +5 %, en **dorado** #8F6D40. Es 1,4 veces la altura de «LOOK AT THIS» y va en la misma línea, a su derecha. Hay una sola palabra dorada por bloque.
4. **Palabra clave en caja «BORING» / «RANDOM NOISE»**: condensada bold crema, de 9–10 % del alto, dentro de un **rectángulo dorado-marrón** #6B4E2A con textura áspera (como de papel o madera), esquinas rectas (radio 0) y sin borde. Padding ≈ 0,3 veces la altura de la letra. La caja mide el 35 % del ancho con «BORING» y el 50 % con «RANDOM NOISE». Va centrada en x, a ~25–33 % de la altura.
5. **Subtítulo**: sans grotesca **black/extrabold**, mayúsculas, blanca, de 2,3–2,6 % del alto (~4 % del ancho por letra). Va sobre una píldora negra al 70–80 % de opacidad con radio ~4 px y padding de 4×8 px. Equivalente en Google Fonts: **Inter ExtraBold** / **Archivo Black** (estilo Proxima Nova Black).

## 4. Composición
- **Gancho:** bloque de título centrado en x, de 45 a 55 % de la altura. Al desenfocarse cae hacia el 60–80 % y se sale por la izquierda, abajo (2,0–8,8 s). Nada queda delante de una persona porque en el gancho no hay persona.
- **Cara:** plano medio corto frontal, ojos al ~30–35 % de la altura y cabeza al ~25 % del ancho. La persona ocupa 75–85 % del ancho. El subtítulo va encima del pecho (80 %). Las manos gesticulan delante y a veces tapan el subtítulo.
- **Captura de After Effects:** a pantalla completa, recortada a 9:16 sobre el panel que importa (Solid Settings, controles del Fractal Noise, línea de tiempo). Con punch-in, el texto del interfaz se ve al ~2–3 % del alto.
- **Subtítulo** en un ancla fija en **x = 50 % y y = 80 %**, en todo el video y sobre cualquier fondo.
- Márgenes: no se respetan en los títulos (sangran a propósito). Los subtítulos sí quedan dentro de la zona segura.

## 5. Elementos gráficos
- **Textura de película** (fondo del gancho y del cierre): negro con rayas verticales, polvo y pelusas que cambian cada cuadro, grano fino animado y una banda de imagen sepia (detalle arquitectónico: una cornisa ornamentada que entra en diagonal abajo, al 0–25 % del alto) desenfocada. El fondo deriva y se reencuadra con lentitud.
- **Flecha a mano**: trazo blanco de ~3 px, curva tipo «swoosh» que sube hacia la derecha y termina en punta abierta. Mide ~30 % del ancho y está al 35–55 % del alto. Aparece a los 3,6–3,9 s **dibujándose** (como un write-on, en ~6–8 cuadros) y señala el título. A los 8,67–8,77 s se encoge y se borra en ~3 cuadros.
- **Rayones blancos diagonales** (10,5–11,27 s): 8–10 líneas blancas finas a mano, de 2–3 px, en diagonal ~25° de abajo a la izquierda hacia arriba a la derecha, que cruzan todo el cuadro sobre negro. Tachan el título, que queda a ~40 % de opacidad detrás. Entran por corte y salen por corte.
- **Caja dorada «BORING»** (10,5–11,27 s): aparece seca, sin animación, sobre el título apagado.
- **Caja dorada «RANDOM NOISE»** (16,5–20,1 s): primero entra «RANDOM» (16,5 s) y después se alarga la caja con «NOISE» (17,0 s). Es un *word-on* palabra a palabra, al ritmo de la voz, y la caja crece de golpe.
- **Título que se arma palabra a palabra** (0–1,0 s): «LOOK» (0,0) → «AT» (0,1) → «THIS» (0,2) → «TITLE» (0,5) → «NETFLIX» (0,6) → «SEQUENCE» (0,7). Cada palabra aparece **de golpe** (corte seco, 1 cuadro), con un desfase de ~0,1–0,2 s igual al ritmo de la palabra dicha. Al armarse completo, todo el bloque se reubica (de y 18 % a 47 %).

## 6. Apoyos
- El tema se enseña con **el resultado en sí**: el título de cine es a la vez el ejemplo y el gancho.
- «Boring/less alive» → el mismo título apagado y tachado con rayones, más la caja «BORING».
- «Fractal noise» → el ruido fractal a pantalla completa (14,1–20,1 s), y «random noise» → la caja con la palabra.
- «A ton of effects» → 3 muestras de 0,66–0,8 s: abanico de luz, remolinos verdes y degradado naranja.
- Receta → capturas de After Effects, cada paso con su panel: crear un sólido, efecto Fractal Noise, Transform, quitar Uniform Scaling, Scale Width, la expresión `time*200`, Levels y modo de fusión.
- Resultado intermedio → vetas grises verticales a pantalla completa (31,43–33,47 s y 37,2–40,07 s).
- Hay un apoyo nuevo cada **~2,1 s** (al ritmo de los cortes). Fuera de 11,27–14,1 s y 22,23–23,6 s, **la cara no se queda en pantalla**: el 85 % del reel es apoyo a pantalla completa.

## 7. Persona
- Plano medio corto (de la cabeza al pecho), frontal y a la altura de los ojos, con cámara de celular fija. Lleva gorra blanca, gafas y camiseta azul.
- Fondo: su cuarto o estudio, con repisas, un televisor CRT, lámparas y luz cálida de techo, más un punto de luz azul de fondo (LED). Es profundidad real, no un fondo falso.
- Color natural, sin B/N, sin silueta y sin recorte. Sale 2 veces: 2,8 s (11,27–14,1) y 1,4 s (22,23–23,6).

## 8. Movimiento y transiciones
- **Cámara en el título:** deriva continua lenta. Entre 2,0 y 8,7 s el bloque pasa de ~85 % a ~125 % del ancho y baja (es un push-in de ~45 % en 6,7 s, lineal o con ease-in-out muy suave), y la textura se mueve con él. Mientras se mueve también entra la flecha: la cámara **sí** se mueve mientras entra un apoyo.
- **Transición firma: desenfoque de lente (defocus).** A 1,5–1,9 s el título se desenfoca (con un blur de ~8–12 px en 4 cuadros) y vuelve a enfocarse ya reencuadrado más grande (de 1,9 a 2,1 s). Es un *rack focus* que sirve de corte. Lo mismo pasa a 3,33–3,5 s (desenfoque + salto de encuadre hacia abajo) y a 8,77–8,93 s (desenfoque, con negro detrás, y reenfoque más chico y centrado: 8,92–9,07 s).
- **Cortes secos:** 11,27 (rayones → cara), 14,1 (cara → ruido), 20,1, 20,77, 21,43 y 22,23 (muestras), 23,6 (cara → captura) y todo el bloque de After Effects (26,33, 26,87, 31,43, 33,47, 34,73, 37,2, 40,07, 41,33, 42,1 y 43,7).
- **Punch-ins en la captura:** cada paso entra ya ampliado sobre el control que importa (entre 150 y 300 % sobre la interfaz). Hay pequeños reencuadres dentro del plano (23,6 → 23,65 s, sube y escala). En la línea de tiempo, el cursor del ratón se ve moverse.
- **Dentro de la captura:** el cambio de la capa negra al ruido (26,28 → 26,33 s) es un corte de un cuadro (antes → después). En 31,18–31,38 s se ve arrastrar el control Scale Width en tiempo real.
- Sin whip pan, sin temblor, sin zoom de golpe por palabra y sin transiciones de deslizamiento.
- **Cierre (43,7–47,17 s):** textura negra vacía → se vuelve a armar el título palabra a palabra, igual que en el 0 s. Cierra en bucle.

## 9. Subtítulos
- Sí, desde 1,6 s hasta el final, en **x 50 % y y 80 %** fijos.
- Llevan **1 a 3 palabras** («SEE IT?», «NOTICE», «THOSE SUBTLE», «STREAKS OF LIGHT»). Cambian por grupos al ritmo del habla, con un corte seco y sin animación.
- Sans black blanca en mayúsculas, de ~2,5 % del alto. En la cara y en After Effects llevan una píldora oscura al 75 % de opacidad. En el gancho (fondo ya negro) la píldora casi no se nota.
- **La palabra clave no se marca en el subtítulo**: la palabra importante se saca a una caja dorada grande («BORING», «RANDOM NOISE») mientras el subtítulo sigue normal debajo.
- De 0 a 1,5 s no hay subtítulo: el título que se arma hace de subtítulo.

## 10. Reglas del sistema
1. El gancho es **el resultado terminado**: los primeros 3 s muestran el efecto que se va a enseñar.
2. El título se arma **palabra por palabra en sincronía con la voz** (un corte seco por palabra, cada 0,1–0,2 s).
3. Tipo condensado gigante en crema con **una sola palabra en dorado** por bloque, y que sangre por los bordes.
4. El fondo de cine es negro con polvo, pelusas, rayas verticales y grano animados en cada cuadro, nunca un negro plano.
5. La cámara del título **deriva siempre** (push-in lento continuo). Nunca está quieta.
6. Para cambiar de encuadre en el título se usa **desenfoque → reenfoque** (4–6 cuadros), no un corte.
7. Lo que «está mal» se muestra degradando el mismo título (apagado, tachado con rayones a mano y una caja dorada que lo nombra).
8. La palabra clave va en **caja dorada texturizada**, con esquinas rectas y centrada arriba, y crece palabra a palabra.
9. El subtítulo va **siempre al 80 % de la altura y centrado**, en mayúsculas black y con 1–3 palabras.
10. La cara sale poco (≤3 s por vez). El resto es apoyo a pantalla completa cada ~2 s.
11. En un tutorial, cada paso es una **captura ampliada sobre el control exacto** que se nombra.
12. Se cierra **repitiendo el gancho** (bucle).

## 11. Qué NO hace
- No pone texto ni gráficos encima de la persona (salvo el subtítulo).
- No usa colores saturados fuera de la ráfaga de muestras de 20–22 s.
- No usa animaciones elásticas, rebotes, deslizamientos ni escalas «pop». Todo entra por corte, por write-on o por desenfoque.
- No hace punch-in por palabra en la cara ni tiene temblor de cámara.
- No usa emojis, íconos, stickers, flechas 3D ni barras de progreso.
- No usa halation, bloom ni aberración cromática sobre la toma de la persona.
- No usa música visualizada ni ondas. El sonido no se refleja en lo visual.

## 12. Tabla de momentos
| Segundo | Qué se ve | Recurso |
|---|---|---|
| 0,00–3,33 | Negro de película con una cornisa sepia abajo. El título se arma palabra a palabra («LOOK AT THIS / NETFLIX / TITLE SEQUENCE»), se desenfoca a 1,5 s y vuelve más grande | Word-on seco + rack focus + push-in lento |
| 3,33–3,50 | El mismo título desenfocado, saltando más abajo (0,17 s) | Desenfoque como corte |
| 3,50–8,77 | Título gigante que sangra por los bordes y deriva. Flecha blanca a mano que se dibuja hacia arriba («those subtle streaks of light behind the text») | Push-in continuo + flecha write-on |
| 8,77–8,93 | El título se desenfoca y la flecha se encoge y desaparece | Transición de desenfoque |
| 8,93–11,27 | Negro puro con el título reenfocado más chico y centrado («and suddenly… it feels way less alive»). A 10,5 s, rayones blancos diagonales y la caja dorada «BORING» encima | Versión «mala» + tachado + caja clave |
| 11,27–14,10 | Cara en plano medio («the secret is… in After Effects… fractal noise») | Toma a cámara |
| 14,10–20,10 | Ruido fractal gris a pantalla completa. Caja «RANDOM» (16,5) → «RANDOM NOISE» (17,0) | Apoyo literal + caja que crece por palabra |
| 20,10–20,77 | Abanico de luz amarillo verdoso desde abajo | Muestra de efecto |
| 20,77–21,43 | Remolinos verdes sobre negro | Muestra de efecto |
| 21,43–22,23 | Degradado naranja con estrellitas | Muestra de efecto |
| 22,23–23,60 | Cara («here's how you can… background with it. First, create») | Toma a cámara |
| 23,60–26,33 | Diálogo Solid Settings ampliado (nombre «Light Leak», 1080×1920) y menú de efectos | Captura + punch-in + cursor |
| 26,33–26,87 | Vista de la comp: la capa negra se vuelve ruido fractal | Antes/después en 1 cuadro |
| 26,87–31,43 | Controles del Fractal Noise (Transform, Uniform Scaling apagado, Scale Width arrastrado en vivo) | Captura ampliada sobre el control |
| 31,43–33,47 | Vetas grises verticales a pantalla completa («thin streaks of light») | Resultado intermedio |
| 33,47–34,73 | Controles: Evolution | Captura |
| 34,73–37,20 | Línea de tiempo con la expresión `effect("Fractal Noise")… time*200` | Captura con texto de código ampliado |
| 37,20–40,07 | Vetas animándose («to keep those streaks constantly shifting»), con un breve panel de efectos a 38,5–39 s | Resultado + captura |
| 40,07–41,33 | Comp con la capa seleccionada (marco rojo) | Captura |
| 41,33–42,10 | Efecto Levels con histograma («to crush the contrast») | Captura ampliada |
| 42,10–43,70 | Vetas sobre textura gris («then just layer in some texture») | Resultado + textura |
| 43,70–47,17 | Negro de película vacío («and you're left with this») → se rearma el título igual que en 0 s («really cinematic, premium looking title sequence») | Cierre en bucle, word-on |
