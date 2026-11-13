"""Ficha completa de cada estilo vigente y NO DAÑO: el estilo efectivo que usa el motor no cambia al completar/limpiar presets.

`tests/estilos_nodano/efectivos.json` es la foto del estilo efectivo (preset + defectos del motor) tomada ANTES de completar las fichas.
Si un cambio mueve un valor, esta prueba falla; para aceptarlo a propósito, regenerar con `uv run python tests/test_estilos_fichas.py`
y que lo apruebe Pablo. El render real (cuadro por cuadro) está en tests/render_nodano.py."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from estudio import camara, config, motor, sonido, subtitulo_opciones, validar  # noqa: E402

PRESETS = config.RAIZ / "librerias" / "estilos" / "presets.json"
FOTO = config.RAIZ / "tests" / "estilos_nodano" / "efectivos.json"
# cambios decididos por Pablo (10-nov) que SÍ mueven el estilo efectivo; todo lo demás debe seguir idéntico a la foto
# Estas diferencias con la foto son DECISIONES de Pablo (10-nov); todo lo demás debe seguir idéntico a la foto.
_T4 = {"tope_imagenes": 4}   # «menos imágenes»: con 8 la app daba Sencilla/Media/Pro = 6/8/10 en vez de 2/4/6 (3D conserva su 8: excepción escrita)
_F = {"flotar": 40}          # todos flotan a la vista (piso `flota_siempre`), menos Básico
INTENCIONALES = {
    "basico": {**_T4, "sfx": 0.0, "basico": {"caja": False, "caja_color": [17, 17, 17], "clave": [229, 37, 42], "color": [255, 255, 255], "efecto": "corte"}},
    # Básico: caja de serie oscura; con la roja (igual que la clave) la palabra clave se perdía al encender Caja
    "cine": {**_F, **_T4, "imagenes": True}, "glass": {**_F, **_T4, "sonido_paleta": "digital", "subtitulo": "vidrio"},   # + «glass debería usar una caja de glass, no de papel» (10-nov)
    "imprenta": {**_F, **_T4, "sonido_paleta": "papel-maquina"},
    "julian-alborna": {**_F, "flotar_elementos": 2, "sonido_paleta": "papel-maquina"},
    "julian-alborna-3d": {**_F, "flotar_elementos": 2},
    "luminoso": {**_F, **_T4, "flotar_elementos": 2, "imagenes": True},          # «un movimiento a la vez» para todos (tope 2)
    "maestro": _F, "maestro-calma": {**_F, **_T4}, "pop": {**_F, **_T4},
    "prestiggio": {**_F, "sonido_paleta": "digital"}, "swiss": {**_F, **_T4, "sonido_paleta": "digital"}, "vox": {**_F, **_T4},
}
VIGENTES = ["basico", "cine", "glass", "imprenta", "julian-alborna", "julian-alborna-3d", "lemo", "luminoso", "maestro", "maestro-calma",
            "pop", "prestiggio", "swiss", "vox"]   # «lemo» (12-nov): el reel hablado con apoyos de Lemo, se elige desde Estilos Pro
# claves que TODO preset declara (el valor sale de lo que el motor usaba); las sub_* solo las usa el subtítulo «basico»
FICHA = ["nombre", "base", "persona", "acento", "acento2", "tinta", "papel", "borde", "tono", "grano", "fuente", "fuente_script",
         "fuente_mono", "subtitulo", "crt", "aberracion_corte", "transicion", "flotar", "flotar_elementos", "bloom", "sfx",
         "imagenes", "tope_imagenes", "sonido_paleta", "camara_apagar", "sin_director"]


def efectivo(estilo_id, pre):
    """Todo lo que el motor, el sonido y el director leen del bloque `estilo`, con el defecto de cada uno aplicado."""
    d = {k: v for k, v in pre.items() if k != "nombre"}
    e = motor.Estilo(d)
    sb_est = {"id": estilo_id, **d}
    return {
        "base": e.base, "persona_bn": e.persona_bn, "acento": e.acento, "acento2": e.acento2, "tinta": e.tinta, "papel": e.papel,
        "borde": e.borde, "tono": list(e.tono), "grano": e.grano, "fuente": e.fuente, "roles": e.roles, "subtitulo": e.subtitulo,
        "basico": e.basico, "crt": e.crt, "aberracion_corte": e.aberracion_corte, "transicion": e.transicion, "flotar": e.flotar,
        "flotar_elementos": e.flotar_elementos, "bloom": e.bloom,
        "sfx": float(d.get("sfx", config.SFX_VOLUMEN)), "imagenes": bool(d.get("imagenes")),
        "tope_imagenes": int(d.get("tope_imagenes", config.TOPE_IMAGENES)), "sonido_paleta": sonido.paleta_de(sb_est),
        "camara_apagar": sorted(set(d.get("camara_apagar") or ()) | ({"pantalla"} if estilo_id in motor.ESTILOS_CAMARA_PROPIA else set())),
        "sin_director": bool(d.get("sin_director")), "filtro": d.get("filtro", "ninguno"), "color": d.get("color"),
    }


def _todos():
    pre = json.loads(PRESETS.read_text())
    return {i: json.loads(json.dumps(efectivo(i, pre[i]), default=list)) for i in VIGENTES}


@pytest.mark.parametrize("estilo", VIGENTES)
def test_el_estilo_efectivo_no_cambia(estilo):
    esperado = {**json.loads(FOTO.read_text())[estilo], **INTENCIONALES.get(estilo, {})}
    assert _todos()[estilo] == esperado


@pytest.mark.parametrize("estilo", VIGENTES)
def test_la_ficha_esta_completa(estilo):
    pre = json.loads(PRESETS.read_text())[estilo]
    falta = [k for k in FICHA if k not in pre]
    assert not falta, f"{estilo}: al preset le faltan {falta}"
    if pre.get("subtitulo") == "basico":
        assert not [k for k in subtitulo_opciones.CLAVES if k not in subtitulo_opciones.SIN_VALOR_DE_SERIE and k not in pre]


@pytest.mark.parametrize("estilo", VIGENTES)
def test_ningun_estilo_pasa_el_tope_de_elementos_que_flotan(estilo):
    """Un movimiento a la vez, para los 13 (Pablo, 10-nov): un solo tope global (reglas.json › flotar_elementos_max)."""
    tope = validar.reglas(estilo)["flotar_elementos_max"]
    assert tope is not None
    assert json.loads(PRESETS.read_text())[estilo]["flotar_elementos"] <= tope
    reglas = json.loads((config.RAIZ / "perfil" / "reglas.json").read_text())
    assert "flotar_elementos_max" in reglas["global"] and not any("flotar_elementos_max" in v for v in reglas["estilos"].values())


def niveles_de_la_app(tope):
    """Misma fórmula que app/app.js (`edicionDe`): Sencilla, Media y Pro = tope-2 (mín. 1), tope, tope+2."""
    return [max(1, tope - 2), tope, tope + 2]


@pytest.mark.parametrize("estilo", VIGENTES)
def test_la_app_y_el_director_usan_el_mismo_tope(estilo):
    tope = json.loads(PRESETS.read_text())[estilo]["tope_imagenes"]
    s, m, p = niveles_de_la_app(tope)
    assert s < m < p                                  # los tres niveles de la app son distintos
    assert m == tope                                   # «Media» es lo que el director usa cuando nadie elige
    if estilo not in ("julian-alborna-3d",):          # 3d conserva el 8 que ya tenía antes de esta limpieza: lo decide Pablo
        assert m <= 4, "menos imágenes (Pablo, 10-nov)"


@pytest.mark.parametrize("estilo", [e for e in VIGENTES if e != "basico"])
def test_todos_flotan_a_la_vista_menos_basico(estilo):
    """Pablo (10-nov): TODOS flotan visible; Básico queda quieto. El piso medible es camara.FLOTA_PISO_PX; ninguna capa de flotación apagada."""
    pre = json.loads(PRESETS.read_text())[estilo]
    assert pre["flotar"] > 0 and "flotar" not in pre["camara_apagar"]
    sb = {"estilo": {"id": estilo, **pre}}
    assert camara.flotacion_px(sb, 60) >= camara.FLOTA_PISO_PX, estilo


def test_la_camara_es_fija_en_todos_los_estilos():
    """Pablo, 11-nov: «los movimientos de cámara lo que están haciendo es dañando el video… dejas todo estático»."""
    from estudio import camara, motor
    assert camara.fija() and validar.reglas(None)["camara_fija"]
    for estilo in json.loads(PRESETS.read_text()):
        sb = {"estilo": {"id": estilo, "flotar": 40}, "punch": [1.0], "empuje": .05}
        assert motor.capas_apagadas(sb) == set(motor.CAPAS_CAMARA)
    cam = motor.CamaraProyecto()
    cam.camara_fija = True
    for esc in ({"t0": 0, "persona": {"modo": "completa"}}, {"t0": 0, "persona": {"modo": "oculta"}, "camara_mov": "continuo"}):
        assert cam.camara_cuadro(45, 1.5, esc, 0.0, 4.0) == {"cw": motor.W, "ch": motor.H, "dx": 0, "dy": 0, "rot": 0, "gira": False, "capas": {}}


def test_con_camara_fija_un_golpe_de_zoom_no_suena():
    from estudio import sonido
    p = type("P", (), {"sb": {"punch": [1.0], "camara": [{"t": 0}, {"t": 2.0}], "estilo": {}}, "escenas": [{"t0": 0}], "elementos": [], "trazos": [],
                       "mapa": list(range(120))})()
    assert not {"golpe", "camara"} & {e[1] for e in sonido.eventos(p)}


def test_una_sola_regla_de_camara():
    r = json.loads((config.RAIZ / "perfil" / "reglas.json").read_text())
    notas = [n for n in r["global"]["nota"] if n.startswith("Cámara")]
    assert len(notas) == 1 and "camara_mov_cada_s" not in r["global"]
    from estudio import director
    assert director._regla_camara() == notas[0]     # el prompt del director LEE la regla, no la repite con otras palabras


def test_no_quedan_presets_fuera_de_los_vigentes():
    assert sorted(json.loads(PRESETS.read_text())) == sorted(VIGENTES)



# ---- contrato por estilo (lo que Pablo exige de cada uno; los valores salen de la ficha y de la regla de cámara) ----
# subtitulo, paleta de sonido, tope de imágenes, ¿pide arte?; la cámara y los golpes se miden en las pruebas de abajo.
CONTRATO = {
    "basico": ("basico", "organico", 4, False), "cine": ("hud", "cine", 4, True), "glass": ("vidrio", "digital", 4, True),
    "imprenta": ("tira", "papel-maquina", 4, True), "julian-alborna": ("hud", "papel-maquina", 3, True), "julian-alborna-3d": ("hud", "digital", 8, True),
    "luminoso": ("hud", "organico", 4, True), "maestro": ("hud", "organico", 4, True), "maestro-calma": ("hud", "organico", 4, True),
    "pop": ("tira", "organico", 4, True), "prestiggio": ("hud", "digital", 2, False), "swiss": ("hud", "digital", 4, True),
    "vox": ("tira", "organico", 4, True), "lemo": ("hud", "organico", 4, True),
}


def test_el_contrato_cubre_todos_los_estilos():
    assert sorted(CONTRATO) == sorted(VIGENTES)


@pytest.mark.parametrize("estilo", VIGENTES)
def test_contrato_subtitulo_sonido_y_tope(estilo):
    sub, paleta, tope, imagenes = CONTRATO[estilo]
    ef = _todos()[estilo]
    assert (ef["subtitulo"], ef["sonido_paleta"], ef["tope_imagenes"], ef["imagenes"]) == (sub, paleta, tope, imagenes)
    assert ef["tope_imagenes"] <= config.TOPE_IMAGENES_MAX
    assert paleta in sonido.PALETAS and sub in validar.SUBTITULOS


@pytest.mark.parametrize("estilo", [e for e in VIGENTES if e not in ("basico", "julian-alborna-3d")])
def test_la_camara_viaja_continua_sin_brincos(estilo):
    """La cámara del motor para este estilo: sin brincos, y sin ir y venir (regla única de cámara, Pablo 10-nov)."""
    pre = json.loads(PRESETS.read_text())[estilo]
    sb = {"estilo": {"id": estilo, **{k: v for k, v in pre.items() if k != "nombre"}}, "cortes": [], "escenas": [{"t0": 0.0}], "elementos": []}
    for dur in (30, 60, 110):
        m = camara.saltos(sb, dur)
        assert m["zoom_por_cuadro"] <= .004 and m["px_por_cuadro"] <= 4, (estilo, dur, m)
        assert m["vueltas_zoom"] <= max(1, dur / 6), (estilo, dur, m)


@pytest.mark.parametrize("estilo", VIGENTES)
def test_golpes_de_zoom_un_solo_techo_para_los_13(estilo):
    """Los golpes de zoom: UN techo (reglas.json › punch_max_por_min, mismo número para los 13); la compuerta nunca exige un mínimo."""
    tope = validar.reglas(estilo).get("punch_max_por_min")
    assert tope is None if estilo == "basico" else tope == 4
    pre = json.loads(PRESETS.read_text())[estilo]
    assert not [k for k in pre if "camara" in k and k != "camara_apagar"]
    if tope:
        pal = [{"w": "a", "s": 0.0, "e": 59.9}]
        assert validar._camara_viva({"punch": []}, validar.reglas(estilo), pal, "normal") == []                      # sin golpes: nada que exigir
        assert validar._camara_viva({"punch": [5.0, 6.0, 7.0, 8.0, 9.0]}, validar.reglas(estilo), pal, "normal")      # 5 en un minuto: de más


def test_ningun_preset_trae_color_ni_claves_sueltas():
    """`color` es una preferencia por video (preferencias.json), nunca del estilo; y el preset solo trae claves que el motor conoce."""
    for estilo, pre in json.loads(PRESETS.read_text()).items():
        assert "color" not in pre and "filtro" not in pre, estilo
        sobran = set(pre) - validar.CLAVES["estilo"]
        assert not sobran, (estilo, sobran)


def test_basico_no_toma_prestado_el_ejemplo_de_otro_estilo():
    from estudio import director
    with pytest.raises(ValueError):
        director._ejemplo("basico")

if __name__ == "__main__":
    FOTO.write_text(json.dumps(_todos(), indent=1, sort_keys=True, ensure_ascii=False))
    print("foto escrita:", FOTO)
