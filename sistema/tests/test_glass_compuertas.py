"""Compuertas nacidas del Glass de prueba del 10-nov (tests/fixtures/glass-nuevo-10nov): cámara que no flota, cosas de más a la vez, cápsulas vacías, «1 citas»."""
import json
from pathlib import Path

from estudio import camara, motor, validar

PRESETS = Path(__file__).parent.parent / "librerias" / "estilos" / "presets.json"
BANCO = Path(__file__).parent / "fixtures" / "glass-nuevo-10nov"


def _sb():
    return json.loads((BANCO / "storyboard.json").read_text())


def _dur(sb):
    pal = [p for p in json.loads((BANCO / "palabras.json").read_text()) if "s" in p]
    return camara.salida(sb, pal[-1]["e"] + .6)


def test_el_reencuadre_no_brinca_y_el_supervisor_no_tiene_que_apagarlo():
    """Los «brincos» del Glass del 10-nov NO eran golpes de zoom: eran el reencuadre arrancando en 1.0 un cuadro antes de su primer tramo (0,23 de zoom)
    y tramos de reencuadre más cortos de lo que permite el zoom por cuadro; más un escalón de la caja de la cara (suavizada ahora)."""
    from estudio import camara_check
    sb = _sb()
    # el reencuadre (motor.encuadres) ya no arranca en 1.0 ni mueve 0,16 de zoom en menos de ENCUADRE_TRAMO_MIN_S
    pal = [p for p in json.loads((BANCO / "palabras.json").read_text()) if "s" in p]
    lista = motor.encuadres(sb, pal, 68.4, "glass-nuevo-10nov")
    assert motor.encuadre_en(lista, lista[0][0] - .005) == lista[0][2]
    assert all(b - a >= motor.ENCUADRE_TRAMO_MIN_S or A == B for a, b, A, B in lista)
    assert camara_check.CAPAS_GENERICAS == ("encuadre", "flotar")


def test_una_sola_cosa_a_la_vez_en_glass():
    sb, r = _sb(), validar.reglas("glass")
    assert r["elementos_a_la_vez_max"] == 1 and not validar.reglas("vox").get("elementos_a_la_vez_max")
    err = validar._una_cosa_a_la_vez(sb, r)
    assert err and err[0].startswith("una cosa:")                                # el caso real tiene tramos con varias cosas
    de_a_una = {**sb, "elementos": [e for e in sb["elementos"] if e["id"] in ("v1", "t1", "e2")], "trazos": []}
    assert validar._una_cosa_a_la_vez(de_a_una, r) == []                         # tarjeta + su texto (grupo g1) y luego una etiqueta: una a la vez


def test_ninguna_capsula_de_vidrio_vacia():
    err = validar._vidrio_vacio(_sb())
    assert err and "v5" in err[0]                                                # entraba 0,7 s antes que su texto
    sb = _sb()
    sb["elementos"] = [e for e in sb["elementos"] if e["id"] not in ("t5",)]
    assert any("v5" in e for e in validar._vidrio_vacio(sb))
    sb = _sb()
    for e in sb["elementos"]:
        if e["id"] == "v5":
            e["t0"] = 28.04                                                       # entra con su texto
    assert not any("v5" in e for e in validar._vidrio_vacio(sb))


def test_el_contador_dice_1_cita_y_2_citas():
    d = {"sufijo": " citas"}
    assert motor.texto_contador(d, 1) == "1 cita" and motor.texto_contador(d, 2) == "2 citas"
    assert motor.texto_contador({"sufijo": " días", "singular": " día"}, 1) == "1 día"
    assert motor.texto_contador({"sufijo": " %"}, 1) == "1 %"
    assert motor.texto_contador({"sufijo": " citas", "decimales": 1}, 1) == "1.0 citas"


def test_un_escalon_de_la_caja_de_la_cara_se_vuelve_rampa():
    mapa = list(range(300))
    caja = lambda x: (x, 100.0, x + 200.0, 300.0)   # noqa: E731
    cruda = {i: caja(0.0 if i < 150 else 86.0) for i in mapa}
    suave = motor._suavizar_caras(cruda, mapa)
    pasos = [abs(suave[i + 1][0] - suave[i][0]) for i in range(299)]
    assert max(pasos) < 86 / 15           # el escalón de 86 px se reparte en más de 30 cuadros
    assert suave[0][0] == 0.0 and abs(suave[299][0] - 86.0) < 1e-6
    assert motor._suavizar_caras({0: None, 1: caja(5.0)}, [0, 1])[0] is None


def _gancho(**extra):
    return {"id": "g", "tipo": "texto", "t0": 0.0, "t1": 3.0, "x": 540, "y": 400, "entra": "fundido", "dur": .01, "flotar": 0, "gancho": True, **extra}


def test_el_gancho_es_un_solo_grupo_de_texto_o_caja_y_fijo():
    r = validar.reglas("vox")
    base = {"estilo": {"id": "vox"}}
    assert validar._gancho({**base, "elementos": [_gancho()]}, r) == []
    assert validar._gancho({**base, "elementos": [_gancho(), _gancho(id="g2", grupo="otro")]}, r)             # 2 ganchos
    assert validar._gancho({**base, "elementos": [_gancho(tipo="foto")]}, r)                                   # una imagen con gancho
    assert validar._gancho({**base, "elementos": [_gancho(flotar=3)]}, r)                                      # un gancho que flota
    sin_flotar_explicito = _gancho(); sin_flotar_explicito.pop("flotar")
    assert validar._gancho({"estilo": {"id": "vox", "flotar_elementos": 2}, "elementos": [sin_flotar_explicito]}, r)   # flota por el estilo
    assert validar._gancho({**base, "elementos": [_gancho(entra="pop")]}, r)   # entrada animada
    dos_de_un_grupo = [_gancho(grupo="h"), _gancho(id="g2", tipo="vidrio", grupo="h")]
    assert validar._gancho({**base, "elementos": dos_de_un_grupo}, r) == []                                    # tarjeta + texto = un grupo


def test_el_inicio_limpio_cubre_trazos_y_golpes_de_zoom_y_el_gancho_no_se_teclea():
    r = {"inicio_limpio_s": 3}
    sb = {"estilo": {"id": "vox"}, "elementos": [], "trazos": [{"tipo": "linea", "t0": 0.5, "t1": 2.0}], "punch": [1.0]}
    err = validar._inicio_limpio(sb, r)
    assert any(e.startswith("trazos[0]") for e in err) and any(e.startswith("punch en") for e in err)
    limpio = validar.limpiar_inicio({**sb, "trazos": [{"tipo": "linea", "t0": 0.5, "t1": 9.0}]})   # lo que entra en el inicio pasa al segundo N
    assert limpio["punch"] == [] and limpio["trazos"][0]["t0"] >= 3 - 1e-6
    assert validar._inicio_limpio({"estilo": {"id": "vox"}, "trazos": [{"tipo": "linea", "t0": 3.5, "t1": 4}], "punch": [3.5]}, r) == []
    assert validar._gancho({"estilo": {"id": "vox"}, "elementos": [_gancho(tecleo=True)]}, validar.reglas("vox"))
    assert validar._gancho({"estilo": {"id": "vox"}, "elementos": [_gancho(titila=True)]}, validar.reglas("vox"))
