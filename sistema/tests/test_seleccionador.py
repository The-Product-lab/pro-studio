"""Seleccionador (docs/PLANO-SELECCIONADOR.md): catálogo vivo, muestras, guardado, compuerta del repertorio y enlaces."""
import json
import threading
import urllib.request
from http.server import ThreadingHTTPServer

import numpy as np
import pytest
from PIL import Image

from estudio import catalogo, color, config, director, efectos, motor, servidor, validar


def _cat(cid):
    return next(c for c in catalogo.catalogo(todas=True)["categorias"] if c["id"] == cid)   # todo lo que el motor sabe, se pregunte o no


def _ids(cid):
    return {o["id"] for o in _cat(cid)["opciones"]}


# ---------- fase 1: el catálogo sale del código ----------
def test_catalogo_es_lo_mismo_que_el_motor_y_la_compuerta():
    assert _ids("transiciones") == validar.ENTRADAS_ESCENA
    assert _ids("subtitulo") == validar.SUBTITULOS
    assert _ids("preset") == set(catalogo.presets()) - set(catalogo.OCULTOS)   # ocultos: vivos en el motor, fuera de la pantalla
    assert all(o in catalogo.presets() for o in catalogo.OCULTOS)   # Pablo 08-nov: la Mac solo interfaz; el motor no pierde estilos
    assert _ids("fuente") == _ids("fuente_script") == _ids("fuente_mono") == set(catalogo.fuentes())
    assert _ids("look") == {l["id"] for l in color.looks()}
    assert set(catalogo.permitidos_repertorio()) == set(validar.REPERTORIO_NOMBRES)
    assert _ids("filtros") == set(efectos.FILTROS) - {"ninguno"}
    assert _ids("cajas") == set(validar.RECURSOS) - catalogo.DATOS
    assert _ids("hooks") == set(catalogo.hooks_aprobados()) and _ids("hooks") <= set(catalogo.HOOKS)
    assert _ids("efectos_mov") == catalogo.EFECTOS_DE_MOVIMIENTO
    for borrada in ("textos", "entradas", "persona", "entrada", "efectos_color", "datos", "trazos", "tratamientos", "fondos", "sonido_paleta", "receta"):
        assert borrada not in {c["id"] for c in catalogo.catalogo()["categorias"]}, borrada   # tanda 3: Pablo las quitó del seleccionador
    assert "destello" not in validar.RECURSOS          # prohibido por Pablo: no se ofrece


def test_lo_que_decide_opus_no_se_pregunta_en_pantalla_pero_sigue_en_el_motor():
    """Pablo (11-nov): «quiero dejar varias cosas que las decida Opus y no yo… tipografías básicas y ya; eso de conectores, datos,
    acento, cajas y etiquetas, transiciones, cámara y flotación, quitar»."""
    pantalla = {c["id"] for c in catalogo.catalogo()["categorias"]}
    todo = {c["id"] for c in catalogo.catalogo(todas=True)["categorias"]}
    quitadas = {"fuente_script", "fuente_mono", "cajas", "transiciones", "efectos_mov"}
    assert quitadas == set(catalogo.FUERA_DE_PANTALLA) and not quitadas & pantalla and quitadas <= todo
    assert [c for c in pantalla if c.startswith("fuente")] == ["fuente"]          # una sola letra a elegir: la de títulos
    for html in ("app.js", "seleccionador.html"):                                 # y las pantallas no las nombran por su cuenta
        fuente = (config.RAIZ / "app" / html).read_text()
        assert "fuente_script" not in fuente and "fuente_mono" not in fuente, html


def test_estilos_aprobados_primero_y_paletas_de_los_estilos():
    est = _cat("preset")["opciones"]
    apro = [a for a in catalogo.PRIMEROS if a in catalogo.presets()] + [a for a in catalogo.aprobados() if a not in catalogo.PRIMEROS]   # Básico siempre primero
    apro = [a for a in apro if a not in catalogo.OCULTOS]
    assert [o["id"] for o in est[:len(apro)]] == [a for a in apro if a in catalogo.presets()]
    assert all(o["aprobado"] for o in est[:len(apro)]) and not any(o["aprobado"] for o in est[len(apro):])
    for o in _cat("paleta")["opciones"]:
        p = catalogo.presets()[o["id"]]
        assert all(p[k].upper() == v and not validar.es_rosa(v) for k, v in o["colores"].items())
    assert len(_ids("look")) == len(color.looks())   # los looks de esta máquina, todos


def test_tipos_de_hook_salen_de_las_copias_aprobadas():
    assert "caja-hook" in catalogo.tipos_de_hook(catalogo._ejemplo("prestiggio"))
    pregunta = {"escenas": [{"t0": 0.0}], "elementos": [{"tipo": "texto", "t0": 1.0, "lineas": [{"texto": "¿Y tu celular?", "tam": 120}]}]}
    assert catalogo.tipos_de_hook(pregunta) == ["pregunta"]
    gigante = {"escenas": [{"t0": 0.0, "entrada": "iris"}],
               "elementos": [{"tipo": "texto", "t0": 0.5, "lineas": [{"texto": "CELULAR", "tam": 220}]},
                             {"tipo": "texto", "t0": 9.0, "lineas": [{"texto": "lejos", "tam": 50}]}]}
    assert catalogo.tipos_de_hook(gigante) == ["palabra-gigante", "apertura"]
    assert catalogo.tipos_de_hook({}) == []
    for o in _cat("hooks")["opciones"]:   # cada tipo dice qué copias aprobadas abren así
        assert o["ejemplos_id"] and set(o["ejemplos_id"]) <= set(catalogo.aprobados())


def test_lo_nuevo_del_motor_aparece_solo(monkeypatch):
    monkeypatch.setattr(validar, "ENTRADAS_ESCENA", validar.ENTRADAS_ESCENA | {"nueva"})
    assert "nueva" in _ids("transiciones")


def test_cada_clave_elegible_la_conoce_el_motor():
    for k in validar.APOYO_CLAVES:
        assert k in validar.CLAVES["elemento"]
    est = motor.Estilo({})
    for k, *_ in catalogo.EFECTOS + catalogo.INTERRUPTORES:
        assert k in validar.CLAVES["estilo"] and hasattr(est, k)
    for c in catalogo.catalogo()["categorias"]:
        if c["destino"] == "estilo" and not c.get("valores"):
            assert c["clave"] in validar.CLAVES["estilo"]


def test_cada_tratamiento_cambia_la_imagen_en_el_motor(tmp_path):
    rng = np.random.default_rng(0)
    Image.fromarray(rng.integers(0, 255, (120, 160, 3), dtype=np.uint8)).save(tmp_path / "a.png")
    est = motor.Estilo({"base": "pantalla"})
    base = {"id": "a", "tipo": "foto", "src": "a.png", "ancho": 160, "x": 540, "y": 900, "t0": 0, "t1": 1, "gris": False}
    sin = np.asarray(motor.Elemento(dict(base), est, tmp_path).img)
    for t in motor.TRATAMIENTOS:
        con = np.asarray(motor.Elemento({**base, "tratamiento": t}, est, tmp_path).img)
        assert con.shape != sin.shape or np.abs(con.astype(int) - sin).mean() > 1, t


# ---------- fase 2: cada opción se ve ----------
def test_cada_opcion_tiene_muestra_o_aviso_claro():
    for c in catalogo.catalogo()["categorias"]:
        for o in c["opciones"]:
            assert o.get("muestra") or o.get("hex") or o.get("fuente") or o.get("colores") or "muestras" in o.get("aviso", "") \
                or "video final" in o.get("aviso", ""), (c["id"], o["id"])


@pytest.mark.skipif(not (config.PROYECTOS / "c8866" / "fuente.json").exists(), reason="sin el C8866 preparado en esta máquina")
def test_cada_opcion_visual_tiene_su_pedido_de_muestra():
    from estudio import muestras
    pedidos = {(c, o) for c, o, *_ in muestras.pedidos()}
    nombre = {"transiciones": "transicion", "efectos_mov": "efecto", "filtros": "filtro",
              "cajas": "recurso", "hooks": "hook"}
    for c in catalogo.catalogo()["categorias"]:
        if c["id"] in ("acento", "acento2", "papel", "borde", "paleta", "fuente", "fuente_script", "fuente_mono"):
            continue   # se ven en la misma tarjeta: el color y la letra
        for o in c["opciones"]:
            if c["id"] == "hooks" and not muestras._final_hook(o.get("ejemplos_id") or []):
                continue   # sin una copia aprobada de ese hook en esta máquina no hay de dónde sacar la muestra
            ya = c["id"] == "preset" and (catalogo.MUESTRAS / f"{o['id']}.jpg").exists()
            assert ya or (nombre.get(c["id"], "estilo" if c["id"] == "preset" else c["id"]), o["id"]) in pedidos, (c["id"], o["id"])
    for c, o, clase, dato in muestras.pedidos():   # lo que se renderiza es un storyboard que el motor sabe leer
        if clase != "estilo":
            assert not [e for e in validar.errores(dato) if "el motor no conoce" in e or "no existe" in e], (c, o)


def test_cada_muestra_en_video_trae_su_poster_y_su_version():
    for c in catalogo.catalogo()["categorias"]:
        for o in c["opciones"]:
            m = o.get("muestra") or ""
            if ".mp4" in m and c["id"] != "preset":
                assert o.get("poster") and "?v=" in o["poster"], (c["id"], o["id"])
            if m:
                assert "?v=" in m   # la URL cambia si la muestra se rehace: el navegador la guarda sin miedo


def test_catalogo_cacheado_se_rehace_si_cambia_algo(tmp_path, monkeypatch):
    a = catalogo.catalogo_cacheado()
    assert catalogo.catalogo_cacheado() is a
    monkeypatch.setattr(catalogo, "_firma", lambda: ("otra",))
    assert catalogo.catalogo_cacheado() is not a


def test_nombre_de_muestra_seguro_para_el_disco():
    assert catalogo.archivo_muestra("look", "mio:mi lut/1") == "look-mio_mi_lut_1"


# ---------- fase 3: guardar en preferencias.json (mezcla, no pisa) ----------
@pytest.fixture
def proyecto(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PROYECTOS", tmp_path)
    d = tmp_path / "v1"
    d.mkdir()
    (d / "fuente.json").write_text(json.dumps({}))
    (d / "preferencias.json").write_text(json.dumps({"estilo": {"color": {"receta": "pablo"}}, "otra": 1}))
    return d


def test_guardar_mezcla_y_libre_borra(proyecto):
    r = catalogo.guardar(proyecto, {"estilo": {"acento": "#FFE800"}, "repertorio": {"transiciones": ["wipe"]}, "preset": "swiss"})
    p = json.loads((proyecto / "preferencias.json").read_text())
    assert p["estilo"] == {"color": {"receta": "pablo"}, "acento": "#FFE800"} and p["otra"] == 1
    assert p["repertorio"] == {"transiciones": ["wipe"]} and p["preset"] == "swiss" and r["preferencias"] == p
    catalogo.guardar(proyecto, {"estilo": {"acento": None}, "repertorio": {"transiciones": []}, "preset": None})
    p = json.loads((proyecto / "preferencias.json").read_text())
    assert p == {"estilo": {"color": {"receta": "pablo"}}, "otra": 1}


@pytest.mark.parametrize("malo", [{"estilo": {"acento": "#FF4FA3"}}, {"estilo": {"acento": "amarillo"}}, {"estilo": {"fuente": "Comic"}},
                                  {"estilo": {"grano": 900}}, {"estilo": {"inventado": 1}}, {"repertorio": {"transiciones": ["teletransporte"]}},
                                  {"repertorio": {"camaras": ["push"]}}, {"preset": "no-existe"}, {"estilo": {"color": {"look": "x"}}},
                                  {"repertorio": {"entradas": "pop"}}])
def test_lo_que_no_existe_no_se_guarda(proyecto, malo):
    antes = (proyecto / "preferencias.json").read_text()
    with pytest.raises(ValueError):
        catalogo.guardar(proyecto, malo)
    assert (proyecto / "preferencias.json").read_text() == antes


def test_guardar_paleta_y_repertorios_nuevos(proyecto):
    pal = _cat("paleta")["opciones"][0]
    catalogo.guardar(proyecto, {"estilo": pal["colores"], "repertorio": {"hooks": ["caja-hook"], "recursos": ["vidrio"],
                                                                      "textos": ["hueca"], "trazos": ["linea"], "filtros": ["bn"]}})
    p = json.loads((proyecto / "preferencias.json").read_text())
    assert all(p["estilo"][k] == v for k, v in pal["colores"].items())
    assert p["repertorio"]["recursos"] == ["vidrio"] and p["repertorio"]["hooks"] == ["caja-hook"]
    with pytest.raises(ValueError):
        catalogo.guardar(proyecto, {"repertorio": {"recursos": ["destello"]}})


def test_con_storyboard_se_aplica_como_personalizar_y_el_director_lo_respeta(proyecto):
    sb = {"estilo": {"id": "swiss", "acento": "#000000"}, "escenas": [{"t0": 0.0, "entrada": "zoom"}], "elementos": []}
    (proyecto / "storyboard.json").write_text(json.dumps(sb))
    r = catalogo.guardar(proyecto, {"estilo": {"acento": "#3DDC84", "grano": 10}, "repertorio": {"transiciones": ["wipe"]}})
    assert json.loads((proyecto / "storyboard.json").read_text())["estilo"]["acento"] == "#3DDC84"
    assert any("zoom" in a for a in r["avisos"])          # el video actual se sale de lo elegido: se avisa, no se rompe
    servidor._guardar_estilo(proyecto, {"acento": "#FFFFFF"})   # Personalizar sigue igual
    assert json.loads((proyecto / "storyboard.json").read_text())["estilo"]["acento"] == "#FFFFFF"
    director._fijar_estilo(proyecto, "swiss")              # al dirigir, lo elegido manda sobre el preset
    est = json.loads((proyecto / "storyboard.json").read_text())["estilo"]
    assert est["acento"] == "#3DDC84" and est["grano"] == 10 and est["color"]["receta"] == "pablo"


def test_la_api_del_seleccionador(proyecto):
    srv = ThreadingHTTPServer(("127.0.0.1", 0), servidor.Manejador)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{srv.server_address[1]}"

    def pedir(ruta, cuerpo=None):
        req = urllib.request.Request(url + ruta, json.dumps(cuerpo).encode() if cuerpo is not None else None,
                                     {"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            return e.read()
    try:
        assert "Edición avanzada".encode() in pedir("/seleccionador")
        assert json.loads(pedir("/api/catalogo"))["categorias"]
        assert json.loads(pedir("/api/seleccion", {"proyecto": "v1", "repertorio": {"entradas": ["llega"]}}))["ok"]
        assert json.loads(pedir("/api/seleccion/v1"))["preferencias"]["repertorio"] == {"entradas": ["llega"]}
        assert not json.loads(pedir("/api/seleccion", {"proyecto": "v1", "estilo": {"acento": "rosa"}}))["ok"]
        assert not json.loads(pedir("/api/seleccion", {"proyecto": "../afuera", "estilo": {}}))["ok"]
        # un proyecto que es un enlace a otro disco (el lote deja lo pesado en C:) sale en la lista y se abre
        otro = proyecto.parent.parent / "otro-disco"
        otro.mkdir()
        (otro / "fuente.json").write_text("{}")
        (proyecto.parent / "v2").symlink_to(otro, target_is_directory=True)
        ids = [p["id"] for p in json.loads(pedir("/api/proyectos?ligero=1"))["proyectos"]]
        assert set(ids) == {"v1", "v2"} and json.loads(pedir("/api/proyectos"))["ok"]
        assert json.loads(pedir("/api/seleccion/v2"))["ok"]
        assert not json.loads(pedir("/api/seleccion/..%2Fafuera"))["ok"]
        assert b"no existe" in pedir("/app/..%2F..%2Fpyproject.toml") or b"inv" in pedir("/app/..%2F..%2Fpyproject.toml")
        lib = json.loads(pedir("/api/librerias"))
        assert all(k.split(":")[0] in ("look", "receta", "color", "persona") and ".jpg" in v for k, v in lib["muestras"].items())
    finally:
        srv.shutdown()


# ---------- fase 4: el director y la compuerta leen el repertorio ----------
def _sb(**extra):
    sb = {"estilo": {"base": "pantalla", "fuente": "Montserrat"}, "escenas": [{"t0": 0.0}], "elementos": [], "subtitulos": {"y": 1450}}
    sb.update(extra)
    return sb


def _texto(i, entra=None, y=600):
    d = {"id": f"t{i}", "tipo": "texto", "x": 540, "y": y, "t0": i * 2.0, "t1": i * 2.0 + 1.5,
         "lineas": [{"texto": "hola", "rol": "display", "tam": 120}]}
    return {**d, "entra": entra} if entra else d


def _con_repertorio(tmp_path, rep):
    (tmp_path / "preferencias.json").write_text(json.dumps({"repertorio": rep}))
    return tmp_path


def test_fuera_de_lo_elegido_se_rechaza(tmp_path):
    c = _con_repertorio(tmp_path, {"transiciones": ["wipe"], "entradas": ["llega"], "tratamientos": ["fusion:pantalla"], "fondos": ["muro-luz"]})
    (tmp_path / "a.png").write_bytes(b"x")
    sb = _sb(escenas=[{"t0": 0.0}, {"t0": 2.0, "entrada": "zoom"}, {"t0": 4.0, "entrada": "wipe"}, {"t0": 5.0},
                      {"t0": 6.0, "persona": {"modo": "recorte", "fondo": "muro-claro"}}],
             elementos=[_texto(0, "pop"), _texto(1), _texto(2, "llega"),
                        {"id": "f", "tipo": "foto", "src": "a.png", "ancho": 500, "x": 540, "y": 900, "t0": 1, "t1": 2, "fundir": .5}])
    err = [e for e in validar.errores(sb, c) if "Pablo eligió" in e]
    assert any("escenas[1]" in e and "zoom" in e for e in err)
    assert not any("escenas[2]" in e or "escenas[3]" in e for e in err)       # lo elegido y el corte seco pasan
    assert any("«t0»" in e and "pop" in e for e in err) and any("«t1»" in e and "sin «entra» es «pop»" in e for e in err)
    assert not any("«t2»" in e for e in err)
    assert any("«f»" in e and "fundir" in e for e in err)
    assert any("escenas[4]" in e and "muro-claro" in e for e in err)
    assert len(err) == 5


def test_sin_repertorio_no_cambia_nada(tmp_path):
    sb = _sb(escenas=[{"t0": 0.0}, {"t0": 2.0, "entrada": "zoom"}], elementos=[_texto(0, "pop")])
    antes = validar.errores(sb, tmp_path)
    (tmp_path / "preferencias.json").write_text(json.dumps({"estilo": {"acento": "#FFE800"}}))
    assert validar.errores(sb, tmp_path) == antes
    _con_repertorio(tmp_path, {"transiciones": []})          # categoría vacía = libre
    assert validar.errores(sb, tmp_path) == antes
    (tmp_path / "preferencias.json").write_text("{roto")
    assert validar.errores(sb, tmp_path) == antes


def test_pocas_opciones_elegidas_no_chocan_con_la_variedad(tmp_path, monkeypatch):
    reglas = tmp_path / "reglas.json"
    reglas.write_text(json.dumps({"global": {"variedad": {"max_mismo_seguido": 2, "max_proporcion": .45, "min_tipos": 3}}}))
    monkeypatch.setattr(validar, "REGLAS", reglas)
    sb = _sb(elementos=[_texto(i, "llega", y=600) for i in range(5)])
    variedad = lambda c: [e for e in validar.consejos(sb, c) if "variedad (entrada de texto)" in e]  # noqa: E731  (variedad es guía desde el 10-nov)
    sin = tmp_path / "sin"
    sin.mkdir()
    assert variedad(sin)                                       # sin elegir: la variedad de siempre
    con = tmp_path / "con"
    con.mkdir()
    _con_repertorio(con, {"entradas": ["llega"]})
    assert variedad(con) == []                                 # Pablo eligió una sola: manda su elección
    _con_repertorio(con, {"entradas": ["llega", "pop"]})
    assert any("seguidas" in e for e in variedad(con)) and not any("tipos distintos" in e or "es el" in e for e in variedad(con))


def test_la_guia_del_director_dice_lo_que_eligio(tmp_path):
    assert director.guia_seleccion(tmp_path) == ""
    _con_repertorio(tmp_path, {"transiciones": ["wipe"], "tratamientos": ["fusion:pantalla", "fundir"]})
    g = director.guia_seleccion(tmp_path)
    assert "Pablo eligió para ESTE video" in g and '"wipe"' in g and '"fusion": "pantalla"' in g and '"fundir"' in g
    assert "no tienes que usarlo todo" in g and "libertad total" in g
    _con_repertorio(tmp_path, {"hooks": ["caja-hook"], "textos": ["hueca"]})
    g = director.guia_seleccion(tmp_path)
    assert "Caja del hook" in g and "prestiggio" in g and '"hueca" (letra hueca' in g


def test_compuerta_de_los_repertorios_nuevos(tmp_path):
    c = _con_repertorio(tmp_path, {"filtros": ["bn"], "trazos": ["linea"], "recursos": ["vidrio"], "textos": ["hueca"], "hooks": ["pregunta"]})
    sb = _sb(escenas=[{"t0": 0.0, "filtro": "termico"}, {"t0": 2.0, "filtro": "bn"}, {"t0": 3.0, "filtro": "ninguno"}],
             elementos=[{**_texto(0), "lineas": [{"texto": "hola", "rol": "display", "tam": 120, "extrusion": [8, "acento"]}]},
                        {**_texto(1), "lineas": [{"texto": "hola", "rol": "display", "tam": 120, "contorno": 5}]},
                        _texto(2),
                        {"id": "e", "tipo": "etiqueta", "lineas": [["x", 40, False, 700]], "x": 540, "y": 600, "t0": 1, "t1": 2, "radio": 12},
                        {"id": "v", "tipo": "vidrio", "x": 540, "y": 600, "t0": 1, "t1": 2}],
             trazos=[{"tipo": "rayos", "desde": [0, 0], "hacia": [[1, 1]], "t0": 1}, {"tipo": "linea", "puntos": [[0, 0], [1, 1]], "t0": 1}],
             cajas=[{"t0": 1, "t1": 2, "sobre": "cara"}])
    err = [e for e in validar._repertorio(sb, validar.repertorio(c))]
    assert any("escenas[0].filtro" in e and "termico" in e for e in err) and not any("escenas[1]" in e or "escenas[2]" in e for e in err)
    assert any("«t0»" in e and "extrusion" in e for e in err) and not any("«t1»" in e or "«t2»" in e for e in err)
    assert any("«e»" in e and "etiqueta-redondeada" in e for e in err) and not any("«v»" in e for e in err)
    assert any("trazos[0]" in e for e in err) and not any("trazos[1]" in e for e in err)
    assert any(e.startswith("cajas") and "caja-hud" in e for e in err)
    assert len(err) == 5                                  # el hook no se mide en la compuerta: lo dice la guía


def test_tipos_de_texto_y_recursos_de_un_elemento():
    assert validar.estilos_texto_de({"tipo": "etiqueta", "lineas": [["a", 40, True, 300]]}) == ["fina", "italica"]
    assert validar.estilos_texto_de({"tipo": "texto", "luz": .5, "tecleo": 9, "lineas": [{"texto": "a", "escala_y": 1.5}]}) == ["estirada", "luz", "tecleo"]
    assert validar.estilos_texto_de({"tipo": "texto", "lineas": [{"texto": "a", "tam": 90}]}) == []
    assert validar.recurso_de({"tipo": "barra", "direccion": "horizontal"}) == "barra-horizontal"
    assert validar.recurso_de({"tipo": "foto"}) is None and validar.recurso_de({"tipo": "destello"}) is None


# ---------- fase 5: se llega desde la app ----------
def test_enlaces_al_seleccionador():
    assert "/seleccionador" in (config.RAIZ / "app" / "app.js").read_text()
    assert "/seleccionador" in (config.RAIZ / "app" / "revision.html").read_text()


# ---------- mini módulo de color (Personalizar): ajustes básicos en la cadena del cubo ----------
def test_ajustes_de_color_en_cero_no_cambian_nada(tmp_path):
    assert color.cubo(tmp_path, {"ajustes": {k: 0 for k in color.AJUSTES}}) is None
    base = color.cubo(tmp_path, {"receta": "pablo"})
    otra = tmp_path / "otra"
    otra.mkdir()
    con_ceros = color.cubo(otra, {"receta": "pablo", "ajustes": {"contraste": 0}})
    assert np.allclose(color._leer_cubo(base)[1], color._leer_cubo(con_ceros)[1])


def test_cada_ajuste_de_color_mueve_lo_que_dice(tmp_path):
    gris = np.array([[.45, .45, .45]])
    medir = lambda aj: color._aplicar_cubo(*color._leer_cubo(color.cubo(tmp_path, {"ajustes": aj})), gris)[0]  # noqa: E731
    assert medir({"exposicion": .5}).mean() > .5 and medir({"exposicion": -.5}).mean() < .4
    calido, frio = medir({"temperatura": .8}), medir({"temperatura": -.8})
    assert calido[0] > calido[2] and frio[2] > frio[0]
    assert medir({"tinte": .8})[1] < medir({"tinte": -.8})[1]
    roja = np.array([[.6, .35, .3]])
    sat = lambda v: np.ptp(color._aplicar_cubo(*color._leer_cubo(color.cubo(tmp_path, {"ajustes": {"saturacion": v}})), roja)[0])  # noqa: E731
    assert sat(.6) > sat(0.0001) > sat(-.6)


def test_ajustes_de_color_se_validan_al_guardar(proyecto):
    catalogo.guardar(proyecto, {"estilo": {"color": {"ajustes": {"exposicion": .2, "tinte": -.1}}}})
    for malo in ({"brillo": .2}, {"exposicion": 3}, {"exposicion": "mucho"}):
        with pytest.raises(ValueError):
            catalogo.guardar(proyecto, {"estilo": {"color": {"ajustes": malo}}})


def test_personalizar_usa_el_catalogo_y_esta_agrupado_por_temas():
    js = (config.RAIZ / "app" / "app.js").read_text()
    assert "/api/catalogo" in js and "FF4FA3" not in js.upper()   # los colores salen del catálogo (sin rosa), no de una lista
    # Personalizar agrupado por temas (tanda 2, 07-nov), en este orden; el color de la toma vive en el seleccionador completo
    orden = [js.index(f'seccion("{s}"') for s in ("persona", "textos", "subtitulos", "hook", "edicion", "sonido", "mas")]
    assert orden == sorted(orden) and "/seleccionador" in js
    for malo in ("Color de acento", "Sony S-Log3", "Tu cámara", "colorEsencial", "colorFino", "eceta", "sub_y", "hookGuardar", "Guardar hook", "Persona blanco"):
        assert malo not in js, malo


def test_el_hook_escrito_se_guarda_y_llega_al_director(proyecto):
    r = catalogo.guardar(proyecto, {"hook_texto": "  Nadie te dice esto  ", "repertorio": {"hooks": ["caja-hook"]}})
    assert r["preferencias"]["hook_texto"] == "Nadie te dice esto"
    assert "el hook dice textualmente «Nadie te dice esto»" in director.guia_seleccion(proyecto)
    with pytest.raises(ValueError, match="120"):
        catalogo.guardar(proyecto, {"hook_texto": "x" * 121})
    with pytest.raises(ValueError):
        catalogo.guardar(proyecto, {"hook_texto": 5})
    assert "hook_texto" not in catalogo.guardar(proyecto, {"hook_texto": None})["preferencias"]


def test_cantidad_de_edicion_se_conserva_en_el_storyboard(proyecto):
    (proyecto / "storyboard.json").write_text(json.dumps({"estilo": {"id": "swiss"}, "escenas": [{"t0": 0.0}], "elementos": []}))
    servidor._guardar_estilo(proyecto, {"sfx": .12, "tope_imagenes": 2})
    est = json.loads((proyecto / "storyboard.json").read_text())["estilo"]
    assert est["sfx"] == .12 and est["tope_imagenes"] == 2
    assert director._tope_elegido(proyecto) == 2


def test_looks_numerados_sin_nombres_y_sin_receta():
    nombres = [o["nombre"] for o in _cat("look")["opciones"]]
    assert nombres == [f"Look {i}" for i in range(1, len(nombres) + 1)]
    assert all(o["nota"] == "" for o in _cat("look")["opciones"])
    assert not any(c["id"] == "receta" for c in catalogo.catalogo()["categorias"])
    assert {o["id"] for o in _cat("look")["opciones"]} == {l["id"] for l in color.looks()}   # looks y LUT, un solo carrusel


# ---------- tanda 4: hook con caja y color; ver sin comprometer ----------
def test_hook_con_caja_y_color_se_guarda_y_se_valida(proyecto):
    r = catalogo.guardar(proyecto, {"hook_texto": "Hola", "hook_caja": False, "hook_color": "#ffe800"})
    assert r["preferencias"]["hook_caja"] is False and r["preferencias"]["hook_color"] == "#FFE800"
    assert catalogo.guardar(proyecto, {"hook_texto": "Hola"})["preferencias"]["hook_caja"] is False   # lo no tocado se conserva
    for malo in ({"hook_caja": "si"}, {"hook_color": "rojo"}, {"hook_color": "#FF4FA3"}):
        with pytest.raises(ValueError):
            catalogo.guardar(proyecto, malo)
    p = catalogo.guardar(proyecto, {"hook_caja": None, "hook_color": None})["preferencias"]
    assert "hook_caja" not in p and "hook_color" not in p


def test_edicion_avanzada_son_cuatro_carriles_en_orden():
    """Eran cinco (07-nov); el 11-nov Pablo dejó a Opus el movimiento, las cajas y las letras de conectores y datos."""
    cats = catalogo.catalogo()["categorias"]
    grupos = list(dict.fromkeys(c["grupo"] for c in cats))
    assert grupos == ["Estilo", "Color", "Tipografía", "Texto"]
    assert [c["id"] for c in cats if c["grupo"] == "Tipografía"] == ["fuente"]
    assert [c["id"] for c in cats if c["grupo"] == "Texto"] == ["hooks", "subtitulo", "borde"]
    html = (config.RAIZ / "app" / "seleccionador.html").read_text()
    assert "Edición avanzada" in html and "aside" not in html.replace("<aside class=\"vista\"", "").replace("</aside>", "")
    assert "vista.js" in html   # la derecha es la vista previa compartida


# ---------- tanda 4: paso Guion ----------
def test_el_guion_es_lo_que_queda_fuera_de_los_cortes(proyecto):
    assert servidor._guion(proyecto) == {"listo": False}   # sin palabras ni cortes: nada inventado
    pal = [{"w": "Hola", "s": 0.0, "e": 0.4}, {"w": "ehh", "s": 1.0, "e": 1.3}, {"w": "mundo", "s": 2.0, "e": 2.5, "fuera": True}]
    (proyecto / "palabras.json").write_text(json.dumps(pal))
    (proyecto / "fuente.json").write_text(json.dumps({"cuadros": 90}))     # el guion se mide con la regla única (montaje.quedan): pide audio medido
    np.save(proyecto / ".energia.npy", np.full(300, -60.0, np.float16))    # silencio total: ninguna palabra tiene voz, cuenta su tiempo
    assert servidor._guion(proyecto) == {"listo": False}   # palabras pero aún sin cortes
    (proyecto / "machote.json").write_text(json.dumps({"cortes": [[0.9, 1.5]]}))
    g = servidor._guion(proyecto)
    assert g["listo"] and g["fuente"] == "machote" and g["texto"] == "Hola mundo" and g["palabras"][1]["fuera"] and not g["aprobado"]
    (proyecto / "storyboard.json").write_text(json.dumps({"cortes": [[0.0, 0.5], [1.9, 2.6]]}))   # manda lo que decidió el director
    g = servidor._guion(proyecto)
    assert g["fuente"] == "storyboard" and g["texto"] == "ehh"
    (proyecto / "storyboard.json").write_text(json.dumps({"cortes": []}))   # sin cortes: todo el texto
    assert servidor._guion(proyecto)["texto"] == "Hola ehh mundo"


def test_aprobar_el_guion_se_guarda_y_se_valida(proyecto):
    assert catalogo.guardar(proyecto, {"guion_aprobado": True})["preferencias"]["guion_aprobado"] is True
    with pytest.raises(ValueError):
        catalogo.guardar(proyecto, {"guion_aprobado": "sí"})
    assert "guion_aprobado" not in catalogo.guardar(proyecto, {"guion_aprobado": None})["preferencias"]


# ---------- tanda 4: biblioteca ----------
def test_la_biblioteca_lista_lo_exportado_del_mas_nuevo_al_mas_viejo(tmp_path, monkeypatch):
    import os
    monkeypatch.setattr(config, "PROYECTOS", tmp_path)
    for nombre, t, est in (("viejo", 1_700_000_000, "swiss"), ("nuevo", 1_760_000_000, "no-existe")):
        d = tmp_path / nombre
        d.mkdir()
        (d / "final.mp4").write_bytes(b"x")
        os.utime(d / "final.mp4", (t, t))
        (d / "storyboard.json").write_text(json.dumps({"estilo": {"id": est}}))
    (tmp_path / "sin-exportar").mkdir()
    (tmp_path / "_subidas").mkdir()
    (tmp_path / "_subidas" / "final.mp4").write_bytes(b"x")
    v = servidor._biblioteca()
    assert [x["id"] for x in v] == ["nuevo", "viejo"]
    assert v[1]["estilo"] == catalogo.presets()["swiss"]["nombre"] and v[0]["estilo"] == "no-existe"
    assert v[0]["fecha"] > v[1]["fecha"]


def test_una_sola_opcion_por_categoria(proyecto):
    """Pablo (10-nov): «no debería dejar escoger más de una cosa por categoría». El servidor rechaza dos y lo nuevo REEMPLAZA a lo anterior."""
    hooks = sorted(catalogo.permitidos_repertorio()["hooks"])[:2]
    assert len(hooks) == 2
    with pytest.raises(ValueError, match="una sola opción"):
        catalogo.guardar(proyecto, {"repertorio": {"hooks": hooks}})
    catalogo.guardar(proyecto, {"repertorio": {"hooks": [hooks[0]]}})
    assert catalogo.guardar(proyecto, {"repertorio": {"hooks": [hooks[1]]}})["preferencias"]["repertorio"]["hooks"] == [hooks[1]]
    assert not any("multiple" in c for c in catalogo.catalogo()["categorias"])
