"""La persona se UBICA (cara y cuerpo, 2 cuadros por segundo), no se recorta del fondo. Pablo, 11-nov: «el recorte frame por frame
únicamente sirve para poner cosas detrás de la persona. Pero yo no necesito recortar para saber dónde está la cara… elimina el tema de
recortes de todo». Caso real: 21 min recortando 4.764 cuadros de un video de 2,5 min antes de poder elegir estilo."""
import json
import re

import pytest

from estudio import config, ingesta, motor, persona, validar

CODIGO = config.RAIZ / "estudio"


def _tabla(tmp_path, cajas, paso=15):
    (tmp_path / persona.ARCHIVO).write_text(json.dumps({"version": persona.VERSION, "paso": paso, "cuadros": len(cajas) * paso, "cajas": cajas}))
    return persona.Tabla(tmp_path)


def test_la_cara_se_abre_con_aire_y_el_cuerpo_se_estima_debajo():
    cara, cuerpo = persona.cajas_de((500, 800, 600, 900))
    assert cara == (475.0, 775.0, 625.0, 925.0)
    assert cuerpo[0] < cara[0] and cuerpo[2] > cara[2] and cuerpo[1] == cara[1] and cuerpo[3] == config.H
    assert persona.cajas_de(None) == (None, None)
    pegada = persona.cajas_de((0, 0, 400, 400))[0]
    assert pegada[0] == 0 and pegada[1] == 0     # nunca sale del cuadro


def test_entre_dos_muestras_la_posicion_se_interpola(tmp_path):
    a, b = [[100, 100, 200, 200], [50, 100, 250, 1920]], [[400, 100, 500, 200], [350, 100, 550, 1920]]
    t = _tabla(tmp_path, [a, b])
    assert t.cara(0) == (100, 100, 200, 200) and t.cara(15) == (400, 100, 500, 200)
    assert t.cara(5)[0] == pytest.approx(200) and t.cara(999)[0] == 400      # pasado el final: la última muestra


def test_sin_persona_no_hay_cajas_y_una_muestra_vacia_no_inventa(tmp_path):
    assert persona.Tabla(tmp_path).cajas(10) == (None, None)       # proyecto sin persona.json
    assert persona.Tabla(None).cajas(0) == (None, None)
    t = _tabla(tmp_path, [None, [[1, 2, 3, 4], [1, 2, 3, 1920]], None])
    assert t.cajas(0) == (None, None) and t.cara(14) == (1, 2, 3, 4) and t.cajas(30) == (None, None)


def test_la_mas_grande_es_la_persona():
    chica, grande = (.9, 10, 10, 30, 30), (.7, 100, 100, 300, 300)
    assert persona._la_persona([chica, grande]) == grande[1:] and persona._la_persona([]) is None


def test_preparar_un_video_ubica_a_la_persona_y_no_crea_mascaras(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PROYECTOS", tmp_path)
    c = tmp_path / "p"
    c.mkdir()
    (c / "fuente.json").write_text(json.dumps({"video": "v.mp4", "original": "v.mov", "cuadros": 30, "hdr": False}))
    visto = []
    monkeypatch.setattr(persona, "ubicar", lambda carpeta, avance=print: visto.append(carpeta))
    ingesta.preparar_media("v.mov", "p", lambda m: None)
    assert visto == [c] and not (c / "alpha").exists()


def test_un_solo_lugar_ubica_a_la_persona():
    """Nada fuera de `persona.py` abre el detector, y en el código ya no queda con qué recortar a la persona del fondo."""
    for f in CODIGO.rglob("*.py"):
        s = f.read_text()
        if f.name != "persona.py":
            assert "CARAS_ONNX" not in s or f.name in ("config.py", "recursos.py", "doctor.py", "motor.py"), f.name
        if f.name != "archivo.py":   # las FOTOS del archivo sí se miran con RVM (saber si muestran a una persona)
            assert not re.search(r'"alpha"|ruta_alfa|_persona_pantalla|def recortar\(', s), f.name
    assert not hasattr(ingesta, "recortar") and not hasattr(motor, "ruta_alfa")


def test_la_persona_va_entera_o_no_va():
    assert validar.MODOS == {"pantalla": {"completa", "oculta"}} and validar.BASES == {"pantalla"}
    gramatica = (CODIGO / "director" / "GRAMATICA.md").read_text()
    assert not re.search(r'"silueta"|"neon"|modo": "recorte"|efecto sándwich', gramatica)


def test_el_cuadro_se_dibuja_sin_mascara(tmp_path):
    import numpy as np
    p = motor.Proyecto.__new__(motor.Proyecto)
    p.est, p.elementos, p.trazos, p.cajas, p.sb, p.dir = motor.Estilo({"base": "pantalla", "grano": 0}), [], [], [], {}, tmp_path
    p.subs = type("S", (), {"dibujar": staticmethod(lambda c, t: None)})()
    p.grano = [np.zeros((motor.H // 2, motor.W // 2), np.float32)] * 8
    p.mapa, p.escenas, p.n_src, p.camara_fija = list(range(60)), [{"t0": 0, "persona": {"modo": "completa"}}], 60, True
    toma = np.random.default_rng(3).integers(0, 255, (motor.H, motor.W, 3), dtype=np.uint8)
    assert np.array_equal(p.cuadro(10, toma), toma)      # persona completa, sin color ni grano: sale la toma tal cual
