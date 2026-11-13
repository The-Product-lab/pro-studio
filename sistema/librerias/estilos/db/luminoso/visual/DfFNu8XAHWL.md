# DfFNu8XAHWL — estudio visual (luminoso)

Reel tutorial de motion: un creador enseña cómo hacer que un título «se vea de película» (glow, softness, halation, grano, imperfecciones). Casi todo el reel es **la propia letra como protagonista**, ampliada hasta llenar el cuadro, más archivo de títulos de cine clásico y grabación de pantalla de After Effects / Photoshop. La persona sale solo 2 veces (11,30 s y 40,5 s). 41,83 s · 29 cortes · 41,6 cortes/min · plano medio 1,39 s (0,17–4,43 s). Cuadro vertical 9:16 (muestras de 360×640).

## 1. Sistema en una frase
**Un solo título amarillo con glow sobre negro, convertido en paisaje: la cámara se mete dentro de la letra «Z» hasta que sus bordes llenan el cuadro, y encima se anota a mano («GLOW & SOFTNESS», «HALATION», «FILM GRAIN», «SOFTNESS») con una flecha blanca dibujada y una lupa circular que compara borde duro vs. borde suave.**
Reconocible en 1 s: negro casi puro + bloque amarillo #F3EC2F con halo cálido + subtítulo pequeño blanco en pastilla abajo.

## 2. Color
Medido: luz media 0,22 · contraste 0,28 · saturación 0,12 (la saturación baja es porque el 75 % del cuadro es negro/gris; el amarillo es muy saturado pero ocupa poco).

| HEX | % | Rol | Dónde |
|---|---|---|---|
| #000100 | 30,2 | Fondo puro | Fondo de los tramos «Z» con halation (18,2–21 s), archivo con marco negro, final AE |
| #1E1E1B | 25,6 | Fondo base (negro levantado, gris cálido con grano) | Fondo del gancho 0–8,4 s y de los títulos de cine (con retícula tenue) |
| #12130E | 13,1 | Sombra / fondo intermedio | Tramo 1,5–1,7 s (versión «sin glow», más plana y oscura) y 5,0–5,5 s |
| #F3EC2F | 10,8 | **Acento único / protagonista** | El título «ZOOM IN» y sus letras ampliadas |
| #3A3934 | 5,9 | Gris medio | Interfaz de After Effects/Photoshop, pastilla del subtítulo |
| #6F4E3C | 5,3 | Marrón cálido | Halo del glow (borde anaranjado del amarillo), humo de «Taxi Driver», sombra del círculo-lupa |
| #81796F | 5,1 | Gris cálido | Archivo B/N (Parent Trap, Hayley Mills, cámara de animación) |
| #BFB6AE | 4,0 | Gris claro | Altas luces del archivo B/N, humo, piel de la persona |

- Armonía: **monocroma negra + un solo acento amarillo**. Acentos secundarios solo en los ejemplos de cine: naranja neón (#FF8A00 aprox., «HOURS/After Hours»), rojo sangre («RAGING BULL», «CRIMSON NIGHTS»), azul eléctrico pequeño (flecha de After Hours). Temperatura global cálida.
- Grade: negros levantados a #1E1E1B con **grano fino animado** constante en el fondo (se ve chispear); polvo y rayitas blancas sueltas (puntos a 0,5 s, 2,4 s, 4,98 s) y **una línea vertical fina gris** que cruza el cuadro (0,9–1,2 s, 2,0 s, 8,28–8,38 s): simulación de rayón de película.
- Viñeta: no en el gancho; sí en el archivo B/N (cada clip va dentro de un **marco redondeado con bordes desenfocados oscuros**, tipo ventana de proyector/cuadro de película).
- Halation: el amarillo tiene un halo **cálido naranja-marrón** (#6F4E3C) de ~2–3 % del ancho alrededor del borde; en 18,2–21 s el halo se ve como un **borde rojizo** en el lado izquierdo y superior del bloque («A REDDISH GLOW»).
- Bloom/glow: sí, fuerte. El título a 0–0,5 s y 8,2 s está con glow amplio (las letras «brillan» y se desenfocan un poco). En la comparación 1,5–1,7 s se quita el glow: el amarillo baja a #E8CE20 plano y el fondo baja a #12130E → enseña la diferencia.
- Aberración cromática: no. Scanlines/CRT: no. Semitono/papel: no. Light leak: no.
- Modo de fusión aparente: glow en **Add/screen** (lo confirma la pantalla de AE a 35,5 s: Glow Threshold 60 %, Glow Radius 24, Glow Intensity 1,0, Composite Original «Behind», Glow Operation «Add»; luego Gaussian Blur 4,0 y Add Grain preset «Eastman Color N…»). Esa es literalmente la receta del look.

## 3. Tipografía
1. **Título protagonista «ZOOM IN» / «MOVIE TITLE»**: sans geométrica extendida (ancha), mayúsculas, peso Black/Heavy, terminales cuadradas, «O» como rectángulo de esquinas redondeadas (estilo Eurostile Extended / Microgramma Bold Extended). Google Fonts: **Michroma** (más fiel en forma) o **Krona One**; para más peso, **Orbitron Black**. Tracking 0, interlineado muy apretado (~0,85). «ZOOM» ocupa ~80 % del ancho, «IN» centrado debajo ~40 %. Color #F3EC2F con glow add + blur 4 px. Centrado en x=50 %, y≈30–40 %.
2. **Subtítulo**: sans condensada bold (tipo Roboto Condensed Bold / **Inter Tight Bold** / **Roboto Condensed 700**), MAYÚSCULAS, blanco, 1–3 palabras, tamaño ~4,5 % del ancho por letra (alto de caja ~2,3 % del alto), dentro de una **pastilla rectangular gris oscura semitransparente** (#3A3934 a ~60 %, radio ~4 px, padding ~1 % ). En fondos negros a veces sin pastilla. Centrado, y≈80 % del alto.
3. **Anotación manuscrita**: letra de rotulador a mano, versalitas/mayúsculas pequeñas («GLOW & SOFTNESS», «HALATION», «FILM GRAIN», «SOFTNESS»), blanca, trazo fino irregular. Google Fonts: **Gochi Hand** o **Patrick Hand SC** (versalitas). Tamaño ~4–5 % del ancho por letra, ancho total ~55–60 % del cuadro, alineada a la izquierda en x≈12 %, y≈50–60 %.
4. Ejemplos de cine (no se diseñan, se citan): neón naranja con halo (After Hours), roja con relleno grueso y sombra (Raging Bull), serif blanca gótica sobre B/N (Snow White), cursiva cepillo roja (Crimson Nights), «TAXI DRIVER» naranja metálica con humo.

## 4. Composición
- Retícula: todo centrado en el eje vertical; tres franjas: arriba (y 15–45 %) el gráfico protagonista, medio (y 45–65 %) anotación manuscrita, abajo (y ≈80 %) subtítulo.
- La «Z» ampliada se recorta contra el **borde derecho**: ocupa del 30 al 100 % en x; barra superior en y≈25–45 %, diagonal y base de y≈55 % al 100 %. El negro del lado izquierdo (≈30 % del ancho) es el espacio donde va la flecha y la anotación.
- Lupa circular: diámetro ~30 % del ancho, centrada sobre la esquina superior izquierda de la barra de la Z (x≈55 %, y≈25 %).
- Ejemplos de cine: banda horizontal a todo ancho, alto ~40 % del cuadro, centrada (y 20–60 %) sobre fondo #1E1E1B con **retícula fina en perspectiva** (grid tenue) arriba y abajo. Archivo B/N en marco vertical redondeado de ~85 % del ancho × 87 % del alto, o cuadrado ~85 % del ancho.
- Persona: solo 2 apariciones, full-frame, centrada.
- Delante/detrás: el subtítulo siempre delante de todo; nada pasa detrás de la persona.

## 5. Elementos gráficos
- **Letra ampliada «Z»** (el elemento central): bloque amarillo sólido con borde suave + halo. Entra por **push-in continuo** desde el título completo (0,6–1,2 s: la Z crece de ~45 % a >100 % del ancho en ~0,6 s, curva ease-in/acelera, desplazando hacia la izquierda hasta dejar solo la esquina). Vuelve a usarse en 2–5 s, 18–21 s, 23,5–25 s, 28–30,5 s.
- **Lupa / círculo de detalle**: círculo de borde suave con sombra suave hacia abajo-derecha (~3 % de distancia, blur grande, marrón #6F4E3C), dentro muestra el borde de la letra **más ampliado y desenfocado** (zoom en la lupa). Entra a 2,1 s **deslizando desde arriba-derecha** (de y=-10 % a su sitio en ~3 cuadros a 10 cps ≈0,3 s, ease-out) y su contenido se ilumina de mitad (izq. oscuro / der. brillante → enseña glow). Se repite a 23,5 s («FILM GRAIN», con textura de grano visible dentro) y 28–30,5 s («SOFTNESS»).
- **Flecha manuscrita blanca**: curva hacia arriba con punta abierta, trazo ~1 % del ancho. **Se dibuja como write-on**: primer cuadro un trazo corto (1,8 s), crece 2,1–2,6 s, punta aparece al final (≈8 cuadros de 20 cps ≈0,4 s, lineal). La anotación se escribe **letra por letra** a la par (2,3 «GLO» → 2,7 «GLOW & SOFTNESS», ~10 letras en 0,4 s). Mismo patrón en 18,2–18,8 s (HALATION).
- **Rayón vertical**: línea gris 1 px a todo alto, aparece 1–3 cuadros y se va (imperfección de película).
- **Franja de luz vertical** (4,98–5,13 s): banda blanca semitransparente ~15 % del ancho sobre la Z, que la «quema» a #FFFF30 → light sweep de transición.
- **Cursor y menús** de la grabación de pantalla (21–23 s, 25–27 s, 31–39 s): ampliados hasta que el menú ocupa ~70 % del ancho; opción resaltada en azul (#2D5BD0 aprox.).
- Pastilla del subtítulo (ver §9).

## 6. Apoyos
- Cada idea dicha = un apoyo visual literal y casi siempre **el propio objeto del que se habla**: «zoom in to this text» → la cámara entra en la letra; «subtle glow» → lupa; «once you know» → títulos de cine reales (After Hours, Raging Bull, Taxi Driver); «were often photographed onto film» → archivo B/N de la cámara de animación; «imperfections» → archivo quemado; «halation / a reddish glow» → borde rojizo marcado con flecha; «layer style / outer glow» → menú real; «grain effect» → zoom con grano; «Gaussian blur» → bloque desenfocado; «preset» → «MOVIE TITLE» en AE.
- Frecuencia: un apoyo nuevo cada ~1,4 s (plano medio medido); el reel es 95 % apoyo, 5 % persona.

## 7. Persona
- 11,30–12,13 s y 40,50–41,83 s: plano medio corto, cabeza en y≈15–35 %, ocupa ~70 % del ancho; gorra blanca, gafas, polo gris; habla a cámara con gesto de mano en primer plano (abajo-izq.).
- Fondo: cuarto cálido con estantes, TV CRT azul encendida, lámpara amarilla (y≈45 %); luz cálida de interior, color natural, sin grade especial ni B/N.
- Sin recorte, sin silueta, sin texto detrás.

## 8. Movimiento y transiciones
- Cámara: **push-in continuo** sobre el gráfico (0,0–0,5 s el título crece ~10 %; 0,6–1,2 s entra en la Z), suave tipo ease-in-out; después **estática** mientras se anota. Ligera deriva en los clips de archivo (Parent Trap 12,6–13,5 s: la tarjeta de Hayley Mills **entra rotando ~15° desde abajo-derecha** y se acomoda en ~0,5 s, ease-out). Sin temblor, sin whip pan.
- Transiciones (cortes medidos):
  - 0,63 y 0,80: cortes de micro-plano (0,17 s) dentro del push-in: saltan la escala, sensación de punch-in.
  - 5,23 / 5,40: **sweep de luz + pull-out**: de la Z ampliada a «ZOOM IN» completo, ZOOM entra recortado por la derecha y se acomoda en 0,3 s (crece/aleja, ease-out).
  - 8,43, 9,63, 10,53: corte seco entre bandas de títulos de cine; la palabra «HOUR» entra con **slide horizontal** de derecha a izquierda (8,43–8,73 s) revelando «HOURS».
  - 11,30: corte seco a la persona.
  - 12,13 → 15,27: archivo B/N en marco redondeado, cortes secos; 15,27 el marco cambia de vertical a cuadrado (corte seco).
  - 18,17: corte seco del archivo a la Z con halation sobre negro puro.
  - 20,73–23,33: grabación de pantalla, cortes secos con zoom en el menú.
  - 24,9–25,43: tres cortes rápidos (0,3 / 0,23 s) + **zoom con desenfoque** gigante sobre «MOVIE / IN» en AE (whip zoom).
  - 26,53–30,87: Z amarilla con glow fuerte, escalas distintas («ZZZ»), luego lupa SOFTNESS.
  - 30,87–39,37: pantalla de AE (panel de efectos, Gaussian blur, preset), cambio de color a rojo «CRIMSON NIGHTS» (38,6 s) con push-in y desenfoque.
  - 40,5: corte seco a la persona para el cierre.

## 9. Subtítulos
- Siempre presentes, posición fija **centro, y≈80 %** del alto (más bajo que lo habitual), 1–3 palabras («TO THIS TEXT.», «NOTICE», «THE SUBTLE GLOW», «AND SOFTNESS»), mayúsculas, blanco, sans condensada bold, ~2,3 % del alto.
- Pastilla gris oscura semitransparente redondeada detrás cuando el fondo es claro/amarillo; sin pastilla sobre negro.
- Sin palabra clave marcada en color: **la palabra clave la marca la anotación manuscrita**, no el subtítulo. Cambio de frase seco, sin animación.

## 10. Reglas del sistema
1. Fondo negro levantado (#1E1E1B) con grano fino animado y rayones ocasionales de película; nunca fondo plano limpio.
2. Un solo acento de color por bloque (amarillo #F3EC2F); los otros colores solo vienen de los ejemplos citados.
3. El título lleva receta fija: Glow (threshold 60 %, radio 24, intensidad 1, Add, original detrás) + Gaussian blur 4 + grano de película.
4. El gráfico ES el tema: la cámara entra en la letra hasta que su borde llena el cuadro; se muestra la textura de cerca.
5. Las anotaciones son manuscritas blancas, con flecha curva dibujada (write-on ~0,4 s) apuntando al detalle desde el lado negro izquierdo.
6. La lupa circular con sombra suave compara antes/después dentro del mismo cuadro.
7. Comparar con/sin efecto con un corte de 0,2 s (1,5–1,7 s: glow apagado) para que se note la diferencia.
8. Ejemplos de cine en banda horizontal centrada sobre retícula tenue; archivo B/N en marco redondeado con borde desenfocado.
9. Plano medio ~1,4 s, cortes en cada frase; la persona solo abre/cierra o hace bisagra (≤2 apariciones).
10. Subtítulo pequeño fijo abajo (y≈80 %), 1–3 palabras, en pastilla gris; nunca compite con el gráfico.
11. Movimientos suaves (push-in ease-in-out, entradas ease-out ~0,3 s); nada elástico ni con rebote.
12. Grabación de pantalla real del programa, ampliada al menú relevante con cursor visible.

## 11. Qué NO hace
- No usa la persona como fondo ni pone texto detrás de ella; casi no hay persona.
- No hay rebotes, overshoot, stop-motion, shake ni whip pans laterales.
- No hay íconos, emojis, stickers, mapas ni cifras.
- No resalta palabras del subtítulo en color ni con tamaño.
- No usa aberración cromática, scanlines, semitono, papel ni light leaks de colores.
- No hay degradados de fondo ni formas decorativas genéricas (cajas, chips, círculos de adorno): el único círculo es funcional (lupa).
- No mezcla varias tipografías de diseño propias: una extendida para el título, una condensada para subtítulos y una manuscrita para notas.

## 12. Tabla de momentos
| Segundo | Qué se ve | Recurso |
|---|---|---|
| 0,00–0,63 | «ZOOM IN» amarillo con glow centrado sobre negro con grano | Push-in suave ~10 %, glow add |
| 0,63–0,80 | La «Z» grande | Micro-plano 0,17 s, punch-in |
| 0,80–5,23 | Z ampliada a borde derecho; 1,5–1,7 sin glow (comparación); 2,1 entra lupa, flecha y «GLOW & SOFTNESS» manuscrito | Push-in continuo hasta esquina; lupa ease-out; write-on de flecha y letras |
| 5,23–5,40 | Z con franja de luz vertical | Light sweep, micro-plano 0,17 s |
| 5,40–8,43 | «ZOOM IN» completo entrando por la derecha y asentándose | Pull-out ease-out; luego estático con glow |
| 8,43–9,63 | «HOUR(S)» neón naranja en banda sobre retícula | Slide horizontal der→izq |
| 9,63–10,53 | «After HOURS» → «RAGING BULL» rojo sobre B/N | Corte seco, banda centrada |
| 10,53–11,30 | «TAXI DRIVER» naranja con humo | Corte seco, humo animado |
| 11,30–12,13 | Persona a cámara («digital filmmaking») | Corte seco, plano medio |
| 12,13–12,87 | Título «The Parent Trap» B/N en marco redondeado | Archivo con viñeta |
| 12,87–13,07 | Tarjeta «Hayley Mills» entra rotando | Entrada rotada ease-out |
| 13,07–13,57 | Tarjeta Hayley Mills asentada | Estático |
| 13,57–15,27 | Animador en cámara de animación (B/N) | Archivo, deriva leve |
| 15,27–18,17 | Archivo quemado (imperfecciones) → «Snow White and the Three Stooges» en marco cuadrado | Corte seco, cambio de marco |
| 18,17–20,73 | Z sobre negro puro con halo rojizo, flecha + «HALATION» | Write-on de flecha y texto |
| 20,73–23,33 | Menú de Photoshop: Layer Style → Inner/Outer Glow | Grabación de pantalla ampliada, cursor |
| 23,33–24,90 | Z con lupa «FILM GRAIN» (grano visible en la lupa) | Lupa ease-out + anotación |
| 24,90–25,20 | Interfaz AE | Micro-plano |
| 25,20–25,43 | Zoom gigante a «MOVIE» | Whip zoom con blur |
| 25,43–26,53 | Letras «O/I/N» gigantes con glow y cursor | Zoom extremo, «grain on top» |
| 26,53–28,03 | «ZZZ» amarillas con glow fuerte | Escalas cambiando, glow add |
| 28,03–30,87 | Z con lupa «SOFTNESS» | Lupa + anotación manuscrita |
| 30,87–33,53 | Bloque amarillo desenfocado + panel AE arriba | Gaussian blur demostrado |
| 33,53–35,13 | «MOVIE TITLE» en la composición de AE | Grabación de pantalla, preset |
| 35,13–36,87 | Panel de efectos: Glow / Gaussian Blur / Add Grain | Pantalla ampliada (la receta) |
| 36,87–37,13 | Panel/«…VIE TLE» | Micro-plano 0,26 s |
| 37,13–38,60 | Selector de color rojo en AE sobre título | Grabación de pantalla |
| 38,60–39,37 | «CRIMSON NIGHTS» rojo cepillo | Cambio de color/fuente, push-in |
| 39,37–40,50 | «CRIMSON NIGHTS» sobre fondo B/N oscuro desenfocado | Push-in + blur |
| 40,50–41,83 | Persona a cámara, pulgar arriba («grab it in my bio») | Corte seco, cierre |
