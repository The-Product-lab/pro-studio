"""Recursos del motor para los estilos nuevos: dibujan siempre igual (deterministas) y del tamaño correcto."""
import pytest
import numpy as np

from estudio import config, efectos, motor

RGB = np.random.default_rng(0).integers(0, 255, (192, 108, 3), dtype=np.uint8)


def test_filtros_nuevos_mismo_tamano_y_deterministas():
    est = motor.Estilo({"base": "pantalla"})
    for nombre in ("halftone", "blueprint"):
        a, b = efectos.filtrar(RGB, nombre, est), efectos.filtrar(RGB, nombre, est)
        assert a.shape == RGB.shape and np.array_equal(a, b)


def test_transiciones_terminan_en_la_imagen_original():
    for f in (efectos.zoom_radial, efectos.pixelar):
        assert np.array_equal(f(RGB, 1.0), RGB)
        assert not np.array_equal(f(RGB, 0.0), RGB)


def test_texto_hueco_no_tiene_relleno_y_extrusion_ensancha():
    est = motor.Estilo({"fuente": "Anton"})
    base = {"id": "t", "tipo": "texto", "x": 540, "y": 600, "t0": 0, "t1": 1, "sombra": False}
    lleno = motor.Elemento({**base, "lineas": [{"texto": "OO", "tam": 200}]}, est, None).img
    hueco = motor.Elemento({**base, "lineas": [{"texto": "OO", "tam": 200, "contorno": 5}]}, est, None).img
    ext = motor.Elemento({**base, "lineas": [{"texto": "OO", "tam": 200, "extrusion": [12, "acento"]}]}, est, None).img
    assert (np.asarray(hueco.getchannel("A")) > 128).sum() < .5 * (np.asarray(lleno.getchannel("A")) > 128).sum()
    assert ext.width >= lleno.width + 12


def test_pixeles_parpadean_igual_en_cada_render():
    from PIL import Image
    est = motor.Estilo({})
    e = motor.Elemento({"id": "px", "tipo": "pixeles", "x": 60, "y": 60, "ancho": 100, "alto": 100, "t0": 0, "t1": 1}, est, None)
    a, b = Image.new("RGBA", (120, 120)), Image.new("RGBA", (120, 120))
    e.dibujar(a, .5)
    e.dibujar(b, .5)
    assert np.array_equal(np.asarray(a), np.asarray(b)) and np.asarray(a)[..., 3].any()


def test_derivar_comparte_video_y_posicion_de_la_persona_sin_rehacer(tmp_path, monkeypatch):
    from estudio import config, ingesta
    monkeypatch.setattr(config, "PROYECTOS", tmp_path)
    base = tmp_path / "base"
    base.mkdir(parents=True)
    (base / "persona.json").write_text('{"version": 2, "paso": 15, "cuadros": 3, "cajas": []}')
    (base / "fuente.json").write_text('{"video": "x.mp4", "cuadros": 3}')
    (base / "palabras.json").write_text("[]")
    (base / "preferencias.json").write_text('{"estilo": {"color": {"receta": "pablo"}}}')
    d = ingesta.derivar("base", "base-maestro")
    assert (d / "persona.json").exists() and (d / "preferencias.json").read_text().count("pablo") == 1
    assert ingesta.derivar("base", "base-maestro") == d   # repetirlo no rompe nada


def test_buscar_fuentes_en_el_catalogo_sin_red(tmp_path, monkeypatch):
    import json as _j
    from estudio import fuentes
    cache = tmp_path / "cat.json"
    cache.write_text(_j.dumps([{"familia": "Bebas Neue", "categoria": "Display", "clases": [], "popularidad": 30, "estilos": ["400"], "ejes": [], "latin": True},
                               {"familia": "Roboto Condensed", "categoria": "Sans Serif", "clases": [], "popularidad": 10, "estilos": ["400"], "ejes": ["wght"], "latin": True}]))
    monkeypatch.setattr(fuentes, "CACHE", cache)
    assert [f["familia"] for f in fuentes.buscar("condensada")] == ["Roboto Condensed"]
    assert fuentes.buscar("", "display")[0]["familia"] == "Bebas Neue"
    assert fuentes._slug("Special Elite") == "specialelite"


def test_sfx_usa_el_banco_grabado_y_si_no_hay_sintetiza(tmp_path, monkeypatch, camara_movil):
    import wave as _w
    from estudio import sonido
    monkeypatch.setattr(sonido, "BANCO", tmp_path)
    monkeypatch.setattr(sonido, "ORGANICO", tmp_path / "no-hay")       # esta prueba mide el banco plano (paleta «suave»)
    p = type("P", (), {"sb": {"punch": [1.0], "estilo": {"sonido_paleta": "suave"}}, "escenas": [{"t0": 0}, {"t0": 2.0, "entrada": "pixel"}], "elementos": [],
                       "trazos": [], "mapa": list(range(120))})()
    sint = sonido.efectos(p, 4.0)
    with _w.open(str(tmp_path / "impact_1.wav"), "wb") as f:
        f.setnchannels(1), f.setsampwidth(2), f.setframerate(48000)
        f.writeframes((np.sin(np.arange(4800) / 3) * 20000).astype(np.int16).tobytes())
    grab = sonido.efectos(p, 4.0)
    assert sint.any() and grab.any() and not np.allclose(sint, grab)
    assert ("corte-glitch" in [e[1] for e in sonido.eventos(p)])


def test_tope_de_imagenes_por_estilo(tmp_path):
    import json as _j
    from estudio import imagenes
    (tmp_path / "storyboard.json").write_text(_j.dumps({"estilo": {"tope_imagenes": 4}}))
    assert imagenes.tope_de(tmp_path) == 4
    (tmp_path / "storyboard.json").write_text(_j.dumps({"estilo": {"tope_imagenes": 50}}))
    assert imagenes.tope_de(tmp_path) == config.TOPE_IMAGENES_MAX      # nunca pasa el techo absoluto


def test_contador_barra_fusion_y_palabra_estirada():
    from PIL import Image
    est = motor.Estilo({"base": "pantalla"})
    c = motor.Elemento({"id": "n", "tipo": "contador", "x": 540, "y": 600, "t0": 0, "t1": 2, "desde": 0, "hasta": 100, "sufijo": " %"}, est, None)
    b = motor.Elemento({"id": "b", "tipo": "barra", "x": 540, "y": 1200, "ancho": 120, "alto": 500, "t0": 0, "t1": 2}, est, None)
    for e in (c, b):
        lz = Image.new("RGBA", (1080, 1920), (0, 0, 0, 255))
        e.dibujar(lz, 1.0)
        assert np.asarray(lz)[..., :3].any()
    base = dict(id="t", tipo="texto", x=540, y=800, t0=0, t1=1, sombra=False)
    normal = motor.Elemento({**base, "lineas": [{"texto": "WHAT", "tam": 200}]}, est, None).img
    alta = motor.Elemento({**base, "lineas": [{"texto": "WHAT", "tam": 200, "escala_y": 1.8}]}, est, None).img
    assert alta.height > normal.height * 1.4 and abs(alta.width - normal.width) < 4


def test_reticula_wipe_y_smear():
    from PIL import Image
    tr = motor.trazos_de({"trazos": [{"tipo": "reticula", "cols": 3, "filas": 3, "t0": 0, "dur": .3, "t1": 2}]}, [])
    assert len(tr) == 8 + 16 * 2                      # 4+4 líneas y 16 cruces de 2 trazos
    est = motor.Estilo({"base": "pantalla"})
    e = motor.Elemento({"id": "t", "tipo": "texto", "x": 540, "y": 600, "t0": 0, "t1": 1, "entra": "smear", "dur": .1,
                        "lineas": [{"texto": "hola", "tam": 120}]}, est, None)
    a, b = Image.new("RGBA", (1080, 1920)), Image.new("RGBA", (1080, 1920))
    e.dibujar(a, .01)
    e.dibujar(b, .5)
    assert np.asarray(a)[..., 3].any() and np.asarray(b)[..., 3].any() and not np.array_equal(np.asarray(a), np.asarray(b))


def test_tecleo_revela_letras_y_barra_horizontal():
    from PIL import Image
    est = motor.Estilo({"base": "pantalla"})
    e = motor.Elemento({"id": "t", "tipo": "texto", "x": 540, "y": 600, "t0": 0, "t1": 3, "tecleo": 10,
                        "lineas": [{"texto": "/editar mi video", "tam": 60}]}, est, None)
    a, b = Image.new("RGBA", (1080, 1920)), Image.new("RGBA", (1080, 1920))
    e.dibujar(a, .1)
    e.dibujar(b, 1.5)
    assert np.asarray(b)[..., 3].sum() > np.asarray(a)[..., 3].sum() * 2       # a los 1,5 s hay muchas más letras
    bh = motor.Elemento({"id": "b", "tipo": "barra", "direccion": "horizontal", "x": 540, "y": 900, "ancho": 600, "alto": 30,
                         "t0": 0, "t1": 2}, est, None)
    c = Image.new("RGBA", (1080, 1920))
    bh.dibujar(c, 1.0)
    assert np.asarray(c)[880:920, 250:830, 3].any()


def test_editar_con_biblioteca_reusa_arte_sin_pisar(tmp_path):
    """Lote de los videos del workshop (04-nov): reusar los renders aprobados en vez de gastar créditos de Higgsfield."""
    from PIL import Image
    from estudio import cli
    bib, proy = tmp_path / "bib", tmp_path / "proy"
    bib.mkdir(), (proy / "arte").mkdir(parents=True)
    Image.new("RGB", (8, 8)).save(bib / "3d_carpeta.png")
    Image.new("RGB", (8, 8)).save(bib / "arch_celular_1.jpg")
    (bib / "CREDITOS.csv").write_text("x")
    Image.new("RGB", (8, 8), "red").save(proy / "arte" / "3d_carpeta.png")   # ya existía: no se pisa
    assert cli._traer_biblioteca(bib, proy) == 1
    assert sorted(p.name for p in (proy / "arte").iterdir()) == ["3d_carpeta.png", "arch_celular_1.png"]
    assert Image.open(proy / "arte" / "3d_carpeta.png").getpixel((0, 0)) == (255, 0, 0)


def test_lote_se_retoma_y_frena_sin_disco(tmp_path, monkeypatch):
    """Lote del workshop (04-nov): lo terminado no se rehace y con C: casi lleno se detiene (ya tumbó WSL una vez)."""
    from estudio import lote
    vids, sal = tmp_path / "v", tmp_path / "s"
    vids.mkdir(), sal.mkdir()
    (vids / "C1.MP4").write_bytes(b"x")
    (sal / "C1-vox.mp4").write_bytes(b"listo")
    llamadas = []
    monkeypatch.setattr(lote, "_correr", lambda args, log: llamadas.append(args) or 1)
    monkeypatch.setattr(lote, "libre_gb", lambda ruta="/mnt/c": 50.0)
    monkeypatch.setattr(lote, "holgura_ubuntu_gb", lambda: 50.0)
    monkeypatch.setattr(lote, "liberar_crudo", lambda v: None)
    lote.lote(vids, ["vox"], sal, avance=lambda *_: None)
    assert llamadas == []                                    # ya estaba: no se rehace
    monkeypatch.setattr(lote, "libre_gb", lambda ruta="/mnt/c": 2.0)
    e = lote.lote(vids, ["vox", "cine"], sal, avance=lambda *_: None)
    assert "disco" in e["_parado"] and llamadas == []
    monkeypatch.setattr(lote, "libre_gb", lambda ruta="/mnt/c": 50.0)
    monkeypatch.setattr(lote, "_correr", lambda args, log: llamadas.append(args) or 0)
    lote.lote(vids, ["cine"], sal, avance=lambda *_: None)
    assert any("lote-c1-cine" in a for a in llamadas[-1])  # nunca el nombre de una copia aprobada
    (vids / "C2.MP4").write_bytes(b"x")                     # un estilo por video (Pablo: «es un estilo por cada video»)
    llamadas.clear()
    lote.lote(vids, [], sal, asignar={"C2": "swiss"}, avance=lambda *_: None)
    eds = [a for a in llamadas if "editar" in a]
    assert len(eds) == 1 and "lote-c2-swiss" in eds[0]
    monkeypatch.setattr(lote, "holgura_ubuntu_gb", lambda: 1.0)   # Pablo: «ojo con llenar Ubuntu»: se frena antes de que crezca
    (sal / "LOTE.json").unlink()
    e = lote.lote(vids, [], sal, asignar={"C2": "cine"}, avance=lambda *_: None)
    assert "Ubuntu" in e["_parado"]


def test_portada_elige_momentos_ricos_fuera_del_inicio_y_de_las_transiciones():
    """Pablo (04-nov): «las miniaturas tienen que verse más pro, con todos los recursos»."""
    from estudio import portadas
    sb = {"cortes": [], "escenas": [{"t0": 0}, {"t0": 8, "persona": {"modo": "oculta"}}],
          "elementos": [{"tipo": "foto", "t0": 9, "t1": 12}, {"tipo": "texto", "t0": 9, "t1": 12}, {"tipo": "texto", "t0": 1, "t1": 2}]}
    ts = portadas.momentos(sb, 20, n=2)
    assert 9 <= ts[0] < 12 and all(t >= 3 for t in ts) and not any(8 <= t < 8.7 for t in ts)


@pytest.mark.usefixtures("camara_movil")
@pytest.mark.parametrize("modo", motor.PANTALLA_CAMARA_MOV)
@pytest.mark.parametrize("tipo", list(motor.PANTALLA_MOVIMIENTOS))
def test_pantalla_oculta_el_texto_ancho_cabe_en_el_primer_y_ultimo_cuadro_del_movimiento(tipo, modo):
    """Pablo (07-nov): «coordinar el movimiento agresivo de la cámara con lo que logra mostrar el lienzo»: si el texto es grande,
    se achica (o se reduce el movimiento) en vez de cortarse en el borde. Se mide en el primer y el último cuadro."""
    est = motor.Estilo({"base": "pantalla"})
    el = motor.Elemento({"id": "t", "tipo": "texto", "x": 540, "y": 900, "t0": 0, "t1": 4, "entra": "fundido", "dur": .01,
                         "lineas": [{"texto": "entrenando.", "tam": 150}]}, est, None)
    assert el.img.width > 0.5 * motor.W            # texto ancho: el caso difícil
    p = motor.Proyecto.__new__(motor.Proyecto)
    esc = {"t0": 0, "persona": {"modo": "oculta"}, "camara_mov": modo}
    p.est, p.elementos, p.trazos, p.cajas, p.sb = est, [el], [], [], {}
    p.subs = type("S", (), {"dibujar": staticmethod(lambda c, t: None)})()
    p.mov_pantalla = {0: tipo}
    p.grano = [np.zeros((motor.H // 2, motor.W // 2), np.float32)] * 8
    rgb = np.full((motor.H, motor.W, 3), 40, np.uint8)
    p.mapa = list(range(4 * motor.FPS + 1))
    for t in (0.05, 3.999):
        # fondo uniforme: cualquier píxel que difiera del fondo (con el grano en 0) es texto
        arr = p.cuadro_pantalla(int(t * motor.FPS), rgb, t, esc, 0.0, 4.0)
        marca = np.abs(arr.astype(int) - arr[0, 0].astype(int)).sum(-1) > 30
        ys, xs = np.where(marca)
        assert len(xs), "el texto no se dibujó"
        assert xs.min() > 0 and ys.min() > 0 and xs.max() < motor.W - 1 and ys.max() < motor.H - 1, (tipo, modo, t, xs.min(), xs.max())


def test_pantalla_oculta_ajuste_achica_y_reencuadra_sin_tocar_el_movimiento():
    mov = motor.movimiento_pantalla("izq-der", "continuo")
    assert motor.ajuste_pantalla(mov, None) == (1.0, 0.0, 0.0)
    assert motor.ajuste_pantalla(mov, (400, 800, 680, 1000)) == (1.0, 0.0, 0.0)        # chico y al centro: sin cambios
    k, tx, ty = motor.ajuste_pantalla(mov, (0, 0, motor.W, motor.H))                   # a cuadro completo: achica hasta el mínimo
    assert motor.PANTALLA_ESCALA_MIN <= k < 0.6
    k, tx, ty = motor.ajuste_pantalla(mov, (0, 800, 700, 1000))                        # pegado a la izquierda: se corre dentro de la zona común
    zona = motor.zona_visible(mov)
    assert k < 1.0 and motor.W / 2 + k * (0 - motor.W / 2) + tx >= zona[0] + motor.PANTALLA_MARGEN_PX - 1


def test_camara_continua_tiene_velocidad_constante_y_la_suave_frena_en_los_extremos():
    h = 1e-4
    v = lambda u, modo: (motor.progreso_pantalla(u + h, modo) - motor.progreso_pantalla(u, modo)) / h
    assert v(0.0, "continuo") == pytest.approx(1.0, rel=1e-3) and v(1 - 2 * h, "continuo") == pytest.approx(1.0, rel=1e-3)
    assert v(0.0, "suave") < 0.01 and v(1 - 2 * h, "suave") < 0.01
    assert v(.5, "suave") > 1.2
    a, b = motor.movimiento_pantalla("izq-der", "suave"), motor.movimiento_pantalla("izq-der", "continuo")
    assert b == a   # mismo recorrido que suave; solo cambia la curva (lineal)


def _proyecto_pantalla(elementos):
    est = motor.Estilo({"base": "pantalla"})
    p = motor.Proyecto.__new__(motor.Proyecto)
    p.est, p.elementos, p.trazos, p.cajas, p.sb = est, elementos, [], [], {}
    return est, p


def test_pantalla_oculta_la_hoja_grande_no_achica_el_texto(tmp_path):
    """Pablo (07-nov, Imprenta): «cuando dice automática hay un montón de pantalla sin mostrar texto»: la hoja a pantalla casi completa
    es fondo, no contenido: no cuenta para la caja ni se escala; el texto con fusión «multiplicar» (sobre la capa transparente) se ve."""
    from PIL import Image
    Image.new("RGBA", (motor.W, motor.H), (200, 190, 170, 255)).save(tmp_path / "hoja.png")
    est = motor.Estilo({"base": "pantalla"})
    hoja = motor.Elemento({"id": "h", "tipo": "foto", "src": "hoja.png", "cubrir": True, "x": 540, "y": 960, "t0": 0, "t1": 4,
                           "entra": "fundido", "dur": .01}, est, tmp_path)
    txt = motor.Elemento({"id": "t", "tipo": "texto", "x": 540, "y": 900, "t0": 0, "t1": 4, "entra": "fundido", "dur": .01,
                          "fusion": "multiplicar", "lineas": [{"texto": "automática", "tam": 150, "color": "#8E1C1A"}]}, est, None)
    assert hoja.es_fondo and not txt.es_fondo
    _, p = _proyecto_pantalla([hoja, txt])
    pe = {"modo": "oculta"}
    esc = {"t0": 0, "persona": pe}
    p.mov_pantalla = {0: "izq-der"}
    k, tx, ty = p.ajuste_oculta(esc, 0.0, 4.0, pe, (None, None))
    caja_texto = np.asarray(p._capa_frente(2.0, pe, (None, None), "contenido").getchannel("A")) >= motor.PANTALLA_ALFA_MIN
    assert caja_texto.any(), "el texto con fusión desapareció en la capa transparente"
    ys, xs = np.where(caja_texto)
    ancho = xs.max() - xs.min()
    zona = motor.zona_visible(motor.movimiento_pantalla("izq-der", "suave"))
    assert k == pytest.approx(min(1.0, (zona[2] - zona[0] - 2 * motor.PANTALLA_MARGEN_PX) / ancho), abs=0.02)   # lo achica el texto, no la hoja
    assert k > 0.6                                                                          # con la hoja medida iría al mínimo (0,3)
    assert (np.asarray(p._capa_frente(2.0, pe, (None, None), "fondo").getchannel("A")) > 0).all()   # la hoja viaja aparte, entera


def test_reencuadre_de_la_persona_es_un_movimiento_fluido_entre_encuadres_distintos():
    palabras = [{"s": 0.2 + i * 0.5} for i in range(40)]
    lista = motor.encuadres({"cortes": []}, palabras, 20.0, "proyecto-x")
    assert lista == motor.encuadres({"cortes": []}, palabras, 20.0, "proyecto-x")        # determinista
    assert len(lista) >= 4
    for (a, b, A, B), (a2, _, A2, _) in zip(lista, lista[1:]):
        assert abs(A[0] - B[0]) >= motor.ENCUADRE_SALTO_MIN and 2.7 <= b - a <= 5.7
        assert B == A2 and b == a2                      # el siguiente parte de donde terminó este: sin salto seco
    a, b, A, B = lista[0]
    pasos = [motor.encuadre_en(lista, a + (b - a) * i / 20) for i in range(21)]
    zs = [z for z, _ in pasos]
    assert zs == sorted(zs) or zs == sorted(zs, reverse=True)       # monótono: un solo movimiento A→B
    assert max(abs(y - x) for x, y in zip(zs, zs[1:])) < 0.5 * abs(zs[-1] - zs[0])   # sin saltos


def test_reencuadre_mantiene_la_cara_dentro_del_cuadro():
    _, p = _proyecto_pantalla([])
    cara = (700, 300, 950, 520)                                        # cara a la derecha
    cw, ch = motor.W / 1.22, motor.H / 1.22
    dx, dy = p._reencuadre_cara(-40, 0, cw, ch, {}, cara)
    v0 = (motor.W - cw) / 2 + dx
    assert v0 <= cara[0] and v0 + cw >= cara[2] and abs(dx) <= (motor.W - cw) / 2


def test_archivo_excluye_fotos_con_personas():
    """Pablo (07-nov, regla 4): sin fotos de personas en el banco de archivo: lo dice el título/etiquetas o lo ve el recorte (RVM)."""
    from PIL import Image
    from estudio import archivo
    assert archivo.habla_de_personas("Portrait of a woman with typewriter")
    assert archivo.habla_de_personas("Vintage typewriter", ["office", "Girl"])
    assert not archivo.habla_de_personas("Vintage typewriter on a wooden desk", ["office", "retro"])
    assert not archivo.tiene_persona(Image.new("RGB", (400, 300), (30, 120, 200)))     # color liso: nadie


def test_quitar_personas_descarta_fotos_con_persona_de_arte_y_storyboard(tmp_path, monkeypatch):
    """La foto con gente del cierre de Cine vino de la biblioteca antes del filtro: al armar el render se descarta."""
    import json
    from PIL import Image
    from estudio import archivo
    (tmp_path / "arte").mkdir()
    for n in ("arch_gente.png", "arch_objeto.png"):
        Image.new("RGB", (50, 50)).save(tmp_path / "arte" / n)
    sb = {"elementos": [{"id": "a", "tipo": "foto", "src": "arte/arch_gente.png"}, {"id": "b", "tipo": "foto", "src": "arte/arch_objeto.png"}]}
    (tmp_path / "storyboard.json").write_text(json.dumps(sb))
    monkeypatch.setattr(archivo, "tiene_persona", lambda im: "gente" in im.filename)
    assert archivo.quitar_personas(tmp_path, avance=lambda *_: None) == ["arte/arch_gente.png"]
    nuevo = json.loads((tmp_path / "storyboard.json").read_text())["elementos"]
    assert [e["id"] for e in nuevo] == ["b"] and (tmp_path / "arte" / "_personas" / "arch_gente.png").exists()


def test_texto_no_se_sale_del_margen_lateral(monkeypatch):
    """Pop 08-nov: «aprender a editar» quedó a ~25 px del borde izquierdo (la deriva del elemento no la medía la compuerta): el motor lo sujeta."""
    import numpy as np
    from PIL import Image
    from estudio import config, motor
    d = {"id": "t", "tipo": "etiqueta", "x": 150, "y": 900, "t0": 0, "t1": 3, "entra": "corte", "lineas": [["aprender", 110, False, 900], ["a editar", 110, False, 900]]}
    e = motor.Elemento(d, motor.Estilo({}), __import__("pathlib").Path("."))
    lienzo = Image.new("RGBA", (motor.W, motor.H), (0, 0, 0, 255))
    e.dibujar(lienzo, 1.5)
    a = np.asarray(lienzo)[..., :3].sum(-1)
    cols = np.where((a > 0).any(0))[0]
    assert cols.size and cols.min() >= config.TEXTO_MARGEN_LATERAL_PX - motor.AIRE_TEXTO


def test_subtitulo_hud_se_oscurece_solo_sobre_fondo_claro_o_rayado():
    """Cine 08-nov: blanco sobre camiseta de rayas/manos se perdía; el velo entra por contraste medido, no sobre fondo oscuro."""
    import numpy as np
    from PIL import Image
    from estudio import motor
    W, H = 400, 200
    oscuro = Image.new("RGBA", (W, H), (20, 20, 20, 255))
    claro = Image.new("RGBA", (W, H), (230, 230, 230, 255))
    rayas = Image.new("RGBA", (W, H), (255, 255, 255, 255))
    a = np.asarray(rayas).copy()
    a[:, ::20, :3] = 10
    rayas = Image.fromarray(a)
    caja = (0, 0, W, H)
    assert not motor.fondo_claro_o_rayado(oscuro, caja)
    assert motor.fondo_claro_o_rayado(claro, caja) and motor.fondo_claro_o_rayado(rayas, caja)


def test_compuerta_linea_minima_frena_etiquetas_chicas():
    """Cine 08-nov: «ESC. 02 — …» a 32 px pasó todas las compuertas (solo se medían las palabras grandes)."""
    from estudio import validar
    sb = {"elementos": [{"id": "m4", "tipo": "texto", "lineas": [{"texto": "ESC. 02", "tam": 32}]}]}
    assert validar._linea_minima(sb, {"texto_linea_min_px": 40}) and not validar._linea_minima(sb, {})
    sb["elementos"][0]["lineas"][0]["tam"] = 40
    assert not validar._linea_minima(sb, {"texto_linea_min_px": 40})


def _subtitulo_vidrio(fondo, palabras=None, y=1455, clave=(1,), t=1.0):
    """Dibuja un bloque de subtítulo «vidrio» sobre `fondo` (color RGB o matriz H×W×3). Devuelve (antes, después, caja del vidrio)."""
    import numpy as np
    from PIL import Image
    from estudio import motor
    palabras = palabras or [{"w": "esto", "s": 0.0, "e": .3}, {"w": "cambia", "s": .35, "e": .7}, {"w": "todo", "s": .75, "e": 1.1}]
    est = motor.Estilo({"subtitulo": "vidrio", "acento": "#D97757", "base": "pantalla"})
    sub = motor.Subtitulos({"subtitulos": {"y": y, "resaltar": list(clave)}}, palabras, est)
    if isinstance(fondo, tuple):
        fondo = np.full((motor.H, motor.W, 3), fondo, np.uint8)
    lienzo = Image.fromarray(np.dstack([fondo, np.full(fondo.shape[:2], 255, np.uint8)]), "RGBA")
    base = np.asarray(lienzo).copy()
    sub.dibujar(lienzo, t)
    return base, np.asarray(lienzo), getattr(sub, "caja", None)


def test_subtitulo_vidrio_sale_dentro_de_la_zona_segura_con_la_clave_en_acento():
    """Glass 10-nov: caja de vidrio, no de papel. Todo lo que dibuja (caja y letras) cae en `config.ZONA_SEGURA`, también con un bloque largo
    y con `subtitulos.y` casi en el borde; la palabra clave sale en el color acento del estilo."""
    import numpy as np
    from estudio import config
    largo = [{"w": w, "s": i * .2, "e": i * .2 + .15} for i, w in enumerate(["automatizaciones", "inteligentes", "extraordinarias"])]
    zx0, zy0, zx1, zy1 = config.ZONA_SEGURA
    for palabras, y in ((None, 1455), (None, 1700), (None, 100), (largo, 1455)):
        antes, despues, caja = _subtitulo_vidrio((0, 0, 0), palabras, y, t=1.0)
        cambio = (np.abs(despues[..., :3].astype(int) - antes[..., :3]) > 12).any(-1)
        ys, xs = np.where(cambio)
        assert ys.size and caja
        assert xs.min() >= zx0 and xs.max() <= zx1 and ys.min() >= zy0 and ys.max() <= zy1, (y, xs.min(), xs.max(), ys.min(), ys.max())
        assert caja[0] >= zx0 and caja[2] <= zx1 and caja[1] >= zy0 and caja[3] <= zy1
    acento = np.array([0xD9, 0x77, 0x57])
    _, con, _ = _subtitulo_vidrio((0, 0, 0), None, 1455, clave=(1,), t=1.0)
    _, sin, _ = _subtitulo_vidrio((0, 0, 0), None, 1455, clave=(), t=1.0)
    assert (np.abs(con[..., :3].astype(int) - acento).sum(-1) < 40).sum() > 200      # la palabra clave sale en acento
    assert (np.abs(sin[..., :3].astype(int) - acento).sum(-1) < 40).sum() < 20       # sin clave no hay acento


def test_subtitulo_vidrio_es_legible_sobre_cualquier_fondo_y_entra_sin_brusquedad():
    """Contraste medido (WCAG, letra blanca contra el vidrio ya dibujado, en el margen interior de la caja) sobre fondo negro, gris, blanco y
    rayas; y la entrada es un fundido, no un golpe."""
    import numpy as np
    from estudio import motor
    def lum(c):
        c = np.asarray(c, float) / 255
        c = np.where(c <= .03928, c / 12.92, ((c + .055) / 1.055) ** 2.4)
        return float(c @ [.2126, .7152, .0722])
    rayas = np.full((motor.H, motor.W, 3), 255, np.uint8)
    rayas[:, ::40] = 10
    for nombre, fondo in (("negro", (0, 0, 0)), ("gris", (128, 128, 128)), ("blanco", (255, 255, 255)), ("rayas", rayas)):
        _, im, caja = _subtitulo_vidrio(fondo, t=1.0)
        margen = im[caja[1] + 16:caja[3] - 16, caja[0] + 12:caja[0] + 30, :3].reshape(-1, 3)   # vidrio sin letras (el relleno izquierdo)
        ratio = (lum((255, 255, 255)) + .05) / (lum(np.median(margen, axis=0)) + .05)
        assert ratio >= 3.0, f"{nombre}: contraste {ratio:.2f} < 3 (AA texto grande)"
    base, a0, _ = _subtitulo_vidrio((0, 0, 0), t=0.0)
    _, a1, _ = _subtitulo_vidrio((0, 0, 0), t=.03)
    _, a2, _ = _subtitulo_vidrio((0, 0, 0), t=.5)
    d = [np.abs(a.astype(int) - base).sum() for a in (a0, a1, a2)]
    assert d[0] < .02 * d[2] and d[0] < d[1] < .8 * d[2]       # arranca invisible y sube de a poco, sin golpe
