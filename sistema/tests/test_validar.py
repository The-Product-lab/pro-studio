"""La compuerta del storyboard: lo que el motor no sabe dibujar y lo que Pablo prohibió no pasa."""
import json

import pytest

from estudio import config, validar

EJEMPLOS = config.RAIZ / "estudio/director/ejemplo"


def _base(**extra):
    sb = {"estilo": {"base": "pantalla", "fuente": "Montserrat"}, "escenas": [{"t0": 0.0}], "elementos": [],
          "subtitulos": {"y": 1450}}
    sb.update(extra)
    return sb


OBSOLETOS = {l.strip() for l in (EJEMPLOS / "OBSOLETOS.txt").read_text().splitlines() if l.strip() and not l.startswith("#")} \
    if (EJEMPLOS / "OBSOLETOS.txt").exists() else set()


@pytest.mark.parametrize("ejemplo", sorted(p.name for p in EJEMPLOS.glob("*.json") if p.name != "palabras.json" and not p.name.endswith(".palabras.json") and p.name not in OBSOLETOS))
def test_cada_ejemplo_de_estilo_pasa_la_compuerta(ejemplo):
    sb = json.loads((EJEMPLOS / ejemplo).read_text())
    pre = json.loads((config.RAIZ / "librerias" / "estilos" / "presets.json").read_text())[ejemplo[:-5]]
    sb["estilo"] = {"id": ejemplo[:-5], **{k: v for k, v in pre.items() if k != "nombre"}}   # con el estilo del PRESET, como `_fijar_estilo`
    # «una cosa a la vez» (10-nov, Glass) y el ritmo calmo (04-nov) son posteriores a los ejemplos aprobados: el director lo cumple por regla, el ejemplo muestra el nivel
    assert [e for e in validar.errores(sb) if not e.startswith(("ritmo:", "una cosa:"))] == []


def test_clave_desconocida_es_error_no_se_ignora():
    sb = _base(escenas=[{"t0": 0.0, "filtro": "glow"}])
    assert any("glow" in e for e in validar.errores(sb))
    sb = _base(elementos=[{"tipo": "tarjeta-vidrio", "x": 540, "y": 600, "t0": 0, "t1": 1}])
    assert any("tarjeta-vidrio" in e for e in validar.errores(sb))
    sb = _base(efecto_magico=True)
    assert any("efecto_magico" in e for e in validar.errores(sb))


def test_rosa_solo_se_prohibe_donde_pablo_lo_pide(tmp_path, monkeypatch):
    assert validar.es_rosa("#FF4FA3") and validar.es_rosa("#E040FB")
    assert not validar.es_rosa("#FF0033") and not validar.es_rosa("#FFE800") and not validar.es_rosa("#00E5FF")
    reglas = tmp_path / "reglas.json"
    reglas.write_text(json.dumps({"global": {}, "estilos": {"ejemplo": {"colores_prohibidos": ["rosa"]}}}))
    monkeypatch.setattr(validar, "REGLAS", reglas)
    rosa = {"base": "pantalla", "acento": "#FF69B4"}
    assert any("rosa" in e for e in validar.errores(_base(estilo={**rosa, "id": "ejemplo"})))
    assert validar.errores(_base(estilo={**rosa, "id": "pop"})) == []


def test_texto_que_se_sale_del_lienzo_se_detecta_midiendo():
    linea = {"texto": "extraordinario", "rol": "display", "tam": 240, "mayus": True}
    sb = _base(elementos=[{"id": "t", "tipo": "texto", "x": 540, "y": 600, "t0": 4, "t1": 5, "lineas": [linea]}])
    assert any("se sale de lo que se ve" in e for e in validar.errores(sb))
    linea["tam"] = 90
    assert validar.errores(sb) == []


def test_texto_y_subtitulos_dentro_de_la_zona_segura():
    linea = {"texto": "hola", "rol": "display", "tam": 120}
    sb = _base(elementos=[{"id": "t", "tipo": "texto", "x": 540, "y": 1650, "t0": 0, "t1": 1, "lineas": [linea]}])
    assert any("zona segura" in e for e in validar.errores(sb))
    assert any("zona segura" in e for e in validar.errores(_base(subtitulos={"y": 1520})))


def test_la_base_collage_y_los_modos_que_recortan_a_la_persona_ya_no_existen():
    """Pablo (11-nov): «elimina el tema de recortes de todo». La persona se ve entera (`completa`) o no se ve (`oculta`)."""
    assert any("estilo.base" in e for e in validar.errores(_base(estilo={"base": "collage"})))
    for modo in ("recorte", "silueta", "neon"):
        sb = _base(estilo={"base": "pantalla"}, escenas=[{"t0": 0.0, "persona": {"modo": modo}}])
        assert any("persona.modo" in e for e in validar.errores(sb)), modo


def test_foto_cubrir_llena_la_pantalla_sin_barras(tmp_path):
    import numpy as np
    from PIL import Image
    from estudio import motor
    Image.new("RGB", (900, 1200), (200, 200, 200)).save(tmp_path / "f.png")   # 3:4
    e = motor.Elemento({"id": "f", "tipo": "foto", "src": "f.png", "cubrir": True, "x": 0, "y": 0, "t0": 0, "t1": 1},
                       motor.Estilo({}), tmp_path)
    assert e.img.size == (1080, 1920) and np.asarray(e.img)[..., 3].min() == 255


def test_color_de_la_toma_de_pablo_no_se_cambia_en_todo_el_video():
    largo = _base(estilo={"base": "pantalla", "filtro": "penumbra"})
    assert any("color de la toma" in e for e in validar.errores(largo))
    sb = _base(escenas=[{"t0": 0.0, "filtro": "bn"}, {"t0": 1.0}, {"t0": 5.0, "filtro": "bn"}])
    sb["cortes"] = []
    errs = [e for e in validar.errores(sb) if "toma de Pablo" in e]
    assert len(errs) == 1 and "escenas[2]" in errs[0]          # 1 s de B/N es golpe puntual; el último dura hasta el final


def test_bloom_no_cambia_el_color_de_la_toma_solo_abre_las_luces():
    import numpy as np
    from estudio import efectos
    img = np.full((192, 108, 3), 128, np.uint8)            # gris medio (piel, camiseta, pared)
    img[90:102, 50:58] = 255                                # una lámpara
    out = efectos.bloom(img, .5)
    assert np.abs(out[10:40, 10:40].astype(int) - 128).max() <= 1      # lejos de la luz: el color de la toma no cambia
    assert out[85, 54].mean() >= 133                                    # junto a la lámpara: se abre el halo
    assert any("bloom" in e for e in validar.errores(_base(estilo={"base": "pantalla", "bloom": .9})))


@pytest.mark.usefixtures("camara_movil")
def test_la_camara_cuenta_al_medir_el_texto():
    linea = {"texto": "subtítulos", "rol": "display", "tam": 120}
    el = {"id": "t", "tipo": "texto", "x": 540, "y": 700, "t0": 0, "t1": 1, "lineas": [linea]}
    quieta = _base(elementos=[el])
    quieta["camara"] = [{"t": 0, "zoom": 1.0}, {"t": 5, "zoom": 1.0}]
    assert not any("se ve" in e for e in validar.errores(quieta))
    linea["tam"] = 175                                       # ~1000 px: cabe quieta, pero un acercamiento al 13 % se lo come
    empuja = _base(elementos=[el])
    empuja["camara"] = [{"t": 0, "zoom": 1.13}, {"t": 5, "zoom": 1.13}]
    assert any("se sale de lo que se ve" in e for e in validar.errores(empuja))


def test_apoyo_literal_tolera_errores_de_oido(tmp_path):
    import json as _j
    (tmp_path / "palabras.json").write_text(_j.dumps([{"w": "Cloud", "s": 1.0, "e": 1.3}, {"w": "WORSHOP", "s": 3.0, "e": 3.5}]))
    (tmp_path / "fuente.json").write_text(_j.dumps({"video": "x.mp4", "cuadros": 150}))
    (tmp_path / "f.png").write_bytes(b"")
    els = [{"id": "a", "tipo": "foto", "src": "f.png", "ancho": 500, "fundir": True, "x": 540, "y": 900, "t0": 1.0, "t1": 2, "muestra": "Claude"},
           {"id": "b", "tipo": "foto", "src": "f.png", "ancho": 500, "fundir": True, "x": 540, "y": 900, "t0": 3.0, "t1": 4, "muestra": "workshop"},
           {"id": "c", "tipo": "foto", "src": "f.png", "ancho": 500, "fundir": True, "x": 540, "y": 900, "t0": 3.0, "t1": 4, "muestra": "tijeras"}]
    errs = [e for e in validar._apoyo_literal({"elementos": els}, {"apoyo_literal_ventana_s": [-1, 1.5]}, _j.loads((tmp_path / "palabras.json").read_text()))]
    assert len(errs) == 1 and "tijeras" in errs[0]


def test_la_compuerta_acepta_todo_lo_que_el_motor_dibuja():
    """Caso real (copia de prestiggio): el motor ya tecleaba y hacía barras horizontales, pero la compuerta las rechazaba."""
    t = {"id": "t", "tipo": "texto", "x": 540, "y": 700, "t0": 0, "t1": 2, "tecleo": 10, "cursor": False,
         "lineas": [{"texto": "/editar", "tam": 80}]}
    b = {"id": "b", "tipo": "barra", "direccion": "horizontal", "x": 540, "y": 900, "ancho": 500, "alto": 30, "t0": 0, "t1": 2}
    sb = _base(elementos=[t, b])
    sb["sonido"] = [{"t": .5, "tipo": "pop"}]
    assert not any("no conoce" in e for e in validar.errores(sb))


def test_revision_guarda_feedback_por_estilo(tmp_path, monkeypatch):
    from estudio import revision
    monkeypatch.setattr(revision, "NOTAS", tmp_path / "FEEDBACK.json")
    ns = revision.anotar("vox", "escena 6: menos papel", 12.5)
    assert ns[-1]["texto"] == "escena 6: menos papel" and ns[-1]["segundo"] == 12.5
    assert revision.anotar("vox", "", aprueba=True)[-1]["aprueba"]
    import pytest
    with pytest.raises(ValueError):
        revision.anotar("inventado", "x")


def test_camara_viaja_continua_sin_brincos_ni_ir_y_venir():
    """Pablo (04-nov): «la cámara tiene brincos… usa el mismo efecto de ir y venir… no viaja entre todo». Caso real: escenas
    push → pull seguidas (zoom 1.09 → 1.10 de golpe en el corte) y la onda de flotar."""
    from estudio import camara
    sb = {"estilo": {"flotar": 10}, "cortes": [[0, 20.45], [26.25, 92.05]],
          "escenas": [{"t0": 20.5, "camara": "push"}, {"t0": 23, "camara": "pull"}, {"t0": 92.1, "camara": "giro"}, {"t0": 94, "camara": "push"}]}
    m = camara.saltos(sb, 30)
    assert m["zoom_por_cuadro"] <= .004 and m["px_por_cuadro"] <= 4
    assert m["vueltas_zoom"] == 0                     # 2.ª nota (luminoso): una sola dirección, nada de ir y venir
    r = camara.Ruta(sb, 30)
    # dentro de una toma las escenas (push → pull) NO reinician la cámara: el zoom sigue entrando, profundo
    zs = [r(camara.salida(sb, t))[0] for t in (20.6, 22.9, 23.1, 25.0, 26.2)]
    assert zs == sorted(zs) and abs(zs[2] - zs[1]) < .01 and zs[-1] - zs[0] > .04
    # keyframes del director con un salto brusco: la compuerta lo frena
    sb2 = {**sb, "camara": [{"t": 20.5, "zoom": 1.0}, {"t": 20.6, "zoom": 1.15}]}
    assert any("brinco" in e for e in validar._camara_continua(sb2))


def test_un_movimiento_a_la_vez_e_imagenes_integradas():
    """Pablo (04-nov): maestro «varios movimientos al mismo tiempo carga el frame»; luminoso seg 8 «el gato se ve como una caja fea»."""
    foto = {"id": "gato", "tipo": "foto", "src": "arte/x.jpg", "x": 540, "y": 600, "t0": 0, "t1": 2, "ancho": 500}
    sb = _base(elementos=[foto])
    sb["estilo"] = {**sb.get("estilo", {}), "id": "maestro", "flotar_elementos": 10}
    err = validar._calma_e_integracion(sb, validar.reglas("maestro"))
    assert any("un movimiento a la vez" in e for e in err) and any("cuadrada montada" in e for e in err)
    # desde el 10-nov el tope vale para todos los estilos (también luminoso)
    assert any("un movimiento" in e for e in validar._calma_e_integracion(sb, validar.reglas("luminoso")))
    foto["fundir"] = True
    sb["estilo"]["flotar_elementos"] = 0
    assert validar._calma_e_integracion(sb, validar.reglas("maestro")) == []
    foto.pop("fundir")
    assert not any("cuadrada" in e for e in validar._calma_e_integracion(sb, validar.reglas("pop")))


def test_textos_en_recorrido_gradual():
    """Pablo (04-nov, pop, general): de un pico a un valle se pasa por la bajada; el texto no salta de arriba a abajo."""
    t = lambda i, y, t0: {"id": i, "tipo": "texto", "x": 540, "y": y, "t0": t0, "t1": t0 + 1, "lineas": [{"texto": "hola", "tam": 120}]}
    r = validar.reglas("pop")
    assert validar._texto_en_recorrido(_base(elementos=[t("a", 400, 0), t("b", 1400, 1.2)]), r)
    assert not validar._texto_en_recorrido(_base(elementos=[t("a", 400, 0), t("b", 700, 1.2), t("c", 1000, 2.4), t("d", 1300, 3.6)]), r)


def test_camara_un_viaje_para_todo_el_video():
    """Pablo (04-nov, glass): la cámara viaja lentamente por todo el video, no va y viene en cada escena ni en cada corte."""
    from estudio import camara
    sb = {"cortes": [[0, 20.45], [26.25, 92.05], [96.25, 150.3]], "escenas": [{"t0": 20.5}, {"t0": 92.1}, {"t0": 150.4}]}
    r = camara.Ruta(sb, 26)
    zs = [r(t / 2)[0] for t in range(52)]
    assert zs == sorted(zs) and max(b - a for a, b in zip(zs, zs[1:])) < .02


def test_integrar_solo_lo_aprobado_y_que_pasa_la_compuerta(tmp_path, monkeypatch):
    """Pablo (04-nov): «que integre bien el nuevo conocimiento sin dañar nada». Candados: aprobado + compuerta + solo ese estilo."""
    from estudio import integrar
    proy = tmp_path / "proy"
    proy.mkdir()
    sb = _base()
    (proy / "storyboard.json").write_text(json.dumps(sb))
    (proy / "palabras.json").write_text("[]")
    ej, pre, fb = tmp_path / "ej", tmp_path / "presets.json", tmp_path / "fb.json"
    ej.mkdir()
    (ej / "OBSOLETOS.txt").write_text("# viejos\nmaestro.json\n")
    pre.write_text(json.dumps({"pop": {"nombre": "Pop"}, "maestro": {"nombre": "Maestro", "acento": "#000"}}))
    fb.write_text(json.dumps([{"estilo": "maestro", "aprueba": False}]))
    kw = dict(feedback=fb, ejemplos=ej, presets=pre, avance=lambda *_: None)
    with pytest.raises(ValueError, match="no está aprobado"):
        integrar.integrar("maestro", str(proy), **kw)
    assert not (ej / "maestro.json").exists()
    fb.write_text(json.dumps([{"estilo": "maestro", "aprueba": True}]))
    r = integrar.integrar("maestro", str(proy), **kw)
    assert (ej / "maestro.json").exists() and (ej / "maestro.palabras.json").exists()
    assert "maestro.json" not in (ej / "OBSOLETOS.txt").read_text()
    todos = json.loads(pre.read_text())
    assert todos["pop"] == {"nombre": "Pop"} and todos["maestro"]["nombre"] == "Maestro" and r["respaldo"]
    # lo que no es del look se conserva (sin `imagenes` el director dejaba de pedir arte) y el color del video no entra
    pre.write_text(json.dumps({"maestro": {"nombre": "Maestro", "imagenes": True, "tope_imagenes": 4}}))
    sb["estilo"]["color"] = {"look": "x"}
    (proy / "storyboard.json").write_text(json.dumps(sb))
    integrar.integrar("maestro", str(proy), **kw)
    m = json.loads(pre.read_text())["maestro"]
    assert m["imagenes"] is True and m["tope_imagenes"] == 4 and "color" not in m
    sb["escenas"][0]["camara"] = "inventada"            # una copia que ya no pasa la compuerta no entra
    (proy / "storyboard.json").write_text(json.dumps(sb))
    with pytest.raises(ValueError, match="compuerta"):
        integrar.integrar("maestro", str(proy), **kw)


def test_la_huella_del_estilo_no_bloquea_al_director():
    """Pablo (04-nov): «el anterior editor no tenía libertad creativa… las guías de estilo bloqueaban». La huella es inspiración:
    la guía la presenta así y el director no la recibe como error a arreglar."""
    from estudio import director
    src = (config.RAIZ / "estudio/director/__init__.py").read_text()
    assert 'if not x.startswith("huella")' in src
    # estilo sin ejemplo aprobado (cine): la huella aparece como inspiración; aprobado (luminoso): su guía manda, sin huella
    sin_aprobar = [h.stem for h in (config.RAIZ / "librerias/estilos/huellas").glob("*.json")
                   if not (EJEMPLOS / f"{h.stem}.json").exists() or f"{h.stem}.json" in OBSOLETOS]
    for e in sin_aprobar[:1]:
        assert "NO obligación" in director._guia(e) or "Lo que suelen tener" not in director._guia(e)
    assert "Lo que suelen tener sus referentes" not in director._guia("luminoso")


def test_montaje_ajusta_lo_medible_y_no_toca_lo_aprobado():
    """Lote del workshop (04-nov): el director fallaba 3 veces la compuerta por milisegundos de corte (C8872). El código corrige
    bordes, aire y silencios; lo que ya cumple queda igual. Los storyboards de estos proyectos son del 04-nov, de antes del tope de
    silencio (0,2 s, 07-nov): ya no cumplen tal cual, así que se mide que `reparar` los deja sin errores y no toca lo ya reparado."""
    from estudio import montaje
    for c in ("c8866-vox", "c8866-cine"):
        carpeta = config.PROYECTOS / c
        if not (carpeta / "storyboard.json").exists():
            pytest.skip("sin proyectos de prueba en esta máquina")
        sb = json.loads((carpeta / "storyboard.json").read_text())
        reparado = montaje.reparar(sb, carpeta)
        assert montaje.errores(reparado, carpeta) == []
        assert montaje.reparar(reparado, carpeta)["cortes"] == reparado["cortes"]


def test_acomodar_corre_textos_fuera_de_cuadro_sin_tocar_lo_aprobado():
    """Lote del workshop (04-nov): C8868 fallaba por textos que la cámara dejaba fuera por píxeles; lo medible lo arregla el código."""
    t = {"id": "t", "tipo": "texto", "x": 60, "y": 700, "t0": 0, "t1": 1, "lineas": [{"texto": "subtítulos", "tam": 120}]}
    sb = _base(elementos=[t])
    assert any("se sale" in e for e in validar.errores(sb))
    assert not any("se sale" in e for e in validar.errores(validar.acomodar(sb)))
    carpeta = config.PROYECTOS / "c8866-vox"
    if (carpeta / "storyboard.json").exists():
        ok = json.loads((carpeta / "storyboard.json").read_text())
        assert validar.acomodar(ok, carpeta) == ok


def test_inicio_limpio_sin_motion_al_principio():
    """Pablo (04-nov, lote del workshop): «no uses motion al principio»: los primeros 3 s solo la persona; lo corre el código."""
    t = {"id": "g", "tipo": "texto", "x": 540, "y": 700, "t0": .5, "t1": 6, "lineas": [{"texto": "gancho", "tam": 120}]}
    chico = {"id": "c", "tipo": "texto", "x": 540, "y": 900, "t0": .2, "t1": 2, "lineas": [{"texto": "x", "tam": 80}]}
    sb = _base(elementos=[t, chico])
    sb["escenas"] = [{"t0": 0, "persona": {"modo": "oculta"}}, {"t0": 5}]
    r = validar.reglas(None)
    assert validar._inicio_limpio(sb, r)
    limpio = validar.limpiar_inicio(sb)
    assert validar._inicio_limpio(limpio, r) == []
    assert [e["id"] for e in limpio["elementos"]] == ["g"] and limpio["elementos"][0]["t0"] >= 3



def test_ritmo_calmo_se_mide_en_el_final():
    """Pablo (04-nov): «el ritmo es muy rápido, muchos cortes y elementos en muy poco tiempo»."""
    r = validar.reglas(None)
    t = lambda i, t0: {"id": i, "tipo": "texto", "x": 540, "y": 700, "t0": t0, "t1": t0 + 1, "lineas": [{"texto": "hola", "tam": 120}]}
    rapido = _base(elementos=[t("a", 4), t("b", 5), t("c", 6), t("d", 7)])
    rapido["escenas"] = [{"t0": 0}, {"t0": 4}, {"t0": 5}]
    assert len(validar._ritmo(rapido, r)) == 2
    calmo = _base(elementos=[t("a", 4), t("b", 7), t("c", 10)])
    calmo["escenas"] = [{"t0": 0}, {"t0": 4}, {"t0": 8}]
    assert validar._ritmo(calmo, r) == []
