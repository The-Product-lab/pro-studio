"""Machote (Pablo, 07-nov): crudo colorizado + solo los cortes, liviano. Las pruebas no gastan IA ni renderizan nada pesado:
el banco de casos reales decide sus cortes en código, la IA se simula y el render se prueba con un clip sintético de 6 s."""
import json
import shutil
import subprocess

import numpy as np
import pytest

from conftest import CASOS
from estudio import config, ingesta, machote, montaje, repeticiones, voz

HOP = voz.HOP
# Errores que el machote NUNCA puede dejar (los que quedan como aviso son voces pegadas a palabras del talento sin toma limpia)
# Fuera de esta lista, a propósito (son de la compuerta de montaje.py, que la sesión de correcciones 07-nov está ajustando):
# · «termina N s después»: falso positivo cuando Whisper estira una palabra sobre la pausa que reparar mismo cerró;
# · «silencio en el video final»: lo que queda va pegado a charla/voz baja que la IA quita en la corrida real, o a un pedacito
#   que montaje no parte. Lo propio del machote sí se mide: ningún tramo del medio sin palabras.
GRAVES = machote.GRAVES
# Casos del banco donde el código solo deja un problema grave SIN borde seguro y lo resuelve la IA (no puede crecer):
# julian3d-c8869 seg 42: «más bien, ya» (orden de grabación) pegado sin pausa a «vería cloud esto cloud este otro» (toma mala).
GRAVES_SIN_IA_MAX = {"julian3d-c8869": 1}


def sintetico(tmp_path, dur, voces, palabras, nombre="p"):
    c = tmp_path / nombre
    c.mkdir()
    db = np.full(int(dur / HOP), -60.0, np.float32)
    for a, b in voces:
        db[int(a / HOP):int(b / HOP)] = -20.0
    np.save(c / ".energia.npy", db.astype(np.float16))
    (c / "fuente.json").write_text(json.dumps({"video": "x.mp4", "cuadros": int(dur * 30)}))
    (c / "palabras.json").write_text(json.dumps([{"w": w, "s": s, "e": e} for w, s, e in palabras]))
    return c


def dos_tomas(tmp_path):
    """Una frase dicha dos veces (queda la última) y una frase única al final."""
    ps = [("hola", 1.0, 1.4), ("esto", 1.4, 1.8), ("es", 1.8, 2.0), ("una", 2.0, 2.3), ("prueba", 2.3, 2.9),
          ("hola", 5.0, 5.4), ("esto", 5.4, 5.8), ("es", 5.8, 6.0), ("una", 6.0, 6.3), ("prueba", 6.3, 6.9),
          ("gracias", 9.0, 9.6), ("por", 9.6, 9.9), ("ver", 9.9, 10.3), ("esto", 10.3, 10.7)]
    return sintetico(tmp_path, 12, [(1, 2.9), (5, 6.9), (9, 10.7)], ps)


def libres_en(c, mj):
    ctx = montaje.contexto(c)
    quedan = montaje.tramos({"cortes": mj["cortes"]}, ctx.fin)
    return [p["w"] for p in ctx.palabras if not p.get("fuera") and any(a - 1e-3 <= (p["s"] + p["e"]) / 2 <= b + 1e-3 for a, b in quedan)]


def test_queda_la_ultima_toma_y_el_inicio_va_limpio(tmp_path):
    c = dos_tomas(tmp_path)
    mj = machote.decidir(c, con_ia=False, avance=lambda m: None)
    ctx = montaje.contexto(c)
    quedan = montaje.tramos({"cortes": mj["cortes"]}, ctx.fin)
    assert 4.7 <= quedan[0][0] <= 5.0 - machote.AIRE_INICIO + .05     # la primera toma ya no está y arranca pegado a la primera palabra
    assert repeticiones.faltas(ctx.palabras, mj["cortes"]) == []
    assert mj["duracion_s"] < mj["fuente_s"] and mj["quitado_s"]["tomas_repetidas"] > 1.5
    assert json.loads((c / "machote.json").read_text())["cortes"] == mj["cortes"]


def test_decidir_es_idempotente_y_no_llama_a_la_ia_sin_permiso(tmp_path, monkeypatch):
    monkeypatch.setattr(machote.ia, "llamar", lambda *a, **k: pytest.fail("no debía llamar a la IA"))
    c = dos_tomas(tmp_path)
    a = machote.decidir(c, con_ia=False, avance=lambda m: None)
    b = machote.decidir(c, con_ia=False, avance=lambda m: None)
    assert a["cortes"] == b["cortes"] and a["ia"]["llamadas"] == 0


def test_la_ia_solo_senala_frases_y_el_codigo_pone_los_bordes(tmp_path, monkeypatch):
    c = dos_tomas(tmp_path)
    pedidos = []

    def falsa(prompt, modelo, cwd, **k):
        pedidos.append((prompt, modelo, k.get("herramientas")))
        return {"result": 'listo {"quitar": [{"id": 0, "motivo": "charla"}, {"id": 99, "motivo": "no existe"}, {"id": "x"}]}'}
    monkeypatch.setattr(machote.ia, "llamar", falsa)
    mj = machote.decidir(c, con_ia=True, avance=lambda m: None)
    # 1.ª llamada: la decisión de cortes; 2.ª: la lectura final del guion que quedó (07-nov)
    assert 1 <= len(pedidos) <= 2 and all(p[1] == "opus" and p[2] == "Read" for p in pedidos)
    assert "escenas" not in pedidos[0][0].lower()                    # solo cortes: ni escenas ni elementos
    assert [q["texto"] for q in mj["ia"]["quito"]] == ["hola esto es una prueba"]   # el id inventado y el mal escrito se ignoran
    assert libres_en(c, mj)[0] == "gracias"
    assert mj["quitado_s"]["ia_fuera_de_guion"] > 1.5


def test_respuesta_rota_o_absurda_de_la_ia_no_tira_el_machote(tmp_path, monkeypatch):
    c = dos_tomas(tmp_path)
    monkeypatch.setattr(machote.ia, "llamar", lambda *a, **k: {"result": "no sé"})
    sin = machote.decidir(c, con_ia=True, avance=lambda m: None)
    assert sin["ia"]["quito"] == [] and montaje.errores({"cortes": sin["cortes"]}, c) == []
    todo = '{"quitar": [' + ",".join(f'{{"id": {i}}}' for i in range(2)) + "]}"
    monkeypatch.setattr(machote.ia, "llamar", lambda *a, **k: {"result": todo})
    assert machote.decidir(c, con_ia=True, avance=lambda m: None)["ia"]["quito"] == []   # quitar todo = respuesta descartada


def test_tramo_sin_palabras_entre_dos_cortes_se_quita(tmp_path):
    """Swiss C8872: entre dos cortes quedaba 2,1 s de puro aire que reparar no partía (dejaba un pedacito): ahora se corta entero."""
    ps = [("hoy", 1.0, 1.5), ("vamos", 1.5, 2.0), ("bien", 2.0, 2.6), ("mañana", 6.0, 6.5), ("mucho", 6.5, 7.0), ("mejor", 7.0, 7.6)]
    c = sintetico(tmp_path, 9, [(1, 2.6), (6, 7.6)], ps)
    ctx = montaje.contexto(c)
    assert machote._sin_palabras(ctx, [[2.7, 3.0], [5.0, 5.9]]) == [[3.0, 5.0]]
    assert machote._sin_palabras(ctx, [[2.7, 3.0]]) == []                 # los bordes del video los maneja _ajustar_bordes
    mj = machote.decidir(c, con_ia=False, avance=lambda m: None)
    assert libres_en(c, mj) == ["hoy", "vamos", "bien", "mañana", "mucho", "mejor"] and mj["duracion_s"] < 5


def test_la_ia_ve_la_charla_pegada_y_lo_que_el_codigo_quito(tmp_path, monkeypatch):
    """La charla del equipo que sigue en el video entra sin marca (la IA decide por el contenido); lo que el código quitó por sonar
    bajo entra marcado [FUERA] para que la IA pueda devolverlo si es guion."""
    ps = [("hoy", 1.0, 1.4), ("les", 1.4, 1.7), ("cuento", 1.7, 2.2), ("algo", 2.2, 2.6),
          ("el", 4.0, 4.2), ("primer", 4.2, 4.6), ("paso", 4.6, 5.0), ("importa", 5.0, 5.6)]
    c = sintetico(tmp_path, 7, [(1, 2.6), (4, 5.6)], ps)
    ctx = montaje.contexto(c)
    for p in ctx.palabras[4:]:
        p.update(fuera=True, motivo="apuntador")
    f = machote._frases_para_ia(ctx, [], [[3.8, 5.8]])
    assert [(x["texto"], x["cortada"]) for x in f] == [("hoy les cuento algo", False), ("el primer paso importa", True)]
    p = machote._prompt_ia(f, 60)
    assert p.index("EN EL VIDEO") < p.index("0 · 1.0-2.6 s · hoy") < p.index("QUITADAS POR EL CÓDIGO") < p.index("1 · 4.0-5.6 s · el primer")
    montaje._CACHE.clear()


def test_la_ia_devuelve_guion_que_el_detector_tomo_por_apuntador(tmp_path, monkeypatch):
    """Prestiggio C8873 / Julián 3D C8869: el detector tomaba guion del talento por apuntador y el código lo cortaba antes de que la
    IA lo viera. Con `restaurar`, vuelve; sin IA, sigue fuera."""
    montaje._CACHE.clear()
    monkeypatch.setattr(montaje.voz, "apuntador", lambda out, *a, **k: [k for k, p in enumerate(out) if p["w"] in ("primer", "paso", "importa.")])
    ps = [("hoy", 1.0, 1.4), ("les", 1.4, 1.7), ("cuento", 1.7, 2.2), ("algo.", 2.2, 2.6),
          ("primer", 4.0, 4.6), ("paso", 4.6, 5.0), ("importa.", 5.0, 5.6),
          ("gracias", 7.0, 7.5), ("por", 7.5, 7.8), ("ver", 7.8, 8.2), ("esto.", 8.2, 8.6)]
    c = sintetico(tmp_path, 10, [(1, 2.6), (4, 5.6), (7, 8.6)], ps)
    sin = machote.decidir(c, con_ia=False, avance=lambda m: None)
    assert "primer" not in _todas_en(c, sin), (sin["cortes"], _todas_en(c, sin))
    monkeypatch.setattr(machote.ia, "llamar", lambda *a, **k: {"result": '{"quitar": [], "restaurar": [{"id": 1, "motivo": "es el paso uno"}]}'})
    con = machote.decidir(c, con_ia=True, avance=lambda m: None)
    assert _todas_en(c, con) == ["hoy", "les", "cuento", "algo.", "primer", "paso", "importa.", "gracias", "por", "ver", "esto."]
    assert con["ia"]["restauro"][0]["texto"] == "primer paso importa."
    montaje._CACHE.clear()


def _todas_en(c, mj):
    quedan = montaje.tramos({"cortes": mj["cortes"]}, mj["fuente_s"])
    return [p["w"] for p in json.loads((c / "palabras.json").read_text()) if any(a - 1e-3 <= (p["s"] + p["e"]) / 2 <= b + 1e-3 for a, b in quedan)]


def test_una_frase_larga_sin_puntos_se_parte_en_sus_pausas():
    ps = [{"w": f"p{k}", "s": k * .5 + (1.0 if k >= 10 else 0) + (.6 if k >= 20 else 0), "e": k * .5 + .45 + (1.0 if k >= 10 else 0) + (.6 if k >= 20 else 0)}
          for k in range(30)]
    trozos = machote._partir(ps, 0, 30)
    assert (0, 10) in trozos and all(ps[b - 1]["e"] - ps[a]["s"] <= machote.FRASE_MAX_S for a, b in trozos)
    assert [x for a, b in trozos for x in range(a, b)] == list(range(30))     # no se pierde ni se repite ninguna palabra


def test_lo_que_la_ia_quita_no_cuenta_como_primera_palabra(tmp_path):
    """Cine C8867: la IA quitó un «¡Hasta la próxima!» fantasma al arranque que reparar no pudo cortar: el inicio limpio salta a
    la primera palabra que sí queda."""
    ps = [("hasta", 1.0, 1.3), ("luego", 1.3, 1.6), ("estás", 3.0, 3.4), ("editando", 3.4, 4.0), ("videos", 4.0, 4.6)]
    c = sintetico(tmp_path, 6, [(1, 1.6), (3, 4.6)], ps)
    ctx = montaje.contexto(c)
    sin_ia = montaje.tramos({"cortes": machote._ajustar_bordes(ctx, [])}, ctx.fin)
    con_ia = montaje.tramos({"cortes": machote._ajustar_bordes(ctx, [], [[1.0, 1.6]])}, ctx.fin)
    assert sin_ia[0][0] < 1.0 and 2.7 <= con_ia[0][0] < 3.0


def test_lo_que_la_ia_lee_y_deja_no_lo_borra_reparar_como_apuntador():
    """Julián 3D C8869: el detector marcaba como apuntador los tres pasos del guion; la IA los dejó y reparar los borraba igual."""
    class C:
        palabras = [{"w": "uno", "s": 1.0, "e": 1.4, "fuera": True, "motivo": "apuntador"},
                    {"w": "pasos", "s": 1.4, "e": 1.9, "fuera": True, "motivo": "apuntador"},
                    {"w": "va", "s": 3.0, "e": 3.3, "fuera": True, "motivo": "claqueta"},
                    {"w": "perdón", "s": 5.0, "e": 5.5, "fuera": True, "motivo": "apuntador"}]
    frases = [{"id": 0, "t0": 1.0, "t1": 1.9}, {"id": 1, "t0": 3.0, "t1": 3.3}, {"id": 2, "t0": 5.0, "t1": 5.5}]
    assert machote._la_ia_lo_dejo(C, frases, quitar={2}, restaurar=set()) == 2
    assert [p.get("fuera") for p in C.palabras] == [False, False, True, True]   # la claqueta y lo que la IA quitó siguen fuera


def test_sobre_el_tope_la_ia_recibe_la_orden_de_recortar(tmp_path):
    f = [{"id": 0, "t0": 0, "t1": 1, "texto": "x"}]
    assert "máximo es 110" in machote._prompt_ia(f, 130)
    assert "máximo es 110" not in machote._prompt_ia(f, 60)


@pytest.mark.parametrize("caso", CASOS)
def test_banco_de_casos_reales(caso, banco):
    """Los videos del lote del 07-nov: en código, el machote no deja versiones repetidas ni bordes con voz ni silencios largos,
    y quita al menos lo que el director ya había quitado como repetición."""
    c = banco(caso)
    mj = machote.decidir(c, con_ia=False, avance=lambda m: None)
    graves = [e for e in mj["residuales"] if any(g in e for g in GRAVES)]
    # lo que el código solo no resuelve no pasa callado: queda en `necesita_ia` y en el flujo real lo decide Opus (Pablo 08-nov)
    assert graves == mj["necesita_ia"]
    assert len(graves) <= GRAVES_SIN_IA_MAX.get(caso, 0), graves
    ctx = montaje.contexto(c)
    libres = [p for p in ctx.palabras if not p.get("fuera")]
    assert repeticiones.faltas(libres, mj["cortes"]) == []
    assert 0 < mj["duracion_s"] < mj["fuente_s"]
    assert machote._sin_palabras(ctx, mj["cortes"]) == []            # ningún tramo de puro aire entre dos cortes
    assert machote.decidir(c, con_ia=False, avance=lambda m: None)["cortes"] == mj["cortes"]   # idempotente


def test_imponer_suma_los_cortes_del_machote_sin_quitar_los_del_director(tmp_path):
    c = dos_tomas(tmp_path)
    mj = machote.decidir(c, con_ia=False, avance=lambda m: None)
    (c / "storyboard.json").write_text(json.dumps({"cortes": [[11.0, 12.0]], "escenas": []}))
    assert machote.imponer(c) is True
    cortes = json.loads((c / "storyboard.json").read_text())["cortes"]
    cubre = lambda x: any(a <= x[0] + 1e-6 and x[1] <= b + 1e-6 for a, b in cortes)  # noqa: E731
    assert cubre([11.0, 12.0]) and all(cubre(x) for x in mj["cortes"])
    assert machote.imponer(c) is False                                 # idempotente
    assert machote.imponer(tmp_path / "no-existe") is False


def test_nota_para_director_solo_con_machote(tmp_path):
    c = dos_tomas(tmp_path)
    assert machote.nota_para_director(c) == ""
    machote.decidir(c, con_ia=False, avance=lambda m: None)
    assert "TAL CUAL" in machote.nota_para_director(c)


def test_derivar_lleva_los_cortes_del_machote_al_proyecto_nuevo(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PROYECTOS", tmp_path)
    base = dos_tomas(tmp_path)
    base.rename(tmp_path / "base")
    machote.decidir(tmp_path / "base", con_ia=False, avance=lambda m: None)
    nuevo = ingesta.derivar("base", "base-estilo")
    assert json.loads((nuevo / "machote.json").read_text())["cortes"] == machote.cargar(tmp_path / "base")["cortes"]
    (tmp_path / "base" / "machote.json").write_text(json.dumps({"cortes": [[0, 1]]}))   # el machote se rehízo: el derivado lo toma
    assert json.loads((ingesta.derivar("base", "base-estilo") / "machote.json").read_text())["cortes"] == [[0, 1]]


# --- render (clip sintético de 6 s: rápido) ---------------------------------------------------------------------------------

@pytest.fixture
def clip(tmp_path):
    try:
        ffmpeg, ffprobe = config.ffmpeg()
    except Exception:   # noqa: BLE001 — sin ffmpeg en esta máquina: se salta, nunca falla por eso
        pytest.skip("sin ffmpeg")
    v = tmp_path / "crudo.mp4"
    subprocess.run([ffmpeg, "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=270x480:r=30:d=6", "-f", "lavfi",
                    "-i", "sine=f=440:d=6", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(v)], check=True)
    c = tmp_path / "proy"
    c.mkdir()
    (c / "fuente.json").write_text(json.dumps({"video": str(v), "cuadros": 180, "hdr": False}))
    (c / "palabras.json").write_text("[]")
    (c / "machote.json").write_text(json.dumps({"cortes": [[1.0, 2.0], [4.0, 4.5]], "color": {"ajustes": {"contraste": .5}},
                                                "firma": machote.firma(c), "fuente_s": 6.0}))
    return c, ffprobe


def _dur(ffprobe, f, flujo):
    return float(subprocess.run([ffprobe, "-v", "error", "-select_streams", flujo, "-show_entries", "stream=duration", "-of", "csv=p=0", str(f)],
                                capture_output=True, text=True, check=True).stdout.strip())


def test_render_solo_cortes_con_color_liviano_y_sin_intermedios(clip):
    c, ffprobe = clip
    salida = machote.render(c, ancho=180, crf=30, avance=lambda m: None)
    assert salida == c / "machote.mp4"
    assert abs(_dur(ffprobe, salida, "v:0") - 4.5) < .1 and abs(_dur(ffprobe, salida, "a:0") - 4.5) < .1   # 6 s − 1 s − 0,5 s, video y audio parejos
    info = json.loads(subprocess.run([ffprobe, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "json", str(salida)],
                                     capture_output=True, text=True).stdout)["streams"][0]
    assert (info["width"], info["height"]) == (180, 320)
    assert not (c / "machote.tmp.mp4").exists()                      # nada a medias
    assert machote.cargar(c)["render"]["bytes"] == salida.stat().st_size
    assert list(c.glob("color-*.cube"))                              # el color del proyecto se aplicó (LUT horneada)


def test_preparar_no_rehace_el_video_si_nada_cambio_y_si_cambia_el_color(clip):
    c, _ = clip
    machote.preparar(c, ancho=180, crf=30, avance=lambda m: None)
    t0 = (c / "machote.mp4").stat().st_mtime_ns
    machote.preparar(c, ancho=180, crf=30, avance=lambda m: None)
    assert (c / "machote.mp4").stat().st_mtime_ns == t0              # mismo color, mismos cortes: no se vuelve a exportar
    (c / "preferencias.json").write_text(json.dumps({"estilo": {"color": {"ajustes": {"contraste": -.5}}}}))
    machote.preparar(c, ancho=180, crf=30, avance=lambda m: None)
    assert (c / "machote.mp4").stat().st_mtime_ns != t0              # otro color: solo el video, los cortes siguen
    assert machote.cargar(c)["cortes"] == [[1.0, 2.0], [4.0, 4.5]]


def test_render_sin_machote_json_avisa(tmp_path):
    (tmp_path / "x").mkdir()
    with pytest.raises(FileNotFoundError):
        machote.render(tmp_path / "x")


def test_corridas_usan_la_cuadricula_del_motor():
    assert machote._corridas(180, [[1.0, 2.0], [4.0, 4.5]]) == [(0, 30), (60, 120), (135, 180)]


# --- los estilos parten del machote -----------------------------------------------------------------------------------------

def test_el_director_recibe_el_machote_y_sus_cortes_entran_siempre(tmp_path, monkeypatch):
    from estudio import director
    c = dos_tomas(tmp_path)
    mj = machote.decidir(c, con_ia=False, avance=lambda m: None)
    prompts = []

    def director_falso(prompt, modelo, cwd, **k):
        prompts.append(prompt)
        (cwd / "storyboard.json").write_text(json.dumps({"cortes": [], "escenas": []}))   # el director «olvidó» copiar los cortes
        return {}
    monkeypatch.setattr(director, "contexto", lambda *a: None)
    monkeypatch.setattr(director, "_validar", lambda *a, **k: None)
    monkeypatch.setattr(director, "_fijar_estilo", lambda *a: None)
    monkeypatch.setattr(director.ia, "llamar", director_falso)
    director.dirigir(c, "vox", False, lambda m: None)
    assert "YA HAY MACHOTE" in prompts[0]
    assert json.loads((c / "storyboard.json").read_text())["cortes"] == mj["cortes"]


def test_editar_deja_el_machote_hecho_antes_del_director(tmp_path, monkeypatch):
    from estudio import cli, director, motor
    monkeypatch.setattr(config, "PROYECTOS", tmp_path)
    base = dos_tomas(tmp_path)
    base.rename(tmp_path / "base")
    llamadas = []
    monkeypatch.setattr(machote, "preparar", lambda carpeta, **k: llamadas.append((carpeta.name, k.get("con_video"))))
    monkeypatch.setattr(director, "dirigir", lambda *a, **k: (tmp_path / "base-x" / "costos.jsonl").write_text(""))
    monkeypatch.setattr(motor, "render", lambda *a, **k: tmp_path / "final.mp4")
    cli.editar(None, "vox", False, 0, nombre="base-x", desde="base")
    assert llamadas == [("base-x", False)]            # decide los cortes (sin renderizar el video liviano) antes de que el director diseñe


def test_el_video_no_arranca_con_restos_de_otra_toma_pegados(tmp_path):
    """Un pedazo de voz sin palabra (cola de una claqueta que el corte dejó pegada) antes de la primera palabra no queda."""
    ps = [("hola", 3.0, 3.4), ("esto", 3.4, 3.9), ("es", 3.9, 4.1), ("claro", 4.1, 4.6)]
    c = sintetico(tmp_path, 8, [(.5, .9), (3.0, 4.6)], ps)
    mj = machote.decidir(c, con_ia=False, avance=lambda m: None)
    quedan = montaje.tramos({"cortes": mj["cortes"]}, 8.0)
    assert 2.7 <= quedan[0][0] <= 3.0 and quedan[-1][1] <= 4.6 + machote.AIRE_FINAL + .05


def test_lo_grave_que_el_codigo_no_resuelve_va_a_la_ia_senalado(banco, monkeypatch):
    """Pablo 08-nov: «cuando pase eso, metés IA full». El tramo de Julián 3D que el código no puede cortar llega a Opus como pista,
    con su segundo en el video cortado, y lo que la IA quita se aplica."""
    c = banco("julian3d-c8869")
    llamadas = []

    def falso(carpeta, ctx, cortes, pistas=()):
        llamadas.append(list(pistas))
        if not pistas:
            return [], []
        quedan = montaje.tramos({"cortes": cortes}, ctx.fin)
        a, b = next((a, b) for a, b in quedan if a <= 42.6 <= b)
        return [(a, b, "vería cloud esto cloud este otro", "resto de otra toma pegado a la orden")], []

    monkeypatch.setattr(machote, "_frases_para_ia", lambda *a, **k: [])
    monkeypatch.setattr(machote, "_leer_guion_final", falso)
    mj = machote.decidir(c, con_ia=True, avance=lambda m: None)
    con_pista = [p for p in llamadas if p]
    assert con_pista and any("voz sonando" in x["detalle"] for x in con_pista[0])
    assert not [e for e in mj["residuales"] if any(g in e for g in GRAVES)]
    assert mj["necesita_ia"] == []
