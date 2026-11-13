# La re-escucha de las pausas: qué se midió el 11-nov

**Problema (Pablo):** «lleva casi 15 min en los guiones… es muy lento». En una Mac Intel de 2017 (sin tarjeta NVIDIA) la re-escucha de
un video de 2 min 39 s tomó 17 min: 34 llamadas a Whisper (19 pausas + 15 palabras largas), ~29 s cada una, porque cada llamada
procesa una ventana completa de 30 s aunque el trozo dure medio segundo.

## Lo que se probó y NO sirve: juntar los trozos en una sola pasada
Pegar los trozos con un silencio entre ellos y transcribirlos juntos baja el tiempo de ~17 min a ~1,5 min, pero Whisper oye otra cosa:
- Con su descarte de «no hay voz» encendido, tras el primer trozo se salta el resto de la ventana (IMG_4965: 0 de 11 voces iguales).
- Con el descarte apagado oye más en la pausa larga del inicio, pero REPITE frases en las pausas cortas
  («Ponla en un pedestal, escríbele todos los días, ¿cómo es?» dos veces): palabras fantasma que acabarían como cortes en el guion.
Este paso decide qué palabras existen en el guion: sin las mismas palabras, no entra. Quedó descartado.

## Lo que sí entró
- La re-escucha avisa por cuál va («re-escuchando las pausas: 12 de 34…») y se puede detener entre una y otra.

## Opciones abiertas (decisión de Pablo)
1. **No re-escuchar pausas en silencio.** En 4 videos reales, toda pausa donde el método actual encontró voz tenía un pico de al
   menos −47 dB por dentro; con un umbral de −50 dB se evitarían 6 de 19, 6 de 28, 21 de 44 y 3 de 10 re-escuchas (20–50 %).
   Riesgo: el margen es de 3 dB y solo son 4 videos; una voz muy baja de fuera de cámara podría pasar sin revisar.
2. **Un modelo más chico solo para la re-escucha** (p. ej. Whisper small: ~6× más rápido, ~460 MB más de descarga). Hay que medir
   si encuentra las mismas voces.
3. **Máquina con GPU NVIDIA** (el PC de la oficina): ahí cada llamada tarda una fracción y el paso no pesa.
