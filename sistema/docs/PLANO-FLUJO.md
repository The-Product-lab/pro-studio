# Plano: flujo ordenado de The Product Studio 2 (Pablo, 07-nov, voz de 3 min)

Estado: BORRADOR para aprobar con Pablo. No se construye nada hasta su OK.

> **Orden de Pablo (10-nov): sin perfiles LOG.** El video se usa tal cual viene; el único color es ninguno o UN LUT sencillo (`color.cubo` + `color.filtro`). Lo que abajo habla de detectar LOG queda anulado.

## Lo que pidió (literal, resumido)
1. Elegido un estilo (ej. Box), se hace DIRECTO ese; nada de pasar antes por «solo subtítulos básicos».
2. Orden fijo, sin pasos repetidos: crudo → detectar formato (S-Log/logarítmico, iPhone, DJI, cámara) y normalizar (HDR→Rec.709)
   → transcribir y generar los datos de cortes → mostrar el guion que quedó → Pablo aprueba o corrige (palabra que no va, falta un
   pedazo) → NO se renderiza sin esa aprobación → cortes perfectos con el guion aprobado → recién ahí el estilo.
3. Ningún silencio de más de 0,2–0,3 s.

## Qué existe hoy (revisado en el código, 07-nov)
| Paso | Hoy | Falta |
|---|---|---|
| Formato | `ingesta.sondear/normalizar`: vertical 1080×1920 30 fps. HDR: solo cambia la matriz bt2020→bt709, SIN curva ni mapeo de tonos (sale lavado), y un iPhone HDR ya vertical a 30 fps no se normaliza nunca. S-Log3 solo si hay XML al lado, y la app sube solo el video: en la app no se detecta nunca | Conversión HDR real (`zscale` + `tonemap`, siempre que sea HDR); DJI D-Log M, Apple Log, S-Log sin XML |
| Transcribir + cortes | `ingesta.preparar` transcribe; los CORTES los decide el director (Opus) en el mismo paso que el diseño; `montaje.reparar` los pule en código | Separar: cortes primero (código + Opus solo para elegir tomas), diseño después |
| Aprobar guion | No existe: del director va directo a «listo para personalizar» | Pantalla de guion + compuerta de render |
| Estilo directo | `/api/preparar` corre el director (Opus, con costo) antes de cualquier aprobación. El «básico» que ve Pablo es muy probablemente `/api/previa-rapida` (`rapida.py`: 2 s del crudo con el estilo dibujado) | Confirmar con Pablo y quitarlo o dejarlo solo como foto |
| Silencios | Tope 0,2 s en main (Mac, b51910c) | Mezclar `pc/silencio-audible` (medir contra el nivel del talento; sin eso el Cine aún tenía 0,38–0,50 s) |

## Contrato
**Entra:** cualquier crudo que una persona no técnica suba: iPhone (SDR, HDR/Dolby Vision, Apple Log), DJI (normal, D-Log M), Sony
(S-Log3 con o sin XML), cámara Rec.709, vertical u horizontal, 24/25/30/60 fps, con o sin claqueta y apuntador, uno o varios en lote.
**Sale:** 1) `fuente.mp4` normalizado (Rec.709, 1080×1920, 30 fps) con su perfil detectado anotado; 2) `guion.json`: las palabras
que quedan, las que se quitan y por qué (repetición, claqueta, voz de fuera, silencio), estado `pendiente | aprobado` y una firma de
los cortes; 3) recién con el guion aprobado: el video en el estilo elegido.
**Nunca:** render sin guion aprobado · el director cambia un corte aprobado · el final dice algo distinto del guion aprobado ·
silencio > 0,2 s · voz de fuera audible · un perfil logarítmico que sale lavado sin aviso · rehacer pasos ya hechos (transcribir,
normalizar, cortar) al cambiar de estilo.

## Correcciones del abogado del diablo (07-nov, ya incorporadas abajo)
1. Los cortes NO son del director: el código los inyecta desde `guion.json` después de cada llamada a la IA (director, ojo,
   agente) y pisa lo que haya. El tope de duración (≤ 1:50) se resuelve en la pantalla del guion, no en el estilo.
2. `reparar` corre UNA vez, antes de mostrar el guion; Pablo aprueba lo que ya salió de ahí; aprobado = congelado (nunca se
   vuelve a reparar). Si una corrección suya obliga a «tragar» o borrar un pedacito, se le muestra antes de aprobar.
3. Un corte sin silencio real (borde «degradado») se muestra en rojo con dos salidas: quitar también la palabra vecina o dejar
   la palabra. Nunca un corte en medio de la voz sin su OK.
4. Lo que Pablo devuelve a mano (aunque sea una toma vieja) queda marcado como intocable: ni la regla de la última toma ni
   `reparar` lo quitan.
5. Firma del guion = cortes en cuadros enteros + hash de `fuente.mp4` + hash de `palabras.json`. Los silencios (F0) van
   PRIMERO, para que un cambio del mapa de voz no invalide guiones ya aprobados.
6. Caché por CONTENIDO del crudo (hash) + versión del perfil de color, no por nombre (dos «IMG_0001.MOV» no se mezclan).
7. Log por histograma: nunca LUT automático. Primero metadatos (exiftool: marca, modelo, DJI, Apple, Dolby Vision); si la
   imagen parece log sin metadatos, aviso + previa A/B en la pantalla del guion; Pablo confirma una vez por cámara y queda
   recordado.
8. Lote en dos tiempos: A) prepara y arma los guiones de todos → UN Telegram con los N guiones; B) solo edita los aprobados;
   los demás quedan «esperando guion» (no «falló»). Un solo normalizador de nombres para la app y el lote.
9. Se aprueba donde vive el proyecto (o por Telegram hacia esa máquina), con escritura atómica y candado por proyecto.
10. La compuerta vive dentro de `motor.Proyecto`/`render`, sin parámetro para saltarla; las previas también la respetan; el
    director no corre (no gasta) hasta que el guion esté aprobado.
11. Pruebas que de verdad prueban: banco de formatos como cuadros PNG + audio corto (no videos, que `verificar` rechaza); una
    prueba que FALLA (no se salta) si falta el banco en la máquina dueña; umbrales en configuración; y una prueba de fin a fin
    que vuelve a transcribir `final.mp4` y lo compara con `guion.json`.

## Fases (cada una: CUANDO… EL SISTEMA DEBE… + comando que sale 0)
**F0 · Silencios primero (falta mezclar).** `pc/silencio-audible` a main con la revisión de la Mac, ANTES de F2–F3. Verifica: `uv run estudio verificar`.

**F1 · Formato (carril PC, `ingesta.py`, `color.py`).** CUANDO entra un crudo DJI D-Log M, Apple Log, S-Log3 sin XML o HDR del
iPhone EL SISTEMA DEBE detectar el perfil (metadatos + medida del histograma: un log tiene negros levantados y poco contraste) y
aplicar su transformación a Rec.709; si no lo reconoce, avisar con el nombre del archivo, nunca seguir lavado.
Banco: un pedazo de 2 s de cada tipo en `tests/banco/formatos/`. Verifica: `uv run pytest tests/test_formatos.py` sale 0.

**F2 · Guion de cortes antes del diseño (carril PC, `montaje.py`, `repeticiones.py`; `director/` compartido).** CUANDO termina la
transcripción EL SISTEMA DEBE armar `guion.json` solo: última toma de cada idea, sin claqueta ni voz de fuera, silencios ≤ 0,2 s
(lo que ya hace `reparar`), y Opus solo para elegir entre tomas cuando el código duda. Sin diseño ni estilo todavía.
Verifica: `uv run pytest tests/test_guion.py` (los 4 casos del banco del 07-nov dan un guion sin repetidas ni claqueta).

**F3 · Aprobación del guion (carril Mac: `app/`, `servidor.py`; compuerta en `motor.py`).** CUANDO el guion está listo EL SISTEMA
DEBE mostrarlo en la app (texto corrido; lo quitado tachado con su motivo) y dejar quitar una palabra o devolver un pedazo; cada
cambio recalcula los cortes en código y se vuelve a mostrar. CUANDO se pide un render sin `guion.json` aprobado, o con cortes que
no coinciden con su firma, EL SISTEMA DEBE negarse con el motivo. Aviso por Telegram: «guion listo para aprobar».
Verifica: `uv run pytest tests/test_aprobacion.py` (render sin aprobación → error; con aprobación → pasa).

**F4 · Estilo directo sobre el guion aprobado (`director/`, `validar.py`).** CUANDO el guion está aprobado EL SISTEMA DEBE pasar
directo al estilo elegido, con los cortes fijos: el director solo diseña; `validar` rechaza un storyboard cuyos cortes difieren de
los aprobados. Cambiar de estilo reusa fuente, guion y cortes (no se transcribe ni se corta de nuevo). Se quita el paso de
subtítulos básicos (cuando Pablo diga dónde lo ve). Verifica: `uv run pytest tests/test_estilo_directo.py`.

**F4b · Texto en pantalla, una vez y en recorrido (Pablo, 07-nov, segundo audio; todos los estilos).** Hoy (medido en los 8
videos del lote del 07-nov): la compuerta de recorrido (`texto_salto_max_px` = 380) solo mira los textos grandes y deja fuera el
subtítulo, que está fijo abajo (y = 1450). Contando el subtítulo, cada video tiene entre 5 y 22 saltos de más de 380 px (Cine 8,
Luminoso 22, Swiss 20, Julian 3D 17), casi todos subtítulo ↔ texto animado en medio de la pantalla. La zona segura solo limita
arriba/abajo (230–1500 px): no hay límite a la derecha (íconos de likes, comentarios, compartir).
- CUANDO un texto (animado, etiqueta o subtítulo) sigue a otro EL SISTEMA DEBE dejar su centro a ≤ `texto_salto_max_px` del
  anterior: el subtítulo deja de estar fijo y sigue el recorrido (el motor lo ubica cerca del último texto, dentro de la zona
  segura); el director recibe el recorrido medido. Verifica: `uv run pytest tests/test_recorrido.py` (los 8 videos del banco
  quedan con 0 saltos tras `acomodar`).
- CUANDO un texto queda a la derecha de `zona_derecha_px` (íconos de Instagram) o abajo de 1500 px EL SISTEMA DEBE correrlo
  adentro (`acomodar`) y la compuerta rechazarlo si no cabe. Verifica: `uv run pytest tests/test_zona_segura.py`.
- CUANDO una imagen, periódico, cartel o infografía ya trae escrita la palabra que se dice (lo sabe por `arte.json`: el texto que
  se le pidió a la imagen) EL SISTEMA DEBE ocultar el subtítulo de esa palabra, como ya hace con los textos animados (C-0007).
  Verifica: `uv run pytest tests/regresion/test_C-0007.py`.

**Compuerta final de cada fase:** `uv run estudio verificar` verde (lo corre el pre-push). Cada fase, su rama y su commit.

## Riesgos y decisiones para Pablo
- La aprobación del guion frena lo automático: el lote nocturno se detendría en cada video hasta que apruebes. Propuesta: el lote
  sigue solo hasta el guion, te avisa por Telegram, y tras tu OK hace todos los estilos de ese video.
- En Prestiggio (el otro editor) la regla es «nunca pedir aprobación a mitad de un video». Esto es SOLO para Studio 2.

## F5 · Edición Sutil / Pro (Pablo, 07-nov 19:49, todos los estilos)
Pablo: «dos opciones: edición sutil, edición pro. La pro tiene efectos, tiene imágenes, tiene transiciones; ojo, sin cargar. Y el
estilo no hace que parezca una cámara de cine: que parezca con esos estilos, ese mood, esa maquetación, los colores, la tipografía».
Causa medida en el Cine C8867: el preset sin `imagenes` → el director recibe «NO hay imágenes, usa solo etiquetas»; la huella del
estilo (`librerias/estilos/huellas/<estilo>.json`: recursos firma por minuto, apoyos 10–24/min, transiciones, paleta, letra) existe
pero sus errores se FILTRAN en `_validar` (inspiración, 04-nov), así que nadie la cumple. Resultado: 1 foto de 8 disponibles.

**Contrato.** Entra: un proyecto + estilo + `modo` ∈ {sutil, pro} (por defecto sutil = lo de hoy; queda en `preferencias.json`;
lo eligen la app, el CLI `--modo` y el lote). Sale en PRO: el video con los recursos firma de la huella al menos en su mínimo por
minuto, apoyos por minuto dentro del rango de la huella, ≥ 2 transiciones distintas de las de la huella, imágenes primero del arte
del proyecto y del banco gratis (`estudio archivo`, Openverse), todo con las reglas de siempre (ritmo máx., una cosa a la vez, zona
segura, sin duplicado). Nunca: gastar créditos de imágenes sin OK; pasar el tope de ritmo (sin cargar); que sutil cambie respecto
de hoy; que un cambio de modo re-transcriba o re-corte (se pule sobre lo hecho).
- CUANDO modo = pro EL SISTEMA DEBE habilitar imágenes en el director (aunque el preset diga «sin imágenes») y darle la huella
  como OBLIGACIÓN (mínimos) y la guía como gusto. Verifica: `uv run pytest tests/regresion/test_C-0010.py::test_pro_pide_imagenes`.
- CUANDO modo = pro y el storyboard no llega a la huella EL SISTEMA DEBE rechazarlo con la lista exacta (Opus completa sobre lo
  que ya está). En sutil la huella sigue siendo inspiración. Verifica: `…::test_pro_bloquea_por_huella` y `…::test_sutil_igual_que_hoy`.
- CUANDO un proyecto ya editado pasa a pro EL SISTEMA DEBE reusar fuente, palabras, cortes y lo que ya está en el storyboard, y
  solo agregar. Verifica: `…::test_pasar_a_pro_no_toca_cortes`.
