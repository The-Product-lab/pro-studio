# Look: swiss-motion — «Swiss motion» (Estilo 12, tipografía suiza internacional en movimiento)

Familia: persona + apoyos con motion graphics · Estado: en prueba · Generador: `tools/lab/swiss_motion.py` · Referente (MIT): `../../../referencias/lemo-opuscar/styles/swiss-motion/STYLE.md`

- **Identidad**: papel + tinta negra + gris claro y UN solo color de señal; cuadrícula de 6 columnas siempre visible (líneas finas que se dibujan al entrar); formas planas, sin degradados, sombras ni grano; Inter en una sola familia, minúscula, alineada a la izquierda; escala extrema (numeral gigante junto a notas chicas en mono). Sensación Apple keynote sobria.
- **Mejor para estas tomas de apoyo**: cifras y numerales · listas de pasos o causas · contrastes (esto / aquello) · errores y correcciones (lo tachado) · frases cortas de remate
- **Paletas** (`plan.paleta`): rojo (`#F2F0EA` / `#141414` / señal `#E30613`, por defecto) · naranja (`#FF5A00`) · azul (`#1F3FFF`). Solo una cosa lleva la señal por pantalla.
- **Tipografía**: Inter 700–800 (letter-spacing −4 %), JetBrains Mono para notas y números de fila.
- **Plantillas de apoyo (7)**: `titular_rejilla` · `numeral_gigante` · `lista_modulos` · `barras_modulos` · `partido` · `excepcion` · `corte_cuchillo`
- **Capas sobre la persona (3)**: `etiqueta` (cartel de museo con barra de señal) · `cifra_modulo` · `barra_tinta`
- **Subtítulo**: caja de papel pegada a la columna 1; cada palabra sube desde su línea base en SU instante (clip-reveal); palabra clave en tinta sobre el color de señal. Con una capa «sobre» no hay subtítulo (una sola cosa en pantalla).
- **Movimiento**: una sola curva `cubic-bezier(.7,0,.2,1)` para todo snap; sin rebote ni resorte; entradas por barrido (clip) o por subida desde la línea base, nunca por fundido; los numerales suben por pasos. La «excepción» es lo único lineal y fuera de la cuadrícula; lo borrado se corta con una línea de cuchillo.
- **Transiciones**: el apoyo entra con barrido lateral y las líneas de la cuadrícula se dibujan; al volver a la persona, fundido (regla de Pablo, ≥ `FUNDIDO` s), no corte seco.
- **Sonido**: papel al entrar el apoyo, clic en cada fila/numeral, raspón de papel en el corte de cuchillo; el motor de sonido del editor puede sustituirlos.
- **Qué lo hace distinto**: es el único look sin textura ni color de acompañamiento: todo el efecto sale de la rejilla, la escala y la precisión del movimiento. Frente a Retro/Cuaderno (papel, objetos) es frío y exacto.
- **Costo**: cero IA; solo texto y números del plan (sin imágenes). Render 35 s ≈ 2 min en la Mac.
