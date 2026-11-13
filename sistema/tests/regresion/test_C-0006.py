"""C-0006 (Pablo, 07-nov, Cine C8867, vale para TODOS los estilos): «en el segundo 2 hay un silencio… hay varios silencios»,
«el editor no puede dejar silencios de más de 0,2».
El silencio se mide contra el nivel del TALENTO (lo que se oye), no contra el ruido de la sala: un soplido a -47 dB con el
talento a -20 dB no parte la pausa. Ninguna unión ni pausa del final pasa de montaje.SILENCIO_MAX_S, y `reparar` lo cierra solo."""
import json

import numpy as np

from conftest import CASOS  # noqa: F401  (pone tests/ en el camino)
from estudio import montaje, voz
from test_reparar import proyecto


def test_el_tope_es_el_de_pablo():
    assert montaje.SILENCIO_MAX_S <= .20


def test_union_con_mucho_aire_no_pasa_y_reparar_la_cierra(tmp_path):
    c = proyecto(tmp_path, 10, [(1, 2), (4, 5)], [("uno", 1, 2), ("dos", 4, 5)])
    sb = {"cortes": [[0, .9], [2.3, 3.7], [5.1, 10]]}           # 0,3 + 0,3 s de silencio en la unión
    assert any("de silencio" in e for e in montaje.errores(sb, c))
    rep = montaje.reparar(sb, c)
    assert montaje.errores(rep, c) == []
    assert montaje.reparar(rep, c) == rep


def test_un_soplido_bajo_no_parte_la_pausa(tmp_path):
    c = proyecto(tmp_path, 10, [(1, 2), (4, 5)], [("uno", 1, 2), ("dos", 4, 5)])
    db = np.load(c / ".energia.npy").astype(np.float32)
    for t in (2.5, 3.0, 3.5):                                   # soplidos de 50 ms a -47 dB (27 dB bajo el talento)
        db[int(t / voz.HOP):int((t + .05) / voz.HOP)] = -47.0
    np.save(c / ".energia.npy", db.astype(np.float16))
    montaje._CACHE.clear()
    sb = {"cortes": [[0, .9], [5.1, 10]]}                       # la pausa de 2 s entre «uno» y «dos» queda entera
    assert any("de silencio" in e for e in montaje.errores(sb, c))
    rep = montaje.reparar(sb, c)
    assert montaje.errores(rep, c) == []


def test_silencio_del_arranque_y_de_la_pausa_interior_tambien(tmp_path):
    c = proyecto(tmp_path, 10, [(1, 2), (2.6, 3.5)], [("uno", 1, 2), ("dos", 2.6, 3.5)])
    sb = {"cortes": [[3.6, 10]]}                                # arranca con 1 s mudo y 0,6 s de pausa en medio
    rep = montaje.reparar(sb, c)
    assert montaje.errores(rep, c) == []
    ctx = montaje.contexto(c)
    y = np.concatenate([ctx.voz[int(a / voz.HOP):int(b / voz.HOP)] for a, b in montaje.tramos(rep, ctx.fin)])
    mudos = [b - a for a, b, v in voz._tandas(y) if not v]
    assert max(mudos) * voz.HOP <= montaje.SILENCIO_MAX_S + voz.HOP / 2


def test_banco_cine_sin_silencios_largos(banco):
    c = banco("cine-c8867")
    rep = montaje.reparar(json.loads((c / "storyboard.json").read_text()), c)
    assert not [e for e in montaje.errores(rep, c) if "de silencio" in e]
