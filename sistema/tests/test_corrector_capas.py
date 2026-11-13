"""Corrector por capas: reglas (0 tokens), una llamada chica con IA falsa, derivación al agente y la ruta /api/corregir."""
import json
import time

import pytest

from estudio import capas, corrector_capas, ia, servidor

CASO = "cine-c8867"
T_K1 = 13.0            # segundo FUENTE donde está el texto «lo entrenas» (k1); el segundo del video final se calcula con los cortes


@pytest.fixture
def proyecto(banco, monkeypatch):
    monkeypatch.setattr(capas, "_errores", lambda sb, carpeta: [])
    monkeypatch.setattr(corrector_capas, "_render", lambda carpeta, avance: carpeta / "final.mp4")
    monkeypatch.setattr(ia, "llamar", lambda *a, **k: pytest.fail("las reglas no deben llamar a la IA"))
    return banco(CASO)


def _sb(p):
    return json.loads((p / "storyboard.json").read_text())


def _seg(p):
    return capas.salida_de(_sb(p), T_K1)


def _k1(p):
    return next(e for e in _sb(p)["elementos"] if e["id"] == "k1")


@pytest.mark.parametrize("frase, comprobar", [
    ("el título más grande", lambda e: e["lineas"][0]["tam"] == 150),
    ("achicá un poco la letra", lambda e: e["lineas"][0]["tam"] == 96),
    ("ponelo en amarillo, el texto", lambda e: e["lineas"][0]["color"] == "#FFE800"),
    ("subí el título", lambda e: e["y"] == 280),
    ('cambiá "lo entrenas" por "lo entrenás"', lambda e: e["lineas"][0]["texto"] == "lo entrenás"),
    ("que diga Claude", lambda e: e["lineas"][0]["texto"] == "Claude"),
    ("quitá el texto", None),
])
def test_reglas_de_texto_con_cero_tokens(proyecto, frase, comprobar):
    r = corrector_capas.corregir(proyecto, frase, _seg(proyecto))
    assert r["estado"] == "aplicado" and r["via"] == "reglas" and r["tokens"] == 0
    if comprobar:
        assert comprobar(_k1(proyecto))
    else:
        assert all(e["id"] != "k1" for e in _sb(proyecto)["elementos"])


def test_quitar_grafico_del_segundo(proyecto):
    sb = _sb(proyecto)
    sb["elementos"].append({"id": "g1", "tipo": "recorte", "src": "arte/x.png", "ancho": 400, "x": 540, "y": 700, "t0": 26.0, "t1": 28.0})
    (proyecto / "storyboard.json").write_text(json.dumps(sb))
    r = corrector_capas.corregir(proyecto, "sacá el gráfico", capas.salida_de(sb, 27.0))
    assert r["estado"] == "aplicado" and r["tokens"] == 0 and all(e["id"] != "g1" for e in _sb(proyecto)["elementos"])


def test_dos_graficos_a_la_vez_es_ambiguo_y_no_se_adivina(proyecto, monkeypatch):
    sb = _sb(proyecto)
    sb["elementos"] += [{"id": f"g{i}", "tipo": "recorte", "src": "arte/x.png", "ancho": 400, "x": 540, "y": 700, "t0": 26.0, "t1": 28.0} for i in (1, 2)]
    (proyecto / "storyboard.json").write_text(json.dumps(sb))
    assert corrector_capas.por_reglas(sb, [], "sacá el gráfico", capas.salida_de(sb, 27.0)) is None


def test_sacar_subtitulo_golpe_efectos_y_color(proyecto, camara_movil):
    seg = _seg(proyecto)
    assert corrector_capas.corregir(proyecto, "sacá el subtítulo", seg)["estado"] == "aplicado" and _sb(proyecto)["subtitulos"]["ocultar"]
    assert corrector_capas.corregir(proyecto, "metele un golpe de zoom", seg)["estado"] == "aplicado"
    assert T_K1 in _sb(proyecto)["punch"]
    assert corrector_capas.corregir(proyecto, "quitá el zoom", seg)["estado"] == "aplicado"
    assert corrector_capas.corregir(proyecto, "bajá los efectos de sonido")["estado"] == "aplicado"
    assert _sb(proyecto)["estilo"]["sfx"] == pytest.approx(0.28 / 1.5, abs=.01)
    assert corrector_capas.corregir(proyecto, "más contraste")["estado"] == "aplicado"
    assert _sb(proyecto)["estilo"]["color"]["ajustes"]["contraste"] == 0.15


def test_sacar_una_palabra_del_video(proyecto):
    pal = json.loads((proyecto / "palabras.json").read_text())
    sb = _sb(proyecto)
    i = next(i for i, p in enumerate(pal) if p["s"] > 20 and not any(a <= p["s"] <= b for a, b in sb["cortes"]))
    seg = capas.salida_de(sb, (pal[i]["s"] + pal[i]["e"]) / 2)
    r = corrector_capas.corregir(proyecto, "sacá esa palabra", seg)
    assert r["estado"] == "aplicado" and [pal[i]["s"], pal[i]["e"]] in _sb(proyecto)["cortes"]


def test_registro_capas_jsonl_con_antes_despues_tokens_y_segundos(proyecto):
    corrector_capas.corregir(proyecto, "el título más grande", _seg(proyecto))
    fila = json.loads((proyecto / "capas.jsonl").read_text().splitlines()[-1])
    assert fila["texto"] == "el título más grande" and fila["tokens"] == 0 and fila["segundos"] >= 0
    assert fila["operaciones"][0]["antes"] and fila["operaciones"][0]["despues"] and fila["estado"] == "aplicado"


def test_simular_no_toca_ni_registra(proyecto):
    antes = (proyecto / "storyboard.json").read_text()
    r = corrector_capas.corregir(proyecto, "el título más grande", _seg(proyecto), simular=True)
    assert r["estado"] == "simulado" and r["operaciones"][0]["op"] == "escalar"
    assert (proyecto / "storyboard.json").read_text() == antes and not (proyecto / "capas.jsonl").exists()


def test_gusto_general_y_musica_van_al_agente_sin_llamar_a_la_ia(proyecto):
    for frase in ("el título más grande, siempre", "bajá la música"):
        r = corrector_capas.corregir(proyecto, frase, _seg(proyecto))
        assert r["estado"] == "derivar" and r["tokens"] == 0 and r["motivo"]


# ---- la llamada chica (IA falsa)

def _ia_falsa(monkeypatch, respuesta: str, proyecto=None, tokens=1234):
    llamadas = []

    def llamar(prompt, modelo, cwd, herramientas="x", tope_usd=0, paso="", **k):
        llamadas.append({"prompt": prompt, "modelo": modelo, "herramientas": herramientas, "tope": tope_usd})
        with open(cwd / "costos.jsonl", "a") as f:
            f.write(json.dumps({"paso": paso, "tokens": {"input_tokens": tokens - 34, "output_tokens": 34}, "usd_equivalente": 0.02}) + "\n")
        return {"result": respuesta}
    monkeypatch.setattr(ia, "llamar", llamar)
    return llamadas


def test_una_sola_llamada_chica_ve_solo_lo_necesario(proyecto, monkeypatch):
    ll = _ia_falsa(monkeypatch, '{"operaciones":[{"op":"mover","id":"k1","dx":-100}]}')
    r = corrector_capas.corregir(proyecto, "corré eso hacia el borde", _seg(proyecto))
    assert r["estado"] == "aplicado" and r["via"] == "ia" and r["tokens"] == 1234 and r["usd"] == 0.02
    assert len(ll) == 1 and ll[0]["modelo"] == "sonnet" and ll[0]["herramientas"] == "" and ll[0]["tope"] == corrector_capas.TOPE_USD <= 0.3
    assert "lo entrenas" in ll[0]["prompt"] and "storyboard" not in ll[0]["prompt"].lower().replace("capas", "")
    assert len(ll[0]["prompt"]) < 6000                   # compacto: no se manda el storyboard entero
    assert json.loads((proyecto / "capas.jsonl").read_text().splitlines()[-1])["tokens"] == 1234


@pytest.mark.parametrize("respuesta, estado", [
    ('{"pregunta":"¿Cuál texto?"}', "pregunta"),
    ('{"derivar":"agente","motivo":"es de gusto"}', "derivar"),
    ('no es json', "derivar"),
    ('{"operaciones":[{"op":"inventada"}]}', "derivar"),
    ('{"operaciones":[{"op":"borrar","id":"no-existe"}]}', "rechazado"),
])
def test_respuestas_raras_de_la_ia_nunca_cambian_nada(proyecto, monkeypatch, respuesta, estado):
    _ia_falsa(monkeypatch, respuesta)
    antes = (proyecto / "storyboard.json").read_text()
    r = corrector_capas.corregir(proyecto, "arreglá eso raro", _seg(proyecto))
    assert r["estado"] == estado and (proyecto / "storyboard.json").read_text() == antes


def test_si_la_ia_falla_se_deriva(proyecto, monkeypatch):
    def rota(*a, **k):
        raise RuntimeError("claude falló")
    monkeypatch.setattr(ia, "llamar", rota)
    assert corrector_capas.corregir(proyecto, "arreglá eso raro", None)["estado"] == "derivar"


# ---- /api/corregir

@pytest.fixture
def api(proyecto, monkeypatch):
    """El servidor de verdad en un puerto libre, con el Agente Editor falso (anota con qué lo llamaron) y los proyectos en un temporal."""
    import threading
    from http.server import ThreadingHTTPServer

    from estudio import config
    monkeypatch.setattr(config, "PROYECTOS", proyecto.parent)
    llamadas = []
    monkeypatch.setattr(servidor.agente, "corregir", lambda texto, proyecto=None, avance=print: llamadas.append((texto, proyecto)) or {"resumen": "agente"})
    srv = ThreadingHTTPServer(("127.0.0.1", 0), servidor.Manejador)
    threading.Thread(target=srv.serve_forever, daemon=True).start()

    def pedir(cuerpo):
        import urllib.request
        rq = urllib.request.Request(f"http://127.0.0.1:{srv.server_port}/api/corregir", json.dumps(cuerpo).encode(), {"Content-Type": "application/json"})
        tid = json.load(urllib.request.urlopen(rq))["trabajo"]
        for _ in range(100):
            t = servidor.TRABAJOS[tid]
            if t["estado"] != "corriendo":
                return t
            time.sleep(.05)
        raise AssertionError("el trabajo no terminó")
    yield pedir, llamadas, proyecto.name
    srv.shutdown()


def test_api_prueba_capas_primero(api):
    pedir, agente, nombre = api
    t = pedir({"texto": "el título más grande", "proyecto": nombre, "segundo": _seg_de(nombre, api)})
    assert t["estado"] == "listo" and t["resultado"]["estado"] == "aplicado" and agente == []


def test_api_si_no_es_de_capa_llama_al_agente_como_siempre(api, monkeypatch):
    pedir, agente, nombre = api
    _ia_falsa(monkeypatch, '{"derivar":"agente","motivo":"gusto"}')
    t = pedir({"texto": "que se sienta más cinematográfico", "proyecto": nombre})
    assert t["estado"] == "listo" and agente == [("que se sienta más cinematográfico", nombre)]


def test_api_pregunta_no_cambia_nada_ni_llama_al_agente(api, monkeypatch):
    pedir, agente, nombre = api
    _ia_falsa(monkeypatch, '{"pregunta":"¿cuál?"}')
    t = pedir({"texto": "arreglá eso raro", "proyecto": nombre})
    assert t["resultado"]["pregunta"] == "¿cuál?" and agente == []


def test_api_bandera_apagada_es_exactamente_el_flujo_de_hoy(api, monkeypatch):
    """No degradar el editor: con ESTUDIO_CAPAS=0 /api/corregir llama al Agente Editor con (texto, proyecto) y nada más, sin tocar capas."""
    pedir, agente, nombre = api
    monkeypatch.setenv("ESTUDIO_CAPAS", "0")
    monkeypatch.setattr(corrector_capas, "intentar", lambda *a, **k: pytest.fail("con la bandera apagada no se prueba capas"))
    t = pedir({"texto": "el título más grande", "proyecto": nombre, "segundo": 5})
    assert t["estado"] == "listo" and t["resultado"] == {"resumen": "agente"} and agente == [("el título más grande", nombre)]


def test_api_sin_proyecto_va_al_agente(api):
    pedir, agente, _ = api
    pedir({"texto": "el título más grande"})
    assert agente == [("el título más grande", None)]


def test_api_render_que_falla_deshace_y_va_al_agente(api, monkeypatch, proyecto):
    pedir, agente, nombre = api
    antes = (proyecto / "storyboard.json").read_text()

    def falla(carpeta, avance):
        raise ValueError("la compuerta no deja renderizar")
    monkeypatch.setattr(corrector_capas, "_render", falla)
    t = pedir({"texto": "el título más grande", "proyecto": nombre, "segundo": _seg(proyecto)})
    assert t["estado"] == "listo" and len(agente) == 1 and (proyecto / "storyboard.json").read_text() == antes


def _seg_de(nombre, api):
    from estudio import config
    return capas.salida_de(json.loads((config.PROYECTOS / nombre / "storyboard.json").read_text()), T_K1)


def test_compuerta_relativa_solo_si_la_correccion_no_sumo_errores(tmp_path, monkeypatch):
    """Un video aprobado con avisos de reglas nuevas (p. ej. cámara viva) se re-exporta tras una corrección de capa que no sumó
    errores; si la última corrección no se aplicó, la compuerta sigue cerrada."""
    import json as _j
    from estudio import corrector_capas as cc, motor
    llamadas = []
    def render(carpeta, avance=print, forzar=False):
        llamadas.append(forzar)
        if not forzar:
            raise ValueError("la compuerta no deja renderizar:\n- cámara viva")
    monkeypatch.setattr(motor, "render", render)
    (tmp_path / cc.REGISTRO).write_text(_j.dumps({"estado": "aplicado", "errores": []}) + "\n")
    cc._render(tmp_path, lambda *_: None)
    assert llamadas == [False, True]
    llamadas.clear()
    (tmp_path / cc.REGISTRO).write_text(_j.dumps({"estado": "rechazado", "errores": ["x"]}) + "\n")
    try:
        cc._render(tmp_path, lambda *_: None)
    except ValueError:
        pass
    else:
        raise AssertionError("sin corrección aplicada no debe forzar")
    assert llamadas == [False]
