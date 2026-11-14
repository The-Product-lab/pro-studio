"""Repartir una grabación en videos (docs/PLANO-LOTE.md). Pablo, 13-nov: «yo te puedo entregar 30 archivos de video y tú miras cuántos
videos finales salen… tienes que revisar a través de las transcripciones qué idea se cierra, qué guion se cierra».
Banco: una grabación de 7 archivos que da 3 videos (una idea en dos archivos; otra dicha tres veces, queda la última; un archivo con
dos ideas; uno sin voz; nombres que no ordenan). El agrupador es un `claude` falso: responde bien, mal o no responde."""
import json
import subprocess
from pathlib import Path

import pytest

from estudio import config, errores, reparto, unir

A = "si tu video no arranca fuerte nadie lo termina de ver"
A2 = "por eso el primer segundo decide todo guarda este consejo"
B_MALA = "el error mas comun al grabar es mirar la pantalla y no"
B = "el error mas comun al grabar es mirar la pantalla y no el lente"
B_CIERRE = "mira siempre el lente y vas a conectar mucho mas"
C = "tres ideas para tu proximo reel una pregunta un dato y una historia"


def _palabras(texto: str, desde: float = .3) -> list:
    """Cada palabra dura 0,3 s y la siguiente arranca 0,1 s después."""
    return [{"w": w, "s": round(desde + i * .4, 2), "e": round(desde + i * .4 + .3, 2), "p": .99} for i, w in enumerate(texto.split())]


def _archivo(carpeta: Path, nombre: str, seg: float, audio: bool = True) -> Path:
    ffmpeg, _ = config.ffmpeg()
    sonido = ["-f", "lavfi", "-i", f"sine=frequency=300:duration={seg}"] if audio else []
    subprocess.run([ffmpeg, "-v", "error", "-y", "-f", "lavfi", "-i", f"testsrc=size=160x284:rate=30:d={seg}", *sonido, "-c:v", "libx264",
                    "-preset", "ultrafast", "-pix_fmt", "yuv420p", *(["-c:a", "aac", "-shortest"] if audio else ["-an"]), str(carpeta / nombre)],
                   check=True)
    return carpeta / nombre


@pytest.fixture
def grabacion(tmp_path, monkeypatch):
    """La tanda del banco, ya «transcrita» (las palabras se escriben a mano: sin Whisper). → (tanda, {clave: id de archivo})."""
    monkeypatch.setattr(config, "PROYECTOS", tmp_path)
    monkeypatch.delenv("ESTUDIO_SIN_IA", raising=False)
    subidas = tmp_path / "_subidas"
    subidas.mkdir()
    dos_ideas = _palabras(C) + _palabras(B_CIERRE, desde=7.0)          # termina la idea C en 5,4 s; pausa; desde 7,0 s el cierre de B
    casos = [("gancho", "toma 1.mp4", _palabras(A)), ("cierre", "toma 2.mp4", _palabras(A2)), ("b1", "toma 3.mp4", _palabras(B)),
             ("b2", "toma 4.mp4", _palabras(B_MALA)), ("b3", "toma 5.mp4", _palabras(B)), ("dos", "toma 10.mp4", dos_ideas),
             ("mudo", "ambiente.mp4", [])]
    rutas = [_archivo(subidas, nombre, (ps[-1]["e"] + .5) if ps else 2.0, audio=bool(ps)) for _, nombre, ps in casos]
    t = reparto.crear([str(r) for r in reversed(rutas)])               # llegan en desorden
    ids = {clave: next(a["id"] for a in t["archivos"] if a["nombre"] == nombre) for clave, nombre, _ in casos}
    for clave, _, ps in casos:
        if ps:
            (reparto.carpeta(t["id"]) / f"{ids[clave]}.palabras.json").write_text(json.dumps(ps))
    return reparto.transcribir(t["id"], lambda m: None), ids


def _claude(tmp_path, monkeypatch, *respuestas) -> Path:
    """Un `claude` falso que contesta esas respuestas en orden (la última se repite) y cuenta las llamadas."""
    cuenta = tmp_path / "llamadas"
    cuenta.write_text("0")
    guion = tmp_path / "claude_falso.py"
    guion.write_text("import json,pathlib\n"
                     f"c=pathlib.Path({str(cuenta)!r});n=int(c.read_text());c.write_text(str(n+1))\n"
                     f"r={list(respuestas)!r}\nprint(json.dumps(r[min(n,len(r)-1)]))\n")
    monkeypatch.setenv("ESTUDIO_CLAUDE_BIN", str(guion))
    return cuenta


def _buena(ids: dict) -> dict:
    return {"videos": [{"titulo": "Arranca fuerte", "idea": "el primer segundo decide", "tramos": [{"archivo": ids["gancho"]}, {"archivo": ids["cierre"]}]},
                       {"titulo": "Mira el lente", "idea": "mirar el lente conecta",
                        "tramos": [{"archivo": ids["b3"]}, {"archivo": ids["dos"], "desde": 6.2, "hasta": 11.0}]},
                       {"titulo": "Tres ideas", "idea": "tres formatos de reel", "tramos": [{"archivo": ids["dos"], "desde": 0, "hasta": 6.2}]}],
            "sobran": [{"archivo": ids["b1"], "motivo": "toma repetida"}, {"archivo": ids["b2"], "motivo": "toma fallada"}]}


def _todo_ubicado(t: dict) -> None:
    """Lo que nunca debe pasar: perder algo sin decirlo. Cada archivo, y cada palabra dicha, está en un video o en sobran, una sola vez."""
    p = t["propuesta"]
    piezas = [x for v in p["videos"] for x in v["tramos"]] + p["sobran"]
    for a in t["archivos"]:
        mias = [x for x in piezas if x["archivo"] == a["id"]]
        assert mias, f"{a['nombre']} no quedó en ningún lado"
        for w in reparto.palabras_de(t, a["id"]):
            medio = (w["s"] + w["e"]) / 2
            assert sum(x["desde"] <= medio <= x["hasta"] for x in mias) == 1, (a["nombre"], w["w"])


# ---------- fase 1 y 2: la tanda y la transcripción en serie ----------
def test_tanda_nueva_anota_todos_los_archivos_en_orden_natural(grabacion):
    t, _ = grabacion
    assert [a["nombre"] for a in t["archivos"]] == ["ambiente.mp4", "toma 1.mp4", "toma 2.mp4", "toma 3.mp4", "toma 4.mp4", "toma 5.mp4", "toma 10.mp4"]
    assert json.loads((reparto.carpeta(t["id"]) / "tanda.json").read_text())["id"] == t["id"]   # vive en disco: se retoma tras cerrar la app
    with pytest.raises(errores.Aviso, match="Ya no encuentro «no-esta.mp4»"):
        reparto.crear([str(config.PROYECTOS / "_subidas" / "no-esta.mp4")])


def test_transcribe_en_serie_guarda_cada_una_y_marca_lo_que_no_tiene_voz(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PROYECTOS", tmp_path)
    (tmp_path / "_subidas").mkdir()
    rutas = [_archivo(tmp_path / "_subidas", f"clip {n}.mp4", 1.0) for n in (1, 2, 3)]
    rutas.append(_archivo(tmp_path / "_subidas", "sin sonido.mp4", 1.0, audio=False))
    (tmp_path / "_subidas" / "roto.mp4").write_bytes(b"no es un video")
    t = reparto.crear([str(r) for r in rutas] + [str(tmp_path / "_subidas" / "roto.mp4")])
    corriendo, maximo, orden = [], [0], []

    def whisper_falso(video, destino):
        corriendo.append(video.name)
        maximo[0] = max(maximo[0], len(corriendo))
        orden.append(video.name)
        ps = [] if "3" in video.name else _palabras("hola esto es una prueba")
        destino.write_text(json.dumps(ps))
        corriendo.pop()
        return ps
    monkeypatch.setattr(reparto.ingesta, "transcribir", whisper_falso)
    avisos = []
    t = reparto.transcribir(t["id"], avisos.append)
    assert maximo[0] == 1 and orden == ["clip 1.mp4", "clip 2.mp4", "clip 3.mp4"]            # de a uno, y solo los que tienen sonido
    assert {a["nombre"]: a["estado"] for a in t["archivos"]} == {"clip 1.mp4": "transcrito", "clip 2.mp4": "transcrito", "clip 3.mp4": "sin_voz",
                                                              "sin sonido.mp4": "sin_voz", "roto.mp4": "error"}
    assert any("transcribiendo 1 de 5" in x for x in avisos)
    reparto.transcribir(t["id"], lambda m: None)
    assert orden == ["clip 1.mp4", "clip 2.mp4", "clip 3.mp4"]                                # lo ya transcrito no se repite
    t = reparto.agrupar(t["id"], lambda m: None)
    motivos = {x["archivo"]: x["motivo"] for x in t["propuesta"]["sobran"]}
    roto = next(a["id"] for a in t["archivos"] if a["nombre"] == "roto.mp4")
    assert "no se pudo leer" in motivos[roto] and len(motivos) >= 3                           # el roto y los mudos no se pierden: se dicen


# ---------- fase 3: agrupar ----------
def test_banco_7_archivos_dan_3_videos_con_la_ultima_toma_y_un_archivo_partido(grabacion, tmp_path, monkeypatch):
    t, ids = grabacion
    llamadas = _claude(tmp_path, monkeypatch, {"is_error": False, "result": "Aquí va:\n" + json.dumps(_buena(ids))})
    t = reparto.agrupar(t["id"], lambda m: None)
    p = t["propuesta"]
    assert llamadas.read_text() == "1" and p["origen"] == "opus" and t["estado"] == "propuesta"
    assert [v["titulo"] for v in p["videos"]] == ["Arranca fuerte", "Mira el lente", "Tres ideas"] and [v["id"] for v in p["videos"]] == ["v1", "v2", "v3"]
    assert [x["archivo"] for x in p["videos"][0]["tramos"]] == [ids["gancho"], ids["cierre"]]   # una idea grabada en dos archivos
    corte = p["videos"][2]["tramos"][0]["hasta"]
    assert p["videos"][1]["tramos"][1]["desde"] == corte and 5.4 < corte < 7.0                # el archivo con dos ideas, partido en la pausa
    sobran = {x["archivo"]: x["motivo"] for x in p["sobran"]}
    assert sobran[ids["b1"]] == "toma repetida" and sobran[ids["b2"]] == "toma fallada" and sobran[ids["mudo"]] == reparto.SIN_VOZ
    assert ids["b3"] not in sobran                                                            # de la idea repetida queda la ÚLTIMA toma
    assert t["avisos"] == []
    _todo_ubicado(t)
    hoja = (reparto.carpeta(t["id"]) / "transcripciones.md").read_text()
    assert "toma 10.mp4" in hoja and "ambiente.mp4" not in hoja and "[0.30–5.40]" in hoja     # lo que leyó el agrupador: frases con su tiempo


def test_revisar_no_deja_perder_ni_repetir_ni_inventar_aunque_el_agrupador_se_equivoque(grabacion, tmp_path, monkeypatch):
    t, ids = grabacion
    mala = {"videos": [{"titulo": "", "tramos": [{"archivo": ids["gancho"]}, {"archivo": ids["cierre"]}, {"archivo": "a99"}]},
                       {"titulo": "Repite", "tramos": [{"archivo": ids["gancho"]}, {"archivo": ids["b3"], "desde": -4, "hasta": 999}]},   # repite el gancho; tiempos fuera
                       {"titulo": "Parte mal", "tramos": [{"archivo": ids["dos"], "desde": 0, "hasta": 4.45}]},                          # 4,45 s cae dentro de una palabra
                       {"titulo": "Vacío", "tramos": []}],
            "sobran": [{"archivo": ids["b1"], "motivo": "toma repetida"}]}                                                             # olvida b2, el mudo y medio «dos»
    _claude(tmp_path, monkeypatch, {"is_error": False, "result": json.dumps(mala)})
    t = reparto.agrupar(t["id"], lambda m: None)
    p = t["propuesta"]
    _todo_ubicado(t)                                                                           # nada se perdió, nada quedó dos veces
    assert [v["titulo"] for v in p["videos"]] == ["Video 1", "Repite", "Parte mal"]            # sin el vacío; el sin título recibe nombre
    assert [x["archivo"] for x in p["videos"][1]["tramos"]] == [ids["b3"]]                     # el gancho repetido se quedó en el primero
    dur_b3 = next(a["duracion"] for a in t["archivos"] if a["id"] == ids["b3"])
    assert p["videos"][1]["tramos"][0] == {"archivo": ids["b3"], "desde": 0.0, "hasta": dur_b3}   # recortado a lo que dura el archivo
    corte = p["videos"][2]["tramos"][0]["hasta"]
    palabras = reparto.palabras_de(t, ids["dos"])
    assert not any(w["s"] < corte < w["e"] for w in palabras)                                  # el corte se corrió fuera de la palabra
    sin_ubicar = {x["archivo"] for x in p["sobran"] if x["motivo"] == reparto.SIN_UBICAR}
    assert sin_ubicar == {ids["b2"], ids["dos"]}
    texto = " ".join(t["avisos"])
    assert "a99" in texto and "ya estaba en otro video" in texto and "toma 4.mp4" in texto and "toma 10.mp4" in texto   # todo dicho a la vista


def test_dos_tomas_iguales_en_lo_que_quedo_se_avisan(grabacion, tmp_path, monkeypatch):
    t, ids = grabacion
    repetidas = _buena(ids)
    repetidas["videos"].append({"titulo": "Otra vez", "tramos": [{"archivo": ids["b1"]}]})   # la primera toma de B también quedó
    repetidas["sobran"] = [{"archivo": ids["b2"], "motivo": "toma fallada"}]
    _claude(tmp_path, monkeypatch, {"is_error": False, "result": json.dumps(repetidas)})
    t = reparto.agrupar(t["id"], lambda m: None)
    assert any("dicen casi lo mismo" in a and "toma 3.mp4" in a and "toma 5.mp4" in a for a in t["avisos"])


@pytest.mark.parametrize("respuestas,llamadas,dice", [
    ([{"is_error": False, "result": "no sé"}], "2", "no respondió claro"),                                  # un reintento y a código
    ([{"is_error": True, "result": "Not logged in · Please run /login"}], "1", "Claude no tiene la sesión"),
])
def test_agrupa_por_codigo_si_opus_no_puede_y_lo_dice(grabacion, tmp_path, monkeypatch, respuestas, llamadas, dice):
    t, ids = grabacion
    cuenta = _claude(tmp_path, monkeypatch, *respuestas)
    t = reparto.agrupar(t["id"], lambda m: None)
    p = t["propuesta"]
    assert cuenta.read_text() == llamadas and p["origen"] == "codigo"
    assert dice in t["avisos"][0] and "Júntalos tú" in t["avisos"][0]
    assert len(p["videos"]) == 4                                                              # cada archivo con voz, menos las tomas repetidas
    sobran = {x["archivo"]: x["motivo"] for x in p["sobran"]}
    assert "toma 5.mp4" in sobran[ids["b1"]] and "toma 5.mp4" in sobran[ids["b2"]] and ids["b3"] not in sobran   # «última toma siempre», también sin IA
    _todo_ubicado(t)


def test_sin_ia_no_llama_a_nadie(grabacion, tmp_path, monkeypatch):
    t, _ = grabacion
    cuenta = _claude(tmp_path, monkeypatch, {"is_error": False, "result": "{}"})
    monkeypatch.setenv("ESTUDIO_SIN_IA", "1")
    t = reparto.agrupar(t["id"], lambda m: None)
    assert cuenta.read_text() == "0" and t["propuesta"]["origen"] == "codigo" and t["avisos"][0] == reparto.SIN_IA


def test_un_solo_archivo_es_un_video_sin_gastar(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PROYECTOS", tmp_path)
    (tmp_path / "_subidas").mkdir()
    cuenta = _claude(tmp_path, monkeypatch, {"is_error": False, "result": "{}"})
    t = reparto.crear([str(_archivo(tmp_path / "_subidas", "solo.mp4", 3.0))])
    (reparto.carpeta(t["id"]) / "a1.palabras.json").write_text(json.dumps(_palabras("uno dos tres cuatro")))
    t = reparto.analizar(t["id"], lambda m: None)
    assert cuenta.read_text() == "0" and len(t["propuesta"]["videos"]) == 1 and t["avisos"] == []


# ---------- fase 4: lo que mueve la persona ----------
def test_persona_mueve_junta_y_rescata_y_la_compuerta_lo_cuida(grabacion, tmp_path, monkeypatch):
    t, ids = grabacion
    _claude(tmp_path, monkeypatch, {"is_error": False, "result": json.dumps(_buena(ids))})
    t = reparto.agrupar(t["id"], lambda m: None)
    p = t["propuesta"]
    # junta el video 3 con el 1, rescata la toma fallada al video 2 y se le olvida mandar «sobran»
    movida = {"videos": [{"titulo": "Arranca fuerte", "tramos": p["videos"][0]["tramos"] + p["videos"][2]["tramos"]},
                         {"titulo": "Mira el lente", "tramos": [{"archivo": ids["b2"]}] + p["videos"][1]["tramos"]}], "sobran": []}
    t = reparto.proponer(t["id"], movida)
    p = t["propuesta"]
    assert p["origen"] == "persona" and len(p["videos"]) == 2 and len(p["videos"][0]["tramos"]) == 3
    assert p["videos"][1]["tramos"][0]["archivo"] == ids["b2"]
    _todo_ubicado(t)                                                                           # b1 y el mudo volvieron solos a «sobran»
    assert any("toma 3.mp4" in a for a in t["avisos"])
    with pytest.raises(errores.Aviso, match="No quedó ningún video"):
        reparto.proponer(t["id"], {"videos": [], "sobran": []})
    assert len(reparto.leer(t["id"])["propuesta"]["videos"]) == 2                              # lo rechazado no pisa lo que había


# ---------- fase 5: armar y preparar, uno tras otro ----------
def test_armar_corta_y_une_los_tramos_y_pone_las_palabras_en_su_tiempo(grabacion, tmp_path, monkeypatch):
    t, ids = grabacion
    _claude(tmp_path, monkeypatch, {"is_error": False, "result": json.dumps(_buena(ids))})
    t = reparto.agrupar(t["id"], lambda m: None)
    v2 = t["propuesta"]["videos"][1]                                                           # la toma buena de B + el cierre que venía en «toma 10»
    video, palabras = reparto.armar(t, v2, lambda m: None)
    dur = sum(x["hasta"] - x["desde"] for x in v2["tramos"])
    assert video.parent == tmp_path / "_subidas" and unir._sonda(video)["duracion"] == pytest.approx(dur, abs=.2)
    assert " ".join(p["w"] for p in palabras) == f"{B} {B_CIERRE}"
    largo_b = v2["tramos"][0]["hasta"]
    cierre = next(p for p in palabras if p["w"] == "siempre")
    assert cierre["s"] == pytest.approx(largo_b + (7.4 - v2["tramos"][1]["desde"]), abs=.02)   # «siempre» sonaba en 7,4 s de su archivo
    assert all(a["s"] <= b["s"] for a, b in zip(palabras, palabras[1:]))
    solo, ps = reparto.armar(t, {"id": "v9", "titulo": "x", "tramos": [{"archivo": ids["gancho"], "desde": 0.0,
                                                                         "hasta": next(a["duracion"] for a in t["archivos"] if a["id"] == ids["gancho"])}]})
    assert solo.name == "toma 1.mp4" and ps == _palabras(A)                                    # un archivo entero se usa tal cual
    assert all(Path(a["video"]).is_file() for a in t["archivos"])                              # los originales siguen ahí


def test_aprobar_prepara_los_videos_uno_tras_otro_y_el_que_falla_no_tumba_a_los_demas(grabacion, tmp_path, monkeypatch):
    t, ids = grabacion
    _claude(tmp_path, monkeypatch, {"is_error": False, "result": json.dumps(_buena(ids))})
    t = reparto.agrupar(t["id"], lambda m: None)
    activos, maximo, hechos = [], [0], []

    def preparar(video, nombre, avance):
        activos.append(nombre)
        maximo[0] = max(maximo[0], len(activos))
        try:
            assert Path(video).is_file() and (config.PROYECTOS / nombre / "palabras.json").is_file()   # llega armado y ya transcrito
            if nombre == "mira-el-lente":
                raise OSError(28, "No space left on device")
            hechos.append(nombre)
        finally:
            activos.pop()
    avisos = []
    t = reparto.preparar_videos(t["id"], preparar, avisos.append)
    estados = {v["titulo"]: (v["estado"], v.get("proyecto")) for v in t["propuesta"]["videos"]}
    assert maximo[0] == 1 and hechos == ["arranca-fuerte", "tres-ideas"] and t["estado"] == "lista"
    assert estados["Arranca fuerte"] == ("listo", "arranca-fuerte") and estados["Tres ideas"] == ("listo", "tres-ideas")
    assert estados["Mira el lente"][0] == "error" and "El disco está lleno" in t["propuesta"]["videos"][1]["error"]
    assert any("video 2 de 3" in a for a in avisos)
    with pytest.raises(errores.Aviso, match="ya se está preparando"):
        reparto.proponer(t["id"], {"videos": t["propuesta"]["videos"], "sobran": []})
    hechos.clear()
    t = reparto.preparar_videos(t["id"], lambda v, n, a: hechos.append(n), lambda m: None)    # se retoma: solo el que faltaba
    assert hechos == ["mira-el-lente"] and all(v["estado"] == "listo" for v in t["propuesta"]["videos"])


# ---------- la pantalla ----------
def test_la_pantalla_ofrece_ver_cuantos_videos_salen_y_deja_mover_juntar_y_separar():
    js = (Path(__file__).resolve().parent.parent / "app" / "app.js").read_text(encoding="utf-8")
    for pieza in ('"/api/tanda"', '"/api/tanda-propuesta"', '"/api/tanda-aprobar"', '"/api/tanda-seguir"', "Ver cuántos videos salen",
                  "data-junta", "data-separa", "data-mueve", "data-tsube", "Aprobar y preparar", "Sobran"):
        assert pieza in js, pieza
    assert "confirm(" in js[js.index("tanAprobar"):]   # nada se prepara sin el sí de la persona


def test_la_vista_de_la_tanda_dice_que_se_dice_en_cada_tramo(grabacion, tmp_path, monkeypatch):
    t, ids = grabacion
    _claude(tmp_path, monkeypatch, {"is_error": False, "result": json.dumps(_buena(ids))})
    t = reparto.agrupar(t["id"], lambda m: None)
    v = reparto.vista(t)
    partido = v["propuesta"]["videos"][1]["tramos"][1]
    assert partido["nombre"] == "toma 10.mp4" and partido["entero"] is False and partido["texto"] == B_CIERRE
    assert v["propuesta"]["videos"][0]["tramos"][0]["entero"] is True and "texto" not in t["propuesta"]["videos"][0]["tramos"][0]   # no se guarda
