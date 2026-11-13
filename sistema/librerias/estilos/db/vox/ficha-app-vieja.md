# Look: vox — el estilo VOX de The Product Lab (sistema que funciona, ejecutable)

Familia: vox · Estado: ✅ **LISTO** (Pablo aprobó la V4 'ingeniero inseguro' 2026-10-12: "está muy bien") · ejecutable con `tools/lab/vox.py` · Nació de la V2 ("mejor mucho") y se corrigió en la V3
(feedback de Pablo 2026-10-12). Los demás looks vox (`vox-mixed`, `vox-pop-mesa`, …) siguen siendo looks aparte.
Variantes (catálogo de la app): **vox tipo 1** = collage animado sin persona (V3, aprobada "no está mal") · **vox tipo 2** = persona + apoyos con texto integrado (V4/V5, lista).

## Cómo se usa (barato)
1. Escribir `edicion-claude/proyectos/<nombre>/plan.json`: paleta, duración, escenas (`t0`, `plantilla`, `fondo`,
   `p` con imágenes y tiempos, `texto` = líneas `[texto, tiempo o lista de tiempos por palabra, estilo]`).
   Marcas en el texto: `*palabra*` acento · `_palabra_` resaltador · `#palabra#` sello.
   Estilos de línea: `hero` (Anton), `medio`, `kicker` (Grotesk mayúscula), `typer` (máquina de escribir), `italica`, `sello`.
2. `python3 tools/lab/vox.py edicion-claude/proyectos/<nombre>` → `hf/index.html` (falla si se rompe una regla).
3. Revisar con UNA hoja de contacto (11 cuadros en una imagen), no con capturas sueltas.
4. `bash tools/render/render.sh <proyecto>/hf "<ruta absoluta>.mp4" --force` en segundo plano (~10 min / 30 s).

Plantillas de escena (11): `recorte_bloque`, `marco`, `objeto_ovalo`, `isotipo`, `oscuro_grieta`, `tira_recorte`,
`grafico`, `golpe_marco`, `ruta`, `chat`, `corona`. Agregar plantillas nuevas al generador, nunca HTML a mano por video.

## Reglas (el código las impone)
- **Un solo texto en pantalla a la vez**, en una capa propia encima del arte. Nada de rótulos, sellos o citas en otra
  zona: si una palabra importa, va dentro del bloque (sello/resaltador/acento).
- **Carril de lectura** (Pablo: "el texto puede estar en cualquier lado, pero para ir del punto A al D tiene que pasar
  primero por B y C"): el ancla del texto recorre todo el cuadro despacio (y 290–1090, lejos de los bordes) y deriva
  sin parar mientras está en pantalla; el bloque nuevo nace donde terminó el anterior y se acomoda. Alineado a la
  izquierda siempre. Compuerta: salto entre bloques ≤ 170 px vertical / 70 px horizontal.
- **El arte ocupa el espacio que el texto deja** (arriba o abajo de su recorrido), nunca debajo del texto.
- **Paleta de la casa**: 5 tonos + papel, `monocromo+acento` o `complementaria` (paletas en `PALETAS` de vox.py:
  tinta-ocre, grafito-rojo, oxido-pino, petroleo-naranja). Recortes en duotono de la paleta (nada de colores de la foto).
  Acento solo en 1-2 palabras por bloque; fondo de acento máx. 1 escena cada 30 s y apagado (82 %). Palabra en acento
  sobre fondo claro usa el acento oscurecido (legible).
- Zona segura IG para texto: y 230-1500.

## Piel (lo que lo hace "The Product Lab", sobrio y orgánico)
Fibra de papel, grano a 12 fps y viñeta dentro de cada apoyo (nunca sobre la persona), trama de puntos suave, viñeta, bloques con
desregistro de impresión (sombra sólida corrida + sombra suave), recortes con borde de papel hueso, luz cálida de un
solo tono, fricción stop-motion de recortes a 12 fps, cámara distinta por escena, barridos de papel entre algunas escenas.

## Mejor para
Explicar una idea frase a frase con objetos/personas recortadas: causa→efecto, roles, datos simples, metáforas
literales ("el marco", "a pecho"), listas, preguntas.

## Persona + apoyos (V4, aprobada)
- `plan.json` con `"persona": "corte.mp4"`, `carril` en el tercio bajo (no tapar la cara), `escala_texto` ~0,6,
  `bloques` = subtítulos solo sobre la persona (60-80 % del guion), `escenas` con `t0`/`t1` = apoyos.
- Apoyos con texto diegético (8 plantillas) + escenas `a_medida` (≥ 30 %, compuerta antirrepetición).
- **Ruido, fibra de papel y viñeta SOLO dentro de los apoyos a pantalla completa.** La persona va con el color del
  crudo: nada de grano, viñeta ni gradación encima, salvo un efecto pasajero y a propósito (transición, golpe).
