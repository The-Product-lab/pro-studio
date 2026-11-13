"""F3 de docs/PLANO-ESTILOS-PRO.md: la API de Estilos Pro (catálogo, lanzar, estado, media) con un `estudio.pro` falso inyectado."""
import json
import sys
import threading
import types
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from estudio import config, pro_catalogo, servidor

# Estas pruebas describen el laboratorio COMPLETO (los 66 estilos y sus muestras ya renderizadas). Una copia de referencia de Lemo
# (p. ej. `ESTUDIO BETA/referencias` en la Mac: 59 estilos, sin muestras) sirve para ver el catálogo, no para estas medidas.
_LAB = pro_catalogo.laboratorio()
pytestmark = pytest.mark.skipif(_LAB is None or not (_LAB / "muestras-lemo").is_dir(), reason="esta máquina no tiene el laboratorio-estilos completo")


@pytest.fixture
def api(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PROYECTOS", tmp_path)
    (tmp_path / "v1").mkdir()
    (tmp_path / "v1" / "preferencias.json").write_text(json.dumps({"guion_aprobado": True}))   # Pro exige guion aprobado
    srv = ThreadingHTTPServer(("127.0.0.1", 0), servidor.Manejador)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{srv.server_address[1]}"

    def pedir(ruta, cuerpo=None):
        req = urllib.request.Request(url + ruta, json.dumps(cuerpo).encode() if cuerpo is not None else None, {"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req) as r:
                return r.status, r.headers.get("Content-Type"), r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.headers.get("Content-Type"), e.read()
    yield pedir
    srv.shutdown()


def _json(r):
    return json.loads(r[2])


def test_catalogo_por_http(api):
    r = _json(api("/api/pro/catalogo"))
    assert r["ok"] and len(r["estilos"]) == 66 and "minutos" in r["aviso"]["texto"]
    e = next(x for x in r["estilos"] if x["slug"] == "watercolor")
    assert e["nombre"] == "Acuarela" and e["poster"] == "/pro-media/watercolor/poster" and e["muestra"] == "/pro-media/watercolor/muestra"
    assert not any("/home" in json.dumps(x) for x in r["estilos"])   # ninguna ruta del disco sale a la app


def test_media_poster_muestra_y_rutas_malas(api):
    codigo, tipo, cuerpo = api("/pro-media/watercolor/poster")
    assert codigo == 200 and tipo == "image/jpeg" and cuerpo[:2] == b"\xff\xd8"
    assert api("/pro-media/watercolor/muestra")[1] == "video/mp4"
    assert api("/pro-media/nada/poster")[0] == 404
    assert api("/pro-media/watercolor/otro")[0] == 404
    assert api("/pro-media/../poster")[0] == 404


def test_sin_motor_pro_responde_503_claro(api, monkeypatch):
    monkeypatch.setitem(sys.modules, "estudio.pro", None)   # import imposible = módulo ausente
    monkeypatch.setattr(servidor, "_pro_modulo", lambda: None)
    for r in (api("/api/pro/lanzar", {"proyecto": "v1", "estilo": "watercolor"}), api("/api/pro/estado?proyecto=v1&estilo=watercolor")):
        assert r[0] == 503 and "no está instalado" in _json(r)["error"]


def test_lanzar_y_estado_con_pro_falso(api, monkeypatch, tmp_path):
    llamadas = []
    falso = types.ModuleType("estudio.pro")
    falso.lanzar = lambda carpeta, slug: llamadas.append(("lanzar", carpeta, slug)) or carpeta / f"pro-{slug}"
    falso.estado = lambda carpeta, slug: {"fase": "lemo", "pct": 40, "linea": "Dirigiendo la película"}
    monkeypatch.setitem(sys.modules, "estudio.pro", falso)

    r = _json(api("/api/pro/lanzar", {"proyecto": "v1", "estilo": "watercolor"}))
    assert r["ok"] and r["carpeta"] == str(tmp_path / "v1" / "pro-watercolor")
    assert llamadas == [("lanzar", tmp_path / "v1", "watercolor")]
    assert _json(api("/api/pro/estado?proyecto=v1&estilo=watercolor")) == {"ok": True, "fase": "lemo", "pct": 40, "linea": "Dirigiendo la película"}

    assert api("/api/pro/lanzar", {"proyecto": "v1", "estilo": "inventado"})[0] == 404
    assert api("/api/pro/lanzar", {"proyecto": "no-existe", "estilo": "watercolor"})[0] == 404
    assert api("/api/pro/lanzar", {"proyecto": "../afuera", "estilo": "watercolor"})[0] == 500   # nombre inválido: nunca llega al motor
    assert api("/api/pro/estado?proyecto=v1&estilo=inventado")[0] == 404
    assert len(llamadas) == 1


def test_pro_sin_guion_aprobado_no_se_lanza_y_no_depende_del_director(api, monkeypatch, tmp_path):
    """Pro parte del machote, no del director normal: se habilita con el guion aprobado (sin storyboard.json) y nunca antes."""
    llamadas = []
    falso = types.ModuleType("estudio.pro")
    falso.lanzar = lambda carpeta, slug: llamadas.append(slug) or carpeta / f"pro-{slug}"
    monkeypatch.setitem(sys.modules, "estudio.pro", falso)
    (tmp_path / "v1" / "preferencias.json").write_text(json.dumps({}))
    r = api("/api/pro/lanzar", {"proyecto": "v1", "estilo": "watercolor"})
    assert r[0] == 409 and "guion" in _json(r)["error"] and llamadas == []
    assert _json(api("/api/proyecto/v1"))["guion_aprobado"] is False
    (tmp_path / "v1" / "preferencias.json").write_text(json.dumps({"guion_aprobado": True}))
    assert not (tmp_path / "v1" / "storyboard.json").exists()   # el director normal no corrió
    assert _json(api("/api/pro/lanzar", {"proyecto": "v1", "estilo": "watercolor"}))["ok"] and llamadas == ["watercolor"]
    assert _json(api("/api/proyecto/v1"))["guion_aprobado"] is True


def test_pro_con_guion_mas_largo_que_el_tope_no_se_lanza(api, monkeypatch, tmp_path):
    from estudio import machote
    llamadas = []
    falso = types.ModuleType("estudio.pro")
    falso.lanzar = lambda carpeta, slug: llamadas.append(slug) or carpeta / f"pro-{slug}"
    monkeypatch.setitem(sys.modules, "estudio.pro", falso)
    (tmp_path / "v1" / "preferencias.json").write_text(json.dumps({"guion_aprobado": True}))
    (tmp_path / "v1" / "machote.json").write_text(json.dumps({"duracion_s": machote.LIMITE_S + .4, "cortes": []}))
    r = api("/api/pro/lanzar", {"proyecto": "v1", "estilo": "watercolor"})
    assert r[0] == 409 and "quita frases" in _json(r)["error"] and llamadas == []
    assert f"{machote.LIMITE_S + .4:.1f}" in _json(r)["error"]   # 110,4 no se muestra como «110»
