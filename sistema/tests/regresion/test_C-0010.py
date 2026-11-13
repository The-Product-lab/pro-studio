"""C-0010 (Pablo, 07-nov, machote C8867: «no sirve», «palabras que no van como el ya», «personas atrás hablando»).
1) Una orden de grabación de dos palabras pegada a una frase («…este con cloud. Ya, listo») se marca como claqueta.
2) Una «isla» (tramo corto, de pocas palabras, entre dos cortes que quitan contenido) es un resto de otra toma y se quita entera;
   un tramo separado solo por pausas cerradas no es isla.
3) El machote real de C8867 queda en el guion aprobado (sin «te», «en», «este con cloud», «listo», «tres»)."""
import json
from pathlib import Path

import pytest

from conftest import CASOS  # noqa: F401
from estudio import montaje, voz
from test_reparar import proyecto


def test_ya_listo_pegado_es_claqueta():
    ps = [{"w": w, "s": i * .3, "e": i * .3 + .25} for i, w in enumerate("videos como este con cloud Ya, listo".split())]
    voz._ordenes_pegadas(ps)
    assert [p["w"] for p in ps if p.get("fuera")] == ["Ya,", "listo"]
    ps2 = [{"w": w, "s": i * .3, "e": i * .3 + .25} for i, w in enumerate("ya no sirve te los entrega listos".split())]
    voz._ordenes_pegadas(ps2)
    assert not any(p.get("fuera") for p in ps2)


def test_isla_entre_cortes_de_contenido_se_quita(tmp_path):
    voces = [(1, 3), (4, 6), (8, 8.6), (10, 12)]
    # «te» suelto es resto de otra toma: se vuelve a decir después (la última toma manda)
    # (no «uno, dos»: desde C-0008 un conteo de arranque es claqueta y ya no sería contenido antes de la isla)
    ps = [("hola", 1, 2), ("amigos", 2, 3), ("viejo", 4, 5), ("toma", 5, 6), ("te", 8, 8.6), ("te", 10, 11), ("cuatro", 11, 12)]
    c = proyecto(tmp_path, 14, voces, ps)
    sb = montaje.reparar({"cortes": [[3.2, 7.8], [8.8, 9.8]]}, c)          # «te» queda solo entre dos cortes que quitaron palabras
    ctx = montaje.contexto(c)
    quedan = montaje.tramos(sb, ctx.fin)
    assert not any(a <= 8.3 <= b for a, b in quedan)


def test_tramo_entre_pausas_cerradas_no_es_isla(tmp_path):
    c = proyecto(tmp_path, 12, [(1, 2), (4, 5), (7, 8)], [("hola", 1, 2), ("mundo", 4, 5), ("amigos", 7, 8)])
    sb = montaje.reparar({"cortes": []}, c)
    ctx = montaje.contexto(c)
    assert any(a <= 4.5 <= b for a, b in montaje.tramos(sb, ctx.fin))


C8867 = Path(__file__).resolve().parents[2] / "proyectos" / "c8867"


@pytest.mark.skipif(not (C8867 / "machote.json").exists(), reason="proyecto C8867 no está en esta máquina")
def test_machote_c8867_sin_restos():
    m = json.loads((C8867 / "machote.json").read_text())
    rep = montaje.reparar({"cortes": m["cortes"]}, C8867)
    ctx = montaje.contexto(C8867)
    q = montaje.tramos(rep, ctx.fin)
    assert not any(a <= 182.5 <= b or a <= 184.0 <= b for a, b in q)        # «este con cloud» / «listo» de la toma abandonada
    assert montaje.errores(rep, C8867) == []
