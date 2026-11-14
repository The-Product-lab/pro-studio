"""La barra Biblioteca de Material: GET /api/biblioteca/proyectos lista lo hecho (liviano) con sus videos terminados."""
import json
import threading
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from estudio import config, servidor


@pytest.fixture
def pedir(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PROYECTOS", tmp_path)
    srv = ThreadingHTTPServer(("127.0.0.1", 0), servidor.Manejador)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{srv.server_address[1]}"
    yield lambda ruta: json.loads(urllib.request.urlopen(url + ruta).read())
    srv.shutdown()


def _proyecto(raiz, pid, **extra):
    d = raiz / pid
    d.mkdir()
    (d / "fuente.json").write_text(json.dumps({"original": f"/x/_subidas/{pid.upper()}.MOV"}))
    for nombre, texto in extra.items():
        f = d / nombre
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(texto)
    return d


def test_lista_con_final_con_pro_y_sin_nada(tmp_path, pedir):
    _proyecto(tmp_path, "con-final", **{"final.mp4": "v", "previa-a.jpg": "j", "machote.json": json.dumps({"duracion_s": 26.5})})
    _proyecto(tmp_path, "con-pro", **{"pro-watercolor/final.mp4": "v", "pro-otro/pelicula.mp4": "v"})
    _proyecto(tmp_path, "aprobado", **{"preferencias.json": json.dumps({"guion_aprobado": True})})
    _proyecto(tmp_path, "nada")
    (tmp_path / "_subidas").mkdir()          # carpetas internas y sin fuente.json no cuentan
    (tmp_path / "suelta").mkdir()
    r = pedir("/api/biblioteca/proyectos")
    por = {p["id"]: p for p in r["proyectos"]}
    assert r["ok"] and set(por) == {"con-final", "con-pro", "aprobado", "nada"}
    f = por["con-final"]
    assert f["estado"] == "final" and f["nombre"] == "CON-FINAL" and f["duracion"] == 26.5
    assert f["miniatura"] == "/archivo/con-final/previa-a.jpg"
    assert f["videos"] == [{"nombre": "Final", "url": "/archivo/con-final/final.mp4", "ruta": "final.mp4"}]
    assert [v["ruta"] for v in por["con-pro"]["videos"]] == ["pro-watercolor/final.mp4", "pro-otro/pelicula.mp4"]
    assert por["con-pro"]["estado"] == "final"
    assert por["aprobado"]["estado"] == "guion aprobado" and por["aprobado"]["videos"] == []
    assert por["nada"]["estado"] == "subido" and por["nada"]["miniatura"] is None


def test_en_proceso_si_hay_trabajo_corriendo(tmp_path, pedir, monkeypatch):
    _proyecto(tmp_path, "editando")
    monkeypatch.setitem(servidor.TRABAJOS, "t-bib", {"proyecto": "editando", "estado": "corriendo", "que": "editar", "log": []})
    assert pedir("/api/biblioteca/proyectos")["proyectos"][0]["estado"] == "en proceso"


def test_la_biblioteca_vieja_sigue_igual(tmp_path, pedir):
    _proyecto(tmp_path, "uno", **{"final.mp4": "v"})
    assert pedir("/api/biblioteca")["videos"][0]["id"] == "uno"
