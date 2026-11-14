"""C-0014: medir en código qué palabras del guion mostró Lemo (`window.TEXTS`), con una página mínima de contrato Lemo hecha aquí."""
import json

import pytest

from estudio import textos_lemo, texto_pelicula

requiere_lemo = pytest.mark.skipif(not (textos_lemo.LEMO / "core").is_dir(), reason="falta la biblioteca de Lemo")


def _ps(*pal):
    return [{"w": w, "s": s, "e": e} for w, s, e in pal]


def test_marcar_normaliza_ventana_y_vacias():
    ps = _ps(("Está", 0.0, .3), ("lleno", .3, .6), ("de", .6, .8), ("videos,", .8, 1.2),      # frase 1
             ("y", 3.0, 3.1), ("ya", 3.1, 3.3),                                              # frase 2: solo vacías
             ("nunca", 6.0, 6.4), ("publicaste", 6.4, 7.0))                                  # lejos en el tiempo del texto de Lemo
    textos = [{"id": "a", "text": "ESTÁ lleno", "t0": 0.0, "t1": 1.0}, {"id": "b", "text": "Videos", "t0": 0.5, "t1": 1.5},
              {"id": "c", "text": "nunca", "t0": 1.0, "t1": 2.0}]                             # «nunca» aparece 4 s antes de decirse: fuera de ventana
    m = textos_lemo.marcar(ps, textos)
    assert [x["mostrada"] for x in m] == [True, True, True, True, False, False, False, False]
    assert m[2]["por"] == "frase" and m[0]["por"] == "lemo"           # «de» hereda de su frase; «Está» coincide sin tildes ni mayúsculas
    assert textos_lemo.norm("¡Más!") == "mas"


@requiere_lemo
def test_leer_con_una_pagina_de_contrato_lemo(tmp_path, pagina_lemo):
    pagina_lemo(tmp_path, [("t1", "Hola", .5, 1.0), ("t2", "mundo", 1.5, 2.0)], 3.0)
    (tmp_path / "palabras.json").write_text(json.dumps(_ps(("hola", .6, .9), ("mundo", 1.6, 1.9), ("raro", 2.5, 2.9))))
    r = textos_lemo.medir(tmp_path)
    assert [t["text"] for t in r["textos"]] == ["Hola", "mundo"] and r["textos"][0]["t0"] == .5
    assert r["indices_mostradas"] == [0, 1] and r["mostradas_lemo"] == 2 and r["cobertura"] == round(2 / 3, 3)
    assert textos_lemo.mostradas(tmp_path) == {0, 1}


@requiere_lemo
def test_pagina_sin_texts_no_cumple_el_contrato(tmp_path):
    (tmp_path / "index.html").write_text("<!doctype html><body><script>window.DUR=1;window.render=t=>{};window.READY=true</script>")
    try:
        textos_lemo.leer_textos(tmp_path)
    except RuntimeError as e:
        assert "TEXTS" in str(e)
    else:
        raise AssertionError("debía fallar sin window.TEXTS")


def test_solo_faltantes_arma_bloques_solo_con_lo_que_falta(tmp_path):
    ps = [{"w": w, "s": i * .4, "e": i * .4 + .35} for i, w in enumerate("uno dos tres cuatro cinco seis".split())]
    (tmp_path / "palabras.json").write_text(json.dumps(ps))
    (tmp_path / "mapa-texto.json").write_text(json.dumps({"video": "pelicula.mp4", "tramos": [
        {"t0": 0, "t1": 3, "libre": {"x0": 100, "y0": 300, "x1": 980, "y1": 700}, "tinta": "#1c1510", "integracion": "grabado", "fondo_luma": 205}]}))
    pl = texto_pelicula.planear(tmp_path, {1, 2, 5})                    # Lemo mostró dos, tres y seis
    assert [(b["i0"], b["i1"]) for b in pl["plan"]] == [(0, 1), (3, 5)]    # faltan: uno | cuatro cinco (rachas separadas)
    inf = texto_pelicula.informe(pl)
    assert inf["ok"] and (inf["mostradas"], inf["lemo"], inf["agregadas"]) == (6, 3, 3)
    assert all(b["tam"] <= texto_pelicula.TAM_MAX_FALTA for b in pl["plan"])
    sin_uno = texto_pelicula.informe(texto_pelicula.planear(tmp_path, {1, 2, 5}) | {"lemo": [2, 5]})   # si Lemo no mostró «dos», la cobertura falla
    assert not sin_uno["ok"] and "1 palabras sin mostrar: dos" in sin_uno["fallas"][0]


def test_errata_de_la_transcripcion_cuenta_como_mostrada():
    """Pablo 09-nov (prueba real ukiyoe): el audio dice «WORSHOP» y Lemo escribió «WORKSHOP»: no hay que agregarla encima."""
    ps = [{"w": "WORSHOP", "s": 1.0, "e": 1.5}, {"w": "gato", "s": 2.0, "e": 2.3}]
    m = textos_lemo.marcar(ps, [{"t0": .8, "t1": 2.0, "text": "comentá la palabra WORKSHOP"}])
    assert m[0]["mostrada"] and not m[1]["mostrada"]


def test_el_guion_del_encargo_usa_el_diccionario_de_nombres():
    from estudio import pro
    assert pro.nombre("Cloud,") == "Claude," and pro.nombre("cloud") == "Claude" and pro.nombre("gato") == "gato"
