"""Estilos Pro (docs/PLANO-ESTILOS-PRO.md, F2): el motor con una IA de prueba. Las pruebas NUNCA llaman a Claude real: la «película»
la entrega una función que genera un pelicula.mp4 corto con ffmpeg y un index.html de contrato Lemo con sus textos (C-0014)."""
import json
import os
import subprocess

import numpy as np
import pytest

from estudio import config, machote, mapa_texto, pro, texto_pelicula, textos_lemo, voz

requiere_lemo = pytest.mark.skipif(not (textos_lemo.LEMO / "core").is_dir(), reason="falta la biblioteca de Lemo en esta máquina")

DUR = 4.0
PALABRAS = [("hola", .4, .8), ("esto", .8, 1.1), ("es", 1.1, 1.3), ("una", 1.3, 1.6), ("prueba", 1.6, 2.2),
            ("de", 2.6, 2.8), ("estilo", 2.8, 3.2), ("pro", 3.2, 3.6)]


def ffmpeg(*args):
    exe, _ = config.ffmpeg()
    subprocess.run([exe, "-v", "error", "-y", *map(str, args)], check=True)


def papel(destino, dur=DUR, audio=None, volumen=2, bloque=None):
    """Video 1080×1920 de papel crema (con un bloque negro opcional) y audio: el de `audio` o un tono."""
    vf = "format=yuv420p" + (f",drawbox=x={bloque[0]}:y={bloque[1]}:w={bloque[2]}:h={bloque[3]}:color=black:t=fill" if bloque else "")
    entrada = ["-i", audio] if audio else ["-f", "lavfi", "-i", f"sine=f=220:d={dur}"]
    ffmpeg("-f", "lavfi", "-i", f"color=c=0xe8e0cc:s=1080x1920:r=30:d={dur}", *entrada, "-vf", vf, "-af", f"volume={volumen}", "-t", dur,
           "-c:v", "libx264", "-c:a", "aac", destino)


@pytest.fixture
def proyecto(tmp_path, monkeypatch):
    """Un proyecto con su machote ya hecho (cortes: ninguno) y el estilo «engraving» en una biblioteca de Lemo de mentira."""
    lemo = tmp_path / "lemo"
    (lemo / "styles" / "engraving").mkdir(parents=True)
    (lemo / "styles" / "engraving" / "STYLE.md").write_text("estilo de prueba")
    if (textos_lemo.LEMO / "core").is_dir():                       # el lector de textos usa el motor real de Lemo (solo lectura)
        (lemo / "core").symlink_to(textos_lemo.LEMO / "core")
    monkeypatch.setattr(pro, "LEMO", lemo)
    monkeypatch.setattr(texto_pelicula, "PESADO", tmp_path / "no-hay-cola.sh")
    c = tmp_path / "reel"
    c.mkdir()
    db = np.full(int(DUR / voz.HOP), -60.0, np.float32)
    db[int(.3 / voz.HOP):int(3.7 / voz.HOP)] = -20.0
    np.save(c / ".energia.npy", db.astype(np.float16))
    (c / "fuente.json").write_text(json.dumps({"video": "x.mp4", "cuadros": int(DUR * 30)}))
    (c / "palabras.json").write_text(json.dumps([{"w": w, "s": s, "e": e} for w, s, e in PALABRAS]))
    (c / "machote.json").write_text(json.dumps({"cortes": [], "duracion_s": DUR}))
    papel(c / machote.VIDEO, bloque=None)
    return c


# Lo que «escribe» la película falsa de Lemo (id, texto, desde, hasta): muestra «hola», «prueba» y «estilo» pero NO «pro»
TEXTOS_LEMO = [("t1", "¡Hola!", .3, 1.2), ("t2", "PRUEBA", 1.5, 2.6), ("t3", "estilo", 2.7, 3.7)]


def ia_que_entrega(llamadas, pagina, fallar_primero=False, textos=None):
    """Una IA falsa: «dirige» la película COMPLETA (papel + audio de la voz) con su index.html de contrato Lemo y deja plano.json.
    Con `fallar_primero`, la 1.ª sale con un negro."""
    def falsa(prompt, modelo, cwd, **k):
        llamadas.append({"prompt": prompt, "modelo": modelo, "cwd": cwd, **k})
        pagina(cwd, TEXTOS_LEMO if textos is None else textos, DUR)
        if fallar_primero and len(llamadas) == 1:
            ffmpeg("-f", "lavfi", "-i", f"color=c=black:s=1080x1920:r=30:d={DUR}", "-i", cwd / "voz.wav", "-t", DUR, "-pix_fmt", "yuv420p",
                   "-c:v", "libx264", "-c:a", "aac", cwd / "pelicula.mp4")
        else:
            papel(cwd / "pelicula.mp4", audio=cwd / "voz.wav", volumen=.4)        # bajito a propósito: el código lo nivela a -14 LUFS
        (cwd / "plano.json").write_text(json.dumps({"acento": "#c2432a", "tramos": [{"t0": 0, "t1": 2.4, "integracion": "grabado"},
                                                                                    {"t0": 2.4, "t1": DUR, "integracion": "máquina"}]}))
        return {"result": "LISTO"}
    return falsa


@requiere_lemo
def test_correr_deja_el_final_con_todas_las_palabras_lemo_mas_las_nuestras(proyecto, pagina_lemo):
    """C-0014: Lemo mostró «hola», «prueba» y «estilo» (y las vacías de sus frases); nosotros agregamos SOLO «pro». Cobertura total 100 %."""
    llamadas = []
    r = pro.correr(proyecto, "engraving", ia=ia_que_entrega(llamadas, pagina_lemo), avance=lambda m: None)
    enc = pro.encargo(proyecto, "engraving")
    assert r["ok"], r
    assert r["palabras"] == f"{len(PALABRAS)}/{len(PALABRAS)}" and (r["lemo"], r["agregadas"]) == (7, 1)
    inf = json.loads((enc / "texto-informe.json").read_text())
    assert [b["toks"] for b in inf["plan"]] == [["pro"]] and inf["plan"][0]["tam"] <= texto_pelicula.TAM_MAX_FALTA < texto_pelicula.TAM_MAX
    assert json.loads((enc / "textos-lemo.json").read_text())["mostradas_lemo"] == 7
    assert "Lemo puso 7 de 8 palabras, agregamos 1" in pro.estado(proyecto, "engraving")["linea"]
    assert json.loads((enc / "mapa-texto.json").read_text())["video"] == "pelicula.mp4"
    assert (enc / "final.mp4").exists() and (enc / "voz.wav").exists()
    est = pro.estado(proyecto, "engraving")
    assert est["fase"] == "listo" and est["pct"] == 100 and est["error"] is None and est["final"] == str(enc / "final.mp4")
    assert abs(pro.lufs(enc / "final.mp4") - pro.LUFS_META) <= pro.LUFS_TOL
    assert inf["mostradas"] == len(PALABRAS)
    # una sola llamada, a Opus, con las reglas y los datos del encargo ya puestos en el prompt
    assert len(llamadas) == 1 and llamadas[0]["modelo"] == "opus" and llamadas[0]["cwd"] == enc
    p = llamadas[0]["prompt"]
    assert "engraving" in p and "[[" not in p and "hola esto es una prueba de estilo pro" in p and "x 60–1020" in p
    assert "pelicula.mp4" in p and "TEXTS" in p and "?limpio=1`" not in p.replace("**No hay modo limpio** ni `?limpio=1`", "")


def test_encargo_viejo_con_limpio_sigue_como_antes(proyecto):
    """Compatibilidad: con `limpio.mp4` y sin `pelicula.mp4` no se llama a la IA y el editor de textos pone TODAS las palabras."""
    enc = pro.encargo(proyecto, "engraving")
    enc.mkdir()
    pro._voz(proyecto, enc)
    papel(enc / "limpio.mp4", audio=enc / "voz.wav", volumen=.4)
    (enc / "plano.json").write_text(json.dumps({"acento": "#c2432a", "tramos": [{"t0": 0, "t1": DUR, "integracion": "grabado"}]}))
    r = pro.correr(proyecto, "engraving", ia=lambda *a, **k: pytest.fail("no debía llamar a la IA"), avance=lambda m: None)
    assert r["ok"] and r["palabras"] == f"{len(PALABRAS)}/{len(PALABRAS)}" and r["agregadas"] == len(PALABRAS) and r["lemo"] == 0
    assert not (enc / "textos-lemo.json").exists() and (enc / "final.mp4").exists()


@requiere_lemo
def test_pro_textos_reaprovecha_una_pelicula_ya_hecha(proyecto, pagina_lemo):
    """`estudio pro-textos`: solo los pasos 2–4 sobre un encargo rendido, sin llamar a Opus."""
    enc = pro.encargo(proyecto, "engraving")
    enc.mkdir()
    pro._voz(proyecto, enc)
    papel(enc / "pelicula.mp4", audio=enc / "voz.wav", volumen=.4)
    pagina_lemo(enc, TEXTOS_LEMO, DUR)
    r = pro.pro_textos(enc, avance=lambda m: None)
    assert r["ok"] and (r["lemo"], r["agregadas"]) == (7, 1) and (enc / "final.mp4").exists()
    with pytest.raises(FileNotFoundError):
        pro.pro_textos(proyecto / "no-hay")


def test_palabras_en_el_tiempo_del_corte(proyecto):
    """La voz cortada y sus palabras salen de los cortes del machote: lo quitado no cuenta y lo que queda se corre."""
    (proyecto / "machote.json").write_text(json.dumps({"cortes": [[2.2, 2.5]], "duracion_s": DUR - .3}))
    enc = pro.encargo(proyecto, "engraving")
    enc.mkdir()
    pro._voz(proyecto, enc)
    ps = json.loads((enc / "palabras.json").read_text())
    assert [p["w"] for p in ps] == [w for w, _, _ in PALABRAS]
    assert ps[5]["s"] == pytest.approx(2.6 - .3, abs=.01)           # «de» estaba en 2,6 s: tras el corte de 0,3 s llega en 2,3


@requiere_lemo
def test_reintenta_una_vez_con_el_informe(proyecto, pagina_lemo):
    llamadas = []
    r = pro.correr(proyecto, "engraving", ia=ia_que_entrega(llamadas, pagina_lemo, fallar_primero=True), avance=lambda m: None)
    assert r["ok"], r
    assert len(llamadas) == 2
    assert "REINTENTO" in llamadas[1]["prompt"] and "cuadros negros" in llamadas[1]["prompt"]


def test_si_vuelve_a_fallar_queda_el_error(proyecto):
    llamadas = []

    def ciega(prompt, modelo, cwd, **k):
        llamadas.append(prompt)
        return {"result": "no hice nada"}
    r = pro.correr(proyecto, "engraving", ia=ciega, avance=lambda m: None)
    est = pro.estado(proyecto, "engraving")
    assert not r["ok"] and len(llamadas) == 2
    assert est["fase"] == "error" and "no entregó pelicula.mp4" in est["error"] and not (pro.encargo(proyecto, "engraving") / "final.mp4").exists()


def test_un_encargo_a_la_vez_por_proyecto_y_estado_de_un_proceso_muerto(proyecto, monkeypatch):
    (proyecto / "pro-otro").mkdir()
    (proyecto / "pro-otro" / "estado.json").write_text(json.dumps({"fase": "pelicula", "pct": 10, "pid": os.getpid()}))
    with pytest.raises(pro.EncargoOcupado):
        pro.lanzar(proyecto, "engraving")
    with pytest.raises(pro.EncargoOcupado):
        pro.correr(proyecto, "engraving", ia=lambda *a, **k: pytest.fail("no debía llamar a la IA"))
    (proyecto / "pro-otro" / "estado.json").write_text(json.dumps({"fase": "pelicula", "pct": 10, "pid": 2 ** 22 + 12345}))
    est = pro.estado(proyecto, "otro")
    assert est["fase"] == "error" and "terminó sin avisar" in est["error"]
    lanzados = []
    monkeypatch.setattr(pro.subprocess, "Popen", lambda cmd, **k: lanzados.append(cmd))
    enc = pro.lanzar(proyecto, "engraving")
    assert enc == proyecto.resolve() / "pro-engraving" and lanzados[0][-3:] == ["pro", str(proyecto.resolve()), "engraving"]
    assert pro.estado(proyecto, "engraving")["fase"] == "cola"


def test_estilo_desconocido(proyecto):
    with pytest.raises(ValueError):
        pro.correr(proyecto, "no-existe", ia=lambda *a, **k: pytest.fail("no debía llamar a la IA"))


def test_mapa_de_texto_sobre_un_video_sintetico(tmp_path):
    bloque = (300, 700, 480, 400)              # x, y, ancho, alto: un bloque negro en el centro
    papel(tmp_path / "limpio.mp4", dur=2.0, bloque=bloque)
    (tmp_path / "palabras.json").write_text(json.dumps([{"w": "uno", "s": .1, "e": .5}, {"w": "dos", "s": .5, "e": .9},
                                                        {"w": "tres", "s": 1.4, "e": 1.8}]))
    mapa = mapa_texto.escribir(tmp_path)
    assert json.loads((tmp_path / "mapa-texto.json").read_text()) == mapa
    assert [(t["t0"], t["t1"]) for t in mapa["tramos"]] == [(0.0, pytest.approx(1.15)), (pytest.approx(1.15), 2.0)]   # parte por la pausa
    zx0, zy0, zx1, zy1 = mapa_texto.ZONA
    for t in mapa["tramos"]:
        lb = t["libre"]
        assert lb and zx0 <= lb["x0"] < lb["x1"] <= zx1 and zy0 <= lb["y0"] < lb["y1"] <= zy1
        assert lb["x1"] <= bloque[0] or lb["x0"] >= bloque[0] + bloque[2] or lb["y1"] <= bloque[1] or lb["y0"] >= bloque[1] + bloque[3]
        assert t["tinta"] == mapa_texto.TINTA_OSCURA and t["fondo_luma"] > 200 and t["integracion"] == "grabado"
    # lo que lee el editor de textos con este mapa: todas las palabras caben
    assert texto_pelicula.informe(texto_pelicula.planear(tmp_path))["ok"]


def test_el_plano_del_editor_1_manda_sobre_las_pausas():
    ps = [{"w": "a", "s": .1, "e": .4}, {"w": "b", "s": .5, "e": .9}]
    plano = {"tramos": [{"t0": 0, "t1": 1.0, "integracion": "rotulador"}]}
    assert mapa_texto.tramos_de(ps, 1.0, plano) == [(0.0, 1.0, "a b", "rotulador")]


def test_voz_en_off_sin_video_ni_machote(tmp_path):
    """Pablo 09-nov: el guion del comercial (solo narración) en un Estilo Pro: la voz se usa tal cual, con sus palabras y el diccionario."""
    import subprocess
    subprocess.run([config.ffmpeg()[0], "-v", "error", "-y", "-f", "lavfi", "-i", "sine=f=220:d=2", str(tmp_path / pro.VOZ_EN_OFF)], check=True)
    (tmp_path / "palabras.json").write_text(json.dumps([{"w": "Soltá", "s": 0.1, "e": 0.5}, {"w": "Cloud", "s": 0.6, "e": 1.0}]))
    enc = tmp_path / "pro-x"
    enc.mkdir()
    dur = pro._voz(tmp_path, enc)
    assert abs(dur - 2.0) < .05 and (enc / "voz.wav").exists()
    assert [p["w"] for p in json.loads((enc / "palabras.json").read_text())] == ["Soltá", "Claude"]
