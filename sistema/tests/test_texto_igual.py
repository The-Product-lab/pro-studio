"""Los textos miden igual en cualquier equipo y, si uno no cabe al exportar, se acomoda solo (Pablo, 13-nov: «en otros Mac los textos
salen un poco más grandes, se salen del video y la compuerta frena el export»).
Causa medida: Pillow elige sola cómo compone el texto. Si el equipo tiene la librería `fribidi` (llega con Homebrew) usa la composición
avanzada (Raqm) y el mismo texto mide entre −4 % y +2 % de ancho; la Mac de Pablo no la tiene. `fuentes.abrir` fija la básica."""
import copy
import json
import re
from pathlib import Path

import pytest
from PIL import ImageFont

from estudio import config, doctor, fuentes, motor, validar

RAIZ = Path(__file__).resolve().parent.parent
GLASS = Path(__file__).parent / "fixtures" / "glass-nuevo-10nov"


def test_toda_letra_se_abre_por_la_unica_puerta():
    for f in sorted((RAIZ / "estudio").rglob("*.py")):
        if f.name != "fuentes.py":
            assert "ImageFont.truetype(" not in f.read_text(encoding="utf-8"), f"{f.name} abre una letra sin pasar por fuentes.abrir"
    assert "layout_engine=ImageFont.Layout.BASIC" in (RAIZ / "estudio" / "fuentes.py").read_text(encoding="utf-8")


def test_la_composicion_es_la_basica_tenga_o_no_fribidi_el_equipo():
    f = motor.fuente(motor.indice_fuentes()["Inter"]["regular"], 90, 700)
    assert f.layout_engine == ImageFont.Layout.BASIC
    assert motor.Estilo({}).font(80).layout_engine == ImageFont.Layout.BASIC


def test_los_textos_de_referencia_miden_lo_mismo_en_todos_los_equipos():
    assert fuentes.medidas_distintas() == []
    assert doctor.revisar_textos()["ok"] is True


def test_el_doctor_avisa_si_en_este_equipo_un_texto_mide_distinto(monkeypatch):
    monkeypatch.setattr(fuentes, "REFERENCIA", [("Inter", 90, "Hola mundo", 520.0)])
    r = doctor.revisar_textos()
    assert r["ok"] is False and "mide 506 y debe medir 520" in r["arreglo"]


def _glass_con_un_texto_que_no_cabe() -> tuple[dict, int]:
    """El diseño del banco (pasa la compuerta de textos) con un texto agrandado hasta salirse del cuadro."""
    sb = json.loads((GLASS / "storyboard.json").read_text())
    assert not [e for e in validar.errores(sb, GLASS) if any(a in e for a in validar.AJUSTABLE)]
    i = next(i for i, e in enumerate(sb["elementos"]) if isinstance(e, dict) and e.get("tipo") == "texto")
    for l in sb["elementos"][i]["lineas"]:
        l["tam"] = int(l["tam"] * 2.6)
    return sb, i


def test_un_texto_que_no_cabe_se_acomoda_solo():
    sb, i = _glass_con_un_texto_que_no_cabe()
    antes = copy.deepcopy(sb)
    assert [e for e in validar.errores(sb, GLASS) if f"elementos[{i}]" in e and "se sale de lo que se ve" in e]
    nuevo, tocados = validar.ajustar_textos(sb, GLASS)
    assert sb == antes and i in tocados                                   # no toca el original; dice cuáles cambió
    assert not [e for e in validar.errores(nuevo, GLASS) if any(a in e for a in validar.AJUSTABLE)]
    assert nuevo["elementos"][i]["lineas"][0]["tam"] < sb["elementos"][i]["lineas"][0]["tam"]   # se achicó la letra
    assert nuevo.get("subtitulos") == sb.get("subtitulos")                # el subtítulo no se toca aquí
    assert validar.ajustar_textos(nuevo, GLASS) == (nuevo, [])            # ya cabe: no se vuelve a tocar


def test_exportar_acomoda_el_texto_en_vez_de_tumbar_el_export(tmp_path, monkeypatch):
    sb, i = _glass_con_un_texto_que_no_cabe()
    for f in GLASS.iterdir():
        (tmp_path / f.name).write_bytes(f.read_bytes())
    (tmp_path / "storyboard.json").write_text(json.dumps(sb, ensure_ascii=False))
    from estudio import archivo, camara_check, persona

    class Sigue(Exception):
        """La compuerta dejó pasar: aquí empezaría el render de verdad."""

    def sigue(*a, **k):
        raise Sigue()
    monkeypatch.setattr(persona, "ubicar", lambda *a, **k: None)
    monkeypatch.setattr(archivo, "quitar_personas", lambda *a, **k: [])
    monkeypatch.setattr(camara_check, "supervisar", sigue)
    avisos = []
    try:
        motor.render(tmp_path, avance=avisos.append)
    except Sigue:
        pass
    except ValueError as e:   # lo que el banco ya traía de otras reglas sigue igual; del texto que no cabía, nada
        assert not any(a in str(e) for a in validar.AJUSTABLE), str(e)
    assert any(re.search(r"textos: \d+ no cabían", a) for a in avisos)
    guardado = json.loads((tmp_path / "storyboard.json").read_text())
    assert guardado["elementos"][i]["lineas"][0]["tam"] < sb["elementos"][i]["lineas"][0]["tam"]   # quedó escrito el ajuste
