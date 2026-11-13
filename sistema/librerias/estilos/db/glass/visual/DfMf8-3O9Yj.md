# DfMf8-3O9Yj — estudio visual (glass)

Reel **horizontal 16:9**, 26,37 s, **sin persona hablando**: es un anuncio de producto (constructor de webs con IA, "Blink") armado **100 % con interfaz animada**: tarjetas de UI flotando sobre gris perla, tipeo en vivo, planos en 3D inclinados y dos fotos de "persona trabajando" como fondo. 12 cortes (27,3/min), plano medio 2,03 s (0,67–5,3 s).

## 1. Sistema en una frase
**UI de producto "Apple/Linear" sobre fondo gris perla #E7E5EA, con tarjetas blancas de esquina redonda y sombra difusa que aparecen escribiéndose (cursor de tipeo), y cada idea se cuenta con un componente de interfaz nuevo; el tramo técnico se va a negro #1B1719.**
Reconocible en 1 s: fondo gris casi blanco sin nada, una sola burbuja/caja de texto blanca en el centro con texto que se escribe letra a letra y un cursor parpadeando.

## 2. Color
| HEX | % | Rol | Dónde |
|---|---|---|---|
| #E7E5EA | 38,3 | Fondo principal (gris perla frío, levemente lila) | 0–12 s y 22–26 s, detrás de todas las tarjetas |
| #1B1719 | 23,7 | Fondo oscuro / texto | 16,3–20,6 s (pantalla negra, editor de código), panel "Core Systems", botones negros (enviar ↑, "Publish") |
| #F0EEEF | 12,7 | Superficie de tarjeta / degradado del fondo | tarjetas de chat, barra de prompt, variaciones del fondo |
| #72523C | 6,5 | Marrón cálido de las fotos | suéter/escritorio de las fotos "persona trabajando" (12,3 s y 20,6 s), bolso marrón |
| #FAF8FB | 5,9 | Blanco de tarjeta | caja de prompt, mock de webs |
| #789EC2 | 4,4 | Azul cielo / acento | cielo detrás de los mock-ups (10,97 s), banners "Style for Every Moment" / "Spring Summer", palabra "Bold Fashion" azul |
| #CBD1D3 | 4,3 | Gris de sombra / burbuja de usuario | burbuja gris del mensaje del usuario, sombras |
| #B6A38D | 4,1 | Beige de fotos de moda | fondos de producto |

- Armonía: **monocroma neutra + un acento azul** (#789EC2 / azul botón ~#2F6BFF). En el panel oscuro aparecen acentos de sistema (rojo ~#F04B3E, amarillo ~#F5B21A, celeste ~#6EB6F0, azul ~#3D5BFF) como íconos de categoría tipo iOS. En el tramo negro: verde lima ~#9BC34A (flecha →, palabra "push") y violeta ~#8B6CF0 (cursor).
- Saturación medida 0,06: casi todo gris; el color solo vive en las fotos y los íconos.
- Luz media 0,66, contraste 0,35: imagen clara, suave, sin negros duros salvo el tramo negro.
- Grade: ninguno sobre la UI (render vectorial limpio). Fotos de persona: cálidas, ámbar/tungsteno (lámpara), sombras marrones levantadas, look "foto de stock IA cálida".
- Grano: no. Viñeta: no. Halation/bloom: no; solo un **glow suave** muy leve detrás de los objetos.
- **Desenfoque**: sí, protagonista. El orbe inicial es una esfera desenfocada (gaussiano fuerte); los elementos que entran o salen pasan por **motion blur / blur de enfoque**; el fondo de cielo a 10,97 s está ligeramente desenfocado (profundidad).

## 3. Tipografía
Una sola familia de sistema: **sans grotesca neutra tipo SF Pro / Inter**. Equivalente Google Fonts: **Inter** (o Geist para el titular de la web).
| Rol | Caja | Peso | Ancho | Tracking | Tamaño (% ancho) | Color | Efecto |
|---|---|---|---|---|---|---|---|
| Texto tipeado en burbuja/prompt ("What can I get done for you today?", "Generating the images", "Adding the ui") | frase normal | Regular 400 | normal | 0 | 2–3 % (prompt grande 9 s: ~3,5 %) | #1B1719 | sin borde, dentro de caja blanca |
| Titular de mock-up web ("Elevate Your Style With **Bold Fashion**") | Title Case | Black/Heavy 800–900 | normal-condensada | −1 a −2 % | ~6 % dentro de la tarjeta | negro + 2.ª línea azul | ninguno |
| Título de panel ("Core Systems", "Authentication", "Payment", "Security", "User Flow") | Title Case | Medium 500 | normal | 0 | 5 % (Core Systems) / 3,5 % (categorías) | blanco sobre #1B1719 | tipeo letra a letra |
| Frase grande sobre negro ("→ When something **breaks**") | frase | Medium 500 | normal | −1 % | ~5 % | blanco; palabra clave naranja ~#E8A050 con **resaltado de selección** (caja gris-azul como texto seleccionado en editor) | flecha verde lima delante |
| Código ("app.locals.startBtnLabel = …") | monoespaciada en estilo | Regular | — | 0 | ~1,3 % | blanco, amarillo, verde, violeta (sintaxis) | una línea resaltada azul como selección |
| Píldora sobre foto ("Make Ideas Real.") | frase | Regular | normal | 0 | ~3 % | blanco | **píldora de vidrio**: fondo blanco 15–20 % + borde 1 px blanco 40 % + blur detrás |
| Botón ("Publish", "Build it with blink.") | frase | Medium | normal | 0 | ~2 % | blanco sobre negro / negro sobre gris | caja negra radio ~4 px |
| CTA final ("Comment BLINK to get the link") | frase, BLINK en mayúsc. | Medium 500 | normal | 0 | ~3,5 % (línea ocupa 34 %) | #1B1719 | ninguno, centrado |
Alineación: todo centrado al cuadro o alineado a la izquierda dentro de su tarjeta; una línea, nunca apilado en bloques.

## 4. Composición
- Sin retícula rígida: **centro óptico** del cuadro para el elemento activo (caja de prompt, botón, frase), y **mosaico flotante disperso** (bento suelto) cuando hay muchos componentes (8,17–10,97 s), con tarjetas cortadas por los bordes del cuadro para dar sensación de espacio mayor.
- Márgenes: elemento solitario a ~40 % del alto, ancho 25–45 % del cuadro; mosaico ocupa 100 % con sangrado.
- Persona: solo en fotos-apoyo. 12,3 s: foto del hombre en el tercio izquierdo (35 % del ancho) junto al panel oscuro a la derecha (40 %), ambos como tarjetas sobre gris. 20,6 s: foto de la mujer a pantalla completa, la píldora de vidrio **delante** de ella, a la altura del hombro, centrada-izquierda.
- Nada queda detrás de la persona (no hay recorte de silueta).

## 5. Elementos gráficos
1. **Orbe degradado** (0–1,4 s): círculo ~10 % del ancho, desenfoque gaussiano fuerte, colores azul marino/verde esmeralda → amarillo; rota/morfea el color, se desplaza diagonal de arriba-izquierda hacia el centro y se encoge hasta convertirse en el avatar del "Agent" (1,4 s). Transición = morph de escala.
2. **Burbujas de chat** (1,5–3 s): agente en blanco #FAF8FB, radio ~8 px, sombra muy suave; usuario en gris #CBD1D3 desplazada a la derecha. Avatar 1,5 % + etiqueta "Agent" gris. Entran con escala 0,9→1 + fundido en ~3 cuadros; el texto se escribe ~12–15 caracteres/s. El chat sube suavemente a medida que entra el siguiente mensaje.
3. **Tarjeta blanca vacía** (3,5 s): rectángulo blanco radio ~6 px que crece desde el centro → se llena con el mock-up web (4 s). Sombra difusa suave hacia abajo (blur ~30 px, 10 % negro).
4. **Mock-up de web** (4–5,3 s, 10,97–12,3 s): tarjeta grande 45–65 % del ancho, radio ~10 px, sombra suave; dentro: nav, titular negro + azul, grilla de fotos de moda. A 10,97 s es un "dashboard" con borde de **vidrio esmerilado** (marco blanco translúcido con blur del cielo detrás) — el único glass literal además de la píldora.
5. **Caja de prompt** (6,67–8,17 s): barra blanca ancha (~45 % → 70 %) radio ~10 px, con "+", selector "Blink 2.0 Pro", "Agent", botón negro ↑ (o azul cuando se presiona). Alrededor, **glifos flotantes** ("/", "<", ">", "*", "-") grises pequeños dispersos que derivan lento — partículas de código.
6. **Píldora de estado** (8,17–10,97 s): caja blanca chica con texto de proceso ("Generating the images|", "Adding the ui", "Preparing the website") + botón negro ↑ a la derecha; sigue fija en el centro mientras alrededor el mosaico cambia.
7. **Componentes bento** (8,2–11 s): banners de moda (azul, radio 10 px), widget clima "24°", tarjeta "New Collection", "Trending Oversized Blazer $129", reseña ★★★★★, carrito "Your Cart", filtros-píldora (All/Women/Men), stat "$12,480", botón "AI Assistant" negro. Entran **uno a uno** en cascada (~1 cada 0,15–0,25 s), deslizando 3–6 % desde fuera del cuadro + fundido, con ease-out; la toma entera deriva lentamente.
8. **Panel oscuro "Core Systems"** (12,3–16,27 s): tarjeta #1B1719 radio ~6 px; 4 filas con ícono cuadrado redondeado de color (rojo, amarillo, celeste, azul) + título + fila de etiquetas-píldora de su color. Cada fila aparece en cascada (12,35–12,6 s, ~2 cuadros entre filas); los títulos se escriben a máquina. Desde 13,4 s el conjunto **gira en 3D** (perspectiva, rotación Y ~15–25°, tilt) y hace push-in hasta salirse del cuadro (16 s). Un **cursor/ícono flecha azul** cuadrado aparece a 15,5 s como "acción".
9. **Flecha verde + cursor violeta** (16,27–17,5 s): "→" verde lima y barra de cursor violeta en negro; el texto "When something breaks" se tipea; la palabra clave recibe **caja de selección** (como texto seleccionado).
10. **Editor de código** (18–20,6 s): marco de ventana fino gris oscuro (1 px, #2A2628), primero muestra "→ push … .cain" (texto tipeado/borrado), luego crece a editor con sidebar de íconos y líneas de código que se escriben; una línea con resaltado de selección azul.
11. **Píldora de vidrio** sobre foto (20,6–21,8 s): entra con fundido + desenfoque→enfoque en ~4 cuadros, el texto "Make Ideas Real." se tipea dentro.
12. **Botón "Publish"** con **puntero de mouse** (21,8–23 s): botón negro radio ~4 px; el puntero gris entra desde abajo-derecha y hace clic; el botón se encoge (press, escala ~0,95) y se transforma en contorno "Build" → "Build it with blink." (morph de botón a texto).
13. **CTA** (24–26 s): texto negro solo, centrado sobre gris; cierre con corte a negro a ~26 s.

## 6. Apoyos
No hay toma de persona hablando: **el apoyo ES el video**. Cada frase de la locución tiene su componente: pregunta → burbuja; pedido → prompt; resultado → mock-up; proceso → píldora de estado + componentes; "sistemas" → panel; "cuando algo se rompe" → frase sobre negro + código; "haz tus ideas realidad" → foto cálida de persona; "publica" → botón + clic. Un apoyo nuevo cada **~0,2 s en el mosaico** y un plano nuevo cada 2,03 s.

## 7. Persona
Solo dos fotos de stock/IA como apoyo emocional: hombre de perfil 3/4 con laptop y lámpara (12,3 s, plano medio, luz tungsteno cálida, fondo oscuro marrón) y mujer de espaldas 3/4 con laptop, ventana luminosa, plantas y lámpara roja (20,6 s, plano medio, luz natural de ventana, paleta marrón/crema). Color natural cálido, sin B/N ni silueta. Funcionan como "respiro humano" entre tramos de UI.

## 8. Movimiento y transiciones
- Animación: **suave, de producto (estilo keynote Apple)**: ease-out largo (cubic/quint), sin rebote, sin overshoot visible; entradas de 3–6 cuadros a 30 cps; tipeo constante con cursor.
- Cámara virtual: **flotante continua** (deriva lenta + leve zoom-in) en casi todos los planos; **push-in 3D con rotación** en el panel (13,4–16,2 s); el mock-up de 10,97 s aparece ya en perspectiva leve con cielo detrás.
- La cámara SÍ se mueve mientras entran apoyos (el mosaico deriva mientras caen las tarjetas).
- Transiciones (con los cortes medidos):
  - 5,3 s: **zoom-out + reencuadre** — el mock-up se encoge a la derecha y aparece el chat a la izquierda (vista de app completa).
  - 6,67 s: corte seco a la caja de prompt sola (zoom-in de la barra).
  - 8,17 s: corte a mosaico; el prompt queda como píldora pequeña central (match por forma).
  - 9,2 / 9,87 s: cortes por cambio de texto de estado; el mosaico salta a nuevo encuadre más abierto (zoom-out en escalones).
  - 10,97 s: corte a mock-up con cielo (revelado del resultado).
  - 12,3 s: corte duro a gris con foto + panel oscuro que se construye.
  - 13,4 s: comienza la rotación 3D (no es corte de contenido, es cambio de ángulo).
  - 14,97 s: segundo escalón del giro (más inclinado), entra fila "User Flow".
  - 16,27 s: **corte a negro** total con flecha verde (cambio de clima: problema).
  - 20,6 s: corte de negro a foto cálida (solución).
  - 21,8 s: corte a gris con botón (acción).
  - ~23–24 s: morph del botón a texto; 26 s fundido/corte a negro.

## 9. Subtítulos
No hay subtítulos de locución. El texto en pantalla es **diegético** (vive dentro de la interfaz: burbujas, prompts, estados, botones). Palabra clave marcada por **color + caja de selección** ("breaks" en naranja con resalte) o por **segundo color** en el titular ("Bold Fashion" en azul). Máximo 1 línea, 2–8 palabras.

## 10. Reglas del sistema
1. Fondo gris perla #E7E5EA liso; nada de texturas, grano ni viñeta.
2. Todo texto entra **escribiéndose** con cursor (12–15 car/s), nunca aparece de golpe.
3. Un elemento activo al centro; si hay muchos, mosaico bento disperso con tarjetas cortadas por el borde.
4. Tarjetas blancas, radio 6–10 px, sombra difusa muy suave (≈10 % negro, blur grande, hacia abajo).
5. Una sola familia sans neutra (Inter); jerarquía por peso y tamaño, no por fuente.
6. Color casi nulo (saturación ~0,06); un acento azul y colores de sistema solo en íconos/etiquetas.
7. Entradas ease-out suaves de 3–6 cuadros, en cascada cada 0,15–0,25 s; sin rebotes.
8. La cámara siempre deriva (flotante/push-in); los planos de "sistema" giran en 3D con perspectiva.
9. Cambio de clima = cambio de fondo: gris claro (producto/solución) ↔ negro #1B1719 (problema/técnico).
10. Fotos humanas cálidas solo como respiro (≤1,3 s cada una) con una píldora de vidrio esmerilado delante.
11. Cada plano ~2 s; ritmo 27 cortes/min.
12. Cierre: botón + puntero que hace clic → morph a frase → CTA de texto solo.

## 11. Qué NO hace
- No hay persona hablando a cámara ni subtítulos de locución.
- No grano, no ruido, no halation, no light leaks, no viñeta, no aberración cromática, no CRT.
- No sombras duras, no trazos gruesos, no tipos serif ni condensados de impacto, no mayúsculas sostenidas.
- No rebotes ni animaciones elásticas; no whip pans ni temblor de cámara.
- No saturación alta ni paletas complementarias fuertes.
- No stickers, emojis ni íconos ilustrados; solo UI.

## 12. Tabla de momentos
| Segundo | Qué se ve | Recurso |
|---|---|---|
| 0–1,4 | Orbe azul/verde→amarillo desenfocado que viaja al centro y se encoge | Blur gaussiano, morph de color y escala → se vuelve avatar |
| 1,4–3,3 | Chat: "What can I get done for you today?" / "Create a modern, colorful fashion e-commerce website." | Burbujas blanca y gris, tipeo |
| 3,3–5,3 | Tarjeta blanca crece → mock-up "Elevate Your Style With Bold Fashion" | Escala desde el centro, sombra suave, deriva |
| 5,3–6,67 | Vista de app: chat izq + preview der | Zoom-out/reencuadre |
| 6,67–8,17 | Caja de prompt sola; prompt largo se escribe; glifos de código flotando; clic en ↑ | Tipeo, partículas "/ < > *", botón pasa a azul |
| 8,17–9,2 | Píldora "Generating the images" + fotos de moda entrando | Mosaico, cascada de tarjetas |
| 9,2–9,87 | "Adding the ui" + clima, reseñas, carrito, filtros | Cascada ~0,2 s, deriva |
| 9,87–10,97 | "Preparing the website" + stat $12,480, AI Assistant | Zoom-out en escalón, más componentes |
| 10,97–12,3 | Dashboard "Lumière – Timeless Style" sobre cielo azul | Marco de vidrio esmerilado, profundidad |
| 12,3–13,4 | Foto hombre (izq) + panel oscuro "Core Systems" construyéndose | Cascada de filas, tipeo de títulos |
| 13,4–14,97 | Panel gira en 3D, filas Authentication/Payment/Security | Rotación Y + push-in suave |
| 14,97–16,27 | Más inclinado; entra "User Flow"; ícono flecha azul | Perspectiva 3D, push-in hasta sangrar |
| 16,27–18 | Negro: "→ When something breaks" (breaks resaltado) | Tipeo, flecha lima, cursor violeta, caja de selección |
| 18–20,6 | Ventana de editor; "push … .cain" → código que se escribe | Marco 1 px, sintaxis de color, línea seleccionada |
| 20,6–21,8 | Foto mujer en laptop + píldora "Make Ideas Real." | Píldora de vidrio con blur, tipeo |
| 21,8–24 | Botón negro "Publish" + puntero que hace clic → "Build" → "Build it with blink." | Press + morph de botón a texto |
| 24–26,37 | "Comment BLINK to get the link" centrado sobre gris; negro final | Texto solo, CTA |
