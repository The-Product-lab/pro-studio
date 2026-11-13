# Plano · Estilos Pro dentro del reel hablado (Lemo hace de todo, nosotros completamos)

Orden de Pablo (voz, 12-nov): «es un sistema similar a los otros 12 que ya tenemos, pero con Lemo… Lemo hace todos los apoyos de
pantalla completa, pero también los apoyos con la persona… lo que tenemos que lograr es utilizar esas animaciones dentro de nuestro
flujo: la persona empieza hablando, una caja de texto como hook, hay un subtítulo… A Lemo no se le puede decir nada, se le deja
totalmente la libertad. Cuando él entregue, vos revisás qué textos faltaron y los integrás en el diseño que él entregó.»
Y: «ojo, no estés creando otro motor». **No se crea ninguno:** Lemo entra por donde entra Higgsfield (`arte.json` → `arte/<id>`);
el render, los textos, el sonido y la cola son los de siempre. Lo anterior (película entera sin la persona, `estudio/pro.py`) se
conserva como capacidad de terminal (`estudio pro`); la app ya no la lanza.

## 00. Corrección tras la prueba F4 (12-nov, noche) — manda sobre lo de abajo
Pablo vio el video-3217 en impasto: los tramos «persona» (texto sobre negro para fundir sobre la toma) salieron negros. «Hay varias
escenas como en el segundo 11 que están de fondo negro. Las quiero con diseño de Lemo, como lo otro: fondos bacanos, figuras de
personas.» Y por el gasto (7,8 M tokens, casi todo relectura de caché de una sola conversación larga): «mira cómo puedes hacer
para que él no tenga que releer todo».
- **Una sola clase: `completo`** (o `nada`). La clase «persona», su fusión «pantalla» y sus compuertas de luma salen del código.
  Compuerta N3: `revisar` rechaza cuadros negros en toda entrega (texto sobre negro = no entra; reintento una vez).
- **Un encargo de Opus por tramo** (`hacer`): cada llamada lleva solo su tramo; un tramo que otro encargo ya dejó hecho (universo
  de varios tramos) no se vuelve a pedir; el techo del reel se descuenta con lo que gasta cada encargo.
- **Corregir sin rehacer:** borrar `lemo/<id>/` de los tramos a cambiar y volver a correr `lemo_apoyos.hacer`: lo entregado se
  conserva; las palabras se corrigen con `estudio corregir-capas` (mini editor).

## 0. Cambio de diseño (12-nov, tarde): Lemo no es un proveedor de clips, es el que hace de todo
Pablo leyó la primera versión (Lemo en lugar de Higgsfield, nuestro director decide dónde va cada apoyo y con tope) y la corrigió:
> «Sí, pero no solamente el reemplazar a Higgsfield… Lemus tiene la capacidad de hacer de todo, o sea, textos, los apoyos completos,
> los universos enteros, ya.»
> «Lemus puede hacer de todo, pero pues no es una camisa de fuerza, o sea, tú tienes que ver dónde puso los textos y tú revisas qué
> faltaron y las pones tú en el estilo mismo de Lemus.»

Qué cambia (recado `claudio/cerebro/drafts/T-0198-recado-lemo-hace-todo.md`; lección `lemo_dejarlo_crear`: encajonado rinde poco):
- El director nuestro ya no decide ni limita los apoyos: **marca los tramos** del reel (dónde y cuánto dura cada uno) sin tope;
  Lemo decide en cada tramo si hace algo, qué y de qué clase (completo o sobre la persona), con textos o sin ellos, y puede
  atravesar varios tramos con un mismo universo. Lo que entrega se usa; lo que no entrega no es una falla.
- Los textos que faltan se buscan en **todo el reel**, no solo en los apoyos completos: medimos lo que Lemo mostró (`TEXTS`) en
  cada entrega, y lo que falta lo mostramos nosotros **en el estilo de Lemo** (acento y letra de su `plano.json`): dentro de su
  película en los completos, y con el gancho y el subtítulo nuestros (que toman su acento y su letra) en todo lo demás, también
  donde Lemo no hizo nada.
- Se quedan igual: la persona en su toma (sin recorte, cámara fija) y la cara libre; la zona segura; un solo camino de render,
  textos y cola; a Lemo solo el contrato técnico; una entrega fallida nunca deja hueco ni tumba el render.

## 1. Contrato
**Entra:** un proyecto con el guion aprobado (machote) y un estilo de Lemo (`lemo-opuscar/styles/<slug>`), pedido como
`--estilo lemo:<slug>` (terminal) o desde Estilos Pro (app). Cualquier video hablado: con o sin cortes, corto o largo, con la cara
visible o no en un tramo.
**Sale:** `proyectos/<p>/final.mp4`, un reel hablado como los otros: la persona en su toma, gancho, subtítulos, y lo que Lemo quiso
hacer en los tramos que le ofrecimos:
- **completo**: pantalla entera, la persona no se ve (la escena queda `persona.modo = "oculta"` solo si Lemo entrega un completo).
- **persona**: animación sobre la toma; Lemo no rinde con transparencia, así que va sobre NEGRO puro y el motor la funde con
  `fusion: "pantalla"` (ya existe). La cara (la caja que le damos) queda en negro.
- **nada**: Lemo puede dejar un tramo sin hacer (`plano.json › "clase": "nada"` o no entregarlo): ahí sigue la persona.
- Textos: Lemo pone los que quiera (gancho, palabras clave, títulos) registrados en `window.TEXTS`. El 100 % de las palabras del
  guion queda en pantalla: lo de Lemo + lo que completamos nosotros (en su película o con el subtítulo), medido al final.
**Nunca:** una palabra del guion sin mostrarse; la cara tapada o la persona recortada; un tramo que Lemo no entregó dejando un hueco
(pantalla sin persona y sin arte) o tumbando el render; texto que solo se lea fuera de la zona segura; instrucciones de diseño a
Lemo (solo el contrato técnico); un segundo camino de render, de textos o de cola; reusar una entrega hecha para otro pedido.

## 2. Arquitectura (cada pieza ya existe; lo nuevo es un preset, un proveedor y unas medidas)
1. **Guion aprobado** (machote) — igual.
2. **Director nuestro** (Opus, `director.dirigir`, preset `lemo`, sección `director/arte_lemo.md`): arma el reel hablado (gancho,
   escenas, subtítulos) y MARCA los tramos que le ofrece a Lemo, sin tope y sin decir cómo: un elemento
   `{"tipo": "clip", "src": "arte/<id>.mp4", "cubrir": true, t0, t1}` por tramo y en `arte.json` `{"id", "clip": true, "idea"}`.
   Propone la clase con la escena (oculta = completo; con la persona + `fusion`), pero es solo una propuesta.
3. **Lemo** (Opus con su biblioteca, `estudio/lemo_apoyos.py`, prompt `director/lemo_apoyos.md`) — recibe TODOS los tramos en una
   sola llamada (así puede hacer un universo continuo): id, duración, clase propuesta, idea, palabras con su tiempo (desde `t0`) y
   la caja de la cara. Libertad total. Por cada tramo que quiera hacer deja `lemo/<id>/` con `index.html` (`render`, `DUR`,
   `TEXTS`), `pelicula.mp4` 1080×1920 30 fps sin audio y `plano.json` (`acento`, `tramos[].integracion` y, si quiere, `clase`).
4. **Compuertas por entrega** (código, `revisar`): tamaño, cuadros por segundo, duración, `TEXTS`, sin negros (completo) / fondo
   negro y cara libre (persona). Solo lo ENTREGADO que falla tiene una vuelta de corrección; lo que no pasa no entra.
5. **Al storyboard** (código): la escena de cada tramo queda como la entrega de Lemo (completo → persona oculta; persona o nada →
   la persona se ve) y la fusión del clip según su clase. Lo que no llegó lo quita `imagenes.quitar_sin_arte`, ya con la persona
   de vuelta en su escena: nunca queda hueco.
6. **Textos de todo el reel** (cadena de Pro, sin cambios): en cada entrega `textos_lemo.medir` dice qué palabras mostró Lemo
   (solo cuenta lo que cae en la zona segura). En los completos `mapa_texto` + `texto_pelicula.componer` agregan las que faltan
   dentro de su película, con su letra. En el resto, el subtítulo nuestro: se oculta solo el bloque cuyas palabras ya están todas
   en pantalla. El bloque `estilo` toma el acento y la letra de Lemo (`plano.json`), salvo lo que la persona eligió para ese video.
   Medida final: `lemo/cobertura.json` (palabras, cuántas puso Lemo, cuáles quedaron sin mostrar: debe ser ninguna).
7. **Ojo, Personalizar, Exportar, sonido** — igual que cualquier estilo.

Tiempo: el storyboard va en tiempo FUENTE y el motor reproduce el clip por `t − t0`. Las palabras se le dan a Lemo en ese reloj
(segundos desde `t0`), sin las que cortó el machote; si un corte cae dentro del tramo, el clip salta ahí lo mismo que la toma.

## 3. Abogado del diablo (cómo se rompe el diseño nuevo) → qué lo impide
1. *Sin tope, el director marca veinte tramos y Lemo tarda horas.* → techo por reel en código (`TOPE_USD_REEL`, `TIMEOUT_REEL_S`),
   no por cantidad; Lemo sabe que no está obligado a llenar todos, y lo entregado se revisa uno por uno.
2. *Lemo no entrega un tramo que el director dejó sin persona → pantalla vacía.* → el código devuelve la persona a toda escena cuyo
   tramo no tiene entrega buena, ANTES de `quitar_sin_arte`. Prueba: `test_lo_que_lemo_no_hizo_deja_a_la_persona`.
3. *Lemo convierte un «persona» en completo (o al revés) y la escena no cuadra.* → la clase final la da su `plano.json`; el código
   parte o ajusta las escenas del tramo (`_persona_en`); la compuerta mide según la clase final; la caja de la cara va en todos.
4. *Se reusa una entrega vieja (otro estilo, otro tramo con el mismo id) o un `arte/<id>.mp4` viejo.* → `pedido.json` con la firma
   (estilo, t0, t1) en cada `lemo/<id>/`: si no coincide, se borra; el `arte/<id>.mp4` de cada pedido se rehace siempre.
5. *Ocultar el subtítulo de un tramo entero borra palabras que caen en el borde del bloque.* → se oculta por BLOQUE de subtítulo y
   solo si todas sus palabras ya están en pantalla; la medida final (`cobertura.json`) lista lo que haya quedado sin mostrar.
6. *Lemo pone texto fuera de la zona segura (lo tapa Instagram).* → ese texto no cuenta como mostrado (`textos_lemo` lee su caja);
   la palabra la ponemos nosotros dentro de la zona.
7. *Lemo pone texto sin registrarlo en `TEXTS`.* → solo se cree lo registrado; lo demás se completa (puede salir repetido, nunca falta).
8. *En un apoyo «persona» Lemo tapa la cara o el fondo no es negro.* → compuerta de luma en el marco y en la caja de la cara.
9. *Nuestro texto no combina con Lemo.* → acento y letra salen de su `plano.json` (la integración que más dura da la letra); la
   persona los puede cambiar en Personalizar como en cualquier estilo, y lo que ya eligió para ese video no se pisa.
10. *Lemo tarda o se corta a medias.* → lo entregado y bueno se usa; un pedido retomado no rehace lo que ya pasa.
11. *La máquina no tiene a Lemo* → la app lo dice antes de elegir (`motor`) y el servidor responde 409. *macOS viejo sin navegador*
    → `laboratorio-estilos/navegador-lemo`. *Se confunde con la película entera de antes* → una sola puerta en la app (esta).

## 4. Fases (cada una con su criterio y su comando)
- **F1 · Proveedor** (hecho). `estudio/lemo_apoyos.py`: pedidos, prompt, compuertas, textos faltantes.
  CUANDO hay `arte.json` con `clip: true` y una IA de prueba entrega las carpetas, EL SISTEMA DEBE dejar `arte/<id>.mp4` solo de
  los que pasan. `uv run pytest -q tests/test_lemo_apoyos.py`
- **F2 · Director** (hecho). Preset `lemo` (oculto del selector normal), su guía, su ejemplo, y el pedido de clip en la compuerta.
  CUANDO el director pide un clip, EL SISTEMA DEBE validarlo sin exigir el archivo todavía. `uv run pytest -q tests/test_lemo_director.py`
- **F3 · Lemo hace de todo + flujo y app.** Director sin tope (solo tramos); Lemo elige clase o nada; escenas según su entrega;
  textos de todo el reel por bloque; estilo de Lemo en gancho y subtítulo; `_dirigir` con `lemo:<slug>`; Estilos Pro en la app
  lanza ESTE flujo y sigue en Personalizar/Exportar.
  CUANDO Lemo entrega unos tramos, cambia la clase de otro y no hace un tercero, EL SISTEMA DEBE dejar las escenas como él las
  entregó, la persona a la vista donde no hizo nada, ninguna palabra sin mostrar (`cobertura.json › sin_mostrar` vacío) y el
  acento y la letra de Lemo en el estilo; Y CUANDO la app pide `lemo:<slug>`, EL SISTEMA DEBE dirigir con el preset `lemo` sin
  pasar por Higgsfield. `uv run pytest -q tests/test_lemo_apoyos.py tests/test_lemo_flujo.py tests/test_lemo_director.py tests/test_pro_api.py`
- **F4 · Prueba real.** `video-3217_singular_display.MOV` (175 s, carpeta `~/Desktop/prestigio /`), un estilo, de punta a punta en
  esta Mac. CUANDO termina, EL SISTEMA DEBE dejar `final.mp4` y `lemo/cobertura.json` con `sin_mostrar` vacío; se anota aquí tiempo,
  consumo, cuántos tramos marcó el director y cuántos hizo Lemo, y el caso entra al banco de pruebas.
  `uv run python -c "import json,sys;sys.exit(1 if json.load(open(sys.argv[1]))['sin_mostrar'] else 0)" proyectos/<p>/lemo/cobertura.json`

## 5. Estado
- 12-nov: Lemo instalado en la Mac (`laboratorio-estilos/lemo-opuscar`, navegador propio), cadena de textos probada con el motor
  real (21 pruebas). F1 y F2 hechos.
- 12-nov, tarde: corrección de Pablo (sección 0). Contrato y arquitectura reescritos; F3 con el diseño nuevo. F4 pendiente (Isis).
