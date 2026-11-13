"""C-0007 (Pablo, 07-nov, todos los estilos): «el texto siempre debe verse, pero el editor DUPLICA: pone el motion graphic/texto
animado y además el subtítulo normal con la misma palabra». Si un texto en pantalla ya muestra la palabra, el subtítulo se
oculta ahí (lo hace el código en `validar.acomodar`) y la compuerta no deja pasar un duplicado."""
from estudio import validar

PALABRAS = [{"w": w, "s": i * .5, "e": i * .5 + .4} for i, w in
            enumerate("le dices qué tipografía te gusta y lo que quieres publicar hoy mismo".split())]


def _sb(*elementos, **sub):
    return {"estilo": {"base": "pantalla"}, "escenas": [{"t0": 0.0}], "elementos": list(elementos),
            "subtitulos": {"y": 1450, "bloques": [[0, 3], [3, 6], [6, 9], [9, 12]], **sub}}


def _texto(t0, t1, *lineas):
    return {"tipo": "texto", "t0": t0, "t1": t1, "lineas": [{"texto": l} for l in lineas]}


def test_palabra_del_texto_repetida_en_el_subtitulo_no_pasa():
    sb = _sb(_texto(1.4, 3.0, "tipografía"))
    assert validar.duplicados(sb, PALABRAS) and validar._sin_duplicado(sb, PALABRAS)


def test_letras_separadas_tambien_cuentan():
    sb = _sb(_texto(4.4, 6.0, "P U B L I C A R"))
    assert validar.duplicados(sb, PALABRAS)


def test_solo_palabras_vacias_en_comun_no_es_duplicado():
    sb = _sb(_texto(1.4, 3.0, "qué maravilla"))
    assert validar.duplicados(sb, PALABRAS) == []


def test_acomodar_oculta_el_subtitulo_repetido_y_el_texto_sigue_en_pantalla(tmp_path):
    import json
    (tmp_path / "palabras.json").write_text(json.dumps(PALABRAS))
    sb = validar.acomodar(_sb(_texto(1.4, 3.0, "tipografía")), tmp_path)
    assert validar.duplicados(sb, PALABRAS) == []
    assert sb["subtitulos"]["ocultar"]
    assert validar._texto_siempre(sb, validar.reglas(None), PALABRAS) == []


def test_palabra_corta_con_contenido_tambien_cuenta():
    """Cine 07-nov (segunda vuelta): «cada vez» en pantalla y «VEZ» en el subtítulo."""
    pal = [{"w": w, "s": i * .5, "e": i * .5 + .4} for i, w in enumerate("se va entrenando cada vez mientras".split())]
    sb = _sb(_texto(1.4, 3.0, "cada vez"))
    sb["subtitulos"]["bloques"] = [[0, 3], [3, 4], [4, 5], [5, 6]]
    assert any(d[2] == "vez" for d in validar.duplicados(sb, pal))
