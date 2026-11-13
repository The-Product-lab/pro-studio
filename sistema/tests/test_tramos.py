"""Corrector ágil (estudio/tramos.py, Pablo 06-nov): una corrección solo vuelve a exportar los tramos que cambió."""
import copy

from estudio import camara, config, tramos

FPS = config.FPS


def _p(tmp_path, sb, n_src=30 * FPS):
    quitar = set()
    for a, b in sb.get("cortes", []):
        quitar.update(range(round(a * FPS), round(b * FPS)))
    mapa = [i for i in range(n_src) if i not in quitar]
    return type("P", (), {"sb": sb, "mapa": mapa, "ruta": camara.Ruta(sb, len(mapa) / FPS), "dir": tmp_path,
                          "meta": {"video": "no-existe.mp4"}, "palabras": [], "cubo": None})()


SB = {"estilo": {"id": "x"}, "cortes": [], "camara": [{"t": 0, "zoom": 1.04}],
      "escenas": [{"t0": 0, "persona": {"modo": "completa"}}, {"t0": 15, "persona": {"modo": "recorte"}}],
      "elementos": [{"id": "a", "t0": 4.0, "t1": 5.0}, {"id": "b", "t0": 20.0, "t1": 22.0}], "trazos": [], "subtitulos": {"y": 1450}}


def _distintos(a, b):
    return [x[0] // FPS for x, y in zip(a, b) if x[2] != y[2]] + ([-1] if len(a) != len(b) else [])


def test_cambiar_un_elemento_solo_toca_sus_tramos(tmp_path):
    antes = tramos.claves(_p(tmp_path, SB))
    sb = copy.deepcopy(SB)
    sb["elementos"][1]["texto"] = "otro"
    assert _distintos(antes, tramos.claves(_p(tmp_path, sb))) == [18, 21]   # 20-22 s ± 1 s → tramos de 18 y 21 s


def test_lo_global_cambia_todos(tmp_path):
    antes = tramos.claves(_p(tmp_path, SB))
    sb = copy.deepcopy(SB)
    sb["estilo"]["acento"] = "#ff0000"
    assert len(_distintos(antes, tramos.claves(_p(tmp_path, sb)))) == len(antes)


def test_un_corte_reusa_lo_de_antes(tmp_path):
    antes = tramos.claves(_p(tmp_path, SB))
    sb = copy.deepcopy(SB)
    sb["cortes"] = [[12.0, 13.0]]
    d = _distintos(antes, tramos.claves(_p(tmp_path, sb)))
    assert d and min(x for x in d if x >= 0) == 12 and 0 not in d and 9 not in d
