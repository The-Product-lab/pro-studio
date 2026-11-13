"""Pro Studio abre como app de escritorio (ventana propia) también en Mac; sin un navegador que sepa hacerlo, en el navegador normal."""
from estudio import servidor

URL = "http://127.0.0.1:8792"


def test_en_mac_abre_ventana_propia_con_el_navegador_que_haya():
    assert servidor.orden_ventana(URL, "darwin", lambda n: n == "Google Chrome") == \
        ["open", "-na", "Google Chrome", "--args", f"--app={URL}", "--window-size=1600,1000"]
    assert servidor.orden_ventana(URL, "darwin", lambda n: n == "Brave Browser")[2] == "Brave Browser"


def test_en_mac_sin_navegador_de_ventana_propia_se_usa_el_normal():
    assert servidor.orden_ventana(URL, "darwin", lambda n: False) is None


def test_fuera_de_mac_la_orden_de_siempre():
    assert servidor.orden_ventana(URL, "linux")[:4] == ["cmd.exe", "/c", "start", "chrome"]


def test_cerrar_solo_pregunta_si_hay_algo_corriendo():
    from estudio import ventana
    assert ventana.pregunta_cierre([]) is None
    assert "Editando (img-1)" in ventana.pregunta_cierre(["Editando (img-1)"])


def test_la_app_de_mac_es_el_mismo_proceso_que_lanza_el_dock(tmp_path):
    """Con `exec` el Dock muestra «Pro Studio» con su icono; lanzando otro proceso aparte mostraba el de Chrome o el de Python."""
    from estudio import config, escritorio
    escritorio._mac(lambda m: None, tmp_path)
    app = tmp_path / f"{config.NOMBRE_APP}.app" / "Contents"
    lanzador = (app / "MacOS" / "abrir").read_text()
    assert "\nexec .venv/bin/python" in lanzador and " servir " in lanzador and "nohup" not in lanzador
    assert "CFBundleIconFile" in (app / "Info.plist").read_text()


def test_la_ventana_no_se_pega_a_otra_copia_de_pro_studio(monkeypatch):
    """11-nov: una copia vieja del estudio ocupaba la dirección y la app nueva abrió su ventana sobre ella sin decir nada."""
    import io
    import json
    import urllib.error
    from estudio import config, servidor

    def contesta(cuerpo):
        return lambda url, timeout=0: io.BytesIO(json.dumps(cuerpo).encode())
    monkeypatch.setattr(servidor.urllib.request, "urlopen", contesta({"ok": True, "trabajos": [], "raiz": str(config.RAIZ)}))
    assert servidor._quien_sirve("http://x") == "esta"
    monkeypatch.setattr(servidor.urllib.request, "urlopen", contesta({"ok": True, "trabajos": [], "raiz": "/otra/carpeta"}))
    assert servidor._quien_sirve("http://x") == "otra"
    monkeypatch.setattr(servidor.urllib.request, "urlopen", contesta({"ok": True}))           # una versión que ni dice quién es
    assert servidor._quien_sirve("http://x") == "otra"

    def no_existe(url, timeout=0):
        raise urllib.error.HTTPError(url, 404, "no", {}, None)
    monkeypatch.setattr(servidor.urllib.request, "urlopen", no_existe)                        # la copia vieja: no conoce la ruta
    assert servidor._quien_sirve("http://x") == "otra"

    def nadie(url, timeout=0):
        raise ConnectionRefusedError()
    monkeypatch.setattr(servidor.urllib.request, "urlopen", nadie)
    assert servidor._quien_sirve("http://x") is None
    fuente = (config.RAIZ / "estudio" / "servidor.py").read_text()
    assert 'if quien == "otra":' in fuente and "ventana.avisar(OTRA_ABIERTA)" in fuente


def test_el_icono_es_minimalista_en_blanco_y_negro():
    """Pablo, 12-nov: el icono «muy minimalista, pero que sea negro y blanco»: solo dos tintas (y sus bordes suavizados), sin color."""
    from estudio import escritorio
    im = escritorio.dibujar_icono(256).convert("RGBA")
    visibles = [p[:3] for p in im.getdata() if p[3] == 255]
    assert visibles and all(max(p) - min(p) <= 3 for p in visibles)            # ningún píxel con color
    assert im.getpixel((2, 2))[3] == 0 and im.getpixel((128, 60))[3] == 255    # aire alrededor del cuadro, como los iconos de macOS
    claro = escritorio.dibujar_icono(256, "PS", negro=False).getpixel((128, 40))
    assert claro[0] > 240
