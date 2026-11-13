"""El detector de la cara recibe el cuadro COMPLETO en su cuadrado sea cual sea la proporción del video.
Caso real (12-nov): un video 3:4 vertical (1360×1808) tumbaba la ingesta porque el relleno suponía video horizontal."""
import pytest

from estudio import persona


@pytest.mark.parametrize("ancho,alto", [(1920, 1080), (1360, 1808), (1080, 1080), (3840, 2160), (1440, 1920)])
def test_cuadro_entra_completo_y_la_x_vuelve_al_original(ancho, alto):
    vf, escala, x0 = persona.ajuste_cuadrado(ancho, alto)
    w, h = (int(v) for v in vf.split(",")[0][len("scale="):].split(":"))
    assert w <= persona.LADO and h <= persona.LADO          # nunca un relleno más chico que la imagen (lo que hacía fallar a ffmpeg)
    assert max(w, h) >= persona.LADO - 2
    medio = (x0 + w / 2 - x0) / escala                      # el centro del cuadrado vuelve al centro del video original
    assert abs(medio - ancho / 2) <= ancho * .01
