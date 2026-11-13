# Gramática del storyboard (lo único que el motor entiende)

> **Compuerta (`estudio/validar.py`):** toda clave, tipo, filtro, entrada, color o fuente que no esté en esta gramática es un ERROR
> y el storyboard vuelve al director con la lista exacta. Los textos se miden renderizándolos: nada fuera del lienzo ni de la
> zona segura. Rosa/magenta prohibido. Si un estilo necesita algo nuevo, primero se agrega al motor, a la compuerta y aquí.

El lienzo mide 1080×1920. **Todos los tiempos están en segundos del video FUENTE**, los mismos de `palabras.json`.
El motor quita los tramos de `cortes` al final: tú escribes siempre en tiempo fuente.

```jsonc
{
  "estilo": {"acento": "#FFE800", "tinta": "#181614", "papel": "#E2D6BE", "persona": "bn" | "color", "fuente": "Playfair"},
  "cortes": [[ini, fin], ...],           // silencios o tomas malas que se quitan (tiempo fuente)
  "escenas": [                           // cada escena dura hasta el t0 de la siguiente; cambiar de escena = corte visual
    {"t0": 0.0, "intencion": "texto corto", "persona": {"modo": "completa" | "oculta"}}
  ],
  "alejar_final": true,
  "elementos": [
    // foto con borde blanco y sombra (gris por defecto; "gris": false para mapas o color)
    {"id": "feria", "tipo": "foto", "src": "arte/feria.png", "ancho": 900, "rot": -3, "x": 540, "y": 470,
     "t0": 0.0, "t1": 2.54, "entra": "cae", "dur": 0.32, "z": "atras", "crop": [x0, y0, x1, y1]},
    // objeto recortado con contorno blanco (PNG con transparencia)
    {"id": "reloj", "tipo": "recorte", "src": "arte/reloj.png", "ancho": 500, "rot": 8, "x": 790, "y": 560,
     "t0": 14.86, "t1": 17.68, "entra": "pop"},
    // etiqueta de texto: fondo "acento" (texto tinta) o "tinta" (texto acento); lineas = [texto, tamaño px, cursiva, peso]
    {"id": "cartel", "tipo": "etiqueta", "lineas": [["Auditorio", 96, true, 800], ["Líderes de Comunidad", 62, false, 700]],
     "fondo": "acento", "rot": -2, "x": 540, "y": 420, "t0": 8.38, "t1": 10.04, "entra": "barrido"}
  ],
  "trazos": [
    {"tipo": "rect", "sobre": "feria", "t0": 1.94, "dur": 0.5, "t1": 2.54},                     // marco amarillo alrededor de un elemento
    {"tipo": "elipse", "sobre": "mapa", "centro": [px, py], "radio": [rx, ry], "t0": 4.0, "dur": 0.6, "t1": 4.95},
    //   centro y radio en PÍXELES DE LA IMAGEN ORIGINAL del elemento (el motor aplica escala, crop y rotación)
    {"tipo": "rayos", "desde": [540, 480], "hacia": [[90, 260], [990, 240]], "t0": 12.86, "dur": 0.42, "t1": 14.74, "z": "atras"},
    {"tipo": "linea", "puntos": [[x, y], [x, y]], "t0": 3.0, "dur": 0.4, "t1": 5.0}
  ],
  "subtitulos": {
    "y": 1455,                                  // centro de la tira; debe quedar DEBAJO de la barbilla
    "bloques": [[i0, i1], ...],                 // rangos de índices de palabras (i1 exclusivo), 2–4 palabras; opcional (si falta, se arman solos)
    "resaltar": [i, ...],                       // índices de palabras clave → resaltado del color de acento
    "ocultar": [[t0, t1], ...]                  // tramos sin subtítulos (cuando una etiqueta ya dice lo mismo)
  }
}
```

**Entradas** (`entra`): `cae`, `izq`, `der`, `sube`, `pop`, `barrido` (para etiquetas). **z**: `atras` (capa de fondo, solo en pantallas con la persona `oculta`) o `frente`.
**Sonido:** sale solo del storyboard (docs/PLANO-SONIDO.md): suenan el cambio de escena, el texto principal (tam ≥ 90), el apoyo que
entra y el trazo (en capas); lo chico no suena. Máx. 2 efectos por segundo, nunca dos a menos de 0,18 s; cada efecto
culmina EN su evento. `estilo.sonido_paleta`: `suave` | `papel` | `digital` | `cine` (cine calla los textos); `estilo.sfx` = volumen
(0 = mudo). Un `sonido` escrito a mano en la raíz se respeta tal cual. Cada render deja `sfx-informe.json`.

## Ubicar a la persona

`persona.x` corre a la persona en horizontal (0 = centro; ±240–260 = a un lado) y `escala` la achica (0,70–0,80).
Va pegada abajo. Un punto (xs, ys) del video fuente cae en la pantalla en
`X = (xs − 540)·escala + 540 + x` y `Y = 1920 − 1920·escala + 10 + ys·escala`.
Usa la caja de la cara de `cara.json` (coordenadas fuente, por segundo) para que **nada tape la cara** y para que
los subtítulos queden debajo de la barbilla.

## Zonas

- El texto (etiquetas y subtítulos) va entre y=230 y y=1500. Instagram tapa arriba y abajo.
- Nada importante se sale del lienzo: deja ~20 px de margen.
- Los elementos grandes (fotos o mapas) van arriba (y 250–900) o al lado contrario de la persona.

## Base «pantalla» (estilos HUD y similares: `estilo.base = "pantalla"`)

El bloque `estilo` lo pone el sistema según el estilo elegido: NO lo cambies. En esta base no hay papel; la persona es el video completo.

```jsonc
"escenas": [
  {"t0": 0.0, "intencion": "…", "filtro": "termico" | "bn" | "rayosx" | "duotono" | "ninguno",
   "entrada": "corte" | "rafaga" | "flash",
   "persona": {"modo": "completa" | "oculta", "fondo": "negro" | "acento" | "#hex"},
   "franjas": [{"filtro": "termico", "etiqueta": "palabra"}, …]}        // opcional: la toma partida en 2–4 franjas
],
"golpe": true,                       // OBSOLETO: ya no hay zoom de golpe en cada corte (daba brincos); se ignora
"elementos": [
  {"id": "t1", "tipo": "texto", "z": "atras" | "frente", "x": 540, "y": 430, "t0": 0.0, "t1": 2.5, "entra": "golpe" | "fundido" | "pop",
   "brillo": false, "interlineado": -10,
   "lineas": [{"texto": "Hoy en", "rol": "script", "tam": 130, "color": "blanco"},
              {"texto": "la feria", "rol": "display", "tam": 230, "color": "acento", "mayus": true}]}
],
"cajas": [   // marcos HUD que siguen la cara o el cuerpo de la persona cuadro a cuadro
  {"t0": 1.5, "t1": 2.5, "sobre": "cara" | "cuerpo" | [x0, y0, x1, y1], "etiqueta": "Sujeto 01", "datos": ["línea mono", "otra"], "margen": 30}
],
"subtitulos": {"y": 1500, "resaltar": [...], "ocultar": [[t0, t1], …]}
```

- La persona NUNCA se recorta del fondo (regla de Pablo; el motor ya no tiene con qué): va entera en su toma (`completa`) o no va (`oculta`). Nada va detrás de ella sobre su toma: `z: "atras"` solo ordena capas dentro de una pantalla con la persona `oculta`.
- Roles de fuente: `display` (sans negra), `script` (caligrafía), `mono` (datos). Colores: `acento`, `acento2`, `blanco`, `negro` o #hex.
- Un `texto` en mayúsculas `display` mide ~0,62×`tam` por letra: no pases de ~1000 px de ancho. Legibilidad (una sola regla para los 13, reglas.json): ninguna línea baja de `texto_linea_min_px` y, en pantalla completa o fondo sólido, la línea principal ocupa al menos `pantalla_principal_ancho_min` del ancho (el error de la compuerta dice los números).

## Recursos de estilo (sirven en cualquier estilo de base «pantalla»; úsalos solo si la guía del estilo los pide)

- **Filtros nuevos** (escena `filtro`): `halftone` (semitono de imprenta B/N, para ráfagas de archivo) y `blueprint`
  (plano técnico azul con retícula isométrica y luces `acento2`).
- **Entradas de escena nuevas** (`entrada`): `zoom` (llega desde 104 % y se asienta en 0,7 s acelerando y desacelerando; C-0002: ya no es whip brusco, úsalo poco) y `pixel` (mosaico que se afina, 0,16 s).
  `estilo.aberracion_corte` (px) pone un pico de aberración cromática en el cuadro de cada corte (lo fija el preset).
- **Texto con volumen** (en cada línea de un `texto`): `"contorno": 5` = letra hueca (solo el borde, del `color` de la línea);
  `"trazo": [6, "negro"]` = relleno con borde; `"extrusion": [12, "acento"]` = bloque 3D duro hacia abajo a la derecha.
  Alterna relleno y hueco en palabras seguidas. La extrusión suma su ancho: mide.
- **Etiqueta tipo tag**: `fondo` y `letra` aceptan cualquier color (`blanco`, `negro`, `acento`, #hex), `radio` (px) redondea
  las esquinas y `rol` (`mono`, `display`, `script`) cambia la fuente: `{"tipo": "etiqueta", "fondo": "blanco", "radio": 14,
  "rol": "mono", "lineas": [["Confianza", 34, false, 700]], ...}`. Brotan con `entra: "pop"` y en cascada (0,2–0,3 s entre una y otra).
- **Bloques de píxeles** (`"tipo": "pixeles"`, `x`, `y`, `ancho`, `alto`, `celda` px, `colores`): glitch geométrico que se arma,
  parpadea 12 veces por segundo y se desarma. Pequeños (80–160 px), junto a una etiqueta o un texto, nunca tapando la cara.
- **Foto a pantalla completa**: en una `foto`, `"cubrir": true` la estira hasta llenar 1080×1920 (recorta lo que sobra,
  sin borde, sin sombra ni barras; `x`, `y` y `ancho` se ignoran). Para ráfagas de archivo: pide ese arte en `aspecto` "9:16".
- **Entradas de escena de collage editorial** (DRUpn): `"bloques"` (destello del acento 1–2 cuadros + mosaico + cuadrados del acento
  en cascada, 0,22 s) y `"invertir"` (negativo de 2 cuadros, cambio de idea).
- **Luz completa** (luminoso): `"luz": true` (o 0–1) en un `texto`, `foto` o `recorte` = retroiluminación + haze + glow + halation;
  `color_luz` (por defecto `acento2`). **Apoyo sutil**: `foto` o `clip` con `"ancho"` 500–700 y `"fundir": .55` (sin marco, bordes que
  se desvanecen en el fondo). **Clip** (`"tipo": "clip"`, `src` mp4): animación a pantalla completa (`cubrir`) o chica y fundida.
- **Fondos de muro**: `persona.fondo` `"muro-luz"` (petróleo con rayas diagonales de luz) o `"muro-claro"` (respiro gris-blanco).
- **Estilo**: `transicion: "desenfoque"` (rack focus en cada corte), `bloom` (0–1). La cámara es FIJA (perfil/reglas.json, nota «Cámara»): no escribas `punch`, `empuje`, `camara`, `camara_mov` ni `flotar`; el motor los ignora.
- **Datos**: `{"tipo": "contador", "x", "y", "desde": 0, "hasta": 100, "sufijo": " %", "cuenta_s": 1.0, "tam", "color", "rol"}`
  (cifra que cuenta) y `{"tipo": "barra", "x", "y" (centro de la base), "ancho", "alto", "color", "crece_s": .6, "contorno": true}`
  (crece desde abajo con contorno escalonado, como las barras de DRUpn).
- **Fusión de un apoyo**: `"fusion": "pantalla"` (el negro de la imagen desaparece, solo suma su luz) o `"multiplicar"` (el blanco
  desaparece, solo oscurece). Úsalo para que una foto con fondo negro no manche un fondo claro.
- **Palabra estirada en vertical**: en una línea de `texto`, `"escala_y": 1.0–2.0` (la palabra gigante alta de DfAE).
- **Peso y cursiva por línea** de `texto`: `"peso": 100–900` (por defecto 900) e `"italica": true` (usa el archivo itálico de la fuente).
  **Etiqueta sin sombra**: `"sombra": false`. **Foto en caja recta** limpia (sin borde ni sombra): `"caja": true` con `ancho`.
- **Editorial seco**: entrada de elemento `"smear"` (barrido horizontal de 2 cuadros); entrada de escena `"wipe"` (un campo del
  acento cubre el cuadro a saltos y se retira, 0,2 s); trazo `{"tipo": "reticula", "cols": 3, "filas": 3, "cruces": 14, "color", "t0", "dur", "t1"}`
  (retícula que se dibuja sola, con cruces de registro).
- **Todo flota (gusto de Pablo)**: `estilo.flotar_elementos` (px; el techo es `flotar_elementos_max` de reglas.json, igual para todos los estilos) hace que cada elemento derive solo, con fase propia; en
  cada elemento `"profundidad": 0–1` (0 = fondo, se mueve poco; 1 = adelante, se mueve más) da el parallax 3D, y `"flotar"` lo fija
  por elemento. Entrada `"llega"`: rápida que desacelera suave (ease-out exponencial, escala 1,15→1), pulida y elegante.
- **Apoyos literales y gratis** (fotos reales de dominio público): `uv run estudio archivo bajar "carpeta" --en "file folder" --proyecto proyectos/<x> -n 3`
  → `arte/arch_carpeta_1.jpg…` (créditos en `arte/CREDITOS-archivo.csv`). En la `foto`: `"tratamiento": "bn" | "halftone" | "duotono"`
  para que todas sean de la misma familia y `"fusion": "multiplicar"` para borrar su fondo blanco sobre claro; sobre oscuro: `"tratamiento": "duotono-inverso"` + `"fusion": "pantalla"` (el objeto flota suelto, sin caja). TODO apoyo lleva `"muestra"`.
- **Cámara FIJA (Pablo, 11-nov: «los movimientos de cámara lo que están haciendo es dañando el video… dejas todo estático»)**:
  la toma sale con su encuadre original, completa: sin zoom, viaje, flotación, reencuadre ni golpes. La regla es una sola
  (`perfil/reglas.json`, nota «Cámara»; el código pregunta en `camara.fija()`). La variedad va en transiciones, entradas de texto y apoyos.
- **Composición integrada** (Pablo: «mover el fondo, el apoyo y la fuente al mismo tiempo; texto e imagen como una sola composición
  de súper diseño»): los fondos `muro-*` ya derivan y respiran solos; dale el mismo `"grupo": "<nombre>"` al texto y a la imagen que
  forman una composición (se mueven juntos) y distinta `"profundidad"` a cada pieza (parallax dentro del grupo). Superpone texto e
  imagen (el texto puede pisar la imagen, con `fusion` o `luz`), varias piezas a la vez, todo en movimiento.
- Escena `entrada` `"iris"` (viñeta oval que se abre desde el centro, 0,4 s) y `"desenfoque"` (rack focus solo en esa escena).
  Trazo `elipse` acepta `color`; foto `caja` acepta `rot`.
- **Panel de vidrio** (glass): `{"tipo": "vidrio", "x", "y", "ancho", "alto", "radio": 28, "desenfoque": 22, "velo": .28, "t0", "t1", "dur"}`
  desenfoca lo que tiene detrás (la toma o el fondo), velo blanco, borde de luz y sombra amplia; flota. Pon texto `z: "frente"`
  encima con el mismo `grupo`. Dibújalo DESPUÉS de lo que debe quedar detrás (orden en `elementos`).
- **Apoyo vivo (C-0003, cine: «los apoyos son muy poco dinámicos»)**: en una `foto`, `recorte` o `clip`, `"acercar": .04–.15`
  lo acerca solo, lento y en una dirección durante toda su vida (Ken Burns; a pantalla completa sigue cubriendo). La compuerta
  rechaza más de .004 de zoom por cuadro: con vida corta, menos `acercar`. Úsalo en todo apoyo quieto.
- **Tecleo**: en un `texto`, `"tecleo": 10` (letras por segundo) con cursor `|` que parpadea (`"cursor": false` lo quita).
  **Barra horizontal**: `barra` con `"direccion": "horizontal"` (crece de izquierda a derecha; x, y = centro de la barra).
