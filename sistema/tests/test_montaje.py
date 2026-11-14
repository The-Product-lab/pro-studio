"""Compuerta del montaje: claqueta fuera, cortes solo en silencio, aire al final de cada tramo, sin silencios largos.
Casos reales: 04-nov un «dos, tres, acción» de fuera de cámara se coló y el final cortó «información»."""
import json

import numpy as np

from estudio import montaje

SR = 16000


def _proyecto(tmp_path, voz):
    """voz = [(t0, t1)] tramos con voz (tono) en un audio de 10 s."""
    x = np.zeros(SR * 10, np.float32)
    for a, b in voz:
        n = np.arange(int(a * SR), int(b * SR))
        x[n] = .3 * np.sin(n / 7)
    np.save(tmp_path / ".audio16k.npy", x)
    (tmp_path / "fuente.json").write_text(json.dumps({"video": "x.mp4", "cuadros": 300}))
    return tmp_path


def _palabras(tmp_path, ps):
    (tmp_path / "palabras.json").write_text(json.dumps([{"w": w, "s": s, "e": e} for w, s, e in ps]))


def test_corte_con_voz_y_sin_aire_se_detectan(tmp_path):
    c = _proyecto(tmp_path, [(1.0, 2.0), (4.0, 5.0)])
    _palabras(c, [("hola", 1.0, 2.0), ("información", 4.0, 4.9)])
    malo = {"cortes": [[0, .9], [4.95, 10]]}           # el fin cae con voz y a 0,05 s de la palabra
    errs = montaje.errores(malo, c)
    assert any("voz sonando" in e for e in errs) and any("deja al menos" in e for e in errs)
    bueno = {"cortes": [[0, .9], [2.1, 3.9], [5.1, 10]]}           # aire de 0,1 s por lado: la unión suma 0,2 s
    assert montaje.errores(bueno, c) == []


def test_claqueta_y_voz_fuera_de_camara_no_pueden_quedar(tmp_path):
    c = _proyecto(tmp_path, [(1.0, 1.6), (3.0, 4.0)])
    (c / "palabras.json").write_text(json.dumps([{"w": "acción.", "s": 1.0, "e": 1.6, "fuera": True}, {"w": "Si", "s": 3.0, "e": 3.4},
                                                 {"w": "quieres", "s": 3.4, "e": 4.0}]))
    errs = montaje.errores({"cortes": [[0, .8], [4.3, 10]]}, c)
    assert any("fuera de cámara" in e for e in errs)
    assert not any("fuera de cámara" in e for e in montaje.errores({"cortes": [[0, 2.5], [4.3, 10]]}, c))


def test_silencio_largo_dentro_del_final(tmp_path):
    c = _proyecto(tmp_path, [(1.0, 2.0), (3.5, 4.5)])
    _palabras(c, [("uno", 1.0, 2.0), ("dos", 3.5, 4.5)])
    assert any("silencio" in e for e in montaje.errores({"cortes": [[0, .9], [4.8, 10]]}, c))


def test_union_con_mas_aire_que_el_tope_se_rechaza(tmp_path):
    """07-nov (Pablo): «el editor no puede dejar silencios de más de 0,2 s». Antes pasaba hasta 0,7 s: 0,3 de una toma + 0,3 de la otra.
    13-nov (Pablo): 0,1 s más de aire en cada corte: el tope es 0,3 s."""
    c = _proyecto(tmp_path, [(1.0, 2.0), (4.0, 5.0)])
    _palabras(c, [("uno", 1.0, 2.0), ("dos", 4.0, 5.0)])
    assert montaje.SILENCIO_MAX_S == .3
    errs = montaje.errores({"cortes": [[0, .9], [2.3, 3.7], [5.1, 10]]}, c)         # 0,3 + 0,3 = 0,6 s de aire en la unión
    assert any("silencio" in e and "0.3" in e for e in errs), errs
    assert montaje.errores({"cortes": [[0, .9], [2.1, 3.9], [5.1, 10]]}, c) == []
    assert montaje.errores({"cortes": [[0, .9], [2.14, 3.86], [5.1, 10]]}, c) == []   # 0,14 + 0,14 de aire: antes se rechazaba, ahora respira
