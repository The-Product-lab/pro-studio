# Plano: los 9 estilos que faltan (obra del PC, noche del 2026-11-04)

Pedido de Pablo: «estudia todos los estilos, te dejaré trabajando toda la noche, mañana quiero venir a darte full feedback».
Cada estilo va a recibir correcciones fuertes de Pablo: esto es la PRIMERA versión de cada uno, no la final.

## Contrato
- **Entra:** los análisis de `librerias/estilos/db/<estilo>/` (las referencias del dueño mandan), el video muestra
  `banco/workshop-C8866.MP4` (Claude Workshop, Sony S-Log3, color Receta Pablo + Elite 200 al 0,7) ya preparado en `proyectos/c8866`.
- **Sale por estilo:** guía `librerias/estilos/<estilo>.md` + preset + los recursos del motor que el estilo necesite (con prueba)
  + un reel del C8866 en ese estilo → `Desktop\claude workshop\REVISION\NN-<estilo>.mp4`, más una página para verlos lado a lado.
- **Nunca:** imponer un estilo (Pablo elige), bajar la compuerta para que algo pase, gastar más arte que el acordado
  (Higgsfield solo en maestro, vox, cine e imprenta, máx. 4 imágenes cada uno), tocar lo que ya funciona.

## Orden y criterio
Orden: maestro → luminoso → swiss → vox → pop → cine → glass → imprenta → prestiggio.
CUANDO un estilo se da por terminado, EL SISTEMA DEBE:
1. pasar `uv run pytest -q` (incluida la compuerta sobre su ejemplo);
2. tener su reel renderizado del C8866 con la compuerta en verde (`estudio.validar.errores(sb) == []`);
3. haber pasado el ojo (Opus) sobre cuadros reales, más una revisión de cuadros mía antes de copiarlo a REVISION.

## Fase extra (si alcanza la noche)
Preparación en dos tiempos: transcribir + cuadros sueltos del crudo → director decide cortes → normalizar y recortar solo
lo que queda (ahorra 60–75 % en videos largos). Pedido de Pablo del 04-nov.

## Estado (2026-11-04, tarde) — TODOS APROBADOS E INTEGRADOS
Pablo aprobó en la pantalla de revisión (`/revision`) los 11: luminoso, maestro, swiss, vox, pop, cine, glass,
imprenta, prestiggio (copia del estilo de la app Prestiggio), julian-alborna (papel) y julian-alborna-3d.
Cada uno vive en el director con `uv run estudio integrar <id> <proyecto>`: guía de APRENDIZAJE (`librerias/estilos/<id>.md`,
qué funciona y por qué; sin recetas), preset y ejemplo aprobado (`estudio/director/ejemplo/<id>.json` + su guion). Las reglas de
Pablo viven en la compuerta; la huella de los referentes ya no bloquea ni se muestra en los estilos aprobados.
Siguiente: prueba real — que la app edite sola un video NUEVO con un estilo integrado y Pablo lo vea.
