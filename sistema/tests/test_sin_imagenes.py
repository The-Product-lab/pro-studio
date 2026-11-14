"""Cada estilo tiene dos variantes: con imágenes o sin imágenes. Caso real (Pablo, 11-nov): el director diseñó con 3 imágenes, ninguna
llegó y las piezas se quitaron después. Ahora se decide ANTES de dirigir, con aviso, y el director resuelve sin ellas desde el principio."""
from estudio import imagenes


def test_sin_generador_se_dirige_sin_imagenes_y_se_avisa(monkeypatch):
    monkeypatch.setattr(imagenes, "conector", lambda: None)
    avisos = []
    assert imagenes.disponibles(True, avisos.append) is False
    assert len(avisos) == 1 and "SIN imágenes" in avisos[0] and "Conectores" in avisos[0]


def test_con_generador_se_respeta_lo_que_eligio_la_persona(monkeypatch):
    monkeypatch.setattr(imagenes, "conector", lambda: imagenes.HF)
    avisos = []
    assert imagenes.disponibles(True, avisos.append) is True
    assert imagenes.disponibles(False, avisos.append) is False and avisos == []


def test_sin_imagenes_elegido_no_consulta_el_conector(monkeypatch):
    monkeypatch.setattr(imagenes, "conector", lambda: (_ for _ in ()).throw(AssertionError("no debe consultarse")))
    assert imagenes.disponibles(False) is False


def test_otro_conector_de_nombre_parecido_sin_autorizar_no_tapa_al_conectado():
    listado = ("claude.ai Higgsfield AI: https://a/mcp - ! Needs authentication\n"
               "claude.ai higgsfield: https://b/mcp - ✔ Connected\n")
    assert imagenes.prefijo_en(listado) == "mcp__claude_ai_higgsfield__"
    assert "nunca un aviso de la sesión" in imagenes.PROMPT


def test_la_pantalla_manda_la_variante_elegida():
    from estudio import config
    js = (config.RAIZ / "app" / "app.js").read_text()
    assert "imagenes: conImagenes" in js and "imagenes: true" not in js
    assert 'id="conImg"' in (config.RAIZ / "app" / "index.html").read_text()
