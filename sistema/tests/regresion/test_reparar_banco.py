"""Fase 4 (T-0193) sobre los 4 videos reales del lote del 07-nov: el montaje se repara en código, sin IA, y se puede repetir."""
import json

import pytest

from conftest import CASOS
from estudio import director, ia, montaje

# cuántos errores de montaje quedan (como AVISOS con su segundo) por caso: tope; si sube, algo se rompió
# prestiggio 2 → 3 (PC, 07-nov, C-0008): la compuerta de voz de fuera ahora mide lo que SE OYE, no el centro de la palabra, y ve
# 0,15 s del apuntador («Mi», 44,84 s) pegados sin pausa a la voz del talento: no hay silencio donde cortar, queda como aviso.
RESIDUALES_MAX = {"cine-c8867": 1, "julian3d-c8869": 3, "prestiggio-c8873": 3, "swiss-c8872": 4}
# el silencio más largo que queda tras reparar (s): tope; solo puede BAJAR. Los que pasan de 0,2 s quedan como aviso con su segundo
# (una palabra con voz de 0,4 s entre dos cortes que el código no puede partir sin dejar un pedacito suelto).
# pc/silencio-audible (07-nov): el silencio se mide contra el nivel del talento (voz.audible), así que un soplido a -47 dB ya no
# parte la pausa: julian .33 → .35 y prestiggio .60 → .61 son el MISMO hueco medido entero (no un retroceso); cine baja.
SILENCIO_PEOR_MAX = {"cine-c8867": .24, "julian3d-c8869": .35, "prestiggio-c8873": .61, "swiss-c8872": .20}


def _quedan(sb, c):
    ctx = montaje.contexto(c)
    return ctx, montaje.tramos(sb, ctx.fin)


@pytest.mark.parametrize("caso", CASOS)
def test_reparar_baja_los_errores_es_idempotente_y_deja_avisos(banco, caso):
    c = banco(caso)
    sb = json.loads((c / "storyboard.json").read_text())
    antes = montaje.errores(sb, c)
    avisos = []
    rep = montaje.reparar(sb, c, avisos)
    despues = montaje.errores(rep, c)
    # no empeora (07-nov: en Swiss se cierra un silencio de 0,65 s y aparece un aviso de aire tras «Por» que es de Whisper, no del
    # audio: la palabra figura desde 52,18 s y suena desde 52,55 s); el tope de residuales de abajo sigue siendo la guarda
    assert len(despues) <= len(antes), (antes, despues)
    assert len(despues) <= RESIDUALES_MAX[caso], despues
    assert montaje.reparar(rep, c) == rep                                  # idempotente
    assert all({"t", "tipo", "motivo"} <= a.keys() for a in avisos)
    # todo lo que queda mal está explicado: un aviso en el mismo segundo que el borde problemático
    for e in despues:
        if "corta con voz" in e:
            assert any(a["tipo"] in ("degradado", "no_borrar") for a in avisos), (e, avisos)


def test_cine_no_deja_ninguna_palabra_fuera_y_conserva_la_version_limpia_de_24_7(banco):
    c = banco("cine-c8867")
    sb = json.loads((c / "storyboard.json").read_text())
    ctx, antes = _quedan(sb, c)
    dentro = lambda q, p: any(a - 1e-3 <= (p["s"] + p["e"]) / 2 <= b + 1e-3 for a, b in q)  # noqa: E731
    assert [p["w"] for p in ctx.palabras if p.get("fuera") and dentro(antes, p)]            # el director dejó voz del apuntador
    rep = montaje.reparar(sb, c)
    _, despues = _quedan(rep, c)
    assert [p["w"] for p in ctx.palabras if p.get("fuera") and dentro(despues, p)] == []
    limpia = [p for p in ctx.palabras if 24.69 <= p["s"] <= 35.08]
    # entera = toda su voz AUDIBLE queda (Whisper le da a «Es» 24,7–25,3 s y suena desde 25,3: el silencio de antes se recorta)
    suena = lambda q, p: any(a - 1e-3 <= montaje._fin_de_voz(ctx, p) - .02 and montaje._fin_de_voz(ctx, p) <= b + 1e-3 for a, b in q)  # noqa: E731
    assert len(limpia) == 34 and all(suena(despues, p) for p in limpia)                    # la versión de 24,7 s, entera


@pytest.mark.parametrize("caso", CASOS)
def test_la_compuerta_del_director_no_le_pide_nada_de_montaje_a_opus(banco, monkeypatch, caso):
    """Cero llamadas a la IA por errores medibles: lo que Opus recibe (si algo) nunca habla de montaje medible."""
    pedidos = []
    monkeypatch.setattr(ia, "llamar", lambda prompt, *a, **k: pedidos.append(prompt))
    c = banco(caso)
    with pytest.raises(Exception):          # otros errores (ritmo, arte que no está en el banco) siguen siendo del director
        director._validar(c, "t", imagenes_pendientes=True)
    assert pedidos and not any("montaje:" in p for p in pedidos)
    assert not (c / "storyboard.json").read_text().startswith("{}")


def test_swiss_las_marcas_fuera_viejas_no_se_comen_la_voz_fuerte_del_talento(banco):
    """Swiss C8872: el `voces_fuera` viejo marcó «Dejé de ser el editor y» (a nivel del talento) y la «Y» estirada de 0,7 s sobre
    una pausa tapaba el silencio real. Ahora el detector nuevo manda: esas palabras son del talento y la última toma se conserva."""
    c = banco("swiss-c8872")
    ctx = montaje.contexto(c)
    dejo = [p for p in ctx.palabras if 85.0 <= p["s"] <= 86.2]
    assert [p["w"] for p in dejo][:6] == ["Dejé", "de", "ser", "el", "editor", "y"] and not any(p.get("fuera") for p in dejo)


@pytest.mark.parametrize("caso", CASOS)
def test_silencios_de_pablo_ninguno_pasa_de_02_s_sin_aviso(banco, caso):
    """07-nov: «el editor no puede dejar silencios de más de 0,2 s». Tras reparar, el silencio máximo baja (nunca sube) y, si pasa de
    0,2 s, la compuerta lo dice con el segundo. Y el recorte solo quita silencio: la voz que conservaba el storyboard sigue."""
    c = banco(caso)
    sb = json.loads((c / "storyboard.json").read_text())
    ctx = montaje.contexto(c)
    antes = montaje.silencio_mayor(ctx, montaje.tramos(sb, ctx.fin))[0]
    rep = montaje.reparar(sb, c)
    despues, t_ed, t_orig = montaje.silencio_mayor(ctx, montaje.tramos(rep, ctx.fin))
    assert despues <= antes + 1e-6 and despues <= SILENCIO_PEOR_MAX[caso] + 1e-6, (antes, despues)
    if despues > montaje.SILENCIO_MAX_S + .005:
        assert any("silencio en el video final" in e and f"{t_orig:.1f} s del original" in e for e in montaje.errores(rep, c))
    sin_silencios = montaje._acortar_silencios
    montaje._acortar_silencios = lambda ctx_, cortes: cortes
    try:
        base = montaje.reparar(sb, c)
    finally:
        montaje._acortar_silencios = sin_silencios
    voz_ = lambda s_: sum(ctx.oye[int(a / .01):int(b / .01)].sum() for a, b in montaje.tramos(s_, ctx.fin))  # noqa: E731
    # reparar con silencios no come voz del guion. Excepción (07-nov, C8869 «colores. [2 s] Ya»): un huérfano de a lo más
    # ISLA_MAX_PALABRAS - 2 palabras pegado a un silencio en el borde de un tramo se va con el silencio, a propósito
    dentro = lambda s_, p: any(a <= (p["s"] + p["e"]) / 2 <= b for a, b in montaje.tramos(s_, ctx.fin))  # noqa: E731
    perdidas = [k for k, p in enumerate(ctx.palabras) if not p.get("fuera") and dentro(base, p) and not dentro(rep, p)]
    corridas = [list(g) for g in __import__("numpy").split(perdidas, __import__("numpy").flatnonzero(__import__("numpy").diff(perdidas) > 1) + 1)] if perdidas else []
    assert all(len(g) <= montaje.ISLA_MAX_PALABRAS - 2 for g in corridas), [[ctx.palabras[k]["w"] for k in g] for g in corridas]
    if not perdidas:
        assert voz_(rep) >= voz_(base) - 2, (voz_(rep), voz_(base))           # ≤ 2 cuadros de redondeo
