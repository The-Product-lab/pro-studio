# Plano: sonido (SFX) ordenado — 2026-11-04

Pedido de Pablo: «reorganiza el módulo de sonido que nunca se pulió en la app… ojo con crear código por crear: las últimas dos
veces dañaste el editor y se embruteció por meter el contenido y la educación a la fuerza».

## Contrato
- **Entra:** el storyboard (escenas, elementos, trazos, `punch`, y si lo trae, `sonido` escrito a mano), `estilo.sfx` (volumen,
  0 = sin efectos, el deslizador de la app) y `estilo.sonido_paleta` opcional; el banco CC0 puede estar vacío (entonces se sintetiza).
- **Sale:** `sfx.wav` mezclado bajo la voz (−14 LUFS) y `sfx-informe.json` (efectos, por minuto, menor separación, nivel).
- **Nunca:** un pop por cada elemento; dos efectos en menos de 0,18 s (salvo las capas de un mismo golpe); más de 2 efectos en un
  segundo; un efecto que llegue DESPUÉS de lo que lo causa; música (solo del banco de Pablo, que aún no existe).

## Qué cambia (solo `estudio/sonido.py`, + 1 clave en la compuerta, + pruebas)
1. **Qué suena** (reglas del curso de Julián, `BASES-EDITOR.md §4`, «sutil; si se notan, sobran»): transición de escena, texto
   principal (tam ≥ 90), apoyo que entra, trazo, `punch`. Lo chico (etiquetas, píxeles, textos secundarios) no suena.
2. **Densidad**: separación mínima y tope por segundo; si sobran, se queda el más importante.
3. **Antes que la reacción**: cada efecto se alinea por su PICO (no por su inicio) al cuadro del evento; el whoosh culmina en el corte.
4. **Capas en el impacto** (`punch`): golpe + swish previo + boom grave, a ganancias distintas.
5. **Paleta por estilo** (Pablo: «el estilo de SFX depende del estilo de edición»): `suave`, `papel`, `digital`, `cine`; cada una
   elige del banco qué suena en cada evento. Por defecto `suave`.
6. **Variación**: rota archivos del banco y varía ganancia (±1,5 dB) para que no suene a máquina.

## Abogado del diablo (cómo se rompe)
- «Quitar sonido a lo chico deja escenas mudas» → la transición y el texto principal siempre suenan; una prueba lo mide.
- «La alineación al pico adelanta sonidos antes del inicio del video» → se recorta a 0.
- «Copias que ya traen `sonido` a mano cambian» → lo escrito a mano se respeta (solo se alinea al pico).
- «El deslizador de la app deja de funcionar» → `estilo.sfx` sigue siendo el volumen; 0 = mudo (prueba).
- «Se vuelve otro módulo grande» → todo cabe en `sonido.py`; sin texto nuevo para el director.

## Criterio y verificación
CUANDO se renderiza un video, EL SISTEMA DEBE dejar `sfx-informe.json` con menor separación ≥ 0,18 s y ≤ 2 efectos/s.
Comando: `uv run pytest -q tests/test_sonido.py` (sale 0).
