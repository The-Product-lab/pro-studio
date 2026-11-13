"""Pruebas rápidas del motor (sin video, sin Claude y sin modelos). El Agente Editor agrega las suyas en tests/regresion/."""
import json
import subprocess
import sys

import pytest

from estudio import config, ia, motor, sonido


def test_ia_rechaza_haiku(tmp_path):
    with pytest.raises(ValueError):
        ia.llamar("hola", "haiku", tmp_path)


def test_subtitulos_en_bloques_de_maximo_3_y_cortan_en_pausas():
    palabras = [{"w": w, "s": i * .3, "e": i * .3 + .25} for i, w in enumerate("hoy nos encontramos en la feria.".split())]
    palabras.append({"w": "Y", "s": 3.0, "e": 3.2})
    bloques = motor.Subtitulos._auto(palabras)
    assert all(b - a <= 3 for a, b in bloques)
    assert bloques[-1] == [6, 7]  # la pausa larga y el punto abren un bloque nuevo


def test_tramos_de_voz_saltan_los_cortes():
    p = type("P", (), {"mapa": [i for i in range(90) if not 30 <= i < 45]})()
    assert sonido._tramos(p) == [(0.0, 1.0), (1.5, 3.0)]


def test_estilo_acepta_fuente_desconocida():
    assert motor.Estilo({"fuente": "NoExiste"}).fuente["regular"].startswith("PlayfairDisplay")


@pytest.mark.parametrize("ejemplo", sorted(p.name for p in (config.RAIZ / "estudio/director/ejemplo").glob("*.json")
                                            if p.name != "palabras.json" and not p.name.endswith(".palabras.json")) or ["(sin ejemplos vigentes)"])
def test_ejemplos_del_director_son_validos_con_escenas_ordenadas(ejemplo):
    if ejemplo.startswith("("):
        return
    sb = json.loads((config.RAIZ / "estudio/director/ejemplo" / ejemplo).read_text())
    t0s = [e["t0"] for e in sb["escenas"]]
    from estudio import validar
    assert t0s == sorted(t0s) and all(e["tipo"] in validar.TIPOS_ELEMENTO for e in sb["elementos"])


def test_filtros_hud_devuelven_imagen_del_mismo_tamano():
    import numpy as np
    from estudio import efectos
    rgb = np.random.default_rng(0).integers(0, 255, (64, 36, 3), dtype=np.uint8)
    est = motor.Estilo({})
    for nombre in efectos.FILTROS:
        assert efectos.filtrar(rgb, nombre, est).shape == rgb.shape


@pytest.mark.parametrize("ruta,codigo", [("estudio/agente/CONSTITUCION.md", 2), ("tests/test_basico.py", 2), ("estudio/motor.py", 0)])
def test_candado_del_agente(ruta, codigo):
    ev = json.dumps({"tool_name": "Edit", "tool_input": {"file_path": str(config.RAIZ / ruta)}})
    r = subprocess.run([sys.executable, "-m", "estudio.agente.proteger"], input=ev, text=True, cwd=config.RAIZ,
                       env={**__import__("os").environ, "ESTUDIO_AGENTE": "1"})
    assert r.returncode == codigo


def test_queda_la_ultima_version_de_una_frase_repetida():
    from estudio import repeticiones
    texto = [("hoy", 0.0), ("vamos", .3), ("a", .5), ("hablar", .6), ("de", 1.6), ("dinero", 1.8),   # 1ª versión (pausa larga)
             ("hoy", 3.0), ("vamos", 3.3), ("a", 3.5), ("hablar", 3.6), ("de", 3.8), ("cómo", 4.0), ("ganar", 4.2), ("dinero.", 4.5),
             ("y", 6.0), ("esto", 6.3), ("es", 6.5), ("otra", 6.7), ("cosa.", 6.9)]
    palabras = [{"w": w, "s": s, "e": s + .25} for w, s in texto]
    g = repeticiones.grupos(palabras)
    assert len(g) == 1 and g[0][-1]["t0"] == 3.0          # la que queda es la última
    assert repeticiones.faltas(palabras, []) and not repeticiones.faltas(palabras, [[0.0, 2.1]])
