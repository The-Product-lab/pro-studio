"""Las dos vistas previas de Personalizar (docs/PLANO-PREVIAS.md): salen rápido, se piden en paralelo, la vieja se descarta, y un panel
nunca queda vacío (10-nov, Pablo: «la de B-roll es muy lenta, aún no muestra nada para escoger»: un arte que faltaba tumbaba las dos
vistas sin decir nada, y la vista rápida nunca dibujaba la segunda)."""
import json
import subprocess
import threading
import time

import numpy as np
import pytest
from PIL import Image

from estudio import catalogo, config, motor, previas, rapida, servidor

ESTILO = {"base": "pantalla", "acento": "#D97757", "acento2": "#8B5CF6", "papel": "#EEEEEE", "tinta": "#111111", "persona": "color"}


def _texto(i, t0, t1, texto):
    return {"id": i, "tipo": "texto", "x": 540, "y": 700, "t0": t0, "t1": t1, "entra": "fundido",
            "lineas": [{"texto": texto, "rol": "display", "tam": 120, "color": "acento"}]}


@pytest.fixture(scope="module")
def base(tmp_path_factory):
    """Lo pesado de un proyecto en miniatura de 12 s (el video), hecho una sola vez para todas las pruebas."""
    c = tmp_path_factory.mktemp("base")
    video = c / "fuente.mp4"
    subprocess.run([config.ffmpeg()[0], "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=size=1080x1920:rate=30:d=12", "-f", "lavfi", "-i",
                    "anullsrc=r=16000:cl=mono", "-t", "12", "-pix_fmt", "yuv420p", "-preset", "ultrafast", "-g", "15", "-shortest", str(video)], check=True)
    return c


@pytest.fixture
def proyecto(base, tmp_path):
    """Proyecto en miniatura: persona, un apoyo a pantalla completa (5–9 s) con un texto y una foto cuyo arte NO existe."""
    c = tmp_path / "p"
    c.mkdir()
    (c / "fuente.mp4").symlink_to(base / "fuente.mp4")
    video = c / "fuente.mp4"
    (c / "fuente.json").write_text(json.dumps({"video": str(video), "original": str(video), "cuadros": 360, "hdr": False}))
    (c / "palabras.json").write_text(json.dumps([{"w": f"p{k}", "s": 3 + k * .3, "e": 3.25 + k * .3} for k in range(8)]))
    sb = {"estilo": ESTILO, "cortes": [], "escenas": [{"t0": 0, "persona": {"modo": "completa"}},
                                                         {"t0": 5, "persona": {"modo": "oculta", "fondo": "#EEEEEE"}},
                                                         {"t0": 9, "persona": {"modo": "completa"}}],
          "elementos": [_texto("a", 3.4, 5, "PERSONA"), _texto("b", 6, 8.5, "APOYO"),
                        {"id": "f", "tipo": "foto", "src": "arte/falta.jpg", "x": 540, "y": 1200, "t0": 6, "t1": 8.5}],
          "subtitulos": {"y": 1400}}
    (c / "storyboard.json").write_text(json.dumps(sb))
    return c


def test_dos_vistas_distintas_y_rapidas(proyecto):
    previas.con_director(proyecto, {})                      # calienta (decodifica los cuadros)
    t = time.time()
    r = previas.con_director(proyecto, {"acento": "#00AAFF"})   # cambio de estilo en caliente
    assert time.time() - t < 2, "cambiar una opción de estilo debe tardar menos de 2 s"
    a, b = (np.asarray(Image.open(proyecto / r[k])) for k in ("a", "b"))
    assert a.shape == (960, 540, 3) and not np.array_equal(a, b)


def test_el_arte_que_falta_no_deja_el_panel_vacio(proyecto):
    r = previas.con_director(proyecto, {})
    assert (proyecto / r["b"]).exists() and "Faltan 1 imagen" in r["nota_b"] and r["nota_a"] == ""
    with pytest.raises(FileNotFoundError):                   # el render completo sigue exigiendo todo su arte
        motor.Proyecto(proyecto)


def test_vista_parcial_es_identica_a_la_completa(proyecto):
    sb = json.loads((proyecto / "storyboard.json").read_text())
    sb["elementos"] = [e for e in sb["elementos"] if e["tipo"] != "foto"]
    of = 200   # dentro del apoyo (6,67 s)
    completo, parcial = motor.Proyecto(proyecto, sb), motor.Proyecto(proyecto, sb, solo_en={of})
    assert len(parcial.elementos) < len(completo.elementos)
    (_, x), (_, y) = next(motor.recorrer(completo, {of})), next(motor.recorrer(parcial, {of}))
    assert np.array_equal(x, y)


def test_sin_apoyo_se_dice_en_vez_de_dejar_un_cuadro_mudo(proyecto):
    sb = json.loads((proyecto / "storyboard.json").read_text())
    sb["escenas"] = [{"t0": 0, "persona": {"modo": "completa"}}]
    (proyecto / "storyboard.json").write_text(json.dumps(sb))
    r = previas.con_director(proyecto, {})
    assert r["nota_b"] == previas.NOTA_SIN_APOYO and (proyecto / r["b"]).exists()


def test_ver_el_estilo_sin_comprometer_no_escribe_el_storyboard(proyecto):
    """Edición avanzada ve sin guardar (antes `servidor._mezclar_estilo`): sin `guardar`, el storyboard queda byte a byte igual."""
    antes = (proyecto / "storyboard.json").read_text()
    previas.con_director(proyecto, {"acento": "#FFE800"})
    assert (proyecto / "storyboard.json").read_text() == antes


def test_guardar_solo_si_sigue_vigente(proyecto):
    guardados = []
    r = previas.con_director(proyecto, {"acento": "#123456"}, lambda c, e: guardados.append(e), vigente=lambda: False)
    assert r == {"cancelada": True} and not guardados
    previas.con_director(proyecto, {"acento": "#123456"}, lambda c, e: guardados.append(e))
    assert guardados == [{"acento": "#123456"}]


def test_mismo_pedido_no_se_vuelve_a_dibujar(proyecto):
    r1 = previas.con_director(proyecto, {})
    (proyecto / r1["a"]).unlink()
    assert previas.con_director(proyecto, {}) is r1 or (proyecto / r1["a"]).exists()   # sin archivo, se redibuja; con archivo, se reusa
    r2 = previas.con_director(proyecto, {})
    assert r2 is previas.con_director(proyecto, {})


def test_la_vista_rapida_trae_las_dos_vistas(proyecto):
    nombre = "prueba-previas-rapida"
    rapida.preparar(proyecto / "fuente.mp4", nombre)
    try:
        r = previas.con_toma(rapida.carpeta_de(nombre), ESTILO)
        a, b = (np.asarray(Image.open(rapida.carpeta_de(nombre) / r[k])) for k in ("a", "b"))
        assert not np.array_equal(a, b) and r["nota_b"] == previas.NOTA_MUESTRA
    finally:
        import shutil
        shutil.rmtree(rapida.carpeta_de(nombre), ignore_errors=True)


def test_la_peticion_nueva_descarta_a_la_vieja():
    suelta = threading.Event()

    def generar(avance, vigente):
        suelta.wait(5)
        return {"cancelada": True} if not vigente() else {"a": "previa-a.jpg", "b": "previa-b.jpg"}
    t1 = servidor._pedir_previa("prueba/k", "/u/", generar)
    t2 = servidor._pedir_previa("prueba/k", "/u/", generar)
    suelta.set()
    for _ in range(100):
        if all(servidor.TRABAJOS[t]["estado"] != "corriendo" for t in (t1, t2)):
            break
        time.sleep(.05)
    assert servidor.TRABAJOS[t1]["resultado"] == {"cancelada": True}
    assert servidor.TRABAJOS[t2]["resultado"]["a"].startswith("/u/previa-a.jpg?v=")


# ---------- guardar lo que la persona tocó: solo esas claves, y siempre antes del render (auditoría de botones 10-nov) ----------

def _con_storyboard(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PROYECTOS", tmp_path)
    c = tmp_path / "p1"
    c.mkdir()
    (c / "storyboard.json").write_text(json.dumps({"estilo": {"acento": "#111111", "fuente": "Corregida", "papel": "#EEEEEE"}}))
    return c


def test_la_previa_guarda_solo_lo_que_cambio_la_persona(tmp_path, monkeypatch):
    """Una corrección (o Edición avanzada) dejó `fuente`; la vista con `acento` cambiado no la pisa con el estilo viejo de la pantalla."""
    c = _con_storyboard(tmp_path, monkeypatch)
    (c / "fuente.json").write_text(json.dumps({"cuadros": 300}))
    monkeypatch.setattr(previas, "pintar", lambda *a, **k: {previas.A: [], previas.B: []})
    monkeypatch.setattr(previas.portadas, "previa", lambda sb, dur, pal: (1.0, 2.0))
    monkeypatch.setattr(previas.portadas, "es_apoyo", lambda sb, t: True)
    previas.con_director(c, {"acento": "#222222"}, servidor._guardar_estilo)
    assert json.loads((c / "storyboard.json").read_text())["estilo"] == {"acento": "#222222", "fuente": "Corregida", "papel": "#EEEEEE"}
    js = (config.RAIZ / "app" / "vista.js").read_text()
    assert "e.cambios" in js   # Personalizar manda solo sus cambios a /api/previa (Edición avanzada, que no guarda, manda el estilo entero)


def test_exportar_guarda_lo_elegido_mientras_el_editor_trabajaba(tmp_path, monkeypatch):
    """Lo elegido durante la preparación (vista rápida, que no guarda) llega con /api/render y se guarda ANTES de renderizar."""
    import urllib.request
    from http.server import ThreadingHTTPServer
    c = _con_storyboard(tmp_path, monkeypatch)
    visto = []
    monkeypatch.setattr(servidor, "_render", lambda pid, avance: visto.append(json.loads((c / "storyboard.json").read_text())["estilo"]))
    srv = ThreadingHTTPServer(("127.0.0.1", 0), servidor.Manejador)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{srv.server_address[1]}/api/render",
                                     json.dumps({"proyecto": "p1", "estilo": {"acento": "#333333"}}).encode(), {"Content-Type": "application/json"})
        assert json.loads(urllib.request.urlopen(req).read())["ok"]
        for _ in range(50):
            if visto:
                break
            time.sleep(.05)
    finally:
        srv.shutdown()
    assert visto == [{"acento": "#333333", "fuente": "Corregida", "papel": "#EEEEEE"}]
    assert '"/api/render", { proyecto, estilo: cambios }' in (config.RAIZ / "app" / "app.js").read_text()


@pytest.mark.parametrize("estilo", sorted(catalogo.presets()))
def test_la_muestra_sobre_el_papel_se_lee_y_no_lleva_sombra(estilo):
    """11-nov, Swiss: en «apoyo a pantalla completa» el título de muestra salía con la sombra del video (un halo sucio sobre el papel
    claro) y «tu estilo» en gris claro sobre papel casi blanco. Los apoyos de verdad van sin sombra sobre papel: la muestra también."""
    from estudio import contraste
    sb = previas.muestra({"id": estilo, **{k: v for k, v in catalogo.presets()[estilo].items() if k != "nombre"}})
    est = motor.Estilo(sb["estilo"])
    papel = motor._hex(sb["escenas"][1]["persona"]["fondo"])
    sobre_persona, sobre_papel = sb["elementos"]
    assert (sobre_persona["t1"], sobre_papel["t0"]) == (1.0, 1.0) and sobre_papel["sombra"] is False and "sombra" not in sobre_persona
    for linea in sobre_papel["lineas"]:
        assert contraste.razon(est.color(linea["color"]), papel) >= contraste.MINIMO, (estilo, linea["texto"], linea["color"])
