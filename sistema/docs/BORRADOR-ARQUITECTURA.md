# The Product Studio 2: borrador de arquitectura

> Fase ARCHITECTURE del método `the-architect` (Enrique Rocha). **No se escribe código hasta el «sí» de Pablo.**
> Después de ese sí se genera el blueprint completo, con pasos EARS, verificación y tags de git.
> Fecha: 2026-11-03. Base: la edición a mano de IMG_0653 y cuatro investigaciones de la app actual.

---

## 1. Visión

Un editor de reels que **diseña cada video a medida**, como la edición a mano de IMG_0653, y que deja **ver en vivo**
cualquier opción: estilo, colores, tipografía, subtítulos, cámara, transiciones, música y SFX.
Corre en **cualquier PC (Mac o Windows) con un solo instalador** y **se mejora y se mantiene solo** sin llenarse
de reglas que se contradicen.

**No-objetivos (v1):** corrección de color, DaVinci, Telegram, publicar en redes, fábrica nocturna.
Esas siguen en sus apps actuales y no se toca nada de ellas.

## 2. Por qué la app actual sale mal (lo que este diseño corrige)

| Causa (verificada en el código) | Cómo lo resuelve el diseño nuevo |
|---|---|
| Elige de un menú cerrado (2–29 plantillas por estilo) | **Gramática de escenas**: el director compone con piezas básicas (persona, imagen, texto, trazo, cámara, transición, sonido). El estilo es gusto y fichas de diseño, no una jaula |
| Prohibido generar arte; recorte de persona apagado | **Arte a medida** por escena (biblioteca propia, b-roll o Higgsfield con tope), recorte de persona siempre disponible |
| El director no ve el video | El director recibe **hoja de contacto + cuadros clave** del video y la referencia, además del transcript |
| Más de 50 compuertas que **borran** | **≤13 reglas duras numeradas, cada una con su test**. Las fallas **vuelven al director con el motivo**; nunca se borra en silencio |
| Nadie juzga la estética | **Ojo de director (Opus)**: mira cuadros del render real con la rúbrica de `motion-architect/review.md` y aprueba o bloquea; máximo 2 vueltas |
| Cámara por temporizador | Cámara **atada a palabras**: punch-ins, reencuadres y cambios de posición de la persona por escena |

## 3. Arquitectura: un motor, dos puertas

```
                 ┌──────────────────────────── MOTOR (paquete único) ────────────────────────────┐
  video crudo →  │ ingesta → transcribir → recortar persona → DIRECTOR (Opus) → storyboard.json  │
                 │      → componer (HTML/GSAP) → VISTA PREVIA EN VIVO ⇄ librerías                │
                 │      → validar (≤13 reglas) → OJO (Opus mira cuadros) → render → sonido → mp4 │
                 └───────────────▲───────────────────────────────────────────▲──────────────────┘
                                 │                                           │
                 APP (ventana: Material → Estilo → Storyboard → Exportar)   CLI + skill de Claude Code
                 (para Pablo y su editor)                                   (`estudio editar video.mov`:
                                                                             lo mismo que hice a mano)
```

- **Una sola fuente de la composición:** el storyboard se convierte en HTML/GSAP. **El mismo HTML** se reproduce en
  vivo en la app (cambiar paleta o tipografía se ve al instante, sin renderizar) y es el que renderiza HyperFrames
  al exportar. Lo que ves es lo que sale.
- **«Una aplicación para usar el mismo motor»:** el motor es un paquete con CLI. Lo usan la app y una skill de Claude
  Code, así cualquier sesión de Claude edita con el mismo motor sin abrir la app.

## 4. El flujo (pantallas de la app)

1. **Material:** subir el video o videos, transcripción automática y corrección de palabras.
2. **Estilo:** galería visual de estilos aplicados **a un cuadro de tu propio video**.
3. **Storyboard (nuevo, el corazón):** tarjetas por escena (cuadro, palabras, qué pasa, arte). Panel lateral de
   **librerías con vista en vivo**: estilo, paleta, tipografía, subtítulo, intensidad, cámara, transición, música
   y SFX. Cada cambio se ve al instante en el reproductor. 👍/👎 y nota por escena (eso alimenta el aprendizaje).
4. **Exportar:** render, sonido y entrega. Un registro de costo y tiempo por video siempre visible.

## 5. Librerías (todas con miniatura y vista en vivo)

| Librería | Origen (lo que ya existe) | v1 |
|---|---|---|
| Estilos | 11 familias / 26 variantes de `estilos-paquete` → convertidas a **fichas de diseño + vocabulario de motion** | Las 11 aprobadas primero, con los favoritos (vox-1, vox-2, maestro-2) arriba |
| Tipografías | Solo **OFL** (~40 familias: motor, brand/estilo, kairos) | Se excluyen DEMO y comerciales sin licencia (Fontspring, Gotham, Proxima, Gilroy) |
| Paletas | `look.py` de cada estilo + marca Prestiggio + kairos + generador por armonía | Sí |
| Subtítulos | 21 módulos + identidades de `embedded-captions` + los de IMG_0653 | Sí |
| SFX | 177 activos (con licencias) + 260 Kenney CC0 | Sí; las reglas de variedad de `video-editor-architect` |
| Música | **Vacía en la Mac**: el banco real está en el PC | Carpeta «Mi música» con su propio índice; se llena desde tu banco |
| Cámara (nueva) | Hoy son parámetros sueltos | Presets con nombre: deriva, punch-in, reencuadre, plano a plano, alejamiento final |
| Transiciones (nueva) | `hyperframes-animation/transitions` (~40) | Las 9 listas del registro, con más a medida que se prueben |

Agregar algo a una librería = soltar archivos en su carpeta; el indexador hace la ficha y la miniatura solo.

## 6-bis. El Agente Editor (lo más importante; pedido de Pablo, 2026-11-03)

El editor tiene **su propio agente** (Claude Code por `claude -p`, Opus) que:

1. **Edita con herramientas deterministas:** cada capacidad del motor es un comando (`estudio transcribir`,
   `cortar`, `recortar`, `componer`, `validar`, `render`, `medir`…). El agente decide; las herramientas hacen, siempre
   igual y con pruebas.
2. **Aprende de cada corrección y puede cambiar el código base.** Ante una corrección, la clasifica:
   - *Solo este video* → arregla el storyboard y vuelve a renderizar.
   - *Gusto o preferencia* → la escribe en el perfil de gusto.
   - *Falla o capacidad que falta en el sistema* → **modifica el código** en una rama aparte.
3. **Prueba que aprendió:** todo cambio de código trae **un caso de regresión nuevo** hecho con la corrección de Pablo,
   y solo entra si pasa **todas** las pruebas viejas, la nueva y el render de oro. Entonces se aplica solo, con commit
   y un **«deshacer»** de un clic. El panel «Qué aprendí» muestra cada corrección → qué cambió → la prueba que la
   protege → antes y después.
4. **Límites que el agente no puede tocar solo:** borrar o debilitar pruebas existentes, permisos, topes de gasto, el
   instalador y su propia constitución (`CLAUDE.md`). Si cree que hace falta, lo propone y espera el OK.

Así una corrección no se pierde: o vive en el perfil, o en el código con su prueba.

## 6. Se mejora y se mantiene solo (método jarvis + aprende-skill)

- **Captura:** solo las reacciones de Pablo (👍/👎 y notas por escena) van a `correcciones.jsonl`.
- **Aprender (Sonnet por `claude -p`):** propone lecciones con su recibo. Pablo las aprueba en el panel «Aprendizajes».
  Cada lección es un commit con botón **deshacer**.
- **Disciplina:**
  - Máximo **40 lecciones activas**.
  - La nueva **reemplaza** a la que contradice; nunca se acumulan las dos.
  - Se retiran las que no se usan en 60 días.
  - Revisión semanal de contradicciones.
- **Reglas duras y código:** el Agente Editor sí cambia código (ver 6-bis), pero siempre con prueba de regresión,
  todas las pruebas en verde, commit y deshacer. Nunca toca permisos, topes ni pruebas viejas sin el OK de Pablo.
- **Perfil de gusto versionado:** perfil > notas del director > borrador.
- **Mantenimiento automático (`estudio doctor`):**
  - Al abrir: revisa dependencias.
  - Cada noche: tests + un render de oro de 5 s comparado con el anterior, y limpieza de caché y proyectos viejos.
  - Si algo se rompe, avisa con el arreglo propuesto.

## 7. Stack y «corre en cualquier PC»

| Pieza | Elección | Por qué |
|---|---|---|
| Orquestación | Python 3.11 (instalado por `uv`, sin tocar el Python del sistema) | Ya probado en esta Mac Intel; ruedas para Mac y Windows |
| Transcripción | faster-whisper large-v3 (pip) | Multiplataforma, sin compilar whisper.cpp |
| Recorte de persona | RobustVideoMatting (onnxruntime, pip) | Probado hoy: limpio, ~5 min para 21 s en CPU |
| ffmpeg | Binario estático con zimg (HDR → SDR del iPhone), descargado por el instalador | Reemplaza el ffmpeg de jellyfin, que es solo de Windows |
| Composición y vista previa | HTML + GSAP | Vista en vivo instantánea en la app |
| Render | HyperFrames (Node + Chrome headless) con versión fija | Ya es el motor de hoy; el instalador trae Node portátil |
| IA | **Solo `claude -p`** (suscripción): Opus dirige y mira, Sonnet ejecuta | Nunca API key, Agent SDK ni Haiku. Topes y `costos.jsonl` por video |
| Imágenes a medida | Higgsfield con **tope por video** y confirmación | Opcional; si está apagado usa la biblioteca y el b-roll |
| App | Servidor local (stdlib o FastAPI) + UI web en ventana propia | El mismo patrón de hoy, pero ordenado por módulos |

**Instalador de un paso:** `instalar.command` (Mac) / `instalar.bat` (Windows) baja uv, Python, Node portátil,
ffmpeg, el modelo whisper y RVM, revisa que `claude` esté logueado y crea el acceso directo. Todo queda dentro de la
carpeta de la app.

## 8. Qué se rescata de la app actual (copiado, no movido: la vieja sigue intacta)

`claude_headless` (el patrón `claude -p` con topes), `lab_cortar` (corte en silencios, la última toma), `camara.py`
(ideas de deriva y planos), `estilo_comun` + `contrato` + `fuentes` + `subtitulos/` (fichas de diseño),
el formato de maqueta + `validar_maqueta`, `calidad.py` + `medir_piezas.cjs` (medir en Chrome), `sonido.py`
(−14 LUFS) + `sfx_reglas`, `sdr.py` (HDR), los 26 looks como fuente de fichas y la subida por partes y
Drive de `tools/simple`.
**No se trae:** fábrica, DaVinci, color, Telegram, vigía, `pesado.sh` (son de Linux/Windows), las copias duplicadas de
looks ni las lecciones viejas (se reescriben como perfil de gusto con Pablo).

## 9. Orden de construcción (resumen; el blueprint lo detalla con EARS + Verify)

1. Esqueleto del repo + instalador + `estudio doctor` (Mac y Windows).
2. Ingesta: HDR → SDR, transcripción y corte en silencios.
3. Recorte de persona (RVM) con caché.
4. Gramática de escenas + compositor HTML/GSAP + **vista previa en vivo**.
5. Librerías: tipografías, paletas y estilos (fichas) con miniaturas.
6. Director (Opus) que ve cuadros y escribe el storyboard.
7. Validador de ≤13 reglas con tests («cumple X de Y»).
8. Ojo de director sobre el render y bucle de máximo 2 vueltas.
9. Render HyperFrames + sonido (SFX con reglas de variedad, música y −14 LUFS).
10. App: Material → Estilo → Storyboard → Exportar.
11. Arte a medida (biblioteca, b-roll y Higgsfield con tope).
12. Aprendizaje (correcciones, lecciones, deshacer) + mantenimiento nocturno.
13. CLI + skill de Claude Code sobre el mismo motor.
14. Prueba de aceptación: IMG_0653 sale **igual o mejor** que la edición a mano, en menos de 15 min.

## 10. Compuerta B: pre-mortem (riesgos)

| Riesgo | Mitigación |
|---|---|
| Render lento en esta Mac Intel o en el PC | Vista previa en vivo sin render; render final en segundo plano; medir en el paso 9 con meta ≤10 min por 30 s |
| `claude` sin login en otro PC | El instalador lo detecta y guía el login una sola vez; sin él la app sigue en modo manual (librerías + storyboard a mano) |
| Gasto de Higgsfield se dispara | Tope por video visible antes de exportar; apagado = $0 |
| El aprendizaje se degrada como las 50 compuertas | Tope de 40, reemplazar en vez de acumular, tests y deshacer por commit |
| Licencias | Solo fuentes OFL; SFX de Epidemic marcados «válido mientras haya suscripción»; Kenney CC0 como base segura |
| Proyecto grande | 14 pasos de una sesión cada uno, con tag de git; la app vieja sigue funcionando mientras tanto |
| Cupo semanal de Opus (hoy 37 %) | Sonnet ejecuta pasos mecánicos; Opus solo para dirigir y mirar |

## 11. Compuerta A: decisiones de Pablo (2026-11-03)

- **Reemplazo directo:** desde que la nueva funcione, la vieja se deja de abrir. No se borra nada; el lanzador
  «The Product Studio.app» pasa a abrir la nueva.
- **Higgsfield encendido con tope** visible por video, que se puede bajar o apagar antes de exportar.
- **Mac y PC de la oficina por igual:** cada paso del blueprint se verifica en los dos (CI local + prueba en Windows).
- **Música:** se trae la carpeta «Musica que si» de Epidemic del PC a «Mi música», indexada por ánimo y ritmo.
  Se hace desde una sesión en el PC (Tailscale está apagado en esta Mac), y el índice viaja por el repo.

Sin dudas abiertas: la compuerta A pasa. Falta el «sí» al borrador para generar el blueprint.
