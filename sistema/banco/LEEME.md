# Banco de pruebas (clips reales, se guardan para siempre)

Cada estilo se prueba sobre los MISMOS clips para poder compararlos. Los videos no van a git (pesan); aquí queda de dónde
sale cada uno para rehacerlo en cualquier máquina.

| Clip | Qué prueba | Origen |
|---|---|---|
| `tierno-24s.mp4` | talking-head sentado, una mujer, micrófono en cuadro, fondo negro de estudio; 4K vertical Rec.709 29,97 fps | primeros 24 s de `captions/edicion-claude/entrada/Eres muy tierno.mov` (PC de la oficina) |

Rehacer: `ffmpeg -i "Eres muy tierno.mov" -t 24 -c:v libx264 -crf 16 -preset fast -c:a aac -b:a 192k banco/tierno-24s.mp4`.
Proyecto preparado (transcripción + alfas): `proyectos/banco-tierno/`.
