"""Pablo 10-nov: elegir una tarjeta no gasta; el guion aprobado no cambia (ni el director ni el montaje lo tocan); rehacer cortes borra la aprobación."""
import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest
from test_machote import dos_tomas, libres_en

from estudio import config, director, machote, montaje, servidor


# ---------- a) un clic en la tarjeta solo selecciona ----------
def test_la_tarjeta_solo_selecciona_y_el_director_pide_boton_y_aviso():
    js = (config.RAIZ / "app" / "app.js").read_text()
    assert "c.onclick = () => seleccionar(id)" in js and "elegir(id)" not in js
    cuerpo = js[js.index("function seleccionar("):js.index("function editarConEstilo(")]
    assert "dirigir" not in cuerpo and "/api/" not in cuerpo                       # seleccionar no llama a nada que gaste
    assert js.count("dirigirConEstilo(") == 2                                      # la definición y UNA sola llamada: el botón
    assert "Editar con este estilo" in js and "confirm(" in js and "usa IA" in js
    assert js.index("confirm(") < js.index("dirigirConEstilo(id);\n  ir(")        # el aviso va antes de dirigir


def test_la_api_no_dirige_sin_confirmacion(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PROYECTOS", tmp_path)
    monkeypatch.setattr(servidor, "TRABAJOS", {})
    (tmp_path / "p1").mkdir()
    (tmp_path / "p1" / "preferencias.json").write_text(json.dumps({"guion_aprobado": True}))
    estilo = next(iter(json.loads((config.RAIZ / "librerias" / "estilos" / "presets.json").read_text())))
    srv = ThreadingHTTPServer(("127.0.0.1", 0), servidor.Manejador)
    threading.Thread(target=srv.serve_forever, daemon=True).start()

    def pedir(cuerpo):
        req = urllib.request.Request(f"http://127.0.0.1:{srv.server_address[1]}/api/dirigir", json.dumps(cuerpo).encode(),
                                     {"Content-Type": "application/json"})
        try:
            return 200, json.loads(urllib.request.urlopen(req).read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())
    try:
        codigo, r = pedir({"proyecto": "p1", "estilo": estilo, "imagenes": True})
        assert codigo == 409 and not r["ok"] and "confirmar" in r["error"] and servidor.TRABAJOS == {}
    finally:
        srv.shutdown()


# ---------- b) rehacer los cortes borra la aprobación ----------
def test_rehacer_el_machote_borra_guion_aprobado(tmp_path):
    c = dos_tomas(tmp_path)
    (c / "preferencias.json").write_text(json.dumps({"guion_aprobado": True, "hook_texto": "hola"}))
    assert machote.guion_aprobado(c)
    machote.decidir(c, con_ia=False, avance=lambda m: None)
    assert not machote.guion_aprobado(c)
    assert json.loads((c / "preferencias.json").read_text()) == {"hook_texto": "hola"}   # solo la aprobación; lo demás se queda


# ---------- c) ningún estilo por defecto ----------
def test_ninguna_pantalla_cae_en_un_estilo_por_defecto():
    for f in ("app.js", "seleccionador.html"):
        assert "collage-papel" not in (config.RAIZ / "app" / f).read_text(), f


# ---------- d) el guion aprobado no cambia ----------
def test_el_director_no_decide_cortes():
    prompt = (config.RAIZ / "estudio" / "director" / "director.md").read_text()
    assert "decides QUÉ FRASES salen" not in prompt and "no agregues, no quites ni muevas ningún corte" in prompt


def test_con_guion_aprobado_el_resultado_tiene_exactamente_las_palabras_aprobadas(tmp_path):
    c = dos_tomas(tmp_path)
    mj = machote.decidir(c, con_ia=False, avance=lambda m: None)
    aprobadas = libres_en(c, mj)
    (c / "preferencias.json").write_text(json.dumps({"guion_aprobado": True}))
    # el director añadió un corte propio (quitaría «gracias por ver») y movió otro: la garantía en código lo deshace
    (c / "storyboard.json").write_text(json.dumps({"cortes": [[9.0, 10.0], [0.0, 0.5]], "escenas": []}))
    assert machote.imponer(c)
    sb = json.loads((c / "storyboard.json").read_text())
    assert sb["cortes"] == [[round(a, 3), round(b, 3)] for a, b in mj["cortes"]]
    assert libres_en(c, {"cortes": sb["cortes"]}) == aprobadas
    assert machote.guion_aprobado(c)


def test_si_el_montaje_quiere_cambiar_los_cortes_aprobados_se_para(tmp_path, monkeypatch):
    c = dos_tomas(tmp_path)
    mj = machote.decidir(c, con_ia=False, avance=lambda m: None)
    (c / "storyboard.json").write_text(json.dumps({"cortes": mj["cortes"], "escenas": []}))
    llamadas = []
    monkeypatch.setattr(director.ia, "llamar", lambda *a, **k: llamadas.append(a))
    monkeypatch.setattr(montaje, "reparar", lambda sb, carpeta, avisos=None: {**sb, "cortes": sb["cortes"] + [[10.0, 10.5]]})
    with pytest.raises(director.GuionCambiado, match="cambiar las palabras"):
        director._validar(c, "director")
    assert llamadas == []                                                          # no se le pide a Opus que "arregle": se avisa y se para
    assert json.loads((c / "storyboard.json").read_text())["cortes"] == mj["cortes"]


# ---------- 2.ª ronda del revisor ----------
def test_preferencias_viejas_con_color_entrada_se_guardan_sin_error(tmp_path):
    from estudio import catalogo
    p = tmp_path / "v1"
    p.mkdir()
    (p / "preferencias.json").write_text(json.dumps({"estilo": {"color": {"entrada": "slog3", "look": "mio:x"}}}))
    r = catalogo.guardar(p, {"estilo": {"color": {"entrada": "rec709", "ajustes": {"contraste": .2}}, "acento": "#FFFFFF"}})
    assert "entrada" not in json.dumps(r["preferencias"]) and r["preferencias"]["estilo"]["color"] == {"ajustes": {"contraste": .2}}
    for f in (config.RAIZ / "estudio" / "director" / "ejemplo").glob("*.json"):
        assert '"entrada": "rec709"' not in f.read_text(), f.name


def test_guion_mas_largo_que_el_tope_no_se_aprueba_ni_se_dirige(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PROYECTOS", tmp_path)
    monkeypatch.setattr(servidor, "TRABAJOS", {})
    c = tmp_path / "p1"
    c.mkdir()
    (c / "fuente.json").write_text("{}")
    (c / "preferencias.json").write_text(json.dumps({"guion_aprobado": True}))
    (c / "machote.json").write_text(json.dumps({"duracion_s": machote.LIMITE_S + 20, "cortes": []}))
    estilo = next(iter(json.loads((config.RAIZ / "librerias" / "estilos" / "presets.json").read_text())))
    srv = ThreadingHTTPServer(("127.0.0.1", 0), servidor.Manejador)
    threading.Thread(target=srv.serve_forever, daemon=True).start()

    def pedir(ruta, cuerpo):
        req = urllib.request.Request(f"http://127.0.0.1:{srv.server_address[1]}{ruta}", json.dumps(cuerpo).encode(), {"Content-Type": "application/json"})
        try:
            return 200, json.loads(urllib.request.urlopen(req).read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())
    try:
        for ruta, cuerpo in (("/api/seleccion", {"proyecto": "p1", "guion_aprobado": True}),
                             ("/api/dirigir", {"proyecto": "p1", "estilo": estilo, "confirmado": True})):
            codigo, r = pedir(ruta, cuerpo)
            assert codigo == 409 and "quita frases" in r["error"] and str(machote.LIMITE_S) in r["error"], ruta
        assert servidor.TRABAJOS == {}
    finally:
        srv.shutdown()


def test_quejas_sobre_los_cortes_paran_sin_llamar_a_opus(tmp_path, monkeypatch):
    c = dos_tomas(tmp_path)
    mj = machote.decidir(c, con_ia=False, avance=lambda m: None)
    (c / "storyboard.json").write_text(json.dumps({"cortes": mj["cortes"], "escenas": []}))
    llamadas = []
    monkeypatch.setattr(director.ia, "llamar", lambda *a, **k: llamadas.append(a))
    monkeypatch.setattr(director.validar, "errores", lambda *a, **k: ["montaje: hay 3.00 s de silencio en el video final"])
    with pytest.raises(director.GuionCambiado, match="problemas de cortes"):
        director._validar(c, "director")
    assert llamadas == []


# ---------- glass-nuevo-10nov: un guion aprobable SIEMPRE pasa la compuerta de montaje del render ----------
GLASS = config.RAIZ / "tests" / "fixtures" / "glass-nuevo-10nov"


@pytest.fixture
def tope_de_entonces(monkeypatch):
    """Estos casos se grabaron con el tope de silencio en 0,20 s (hoy 0,30: Pablo, 13-nov) y prueban la MECÁNICA de reparar y congelar
    el guion sobre un residual de 0,22 s, que con el tope de hoy ya no es residual. Corren con el tope con que se grabaron."""
    monkeypatch.setattr(montaje, "SILENCIO_MAX_S", .20)
    monkeypatch.setattr(montaje, "SILENCIO_META_S", .20 - 3 * montaje.voz.HOP)


def _glass(tmp_path):
    import shutil
    c = tmp_path / "glass"
    shutil.copytree(GLASS, c)
    return c


def test_glass_reparar_cierra_la_pausa_de_0_22_s(tmp_path, tope_de_entonces):
    """Causa: el corte [25.765, 26.85] terminaba dentro de la pausa que Whisper estiró sobre «entendí» (empieza a sonar en 26.99). Alargarlo
    a la pausa real parecía llevarse media palabra por TIEMPO y se rechazaba, aunque solo era silencio: quedaban 0,22 s (máx. 0,2)."""
    c = _glass(tmp_path)
    cortes = json.loads((c / "machote.json").read_text())["cortes"]
    assert any("silencio" in e for e in montaje.errores({"cortes": cortes}, c))       # tal cual salió, la compuerta lo rechaza
    assert montaje.errores(montaje.reparar({"cortes": cortes}, c), c) == []           # reparado, pasa; los umbrales no se tocaron


def test_un_guion_con_residual_no_se_aprueba_ni_se_dirige_antes_de_gastar(tmp_path, monkeypatch, tope_de_entonces):
    monkeypatch.setattr(config, "PROYECTOS", tmp_path)
    monkeypatch.setattr(servidor, "TRABAJOS", {})
    import shutil
    shutil.copytree(GLASS, tmp_path / "g1")
    monkeypatch.setattr(montaje, "reparar", lambda sb, carpeta, avisos=None: sb)   # sin reparación: el residual queda y debe bloquear antes de gastar
    assert machote.impedimento(tmp_path / "g1") is not None and "silencio" in machote.impedimento(tmp_path / "g1")
    (tmp_path / "g1" / "preferencias.json").write_text(json.dumps({"guion_aprobado": True}))
    estilo = next(iter(json.loads((config.RAIZ / "librerias" / "estilos" / "presets.json").read_text())))
    srv = ThreadingHTTPServer(("127.0.0.1", 0), servidor.Manejador)
    threading.Thread(target=srv.serve_forever, daemon=True).start()

    def pedir(ruta, cuerpo):
        req = urllib.request.Request(f"http://127.0.0.1:{srv.server_address[1]}{ruta}", json.dumps(cuerpo).encode(), {"Content-Type": "application/json"})
        try:
            return 200, json.loads(urllib.request.urlopen(req).read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())
    try:
        for ruta, cuerpo in (("/api/seleccion", {"proyecto": "g1", "guion_aprobado": True}),
                             ("/api/dirigir", {"proyecto": "g1", "estilo": estilo, "confirmado": True})):
            codigo, r = pedir(ruta, cuerpo)
            assert codigo == 409 and "silencio" in r["error"], ruta
        assert servidor.TRABAJOS == {}
    finally:
        srv.shutdown()


# ---------- mover un borde dentro de un silencio NO es cambiar el guion ----------
def test_glass_reparacion_tecnica_actualiza_el_machote_y_el_storyboard_sin_opus(tmp_path, monkeypatch, tope_de_entonces):
    c = _glass(tmp_path)
    viejo = json.loads((c / "machote.json").read_text())
    (c / "preferencias.json").write_text(json.dumps({"guion_aprobado": True}))
    (c / "storyboard.json").write_text(json.dumps({"cortes": viejo["cortes"], "escenas": [{"t0": 5.205}]}))
    llamadas = []
    monkeypatch.setattr(director.ia, "llamar", lambda *a, **k: llamadas.append(a))
    ctx = montaje.contexto(c)
    nuevos = montaje.reparar({"cortes": viejo["cortes"]}, c)["cortes"]
    assert nuevos != viejo["cortes"]
    assert montaje.palabras_que_quedan(ctx, nuevos) == montaje.palabras_que_quedan(ctx, viejo["cortes"])   # mismas palabras
    assert machote.reparar_cortes(c, lambda m: None)["estado"] == "ajustado"          # sin GuionCambiado
    mj = json.loads((c / "machote.json").read_text())
    assert montaje.errores({"cortes": mj["cortes"]}, c) == [] and machote.guion_aprobado(c)   # sigue aprobado
    reg = mj["ajustes_tecnicos"][-1]
    assert reg["mismas_palabras"] and reg["cambios"][0]["mueve_s"] > 0                # registro de qué borde se movió y cuánto
    sb = json.loads((c / "storyboard.json").read_text())
    assert sb["cortes"] == mj["cortes"] and sb["escenas"] == [{"t0": 5.205}]          # cortes nuevos; lo demás del director intacto
    assert llamadas == []
    assert machote.impedimento(c) is None


def test_si_cambiaran_las_palabras_la_reparacion_no_se_aplica(tmp_path):
    c = _glass(tmp_path)
    antes = (c / "machote.json").read_text()
    assert not machote.actualizar_cortes(c, [[0.0, 30.0]], lambda m: None)           # quitaría media historia: eso sí es otro guion
    assert (c / "machote.json").read_text() == antes


# ---------- machote apto de antes del reparar actual (cmp/v-c8873-glass): se estabiliza solo, antes de gastar ----------
def test_machote_apto_viejo_se_actualiza_solo_sin_opus_ni_guion_cambiado(tmp_path, monkeypatch, tope_de_entonces):
    import shutil
    c = tmp_path / "v"
    shutil.copytree(config.RAIZ / "tests" / "fixtures" / "machote-apto-viejo-c8873", c)
    for f in (".energia.npy", "palabras.json"):   # el audio y las palabras son los del banco (mismo video C8873): no se copian dos veces al repo
        shutil.copy(config.RAIZ / "tests" / "banco" / "prestiggio-c8873" / f, c / f)
    (c / "preferencias.json").write_text(json.dumps({"guion_aprobado": True}))
    antes = json.loads((c / "machote.json").read_text())
    assert machote.apto(c)
    llamadas = []
    monkeypatch.setattr(director.ia, "llamar", lambda *a, **k: llamadas.append(a))
    assert machote.impedimento(c) is None                                  # apto, pero NO se salta la estabilidad: se actualizó
    despues = json.loads((c / "machote.json").read_text())
    assert despues["cortes"] != antes["cortes"] and despues["ajustes_tecnicos"][-1]["mismas_palabras"]
    assert machote.impedimento(c) is None and json.loads((c / "machote.json").read_text())["cortes"] == despues["cortes"]   # y ya es estable
    (c / "storyboard.json").write_text(json.dumps({"cortes": despues["cortes"], "escenas": []}))
    monkeypatch.setattr(director.validar, "errores", lambda *a, **k: [])    # lo creativo no es de esta prueba: solo los cortes
    director._validar(c, "director", imagenes_pendientes=True)             # la parada del director ya no puede dispararse
    assert llamadas == [] and machote.guion_aprobado(c)
    assert json.loads((c / "storyboard.json").read_text())["cortes"] == despues["cortes"]


# ---------- ronda 5: guion que cambia al reparar = aprobación única, nunca un ciclo; una sola regla de «qué palabras quedan» ----------
C8866 = (("palabras.json", "estudio/director/ejemplo/maestro-calma.palabras.json"),)   # las palabras de C8866 ya viven como ejemplo del director


def _copia(tmp_path, nombre, banco=()):
    import shutil
    c = tmp_path / nombre
    shutil.copytree(config.RAIZ / "tests" / "fixtures" / nombre, c)
    for dest, origen in banco:   # lo que ya vive en tests/banco no se copia dos veces al repo
        shutil.copy(config.RAIZ / origen, c / dest)
    (c / "preferencias.json").write_text(json.dumps({"guion_aprobado": True}))
    return c


@pytest.mark.parametrize("nombre,palabra,banco", [("sin-salida-c8866", "como", (("palabras.json", "estudio/director/ejemplo/maestro-calma.palabras.json"),)),
                                                  ("sin-salida-c8869", "si", (("fuente.json", "tests/banco/julian3d-c8869/fuente.json"), ("palabras.json", "tests/banco/julian3d-c8869/palabras.json"), (".energia.npy", "tests/banco/julian3d-c8869/.energia.npy")))])
def test_si_la_reparacion_cambia_palabras_se_aplica_se_pide_aprobar_una_vez_y_no_hay_ciclo(tmp_path, monkeypatch, nombre, palabra, banco):
    """c8866 («como» 229,3 s) y c8869 («si» 64,8 s) —y sus versiones y prueba-capas— quedaban sin salida: 409 «vuelve a aprobarlo» eternamente."""
    c = _copia(tmp_path, nombre, banco)
    llamadas = []
    monkeypatch.setattr(director.ia, "llamar", lambda *a, **k: llamadas.append(a))
    antes = [p["w"] for p in servidor._guion(c)["palabras"]]
    msg = machote.impedimento(c)
    assert msg and "Aprueba el guion nuevo" in msg and f"«{palabra}»" in msg.lower().replace(palabra.capitalize(), palabra)   # dice qué cambió
    assert not machote.guion_aprobado(c)                                              # la aprobación se borró
    reg = json.loads((c / "machote.json").read_text())["ajustes_tecnicos"][-1]
    assert reg["mismas_palabras"] is False and (reg["quitadas"] or reg["agregadas"])
    despues = [p["w"] for p in servidor._guion(c)["palabras"]]
    assert despues != antes                                                           # la app muestra el guion nuevo
    (c / "preferencias.json").write_text(json.dumps({"guion_aprobado": True}))        # la persona lo aprueba UNA vez
    assert machote.impedimento(c) is None and machote.guion_aprobado(c)               # y ya se puede dirigir: sin segundo 409
    assert llamadas == []


def test_reparar_cortes_del_cli_deja_el_guion_nuevo_pendiente_y_lo_dice(tmp_path):
    c = _copia(tmp_path, "sin-salida-c8866", C8866)
    r = machote.reparar_cortes(c, lambda m: None)
    assert r["estado"] == "guion_nuevo" and "Aprueba el guion nuevo" in r["mensaje"] and not machote.guion_aprobado(c)
    assert machote.reparar_cortes(c, lambda m: None)["estado"] == "estable"


def test_mismas_palabras_no_acepta_un_corte_que_se_come_medio_un_con_voz(tmp_path):
    """Caso del revisor: c8867, medio «un» (19 cuadros de voz). Las palabras no cambian, pero el montaje trae errores nuevos: se rechaza."""
    c = _copia(tmp_path, "medio-un-c8867", ((".energia.npy", "tests/banco/cine-c8867/.energia.npy"),))
    import numpy as np
    from estudio import voz
    ctx = montaje.contexto(c)
    viejos = json.loads((c / "machote.json").read_text())["cortes"]
    un = next(p for p in ctx.palabras if p["w"].lower().strip(",.") == "un" and abs(p["s"] - 25.82) < .01)
    fr = np.flatnonzero(ctx.oye[int(un["s"] / voz.HOP):int(un["e"] / voz.HOP) + 1]) + int(un["s"] / voz.HOP)
    assert len(fr) == 19
    nuevos = montaje._fusionar([list(x) for x in viejos] + [[round(fr[0] * voz.HOP, 3), round((fr[0] + len(fr) // 2) * voz.HOP, 3)]])
    assert not machote.cambia_palabras(c, nuevos) and machote._errores_nuevos(c, viejos, nuevos)
    antes = (c / "machote.json").read_text()
    assert not machote.actualizar_cortes(c, nuevos, lambda m: None) and (c / "machote.json").read_text() == antes


def test_el_guion_de_la_app_y_las_palabras_cortadas_usan_la_misma_regla(tmp_path):
    c = _copia(tmp_path, "sin-salida-c8866", C8866)
    mj = json.loads((c / "machote.json").read_text())
    app = [p["w"] for p in servidor._guion(c)["palabras"] if not p.get("fuera")]
    assert app == [p["w"] for p in machote.palabras_cortadas(c, mj)]


def test_impedimento_respeta_el_candado_del_director_y_las_escrituras_son_atomicas(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PROYECTOS", tmp_path)
    c = _copia(tmp_path, "sin-salida-c8866", C8866)
    antes = (c / "machote.json").read_text()
    lock = threading.Lock()
    monkeypatch.setitem(servidor._DIRIGIENDO, c.name, lock)
    with lock:
        assert "Ya se está dirigiendo" in servidor._impedimento(c) and (c / "machote.json").read_text() == antes   # no escribe
    assert servidor._impedimento(c)                                                                            # libre: reparar
    assert not list(c.glob("*.part"))                                                                          # temporal + os.replace


# ---------- ronda 6 ----------
@pytest.mark.parametrize("fixture,banco", [("glass-nuevo-10nov", ()), ("medio-un-c8867", ((".energia.npy", "tests/banco/cine-c8867/.energia.npy"),))])
def test_una_palabra_solo_queda_si_de_verdad_suena(tmp_path, fixture, banco):
    """Medido: «Y» 0,01 s a -57 dB, «Desde» y «Todo» 0,06 s (glass), «Es» 0,02 s y «le» 0,04 s (c8867) entraban al guion sin oírse."""
    c = _copia(tmp_path, fixture, banco)
    cortes = json.loads((c / "machote.json").read_text())["cortes"]
    ctx = montaje.contexto(c)
    for p in montaje.quedan(ctx, cortes):
        centro = (p["s"] + p["e"]) / 2
        assert montaje._voz_de(ctx, p) >= montaje.VOZ_PALABRA_MIN or not any(a <= centro <= b for a, b in cortes), p
    sordas = [p["w"] for p in ctx.palabras if montaje._voz_de(ctx, p) < montaje.VOZ_PALABRA_MIN and any(a <= (p["s"] + p["e"]) / 2 <= b for a, b in cortes)]
    assert sordas and not set(map(id, [p for p in montaje.quedan(ctx, cortes) if p["w"] in sordas and any(a <= (p["s"] + p["e"]) / 2 <= b for a, b in cortes)]))


def test_escrituras_concurrentes_sin_errores_ni_lecturas_a_medias(tmp_path):
    f = tmp_path / "machote.json"
    machote._guardar(f, {"n": 0, "relleno": "x" * 5000})
    errores, leidas = [], []

    def escribir(k):
        try:
            for i in range(60):
                machote._guardar(f, {"n": k * 100 + i, "relleno": "x" * 5000})
        except Exception as e:  # noqa: BLE001
            errores.append(e)

    def leer():
        try:
            for _ in range(200):
                leidas.append(json.loads(f.read_text())["relleno"] == "x" * 5000)
        except Exception as e:  # noqa: BLE001
            errores.append(e)
    hilos = [threading.Thread(target=escribir, args=(k,)) for k in range(4)] + [threading.Thread(target=leer) for _ in range(2)]
    [h.start() for h in hilos]
    [h.join() for h in hilos]
    assert errores == [] and all(leidas) and not list(tmp_path.glob("*.part"))


def test_impedimento_toma_el_candado_mientras_corre(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PROYECTOS", tmp_path)
    c = tmp_path / "p1"
    c.mkdir()
    dentro, soltar, resultado = threading.Event(), threading.Event(), []

    def lento(carpeta):
        dentro.set()
        soltar.wait(5)
        return None
    monkeypatch.setattr(machote, "impedimento", lento)
    h = threading.Thread(target=lambda: resultado.append(servidor._impedimento(c)))
    h.start()
    assert dentro.wait(5)
    assert "Ya se está dirigiendo" in servidor._impedimento(c)      # otra petición no entra mientras corre
    soltar.set()
    h.join()
    assert resultado == [None] and servidor._impedimento(c) is None   # y el candado se suelta


def test_get_guion_no_escribe_ni_mide_audio(tmp_path):
    c = tmp_path / "p"
    c.mkdir()
    (c / "palabras.json").write_text(json.dumps([{"w": "Hola", "s": 0.0, "e": .4}, {"w": "ehh", "s": 1.0, "e": 1.3}]))
    (c / "machote.json").write_text(json.dumps({"cortes": [[.9, 1.5]]}))
    assert servidor._guion(c)["texto"] == "Hola"
    assert sorted(f.name for f in c.iterdir()) == ["machote.json", "palabras.json"]


def test_la_app_vuelve_a_mostrar_el_guion_tras_un_guion_nuevo():
    js = (config.RAIZ / "app" / "app.js").read_text()
    assert "r.guion_nuevo" in js and "pintarGuion()" in js[js.index("r.guion_nuevo"):js.index("r.guion_nuevo") + 200]
