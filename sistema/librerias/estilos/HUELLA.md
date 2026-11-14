# Ficha de referente y huella de estilo (cómo se aprende de los referentes)

Cada reel de referencia estudiado (`db/<estilo>/analisis/<código>.md`) se convierte en una **ficha** medible
(`db/<estilo>/fichas/<código>.json`). Las fichas de un estilo se cruzan en su **huella** (`huellas/<estilo>.json`):
lo que el estilo ES, en números y listas que la compuerta puede medir sobre el storyboard. La guía `<estilo>.md` explica
la huella con palabras para el director; si chocan, manda la huella. Las correcciones de Pablo cambian la huella.

Reglas del cruce:
- Las referencias del dueño mandan; una de búsqueda nunca contradice a una del dueño.
- **Nunca se descarta un referente por su idioma, tema o cultura**: Pablo elige por la EDICIÓN (04-nov: los dos más queridos de
  maestro estaban «descartados» por ser telecom en árabe). Lo único que se descarta es lo que Pablo marca «no me gusta» en el
  taller. Un tutorial de software se usa por sus efectos, no por su interfaz.
- **Las marcas de Pablo en el taller (`db/<estilo>/gustos.json` y `gustos-reel.json`) mandan sobre todo análisis.**
- Rangos, no números sueltos: el rango cubre las referencias buenas (min–max), no la media.
- Cada recurso apunta a cómo se hace en el motor (`motor`) o queda en `falta_en_motor`.

## Ficha (`db/<estilo>/fichas/<código>.json`)
```json
{"ref": "DfAE8n5ovTR", "fuente": "dueño | busqueda", "sirve": true, "por_que": "qué del estilo muestra (o por qué no sirve)",
 "paleta": [{"hex": "#B21E27", "rol": "palabra clave / fondo / acento secundario…", "cuanto": "dominante | acento | detalle"}],
 "tipografia": [{"rol": "display | script | mono | cuerpo", "como_es": "sans condensada pesada en mayúsculas", "google": "Anton"}],
 "ritmo": {"cambio_cada_s": [1.5, 2.5], "cortes_por_min": [25, 35], "gancho": "qué pasa en 0–2 s"},
 "subtitulos": {"hay": true, "modo": "palabra | bloque | frase | ninguno", "y_aprox": 1450, "mayus": true, "clave": "cómo se marca"},
 "persona": {"tratamiento": "color natural en penumbra / recorte / B/N…", "encuadre": "plano medio centrado…"},
 "recursos": [{"nombre": "palabra gigante detrás de la cabeza", "por_min": [10, 20], "dur_s": [0.8, 1.6],
               "cuando": "palabras clave estructurales", "como": "detalle medible"}],
 "apoyos": {"por_min": [12, 20], "tipos": ["tags", "foto de archivo B/N", "ráfaga"]},
 "imagenes": {"tipo": "archivo B/N / 3D / stock…", "tratamiento": "grano, borde, recorte…", "cuantas": 3},
 "transiciones": ["corte duro", "whip zoom"], "camara": ["micro-zoom 100→105 % por plano", "punch en palabra clave"],
 "sonido": ["whoosh en corte", "pop en entradas"], "si": ["…"], "no": ["…"]}
```

## Huella (`huellas/<estilo>.json`)
```json
{"estilo": "maestro", "identidad": "una frase", "referencias": ["DfAE8n5ovTR (dueño)", "…"],
 "descartadas": [{"ref": "DRUpn6CDHw9", "por": "telecom en árabe: no muestra palabra detrás"}],
 "paleta": [{"hex": "#B21E27", "rol": "…"}], "colores_extra_permitidos": ["#FFFFFF", "#121212"],
 "tipografia": {"display": "Anton", "script": "Playfair Itálica", "mono": "JetBrains Mono"},
 "ritmo": {"cambio_cada_s": [1.2, 2.5], "gancho_cambio_cada_s": [0.8, 1.4]},
 "subtitulos": {"modo": "palabra", "y": [1440, 1480]},
 "recursos_firma": [{"nombre": "palabra detrás", "motor": {"tipo": "texto", "z": "atras"}, "por_min": [8, 20]}],
 "apoyos_por_min": [12, 24], "imagenes_max": 4,
 "transiciones": ["corte", "zoom"], "si": ["…"], "no": ["…"], "falta_en_motor": ["…"]}
```
`recursos_firma[].motor` es un patrón que se busca en `storyboard.elementos` (o `escenas` si lleva `"en": "escenas"`):
todas sus claves deben coincidir. Ej.: `{"en": "escenas", "filtro": "halftone"}`, `{"tipo": "etiqueta"}`, `{"en": "escenas", "persona.modo": "silueta"}`.
