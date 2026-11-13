# Dcb7aXrzmX7 · glass · estudio visual

> Reel de portafolio de una agencia («Searching Ad», sale en el cierre). Muestra **tres edits 16:9 de un mismo anuncio** (inversor inmobiliario alemán, «Deland Real Estate») **apilados en un lienzo vertical blanco y corriendo a la vez**, desfasados en el tiempo. Cada franja es una versión: unas veces muestra a la persona, otras una escena de tarjetas de UI de vidrio esmerilado en 3D. Duración 29,7 s · 12 cortes medidos · 24,2 cortes/min · plano medio 2,28 s (min 0,03 / máx 4,9).
> Coordenadas en un lienzo 1080×1920 (medidas a partir de los cuadros 360×640 ×3).

---

## 1. Sistema en una frase

**Tríptico de tres franjas 16:9 sobre blanco puro, donde la cabeza parlante se alterna con un «mundo de UI» de tarjetas blancas de vidrio flotando en perspectiva sobre un fondo menta con cubos isométricos, todo en verde azulado/menta y con un único acento cian eléctrico que brilla.**

Se reconoce en 1 s por: (a) las tres franjas apiladas con un borde blanco ancho alrededor; (b) tarjetas blancas tipo dashboard (cifras en euros que cuentan, gráficos de área) inclinadas en 3D; (c) una palabra serif que se «decodifica» desde letras aleatorias; (d) el destello cian.

---

## 2. Color

| HEX medido | % | Rol | Dónde |
|---|---|---|---|
| `#FDFFFC` | 37,5 | **Lienzo** (marco blanco alrededor de las franjas) y relleno de las tarjetas de UI | margen superior/inferior y laterales del lienzo; cuerpo de cada tarjeta; fondo del cierre (27–28,3 s) |
| `#EFF6F0` | 16,7 | **Fondo de la escena UI**: menta casi blanca | franjas de UI y la franja del titular «Wie fängst du an?» |
| `#797261` | 12,2 | Sombras y medios tonos de la toma (muebles de cocina, sombra de la camisa) | franjas de la persona |
| `#A59785` | 8,9 | Madera / pared beige cálida de la cocina, piel | franjas de la persona |
| `#B7D9D4` | 7,7 | **Verde agua de acento suave**: relleno del gráfico de área, patrón de cubos, píldoras, línea de subrayado del titular | escena UI, subrayados, tinte cian del final |
| `#F7FAF7` | 6,4 | Segundo plano de tarjetas, fondo del logo (gris muy claro) | panel del logo 17–19,5 s, tarjetas de atrás |
| `#111816` | 5,8 | **Negro verdoso**: texto de UI, cocina negra (horno), fundidos a negro, cierre negro | cifras de tarjetas, 1,0–1,2 s, 20,5 s, 23,0 s, 28,3–29,7 s |
| `#E4E9E4` | 5,0 | Bordes/separadores de tarjetas, sombras muy suaves | contornos de tarjetas, cajas internas |

Colores no medidos por porcentaje pero clave (se ven en cuadros):
- **Verde petróleo de marca** ≈ `#0F6E64`–`#13706A`: tarjeta «Gewinn 85.092€ Steuerfrei» (degradado de `#1C7A6C` arriba-izq a `#0E5C54` abajo-der), barra de «Trag dich ein», logo Deland, borde superior de la tarjeta «Immobilie #1», titular serif `#1F5C58`.
- **Cian eléctrico** ≈ `#00F5FF`/`#14FFFF`: brillo de «200,000€» y «Marco», píldora «Strategie», cifra que cuenta en el chip «Echter Vermögensaufbau», inundación y logo del cierre. Es el único color saturado del reel.
- **Rojo suave** ≈ `#F5C9C9` con texto `#D04848`: píldora «Erstattet» de la tarjeta Finanzamt (un solo toque).

Armonía: **análoga fría** (menta → verde agua → petróleo) con **un solo acento** cian. La toma de la persona es cálida (beige/madera) y crea contraste de temperatura con la UI fría.
Tratamiento: luz media 0,82 (muy clara, por el blanco), contraste 0,26 (bajo), saturación 0,06 (casi desaturado). Toma limpia, natural, sin grade visible; negros de la cocina sin levantar. **Sin grano, sin ruido, sin viñeta** en la UI; en las franjas con cifra serif grande hay un **degradado negro inferior** (≈ 45 % inferior de la franja, de 0 % a ~70 % de opacidad) para que lea el blanco. Sin halation, sin aberración cromática, sin scanlines, sin polvo, sin papel, sin semitono, sin light leaks. El único «efecto de luz» es **glow cian** (modo screen/add: el cian se suma y aclara lo que hay debajo).

---

## 3. Tipografía

| Estilo | Rol | Caja | Peso / ancho | Serif | Tracking | Tamaño (% ancho del lienzo) | Color / efecto | Google Fonts |
|---|---|---|---|---|---|---|---|---|
| **Serif titular** «Wie fängst du an?» | gancho / pregunta | frase normal | Regular 400, ancho normal | sí, transicional (tipo Times/Tinos) | normal (0) | ≈ 6 % de alto de letra; la frase ocupa ≈ 60 % del ancho de la franja (≈ 48 % del lienzo) | `#1F5C58` sólido, sin sombra; **subrayado** fino de 2 px debajo que se desvanece en ambos extremos (verde agua) | **Tinos** o **Libre Caslon Text**; alternativa **Playfair Display** si se quiere más contraste |
| **Serif itálica de cifra/nombre** «200,000€», «800,000€», «Marco» | dato impactante / presentación | normal | Regular itálica, contraste alto | sí, didona/transicional itálica | ligeramente abierto | ≈ 9–10 % de alto; ocupa ≈ 40 % del ancho de la franja | blanco `#FFFFFF` sobre degradado negro; **glow cian** que barre de izquierda a derecha | **Playfair Display Italic** (más cercana) o **Cormorant Garamond Italic** |
| **Sans de UI** («Investment», «Gehalt», «Monatlicher Output», «Finanzamt») | etiquetas de tarjetas | normal | Medium 500 para títulos de tarjeta, Regular 400 para filas, **Semibold/Bold 600–700 para cifras** («3.000€») | no, grotesca neutra tipo SF Pro/Inter | 0 | títulos ≈ 2,5 % del ancho del lienzo; cifras ≈ 4 %; filas ≈ 1,5 % | `#111816` en filas, gris `#8A8F8C` en etiquetas secundarias | **Inter** |
| **Cifra dentro de la tarjeta verde** «85.092€» | ganancia | — | Semibold itálica (sintética por la perspectiva) | no | 0 | ≈ 4,5 % | blanco sobre petróleo | **Inter** SemiBold |
| **Subtítulo** («Einnahmequelle», «fast selbst», «für dich arbeitet») | subtítulo palabra a palabra | normal | Medium 500 | no | 0 | ≈ 3 % de alto de letra (palabra larga = 23 % del ancho del lienzo) | blanco, con sombra muy suave (difusa, 0 px de distancia, ~6 px blur, 40 % negro) | **Inter** Medium |
| **CTA** «Trag dich ein» | llamado a la acción | normal | Medium 500 | no | 0 | ≈ 4 % de alto; barra ≈ 50 % del ancho de la franja | blanco sobre barra `#13706A` | **Inter** Medium |
| **Rótulo** «Gründer und Geschäftsführer» | cargo bajo el nombre | normal | Regular | no | +2 % | ≈ 1,5 % | blanco 85 % | **Inter** |
| **Logo** «Deland Real Estate» / «PARTNERS GMBH» | marca del cliente | Título / VERSALITAS | Semibold / Medium | no, geométrica | 0 / **+30 %** en la línea pequeña | ≈ 5 % / 1,2 % | `#111816` / `#0F6E64` | **Montserrat** SemiBold / Montserrat Medium tracking ancho |
| **Logo de la agencia** «Searching Ad» | firma final | Título | Semibold | no | 0 | ≈ 9 % | gris oscuro `#3A3A3A` sobre blanco → blanco sobre negro | **Inter** SemiBold |

Apilado: siempre en una sola línea; la cifra serif va sola y centrada; el nombre «Marco» lleva el cargo en una segunda línea pequeña justo debajo (interlineado apretado, ≈ 0,9).

---

## 4. Composición

- **Retícula de tres franjas** horizontales 16:9, centradas, sobre el lienzo `#FDFFFC`:
  - ancho de franja ≈ 870 px (**80,5 % del ancho**), x 105–975; margen lateral ≈ 9,7 % por lado;
  - franja 1: y ≈ 204–696; franja 2: y ≈ 714–1206; franja 3: y ≈ 1221–1713; alto ≈ 490 px (**25,5 % del alto** cada una);
  - separación entre franjas ≈ 15–18 px (0,9 %); margen superior ≈ 10,6 % y inferior ≈ 10,8 % del alto;
  - esquinas de franja con radio pequeño (≈ 8–12 px) en las tomas de persona; las de UI casi rectas.
  - Las tres franjas caen dentro de la zona segura de IG (y 204–1713).
- **Persona**: centrada horizontalmente en su franja, plano medio (cabeza al 20–30 % del alto de la franja, manos juntas sobre la mesa al borde inferior); ocupa ≈ 35 % del ancho de la franja. Mira a cámara.
- **Texto**: subtítulo centrado al ≈ 85 % del alto de la franja (sobre el pecho/manos). Cifra serif grande centrada al ≈ 70 % del alto, **delante** de la persona (le tapa el torso). Chip «Echter Vermögensaufbau» a la **izquierda**, a la altura de los hombros (x ≈ 8–30 % de la franja), sin tapar la cara.
- **Escena UI**: tarjetas distribuidas a distintos z; una tarjeta principal centrada (≈ 55–65 % del ancho de la franja) y otras recortadas por los bordes de la franja (salen del cuadro), lo que da sensación de espacio más grande que la ventana.
- Delante/detrás: nada queda detrás de la persona (no hay recorte de silueta); todo va encima de la toma.

---

## 5. Elementos gráficos

1. **Marco de lienzo blanco** `#FDFFFC`: fijo todo el reel salvo el cierre. Al arrancar (0,00–0,50 s) el bloque de las tres franjas **se reduce y asienta** (escala de ≈ 104 % → 100 %, ease-out, ~12 cuadros) y la franja del medio arranca con encuadre más cerrado (punch-out de ≈ 115 % → 100 % en 1–2 cuadros).
2. **Fondo menta con cubos isométricos**: `#EFF6F0` con un patrón repetido del cubo hexagonal del logo Deland, en `#B7D9D4` a ≈ 8–12 % de opacidad; cubos de ≈ 1/3 del alto de la franja. Se mueve en paralaje lento con la cámara de la escena UI.
3. **Tarjeta de vidrio blanca** (el elemento base): rectángulo `#FFFFFF`, radio ≈ 12–16 px (≈ 3 % de su ancho), borde de 1 px `#E4E9E4`, **sombra suave** difusa (desplazada ≈ 6–10 px hacia abajo, blur ≈ 25–30 px, 8–12 % negro verdoso). Dentro: filas separadas por líneas de 1 px, cajitas internas grises `#F3F5F3` con radio 6 px. Variantes vistas:
   - «Investment · Immobilie Berlin 240.000€ · Status Einzelinvestment» (1,3–4,5 s; 22,6–26 s).
   - Píldora «Kunde» con ícono de avatar petróleo (aparece 2,5 s: sube desde abajo con fundido, ~5 cuadros, ease-out).
   - «Strategie Planung · Phase 1–4» (barra de pasos) y «Langfristiger Vermögensaufbau · Portfolio Strategie» (lista con viñetas que se va escribiendo).
   - «Finanzamt · Steuerprüfung Aktiv · Steuern [Erstattet]» con **cursor de mano** que entra desde la derecha (6,25 s), hace clic en la fila (7,5 s) y la píldora roja pasa a **píldora cian «Strategie»**; luego aparece «Steuerstrategie aktiv» con check verde y paginación «Strategie Analyse ● ○ ○ ○».
   - «Gehalt · Monatlicher Output 2.510€ → 3.000€ · Startkapital erkannt 15.000€» con **gráfico de área** (línea petróleo, relleno degradado `#B7D9D4` → transparente) y meses Jan–Jun. La cifra **cuenta** continuamente (≈ +40 €/cuadro).
   - «Finanzierung · Einkommen 3.000 ✓ · Eigenkapital 15.000 ✓ · Status Genehmigt» (base con tinte verde claro).
   - **Tarjeta verde «Gewinn»**: degradado petróleo, radio 12 px, brillito ✦ blanco arriba-derecha, cifra blanca que cuenta de 20€ → 90.000€ (11,2–15,5 s) con «Steuerfrei»; a su lado «Immobilie Berlin · Kaufpreis» y debajo «Verkaufspreis 198.421€→240.000€» (también cuentan). Va sobre una tarjeta contenedora blanca grande inclinada.
   - «Immobilie #1 · Berlin» con borde superior petróleo de ≈ 6 px y botón «Start»; «Prozess 1. Finanzierung ✓ 2. Analyse ✓ 3. Kauf».
   - Entrada de tarjetas: suben/aparecen con **fundido + desplazamiento corto (≈ 10–20 px) + desenfoque que se aclara**, 6–8 cuadros, ease-out; entran en **cascada** con desfase ≈ 3–5 cuadros. Salida: siguen deslizando hacia un borde de la franja y se cortan con el marco (no se desvanecen), o la franja entera corta a la toma.
4. **Chip «€ Echter Vermögensaufbau 101.392€» + «⚠ Gehalt erhalten»**: círculo blanco con «€» negro (≈ 4 % del ancho de franja), texto blanco pequeño, cifra en **cian** que cuenta; segunda línea con triángulo amarillo. Sin caja de fondo (flota directo sobre la toma). Entra a 0,05 s con fundido desde la izquierda en ~4 cuadros.
5. **Degradado negro inferior** detrás de la cifra serif: lineal, de transparente (≈ 55 % del alto) a ≈ 70 % negro en el borde inferior. Entra con la cifra.
6. **Barrido de glow cian** sobre la serif itálica («200,000€», «Marco»): mancha cian con blur grande (≈ 20 px) en modo screen que recorre las letras de izq. a der. en ≈ 0,6–1 s y se apaga a la derecha; deja el texto blanco limpio.
7. **Barra CTA «Trag dich ein»**: rectángulo petróleo `#13706A`, radio 0 (esquinas rectas), ≈ 50 % del ancho de franja, centrado al 80 % del alto. Entra (15,70 s) **como vidrio translúcido** (petróleo al 30 % con desenfoque de fondo) y en ≈ 8 cuadros se vuelve sólido.
8. **Subrayado del titular**: línea de 2 px bajo «Wie fängst du an?», ≈ 70 % del ancho de la frase, con extremos que se desvanecen (degradado transparente → petróleo → transparente).
9. **Logo Deland animado** (17,0–19,5 s, franja 2, fondo `#F4F4F4`): cuatro chevrones petróleo dispersos que **rotan y convergen** (17,0 → 17,5 s) en un hexágono (18,0 s); se rellena el cubo isométrico y aparece el wordmark debajo (18,5 s). Curva suave, ~1,5 s total.
10. **Cierre de agencia**: 25,5 s todo el lienzo se tiñe de cian claro (`#B7F5F5`), las tres franjas se funden en una sola escena UI continua; 26,0 s **rectángulo cian `#14FFFF` con halo** (glow exterior ≈ 60 px) llena el centro; 27,0 s se contrae a un **cuadrado contorneado cian** pequeño sobre blanco; 27,5 s **rota 45° a rombo** y el texto «Searching» se escribe tipo máquina; 28,0 s «Searching Ad» completo; 28,3 s corte duro a **negro** con un rombo grande de contorno grueso cian brillante; 28,35–29,7 s el rombo se **disuelve en partículas cian** (polvo con glow) que vibran.

---

## 6. Apoyos

- Cada idea dicha tiene una tarjeta de UI que la «demuestra»: inversión → tarjeta Investment; cliente → píldora Kunde; plan → Strategie Planung; impuestos → Finanzamt + clic a «Strategie»; sueldo/ingreso → Gehalt con gráfico; financiación → tarjeta Finanzierung «Genehmigt»; ganancia libre de impuestos → tarjeta verde Gewinn que cuenta; inmueble → Immobilie #1.
- Cifras: el dato grande se da con **serif itálica a pantalla de franja** sobre la persona (200,000€ en 9,5–11,2 s; 800,000€ en 18,0–19,6 s).
- Presentación: nombre «Marco» + cargo (15,0–17,0 s); marca: logo Deland (17,0–19,5 s); CTA: «Trag dich ein» (15,7–17,0 s).
- Frecuencia: con tres franjas siempre hay **al menos una con apoyo gráfico en pantalla**; en la escena UI entra un elemento nuevo cada ≈ 0,8–1,2 s (tarjeta, píldora, cursor, check, cifra que cambia). En la suma del lienzo: ~1 apoyo nuevo por segundo.

---

## 7. Persona

- Un solo hombre, camisa blanca, micrófono negro de solapa, sentado a una mesa en una cocina moderna (muebles beige, horno negro a la izquierda, ventana con verde a la derecha). Plano medio frontal, cámara a la altura de los ojos, centrado.
- Recorte: de la cintura/mesa hacia arriba, aire de cabeza ≈ 15 % del alto de la franja. Algunas franjas usan un encuadre ligeramente más cerrado (punch ≈ 110–115 %) para variar entre versiones.
- Tratamiento: a color natural, luz de día suave desde la ventana (derecha de cuadro), sin grade, sin B/N, sin silueta, sin recorte del fondo. El fondo es la cocina real.

---

## 8. Movimiento y transiciones

- **Cámara de la persona**: estática (trípode). Variación solo por cambio de escala entre cortes (jump cut con punch-in/out de ≈ 10–15 %), no hay zoom animado ni temblor.
- **Cámara de la escena UI**: **flotante 3D continua**. Las tarjetas están en perspectiva (rotación Y/X de ≈ 10–20°) y la cámara hace un **dolly/pan lateral lento** hacia la derecha (las tarjetas de la izquierda salen por el borde: 4,5 s «Investment» recortada) y leve rotación orbital (9,0–10,5 s el conjunto se inclina ≈ 25° y se aleja). Movimiento constante, lineal con suavizado leve; las tarjetas nunca se quedan quietas.
- Sí: la cámara de la UI se mueve **mientras** entran las tarjetas (paralaje: las de delante se desplazan más que el fondo de cubos).
- **Transición «dip» por negro → gris → menta** (franja 3, 0,90–1,40 s; repetida en 20,5 s y 22,9–23,0 s): la toma se oscurece a negro en ~3 cuadros, queda negro ~4 cuadros, sube a gris `#4A4A4A` → `#9A9A9A` → `#BFC2C0` y se aclara al menta con las letras ya decodificando. Total ≈ 0,5 s.
- **Texto decodificado / scramble**: «Wie fängst du an?» aparece como caracteres aleatorios borrosos («i y» → «hwq j» → «f gwpi uv» → «Wie gvohtu f w» → «Wie fungst ev bo@» → «Wie fängst du an?»), resolviéndose **de izquierda a derecha** en ≈ 1,0 s (1,3–2,3 s), con desenfoque de movimiento horizontal que se aclara. Mismo recurso en «N bsdp» → «Marco» (15,0 s) y «801-111K» → «800,000€» (18,0 s).
- **Corte duro** entre toma y UI dentro de cada franja (ej. 1,30 s franja 1; 6,20 s franja 2; 7,73 s franja 1; 22,63 s franja 1; 25,77 s franja 2), sin transición.
- **Contadores**: cifras que suben de forma continua (lineal) durante todo el plano.
- **Desfase entre franjas**: las tres versiones corren el mismo material con distinto montaje, así los cortes de cada franja caen en tiempos distintos y el lienzo nunca corta entero a la vez (salvo 25,77 s y el cierre). El bloque 20–25 s repite el arranque (bucle de muestra).
- Curvas: entradas ease-out suaves (expo out), sin rebote ni overshoot; nada de stop-motion. Sensación «producto de software», pulida.

Cortes medidos y qué cambia:
0,03 · 1,30 · 6,20 · 7,73 · 10,57 · 11,23 · 15,70 · 16,83 · 19,57 · 22,63 · 25,77 · 28,30.

---

## 9. Subtítulos

- Sí, en las franjas de persona: **1–2 palabras** a la vez («Steuervorteile», «fast selbst», «weiter ausbauen», «tragt», «Einnahmequelle», «Wenn du», «hier bist,», «wirst du», «Das sind», «dann insgesamt», «bis ins Alter»).
- Posición: centrado horizontal, al ≈ 85 % del alto de su franja (sobre las manos).
- Tamaño pequeño: ≈ 3 % del ancho del lienzo de alto de letra (≈ 33 px en 1080), Inter Medium blanco con sombra difusa suave.
- **No se marca palabra clave** con color; la palabra clave se saca del subtítulo y se convierte en apoyo (serif grande o tarjeta de UI) en otra franja.
- Cambio de palabra en corte seco, sin animación de entrada.

---

## 10. Reglas del sistema

1. Lienzo blanco `#FDFFFC` con tres franjas 16:9 al 80 % del ancho, separadas ≈ 1 % y centradas; nunca a pantalla completa hasta el cierre.
2. Toda la UI son **tarjetas blancas** de radio ≈ 3 % del ancho, borde 1 px `#E4E9E4` y sombra suave abajo; nada de contornos gruesos ni sombras duras.
3. Fondo de UI siempre menta `#EFF6F0` con el **patrón de cubos de marca** a ≈ 10 % de opacidad.
4. Paleta fría análoga (menta, verde agua `#B7D9D4`, petróleo) + **un solo acento cian** que se usa para brillo, estado activo y la cifra clave.
5. La escena UI **siempre se mueve** en 3D (perspectiva de 10–20° + deriva lateral lenta); la persona siempre está quieta.
6. Cada cifra **cuenta** en vivo; ningún número aparece estático.
7. El dato grande o el nombre se pone en **serif itálica blanca** sobre degradado negro, con un **barrido de glow cian**.
8. Titulares y cifras clave entran **decodificándose** de izquierda a derecha en ≈ 1 s.
9. Subtítulo pequeño, 1–2 palabras, centrado abajo, blanco liso; la palabra clave se vuelve apoyo, no color.
10. Las tarjetas entran en cascada (desfase 3–5 cuadros) con fundido + desenfoque + desplazamiento corto, ease-out; salen deslizando fuera del borde.
11. Interacción simulada (cursor de mano, clic, estado que cambia a cian) para «demostrar» lo que se dice.
12. Pasos entre bloques con dip negro → gris → menta de ≈ 0,5 s o corte seco; nunca whip ni zoom de transición.

---

## 11. Qué NO hace

- No usa grano, ruido, halation, viñeta, aberración, scanlines, polvo, papel ni semitono.
- No recorta a la persona ni pone nada detrás de ella; no B/N, no silueta, no grade de color.
- No mueve la cámara sobre la persona (ni zoom lento, ni temblor, ni whip); solo cambios de escala en el corte.
- No usa colores saturados salvo el cian; no hay amarillos/rojos fuertes (solo el triangulito ⚠ y la píldora rosada).
- No pone subtítulos grandes ni palabra resaltada; no usa mayúsculas gritonas.
- No usa transiciones llamativas (glitch, whip pan, zoom blur) entre planos, salvo el cierre de marca.
- No usa emojis, íconos de stock ni fotos de stock: los apoyos son UI hecha a medida.
- No tiene rebote/overshoot ni animación a 12 cps.

---

## 12. Tabla de momentos

(F1 = franja superior, F2 = media, F3 = inferior)

| Segundo | Qué se ve | Recurso |
|---|---|---|
| 0,00–0,03 | F1 persona «Steuervorteile», F2 persona con encuadre más cerrado, F3 persona | arranque, el bloque se asienta (escala 104 → 100 %) |
| 0,03–1,30 | F1 persona («fast selbst», «tragt»); F2 persona + chip «€ Echter Vermögensaufbau» con cifra cian que cuenta; F3 persona «weiter ausbauen» que se va a negro (0,9–1,1 s) y sube a gris | chip flotante, dip a negro en F3 |
| 1,30–6,20 | F1 corta a UI: tarjeta Investment (1,3), píldora Kunde sube (2,5), Strategie Planung entra por la derecha (3,5–4,0) y la cámara se desliza a la derecha; F2 persona («Einnahmequelle», «Startkapital», «Vermögensaufbau»); F3 menta: «Wie fängst du an?» se decodifica (1,3–2,3), luego (3,5) corte a tarjeta Gehalt con cifra 2.510€ → 2.940€ | corte seco a UI, scramble serif, cascada de tarjetas, contador |
| 6,20–7,73 | F2 corta a UI Finanzamt; entra el cursor de mano por la derecha (6,25), clic (7,5) → píldora cian «Strategie»; F1 Strategie Planung + Langfristiger Vermögensaufbau; F3 Gehalt sube a 3.000€ y se inclina | interacción simulada, estado activo cian |
| 7,73–10,57 | F1 vuelve a persona («als sich», «die Immobilie»); F2 Finanzamt con «Steuerstrategie aktiv» y aparecen tarjetas Immobilien / Steuervorteile (8,0–9,0) mientras la escena rota y se aleja; F3 Gehalt + Finanzierung «Genehmigt»; 9,5 s F1 «200,000€» serif itálica con barrido cian | órbita 3D, cifra serif + glow |
| 10,57–11,23 | F1 «200,000€» quieto; F2 corta a persona («Wenn du», «hier bist,»); F3 Finanzierung | corte seco UI → persona |
| 11,23–15,70 | F1 corta a tarjeta verde Gewinn 20€ → 90.000€ (cuenta, tarjeta inclinada en perspectiva que se acerca); F2 persona («wirst du», «für dich arbeitet»); F3 Gehalt + Immobilie #1 + Prozess con checks; 15,0 s F2 «N bsdp» → «Marco» decodifica con glow cian | contador, perspectiva, scramble del nombre |
| 15,70–16,83 | F1 Gewinn 90.000€; F2 «Marco» + «Gründer und Geschäftsführer»; F3 corta a persona y entra la barra «Trag dich ein» de vidrio a sólido | rótulo de nombre, CTA |
| 16,83–19,57 | F1 vuelve a persona («Das sind», «dann insgesamt»); F2 «Marco» → 17,0 s logo Deland se arma (chevrones → hexágono → cubo + wordmark, 17,0–18,5); F3 «Trag dich ein» y luego persona; 18,0 s F1 «801-111K» → «800,000€» con glow | logo animado, scramble de cifra |
| 19,57–22,63 | F2 corta a persona con chip «Echter Vermögensaufbau» (bucle del inicio); F1 «800,000€» se apaga (19,6) y vuelve a persona; F3 persona («Beste», «bis ins Alter», «weiter ausbauen») → negro (20,5) → «Wie fängst du an?» se decodifica otra vez (21,0–22,0) | repetición del arranque, dip a negro, scramble |
| 22,63–25,77 | F1 corta a Investment + Kunde + Strategie Planung (deriva a la derecha); F2 persona («Einnahmequelle», «Vermögensaufbau»); F3 dip gris/negro (22,9–23,0) → Gehalt contando | corte seco, dip, contador |
| 25,77–28,30 | F2 corta a UI Finanzamt y las 3 franjas forman una escena UI continua; el lienzo se tiñe de cian (25,5–26,0); rectángulo cian con halo (26,0–26,5); se contrae a cuadrado contorneado sobre blanco (27,0); rota a rombo + «Searching» se escribe (27,5); «Searching Ad» (28,0) | fusión de franjas, inundación cian, logo de agencia |
| 28,30–29,70 | Corte a negro: rombo grande cian brillante (28,3) que se deshace en partículas con glow alrededor del logo «Searching Ad» blanco | corte duro, partículas cian, firma final |
