"""Lemo como proveedor de apoyos del reel hablado (docs/PLANO-LEMO-APOYOS.md, F1). Las pruebas NUNCA llaman a Claude: la «IA» es
una función que deja en `lemo/<id>/` lo que Lemo entregaría (película sin audio, index.html de contrato Lemo, plano.json)."""
import json
import subprocess

import pytest

from estudio import config, lemo_apoyos, pro, texto_pelicula, textos_lemo

requiere_lemo = pytest.mark.skipif(not (textos_lemo.LEMO / "core").is_dir(), reason="falta la biblioteca de Lemo en esta máquina")
PALABRAS = [("hola", .2, .6), ("esto", 1.1, 1.4), ("es", 1.4, 1.6), ("una", 1.6, 1.9), ("prueba", 1.9, 2.5), ("de", 3.1, 3.3), ("lemo", 3.3, 3.8)]
CARA = (400, 500, 700, 900)


def video(destino, dur, fondo="0xe8e0cc", caja=None):
    """1080×1920 sin audio, de un color, con una caja blanca opcional (x, y, w, h)."""
    vf = "format=yuv420p" + (f",drawbox=x={caja[0]}:y={caja[1]}:w={caja[2]}:h={caja[3]}:color=white:t=fill" if caja else "")
    subprocess.run([config.ffmpeg()[0], "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c={fondo}:s=1080x1920:r=30:d={dur}", "-vf", vf,
                    "-t", str(dur), "-c:v", "libx264", str(destino)], check=True)


@pytest.fixture
def reel(tmp_path, monkeypatch):
    """Un proyecto ya dirigido: la persona, un apoyo completo «a» (1–3 s, persona oculta) y uno sobre la persona «b» (3–4 s)."""
    lemo = tmp_path / "lemo-lib"
    (lemo / "styles" / "engraving").mkdir(parents=True)
    (lemo / "styles" / "engraving" / "STYLE.md").write_text("estilo de prueba")
    if (textos_lemo.LEMO / "core").is_dir():
        (lemo / "core").symlink_to(textos_lemo.LEMO / "core")
    monkeypatch.setattr(pro, "LEMO", lemo)
    monkeypatch.setattr(texto_pelicula, "PESADO", tmp_path / "no-hay-cola.sh")
    c = tmp_path / "reel"
    c.mkdir()
    (c / "palabras.json").write_text(json.dumps([{"w": w, "s": s, "e": e} for w, s, e in PALABRAS]))
    con_aire = [float(x) for x in CARA]
    (c / "persona.json").write_text(json.dumps({"version": 2, "paso": 15, "cuadros": 120, "cajas": [[con_aire, [200., 500., 900., 1920.]]] * 9}))
    (c / "storyboard.json").write_text(json.dumps({
        "estilo": {"acento": "#FFE800"}, "cortes": [],
        "escenas": [{"t0": 0, "persona": {"modo": "completa"}}, {"t0": 1.0, "persona": {"modo": "oculta"}}, {"t0": 3.0, "persona": {"modo": "completa"}}],
        "elementos": [{"id": "a", "tipo": "clip", "src": "arte/a.mp4", "cubrir": True, "t0": 1.0, "t1": 3.0},
                      {"id": "b", "tipo": "clip", "src": "arte/b.mp4", "cubrir": True, "fusion": "pantalla", "t0": 3.0, "t1": 4.0}],
        "subtitulos": {"y": 1455, "ocultar": [[0, .5]]}}))
    (c / "arte.json").write_text(json.dumps([{"id": "a", "clip": True, "idea": "una prueba"}, {"id": "b", "clip": True, "idea": "de lemo"},
                                             {"id": "foto", "prompt": "una foto"}]))
    return c


def lemo_falso(llamadas, pagina, b_vacio=False, a_negro_primero=False):
    def falsa(prompt, modelo, cwd, **k):
        llamadas.append({"prompt": prompt, "modelo": modelo, "cwd": cwd, **k})
        for id_, dur in (("a", 2.0), ("b", 1.0)):
            if f'"id": "{id_}"' not in prompt:
                continue
            d = cwd / id_
            d.mkdir(exist_ok=True)
            pagina(d, [("t1", "ESTO", 0, .5)] if id_ == "a" else [], dur)   # en «a» Lemo muestra «esto» (y las vacías de su frase), no «prueba»
            if id_ == "a":
                video(d / "pelicula.mp4", dur, fondo="black" if a_negro_primero and len(llamadas) == 1 else "0xe8e0cc")
            else:
                video(d / "pelicula.mp4", dur, **({"fondo": "black", "caja": (100, 1000, 300, 300)} if b_vacio else {"fondo": "0x3a5a8a"}))
            (d / "plano.json").write_text(json.dumps({"acento": "#c2432a", "tramos": [{"t0": 0, "t1": dur, "integracion": "grabado"}]}))
        return {"result": "LISTO"}
    return falsa


def test_pedidos_salen_del_storyboard_con_su_clase_palabras_y_cara(reel):
    a, b = lemo_apoyos.pedidos(reel)
    assert (a["id"], a["clase"], a["dur"], a["cara"]) == ("a", "completo", 2.0, list(CARA))   # la cara va siempre
    assert [(p["w"], p["s"]) for p in a["palabras"]] == [("esto", .1), ("es", .4), ("una", .6), ("prueba", .9)]   # en segundos desde t0
    assert (b["id"], b["clase"], b["dur"], b["cara"]) == ("b", "completo", 1.0, list(CARA))   # 12-nov: nunca «persona» (texto sobre negro)
    assert [p["w"] for p in b["palabras"]] == ["de", "lemo"]


def test_las_palabras_que_el_machote_corto_no_se_le_dan_a_lemo(reel):
    sb = json.loads((reel / "storyboard.json").read_text())
    sb["cortes"] = [[1.05, 1.65]]
    (reel / "storyboard.json").write_text(json.dumps(sb))
    assert [p["w"] for p in lemo_apoyos.pedidos(reel)[0]["palabras"]] == ["una", "prueba"]


@requiere_lemo
def test_hacer_deja_los_apoyos_completa_textos_y_oculta_el_subtitulo(reel, pagina_lemo):
    llamadas, avisos = [], []
    r = lemo_apoyos.hacer(reel, "engraving", ia=lemo_falso(llamadas, pagina_lemo), avance=avisos.append)
    assert r == {"pedidos": 2, "hechos": ["a", "b"], "fallas": {}}
    assert (reel / "arte" / "a.mp4").exists() and (reel / "arte" / "b.mp4").exists()
    sb = json.loads((reel / "storyboard.json").read_text())
    # se ocultan los bloques del subtítulo que ya están todos en pantalla: «a» y también «b» (Lemo no puso texto y lo completamos en su película)
    assert sb["subtitulos"]["ocultar"] == [[0, .5], [1.1, 1.9], [1.9, 3.1], [3.1, 4.4]]
    assert json.loads((reel / "lemo" / "cobertura.json").read_text())["sin_mostrar"] == []
    assert sb["estilo"]["acento"] == "#c2432a"                        # el texto nuestro toma el acento de Lemo
    inf = json.loads((reel / "lemo" / "a" / "texto-informe.json").read_text())
    assert inf["mostradas"] == inf["palabras"] == 4 and inf["agregadas"] >= 1      # Lemo + lo nuestro = todas
    assert any("agregamos" in m for m in avisos)
    # un encargo de Opus por tramo (12-nov: «que no tenga que releer todo»), en la carpeta de trabajo, solo con el contrato técnico
    assert len(llamadas) == 2 and all(x["modelo"] == "opus" and x["cwd"] == reel / "lemo" for x in llamadas)
    assert '"id": "a"' in llamadas[0]["prompt"] and '"id": "b"' not in llamadas[0]["prompt"] and '"id": "b"' in llamadas[1]["prompt"]
    p = llamadas[0]["prompt"]
    assert "[[" not in p and "engraving" in p and '"clase": "completo"' in p and '"clase": "persona"' not in p and str(list(CARA)) in p
    assert "foto" not in [x["id"] for x in lemo_apoyos.pedidos(reel)]            # las imágenes no son de Lemo


def test_un_tramo_de_texto_sobre_negro_no_entra(reel, pagina_lemo):
    """12-nov (video-3217, seg 11): «hay varias escenas que están de fondo negro, las quiero con diseño de Lemo»."""
    llamadas = []
    r = lemo_apoyos.hacer(reel, "engraving", ia=lemo_falso(llamadas, pagina_lemo, b_vacio=True), avance=lambda m: None)
    assert "b" in r["fallas"] and "fondo vacío" in " ".join(r["fallas"]["b"]) and "b" not in r["hechos"]
    assert not (reel / "arte" / "b.mp4").exists()
    assert len(llamadas) == 3 and "REINTENTO" in llamadas[2]["prompt"] and '"id": "a"' not in llamadas[2]["prompt"]   # se corrige una vez, solo lo malo


def test_un_fondo_oscuro_pintado_si_pasa_y_uno_vacio_no(reel):
    d = reel / "lemo" / "b"
    d.mkdir(parents=True)
    (d / "index.html").write_text("window.TEXTS=()=>[]")
    (d / "plano.json").write_text("{}")
    video(d / "pelicula.mp4", 1.0, fondo="0x1c2a48")                 # noche azul oscura (como la puerta de impasto): es diseño
    assert lemo_apoyos.revisar(reel, lemo_apoyos.pedidos(reel)[1]) == []
    video(d / "pelicula.mp4", 1.0, fondo="black", caja=(100, 1000, 300, 300))
    assert any("fondo vacío" in x for x in lemo_apoyos.revisar(reel, lemo_apoyos.pedidos(reel)[1]))


def test_apoyo_que_no_dura_lo_pedido_o_no_llego_falla(reel):
    ped = lemo_apoyos.pedidos(reel)[0]
    assert "no entregó" in lemo_apoyos.revisar(reel, ped)[0]
    d = reel / "lemo" / "a"
    d.mkdir(parents=True)
    video(d / "pelicula.mp4", 1.2)
    assert any("dura 1.20 s" in x for x in lemo_apoyos.revisar(reel, ped))


def test_sin_pedidos_de_clip_no_se_llama_a_nadie(reel):
    (reel / "arte.json").write_text(json.dumps([{"id": "foto", "prompt": "una foto"}]))
    assert lemo_apoyos.hacer(reel, "engraving", ia=lambda *a, **k: pytest.fail("no debía llamar")) == {"pedidos": 0, "hechos": [], "fallas": {}}


# ---------- F3: Lemo hace de todo (PLANO-LEMO-APOYOS §0): elige la clase o nada, y nosotros completamos en todo el reel ----------

def entrega(d, dur, plano, pagina, fondo="0xe8e0cc", caja=None, textos=()):
    """Lo que Lemo deja en un tramo: película, index.html de contrato y su plano.json."""
    d.mkdir(parents=True, exist_ok=True)
    pagina(d, list(textos), dur)
    video(d / "pelicula.mp4", dur, fondo=fondo, caja=caja)
    (d / "plano.json").write_text(json.dumps(plano))


def test_lemo_elige_la_clase_y_lo_que_no_hizo_deja_a_la_persona(reel, pagina_lemo):
    """Pablo, 12-nov: «Lemus puede hacer de todo, pero pues no es una camisa de fuerza». El director propuso «a» completo y «b» sobre
    la persona; Lemo no hace «a» y hace «b» de pantalla completa. Las escenas quedan como él entregó y nunca hay hueco."""
    llamadas = []

    def falsa(prompt, modelo, cwd, **k):
        llamadas.append(prompt)
        (cwd / "a" / "plano.json").write_text(json.dumps({"clase": "nada"}))
        entrega(cwd / "b", 1.0, {"clase": "completo", "acento": "#204060", "tramos": [{"t0": 0, "t1": 1.0, "integracion": "rotulador"}]}, pagina_lemo)
        return {"result": "LISTO"}
    r = lemo_apoyos.hacer(reel, "engraving", ia=falsa, avance=lambda m: None)
    assert r == {"pedidos": 2, "hechos": ["b"], "fallas": {}} and len(llamadas) == 1   # «nada» no es una falla: no hay reintento
    sb = json.loads((reel / "storyboard.json").read_text())
    modo = {e["t0"]: e["persona"]["modo"] for e in sb["escenas"]}
    assert modo == {0: "completa", 1.0: "completa", 3.0: "oculta"}      # «a» vuelve a la persona; «b» pasa a pantalla completa
    b = next(e for e in sb["elementos"] if e["id"] == "b")
    assert "fusion" not in b and not (reel / "arte" / "a.mp4").exists() and (reel / "arte" / "b.mp4").exists()
    assert sb["estilo"]["acento"] == "#204060" and sb["estilo"]["fuente"] == "Covered By Your Grace"   # su letra en nuestro texto
    assert json.loads((reel / "lemo" / "cobertura.json").read_text())["sin_mostrar"] == []


def test_persona_en_parte_las_escenas_y_no_toca_lo_que_ya_esta():
    sb = {"escenas": [{"t0": 0, "persona": {"modo": "completa"}, "intencion": "toma"}]}
    lemo_apoyos._persona_en(sb, 1.0, 3.0, "oculta", fin=10)
    assert [(e["t0"], e["persona"]["modo"]) for e in sb["escenas"]] == [(0, "completa"), (1.0, "oculta"), (3.0, "completa")]
    antes = json.dumps(sb)
    lemo_apoyos._persona_en(sb, 1.0, 3.0, "oculta", fin=10)
    assert json.dumps(sb) == antes
    lemo_apoyos._persona_en(sb, 1.0, 3.0, "completa", fin=10)
    assert all(e["persona"]["modo"] == "completa" for e in sb["escenas"])
    sin = {"escenas": []}
    lemo_apoyos._persona_en(sin, 2.0, 4.0, "oculta", fin=10)                       # sin escenas: la persona vuelve al terminar
    assert [(e["t0"], e["persona"]["modo"]) for e in sin["escenas"]] == [(2.0, "oculta"), (4.0, "completa")]


def test_una_entrega_de_otro_pedido_o_un_arte_viejo_no_entran(reel, pagina_lemo):
    vieja = reel / "lemo" / "a"
    entrega(vieja, 2.0, {"acento": "#000000"}, pagina_lemo)
    (vieja / "pedido.json").write_text(json.dumps({"estilo": "watercolor", "t0": 1.0, "t1": 3.0}))
    (reel / "arte").mkdir()
    (reel / "arte" / "b.mp4").write_bytes(b"de otro video")
    llamadas = []
    r = lemo_apoyos.hacer(reel, "engraving", ia=lambda p, *a, **k: llamadas.append(p), avance=lambda m: None)
    assert r["hechos"] == [] and not (vieja / "pelicula.mp4").exists() and not (reel / "arte" / "b.mp4").exists()
    assert '"id": "a"' in llamadas[0] and '"id": "b"' in llamadas[1]          # lo viejo se pidió de nuevo, no se reusó
    assert json.loads((vieja / "pedido.json").read_text()) == {"estilo": "engraving", "t0": 1.0, "t1": 3.0}


def test_el_subtitulo_se_oculta_por_bloque_y_lo_del_director_dentro_de_un_tramo_no_cuenta(reel):
    """Abogado del diablo 5: dentro de un tramo de Lemo el subtítulo lo decide la medida; un bloque se oculta solo si TODAS sus
    palabras ya están en pantalla."""
    sb = json.loads((reel / "storyboard.json").read_text())
    sb["subtitulos"]["ocultar"] = [[0, .5], [1.0, 3.0]]          # el director ocultó dentro del tramo de «a»
    (reel / "storyboard.json").write_text(json.dumps(sb))
    ped = lemo_apoyos.pedidos(reel)
    a = {**ped[0]}
    cob = lemo_apoyos._al_storyboard(reel, ped, [a], {1, 2, 3})      # Lemo mostró «esto es una», no «prueba»
    sub = json.loads((reel / "storyboard.json").read_text())["subtitulos"]
    assert sub["ocultar"] == [[0, .5], [1.1, 1.9]]                 # el bloque de «prueba» sigue a la vista
    assert cob["sin_mostrar"] == [] and cob["en_pelicula_de_lemo"] == 3


def test_texto_de_lemo_fuera_de_la_zona_segura_no_cuenta():
    assert textos_lemo.en_zona({"text": "x", "x0": 100, "y0": 300, "x1": 900, "y1": 420})
    assert not textos_lemo.en_zona({"text": "x", "x0": 100, "y0": 1600, "x1": 900, "y1": 1700})   # debajo: lo tapa Instagram
    assert textos_lemo.en_zona({"text": "x"})                                                    # sin caja medida, cuenta
