# Ddk09yCNf4m — «Design Styles» (lista numerada + póster que cambia)

Cuadro de referencia: 360×640 (9:16). Duración 19,87 s. **Un solo plano, 0 cortes** (medido). Las medidas en % salen de los cuadros grandes `t_0013.0.jpg` y `t_0019.5.jpg`.

## 1. Sistema en una frase
Una toma fija a cámara con una **lista numerada 1–22 ya dibujada en vacío** a la izquierda que se va llenando renglón a renglón, y un **póster de muestra** encima de la cabeza que se cambia por corte seco cada ~0,9 s con cada estilo nombrado.
**Se reconoce en 1 segundo por:** la columna de números vacíos «1. 2. 3. … 22.» a la izquierda (promete el recorrido completo) + el título negro condensado «Design Styles» + un recuadro de imagen sobre la cabeza.

## 2. Color
Paleta medida (casi todo es la grabación; los gráficos no traen color propio, el color lo trae cada póster):

| HEX | % | Rol / dónde |
|---|---|---|
| #807E78 | 20,0 | Pared y cortina gris-beige (fondo medio) |
| #9E958A | 19,4 | Cortina beige iluminada (fondo izquierdo, detrás de la lista) |
| #736358 | 13,4 | Sombras de la cortina, piel en sombra |
| #313131 | 11,6 | Sillas y mesas negras del fondo, título «Design Styles» |
| #BBB3A9 | 10,1 | Camisa en sombra, portátil gris |
| #4F4946 | 9,7 | Sombras del cuarto, pelo |
| #E3DDD7 | 8,9 | Camisa blanca iluminada, techo, letras de la lista (blanco) |
| #A07C69 | 6,8 | Piel |

- Armonía: **monocroma neutra cálida** (grises beige) con saturación 0,08 medida → el ÚNICO color fuerte del cuadro es el póster (rojo de «Maximalism», magenta del oso, cian de «QANDOX», verde de «Liquid Glass»). El póster es el acento y cambia en cada renglón.
- Grade: ninguno visible; luz natural de oficina, luz media 0,5, contraste bajo 0,19, negros sin levantar ni aplastar. Ligera dominante cálida.
- Grano: no (solo compresión de celular). Viñeta: no. Halation, bloom, glow, aberración cromática, scanlines, polvo, papel, semitono, light leak: **no**. Profundidad: la del celular, fondo apenas suave.

## 3. Tipografía
| Rol | Letra | Mayúsc. | Peso / ancho | Tamaño | Color y borde | Google Fonts |
|---|---|---|---|---|---|---|
| Título «Design Styles» | Grotesca condensada tipo Impact/Haettenschweiler | Tipo título (D y S mayúsculas) | Black, condensada, tracking 0 o un pelo cerrado | ancho del bloque ≈ 40 % del cuadro (x 8 %→48 %); alto de mayúscula ≈ 3,4 % del alto (≈ 6 % del ancho) | Negro #1E1E1E con **trazo blanco fino (~1 px a 360)** y sombra suave oscura abajo | **Anton** (o Oswald 700) |
| Números «1.»…«22.» | Helvética/Arial | — | Regular | x-height pequeña, cifra ≈ 3,6 % del ancho; alineados a la DERECHA en x ≈ 12 % | Blanco #F2F2F2 con sombra negra suave (blur 2–3 px, sin desplazamiento claro) | **Inter** 400 / Arimo |
| Nombre del estilo | Helvética/Arial | Tipo título («Swiss Design») | Regular, ancho normal, tracking 0 | igual que los números; el renglón más ancho («Glassmorphism») ≈ 26 % del ancho | Blanco con la misma sombra suave | **Inter** 400 / Arimo |

- Alineación: todo a la izquierda; número + punto, espacio, nombre (columna del nombre en x ≈ 14 %).
- Interlineado: 22 renglones de y 14,7 % a y 77,7 % → **paso de 3,0 % del alto** (≈ 1,35 × cuerpo). Muy apretado, lista tipo índice.
- Apilado: vertical estricto, un estilo por renglón, nunca dos columnas.

## 4. Composición
- Retícula de 2 columnas: **izquierda (x 8–50 %)** = título + lista; **derecha (x 55–86 %)** = póster arriba, persona abajo.
- Título: y 9–12,5 %. Lista: y 14–78 %. Margen izquierdo ≈ 8 % (título) / 6 % (números).
- Póster: x 55 %→86 % (≈ 31 % del ancho), y 9,7 %→31,5 % (≈ 22 % del alto); proporción ≈ 4:5 vertical. Su borde superior **alineado con la línea alta del título**.
- Persona: centrada-derecha (eje en x ≈ 70 %), cabeza y 32–47 %, ocupa ≈ 55 % del ancho y del alto desde el pecho hasta abajo; el portátil gris tapa el 20 % inferior derecho (y 80–100 %).
- Capas: fondo (cuarto) → persona → lista y póster ENCIMA de todo. La lista pisa la cortina y el brazo izquierdo de la persona (x ~40–48 % en los renglones 14–22 cruza la camisa/brazo; queda legible por la sombra). El póster nunca toca la cabeza: hay ≈ 0,5 % de aire entre su borde bajo y el pelo.
- Franja segura: todo el contenido entre y 9 % y 78 %; la parte baja queda limpia (persona + portátil) para la UI de IG.

## 5. Elementos gráficos
1. **Título «Design Styles»** — fijo desde el cuadro 0 hasta el final; no entra ni sale, no se mueve.
2. **Columna de números 1–22** — fija desde el cuadro 0, completa y vacía. Es el «andamio»: el espectador ve cuántos faltan.
3. **Renglón del nombre** — aparece por **corte seco en 1 cuadro** (0,80 s sin texto → 0,90 s «Maximalism» completo; igual en 1,90→2,00 y 2,80→2,90). Sin fundido, sin escritura, sin deslizamiento, sin resaltado del renglón nuevo. Los anteriores se quedan (acumulación).
4. **Póster de muestra** — rectángulo de esquinas rectas (radio 0), sin marco, sin trazo, sin sombra visible, opaco, a 31 % de ancho. Es una imagen real del estilo (afiche Bauhaus para Swiss, interfaz verde translúcida para Liquid Glass, oso pop magenta para Pixel Art, etc.). **Reemplazo por corte seco** en el MISMO cuadro en que aparece el nombre: sin transición, sin escala, sin rebote.
- No hay otros gráficos: ni íconos, ni flechas, ni barras, ni subrayado, ni marcador de «renglón actual».

## 6. Apoyos
- Un apoyo por idea, y la idea es un nombre: **cada estilo = 1 póster que lo ejemplifica**. 22 apoyos en 19,9 s → **un apoyo cada ~0,9 s (≈ 66 por minuto)**.
- El apoyo es siempre del mismo tipo (afiche vertical) y en el mismo lugar; lo que cambia es solo el contenido, por eso la densidad altísima no satura.
- Sincronía: el nombre y el póster entran en el cuadro en que la persona dice la palabra.

## 7. Persona
- Plano medio corto (cabeza a cintura), sentado detrás de un portátil, de frente a cámara, mirada a lente.
- Gesto constante: **índice levantado** («número uno») toda la toma, junto a la cara.
- A color natural, sin recorte, sin silueta, sin B-N. Fondo real: oficina con cortinas beige, escritorios blancos y sillas negras; techo con luminaria arriba (y 0–5 %).
- Luz: ambiente de oficina suave, cara bien iluminada de frente, sin contraluz.

## 8. Movimiento y transiciones
- Cámara: **estática** (celular en trípode); micro-reencuadres casi nulos, solo se mueve la persona. Sin push-in, sin punch, sin whip, sin temblor.
- Cortes de toma: **ninguno** (cortes_s = [], plano único de 19,87 s).
- Las únicas «transiciones» son los reemplazos secos del póster + renglón (≈ 22 en total, cada ~0,9 s; el más largo, Glassmorphism ≈ 6,0→7,5 s).
- La cámara no reacciona cuando entra un apoyo.

## 9. Subtítulos
No hay subtítulos de lo que dice. La lista hace de subtítulo: cada palabra clave que pronuncia queda escrita como renglón. Palabra clave = el renglón entero (1–2 palabras), sin color de marca ni resaltado.

## 10. Reglas del sistema
1. Mostrar desde el cuadro 0 la estructura completa vacía (números 1…N) para que el espectador sepa el recorrido y se quede hasta el final.
2. Título fijo arriba-izquierda, grotesca black condensada negra con trazo blanco fino; nunca se anima.
3. Lista en sans regular blanca con sombra suave, paso de 3 % del alto, números alineados a la derecha.
4. Cada renglón entra por corte seco en 1 cuadro, en la palabra dicha; nunca animado.
5. Cada renglón trae a la vez un póster que lo ejemplifica, en el mismo cuadro.
6. Un solo póster en pantalla, siempre en el mismo sitio (31 % de ancho, sobre la cabeza, alineado con el título); el nuevo reemplaza al anterior.
7. Póster rectangular, sin marco, sin sombra, sin radio.
8. Ritmo fijo de ~0,9 s por elemento (≈ 66/min); toda la serie del mismo estilo de apoyo.
9. Una sola toma fija, sin cortes ni zooms; la energía la ponen los cambios de imagen.
10. El color lo aporta solo el póster; el resto del cuadro queda neutro sin grade.
11. Nada tapa la cara; la parte inferior (y > 80 %) queda libre.
12. Termina con la lista completa (22/22) en pantalla: el último cuadro es el «resumen» guardable.

## 11. Qué NO hace
- No corta la toma, no hace zoom ni punch-in, no mueve la cámara.
- No anima nada: sin ease, sin rebote, sin escritura letra a letra, sin fundidos, sin deslizamientos.
- No resalta el renglón actual ni tacha los anteriores.
- No usa subtítulos de la voz, ni color de marca, ni íconos, ni flechas.
- No pone texturas (grano, halation, papel, viñeta) ni grade.
- No pone dos imágenes a la vez ni marco/sombra al póster.
- No usa retícula suiza estricta ni Helvética Bold grande: el «swiss» aquí es solo el orden (lista alineada, columnas, una imagen) y uno de los pósteres (Bauhaus, 13,0 s).

## 12. Tabla de momentos (plano único 0–19,87 s; renglones = recurso)
| Segundo | Qué se ve | Recurso |
|---|---|---|
| 0,0 | Título + 1–22 vacíos, «1. Minimalism», póster minimalista crema con figura roja | Estructura completa desde el cuadro 0 |
| 0,9 | «2. Maximalism» + afiche rojo-amarillo «SABRINA» | Corte seco renglón + póster |
| 2,0 | «3. Futuristic» + afiche gris «FUTURE» | Corte seco |
| 2,9 | «4. Vector Art» + ilustración vectorial de rostro | Corte seco |
| ~4,0 | «5. Collage Art» + collage «MUMBAI» | Corte seco |
| ~4,5 | «6. Retro» + TV antigua «STATIC» | Corte seco |
| ~5,5 | «7. Pop Art» + afiche amarillo-negro | Corte seco |
| ~6,0 | «8. Glassmorphism» + flores tras vidrio | Corte seco (el más largo, ~1,5 s) |
| ~7,5 | «9. Neumorphism» + objeto blanco en relieve | Corte seco |
| ~8,0 | «10. Cyberpunk» + «AFTER HOURS» rojo-negro | Corte seco |
| ~9,0 | «11. Clay Style» + letras infladas «BIGGER» rojo-amarillo | Corte seco |
| ~10,0 | «12. Pixel Art» + oso pop magenta | Corte seco |
| ~11,0 | «13. Editorial» + revista con collage | Corte seco |
| ~12,0 | «14. Y2K» + figura cromada azul | Corte seco |
| 13,0 | «15. Swiss Design» + afiche «bau haus» con círculo rojo | Corte seco |
| ~13,5 | «16. Surreal Design» + «QANDOX?» cian con nubes | Corte seco |
| ~15,0 | «17. Bohemian» + ilustración terracota | Corte seco |
| ~15,5 | «18. Victorian» + grabado sepia | Corte seco |
| ~16,5 | «19. Graffiti» + letras verde ácido | Corte seco |
| ~17,0 | «20. Aurora» + «AURORAE» degradado violeta | Corte seco |
| ~18,0 | «21. Handwritten» + lettering rojo | Corte seco |
| ~19,0–19,87 | «22. Liquid Glass» + interfaz «28°C» translúcida sobre césped; lista completa | Corte seco; cierre con la lista llena |
