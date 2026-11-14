# Plano — Estilos Pro en PRO STUDIO (Pablo, 09-nov)

Orden de Pablo (voz, 09-nov 12:58): «poné todos los estilos de Lemo en PRO STUDIO; lo último de Julián (Lemo como motor absoluto + vos
poniendo los textos que faltan) funcionó muy bien: usá esa misma combinación de motor para todos los estilos; la versión completa de
PRO STUDIO con la parte de Lemo, con todos los estilos». Antecedentes: `laboratorio-estilos/PLANO-ANIMACION-LIBRE.md` (decisión 08-nov:
Lemo aparte, sin plantillas, dos editores en cadena) y la prueba que decidió: `laboratorio-estilos/julian-animado/` + C-0013.

## 1. Contrato
**Entra:** un proyecto de PRO STUDIO con el guion ya aprobado (machote con sus cortes) y un estilo de Lemo (`lemo-opuscar/styles/<slug>`,
66 estilos). Cualquier proyecto real: un hablante o varios, 15–120 s, con o sin palabras raras.
**Sale:** `proyectos/<p>/pro-<slug>/final.mp4` 1080×1920: película animada de punta a punta dirigida por Opus con el método de Lemo
sobre la VOZ cortada del reel (la persona no aparece), con los textos del guion que Lemo mismo pone en su película; encima, nuestro
editor de textos (`estudio/texto_pelicula.py`) agrega, chico y discreto, SOLO lo que Lemo no mostró (C-0014). Más `estado.json` (fase, %, línea, error), `costos.jsonl` y las compuertas.
**Nunca:** una palabra dicha sin mostrarse (Lemo + las nuestras = 100 %; la cobertura se mide en código, no por lo que diga Opus); texto fuera de la zona segura; rosa, burbujas, corazones, destellos, cursiva decorativa,
fotos flotantes de mujeres; gasto de API (solo `claude -p` de la suscripción, por `estudio/ia.py`); un render fuera de la cola
(`captions/tools/pesado.sh` en el PC); lanzar sin que la app muestre antes el aviso de tiempo y consumo.

## 2. Arquitectura (Lemo hace la película; nuestro editor completa lo que falte)
**Cambio C-0014 (Pablo, 09-nov):** «No debería poner todas las palabras, porque Lemo va a ser lo mejor que el otro editor; entonces hay
que dejar que Lemo haga y tú encima pones lo que haga falta… si tú haces todo no va a ser igual a Lemo, va a quedar más feo, porque tú
no tienes toda la información de Lemo.» Antes (C-0013) Lemo entregaba `limpio.mp4` SIN palabras y nuestro editor dibujaba TODAS: lo
nuestro competía con el mundo de Lemo sin saber lo que Lemo sabe (qué hay en pantalla, qué material, qué movimiento). Ahora Lemo
manda y lo nuestro es solo el parche que garantiza la regla de siempre (toda palabra dicha se ve).
1. **Voz y palabras del reel cortado** — la pista de voz con los cortes aprobados y `palabras.json` en el tiempo del corte.
2. **Editor 1 · Lemo (Opus, `claude -p`)** — en `proyectos/<p>/pro-<slug>/` con el motor de Lemo: lee `DIRECTOR.md`, `STYLE.md` y `demo/`
   del estilo y escribe la película COMPLETA con sus propios textos del guion, integrados al mundo como el estilo lo pida (sin modo
   limpio). Contrato Lemo: `window.render(t)`, `DUR`, `EV` y `TEXTS` — todo texto en pantalla registrado con su texto real. Entrega
   `pelicula.mp4` (voz + música + foley) + `index.html` + `plano.json`.
3. **Compuertas de la película** — formato, duración = voz, sin negros, `plano.json`, `index.html` con `TEXTS`; un reintento con informe.
4. **Medición de lo que mostró Lemo** — `estudio/textos_lemo.py` (+ `textos_lemo.mjs` sobre `core/render/page.mjs` de Lemo, sin GL) recorre
   la película cada 0,1 s juntando `TEXTS(t)`. Una palabra del guion cuenta como mostrada si su forma normalizada (sin tildes, minúsculas,
   sin signos) está como palabra de un texto en pantalla entre 0,6 s antes y 1,5 s después de cuando se dice. Las palabras vacías
   (de, la, que, y…) cuentan si ellas están en pantalla o si la palabra con contenido más cercana de su misma frase (sin cruzar una
   pausa ≥ 0,35 s ni un punto) está mostrada; una frase solo de vacías no hereda. Salida `textos-lemo.json` (lista y % de cobertura).
   Constantes arriba del módulo.
5. **Mapa de texto** — `estudio/mapa_texto.py` mide sobre `pelicula.mp4` (los textos de Lemo ya son «ocupado») → `mapa-texto.json`.
6. **Editor 2 · solo faltantes** — `texto_pelicula.componer(..., lemo=<índices>)` arma bloques SOLO con las palabras que faltan (mismo orden
   y tiempo), con letra menor (`TAM_MAX_FALTA`/`TAM_MIN_FALTA`) en el hueco libre, o en un pliego si el mundo está lleno →
   `final.mp4`. Compuerta: Lemo + las nuestras = 100 %, zona segura, letra, contraste.
7. **Compuertas finales** — duración = voz, sin negros, −14 LUFS ±1. `estado.linea`: «Lemo puso X de N palabras, agregamos Y».
**Compatibilidad:** un encargo con `limpio.mp4` y sin `pelicula.mp4` sigue como antes (el editor de textos pone todas). Reaprovechar una
película ya hecha sin llamar a Opus: `uv run estudio pro-textos <carpeta-encargo>` (pasos 4–7).

## 3. Interfaces
- `estudio/pro_catalogo.py` · `catalogo() -> list[dict]`: `{slug, nombre (es), familia, temas[], poster, muestra|None, probado: bool}`
  para los 66 estilos (muestras ya hechas en `laboratorio-estilos/muestras-lemo`, `muestras-opus`, `peliculas`, `julian-animado`).
- `estudio/textos_lemo.py` · `medir(carpeta, lemo=None) -> dict` (escribe `textos-lemo.json`) · `mostradas(carpeta) -> set[int]`.
- `estudio/pro.py` · `pro_textos(enc, video=None)` (pasos 4–7 sobre un encargo rendido) · `lanzar(carpeta: Path, slug: str) -> Path` (proceso aparte, devuelve la carpeta del encargo) ·
  `estado(carpeta: Path, slug: str) -> dict` · `correr(carpeta, slug)` (el trabajo entero, para CLI y pruebas).
- Servidor: `GET /api/pro/catalogo` · `POST /api/pro/lanzar {proyecto, estilo}` · `GET /api/pro/estado?proyecto=&estilo=` ·
  `GET /pro-media/<slug>/<poster|muestra>`.
- App: en **Estilo**, un selector «Estilos | Estilos Pro». Pro = cuadrícula de los 66 (póster, muestra al tocar, por familia/tema).
  Al elegir uno → **Exportar** muestra el aviso (tiempo y consumo medidos del último reel Pro) y lanza; progreso con `estado`.
- CLI: `uv run estudio pro <proyecto> <slug>` · `uv run estudio pro-textos <carpeta-encargo> [--video x.mp4]`.

## 4. Abogado del diablo (cómo se rompe)
1. *Opus no termina o deja una película rota.* → `ia.llamar` con tope y timeout; la película pasa las compuertas de Lemo
   (lectura, negros, duración = voz) antes del mapa; si falla, un reintento con el informe; si vuelve a fallar, `estado.error` claro.
2. *El límite de la suscripción a mitad.* → `ia.llamar` ya espera y repite el mismo paso.
3. *Lemo escribe texto que no registra en `TEXTS` (o registra uno distinto del que dibuja).* → la medición solo cree lo registrado: lo no
   registrado cuenta como faltante y se duplica encima (fallo visible, nunca palabras perdidas). El prompt exige `TEXTS` completo y
   que corra `readcheck.mjs`; sin `window.TEXTS` la película no pasa la compuerta.
4. *Dos reels Pro a la vez tumban el PC.* → todo render por `pesado.sh`; uno a la vez.
5. *Estilo que choca con lo prohibido (rosa, destellos, cursiva).* → el prompt lo exige, el catálogo marca los estilos con riesgo
   (p. ej. el titleBar de art-deco trae destello) y la revisión de cuadros de Opus lo busca.
6. *Pablo no sabe cuánto tarda.* → el aviso usa lo medido (`costos.jsonl` del último reel Pro), no estimaciones. Hoy: ~376k tokens y
   ~63 min de producción + ~9 min de render (Julián animado).
7. *La app es carril de la Mac.* → cambio chico y aislado (una sección), avisado en el HANDOFF y en el commit; la Mac lo puede rehacer.

## 5. Fases (cada una con su verificación, sale 0)
- **F1 catálogo** — CUANDO se pide el catálogo EL SISTEMA DEBE devolver 66 estilos con nombre en español y póster existente.
  `uv run pytest -q tests/test_pro_catalogo.py`
- **F2 motor** — CUANDO se lanza un reel Pro con una IA de prueba (película fija) EL SISTEMA DEBE dejar `final.mp4` con 100 % de
  palabras (Lemo + las nuestras, solo las faltantes) y `estado.fase == "listo"`. `uv run pytest -q tests/test_pro.py`
- **F3 servidor + app** — CUANDO la app abre Estilo → Estilos Pro EL SISTEMA DEBE mostrar los 66 y lanzar con aviso.
  `uv run pytest -q tests/test_pro_api.py`
- **F4 prueba real** — un reel real de punta a punta con un estilo nuevo (no imprenta) sobre `c8866m`; Pablo lo ve.
- **Compuerta del repo:** `uv run estudio verificar` verde en cada fase.
