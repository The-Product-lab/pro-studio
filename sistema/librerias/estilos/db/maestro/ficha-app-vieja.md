# Look: maestro — mezcla persona + B-roll real (referente @rpn, `fuentes/referentes/mezcla-maestra/ficha.md`)

Familia: cine/documental · Estado: **ejecutable** con `tools/lab/lab_maestro.py` (V1 2026-10-12) · DISTINTO al vox: nada de
papel ni recortes; video real a pantalla completa. Nunca fusionarlo con vox (Pablo: "son dos cosas distintas").

## Revisión de Pablo 2026-10-25 (maestro-2 · capas cósmicas) — manda sobre lo de abajo
- **Persona limpia**: cuando se ve el talento no va nada encima (fuera las `capas` de líneas/marcos/círculos sobre la
  persona: "muy invasivo"). Solo el subtítulo y los titulares. Lo gráfico vive en las ráfagas de apoyo.
- **Nada con cara de banco de imágenes**: fuera escenas de estilo de vida (pareja en restaurante, calle de neón, mano bajo
  el agua, persona hundiéndose, pelo, flor rosa, copas, pájaros, ola). Solo objeto aislado B/N, macro, patente, 3D negro,
  rayos, partículas, espirales, iris, siluetas.

## V2 (2026-10-12) — reemplaza el "Cómo se usa" de abajo
Sin stock. `arte.json` → `lab_maestro.py <proy> arte` (FLUX; sufijos de dirección de arte por familia en el código) →
`plan_maestro.json` con `rafagas` de microplanos (`hud`, `flash`, `tipo`, `pagina`, `circulo`, `objeto`, `patente`,
`tarjetas`, `vacio`, `noche`) → `lab_maestro.py <proy>`. El código pone solo: movimiento de cámara rotativo por plano,
desenfoque de entrada, glitch de 2 cuadros en cada corte, grano solo en apoyos, sfx por tipo de plano, subtítulo
1-2 palabras (oculto cuando el plano trae su propio texto), saltos de encuadre de la persona.

## Cómo se usa (V1, superado)
1. Corte del guion: `tools/lab/lab_cortar.py` (silencios reales, ≤ 1:40) → `corte.mp4` + `transcript.json` (corregir palabras mal oídas).
2. B-roll: `tools/lab/broll.py buscar "<inglés>"` (Mixkit, gratis, sin llave; se elige por la descripción, sin mirar
   imágenes) → `bajar <ids>` a `biblioteca/broll/` (reutilizable).
3. `plan_maestro.json`: insertos (`hud`, `broll`, `grilla`, `medidor`), titulares, palabras de énfasis, sfx.
4. `python3 tools/lab/lab_maestro.py <proyecto>` → `hf_maestro/index.html`; render con `--sdr -w 2`.

## Reglas (el código las impone)
- Subtítulo mono mayúscula en caja oscura abajo al centro, 2-3 palabras, IGUAL sobre persona y B-roll; 60-80 % del
  guion (fuera muletillas y frases conectoras); 1 palabra de énfasis en serif itálica grande dentro de la línea.
- Una sola cosa a la vez: el subtítulo se oculta con titular / grilla / medidor / gancho.
- Persona: zoom lento continuo que reinicia por tramo + salto de encuadre en cada empalme (esconde los cortes).
- Gancho: ráfaga B/N de 0,45 s por toma con display rojo/blanco, marcos HUD, REC/PLAY, scanlines, glitch en cada corte.
- Enumeración → grilla editorial blanca que se llena (una fila por palabra); progreso → UI de datos minimal (barras negras, rojo en la actual).
- Paleta propia del referente: blanco hueso, negro, rojo #e3261b. B-roll con gradación sobria (sat 0,82).

## DIRECCIÓN DE ARTE (estudiada cuadro a cuadro 2026-10-12 tras el rechazo de la V1 — esto manda)
La V1 falló por usar stock de estilo de vida y componentes simples. El referente es **editorial premium monocromo**:
- **Paleta**: blanco papel / negro / grises + **rojo** solo como acento de marca. El color "cine" queda solo en la persona
  y en el montaje nocturno (neón saturado, desenfoque).
- **Imágenes**: nunca stock de gente sonriendo. Objetos **aislados en B/N de alto contraste** (producto de estudio sobre
  blanco o negro), **macro de texturas** (billete, grabado, plano de patente), **3D abstracto** negro con anillo de luz,
  rayos/electricidad sobre negro, campos de partículas de datos. Se generan (Higgsfield / FLUX) con esa dirección.
- **Composiciones** (cada apoyo = 3-6 microplanos de 0,2-0,6 s):
  1. HUD: foto B/N + display rojo con bloque blanco, retícula, "PLAY ▶", barras de glitch.
  2. Logo/palabra roja sobre negro → misma sobre blanco (corte en seco).
  3. Página editorial blanca: microtexto mono, texto vertical, filetes, **barras diagonales negras** tipo cinta; grilla
     de objetos B/N que se llena una fila por palabra.
  4. Círculo blanco/negro que enmarca un objeto, con etiquetas laterales y líneas finas.
  5. **Tipografía gigante + bloque de imagen encima** ("Ma▇chine"): la imagen tapa el centro de la palabra.
  6. **Tarjetas flotantes en 3D** (perspectiva, se apilan y vuelan) sobre blanco con un titular serif.
  7. Vacío negro con partículas / números (datos), anillo de luz.
- **Subtítulo**: UNA palabra a la vez, mono mayúscula ~26 px en caja oscura chica, abajo al centro; a veces una palabra
  en serif itálica grande ("Opposite") dentro de la línea.
- **Ritmo**: 55 cortes/min, mediana 0,6 s; apoyos en ráfagas; persona con zoom lento.

## GLOSARIO COMÚN Pablo ↔ Claude (nombres de las composiciones del referente, con su segundo exacto)
Video: `cerebro/fuentes/referentes/mezcla-maestra/video.mp4`. Cuando Pablo nombre uno, es exactamente esto.
| Nombre | Qué es | Dónde verlo |
|---|---|---|
| **HUD** | foto B/N + palabra roja con bloque blanco, retícula, "PLAY ▶", barras de glitch | 0:01-0:02 ("Japanese companies") |
| **Logo flash** | palabra/logo rojo sobre negro → corte seco a la misma sobre blanco | 0:03 (YAMAHA) |
| **Página editorial** | página blanca con microtexto mono, texto vertical, filetes y barras diagonales negras; grilla de objetos B/N que se llena una fila por palabra | 0:04-0:06 (pianos → motos → palos de golf → robots) |
| **Círculo** | objeto dentro de un círculo blanco/negro con etiquetas laterales y líneas finas | 0:09 (piedra "from the ground") |
| **Objeto aislado** | producto B/N de alto contraste a pantalla completa (llanta, turbina) | 0:09-0:10 |
| **Tipo + bloque** | palabra gigante con un bloque de imagen encima que le tapa el centro | 0:10 ("Ma▇chine" con la mano) |
| **Montaje nocturno** | ráfaga de B-roll cine de noche, neón saturado, desenfoque | 0:12-0:15 |
| **Tarjetas 3D** | capturas/fotos flotando en perspectiva que vuelan y se apilan sobre blanco + titular serif | 0:40-0:42 (TOTO) |
| **Rayos** | electricidad blanca sobre negro, metáfora literal | 0:47-0:48 ("General Electric") |
| **Patente** | dibujo técnico de patente en línea negra sobre blanco | 0:49 |
| **3D abstracto** | objeto negro brillante / anillo de luz sobre gris o negro | 0:49-0:50 |
| **Macro textura** | detalle extremo de una textura (billete) | 0:50-0:51 |
| **Collage + palabra 3D** | grilla de fotos de personas + palabra 3D blanca enorme encima | 0:52-0:54 ("A Team") |
| **Vacío de datos** | partículas/números blancos sobre negro | 0:54-0:55 |
| **Subtítulo maestro** | UNA palabra, mono mayúscula diminuta, caja oscura chica, abajo al centro | todo el video |
| **Palabra serif** | una palabra del subtítulo en serif itálica grande | 0:00 "wondered", 0:44 "Opposite" |
| **Prop a cámara** | la persona muestra un objeto real (libro) justo al decir la palabra | 0:43 "AMERICA" |
