# BLUEPRINT · The Product Studio 2  (v2: corregido tras el validador)

> **⚠ CAMBIO DE PLAN (2026-11-03, decisión de Pablo: «camino rápido, toda la app hoy»).** Lo que se construyó hoy NO sigue
> estos 16 pasos: se generalizó el motor Python/Pillow que ya había editado IMG_0653 (sin HTML, Node ni HyperFrames), con
> director y ojo por `claude -p`, la app en `estudio/servidor.py` + `app/` (puerto 8792) y el Agente Editor en `estudio/agente/`.
> El estado real está en `README.md`. Este blueprint queda como referencia para endurecer (pruebas por paso, Windows, aprendizaje).

> Generado con el método `the-architect` (Enrique Rocha), fase GENERATE, 2026-11-03, tras el «Sí, aprobado» de Pablo.
> **Autocontenido:** un constructor sin contexto debe poder seguirlo. El diseño y sus razones están en `BORRADOR-ARQUITECTURA.md`.
> Desviación anunciada: va en un solo archivo, en español y con EARS en español (CUANDO… EL SISTEMA DEBE…), para que Pablo lo lea entero.
> v2 corrige los 8 BLOCKER, 9 MAJOR y 3 MINOR de la primera validación.

---

## §1 Visión y No-Objetivos

**Visión:** un editor de reels verticales que diseña cada video a medida: escenas, arte, cámara y sonido amarrados a las palabras.
Tiene vista previa en vivo de todas las opciones y un **Agente Editor propio**. Ese agente edita con herramientas deterministas y
**aprende de cada corrección de Pablo, incluso cambiando el código base**. Cada aprendizaje queda protegido por una prueba de
regresión que lo demuestra. Corre en macOS (Intel y Apple Silicon) y en Windows 10/11 x64 con un solo instalador.

**No-Objetivos v1:** corrección de color, DaVinci, Telegram, publicar en redes, fábrica nocturna, multiusuario y nube.
Linux de escritorio funciona, pero no se prueba.

## §2 Stack

| Capa | Elección |
|---|---|
| Motor y herramientas | Python 3.11, paquete `estudio`, entorno `uv` dentro de la carpeta |
| Transcripción | faster-whisper `large-v3` en CPU, int8 |
| Recorte de persona | RobustVideoMatting `rvm_mobilenetv3_fp32.onnx` + onnxruntime |
| Video y audio | ffmpeg y ffprobe de `static-ffmpeg`. HDR→SDR con `tonemap_lut` (filtros `lutrgb`, **sin zscale**: vale con cualquier ffmpeg) |
| Composición y vista previa | HTML + GSAP: un `index.html` por proyecto, el mismo para la vista en vivo y el render |
| Render | HyperFrames CLI corrido con el **Node portátil** de `.tps/node` (nunca con el `npx` del sistema) y su Chrome fijado (`hyperframes browser ensure`) |
| App | Servidor local `http.server` (stdlib) + UI web modular sin framework, abierta en ventana propia de Chrome o Edge |
| IA | **Solo el binario oficial `claude -p`** con la suscripción. Opus dirige, mira y corrige código; Sonnet hace lo mecánico. Prohibidos la API key, el Agent SDK y Haiku |
| Imágenes a medida | Higgsfield por `claude -p` con el conector de la cuenta, con tope por video |
| Pruebas | pytest. Lo pesado (whisper, RVM, Claude real, render completo) se marca `@pytest.mark.pesado` y queda **fuera por defecto** |

## §3 Directorios

```
the-product-studio-2/
  BLUEPRINT.md  BORRADOR-ARQUITECTURA.md  README.md  CLAUDE.md (instrucciones del CONSTRUCTOR)
  instalar.command  instalar.bat  abrir.command  abrir.bat
  pyproject.toml  uv.lock  uv.toml  package.json  package-lock.json  .gitignore
  .claude/settings.json                     # permisos del constructor + hook de rutas protegidas (activo solo si ESTUDIO_AGENTE=1)
  estudio/                                  # EL MOTOR
    __init__.py  cli.py  config.py  doctor.py  recursos.py  ia.py  imagenes.py
    ingesta/      hdr.py  transcribir.py  cortar.py
    persona/      matte.py
    escena/       gramatica.py  componer.py  runtime/estudio.js  runtime/base.css
    librerias/    indexar.py  miniaturas.py  licencias.py
    validar/      reglas.py
    director/     hoja_contacto.py  dirigir.py  prompts/{director.md, rubrica-motion.md, arte-11-bloques.md}
    ojo/          revisar.py
    render/       render.py  sonido.py
    agente/       CONSTITUCION.md  herramientas.md  editar.py  corregir.py  aprendizajes.py  proteger.py
    servidor/     server.py  api.py
  app/            index.html  app.js  estilos.css  vistas/{material,estilo,storyboard,exportar,aprendi}.js
  semillas/       (comiteado) fuentes-ofl/  paletas.json  estilos/  sfx-cc0/  camara.json  transiciones.json
  librerias/      (generado por `estudio librerias indexar` desde semillas/ + privadas/) <lib>/indice.json
  privadas/       (gitignored) sfx-epidemic/  musica/   ← material con licencia de suscripción; se copia a mano o desde el PC
  perfil/         gusto.json  correcciones.jsonl
  tests/          conftest.py  fakes/{claude.py, transcribir.py, matte.py}  fixtures/generar.py  oro/<plataforma>.json
                  regresion/<C-NNNN>/  test_NN_*.py
  .tps/           (gitignored) node/  modelos/  chrome/  cache/
  proyectos/      (gitignored)
```

## §4 Datos (archivos, sin base de datos)

- `proyectos/<id>/proyecto.json`: fuente, ajustes, estado (`nuevo|dirigiendo|listo|exportando|interrumpido|exportado`), `veredicto_ojo` y costos.
- `transcript.json`: `[{"w":str,"s":float,"e":float,"p":float}]`.
- `storyboard.vN.json`: la gramática de §6.1. Cada versión es inmutable; `storyboard.json` es un puntero `{"actual": N}`.
- `librerias/<lib>/indice.json`: `[{"id","nombre","archivo","licencia","etiquetas":[],"miniatura","estado":"aprobado|en-prueba|retirado"}]`.
- `perfil/gusto.json`: `{"lecciones":[{"id":"L-NNN","texto","fuente":"C-NNNN","fecha","usos":int,"estado":"activa|retirada|reemplazada-por-L-NNN"}]}`, con un máximo de 40 activas.
- `perfil/correcciones.jsonl`: `{"id":"C-NNNN","fecha","proyecto","escena","texto","clase":"video|gusto|sistema","resultado","commit"}`.
- `proyectos/<id>/costos.jsonl`: `{"paso","modelo","usd_equivalente","segundos","ok"}`.

## §5 API local (`127.0.0.1:8790`)

| Método | Ruta |
|---|---|
| GET | `/api/librerias/<lib>` |
| POST | `/api/proyectos` (subida por partes) |
| GET | `/api/proyectos/<id>` |
| POST | `/api/proyectos/<id>/dirigir` |
| PATCH | `/api/proyectos/<id>/storyboard` |
| GET | `/p/<id>/index.html` |
| POST | `/api/proyectos/<id>/exportar` |
| POST | `/api/correcciones` |
| GET | `/api/aprendizajes` |
| POST | `/api/aprendizajes/<C>/deshacer` |
| GET | `/api/doctor` |

Las respuestas son `{"ok":true,...}` o `{"ok":false,"error":str,"arreglo":str}`.

## §6 Frontend

Cuatro vistas: **Material → Estilo → Storyboard → Exportar**, más el panel **Qué aprendí**.
- **Storyboard:** a la izquierda, tarjetas de escena (cuadro, palabras, intención, arte, 👍/👎 y nota). Al centro, el reproductor:
  un iframe con `/p/<id>/index.html` que recibe los ajustes por `postMessage`, sin recargar. A la derecha, las librerías con miniaturas.
  Pasar el cursor por una opción la previsualiza; el clic la aplica.
- Estética sobria tipo Apple: secciones claras, solo elementos útiles, modo claro y oscuro, movimiento de UI menor de 300 ms.

### §6.1 Gramática de escenas (`storyboard.vN.json`)

```json
{"version":1,"estilo":"vox-2","fichas":{"paleta":"tinta-ocre","titulo":"Anton","texto":"Inter","subtitulo":"tira-papel"},
 "escenas":[{"id":"s1","t0":0.0,"t1":2.54,"intencion":"gancho: la feria más grande",
   "persona":{"modo":"recorte","x":0,"escala":0.74},
   "capas":[{"tipo":"imagen","src":"arte/feria.png","marco":"foto","x":540,"y":470,"w":900,"rot":-3,"entra":"cae","z":"atras","palabra":5},
            {"tipo":"trazo","forma":"rect","sobre":0,"t":1.94,"dur":0.5,"color":"acento"}],
   "camara":[{"tipo":"empuje","de":1.0,"a":1.045},{"tipo":"punch","t":2.54,"cuanto":0.07}],
   "subtitulos":{"ocultar":false},"sonido":[{"tipo":"whoosh","t":2.42}]}]}
```

| Elemento | Valores en v1 |
|---|---|
| Tipos de capa | `imagen`, `video`, `texto`, `etiqueta`, `trazo` (forma: `linea`, `rect`, `elipse`, `flecha`, `ruta`), `forma`, `contador`, `pieza` |
| Entradas | `cae`, `izq`, `der`, `sube`, `pop`, `barrido`, `fundido` |
| Cámara | `empuje`, `punch`, `reencuadre`, `deriva`, `aleja` |
| `persona.modo` | `recorte`, `cuadro`, `completa`, `oculta` |

`palabra` es el índice en `transcript.json` al que se amarra la capa.

## §7 Sistema de diseño

- Cada estilo tiene sus fichas: paleta, familias, grano, textura y curvas. La curva por defecto es `cubic-bezier(0.23,1,0.32,1)`.
- Zona segura para texto 9:16: `y` entre 230 y 1500, `x` entre 135 y 945 (sobre 1080×1920).
- La rúbrica de motion se copia al repo en el Paso 10, en `estudio/director/prompts/rubrica-motion.md`. Fuente: `tododeia-arquitectos/motion-architect/skills/motion-architect/references/craft/review.md`.

## §8 Auth

La app es local y no tiene auth. La IA usa el login de `claude` del usuario.

## §9 BUILD ORDER

**Reglas comunes a todos los pasos:**
- Cada paso entra en una sesión, tiene de 2 a 6 criterios EARS y al menos uno es de falla.
- `Verify` lista comandos separados por «·». Cada uno se corre por separado y funciona igual en bash y en PowerShell 5: **nunca `&&`**, siempre `uv run …`.
- `Checkpoint` es `git add -A` + `git commit -m "step NN: …"` + `git tag step-NN-slug`.
- Si un paso se rompe, se vuelve al tag anterior (`git reset --hard <tag>`). Ningún paso puede romper un Verify anterior: al final de cada paso corre también `uv run pytest -q`, que es la suite rápida, sin pesados.
- Requisito previo de la máquina: `uv` en el PATH (el instalador lo instala con el instalador oficial si falta) y `git`.

### Paso 01 · esqueleto, doctor y repositorio
- **Do:** `git init -b main`; escribir `.gitignore`, `uv.toml` (`cache-dir = ".tps/cache/uv"`), `pyproject.toml` (deps de §11, script `estudio = "estudio.cli:main"`, pytest con `addopts = "-m 'not pesado'"` y marca `pesado` registrada), `package.json` (§11) y `estudio/{__init__,config,doctor,cli}.py`.
- **`doctor`:**
  - `doctor --offline` revisa python, node, hyperframes, gsap, chrome, ffmpeg, ffprobe y modelos **sin** llamar a Claude.
  - `doctor` (completo) además corre `claude -p` y guarda la respuesta en caché por 24 h.
  - `ESTUDIO_CLAUDE_BIN` reemplaza al binario (si termina en `.py`, se corre con el Python actual).
- Escribir `tests/fakes/claude.py` (imprime `{"is_error":false,"result":"ok"}` y `--version` → `2.1.0 (fake)`), `tests/conftest.py` y `tests/test_01_doctor.py`.
- Correr `uv lock` y comitear `uv.lock`.
- **Done when:**
  - CUANDO se corre `uv run estudio doctor --offline --json` en un repo sin instalar EL SISTEMA DEBE devolver JSON con 8 items, cada uno `{nombre, ok, version, arreglo}`, y código 1.
  - CUANDO `ESTUDIO_CLAUDE_BIN` apunta a un archivo inexistente EL SISTEMA DEBE marcar `claude` con `ok:false` y un `arreglo` no vacío.
  - CUANDO `ESTUDIO_CLAUDE_BIN=tests/fakes/claude.py` EL SISTEMA DEBE marcar `claude` con `ok:true`.
- **Verify:** `uv run pytest -q tests/test_01_doctor.py`
- **Checkpoint:** `step-01-esqueleto`

### Paso 02 · instalador de un paso
- **Do:**
  - `estudio/recursos.py`: `instalar-recursos`, idempotente. Baja **Node 26.13.0** portátil a `.tps/node` desde nodejs.org (darwin-x64, darwin-arm64 o win-x64), corre `npm install` con ese Node, corre `hyperframes browser ensure` con `PUPPETEER_CACHE_DIR=.tps/chrome`, ffmpeg con static-ffmpeg, RVM y whisper a `.tps/modelos`.
  - `instalar.command` (bash) e `instalar.bat` (cmd + PowerShell): si falta `uv`, lo instalan con el instalador oficial de astral.sh; luego `UV_PYTHON_INSTALL_DIR=.tps/python uv sync`, después `uv run estudio instalar-recursos` y al final `uv run estudio doctor`.
  - `abrir.command` y `abrir.bat` quedan como esqueleto: llaman `uv run estudio servir`, que en el Paso 13 abre la app.
  - Comitear `package-lock.json`.
- **Done when:**
  - CUANDO se corre `uv run estudio instalar-recursos` dos veces seguidas EL SISTEMA DEBE terminar con código 0 y, la segunda vez, no descargar nada (en menos de 10 s).
  - CUANDO termina la instalación EL SISTEMA DEBE pasar `uv run estudio doctor --offline --json` con `ok:true`.
  - CUANDO no hay red y faltan recursos EL SISTEMA DEBE salir con código 1, nombrando qué falta, sin dejar archivos `.part`.
- **Verify:** `uv run estudio instalar-recursos` · `uv run estudio doctor --offline --json` · `uv run pytest -q`
- **Checkpoint:** `step-02-instalador`

### Paso 03 · puerta de IA e imágenes
- **Do:**
  - `estudio/ia.py`: `llamar(prompt, modelo, herramientas, tope_usd, cwd, proyecto)`. Envuelve `claude -p --model <m> --output-format json --allowedTools <h> --permission-mode acceptEdits --max-budget-usd <t> --no-session-persistence --strict-mcp-config --mcp-config {"mcpServers":{}}`. Rechaza `haiku` y registra en `costos.jsonl`.
  - `estudio/imagenes.py`: primero la caché por hash de prompt y tamaño; si no está, Higgsfield vía `ia.llamar` **sin** `--strict-mcp-config`, con `--allowedTools mcp__claude_ai_higgsfield__generate_image,mcp__claude_ai_higgsfield__jobs_wait`. Tope por proyecto en `proyecto.json` (por defecto 8).
  - `tests/test_03_ia.py` con `tests/fakes/claude.py`.
- **Done when:**
  - CUANDO se pide `modelo="haiku"` EL SISTEMA DEBE lanzar `ValueError`.
  - CUANDO termina una llamada EL SISTEMA DEBE escribir una línea en `costos.jsonl` con `usd_equivalente` y `segundos`.
  - CUANDO el proyecto ya usó su tope de imágenes EL SISTEMA DEBE devolver `None` y anotar `{"tope":true}` en `costos.jsonl`, sin llamar a Claude.
- **Verify:** `uv run pytest -q tests/test_03_ia.py`
- **Checkpoint:** `step-03-ia`

### Paso 04 · ingesta: HDR, transcripción y corte
- **Do:**
  - `tests/fixtures/generar.py`: con ffmpeg `lavfi` crea `hlg_6s.mov` (`testsrc2` + un tono de 440 Hz, metadatos `-color_trc arib-std-b67 -color_primaries bt2020 -colorspace bt2020nc`), `sdr_6s.mp4` y `mudo_6s.mp4` (sin pista de audio). Se corre desde `conftest.py` si los archivos no existen.
  - `ingesta/hdr.py`: portar `es_hdr` y `tonemap_lut` (la cadena de `lutrgb` HLG/PQ→Rec.709 está en `BORRADOR-ARQUITECTURA.md` §7; usar la fórmula ARIB STD-B67 inversa más la OETF Rec.709).
  - `ingesta/transcribir.py`: faster-whisper con palabras; la interfaz `transcribir(ruta) -> list`, inyectable.
  - `ingesta/cortar.py`: corta silencios mayores de 0,45 s y aplica la regla de la última toma (frase repetida → queda la última).
  - `tests/fakes/transcribir.py` y `tests/test_04_ingesta.py`.
- **Done when:**
  - CUANDO la fuente es `hlg_6s.mov` EL SISTEMA DEBE producir `corte.mp4` con `color_transfer=bt709` según ffprobe.
  - CUANDO el transcript falso tiene un hueco de 1,0 s entre palabras EL SISTEMA DEBE acortar la duración del corte entre 0,5 y 0,6 s y desplazar los tiempos posteriores.
  - CUANDO la fuente es `mudo_6s.mp4` EL SISTEMA DEBE lanzar `ValueError("el video no tiene audio")` y no crear la carpeta del proyecto.
  - (pesado) CUANDO se transcribe con whisper real un clip con voz EL SISTEMA DEBE devolver palabras con `s < e`.
- **Verify:** `uv run pytest -q tests/test_04_ingesta.py`
- **Checkpoint:** `step-04-ingesta`

### Paso 05 · recorte de persona
- **Do:** `persona/matte.py` (RVM con estado recurrente, `alpha/a_NNNN.png` y caché por hash de la fuente), `tests/fakes/matte.py` y `tests/test_05_matte.py`.
- **Done when:**
  - CUANDO el recorte se repite sobre la misma fuente EL SISTEMA DEBE devolver la caché sin llamar al modelo (prueba con un modelo falso que cuenta las llamadas: 0 la segunda vez).
  - CUANDO falta el modelo onnx EL SISTEMA DEBE lanzar `FileNotFoundError` con el arreglo «corre el instalador».
  - (pesado) CUANDO se recorta `sdr_6s.mp4` con RVM real EL SISTEMA DEBE escribir un alfa por cuadro.
- **Verify:** `uv run pytest -q tests/test_05_matte.py`
- **Checkpoint:** `step-05-persona`

### Paso 06 · gramática de escenas y compositor en vivo
- **Do:**
  - `escena/gramatica.py`: valida §6.1 y devuelve errores con escena y capa.
  - `escena/componer.py`: storyboard → `index.html` con GSAP y `window.__timelines.main` en pausa.
  - `escena/runtime/estudio.js` y `base.css`: aplican las fichas por `postMessage`.
  - `tests/fixtures/storyboard_ejemplo.json` y `tests/test_06_componer.py`.
- **Done when:**
  - CUANDO una capa tiene `tipo:"holograma"` EL SISTEMA DEBE rechazar el storyboard con el mensaje `escena s1, capa 0: tipo desconocido`.
  - CUANDO se compone el ejemplo EL SISTEMA DEBE pasar `uv run estudio hf check <dir>` con código 0.
  - CUANDO el iframe recibe `{"paleta":"grafito-rojo"}` EL SISTEMA DEBE cambiar `--acento` en `:root` sin recargar. Se comprueba con el Chrome de `.tps/chrome` en modo headless leyendo el estilo computado.
- **Verify:** `uv run pytest -q tests/test_06_componer.py`
- **Checkpoint:** `step-06-escena`

### Paso 07 · librerías con miniaturas
- **Do:**
  - Sembrar `semillas/` (se comitea): las fuentes OFL del motor viejo, `paletas.json` con las paletas de los `look.py`, las fichas de los 11 estilos aprobados, los 260 SFX CC0 de Kenney, `camara.json` (los 5 presets de §6.1) y `transiciones.json` (9).
  - `librerias/licencias.py` con la lista literal de fuentes NO permitidas: `Fontspring-DEMO*`, `Gotham*`, `Proxima Nova*`, `Gilroy*`, `FuturaPT*`, `AppleGaramond*`, y cualquier archivo sin `OFL.txt`, `LICENSE` o una entrada en `semillas/fuentes-ofl/LICENCIAS.json`.
  - `librerias/indexar.py` (`semillas/` + `privadas/` → `librerias/`) y `librerias/miniaturas.py`.
  - La prueba usa un mini catálogo en `tests/fixtures/mini-semillas/`. `tests/test_07_librerias.py`.
- **Done when:**
  - CUANDO se indexa una fuente `Fontspring-DEMO-x.otf` EL SISTEMA DEBE excluirla y listarla en `rechazados`.
  - CUANDO aparece un archivo nuevo en `privadas/sfx-epidemic/` EL SISTEMA DEBE indexarlo con `licencia:"epidemic-suscripcion"` y `estado:"en-prueba"`.
  - CUANDO `privadas/musica/` está vacía EL SISTEMA DEBE crear `librerias/musica/indice.json` como `[]`, sin error.
- **Verify:** `uv run estudio librerias indexar` · `uv run pytest -q tests/test_07_librerias.py`
- **Checkpoint:** `step-07-librerias`

### Paso 08 · render y sonido
- **Do:**
  - `render/render.py` corre `hyperframes render` con el Node y el Chrome de `.tps`.
  - `render/sonido.py`: voz con loudnorm a −14 LUFS; SFX del storyboard sin repetir archivo en 5 eventos y con un máximo de 2 seguidos de la misma categoría; música de `librerias/musica` si existe.
  - `tests/oro/`: `uv run estudio oro grabar` guarda la huella de **esta plataforma** en `tests/oro/<sys.platform>-<machine>.json` (promedio de luma de 12 cuadros).
  - `tests/test_08_render.py`.
- **Done when:**
  - CUANDO se renderiza el storyboard de ejemplo con el corte de `sdr_6s.mp4` EL SISTEMA DEBE producir un mp4 de 1080×1920 a 30 fps.
  - CUANDO hay huella de oro para la plataforma EL SISTEMA DEBE coincidir con un error menor de 2 niveles de luma por cuadro; si no hay huella, la prueba se salta y avisa.
  - CUANDO se mide el audio final EL SISTEMA DEBE dar −14 ± 1 LUFS y picos ≤ −1 dBTP.
  - CUANDO el plan de SFX repite el mismo archivo 3 veces seguidas EL SISTEMA DEBE sustituir el 2.º y el 3.º por otros de la misma categoría.
- **Verify:** `uv run pytest -q tests/test_08_render.py`
- **Checkpoint:** `step-08-render`

### Paso 09 · validador (8 reglas, cada una con su test; nunca borra)
- **Do:** `validar/reglas.py`. Usa el alfa de la persona: la **cara** es el 28 % superior del recuadro del alfa en cada cuadro.
  - R1 · ninguna capa tapa la cara más de un 12 %.
  - R2 · la franja de subtítulos está libre.
  - R3 · el texto queda en la zona segura (§7).
  - R4 · el texto se puede leer: ≥ 0,9 s por cada 3 palabras.
  - R5 · ninguna capa sale cortada del cuadro.
  - R6 · los SFX cumplen las reglas de variedad.
  - R7 · cada capa con `palabra` arranca a ±0,25 s de esa palabra.
  - R8 · la duración total es ≤ 110 s.
  - La salida es `{"cumple":X,"de":8,"fallas":[{regla,escena,capa,motivo,arreglo}]}`. `tests/test_09_validar.py`.
- **Done when:**
  - CUANDO una capa tapa el 30 % de la cara EL SISTEMA DEBE reportar R1 con escena, capa y arreglo, y dejar el archivo del storyboard idéntico (mismo hash).
  - CUANDO todo cumple EL SISTEMA DEBE salir con código 0 y `cumple 8 de 8`.
- **Verify:** `uv run pytest -q tests/test_09_validar.py`
- **Checkpoint:** `step-09-validar`

### Paso 10 · director (Opus ve el video)
- **Do:**
  - `director/hoja_contacto.py`: un cuadro por segundo más los cuadros clave, en una imagen.
  - `director/dirigir.py` + `prompts/director.md` (director creativo; estilo como guía, no jaula; gramática §6.1; perfil de gusto) + `prompts/arte-11-bloques.md` (copiado de `tododeia-arquitectos/creative-architect/skills/direccion-de-arte/references/bloques.md`) + `prompts/rubrica-motion.md` (§7).
  - Si `validar` falla, devuelve el reporte al director (máximo 2 vueltas).
  - `tests/test_10_director.py` con `tests/fakes/claude.py` en modo `--escenario director` (escribe un storyboard válido).
- **Done when:**
  - CUANDO se dirige EL SISTEMA DEBE pasarle a `claude` la ruta de la hoja de contacto (visible en los argumentos que registra el falso) y dejar `storyboard.v1.json` válido según `gramatica`.
  - CUANDO el falso escribe dos veces un storyboard que falla R1 EL SISTEMA DEBE quedarse con la última versión y guardar en `proyecto.json` `avisos` con la falla, sin borrar escenas.
- **Verify:** `uv run pytest -q tests/test_10_director.py`
- **Checkpoint:** `step-10-director`

### Paso 11 · ojo de director
- **Do:** `ojo/revisar.py`. Renderiza de 8 a 12 cuadros clave a 540×960 (`hyperframes snapshot`). Opus los mira con la rúbrica y devuelve `{"veredicto":"aprobar|bloquear","cambios":[...]}`. Si bloquea, va al director (máximo 2 vueltas). `tests/test_11_ojo.py` con el falso en modo `--escenario ojo-bloquea`.
- **Done when:**
  - CUANDO el ojo bloquea EL SISTEMA DEBE crear `storyboard.vN+1.json` con los cambios y volver a mirar.
  - CUANDO se agotan las 2 vueltas EL SISTEMA DEBE escribir `veredicto_ojo:"bloquear"` y los cambios pendientes en `proyecto.json`.
- **Verify:** `uv run pytest -q tests/test_11_ojo.py`
- **Checkpoint:** `step-11-ojo`

### Paso 12 · servidor y API
- **Do:** `servidor/{server,api}.py` (§5, solo en 127.0.0.1:8790; los trabajos persisten en `proyecto.json` y se reanudan) y `tests/test_12_api.py`.
- **Done when:**
  - CUANDO se hace `PATCH` al storyboard EL SISTEMA DEBE escribir `storyboard.vN+1.json` y conservar `storyboard.vN.json` intacto.
  - CUANDO el servidor arranca con un proyecto en `exportando` EL SISTEMA DEBE marcarlo `interrumpido`.
  - CUANDO llega un `PATCH` con gramática inválida EL SISTEMA DEBE responder 400 `{"ok":false,"error","arreglo"}` sin escribir nada.
- **Verify:** `uv run pytest -q tests/test_12_api.py`
- **Checkpoint:** `step-12-api`

### Paso 13 · la app (UI con vista en vivo)
- **Do:** `app/index.html`, `app/app.js`, `app/estilos.css`, `app/vistas/*.js` (5 vistas). `estudio servir` abre Chrome o Edge en modo `--app`. `tests/test_13_ui.py` usa el Chrome headless de `.tps`.
- **Done when:**
  - CUANDO se pasa el cursor por una paleta EL SISTEMA DEBE previsualizarla en el reproductor en menos de 150 ms, sin navegar ni recargar el iframe (misma instancia de `window`).
  - CUANDO se abre la vista Storyboard de un proyecto con 8 escenas EL SISTEMA DEBE mostrar 8 tarjetas con su cuadro.
- **Verify:** `uv run pytest -q tests/test_13_ui.py`
- **Checkpoint:** `step-13-app`

### Paso 14 · Agente Editor: edita con herramientas deterministas
- **Do:**
  - `cli.py` expone cada herramienta: `transcribir`, `cortar`, `recortar`, `dirigir`, `componer`, `validar`, `mirar`, `render`, `medir`.
  - `agente/herramientas.md` es el manual de uso; `agente/CONSTITUCION.md` dice qué puede y qué no.
  - `agente/editar.py` lanza `claude -p` (Opus) con `ESTUDIO_AGENTE=1`, `--append-system-prompt` = la constitución y `--allowedTools "Bash(uv run estudio:*),Read,Write,Edit,Glob,Grep"`.
  - `tests/test_14_agente.py` con el falso en modo `--escenario agente` (registra los comandos pedidos).
- **Done when:**
  - CUANDO se corre `uv run estudio agente editar <video>` EL SISTEMA DEBE invocar `claude` con exactamente esa lista de herramientas y `ESTUDIO_AGENTE=1` en el entorno.
  - CUANDO la lista de herramientas incluye cualquier cosa fuera de la permitida EL SISTEMA DEBE negarse a lanzar el agente.
- **Verify:** `uv run pytest -q tests/test_14_agente.py`
- **Checkpoint:** `step-14-agente`

### Paso 15 · Agente Editor: aprende de correcciones y cambia el código base
- **Do:**
  - `agente/corregir.py`: la corrección `C-NNNN` se clasifica con Sonnet y se resuelve según su clase.
    - `video`: storyboard nuevo y render.
    - `gusto`: lección en `perfil/gusto.json` (tope de 40; la nueva reemplaza a la que contradice).
    - `sistema`: Opus trabaja en un **git worktree** `aprende/C-NNNN`, cambia el código y **escribe `tests/regresion/C-NNNN/`**. Luego corre `uv run pytest -q` + el oro de la plataforma. Si todo pasa: merge, commit `aprende(C-NNNN): …` y tag `aprende-C-NNNN`. Si no: borra el worktree y anota el motivo.
  - `agente/proteger.py` es el hook PreToolUse de `.claude/settings.json`. **Solo actúa si `ESTUDIO_AGENTE=1`** (así el constructor humano no queda bloqueado) y bloquea: modificar o borrar archivos de `tests/` que ya existían (solo se pueden agregar), `agente/CONSTITUCION.md`, `instalar.*`, `.claude/` y los topes de `config.py`.
  - `agente/aprendizajes.py`: el panel «Qué aprendí» y el «deshacer» (`git revert`).
  - `tests/test_15_aprende.py` **trabaja en un repo temporal (`tmp_path`)** que clona el repo y nunca toca el repo real.
- **Done when:**
  - CUANDO una corrección `sistema` se aplica en el repo temporal EL SISTEMA DEBE dejar `tests/regresion/C-0001/`, que falla en el commit anterior y pasa en el nuevo.
  - CUANDO el cambio del falso rompe una prueba existente EL SISTEMA DEBE dejar `main` sin cambios (mismo hash) y el motivo en `correcciones.jsonl`.
  - CUANDO, con `ESTUDIO_AGENTE=1`, se intenta editar un archivo de prueba existente EL SISTEMA DEBE bloquearlo (el hook sale con código 2 y un mensaje).
  - CUANDO se pide deshacer `C-0001` EL SISTEMA DEBE revertir ese commit y dejar la suite en verde.
- **Verify:** `uv run pytest -q tests/test_15_aprende.py`
- **Checkpoint:** `step-15-aprende`

### Paso 16 · mantenimiento y reemplazo de la app vieja
- **Do:**
  - `estudio doctor --noche`: corre la suite rápida + el oro, limpia proyectos de más de 30 días cuando `proyectos/` pasa de 20 GB, y revisa las contradicciones del perfil con Sonnet.
  - Tarea programada: launchd en Mac (`~/Library/LaunchAgents/com.tpl.estudio.plist`, se crea **solo con confirmación del usuario** en el instalador) y el Programador de tareas en Windows.
  - Script `reemplazar-lanzador` que apunta «The Product Studio.app» a `abrir.command`, dejando la app vieja intacta en disco.
  - `tests/test_16_mantenimiento.py`.
- **Done when:**
  - CUANDO falla una prueba en `doctor --noche` EL SISTEMA DEBE escribir `.tps/aviso.json` con la prueba y el arreglo propuesto, y la API `/api/doctor` debe devolverlo.
  - CUANDO `proyectos/` tiene menos de 20 GB EL SISTEMA DEBE dejar todos los proyectos intactos.
- **Verify:** `uv run pytest -q tests/test_16_mantenimiento.py` · `uv run pytest -q`
- **Checkpoint:** `step-16-mantenimiento`

## §10 Bootstrap

- Mac: `./instalar.command`
- Windows: `instalar.bat`

Los dos hacen lo mismo, un comando por línea:
1. `uv` (si falta, lo instala el instalador oficial)
2. `uv sync` (con `UV_PYTHON_INSTALL_DIR=.tps/python`)
3. `uv run estudio instalar-recursos`
4. `uv run estudio doctor`

No hay variables obligatorias. Opcional: `ESTUDIO_CLAUDE_BIN`.

## §11 Dependencias (el único lugar con versiones; verificadas en los registros el 2026-11-03)

| Paquete | Versión | Fuente de la verificación |
|---|---|---|
| uv | 0.13.7 (vale ≥0.12) | api.github.com astral-sh/uv |
| Python | 3.11 | instalado por uv |
| faster-whisper | 1.2.1 | PyPI |
| onnxruntime | 1.31.1; **1.23.2 en macOS x86_64** (1.31 ya no publica ruedas para Mac Intel) | PyPI (archivos por versión) |
| static-ffmpeg | 3.0 | PyPI |
| pillow | 12.3.0 | PyPI (13.0.0 existe, sin probar en Mac Intel) |
| numpy | >=2,<3 | PyPI 2.5.4 |
| pytest | 9.2.0 | PyPI |
| Node | 26.13.0 (primera LTS en nodejs.org/dist/index.json ese día) | nodejs.org |
| hyperframes | 0.9.9 (engines node ≥22) | npm |
| gsap | 3.15.1 | npm |
| claude | ≥ 2.1 (el del usuario; en esta Mac 2.1.318) | `claude --version` |

## §12 Deploy

No hay servidor. Se clona o copia la carpeta y se corre el instalador. Para actualizar: `git pull` y luego el instalador.

## §13 Testing

- Suite rápida: `uv run pytest -q`, sin red, sin Claude real y sin modelos pesados.
- Suite completa: `uv run pytest -q -m pesado`.
- Oro por plataforma y regresiones por cada corrección.

## §14 Seguridad

- El servidor escucha solo en 127.0.0.1.
- El agente corre con una lista cerrada de herramientas, el hook de rutas protegidas y nunca con `bypassPermissions`.
- No hay secretos en el repo.

## §15 Accesibilidad

Contraste AA, teclado en el storyboard y subtítulos legibles (R4).

## §16 Observabilidad y costo

- `costos.jsonl` por proyecto y un resumen en Exportar.
- Topes por llamada en USD equivalentes: director 3, ojo 1,5, corregir 4, aprender 0,5, clasificar 0,2.
- Imágenes: 8 por video por defecto.

## §17 Model routing

| Tarea | Modelo |
|---|---|
| Dirigir, ojo, corregir código, editar como agente | Opus |
| Clasificar correcciones, revisar el perfil | Sonnet |

- Haiku está prohibido (`ia.py` lo rechaza).
- Todo pasa por `claude -p`.

## §18 Skills para la construcción

- **Skills de HyperFrames:** `hyperframes`, `hyperframes-core`, `hyperframes-animation`, `hyperframes-cli`.
- **Diseño:** `design-motion-principles`, `minimalist-ui`.
- **Referencias de Enrique** (se copian al repo en el paso que las usa): `motion-architect/references/craft/*`, `creative-architect/skills/direccion-de-arte/references/*`, `video-editor-architect/.claude/skills/sfx`.

## §19 Agent Workspace

**`CLAUDE.md`** es para el **constructor**: cómo seguir este blueprint, correr Verify y no saltarse pasos. La constitución del agente es otro archivo: `estudio/agente/CONSTITUCION.md`.

**`.claude/settings.json`** (se crea en el Paso 01 y se completa en el 15):
```json
{"permissions":{"allow":["Bash(uv run:*)","Bash(uv sync:*)","Bash(uv lock:*)","Bash(git:*)","Read","Write","Edit","Glob","Grep"]},
 "hooks":{"PreToolUse":[{"matcher":"Write|Edit|Bash","hooks":[{"type":"command","command":"uv run python -m estudio.agente.proteger"}]}]}}
```
(El hook se agrega en el Paso 15; antes no existe.)

## §20 Compuerta global, riesgos y decisiones

**Compuertas, por máquina:**
- **Mac:** `uv run pytest -q` y `uv run pytest -q -m pesado`.
- **Windows:** lo mismo, en el PC de la oficina.
- **Aceptación manual (Pablo):** IMG_0653 editado de punta a punta en ≤ 15 min, «cumple 8 de 8», ojo en `aprobar`, y Pablo lo juzga igual o mejor que la edición a mano del 2026-11-03.

**Riesgos:** ver `BORRADOR-ARQUITECTURA.md` §10. Además:
- La huella de oro es distinta en cada plataforma: por eso se graba una por máquina.
- La caché del Chrome de HyperFrames tiene que caer en `.tps/chrome` (`PUPPETEER_CACHE_DIR`). Se verifica en el Paso 02; si HyperFrames ignora la variable, se documenta la ruta real.

**Decisiones de 2026-11-03:**
- Reemplazo directo de la app vieja.
- Higgsfield encendido, con tope.
- Mac y PC por igual.
- La música Epidemic va a `privadas/musica` (no se sube a git, por licencia).
- El Agente Editor cambia código, siempre con regresión, worktree y deshacer.
