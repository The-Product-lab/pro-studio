# Plano — Editor por capas: correcciones sin rehacer (Pablo, 09-nov)

Orden (09-nov): «revisar el mini editor… que en correcciones no gastes tokens. Todo el editor debe ser así: yo te doy un video, tú creas
el código, el estudio normal; pero no quiero que gastes tokens en correcciones: trabajos por capas, como Photoshop, DaVinci o Premiere,
donde solo entrás, hacés el cambio exacto y no tenés que rehacer nada más». Aprobado con: «no hay problema de meter IA para entender el
error y la corrección».

## 0. Cómo está hoy
- El video ya es datos por capas: `storyboard.json` (cortes, escenas, elementos, trazos, subtítulos, cámara/punch/empuje, estilo) y el
  render ya es por tramos (`estudio/tramos.py`: solo se re-exportan los segundos que cambiaron).
- Pero **cada corrección la piensa Opus** (`estudio/agente`): lee el repo y todo el storyboard y edita a mano (tope 4 USD por corrección).
- Estilos Pro: la película es código (`film.js` de Lemo): cualquier cambio es Opus reescribiendo código.

## 0b. No degradar el editor (Pablo, 09-nov: «ojo, ¿eso toca el editor? No podemos degradar el editor; esto es una cosa aparte»)
- Todo es **aditivo**: módulos nuevos (`capas.py`, `corrector_capas.py`) que usan el storyboard y `tramos` como ya existen.
- **No se tocan** `motor.py`, `validar.py`, `tramos.py`, `montaje.py`, el director normal ni sus prompts. El flujo de crear un video
  queda idéntico.
- El Agente Editor de hoy sigue entero como respaldo: si el intérprete no está seguro, la corrección va a él como siempre.
- `/api/corregir` usa capas solo para operaciones validadas; se puede apagar con una sola bandera (vuelve al flujo de hoy).
- Compuerta: `estudio verificar` + golden set del editor iguales antes y después de cada fase.

## 1. Contrato
**Entra:** una corrección de Pablo (texto o voz transcripta), opcionalmente con el segundo y el estilo/proyecto; o un cambio directo
hecho en el panel de capas de la app.
**Sale:** el mismo video con SOLO ese cambio, re-exportado por tramos; un registro con lo que se cambió (deshacer de un paso) y los
tokens gastados.
**Nunca:** rehacer el video entero por un cambio de capa; que la IA edite el storyboard o el código a mano para un cambio de capa
(la IA solo interpreta; el cambio lo aplica código); un cambio que no pase `validar.py`; perder el estado anterior (siempre se puede deshacer).

## 2. Diseño
1. **Capas** (`estudio/capas.py`): vista por capas del storyboard (texto, gráficos/elementos, trazos, subtítulos, cortes, cámara, color,
   sonido) con un catálogo cerrado de OPERACIONES deterministas: `texto.editar`, `texto.estilo` (tamaño, color, peso), `mover`, `escalar`,
   `tiempo` (t0/t1/corrimiento), `borrar`, `agregar_texto`, `subtitulo.palabra` (cambiar cómo se escribe), `subtitulo.ocultar`,
   `camara.golpe`/`camara.quitar`, `color.ajuste`, `sonido.volumen` (música/sfx), `corte.quitar`/`corte.restaurar` (palabras).
   Cada operación valida (validar.py), guarda el anterior (deshacer) y devuelve los tramos que tocó.
2. **Intérprete** (`estudio/corrector_capas.py`): la corrección → lista de operaciones.
   a) Reglas en código para lo común («más grande el título», «cambiá X por Y», «quitá el gráfico del segundo 12», «bajá la música»,
      «que diga Claude», «sacá esa palabra») → 0 tokens.
   b) Lo demás: **una llamada chica** (Sonnet, `ia.llamar`, sin herramientas) que ve SOLO la corrección, el segundo y las capas que hay
      en ese momento (JSON compacto) y el catálogo de operaciones → devuelve operaciones en JSON. Tope bajo (constante).
   c) Si la corrección no es de capa (gusto general, falla del sistema, algo que el catálogo no cubre) → recién ahí el Agente Editor de
      hoy (Opus), como siempre.
3. **Aplicar y exportar**: operaciones → storyboard → `tramos` (solo lo que cambió). Previa del segundo afectado para la revisión.
4. **Registro**: `perfil/correcciones.jsonl` sigue igual (frase literal); se suma `capas.jsonl` por proyecto con operación, antes/después,
   tokens (0 si fue por reglas) y segundos.
5. **App — panel de capas** (carril Mac, fase aparte): línea de tiempo; tocar un segundo muestra sus capas; editar directo (texto, mover,
   color, borrar, tiempo, volumen) llama a las mismas operaciones → 0 tokens.
6. **Estilos Pro con capas**: el director de Lemo deja la película con sus capas como DATOS que `film.js` lee: `capas/texto.json`
   (cada texto: contenido, letra, color, tamaño, lugar en el mundo, entrada, t0/t1), `capas/camara.json`, `capas/color.json`
   (paleta), `capas/sonido.json` (niveles de música/sfx). Así las mismas operaciones corrigen una película Pro sin llamar a Opus.
   (Se encadena con el integrador de texto: `ESCRIBIR` escribe en la capa de texto.)

## 3. Abogado del diablo
1. *El intérprete entiende mal y cambia otra cosa.* → la operación devuelve la previa del segundo y el «antes/después»; deshacer de un
   paso; las reglas solo disparan con frases inequívocas; ante ambigüedad la llamada chica devuelve `pregunta` y no cambia nada.
2. *Una corrección mezcla capa + gusto («el título más grande, siempre»).* → se parte: la parte de capa por operaciones, la de gusto al
   agente (o a `perfil/gusto.md` por regla).
3. *El catálogo no alcanza.* → cae al agente de hoy; cada caída se registra y si una clase se repite se vuelve operación nueva (con prueba).
4. *Tramos reusa algo viejo.* → tramos ya compara el cuadro del medio de cada tramo reusado; ante duda exporta entero.
5. *Pro: Lemo no deja capas.* → el prompt lo exige y una compuerta en código lo mide (existe `capas/texto.json` y `TEXTS` sale de él);
   si falta, la corrección de esa película cae a la ronda de Opus (como hoy).
6. *Carril de la Mac (app/, servidor.py).* → backend y API primero; el panel es fase aparte y avisada.

## 4. Fases (cada una con su verificación, sale 0)
- **F1 capas** — CUANDO se aplica una operación del catálogo EL SISTEMA DEBE cambiar solo esa pieza, validar, guardar deshacer y
  devolver los tramos tocados. `uv run pytest -q tests/test_capas.py`
- **F2 intérprete** — CUANDO llega una corrección común EL SISTEMA DEBE resolverla por reglas con 0 tokens; CUANDO no es común, con una
  sola llamada chica (IA falsa en la prueba); CUANDO no es de capa, derivarla al agente. `uv run pytest -q tests/test_corrector_capas.py`
- **F3 ruta** — `/api/corregir` prueba primero capas y solo después el agente; registra tokens. `uv run pytest -q tests/test_corrector_capas.py -k api`
- **F4 Pro con capas** — director/pro.md + compuerta de capas; operaciones sobre una película Pro mínima. `uv run pytest -q tests/test_capas.py -k pro`
- **F5 panel en la app** — carril Mac, avisado. 
- **F6 prueba real** — 5 correcciones típicas de Pablo sobre un reel real: tokens y tiempo medidos.
- Compuerta del repo: `uv run estudio verificar` verde en cada fase.
