"""F3 de docs/PLANO-LEMO-APOYOS.md: «lemo:<slug>» entra por el MISMO flujo que cualquier estilo (`servidor._dirigir` y `/api/dirigir`),
con el preset «lemo», sin pasar por Higgsfield, y deja el reel listo para Personalizar y Exportar. Nunca llama a Claude: el director
y Lemo son funciones de prueba."""
import json
import subprocess
import threading
import types
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from estudio import config, director, imagenes, ingesta, lemo_apoyos, pro, pro_catalogo, servidor, texto_pelicula, textos_lemo

PALABRAS = [("hola", .2, .6), ("esto", 1.1, 1.4), ("es", 1.4, 1.6), ("una", 1.6, 1.9), ("prueba", 1.9, 2.5), ("de", 3.1, 3.3), ("lemo", 3.3, 3.8)]
SB = {"cortes": [], "subtitulos": {"y": 1455},
      "escenas": [{"t0": 0, "persona": {"modo": "completa"}}, {"t0": 1.0, "persona": {"modo": "oculta"}}, {"t0": 3.0, "persona": {"modo": "completa"}}],
      "elementos": [{"id": "a", "tipo": "clip", "src": "arte/a.mp4", "cubrir": True, "t0": 1.0, "t1": 3.0},
                    {"id": "b", "tipo": "clip", "src": "arte/b.mp4", "cubrir": True, "fusion": "pantalla", "t0": 3.0, "t1": 4.0}]}


def _video(destino, dur):
    subprocess.run([config.ffmpeg()[0], "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=0xe8e0cc:s=1080x1920:r=30:d={dur}",
                    "-vf", "format=yuv420p", "-t", str(dur), "-c:v", "libx264", str(destino)], check=True)


@pytest.fixture
def proyecto(tmp_path, monkeypatch):
    lemo = tmp_path / "lemo-lib"
    (lemo / "styles" / "engraving").mkdir(parents=True)
    (lemo / "styles" / "engraving" / "STYLE.md").write_text("estilo de prueba")
    if (textos_lemo.LEMO / "core").is_dir():
        (lemo / "core").symlink_to(textos_lemo.LEMO / "core")
    monkeypatch.setattr(pro, "LEMO", lemo)
    monkeypatch.setattr(texto_pelicula, "PESADO", tmp_path / "no-hay-cola.sh")
    monkeypatch.setattr(config, "PROYECTOS", tmp_path / "proyectos")
    c = tmp_path / "proyectos" / "v1"
    c.mkdir(parents=True)
    (c / "palabras.json").write_text(json.dumps([{"w": w, "s": s, "e": e} for w, s, e in PALABRAS]))
    (c / "persona.json").write_text(json.dumps({"version": 2, "paso": 15, "cuadros": 120, "cajas": [[[400., 500., 700., 900.], [200., 500., 900., 1920.]]] * 9}))
    (c / "fuente.json").write_text(json.dumps({"original": str(tmp_path / "video.mov"), "cuadros": 120}))
    (c / "preferencias.json").write_text(json.dumps({"guion_aprobado": True}))
    return c


def test_dirigir_con_lemo_usa_el_preset_lemo_y_no_pasa_por_higgsfield(proyecto, monkeypatch, pagina_lemo):
    vistos, llamadas = [], []

    def director_falso(carpeta, estilo, con_imagenes, avance):
        vistos.append(estilo)
        (carpeta / "storyboard.json").write_text(json.dumps(SB))
        (carpeta / "arte.json").write_text(json.dumps([{"id": "a", "clip": True, "idea": "una prueba"}, {"id": "b", "clip": True, "idea": "de lemo"}]))
        director._fijar_estilo(carpeta, estilo)       # el de verdad: pasa `estilo.lemo` de preferencias al storyboard

    def lemo_falso(prompt, modelo, cwd, **k):
        llamadas.append(prompt)
        d = cwd / "a"
        pagina_lemo(d, [("t1", "ESTO ES UNA PRUEBA", 0, 2.0)], 2.0)
        _video(d / "pelicula.mp4", 2.0)
        (d / "plano.json").write_text(json.dumps({"acento": "#8a2be2", "tramos": [{"t0": 0, "t1": 2.0, "integracion": "máquina"}]}))
        (cwd / "b" / "plano.json").write_text(json.dumps({"clase": "nada"}))
        return {"result": "LISTO"}

    monkeypatch.setattr(ingesta, "preparar_media", lambda *a, **k: None)
    monkeypatch.setattr(imagenes, "disponibles", lambda *a, **k: pytest.fail("con Lemo el arte no pasa por Higgsfield"))
    monkeypatch.setattr(director, "dirigir", director_falso)
    monkeypatch.setattr(director, "mirar", lambda *a, **k: {"veredicto": "aprobar"})
    monkeypatch.setattr(lemo_apoyos._ia, "llamar", lemo_falso)
    servidor._PEDIDO["v1"] = token = 7
    avisos = []
    assert servidor._dirigir("v1", "lemo:engraving", True, "normal", token, avisos.append) == "v1"
    assert vistos == ["lemo"] and len(llamadas) == 1        # un encargo por tramo; «b» ya quedó resuelto y no se pide otra vez
    assert '"id": "a"' in llamadas[0] and '"id": "b"' not in llamadas[0]
    sb = json.loads((proyecto / "storyboard.json").read_text())
    assert sb["estilo"]["id"] == "lemo" and sb["estilo"]["lemo"] == "engraving"
    assert sb["estilo"]["acento"] == "#8a2be2" and sb["estilo"]["fuente"] == "Courier Prime"     # gancho y subtítulo en su estilo
    assert [e["id"] for e in sb["elementos"]] == ["a"]                     # «b» no se hizo: se quitó, y la persona sigue ahí
    assert {e["t0"]: e["persona"]["modo"] for e in sb["escenas"]} == {0: "completa", 1.0: "oculta", 3.0: "completa"}
    assert (proyecto / "arte" / "a.mp4").exists()
    assert json.loads((proyecto / "lemo" / "cobertura.json").read_text())["sin_mostrar"] == []
    assert avisos[-1] == "listo para personalizar"
    assert lemo_apoyos.elegir(proyecto, "swiss") == "swiss" and lemo_apoyos.slug_de(proyecto) is None   # otro estilo deja a Lemo


@pytest.fixture
def api(proyecto, monkeypatch):
    lanzados = []
    monkeypatch.setattr(servidor, "_trabajo", lambda nombre, fn, *a, proyecto=None: lanzados.append((nombre, a)) or "t-1")
    monkeypatch.setattr(servidor, "_impedimento", lambda carpeta: None)
    monkeypatch.setattr(pro_catalogo, "por_slug", lambda s: {"slug": s} if s == "engraving" else None)
    motor = types.SimpleNamespace(instalado=True)
    monkeypatch.setattr(servidor, "_pro_modulo", lambda: types.SimpleNamespace(motor_instalado=lambda: motor.instalado))
    srv = ThreadingHTTPServer(("127.0.0.1", 0), servidor.Manejador)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{srv.server_address[1]}"

    def pedir(estilo):
        cuerpo = json.dumps({"proyecto": "v1", "estilo": estilo, "confirmado": True}).encode()
        req = urllib.request.Request(url + "/api/dirigir", cuerpo, {"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())
    yield pedir, lanzados, motor
    srv.shutdown()


def test_api_dirigir_acepta_un_estilo_pro_y_rechaza_lo_que_no_sirve(api):
    pedir, lanzados, motor = api
    codigo, r = pedir("lemo:engraving")
    assert codigo == 200 and r["ok"] and lanzados == [("dirigir", ("v1", "lemo:engraving", True, "normal", servidor._PEDIDO["v1"]))]
    assert pedir("lemo:inventado")[0] == 404
    assert pedir("lemo")[0] == 404                         # el preset «lemo» solo se pide con un estilo de Lemo
    motor.instalado = False
    codigo, r = pedir("lemo:engraving")
    assert codigo == 409 and "motor de Lemo" in r["error"]
    assert len(lanzados) == 1


def test_la_app_lanza_el_flujo_de_siempre_y_ya_no_la_pelicula_entera():
    js, html = (config.RAIZ / "app" / "pro.js").read_text(), (config.RAIZ / "app" / "index.html").read_text()
    assert '"/api/dirigir"' in js and "estilo: `lemo:${slug}`" in js and 'ir("per")' in js
    assert "/api/pro/lanzar" not in js and 'id="proLanzar"' not in html     # la película entera quedó solo en la terminal (`estudio pro`)
