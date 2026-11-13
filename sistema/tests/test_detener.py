"""La app dice qué está haciendo y se le puede decir que no (Pablo, 11-nov): cada trabajo aparece en /api/actividad con su paso y
su tiempo, y /api/detener corta el proceso que tenga abierto y no deja arrancar el paso siguiente."""
import json
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from estudio import config, servidor, trabajo


@pytest.fixture
def api(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PROYECTOS", tmp_path)
    monkeypatch.setattr(servidor, "TRABAJOS", {})
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


def _esperar(cond, s=10):
    fin = time.time() + s
    while time.time() < fin and not cond():
        time.sleep(.05)
    assert cond()


def test_la_actividad_dice_que_corre_de_que_video_y_en_que_paso(api):
    soltar = threading.Event()

    def lento(avance):
        avance("[video] normalizando a vertical…")
        soltar.wait(10)
    tid = servidor._trabajo("preparar", lento, proyecto="mi-video")
    _esperar(lambda: api("/api/actividad")[1]["trabajos"] and api("/api/actividad")[1]["trabajos"][0]["paso"])
    t = api("/api/actividad")[1]["trabajos"][0]
    assert (t["id"], t["que"], t["proyecto"], t["paso"], t["deteniendo"]) == (tid, "Preparando tu video", "mi-video", "[video] normalizando a vertical…", False)
    soltar.set()
    _esperar(lambda: api("/api/actividad")[1]["trabajos"] == [])           # terminó: ya no figura


def test_detener_corta_el_proceso_abierto_y_el_trabajo_queda_detenido_no_en_error(api):
    hecho = []

    def largo(avance):
        avance("convirtiendo")
        trabajo.correr([sys.executable, "-c", "import time; time.sleep(60)"], check=True)   # el ffmpeg de un 4K
        hecho.append("siguió")                                               # nunca debe llegar aquí
    tid = servidor._trabajo("preparar", largo, proyecto="v")
    _esperar(lambda: trabajo._PROCESOS.get(tid))
    t0 = time.time()
    assert api("/api/detener", {"trabajo": tid})[0] == 200
    _esperar(lambda: servidor.TRABAJOS[tid]["estado"] != "corriendo")
    assert time.time() - t0 < 5 and servidor.TRABAJOS[tid]["estado"] == "detenido" and hecho == []
    assert servidor.TRABAJOS[tid]["log"][-1] == "Detenido: lo paraste tú."
    assert tid not in trabajo._DETENIDOS and tid not in trabajo._PROCESOS  # no deja rastro
    assert api("/api/detener", {"trabajo": tid})[0] == 404                 # ya no corre: no hay nada que detener


def test_detener_tambien_para_el_carril_del_video_y_el_paso_siguiente(api):
    """`preparar` lanza el video en otro hilo: es del mismo trabajo. Y lo que no tiene proceso abierto para en su siguiente aviso."""
    pasos, entro = [], threading.Event()

    def con_carril(avance):
        def carril():
            entro.set()
            try:
                for k in range(200):
                    time.sleep(.05)
                    avance(f"recorte {k}")
                    pasos.append(k)
            except trabajo.Detenido:   # como en `servidor._preparar`: el carril guarda su fallo y el hilo principal lo vuelve a ver
                pass
        h = threading.Thread(target=trabajo.heredar(carril))
        h.start()
        h.join()
        avance("fin")   # el hilo principal tampoco sigue
        pasos.append("fin")
    tid = servidor._trabajo("preparar", con_carril, proyecto="v")
    entro.wait(5)
    api("/api/detener", {"trabajo": tid})
    _esperar(lambda: servidor.TRABAJOS[tid]["estado"] == "detenido")
    assert "fin" not in pasos and len(pasos) < 20


def test_fuera_de_un_trabajo_correr_es_un_subprocess_run_normal():
    r = trabajo.correr([sys.executable, "-c", "print('hola')"], capture_output=True, text=True, check=True)
    assert r.stdout.strip() == "hola" and r.returncode == 0
    with pytest.raises(Exception):
        trabajo.correr([sys.executable, "-c", "raise SystemExit(3)"], check=True)


def test_la_barra_de_avisos_va_en_su_franja_y_no_tapa_botones():
    """Pablo, 12-nov: los avisos de abajo «están mal puestos porque aparecen sobre varias cosas», Exportar entre ellas. La barra ocupa
    su propia franja y la pantalla se encoge ese alto (--act-h, medido por actividad.js)."""
    from estudio import config
    css = (config.RAIZ / "app" / "vista.css").read_text()
    regla = css[css.index("#actividad{"):].split("}", 1)[0]
    assert "bottom:0" in regla and "left:0" in regla and "translate" not in regla
    assert ".app{height:calc(100vh - var(--act-h,0px))" in css
    assert '"--act-h"' in (config.RAIZ / "app" / "actividad.js").read_text()
