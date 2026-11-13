"""C-0008 (Pablo, 07-nov, Cine C8867, todos los estilos): «se escucha una persona de atrás decir uno, dos, tres, va… estás dejando
pasar las cosas que suenan pasito; el sistema no los puede permitir».
La voz de fuera (claqueta, apuntador) dura lo que SUENA, no lo que Whisper le da, y la compuerta mira la voz audible que queda
dentro de un tramo, no el centro de la palabra."""
import json

import numpy as np

from conftest import CASOS  # noqa: F401
from estudio import montaje, voz
from test_reparar import proyecto


def _con_conteo(tmp_path):
    # talento 1–2 s y 4–5 s; conteo bajo (-38 dB) 2,6–3,5 s que Whisper cierra en 3,0 s; el talento sigue en 4 s
    c = proyecto(tmp_path, 10, [(1, 2), (4, 5), (6, 7)], [("hola", 1, 1.5), ("amigos", 1.5, 2), ("dos", 2.6, 2.8, True),
                                                          ("tres", 2.8, 3.0, True), ("sigo", 4, 5), ("aquí", 6, 7)])
    db = np.load(c / ".energia.npy").astype(np.float32)
    db[int(2.6 / voz.HOP):int(3.5 / voz.HOP)] = -38.0
    np.save(c / ".energia.npy", db.astype(np.float16))
    montaje._CACHE.clear()
    return c


def test_la_voz_de_fuera_se_estira_a_lo_que_suena(tmp_path):
    ctx = montaje.contexto(_con_conteo(tmp_path))
    tres = next(p for p in ctx.palabras if p["w"] == "tres")
    assert tres["e"] >= 3.45


def test_la_cola_audible_del_conteo_dentro_de_un_tramo_no_pasa_y_reparar_la_quita(tmp_path):
    c = _con_conteo(tmp_path)
    sb = {"cortes": [[2.1, 3.1]]}                 # el corte se queda en el fin de Whisper: suenan 0,4 s del conteo
    assert any("fuera de cámara" in e for e in montaje.errores(sb, c))
    rep = montaje.reparar(sb, c)
    assert not [e for e in montaje.errores(rep, c) if "fuera de cámara" in e]


def test_banco_cine_el_dos_tres_no_queda(banco):
    c = banco("cine-c8867")
    rep = montaje.reparar(json.loads((c / "storyboard.json").read_text()), c)
    assert not [e for e in montaje.errores(rep, c) if "fuera de cámara" in e or "claqueta" in e]
