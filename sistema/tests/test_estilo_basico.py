"""Estilo Básico (Pablo, 08-nov): solo subtítulo palabra por palabra; determinista, sin director, primero en la lista, opciones validadas."""
import json
from pathlib import Path

import pytest
from PIL import Image

from estudio import catalogo, config, director, motor, subtitulo_basico as sb, validar

PALABRAS = [{"w": w, "s": i * .4, "e": i * .4 + .3} for i, w in enumerate("hoy grabamos videos para ustedes todos juntos ahora mismo.".split())]


def test_es_el_primero_de_la_lista_y_no_usa_director():
    assert list(catalogo.presets())[0] == "basico"
    assert next(c for c in catalogo.catalogo()["categorias"] if c["id"] == "preset")["opciones"][0]["id"] == "basico"
    assert director.sin_director("basico") and not director.sin_director("vox")
    assert "basico" in validar.SUBTITULOS


def test_armar_storyboard_solo_toma_y_subtitulo(tmp_path):
    (tmp_path / "palabras.json").write_text(json.dumps(PALABRAS))
    s = sb.armar(tmp_path)
    assert s["elementos"] == [] and s["trazos"] == [] and len(s["escenas"]) == 1
    assert s["escenas"][0]["persona"]["modo"] == "completa"
    assert s["camara"] == [{"t": 0.0, "zoom": 1.0, "x": 0.0, "y": 0.0, "rot": 0.0}]   # cámara fija
    bl = s["subtitulos"]["bloques"]
    assert bl[0][0] == 0 and bl[-1][1] == len(PALABRAS) and all(b - a <= sb.PALABRAS_BLOQUE for a, b in bl)
    cl = s["subtitulos"]["resaltar"]
    assert cl and all(len(PALABRAS[j]["w"]) >= 5 for j in cl)
    assert not any(j2 - j1 < 1 for j1, j2 in zip(cl, cl[1:]))


def test_storyboard_del_basico_pasa_la_compuerta(tmp_path):
    (tmp_path / "palabras.json").write_text(json.dumps(PALABRAS))
    s = sb.armar(tmp_path)
    presets = catalogo.presets()["basico"]
    s["estilo"] = {"id": "basico", **{k: v for k, v in presets.items() if k != "nombre"}}
    assert validar.errores(s, None, estilo="basico") == []


@pytest.mark.parametrize("malo", [{"sub_efecto": "giro"}, {"sub_color": "rojo"}, {"sub_caja_color": "#FF69B4"}])
def test_opciones_malas_las_rechaza_la_compuerta(malo):
    est = {"id": "basico", **{k: v for k, v in catalogo.presets()["basico"].items() if k != "nombre"}, **malo}
    s = {"estilo": est, "cortes": [], "escenas": [{"t0": 0.0, "persona": {"modo": "completa"}}], "elementos": [], "subtitulos": {}}
    if "sub_caja_color" not in malo:   # el rosa lo frena el seleccionador (sin rosa), no la compuerta del storyboard
        assert validar.errores(s, None, estilo="basico")
    err = []
    catalogo._valor_estilo(*next(iter(malo.items())), err)
    assert err


@pytest.mark.parametrize("efecto", sb.EFECTOS)
@pytest.mark.parametrize("caja", [False, True])
def test_dibuja_palabra_por_palabra_en_zona_segura(efecto, caja):
    est = motor.Estilo({**catalogo.presets()["basico"], "sub_efecto": efecto, "sub_caja": caja})
    f = est.font_rol("display", sb.TAM, 900)
    ws = [("Hoy", 1.0, False), ("grabamos", 1.4, True), ("videos", 1.8, False)]

    def pinta(t):
        lienzo = Image.new("RGBA", (config.W, config.H), (0, 0, 0, 255))
        sb.dibujar(lienzo, t, ws, est, f)
        return lienzo
    assert pinta(.5).getbbox() == (0, 0, config.W, config.H) and pinta(.5).convert("L").getextrema() == (0, 0)   # nada antes de decirse
    assert pinta(1.05).convert("L").getextrema()[1] > 0
    tres = pinta(2.5)
    assert tres.convert("L").getextrema()[1] > 0
    caja_t = tres.convert("L").point(lambda v: 255 if v > 30 else 0).getbbox()
    assert 230 <= caja_t[1] and caja_t[3] <= 1500, caja_t
    assert caja_t[0] >= 60 and caja_t[2] <= config.W - 60


def test_el_efecto_corte_no_tiene_cuadros_intermedios():
    est = motor.Estilo({**catalogo.presets()["basico"]})
    f = est.font_rol("display", sb.TAM, 900)
    ws = [("Hoy", 1.0, False)]
    a, b = (Image.new("RGBA", (config.W, config.H)) for _ in range(2))
    sb.dibujar(a, 1.0, ws, est, f)
    sb.dibujar(b, 1.1, ws, est, f)
    assert a.tobytes() == b.tobytes()
