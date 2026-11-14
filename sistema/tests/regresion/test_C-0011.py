"""C-0011 (Pablo, 07-nov): revisión final OBLIGATORIA del corte terminado. Se mide el audio del video renderizado: silencios de
más de 0,2 s, voz de fondo baja sostenida y pedazos repetidos (falso arranque o CTA dos veces). Si falla, el machote no es apto."""
import numpy as np

from estudio import revisar_corte as r

SR = r.SR


def _audio(tramos):
    """tramos = [(segundos, dB)]: ruido de tono a ese nivel (−120 = silencio)."""
    out = []
    for s, db in tramos:
        n = int(s * SR)
        a = 10 ** (db / 20) * np.sqrt(2)
        out.append(a * np.sin(2 * np.pi * 220 * np.arange(n) / SR) if db > -100 else np.zeros(n))
    return np.concatenate(out).astype(np.float32)


def test_silencio_largo_bloquea_y_voz_baja_queda_como_aviso(monkeypatch):
    x = _audio([(2, -17), (.5, -120), (2, -17), (.6, -33), (2, -17)])
    monkeypatch.setattr(r, "_audio", lambda v: x)
    i = r.revisar("x.mp4", palabras=[])
    assert not i["ok"] and "silencio" in {f["tipo"] for f in i["fallas"]}
    assert "voz_de_fondo" in {f["tipo"] for f in i["avisos"]}           # se informa, pero no bloquea (es la respiración)


def test_pausa_corta_pasa(monkeypatch):
    x = _audio([(2, -17), (.15, -120), (2, -17)])
    monkeypatch.setattr(r, "_audio", lambda v: x)
    assert r.revisar("x.mp4", palabras=[])["ok"]


def _p(texto, t0=0.0, paso=.3):
    return [{"w": w, "s": t0 + k * paso, "e": t0 + k * paso + .25} for k, w in enumerate(texto.split())]


def test_falso_arranque_y_cta_doble_son_repeticion():
    assert r.repeticiones(_p("y lo mejor de todo es que y lo mejor de todo es que claude se entrena"))
    assert r.repeticiones(_p("y todo y todo directamente desde tu computador"))
    assert r.repeticiones(_p("si quieres aprender a editar videos te enseño en el taller si quieres aprender a editar videos comenta"))


def test_dos_menciones_del_guion_no_son_repeticion():
    assert r.repeticiones(_p("todos hablan de como editar videos con claude pero nadie te muestra el paso a paso si quieres "
                             "aprender a editar videos con claude comenta")) == []
