"""Editor de textos sobre película (Pablo 09-nov: «no muestra todas las palabras»): toda palabra dicha se dibuja, dentro de la zona."""
import json

from estudio import texto_pelicula as tp


def _carpeta(tmp_path, tramos):
    ps = [{"w": w, "t0": i * .4, "t1": i * .4 + .35} for i, w in enumerate("Tu celular está lleno de videos que nunca publicaste y ya no sirve".split())]
    (tmp_path / "palabras.json").write_text(json.dumps(ps))
    (tmp_path / "mapa-texto.json").write_text(json.dumps({"video": "limpio.mp4", "tramos": tramos}))
    return tmp_path


def test_todas_las_palabras_y_zona(tmp_path):
    tramos = [{"t0": 0, "t1": 2.4, "libre": {"x0": 100, "y0": 300, "x1": 980, "y1": 600}, "tinta": "#1c1510", "acento": "#c2432a",
               "integracion": "grabado", "fondo_luma": 205},
              {"t0": 2.4, "t1": 6, "libre": None, "tinta": "#1c1510", "integracion": "rotulador", "fondo_luma": 0}]
    pl = tp.planear(_carpeta(tmp_path, tramos))
    inf = tp.informe(pl)
    assert inf["ok"], inf["fallas"]
    assert inf["mostradas"] == inf["palabras"] == 13
    assert any(b["lugar"] == "pliego" for b in pl["plan"])          # sin hueco libre → pliego, nunca se pierde la palabra
    for b in pl["plan"]:
        x0, y0, x1, y1 = b["caja"]
        assert tp.ZONA[0] <= x0 and tp.ZONA[1] <= y0 and x1 <= tp.ZONA[2] and y1 <= tp.ZONA[3]
        assert b["tam"] >= tp.TAM_MIN


def test_hueco_chico_va_al_pliego(tmp_path):
    tramos = [{"t0": 0, "t1": 6, "libre": {"x0": 600, "y0": 300, "x1": 700, "y1": 330}, "tinta": "#1c1510", "integracion": "grabado",
               "fondo_luma": 205}]
    pl = tp.planear(_carpeta(tmp_path, tramos))
    assert all(b["lugar"] == "pliego" for b in pl["plan"])
    assert tp.informe(pl)["ok"]


def test_contraste_bajo_no_pasa_en_libre(tmp_path):
    tramos = [{"t0": 0, "t1": 6, "libre": {"x0": 100, "y0": 300, "x1": 980, "y1": 900}, "tinta": "#2a2a2a", "integracion": "grabado",
               "fondo_luma": 30}]
    pl = tp.planear(_carpeta(tmp_path, tramos))
    assert all(b["lugar"] == "pliego" for b in pl["plan"])            # tinta oscura sobre fondo oscuro → pliego claro
