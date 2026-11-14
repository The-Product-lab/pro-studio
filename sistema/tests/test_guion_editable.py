"""El guion lo corrige la persona (Pablo, 11-nov: «un mini editor de texto que me permita revisar qué deja y qué no, y decidir qué
dejar también… el problema de esos editores es que no mandan la orden al código: crea algo que sí sirva»). Lo que se prueba aquí es
justo eso: lo que la persona marca termina en los `cortes` de `machote.json` (lo que se renderiza), manda sobre el detector y sobre
la regla de la última toma, y lo que no se pudo cumplir se dice."""
import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import numpy as np
import pytest

from estudio import config, machote, montaje, servidor, voz
from test_machote import dos_tomas, sintetico

CALLADO = lambda m: None  # noqa: E731


def _guion(c):
    g = machote.guion_editable(c)
    return g, {p["k"] for p in g["palabras"] if p["queda"]}


def _texto(c):
    ctx = montaje.contexto(c)
    return " ".join(p["w"] for p in montaje.quedan(ctx, machote.cargar(c)["cortes"]))


def test_el_editor_muestra_todo_lo_dicho_con_el_motivo_de_lo_que_no_queda(tmp_path):
    c = dos_tomas(tmp_path)
    machote.decidir(c, con_ia=False, avance=CALLADO)
    g, quedan = _guion(c)
    assert [p["w"] for p in g["palabras"]][:5] == ["hola", "esto", "es", "una", "prueba"] and len(g["palabras"]) == 14
    assert quedan == set(range(5, 14))                                           # la primera toma no queda…
    assert {g["palabras"][k]["motivo"] for k in range(5)} == {"toma repetida: queda la última"}   # …y dice por qué
    assert g["frases"] == [[0, 5], [5, 10], [10, 14]] and g["problemas"] == []
    assert g["firma"] == montaje.firma_palabras(c)


def test_quitar_una_frase_la_saca_de_los_cortes_que_se_renderizan(tmp_path):
    c = dos_tomas(tmp_path)
    machote.decidir(c, con_ia=False, avance=CALLADO)
    (c / "preferencias.json").write_text(json.dumps({"guion_aprobado": True}))
    r = machote.editar_guion(c, range(5, 10), avance=CALLADO)                    # se va «gracias por ver esto»
    assert _texto(c) == "hola esto es una prueba" and r["no_se_pudo"] == [] and r["problemas"] == []
    mj = machote.cargar(c)
    assert any(a <= 9.0 and b >= 10.7 for a, b in mj["cortes"])                  # está en machote.json: es lo que corta el render
    assert mj["duracion_s"] < 2.5 and mj["persona"]["quito"] == 4
    assert not machote.guion_aprobado(c)                                          # guion nuevo: se aprueba de nuevo
    assert json.loads((c / montaje.PERSONA).read_text())["quitar"] == [10, 11, 12, 13]


def test_lo_editado_llega_al_storyboard_que_ya_existia(tmp_path):
    c = dos_tomas(tmp_path)
    mj = machote.decidir(c, con_ia=False, avance=CALLADO)
    (c / "storyboard.json").write_text(json.dumps({"cortes": mj["cortes"], "escenas": []}))
    machote.editar_guion(c, range(5, 10), avance=CALLADO)
    assert json.loads((c / "storyboard.json").read_text())["cortes"] == machote.cargar(c)["cortes"]


def test_la_toma_que_la_persona_escoge_manda_sobre_la_regla_de_la_ultima(tmp_path):
    c = dos_tomas(tmp_path)
    machote.decidir(c, con_ia=False, avance=CALLADO)
    r = machote.editar_guion(c, [0, 1, 2, 3, 4, 10, 11, 12, 13], avance=CALLADO)   # deja la PRIMERA toma y quita la última
    assert _texto(c) == "hola esto es una prueba gracias por ver esto"
    assert {p["k"] for p in r["palabras"] if p["queda"]} == {0, 1, 2, 3, 4, 10, 11, 12, 13}
    assert r["problemas"] == [] and machote.impedimento(c) is None                # no es «versión repetida»: ella la escogió
    antes = machote.cargar(c)["cortes"]
    assert machote.reparar_machote(c, CALLADO)["estado"] in ("estable", "ajustado")   # una reparación posterior no se la traga
    assert _texto(c) == "hola esto es una prueba gracias por ver esto" and len(machote.cargar(c)["cortes"]) == len(antes)


def _con_voz_baja(tmp_path):
    """El talento dice su frase a -20 dB y el llamado a la acción 22 dB más bajo: el detector lo toma por apuntador (IMG_4965)."""
    ps = [("hoy", 1.0, 1.3), ("te", 1.3, 1.5), ("cuento", 1.5, 2.0), ("tres", 2.0, 2.4), ("cosas", 2.4, 2.9), ("importantes", 2.9, 3.6),
          ("comenta", 6.0, 6.5), ("la", 6.5, 6.7), ("palabra", 6.7, 7.2), ("prestigio", 7.2, 7.9)]
    c = sintetico(tmp_path, 9, [(1, 3.6)], ps)
    db = np.load(c / ".energia.npy").astype(np.float32)
    db[int(6.0 / voz.HOP):int(7.9 / voz.HOP)] = -42.0
    np.save(c / ".energia.npy", db.astype(np.float16))
    return c


def test_lo_que_el_detector_tomo_por_otra_persona_se_puede_devolver(tmp_path):
    c = _con_voz_baja(tmp_path)
    machote.decidir(c, con_ia=False, avance=CALLADO)
    g, quedan = _guion(c)
    assert quedan == set(range(6))                                                # el llamado a la acción se perdió…
    assert g["palabras"][6]["motivo"].startswith("sonaba muy baja") and g["palabras"][6]["baja"]   # …y la pantalla dice por qué
    r = machote.editar_guion(c, range(10), avance=CALLADO)
    assert _texto(c).endswith("comenta la palabra prestigio") and r["no_se_pudo"] == []
    assert not any("voz fuera" in e for e in montaje.errores({"cortes": machote.cargar(c)["cortes"]}, c))   # ya es del talento
    assert not any(a < 7.5 and b > 6.2 for a, b in machote.cargar(c)["cortes"])   # su voz está en el video que se renderiza
    r = machote.editar_guion(c, range(6), avance=CALLADO)                         # y si se arrepiente, se vuelve a ir
    assert _texto(c) == "hoy te cuento tres cosas importantes"


def test_las_decisiones_valen_solo_para_la_transcripcion_en_que_se_tomaron(tmp_path):
    c = _con_voz_baja(tmp_path)
    machote.decidir(c, con_ia=False, avance=CALLADO)
    machote.editar_guion(c, range(10), avance=CALLADO)
    assert montaje.decisiones(c)["dejar"] == {6, 7, 8, 9}
    ps = json.loads((c / "palabras.json").read_text())
    (c / "palabras.json").write_text(json.dumps(ps[1:]))                          # otra transcripción: los índices ya no son esos
    assert montaje.decisiones(c) == {"dejar": set(), "quitar": set()}
    (c / "palabras.json").write_text(json.dumps(ps))
    machote.decidir(c, con_ia=False, avance=CALLADO)                              # decidir de nuevo = guion nuevo, sin marcas viejas
    assert not (c / montaje.PERSONA).exists()


def test_una_palabra_sin_nada_que_oir_queda_o_no_segun_lo_que_marco_la_persona(tmp_path):
    """IMG_4965: «y» (0,4 s a -65 dB) antes de «vas a volver»: en su sitio no suena nada y el audio no puede decidir."""
    ps = [("antes", 1.0, 1.6), ("y", 3.0, 3.4), ("vas", 3.4, 3.8), ("a", 3.8, 4.0), ("volver", 4.0, 4.6)]
    c = sintetico(tmp_path, 6, [(1, 1.6), (3.4, 4.6)], ps)
    pausa = [[1.7, 3.35]]
    assert montaje.palabras_que_quedan(montaje.contexto(c), pausa) == [0, 2, 3, 4]                 # sin marca: su punto medio, como siempre
    (c / montaje.PERSONA).write_text(json.dumps({"firma": montaje.firma_palabras(c), "dejar": [1], "quitar": []}))
    assert montaje.palabras_que_quedan(montaje.contexto(c), pausa) == [0, 1, 2, 3, 4]              # la persona la dejó: queda en el texto
    (c / montaje.PERSONA).write_text(json.dumps({"firma": montaje.firma_palabras(c), "dejar": [], "quitar": [1]}))
    assert montaje.palabras_que_quedan(montaje.contexto(c), []) == [0, 2, 3, 4]                    # la quitó: no sale en el texto


def test_el_guion_no_puede_quedar_vacio(tmp_path):
    c = dos_tomas(tmp_path)
    antes = machote.decidir(c, con_ia=False, avance=CALLADO)["cortes"]
    with pytest.raises(ValueError, match="vacío"):
        machote.editar_guion(c, [], avance=CALLADO)
    assert machote.cargar(c)["cortes"] == antes and not (c / montaje.PERSONA).exists()


def test_los_problemas_se_dicen_en_cristiano_y_en_su_palabra(tmp_path):
    c = dos_tomas(tmp_path)
    ctx = montaje.contexto(c)
    ps = machote._problemas(ctx, [
        "montaje: voz fuera de cámara «vas» en 5.40 s quedó en el video: córtala",
        "montaje: el fin del tramo 0.00–6.90 s corta con voz sonando: mueve el corte a un silencio",
        "montaje: el tramo 0.00–6.90 s termina 0.00 s después de «prueba»: deja al menos 0.08 s para que la palabra termine",
        "montaje: hay 1.39 s de silencio en el video final (en 17.0 s del editado, 9.3 s del original): máx. 0.2 s",
        "montaje: quedan versiones repetidas (queda solo la ÚLTIMA): 1.00–2.90 s «hola esto es una prueba» (repite una idea…)",
        "machote: dura 130 s y el máximo del reel es 110 s"])
    assert [x["k"] for x in ps] == [6, 9, 10, 0, None]                            # dos avisos de la misma palabra = uno
    assert "tócala para dejarla" in ps[0]["texto"] and "mochada" in ps[1]["texto"] and "pausa de 1.39 s" in ps[2]["texto"]
    assert "repites más adelante" in ps[3]["texto"] and ps[4]["texto"].startswith("dura 130 s")
    assert not any("montaje:" in x["texto"] or "tramo" in x["texto"] for x in ps)  # nada de jerga en pantalla


# ---------- por la app: la pantalla manda la orden y recibe los cortes ya hechos ----------

@pytest.fixture
def api(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PROYECTOS", tmp_path)
    srv = ThreadingHTTPServer(("127.0.0.1", 0), servidor.Manejador)
    threading.Thread(target=srv.serve_forever, daemon=True).start()

    def pedir(ruta, cuerpo=None):
        req = urllib.request.Request(f"http://127.0.0.1:{srv.server_address[1]}{ruta}",
                                     json.dumps(cuerpo).encode() if cuerpo is not None else None, {"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())
    yield pedir
    srv.shutdown()


def test_por_la_app_la_correccion_se_aplica_y_el_guion_que_vuelve_es_el_cortado(api, tmp_path):
    c = dos_tomas(tmp_path)
    machote.decidir(c, con_ia=False, avance=CALLADO)
    g = api("/api/guion/p")[1]
    assert g["listo"] and g["texto"] == "hola esto es una prueba gracias por ver esto" and len(g["edicion"]["palabras"]) == 14
    cod, r = api("/api/guion-editar", {"proyecto": "p", "firma": g["edicion"]["firma"], "quedan": [5, 6, 7, 8, 9]})
    assert cod == 200 and r["ok"] and [p["k"] for p in r["edicion"]["palabras"] if p["queda"]] == [5, 6, 7, 8, 9]
    assert api("/api/guion/p")[1]["texto"] == "hola esto es una prueba"            # lo que se aprueba es lo que se corta
    assert api("/api/seleccion", {"proyecto": "p", "guion_aprobado": True})[0] == 200 and machote.guion_aprobado(c)


def test_por_la_app_no_se_aplica_sobre_otro_guion_ni_se_deja_vacio(api, tmp_path):
    c = dos_tomas(tmp_path)
    antes = machote.decidir(c, con_ia=False, avance=CALLADO)["cortes"]
    cod, r = api("/api/guion-editar", {"proyecto": "p", "firma": "otra", "quedan": [5]})
    assert cod == 409 and r["guion_nuevo"] and machote.cargar(c)["cortes"] == antes
    firma = montaje.firma_palabras(c)
    assert api("/api/guion-editar", {"proyecto": "p", "firma": firma, "quedan": []})[0] == 400
    assert api("/api/guion-editar", {"proyecto": "no-existe", "firma": firma, "quedan": [1]})[0] == 404
    lock = servidor._DIRIGIENDO.setdefault("p", threading.Lock())
    with lock:                                                                     # con el director corriendo no se toca el guion
        assert api("/api/guion-editar", {"proyecto": "p", "firma": firma, "quedan": [5]})[0] == 409
    assert machote.cargar(c)["cortes"] == antes


def test_la_pantalla_manda_la_correccion_al_motor_y_no_aprueba_con_cambios_sin_aplicar():
    js = (Path(servidor.APP) / "app.js").read_text() if hasattr(servidor, "APP") else (config.RAIZ / "app" / "app.js").read_text()
    assert '"/api/guion-editar", { proyecto, firma: G.firma, quedan: [...guiQuiere] }' in js
    assert '$("#guiOk").disabled = !!cambios || generales.length > 0' in js and "con_detalles: !!G" in js
    assert "guiCargar(r.edicion" in js                                             # pinta lo que el motor cortó, no lo que ella marcó


def _pegadas(tmp_path):
    """Dos frases dichas de corrido, sin pausa entre ellas (IMG_4955: «…a qué te dedicas si tú eres psicólogo, no le vas a…»)."""
    ps = [("a", 1.0, 1.1), ("qué", 1.1, 1.3), ("te", 1.3, 1.5), ("dedicas", 1.5, 2.0), ("si", 2.0, 2.2), ("eres", 2.2, 2.5),
          ("psicólogo", 2.5, 3.1), ("no", 3.1, 3.3), ("le", 3.3, 3.5), ("vas", 3.5, 3.8), ("a", 3.8, 3.9), ("decir", 3.9, 4.4)]
    c = sintetico(tmp_path, 6, [(1, 4.4)], ps)
    machote.decidir(c, con_ia=False, avance=CALLADO)
    machote.editar_guion(c, [0, 1, 2, 3, 7, 8, 9, 10, 11], avance=CALLADO)      # quita «si eres psicólogo»: no hay silencio donde cortar
    return c


def test_un_detalle_de_montaje_no_deja_el_guion_sin_salida_la_persona_puede_aprobarlo_asi(api, tmp_path):
    c = _pegadas(tmp_path)
    assert machote.guion_editable(c)["problemas"] and machote.impedimento(c)       # el detalle se señala…
    assert api("/api/seleccion", {"proyecto": "p", "guion_aprobado": True})[0] == 409   # …y sin verlo no se aprueba
    assert api("/api/seleccion", {"proyecto": "p", "guion_aprobado": True, "con_detalles": True})[0] == 200   # viéndolo, sí: ella decide
    assert machote.guion_aprobado(c) and machote.impedimento(c) is None and machote.tolera_montaje(c)   # y el director y el render lo respetan


def test_aprobar_asi_vale_solo_para_ese_guion_y_nunca_salta_el_tope(api, tmp_path, monkeypatch):
    c = _pegadas(tmp_path)
    machote.aceptar_detalles(c)
    machote.editar_guion(c, [0, 1, 2, 3, 8, 9, 10, 11], avance=CALLADO)           # otro guion: lo aceptado ya no vale
    assert not machote.tolera_montaje(c)
    machote.aceptar_detalles(c)
    monkeypatch.setattr(machote, "LIMITE_S", 1)                                    # el tope de duración no se acepta «así»
    assert "máximo" in machote.impedimento(c)
    assert api("/api/seleccion", {"proyecto": "p", "guion_aprobado": True, "con_detalles": True})[0] == 409


def test_corregir_la_ortografia_de_una_palabra_no_suelta_lo_que_la_persona_dejo_ni_su_aprobacion(tmp_path):
    """12-nov (video-3217): «Cádiz» → «detalles» con el mini editor cambiaba la huella de la transcripción; la «y» que la persona
    dejó se perdía, el guion pedía aprobarse otra vez y la compuerta del render volvía a bloquear lo ya aceptado."""
    ps = [("antes", 1.0, 1.6), ("y", 3.0, 3.4), ("vas", 3.4, 3.8), ("a", 3.8, 4.0), ("volver", 4.0, 4.6)]
    c = sintetico(tmp_path, 6, [(1, 1.6), (3.4, 4.6)], ps)
    pausa = [[1.7, 3.35]]
    (c / montaje.PERSONA).write_text(json.dumps({"firma": montaje.firma_palabras(c), "dejar": [1], "quitar": []}))
    machote._guardar(c / machote.ARCHIVO, {"cortes": pausa})
    machote.aceptar_detalles(c)
    assert machote.tolera_montaje(c)
    pal = json.loads((c / "palabras.json").read_text())
    pal[4]["w"] = "volvés"                                                       # solo la ortografía; los tiempos son los mismos
    (c / "palabras.json").write_text(json.dumps(pal))
    assert montaje.palabras_que_quedan(montaje.contexto(c), pausa) == [0, 1, 2, 3, 4]
    assert machote.tolera_montaje(c)
    pal[4]["e"] = 4.9                                                            # otra transcripción (otros tiempos): ya no valen
    (c / "palabras.json").write_text(json.dumps(pal))
    assert montaje.palabras_que_quedan(montaje.contexto(c), pausa) == [0, 2, 3, 4] and not machote.tolera_montaje(c)
