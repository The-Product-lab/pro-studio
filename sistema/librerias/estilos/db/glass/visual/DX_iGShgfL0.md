# DX_iGShgfL0 — estudio visual (estilo glass)

Reel 9:16 de 34,7 s, **100 % motion graphic, sin persona en cuadro** (explainer con voz en off sobre la subida del precio de la RAM, TurboQuant de Google y la caída de Samsung/Micron/SK Hynix; cierra con CTA para descargar el archivo del proyecto). 6 cortes medidos (3,23 · 7,3 · 8,6 · 15,1 · 21,93 · 30,0) = 7 escenas, 10,4 cortes/min, plano medio 4,96 s (1,3–8,07 s). Pero **dentro de cada escena la palabra cambia cada 0,3–0,6 s**: el ritmo real lo da la tipografía cinética, no el corte.

## 1. Sistema en una frase
Tipografía cinética palabra por palabra sobre papel gris claro (o verde oliva casi negro), con **un solo acento verde lima (#B4E233)** en forma de cinta orgánica/ondulada con sombra suave y objetos 3D mate (stick de RAM, disco lima, monitor retro) que entran desenfocados y se enfocan.
**Reconocible en 1 s:** fondo #E1E3DF con grano fino + cinta lima ondulada con sombra + letras que aparecen con desenfoque y van del gris claro al negro.

## 2. Color
Armonía **monocroma verde-amarillo + neutros, un solo acento** (saturación media 0,10: todo es neutro salvo el lima). Temperatura neutra-fría en el gris, cálida-ácida en el lima.

| HEX | % | Rol | Dónde |
|---|---|---|---|
| #E1E3DF | 46,0 | Fondo papel claro | Escenas 1, 2, 3, 5, 7 (0–8,6 s, 21,93–34,7 s) |
| #121B05 | 21,0 | Fondo oscuro (negro verdoso) | Escenas 4 y 5 (8,6–21,93 s), esquina inferior derecha del degradado |
| #354418 | 12,1 | Oliva del degradado oscuro | Arriba-izquierda de las escenas oscuras (degradado diagonal oliva → negro) |
| #D2D9C3 | 7,4 | Lima lavado / tarjetas | Píldoras «Six times smaller…», halo del lima sobre gris |
| #B4E233 | 4,9 | **Acento único** | Cintas onduladas, disco 3D, Pac-Man, subrayado del «2026», fondo pleno de «but for how long» (29–30 s) |
| #CFE594 | 3,8 | Lima medio / zona de transición | Degradados y desenfoque de las cintas, piso lima de «AI was eating» |
| #9BA095 | 2,6 | Gris medio | Texto secundario, letra en estado «entrando» (antes de oscurecer) |
| #66714E | 2,1 | Oliva gris | «within/hours» en oscuro antes de encender, texto fantasma «WIPED» |

Texto principal: casi negro #222 sobre claro; blanco/gris claro con brillo sobre oscuro; lima sobre oscuro para «within/hours».

Tratamiento: luz media 0,61, contraste 0,34 (bajo, suave). **Grano fino constante** sobre todo el cuadro (se ve como textura de papel/ruido monocromo, ~1 px). Viñeta: no en claro; en oscuro el degradado hace de viñeta (esquina inferior-derecha a negro). Halation: no. **Bloom/glow:** sí, suave en los números blancos sobre oscuro («48», «$ 450B»: degradado blanco→gris de arriba abajo con brillo difuso) y en el halo lima difuso alrededor de la cinta del CTA. Aberración cromática: no. Scanlines/polvo/rayones/semitono: no. Light leak: no. **Desenfoque:** sí, como recurso de entrada (gaussian blur de 4–10 px que se resuelve a 0) y como profundidad en cintas fuera de foco detrás del objeto (7,4–8,6 s, 33–34 s).

## 3. Tipografía
1. **Titular sans geométrica** (rol: frase principal palabra a palabra, «in early march», «AI was eating memory alive», «Google dropped a paper», «The demand», «AI companies will»). Minúscula/frase, peso medium-semibold, ancho normal, sin serif, tracking −2 a −3 %, interlineado ~0,95. Tamaño ≈ 7–9 % del ancho por línea de cap-height (la línea entera ocupa 55–70 % del ancho). Color #222 sobre claro. Sin borde ni sombra. **Google Fonts: Plus Jakarta Sans / Manrope (600)**; equivalente más fiel: *Inter Tight* o *Familjen Grotesk*. Juego tipográfico: la palabra débil va más chica y desplazada abajo (subíndice: «AI companies _will_», «was _eating_», «always grows back» más ligera).
2. **Cifra hero** («2026», «32 GB», «48», «$ 450B»): misma familia en **ExtraBold/Black**, tracking −4 %, ocupa 80–110 % del ancho (se sale por la derecha a propósito: «32 G|», «$ 450B»). Negro sobre claro con cinta lima de subrayado detrás; lima #A6CF2E en «32 GB»; blanco con degradado vertical y glow sobre oscuro («48»). Google Fonts: **Plus Jakarta Sans 800** / *Archivo Black*.
3. **Serif cursiva de contraste** («build bigger models», «how long»): serif display itálica, minúscula, peso regular, ~6–8 % del ancho, en lima sobre claro o negro sobre lima. Google Fonts: **Playfair Display Italic** / *Instrument Serif Italic*.
4. **Condensada en mayúsculas** («EDITORS», «VISIT NOW & DOWNLOAD IT»): grotesca condensada bold, todo mayúsculas, tracking 0, interlineado 1,1, ~30–35 % del ancho por palabra, gris #444 (entra en gris claro y se oscurece). Google Fonts: **Bebas Neue** / *Oswald 600*.
5. **Cuerpo / párrafo citado** («As of March 2026, RAM prices remain significantly elevated…», subtítulo de TurboQuant, textos de las tarjetas): sans regular, 2–2,5 % del ancho, gris #888, centrado, 4 líneas, aparece palabra a palabra en gris muy claro.
6. **Rótulos de borde tipo película** («NICKSON STOCK», «DESIGNLAB 400», «▶ 23»): mono/grotesca condensada bold en mayúsculas, ~1,5 % del ancho, girada 90°, en ambos márgenes laterales (x≈2 % y x≈97 %), repetidos verticalmente como el borde de un negativo 35 mm. Google Fonts: *Space Mono 700* / *Oswald*.
7. **Número de tiempo amarillo** arriba-izquierda (#E5E000, ~1 % del ancho): es una marca de la hoja de contacto, no del reel.

Modo de entrada de letra (todos los estilos): cada palabra entra **desenfocada + en gris claro (#C0C0C0, ~40 % opacidad)** y en 3–5 cuadros pasa a nítida y al color final. En «TurboQuant» (8,6–8,9 s) entra **letra por letra en orden aleatorio** (T, o, t, nt, rb, Q…) con desenfoque, ~6 cuadros a 20 cps.

## 4. Composición
- Retícula central: todo centrado en x=50 %, salvo cifras hero que se desbordan a la derecha.
- Titular en el tercio superior (y 10–22 % del alto); bloque de texto o cifra en el centro (y 35–50 %); párrafo en y 55–65 %; objetos/tarjetas en y 55–85 %.
- Márgenes: 4–5 % en claro con rótulos de película; en oscuro las píldoras ocupan 86 % del ancho (margen 7 %).
- No hay persona: profundidad por capas → fondo (papel/degradado) · líneas finas de contorno topográfico gris 1 px (escena 1) o arcos finos (escenas 5, 6) · cintas lima (detrás o delante) · texto · objeto 3D encima del texto (el stick de RAM **tapa** «32 GB»; el disco lima está delante).
- Marcos de esquina finos (escuadras «⌐» 1 px gris, 10 % del lado) en «The demand» (26,5–29 s).

## 5. Elementos gráficos
1. **Cinta lima ondulada** (#B4E233, grosor 2–3 % del ancho, borde levemente irregular, «papel rasgado/rotulador»): sombra suave gris abajo (offset 1–2 % hacia abajo-derecha, blur ~4 %). Entra **dibujándose** desde un extremo (stroke reveal ~0,8 s, ease-out) arriba-izquierda y abajo-derecha (0,3–1,1 s). Variantes: línea de gráfico que sube en escalera (26,5–29 s) con relleno degradado lima→transparente debajo; trazo fuera de foco grueso de fondo (7,4–8,6 s, 33–34 s, opacidad 30–50 %, blur ~3 %).
2. **Subrayado/marcador lima** detrás de «2026»: rectángulo inclinado −3° con bordes ásperos, ~85 % del ancho de la cifra, crece de izquierda a derecha mientras cuenta el número.
3. **Stick de RAM 3D**: barra gris carbón mate con celdas, sombra suave, gira de horizontal a −25° y hace push hacia cámara (3,0–3,6 s), cubriendo la cifra.
4. **Disco lima apilado** (3 discos concéntricos, efecto botón/vinilo con sombra interior): nace como punto (3,0 s) y crece con ease-out hasta ~35 % del ancho, luego salta a ~50 % y sale por arriba (3,4 s).
5. **Línea de puntos curva** (1 px negro, guiones) del stick a la etiqueta «stick of RAM costs»: se dibuja de arriba abajo (3,4–4,0 s), tipo anotación.
6. **Pac-Man lima 3D** (bola con boca negra, ~30 % del ancho) sobre un **piso lima** (plano degradado lima→blanco que ocupa el 45 % inferior): come una barra gris; en 7,2 s hace zoom-in grande y sale por la derecha.
7. **Monitor retro beige 3D** (estilo Macintosh) con un gráfico de barras azul/naranja/verde en pantalla, ~40 % del ancho, centrado; con arco fino gris detrás. Entra desenfocado y se enfoca (7,3–7,45 s).
8. **Píldoras glass-lima** (#D2E5A8, radio ~20 % del alto, 86 % del ancho, sombra suave negra): primero entran **vacías como barra corta** (esqueleto/placeholder, 9,5–11 s) que se ensancha y luego se llenan de texto palabra a palabra («Six _times_» → «Six times smaller»). Apiladas en 3 filas con separación ≈ 1,3× su alto, en cascada (~1,5 s entre una y otra, cada una al decirla).
9. **Ola oliva** (banda curva #354418 sobre negro, 15 % inferior) que deriva lentamente en las escenas oscuras.
10. **Tarjetas de empresa** (blancas #F0F0F0, radio 4 %, sombra suave, ~50 % del ancho): logo + nombre + descripción en gris. Entran desde abajo (y 100 %→65 %) con ease-out, se suceden Samsung → SK Hynix → Micron (cada ~0,7 s, la anterior sube y sale), y en 19,5 s se reordenan en fila de 3 (cada una ~28 %).
11. **Curva de caída** (línea blanca 1 px con relleno oliva debajo) que baja como gráfico de desplome detrás de las tarjetas (20,5–21,9 s), y palabra fantasma gigante «WIPED» en oliva al 30 % detrás.
12. **Comillas negras gigantes** (« “ » y « , » sólidas, ~20 % del ancho): entran por separado, la de apertura desde abajo-centro, la de cierre desde abajo, con desenfoque; sostienen «Analysts say this won't save us.» + avatar/sticker de persona con casco.
13. **Órbitas concéntricas** (3 círculos 1 px gris oscuro, el interior relleno blanco con sombra interior suave = glass/neumorfismo): logos de IA (Meta ∞, OpenAI, Grok, Gemini ✦, DeepSeek, Claude ✳) giran lentamente en las órbitas.
14. **Fondo lima pleno** (29,0–30,0 s) con arcos finos negros 1 px.
15. **Halo lima difuso** (blur alto, opacidad 70 %) detrás de «EDITORS»/CTA, que se forma como trazo que se dibuja (31,5–33 s).

## 6. Apoyos
Un apoyo por idea, cada **~1,5–2,5 s** (≈ 25–30 por minuto contando cada objeto nuevo):
fecha → contador de años + subrayado · «32 GB» → stick de RAM + disco · precio → contador $433→$490 · «AI eating memory» → Pac-Man · «Google dropped a paper» → monitor retro con gráfico · cifras de TurboQuant → píldoras · «48 hours» → cifra hero · empresas → tarjetas con logo · pérdida → cifra $229B→$450B que cuenta + curva cayendo + «WIPED» · cita → comillas + sticker · «AI companies» → órbita con logos · «demand grows back» → gráfico en escalera · pregunta → pantalla lima · CTA → tipografía condensada.
Cada apoyo **ilustra literal la palabra** que se oye (metáfora visual directa).

## 7. Persona
No aparece. Solo un sticker pequeño (cabeza con casco, ~15 % del ancho) junto a la cita en 22,5–23 s.

## 8. Movimiento y transiciones
- **Cámara virtual**: casi estática con **deriva/escala lenta continua** (push-in ~3–5 % por escena). Push-in fuerte de cierre de escena: en 3,3 s y 7,2 s todo escala ~140–160 % hacia cámara justo antes del corte (el disco, el stick y el titular se salen del cuadro). En 15,05–15,15 s el bloque de píldoras hace zoom ~115 % y se va hacia arriba. **La cámara sí se mueve mientras entra el apoyo.** Sin temblor, sin whip.
- **Curvas**: ease-out suave (expo/cubic), sin rebote ni overshoot; entradas de 3–6 cuadros (a 30 cps) para letras, 8–15 para objetos. Contadores numéricos con ease-out (2013→2026 en ~1,5 s; $433→$490; $229B→$450B en ~2 s), los dígitos nuevos entran desde abajo grises y se oscurecen.
- **Transiciones entre escenas**: corte seco tras un push-in (3,23, 7,3), **corte de claro a oscuro** sin fundido (8,6: blanco → degradado oliva, TurboQuant aparece letra a letra), corte tras zoom-out de píldoras (15,1), **corte a blanco vacío** 2–4 cuadros y entra la comilla (21,93), corte de lima pleno a claro (30,0). Dentro de escena, cambios por desenfoque: lo viejo se desenfoca y se aclara mientras lo nuevo se enfoca (ej. 7,3 s: «Google» entra con blur 8 px → 0 en 0,15 s).

## 9. Subtítulos
No hay subtítulos clásicos: **el titular ES el subtítulo** (tipografía cinética que escribe la locución), 1–5 palabras visibles, 1–2 líneas, tercio superior o centro. Palabra clave: más grande y más pesada (cifra hero), en lima, en serif itálica, o dentro de una píldora. Palabra débil: más pequeña, desplazada a subíndice o gris.

## 10. Reglas del sistema
1. Fondo único por escena: papel #E1E3DF con grano fino, o degradado diagonal #354418→#121B05. Nunca foto.
2. Un solo color de acento: lima #B4E233 (y sus lavados). Todo lo demás, neutro.
3. Toda palabra entra desenfocada y gris claro y se resuelve a nítida y oscura en 3–5 cuadros, al ritmo exacto de la voz.
4. Jerarquía por tamaño y peso dentro de la misma familia: palabras débiles chicas/subíndice, cifras gigantes que se desbordan del cuadro.
5. Una cifra siempre se anima contando (ease-out), nunca aparece quieta.
6. Cada idea tiene un objeto 3D mate o una forma glass que la ilustra literal, centrado, con sombra suave.
7. Sombras siempre suaves y abajo (sin sombras duras ni trazos de contorno en las letras).
8. Cinta lima orgánica que se dibuja como trazo para dar continuidad y dirección.
9. Push-in continuo y un empujón fuerte hacia cámara antes de cada corte.
10. Ease-out sin rebote; nada elástico.
11. Listas = píldoras redondeadas que entran como esqueleto vacío y luego se llenan de texto, en cascada al decirse.
12. Cambio de claro a oscuro marca un capítulo nuevo de la historia.

## 11. Qué NO hace
No hay persona ni toma real, no hay color saturado fuera del lima (excepto logos de marcas), no hay halation, aberración cromática, scanlines, polvo ni light leaks, no hay trazos de contorno ni sombras duras, no hay rebote/elástico, no hay whip pans ni temblor, no hay subtítulos en caja ni karaoke, no hay emojis, no hay transiciones de fundido largo ni barridos, no mezcla más de 2 fondos.

## 12. Tabla de momentos
| Segundo | Qué se ve | Recurso |
|---|---|---|
| 0,0–3,23 | Papel con contornos topográficos; «in early march» palabra a palabra; cintas lima se dibujan arriba-izq y abajo-der; «2026» cuenta desde 2013 con subrayado lima; párrafo gris; rótulos de película en bordes. 2,0 s: corte interno a «32 GB» lima con stick de RAM que gira y disco lima que crece | Cinética desenfoque→nítido, contador, stroke reveal, objeto 3D |
| 3,23–7,3 | Push-in fuerte: disco lima arriba, stick tapa «32 G|», línea de puntos a «stick of RAM costs», contador «$ 433→$ 490» con subrayado lima; 5,5 s escena «AI was eating memory alive» con Pac-Man lima sobre piso lima comiendo barra gris; push-in grande al final | Anotación punteada, contador, metáfora 3D, push-in de salida |
| 7,3–8,6 | Monitor retro beige con gráfico de barras; «Google dropped a paper» (Google con colores de marca) entra desenfocado; cinta lima fuera de foco de fondo y arco fino | Desenfoque de entrada, objeto 3D retro, profundidad |
| 8,6–15,1 | Corte a oscuro oliva→negro; «TurboQuant» letra a letra aleatoria; subtítulo gris; 3 píldoras lima-glass entran como esqueleto y se llenan: «Six times smaller», «Eight times faster», «Zero accuracy lost»; ola oliva abajo; zoom-out final | Cambio de capítulo claro→oscuro, píldoras en cascada |
| 15,1–21,93 | «within» lima → «48» blanco gigante con brillo → «hours»; tarjetas Samsung, SK Hynix, Micron suben en sucesión; 19,5 s cifra «$ 229B→$ 450B» cuenta con brillo, tarjetas en fila, curva de desplome y «WIPED» fantasma oliva | Cifra hero con glow, tarjetas con logo, contador, gráfico cayendo |
| 21,93–30,0 | Blanco vacío 2–4 cuadros; comillas negras gigantes + «Analysts say this won't save us.» + sticker; 23,5 s órbitas glass con logos de IA, «AI companies will just _build bigger models_» (serif itálica lima); 26,5 s «The demand always grows back» con gráfico lima en escalera, píldora lima «Software just defeated hardware», marcos de esquina; 29,0 s pantalla lima plena «but for _how long_» | Comillas, órbitas neumórficas, gráfico ascendente, fondo de acento pleno |
| 30,0–34,7 | Papel con rótulos de película; «EDITORS» condensada gris→negro; «this project file is now on …» ; halo lima difuso se dibuja detrás; «VISIT NOW & DOWNLOAD IT» | CTA tipográfico condensado, glow lima difuso |
