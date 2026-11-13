"""El instalador nunca deja la pantalla quieta mientras baja algo grande."""
from estudio import recursos


def test_una_descarga_larga_da_senal_de_vida_y_se_calla_al_terminar():
    """10-nov: con internet lento el instalador pasaba minutos con la pantalla quieta y parecía colgado."""
    import time
    dicho = []
    with recursos.latido(dicho.append, cada_s=.03):
        time.sleep(.2)
    n = len(dicho)
    assert n >= 2 and all("sigue bajando" in m for m in dicho)
    time.sleep(.1)
    assert len(dicho) == n
