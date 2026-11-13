"""C-0002 (Pablo): «usa un efecto de zoom in zoom out juntos que es feo, brusco sin calma, no tiene desaceleración y aceleración».
La entrada `zoom` debe ser corta en amplitud, durar lo bastante y acelerar/desacelerar (velocidad ~0 al empezar y al asentarse)."""
from estudio import efectos


def test_zoom_de_entrada_con_calma():
    assert efectos.ZOOM_ENTRADA_DUR >= .6 and efectos.ZOOM_ENTRADA_AMP <= .08
    k = [efectos.zoom_entrada_k(i / 100) for i in range(101)]
    assert k[0] == 1 and k[-1] == 0
    assert all(a >= b for a, b in zip(k, k[1:]))          # una sola dirección, nunca va y viene
    assert k[0] - k[2] < .002 and k[-3] - k[-1] < .002    # arranca y llega suave (acelera y desacelera)
    paso_max = max(a - b for a, b in zip(k, k[1:])) * efectos.ZOOM_ENTRADA_AMP
    cuadros = efectos.ZOOM_ENTRADA_DUR * 30
    assert paso_max * 100 / cuadros < .004                 # nunca más de .004 de zoom por cuadro (misma vara que la cámara)
