"""Detector de voz adaptativo, apuntador y claqueta por patrón (T-0193 Fase 4)."""
import numpy as np
import pytest

from estudio import voz

HOP = voz.HOP


def energia(dur, tramos, base=-60.0):
    db = np.full(int(dur / HOP), base, np.float32)
    for a, b, nivel in tramos:
        db[int(a / HOP):int(b / HOP)] = nivel
    return db


def palabras(spec):
    return [{"w": w, "s": s, "e": e} for w, s, e in spec]


def test_el_umbral_se_adapta_al_ruido_de_cada_video():
    limpio = energia(10, [(2, 4, -20)], base=-70)
    ruidoso = energia(10, [(2, 4, -20)], base=-40) + np.random.default_rng(1).normal(0, 1, 1000).astype(np.float32)
    assert voz.umbral(limpio) < voz.umbral(ruidoso) < -20
    assert voz.mapa_voz(limpio)[300] and not voz.mapa_voz(limpio)[100]
    assert voz.mapa_voz(ruidoso)[300] and not voz.mapa_voz(ruidoso)[100]


def test_un_audio_de_pura_voz_no_se_apaga_entero():
    assert voz.mapa_voz(energia(5, [(0, 5, -18)], base=-18)).all()


def test_la_histeresis_no_parte_la_voz_por_un_bajon_pequeno_y_se_descartan_chasquidos():
    db = energia(4, [(1, 3, -20)], base=-70)
    db[200] = voz.umbral(db) - 1.5                 # un bajón de 1,5 dB bajo el umbral, dentro de la histéresis de 3 dB
    db[50] = -10                                    # un chasquido de 10 ms
    m = voz.mapa_voz(db)
    assert m[190:210].all() and not m[50]


def test_silencios_y_hay_voz():
    m = voz.mapa_voz(energia(6, [(1, 2, -20), (4, 5, -20)], base=-70))
    sil = voz.silencios(m)
    assert any(a < 2.1 and b > 3.9 for a, b in sil)
    assert voz.hay_voz(m, 1.5) and not voz.hay_voz(m, 3.0)


@pytest.mark.parametrize("frase,es", [
    (["1,", "2,", "3,", "va"], True), (["123va"], True), (["Dos,", "tres,", "acción."], True), (["tres", "acción"], True),
    (["Acción"], True), (["Corte."], True), (["otra", "vez"], True), (["Ya,", "siguiente"], True),
    (["Uno,", "preparas", "tu", "computadora"], False), (["uno"], False), (["Dos", "tres", "veces"], False),
    (["Si", "quieres", "aprender"], False), ([], False)])
def test_claqueta_por_patron_no_por_lista_cerrada(frase, es):
    assert voz.es_claqueta([{"w": w} for w in frase]) is es


def test_el_apuntador_es_voz_sostenida_bajo_el_talento_de_ese_video():
    """Talento a -16 dB; alguien dicta bajito a -34 (≈18 dB abajo) entre 5 y 9 s."""
    db = energia(20, [(1, 4, -16), (5, 9, -34), (11, 15, -16)], base=-65)
    ps = palabras([(f"t{k}", 1 + k * .5, 1.45 + k * .5) for k in range(6)] + [(f"a{k}", 5 + k * .5, 5.45 + k * .5) for k in range(8)] +
                  [(f"u{k}", 11 + k * .5, 11.45 + k * .5) for k in range(8)])
    marcadas = voz.apuntador(ps, db)
    assert marcadas == set(range(6, 14))


def test_un_video_entero_en_voz_baja_no_tiene_apuntador():
    db = energia(15, [(1, 14, -38)], base=-70)
    assert voz.apuntador(palabras([(f"w{k}", 1 + k * .5, 1.45 + k * .5) for k in range(24)]), db) == set()


def test_una_palabra_suave_suelta_no_es_apuntador_y_la_ultima_de_la_toma_tampoco():
    db = energia(12, [(1, 9, -16), (5, 5.4, -34)], base=-65)       # una sola palabra baja en medio del talento
    ps = palabras([(f"w{k}", 1 + k * .5, 1.45 + k * .5) for k in range(16)])
    assert voz.apuntador(ps, db) == set()


def test_marcar_fuera_suma_apuntador_y_claqueta_sin_quitar_marcas_previas():
    db = energia(20, [(0, 1.6, -30), (2, 5, -16), (6, 9, -34), (10, 14, -16)], base=-65)
    ps = palabras([("1,", 0, .3), ("2,", .4, .7), ("3,", .8, 1.1), ("va", 1.2, 1.6)] + [(f"t{k}", 2 + k * .5, 2.45 + k * .5) for k in range(6)] +
                  [(f"a{k}", 6 + k * .5, 6.45 + k * .5) for k in range(6)] + [(f"u{k}", 10 + k * .5, 10.45 + k * .5) for k in range(8)])
    ps[4].update(fuera=True, motivo="apuntador")      # marca del detector nuevo: se respeta
    out = voz.marcar_fuera(ps, db)
    motivos = {p["w"]: p.get("motivo") for p in out if p.get("fuera")}
    assert all(motivos[w] == "claqueta" for w in ("1,", "2,", "3,", "va"))
    assert all(motivos.get(f"a{k}") == "apuntador" for k in range(6))
    assert "t1" not in motivos and "u0" not in motivos and out[4]["fuera"] and "fuera" not in ps[5]


def test_marcas_viejas_sin_motivo_sobre_voz_fuerte_del_talento_se_sueltan_y_las_bajas_se_quedan():
    """Swiss C8872: el `voces_fuera` viejo marcó «Dejé de ser el editor» (a nivel del talento) como fuera de cámara."""
    db = energia(20, [(1, 5, -16), (6, 9, -36), (10, 14, -16)], base=-65)
    ps = palabras([(f"t{k}", 1 + k * .5, 1.45 + k * .5) for k in range(8)] + [(f"b{k}", 6 + k * .5, 6.45 + k * .5) for k in range(6)] +
                  [(f"u{k}", 10 + k * .5, 10.45 + k * .5) for k in range(8)])
    for k in (2, 3, 4):                       # fuertes
        ps[k]["fuera"] = True
    for k in (8, 9, 10, 11, 12, 13):          # bajas de verdad
        ps[k]["fuera"] = True
    out = voz.marcar_fuera(ps, db)
    assert not any(out[k].get("fuera") for k in (2, 3, 4))
    assert all(out[k].get("fuera") for k in (8, 9, 10, 11, 12, 13))


def test_una_palabra_fuerte_entre_dos_marcas_bajas_queda_marcada_para_no_dejar_agujero():
    db = energia(20, [(1, 5, -16), (6, 9, -36), (10, 14, -16)], base=-65)
    db[int(7.0 / HOP):int(7.45 / HOP)] = -16
    ps = palabras([(f"t{k}", 1 + k * .5, 1.45 + k * .5) for k in range(8)] + [(f"b{k}", 6 + k * .5, 6.45 + k * .5) for k in range(6)] +
                  [(f"u{k}", 10 + k * .5, 10.45 + k * .5) for k in range(8)])
    for k in range(8, 14):
        ps[k]["fuera"] = True
    assert voz.marcar_fuera(ps, db)[10].get("fuera")
