"""Supervisor de cámara (Pablo 08-nov): un caso que brinca, uno limpio, el A→B que no se lleva un corte real y el arreglo de capas."""
import json

import pytest

from estudio import camara_check

FPS = 30
pytestmark = pytest.mark.usefixtures("camara_movil")   # prueban la maquinaria de cámara, hoy apagada por regla


def proyecto(tmp_path, sb, dur=14.0):
    c = tmp_path / "p"
    c.mkdir()
    (c / "fuente.json").write_text(json.dumps({"video": "x.mp4", "cuadros": int(dur * FPS)}))
    (c / "palabras.json").write_text(json.dumps([{"w": "hola", "s": i * .5, "e": i * .5 + .3} for i in range(int(dur * 2))]))
    (c / "storyboard.json").write_text(json.dumps(sb))
    return c


def base(estilo="vox", **extra):
    sb = {"estilo": {"id": estilo, "base": "pantalla", "flotar": 4}, "cortes": [],
          "escenas": [{"t0": 0, "entrada": "corte"}, {"t0": 5, "entrada": "flash", "camara_mov": "suave", "persona": {"modo": "oculta"}},
                      {"t0": 10, "entrada": "corte"}], "elementos": []}
    sb.update(extra)
    return sb


def test_limpio_pasa(tmp_path):
    m = camara_check.medir(proyecto(tmp_path, base()))
    assert m["fallas"] == [] and m["saltos"] == 0


def test_brinco_de_keyframes_falla_y_no_se_arregla(tmp_path):
    sb = base(camara=[{"t": 1, "zoom": 1.0}, {"t": 3, "zoom": 1.0}, {"t": 3.1, "zoom": 1.5}, {"t": 4, "zoom": 1.5}])
    c = proyecto(tmp_path, sb)
    assert any("brincos" in f for f in camara_check.medir(c)["fallas"])
    antes = (c / "storyboard.json").read_text()
    with pytest.raises(ValueError, match="supervisor"):
        camara_check.supervisar(c, avance=lambda *_: None)
    assert (c / "storyboard.json").read_text() == antes   # lo que no se arregla no se toca


def test_corte_real_dentro_de_pantalla_completa_no_brinca(tmp_path):
    """Antes el A→B se medía en tiempo fuente: un corte de 3 s dentro de la escena se llevaba 3/5 del movimiento de golpe."""
    m = camara_check.medir(proyecto(tmp_path, base(cortes=[[6.0, 7.0]])))
    assert m["saltos"] == 0 and m["peor"]["px"] < 14 and m["peor"]["zoom"] < .02


def test_camara_propia_un_solo_movimiento(tmp_path):
    c = proyecto(tmp_path, base("julian-alborna-3d", camara=[{"t": 0, "zoom": 1.0}, {"t": 9, "zoom": 1.3}]))
    assert any("a la vez" in f for f in camara_check.medir(c)["fallas"])
    m = camara_check.supervisar(c, avance=lambda *_: None)
    assert m["fallas"] == [] and m["capas_max"] <= 1
    assert "encuadre" in json.loads((c / "storyboard.json").read_text())["camara_apagar"]


def test_julian3d_pantalla_completa_quieta(tmp_path):
    """Julián 3D (Pablo 08-nov: «déjalo quieto»): en la escena oculta la cámara del motor no se mueve: zoom 1 y sin desplazamiento."""
    c = proyecto(tmp_path, base("julian-alborna-3d"))
    p = camara_check._Ligera(c, json.loads((c / "storyboard.json").read_text()))
    assert p.pantalla_quieta
    for of in range(5 * FPS, 10 * FPS):
        t = p.mapa[of] / FPS
        esc, s0, s1 = p.escena(t)
        v = p.camara_cuadro(of, t, esc, s0, s1)
        assert v["cw"] == pytest.approx(1080) and v["dx"] == 0 and v["dy"] == 0 and "pantalla" not in v["capas"]


def test_estilo_puede_apagar_pantalla_por_datos(tmp_path):
    sb = base("vox")
    sb["estilo"]["camara_apagar"] = ["pantalla"]
    c = proyecto(tmp_path, sb)
    assert camara_check._Ligera(c, sb).pantalla_quieta


def test_viaje_que_arranca_en_cero_no_brinca_el_primer_cuadro(tmp_path):
    """Pop 08-nov: con dx=0 en el cuadro 0 el margen de giro no estaba y en el 1 entraba entero (2 % de zoom de golpe)."""
    sb = base()
    sb["estilo"] = {"id": "vox", "base": "pantalla"}
    sb["camara"] = [{"t": 0, "zoom": 1.0, "x": 0, "y": 0, "rot": 0}, {"t": 6, "zoom": 1.0, "x": 40, "y": 0, "rot": 0}]
    c = proyecto(tmp_path, sb)
    p = camara_check._Ligera(c, sb)
    z = []
    for of in range(4):
        t = p.mapa[of] / FPS
        esc, s0, s1 = p.escena(t)
        z.append(camara_check._vista(p.camara_cuadro(of, t, esc, s0, s1))[0])
    assert max(abs(b - a) for a, b in zip(z, z[1:])) < .002, z   # antes: .02 de golpe en el cuadro 1
    assert camara_check.medir(c)["fallas"] == []


def test_valor_igual_al_maximo_no_falla(tmp_path, monkeypatch):
    c = proyecto(tmp_path, base())
    peor = camara_check.medir(c)["peor"]["zoom"]
    monkeypatch.setattr(camara_check, "SALTO_ZOOM", peor - 1e-9)   # un epsilon por debajo: la tolerancia lo absorbe
    assert camara_check.medir(c)["saltos"] == 0


def test_corte_fraccionario_dentro_de_pantalla_completa_no_sacude(tmp_path):
    """Swiss 21,6 s (10-nov): un corte de 0,030 s quita UN cuadro entero (1/30 s) pero `camara.salida` restaba 0,030: el avance del A→B
    daba un tirón (4,6 px por cuadro de aceleración) al pasar el corte. El avance se mide ahora en cuadros de salida."""
    sb = base(cortes=[[2.015, 2.045]])
    sb["escenas"][1]["camara_mov"] = "continuo"
    sb["escenas"][1]["t0"] = 1.0
    sb["escenas"][2]["t0"] = 9.0
    c = proyecto(tmp_path, sb)
    p = camara_check._Ligera(c, sb)
    v = []
    for of in range(45, 80):                      # alrededor del corte (cuadro 61), dentro de la escena oculta
        t = p.mapa[of] / FPS
        esc, s0, s1 = p.escena(t)
        v.append(p.camara_cuadro(of, t, esc, s0, s1)["capas"]["pantalla"])
    d = [(b[0] - a[0], b[1] - a[1], b[2] - a[2]) for a, b in zip(v, v[1:])]
    assert max(abs(y - x) for a, b in zip(d, d[1:]) for x, y in zip(a, b)) < 1e-6, d   # «continuo» es lineal: velocidad constante, sin tirón en el corte
    assert camara_check.medir(c)["fallas"] == []


def test_empuje_de_la_cara_entra_y_sale_sin_quiebre():
    """Prestiggio 22,4 s: el empujón duro de la cara frenaba de golpe (de 4,4 px por cuadro a 0). Ahora la rampa es continua y nunca
    deja la cara más adentro del margen que el empujón duro."""
    from estudio import motor
    k = motor.ENCUADRE_CARA_SUAVE_PX
    assert motor.empuje_suave(-k, k) == 0 and motor.empuje_suave(k, k) == k
    for x in range(-100, 100):
        assert motor.empuje_suave(x, k) >= max(0, x) - 1e-9
    v = [motor.empuje_suave(x * 4.4, k) for x in range(-30, 30)]            # la cara se acerca al borde a 4,4 px por cuadro
    assert max(abs((c - b) - (b - a)) for a, b, c in zip(v, v[1:], v[2:])) < 1.0   # antes: 4,4 de golpe
