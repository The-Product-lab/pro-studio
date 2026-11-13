"""F1 de docs/PLANO-ESTILOS-PRO.md: el catálogo de Estilos Pro trae todos los estilos de Lemo, con nombre en español y póster."""
import json
from pathlib import Path

import pytest

from estudio import pro_catalogo

# Estas pruebas describen el laboratorio COMPLETO (los 66 estilos y sus muestras ya renderizadas). Una copia de referencia de Lemo
# (p. ej. `ESTUDIO BETA/referencias` en la Mac: 59 estilos, sin muestras) sirve para ver el catálogo, no para estas medidas.
_LAB = pro_catalogo.laboratorio()
pytestmark = pytest.mark.skipif(_LAB is None or not (_LAB / "muestras-lemo").is_dir(), reason="esta máquina no tiene el laboratorio-estilos completo")


def test_trae_todos_los_estilos_de_lemo():
    lab = pro_catalogo.laboratorio()
    en_disco = {p.name for p in (lab / "lemo-opuscar" / "styles").iterdir() if p.is_dir() and not p.name.startswith("_")}
    cat = pro_catalogo.catalogo()
    assert {e["slug"] for e in cat} == en_disco and len(cat) == len(en_disco) == 66


def test_nombres_en_espanol_posters_y_temas():
    nombres = set()
    for e in pro_catalogo.catalogo():
        assert e["nombre"].strip() and e["familia"].strip() and e["temas"], e["slug"]
        assert e["nombre"] not in nombres, e["nombre"]
        nombres.add(e["nombre"])
        assert Path(e["poster"]).is_file(), e["slug"]
        assert e["muestra"] is None or Path(e["muestra"]).is_file()
        assert e["probado"] == bool(e["muestra"])
        assert not any(c in e["familia"] for c in "&"), e["familia"]   # familias traducidas, no las del inglés crudo


def test_los_datos_no_dejan_estilos_sueltos():
    datos = json.loads(pro_catalogo.DATOS.read_text(encoding="utf-8"))
    assert set(datos["estilos"]) == {e["slug"] for e in pro_catalogo.catalogo()}
    assert set(datos["riesgos"]) <= set(datos["estilos"])


def test_art_deco_lleva_su_riesgo_y_engraving_su_muestra():
    por = {e["slug"]: e for e in pro_catalogo.catalogo()}
    assert "destello" in por["art-deco"]["riesgo"]
    assert por["engraving"]["muestra"].endswith("julian-animado.mp4")
    assert pro_catalogo.por_slug("no-existe") is None


def test_el_aviso_usa_lo_medido_o_lo_de_julian(tmp_path, monkeypatch):
    monkeypatch.setattr("estudio.config.PROYECTOS", tmp_path)
    a = pro_catalogo.aviso()
    assert not a["medido"] and a["minutos"] == pro_catalogo.MEDIDO_INICIAL["minutos"] and "minutos" in a["texto"]
    carpeta = tmp_path / "v1" / "pro-watercolor"
    carpeta.mkdir(parents=True)
    (carpeta / "costos.jsonl").write_text('{"segundos": 1800, "usd_equivalente": 4.5}\n{"segundos": 1800, "usd_equivalente": 1.5}\n')
    a = pro_catalogo.aviso()
    assert a["medido"] and a["minutos"] == 60 and "6.0" in a["texto"]
