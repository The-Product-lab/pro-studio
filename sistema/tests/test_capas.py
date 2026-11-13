"""Editor por capas (estudio/capas.py): cada operación cambia solo su pieza, valida, deja deshacer y dice qué tramos tocó."""
import json

import pytest

from estudio import camara, capas

CASO = "cine-c8867"


@pytest.fixture
def proyecto(banco, monkeypatch):
    """Copia del caso real; la compuerta se reemplaza por una barata (una prueba usa la de verdad)."""
    monkeypatch.setattr(capas, "_errores", lambda sb, carpeta: [])
    return banco(CASO)


def _sb(p):
    return json.loads((p / "storyboard.json").read_text())


def _el(sb, id_):
    return next(e for e in sb["elementos"] if e["id"] == id_)


def test_vista_de_un_segundo(proyecto):
    sb, pal = _sb(proyecto), json.loads((proyecto / "palabras.json").read_text())
    v = capas.vista(sb, pal, 13.0)
    assert [e["id"] for e in v["elementos"]] == ["k1"]
    assert v["elementos"][0]["texto"] == "lo entrenas" and v["elementos"][0]["tam"] == 120
    assert v["subtitulos"]["palabras"] and v["estilo"]["id"] == "cine"
    assert v["t_final"] == round(capas.salida_de(sb, 13.0), 2)


def test_tiempo_final_y_fuente_son_inversos(proyecto):
    sb = _sb(proyecto)
    for t in (4.5, 13.0, 30.2):
        assert capas.fuente_de(sb, capas.salida_de(sb, t)) == pytest.approx(t)


def test_texto_editar_cambia_solo_ese_texto(proyecto):
    antes = _sb(proyecto)
    r = capas.aplicar(proyecto, [{"op": "texto.editar", "id": "k1", "texto": "lo entrenás"}])
    assert r["ok"] and r["cambios"][0]["antes"] == "lo entrenas"
    despues = _sb(proyecto)
    assert _el(despues, "k1")["lineas"][0]["texto"] == "lo entrenás"
    despues["elementos"][despues["elementos"].index(_el(despues, "k1"))] = _el(antes, "k1")
    assert despues == antes                       # nada más cambió
    assert isinstance(r["tramos"], list) and 0 < len(r["tramos"]) < 8


def test_escalar_y_estilo_de_texto(proyecto):
    capas.aplicar(proyecto, [{"op": "escalar", "id": "k1", "factor": 1.5}, {"op": "texto.estilo", "id": "k1", "color": "#FFE800", "peso": 700}])
    ln = _el(_sb(proyecto), "k1")["lineas"][0]
    assert (ln["tam"], ln["color"], ln["peso"]) == (180, "#FFE800", 700)


def test_mover_tiempo_y_borrar(proyecto):
    capas.aplicar(proyecto, [{"op": "mover", "id": "k1", "dy": -50}, {"op": "tiempo", "id": "k1", "corrimiento": 0.5}])
    e = _el(_sb(proyecto), "k1")
    assert (e["y"], e["t0"], e["t1"]) == (310, 13.0, 14.7)
    capas.aplicar(proyecto, [{"op": "borrar", "id": "k1"}])
    assert all(x["id"] != "k1" for x in _sb(proyecto)["elementos"])


def test_borrar_un_elemento_se_lleva_sus_trazos(proyecto):
    sb = _sb(proyecto)
    sb["trazos"] = [{"tipo": "rect", "sobre": "k1", "t0": 12.6, "dur": .3, "t1": 13.2}, {"tipo": "linea", "puntos": [[1, 1], [2, 2]], "t0": 1, "dur": .3, "t1": 2}]
    (proyecto / "storyboard.json").write_text(json.dumps(sb))
    capas.aplicar(proyecto, [{"op": "borrar", "id": "k1"}])
    assert [t["tipo"] for t in _sb(proyecto)["trazos"]] == ["linea"]
    capas.deshacer(proyecto)
    assert len(_sb(proyecto)["trazos"]) == 2


def test_agregar_texto_y_deshacer_un_paso(proyecto):
    original = (proyecto / "storyboard.json").read_text()
    r = capas.aplicar(proyecto, [{"op": "agregar_texto", "texto": "Claude", "t0": 20.0, "t1": 21.0}])
    assert r["ok"] and _el(_sb(proyecto), "cap1")["lineas"][0]["texto"] == "Claude"
    assert capas.deshacer(proyecto)["ok"]
    assert (proyecto / "storyboard.json").read_text() == original
    assert not capas.deshacer(proyecto)["ok"]     # un solo paso


def test_subtitulos_palabra_ocultar_y_golpe(proyecto, monkeypatch):
    pal = json.loads((proyecto / "palabras.json").read_text())
    r = capas.aplicar(proyecto, [{"op": "camara.golpe", "t": 12.0}])   # la cámara es fija (regla del 11-nov): se contesta, no se anota
    assert not r["ok"] and "fija" in r["errores"][0]
    monkeypatch.setattr(camara, "fija", lambda: False)   # la operación sigue existiendo para cuando la regla se quite
    capas.aplicar(proyecto, [{"op": "subtitulo.palabra", "indice": 5, "texto": "Claude"}, {"op": "subtitulo.ocultar", "t0": 30, "t1": 32},
                             {"op": "camara.golpe", "t": 12.0}])
    assert json.loads((proyecto / "palabras.json").read_text())[5]["w"] == "Claude" != pal[5]["w"]
    sb = _sb(proyecto)
    assert [30, 32] in sb["subtitulos"]["ocultar"] and 12.0 in sb["punch"]
    r = capas.aplicar(proyecto, [{"op": "camara.quitar", "t": 12.1}])
    assert r["ok"] and 12.0 not in _sb(proyecto)["punch"]
    capas.deshacer(proyecto)
    capas.deshacer(proyecto)
    assert json.loads((proyecto / "palabras.json").read_text())[5]["w"] == "Claude"   # deshacer es de un paso: el segundo no tenía nada que volver


def test_color_y_sonido(proyecto):
    capas.aplicar(proyecto, [{"op": "color.ajuste", "clave": "contraste", "delta": 0.2}, {"op": "sonido.volumen", "valor": 0.1}])
    est = _sb(proyecto)["estilo"]
    assert est["color"]["ajustes"]["contraste"] == 0.2 and est["sfx"] == 0.1
    r = capas.aplicar(proyecto, [{"op": "sonido.volumen", "que": "musica", "valor": 0.1}])
    assert not r["ok"] and "música" in r["errores"][0]


def test_corte_quitar_y_restaurar_palabras(proyecto):
    sb, pal = _sb(proyecto), json.loads((proyecto / "palabras.json").read_text())
    i = next(i for i, p in enumerate(pal) if p["s"] > 20 and not any(a <= p["s"] <= b for a, b in sb["cortes"]))
    r = capas.aplicar(proyecto, [{"op": "corte.quitar", "indices": [i]}])
    assert r["ok"] and [pal[i]["s"], pal[i]["e"]] in _sb(proyecto)["cortes"]
    assert r["tramos"] == "todos" or r["tramos"]
    r = capas.aplicar(proyecto, [{"op": "corte.restaurar", "indices": [i]}])
    assert r["ok"] and _sb(proyecto)["cortes"] == sb["cortes"]


def test_operacion_invalida_no_cambia_nada(proyecto):
    antes = (proyecto / "storyboard.json").read_text()
    for op in ({"op": "borrar", "id": "no-existe"}, {"op": "escalar", "id": "k1", "factor": 99}, {"op": "inventada"},
               {"op": "mover", "id": "k1"}, {"op": "texto.editar", "id": "k1", "texto": "  "}, {"op": "tiempo", "id": "k1", "t1": 1}):
        r = capas.aplicar(proyecto, [{"op": "mover", "id": "k1", "dx": 5}, op])     # la primera sí vale: todo o nada
        assert not r["ok"] and r["errores"], op
    assert (proyecto / "storyboard.json").read_text() == antes
    assert not (proyecto / capas.DESHACER).exists()


def test_la_compuerta_de_validar_rechaza_y_no_toca_nada(banco):
    p = banco(CASO)                                  # validar.py de verdad
    antes = (p / "storyboard.json").read_text()
    r = capas.aplicar(p, [{"op": "texto.estilo", "id": "k1", "tam": 12}])
    assert not r["ok"] and any("mínimo legible" in e for e in r["errores"])
    assert (p / "storyboard.json").read_text() == antes and not (p / capas.DESHACER).exists()
    assert capas.aplicar(p, [{"op": "texto.editar", "id": "k1", "texto": "lo entrenas bien"}])["ok"]   # un cambio sano sí pasa


def test_catalogo_cubre_el_plano():
    esperadas = {"texto.editar", "texto.estilo", "mover", "escalar", "tiempo", "borrar", "agregar_texto", "subtitulo.palabra",
                 "subtitulo.ocultar", "camara.golpe", "camara.quitar", "color.ajuste", "sonido.volumen", "corte.quitar", "corte.restaurar"}
    assert set(capas.CATALOGO) == esperadas
