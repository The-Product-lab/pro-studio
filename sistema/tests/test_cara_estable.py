"""Caja de la cara sin manos de paso (Pablo 08-nov, Pop seg 2: «ahí hay un salto»).

Una muestra mala (la caja de la cara ensanchada hasta una mano levantada) hacía que el reencuadre corría la cámara
50-70 px durante esos cuadros y la devolvía. `caras_estables` debe dar la caja de la cabeza aunque la mano dure ~0,4 s, y el
supervisor de cámara debe medir con esa misma caja (lo que se mide es lo que se ve).
"""
import json

from estudio import camara_check, motor, persona

CABEZA = (440, 300, 640, 760)   # x0, y0, x1, y1 en px fuente
MANO = (700, 420, 980, 640)     # una muestra mala: la caja se ensancha hasta la mano levantada


def _proyecto(tmp_path, n=60, mano=range(25, 38)):
    """`persona.json` con una caja por cuadro; en los cuadros de `mano` la caja de la cara llega hasta la mano."""
    cuerpo = [300, CABEZA[1], 780, motor.H]
    cajas = [[[CABEZA[0], CABEZA[1], MANO[2] if i in mano else CABEZA[2], CABEZA[3]], cuerpo] for i in range(n)]
    (tmp_path / persona.ARCHIVO).write_text(json.dumps({"version": persona.VERSION, "paso": 1, "cuadros": n, "cajas": cajas}))
    return list(range(n))


def test_mano_levantada_no_ensancha_la_cara(tmp_path):
    mapa = _proyecto(tmp_path)
    tabla = persona.Tabla(tmp_path)
    crudas = [tabla.cara(i) for i in mapa]
    assert crudas[30][2] > crudas[10][2] + 200, "la prueba debe reproducir el error: la mano ensancha la caja cruda"
    caras = motor.caras_estables(tmp_path, mapa)
    derechos = [caras[i][2] for i in mapa]
    assert max(derechos) - min(derechos) <= 4, f"la caja de la cara cambia con la mano: {sorted(set(derechos))}"


def test_cache_se_reusa_y_se_renueva(tmp_path):
    mapa = _proyecto(tmp_path, n=20, mano=())
    a = motor.caras_estables(tmp_path, mapa)
    assert (tmp_path / ".cara-estable.json").exists()
    assert motor.caras_estables(tmp_path, mapa) == a
    otro = mapa[:10]
    assert set(motor.caras_estables(tmp_path, otro)) == set(otro), "otro mapa (otros cortes) no reusa la caja vieja"
    assert json.loads((tmp_path / ".cara-estable.json").read_text())["clave"]


def test_supervisor_mide_con_la_cara(monkeypatch, tmp_path):
    """El supervisor pasa la caja estable de la cara a camara_cuadro, igual que el render."""
    vistas = []
    original = motor.CamaraProyecto.camara_cuadro

    def espia(s, of, t, esc, s0, s1, cara=None, pe=None):
        vistas.append(cara)
        return original(s, of, t, esc, s0, s1, cara, pe)

    mapa = _proyecto(tmp_path, n=30, mano=())
    (tmp_path / "fuente.json").write_text(json.dumps({"cuadros": len(mapa)}))
    sb = {"cortes": [], "escenas": [{"t0": 0.0, "persona": {"modo": "completa"}}], "estilo": {}}
    monkeypatch.setattr(motor.CamaraProyecto, "camara_cuadro", espia)
    camara_check.medir(tmp_path, sb)
    assert vistas and all(v is not None for v in vistas)


def test_vista_previa_mide_solo_su_ventana_con_las_mismas_cajas(tmp_path):
    """Las vistas previas piden `cerca`: mismas cajas que el cálculo completo, sin leer todas las máscaras ni guardar caché."""
    mapa = _proyecto(tmp_path, n=90, mano=range(25, 38))
    parcial = motor.caras_estables(tmp_path, mapa, cerca={30, 70})
    assert not (tmp_path / ".cara-estable.json").exists() and set(parcial) == {30, 70}
    completo = motor.caras_estables(tmp_path, mapa)
    assert parcial == {i: completo[i] for i in (30, 70)}


def test_vista_previa_da_las_mismas_cajas_que_el_calculo_completo_con_el_suavizado(tmp_path):
    """La caja de la cara se suaviza con vecinos lejanos (±CARA_SUAVE_S ×2): `cerca` amplía lo que mide y da lo MISMO que el cálculo completo."""
    mapa = _proyecto(tmp_path, n=240, mano=range(100, 141))
    parcial = motor.caras_estables(tmp_path, mapa, cerca={10, 118, 125, 200, 239})
    completo = motor.caras_estables(tmp_path, mapa)
    assert set(parcial) == {10, 118, 125, 200, 239}
    for i, caja in parcial.items():
        assert all(abs(a - b) < 1e-9 for a, b in zip(caja, completo[i])), i
