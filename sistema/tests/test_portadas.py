"""Puntos 7, 8 y 9 de la tanda 1 (Pablo, 07-nov): carátulas estandarizadas.
Grande = apoyo SIN persona; miniaturas = persona con subtítulos/imágenes/textos; el nombre del estilo siempre se lee.
Se prueba con los storyboards reales de cada estilo aprobado (director/ejemplo): el criterio es de código, no a mano por estilo."""
import json
import subprocess

import numpy as np
import pytest
from PIL import Image

from estudio import config, portadas
from estudio.director import AQUI, _obsoletos

EJEMPLOS = sorted(f for f in (AQUI / "ejemplo").glob("*.json") if not f.name.endswith("palabras.json") and f.name not in _obsoletos())


def _dur_final(sb):
    fin = max([e.get("t1", 0) for e in sb["elementos"]] + [e["t0"] for e in sb["escenas"]]) + 2
    return fin - sum(b - a for a, b in sb.get("cortes", []))


def _palabras(f):
    p = f.with_name(f.stem + ".palabras.json")
    return json.loads(p.read_text()) if p.exists() else None


@pytest.mark.parametrize("f", EJEMPLOS, ids=lambda f: f.stem)
def test_grande_es_apoyo_y_miniaturas_son_persona_con_texto(f):
    sb = json.loads(f.read_text())
    c = portadas.cuadros_de(sb, _dur_final(sb), _palabras(f))
    assert c["apoyo"] and all(portadas._sin_persona(sb, portadas._a_fuente(sb, t)) for t in c["apoyo"]), f.stem
    assert len(c["persona"]) == 3, f.stem
    for t in c["persona"]:   # ahí SÍ aparece la persona, con texto encima
        s = portadas._a_fuente(sb, t)
        assert not portadas._sin_persona(sb, s), f.stem
        assert any(e.get("tipo") in portadas.TEXTO for e in portadas._activos(sb, s)), f.stem


def test_prestiggio_tiene_su_pantalla_negra_con_la_palabra():
    f = AQUI / "ejemplo" / "prestiggio.json"
    sb = json.loads(f.read_text())
    g = portadas.cuadros_de(sb, _dur_final(sb), _palabras(f))["golpe"]
    assert g and portadas._golpe(sb, portadas._a_fuente(sb, g[0]))


def test_sin_apoyo_sin_persona_con_texto_es_error_no_relleno():
    sin_oculta = {"cortes": [], "escenas": [{"t0": 0}], "elementos": [{"tipo": "texto", "t0": 4, "t1": 20}]}
    with pytest.raises(ValueError, match="apoyo"):
        portadas.cuadros_de(sin_oculta, 22)
    sin_texto = {"cortes": [], "escenas": [{"t0": 0}, {"t0": 10, "persona": {"modo": "oculta"}}],
                 "elementos": [{"tipo": "foto", "t0": 11, "t1": 16}]}
    with pytest.raises(ValueError, match="persona con texto"):
        portadas.cuadros_de(sin_texto, 22)


def test_las_miniaturas_son_variadas():
    sb = {"cortes": [], "escenas": [{"t0": 0}],
          "elementos": [{"tipo": "texto", "t0": 4, "t1": 7}, {"tipo": "texto", "t0": 8, "t1": 11},
                        {"tipo": "foto", "t0": 12, "t1": 15}, {"tipo": "texto", "t0": 12, "t1": 15},
                        {"tipo": "texto", "t0": 16, "t1": 19}]}
    ts = portadas.momentos(sb, 22, n=3, quien="persona")
    assert any(12 <= t < 15 for t in ts) and any(4 <= t < 7 or 8 <= t < 11 or 16 <= t < 19 for t in ts)


def test_sin_voz_no_vale_para_miniatura():
    sb = {"cortes": [], "escenas": [{"t0": 0}],
          "elementos": [{"tipo": "texto", "t0": 4, "t1": 20}]}
    ts = portadas.momentos(sb, 22, n=3, quien="persona", palabras=[{"w": "x", "s": 11, "e": 12}])
    assert ts and all(11 <= t <= 12.2 for t in ts)


def test_nombre_legible_sobre_cualquier_fondo():
    """Prestiggio y Vox (Pablo): el nombre no se leía sobre un motion cargado. Fondo claro y con ruido → igual pasa el mínimo."""
    rng = np.random.default_rng(3)
    for base in (np.full((300, 700, 3), 235, np.uint8), rng.integers(0, 255, (300, 700, 3), dtype=np.uint8)):
        im = Image.fromarray(base).convert("RGBA")
        caja = (40, 80, 600, 220)
        assert portadas.contraste(im, caja) < portadas.LEGIBLE_MIN
        portadas.asegurar_legible(im, caja)
        assert portadas.contraste(im, caja) >= portadas.LEGIBLE_MIN


def test_zona_libre_gana_a_la_cargada():
    rng = np.random.default_rng(1)
    a = np.zeros((400, 400, 3), np.uint8)
    a[200:] = rng.integers(0, 255, (200, 400, 3), dtype=np.uint8)
    im = Image.fromarray(a)
    assert portadas.enredo(im, (0, 0, 400, 200)) < portadas.enredo(im, (0, 200, 400, 400))


def test_portada_completa_de_punta_a_punta(tmp_path):
    ffmpeg, _ = config.ffmpeg()
    subprocess.run([ffmpeg, "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=360x640:rate=10:duration=24", "-pix_fmt", "yuv420p",
                    str(tmp_path / "final.mp4")], check=True)
    sb = {"cortes": [], "escenas": [{"t0": 0}, {"t0": 10, "persona": {"modo": "oculta"}}, {"t0": 17}],
          "elementos": [{"tipo": "texto", "t0": 3, "t1": 9}, {"tipo": "foto", "t0": 11, "t1": 16}, {"tipo": "texto", "t0": 18, "t1": 23}]}
    (tmp_path / "storyboard.json").write_text(json.dumps(sb))
    out = portadas.portada("prestiggio", tmp_path, tmp_path / "p.jpg")
    assert Image.open(out).size == (portadas.W, portadas.H)
    assert all(11 <= t < 16 for t in portadas.cuadros_de(sb, 24)["apoyo"])


def test_las_vistas_de_personalizar_son_persona_y_apoyo():
    """Punto 10: izquierda = la persona con sus textos; derecha = apoyo a pantalla completa (sin persona)."""
    sb = {"cortes": [], "escenas": [{"t0": 0}, {"t0": 10, "persona": {"modo": "oculta"}}, {"t0": 17}],
          "elementos": [{"tipo": "texto", "t0": 3, "t1": 9}, {"tipo": "foto", "t0": 11, "t1": 16}, {"tipo": "texto", "t0": 18, "t1": 23}]}
    persona, apoyo = portadas.previa(sb, 24)
    assert not portadas._sin_persona(sb, persona) and portadas._sin_persona(sb, apoyo)


def test_el_apoyo_se_ve_aunque_falten_miniaturas_de_persona():
    """Punto 5 (tanda 3): con menos de 3 cuadros de persona con texto, `cuadros_de` fallaba y la vista caía en un cuadro cualquiera;
    ahora el apoyo sin persona se muestra igual."""
    sb = {"cortes": [], "escenas": [{"t0": 0}, {"t0": 10, "persona": {"modo": "oculta"}}, {"t0": 17}],
          "elementos": [{"tipo": "texto", "t0": 3, "t1": 6}, {"tipo": "texto", "t0": 11, "t1": 16}]}
    with pytest.raises(ValueError):
        portadas.cuadros_de(sb, 24)
    persona, apoyo = portadas.previa(sb, 24)
    assert portadas._sin_persona(sb, apoyo) and not portadas._sin_persona(sb, persona)
