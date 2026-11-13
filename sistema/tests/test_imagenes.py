"""El arte nunca tumba un video: el conector de Higgsfield se busca en la cuenta de ESTA máquina (su nombre cambia de una cuenta a
otra) y lo que no se pudo generar se quita del storyboard antes del ojo y del render (10-nov: sin conector, o con una imagen
fallida, el video ya dirigido reventaba al final con «archivo no encontrado»)."""
import json

import pytest

from estudio import ia, imagenes

LISTA = """Checking MCP server health…

claude.ai Gmail: https://gmailmcp.googleapis.com/mcp/v1 - ✔ Connected
claude.ai Higgsfield AI: https://claude-mcp.higgsfield.ai/mcp - ! Needs authentication
{otro}
plugin:x:notion: https://mcp.notion.com/mcp (HTTP) - ! Needs authentication
"""


def test_el_conector_se_llama_como_en_la_cuenta():
    con = LISTA.format(otro="claude.ai higgsfield: https://mcp.higgsfield.ai/mcp - ✔ Connected")
    assert imagenes.prefijo_en(con) == "mcp__claude_ai_higgsfield__"
    assert imagenes.prefijo_en(con.replace("! Needs authentication", "✔ Connected", 1).replace("claude.ai higgsfield:", "otro:")) \
        == "mcp__claude_ai_Higgsfield_AI__"


def test_sin_higgsfield_conectado_es_none_y_lista_ilegible_es_el_de_siempre():
    assert imagenes.prefijo_en(LISTA.format(otro="")) is None
    assert imagenes.prefijo_en("") == imagenes.HF
    assert imagenes.prefijo_en("error raro sin servidores") == imagenes.HF


def _proyecto(tmp_path):
    (tmp_path / "arte").mkdir()
    (tmp_path / "arte.json").write_text(json.dumps([{"id": "celular", "prompt": "un celular"}, {"id": "carpeta", "prompt": "una carpeta"}]))
    (tmp_path / "storyboard.json").write_text(json.dumps({"estilo": {}, "elementos": [
        {"id": "t1", "tipo": "texto", "texto": "hola"},
        {"id": "a1", "tipo": "foto", "src": "arte/celular.png"},
        {"id": "a2", "tipo": "foto", "src": "arte/carpeta.png"}],
        "trazos": [{"tipo": "rect", "sobre": "a2"}, {"tipo": "rect", "sobre": "a1"}, {"tipo": "linea", "sobre": "cara"}]}))
    return tmp_path


def test_sin_conector_el_video_sigue_sin_arte(tmp_path, monkeypatch):
    c = _proyecto(tmp_path)
    monkeypatch.setattr(imagenes, "conector", lambda: None)
    monkeypatch.setattr(ia, "llamar", lambda *a, **k: (_ for _ in ()).throw(AssertionError("sin conector no se llama a Claude")))
    dicho = []
    assert sorted(imagenes.arte_del_video(c, True, dicho.append)) == ["arte/carpeta.png", "arte/celular.png"]
    sb = json.loads((c / "storyboard.json").read_text())
    assert [e["id"] for e in sb["elementos"]] == ["t1"] and sb["trazos"] == [{"tipo": "linea", "sobre": "cara"}]
    assert any("Higgsfield no está conectado" in m for m in dicho) and any("2 imágenes no se pudieron generar" in m for m in dicho)


def test_una_imagen_que_falla_se_pide_otra_vez_y_si_no_sale_se_quita(tmp_path, monkeypatch):
    c = _proyecto(tmp_path)
    monkeypatch.setattr(imagenes, "conector", lambda: "mcp__mio__")
    pedidos = []

    def llamar(prompt, *a, **k):
        assert "mcp__mio__generate_image_batch" in prompt and "ToolSearch" in prompt and k["mcp"] is True
        assert k["herramientas"].startswith("mcp__mio__")
        pedidos.append([i for i in ("celular", "carpeta") if f'"id": "{i}"' in prompt])
        return {"result": json.dumps({"urls": {"celular": (c / "origen.png").as_uri()}, "fallidos": ["carpeta"]})}
    (c / "origen.png").write_bytes(b"png")
    monkeypatch.setattr(ia, "llamar", llamar)
    assert imagenes.arte_del_video(c, True, lambda m: None) == ["arte/carpeta.png"]
    assert pedidos == [["celular", "carpeta"], ["carpeta"]]            # la fallida se pidió una vez más, sola
    assert (c / "arte" / "celular.png").read_bytes() == b"png"
    sb = json.loads((c / "storyboard.json").read_text())
    assert [e["id"] for e in sb["elementos"]] == ["t1", "a1"] and {"tipo": "rect", "sobre": "a2"} not in sb["trazos"]


def test_claude_que_falla_no_tumba_el_video_pero_el_cupo_agotado_si_se_propaga(tmp_path, monkeypatch):
    c = _proyecto(tmp_path)
    monkeypatch.setattr(imagenes, "conector", lambda: "mcp__mio__")
    monkeypatch.setattr(ia, "llamar", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("imagenes: claude falló: sin herramienta")))
    assert len(imagenes.arte_del_video(c, True, lambda m: None)) == 2
    (tmp_path / "otro").mkdir()
    c2 = _proyecto(tmp_path / "otro")
    monkeypatch.setattr(ia, "llamar", lambda *a, **k: (_ for _ in ()).throw(ia.LimiteAgotado("hit your limit")))
    with pytest.raises(ia.LimiteAgotado):
        imagenes.arte_del_video(c2, True, lambda m: None)


def test_con_todo_el_arte_no_se_toca_el_storyboard(tmp_path):
    c = _proyecto(tmp_path)
    for n in ("celular", "carpeta"):
        (c / "arte" / f"{n}.png").write_bytes(b"png")
    antes = (c / "storyboard.json").read_text()
    assert imagenes.arte_del_video(c, False, lambda m: None) == [] and (c / "storyboard.json").read_text() == antes
