"""F2/F3 de docs/PLANO-LEMO-APOYOS.md: el director con el preset «lemo» le MARCA tramos a Lemo, sin tope y sin decirle cómo (Pablo,
12-nov: «Lemus puede hacer de todo, pero pues no es una camisa de fuerza»), y la compuerta acepta el clip pedido antes de que exista.
Nunca llama a Claude: la «IA» guarda el prompt y corta ahí."""
import json

import pytest

from estudio import director, ia, lemo_apoyos, pro, validar


class Cortar(Exception):
    pass


@pytest.fixture
def carpeta(tmp_path, monkeypatch):
    lemo = tmp_path / "lemo-lib"
    (lemo / "styles" / "engraving").mkdir(parents=True)
    (lemo / "styles" / "engraving" / "STYLE.md").write_text("estilo de prueba")
    (lemo / "styles" / "engraving" / "style.json").write_text(json.dumps({"en": "Engraving", "line": "una línea", "uses": ["Historia"]}))
    monkeypatch.setattr(pro, "LEMO", lemo)
    c = tmp_path / "v1"
    c.mkdir()
    (c / "palabras.json").write_text(json.dumps([{"w": "hola", "s": .2, "e": .6}]))
    (c / "preferencias.json").write_text(json.dumps({"guion_aprobado": True}))
    monkeypatch.setattr(director, "contexto", lambda *a: None)
    return c


def _prompt(carpeta, monkeypatch, estilo):
    visto = []

    def falsa(prompt, *a, **k):
        visto.append(prompt)
        raise Cortar
    monkeypatch.setattr(ia, "llamar", falsa)
    with pytest.raises(Cortar):
        director.dirigir(carpeta, lemo_apoyos.elegir(carpeta, estilo), True, lambda m: None)
    return visto[0]


def test_el_director_le_marca_tramos_a_lemo_sin_tope(carpeta, monkeypatch):
    p = _prompt(carpeta, monkeypatch, "lemo:engraving")
    assert "Tramos para Lemo" in p and "sin tope" in p and "camisa de fuerza" in p and "Engraving" in p
    assert "máximo" not in p.split("## Tramos para Lemo")[1].split("##")[0]      # ya no le limita la cantidad
    assert '"prompt"' not in p.split("## Tramos para Lemo")[1].split("##")[0]    # ni le pide imágenes a Higgsfield


def test_otro_estilo_sigue_pidiendo_arte_con_tope(carpeta, monkeypatch):
    p = _prompt(carpeta, monkeypatch, "swiss")
    assert "Tramos para Lemo" not in p and "Arte a medida" in p and "máximo" in p


def test_el_clip_pedido_pasa_la_compuerta_antes_de_existir(carpeta):
    sb = {"elementos": [{"id": "a1", "tipo": "clip", "src": "arte/a1.mp4", "cubrir": True, "t0": 3.0, "t1": 6.0}]}
    falta = "el clip arte/a1.mp4 no existe"
    assert not any(falta in e for e in validar.errores(sb, carpeta, imagenes_pendientes=True))
    assert any(falta in e for e in validar.errores(sb, carpeta, imagenes_pendientes=False))


def test_el_ejemplo_de_lemo_usa_el_guion_de_maestro_calma_sin_copiarlo():
    """`estudio verificar` › copias idénticas: el guion del ejemplo vive una sola vez y el director lo encuentra igual."""
    assert director._palabras_del_ejemplo("lemo").name == "maestro-calma.palabras.json"
    assert not (director.AQUI / "ejemplo" / "lemo.palabras.json").exists()
    assert director._palabras_del_ejemplo("swiss").name == "swiss.palabras.json"
