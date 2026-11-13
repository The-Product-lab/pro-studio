"""F7 (T-0193): sin el PATH de Windows el lote no muere ni finge que las guardas funcionan."""
from estudio import entorno, lote


def test_windows_exe_busca_en_system32_cuando_el_path_esta_vacio(monkeypatch, tmp_path):
    (tmp_path / "attrib.exe").write_text("")
    monkeypatch.setenv("PATH", "")
    monkeypatch.setattr(entorno, "SYSTEM32", tmp_path)
    assert entorno.windows_exe("attrib.exe") == str(tmp_path / "attrib.exe")


def test_sin_el_ejecutable_devuelve_none_y_correr_no_lanza(monkeypatch, tmp_path):
    monkeypatch.setenv("PATH", "")
    monkeypatch.setattr(entorno, "SYSTEM32", tmp_path)
    monkeypatch.setattr(entorno, "RUTAS", {})
    assert entorno.windows_exe("attrib.exe") is None
    assert entorno.correr_windows("attrib.exe", ["-P"]) is None


def test_liberar_crudo_sin_attrib_registra_y_no_detiene(monkeypatch, tmp_path):
    monkeypatch.setattr(entorno, "correr_windows", lambda *a, **k: None)
    monkeypatch.setattr(lote, "_windows", lambda r: str(r))
    motivo = lote.liberar_crudo(tmp_path / "OneDrive" / "C1.MP4")
    assert motivo and "attrib.exe" in motivo


def test_liberar_crudo_con_codigo_1_es_aviso(monkeypatch, tmp_path):
    class R:
        returncode = 1
    monkeypatch.setattr(entorno, "correr_windows", lambda *a, **k: R())
    monkeypatch.setattr(lote, "_windows", lambda r: str(r))
    assert "código 1" in lote.liberar_crudo(tmp_path / "OneDrive" / "C1.MP4")


def test_liberar_crudo_fuera_de_onedrive_no_hace_nada(tmp_path):
    assert lote.liberar_crudo(tmp_path / "C1.MP4") is None


def test_holgura_none_cuando_no_se_puede_medir(monkeypatch):
    monkeypatch.setattr(entorno, "correr_windows", lambda *a, **k: None)
    assert lote.holgura_ubuntu_gb() is None      # antes devolvía 999 y apagaba la guarda en silencio
