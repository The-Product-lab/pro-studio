"""Color: el video se usa tal cual; el único color es un LUT elegido, y se aplica en UN solo lugar (`color.cubo` + `color.filtro`)."""
import numpy as np

from estudio import config, color


def test_sin_lut_el_cuadro_sale_igual_al_original(tmp_path):
    assert color.cubo(tmp_path, None) is None and color.cubo(tmp_path, {}) is None
    assert color.cubo(tmp_path, {"ajustes": {k: 0 for k in color.AJUSTES}}) is None
    assert color.filtro(None) == ""   # sin cubo no se agrega ningún filtro: ffmpeg no toca el color


def test_con_lut_todos_los_caminos_usan_la_misma_funcion(tmp_path):
    look = next(l for l in color.looks() if l["id"].startswith("natural-"))
    c = color.cubo(tmp_path, {"look": look["id"], "fuerza": 1.0})
    assert c and c.exists() and "lut3d" in color.filtro(c)
    n, tabla = color._leer_cubo(c)
    gris = np.array([[.4, .4, .4]])
    assert not np.allclose(color._aplicar_cubo(n, tabla, gris), gris)   # el LUT cambia el color
    # una sola regla: ningún otro módulo arma su propio lut3d; todos llaman a color.filtro
    fuera = [p.name for p in (config.RAIZ / "estudio").rglob("*.py") if p.name != "color.py" and "lut3d" in p.read_text()]
    assert fuera == []
    usan = [p.name for p in (config.RAIZ / "estudio").rglob("*.py") if "color.filtro(" in p.read_text()]
    assert {"motor.py", "machote.py"} <= set(usan)


def test_no_queda_nada_de_perfiles_log():
    for p in (config.RAIZ / "estudio").rglob("*.py"):
        t = p.read_text()
        for viejo in ("PerfilNoSoportado", "perfil_cambia", "entrada_pedida", "color.detectar", "entrada_guardada"):
            assert viejo not in t, (p.name, viejo)
    assert not (config.RAIZ / "librerias" / "color" / "perfiles.json").exists()
