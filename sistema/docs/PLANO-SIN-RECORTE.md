# Plano: la persona se ubica, no se recorta (11-nov)

**Orden de Pablo:** «el recorte frame por frame únicamente sirve para poner cosas detrás de la persona. Pero yo no necesito recortar
para saber dónde está la cara… elimina el tema de recortes de todo, no le veo uso».

## Qué pasaba
- La ingesta separaba a la persona del fondo en TODOS los cuadros (RVM): 21 min en una Mac para un video de 2,5 min, antes de elegir estilo.
- La regla `sujeto_recortado_prohibido` (04-nov) ya prohibía mostrarla recortada: de esas máscaras solo se usaba la posición de la cara.
- Esa posición además salía mal con fondos con maniquíes o figuras (IMG_4965: «cara» de 688 px de ancho).

## Contrato
- CUANDO se prepara un video EL SISTEMA DEBE dejar `persona.json` (cara y cuerpo cada 15 cuadros) y NO crear `alpha/`.
  Verifica: `pytest tests/test_persona.py`.
- CUANDO el director, el motor o una compuerta necesitan saber dónde está la persona EL SISTEMA DEBE leerlo de `estudio/persona.py`
  (único lugar). Verifica: `pytest tests/test_persona.py::test_un_solo_lugar_ubica_a_la_persona`.
- La persona va entera (`completa`) o no va (`oculta`). No existen la base `collage` ni los modos `recorte`, `silueta`, `neon`.
  Verifica: `pytest tests/test_validar.py -k collage`.

## Cómo
- `estudio/persona.py`: detector de caras YuNet (OpenCV Zoo, 230 KB, por onnxruntime), 2 cuadros por segundo, interpolado.
  El cuerpo se ESTIMA desde la cara (no se mide).
- Medido en la Mac Intel de 2017: 7–22 s por video (antes ~21 min). La tarjeta Radeon no ayuda al modelo viejo (CoreML 5× más lento).
- RVM se queda solo para `estudio/archivo.py` (saber si una FOTO del archivo muestra a una persona).

## Proyectos viejos
Tienen `alpha/` y no `persona.json`: `ingesta.preparar_media` (lo llama cada edición) crea el `persona.json` en segundos. La carpeta
`alpha/` ya no se lee; se puede borrar.
