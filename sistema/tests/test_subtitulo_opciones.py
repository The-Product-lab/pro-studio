"""Opciones del subtítulo (Pablo, 10-nov: «¿puedo quitarle la caja, cambiar color, efecto y tipografía?»): las MISMAS claves sub_* para
tira, hud, vidrio y básico. Por cada clave y tipo: el valor llega al dibujo, o el tipo no la admite y lo dice (`SOPORTE`) y no cambia nada.
Sin elegir nada, el subtítulo de cada tipo sale como siempre (los 13 estilos, en tests/render_nodano.py y test_estilos_fichas)."""
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from estudio import catalogo, config, contraste, motor, subtitulo_opciones as so, validar  # noqa: E402

TIPOS = ["tira", "hud", "vidrio", "basico"]
PAL = [{"w": "esto", "s": 0.0, "e": .3}, {"w": "cambia", "s": .35, "e": .7}, {"w": "todo", "s": .75, "e": 1.1}]
VERDE, AZUL, NARANJA = "#00FF00", "#0000FF", "#FF8800"


def dibujar(tipo, t=1.0, fondo=(0, 0, 0), **sub):
    """Subtítulo `tipo` con las opciones `sub` (sin el prefijo `sub_`) sobre un fondo liso; devuelve la imagen RGB."""
    est = motor.Estilo({"subtitulo": tipo, "base": "pantalla", "acento": "#D97757", "tinta": "#111111", "borde": "#9AB8D8",
                        **{f"sub_{k}": v for k, v in sub.items()}})
    s = motor.Subtitulos({"subtitulos": {"y": 1455, "resaltar": [1]}}, PAL, est)
    lienzo = Image.fromarray(np.dstack([np.full((motor.H, motor.W, 3), fondo, np.uint8), np.full((motor.H, motor.W), 255, np.uint8)]), "RGBA")
    s.dibujar(lienzo, t)
    return np.asarray(lienzo)[..., :3].astype(int)


def cerca(im, hexa, tol=40):
    c = np.array([int(hexa[i:i + 2], 16) for i in (1, 3, 5)])
    return int((np.abs(im - c).sum(-1) < tol).sum())


def igual(a, b):
    return bool((a == b).all())


def soporta(tipo, clave):
    return so.SOPORTE[tipo][clave] is None


def test_cada_tipo_declara_cada_clave_y_el_motivo_de_lo_que_no_admite():
    assert sorted(so.SOPORTE) == sorted(TIPOS) == sorted(validar.SUBTITULOS)
    for tipo in TIPOS:
        assert set(so.SOPORTE[tipo]) == set(so.CLAVES)
        for clave, motivo in so.SOPORTE[tipo].items():
            assert motivo is None or (isinstance(motivo, str) and len(motivo) > 10 and "\n" not in motivo)   # una línea que explica por qué
    assert so.SOPORTE["hud"]["sub_caja"] and so.SOPORTE["hud"]["sub_caja_color"]   # el HUD no tiene caja


def test_una_sola_validacion_para_todos_los_tipos():
    malos = {"sub_color": "rojo", "sub_clave": "#FF00AA", "sub_caja_color": 5, "sub_caja": "si", "sub_efecto": "gira", "sub_fuente": "NoExiste"}
    buenos = {"sub_color": "#112233", "sub_clave": "#112233", "sub_caja_color": "#112233", "sub_caja": False, "sub_efecto": "pop", "sub_fuente": "Inter"}
    assert set(malos) == set(buenos) == set(so.CLAVES)
    for k in so.CLAVES:
        e1, e2 = [], []
        catalogo._valor_estilo(k, malos[k], e1)
        assert e1 and so.error(k, malos[k]), k                                  # la pantalla lo rechaza
        assert any(k in m for m in so.errores({k: malos[k]})), k                # y la compuerta del storyboard también, con la misma regla
        catalogo._valor_estilo(k, buenos[k], e2)
        assert not e2 and so.error(k, buenos[k]) is None, k
        assert k in validar.CLAVES["estilo"]


@pytest.mark.parametrize("tipo", TIPOS)
def test_sub_color_llega_al_dibujo(tipo):
    assert cerca(dibujar(tipo, color=VERDE), VERDE) > 150 and cerca(dibujar(tipo), VERDE) == 0
    assert soporta(tipo, "sub_color")


@pytest.mark.parametrize("tipo", TIPOS)
def test_sub_clave_llega_al_dibujo(tipo):
    assert cerca(dibujar(tipo, clave=AZUL), AZUL) > 150 and cerca(dibujar(tipo), AZUL) == 0
    assert soporta(tipo, "sub_clave")


@pytest.mark.parametrize("tipo", TIPOS)
def test_sub_fuente_llega_al_dibujo(tipo):
    assert not igual(dibujar(tipo, fuente="Courier Prime"), dibujar(tipo))
    assert soporta(tipo, "sub_fuente")


@pytest.mark.parametrize("tipo", TIPOS)
def test_sub_efecto_llega_al_dibujo(tipo):
    """Al arrancar la palabra cada efecto se ve distinto: corte entra de golpe, pop crece, sube se funde y sube."""
    caras = {e: dibujar(tipo, t=.03, efecto=e) for e in so.EFECTOS}
    for a in so.EFECTOS:
        for b in so.EFECTOS:
            assert a == b or not igual(caras[a], caras[b]), (tipo, a, b)
    assert soporta(tipo, "sub_efecto")


def test_sub_caja_llega_al_dibujo_o_queda_apagada_con_motivo():
    # Tira: la tira de papel (borde del estilo) aparece o desaparece
    assert cerca(dibujar("tira"), "#9AB8D8", 30) > 5000 and cerca(dibujar("tira", caja=False), "#9AB8D8", 30) == 0
    # Vidrio: el cristal (velo claro) sale en el relleno de la caja, o no hay nada
    assert cerca(dibujar("vidrio"), "#383838", 12) > 3000 and cerca(dibujar("vidrio", caja=False), "#383838", 12) < 300   # velo blanco al 22 % sobre negro
    # Básico: caja de color opcional (sin elegir, no hay)
    assert cerca(dibujar("basico", caja_color="#E5252A"), "#E5252A") == 0 and cerca(dibujar("basico", caja=True, caja_color="#E5252A"), "#E5252A") > 3000
    # HUD: no tiene caja → apagado con motivo y el dibujo no cambia
    assert so.SOPORTE["hud"]["sub_caja"] and igual(dibujar("hud", caja=True), dibujar("hud"))
    for tipo in ("tira", "vidrio", "basico"):
        assert soporta(tipo, "sub_caja")


def test_sub_caja_color_llega_al_dibujo_o_queda_apagado_con_motivo():
    assert cerca(dibujar("tira", caja_color=NARANJA), NARANJA, 30) > 5000
    v = dibujar("vidrio", caja_color=NARANJA)[1439:1500, 300:330].reshape(-1, 3).mean(0)
    assert v[0] > v[1] > v[2] > 5                                                   # el cristal se tiñe de naranja
    assert cerca(dibujar("basico", caja=True, caja_color=NARANJA), NARANJA, 30) > 3000
    assert so.SOPORTE["hud"]["sub_caja_color"] and igual(dibujar("hud", caja_color=NARANJA), dibujar("hud"))


@pytest.mark.parametrize("tipo,caja", [("tira", False), ("vidrio", False), ("vidrio", True)])
@pytest.mark.parametrize("fondo", [(0, 0, 0), (240, 240, 240)])
@pytest.mark.parametrize("t", [0.0, .03, .08, 1.0])
@pytest.mark.parametrize("y", [1455, 1700, 100])
def test_el_subtitulo_vidrio_o_sin_caja_no_sale_de_la_zona_segura_ni_en_la_entrada(tipo, caja, fondo, t, y):
    """Sobre fondo oscuro y claro y durante la entrada (el desplazamiento de 10 px se suma ANTES de ajustar a la zona): caja y letras dentro."""
    est = motor.Estilo({"subtitulo": tipo, "base": "pantalla", "sub_caja": caja})
    s = motor.Subtitulos({"subtitulos": {"y": y, "resaltar": [1]}}, PAL, est)
    lienzo = Image.fromarray(np.dstack([np.full((motor.H, motor.W, 3), fondo, np.uint8), np.full((motor.H, motor.W), 255, np.uint8)]), "RGBA")
    base = np.asarray(lienzo)[..., :3].astype(int)
    s.dibujar(lienzo, t)
    dif = np.abs(np.asarray(lienzo)[..., :3].astype(int) - base).max(-1)
    zx0, zy0, zx1, zy1 = config.ZONA_SEGURA
    for umbral, margen in ((90, 0), (12, config.SUAVE_PX)):
        ys, xs = np.where(dif > umbral)
        if ys.size:
            assert xs.min() >= zx0 - margen and xs.max() <= zx1 + margen and ys.min() >= zy0 - margen and ys.max() <= zy1 + margen, (umbral, ys.min(), ys.max())
    if t >= 1.0 and tipo == "vidrio" and caja:
        assert s.caja[1] >= zy0 and s.caja[3] <= zy1


def test_sin_caja_sobre_fondo_claro_hay_velo_de_bordes_suaves():
    claro = dibujar("vidrio", fondo=(240, 240, 240), caja=False)
    fila = claro[1470, 300:800, 0]                                   # a media altura de la franja: del fondo liso al velo sin escalón brusco
    assert fila.min() < 235 and np.abs(np.diff(fila)).max() < 25


def test_la_pantalla_recibe_lo_que_cada_tipo_admite_y_nombra_cada_clave():
    cat = catalogo.catalogo()["subtitulo"]
    assert sorted(cat["tipos"]) == sorted(TIPOS)
    for tipo, d in cat["tipos"].items():
        assert d["soporte"] == so.SOPORTE[tipo]
    assert [e["id"] for e in cat["efectos"]] == list(so.EFECTOS)
    js = (config.RAIZ / "app" / "app.js").read_text()
    for k in so.CLAVES:                                                              # la pantalla (Personalizar) maneja cada clave
        assert k in js, k


def test_sin_elegir_nada_el_estilo_efectivo_no_trae_opciones():
    est = motor.Estilo({"subtitulo": "tira"})
    assert est.sub == {"caja": None, "color": None, "clave": None, "caja_color": None, "efecto": None, "fuente": None}


ELEGIDO = {"sub_color": "#00FF00", "sub_fuente": "Inter", "sub_caja": False, "sub_efecto": "pop"}
DEL_ESTILO = {k: None for k in ELEGIDO}


@pytest.mark.parametrize("estilo", ["glass", "basico"])
@pytest.mark.parametrize("via", ["previa", "previa-sin-guardar", "seleccion"])
def test_del_estilo_vuelve_al_valor_del_estilo_por_la_api(tmp_path, estilo, via):
    """Ida y vuelta de Personalizar: elegir verde, Inter, sin caja y pop → queda en el storyboard; «Del estilo» (null) → vuelve al valor del
    preset (Básico trae sus propios sub_*; Glass no trae ninguno y se quitan). Las mismas reglas por /api/previa y /api/seleccion."""
    import json
    from estudio import servidor
    pre = {k: v for k, v in catalogo.presets()[estilo].items() if k != "nombre"}
    sbf = tmp_path / "storyboard.json"
    sbf.write_text(json.dumps({"estilo": {"id": estilo, **pre}, "elementos": []}))
    (tmp_path / "palabras.json").write_text("[]")

    def mandar(cambios):
        if via == "previa":
            servidor._guardar_estilo(tmp_path, cambios)
            return json.loads(sbf.read_text())["estilo"]
        if via == "previa-sin-guardar":     # lo que hace previas.con_director cuando no guarda (Edición avanzada): la misma regla, sin escribir
            return catalogo.aplicar_estilo(json.loads(sbf.read_text())["estilo"], cambios)
        catalogo.guardar(tmp_path, {"estilo": cambios})
        return json.loads(sbf.read_text())["estilo"]

    if via == "previa-sin-guardar":     # no escribe: cada llamada parte de lo guardado, así que la ida y vuelta se hace sobre el resultado
        assert "catalogo.aplicar_estilo" in (config.RAIZ / "estudio" / "previas.py").read_text()
        elegido = mandar(ELEGIDO)
        assert all(elegido[k] == v for k, v in ELEGIDO.items())
        sbf.write_text(json.dumps({"estilo": elegido, "elementos": []}))
        vuelta = mandar(DEL_ESTILO)
    else:
        elegido = mandar(ELEGIDO)
        assert all(elegido[k] == v for k, v in ELEGIDO.items()), elegido
        assert not so.errores(elegido)
        vuelta = mandar(DEL_ESTILO)
    for k in ELEGIDO:
        assert vuelta.get(k) == pre.get(k), (k, vuelta.get(k), pre.get(k))    # el del preset, o ausente si el preset no lo trae
    assert {k: v for k, v in vuelta.items() if k not in so.CLAVES} == {"id": estilo, **{k: v for k, v in pre.items() if k not in so.CLAVES}}
    if via == "seleccion":
        assert not any(k in json.loads((tmp_path / "preferencias.json").read_text()).get("estilo", {}) for k in ELEGIDO)


def test_las_opciones_se_leen_de_una_sola_lista():
    """Ni subtitulo_basico ni la pantalla repiten la lista de claves o de formas: salen de subtitulo_opciones y del catálogo."""
    from estudio import subtitulo_basico
    assert not hasattr(subtitulo_basico, "OPCIONES_CLAVES")
    js = (config.RAIZ / "app" / "vista.js").read_text() + (config.RAIZ / "app" / "app.js").read_text()
    assert 'tipo === "tira" || tipo === "vidrio"' not in js and "SUB_FORMAS" not in js
    assert so.para_pantalla()["tipos"]["vidrio"]["caja"] is True and so.para_pantalla()["tipos"]["hud"]["caja"] is False


def test_una_sola_formula_de_contraste():
    from estudio import portadas, texto_pelicula
    assert texto_pelicula.contraste is contraste.razon and texto_pelicula.CONTRASTE_MIN == contraste.MINIMO == 3.0
    assert portadas._luz is contraste.luz and not hasattr(motor, "_luz") and not hasattr(motor, "SUBTITULO_CONTRASTE")
    assert abs(contraste.razon((0, 0, 0), (255, 255, 255)) - 21) < 1e-9


def test_todos_los_caminos_de_vista_previa_mandan_el_id_del_estilo():
    js = (config.RAIZ / "app" / "vista.js").read_text()
    assert js.count("{ ...e.estilo, id: e.estiloId }") == 1
    una = js[js.index("async function una("):js.index("if (!r.ok)")]
    assert una.count("estilo }") == 1 and "e.estilo }" not in una     # el único camino de vista (previa-rapida) usa el estilo CON id


def test_basico_de_serie_con_caja_deja_visible_la_clave():
    """Valor de serie del preset (no una fórmula): la caja de Básico no es del color de la clave, así que al encender Caja la palabra clave se ve."""
    pre = catalogo.presets()["basico"]
    assert pre["sub_caja_color"].upper() != pre["sub_clave"].upper() and pre["sub_caja"] is False


def test_lo_que_elige_la_persona_sale_tal_cual_aunque_no_contraste():
    """Pablo organiza los colores: con texto y caja casi iguales (contraste ~1) el dibujo usa exactamente esos colores, sin contorno ni velo añadidos."""
    claro, hexa = (240, 240, 240), "#EEEEEE"
    tira = dibujar("tira", fondo=claro, color=hexa, clave=hexa, caja_color="#F0F0F0")[1200:1500, 60:1020].reshape(-1, 3)
    assert int((tira.sum(-1) < 180).sum()) == 0                                            # sin contorno oscuro (la tira no lleva sombra de letra)
    assert int((np.abs(tira - 238).sum(-1) < 12).sum()) > 500
    vid = dibujar("vidrio", fondo=claro, color=hexa, clave=hexa, caja_color="#F0F0F0")
    assert np.median(vid[1445:1455, 120:140].reshape(-1, 3)) > 200                         # el cristal sigue claro: no se oscureció «para que se lea»
    bas = dibujar("basico", fondo=claro, color=hexa, clave=hexa, caja=True, caja_color="#F0F0F0")[1200:1500, 60:1020].reshape(-1, 3)
    assert int((np.abs(bas - 240).sum(-1) < 12).sum()) > 3000 and int((bas.sum(-1) < 180).sum()) < 100   # la caja es del color elegido, sin contorno de letra
    hud = dibujar("hud", fondo=claro, color=hexa)
    assert not igual(hud, dibujar("hud", fondo=claro, color="#202020")) and cerca(hud, hexa, 12) > 200   # el color elegido es el que se dibuja
