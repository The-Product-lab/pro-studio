## Arte a medida ({imagenes})
Escribe `arte.json` (máximo {tope}): `[{{"id": "mapa", "prompt": "…", "recorte": false, "aspecto": "3:4"}}, …]`.
- Prompt en inglés con estos bloques, en orden: concepto · sujeto · composición · luz · fondo · materiales · lente ·
  paleta · referencia de estilo · calidad · qué evitar. Fotos: «vintage black and white archival photograph…, film grain».
  Mapas o grabados: «antique engraved map…, sepia ink on aged paper». Objetos para recortar: «isolated single object on plain white background» y `"recorte": true`.
- Nada de texto legible dentro de las imágenes (el texto lo ponen las etiquetas). Nada de caras de personas reales.
- En el storyboard usa `"src": "arte/<id>.png"`. Para los trazos sobre una imagen que aún no existe, estima `centro` y
  `radio` en píxeles de esa imagen (2048 de ancho si es 1:1; 1760×2352 si es 3:4; 2352×1760 si es 4:3). Después alguien
  los ajusta mirando la imagen real.
