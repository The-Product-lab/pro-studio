# The Product Studio 2 (TPS2)

Editor de reels de The Product Lab: storyboard JSON que diseña el director (IA por `claude -p`), compuerta `validar.py`, motor que renderiza, app local en el puerto 8792. Vive en dos máquinas (Mac y PC de la oficina) y las dos trabajan a la vez. Manda la Constitución de TPL (`~/Desktop/CLAUDE CODE/CLAUDE.md`); este archivo es lo propio de este repo.

## Cómo se trabaja (Mac y PC por igual)
1. **Una sola verdad: `origin/main`.** Nada queda «solo en mi disco»: si no está en una rama empujada, no existe.
2. **Una rama por mejora**, en un worktree aparte (`git worktree add ../tps2-<tema> -b <maquina>/<tema> origin/main`). El árbol principal solo corre `main`; nadie edita ahí ni deja cambios sin commit.
3. **Antes de entregar: `uv run estudio verificar`** (capa 1, menos de 60 s: sin basura, compila, todas las pruebas, su número no baja, cada corrección «sistema» con su prueba). Sale 0 o 1. El hook `pre-push` lo corre solo y bloquea el push si falla. GitHub Actions (`.github/workflows/verificar.yml`) corre lo mismo, por si alguien salta el hook.
4. **El hook se activa con `git config core.hooksPath .githooks`**; ya lo hacen `instalar.command` e `instalar.bat`. Si clonaste sin instalar, córrelo a mano.
5. `git pull --rebase` antes de empujar; `git add` por nombre, nunca autostash. Commit + push de cada mejora de sistema (nunca videos ni datos).
6. Antes de abrir una obra, lee `~/Desktop/CLAUDE CODE/claudio/cerebro/registro/obras.md` y anota tu línea (sistema `the-product-studio-2`, tu carril); ciérrala al terminar.
7. Una corrección de Pablo a un sistema se registra con su frase literal en `perfil/correcciones.jsonl`; si es de clase «sistema», entra con su `tests/regresion/test_<id>.py` (lo exige `verificar`). Una frase en un prompt no es arreglo de algo medible.

## Carriles
| Carril | Dueño | Qué |
|---|---|---|
| Motor | **PC** | `motor.py`, `tramos.py`, `camara.py`, `efectos.py`, `color.py` (render), `montaje.py`, `repeticiones.py`, `voz.py`, `cirugia.py`, `sonido.py`, `sfx.py`, `ingesta.py`, `lote.py`, `ia.py`, `disco.py`, `entorno.py`, `doctor.py`; sus pruebas y `tests/banco/` |
| Superficie y gusto | **Mac** | `app/`, `servidor.py`, `catalogo.py`, `muestras.py`, `rapida.py`, `portadas.py`, `revision.py`, `tablero.py`; `librerias/estilos/`, `estilista.py`, `referentes.py`, `estudio_visual.py`, `aprobar.py`, `integrar.py`, `huella.py`; `perfil/gusto.md`, `estudio/agente/`, `tests/regresion/`; `verificar.py`, `tests/golden/`; este archivo y los `PLANO-*.md` |
| Compartido | los dos, con aviso | `validar.py` (un cambio por vez), `director/` (prompts y ejemplos, junto con el motor que lo habilita), `config.py`, `cli.py`, `pyproject.toml`, `uv.lock` (lo regenera solo quien cambia dependencias), `librerias/estilos/presets.json`, `librerias/color`, `librerias/fuentes` |

Un carril no es una prohibición: tocar el carril contrario es posible **con una línea previa en `obras.md`** y rebase el mismo día. Lo que de verdad choca es `motor.py`/`tramos.py`, `validar.py` y `montaje.py`: ahí, una sola rama abierta a la vez. **En choque gana la Mac.**

## Regla de limpieza (Pablo, 07-nov)
El repo y el editor guardan **solo lo necesario para producir**. Nada de copias «por si acaso», archivos de intentos viejos ni intermedios acumulados: lo viejo ya está en el historial de git. `.gitignore` y `estudio verificar` lo hacen cumplir (videos, archivos > 5 MB, carpetas de intentos o temporales, copias idénticas). La deuda anterior está en `tests/basura-conocida.txt` y solo puede bajar. Los videos y el banco crudo viven fuera de git.

## Dónde está cada cosa
- `README.md`: instalar y usar. `HANDOFF-PC.md`: lo que necesita el Claude del PC (instalación, lo privado, render).
- `METODO-ESTILOS.md`, `PLANO-ESTILOS.md`, `PLANO-SELECCIONADOR.md`, `PLANO-SONIDO.md`: métodos y planos de estilos, seleccionador y sonido. `BLUEPRINT.md` y `BORRADOR-ARQUITECTURA.md` describen un sistema anterior (históricos).
- Plano de la arquitectura paralela y la compuerta: `~/Desktop/CLAUDE CODE/claudio/cerebro/drafts/T-0195-arquitectura-paralela.md`. Plano de la ingesta, el lote y el reintento: T-0193 (rama `isis/t0193`).
- Reglas del motor: `estudio/director/GRAMATICA.md`. Lo privado (LUTs, receta de color de Pablo) está en `privadas/`, nunca en git.
- IA solo por `claude -p` (Opus decide y revisa, Sonnet ejecuta; nunca Haiku ni API).
