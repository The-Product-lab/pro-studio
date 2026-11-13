# Básico — el estilo número 1 (Pablo, 08-nov)

«Un estilo BÁSICO, que sea el PRIMERO: solo subtítulo word by word; se le puede poner cualquier color, caja de color y algún efecto,
pero nada más. Es el más importante porque es el que más se va a usar.» Referente: reel `DcT81r7Otdh`
(análisis en `laboratorio-estilos/referentes/DcT81r7Otdh.md`).

## Qué es
La toma de la persona tal cual (con su color), cámara fija, y encima SOLO el subtítulo palabra por palabra. Sin motion graphics, sin
fotos, sin pantallas completas, sin cámara extra, sin textos animados. No usa director: el storyboard sale determinista de
`palabras.json` (`estudio/subtitulo_basico.py › armar`), cuesta 0 de Opus. Preset con `sin_director: true`.

## El subtítulo (del referente)
- Mayúsculas pesadas (Inter 900), blancas, 1–3 palabras por línea, bloques de hasta 3 palabras; centro dentro de la zona segura.
- Cada palabra aparece cuando se dice; el bloque ya está medido, nada se corre.
- Una palabra clave por bloque (la más larga con contenido, nunca en bloques seguidos) en otro color (rojo por defecto).
- Sombra suave, sin contorno.
- Sonido: efectos suaves en los cortes (paleta orgánica), como hoy.

## Opciones (claves de `estilo`, van por `preferencias.json` como el color)
| Clave | Valores | Por defecto |
|---|---|---|
| `sub_color` | #RRGGBB, color del texto | #FFFFFF |
| `sub_clave` | #RRGGBB, color de las palabras clave | #E5252A |
| `sub_caja` | true/false, caja de color redondeada detrás de cada línea | false |
| `sub_caja_color` | #RRGGBB | #E5252A |
| `sub_efecto` | `corte` (seco, el del referente) · `pop` (escala con rebote) · `sube` (sube y aparece) | corte |

Los números (tamaño, y, sombra, duraciones) viven solo en `estudio/subtitulo_basico.py`.

## Reglas
`perfil/reglas.json › estilos.basico` apaga las reglas de ritmo, recursos, golpes de zoom, flotación e inicio limpio. Es la excepción escrita a la regla de cámara: cámara quieta, la toma tal cual.
Siguen valiendo la compuerta de color/fuentes/rosa y «texto siempre» (el subtítulo cubre todo).

## Orden en la lista
Va PRIMERO: `catalogo.PRIMEROS` y es la primera clave de `presets.json`. Si la app (`app/`) arma su propia lista, que respete ese orden.
