"""Sonido ordenado (docs/PLANO-SONIDO.md). Casos reales: la copia de prestiggio saturaba (un pop por elemento)."""
from types import SimpleNamespace

import numpy as np

from estudio import sonido, validar


class _E:
    def __init__(s, t0, tipo, tam=0):
        s.t0, s.entra = t0, "pop"
        s.d = {"tipo": tipo, "lineas": [{"texto": "hola", "tam": tam}]}


def _p(elementos, escenas=None, estilo=None, **sb):
    escenas = escenas or [{"t0": 0}]
    return SimpleNamespace(sb={"estilo": estilo or {}, **sb}, escenas=escenas, elementos=elementos, trazos=[],
                           mapa=list(range(30 * 20)), dir=None)


def test_no_suena_un_pop_por_cada_elemento():
    """Diez etiquetas chicas y textos secundarios en 2 s: no suenan; el texto principal y el corte sí."""
    els = [_E(1 + i * .1, "etiqueta", 40) for i in range(10)] + [_E(3.0, "texto", 140)]
    ev = sonido.eventos(_p(els, escenas=[{"t0": 0}, {"t0": 5.0}]))
    cats = sorted(e[1] for e in ev)
    assert cats == ["corte", "texto"]


def test_densidad_maxima_y_separacion():
    ev = [(1.0 + i * .05, "texto", .6, 2) for i in range(12)] + [(1.2, "corte", .85, 3)]
    q = sonido.depurar(ev)
    ts = [e[0] for e in q]
    assert min(b - a for a, b in zip(ts, ts[1:])) >= sonido.SEPARACION_MIN
    assert any(e[1] == "corte" for e in q)                 # lo importante se queda
    assert max(sum(1 for y in ts if x <= y < x + 1) for x in ts) <= sonido.MAX_POR_SEGUNDO


def test_el_efecto_culmina_en_el_evento():
    """El sonido que causa algo va antes de la reacción: el pico cae en el cuadro del evento, no después."""
    p = _p([], escenas=[{"t0": 0}, {"t0": 5.0}])
    inf = {}
    out = sonido.efectos(p, 10, inf)
    env = np.convolve(np.abs(out), np.ones(240) / 240, "same")
    pico = env[int(4 * sonido.SR):int(6 * sonido.SR)].argmax() / sonido.SR + 4
    assert abs(pico - 5.0) < .06 and inf["efectos"] == 1


def test_paleta_cine_calla_los_textos_y_la_compuerta_valida_la_paleta():
    p = _p([_E(2.0, "texto", 140)], estilo={"sonido_paleta": "cine"})
    inf = {}
    sonido.efectos(p, 5, inf)
    assert inf["efectos"] == 0
    assert validar._paleta_sonido({"estilo": {"sonido_paleta": "inventada"}})
    assert not validar._paleta_sonido({"estilo": {"sonido_paleta": "papel"}})


def test_lo_escrito_a_mano_se_respeta():
    p = _p([], sonido=[{"t": 1.0, "tipo": "pop"}, {"t": 1.05, "tipo": "click"}])
    assert len(sonido.depurar([(t, ti, g, i) for t, ti, g, i in sonido.eventos(p)])) == 2
