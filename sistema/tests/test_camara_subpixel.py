"""La cámara recorta con decimales: un movimiento lento avanza sin escalones (brincos)."""
import numpy as np
from PIL import Image

from estudio import motor


def _centro(im):
    a = np.asarray(im.convert("L"), np.float64)
    return (a.sum(0) * np.arange(a.shape[1])).sum() / a.sum()


def test_movimiento_lento_sin_escalones():
    w, h = motor.W, motor.H
    base = Image.new("L", (w, h), 0)
    base.paste(255, (w // 2 - 40, h // 2 - 40, w // 2 + 40, h // 2 + 40))
    # borde suave para que el desplazamiento fraccionario sea medible
    from PIL import ImageFilter
    base = base.filter(ImageFilter.GaussianBlur(6))
    cw = w / 1.05
    xs = []
    for i in range(60):
        dx = 10 * i / 59
        xs.append(_centro(motor.recorte_fino(base, (w - cw) / 2 + dx, 0, (w + cw) / 2 + dx, h)))
    d = np.diff(xs)
    assert (d < 0).all(), "el centro debe avanzar sin retroceder"
    assert d.std() / abs(d.mean()) < 0.1, f"escalones: {d.std() / abs(d.mean()):.2f}"
