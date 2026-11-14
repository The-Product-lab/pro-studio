"""Estilos Pro (Pablo 09-nov): «hay que dejar que Lemo haga y tú encima pones lo que haga falta… si tú haces todo no va a ser igual a Lemo».
Lo que Lemo mostró no se repite: nuestro editor agrega SOLO las palabras que faltan, chicas, y Lemo + nuestras = 100 %."""
import json

import pytest

from estudio import texto_pelicula as tp
from estudio import textos_lemo

requiere_lemo = pytest.mark.skipif(not (textos_lemo.LEMO / "core").is_dir(), reason="falta la biblioteca de Lemo")


@requiere_lemo
def test_solo_faltantes_chicas_y_cobertura_total(tmp_path, pagina_lemo):
    frase = "Tu celular está lleno de videos que nunca publicaste".split()
    ps = [{"w": w, "s": i * .4, "e": i * .4 + .35} for i, w in enumerate(frase)]
    (tmp_path / "palabras.json").write_text(json.dumps(ps))
    pagina_lemo(tmp_path, [("a", "CELULAR", .3, 2.0), ("b", "videos", 2.0, 3.4)], 4.0)      # Lemo muestra «celular» y «videos»
    r = textos_lemo.medir(tmp_path)
    mostradas = textos_lemo.mostradas(tmp_path)
    assert {1, 5} <= mostradas and r["por_palabra"][0]["por"] == "frase"        # «Tu» (vacía) hereda de «celular» dentro de su frase
    assert not {7, 8} & mostradas                                                                  # «nunca publicaste»: nadie las mostró
    (tmp_path / "mapa-texto.json").write_text(json.dumps({"video": "pelicula.mp4", "tramos": [
        {"t0": 0, "t1": 4, "libre": {"x0": 100, "y0": 300, "x1": 980, "y1": 700}, "tinta": "#1c1510", "integracion": "grabado", "fondo_luma": 205}]}))
    pl = tp.planear(tmp_path, mostradas)
    inf = tp.informe(pl)
    puestas = {j for b in pl["plan"] for j in range(b["i0"], b["i1"])}
    assert inf["ok"] and puestas.isdisjoint(mostradas)                    # nada se repite encima de lo de Lemo
    assert puestas | mostradas == set(range(len(ps))) and inf["mostradas"] == inf["palabras"]
    assert pl["plan"] and all(b["tam"] <= tp.TAM_MAX_FALTA < tp.TAM_MAX for b in pl["plan"])   # chicas y discretas
