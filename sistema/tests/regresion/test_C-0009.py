"""C-0009 (Pablo, 07-nov, Cine C8867, todos los estilos): «el editor no le está poniendo casi recurso».
Después del inicio limpio, ningún tramo pasa más de reglas.json › recurso_hueco_max_s sin un recurso visible (imagen, clip,
panel o texto grande); el subtítulo solo no cuenta. El Cine de ese día tenía 5,6 s seguidos sin nada."""
from estudio import validar

PALABRAS = [{"w": f"p{i}", "s": i * .5, "e": i * .5 + .4} for i in range(40)]    # 20 s hablando


def _sb(*elementos):
    return {"estilo": {"base": "pantalla"}, "escenas": [{"t0": 0.0}], "elementos": list(elementos), "subtitulos": {"y": 1450}}


def _foto(t0, t1):
    return {"tipo": "foto", "t0": t0, "t1": t1}


def test_la_regla_existe_para_todos_los_estilos():
    assert validar.reglas(None)["recurso_hueco_max_s"] and validar.reglas("cine")["recurso_hueco_max_s"]


def test_tramo_largo_sin_recurso_no_pasa():
    sb = _sb(*[_foto(t, t + 2) for t in (3, 5, 7)], _foto(14, 20.6))      # 9–14 s sin nada
    err = validar._recursos(sb, validar.reglas(None), PALABRAS)
    assert err and "sin ningún recurso" in err[0]


def test_recursos_seguidos_pasan_y_el_inicio_limpio_no_cuenta():
    sb = _sb(*[_foto(t, t + 2) for t in range(3, 21, 2)])
    assert validar._recursos(sb, validar.reglas(None), PALABRAS) == []


def test_texto_chico_no_es_recurso():
    chico = {"tipo": "texto", "t0": 3, "t1": 21, "lineas": [{"texto": "ESC. 02", "tam": 30}]}
    assert validar._recursos(_sb(chico), validar.reglas(None), PALABRAS)
