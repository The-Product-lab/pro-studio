"""F6 (T-0193): disco de trabajo fijo con espacio, y enlaces rotos detectados y rehechos (no `FileExistsError`)."""
import pytest

from estudio import disco


def _tipo(monkeypatch, tipos):
    monkeypatch.setattr(disco, "tipo_unidad", lambda l: tipos.get(l))


def test_unidad_extraible_se_rechaza_con_el_nombre_de_la_unidad(monkeypatch):
    _tipo(monkeypatch, {"G": 2})
    with pytest.raises(disco.DiscoError, match=r"unidad G:.*extraíble"):
        disco.validar_trabajo_en("/mnt/g/StudioProyectos")


def test_unidad_que_no_se_puede_medir_se_rechaza(monkeypatch):
    _tipo(monkeypatch, {})
    with pytest.raises(disco.DiscoError, match="no pude comprobar"):
        disco.validar_trabajo_en("/mnt/e/StudioProyectos")


def test_unidad_bloqueada_aunque_windows_la_marque_fija(monkeypatch):
    _tipo(monkeypatch, {"H": 3})
    monkeypatch.setenv(disco.BLOQUEADAS_ENV, "g, h")
    with pytest.raises(disco.DiscoError, match="bloqueadas"):
        disco.validar_trabajo_en("/mnt/h/x")


def test_disco_de_linux_con_espacio_pasa_y_sin_espacio_no(tmp_path):
    disco.validar_trabajo_en(tmp_path / "nueva" / "carpeta", minimo_gb=0)
    with pytest.raises(disco.DiscoError, match="libres"):
        disco.validar_trabajo_en(tmp_path, minimo_gb=10 ** 9)


def test_enlace_roto_se_detecta_y_enlazar_lo_rehace(tmp_path):
    proyectos, datos = tmp_path / "proyectos", tmp_path / "datos"
    proyectos.mkdir()
    (proyectos / "c1").symlink_to(datos / "c1", target_is_directory=True)       # destino que no existe
    assert [e.name for e, _ in disco.rotos(proyectos)] == ["c1"]
    disco.enlazar(proyectos / "c1", datos / "c1")                                # mismo nombre, antes era FileExistsError
    assert disco.rotos(proyectos) == [] and (proyectos / "c1").resolve() == (datos / "c1").resolve()


def test_enlace_correcto_no_se_toca_y_una_carpeta_real_no_se_pisa(tmp_path):
    destino = tmp_path / "d"
    destino.mkdir()
    (tmp_path / "e").symlink_to(destino, target_is_directory=True)
    disco.enlazar(tmp_path / "e", destino)
    (tmp_path / "real").mkdir()
    with pytest.raises(disco.DiscoError, match="no lo piso"):
        disco.enlazar(tmp_path / "real", destino)


def test_base_movido_el_enlace_apunta_al_nuevo_destino(tmp_path):
    (tmp_path / "viejo").mkdir()
    (tmp_path / "p").symlink_to(tmp_path / "viejo", target_is_directory=True)
    disco.enlazar(tmp_path / "p", tmp_path / "nuevo")
    assert (tmp_path / "p").resolve() == (tmp_path / "nuevo").resolve()


def test_revisar_enlaces_reporta_unidad_ausente_y_solo_repara_con_permiso(monkeypatch, tmp_path):
    _tipo(monkeypatch, {"Q": 3})
    (tmp_path / "x").symlink_to("/mnt/q/StudioProyectos-t0193/x", target_is_directory=True)
    inf = disco.revisar_enlaces(tmp_path)
    assert inf[0]["proyecto"] == "x" and inf[0]["unidad"] == "Q"
    local = tmp_path / "datos"
    local.mkdir()
    (tmp_path / "y").symlink_to(local / "y", target_is_directory=True)
    disco.revisar_enlaces(tmp_path, reparar=True)
    assert (local / "y").is_dir()
