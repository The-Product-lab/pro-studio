# Resultado T-0193b (07-nov) — rama isis/t0193, sin push

`uv run pytest -q`: **216 passed, 2 skipped** (los 2 skip ya existían).

## 1. Sin `.intentos/`
- `ingesta.archivar_intento` → `ingesta.limpiar_intento`: el reintento limpio **borra** storyboard.json, arte.json, costos.jsonl y `_guia` y arranca; no copia nada. `arte/` (imágenes pagadas) se queda. `tests/test_derivar.py` ajustado (nada se acumula tras 3 reintentos).
- Intermedios viejos encontrados en `the-product-studio-2/proyectos/` (solo lista, no borré nada de ahí):
  - `video_mudo.mp4` (~24 MB por proyecto) y `.tramos/` → sobraban tras cada render. **Ya no se generan**: `motor.limpiar_render` los quita al terminar (aunque falle la mezcla).
  - `sfx.wav` (~2,4 MB) → intermedio de la mezcla; `sonido.mezclar` lo borra siempre (try/finally).
  - Sin tocar, a decidir: `.cuadros/` (440 MB en c8866-swiss; caché de vistas previas, se reutiliza → no es basura clara), `.audio16k.npy` (15 MB, lo usa el montaje), `previa.jpg`, `sfx-informe.json` (nadie lo lee, 1 KB), `copia.py`/`lado.py` (scripts sueltos de la tanda de estilos del 04-nov, no los genera el motor; borrarlos es decisión de Pablo/Isis), `.clips/`.
  - Pruebas: `tests/test_limpieza_render.py`.

## 2. Swiss C8872
Dos causas reales, ambas corregidas en `voz.py`:
- Marcas `fuera` viejas (sin `motivo`, del `voces_fuera` viejo) sobre voz a nivel del talento («Dejé de ser el editor y» a 85 s) mandaban sobre el detector nuevo. Ahora `marcar_fuera` las suelta salvo que suenen ≥10 dB bajo el talento (y conserva la palabra fuerte aislada entre dos marcas bajas). Prueba: `test_marcas_viejas_…`, `test_una_palabra_fuerte_entre_…` y `test_swiss_las_marcas_fuera_viejas_…` (banco).
- `sumar_palabras` volvía «voz» toda una palabra estirada por Whisper (la «Y» de 0,7 s a 89,37 s) y tapaba silencios. Ahora solo suma palabras que de verdad suenan bajo el umbral.
- Efecto medido: Cine 1 → **0** residuales (tope del banco bajado a 0). **Swiss sigue en 4 avisos**: el director cortó en medio de «…editor **y|** eso me permite…» (86,39 s) y alrededor de la «Y» de 89–90 s, donde el audio no tiene silencio (dip de ~30 ms). Arreglarlo exigiría cambiar qué palabras quita el director, así que queda como aviso `degradado` con su segundo, no como error que tumbe el video.

## 3. No idempotentes
Reproducido con fuzz (semilla 143 de 4000; 2 casos en total). Causa: la 1.ª pasada deja un `no_borrar`, y el «pedacito suelto» que agranda después traga una palabra que en la 2.ª pasada vuelve «tragable» y corta más. Arreglo: `reparar` repite hasta el punto fijo (`MAX_PASADAS=4`, cada pasada es `_pasada`). Fuzz de 4000 casos: 0 fallos. Pruebas: `test_caso_no_idempotente_del_abogado…` y `test_propiedad_idempotente_con_voz_fuera_pegada…` (200 casos). Costo: una pasada extra por llamada.

## 4. Verde y commit — ver git log.

## En simple para Pablo (6 líneas)
1. Ya no se guardan intentos: un reintento borra lo fallado y arranca limpio.
2. Tras cada video quedan solo el final y lo que se reutiliza: ya no sobran el video mudo, los trozos ni el wav de efectos.
3. Las marcas viejas de «voz de fuera» ya no se comen tu voz fuerte; el detector nuevo manda (Cine queda en cero errores).
4. En Swiss quedan 4 avisos: el corte del director cae donde tu voz no tiene ni un respiro; se avisa con el segundo, el video no se cae.
5. El arreglo de cortes ahora da el mismo resultado si lo repites (se probó con 4000 casos al azar).
6. Pendiente tuyo: decidir si se borran `copia.py`/`lado.py` y la caché `.cuadros` (440 MB) de los proyectos viejos.
