"""F4 del plano T-0193 (reintento sucio): derivar borra el intento previo y deja la carpeta limpia para el director."""
import json

import pytest

from estudio import config, ingesta


@pytest.fixture
def proyectos(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PROYECTOS", tmp_path)
    base = tmp_path / "base"
    base.mkdir(parents=True)
    (base / "persona.json").write_text('{"version": 2, "paso": 15, "cuadros": 30, "cajas": []}')
    (base / "fuente.json").write_text('{"video": "v.mp4", "cuadros": 30}')
    (base / "palabras.json").write_text("[]")
    return tmp_path


def _intento_sucio(c):
    (c / "arte").mkdir(parents=True, exist_ok=True)
    (c / "arte" / "foto.png").write_bytes(b"png")
    (c / "storyboard.json").write_text(json.dumps({"cortes": [[1, 2]]}))
    (c / "arte.json").write_text('[{"id": "foto"}]')
    (c / "costos.jsonl").write_text('{"usd": 1.5}\n')
    (c / "_guia").mkdir()
    (c / "_guia" / "GRAMATICA.md").write_text("g")


def test_derivar_borra_el_intento_y_el_director_parte_sin_nada(proyectos):
    c = proyectos / "lote"
    _intento_sucio(c)
    ingesta.derivar("base", "lote")
    for n in ("storyboard.json", "arte.json", "costos.jsonl", "_guia"):
        assert not (c / n).exists(), n
    assert (c / "arte" / "foto.png").exists()               # las imágenes pagadas se quedan
    assert not (c / ".intentos").exists()                   # sin copias: nada que se acumule


def test_derivar_sin_intento_previo_no_deja_nada_extra(proyectos):
    ingesta.derivar("base", "nuevo")
    assert not (proyectos / "nuevo" / ".intentos").exists()
    assert (proyectos / "nuevo" / "palabras.json").exists()


def test_reintentos_seguidos_no_acumulan_nada(proyectos):
    c = proyectos / "lote"
    _intento_sucio(c)
    for _ in range(3):
        ingesta.derivar("base", "lote")
        _intento_sucio(c)
    ingesta.derivar("base", "lote")
    assert sorted(p.name for p in c.iterdir()) == ["arte", "fuente.json", "palabras.json", "persona.json"]


def test_archivo_vacio_no_cuenta_como_intento(proyectos):
    c = proyectos / "lote"
    c.mkdir()
    (c / "storyboard.json").write_text("")
    assert ingesta.limpiar_intento(c) is False
    assert not (c / "storyboard.json").exists()


def test_derivar_lleva_la_posicion_de_la_persona_del_base(proyectos):
    c = proyectos / "lote"
    c.mkdir()
    (c / "persona.json").write_text("vieja")
    ingesta.derivar("base", "lote")
    assert (c / "persona.json").read_text() == (proyectos / "base" / "persona.json").read_text()   # siempre la del base actual
    assert not (c / "alpha").exists()   # ya no hay máscaras: a la persona no se la recorta


def test_derivar_sobre_el_mismo_base_se_niega_sin_borrar_nada(proyectos):
    (proyectos / "base" / "storyboard.json").write_text("{}")
    with pytest.raises(ValueError, match="mismo"):
        ingesta.derivar("base", "base")
    assert (proyectos / "base" / "storyboard.json").exists()
