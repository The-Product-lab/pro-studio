# Método para los estilos: estudiar → implementar → crear

Así nace cada uno de los 11 estilos de The Product Studio 2. Lo puede repetir la Mac o la PC. El conocimiento vive en
`librerias/estilos/db/` (versionado). Solo los videos de referencia quedan fuera de git.

## Estado al 03-nov
| Estilo | Estudio (vidIQ) | Implementado en el motor | Referencias de Pablo |
|---|---|---|---|
| maestro | 6 | no | Dc_2Y1qI0ZH, DfAE8n5ovTR |
| luminoso | 4 | no | Dbq9awKotYY |
| swiss | 5 | no | De9SYDwhTG0 |
| vox | 4 | no | — |
| pop | 4 | no | — |
| cine | 4 | no | — |
| glass | 3 | no | — |
| imprenta | 3 | no | — |

Las referencias de Pablo pesan más que las de creadores encontrados con la búsqueda. Si chocan, gana lo de Pablo.

## 1. Estudiar (vidIQ, siempre de cero)
Reglas de Pablo:
- Se busca por **formato de edición**, nunca por tema.
- Se buscan **creadores** que editan así, no videos sueltos.
- Las fichas viejas de la app anterior (`ficha-app-vieja.md`) solo sirven de contexto: **todo se re-estudia nuevo**.
- Hay que trabajar ordenado: una carpeta por estilo, nada suelto.

Herramientas (MCP de vidIQ en Claude Code):
- `vidiq_ig_accounts_from_outliers`: cuentas que hacen ese formato.
- `vidiq_ig_profile_reels`: sus reels con métricas, para elegir los 3–6 mejores del formato.
- `vidiq_watch_shortform_content`: análisis cuadro a cuadro (10 créditos, máximo 2 trabajos a la vez).
  Se pregunta por los 11 bloques: lenguaje visual, paleta HEX, tipografías, subtítulos, fondos y texturas, persona,
  elementos gráficos, movimiento, transiciones, ritmo, sonido.

Salida:
- `db/<estilo>/analisis/<shortcode>.md`, con encabezado `# <ESTILO> · @creador · URL` y la línea «fuente: referencia del dueño» o «búsqueda de creadores».
- `db/<estilo>/portadas/<shortcode>.jpg`.
- `db/referencias.json`: la referencia y su estado (`estudiado`).
- La galería `db/galeria.html` se regenera para que Pablo vea todo antes de aprobar.

## 2. Sintetizar
`librerias/estilos/<estilo>.md` es la guía que lee el director. Sale de cruzar todos los análisis. Lleva:
- identidad en una frase;
- paleta;
- roles de tipografía (display, script, mono);
- base (`pantalla`: la persona en su toma completa; el collage se retiró el 11-nov);
- recursos con su cuándo (filtros, cajas, franjas, texto detrás, trazos);
- ritmo (cambio cada 1,5–3 s);
- subtítulos;
- transiciones;
- sonido;
- qué NO hacer.

Lo que el motor no sabe hacer todavía se anota como «falta en motor».

## 3. Implementar
1. Preset en `librerias/estilos/presets.json`: acento, acento2, tinta, papel, fuente, roles, base, subtítulo, crt, grano y el resto que pida el estilo.
2. Si hay recursos nuevos, van al compositor como funciones reutilizables, nunca un parche por video:
   - en el motor Python: `estudio/motor.py` y `estudio/efectos.py`;
   - en el motor HyperFrames: `estudio/hf/`, cuando esté hecho.
3. Se documentan en `estudio/director/GRAMATICA.md`.
4. Se escribe `estudio/director/ejemplo/<estilo>.json`: un storyboard ejemplar sobre `ejemplo/palabras.json`.
5. `uv run pytest`: el test de ejemplos valida que el JSON sea correcto.

## 4. Crear y probar
1. `uv run estudio editar <clip> --estilo <estilo> --nombre <x>`.
2. Mirar cuadros reales con `estudio previa`, corregir y volver a mirar.
3. El final se copia a la carpeta de revisión y Pablo decide.
   El estilo se elige siempre con él; nunca se impone uno.
4. Cada corrección de Pablo pasa por el Agente Editor:
   - gusto → `perfil/gusto.md`;
   - sistema → código + test de regresión.
