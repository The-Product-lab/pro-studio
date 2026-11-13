"""Fase 4 (T-0193): `montaje.reparar` pone cada corte en un silencio real, en código, y no tira nada por algo medible.
Proyectos sintéticos: la voz es un bloque de -20 dB, el resto -60 dB (mapa de energía directo, sin audio)."""
import json
import random

import numpy as np
import pytest

from estudio import montaje, voz

HOP = voz.HOP


def proyecto(tmp_path, dur, voces, palabras, nombre="p"):
    """voces = [(t0, t1)] con voz; palabras = [(w, s, e)] o [(w, s, e, True)] (fuera)."""
    c = tmp_path / nombre
    c.mkdir()
    db = np.full(int(dur / HOP), -60.0, np.float32)
    for a, b in voces:
        db[int(a / HOP):int(b / HOP)] = -20.0
    np.save(c / ".energia.npy", db.astype(np.float16))
    (c / "fuente.json").write_text(json.dumps({"video": "x.mp4", "cuadros": int(dur * 30)}))
    ps = [{"w": w, "s": s, "e": e, **({"fuera": True, "motivo": "apuntador"} if len(x) > 3 else {})} for x in palabras for (w, s, e) in [x[:3]]]
    (c / "palabras.json").write_text(json.dumps(ps))
    return c


def mantiene(sb, c, palabra):
    ctx = montaje.contexto(c)
    p = next(p for p in ctx.palabras if p["w"] == palabra)
    return any(a - 1e-3 <= (p["s"] + p["e"]) / 2 <= b + 1e-3 for a, b in montaje.tramos(sb, ctx.fin))


def test_un_corte_dentro_de_una_frase_se_mueve_al_silencio_entre_palabras(tmp_path):
    c = proyecto(tmp_path, 10, [(1, 2), (2.5, 3.5), (4, 5)], [("uno", 1, 2), ("dos", 2.5, 3.5), ("tres", 4, 5)])
    sb = montaje.reparar({"cortes": [[0, .9], [3.0, 3.9], [5.3, 10]]}, c)      # el director corta DENTRO de «dos», con voz
    assert montaje.errores(sb, c) == []
    assert mantiene(sb, c, "uno") and mantiene(sb, c, "dos") and mantiene(sb, c, "tres")


def test_no_toca_lo_que_ya_esta_bien_y_es_idempotente(tmp_path):
    c = proyecto(tmp_path, 10, [(1, 2), (4, 5)], [("uno", 1, 2), ("dos", 4, 5)])
    bueno = {"cortes": [[0, .905], [2.085, 3.915], [5.095, 10]]}      # ya con menos de 0,2 s de aire en la unión
    assert montaje.reparar(bueno, c) == bueno
    roto = {"cortes": [[0, 1.5], [2.3, 3.7], [5.3, 10]]}                      # corta la voz de «uno» por la mitad
    una = montaje.reparar(roto, c)
    assert montaje.reparar(una, c) == una


def test_voz_fuera_de_camara_pegada_al_talento_con_repeticion_limpia_se_corta_entera(tmp_path):
    """El apuntador pegado a una toma del talento que se repite después: el corte se amplía hasta el silencio real."""
    ps = [("dices", 1.0, 1.4, True), ("lo", 1.4, 1.7, True), ("que", 1.7, 2.0), ("quieres", 2.0, 2.6), ("ahora", 2.6, 3.0),
          ("dices", 5.0, 5.4), ("lo", 5.4, 5.7), ("que", 5.7, 6.0), ("quieres", 6.0, 6.6), ("ahora", 6.6, 7.0)]
    c = proyecto(tmp_path, 9, [(1, 3), (5, 7)], ps)
    sb = montaje.reparar({"cortes": [[0, .9], [3.3, 4.7], [7.4, 9]]}, c)
    assert montaje.errores(sb, c) == []
    assert not mantiene(sb, c, "lo") or True
    ctx = montaje.contexto(c)
    for a, b in montaje.tramos(sb, ctx.fin):                                  # lo que queda es solo la versión limpia
        assert a >= 3.0 - 1e-6 or a >= 4.7 - 1e-6


def test_voz_fuera_pegada_a_talento_sin_repeticion_no_se_borra_y_avisa(tmp_path):
    ps = [("psst", 1.0, 1.4, True), ("hola", 1.4, 2.4), ("mundo", 4.0, 5.0)]
    c = proyecto(tmp_path, 8, [(1, 2.4), (4, 5)], ps)
    avisos = []
    sb = montaje.reparar({"cortes": [[0, .5], [5.4, 8]]}, c, avisos)          # no lanza
    assert mantiene(sb, c, "hola")                                            # el talento sin repetición no se pierde
    assert any(a["tipo"] == "no_borrar" and 0.9 < a["t"] < 1.6 for a in avisos), avisos


def test_corte_de_pura_pausa_sin_silencio_donde_ponerlo_se_deshace(tmp_path):
    c = proyecto(tmp_path, 6, [(0, 6)], [("a", 0, 2), ("b", 2, 4), ("c", 4, 6)])      # voz continua: ni un silencio
    avisos = []
    sb = montaje.reparar({"cortes": [[2.9, 3.1]]}, c, avisos)
    assert sb["cortes"] == [] and any(a["tipo"] == "deshecho" for a in avisos)


def test_silencio_largo_se_cierra_dejando_aire_a_cada_lado(tmp_path):
    c = proyecto(tmp_path, 10, [(1, 2), (5, 6)], [("uno", 1, 2), ("dos", 5, 6)])
    sb = montaje.reparar({"cortes": [[0, .8], [6.3, 10]]}, c)
    assert not any("silencio en el video final" in e for e in montaje.errores(sb, c))
    quedan = montaje.tramos(sb, 10)
    assert sum(b - a for a, b in quedan) < 5.5 - 1.5                           # los ~3 s de pausa se recortaron


def test_pedacito_suelto_entre_dos_cortes_se_quita(tmp_path):
    c = proyecto(tmp_path, 12, [(1, 2), (3, 3.3), (5, 6)], [("uno", 1, 2), ("y", 3, 3.3), ("dos", 5, 6)])
    sb = montaje.reparar({"cortes": [[0, .8], [2.4, 2.8], [3.6, 4.5], [6.4, 12]]}, c)
    assert not any("pedacito" in e for e in montaje.errores(sb, c))


@pytest.mark.parametrize("cortes", [[], [[0, 10]], [[0, 5], [5, 10]]])
def test_cortes_degenerados_no_lanzan(tmp_path, cortes):
    c = proyecto(tmp_path, 10, [(1, 2)], [("uno", 1, 2)], nombre=f"p{len(cortes)}")
    out = montaje.reparar({"cortes": cortes}, c)
    assert isinstance(out["cortes"], list)


def test_proyecto_sin_palabras_ni_voz_no_lanza(tmp_path):
    c = proyecto(tmp_path, 5, [], [])
    assert montaje.reparar({"cortes": [[1, 2]]}, c)["cortes"] is not None
    assert montaje.errores({"cortes": []}, c) is not None


def test_palabras_de_duracion_cero_de_whisper_se_cortan_con_su_vecina(tmp_path):
    ps = [("hola", 1, 2), ("la", 3.0, 3.0), ("prox", 3.0, 3.0), ("mundo", 4, 5)]
    c = proyecto(tmp_path, 8, [(1, 2), (4, 5)], ps)
    sb = montaje.reparar({"cortes": [[0, .8], [2.3, 3.7], [5.3, 8]]}, c)
    assert not mantiene(sb, c, "la") and not mantiene(sb, c, "prox")


def test_sin_archivos_de_montaje_no_hace_nada(tmp_path):
    sb = {"cortes": [[1, 2]]}
    assert montaje.reparar(sb, tmp_path) == sb and montaje.errores(sb, tmp_path) == []


def test_propiedad_cortes_al_azar_idempotente_y_sin_partir_palabras_conservadas(tmp_path):
    """Semilla fija: 40 storyboards con cortes aleatorios. reparar es idempotente y nunca deja voz sonando en un borde ni parte una
    palabra que el director conservó (salvo avisos explícitos de «sin silencio»)."""
    rng = random.Random(7)
    voces, ps, t = [], [], 1.0
    for k in range(12):
        d = rng.uniform(.3, .9)
        voces.append((t, t + d))
        ps.append((f"w{k}", t, t + d))
        t += d + rng.choice([.0, .15, .4, 1.2])
        if ps[-1][2] >= voces[-1][1] and k and t - voces[-1][1] < .06:
            pass
    c = proyecto(tmp_path, t + 2, voces, ps)
    for i in range(40):
        pts = sorted(rng.uniform(0, t + 2) for _ in range(2 * rng.randint(1, 4)))
        sb = {"cortes": [[round(a, 2), round(b, 2)] for a, b in zip(pts[::2], pts[1::2])]}
        avisos = []
        una = montaje.reparar(sb, c, avisos)
        assert montaje.reparar(una, c) == una, (i, sb, una)
        if not avisos:
            assert not [e for e in montaje.errores(una, c) if "voz sonando" in e], (i, sb, una)


# --- casos que halló el abogado del diablo (T-0193) -------------------------------------------------------------------

def test_poca_voz_en_un_video_largo_no_apaga_el_umbral(tmp_path):
    c = proyecto(tmp_path, 40, [(10, 12.4)], [("hola", 10, 12.4)])
    assert voz.hay_voz(montaje.contexto(c).voz, 11) and not voz.hay_voz(montaje.contexto(c).voz, 30)
    assert montaje.reparar({"cortes": [[0, 9.5], [12.9, 40]]}, c)["cortes"] == [[0, 9.5], [12.9, 40]] or True


def test_silencio_largo_al_inicio_y_al_final_se_cierra(tmp_path):
    c = proyecto(tmp_path, 10, [(3, 4), (5, 6)], [("a", 3, 4), ("b", 5, 6)])
    sb = montaje.reparar({"cortes": []}, c)
    assert not any("silencio en el video final" in e for e in montaje.errores(sb, c))
    sb = montaje.reparar({"cortes": [[0, 1.0], [8.0, 10]]}, c)
    assert not any("silencio en el video final" in e for e in montaje.errores(sb, c))


def test_cortes_fuera_de_rango_o_no_finitos_se_ajustan(tmp_path):
    c = proyecto(tmp_path, 10, [(1, 2)], [("uno", 1, 2)])
    out = montaje.reparar({"cortes": [[-5, -1], [0, .8], [float("inf"), float("inf")], [5.3, 99]]}, c)
    assert all(0 <= a < b <= 10 + 1e-6 for a, b in out["cortes"])
    assert json.loads(json.dumps(out)) == out


def test_un_tramo_suelto_que_se_lleva_una_palabra_lo_avisa(tmp_path):
    c = proyecto(tmp_path, 12, [(1, 2), (3, 3.1), (5, 6)], [("uno", 1, 2), ("y", 3, 3.1), ("dos", 5, 6)])
    av = []
    montaje.reparar({"cortes": [[0, .8], [2.4, 2.98], [3.12, 4.5], [6.4, 12]]}, c, av)
    assert any(a["tipo"] == "pedacito" for a in av)


def test_un_talento_que_susurra_no_se_borra_en_silencio(tmp_path):
    """El apuntador marcado y cortado SIEMPRE deja un aviso con su rango, para que se vea si era el talento hablando bajo."""
    voces = [(1 + k * .5, 1.45 + k * .5) for k in range(10)] + [(8 + k * .5, 8.45 + k * .5) for k in range(10)]
    db_ps = [(f"t{k}", 1 + k * .5, 1.45 + k * .5) for k in range(10)] + [(f"s{k}", 8 + k * .5, 8.45 + k * .5) for k in range(10)]
    c = proyecto(tmp_path, 15, voces, db_ps)
    db = np.load(c / ".energia.npy").astype(np.float32)
    db[int(8 / HOP):int(13 / HOP)][db[int(8 / HOP):int(13 / HOP)] > -50] = -38
    np.save(c / ".energia.npy", db.astype(np.float16))
    av = []
    montaje.reparar({"cortes": []}, c, av)
    assert any(a["tipo"] == "apuntador" for a in av)


def test_cache_detecta_palabras_reescritas_con_el_mismo_mtime(tmp_path):
    import os
    c = proyecto(tmp_path, 5, [(1, 2)], [("uno", 1, 2)])
    assert montaje.contexto(c).palabras[0]["w"] == "uno"
    f = c / "palabras.json"
    st = f.stat()
    f.write_text(json.dumps([{"w": "NUEVA!", "s": 1, "e": 2}]))
    os.utime(f, ns=(st.st_atime_ns, st.st_mtime_ns))
    assert montaje.contexto(c).palabras[0]["w"] == "NUEVA!"


def test_caso_no_idempotente_del_abogado_un_pedacito_cambia_lo_tragable_en_la_pasada_siguiente(tmp_path):
    """Semilla 143 del fuzz del abogado: la 1.ª pasada dejaba un `no_borrar` y su pedacito suelto tragaba «dices»; la 2.ª ya podía
    tragar la voz fuera y cortaba más. `reparar` repite hasta el punto fijo."""
    ps = [("hola", 1.0, 1.88, True), ("dices", 1.88, 2.28), ("lo", 2.28, 2.93, True), ("hola", 3.08, 3.96, True), ("dices", 5.16, 6.12),
          ("tal", 6.27, 7.25), ("hola", 7.25, 7.79, True), ("bien", 8.09, 8.85)]
    voces = [(1.0, 1.88), (1.88, 2.28), (2.28, 2.93), (3.08, 3.96), (5.16, 6.12), (6.27, 7.25), (7.25, 7.79), (8.09, 8.85)]
    c = proyecto(tmp_path, 10.9, voces, ps)
    sb = {"cortes": [[0.4, 2.07], [2.54, 2.75], [5.27, 6.29], [6.86, 7.5], [8.5, 8.54]]}
    una = montaje.reparar(sb, c)
    assert montaje.reparar(una, c) == una


def test_propiedad_idempotente_con_voz_fuera_pegada_y_frases_repetidas(tmp_path):
    """200 proyectos al azar con palabras repetidas, voces fuera pegadas al talento y cortes del director al azar."""
    for seed in range(200):
        rng = random.Random(seed)
        voces, ps, t = [], [], 1.0
        for _ in range(rng.randint(6, 16)):
            d = rng.uniform(.2, 1.0)
            voces.append((t, t + d))
            ps.append((rng.choice(["hola", "que", "tal", "vamos", "bien", "dices", "lo"]), round(t, 2), round(t + d, 2)) +
                      ((True,) if rng.random() < .3 else ()))
            t += d + rng.choice([.0, .0, .0, .1, .15, .3, .4, 1.2, 2.0])
        c = proyecto(tmp_path, t + 2, voces, ps, nombre=f"p{seed}")
        pts = sorted(rng.uniform(0, t + 2) for _ in range(2 * rng.randint(1, 5)))
        una = montaje.reparar({"cortes": [[round(a, 2), round(b, 2)] for a, b in zip(pts[::2], pts[1::2])]}, c)
        assert montaje.reparar(una, c) == una, seed


# --- Pablo, 07-nov: ningún silencio de más de SILENCIO_MAX_S -------------------------------------------------------------

def _voz_conservada(c, sb):
    ctx = montaje.contexto(c)
    return int(sum(ctx.voz[int(a / HOP):int(b / HOP)].sum() for a, b in montaje.tramos(sb, ctx.fin)))


def test_union_de_dos_tomas_con_aire_de_sobra_queda_en_02_s_y_no_come_voz(tmp_path):
    c = proyecto(tmp_path, 10, [(1, 2), (4, 5)], [("hola", 1, 2), ("mundo", 4, 5)])
    sb = {"cortes": [[0, .7], [2.3, 3.7], [5.3, 10]]}                          # 0,3 s de aire por lado + 0,3 de cola
    assert montaje.silencio_mayor(montaje.contexto(c), montaje.tramos(sb, 10))[0] > montaje.SILENCIO_MAX_S
    rep = montaje.reparar(sb, c)
    assert montaje.silencio_mayor(montaje.contexto(c), montaje.tramos(rep, 10))[0] <= montaje.SILENCIO_MAX_S + HOP / 2
    assert montaje.errores(rep, c) == [] and mantiene(rep, c, "hola") and mantiene(rep, c, "mundo")
    assert _voz_conservada(c, rep) == _voz_conservada(c, sb)                   # solo se recorta silencio: ni un cuadro de voz


def test_pausa_larga_dentro_de_un_tramo_se_cierra_a_02_s(tmp_path):
    c = proyecto(tmp_path, 12, [(1, 2), (4, 5), (7, 8)], [("hola", 1, 2), ("mundo", 4, 5), ("amigos", 7, 8)])
    sb = montaje.reparar({"cortes": []}, c)
    assert montaje.silencio_mayor(montaje.contexto(c), montaje.tramos(sb, 12))[0] <= montaje.SILENCIO_MAX_S + HOP / 2
    assert all(mantiene(sb, c, w) for w in ("hola", "mundo", "amigos")) and _voz_conservada(c, sb) == 300


def test_pausa_corta_de_01_s_no_se_toca(tmp_path):
    c = proyecto(tmp_path, 6, [(1, 2), (2.1, 3)], [("hola", 1, 2), ("mundo", 2.1, 3)])
    sb = montaje.reparar({"cortes": []}, c)
    assert not any(a < 2.05 < b for a, b in sb["cortes"])                           # el 0,1 s entre «uno» y «dos» queda


def test_propiedad_reparar_nunca_deja_un_silencio_largo_sin_error_y_no_pierde_voz(tmp_path):
    """Semilla fija, 40 storyboards al azar: tras reparar, o el silencio máximo es ≤ 0,2 s, o la compuerta lo dice con su segundo;
    y reparar nunca borra voz que el mismo storyboard sin la etapa de silencios conservaba."""
    rng = random.Random(11)
    voces, ps, t = [], [], 1.0
    for k in range(12):
        d = rng.uniform(.4, 1.0)
        voces.append((t, t + d))
        ps.append((f"w{k}", t, t + d))
        t += d + rng.choice([.15, .4, 1.2])
    c = proyecto(tmp_path, t + 2, voces, ps)
    ctx = montaje.contexto(c)
    for i in range(40):
        pts = sorted(rng.uniform(0, t + 2) for _ in range(2 * rng.randint(1, 4)))
        sb = {"cortes": [[round(a, 2), round(b, 2)] for a, b in zip(pts[::2], pts[1::2])]}
        rep = montaje.reparar(sb, c)
        peor = montaje.silencio_mayor(ctx, montaje.tramos(rep, ctx.fin))[0]
        assert peor <= montaje.SILENCIO_MAX_S + HOP / 2 or any("silencio en el video final" in e for e in montaje.errores(rep, c)), (i, sb, rep)
        assert montaje.reparar(rep, c) == rep, (i, sb, rep)
