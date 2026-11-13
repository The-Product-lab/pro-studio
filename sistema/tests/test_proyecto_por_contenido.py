"""Un proyecto es de UN video, reconocido por su contenido. Caso real (Pablo, 11-nov): «le subo un video, me pone un guion de
otra cosa en segundos» — la app reconocía el video por el nombre del archivo y otro video heredaba el guion del anterior."""
from estudio import config, ingesta


def _video(ruta, contenido: bytes):
    ruta.write_bytes(contenido)
    return ruta


def _casa(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PROYECTOS", tmp_path / "proyectos")
    (tmp_path / "proyectos").mkdir()


def test_el_mismo_video_retoma_su_proyecto(tmp_path, monkeypatch):
    _casa(tmp_path, monkeypatch)
    v = _video(tmp_path / "IMG_1.MOV", b"a" * 5000)
    assert ingesta.proyecto_para(v, "img-1") == ("img-1", False)
    assert ingesta.proyecto_para(v, "img-1") == ("img-1", True)


def test_otro_video_con_el_mismo_nombre_no_hereda_el_guion(tmp_path, monkeypatch):
    _casa(tmp_path, monkeypatch)
    ingesta.proyecto_para(_video(tmp_path / "a.mov", b"a" * 5000), "img-1")
    otro = _video(tmp_path / "b.mov", b"b" * 5000)
    assert ingesta.proyecto_para(otro, "img-1") == ("img-1-2", False)
    assert ingesta.proyecto_para(otro, "img-1") == ("img-1-2", True)


def test_mismo_tamano_y_distinto_final_es_otro_video(tmp_path, monkeypatch):
    _casa(tmp_path, monkeypatch)
    n = 3 * ingesta.HUELLA_TROZO
    a = _video(tmp_path / "a.mov", b"x" * n)
    b = _video(tmp_path / "b.mov", b"x" * (n - 1) + b"y")
    assert ingesta.huella(a) != ingesta.huella(b)


def test_empezar_de_cero_no_toca_lo_anterior(tmp_path, monkeypatch):
    _casa(tmp_path, monkeypatch)
    v = _video(tmp_path / "a.mov", b"a" * 5000)
    ingesta.proyecto_para(v, "img-1")
    (config.PROYECTOS / "img-1" / "machote.json").write_text("{}")
    assert ingesta.proyecto_para(v, "img-1", de_cero=True) == ("img-1-2", False)
    assert (config.PROYECTOS / "img-1" / "machote.json").exists()


def test_proyecto_anterior_a_la_regla_se_adopta_solo_por_nombre_exacto(tmp_path, monkeypatch):
    _casa(tmp_path, monkeypatch)
    (config.PROYECTOS / "img-1").mkdir()        # sin .huella: hecho antes de esta regla
    (config.PROYECTOS / "img-1-2").mkdir()      # otro viejo, de un archivo «IMG_1 2»
    a = _video(tmp_path / "a.mov", b"a" * 5000)
    assert ingesta.proyecto_para(a, "img-1") == ("img-1", True)
    b = _video(tmp_path / "b.mov", b"b" * 5000)
    assert ingesta.proyecto_para(b, "img-1") == ("img-1-3", False)   # nunca adopta el viejo «img-1-2», que es de otro video
