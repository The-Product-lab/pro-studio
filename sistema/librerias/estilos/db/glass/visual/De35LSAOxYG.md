# De35LSAOxYG — glass · estudio visual cuadro a cuadro

Cuadros a 16:9 horizontal (360×202 en la muestra). Dura 46,17 s · 17 cortes · 22,1 cortes/min · plano medio 2,56 s (mín. 0,8 · máx. 7,33). Luz media 0,79 · contraste 0,26 · saturación 0,12.
**No sale ninguna persona.** Es un motion graphic puro: tipografía cinética sobre papel gris claro + interfaz de software (ventanas, campo de prompt, chips, íconos de apps) + un mockup de escritorio macOS. Es un anuncio de producto («Blink», un creador de apps con IA). La voz en off manda y cada palabra aparece cuando se dice.

## 1. Sistema en una frase
Texto de Helvetica negra, una o pocas palabras centradas sobre gris perla (#EBEAED), escritas al ritmo de la voz, que se transforman sin parar en piezas de interfaz limpia (tarjeta de alerta, terminal, campo de prompt, chips de colores, órbita de íconos). Los acentos son azul eléctrico (#3B82EA) con desenfoque de vidrio y una cursiva serif tipo Playfair para la palabra emocional.
**Se reconoce en 1 s por:** fondo gris claro casi blanco y sin textura, una sola línea de texto en el centro óptico que se escribe letra a letra con el color pasando de azul a negro, y una mezcla sans/serif-cursiva en la misma frase.

## 2. Color
| HEX | % | Rol | Dónde |
|---|---|---|---|
| #EBEAED | 39,6 | Fondo base (papel gris perla, ligeramente frío/lila) | Casi todos los planos de texto (0–6 s, 7,5–21 s, 23–30 s, 35,5–39 s) |
| #DBDEE3 | 14,7 | Fondo en sombra / degradado de vidrio y viñeta suave | Bordes del cuadro en 3,0–4,5 s; zonas grises tras el desenfoque azul |
| #52223C | 12,5 | Vino oscuro: promedio del escritorio macOS (magenta/rojo del fondo de pantalla) y la ventana oscura | 30,0–34,3 s (mockup macOS, error rojo) |
| #FCFAFD | 10,5 | Blanco de las tarjetas y paneles (alerta, banda del «From full-stack», mockup final) | 4,5–6,0 s, 14,0–20,3 s, 39–46 s |
| #3B82EA | 8,1 | **Acento único**: botón enviar, círculo con flecha, campos de fondo azul, barra «More Time», borde de foco | 12,5–13,3 s, 21,9–23,0 s, 37,5–41,5 s, 42,5 s |
| #EEECEF | 6,2 | Variante del fondo (gradiente del papel) | Planos de texto |
| #9FB8A6 | 5,2 | Verde salvia: billetes y cuadros «Resolved» (verde bajado de valor) | 1,4–2,8 s y 34,3–35,5 s |
| #F5F4F7 | 3,2 | Luces del papel / centro del degradado | Centro de los planos claros |

Colores semánticos de la interfaz (pequeños): rojo alerta ~#EF4B56 (escudo, botón «Verify now», `// endless`, tarjeta «Found the issue»), verde código ~#9BE59B (`"debugging"`), verde billete ~#3FA24F/#7ED87E, morado chip ~#C99BF0, rojo chip ~#F4A6A6, azul chip ~#A9C6F5, verde chip ~#A8E6A8, negro terminal ~#0E0C14.
- **Armonía:** neutro frío casi monocromo + un solo acento azul. Rojo y verde aparecen solo como código semántico (error/arreglado), nunca como decoración.
- **Tratamiento:** imagen plana digital, sin grade de cine. Contraste bajo en fondo y negro puro solo en las letras. Saturación global 0,12 (baja); la saturación se concentra en los acentos.
- Grano: no. Ruido: no. Halation: no. Viñeta: muy suave, gris (#DBDEE3) en esquinas en algunos planos (3,0–4,5 s, 7,5–9 s con halo azul arriba). Aberración cromática: no. Scanlines, polvo, papel, semitono: no.
- **Glow/bloom:** sí, pero como «vidrio»: manchas de azul muy desenfocadas (blur gaussiano grande, ~30–40 % del cuadro) que entran como luz detrás de las piezas: halo azul celeste arriba del campo «Don't just think it» (7,5–9 s), barrido azul de pantalla completa (13,05–13,3 s; 21,7–23,0 s; 39,0–41,5 s). Funcionan como luz suave/screen sobre el gris.
- **Light leak:** el «barrido azul» de las transiciones hace de leak frío, entra desde la esquina superior izquierda en diagonal.

## 3. Tipografía
| Rol | Familia probable → Google Fonts | Peso / ancho | Caja | Tamaño (% del ancho) | Color | Efectos |
|---|---|---|---|---|---|---|
| Texto narrado (principal) | Helvetica Neue / SF Pro → **Inter** (o Hanken Grotesk) | Regular 400, ancho normal | minúsculas tipo oración | 4–6 % de alto de x; la línea ocupa 25–40 % del ancho («you're dealing with» ≈ 30 %) | #111 sobre gris; blanco sobre azul/negro | Ninguno. Sin sombra, sin borde |
| Palabra gigante de golpe | igual (Helvetica) | Regular 400 | Mayúscula inicial («Apps») | ≈ 35 % del ancho, alto de cap ≈ 30 % del alto del cuadro | negro | Ninguno |
| Palabra emocional | Playfair Display Italic → **Playfair Display Italic** | Regular/Medium | minúsculas, cursiva | «Blink» ≈ 22 % del ancho a 9 s; «spend», «Less», «More» ≈ 5–8 % | azul marino #1F2A55 o negro; «spend» azul medio | Ninguno |
| Titular serif recto | Playfair Display Roman | Regular | «Don't just think it.» | ≈ 25 % del ancho | gris azulado #3C4566 | Ninguno; en dos líneas, la 2.ª en cursiva («Blink it.») |
| Lista vertical tipo tambor | Helvetica Regular | 400 | minúsculas (con «Authentication» con mayúscula) | ≈ 7 % de alto de x | gris #9A9A9E los inactivos; negro el activo | El activo lleva **corchetes de selección** finos: 4 puntos/esquinas azules en sus extremos (caja de selección de Figma) |
| UI (chips, botones, código) | SF Pro / Menlo → **Inter** + **JetBrains Mono** | 400–500 | mixta | 2–4 % | según chip | Chips con trazo 1 px del mismo tono más oscuro |
| CTA final | Helvetica **Bold** + Regular pequeña | 700 / 400 | «Comment "blink" and» + «I'll send you the link.» | 1.ª línea ≈ 45 % del ancho; 2.ª ≈ 25 % | negro | Sin sombra; legible sobre una retícula de miniaturas desvanecida al blanco |

Tracking normal (0), interlineado ~1,05 en la lista tambor. Todo centrado. Se apila en máximo 2 líneas salvo la lista tambor (7–8 renglones). **Mezcla clave: sans recta + serif cursiva dentro de la misma frase** («Blink > doesn't», «So you can *spend*», «*Less* — Time»).

## 4. Composición
- Retícula: **centro absoluto**. Casi todo cae en la franja horizontal 40–60 % del alto. Márgenes laterales ≥ 15 %.
- Planos de comparación en **tres columnas**: palabra izq. (x≈10–15 %) · objeto central (x 30–70 %) · palabra der. (x≈85–90 %). Ej.: «broken [billetes] payments», «Someone [mockup] build this», «*More* [barra] Time».
- 1,4–2,8 s: **líneas de retícula visibles** (gris claro 1 px, verticales a x≈20 % y 78 %, horizontales a y≈25 % y 75 %) con **puntos azules de 3–4 px en los cruces** — retícula de diseño/Figma hecha visible.
- Nada delante/detrás de una persona (no hay persona). La profundidad sale del desenfoque: lo de atrás se desenfoca (manchas azules, retícula de miniaturas del CTA desvanecida al blanco ~70 %).

## 5. Elementos gráficos
1. **Billetes vectoriales** (1,4–2,8 s): 3 billetes planos verde #3FA24F con borde #7ED87E de ~3 % de grosor, signo $ en círculo claro. Ancho ≈ 40 % del cuadro. Entran escalando desde ~60 % con leve giro (−8°→0°) en ~4 cuadros (0,2 s), se abren en abanico con desfase de ~2 cuadros. **Salida:** el billete de arriba se **rasga/se dobla** desde la esquina derecha (2,6–2,77 s) y corte seco.
2. **Red de errores** (2,77–4,5 s): ~15 cuadrados planos (azul #4A86F0, petróleo #1E4B4F, turquesa #2BB5A5, azul oscuro #1428C8) de 2–4 % del ancho con símbolos (! ? × / = </>) unidos por líneas negras de 1 px, palabras sueltas «error», «Failed!». Al centro, un campo blanco con «Complicated authentication» que se escribe. Entrada: aparece desde escala ~40 % (cuadro 2,77) y se acerca a 100 % en ~4 cuadros, ease-out. Los nodos se reacomodan (deriva) cada pocos cuadros.
3. **Tarjeta de alerta** (4,5–5,8 s): tarjeta blanca 25 % ancho, esquinas ~4 px, sombra muy suave; escudo rojo con «!», «Potential Security Threat» en negrita, botón rojo «Verify now». Estática.
4. **Ventana terminal** (5,8–6,77 s): ventana oscura #0E0C14 con barra clara y 3 semáforos macOS (rojo/amarillo/verde). Entra deslizando desde abajo-derecha (en 1 cuadro ya está en sitio, ease-out fuerte). Se escribe `// endless ("debugging` con cursor bloque gris. **Salida:** push-in (zoom de cámara ~110 %→150 %) hacia el texto + oscurecimiento del fondo → queda solo «debugging» blanco sobre negro (6,77 s), con las letras del final entrando en desenfoque.
5. **Campo de prompt «Full stack App»** (7,5–9 s): tarjeta blanca 60 % ancho, pestañas (Full stack App · Mobile · Website · Chrome), botón enviar azul circular; halo azul celeste desenfocado arriba.
6. **Botón azul con flecha** (12,5–13,05 s): círculo #3B82EA con degradado (claro arriba-izq.), flecha blanca; un cursor negro de macOS lo alcanza y hace clic → **el círculo crece hasta llenar el cuadro** (13,0–13,1 s, ~3 cuadros, ease-in) y se vuelve campo azul desenfocado de donde salen las pantallas del producto.
7. **Pantallas del producto** (13,1–14 s): 3 capturas de dashboard en tarjetas con sombra suave, que entran **de desenfocadas a nítidas** (blur ~20 px → 0 en ~6 cuadros) y se abren en cascada.
8. **Banda blanca + chips** (14–20,3 s): banda blanca horizontal (y 35–75 %) con «+ From full-stack» que se escribe; a su derecha, **chips en cascada vertical**: SaaS platforms (azul #A9C6F5), Mobile apps (rojo #F4A6A6), Chrome extensions (verde #A8E6A8), AI agents (morado #C99BF0); radio ~4 px, trazo 1 px más oscuro, texto del mismo tono saturado. Entra uno cada ~0,5–1 s, desde abajo con fade; la lista **sube** a medida que entra el siguiente (scroll vertical suave); toda la banda deriva a la izquierda (cámara flotante horizontal lenta).
9. **Campo de prompt sencillo** (20,3–21,9 s): píldora blanca 25 % ancho, borde gris 2 px, «+», mic, botón azul cuadrado redondeado; se escribe «All from a simple prompt.». Al final el borde se pone azul (foco) y el campo **se hunde en un barrido azul de vidrio** que entra desde la esquina superior izq.
10. **Órbita de íconos** (23–25 s): elipse de línea negra de 1–2 px (≈ 90 % ancho, inclinada) y otra elipse gris tenue detrás; 10 íconos de app en cuadrados redondeados negro azulado (radio ~20 %) con glifo de color (N blanco, S morado, escudo arcoíris, engranaje rosa, correo rojo, documento rosa, cuadrícula azul, triángulo azul-violeta). Giran sobre la órbita en deriva continua. Entrada: zoom-out de cámara desde muy cerca (23,03: «The» enorme y desenfocado) hasta plano general en ~5 cuadros.
11. **Lista tambor** (24,8–30 s): columna de palabras (integrations, databases, payments, Authentication, hosting) que **rueda verticalmente** como selector de iOS; la activa en negro con corchetes azules de selección, las demás en gris. Se repite en loop hacia arriba.
12. **Escritorio macOS** (30–34,3 s): fondo de pantalla de Big Sur (magenta/rojo/naranja/azul), ventana oscura de código con línea de error en rojo, dock con 4 íconos; ligero push-in. 31,53 s: corte a ventana grande «ResourceNotFoundException» con stack trace (la ventana cubre 85 % del cuadro). 33,03 s: **punch-in extremo** al código (`// ✕ Error: user is undefined` enorme, 1 cuadro) y vuelta a plano con tarjeta roja «Found the issue» encima de la ventana.
13. **Transición a «Resolved»** (34,0–35,5 s): la tarjeta roja **gira en 3D** (rotación Y/Z ~15°) mientras se tiñe de rojo → naranja → verde (34,12–34,27), el escritorio se desvanece a blanco y la tarjeta queda como cuadrito verde que **crece con anillos concéntricos verdes** (3 cuadrados redondeados #C8F5D2/#9FE6B5/#6CC98A) que se expanden hacia afuera con overshoot; icono check en círculo + «Resolved». Luego los anillos se contraen.
14. **Barra de progreso** (36,5–38,5 s): píldora gris con relleno rosa/rojo corto («*Less* ▬ Time») → relleno azul largo («*More* ▬▬▬ Time»). La barra se convierte (38,5 s) en un rectángulo azul con borde azul claro que **crece** y se vuelve la tarjeta del producto.
15. **Mockup final** (39–43 s): sitio de viajes en tarjeta blanca con esquina redondeada y sombra larga y suave, en leve perspectiva 3D (rotación ~10°); entra sobre un campo azul de vidrio; un botón cuadrado azul con flecha aparece al centro (42,5 s).
16. **CTA** (43,5–46 s): retícula de miniaturas (posters amarillos) en blanco al ~30 % de opacidad con desvanecimiento radial; texto negro centrado encima.

## 6. Apoyos
- **Cada idea dicha tiene su objeto literal**: «broken payments» → billetes que se rompen; «complicated authentication» → red de errores; «security» → alerta; «endless debugging» → terminal; «apps» → palabra gigante; «helps you» → botón con cursor; «from full-stack…» → chips; «simple prompt» → campo; «the hard stuff is built in» → órbita de íconos de servicios; lista → tambor; error → stack trace + «Found the issue»; arreglado → «Resolved»; «less/more time» → barra; «someone build this» → mockup.
- Frecuencia: **un apoyo nuevo cada 1–2,5 s**; nunca hay más de 2 s sin un objeto nuevo o una transformación. Los apoyos son **íconos/UI planos**, nunca fotos.

## 7. Persona
No aparece. No hay rostro, ni silueta, ni toma de cámara. Toda la «actuación» la hace el cursor de macOS (12,7–13 s) y el texto que se escribe.

## 8. Movimiento y transiciones
- **Cámara:** virtual. Deriva lenta continua (≈1–3 % del ancho por segundo) en casi todos los planos: la banda de chips se desliza a la izquierda, la lista tambor sube, la órbita gira, el escritorio macOS se acerca suave. Sí se mueve mientras entra un apoyo.
- **Push-in a la palabra:** 6,5–6,77 s (terminal → «debugging»); 33,03 s punch-in de 1 cuadro al código; 13,0 s el botón llena la pantalla.
- **Zoom-out de revelado:** 23,03 s (de «The» gigante a la órbita) y 2,77 s (la red aparece pequeña y se acerca).
- **Curvas:** ease-out fuerte (llegan en 3–5 cuadros a 20 cps y se asientan), con **overshoot leve** en los anillos «Resolved» y en los chips. Nada lineal ni stop-motion. Estilo: UI de Apple, suave y seca a la vez.
- **Escritura:** el texto se escribe letra a letra, ~1 letra por cuadro a 20 cps (≈15–20 letras/s); **las letras nuevas entran azules/grises y desenfocadas y se asientan en negro** (0,0–0,4 s «Suddenly»: azul #3B5BB8 → negro en ~6 cuadros; «debugging» las letras finales entran borrosas). Al cerrar la frase, el bloque sube un poco de tamaño (escala 100→110 % en «Suddenly,» 0,3–0,5 s).
- **Salida del texto:** las palabras se separan (1,2–1,3 s «you're  dealing  with» se espacian) y desaparecen con desenfoque; o salen por los lados empujadas por el siguiente objeto.
- **Transiciones por corte medido:**
  - 2,77 billetes rotos → red: corte seco tras el rasgado.
  - 5,80 alerta → terminal: la ventana entra deslizando desde la esquina inf.-der.
  - 6,67 terminal → «debugging» negro: push-in + oscurecimiento (~3 cuadros).
  - 7,47 negro → blanco: **barrido de luz/degradado blanco de izquierda a derecha** (7,37–7,52), el negro se va como cortina difusa.
  - 13,00 botón → campo azul: el círculo azul crece hasta tapar todo (morph).
  - 20,33 chips → campo de prompt: la banda blanca sale hacia arriba/izquierda, aparece el campo (corte con slide).
  - 21,87 prompt → «And the best part?»: barrido azul de vidrio desde la esquina sup.-izq. que cubre todo en ~6 cuadros; el campo se disuelve debajo; el texto blanco entra con blur.
  - 23,03 azul → órbita: el texto encoge a casi nada (22,98) y la cámara sale desde «The» gigante; el azul se aclara a gris desde la derecha.
  - 24,70 órbita → lista: la órbita queda arriba y la lista entra por abajo (scroll vertical).
  - 29,97 lista → macOS: corte seco.
  - 31,53 escritorio → ventana grande: corte con salto de escala (punch).
  - 33,03 punch-in al código de 1 cuadro, vuelta con tarjeta roja encima.
  - 34,27 tarjeta roja → «Resolved»: giro 3D + cambio de color + desvanecido a blanco.
  - 35,50 «Resolved» → «So you can spend»: los anillos se encogen y corte a gris.
  - 38,77 barra → tarjeta azul → mockup: la barra se convierte en rectángulo que crece (morph).
  - 39,70 mockup → campo azul «If you've ever thought»: el mockup se va dentro del azul.
  - 41,20 azul → «Someone [mockup] build this»: el azul se encoge a una tarjeta y se aclara a gris.

## 9. Subtítulos
No hay subtítulos aparte: **el texto narrado ES el gráfico**. Siempre centrado (y≈48 %), 1–4 palabras a la vez, Helvetica Regular negra. La palabra clave se marca de tres maneras: (a) cambio de familia a Playfair cursiva («Blink», «spend», «Less», «More»), (b) escala gigante sola en el cuadro («Apps», ≈35 % del ancho), (c) en la lista, negro + corchetes azules frente a gris.

## 10. Reglas del sistema
1. Fondo gris perla #EBEAED liso, sin grano ni textura; la profundidad solo con desenfoque.
2. Un solo acento de color: azul #3B82EA. Rojo = problema, verde = resuelto; nunca decorativos.
3. El texto aparece al ritmo exacto de la voz, letra a letra (~1 letra por cuadro a 20 cps), entrando en azul/borroso y asentándose en negro.
4. Una sola idea en el centro del cuadro; máximo 4 palabras visibles (salvo la lista tambor).
5. Mezclar en la misma frase Helvetica/Inter recta con Playfair cursiva para la palabra emocional.
6. Cada concepto se convierte en un objeto de interfaz plana literal (tarjeta, campo, chip, ícono, ventana) en menos de 1 s.
7. Nada corta en seco sin razón: los objetos se transforman en el siguiente (círculo que llena la pantalla, barra que se vuelve tarjeta, tarjeta roja que gira a verde).
8. Barridos de vidrio azul desenfocado (blur grande, desde la esquina sup.-izq.) como transición entre bloques de ideas.
9. Cámara virtual siempre en deriva suave; push-in o zoom-out solo para cambiar de bloque.
10. Entradas ease-out de 3–5 cuadros (0,15–0,25 s) con overshoot mínimo; cascadas con desfase de 2–3 cuadros o una por palabra dicha.
11. Comparaciones en 3 columnas: palabra · objeto · palabra.
12. UI con estética macOS/Figma: semáforos, cursor negro, corchetes de selección azules, esquinas de 4–20 % de radio, sombras largas y muy suaves.

## 11. Qué NO hace
- No muestra a ninguna persona ni usa toma de cámara.
- No usa grano, viñeta fuerte, halation, aberración, scanlines ni texturas de papel.
- No usa mayúsculas sostenidas, letra condensada ni negrita (salvo el CTA final).
- No pone trazo ni sombra en el texto.
- No usa fotos de stock ni imágenes generadas; solo vectores e interfaz.
- No pone subtítulos en una franja aparte del gráfico.
- No usa colores saturados de fondo salvo el azul de vidrio y el escritorio macOS.
- No usa movimientos elásticos exagerados ni stop-motion.
- No mete más de un objeto protagonista a la vez.

## 12. Tabla de momentos
| Segundo | Qué se ve | Recurso |
|---|---|---|
| 0,00–2,77 | «Suddenly,» → «you're dealing with» escritos al centro; 1,4 s billetes verdes entre «broken» y «payments» sobre retícula visible con puntos azules; el billete se rasga | Escritura azul→negro, retícula Figma, objeto literal, rasgado |
| 2,77–5,80 | Red de cuadrados con símbolos y líneas + «Complicated authentication»; 4,5 s tarjeta «Potential Security Threat» | Zoom-in de revelado, nodos en deriva, tarjeta de alerta |
| 5,80–6,67 | Ventana terminal: `// endless ("debugging` | Slide desde abajo-der., escritura de código |
| 6,67–7,47 | «debugging» blanco sobre negro | Push-in + oscurecimiento |
| 7,47–13,00 | Barrido blanco; «Don't just think it. *Blink it.*» sobre campo de prompt con halo azul; «*Blink*» gigante; «*Blink* > doesn't», «*Blink* ✱ just»; «Apps» enorme; «It helps you a^i#» (texto que se glitchea); botón azul con cursor | Serif cursiva + sans, palabra gigante, cursor que hace clic |
| 13,00–20,33 | Botón llena el cuadro de azul → dashboards de desenfocado a nítido; banda blanca «+ From full-stack» con chips SaaS/Mobile/Chrome/AI agents en cascada | Morph de círculo, blur→nítido, chips en cascada, deriva lateral |
| 20,33–21,87 | Campo de prompt: «All from a simple prompt.» | Escritura, borde de foco azul |
| 21,87–23,03 | Barrido azul de vidrio; «And the best part?» blanco | Light leak azul, texto con blur |
| 23,03–24,70 | «The hard stuff… is built in.» dentro de una órbita de 10 íconos de app | Zoom-out desde la palabra, órbita en rotación |
| 24,70–29,97 | Lista tambor: integrations / databases / payments / authentication / hosting, la activa con corchetes azules | Scroll vertical tipo selector iOS |
| 29,97–31,53 | Escritorio macOS Big Sur, ventana de código con línea roja, dock | Corte seco, push-in suave |
| 31,53–33,03 | Ventana grande «ResourceNotFoundException» con stack trace | Punch de escala |
| 33,03–34,27 | Punch-in de 1 cuadro a «✕ Error: user is undefined»; tarjeta roja «Found the issue» encima | Punch-in extremo, tarjeta superpuesta |
| 34,27–35,50 | La tarjeta gira en 3D y pasa de rojo a verde; anillos verdes concéntricos con check «Resolved» | Giro 3D, cambio de color, anillos con overshoot |
| 35,50–38,77 | «So you can *spend*» → «*Less* ▬ Time» (rosa corto) → «*More* ▬▬▬ Time» (azul largo); la barra se vuelve rectángulo azul | Comparación en 3 columnas, barra de progreso, morph |
| 38,77–39,70 | Tarjeta azul que se vuelve el mockup del producto en campo azul | Morph, perspectiva 3D |
| 39,70–41,20 | Campo azul de vidrio: «If you've ever thought» | Texto blanco sobre azul |
| 41,20–46,17 | «Someone [mockup de web de viajes] build this»; botón azul con flecha; campo «now you ca…»; CTA «Comment "blink" and / I'll send you the link.» sobre retícula de miniaturas desvanecida | Mockup en 3 columnas, CTA en negrita sobre fondo desvanecido |
