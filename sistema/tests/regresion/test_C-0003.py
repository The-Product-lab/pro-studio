"""C-0003 (Pablo, cine): «no me gustan los apoyos porque son muy poco dinámicos, no se siente cine».
Un apoyo (foto o clip) con `"acercar"` se acerca solo, lento y en una dirección, durante toda su vida (Ken Burns de cine),
sin pasar la vara de la cámara (.004 de zoom por cuadro), y a pantalla completa sigue cubriendo el cuadro sin dejar bordes."""
import numpy as np
from PIL import Image

from estudio import efectos, motor, validar


def test_curva_de_acercar_suave_y_en_un_sentido():
    k = [efectos.acercar_k(i / 100) for i in range(101)]
    assert k[0] == 0 and k[-1] == 1
    assert all(b >= a for a, b in zip(k, k[1:]))
    assert k[1] - k[0] < .001 and k[-1] - k[-2] < .001     # arranca y llega suave


def _foto(tmp_path, **extra):
    arr = np.zeros((1920, 1080, 3), np.uint8)
    arr[::40] = 255                                       # rayas: el acercamiento se nota en los píxeles
    Image.fromarray(arr).save(tmp_path / "f.png")
    d = {"id": "a", "tipo": "foto", "src": "f.png", "cubrir": True, "x": 540, "y": 960, "t0": 0.0, "t1": 3.0,
         "entra": "fundido", "dur": .01, "z": "atras", "muestra": "rayas", **extra}
    est = motor.Estilo({"base": "pantalla", "acento": "#A00E0D", "acento2": "#F5F4F0", "tinta": "#060707", "papel": "#F5F4F0"})
    return motor.Elemento(d, est, tmp_path)


def _cuadro(el, t):
    lienzo = Image.new("RGBA", (1080, 1920), (0, 0, 0, 255))
    el.dibujar(lienzo, t)
    return np.asarray(lienzo)


def test_el_apoyo_se_mueve_solo_y_sigue_cubriendo(tmp_path):
    quieto = _foto(tmp_path)
    assert (_cuadro(quieto, .1) == _cuadro(quieto, 2.9)).all()
    vivo = _foto(tmp_path, acercar=.08)
    a, b = _cuadro(vivo, .1), _cuadro(vivo, 2.9)
    assert not (a == b).all()                                 # se movió
    assert b.shape == (1920, 1080, 4) and (b[..., 3] == 255).all()


def test_compuerta_acercar_sin_brincos():
    base = {"id": "a", "tipo": "foto", "src": "x.png", "cubrir": True, "x": 540, "y": 960, "z": "atras", "muestra": "x"}
    assert not [e for e in validar.errores_acercar({**base, "t0": 0, "t1": 3, "acercar": .08})]
    assert validar.errores_acercar({**base, "t0": 0, "t1": .5, "acercar": .12})       # muy rápido: brinco
    assert validar.errores_acercar({**base, "t0": 0, "t1": 9, "acercar": .4})         # demasiado
