"""Lo que la persona ve en la pantalla de Estilos. Pablo, 11-nov: «a la aplicación le falta en estilos el estilo simple, que es solo
subtítulos… y quita ese maestro calma, que ni siquiera se ve la foto»."""
from estudio import catalogo, config, servidor


def test_basico_va_primero_y_maestro_calma_no_sale():
    lista = catalogo.en_pantalla()
    assert lista[0] == "basico" and "maestro-calma" not in lista and len(lista) == len(set(lista)) == 12
    assert "maestro-calma" in catalogo.presets()      # el motor no pierde el estilo: solo deja de mostrarse


def test_cada_estilo_que_se_ve_tiene_su_portada():
    for estilo in catalogo.en_pantalla():
        assert (config.RAIZ / "app" / "muestras" / f"{estilo}.jpg").is_file(), estilo


def test_la_pantalla_de_estilos_y_edicion_avanzada_usan_la_misma_lista():
    avanzada = [o["id"] for o in next(c for c in catalogo.catalogo()["categorias"] if c["id"] == "preset")["opciones"]]
    assert avanzada[:len(catalogo.en_pantalla())] == catalogo.en_pantalla()
    fuente = (config.RAIZ / "estudio" / "servidor.py").read_text()
    assert '"aprobados": catalogo.en_pantalla()' in fuente and '(_DIR / "ejemplo").glob' not in fuente
    assert servidor is not None


def test_la_portada_de_un_estilo_sin_director_se_dibuja_sin_video(tmp_path):
    from PIL import Image
    from estudio import portadas
    f = portadas.portada_sin_director("basico", tmp_path / "b.jpg")
    assert Image.open(f).size == (portadas.W, portadas.H)


def test_el_aviso_de_un_estilo_sin_director_no_habla_de_ia_ni_imagenes():
    """Pablo, 11-nov: en Básico «me apareció el aviso de siempre, que usa IA como director y usa imágenes… aquí no vamos a usar nada»."""
    js = (config.RAIZ / "app" / "app.js").read_text()
    cuerpo = js[js.index("function editarConEstilo("):js.index("dirigirConEstilo(id);\n  ir(")]
    assert "sin_director" in cuerpo and "no usa IA ni imágenes" in cuerpo
    assert catalogo.presets()["basico"]["sin_director"] is True


def test_basico_es_solo_subtitulos_chiquitos_y_abajo():
    """Pablo, 11-nov: «es únicamente subtítulos, abajito, chiquitos y ya»: ni textos grandes, ni apoyos, ni efectos de sonido."""
    from estudio import subtitulo_basico as sb
    assert sb.TAM <= 64 and 1380 <= sb.Y and sb.Y + sb.TAM * sb.INTERLINEA + sb.CAJA_PAD[1] <= 1500   # dos líneas con caja caben en la zona segura
    pre = catalogo.presets()["basico"]
    assert pre["sfx"] == 0 and pre["imagenes"] is False and pre["sin_director"] is True
    css = (config.RAIZ / "app" / "estilos.css").read_text()
    assert ".per.solo-sub .pv:last-child" in css and 'solo-sub", !!lib.estilos[estiloId]?.sin_director' in (config.RAIZ / "app" / "app.js").read_text()


def test_al_redisenar_el_video_exportado_antes_deja_de_ser_el_final(tmp_path):
    """11-nov: tras pasar de Swiss a Básico, Exportar seguía mostrando el video del Swiss como si fuera el de ahora."""
    from estudio import ingesta
    (tmp_path / "final.mp4").write_bytes(b"swiss")
    (tmp_path / "storyboard.json").write_text("{}")
    ingesta.limpiar_intento(tmp_path)
    assert not (tmp_path / "final.mp4").exists() and (tmp_path / ingesta.FINAL_ANTERIOR).read_bytes() == b"swiss"   # se conserva, aparte


def test_las_miniaturas_se_cargan_todas_de_entrada():
    """Pablo, 11-nov: «las miniaturas no me están abriendo… que yo no tenga que darle clic a ningún estilo para verlas». La ventana
    de la app usa WebKit, y con `loading="lazy"` cargaba 5 de 12 portadas en Estilos y 44 de 59 en Estilos Pro; las demás, nunca."""
    for archivo in ("app.js", "pro.js"):
        assert 'loading="lazy"' not in (config.RAIZ / "app" / archivo).read_text(), archivo


def test_las_miniaturas_dentro_de_un_boton_tienen_tamano_propio():
    """Pablo, 12-nov: en Estilos Pro «no que yo tenga que darle a cada nombre para ver la imagen… todas se tienen que ver al mismo
    tiempo, chiquito». En WebKit (la ventana de la app) la caja de la miniatura medía 0×0 dentro de un botón en columna flexible:
    medido, 59 estilos con solo el nombre. La caja lleva su ancho y su alto escritos (no depende de `aspect-ratio` ni de flex)."""
    pro = (config.RAIZ / "app" / "pro.css").read_text()
    assert ".pro-t{display:block" in pro and "padding-top:56.25%" in pro and "minmax(150px" in pro
    est = (config.RAIZ / "app" / "estilos.css").read_text()
    assert ".mq{display:block" in est and "padding-top:177.78%" in est
    js = (config.RAIZ / "app" / "pro.js").read_text()
    assert js.index("<b>${escP(e.nombre)}</b><span class=\"pv-img\">") > 0     # el nombre arriba, la imagen debajo
