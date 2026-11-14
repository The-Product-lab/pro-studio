"""Pablo (04-nov, todos los estilos, también light): «siempre debe haber movimiento de textos. Siempre aparece el texto sea
animación sea subtítulo todo. No puede quedarse quieto sin ningún tipo de elementos porque se mata el ritmo».
La compuerta mide en el video final el tramo más largo sin subtítulo ni texto en pantalla (reglas.json › texto_siempre_max_s)."""
from estudio import validar

PALABRAS = [{"w": f"p{i}", "s": i * .5, "e": i * .5 + .4} for i in range(30)]   # 15 s hablando sin pausas


def _sb(**sub):
    return {"estilo": {"base": "pantalla"}, "escenas": [{"t0": 0.0}], "elementos": [], "subtitulos": {"y": 1450, **sub}}


def test_subtitulo_continuo_pasa():
    assert validar._texto_siempre(_sb(), validar.reglas(None), PALABRAS) == []


def test_subtitulo_oculto_sin_otro_texto_no_pasa():
    err = validar._texto_siempre(_sb(ocultar=[[4.0, 9.0]]), validar.reglas(None), PALABRAS)
    assert err and "sin ningún texto" in err[0]


def test_un_texto_animado_cubre_el_hueco():
    sb = _sb(ocultar=[[4.0, 9.0]])
    sb["elementos"] = [{"tipo": "texto", "t0": 3.9, "t1": 9.2}]
    assert validar._texto_siempre(sb, validar.reglas(None), PALABRAS) == []


def test_se_mide_en_el_video_final_descontando_cortes():
    sb = _sb(ocultar=[[4.0, 9.0]])
    sb["cortes"] = [[4.5, 8.5]]                      # lo que se corta no cuenta: quedan 1 s sin texto
    assert validar._texto_siempre(sb, validar.reglas(None), PALABRAS) == []
