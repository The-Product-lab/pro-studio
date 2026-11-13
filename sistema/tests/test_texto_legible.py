"""Legibilidad (Pablo 10-nov, muestra de Prestiggio): «se están creando palabras muy pequeñas en las tomas de b-roll… y en pantalla completa, fondo sólido».
Dos pisos de defecto para los 13 estilos (reglas.json › global) y las cuatro reglas de mínimo que pasaron de bloquear a guía."""
import copy
import json
from pathlib import Path

from estudio import motor, validar

SB = json.loads((Path(__file__).parent / "fixtures" / "muestra-prestiggio" / "storyboard.json").read_text())


def _lineas(sb):
    for e in sb["elementos"]:
        if e["tipo"] in ("texto", "etiqueta"):
            for l in e.get("lineas", []):
                yield e, l


def test_la_muestra_de_prestiggio_falla_el_piso_de_legibilidad_y_pasa_al_subirlo():
    r = validar.reglas("prestiggio")
    assert r["texto_linea_min_px"] == validar.reglas("vox")["texto_linea_min_px"] == 48          # UN valor para todos (ya no solo Cine)
    err = validar._linea_minima(SB, r)
    assert err and "mínimo legible de 48 px" in err[0]                                          # «• MULTIPLICA» a 30 px, «• UN EDITOR TE COBRA» a 34
    arreglado = copy.deepcopy(SB)
    for _, l in _lineas(arreglado):
        if isinstance(l, dict):
            l["tam"] = max(l["tam"], 48)                                                        # lo que hace el director al leer el error
        else:
            l[1] = max(l[1], 48)
    assert validar._linea_minima(arreglado, r) == []


def test_el_contador_tambien_tiene_piso():
    r = {"texto_linea_min_px": 48}
    assert validar._linea_minima({"elementos": [{"id": "n", "tipo": "contador", "tam": 30}]}, r)
    assert validar._linea_minima({"elementos": [{"id": "n", "tipo": "contador", "tam": 120}]}, r) == []


def test_en_pantalla_completa_la_frase_principal_domina_el_cuadro():
    r = validar.reglas("prestiggio")
    assert 0 < r["pantalla_principal_ancho_min"] < 1
    sb = copy.deepcopy(SB)
    assert validar._pantalla_principal(sb, r) == []                                              # «dejan de» + «publicar» (grande) pasa
    solo_chica = copy.deepcopy(SB)
    solo_chica["elementos"] = [e for e in solo_chica["elementos"] if e["id"] != "n3"]            # la escena queda con «dejan de» a 80 px
    err = validar._pantalla_principal(solo_chica, r)
    assert err and err[0].startswith("pantalla completa (segundo 24.6") and "mínimo" in err[0]   # el error dice el número


def test_una_frase_armada_palabra_a_palabra_cuenta_como_una_linea():
    est = motor.Estilo({"base": "pantalla"})
    sb = {"escenas": [{"t0": 0}], "elementos": [
        {"id": "a", "tipo": "texto", "x": 300, "y": 500, "t0": 0, "t1": 2, "lineas": [{"texto": "tu", "rol": "display", "tam": 120}]},
        {"id": "b", "tipo": "texto", "x": 700, "y": 500, "t0": 0, "t1": 2, "lineas": [{"texto": "problema", "rol": "display", "tam": 120}]}]}
    junto = validar._linea_principal_px(sb, 0, 9, est)
    solo = validar._linea_principal_px({**sb, "elementos": sb["elementos"][:1]}, 0, 9, est)
    assert junto > solo * 2 and validar._linea_principal_px({"elementos": []}, 0, 9, est) is None


def test_hueco_texto_variedad_y_ritmo_ya_no_bloquean_son_guia():
    """«Déjalas que Opus decida»: salen de `errores` y se ofrecen como `consejos` (no frenan nada)."""
    sb = {"estilo": {"id": "vox", "base": "pantalla", "fuente": "Inter"}, "cortes": [], "escenas": [{"t0": 0.0}, {"t0": 1.0}], "elementos": [], "subtitulos": {"y": 1450}}
    assert not any(e.startswith(("ritmo:", "recursos:", "texto siempre:", "variedad")) for e in validar.errores(sb))
    assert any(e.startswith("ritmo:") for e in validar.consejos(sb))                              # una escena de 1 s: ritmo
    notas = " ".join(validar.reglas("vox")["nota"])
    assert "Opus decide" in notas                                                                  # la guía va en una frase, sin números


def test_un_solo_piso_para_franjas_y_cajas_hud():
    """El 48 vive solo en reglas.json; lo leen la compuerta, las franjas y las cajas HUD. Estilos Pro y subtítulos quedan FUERA (decisión de Pablo, 10-nov)."""
    from estudio import config
    piso = config.piso_texto_px()
    assert piso == validar.reglas(None)["texto_linea_min_px"] == 48
    assert motor.FRANJA_TAM_MIN == piso and motor.HUD_MONO_TAM >= piso
    assert validar._linea_minima({"elementos": [], "subtitulos": {"tam": 30}}, {"texto_linea_min_px": piso}) == []   # el subtítulo no entra en la regla


def test_los_consejos_le_llegan_a_opus_en_la_ronda_del_ojo(tmp_path, monkeypatch):
    from estudio import director, ia
    sb = {"estilo": {"id": "vox", "base": "pantalla", "fuente": "Inter"}, "cortes": [], "escenas": [{"t0": 0.0}, {"t0": 1.0}], "elementos": [], "subtitulos": {"y": 1450}}
    (tmp_path / "storyboard.json").write_text(json.dumps(sb))
    visto = {}
    monkeypatch.setattr(director, "_validar", lambda *a, **k: None)
    monkeypatch.setattr(director, "tiempos_revision", lambda c: [1.0])
    monkeypatch.setattr(director.motor, "vista_previa", lambda *a, **k: None)
    monkeypatch.setattr(ia, "llamar", lambda prompt, *a, **k: visto.setdefault("prompt", prompt) and {"result": "{}"})
    director.mirar(tmp_path, 1, avance=lambda *_: None)
    assert "Notas de guía" in visto["prompt"] and "no obligan" in visto["prompt"] and "ritmo:" in visto["prompt"]
