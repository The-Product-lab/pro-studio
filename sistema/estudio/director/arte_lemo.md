## Tramos para Lemo (él decide qué hace en cada uno; tú solo los marcas)
Lemo puede hacer de todo: apoyos de pantalla completa, apoyos sobre la persona, textos (gancho, palabras clave, títulos) y un
universo que atraviese varios tramos seguidos. No es una camisa de fuerza: en cada tramo hace lo que quiera, o nada. Tú le ofreces
los tramos, sin tope: los momentos donde la voz dice algo que se pueda ver, del largo que pida la idea (un tramo largo o varios
seguidos le dejan armar un universo continuo). Por cada tramo, dos cosas:
1. En `storyboard.json`, un elemento `clip` que ocupa el tramo:
   `{{"id": "a1", "tipo": "clip", "src": "arte/a1.mp4", "cubrir": true, "x": 540, "y": 960, "muestra": "<la palabra que se dice ahí>", "t0": …, "t1": …}}`
   Propón la clase con la escena (Lemo la puede cambiar y el código ajusta las escenas a lo que él entregue):
   - Pantalla completa: en una escena con `"persona": {{"modo": "oculta"}}` que dure lo mismo que el clip.
   - Con la persona: en una escena con la persona `completa`, y al clip le agregas `"fusion": "pantalla"`.
   `t0` es el inicio de una palabra y `t1` el final de una idea. Nunca en los primeros segundos (van limpios, con la persona).
2. En `arte.json`: `[{{"id": "a1", "clip": true, "idea": "<qué dice la voz en ese tramo, en una frase>"}}, …]`.
   Solo la idea: nada de cómo dibujarla. El archivo `arte/a1.mp4` no existe todavía; lo entrega Lemo después, si lo hace.
No pidas imágenes (nada de `prompt`): en este estilo todo el arte es de Lemo. Dentro de los tramos no pongas etiquetas ni ocultes
el subtítulo: lo que Lemo no muestre lo completamos nosotros con su letra y su color, según lo que él entregue.
