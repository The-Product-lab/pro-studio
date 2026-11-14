# Plano: repartir una grabación en videos (T-0333, corrección de Pablo del 13-nov)

Pablo: «yo te puedo entregar 30 archivos de video y tú miras cuántos videos finales salen… puede que tres archivos sean un video,
cinco archivos un video… tienes que revisar a través de las transcripciones qué idea se cierra, qué guion se cierra».
La base ya existe: subir varios archivos y unir partes (`estudio/unir.py`). Esto la agranda: el sistema decide QUÉ archivos forman
cada video; la persona lo aprueba.

## Contrato
- **Entra:** N archivos de una grabación (de 1 a 30 o más), en cualquier orden. Puede haber: varias tomas de la misma idea, tomas
  falladas, archivos que solos son un video, archivos que juntos son un video, un archivo con dos ideas, archivos sin voz o sin
  sonido, tamaños y cuadros por segundo distintos. El nombre y la fecha ayudan pero no mandan.
- **Sale:** una **propuesta** de M videos. Cada video: título, la idea que cierra y sus **tramos** en orden (archivo, desde, hasta).
  Lo que no entra a ningún video va a **sobran**, con su motivo (toma repetida, toma fallada, sin voz).
- **Después de aprobar:** cada video se arma (se cortan y unen sus tramos) y entra al flujo de siempre (guion → estilo → editar →
  exportar) como un proyecto más, uno tras otro.

## Qué no debe pasar nunca
1. **Perder un archivo sin decirlo.** Todo archivo, y toda palabra dicha en él, queda en un video o en «sobran» con motivo. Lo
   garantiza el código (`reparto.revisar`), no el modelo: lo que el agrupador no ubique se manda a «sobran» con aviso a la vista.
2. **Mezclar dos ideas en un video.** Lo decide Opus con las transcripciones y lo confirma la persona: nada se prepara sin su
   aprobación. El código garantiza lo medible: ningún tramo queda en dos videos y un archivo solo se parte en una pausa.
3. Gastar o trabajar pesado sin orden: se transcribe un archivo a la vez y los videos aprobados se preparan uno tras otro.
4. Tocar los archivos originales: los tramos se cortan sobre copias; el original subido queda hasta que su video esté armado.

## Abogado del diablo (cómo se rompe) y la defensa
| Ataque | Defensa |
|---|---|
| La misma idea dicha 3 veces en 3 archivos | Regla «última toma siempre»: queda la última, las otras van a sobran «toma repetida». El código además avisa si dos tramos que quedaron dicen casi lo mismo. |
| Un archivo con dos ideas | El agrupador puede partirlo en dos tramos; el código corre el punto de corte a la pausa entre palabras más cercana (nunca dentro de una palabra). |
| Archivos sin voz o sin pista de sonido | No se mandan al agrupador: van a sobran «sin voz». La persona puede meterlos a un video a mano. |
| El modelo olvida un archivo o parte de él | `revisar` mide palabra por palabra: lo que nadie reclamó va a sobran «sin ubicar» y se avisa arriba de la propuesta. |
| El modelo pone el mismo tramo en dos videos | Gana el primero; al segundo se le recorta lo ya tomado, con aviso. |
| El modelo inventa un archivo o tiempos fuera del archivo | Se descarta o se recorta a la duración real, con aviso. |
| El modelo no responde JSON, o Claude no tiene sesión | Un reintento; si no, reparto por código (cada archivo un video, repetidas fuera) con el aviso de que hay que juntar a mano. Nunca se queda sin propuesta ni pierde lo transcrito. |
| Orden de nombre o fecha engañoso | Es solo una pista en lo que lee el agrupador; el orden final sale del sentido y la persona puede reordenar. |
| 30 archivos largos | Transcripción en serie con avance y «Detener»; lo ya transcrito se guarda por archivo y no se repite. Las transcripciones van al agrupador en un archivo (no en la orden: en Windows la orden tiene tope de largo). |
| La persona mueve cosas y deja un video vacío o un archivo fuera | Lo que manda la pantalla pasa por el mismo `revisar`. |
| Un video falla al prepararse | Se anota en ese video con su frase y se sigue con el siguiente; los demás no se pierden. |
| Se cierra la app a la mitad | La tanda vive en disco (`proyectos/_tandas/<id>/tanda.json`); al volver se retoma donde iba. |

Límite honesto: que dos ideas no se mezclen es un juicio de sentido; el código no lo puede medir. Por eso la propuesta SIEMPRE pasa por
la persona antes de preparar nada.

## Piezas
- `estudio/reparto.py`: la tanda (crear, transcribir en serie, agrupar con Opus o por código, `revisar`, armar cada video).
- `estudio/unir.py`: ahora también une tramos (un pedazo de cada archivo).
- `estudio/servidor.py`: `/api/tanda` (crear), `/api/tanda/<id>` (estado y propuesta), `/api/tanda-propuesta` (lo que movió la
  persona), `/api/tanda-aprobar` (preparar los videos, uno tras otro).
- `app/`: en Material, con varios archivos, «Ver cuántos videos salen» y la pantalla de propuesta (mover, juntar, separar, rescatar).

## Fases y su verificación
1. **Subir el lote.** CUANDO se eligen o sueltan muchos archivos, EL SISTEMA DEBE subirlos todos y crear la tanda con cada uno.
   `uv run pytest tests/test_reparto.py -k tanda_nueva`
2. **Transcribir en serie.** CUANDO la tanda arranca, DEBE transcribir un archivo a la vez, guardar cada transcripción y marcar «sin
   voz» lo que no tiene. `uv run pytest tests/test_reparto.py -k serie`
3. **Agrupar.** CUANDO están las transcripciones, DEBE proponer videos con Opus y pasar la propuesta por `revisar` (nada perdido,
   nada repetido, cortes en pausa); sin IA, reparto por código. `uv run pytest tests/test_reparto.py -k "agrupa or revisar or banco"`
4. **Propuesta en pantalla.** CUANDO la persona mueve, junta o separa, DEBE guardarse solo si pasa `revisar`, y decir qué corrigió.
   `uv run pytest tests/test_reparto.py -k persona`
5. **Preparar.** CUANDO se aprueba, cada video DEBE armarse de sus tramos y quedar como proyecto con su guion, uno tras otro; el que
   falle no tumba a los demás. `uv run pytest tests/test_reparto.py -k "armar or aprobar"`
6. **De punta a punta.** `uv run estudio autoprueba` (lote de archivos → propuesta → mover → aprobar → proyecto exportado) sale 0.

## Banco de pruebas
`tests/test_reparto.py` arma lotes sintéticos (video de prueba + palabras escritas, sin Whisper) de 6 a 8 archivos que dan 2 o 3
videos: con una idea repetida tres veces, un archivo con dos ideas, uno sin voz y nombres en desorden. El agrupador de las pruebas es
un `claude` falso (`ESTUDIO_CLAUDE_BIN`) que responde bien, mal (olvida, repite, inventa) o no responde.
